# API Gateway Health Check Guide

## Overview

The MAMS API Gateway provides comprehensive health check endpoints for monitoring service health, readiness, and diagnostics. These endpoints are designed to work with various monitoring systems, container orchestrators, and load balancers.

## Health Check Endpoints

### 1. Basic Health Check

**Endpoint**: `GET /health/`

Provides a quick health status of the API Gateway.

**Query Parameters**:
- `include_details` (boolean, default: false): Include detailed component information
- `check_dependencies` (boolean, default: false): Check downstream service dependencies

**Response Example**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "version": "1.0.0",
  "environment": "production",
  "uptime_seconds": 3600.5,
  "response_time_ms": 15.23
}
```

**With Details**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "version": "1.0.0",
  "environment": "production",
  "uptime_seconds": 3600.5,
  "response_time_ms": 25.45,
  "components": [
    {
      "name": "database",
      "status": "healthy",
      "timestamp": "2024-01-15T10:30:45.100Z",
      "message": "Database connection successful",
      "response_time_ms": 5.23
    },
    {
      "name": "redis",
      "status": "healthy",
      "timestamp": "2024-01-15T10:30:45.105Z",
      "message": "Redis connection successful",
      "response_time_ms": 2.15,
      "details": {
        "version": "7.0.5",
        "connected_clients": 5,
        "used_memory_human": "25.3M",
        "ping_latency_ms": 0.45
      }
    }
  ]
}
```

### 2. Readiness Check

**Endpoint**: `GET /health/ready`

Checks if the service is ready to accept requests. Used by Kubernetes readiness probes and load balancers.

**Response Example**:
```json
{
  "ready": true,
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "redis": {
      "status": "healthy",
      "message": "Redis connection successful"
    }
  }
}
```

**Status Codes**:
- `200 OK`: Service is ready
- `503 Service Unavailable`: Service is not ready

### 3. Liveness Check

**Endpoint**: `GET /health/live`

Simple check to verify the service is alive and responding. Used by Kubernetes liveness probes.

**Response Example**:
```json
{
  "status": "alive",
  "service": "MAMS API Gateway",
  "version": "1.0.0",
  "timestamp": 1705318245.123,
  "uptime": 3600.5
}
```

### 4. Startup Check

**Endpoint**: `GET /health/startup`

Used by Kubernetes to know when the container has started. Returns 200 as soon as the basic application is running.

**Response Example**:
```json
{
  "status": "started",
  "timestamp": 1705318245.123,
  "version": "1.0.0",
  "environment": "production"
}
```

### 5. Service Health Status

**Endpoint**: `GET /health/services`

Get health status of all downstream services. Requires authentication.

**Query Parameters**:
- `check_health` (boolean, default: true): Perform active health checks

**Response Example**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "services": {
    "user-management": {
      "status": "healthy",
      "message": "Service user-management is healthy",
      "response_time_ms": 12.34,
      "details": {
        "status_code": 200,
        "available_instances": 3
      }
    },
    "asset-management": {
      "status": "healthy",
      "message": "Service asset-management is healthy",
      "response_time_ms": 15.67,
      "details": {
        "status_code": 200,
        "available_instances": 2
      }
    }
  }
}
```

### 6. Health Metrics

**Endpoint**: `GET /health/metrics`

Get basic health metrics for monitoring systems.

**Response Example**:
```json
{
  "timestamp": 1705318245.123,
  "gateway": {
    "status": "healthy",
    "version": "1.0.0",
    "environment": "production"
  },
  "redis": {
    "status": "healthy"
  },
  "services": {
    "total_healthy": 10,
    "total_unhealthy": 0,
    "total_instances": 10,
    "by_service": {
      "user-management": {
        "healthy_instances": 3,
        "unhealthy_instances": 0,
        "total_instances": 3
      }
    }
  }
}
```

### 7. Diagnostics

**Endpoint**: `GET /health/diagnostics`

Provides comprehensive diagnostic data for troubleshooting. Requires admin permissions.

**Response Example**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "version": "1.0.0",
  "environment": "production",
  "uptime_seconds": 3600.5,
  "components": [...],
  "dependencies": [...],
  "configuration": {
    "environment": "production",
    "debug_mode": false,
    "allowed_hosts": ["api.mams.local"],
    "cors_origins": ["https://app.mams.local"],
    "rate_limit_enabled": true
  },
  "performance": {
    "request_duration": {
      "count": 10000,
      "min": 0.001,
      "max": 2.345,
      "avg": 0.067,
      "p50": 0.045,
      "p90": 0.123,
      "p95": 0.234,
      "p99": 0.567
    }
  },
  "errors": {
    "recent_errors_count": 5,
    "last_error_timestamp": "2024-01-15T10:25:00.000Z",
    "error_rate_per_minute": 0.08
  },
  "connections": {
    "database": {
      "size": 10,
      "checked_in": 8,
      "checked_out": 2,
      "overflow": 0,
      "total": 10
    },
    "redis": {
      "created_connections": 5,
      "available_connections": 4,
      "in_use_connections": 1
    }
  }
}
```

