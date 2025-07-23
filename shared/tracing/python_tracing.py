"""
MAMS Distributed Tracing Configuration

This module provides standardized tracing configuration for all MAMS services.
It ensures consistent trace collection, proper instrumentation, and integration
with the distributed tracing system (Jaeger/Tempo).
"""

import os
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
import time

from opentelemetry import trace, baggage
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.propagate import inject, extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.semantic_conventions.trace import SpanAttributes
from opentelemetry.semantic_conventions.resource import ResourceAttributes


logger = logging.getLogger(__name__)


class MAMSTracingConfig:
    """Configuration class for MAMS distributed tracing."""
    
    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        environment: str = "development",
        cluster_name: str = "local",
        jaeger_endpoint: Optional[str] = None,
        otlp_endpoint: Optional[str] = None,
        sample_rate: float = 1.0,
        enable_console_export: bool = False
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.cluster_name = cluster_name
        self.jaeger_endpoint = jaeger_endpoint or os.getenv("JAEGER_ENDPOINT", "http://jaeger:14268/api/traces")
        self.otlp_endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT", "http://otel-collector:4317")
        self.sample_rate = sample_rate
        self.enable_console_export = enable_console_export


def setup_tracing(config: MAMSTracingConfig) -> trace.Tracer:
    """
    Setup distributed tracing for MAMS services.
    
    Args:
        config: Tracing configuration
        
    Returns:
        Configured tracer instance
    """
    # Create resource with service information
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: config.service_name,
        ResourceAttributes.SERVICE_VERSION: config.service_version,
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: config.environment,
        "service.namespace": "mams",
        "cluster.name": config.cluster_name,
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Setup exporters
    exporters = []
    
    # Jaeger exporter
    try:
        jaeger_exporter = JaegerExporter(
            agent_host_name=config.jaeger_endpoint.split("://")[1].split(":")[0],
            agent_port=int(config.jaeger_endpoint.split(":")[-1].split("/")[0]),
            collector_endpoint=config.jaeger_endpoint,
        )
        exporters.append(BatchSpanProcessor(jaeger_exporter))
        logger.info(f"Jaeger exporter configured: {config.jaeger_endpoint}")
    except Exception as e:
        logger.warning(f"Failed to configure Jaeger exporter: {e}")
    
    # OTLP exporter (primary)
    try:
        otlp_exporter = OTLPSpanExporter(
            endpoint=config.otlp_endpoint,
            insecure=True,  # Use secure=False for development
        )
        exporters.append(BatchSpanProcessor(otlp_exporter))
        logger.info(f"OTLP exporter configured: {config.otlp_endpoint}")
    except Exception as e:
        logger.warning(f"Failed to configure OTLP exporter: {e}")
    
    # Console exporter for debugging
    if config.enable_console_export:
        from opentelemetry.exporter.console import ConsoleSpanExporter
        console_exporter = ConsoleSpanExporter()
        exporters.append(SimpleSpanProcessor(console_exporter))
        logger.info("Console exporter enabled")
    
    # Add processors to provider
    for exporter in exporters:
        provider.add_span_processor(exporter)
    
    # Set the global tracer provider
    trace.set_tracer_provider(provider)
    
    # Get tracer
    tracer = trace.get_tracer(config.service_name, config.service_version)
    
    logger.info(f"Tracing initialized for service: {config.service_name}")
    return tracer


def instrument_fastapi(app, service_name: str):
    """Instrument FastAPI application for tracing."""
    FastAPIInstrumentor.instrument_app(
        app,
        server_request_hook=_server_request_hook,
        client_request_hook=_client_request_hook,
        client_response_hook=_client_response_hook,
        excluded_urls="health,metrics,ping",
    )
    logger.info(f"FastAPI instrumentation enabled for {service_name}")


