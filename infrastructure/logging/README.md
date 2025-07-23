# MAMS Log Aggregation System

This directory contains the complete log aggregation infrastructure for the MAMS (Media Asset Management System). The system provides centralized logging, monitoring, and alerting capabilities across all microservices.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   MAMS Services │ -> │ Log Shippers │ -> │   OpenSearch    │
│  (13 services)  │    │   (Multiple) │    │    Cluster      │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │                       │
                              v                       v
                       ┌─────────────┐        ┌─────────────┐
                       │  Logstash   │        │   Grafana   │
                       │ Processing  │        │ Dashboards  │
                       └─────────────┘        └─────────────┘
                              │                       │
                              v                       v
                       ┌─────────────┐        ┌─────────────┐
                       │ Prometheus  │        │ AlertManager│
                       │   Metrics   │        │   Alerts    │
                       └─────────────┘        └─────────────┘
```

## Components

### Log Shippers
- **Filebeat**: Lightweight log forwarder for Docker containers and system logs
- **Vector**: High-performance log collector with advanced routing and processing
- **Fluentd**: Unified logging layer with plugin ecosystem

### Log Processing
- **Logstash**: Centralized log processing with parsing, enrichment, and routing
- **Vector**: Alternative high-performance processing pipeline

### Storage & Search
- **OpenSearch**: Distributed search and analytics engine (Elasticsearch fork)
- **OpenSearch Dashboards**: Web interface for log exploration and visualization

### Monitoring & Alerting
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and management
- **Jaeger**: Distributed tracing (optional)

## Quick Start

1. **Start the logging stack:**
   ```bash
   docker-compose -f docker-compose.logging.yml up -d
   ```

2. **Verify services are running:**
   ```bash
   docker-compose -f docker-compose.logging.yml ps
   ```

3. **Access web interfaces:**
   - OpenSearch Dashboards: http://localhost:5601
   - Grafana: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090
   - AlertManager: http://localhost:9093

## Service Configuration

### MAMS Services Integration

Each MAMS service should use the standardized logging configuration:

```python
from shared.logging.python_logging import setup_fastapi_logging

# In your FastAPI service
app = FastAPI()
setup_fastapi_logging(app, "asset-management")  # Replace with your service name
```

### Environment Variables

Set these environment variables in your services:

```env
SERVICE_NAME=asset-management
ENVIRONMENT=development
CLUSTER_NAME=mams-dev
LOG_LEVEL=INFO
```

## Log Structure

All logs follow a standardized JSON structure:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "service_name": "asset-management",
  "message": "Asset created successfully",
  "request_id": "req_123456",
  "user_id": "user_789",
  "trace_id": "trace_abc123",
  "execution_time": 0.045,
  "hostname": "mams-asset-001",
  "environment": "development",
  "cluster": "mams-dev"
}
```

## Index Strategy

Logs are automatically routed to different OpenSearch indices:

- `mams-logs-YYYY.MM.DD`: General application logs
- `mams-errors-YYYY.MM.DD`: Error and critical logs
- `mams-metrics-YYYY.MM.DD`: Performance and metrics logs
- `mams-security-YYYY.MM.DD`: Security and audit logs

## Lifecycle Management

Indices are automatically managed with the following lifecycle:

- **Hot phase**: 0-7 days (fast storage, full indexing)
- **Warm phase**: 7-30 days (merge segments, reduce replicas)
- **Cold phase**: 30-90 days (move to cold storage)
- **Delete phase**: 90+ days (automatic deletion)

## Alerting Rules

The system includes pre-configured alerts for:

### Service Health
- Service availability
- High error rates
- High response times
- Database connection issues

### Infrastructure
- High CPU/memory usage
- Disk space warnings
- OpenSearch cluster health
- Log ingestion failures

### Business Metrics
- Asset upload failures
- Search performance issues
- Workflow processing delays

## Configuration Files

### Main Configuration
- `docker-compose.logging.yml`: Complete logging stack
- `logstash/pipeline/mams.conf`: Log processing pipeline
- `vector/config/vector.toml`: Alternative processing pipeline

### Service Configurations
- `opensearch/config/opensearch.yml`: Search engine settings
- `prometheus/config/prometheus.yml`: Metrics collection
- `grafana/provisioning/`: Dashboard and datasource config
- `alertmanager/config/alertmanager.yml`: Alert routing

