"""
Load Balancer Implementation

Provides various load balancing strategies for distributing
requests across multiple service instances.
"""

import random
import time
from typing import List, Dict, Optional, Protocol
from enum import Enum
import logging
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ServiceInstance:
    """Represents a service instance"""
    id: str
    url: str
    healthy: bool = True
    weight: int = 1
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_health_check: float = 0.0


class LoadBalancingStrategy(Enum):
    """Available load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_LEAST_CONNECTIONS = "weighted_least_connections"
    RANDOM = "random"
    WEIGHTED_RANDOM = "weighted_random"
    IP_HASH = "ip_hash"
    RESPONSE_TIME = "response_time"


class LoadBalancer(Protocol):
    """Protocol for load balancer implementations"""
    
    def select(self, instances: List[ServiceInstance], context: Optional[Dict] = None) -> Optional[ServiceInstance]:
        """Select an instance based on the strategy"""
        ...


class RoundRobinBalancer:
    """Round-robin load balancer"""
    
    def __init__(self):
        self._current = 0
        self._lock = asyncio.Lock()
    
    async def select(self, instances: List[ServiceInstance], context: Optional[Dict] = None) -> Optional[ServiceInstance]:
        """Select next instance in round-robin fashion"""
        healthy_instances = [i for i in instances if i.healthy]
        
        if not healthy_instances:
            return None
        
        async with self._lock:
            instance = healthy_instances[self._current % len(healthy_instances)]
            self._current = (self._current + 1) % len(healthy_instances)
            
        return instance


class WeightedRoundRobinBalancer:
    """Weighted round-robin load balancer"""
    
    def __init__(self):
        self._current = 0
        self._current_weight = 0
        self._lock = asyncio.Lock()
    
    async def select(self, instances: List[ServiceInstance], context: Optional[Dict] = None) -> Optional[ServiceInstance]:
        """Select instance based on weight"""
        healthy_instances = [i for i in instances if i.healthy]
        
        if not healthy_instances:
            return None
        
        async with self._lock:
            # Calculate total weight
            total_weight = sum(i.weight for i in healthy_instances)
            
            if total_weight == 0:
                return healthy_instances[0]
            
            # Find the instance based on weighted position
            position = self._current_weight
            for instance in healthy_instances:
                position -= instance.weight
                if position < 0:
                    self._current_weight = (self._current_weight + 1) % total_weight
                    return instance
            
            # Fallback (shouldn't reach here)
            self._current_weight = 0
            return healthy_instances[0]


class LeastConnectionsBalancer:
    """Least connections load balancer"""
    
    async def select(self, instances: List[ServiceInstance], context: Optional[Dict] = None) -> Optional[ServiceInstance]:
        """Select instance with least active connections"""
        healthy_instances = [i for i in instances if i.healthy]
        
        if not healthy_instances:
            return None
        
        # Sort by active connections
        return min(healthy_instances, key=lambda i: i.active_connections)


class WeightedLeastConnectionsBalancer:
    """Weighted least connections load balancer"""
    
    async def select(self, instances: List[ServiceInstance], context: Optional[Dict] = None) -> Optional[ServiceInstance]:
        """Select instance with best connection-to-weight ratio"""
        healthy_instances = [i for i in instances if i.healthy]
        
        if not healthy_instances:
            return None
        
        # Calculate connection-to-weight ratio
        def connection_ratio(instance: ServiceInstance) -> float:
            if instance.weight == 0:
                return float('inf')
            return instance.active_connections / instance.weight
        
        return min(healthy_instances, key=connection_ratio)


class RandomBalancer:
    """Random load balancer"""
    
    async def select(self, instances: List[ServiceInstance], context: Optional[Dict] = None) -> Optional[ServiceInstance]:
        """Select random healthy instance"""
        healthy_instances = [i for i in instances if i.healthy]
        
        if not healthy_instances:
            return None
        
        return random.choice(healthy_instances)


class WeightedRandomBalancer:
    """Weighted random load balancer"""
    
    async def select(self, instances: List[ServiceInstance], context: Optional[Dict] = None) -> Optional[ServiceInstance]:
        """Select random instance based on weight"""
        healthy_instances = [i for i in instances if i.healthy]
        
        if not healthy_instances:
            return None
        
        # Calculate weights
        weights = [i.weight for i in healthy_instances]
        
        # If all weights are 0, select randomly
        if sum(weights) == 0:
            return random.choice(healthy_instances)
        
        # Weighted random selection
        return random.choices(healthy_instances, weights=weights)[0]


class IPHashBalancer:
    """IP hash based load balancer"""
    
    async def select(self, instances: List[ServiceInstance], context: Optional[Dict] = None) -> Optional[ServiceInstance]:
        """Select instance based on client IP hash"""
        healthy_instances = [i for i in instances if i.healthy]
        
        if not healthy_instances:
            return None
        
        # Get client IP from context
        if not context or 'client_ip' not in context:
            # Fallback to random if no IP
            return random.choice(healthy_instances)
        
        # Simple hash based on IP
        client_ip = context['client_ip']
        hash_value = hash(client_ip)
        
        # Select instance based on hash
        index = hash_value % len(healthy_instances)
        return healthy_instances[index]


class ResponseTimeBalancer:
    """Response time based load balancer"""
    
    async def select(self, instances: List[ServiceInstance], context: Optional[Dict] = None) -> Optional[ServiceInstance]:
        """Select instance with best response time"""
        healthy_instances = [i for i in instances if i.healthy]
        
        if not healthy_instances:
            return None
        
        # Filter instances with response time data
        instances_with_data = [
            i for i in healthy_instances 
            if i.total_requests > 0 and i.avg_response_time > 0
        ]
        
        if not instances_with_data:
            # No data available, select randomly
            return random.choice(healthy_instances)
        
        # Select instance with lowest average response time
        return min(instances_with_data, key=lambda i: i.avg_response_time)


class LoadBalancerManager:
    """Manages load balancers for different services"""
    
    def __init__(self, default_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        """
        Initialize load balancer manager
        
        Args:
            default_strategy: Default load balancing strategy
        """
        self._default_strategy = default_strategy
        self._balancers: Dict[str, LoadBalancer] = {}
        self._strategies: Dict[LoadBalancingStrategy, LoadBalancer] = {
            LoadBalancingStrategy.ROUND_ROBIN: RoundRobinBalancer(),
            LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: WeightedRoundRobinBalancer(),
            LoadBalancingStrategy.LEAST_CONNECTIONS: LeastConnectionsBalancer(),
            LoadBalancingStrategy.WEIGHTED_LEAST_CONNECTIONS: WeightedLeastConnectionsBalancer(),
            LoadBalancingStrategy.RANDOM: RandomBalancer(),
            LoadBalancingStrategy.WEIGHTED_RANDOM: WeightedRandomBalancer(),
            LoadBalancingStrategy.IP_HASH: IPHashBalancer(),
            LoadBalancingStrategy.RESPONSE_TIME: ResponseTimeBalancer(),
        }
        self._service_strategies: Dict[str, LoadBalancingStrategy] = {}
    
    def set_service_strategy(self, service_name: str, strategy: LoadBalancingStrategy) -> None:
        """
        Set load balancing strategy for a service
        
        Args:
            service_name: Service name
            strategy: Load balancing strategy
        """
        self._service_strategies[service_name] = strategy
        logger.info(f"Set {service_name} load balancing strategy to {strategy.value}")
    
    def get_balancer(self, service_name: str) -> LoadBalancer:
        """
        Get load balancer for service
        
        Args:
            service_name: Service name
            
        Returns:
            Load balancer instance
        """
        strategy = self._service_strategies.get(service_name, self._default_strategy)
        return self._strategies[strategy]
    
    async def select_instance(
        self,
        service_name: str,
        instances: List[ServiceInstance],
        context: Optional[Dict] = None
    ) -> Optional[ServiceInstance]:
        """
        Select a service instance
        
        Args:
            service_name: Service name
            instances: Available instances
            context: Request context (e.g., client IP)
            
        Returns:
            Selected instance or None
        """
        if not instances:
            logger.warning(f"No instances available for service {service_name}")
            return None
        
        balancer = self.get_balancer(service_name)
        instance = await balancer.select(instances, context)
        
        if instance:
            logger.debug(
                f"Selected instance {instance.id} for service {service_name} "
                f"using {self._service_strategies.get(service_name, self._default_strategy).value} strategy"
            )
        else:
            logger.warning(f"No healthy instances available for service {service_name}")
        
        return instance
    
    def update_instance_metrics(
        self,
        instance: ServiceInstance,
        response_time: float,
        success: bool
    ) -> None:
        """
        Update instance metrics after request
        
        Args:
            instance: Service instance
            response_time: Response time in seconds
            success: Whether request succeeded
        """
        instance.total_requests += 1
        
        if not success:
            instance.failed_requests += 1
        
        # Update average response time (simple moving average)
        if instance.total_requests == 1:
            instance.avg_response_time = response_time
        else:
            # Weighted average giving more weight to recent requests
            alpha = 0.2  # Smoothing factor
            instance.avg_response_time = (
                alpha * response_time + 
                (1 - alpha) * instance.avg_response_time
            )


# Global load balancer manager
load_balancer_manager = LoadBalancerManager()