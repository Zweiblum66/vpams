"""
Enhanced Logging System

Advanced logging capabilities including request/response body logging,
correlation tracking, performance metrics, and log aggregation support.
"""

import json
import time
import re
from typing import Dict, Any, Optional, List, Set, Union
from datetime import datetime
import hashlib
from collections import defaultdict
import asyncio

from starlette.requests import Request
from starlette.responses import Response
from starlette.datastructures import Headers
import structlog

from .config import get_settings

settings = get_settings()

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
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


class SensitiveDataMasker:
    """Masks sensitive data in logs"""
    
    # Patterns for sensitive data
    SENSITIVE_PATTERNS = {
        'password': re.compile(r'"password"\s*:\s*"[^"]*"', re.IGNORECASE),
        'token': re.compile(r'"(token|access_token|refresh_token)"\s*:\s*"[^"]*"', re.IGNORECASE),
        'api_key': re.compile(r'"(api_key|apikey)"\s*:\s*"[^"]*"', re.IGNORECASE),
        'secret': re.compile(r'"[^"]*secret[^"]*"\s*:\s*"[^"]*"', re.IGNORECASE),
        'authorization': re.compile(r'(Authorization|authorization)\s*:\s*[^\s,}]+', re.IGNORECASE),
        'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    }
    
    # Fields to completely exclude from logs
    EXCLUDED_FIELDS = {
        'password', 'pwd', 'passwd', 'secret', 'token', 'api_key', 'apikey',
        'private_key', 'credit_card', 'cc_number', 'cvv', 'ssn', 'social_security'
    }
    
    @classmethod
    def mask_string(cls, data: str) -> str:
        """Mask sensitive data in a string"""
        if not data:
            return data
            
        masked = data
        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
            if pattern_name == 'email':
                # Special handling for email - mask but keep domain
                masked = pattern.sub(lambda m: cls._mask_email(m.group(0)), masked)
            else:
                masked = pattern.sub(lambda m: f'"{pattern_name}": "***MASKED***"', masked)
        
        return masked
    
    @classmethod
    def mask_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in a dictionary"""
        if not data:
            return data
            
        masked = {}
        for key, value in data.items():
            if key.lower() in cls.EXCLUDED_FIELDS:
                masked[key] = "***MASKED***"
            elif isinstance(value, dict):
                masked[key] = cls.mask_dict(value)
            elif isinstance(value, list):
                masked[key] = [cls.mask_dict(item) if isinstance(item, dict) else item for item in value]
            elif isinstance(value, str):
                masked[key] = cls.mask_string(value)
            else:
                masked[key] = value
                
        return masked
    
    @staticmethod
    def _mask_email(email: str) -> str:
        """Mask email address but keep domain"""
        parts = email.split('@')
        if len(parts) == 2:
            username = parts[0]
            domain = parts[1]
            if len(username) > 2:
                masked_username = username[0] + '*' * (len(username) - 2) + username[-1]
            else:
                masked_username = '*' * len(username)
            return f"{masked_username}@{domain}"
        return "***MASKED***"


class RequestResponseLogger:
    """Enhanced request/response logger"""
    
    def __init__(
        self,
        log_request_body: bool = True,
        log_response_body: bool = True,
        max_body_size: int = 10240,  # 10KB
        exclude_paths: Optional[List[str]] = None,
        mask_sensitive_data: bool = True
    ):
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        self.exclude_paths = exclude_paths or ['/health', '/metrics', '/docs', '/openapi.json']
        self.mask_sensitive_data = mask_sensitive_data
        self.logger = structlog.get_logger("api_gateway.request_response")
    
    async def log_request(self, request: Request, request_id: str) -> Dict[str, Any]:
        """Log incoming request details"""
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return {}
        
        # Extract request details
        request_data = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": str(request.url.path),
            "query_params": dict(request.query_params),
            "headers": self._clean_headers(dict(request.headers)),
            "client": {
                "host": request.client.host if request.client else None,
                "port": request.client.port if request.client else None
            },
            "url": {
                "scheme": request.url.scheme,
                "netloc": request.url.netloc,
                "path": request.url.path,
                "query": request.url.query
            }
        }
        
        # Add user context if available
        if hasattr(request.state, 'user_id'):
            request_data['user_id'] = request.state.user_id
        
        # Log request body if enabled
        if self.log_request_body and request.method in ['POST', 'PUT', 'PATCH']:
            try:
                content_type = request.headers.get('content-type', '')
                body = await request.body()
                
                if len(body) <= self.max_body_size:
                    if 'application/json' in content_type:
                        try:
                            body_data = json.loads(body)
                            if self.mask_sensitive_data:
                                body_data = SensitiveDataMasker.mask_dict(body_data)
                            request_data['body'] = body_data
                        except json.JSONDecodeError:
                            request_data['body'] = f"<Binary data: {len(body)} bytes>"
                    else:
                        request_data['body'] = f"<{content_type}: {len(body)} bytes>"
                else:
                    request_data['body'] = f"<Body too large: {len(body)} bytes>"
                    
                # Store body for later use in request
                request.state._body = body
                
            except Exception as e:
                request_data['body_error'] = str(e)
        
        # Log the request
        self.logger.info("Incoming request", **request_data)
        
        return request_data
    
    async def log_response(
        self,
        request: Request,
        response: Response,
        request_data: Dict[str, Any],
        response_time: float,
        request_id: str
    ) -> None:
        """Log response details"""
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return
        
        response_data = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": response.status_code,
            "response_time": round(response_time * 1000, 2),  # Convert to milliseconds
            "headers": self._clean_headers(dict(response.headers)),
        }
        
        # Log response body if enabled
        if self.log_response_body and hasattr(response, 'body'):
            try:
                content_type = response.headers.get('content-type', '')
                body = response.body
                
                if len(body) <= self.max_body_size:
                    if 'application/json' in content_type:
                        try:
                            body_data = json.loads(body)
                            if self.mask_sensitive_data:
                                body_data = SensitiveDataMasker.mask_dict(body_data)
                            response_data['body'] = body_data
                        except json.JSONDecodeError:
                            response_data['body'] = f"<Binary data: {len(body)} bytes>"
                    else:
                        response_data['body'] = f"<{content_type}: {len(body)} bytes>"
                else:
                    response_data['body'] = f"<Body too large: {len(body)} bytes>"
                    
            except Exception as e:
                response_data['body_error'] = str(e)
        
        # Combine request and response data
        log_entry = {
            **request_data,
            "response": response_data
        }
        
        # Log based on status code
        if response.status_code >= 500:
            self.logger.error("Request completed with server error", **log_entry)
        elif response.status_code >= 400:
            self.logger.warning("Request completed with client error", **log_entry)
        else:
            self.logger.info("Request completed successfully", **log_entry)
    
    def _clean_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Clean and mask sensitive headers"""
        sensitive_headers = {'authorization', 'cookie', 'x-api-key', 'x-auth-token'}
        cleaned = {}
        
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                if self.mask_sensitive_data:
                    cleaned[key] = "***MASKED***"
            else:
                cleaned[key] = value
                
        return cleaned


class PerformanceLogger:
    """Logs performance metrics"""
    
    def __init__(self):
        self.logger = structlog.get_logger("api_gateway.performance")
        self.metrics = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def log_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None
    ) -> None:
        """Log a performance metric"""
        metric_data = {
            "metric": metric_name,
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
            "tags": tags or {}
        }
        
        if request_id:
            metric_data["request_id"] = request_id
        
        self.logger.info(f"Performance metric: {metric_name}", **metric_data)
        
        # Store for aggregation
        async with self._lock:
            self.metrics[metric_name].append(value)
            
            # Keep only last 1000 values per metric
            if len(self.metrics[metric_name]) > 1000:
                self.metrics[metric_name] = self.metrics[metric_name][-1000:]
    
    async def get_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        async with self._lock:
            values = self.metrics.get(metric_name, [])
            
            if not values:
                return {}
            
            values_sorted = sorted(values)
            count = len(values)
            
            return {
                "count": count,
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / count,
                "p50": values_sorted[int(count * 0.5)],
                "p90": values_sorted[int(count * 0.9)],
                "p95": values_sorted[int(count * 0.95)],
                "p99": values_sorted[int(count * 0.99)] if count > 100 else values_sorted[-1]
            }


