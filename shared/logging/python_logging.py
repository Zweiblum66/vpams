"""
MAMS Structured Logging Configuration

This module provides standardized logging configuration for all MAMS services.
It ensures consistent log format, structured logging, and proper integration
with the log aggregation system.
"""

import json
import logging
import logging.config
import os
import sys
import time
import traceback
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from pythonjsonlogger import jsonlogger


# Context variables for request tracking
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
trace_id_ctx: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
span_id_ctx: ContextVar[Optional[str]] = ContextVar("span_id", default=None)


class MAMSJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for MAMS logs."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hostname = os.uname().nodename
        self.service_name = os.getenv("SERVICE_NAME", "unknown")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.cluster = os.getenv("CLUSTER_NAME", "local")

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Standard fields
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["service_name"] = self.service_name
        log_record["hostname"] = self.hostname
        log_record["environment"] = self.environment
        log_record["cluster"] = self.cluster
        log_record["process_id"] = os.getpid()
        log_record["thread_id"] = record.thread
        
        # Context fields
        if request_id_ctx.get():
            log_record["request_id"] = request_id_ctx.get()
        if user_id_ctx.get():
            log_record["user_id"] = user_id_ctx.get()
        if trace_id_ctx.get():
            log_record["trace_id"] = trace_id_ctx.get()
        if span_id_ctx.get():
            log_record["span_id"] = span_id_ctx.get()
        
        # Exception information
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": "".join(traceback.format_exception(*record.exc_info))
            }
        
        # Function and location info
        log_record["function"] = record.funcName
        log_record["filename"] = record.filename
        log_record["line_number"] = record.lineno
        
        # Performance data
        if hasattr(record, "execution_time"):
            log_record["execution_time"] = record.execution_time
        if hasattr(record, "memory_usage"):
            log_record["memory_usage"] = record.memory_usage


class StructlogProcessor:
    """Structlog processor for MAMS."""
    
    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Add timestamp
        event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Add context
        if request_id_ctx.get():
            event_dict["request_id"] = request_id_ctx.get()
        if user_id_ctx.get():
            event_dict["user_id"] = user_id_ctx.get()
        if trace_id_ctx.get():
            event_dict["trace_id"] = trace_id_ctx.get()
        if span_id_ctx.get():
            event_dict["span_id"] = span_id_ctx.get()
        
        return event_dict


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    use_json: bool = True,
    enable_structlog: bool = True,
    log_file: Optional[str] = None
) -> None:
    """
    Setup logging configuration for MAMS services.
    
    Args:
        service_name: Name of the service (e.g., "asset-management")
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting
        enable_structlog: Whether to enable structlog
        log_file: Optional log file path
    """
    # Set service name in environment
    os.environ["SERVICE_NAME"] = service_name
    
    # Configure logging
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": MAMSJSONFormatter,
                "format": "%(timestamp)s %(level)s %(service_name)s %(message)s"
            },
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json" if use_json else "standard",
                "stream": sys.stdout
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO", 
                "handlers": ["console"],
                "propagate": False
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            }
        }
    }
    
    # Add file handler if specified
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "json" if use_json else "standard",
            "filename": log_file,
            "maxBytes": 100 * 1024 * 1024,  # 100MB
            "backupCount": 5
        }
        
        # Add file handler to all loggers
        for logger_config in config["loggers"].values():
            logger_config["handlers"].append("file")
    
    logging.config.dictConfig(config)
    
    # Setup structlog if enabled
    if enable_structlog:
        structlog.configure(
            processors=[
                StructlogProcessor(),
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True
        )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def get_structlog_logger(name: str) -> structlog.BoundLogger:
    """Get a structlog logger instance."""
    return structlog.get_logger(name)


class LogContext:
    """Context manager for setting log context variables."""
    
    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ):
        self.request_id = request_id
        self.user_id = user_id
        self.trace_id = trace_id
        self.span_id = span_id
        self.tokens = []
    
    def __enter__(self):
        if self.request_id:
            self.tokens.append(request_id_ctx.set(self.request_id))
        if self.user_id:
            self.tokens.append(user_id_ctx.set(self.user_id))
        if self.trace_id:
            self.tokens.append(trace_id_ctx.set(self.trace_id))
        if self.span_id:
            self.tokens.append(span_id_ctx.set(self.span_id))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for token in reversed(self.tokens):
            token.var.reset(token)


def log_performance(func):
    """Decorator to log function performance."""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Create log record with execution time
            record = logger.makeRecord(
                logger.name,
                logging.INFO,
                func.__code__.co_filename,
                func.__code__.co_firstlineno,
                f"Function {func.__name__} executed successfully",
                (),
                None,
                func.__name__
            )
            record.execution_time = execution_time
            logger.handle(record)
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log the error with execution time
            record = logger.makeRecord(
                logger.name,
                logging.ERROR,
                func.__code__.co_filename,
                func.__code__.co_firstlineno,
                f"Function {func.__name__} failed: {str(e)}",
                (),
                sys.exc_info(),
                func.__name__
            )
            record.execution_time = execution_time
            logger.handle(record)
            raise
    
    return wrapper


# Security logging helpers
def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log security-related events."""
    logger = get_structlog_logger("security")
    
    log_data = {
        "event_type": event_type,
        "success": success,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if user_id:
        log_data["user_id"] = user_id
    if ip_address:
        log_data["ip_address"] = ip_address
    if resource:
        log_data["resource"] = resource
    if action:
        log_data["action"] = action
    if details:
        log_data["details"] = details
    
    if success:
        logger.info("Security event", **log_data)
    else:
        logger.warning("Security event failed", **log_data)


# Example usage and service-specific setup functions
def setup_fastapi_logging(app, service_name: str) -> None:
    """Setup logging for FastAPI applications."""
    setup_logging(service_name)
    
    @app.middleware("http")
    async def logging_middleware(request, call_next):
        import uuid
        request_id = str(uuid.uuid4())
        
        with LogContext(request_id=request_id):
            logger = get_logger("fastapi.request")
            start_time = time.time()
            
            # Log request
            logger.info(
                f"Request started: {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_ip": request.client.host if request.client else None
                }
            )
            
            try:
                response = await call_next(request)
                execution_time = time.time() - start_time
                
                # Log response
                logger.info(
                    f"Request completed: {response.status_code}",
                    extra={
                        "status_code": response.status_code,
                        "execution_time": execution_time
                    }
                )
                
                return response
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Request failed: {str(e)}",
                    extra={
                        "execution_time": execution_time,
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise