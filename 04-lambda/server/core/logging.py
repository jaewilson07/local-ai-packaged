"""Structured logging configuration."""

import logging
import sys


def setup_logging(level: str = "info") -> None:
    """
    Setup structured logging for the application.
    
    Args:
        level: Log level (debug, info, warning, error)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)

