# MAMS Distributed Tracing System

This directory contains the complete distributed tracing infrastructure for the MAMS (Media Asset Management System). The system provides end-to-end request tracing, performance monitoring, and dependency mapping across all microservices.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   MAMS Services │ -> │ OTEL Collector│ -> │     Jaeger      │
│  (13 services)  │    │   (Gateway)   │    │   (Storage)     │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                       │                       │
         v                       v                       v
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Auto-Instrument│    │    Tempo     │    │  OpenSearch     │
│   (Libraries)   │    │ (Alternative)│    │   (Traces)      │
└─────────────────┘    └──────────────┘    └─────────────────┘
                                                   │
                                                   v
                                           ┌─────────────────┐
                                           │ Trace Analytics │
                                           │   Dashboard     │
                                           └─────────────────┘
```

## Components

### Trace Collection
- **OpenTelemetry Collector**: Central trace collection and processing gateway
- **Jaeger All-in-One**: Complete tracing backend (development)
- **Jaeger Agent/Collector/Query**: Distributed tracing components (production)
- **Grafana Tempo**: Alternative tracing backend with Prometheus integration

### Trace Storage
- **OpenSearch**: Primary trace storage with full-text search capabilities
- **Jaeger Native Storage**: High-performance trace storage
- **Local File Storage**: Development and testing storage

### Trace Analysis
- **Jaeger UI**: Interactive trace exploration and analysis
- **OpenSearch Dashboards**: Advanced trace analytics and visualization
- **Grafana**: Metrics correlation with traces

### Instrumentation
- **Auto-Instrumentation**: Automatic instrumentation for FastAPI, SQLAlchemy, Redis, etc.
- **Manual Instrumentation**: Custom spans and trace correlation
- **Propagation**: Context propagation across service boundaries

## Quick Start

1. **Start the tracing stack:**
   ```bash
   docker-compose -f docker-compose.tracing.yml up -d
   ```

2. **Setup OpenSearch indices and templates:**
   ```bash
   cd infrastructure/tracing
   python setup.py
   ```

3. **Access web interfaces:**
   - Jaeger UI: http://localhost:16686
   - OpenSearch Dashboards: http://localhost:5601
   - OpenTelemetry Collector: http://localhost:8888/metrics

## Service Integration

### FastAPI Service Setup

```python
from shared.tracing.python_tracing import setup_service_tracing

# Initialize FastAPI app
app = FastAPI()

# Setup complete tracing
tracer = setup_service_tracing(
    app=app,
    service_name="asset-management",
    service_version="1.0.0"
)

# Optional: Add trace correlation middleware
app.middleware("http")(trace_correlation_middleware)
```

### Manual Tracing

```python
from shared.tracing.python_tracing import trace_function, TracedOperation, MAMSSpanAttributes

# Decorator-based tracing
@trace_function(operation_name="process_asset")
async def process_asset(asset_id: str):
    # Function automatically traced
    pass

# Context manager tracing
async def upload_file(file_data: bytes):
    tracer = trace.get_tracer(__name__)
    
    with TracedOperation(tracer, "file_upload") as span:
        span.set_attribute(MAMSSpanAttributes.ASSET_TYPE, "video")
        span.set_attribute(MAMSSpanAttributes.USER_ID, user_id)
        
        # Upload logic here
        result = await storage.upload(file_data)
        
        span.set_attribute("file.size", len(file_data))
        return result
```

### Environment Variables

```env
# Service identification
SERVICE_NAME=asset-management
SERVICE_VERSION=1.0.0
ENVIRONMENT=development
CLUSTER_NAME=mams-dev

# Tracing endpoints
JAEGER_ENDPOINT=http://jaeger:14268/api/traces
OTLP_ENDPOINT=http://otel-collector:4317
OPENSEARCH_URL=https://opensearch-node1:9200