def instrument_databases():
    """Instrument database connections for tracing."""
    # SQLAlchemy
    try:
        SQLAlchemyInstrumentor().instrument(
            enable_commenter=True,
            commenter_options={
                "db_driver": True,
                "db_framework": True,
            }
        )
        logger.info("SQLAlchemy instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument SQLAlchemy: {e}")
    
    # PostgreSQL
    try:
        Psycopg2Instrumentor().instrument()
        logger.info("Psycopg2 instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument Psycopg2: {e}")
    
    # MongoDB
    try:
        PymongoInstrumentor().instrument()
        logger.info("PyMongo instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument PyMongo: {e}")
    
    # Redis
    try:
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument Redis: {e}")


def instrument_http_clients():
    """Instrument HTTP clients for tracing."""
    # Requests
    try:
        RequestsInstrumentor().instrument()
        logger.info("Requests instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument Requests: {e}")
    
    # HTTPX
    try:
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument HTTPX: {e}")


def instrument_logging():
    """Instrument logging for trace correlation."""
    try:
        LoggingInstrumentor().instrument(set_logging_format=True)
        logger.info("Logging instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument logging: {e}")


def instrument_celery():
    """Instrument Celery for distributed task tracing."""
    try:
        CeleryInstrumentor().instrument()
        logger.info("Celery instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument Celery: {e}")


def _server_request_hook(span, scope):
    """Hook to customize server request spans."""
    if span and span.is_recording():
        # Add custom attributes
        span.set_attribute("mams.service_type", "api")
        span.set_attribute("mams.request_type", "http")
        
        # Add user context if available
        if "user" in scope.get("state", {}):
            user = scope["state"]["user"]
            span.set_attribute("mams.user_id", str(user.id))
            span.set_attribute("mams.user_role", user.role)


def _client_request_hook(span, scope):
    """Hook to customize client request spans."""
    if span and span.is_recording():
        span.set_attribute("mams.request_direction", "outbound")


def _client_response_hook(span, scope, message):
    """Hook to customize client response spans."""
    if span and span.is_recording():
        span.set_attribute("mams.response_processed", True)


