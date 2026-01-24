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

# Get the project root directory (parent of app directory)
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_DOCS_PATH = PROJECT_ROOT / "app" / "docs" / "faq.txt"

# Allow DOCS_PATH to be relative to project root or absolute
DOCS_PATH_ENV = os.getenv("DOCS_PATH", None)
if DOCS_PATH_ENV:
    DOCS_PATH = Path(DOCS_PATH_ENV) if Path(DOCS_PATH_ENV).is_absolute() else PROJECT_ROOT / DOCS_PATH_ENV
else:
    DOCS_PATH = DEFAULT_DOCS_PATH

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "250"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "10"))


def validate_inputs() -> None:
    """Validate that all required inputs are present."""
    errors = []
    
    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY environment variable is required")
    
    # Convert to Path object if it's a string
    docs_file = DOCS_PATH if isinstance(DOCS_PATH, Path) else Path(DOCS_PATH)
    
    if not docs_file.exists():
        errors.append(f"Document file not found: {docs_file}")
        logger.error(f"Looking for file at: {docs_file.absolute()}")
        # Suggest alternative paths
        alt_path = PROJECT_ROOT / "app" / "docs" / "faq.txt"
        if alt_path.exists():
            logger.info(f"Found file at alternative location: {alt_path.absolute()}")
    
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
    
    # Log the resolved path
    logger.info(f"Using document file: {docs_file.absolute()}")


def load_documents() -> list:
    """Load documents from the specified path."""
    try:
        # Ensure we have a Path object
        docs_file = DOCS_PATH if isinstance(DOCS_PATH, Path) else Path(DOCS_PATH)
        docs_file_str = str(docs_file)
        
        logger.info(f"Loading documents from: {docs_file.absolute()}")
        loader = TextLoader(docs_file_str, encoding="utf-8")
        documents = loader.load()
        
        # Log document info
        total_chars = sum(len(doc.page_content) for doc in documents)
        logger.info(f"Loaded {len(documents)} document(s)")
        logger.info(f"Total characters: {total_chars:,}")
        
        return documents
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        logger.error(f"Please ensure faq.txt exists at: {DOCS_PATH}")
        sys.exit(1)
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
