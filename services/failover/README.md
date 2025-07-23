# Region Failover Service

Automatic and manual region failover management for MAMS platform with zero-downtime deployment capabilities.

## Overview

The Failover service provides comprehensive region failover management with health monitoring, automatic failover, and data consistency checking to ensure high availability and disaster recovery.

## Features

### Health Monitoring
- **Continuous Health Checks**: Monitor all regions and services every 30 seconds
- **Service-Level Monitoring**: Track individual service health across regions
- **Database Health Checks**: Monitor PostgreSQL, MongoDB, Redis, and OpenSearch
- **Configurable Thresholds**: Customizable failure thresholds before triggering failover

### Failover Capabilities
- **Automatic Failover**: Detect failures and automatically failover to healthy regions
- **Manual Failover**: Administrator-triggered failover for maintenance
- **Scheduled Failover**: Plan failovers during maintenance windows
- **Failback Support**: Automatic or manual failback to primary region

### Data Protection
- **RPO Monitoring**: Track Recovery Point Objective compliance
- **RTO Tracking**: Monitor Recovery Time Objective achievement
- **Data Consistency Checks**: Verify data consistency between regions
- **Zero Data Loss**: Ensure minimal data loss during failover

### Notifications & Alerting
- **Multi-Channel Alerts**: Email, Slack, Webhook, PagerDuty
- **Configurable Severity**: Critical, Warning, Info levels
- **Rate Limiting**: Prevent alert fatigue
- **Test Notifications**: Verify notification channels

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Health Monitor  │────▶│ Failover Engine │────▶│ Load Balancer   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        │
         ├── Service Checks      ├── Decision Logic      ├── Route53
         ├── Database Checks     ├── Execution Plans     ├── ALB/NLB
         └── Network Tests       └── Rollback Logic      └── CloudFront
```

## API Endpoints

### Status & Monitoring
- `GET /api/v1/failover/status` - Current failover status
- `GET /api/v1/failover/regions` - Region health status
- `GET /api/v1/failover/topology` - System topology view

### Failover Operations
- `POST /api/v1/failover/failover` - Trigger manual failover
- `POST /api/v1/failover/failback` - Return to primary region
- `POST /api/v1/failover/test-failover` - Test failover without execution

### Metrics & History
- `GET /api/v1/failover/history` - Failover event history
- `GET /api/v1/failover/metrics` - Failover metrics and statistics
- `GET /api/v1/failover/rpo-status` - RPO compliance status

### Configuration
- `GET /api/v1/failover/plans` - Available failover plans
- `PUT /api/v1/failover/configuration` - Update failover settings
- `POST /api/v1/failover/notifications/test` - Test notification channels

### Data Consistency
- `POST /api/v1/failover/consistency-check` - Check data consistency

## Configuration

### Environment Variables

```env
# Service Configuration
SERVICE_NAME=failover
SERVICE_PORT=8017
ENVIRONMENT=development

# Region Configuration
PRIMARY_REGION=us-east-1
SECONDARY_REGIONS=["us-west-2", "eu-west-1", "ap-southeast-1"]
CURRENT_REGION=us-east-1

# Failover Settings
HEALTH_CHECK_INTERVAL_SECONDS=30
HEALTH_CHECK_TIMEOUT_SECONDS=10
FAILOVER_THRESHOLD=3
FAILBACK_DELAY_MINUTES=30
AUTO_FAILOVER_ENABLED=true
AUTO_FAILBACK_ENABLED=true

# RPO/RTO Objectives
RPO_MINUTES=5
RTO_MINUTES=15

# Notifications
ENABLE_NOTIFICATIONS=true
NOTIFICATION_EMAILS=["ops@example.com"]
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
PAGERDUTY_INTEGRATION_KEY=xxx

# Load Balancer
LOAD_BALANCER_TYPE=weighted
REGION_WEIGHTS={"us-east-1": 0.4, "us-west-2": 0.3, "eu-west-1": 0.2, "ap-southeast-1": 0.1}

# Database URLs (per region)
DATABASE_ENDPOINTS={...}

# Redis State Management
REDIS_URL=redis://localhost:6379/1
```

## Usage Examples

### Manual Failover

```python
import httpx

# Trigger manual failover
response = httpx.post(
    "http://localhost:8017/api/v1/failover/failover",
    json={
        "target_region": "us-west-2",
        "reason": "Planned maintenance on primary region",
        "force": False,
        "maintenance_mode": True,
        "expected_duration_minutes": 60
    },
    headers={"Authorization": "Bearer token"}
)
```

### Test Failover

```python
# Test failover without execution
response = httpx.post(
    "http://localhost:8017/api/v1/failover/test-failover",
    params={
        "target_region": "us-west-2",
        "dry_run": True
    },
    headers={"Authorization": "Bearer token"}
)

