"""Configuration management for the chatbot application."""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Vector Database
    VECTORDB_PATH: str = os.getenv("VECTORDB_PATH", "./vectordb")
    
    # Model Configuration
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    
    # Retrieval Configuration
    RETRIEVER_K: int = int(os.getenv("RETRIEVER_K", "4"))  # Number of documents to retrieve
    RETRIEVER_SEARCH_TYPE: str = os.getenv("RETRIEVER_SEARCH_TYPE", "similarity")
    RETRIEVAL_TIMEOUT: float = float(os.getenv("RETRIEVAL_TIMEOUT", "30.0"))
    RETRIEVAL_MAX_RETRIES: int = int(os.getenv("RETRIEVAL_MAX_RETRIES", "3"))
    
    # Application
    APP_NAME: str = os.getenv("APP_NAME", "FAQ Chatbot API")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # API Configuration
    API_TIMEOUT: float = float(os.getenv("API_TIMEOUT", "60.0"))
    MAX_REQUEST_SIZE: int = int(os.getenv("MAX_REQUEST_SIZE", "1048576"))  # 1MB default
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # CORS Configuration
    # When using credentials (cookies/auth), browser requires a specific origin, not "*".
    
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS")
    
    # LLM Configuration
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS: Optional[int] = int(os.getenv("LLM_MAX_TOKENS", "1000")) if os.getenv("LLM_MAX_TOKENS") else None
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "30.0"))
    
    @classmethod
    def get_cors_origins(cls) -> list:
        """
        Parse CORS origins from environment variable.
        When allow_credentials=True, browser forbids '*'; use explicit origin(s).
        """
        if not cls.CORS_ORIGINS or cls.CORS_ORIGINS.strip() == "":
            return ["*"]
        if cls.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in cls.CORS_ORIGINS.split(",") if origin.strip()]
    
    @classmethod
    def validate(cls) -> None:
        """Validate that required settings are present and valid."""
        errors = []
        
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY environment variable is required")
        
        if not os.path.exists(cls.VECTORDB_PATH):
            errors.append(f"Vector database path does not exist: {cls.VECTORDB_PATH}")
        
        if cls.RETRIEVER_K < 1 or cls.RETRIEVER_K > 100:
            errors.append("RETRIEVER_K must be between 1 and 100")
        
        if cls.RETRIEVAL_TIMEOUT <= 0:
            errors.append("RETRIEVAL_TIMEOUT must be greater than 0")
        
        if cls.API_TIMEOUT <= 0:
            errors.append("API_TIMEOUT must be greater than 0")
        
        if cls.LLM_TEMPERATURE < 0 or cls.LLM_TEMPERATURE > 2:
            errors.append("LLM_TEMPERATURE must be between 0 and 2")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


# Global settings instance
settings = Settings()


def validate_settings():
    """
    Validate settings. Call this explicitly if you want to validate at startup.
    
    Raises:
        ValueError: If required settings are missing
    """
    settings.validate()

