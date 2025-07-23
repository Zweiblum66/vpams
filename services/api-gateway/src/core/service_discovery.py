"""
Service Discovery Module

Handles service discovery, health checks, and load balancing for downstream services.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
import httpx
from urllib.parse import urljoin
import time

from .config import get_settings
from .circuit_breaker import circuit_breaker_manager, CircuitBreakerError
from .retry import retry_async, RetryConfig, RetryError, HTTPServerError, HTTPTimeoutError, HTTPConnectionError
from .load_balancer import (
    ServiceInstance, LoadBalancingStrategy, load_balancer_manager
)

settings = get_settings()
logger = logging.getLogger(__name__)

# Global service registry
_service_registry: Dict[str, List[ServiceInstance]] = {}
_service_health: Dict[str, Dict[str, ServiceInstance]] = {}  # service_name -> {instance_id -> instance}


async def init_service_discovery() -> None:
    """Initialize service discovery"""
    global _service_registry, _service_health
    
    logger.info("Initializing service discovery")
    
    # Initialize with configured services
    for service_name, service_url in settings.services.items():
        instance_id = f"{service_name}-1"
        instance = ServiceInstance(
            id=instance_id,
            url=service_url,
            healthy=True,
            weight=1,
            last_health_check=time.time()
        )
        
        _service_registry[service_name] = [instance]
        
        if service_name not in _service_health:
            _service_health[service_name] = {}
        _service_health[service_name][instance_id] = instance
    
    # Configure load balancing strategies for specific services
    # You can customize this based on service requirements
    load_balancer_manager.set_service_strategy("search-engine", LoadBalancingStrategy.LEAST_CONNECTIONS)
    load_balancer_manager.set_service_strategy("proxy-generation", LoadBalancingStrategy.WEIGHTED_LEAST_CONNECTIONS)
    load_balancer_manager.set_service_strategy("ai-ml-service", LoadBalancingStrategy.RESPONSE_TIME)
    
    # Start health check task
    asyncio.create_task(health_check_task())
    
    logger.info(f"Service discovery initialized with {len(settings.services)} services")


async def cleanup_service_discovery() -> None:
    """Cleanup service discovery"""
    logger.info("Cleaning up service discovery")
    # Any cleanup tasks would go here


async def get_service_instance(service_name: str, context: Optional[Dict] = None) -> Optional[ServiceInstance]:
    """
    Get healthy service instance for a service using load balancing
    
    Args:
        service_name: Name of the service
        context: Request context for load balancing (e.g., client IP)
        
    Returns:
        Service instance if available, None otherwise
    """
    global _service_registry
    
    if service_name not in _service_registry:
        logger.warning(f"Service {service_name} not found in registry")
        return None
    
    # Get all instances for the service
    instances = _service_registry[service_name]
    
    # Select instance using load balancer
    instance = await load_balancer_manager.select_instance(
        service_name=service_name,
        instances=instances,
        context=context
    )
    
    return instance


async def get_service_url(service_name: str) -> Optional[str]:
    """
    Get healthy service URL for a service (backward compatibility)
    
    Args:
        service_name: Name of the service
        
    Returns:
        Service URL if available, None otherwise
    """
    instance = await get_service_instance(service_name)
    return instance.url if instance else None


async def register_service(service_name: str, service_url: str, weight: int = 1) -> None:
    """
    Register a service instance
    
    Args:
        service_name: Name of the service
        service_url: URL of the service instance
        weight: Weight for load balancing
    """
    global _service_registry, _service_health
    
    if service_name not in _service_registry:
        _service_registry[service_name] = []
    
    if service_name not in _service_health:
        _service_health[service_name] = {}
    
    # Check if instance already exists
    existing_instance = None
    for instance in _service_registry[service_name]:
        if instance.url == service_url:
            existing_instance = instance
            break
    
    if not existing_instance:
        # Create new instance
        instance_id = f"{service_name}-{len(_service_registry[service_name]) + 1}"
        instance = ServiceInstance(
            id=instance_id,
            url=service_url,
            healthy=True,
            weight=weight,
            last_health_check=time.time()
        )
        
        _service_registry[service_name].append(instance)
        _service_health[service_name][instance_id] = instance
        
        logger.info(f"Registered service {service_name} instance {instance_id} at {service_url}")


async def deregister_service(service_name: str, service_url: str) -> None:
    """
    Deregister a service instance
    
    Args:
        service_name: Name of the service
        service_url: URL of the service instance
    """
    global _service_registry, _service_health
    
    if service_name in _service_registry:
        # Find and remove instance
        for i, instance in enumerate(_service_registry[service_name]):
            if instance.url == service_url:
                removed_instance = _service_registry[service_name].pop(i)
                
                # Remove from health tracking
                if service_name in _service_health:
                    _service_health[service_name].pop(removed_instance.id, None)
                
                logger.info(f"Deregistered service {service_name} instance {removed_instance.id} at {service_url}")
                break


async def check_service_health(service_url: str) -> bool:
    """
    Check health of a service instance
    
    Args:
        service_url: URL of the service instance
        
    Returns:
        True if healthy, False otherwise
    """
    try:
        health_url = urljoin(service_url, "/health")
        
        async with httpx.AsyncClient(timeout=settings.health_check_timeout) as client:
            response = await client.get(health_url)
            return response.status_code == 200
            
    except Exception as e:
        logger.warning(f"Health check failed for {service_url}: {e}")
        return False


async def health_check_task() -> None:
    """Background task to check service health"""
    global _service_health
    
    while True:
        try:
            # Check health of all registered services
            for service_name, instances in _service_registry.items():
                for instance in instances:
                    is_healthy = await check_service_health(instance.url)
                    
                    # Update health status
                    previous_health = instance.healthy
                    instance.healthy = is_healthy
                    instance.last_health_check = time.time()
                    
                    # Log health changes
                    if previous_health != is_healthy:
                        status = "healthy" if is_healthy else "unhealthy"
                        logger.info(f"Service {service_name} instance {instance.id} at {instance.url} is now {status}")
                        
                        # Update circuit breaker state if unhealthy
                        if not is_healthy:
                            breaker = circuit_breaker_manager.get_breaker(service_name)
                            # Manually record failure to influence circuit breaker
                            await breaker._record_failure()
            
            # Wait before next health check
            await asyncio.sleep(settings.health_check_interval)
            
        except Exception as e:
            logger.error(f"Error in health check task: {e}")
            await asyncio.sleep(settings.health_check_interval)


async def get_service_status() -> Dict[str, Dict[str, Any]]:
    """
    Get status of all services
    
    Returns:
        Dictionary with service status information
    """
    global _service_registry
    
    status = {}
    
    for service_name, instances in _service_registry.items():
        status[service_name] = {}
        for instance in instances:
            status[service_name][instance.url] = {
                "id": instance.id,
                "healthy": instance.healthy,
                "weight": instance.weight,
                "active_connections": instance.active_connections,
                "total_requests": instance.total_requests,
                "failed_requests": instance.failed_requests,
                "avg_response_time": round(instance.avg_response_time, 3),
                "last_health_check": instance.last_health_check
            }
    
    # Add circuit breaker status
    circuit_status = circuit_breaker_manager.get_all_status()
    
    return {
        "services": status,
        "circuit_breakers": circuit_status
    }


class ServiceClient:
    """HTTP client for calling downstream services with circuit breaker and retry logic"""
    
    def __init__(self, service_name: str, retry_config: Optional[RetryConfig] = None):
        self.service_name = service_name
        self.client = httpx.AsyncClient(
            timeout=settings.request_timeout,
            headers={"User-Agent": "MAMS-API-Gateway/1.0"}
        )
        self.retry_config = retry_config or RetryConfig(
            max_attempts=3,
            initial_delay=0.5,
            max_delay=5.0,
            retryable_exceptions=[
                HTTPServerError,
                HTTPTimeoutError,
                HTTPConnectionError,
                httpx.TimeoutException,
                httpx.ConnectError
            ]
        )
    
    async def request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        json: Optional[Dict] = None,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        context: Optional[Dict] = None
    ) -> httpx.Response:
        """
        Make HTTP request to downstream service with circuit breaker and retry
        
        Args:
            method: HTTP method
            path: Request path
            headers: Request headers
            params: Query parameters
            json: JSON data
            data: Form data
            files: File uploads
            context: Request context for load balancing
            
        Returns:
            HTTP response
            
        Raises:
            Exception: If service is unavailable or request fails
        """
        # Get circuit breaker for this service
        circuit_breaker = circuit_breaker_manager.get_breaker(self.service_name)
        
        async def _make_request():
            # Get service instance with load balancing
            instance = await get_service_instance(self.service_name, context)
            
            if not instance:
                raise HTTPConnectionError(f"Service {self.service_name} is not available")
            
            # Build full URL
            url = urljoin(instance.url, path)
            
            # Track connection
            instance.active_connections += 1
            start_time = time.time()
            success = False
            
            try:
                # Make request
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                    data=data,
                    files=files
                )
                
                # Check status code
                if response.status_code >= 500:
                    raise HTTPServerError(f"Server error: {response.status_code}")
                
                success = True
                return response
                
            except httpx.TimeoutException as e:
                raise HTTPTimeoutError(f"Request timeout: {e}")
            except httpx.ConnectError as e:
                raise HTTPConnectionError(f"Connection error: {e}")
            finally:
                # Update metrics
                instance.active_connections -= 1
                response_time = time.time() - start_time
                load_balancer_manager.update_instance_metrics(
                    instance=instance,
                    response_time=response_time,
                    success=success
                )
        
        # Execute with circuit breaker
        try:
            # Execute with circuit breaker and retry
            response = await retry_async(
                lambda: circuit_breaker.call(_make_request),
                config=self.retry_config
            )
            return response
            
        except CircuitBreakerError:
            logger.error(f"Circuit breaker open for service {self.service_name}")
            raise HTTPConnectionError(f"Service {self.service_name} is currently unavailable")
        except RetryError as e:
            logger.error(f"All retry attempts failed for service {self.service_name}: {e.last_exception}")
            raise e.last_exception
    
    async def get(self, path: str, **kwargs) -> httpx.Response:
        """Make GET request"""
        return await self.request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs) -> httpx.Response:
        """Make POST request"""
        return await self.request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs) -> httpx.Response:
        """Make PUT request"""
        return await self.request("PUT", path, **kwargs)
    
    async def patch(self, path: str, **kwargs) -> httpx.Response:
        """Make PATCH request"""
        return await self.request("PATCH", path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """Make DELETE request"""
        return await self.request("DELETE", path, **kwargs)
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()


def get_service_client(service_name: str) -> ServiceClient:
    """Get service client for a specific service"""
    return ServiceClient(service_name)