# Debugging
TRACING_DEBUG=false
OTEL_LOG_LEVEL=info
```

## Trace Data Structure

### Span Attributes

All MAMS traces include standardized attributes:

```json
{
  "traceId": "abc123...",
  "spanId": "def456...",
  "operationName": "POST /api/v1/assets",
  "startTime": 1642678800000000,
  "duration": 1234567,
  "tags": {
    // Standard attributes
    "service.name": "mams-asset-management",
    "service.version": "1.0.0",
    "http.method": "POST",
    "http.url": "/api/v1/assets",
    "http.status_code": 201,
    
    // MAMS-specific attributes
    "mams.user.id": "user_123",
    "mams.user.role": "editor",
    "mams.asset.id": "asset_456",
    "mams.asset.type": "video",
    "mams.execution_time": 1.234,
    "mams.service.type": "api"
  }
}
```

### Custom Span Attributes

```python
from shared.tracing.python_tracing import MAMSSpanAttributes

# Business context
span.set_attribute(MAMSSpanAttributes.USER_ID, user.id)
span.set_attribute(MAMSSpanAttributes.ASSET_ID, asset.id)
span.set_attribute(MAMSSpanAttributes.PROJECT_ID, project.id)
span.set_attribute(MAMSSpanAttributes.WORKFLOW_ID, workflow.id)

# Performance metrics
span.set_attribute(MAMSSpanAttributes.EXECUTION_TIME, duration)
span.set_attribute(MAMSSpanAttributes.QUEUE_TIME, queue_duration)
span.set_attribute(MAMSSpanAttributes.CACHE_HIT, True)

# Infrastructure context
span.set_attribute(MAMSSpanAttributes.STORAGE_BACKEND, "s3")
span.set_attribute(MAMSSpanAttributes.DATABASE_NAME, "mams_main")
```

## Configuration Profiles

### Development Profile
```bash
docker-compose -f docker-compose.tracing.yml up -d
```
- Jaeger All-in-One
- Console debugging enabled
- High sampling rate (100%)
- Local storage

### Production Profile
```bash
docker-compose -f docker-compose.tracing.yml --profile production up -d
```
- Separate Jaeger components
- OpenSearch storage
- Optimized sampling (10%)
- High availability setup

### Tempo Profile (Alternative)
```bash
docker-compose -f docker-compose.tracing.yml --profile tempo up -d
```
- Grafana Tempo backend
- Prometheus integration
- Compact storage format

## Sampling Configuration

### Tail Sampling (Recommended)

The OpenTelemetry Collector uses intelligent tail sampling:

```yaml
tail_sampling:
  policies:
    # Always sample errors
    - name: errors
      type: status_code
      status_code: [ERROR]
    
    # Sample 10% of successful requests
    - name: probabilistic
      type: probabilistic
      probabilistic:
        sampling_percentage: 10.0
    
    # Always sample slow requests (>2s)
    - name: high_latency
      type: latency
      latency:
        threshold_ms: 2000
    
    # Sample 100% of critical services
    - name: critical_services
      type: string_attribute
      string_attribute:
        key: service.name
        values: ["mams-user-management", "mams-api-gateway"]
```

### Head Sampling (Simple)

For development or low-volume environments:

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of traces
sampler = TraceIdRatioBased(0.1)
```

## Index Management

### Index Templates

Traces are stored using optimized index templates:

- **mams-jaeger-span-\***: Individual span data
- **mams-jaeger-service-\***: Service discovery data
- **mams-traces-\***: Consolidated trace data

### Lifecycle Policies

Automatic index lifecycle management:

1. **Hot phase** (0-3 days): Fast storage, active indexing
2. **Warm phase** (3-7 days): Reduced replicas, force merge
3. **Cold phase** (7-30 days): Cold storage, minimal resources
4. **Delete phase** (30+ days): Automatic deletion

### Index Aliases

Simplified querying through aliases:

- `mams-jaeger-spans`: All span indices
- `mams-jaeger-services`: All service indices
- `mams-traces`: All trace data

