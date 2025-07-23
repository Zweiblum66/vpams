"""
Service Management API

Endpoints for managing service discovery, load balancing, and circuit breakers.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.config import get_settings
from core.service_discovery import (
    register_service, deregister_service, get_service_status
)
from core.circuit_breaker import circuit_breaker_manager
from core.load_balancer import LoadBalancingStrategy, load_balancer_manager
from api.dependencies import get_current_user, require_permissions

settings = get_settings()
router = APIRouter(prefix="/api/v1/services", tags=["service-management"])


class ServiceRegistration(BaseModel):
    """Service registration request"""
    service_name: str = Field(..., description="Service name")
    service_url: str = Field(..., description="Service URL")
    weight: int = Field(default=1, ge=0, le=100, description="Weight for load balancing")


class ServiceDeregistration(BaseModel):
    """Service deregistration request"""
    service_name: str = Field(..., description="Service name")
    service_url: str = Field(..., description="Service URL")


class LoadBalancingConfig(BaseModel):
    """Load balancing configuration"""
    service_name: str = Field(..., description="Service name")
    strategy: LoadBalancingStrategy = Field(..., description="Load balancing strategy")


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration"""
    service_name: str = Field(..., description="Service name")
    failure_threshold: int = Field(default=5, ge=1, le=100)
    recovery_timeout: int = Field(default=60, ge=10, le=600)
    success_threshold: int = Field(default=2, ge=1, le=10)


@router.get("/status")
async def get_all_services_status(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get status of all services
    
    Returns detailed information about all registered services,
    their health status, and circuit breaker states.
    """
    return await get_service_status()


@router.post("/register")
async def register_service_instance(
    registration: ServiceRegistration,
    current_user: Dict = Depends(require_permissions("admin", "service.write"))
):
    """
    Register a new service instance
    
    Adds a new instance to the service registry for load balancing.
    Requires admin permissions.
    """
    await register_service(
        service_name=registration.service_name,
        service_url=registration.service_url,
        weight=registration.weight
    )
    
    return {
        "message": "Service instance registered successfully",
        "service_name": registration.service_name,
        "service_url": registration.service_url,
        "weight": registration.weight
    }


@router.delete("/deregister")
async def deregister_service_instance(
    deregistration: ServiceDeregistration,
    current_user: Dict = Depends(require_permissions("admin", "service.write"))
):
    """
    Deregister a service instance
    
    Removes an instance from the service registry.
    Requires admin permissions.
    """
    await deregister_service(
        service_name=deregistration.service_name,
        service_url=deregistration.service_url
    )
    
    return {
        "message": "Service instance deregistered successfully",
        "service_name": deregistration.service_name,
        "service_url": deregistration.service_url
    }


@router.get("/load-balancing/strategies")
async def get_load_balancing_strategies(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get available load balancing strategies
    
    Returns a list of all available load balancing strategies.
    """
    return {
        "strategies": [
            {
                "name": strategy.value,
                "description": get_strategy_description(strategy)
            }
            for strategy in LoadBalancingStrategy
        ]
    }


@router.put("/load-balancing/config")
async def update_load_balancing_config(
    config: LoadBalancingConfig,
    current_user: Dict = Depends(require_permissions("admin", "service.write"))
):
    """
    Update load balancing configuration for a service
    
    Sets the load balancing strategy for a specific service.
    Requires admin permissions.
    """
    load_balancer_manager.set_service_strategy(
        service_name=config.service_name,
        strategy=config.strategy
    )
    
    return {
        "message": "Load balancing configuration updated",
        "service_name": config.service_name,
        "strategy": config.strategy.value
    }


@router.get("/circuit-breakers")
async def get_circuit_breakers_status(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get status of all circuit breakers
    
    Returns the current state of all circuit breakers.
    """
    return circuit_breaker_manager.get_all_status()


@router.post("/circuit-breakers/{service_name}/reset")
async def reset_circuit_breaker(
    service_name: str,
    current_user: Dict = Depends(require_permissions("admin", "service.write"))
):
    """
    Reset a circuit breaker
    
    Manually resets a circuit breaker to closed state.
    Requires admin permissions.
    """
    await circuit_breaker_manager.reset(service_name)
    
    return {
        "message": f"Circuit breaker for {service_name} has been reset",
        "service_name": service_name,
        "state": "closed"
    }


@router.post("/circuit-breakers/reset-all")
async def reset_all_circuit_breakers(
    current_user: Dict = Depends(require_permissions("admin", "service.write"))
):
    """
    Reset all circuit breakers
    
    Manually resets all circuit breakers to closed state.
    Requires admin permissions.
    """
    await circuit_breaker_manager.reset_all()
    
    return {
        "message": "All circuit breakers have been reset",
        "state": "closed"
    }


def get_strategy_description(strategy: LoadBalancingStrategy) -> str:
    """Get human-readable description for load balancing strategy"""
    descriptions = {
        LoadBalancingStrategy.ROUND_ROBIN: "Distributes requests evenly in circular order",
        LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: "Distributes requests based on instance weights",
        LoadBalancingStrategy.LEAST_CONNECTIONS: "Routes to instance with fewest active connections",
        LoadBalancingStrategy.WEIGHTED_LEAST_CONNECTIONS: "Routes based on connection-to-weight ratio",
        LoadBalancingStrategy.RANDOM: "Randomly selects a healthy instance",
        LoadBalancingStrategy.WEIGHTED_RANDOM: "Randomly selects based on instance weights",
        LoadBalancingStrategy.IP_HASH: "Routes based on client IP address hash",
        LoadBalancingStrategy.RESPONSE_TIME: "Routes to instance with best response time"
    }
    return descriptions.get(strategy, "Unknown strategy")