### Templates and Policies
- `opensearch/index-templates/`: Index mapping templates
- `opensearch/lifecycle-policies/`: Automatic index management
- `prometheus/rules/`: Alerting and recording rules

## Security

### Authentication
- OpenSearch: Basic auth (admin/OpenSearch123!)
- Grafana: Local admin account (admin/admin)
- Prometheus: No authentication (internal network only)

### TLS/SSL
- OpenSearch: Self-signed certificates enabled
- All internal communication over encrypted channels
- External access through reverse proxy recommended

### Data Privacy
- Automatic anonymization of sensitive fields (passwords, API keys)
- User data handling compliant with GDPR requirements
- Audit trail for all access and modifications

## Performance Tuning

### OpenSearch Optimization
```yaml
# High-throughput ingestion settings
index.refresh_interval: 30s
index.translog.durability: async
index.translog.sync_interval: 30s
indices.breaker.total.limit: 70%
```

### Logstash Tuning
```yaml
# Processing optimization
pipeline.workers: 4
pipeline.batch.size: 1000
queue.type: persisted
queue.max_bytes: 4gb
```

### Vector Performance
```toml
# High-performance settings
[sinks.opensearch_main.batch]
max_events = 1000
timeout_secs = 5
```

## Monitoring the Monitoring

### Health Checks
All services include health check endpoints:
- OpenSearch: `GET /_cluster/health`
- Logstash: `GET :9600/_node/stats`
- Vector: `GET :8080/health`
- Prometheus: `GET :9090/-/healthy`

### Self-Monitoring
The logging system monitors itself:
- Log ingestion rates and latencies
- Search performance metrics
- Alert delivery status
- Storage utilization

## Troubleshooting

### Common Issues

1. **Logs not appearing in OpenSearch**
   - Check Logstash processing: `curl http://localhost:9600/_node/stats`
   - Verify index creation: `curl -u admin:OpenSearch123! https://localhost:9200/_cat/indices`
   - Check for parsing errors in Logstash logs

2. **High memory usage**
   - Tune OpenSearch heap size: `-Xms2g -Xmx2g`
   - Adjust Logstash batch sizes
   - Configure index lifecycle management

3. **Missing alerts**
   - Verify AlertManager configuration
   - Check Prometheus rule evaluation
   - Test notification channels

### Debugging Commands

```bash
# Check log flow
docker-compose -f docker-compose.logging.yml logs -f logstash

# OpenSearch cluster status
curl -u admin:OpenSearch123! https://localhost:9200/_cluster/health?pretty

# Prometheus targets
curl http://localhost:9090/api/v1/targets

# Vector metrics
curl http://localhost:8080/metrics
```

## Development vs Production

### Development Setup
- Single-node OpenSearch cluster
- No authentication for internal services
- Debug logging enabled
- Local storage volumes

### Production Considerations
- Multi-node OpenSearch cluster with proper discovery
- Full authentication and authorization
- TLS certificates from proper CA
- Persistent storage with backup strategies
- Resource limits and monitoring
- Network security and firewall rules

## Integration Examples

### FastAPI Service
```python
from shared.logging.python_logging import setup_fastapi_logging, LogContext, log_performance

app = FastAPI()
setup_fastapi_logging(app, "my-service")

@app.post("/assets")
@log_performance
async def create_asset(asset_data: AssetCreate, current_user: User = Depends(get_current_user)):
    with LogContext(user_id=current_user.id):
        logger = get_logger(__name__)
        logger.info("Creating new asset", extra={"asset_type": asset_data.type})
        # ... asset creation logic
```

### Security Logging
```python
from shared.logging.python_logging import log_security_event

# Log authentication attempts
log_security_event(
    event_type="authentication",
    user_id=user.id,
    ip_address=request.client.host,
    action="login",
    success=True
)
```

## Maintenance

### Regular Tasks
- Monitor index growth and lifecycle transitions
- Review and update alerting rules
- Backup OpenSearch configuration and data
- Update log retention policies as needed
- Review and rotate authentication credentials

### Scaling
- Add OpenSearch nodes for increased capacity
- Scale Logstash workers for higher throughput
- Implement log sampling for high-volume services
- Consider cold storage for long-term retention

---

For more information on specific components, refer to their respective configuration files and the official documentation.