## Performance Monitoring

### Span Metrics

Automatically generated metrics from traces:

```
# Request rate
mams_request_rate_total{service="asset-management", operation="upload"}

# Latency histogram
mams_request_duration_seconds{service="asset-management", operation="upload"}

# Error rate
mams_error_rate_total{service="asset-management", operation="upload"}
```

### Service Map

Automatic service dependency mapping:

```
mams-api-gateway -> mams-asset-management -> mams-storage
                 -> mams-user-management -> postgres
```

## Query Examples

### Jaeger UI Queries

Find traces by:
```
service="mams-asset-management" operation="upload_asset"
duration>2s
error=true
mams.user.id="user_123"
```

### OpenSearch Queries

```json
{
  "query": {
    "bool": {
      "must": [
        {"term": {"process.serviceName": "mams-asset-management"}},
        {"range": {"duration": {"gte": 2000000}}},
        {"nested": {
          "path": "tags",
          "query": {
            "bool": {
              "must": [
                {"term": {"tags.key": "mams.user.id"}},
                {"term": {"tags.value": "user_123"}}
              ]
            }
          }
        }}
      ]
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **No traces appearing**
   - Check OpenTelemetry Collector logs: `docker logs mams-otel-collector`
   - Verify service instrumentation
   - Check sampling configuration

2. **High cardinality warnings**
   - Review span attributes
   - Implement attribute filtering
   - Adjust sampling rates

3. **Storage issues**
   - Monitor OpenSearch disk usage
   - Verify lifecycle policies
   - Check index template settings

### Debug Commands

```bash
# Check collector status
curl http://localhost:13133/health

# Check Jaeger health
curl http://localhost:16686/api/services

# Check OpenSearch indices
curl -u admin:OpenSearch123! -k https://localhost:9200/_cat/indices/mams-jaeger*

# View trace data
curl -u admin:OpenSearch123! -k https://localhost:9200/mams-jaeger-span-*/_search
```

## Integration with Other Systems

### Logging Correlation

Traces are automatically correlated with logs:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "message": "Asset uploaded successfully",
  "trace_id": "abc123...",
  "span_id": "def456...",
  "service_name": "asset-management"
}
```

### Metrics Correlation

Prometheus metrics include trace context:

```
http_requests_total{service="asset-management", trace_id="abc123"}
```

### Alert Integration

Traces can trigger alerts:

```yaml
- alert: HighLatencyTrace
  expr: trace_duration_seconds > 5
  labels:
    severity: warning
  annotations:
    summary: "High latency trace detected"
    trace_url: "http://jaeger:16686/trace/{{ $labels.trace_id }}"
```

## Security Considerations

### Data Sanitization

Sensitive data is automatically filtered:

```python
# Sensitive keys are removed
sensitive_keys = ['password', 'token', 'api_key', 'authorization']
```

### Access Control

- OpenSearch authentication required
- Service-to-service communication over internal networks
- TLS encryption for external access

### Data Retention

- Automatic data deletion after retention period
- GDPR-compliant data handling
- Audit trail for trace access

## Monitoring the Tracing System

### Health Checks

All components include health checks:

```bash
# OpenTelemetry Collector
GET http://localhost:13133/health

# Jaeger Query
GET http://localhost:16686/api/services

# OpenSearch
GET https://localhost:9200/_cluster/health
```

### Performance Metrics

Monitor tracing system performance:

```
# Collector metrics
otelcol_processor_batch_batch_send_size
otelcol_exporter_sent_spans_total
otelcol_receiver_accepted_spans_total

# Jaeger metrics
jaeger_collector_spans_received_total
jaeger_query_requests_total

# OpenSearch metrics
opensearch_indices_docs_count
opensearch_indices_store_size_bytes
```

---

For more information on specific components, refer to their respective configuration files and the official OpenTelemetry documentation.