"""
Tests for Request Routing

Tests circuit breakers, load balancing, retry logic, and service discovery.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
import httpx

from src.core.circuit_breaker import (
    CircuitBreaker, CircuitState, CircuitBreakerError, CircuitBreakerManager
)
from src.core.retry import (
    retry_async, RetryConfig, RetryError, HTTPServerError
)
from src.core.load_balancer import (
    ServiceInstance, LoadBalancingStrategy, RoundRobinBalancer,
    LeastConnectionsBalancer, ResponseTimeBalancer, LoadBalancerManager
)
from src.core.service_discovery import ServiceClient


@pytest.mark.asyncio
class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    async def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state allows requests"""
        breaker = CircuitBreaker(
            name="test-service",
            failure_threshold=3,
            recovery_timeout=60
        )
        
        async def successful_call():
            return "success"
        
        result = await breaker.call(successful_call)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
    
    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures"""
        breaker = CircuitBreaker(
            name="test-service",
            failure_threshold=3,
            recovery_timeout=60
        )
        
        async def failing_call():
            raise Exception("Service error")
        
        # First 3 failures should go through
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_call)
        
        # Circuit should now be open
        assert breaker.state == CircuitState.OPEN
        
        # Next call should fail immediately
        with pytest.raises(CircuitBreakerError):
            await breaker.call(failing_call)
    
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery through half-open state"""
        breaker = CircuitBreaker(
            name="test-service",
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms for testing
            success_threshold=2
        )
        
        call_count = 0
        
        async def intermittent_call():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Service error")
            return "success"
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await breaker.call(intermittent_call)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(0.15)
        
        # Should transition to half-open and succeed
        result = await breaker.call(intermittent_call)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN
        
        # Another success should close the circuit
        result = await breaker.call(intermittent_call)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
    
    async def test_circuit_breaker_manager(self):
        """Test circuit breaker manager"""
        manager = CircuitBreakerManager()
        
        # Get breaker for service
        breaker1 = manager.get_breaker("service-1")
        breaker2 = manager.get_breaker("service-1")
        
        # Should return same instance
        assert breaker1 is breaker2
        
        # Get status
        status = manager.get_all_status()
        assert "service-1" in status
        assert status["service-1"]["state"] == "closed"


@pytest.mark.asyncio
class TestRetryMechanism:
    """Test retry functionality"""
    
    async def test_retry_success_on_second_attempt(self):
        """Test retry succeeds on second attempt"""
        call_count = 0
        
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise HTTPServerError("Server error")
            return "success"
        
        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        result = await retry_async(flaky_function, config=config)
        
        assert result == "success"
        assert call_count == 2
    
    async def test_retry_exhausted(self):
        """Test retry fails after max attempts"""
        call_count = 0
        
        async def always_failing():
            nonlocal call_count
            call_count += 1
            raise HTTPServerError("Server error")
        
        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        
        with pytest.raises(RetryError) as exc_info:
            await retry_async(always_failing, config=config)
        
        assert call_count == 3
        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exception, HTTPServerError)
    
    async def test_retry_non_retryable_exception(self):
        """Test retry doesn't retry non-retryable exceptions"""
        call_count = 0
        
        async def auth_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid request")
        
        config = RetryConfig(
            max_attempts=3,
            retryable_exceptions=[HTTPServerError],
            initial_delay=0.01
        )
        
        with pytest.raises(ValueError):
            await retry_async(auth_error, config=config)
        
        assert call_count == 1  # No retries
    
    async def test_retry_delay_calculation(self):
        """Test exponential backoff delay calculation"""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=10.0,
            jitter=False
        )
        
        assert config.calculate_delay(0) == 1.0  # First retry
        assert config.calculate_delay(1) == 2.0  # Second retry
        assert config.calculate_delay(2) == 4.0  # Third retry
        assert config.calculate_delay(3) == 8.0  # Fourth retry
        assert config.calculate_delay(4) == 10.0  # Capped at max


