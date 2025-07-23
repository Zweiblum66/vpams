"""
Logging configuration for Plugin Service
"""

import logging
import sys
import structlog
from datetime import datetime
from typing import Any, Dict

from .config import settings


def configure_logging():
    """Configure structured logging"""
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper())
    )
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        add_service_context,
    ]
    
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def add_service_context(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add service context to all log entries"""
    event_dict["service"] = settings.service_name
    event_dict["environment"] = settings.environment
    event_dict["version"] = settings.service_version
    
    # Add timestamp if not present
    if "timestamp" not in event_dict:
        event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    
    return event_dict


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger instance"""
    return structlog.get_logger(name)