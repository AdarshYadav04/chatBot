"""Retrieval module for RAG-based question answering."""
import logging
import threading
from typing import List, Optional
from pathlib import Path
from functools import wraps
import time

from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)


class RetrievalError(Exception):
    """Custom exception for retrieval errors."""
    pass


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry operations on failure."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay} seconds..."
                        )
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            raise RetrievalError(f"Failed after {max_retries} attempts: {last_exception}") from last_exception
        return wrapper
    return decorator


class VectorStoreRetriever:
    """Manages vector store and retrieval operations with production-ready features."""
    
    _lock = threading.Lock()  # Thread safety for singleton pattern
    
    def __init__(
        self,
        vectordb_path: Optional[str] = None,
        embedding_model: Optional[str] = None,
        api_key: Optional[str] = None,
        k: int = 4,
        search_type: str = "similarity",
        timeout: Optional[float] = None
    ):
        """
        Initialize the vector store retriever.
        
        Args:
            vectordb_path: Path to the vector database directory
            embedding_model: Name of the embedding model
            api_key: Google API key for embeddings
            k: Number of documents to retrieve
            search_type: Type of search ("similarity", "mmr", etc.)
            timeout: Timeout in seconds for retrieval operations
        """
        self.vectordb_path = vectordb_path or settings.VECTORDB_PATH
        self.embedding_model = embedding_model or settings.EMBEDDING_MODEL
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.k = k or settings.RETRIEVER_K
        self.search_type = search_type or settings.RETRIEVER_SEARCH_TYPE
        self.timeout = timeout or getattr(settings, 'RETRIEVAL_TIMEOUT', 30.0)
        
        if not self.api_key:
            raise ValueError("API key is required for embeddings")
        
        self._embeddings: Optional[GoogleGenerativeAIEmbeddings] = None
        self._vectorstore: Optional[FAISS] = None
        self._retriever: Optional[BaseRetriever] = None
        self._initialized = False
        
    @retry_on_failure(max_retries=3, delay=1.0)
    def _initialize_embeddings(self) -> GoogleGenerativeAIEmbeddings:
        """Initialize and return the embeddings model."""
        if self._embeddings is None:
            logger.info(f"Initializing embeddings model: {self.embedding_model}")
            try:
                self._embeddings = GoogleGenerativeAIEmbeddings(
                    model=self.embedding_model,
                    google_api_key=self.api_key,
                )
                logger.info("Embeddings model initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize embeddings: {e}")
                raise RetrievalError(f"Failed to initialize embeddings: {e}") from e
        return self._embeddings
    
    @retry_on_failure(max_retries=2, delay=0.5)
    def _load_vectorstore(self) -> FAISS:
        """Load the vector store from disk with error handling."""
        if self._vectorstore is None:
            logger.info(f"Loading vector store from: {self.vectordb_path}")
            
            # Validate path exists
            vectordb_path = Path(self.vectordb_path)
            if not vectordb_path.exists():
                error_msg = (
                    f"Vector database not found at: {self.vectordb_path}. "
                    "Please run ingestion first."
                )
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            # Check for required files
            required_files = ["index.faiss", "index.pkl"]
            for file_name in required_files:
                file_path = vectordb_path / file_name
                if not file_path.exists():
                    error_msg = f"Required vector database file not found: {file_path}"
                    logger.error(error_msg)
                    raise FileNotFoundError(error_msg)
            
            try:
                embeddings = self._initialize_embeddings()
                
                # Load vector store with proper deserialization settings
                self._vectorstore = FAISS.load_local(
                    str(vectordb_path),
                    embeddings,
                    allow_dangerous_deserialization=True,
                )
                self._initialized = True
                logger.info("Vector store loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load vector store: {e}", exc_info=True)
                raise RetrievalError(f"Failed to load vector store: {e}") from e
        
        return self._vectorstore
    
    def get_retriever(self) -> BaseRetriever:
        """
        Get or create the retriever instance.
        
        Returns:
            BaseRetriever: Configured retriever instance
        """
        if self._retriever is None:
            vectorstore = self._load_vectorstore()
            
            # Configure retriever with search parameters
            search_kwargs = {"k": self.k}
            
            self._retriever = vectorstore.as_retriever(
                search_type=self.search_type,
                search_kwargs=search_kwargs
            )
            logger.info(f"Retriever initialized with k={self.k}, search_type={self.search_type}")
        
        return self._retriever
    
    def retrieve_documents(self, query: str, k: Optional[int] = None) -> List[Document]:
        """
        Retrieve documents for a given query with error handling and validation.
        
        Args:
            query: The search query (must be non-empty)
            k: Number of documents to retrieve (overrides default if provided)
            
        Returns:
            List of retrieved documents
            
        Raises:
            RetrievalError: If retrieval fails
            ValueError: If query is invalid
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        # Validate k parameter
        if k is not None and (k < 1 or k > 100):
            raise ValueError("k must be between 1 and 100")
        
        start_time = time.time()
        
        try:
            retriever = self.get_retriever()
            
            # Temporarily override k if provided
            if k is not None and k != self.k:
                search_kwargs = {"k": k}
                temp_retriever = self._vectorstore.as_retriever(
                    search_type=self.search_type,
                    search_kwargs=search_kwargs
                )
                docs = temp_retriever.get_relevant_documents(query)
            else:
                docs = retriever.get_relevant_documents(query)
            
            elapsed_time = time.time() - start_time
            logger.debug(
                f"Retrieved {len(docs)} documents for query in {elapsed_time:.2f}s: "
                f"{query[:50]}..."
            )
            
            if not docs:
                logger.warning(f"No documents retrieved for query: {query[:50]}...")
            
            return docs
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"Retrieval failed after {elapsed_time:.2f}s for query '{query[:50]}...': {e}",
                exc_info=True
            )
            raise RetrievalError(f"Failed to retrieve documents: {e}") from e
    
    def get_vectorstore(self) -> FAISS:
        """
        Get the vector store instance.
        
        Returns:
            FAISS: The vector store instance
        """
        return self._load_vectorstore()


# Global retriever instance (lazy-loaded, thread-safe)
_retriever_instance: Optional[VectorStoreRetriever] = None
_instance_lock = threading.Lock()


def get_retriever() -> BaseRetriever:
    """
    Get the global retriever instance (thread-safe singleton).
    
    Returns:
        BaseRetriever: The configured retriever
        
    Raises:
        RetrievalError: If retriever cannot be initialized
    """
    global _retriever_instance
    if _retriever_instance is None:
        with _instance_lock:
            # Double-check locking pattern
            if _retriever_instance is None:
                try:
                    _retriever_instance = VectorStoreRetriever()
                    logger.info("Global retriever instance created")
                except Exception as e:
                    logger.error(f"Failed to create retriever instance: {e}")
                    raise RetrievalError(f"Failed to initialize retriever: {e}") from e
    return _retriever_instance.get_retriever()


def get_vectorstore_retriever() -> VectorStoreRetriever:
    """
    Get the global VectorStoreRetriever instance (thread-safe singleton).
    
    Returns:
        VectorStoreRetriever: The retriever manager instance
        
    Raises:
        RetrievalError: If retriever cannot be initialized
    """
    global _retriever_instance
    if _retriever_instance is None:
        with _instance_lock:
            if _retriever_instance is None:
                try:
                    _retriever_instance = VectorStoreRetriever()
                    logger.info("Global retriever instance created")
                except Exception as e:
                    logger.error(f"Failed to create retriever instance: {e}")
                    raise RetrievalError(f"Failed to initialize retriever: {e}") from e
    return _retriever_instance