# Review test results
print(response.json())
# {
#     "target_region": "us-west-2",
#     "target_health": {...},
#     "rpo_status": {...},
#     "estimated_downtime_minutes": 15,
#     "pre_checks_passed": true,
#     "recommendations": []
# }
```

### Monitor Region Health

```python
# Get all region health
response = httpx.get(
    "http://localhost:8017/api/v1/failover/regions",
    headers={"Authorization": "Bearer token"}
)

# Check specific region
response = httpx.get(
    "http://localhost:8017/api/v1/failover/regions?region=us-east-1",
    headers={"Authorization": "Bearer token"}
)
```

### Check Data Consistency

```python
# Run consistency check
response = httpx.post(
    "http://localhost:8017/api/v1/failover/consistency-check",
    json={
        "regions": ["us-east-1", "us-west-2"],
        "check_type": "full"  # full, incremental, sample
    },
    headers={"Authorization": "Bearer token"}
)
```

## Failover Process

### Automatic Failover Flow

1. **Detection Phase**
   - Health checks detect service failures
   - Consecutive failures exceed threshold
   - System evaluates failover candidates

2. **Decision Phase**
   - Select best target region based on:
     - Health status
     - Latency
     - Configured priority
   - Verify RPO compliance

3. **Execution Phase**
   - Update DNS records (Route53)
   - Reconfigure load balancers
   - Redirect traffic to target region
   - Update service configurations

4. **Verification Phase**
   - Verify all services healthy
   - Check data consistency
   - Confirm user access

5. **Notification Phase**
   - Send alerts to all channels
   - Log event for audit
   - Update metrics

### Manual Failover Process

1. **Pre-checks**
   - Verify target region health
   - Check replication lag
   - Validate network connectivity

2. **Approval** (if required)
   - Administrator reviews plan
   - Confirms execution

3. **Execution**
   - Same as automatic failover
   - With optional maintenance mode

4. **Post-checks**
   - Verify successful transition
   - Document any issues

## Health Check Configuration

### Service Health Checks

Each service is monitored with:
- HTTP health endpoint check
- Response time measurement
- Error rate tracking

### Database Health Checks

- **PostgreSQL**: Connection and query test
- **MongoDB**: Replica set status
- **Redis**: Ping and memory usage
- **OpenSearch**: Cluster health API

### Custom Health Checks

Add custom health checks:

```python
# In configuration
SERVICE_HEALTH_ENDPOINTS = {
    "custom_service": "http://custom-service:8080/health"
}
```

## Monitoring & Metrics

### Prometheus Metrics

- `failover_total` - Total failover events
- `failover_duration_seconds` - Failover execution time
- `failover_region_health_percentage` - Region health score
- `failover_rpo_status` - RPO compliance status
- `failover_service_availability` - Service availability by region

### Grafana Dashboards

Pre-built dashboards for:
- Region health overview
- Failover history
- RPO/RTO tracking
- Service availability
- Alert summary

## Security

### Authentication
- JWT-based authentication
- Role-based access control

### Permissions
- `failover.read` - View status and metrics
- `failover.execute` - Trigger failovers
- `failover.test` - Run failover tests
- `failover.admin` - Modify configuration

### Audit Trail
- All failover events logged
- User actions tracked
- Configuration changes recorded

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start service
python -m src.main
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_failover_manager.py -v
```

### Docker

```bash
# Build image
docker build -t mams-failover-service .

# Run container
docker run -p 8017:8017 --env-file .env mams-failover-service
```

## Troubleshooting

### Common Issues

1. **Failover not triggering**
   - Check `FAILOVER_THRESHOLD` setting
   - Verify `AUTO_FAILOVER_ENABLED` is true
   - Review health check logs

2. **False positive health checks**
   - Increase `HEALTH_CHECK_TIMEOUT_SECONDS`
   - Check network connectivity
   - Review service logs

3. **Slow failover execution**
   - Check DNS propagation time
   - Review load balancer update speed
   - Optimize service startup time

## Best Practices

1. **Regular Testing**
   - Test failover monthly
   - Verify all regions quarterly
   - Update runbooks regularly

2. **Monitoring**
   - Set up alerts for all regions
   - Monitor RPO compliance
   - Track failover metrics

3. **Documentation**
   - Document all custom configurations
   - Maintain region-specific runbooks
   - Keep contact lists updated

4. **Data Consistency**
   - Run consistency checks daily
   - Monitor replication lag
   - Test data recovery procedures