# Geo-Replication Service Documentation

## Overview

The Geo-Replication Service manages cross-region data synchronization for the MAMS platform, ensuring data consistency, high availability, and disaster recovery capabilities across multiple geographic regions.

## Architecture

### Components

1. **Replication Manager**
   - Orchestrates all replication activities
   - Monitors region health
   - Handles conflict resolution
   - Manages replication jobs

2. **Region Connectors**
   - PostgreSQL for relational data
   - MongoDB for metadata
   - Redis for cache/session data
   - OpenSearch for search indices
   - S3 for media files

3. **Replication Types**
   - Database replication (CDC-based)
   - File replication (S3 cross-region)
   - Cache replication (Redis)
   - Search index replication (OpenSearch CCR)
   - Metadata replication (MongoDB change streams)

### Data Flow

```
Primary Region (us-east-1)
    ├── Database Changes ──────► CDC ──────► Secondary Regions
    ├── File Uploads ──────────► S3 ───────► Cross-Region Replication
    ├── Cache Updates ─────────► Redis ────► Async Replication
    ├── Search Updates ────────► OpenSearch ► Cross-Cluster Replication
    └── Metadata Changes ──────► MongoDB ───► Change Streams
```

## Configuration

### Environment Variables

```env
# Region Configuration
PRIMARY_REGION=us-east-1
SECONDARY_REGIONS=eu-west-1,ap-southeast-1
CURRENT_REGION=us-east-1

# Replication Settings
GEO_REPLICATION_ENABLED=true
REPLICATION_MODE=async
CONFLICT_RESOLUTION_STRATEGY=last_write_wins
MAX_REPLICATION_LAG_SECONDS=300

# Database Endpoints
PRIMARY_DB_URL=postgresql+asyncpg://user:pass@primary-db:5432/mams
EU_WEST_1_DB_URL=postgresql+asyncpg://user:pass@eu-db:5432/mams
AP_SOUTHEAST_1_DB_URL=postgresql+asyncpg://user:pass@ap-db:5432/mams

# Service Configuration
SERVICE_PORT=8015
LOG_LEVEL=INFO
```

### Replication Modes

1. **Async Mode** (Default)
   - Best performance
   - Eventual consistency
   - Suitable for most use cases

2. **Sync Mode**
   - Strong consistency
   - Higher latency
   - Use for critical data

3. **Semi-Sync Mode**
   - Balanced approach
   - Waits for at least one replica
   - Good compromise

### Conflict Resolution Strategies

1. **Last Write Wins** (Default)
   - Compares timestamps
   - Simple and effective
   - May lose concurrent updates

2. **Primary Wins**
   - Primary region always wins
   - Simple but may lose updates
   - Good for master-slave setups

3. **Version Vector**
   - Tracks version per region
   - Detects concurrent updates
   - Most accurate but complex

4. **Manual**
   - Logs conflicts for review
   - Human intervention required
   - Use for critical conflicts

## API Endpoints

### Status and Monitoring

```http
GET /api/v1/replication/status
```
Returns overall replication status including:
- Active/inactive regions
- Replication lag
- Pending jobs
- Health status

```http
GET /api/v1/replication/regions
```
Lists all configured regions with their current status.

```http
GET /api/v1/replication/metrics
```
Provides detailed replication metrics:
- Items processed/pending
- Bytes transferred
- Error rates
- Throughput

### Management

```http
POST /api/v1/replication/sync
```
Manually triggers data synchronization.

Request body:
```json
{
  "source_region": "us-east-1",
  "target_regions": ["eu-west-1"],
  "sync_type": "full",
  "force": false
}
```

```http
GET /api/v1/replication/jobs
```
Lists replication jobs with filtering options.

```http
GET /api/v1/replication/conflicts
```
Shows pending conflicts requiring resolution.

```http
POST /api/v1/replication/conflicts/{conflict_id}/resolve
```
Manually resolves a conflict.

### Failover

```http
POST /api/v1/replication/failover/{region_id}
```
Triggers failover for a specific region.

## Deployment

### Docker Deployment

