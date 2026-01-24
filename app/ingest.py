"""Document ingestion script for creating vector database."""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
VECTORDB_PATH = os.getenv("VECTORDB_PATH", "./vectordb")
DOCS_PATH = os.getenv("DOCS_PATH", "app/docs/faq.txt")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "250"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "10"))


def validate_inputs() -> None:
    """Validate that all required inputs are present."""
    errors = []
    
    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY environment variable is required")
    
    docs_file = Path(DOCS_PATH)
    if not docs_file.exists():
        errors.append(f"Document file not found: {DOCS_PATH}")
    
    if CHUNK_SIZE < 1:
        errors.append("CHUNK_SIZE must be greater than 0")
    
    if CHUNK_OVERLAP < 0:
        errors.append("CHUNK_OVERLAP must be non-negative")
    
    if CHUNK_OVERLAP >= CHUNK_SIZE:
        errors.append("CHUNK_OVERLAP must be less than CHUNK_SIZE")
    
    if errors:
        logger.error("Validation errors:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)


def load_documents() -> list:
    """Load documents from the specified path."""
    try:
        logger.info(f"Loading documents from: {DOCS_PATH}")
        loader = TextLoader(DOCS_PATH, encoding="utf-8")
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} document(s)")
        return documents
    except Exception as e:
        logger.error(f"Failed to load documents: {e}", exc_info=True)
        sys.exit(1)


def split_documents(documents: list) -> list:
    """Split documents into chunks."""
    try:
        logger.info(f"Splitting documents (chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP})")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        chunks = text_splitter.split_documents(documents)
        logger.info(f"Created {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Failed to split documents: {e}", exc_info=True)
        sys.exit(1)


def create_vectorstore(chunks: list) -> FAISS:
    """Create and return the vector store."""
    try:
        logger.info("Creating embeddings and vector store...")
        logger.info("This may take a few minutes depending on the number of chunks...")
        
        embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            google_api_key=GEMINI_API_KEY,
        )
        
        vectorstore = FAISS.from_documents(chunks, embeddings)
        logger.info("Vector store created successfully")
        return vectorstore
    except Exception as e:
        logger.error(f"Failed to create vector store: {e}", exc_info=True)
        sys.exit(1)


def save_vectorstore(vectorstore: FAISS) -> None:
    """Save the vector store to disk."""
    try:
        vectordb_path = Path(VECTORDB_PATH)
        vectordb_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving vector store to: {VECTORDB_PATH}")
        vectorstore.save_local(VECTORDB_PATH)
        logger.info("Vector store saved successfully")
        
        # Verify files were created
        required_files = ["index.faiss", "index.pkl"]
        for file_name in required_files:
            file_path = vectordb_path / file_name
            if file_path.exists():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                logger.info(f"  - {file_name}: {size_mb:.2f} MB")
            else:
                logger.warning(f"  - {file_name}: not found")
                
    except Exception as e:
        logger.error(f"Failed to save vector store: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main ingestion function."""
    logger.info("=" * 60)
    logger.info("Starting document ingestion process")
    logger.info("=" * 60)
    
    # Validate inputs
    validate_inputs()
    
    # Load documents
    documents = load_documents()
    
    # Split documents
    chunks = split_documents(documents)
    
    # Create vector store
    vectorstore = create_vectorstore(chunks)
    
    # Save vector store
    save_vectorstore(vectorstore)
    
    logger.info("=" * 60)
    logger.info("Ingestion complete!")
    logger.info(f"Vector store saved at: {VECTORDB_PATH}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
