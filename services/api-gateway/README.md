# MAMS API Gateway Service

The API Gateway service serves as the central entry point for all MAMS microservices, providing authentication, authorization, rate limiting, request routing, and monitoring capabilities.

## Features

- **Authentication & Authorization**: JWT token validation and API key support
- **Rate Limiting**: Redis-based distributed rate limiting with sliding window
- **Request Routing**: Intelligent routing to downstream microservices
- **Health Checks**: Comprehensive health monitoring for all services
- **Request/Response Logging**: Structured logging with request tracking
- **Service Discovery**: Dynamic service discovery with health monitoring
- **Error Handling**: Centralized error handling with proper HTTP status codes
- **Security**: CORS, security headers, input validation, and request size limits
- **Monitoring**: Prometheus metrics and health check endpoints

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │   Load Balancer │    │   API Gateway   │
│                 │────│                 │────│                 │
│ Web, Mobile,    │    │ (nginx, etc.)   │    │ Authentication  │
│ Third-party     │    │                 │    │ Rate Limiting   │
└─────────────────┘    └─────────────────┘    │ Routing         │
                                              └─────────────────┘
                                                       │
                                              ┌─────────────────┐
                                              │ Service Discovery│
                                              │ Health Checks   │
                                              └─────────────────┘
                                                       │
                       ┌───────────────────────────────┼───────────────────────────────┐
                       │                               │                               │
              ┌─────────────────┐            ┌─────────────────┐            ┌─────────────────┐
              │ User Management │            │ Asset Management│            │ Metadata Service │
              │   Service       │            │    Service      │            │                 │
              │   Port: 8001    │            │   Port: 8002    │            │   Port: 8003    │
              └─────────────────┘            └─────────────────┘            └─────────────────┘
```

## Quick Start

### 1. Using Docker Compose (Recommended)

```bash
# Start the API Gateway with dependencies
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f api-gateway

# Stop services
docker-compose -f docker-compose.dev.yml down
```

### 2. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Edit .env with your settings
nano .env

# Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# Start PostgreSQL (required)
docker run -d -p 5432:5432 -e POSTGRES_DB=mams_gateway -e POSTGRES_USER=mams_app -e POSTGRES_PASSWORD=mams_dev_password postgres:15-alpine

# Run the application
cd src
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest src/test_main.py -v
```

## API Endpoints

### Health Check Endpoints

- `GET /health` - Basic health check
- `GET /health/ready` - Readiness probe (checks dependencies)
- `GET /health/live` - Liveness probe (simple alive check)
- `GET /health/services` - Detailed service health status
- `GET /health/metrics` - Health metrics for monitoring

### API Routes

All API routes are prefixed with `/api/v1/` and routed to appropriate services:

- `GET /api/` - API information and available services
- `GET /api/status` - Gateway status and service health
- `ALL /api/v1/{service}/{path}` - Proxied to downstream services

### Service Routing

| Path Prefix | Service | Description |
|-------------|---------|-------------|
| `/api/v1/auth/` | user-management | Authentication endpoints |
| `/api/v1/users/` | user-management | User management |
| `/api/v1/assets/` | asset-management | Asset operations |
| `/api/v1/metadata/` | metadata-service | Metadata operations |
| `/api/v1/search/` | search-engine | Search functionality |
| `/api/v1/storage/` | storage-abstraction | Storage operations |
| `/api/v1/ingest/` | ingest-service | Content ingestion |
| `/api/v1/proxy/` | proxy-generation | Proxy generation |
| `/api/v1/workflows/` | workflow-engine | Workflow management |
| `/api/v1/ai/` | ai-ml-service | AI/ML operations |
| `/api/v1/rights/` | rights-management | Rights management |
| `/api/v1/monitoring/` | monitoring-logging | Monitoring data |
| `/api/v1/integrations/` | integration-service | External integrations |

## Configuration

### Environment Variables

Key environment variables (see `.env.example` for complete list):

```bash
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here-at-least-32-characters-long

# Server
HOST=0.0.0.0
PORT=8000

# Security
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Redis
REDIS_URL=redis://localhost:6379/0

# Database
DATABASE_URL=postgresql://mams_app:mams_dev_password@localhost:5432/mams_gateway
```

### Service Configuration

Configure downstream services in the `SERVICES` environment variable:

```json
{
  "user-management": "http://localhost:8001",
  "asset-management": "http://localhost:8002",
  "metadata-service": "http://localhost:8003"
}
```

## Authentication

The API Gateway supports multiple authentication methods:

### JWT Token Authentication

```bash
# Login to get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Use token in requests
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <token>"
```

### API Key Authentication

```bash
# Use API key in header
curl -X GET http://localhost:8000/api/v1/assets \
  -H "X-API-Key: <api-key>"
```

## Rate Limiting

