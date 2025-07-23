"""
Logging configuration for AI/ML Service
"""

import logging
import sys
from typing import Dict, Any

import structlog
from pythonjsonlogger import jsonlogger

from .config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)
    logging.getLogger("tensorflow").setLevel(logging.WARNING)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.DEBUG else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class MLLogger:
    """Specialized logger for ML operations."""
    
    def __init__(self, name: str = "ml"):
        self.logger = get_logger(name)
    
    def log_model_load(self, model_name: str, model_type: str, load_time: float) -> None:
        """Log model loading event."""
        self.logger.info(
            "Model loaded",
            model_name=model_name,
            model_type=model_type,
            load_time_seconds=load_time,
            event_type="model_load"
        )
    
    def log_inference(self, model_name: str, input_type: str, 
                     inference_time: float, batch_size: int = 1) -> None:
        """Log inference event."""
        self.logger.info(
            "Inference completed",
            model_name=model_name,
            input_type=input_type,
            inference_time_seconds=inference_time,
            batch_size=batch_size,
            event_type="inference"
        )
    
    def log_error(self, operation: str, error: str, **kwargs) -> None:
        """Log ML operation error."""
        self.logger.error(
            "ML operation failed",
            operation=operation,
            error=error,
            event_type="ml_error",
            **kwargs
        )
    
    def log_cache_hit(self, cache_key: str, model_name: str) -> None:
        """Log cache hit event."""
        self.logger.debug(
            "Cache hit",
            cache_key=cache_key,
            model_name=model_name,
            event_type="cache_hit"
        )
    
    def log_cache_miss(self, cache_key: str, model_name: str) -> None:
        """Log cache miss event."""
        self.logger.debug(
            "Cache miss",
            cache_key=cache_key,
            model_name=model_name,
            event_type="cache_miss"
        )
    
    def log_batch_processing(self, batch_size: int, processing_time: float, 
                           success_count: int, error_count: int) -> None:
        """Log batch processing event."""
        self.logger.info(
            "Batch processing completed",
            batch_size=batch_size,
            processing_time_seconds=processing_time,
            success_count=success_count,
            error_count=error_count,
            event_type="batch_processing"
        )
    
    def log_resource_usage(self, cpu_percent: float, memory_percent: float, 
                          gpu_percent: float = None) -> None:
        """Log resource usage."""
        self.logger.info(
            "Resource usage",
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            gpu_percent=gpu_percent,
            event_type="resource_usage"
        )