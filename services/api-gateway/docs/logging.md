# API Gateway Logging Guide

## Overview

The MAMS API Gateway implements a comprehensive logging system that provides:
- Request/response logging with body capture
- Correlation tracking across services
- Performance metrics collection
- Security audit logging
- Multiple output formats and destinations
- Real-time log aggregation

## Logging Architecture

### Components

1. **Enhanced Logging Module** (`enhanced_logging.py`)
   - Request/Response Logger
   - Performance Logger
   - Audit Logger
   - Log Aggregator
   - Sensitive Data Masker

2. **Enhanced Middleware** (`enhanced_middleware.py`)
   - Correlation ID Middleware
   - Enhanced Logging Middleware
   - Audit Logging Middleware
   - Metrics Middleware

3. **Log Formatters** (`log_formatters.py`)
   - JSON formatters
   - Elasticsearch formatter
   - CloudWatch formatter
   - Datadog formatter
   - Human-readable formatter

## Log Types

### 1. Request/Response Logs

Captures complete HTTP transaction details:

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "correlation_id": "7d793037-2d9d-4e5f-9e6b-3c4d3e2f1e0d",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "method": "POST",
  "path": "/api/v1/assets",
  "query_params": {"limit": "20"},
  "headers": {
    "content-type": "application/json",
    "authorization": "***MASKED***"
  },
  "body": {
    "name": "test.mp4",
    "tags": ["video", "demo"]
  },
  "user_id": "user123",
  "client": {
    "host": "192.168.1.100",
    "port": 54321
  },
  "response": {
    "status_code": 201,
    "response_time": 145.23,
    "headers": {
      "content-type": "application/json"
    },
    "body": {
      "id": "asset123",
      "name": "test.mp4"
    }
  }
}
```

### 2. Performance Metrics

Tracks request duration and other performance indicators:

```json
{
  "metric": "request_duration",
  "value": 0.145,
  "timestamp": "2024-01-15T10:30:45.123Z",
  "tags": {
    "method": "POST",
    "path": "/api/v1/assets",
    "status": "201"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 3. Audit Logs

Records security-relevant events:

```json
{
  "event_type": "auth.login",
  "user_id": "user123",
  "success": true,
  "method": "password",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 4. Service Call Logs

Tracks calls to downstream services:

```json
{
  "service_name": "asset-management",
  "method": "POST",
  "path": "/assets",
  "status_code": 201,
  "response_time": 0.089,
  "success": true,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Configuration

### Environment Variables

```env
# Logging levels
LOG_LEVEL=INFO
LOG_FORMAT=json

# Request/Response logging
LOG_REQUEST_BODY=true
LOG_RESPONSE_BODY=true
MAX_BODY_LOG_SIZE=10240

# Sensitive data masking
MASK_SENSITIVE_DATA=true

# Log destinations
LOG_TO_FILE=true
LOG_TO_STDOUT=true
LOG_FILE_PATH=/var/log/api-gateway/app.log
LOG_FILE_MAX_SIZE=104857600  # 100MB
LOG_FILE_BACKUP_COUNT=10

# External logging services
ELASTICSEARCH_URL=http://localhost:9200
CLOUDWATCH_LOG_GROUP=/aws/mams/api-gateway
DATADOG_API_KEY=your-datadog-api-key
```

### Logging Configuration in Code

```python
# In main.py or config.py
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "core.log_formatters.CompactJSONFormatter"
        },
        "human": {
            "()": "core.log_formatters.HumanReadableFormatter",
            "use_colors": True
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "human" if settings.debug else "json",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "logs/api-gateway.log",
            "maxBytes": 104857600,  # 100MB
            "backupCount": 10
        },
        "elasticsearch": {
            "class": "custom_handlers.ElasticsearchHandler",
            "level": "INFO",
            "formatter": "elasticsearch",
            "hosts": ["localhost:9200"],
            "index": "api-gateway"
        }
    },
    "loggers": {
        "api_gateway": {
            "level": "INFO",
            "handlers": ["console", "file", "elasticsearch"],
            "propagate": False
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

## Sensitive Data Masking

The system automatically masks sensitive data in logs:

### Masked Patterns
- Passwords
- Tokens (access_token, refresh_token)
- API keys
- Secrets
- Authorization headers
- Credit card numbers
- Social Security numbers
- Email addresses (partially masked)

### Example
```json
// Original
{
  "password": "secretpassword123",
  "api_key": "sk-1234567890abcdef",
  "email": "user@example.com"
}

// Masked
{
  "password": "***MASKED***",
  "api_key": "***MASKED***",
  "email": "u**r@example.com"
}
```

## Correlation Tracking

### Request Flow
```
Client Request
    ↓ (X-Correlation-ID: abc123)
API Gateway
    ↓ (X-Correlation-ID: abc123, X-Request-ID: def456)
Service A
    ↓ (X-Correlation-ID: abc123)
Service B
```

### Using Correlation IDs

```python
# In your service code
import structlog

logger = structlog.get_logger()

# Correlation ID is automatically bound to all logs
logger.info("Processing request", user_id=user_id, action="create_asset")
# Output includes correlation_id and request_id automatically
```

## Log Aggregation

### Real-time Metrics

The system aggregates logs in memory for real-time monitoring:

```python
# Aggregated data structure
{
  "request_counts": {
    "GET:/api/v1/assets": 1523,
    "POST:/api/v1/assets": 234
  },
  "error_counts": {
    "GET:/api/v1/assets:404": 12,
    "POST:/api/v1/assets:400": 5
  },
  "response_time_stats": {
    "GET:/api/v1/assets": {
      "count": 1523,
      "avg": 0.045,
      "min": 0.012,
      "max": 0.234
    }
  }
}
```

### Accessing Aggregated Data

```http
GET /api/v1/logs/aggregations
Authorization: Bearer <token>

Response:
{
  "request_counts": {...},
  "error_counts": {...},
  "response_time_stats": {...}
}
```

## Performance Metrics

### Available Metrics
- `request_duration` - Total request processing time
- `downstream_call_duration` - Time for downstream service calls
- `database_query_duration` - Database query execution time
- `cache_hit_rate` - Cache hit/miss ratio

### Viewing Metrics

```http
GET /api/v1/logs/metrics?metrics=request_duration,cache_hit_rate
Authorization: Bearer <token>

Response:
{
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
}
```

## Audit Logging

### Logged Events

1. **Authentication Events**
   - Login attempts (success/failure)
   - Logout
   - Token refresh
   - Password changes

2. **Authorization Events**
   - Permission checks
   - Access denied events
   - Role changes

3. **Data Access Events**
   - Sensitive data access
   - Data modifications
   - Bulk operations

### Audit Log Format

```json
{
  "event_type": "auth.login",
  "user_id": "user123",
  "success": true,
  "method": "password",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## External Log Destinations

### Elasticsearch/OpenSearch

```python
# Configure in log_formatters.py
formatter = ElasticsearchFormatter(
    index_name="api-gateway",
    doc_type="_doc"
)

# Logs are formatted for bulk indexing
```

### AWS CloudWatch

```python
# Configure for CloudWatch
formatter = CloudWatchFormatter()

# Supports CloudWatch Insights queries
fields @timestamp, @message, request_id, user_id, status_code
| filter status_code >= 400
| stats count() by bin(5m)
```

### Datadog

```python
# Configure for Datadog
formatter = DatadogFormatter()

# Includes APM trace correlation
```

## Log Management API

### Search Logs

```http
GET /api/v1/logs/search
  ?start_time=2024-01-15T00:00:00Z
  &end_time=2024-01-15T23:59:59Z
  &level=ERROR
  &user_id=user123
Authorization: Bearer <admin_token>
```

### Export Logs

```http
GET /api/v1/logs/export?format=csv&start_time=2024-01-15
Authorization: Bearer <admin_token>
```

### Update Log Level

```http
PUT /api/v1/logs/config/level?logger_name=api_gateway&level=DEBUG
Authorization: Bearer <admin_token>
```

## Best Practices

### 1. Structured Logging

Always use structured logging with consistent fields:

```python
logger.info(
    "Asset created",
    asset_id=asset.id,
    user_id=current_user.id,
    size_bytes=file_size,
    duration_ms=processing_time
)
```

### 2. Appropriate Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General operational information
- **WARNING**: Warning conditions that might need attention
- **ERROR**: Error conditions that prevented an operation
- **CRITICAL**: Critical conditions that require immediate attention

### 3. Performance Considerations

- Avoid logging large objects in hot paths
- Use sampling for high-frequency events
- Configure appropriate log rotation
- Use async logging handlers for external services

### 4. Security

- Always mask sensitive data
- Don't log passwords, tokens, or PII
- Use audit logs for compliance
- Implement log retention policies

### 5. Correlation

- Always propagate correlation IDs
- Use correlation IDs in error messages
- Include correlation IDs in external service calls

## Troubleshooting

### High Log Volume

1. Check log levels (reduce from DEBUG to INFO)
2. Enable sampling for high-frequency endpoints
3. Increase log rotation frequency
4. Use log aggregation instead of individual events

### Missing Logs

1. Check log level configuration
2. Verify handler configuration
3. Check disk space for file handlers
4. Verify network connectivity for external handlers

### Performance Impact

1. Use async logging handlers
2. Disable request/response body logging
3. Reduce logged fields
4. Use local buffering for external services

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Error Rate**
   ```
   errors_per_minute = count(level="ERROR") / time_window
   ```

2. **Response Time**
   ```
   p95_response_time = percentile(response_time, 95)
   ```

3. **Log Volume**
   ```
   logs_per_second = count(*) / time_window
   ```

### Alert Conditions

- Error rate > 1% of requests
- P95 response time > 1 second
- Any CRITICAL level logs
- Failed authentication attempts > 10 per minute
- Disk space for logs < 10%

## Integration Examples

### Grafana Dashboard

```json
{
  "dashboard": {
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(api_gateway_requests_total[5m])"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(api_gateway_errors_total[5m])"
        }]
      },
      {
        "title": "Response Time",
        "targets": [{
          "expr": "histogram_quantile(0.95, api_gateway_request_duration_seconds)"
        }]
      }
    ]
  }
}
```

### Elasticsearch Query

```json
GET /api-gateway-*/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"level": "ERROR"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  },
  "aggs": {
    "errors_by_endpoint": {
      "terms": {"field": "path.keyword"}
    }
  }
}
```