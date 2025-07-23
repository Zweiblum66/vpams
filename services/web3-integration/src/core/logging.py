"""Logging configuration for Web3 Integration Service"""

import logging
import sys
from typing import Optional

def setup_logging(name: Optional[str] = None) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name or "web3-integration")
    
    # Set level from config
    from .config import settings
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger