# API Gateway Service

## Overview

The API Gateway Service is the single entry point for all client requests to the MAMS platform. It provides authentication, authorization, rate limiting, request routing, and acts as a reverse proxy to all backend microservices.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway Service                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Security   │  │Rate Limiting │  │     Routing     │  │
│  │             │  │              │  │                 │  │
│  │  - Auth     │  │ - Per User   │  │ - Path Based    │  │
│  │  - CORS     │  │ - Per IP     │  │ - Load Balance  │  │
│  │  - Headers  │  │ - Throttling │  │ - Health Check  │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                  Middleware Stack                     │  │
│  │   Request ID | Logging | Metrics | Error Handler     │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                 Service Registry                      │  │
│  │   All Backend Services | Health Status | Endpoints   │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Authentication & Authorization
- JWT token validation
- OAuth2/OIDC support
- API key authentication
- Role-based access control (RBAC)
- Multi-factor authentication (MFA)

### 2. Rate Limiting
- Per-user rate limits
- Per-IP rate limits
- Endpoint-specific limits
- Burst handling
- Rate limit headers

### 3. Request Routing
- Path-based routing
- Service discovery
- Load balancing
- Circuit breaking
- Retry logic

### 4. Security
- CORS handling
- Request validation
- Header sanitization
- SQL injection prevention
- XSS protection

### 5. Monitoring & Logging
- Request/response logging
- Performance metrics
- Error tracking
- Distributed tracing
- Health checks

## API Endpoints

### Authentication Endpoints

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure-password",
  "mfa_code": "123456" // Optional
}
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "name": "John Doe",
    "roles": ["user", "editor"]
  }
}
```

#### Refresh Token
```http
POST /api/v1/auth/refresh
Content-Type: application/json
Authorization: Bearer {refresh_token}

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Logout
```http
POST /api/v1/auth/logout
Authorization: Bearer {access_token}
```

### Service Proxy Endpoints

All service endpoints are proxied through the gateway:

```
/api/v1/users/*      → User Management Service (8001)
/api/v1/storage/*    → Storage Abstraction Service (8002)
/api/v1/assets/*     → Asset Management Service (8004)
/api/v1/metadata/*   → Metadata Service (8005)
/api/v1/search/*     → Search Engine Service (8006)
/api/v1/ingest/*     → Ingest Service (8007)
/api/v1/proxy/*      → Proxy Generation Service (8008)
/api/v1/workflows/*  → Workflow Engine Service (8009)
/api/v1/ml/*         → AI/ML Service (8010)
/api/v1/rights/*     → Rights Management Service (8011)
/api/v1/monitor/*    → Monitoring Service (8012)
```

### Gateway-Specific Endpoints

#### Health Check
```http
GET /health

Response:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "services": {
    "user-management": "healthy",
    "asset-management": "healthy",
    "storage": "healthy",
    // ... all services
  }
}
```

#### Service Discovery
```http
GET /api/v1/services

Response:
{
  "services": [
    {
      "name": "user-management",
      "version": "1.0.0",
      "status": "healthy",
      "endpoints": ["/api/v1/users"],
      "url": "http://user-management:8001"
    },
    // ... all services
  ]
}
```

#### Rate Limit Status
```http
GET /api/v1/rate-limit
Authorization: Bearer {token}

Response:
{
  "limit": 1000,
  "remaining": 950,
  "reset": 1642089600,
  "retry_after": null
}
```

## Configuration

### Environment Variables

```bash
# Service Configuration
API_GATEWAY_PORT=8000
SERVICE_NAME=api-gateway
LOG_LEVEL=INFO

# Security
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
REFRESH_TOKEN_EXPIRATION_DAYS=30

# CORS
CORS_ORIGINS=http://localhost:3000,https://app.mams.com
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=1000/hour
RATE_LIMIT_BURST=100

# Service Discovery
SERVICE_DISCOVERY_METHOD=dns  # dns, consul, kubernetes
SERVICE_REGISTRY_URL=http://consul:8500

# Redis (for rate limiting and session storage)
REDIS_URL=redis://redis:6379/0

# Monitoring
ENABLE_METRICS=true
ENABLE_TRACING=true
JAEGER_AGENT_HOST=jaeger
JAEGER_AGENT_PORT=6831
```

### Service Configuration (config.yaml)

```yaml
api_gateway:
  # Request handling
  request:
    max_body_size: 5GB
    timeout: 300s
    max_header_size: 8192
    
  # Security
  security:
    enabled: true
    jwt:
      algorithm: HS256
      expiration_minutes: 60
      refresh_expiration_days: 30
    api_keys:
      enabled: true
      header_name: X-API-Key
    
  # Rate limiting
  rate_limiting:
    enabled: true
    storage: redis
    rules:
      - path: /api/v1/auth/login
        limit: 5/minute
      - path: /api/v1/assets/upload
        limit: 100/hour
      - path: /api/v1/*
        limit: 1000/hour
        
  # Service routing
  services:
    - name: user-management
      prefix: /api/v1/users
      url: http://user-management:8001
      timeout: 30s
      retry:
        attempts: 3
        backoff: exponential
    - name: asset-management
      prefix: /api/v1/assets
      url: http://asset-management:8004
      timeout: 300s
      
  # Circuit breaker
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 60s
    expected_response_time: 10s
```

## Rate Limiting

### Rate Limit Rules

```python
RATE_LIMIT_RULES = {
    # Authentication endpoints
    "/api/v1/auth/login": "5/minute",
    "/api/v1/auth/register": "3/hour",
    "/api/v1/auth/password-reset": "3/hour",
    
    # Upload endpoints
    "/api/v1/assets/upload": "100/hour",
    "/api/v1/assets/*/upload": "50/hour",
    
    # Search endpoints
    "/api/v1/search": "100/minute",
    
    # Default for authenticated users
    "authenticated": "1000/hour",
    
    # Default for anonymous users
    "anonymous": "100/hour",
}
```

### Rate Limit Headers

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642089600
X-RateLimit-Reset-After: 3600
X-RateLimit-Bucket: user-123
```

## Security Features

### 1. Request Validation

```python
# Middleware for request validation
@app.middleware("http")
async def validate_request(request: Request, call_next):
    # Check content type
    if request.method in ["POST", "PUT", "PATCH"]:
        content_type = request.headers.get("content-type", "")
        if not content_type.startswith(("application/json", "multipart/form-data")):
            return JSONResponse(
                status_code=415,
                content={"error": "Unsupported Media Type"}
            )
    
    # Validate headers
    if len(request.headers) > 100:
        return JSONResponse(
            status_code=431,
            content={"error": "Request Header Fields Too Large"}
        )
    
    # Check for SQL injection patterns
    if contains_sql_injection(request.url.path):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid request"}
        )
    
    response = await call_next(request)
    return response
```

### 2. CORS Configuration

```python
# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-RateLimit-*"],
)
```

### 3. Security Headers

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

## Load Balancing

### Strategy Options

```python
class LoadBalancingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"
    RANDOM = "random"
```

### Implementation

```python
class ServiceRouter:
    def __init__(self, strategy: LoadBalancingStrategy):
        self.strategy = strategy
        self.services = {}
        self.current_index = {}
        
    def get_service_instance(self, service_name: str) -> str:
        instances = self.services.get(service_name, [])
        if not instances:
            raise ServiceUnavailableError(f"No instances available for {service_name}")
            
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            index = self.current_index.get(service_name, 0)
            instance = instances[index % len(instances)]
            self.current_index[service_name] = index + 1
            return instance
            
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(instances)
        
        # ... other strategies
```

## Circuit Breaker

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError("Circuit breaker is OPEN")
                
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

## Monitoring & Metrics

### Prometheus Metrics

```python
# Define metrics
request_count = Counter(
    'api_gateway_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'api_gateway_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'api_gateway_active_connections',
    'Number of active connections'
)

# Track metrics
@app.middleware("http")
async def track_metrics(request: Request, call_next):
    start_time = time.time()
    active_connections.inc()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response
    finally:
        active_connections.dec()
```

## WebSocket Support

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # Validate token
    user = await validate_websocket_token(token)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return
        
    await websocket.accept()
    
    # Add to connection manager
    await connection_manager.connect(websocket, user.id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Route message to appropriate service
            if data["type"] == "asset_update":
                await route_to_service("asset-management", data)
            elif data["type"] == "workflow_status":
                await route_to_service("workflow-engine", data)
                
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, user.id)
```

## Error Handling

### Global Error Handler

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log error
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Determine error response
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "timestamp": datetime.utcnow().isoformat(),
                    "path": request.url.path
                }
            }
        )
    
    # Generic error response
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request.state.request_id
            }
        }
    )
```

## Deployment

### Docker Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: mams/api-gateway:latest
        ports:
        - containerPort: 8000
        env:
        - name: SERVICE_NAME
          value: api-gateway
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
```

## Performance Optimization

### 1. Connection Pooling
- HTTP connection pools for backend services
- Redis connection pool for rate limiting
- Database connection pool for auth

### 2. Caching
- Response caching for GET requests
- JWT validation caching
- Service discovery caching

### 3. Async Processing
- Non-blocking I/O
- Concurrent request handling
- Background task processing

### 4. Request Optimization
- Request deduplication
- Response compression
- HTTP/2 support

---

For more information:
- [Authentication Guide](../configuration/authentication.md)
- [Rate Limiting Configuration](../configuration/rate-limiting.md)
- [Security Best Practices](../security/api-security.md)
- [Monitoring Setup](../operations/monitoring.md)