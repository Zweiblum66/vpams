"""Logging configuration for Metaverse Support Service"""

import logging
import structlog
from typing import Any

from .config import settings

def setup_logging() -> Any:
    """Setup structured logging"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Get logger
    logger = structlog.get_logger("metaverse-support")
    
    return logger