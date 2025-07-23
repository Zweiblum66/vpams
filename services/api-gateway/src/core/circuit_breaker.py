"""
Circuit Breaker Implementation

Implements circuit breaker pattern to prevent cascading failures
when downstream services are unavailable.
"""

import asyncio
import time
from typing import Optional, Callable, Any, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Service is down, fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker implementation for service calls
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is down, requests fail immediately
    - HALF_OPEN: Testing if service has recovered
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker
        
        Args:
            name: Circuit breaker name (usually service name)
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            expected_exception: Exception type to catch
            success_threshold: Successes needed to close from half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)"""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)"""
        return self._state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half open (testing recovery)"""
        return self._state == CircuitState.HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function fails
        """
        async with self._lock:
            # Check if we should transition from open to half-open
            if self.is_open and self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
        
        # If open, fail fast
        if self.is_open:
            raise CircuitBreakerError(f"Circuit breaker {self.name} is OPEN")
        
        try:
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Record success
            await self._record_success()
            return result
            
        except self.expected_exception as e:
            # Record failure
            await self._record_failure()
            raise e
    
    async def _record_success(self) -> None:
        """Record successful call"""
        async with self._lock:
            self._failure_count = 0
            
            if self.is_half_open:
                self._success_count += 1
                
                # Check if we can close the circuit
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    logger.info(f"Circuit breaker {self.name} is now CLOSED")
    
    async def _record_failure(self) -> None:
        """Record failed call"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            # Reset success count on any failure in half-open state
            if self.is_half_open:
                self._success_count = 0
            
            # Check if we should open the circuit
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker {self.name} is now OPEN after "
                    f"{self._failure_count} failures"
                )
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset from open state"""
        return (
            self._last_failure_time is not None and
            time.time() - self._last_failure_time >= self.recovery_timeout
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
            "is_healthy": self.is_closed
        }
    
    async def reset(self) -> None:
        """Manually reset circuit breaker"""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            logger.info(f"Circuit breaker {self.name} manually reset")


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreakerManager:
    """Manages multiple circuit breakers for different services"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker manager
        
        Args:
            failure_threshold: Default failure threshold
            recovery_timeout: Default recovery timeout
            success_threshold: Default success threshold
        """
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._success_threshold = success_threshold
    
    def get_breaker(self, name: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for service
        
        Args:
            name: Service name
            
        Returns:
            Circuit breaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=self._failure_threshold,
                recovery_timeout=self._recovery_timeout,
                success_threshold=self._success_threshold
            )
        
        return self._breakers[name]
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {
            name: breaker.get_status()
            for name, breaker in self._breakers.items()
        }
    
    async def reset_all(self) -> None:
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            await breaker.reset()
    
    async def reset(self, name: str) -> None:
        """Reset specific circuit breaker"""
        if name in self._breakers:
            await self._breakers[name].reset()


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()