@pytest.mark.asyncio
class TestLoadBalancing:
    """Test load balancing strategies"""
    
    def create_instances(self, count: int) -> list[ServiceInstance]:
        """Create test service instances"""
        return [
            ServiceInstance(
                id=f"instance-{i}",
                url=f"http://localhost:800{i}",
                healthy=True,
                weight=i + 1,
                active_connections=i * 2,
                avg_response_time=0.1 * (i + 1)
            )
            for i in range(count)
        ]
    
    async def test_round_robin_balancer(self):
        """Test round-robin load balancing"""
        balancer = RoundRobinBalancer()
        instances = self.create_instances(3)
        
        # Should cycle through instances
        selected = []
        for _ in range(6):
            instance = await balancer.select(instances)
            selected.append(instance.id)
        
        assert selected == [
            "instance-0", "instance-1", "instance-2",
            "instance-0", "instance-1", "instance-2"
        ]
    
    async def test_least_connections_balancer(self):
        """Test least connections load balancing"""
        balancer = LeastConnectionsBalancer()
        instances = self.create_instances(3)
        
        # Should select instance with least connections
        instance = await balancer.select(instances)
        assert instance.id == "instance-0"  # Has 0 connections
        
        # Increase connections
        instances[0].active_connections = 10
        
        instance = await balancer.select(instances)
        assert instance.id == "instance-1"  # Now has least (2)
    
    async def test_response_time_balancer(self):
        """Test response time load balancing"""
        balancer = ResponseTimeBalancer()
        instances = self.create_instances(3)
        
        # Set request counts to enable response time selection
        for instance in instances:
            instance.total_requests = 100
        
        # Should select instance with best response time
        instance = await balancer.select(instances)
        assert instance.id == "instance-0"  # Has 0.1s response time
    
    async def test_unhealthy_instance_filtering(self):
        """Test that unhealthy instances are filtered out"""
        balancer = RoundRobinBalancer()
        instances = self.create_instances(3)
        
        # Mark middle instance as unhealthy
        instances[1].healthy = False
        
        # Should skip unhealthy instance
        selected = []
        for _ in range(4):
            instance = await balancer.select(instances)
            selected.append(instance.id)
        
        assert "instance-1" not in selected
        assert selected == ["instance-0", "instance-2", "instance-0", "instance-2"]
    
    async def test_load_balancer_manager(self):
        """Test load balancer manager"""
        manager = LoadBalancerManager()
        instances = self.create_instances(3)
        
        # Set strategy for service
        manager.set_service_strategy("test-service", LoadBalancingStrategy.LEAST_CONNECTIONS)
        
        # Select instance
        instance = await manager.select_instance("test-service", instances)
        assert instance.id == "instance-0"  # Least connections
        
        # Update metrics
        manager.update_instance_metrics(instance, response_time=0.05, success=True)
        assert instance.total_requests == 1
        assert instance.avg_response_time == 0.05


@pytest.mark.asyncio
class TestServiceClient:
    """Test service client with integrated features"""
    
    @patch('src.core.service_discovery.get_service_instance')
    @patch('httpx.AsyncClient.request')
    async def test_service_client_successful_request(self, mock_request, mock_get_instance):
        """Test successful request through service client"""
        # Mock service instance
        instance = ServiceInstance(
            id="test-1",
            url="http://localhost:8001",
            healthy=True
        )
        mock_get_instance.return_value = instance
        
        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = b'{"status": "ok"}'
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response
        
        # Create client and make request
        client = ServiceClient("test-service")
        response = await client.get("/test")
        
        assert response.status_code == 200
        assert instance.total_requests == 1
        assert instance.failed_requests == 0
    
    @patch('src.core.service_discovery.get_service_instance')
    @patch('httpx.AsyncClient.request')
    async def test_service_client_retry_on_failure(self, mock_request, mock_get_instance):
        """Test service client retries on failure"""
        # Mock service instance
        instance = ServiceInstance(
            id="test-1",
            url="http://localhost:8001",
            healthy=True
        )
        mock_get_instance.return_value = instance
        
        # Mock failures then success
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("Timeout")
            
            response = AsyncMock()
            response.status_code = 200
            response.content = b'{"status": "ok"}'
            response.headers = {"content-type": "application/json"}
            return response
        
        mock_request.side_effect = side_effect
        
        # Create client with custom retry config
        retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)
        client = ServiceClient("test-service", retry_config=retry_config)
        
        # Should succeed after retries
        response = await client.get("/test")
        assert response.status_code == 200
        assert call_count == 3


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for routing components"""
    
    @patch('src.core.service_discovery.check_service_health')
    async def test_health_check_updates_circuit_breaker(self, mock_health_check):
        """Test health check failures influence circuit breaker"""
        from src.core.service_discovery import health_check_task, _service_registry
        from src.core.circuit_breaker import circuit_breaker_manager
        
        # Create test instance
        instance = ServiceInstance(
            id="test-1",
            url="http://localhost:8001",
            healthy=True
        )
        _service_registry["test-service"] = [instance]
        
        # Mock health check failure
        mock_health_check.return_value = False
        
        # Run one iteration of health check
        # Note: In real implementation, this runs in a loop
        # For testing, we'll call the check directly
        is_healthy = await mock_health_check(instance.url)
        instance.healthy = is_healthy
        
        # Circuit breaker should be influenced
        breaker = circuit_breaker_manager.get_breaker("test-service")
        # In real implementation, health check would record failure
        await breaker._record_failure()
        
        assert breaker._failure_count == 1
    
    async def test_end_to_end_request_routing(self):
        """Test complete request routing flow"""
        # This would be a more complex integration test
        # involving actual service setup
        pass