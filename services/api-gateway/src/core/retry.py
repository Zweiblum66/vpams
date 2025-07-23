"""
Retry Mechanism

Implements exponential backoff retry logic for failed requests.
"""

import asyncio
import random
import logging
from typing import Optional, Callable, Any, List, Type
from functools import wraps

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        non_retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize retry configuration
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to prevent thundering herd
            retryable_exceptions: Exceptions that should trigger retry
            non_retryable_exceptions: Exceptions that should not be retried
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [Exception]
        self.non_retryable_exceptions = non_retryable_exceptions or []
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number
        
        Args:
            attempt: Attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = self.initial_delay * (self.exponential_base ** attempt)
        
        # Cap at max delay
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            # Add random jitter between 0% and 25% of the delay
            jitter_amount = delay * random.uniform(0, 0.25)
            delay += jitter_amount
        
        return delay
    
    def should_retry(self, exception: Exception) -> bool:
        """
        Check if exception should trigger retry
        
        Args:
            exception: Exception that occurred
            
        Returns:
            True if should retry, False otherwise
        """
        # Check non-retryable exceptions first
        for exc_type in self.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False
        
        # Check retryable exceptions
        for exc_type in self.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True
        
        return False


class RetryError(Exception):
    """Exception raised when all retry attempts are exhausted"""
    
    def __init__(self, message: str, last_exception: Exception, attempts: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts


async def retry_async(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Retry an async function with exponential backoff
    
    Args:
        func: Async function to retry
        *args: Function arguments
        config: Retry configuration
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        RetryError: If all attempts are exhausted
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            # Try to execute the function
            result = await func(*args, **kwargs)
            
            # Success - return result
            if attempt > 0:
                logger.info(
                    f"Function {func.__name__} succeeded after {attempt + 1} attempts"
                )
            
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if we should retry
            if not config.should_retry(e):
                logger.warning(
                    f"Function {func.__name__} failed with non-retryable "
                    f"exception: {type(e).__name__}: {e}"
                )
                raise
            
            # Check if we have more attempts
            if attempt >= config.max_attempts - 1:
                logger.error(
                    f"Function {func.__name__} failed after {config.max_attempts} "
                    f"attempts. Last error: {type(e).__name__}: {e}"
                )
                break
            
            # Calculate delay
            delay = config.calculate_delay(attempt)
            
            logger.warning(
                f"Function {func.__name__} failed (attempt {attempt + 1}/"
                f"{config.max_attempts}): {type(e).__name__}: {e}. "
                f"Retrying in {delay:.2f} seconds..."
            )
            
            # Wait before retry
            await asyncio.sleep(delay)
    
    # All attempts exhausted
    raise RetryError(
        f"Function {func.__name__} failed after {config.max_attempts} attempts",
        last_exception=last_exception,
        attempts=config.max_attempts
    )


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to async functions
    
    Args:
        config: Retry configuration
        
    Example:
        @with_retry(RetryConfig(max_attempts=5))
        async def flaky_function():
            # Function that might fail
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(func, *args, config=config, **kwargs)
        return wrapper
    return decorator


class RetryableHTTPError(Exception):
    """Base class for retryable HTTP errors"""
    pass


class HTTPServerError(RetryableHTTPError):
    """5xx server errors - should be retried"""
    pass


class HTTPTimeoutError(RetryableHTTPError):
    """Timeout errors - should be retried"""
    pass


class HTTPConnectionError(RetryableHTTPError):
    """Connection errors - should be retried"""
    pass


# Default retry configurations for different scenarios
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=10.0,
    retryable_exceptions=[
        RetryableHTTPError,
        asyncio.TimeoutError,
        ConnectionError
    ]
)

AGGRESSIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=0.5,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=[
        RetryableHTTPError,
        asyncio.TimeoutError,
        ConnectionError
    ]
)

NO_RETRY_CONFIG = RetryConfig(
    max_attempts=1,
    retryable_exceptions=[]
)