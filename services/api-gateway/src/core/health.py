"""
Enhanced Health Check System

Provides comprehensive health checks for the API Gateway including:
- Component health monitoring
- Dependency checks
- Performance metrics
- Resource utilization
- Circuit breaker status
"""

import asyncio
import psutil
import aiohttp
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.config import get_settings
from core.redis import get_redis_client
from core.service_discovery import get_service_client

logger = logging.getLogger(__name__)
settings = get_settings()


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth:
    """Health check result for a component"""
    
    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        response_time: Optional[float] = None
    ):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.response_time = response_time
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = {
            "name": self.name,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat() + "Z"
        }
        
        if self.message:
            result["message"] = self.message
        
        if self.details:
            result["details"] = self.details
        
        if self.response_time is not None:
            result["response_time_ms"] = round(self.response_time * 1000, 2)
        
        return result


class HealthChecker:
    """Main health checker class"""
    
    def __init__(self):
        self.checks: Dict[str, callable] = {}
        self.cache: Dict[str, Tuple[ComponentHealth, datetime]] = {}
        self.cache_ttl = timedelta(seconds=10)  # Cache results for 10 seconds
        
        # Register default checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks"""
        self.register_check("database", self._check_database)
        self.register_check("redis", self._check_redis)
        self.register_check("disk_space", self._check_disk_space)
        self.register_check("memory", self._check_memory)
        self.register_check("cpu", self._check_cpu)
    
    def register_check(self, name: str, check_func: callable):
        """Register a health check function"""
        self.checks[name] = check_func
    
    async def check_health(
        self,
        include_details: bool = True,
        check_dependencies: bool = True
    ) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Args:
            include_details: Include detailed information
            check_dependencies: Check downstream service dependencies
            
        Returns:
            Health check results
        """
        start_time = time.time()
        
        # Run all registered checks
        component_results = await self._run_component_checks()
        
        # Check downstream services if requested
        dependency_results = []
        if check_dependencies:
            dependency_results = await self._check_dependencies()
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(
            component_results + dependency_results
        )
        
        # Build response
        response = {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": getattr(settings, 'version', '1.0.0'),
            "environment": settings.environment,
            "uptime_seconds": self._get_uptime(),
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }
        
        if include_details:
            response["components"] = [c.to_dict() for c in component_results]
            
            if dependency_results:
                response["dependencies"] = [d.to_dict() for d in dependency_results]
            
            response["system"] = await self._get_system_info()
        
        return response
    
    async def _run_component_checks(self) -> List[ComponentHealth]:
        """Run all registered component checks"""
        results = []
        
        # Run checks concurrently
        tasks = []
        for name, check_func in self.checks.items():
            tasks.append(self._run_check_with_cache(name, check_func))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to unhealthy status
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                name = list(self.checks.keys())[i]
                final_results.append(ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(result)}"
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def _run_check_with_cache(
        self,
        name: str,
        check_func: callable
    ) -> ComponentHealth:
        """Run a check with caching"""
        # Check cache
        if name in self.cache:
            cached_result, cached_time = self.cache[name]
            if datetime.utcnow() - cached_time < self.cache_ttl:
                return cached_result
        
        # Run check
        start_time = time.time()
        try:
            result = await check_func()
            result.response_time = time.time() - start_time
        except Exception as e:
            logger.error(f"Health check '{name}' failed: {e}")
            result = ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                response_time=time.time() - start_time
            )
        
        # Cache result
        self.cache[name] = (result, datetime.utcnow())
        
        return result
    
    async def _check_database(self) -> ComponentHealth:
        """Check database connectivity"""
        try:
            from db.base import AsyncSessionLocal
            
            async with AsyncSessionLocal() as session:
                # Simple query to check connection
                result = await session.execute(text("SELECT 1"))
                result.scalar()
            
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database connection successful"
            )
            
        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}"
            )
    
    async def _check_redis(self) -> ComponentHealth:
        """Check Redis connectivity"""
        try:
            redis = await get_redis_client()
            
            # Ping Redis
            start_time = time.time()
            await redis.ping()
            response_time = time.time() - start_time
            
            # Get Redis info
            info = await redis.info()
            
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection successful",
                details={
                    "version": info.get("redis_version", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "ping_latency_ms": round(response_time * 1000, 2)
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}"
            )
    
    async def _check_disk_space(self) -> ComponentHealth:
        """Check disk space availability"""
        try:
            disk_usage = psutil.disk_usage('/')
            
            # Determine status based on available space
            if disk_usage.percent > 95:
                status = HealthStatus.UNHEALTHY
                message = "Critical: Disk space almost full"
            elif disk_usage.percent > 85:
                status = HealthStatus.DEGRADED
                message = "Warning: Low disk space"
            else:
                status = HealthStatus.HEALTHY
                message = "Disk space OK"
            
            return ComponentHealth(
                name="disk_space",
                status=status,
                message=message,
                details={
                    "total_gb": round(disk_usage.total / (1024**3), 2),
                    "used_gb": round(disk_usage.used / (1024**3), 2),
                    "free_gb": round(disk_usage.free / (1024**3), 2),
                    "percent_used": disk_usage.percent
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="disk_space",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check disk space: {str(e)}"
            )
    
    async def _check_memory(self) -> ComponentHealth:
        """Check memory utilization"""
        try:
            memory = psutil.virtual_memory()
            
            # Determine status based on memory usage
            if memory.percent > 95:
                status = HealthStatus.UNHEALTHY
                message = "Critical: Memory almost exhausted"
            elif memory.percent > 85:
                status = HealthStatus.DEGRADED
                message = "Warning: High memory usage"
            else:
                status = HealthStatus.HEALTHY
                message = "Memory usage OK"
            
            return ComponentHealth(
                name="memory",
                status=status,
                message=message,
                details={
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent_used": memory.percent,
                    "process_memory_mb": round(
                        psutil.Process().memory_info().rss / (1024**2), 2
                    )
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check memory: {str(e)}"
            )
    
    async def _check_cpu(self) -> ComponentHealth:
        """Check CPU utilization"""
        try:
            # Get CPU usage over 1 second interval
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Determine status based on CPU usage
            if cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "Critical: Very high CPU usage"
            elif cpu_percent > 75:
                status = HealthStatus.DEGRADED
                message = "Warning: High CPU usage"
            else:
                status = HealthStatus.HEALTHY
                message = "CPU usage OK"
            
            return ComponentHealth(
                name="cpu",
                status=status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "cpu_count": psutil.cpu_count(),
                    "process_cpu_percent": psutil.Process().cpu_percent()
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="cpu",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check CPU: {str(e)}"
            )
    
    async def _check_dependencies(self) -> List[ComponentHealth]:
        """Check health of downstream services"""
        from core.service_discovery import SERVICE_REGISTRY
        
        results = []
        
        # Check each registered service
        tasks = []
        for service_name in SERVICE_REGISTRY:
            tasks.append(self._check_service_health(service_name))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to unhealthy status
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_name = list(SERVICE_REGISTRY.keys())[i]
                final_results.append(ComponentHealth(
                    name=f"service:{service_name}",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Service check failed: {str(result)}"
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def _check_service_health(self, service_name: str) -> ComponentHealth:
        """Check health of a specific service"""
        try:
            client = get_service_client(service_name)
            
            # Try to call health endpoint
            start_time = time.time()
            response = await client.request(
                method="GET",
                path="/health",
                timeout=5.0
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                status = HealthStatus.HEALTHY
                message = f"Service {service_name} is healthy"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Service {service_name} returned status {response.status_code}"
            
            return ComponentHealth(
                name=f"service:{service_name}",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "status_code": response.status_code,
                    "available_instances": len(client.instances)
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name=f"service:{service_name}",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check service: {str(e)}"
            )
    
    def _calculate_overall_status(
        self,
        results: List[ComponentHealth]
    ) -> HealthStatus:
        """Calculate overall health status from component results"""
        if not results:
            return HealthStatus.UNKNOWN
        
        # Count statuses
        unhealthy_count = sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for r in results if r.status == HealthStatus.DEGRADED)
        
        # Critical components that must be healthy
        critical_components = ["database", "redis"]
        critical_unhealthy = any(
            r.name in critical_components and r.status == HealthStatus.UNHEALTHY
            for r in results
        )
        
        # Determine overall status
        if critical_unhealthy or unhealthy_count > len(results) * 0.3:
            return HealthStatus.UNHEALTHY
        elif unhealthy_count > 0 or degraded_count > len(results) * 0.5:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def _get_uptime(self) -> float:
        """Get service uptime in seconds"""
        if hasattr(settings, 'startup_time'):
            return time.time() - settings.startup_time
        return 0
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                "hostname": socket.gethostname(),
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine()
                },
                "python_version": platform.python_version(),
                "process": {
                    "pid": os.getpid(),
                    "threads": threading.active_count()
                }
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {}


# Import additional required modules
import socket
import platform
import os
import threading


# Global health checker instance
health_checker = HealthChecker()


# Convenience functions
async def check_health(
    include_details: bool = True,
    check_dependencies: bool = True
) -> Dict[str, Any]:
    """Perform health check using global instance"""
    return await health_checker.check_health(
        include_details=include_details,
        check_dependencies=check_dependencies
    )


def register_health_check(name: str, check_func: callable):
    """Register a custom health check"""
    health_checker.register_check(name, check_func)