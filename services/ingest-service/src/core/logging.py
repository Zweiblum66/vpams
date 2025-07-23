"""
Logging configuration for the Ingest Service
"""

import logging
import structlog
from typing import Any, Dict
from .config import settings


def configure_logging() -> None:
    """Configure structured logging for the service"""
    
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(message)s"
    )
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name)


def log_ingest_event(
    logger: structlog.stdlib.BoundLogger,
    event_type: str,
    file_path: str,
    **kwargs: Any
) -> None:
    """Log an ingest-related event with consistent structure"""
    logger.info(
        event_type,
        file_path=file_path,
        service="ingest-service",
        **kwargs
    )


def log_performance_metric(
    logger: structlog.stdlib.BoundLogger,
    operation: str,
    duration_ms: float,
    **kwargs: Any
) -> None:
    """Log a performance metric"""
    logger.info(
        "performance_metric",
        operation=operation,
        duration_ms=duration_ms,
        service="ingest-service",
        **kwargs
    )


def log_error(
    logger: structlog.stdlib.BoundLogger,
    error_type: str,
    error_message: str,
    **kwargs: Any
) -> None:
    """Log an error with consistent structure"""
    logger.error(
        error_type,
        error_message=error_message,
        service="ingest-service",
        **kwargs
    )