The gateway implements sliding window rate limiting:

- **Default**: 100 requests per minute per user/IP
- **Burst**: 20 requests in quick succession
- **Headers**: Response includes rate limit headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1640995200
```

## Monitoring

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/ready

# Service status
curl http://localhost:8000/health/services

# Metrics
curl http://localhost:8000/health/metrics
```

### Logging

The gateway provides structured JSON logging:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "api_gateway.access",
  "message": "GET /api/v1/users - 200 - 0.045s",
  "request_id": "req_123",
  "method": "GET",
  "path": "/api/v1/users",
  "status_code": 200,
  "response_time": 0.045,
  "user_id": "user123",
  "ip_address": "192.168.1.100"
}
```

## Error Handling

The gateway provides standardized error responses:

```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Authentication required",
    "details": {},
    "timestamp": 1640995200,
    "request_id": "req_123"
  }
}
```

### Error Codes

- `AUTHENTICATION_REQUIRED` (401)
- `INVALID_TOKEN` (401)
- `INSUFFICIENT_PERMISSIONS` (403)
- `RATE_LIMIT_EXCEEDED` (429)
- `VALIDATION_ERROR` (422)
- `SERVICE_UNAVAILABLE` (503)
- `BAD_GATEWAY` (502)
- `GATEWAY_TIMEOUT` (504)

## Development

### Project Structure

```
src/
├── main.py                 # FastAPI application
├── core/
│   ├── config.py          # Configuration settings
│   ├── exceptions.py      # Custom exceptions
│   ├── logging.py         # Logging configuration
│   ├── middleware.py      # Custom middleware
│   ├── redis.py           # Redis connection
│   ├── security.py        # Security utilities
│   └── service_discovery.py  # Service discovery
├── api/
│   ├── routes.py          # Main API routes
│   └── health.py          # Health check routes
└── test_main.py           # Basic tests
```

### Adding New Services

1. Update `SERVICE_ROUTES` in `api/routes.py`:
```python
SERVICE_ROUTES = {
    "new-service": "new-service-name",
    # ... existing routes
}
```

2. Add service URL to configuration:
```bash
# In .env or docker-compose
SERVICES={"new-service-name":"http://localhost:8013"}
```

### Middleware Order

Middleware is applied in this order (last added, first executed):

1. `SecurityHeadersMiddleware` - Security headers
2. `ErrorHandlingMiddleware` - Error handling
3. `LoggingMiddleware` - Request logging
4. `RateLimitMiddleware` - Rate limiting
5. `AuthenticationMiddleware` - Authentication
6. `RequestSizeMiddleware` - Request size validation
7. `MaintenanceModeMiddleware` - Maintenance mode
8. `APIVersionMiddleware` - API version validation

## Production Deployment

### Docker Production Build

```bash
# Build production image
docker build -t mams-api-gateway:latest .

# Run production container
docker run -d \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e SECRET_KEY=your-production-secret \
  -e REDIS_URL=redis://redis:6379/0 \
  mams-api-gateway:latest
```

### Production Considerations

1. **Environment Variables**: Use production values for secrets
2. **Health Checks**: Configure load balancer health checks
3. **Monitoring**: Set up Prometheus metrics collection
4. **Logging**: Configure log aggregation
5. **Security**: Enable HTTPS, proper CORS, security headers
6. **Scaling**: Use multiple instances behind load balancer
7. **Database**: Use production PostgreSQL with backups
8. **Redis**: Use Redis cluster for high availability

## Troubleshooting

### Common Issues

1. **Service Unavailable**: Check downstream service health
2. **Rate Limit Exceeded**: Verify Redis connection and configuration
3. **Authentication Failed**: Check JWT secret and token validity
4. **Connection Errors**: Verify service URLs and network connectivity

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

### Health Check Failures

Check service health and dependencies:

```bash
# Check Redis
docker exec -it mams-redis redis-cli ping

# Check PostgreSQL
docker exec -it mams-postgres psql -U mams_app -d mams_gateway -c "SELECT 1"

# Check service endpoints
curl http://localhost:8001/health  # user-management
curl http://localhost:8002/health  # asset-management
```

## Security

### Security Features

- JWT token validation with expiration
- API key authentication support
- Rate limiting per user/IP
- CORS configuration
- Security headers (CSP, XSS protection, etc.)
- Input validation and sanitization
- Request size limits
- Secure error handling (no sensitive data leakage)

### Security Best Practices

1. Use strong JWT secrets (32+ characters)
2. Configure proper CORS origins
3. Set appropriate rate limits
4. Use HTTPS in production
5. Regular security updates
6. Monitor authentication failures
7. Implement proper logging

## Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Ensure health checks pass
5. Test with multiple downstream services

## License

This project is part of the MAMS (Media Asset Management System) and is subject to the project's license terms.