class AuditLogger:
    """Logs security and compliance events"""
    
    def __init__(self):
        self.logger = structlog.get_logger("api_gateway.audit")
    
    async def log_authentication(
        self,
        event_type: str,
        user_id: Optional[str],
        success: bool,
        method: str,
        ip_address: str,
        user_agent: Optional[str],
        reason: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> None:
        """Log authentication events"""
        event_data = {
            "event_type": f"auth.{event_type}",
            "user_id": user_id,
            "success": success,
            "method": method,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }
        
        if reason:
            event_data["reason"] = reason
        
        if success:
            self.logger.info(f"Authentication {event_type} succeeded", **event_data)
        else:
            self.logger.warning(f"Authentication {event_type} failed", **event_data)
    
    async def log_authorization(
        self,
        user_id: str,
        resource: str,
        action: str,
        allowed: bool,
        permissions: List[str],
        required_permissions: List[str],
        request_id: Optional[str] = None
    ) -> None:
        """Log authorization events"""
        event_data = {
            "event_type": "authz.check",
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "allowed": allowed,
            "permissions": permissions,
            "required_permissions": required_permissions,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }
        
        if allowed:
            self.logger.info("Authorization check passed", **event_data)
        else:
            self.logger.warning("Authorization check failed", **event_data)
    
    async def log_data_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        success: bool,
        data_classification: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> None:
        """Log data access events for compliance"""
        event_data = {
            "event_type": "data.access",
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "success": success,
            "data_classification": data_classification,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        }
        
        self.logger.info("Data access event", **event_data)


class LogAggregator:
    """Aggregates logs for analysis and alerting"""
    
    def __init__(self, window_size: int = 300):  # 5 minutes
        self.window_size = window_size
        self.error_counts = defaultdict(int)
        self.request_counts = defaultdict(int)
        self.response_times = defaultdict(list)
        self.logger = structlog.get_logger("api_gateway.aggregator")
        self._lock = asyncio.Lock()
    
    async def aggregate_request(
        self,
        path: str,
        method: str,
        status_code: int,
        response_time: float
    ) -> None:
        """Aggregate request data"""
        async with self._lock:
            key = f"{method}:{path}"
            self.request_counts[key] += 1
            self.response_times[key].append(response_time)
            
            if status_code >= 400:
                error_key = f"{key}:{status_code}"
                self.error_counts[error_key] += 1
                
                # Check for anomalies
                if self.error_counts[error_key] > 10:
                    self.logger.warning(
                        "High error rate detected",
                        path=path,
                        method=method,
                        status_code=status_code,
                        error_count=self.error_counts[error_key]
                    )
    
    async def get_summary(self) -> Dict[str, Any]:
        """Get aggregated summary"""
        async with self._lock:
            summary = {
                "request_counts": dict(self.request_counts),
                "error_counts": dict(self.error_counts),
                "response_time_stats": {}
            }
            
            for key, times in self.response_times.items():
                if times:
                    summary["response_time_stats"][key] = {
                        "count": len(times),
                        "avg": sum(times) / len(times),
                        "min": min(times),
                        "max": max(times)
                    }
            
            return summary
    
    async def reset(self) -> None:
        """Reset aggregated data"""
        async with self._lock:
            self.error_counts.clear()
            self.request_counts.clear()
            self.response_times.clear()


# Global instances
request_response_logger = RequestResponseLogger()
performance_logger = PerformanceLogger()
audit_logger = AuditLogger()
log_aggregator = LogAggregator()