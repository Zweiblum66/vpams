"""
Logging configuration for Disaster Recovery Service
"""

import logging
import sys
from datetime import datetime
import json
from typing import Any, Dict

from .config import settings


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": settings.SERVICE_NAME,
        }
        
        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


def setup_logging():
    """Configure logging for the application"""
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Use JSON formatter in production, simple formatter in development
    if settings.DEBUG:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        formatter = JSONFormatter()
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


# Initialize logging on module import
setup_logging()