```bash
# Build the image
docker build -t mams-geo-replication:latest .

# Run the service
docker run -d \
  --name geo-replication \
  -p 8015:8015 \
  -e PRIMARY_REGION=us-east-1 \
  -e SECONDARY_REGIONS=eu-west-1,ap-southeast-1 \
  mams-geo-replication:latest
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: geo-replication
  namespace: mams
spec:
  replicas: 2
  selector:
    matchLabels:
      app: geo-replication
  template:
    metadata:
      labels:
        app: geo-replication
    spec:
      containers:
      - name: geo-replication
        image: mams-geo-replication:latest
        ports:
        - containerPort: 8015
        env:
        - name: PRIMARY_REGION
          value: "us-east-1"
        - name: SECONDARY_REGIONS
          value: "eu-west-1,ap-southeast-1"
        livenessProbe:
          httpGet:
            path: /health
            port: 8015
          initialDelaySeconds: 30
          periodSeconds: 10
```

## Monitoring

### Key Metrics

1. **Replication Lag**
   - Target: < 60 seconds
   - Alert threshold: > 300 seconds
   - Critical: > 900 seconds

2. **Error Rate**
   - Target: < 0.1%
   - Alert threshold: > 1%
   - Critical: > 5%

3. **Throughput**
   - Monitor MB/s per region
   - Check for bottlenecks
   - Optimize batch sizes

### Prometheus Queries

```promql
# Average replication lag
avg(replication_lag_seconds) by (target_region)

# Error rate by type
rate(replication_errors_total[5m]) by (replication_type)

# Pending items
sum(replication_items_pending) by (region)
```

### Alerting Rules

```yaml
groups:
  - name: replication_alerts
    rules:
      - alert: HighReplicationLag
        expr: replication_lag_seconds > 300
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High replication lag detected"
          
      - alert: ReplicationFailure
        expr: rate(replication_errors_total[5m]) > 0.01
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Replication errors exceeding threshold"
```

## Troubleshooting

### Common Issues

1. **High Replication Lag**
   - Check network bandwidth
   - Verify region connectivity
   - Review batch sizes
   - Check for large transactions

2. **Replication Errors**
   - Check credentials
   - Verify endpoints
   - Review error logs
   - Check storage space

3. **Conflicts**
   - Review conflict resolution strategy
   - Check for clock skew
   - Verify application logic
   - Consider manual resolution

### Debug Commands

```bash
# Check replication status
curl http://localhost:8015/api/v1/replication/status

# Force sync a region
curl -X POST http://localhost:8015/api/v1/replication/sync \
  -H "Content-Type: application/json" \
  -d '{"source_region": "us-east-1", "target_regions": ["eu-west-1"], "sync_type": "full"}'

# Check specific region health
curl http://localhost:8015/api/v1/replication/regions/eu-west-1/health-check
```

## Best Practices

1. **Data Consistency**
   - Use appropriate replication mode
   - Monitor lag closely
   - Handle conflicts properly
   - Test failover regularly

2. **Performance**
   - Optimize batch sizes
   - Use compression
   - Monitor bandwidth usage
   - Implement rate limiting

3. **Security**
   - Encrypt data in transit
   - Use secure connections
   - Rotate credentials
   - Audit access logs

4. **Disaster Recovery**
   - Regular backup verification
   - Document failover procedures
   - Test recovery time
   - Monitor RPO/RTO

## Integration

### With Other Services

1. **Asset Management Service**
   - Replicates asset metadata
   - Ensures file availability
   - Handles version conflicts

2. **Search Engine Service**
   - Replicates search indices
   - Maintains query consistency
   - Handles relevance tuning

3. **User Management Service**
   - Replicates user sessions
   - Syncs permissions
   - Handles authentication

### Event Notifications

The service publishes events for:
- Replication started/completed
- Conflicts detected
- Failover initiated
- Region status changes

Subscribe to these events for automated workflows.

## Maintenance

### Regular Tasks

1. **Weekly**
   - Review replication metrics
   - Check for pending conflicts
   - Verify backup integrity

2. **Monthly**
   - Test failover procedures
   - Review and optimize queries
   - Update documentation

3. **Quarterly**
   - Performance tuning
   - Capacity planning
   - Security audit

### Upgrade Procedures

1. Rolling upgrade supported
2. Test in staging first
3. Monitor metrics during upgrade
4. Have rollback plan ready

## Support

For issues or questions:
1. Check service logs
2. Review metrics dashboard
3. Consult troubleshooting guide
4. Contact DevOps team