### 8. Health History

**Endpoint**: `GET /health/history`

Returns historical health check data for trend analysis. Requires authentication.

**Query Parameters**:
- `hours` (integer, default: 24, max: 168): Hours of history to retrieve

**Response Example**:
```json
{
  "requested_hours": 24,
  "data_points": [
    {
      "timestamp": "2024-01-15T10:00:00.000Z",
      "status": "healthy",
      "response_time_ms": 15.23,
      "component_statuses": {
        "database": "healthy",
        "redis": "healthy"
      }
    }
  ],
  "summary": {
    "average_response_time_ms": 16.45,
    "uptime_percentage": 99.95,
    "total_checks": 1440,
    "failed_checks": 1
  }
}
```

## Health Status Values

The system uses the following health status values:

- **healthy**: All components are functioning normally
- **degraded**: Some non-critical components have issues, but the service is operational
- **unhealthy**: Critical components have failed, service is not operational
- **unknown**: Unable to determine health status

## Component Health Checks

The following components are monitored:

### 1. Database
- Connection availability
- Query execution capability
- Connection pool status

### 2. Redis
- Connection availability
- Ping latency
- Memory usage
- Connected clients

### 3. Disk Space
- Available disk space
- Usage percentage
- Thresholds:
  - Healthy: < 85% used
  - Degraded: 85-95% used
  - Unhealthy: > 95% used

### 4. Memory
- System memory usage
- Process memory usage
- Thresholds:
  - Healthy: < 85% used
  - Degraded: 85-95% used
  - Unhealthy: > 95% used

### 5. CPU
- CPU usage percentage
- Process CPU usage
- Thresholds:
  - Healthy: < 75% used
  - Degraded: 75-90% used
  - Unhealthy: > 90% used

## Integration with Monitoring Systems

### Kubernetes Configuration

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: api-gateway
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8000
      initialDelaySeconds: 15
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    
    startupProbe:
      httpGet:
        path: /health/startup
        port: 8000
      initialDelaySeconds: 0
      periodSeconds: 5
      timeoutSeconds: 5
      failureThreshold: 30
```

### Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'api-gateway'
    static_configs:
      - targets: ['api-gateway:8000']
    metrics_path: '/health/metrics'
    scrape_interval: 30s
```

### Load Balancer Configuration

Example for AWS ALB:
```
Health check path: /health/ready
Health check interval: 30 seconds
Health check timeout: 5 seconds
Healthy threshold: 2
Unhealthy threshold: 3
```

## Custom Health Checks

You can register custom health checks programmatically:

```python
from core.health import register_health_check, ComponentHealth, HealthStatus

async def check_external_api() -> ComponentHealth:
    """Check external API availability"""
    try:
        # Your check logic here
        response = await external_api_client.health_check()
        
        if response.status_code == 200:
            return ComponentHealth(
                name="external_api",
                status=HealthStatus.HEALTHY,
                message="External API is available"
            )
        else:
            return ComponentHealth(
                name="external_api",
                status=HealthStatus.UNHEALTHY,
                message=f"External API returned {response.status_code}"
            )
    except Exception as e:
        return ComponentHealth(
            name="external_api",
            status=HealthStatus.UNHEALTHY,
            message=str(e)
        )

# Register the check
register_health_check("external_api", check_external_api)
```

## Best Practices

1. **Use Appropriate Endpoints**:
   - Use `/health/live` for liveness checks
   - Use `/health/ready` for readiness checks
   - Use `/health/` for general monitoring

2. **Configure Timeouts**:
   - Set appropriate timeouts for health checks (5-10 seconds)
   - Don't make timeout too short to avoid false positives

3. **Set Thresholds**:
   - Configure failure thresholds to avoid flapping
   - Use higher thresholds for liveness than readiness

4. **Monitor Dependencies**:
   - Enable dependency checks for comprehensive monitoring
   - Use caching to avoid overloading downstream services

5. **Security**:
   - Protect diagnostic endpoints with authentication
   - Don't expose sensitive information in public endpoints

6. **Performance**:
   - Health checks are cached for 10 seconds by default
   - Adjust cache TTL based on your needs

## Troubleshooting

### Service Shows Unhealthy

1. Check `/health/diagnostics` for detailed information
2. Review component statuses
3. Check connection pool statistics
4. Review recent errors

### High Response Times

1. Check CPU and memory usage
2. Review database connection pool
3. Check downstream service health
4. Enable performance metrics logging

### Intermittent Failures

1. Increase health check timeouts
2. Adjust failure thresholds
3. Check for resource contention
4. Review network connectivity