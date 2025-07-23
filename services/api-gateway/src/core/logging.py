"""
Logging Configuration

Centralized logging setup for the API Gateway service with structured logging,
request tracking, and proper log formatting.
"""

import json
import logging
import logging.config
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import uuid
from pathlib import Path

from .config import get_settings

settings = get_settings()


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process']:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class RequestIDFilter(logging.Filter):
    """Filter to add request ID to log records"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request ID to log record"""
        # Try to get request ID from context
        request_id = getattr(record, 'request_id', None)
        if not request_id:
            # Generate a new request ID if not present
            request_id = str(uuid.uuid4())
        
        record.request_id = request_id
        return True


def setup_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    json_logs: bool = False
) -> None:
    """
    Setup logging configuration
    
    Args:
        log_level: Log level override
        log_format: Log format override
        json_logs: Whether to use JSON formatting
    """
    level = log_level or settings.log_level
    format_str = log_format or settings.log_format
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": format_str,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": JSONFormatter,
            },
        },
        "filters": {
            "request_id": {
                "()": RequestIDFilter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "json" if json_logs else "standard",
                "filters": ["request_id"],
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": level,
                "formatter": "json",
                "filters": ["request_id"],
                "filename": "logs/api-gateway.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filters": ["request_id"],
                "filename": "logs/api-gateway-errors.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file"],
                "level": level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "fastapi": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "httpx": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "redis": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }
    
    # Add error file handler for production
    if settings.environment == "production":
        logging_config["loggers"][""]["handlers"].append("error_file")
    
    logging.config.dictConfig(logging_config)
    
    # Set up specific logger levels
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    
    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {level}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"JSON logs: {json_logs}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)


def log_request(
    method: str,
    path: str,
    status_code: int,
    response_time: float,
    request_id: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log request information
    
    Args:
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        response_time: Response time in seconds
        request_id: Request ID
        user_id: User ID if authenticated
        ip_address: Client IP address
        user_agent: User agent string
        extra_data: Additional data to log
    """
    logger = get_logger("api_gateway.access")
    
    log_data = {
        "request_id": request_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "response_time": response_time,
        "user_id": user_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }
    
    if extra_data:
        log_data.update(extra_data)
    
    logger.info(
        f"{method} {path} - {status_code} - {response_time:.3f}s",
        extra=log_data
    )


def log_error(
    error: Exception,
    request_id: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log error information
    
    Args:
        error: Exception object
        request_id: Request ID
        context: Additional context data
    """
    logger = get_logger("api_gateway.error")
    
    log_data = {
        "request_id": request_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    
    if context:
        log_data.update(context)
    
    logger.error(
        f"Error: {type(error).__name__}: {str(error)}",
        extra=log_data,
        exc_info=True
    )


def log_service_call(
    service_name: str,
    method: str,
    path: str,
    status_code: int,
    response_time: float,
    request_id: str,
    success: bool = True,
    error_message: Optional[str] = None
) -> None:
    """
    Log downstream service call
    
    Args:
        service_name: Name of the downstream service
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        response_time: Response time in seconds
        request_id: Request ID
        success: Whether the call was successful
        error_message: Error message if failed
    """
    logger = get_logger("api_gateway.service_call")
    
    log_data = {
        "request_id": request_id,
        "service_name": service_name,
        "method": method,
        "path": path,
        "status_code": status_code,
        "response_time": response_time,
        "success": success,
        "error_message": error_message,
    }
    
    if success:
        logger.info(
            f"Service call to {service_name}: {method} {path} - {status_code} - {response_time:.3f}s",
            extra=log_data
        )
    else:
        logger.error(
            f"Service call failed to {service_name}: {method} {path} - {status_code} - {error_message}",
            extra=log_data
        )