# API Gateway Request Routing Guide

## Overview

The MAMS API Gateway implements sophisticated request routing to microservices with features including:
- **Load Balancing**: Multiple strategies for distributing requests
- **Circuit Breakers**: Prevent cascading failures
- **Retry Logic**: Automatic retry with exponential backoff
- **Health Checks**: Continuous monitoring of service health
- **Service Discovery**: Dynamic service registration and discovery

## Architecture

### Components

1. **Service Discovery**
   - Maintains registry of available service instances
   - Performs periodic health checks
   - Tracks instance metrics

2. **Load Balancer**
   - Implements multiple load balancing strategies
   - Considers instance health and metrics
   - Supports weighted distribution

3. **Circuit Breaker**
   - Prevents calls to failing services
   - Automatic recovery detection
   - Manual reset capability

4. **Retry Mechanism**
   - Exponential backoff with jitter
   - Configurable retry policies
   - Smart exception handling

## Service Routes

The gateway routes requests based on the URL path:

| Path Prefix | Service |
|-------------|---------|
| `/api/v1/users` | user-management |
| `/api/v1/auth` | user-management |
| `/api/v1/assets` | asset-management |
| `/api/v1/metadata` | metadata-service |
| `/api/v1/search` | search-engine |
| `/api/v1/storage` | storage-abstraction |
| `/api/v1/ingest` | ingest-service |
| `/api/v1/proxy` | proxy-generation |
| `/api/v1/workflows` | workflow-engine |
| `/api/v1/ai` | ai-ml-service |
| `/api/v1/rights` | rights-management |
| `/api/v1/monitoring` | monitoring-logging |
| `/api/v1/integrations` | integration-service |

## Load Balancing Strategies

### 1. Round Robin (Default)
```python
# Requests distributed evenly in order
Request 1 → Instance A
Request 2 → Instance B
Request 3 → Instance C
Request 4 → Instance A
```

### 2. Weighted Round Robin
```python
# Distribution based on weights
Instance A (weight=3)
Instance B (weight=1)
Pattern: A, A, A, B, A, A, A, B...
```

### 3. Least Connections
```python
# Routes to instance with fewest active connections
Instance A: 5 connections → Skip
Instance B: 2 connections → Selected
Instance C: 8 connections → Skip
```

### 4. Weighted Least Connections
```python
# Considers both connections and weight
Instance A: 10 connections, weight=2 → Ratio: 5.0
Instance B: 6 connections, weight=3 → Ratio: 2.0 (Selected)
```

### 5. Random
```python
# Random selection of healthy instances
```

### 6. Weighted Random
```python
# Random selection considering weights
Instance A (weight=3): 60% chance
Instance B (weight=2): 40% chance
```

### 7. IP Hash
```python
# Consistent routing based on client IP
hash(192.168.1.100) → Always Instance B
hash(192.168.1.101) → Always Instance A
```

### 8. Response Time
```python
# Routes to instance with best average response time
Instance A: avg 120ms → Skip
Instance B: avg 45ms → Selected
Instance C: avg 230ms → Skip
```

## Circuit Breaker States

### Closed (Normal)
- All requests pass through
- Failures are counted
- Transitions to Open after threshold

### Open (Failing)
- Requests fail immediately
- No calls to downstream service
- Waits for recovery timeout

### Half-Open (Testing)
- Limited requests allowed
- Testing if service recovered
- Transitions to Closed or Open based on results

```
   CLOSED
    ↓ (failures > threshold)
   OPEN
    ↓ (after timeout)
   HALF-OPEN
    ↓ (success) ↓ (failure)
   CLOSED     OPEN
```

## Retry Configuration

### Default Retry Policy
```python
{
    "max_attempts": 3,
    "initial_delay": 0.5,  # seconds
    "max_delay": 5.0,      # seconds
    "exponential_base": 2.0,
    "jitter": True
}
```

### Retry Timing
```
Attempt 1: Immediate
Attempt 2: Wait 0.5-0.625s (with jitter)
Attempt 3: Wait 1.0-1.25s (with jitter)
```

### Retryable Conditions
- 5xx server errors
- Connection timeouts
- Connection failures
- Network errors

### Non-Retryable Conditions
- 4xx client errors
- Authentication failures
- Invalid requests

## Request Flow

1. **Client Request**
   ```
   Client → API Gateway
   ```

2. **Authentication & Rate Limiting**
   ```
   Gateway → Validate JWT → Check Rate Limits
   ```

3. **Service Resolution**
   ```
   Path → Service Name → Available Instances
   ```

4. **Load Balancing**
   ```
   Strategy → Select Instance → Update Metrics
   ```

5. **Circuit Breaker Check**
   ```
   Check State → Allow/Deny Request
   ```

6. **Request Execution**
   ```
   Proxy Request → Handle Response/Error
   ```

7. **Retry on Failure**
   ```
   Check Retry Policy → Wait → Retry
   ```

8. **Response to Client**
   ```
   Add Headers → Return Response
   ```

## Headers

### Request Headers Added by Gateway
```http
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
X-User-ID: user123
X-Gateway: MAMS-API-Gateway
```