class TracedOperation:
    """Context manager for creating traced operations."""
    
    def __init__(
        self,
        tracer: trace.Tracer,
        operation_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        self.tracer = tracer
        self.operation_name = operation_name
        self.kind = kind
        self.attributes = attributes or {}
        self.span = None
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.span = self.tracer.start_span(
            self.operation_name,
            kind=self.kind,
            attributes=self.attributes
        )
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            # Add execution time
            execution_time = time.time() - self.start_time
            self.span.set_attribute("mams.execution_time", execution_time)
            
            # Handle exceptions
            if exc_type:
                self.span.record_exception(exc_val)
                self.span.set_status(
                    Status(StatusCode.ERROR, str(exc_val))
                )
            else:
                self.span.set_status(Status(StatusCode.OK))
            
            self.span.end()


def trace_function(
    operation_name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
):
    """Decorator to trace function execution."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with TracedOperation(tracer, name, kind, attributes) as span:
                # Add function metadata
                span.set_attribute("code.function", func.__name__)
                span.set_attribute("code.namespace", func.__module__)
                
                # Add arguments if not sensitive
                if not _contains_sensitive_data(kwargs):
                    span.set_attribute("mams.function_args", str(kwargs))
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Add result metadata
                    if hasattr(result, '__len__'):
                        span.set_attribute("mams.result_count", len(result))
                    
                    return result
                except Exception as e:
                    span.set_attribute("mams.error_type", type(e).__name__)
                    raise
        
        return wrapper
    return decorator


def trace_async_function(
    operation_name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
):
    """Decorator to trace async function execution."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with TracedOperation(tracer, name, kind, attributes) as span:
                # Add function metadata
                span.set_attribute("code.function", func.__name__)
                span.set_attribute("code.namespace", func.__module__)
                span.set_attribute("mams.async", True)
                
                # Add arguments if not sensitive
                if not _contains_sensitive_data(kwargs):
                    span.set_attribute("mams.function_args", str(kwargs))
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # Add result metadata
                    if hasattr(result, '__len__'):
                        span.set_attribute("mams.result_count", len(result))
                    
                    return result
                except Exception as e:
                    span.set_attribute("mams.error_type", type(e).__name__)
                    raise
        
        return wrapper
    return decorator


def add_trace_context_to_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Add trace context to HTTP headers for propagation."""
    inject(headers)
    return headers


def extract_trace_context_from_headers(headers: Dict[str, str]) -> None:
    """Extract trace context from HTTP headers."""
    extract(headers)


def set_baggage_item(key: str, value: str) -> None:
    """Set baggage item for trace context propagation."""
    baggage.set_baggage(key, value)


def get_baggage_item(key: str) -> Optional[str]:
    """Get baggage item from trace context."""
    return baggage.get_baggage(key)


def get_current_trace_id() -> Optional[str]:
    """Get current trace ID."""
    span = trace.get_current_span()
    if span and span.is_recording():
        return format(span.get_span_context().trace_id, 'x')
    return None


def get_current_span_id() -> Optional[str]:
    """Get current span ID."""
    span = trace.get_current_span()
    if span and span.is_recording():
        return format(span.get_span_context().span_id, 'x')
    return None


def _contains_sensitive_data(data: Dict[str, Any]) -> bool:
    """Check if data contains sensitive information."""
    sensitive_keys = {
        'password', 'token', 'secret', 'key', 'authorization',
        'credit_card', 'ssn', 'pin', 'api_key', 'private_key'
    }
    
    if isinstance(data, dict):
        return any(
            any(sensitive in str(key).lower() for sensitive in sensitive_keys)
            for key in data.keys()
        )
    return False


# Custom span attributes for MAMS
class MAMSSpanAttributes:
    """Custom span attributes for MAMS services."""
    
    # Business operation attributes
    USER_ID = "mams.user.id"
    USER_ROLE = "mams.user.role"
    ASSET_ID = "mams.asset.id"
    ASSET_TYPE = "mams.asset.type"
    PROJECT_ID = "mams.project.id"
    WORKFLOW_ID = "mams.workflow.id"
    
    # Performance attributes
    EXECUTION_TIME = "mams.execution_time"
    QUEUE_TIME = "mams.queue_time"
    PROCESSING_TIME = "mams.processing_time"
    
    # Infrastructure attributes
    SERVICE_TYPE = "mams.service.type"
    STORAGE_BACKEND = "mams.storage.backend"
    DATABASE_NAME = "mams.database.name"
    CACHE_HIT = "mams.cache.hit"
    
    # Error attributes
    ERROR_TYPE = "mams.error.type"
    ERROR_CODE = "mams.error.code"
    RETRY_COUNT = "mams.retry.count"


# Example usage for FastAPI service
def setup_service_tracing(
    app,
    service_name: str,
    service_version: str = "1.0.0",
    enable_all_instrumentations: bool = True
) -> trace.Tracer:
    """
    Complete tracing setup for a MAMS service.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service
        service_version: Version of the service
        enable_all_instrumentations: Whether to enable all instrumentations
        
    Returns:
        Configured tracer instance
    """
    # Create configuration
    config = MAMSTracingConfig(
        service_name=service_name,
        service_version=service_version,
        environment=os.getenv("ENVIRONMENT", "development"),
        cluster_name=os.getenv("CLUSTER_NAME", "local"),
        enable_console_export=os.getenv("TRACING_DEBUG", "false").lower() == "true"
    )
    
    # Setup tracing
    tracer = setup_tracing(config)
    
    # Instrument FastAPI
    instrument_fastapi(app, service_name)
    
    if enable_all_instrumentations:
        # Instrument all supported libraries
        instrument_databases()
        instrument_http_clients()
        instrument_logging()
        instrument_celery()
    
    return tracer


# Example middleware for manual trace correlation
async def trace_correlation_middleware(request, call_next):
    """Middleware to ensure trace correlation across requests."""
    # Extract trace context from headers
    extract_trace_context_from_headers(dict(request.headers))
    
    # Get current trace info
    trace_id = get_current_trace_id()
    span_id = get_current_span_id()
    
    # Add to request state for logging
    request.state.trace_id = trace_id
    request.state.span_id = span_id
    
    # Process request
    response = await call_next(request)
    
    # Add trace headers to response
    if trace_id:
        response.headers["X-Trace-Id"] = trace_id
    if span_id:
        response.headers["X-Span-Id"] = span_id
    
    return response