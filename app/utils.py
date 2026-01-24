"""Utility functions for the chatbot application."""
import logging
import sys
from typing import Optional
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> None:
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        format_string: Optional custom format string
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "[%(filename)s:%(lineno)d] - %(message)s"
        )
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=log_level,
        format=format_string,
        handlers=handlers,
        force=True  # Override any existing configuration
    )


def validate_file_exists(file_path: str, description: str = "File") -> Path:
    """
    Validate that a file exists.
    
    Args:
        file_path: Path to the file
        description: Description of the file for error messages
        
    Returns:
        Path object if file exists
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {file_path}")
    return path