### Response Headers Added by Gateway
```http
X-Gateway: MAMS-API-Gateway
X-Response-Time: 0.145
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

## Service Management API

### Register Service Instance
```http
POST /api/v1/services/register
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "service_name": "asset-management",
  "service_url": "http://asset-service-2:8002",
  "weight": 2
}
```

### Update Load Balancing Strategy
```http
PUT /api/v1/services/load-balancing/config
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "service_name": "search-engine",
  "strategy": "least_connections"
}
```

### Check Service Status
```http
GET /api/v1/services/status
Authorization: Bearer <token>

Response:
{
  "services": {
    "asset-management": {
      "http://localhost:8002": {
        "id": "asset-management-1",
        "healthy": true,
        "weight": 1,
        "active_connections": 3,
        "total_requests": 1523,
        "failed_requests": 12,
        "avg_response_time": 0.087,
        "last_health_check": 1640995200
      }
    }
  },
  "circuit_breakers": {
    "asset-management": {
      "name": "asset-management",
      "state": "closed",
      "failure_count": 0,
      "success_count": 0,
      "is_healthy": true
    }
  }
}
```

### Reset Circuit Breaker
```http
POST /api/v1/services/circuit-breakers/asset-management/reset
Authorization: Bearer <admin_token>
```

## Configuration

### Environment Variables
```env
# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2

# Request Timeout
REQUEST_TIMEOUT=30

# Health Checks
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=5
```

### Service-Specific Configuration
```python
# In service_discovery.py init function
load_balancer_manager.set_service_strategy("search-engine", LoadBalancingStrategy.LEAST_CONNECTIONS)
load_balancer_manager.set_service_strategy("proxy-generation", LoadBalancingStrategy.WEIGHTED_LEAST_CONNECTIONS)
load_balancer_manager.set_service_strategy("ai-ml-service", LoadBalancingStrategy.RESPONSE_TIME)
```

## Error Handling

### Service Unavailable (503)
```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Service asset-management is unavailable",
    "details": {
      "service": "asset-management",
      "circuit_breaker_state": "open"
    }
  }
}
```

### Gateway Timeout (504)
```json
{
  "error": {
    "code": "GATEWAY_TIMEOUT",
    "message": "Request to asset-management timed out",
    "details": {
      "service": "asset-management",
      "timeout": 30
    }
  }
}
```

### Bad Gateway (502)
```json
{
  "error": {
    "code": "BAD_GATEWAY",
    "message": "Bad response from asset-management: 500",
    "details": {
      "service": "asset-management",
      "upstream_status": 500
    }
  }
}
```

## Monitoring

### Metrics to Monitor
1. **Service Health**
   - Instance availability
   - Health check success rate
   - Response times

2. **Circuit Breakers**
   - Open/Closed states
   - Failure rates
   - Recovery times

3. **Load Distribution**
   - Requests per instance
   - Connection counts
   - Load balance effectiveness

4. **Retry Metrics**
   - Retry rates
   - Success after retry
   - Retry exhaustion

### Prometheus Metrics
```
# Service health
service_instance_healthy{service="asset-management",instance="1"} 1
service_instance_response_time{service="asset-management",instance="1"} 0.087

# Circuit breaker
circuit_breaker_state{service="asset-management",state="closed"} 1
circuit_breaker_failures_total{service="asset-management"} 12

# Load balancing
load_balancer_requests_total{service="asset-management",instance="1"} 1523
load_balancer_active_connections{service="asset-management",instance="1"} 3

# Retries
retry_attempts_total{service="asset-management",result="success"} 45
retry_attempts_total{service="asset-management",result="exhausted"} 2
```

## Best Practices

### 1. Service Registration
- Register multiple instances for high availability
- Use appropriate weights based on instance capacity
- Update weights during maintenance

### 2. Load Balancing Strategy Selection
- **Round Robin**: For uniform instances
- **Least Connections**: For long-running requests
- **Response Time**: For performance-critical services
- **IP Hash**: For session affinity needs

### 3. Circuit Breaker Tuning
- Set failure threshold based on service criticality
- Adjust recovery timeout for service startup time
- Monitor circuit breaker states

### 4. Retry Configuration
- Limit retries for non-idempotent operations
- Use shorter delays for user-facing requests
- Add jitter to prevent thundering herd

### 5. Health Checks
- Implement meaningful health endpoints
- Include dependency checks
- Return detailed health information

## Troubleshooting

### Service Always Unavailable
1. Check service health endpoint
2. Verify network connectivity
3. Check circuit breaker state
4. Review service logs

### Uneven Load Distribution
1. Check load balancing strategy
2. Verify instance weights
3. Monitor active connections
4. Review instance health

### High Retry Rates
1. Check service stability
2. Review timeout settings
3. Analyze failure patterns
4. Consider circuit breaker thresholds

### Circuit Breaker Stuck Open
1. Manually check service health
2. Reset circuit breaker if healthy
3. Increase recovery timeout
4. Review failure threshold

## Performance Optimization

### 1. Connection Pooling
- Reuse HTTP connections
- Configure appropriate pool size
- Monitor connection usage

### 2. Timeout Tuning
- Set realistic timeouts
- Consider operation complexity
- Balance user experience vs reliability

### 3. Caching Strategy
- Cache service discovery results
- Implement negative caching
- Use appropriate TTLs

### 4. Metric Collection
- Use sampling for high-volume metrics
- Aggregate before sending
- Monitor metric overhead