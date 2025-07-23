# Common Issues and Solutions

## Overview

This guide covers the most common issues encountered with MAMS and their solutions. Each issue includes symptoms, root causes, diagnostic steps, and resolution procedures.

## 🔴 Critical Issues

### 1. Service Not Starting

**Symptoms:**
- Service pods in `CrashLoopBackOff` or `Error` state
- Health checks failing
- Service unreachable

**Common Causes:**
- Database connection failure
- Missing environment variables
- Insufficient resources
- Configuration errors

**Diagnosis:**
```bash
# Check pod status
kubectl get pods -n mams-prod

# View pod logs
kubectl logs <pod-name> -n mams-prod

# Describe pod for events
kubectl describe pod <pod-name> -n mams-prod

# Check previous container logs
kubectl logs <pod-name> -n mams-prod --previous
```

**Solutions:**

1. **Database Connection Issues:**
```bash
# Test database connectivity
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql -h postgres-service -U mams_user -d mams_prod

# Check database service
kubectl get svc postgres-service -n mams-prod
kubectl get endpoints postgres-service -n mams-prod
```

2. **Missing Environment Variables:**
```bash
# Check ConfigMap
kubectl get configmap mams-config -n mams-prod -o yaml

# Check Secrets
kubectl get secret mams-secrets -n mams-prod -o yaml

# Verify environment in pod
kubectl exec <pod-name> -n mams-prod -- env | grep -E "(DATABASE|REDIS|JWT)"
```

3. **Resource Constraints:**
```yaml
# Update resource limits
kubectl edit deployment <service-name> -n mams-prod

# Increase limits
resources:
  requests:
    cpu: 1
    memory: 2Gi
  limits:
    cpu: 2
    memory: 4Gi
```

### 2. Upload Failures

**Symptoms:**
- Files fail to upload
- Upload times out
- "413 Request Entity Too Large" error

**Common Causes:**
- File size exceeds limit
- Storage quota exceeded
- Network timeouts
- Proxy body size limit

**Diagnosis:**
```bash
# Check upload logs
kubectl logs -f deployment/ingest-service -n mams-prod | grep -i error

# Check storage usage
kubectl exec deployment/storage-service -n mams-prod -- df -h

# Check ingress configuration
kubectl get ingress mams-ingress -n mams-prod -o yaml | grep body-size
```

**Solutions:**

1. **Increase Upload Limits:**
```yaml
# Update ingress annotation
metadata:
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "10000m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
```

2. **Service Configuration:**
```bash
# Update service environment
kubectl set env deployment/ingest-service -n mams-prod \
  MAX_UPLOAD_SIZE_GB=100 \
  UPLOAD_TIMEOUT_SECONDS=3600
```

3. **Storage Issues:**
```bash
# Check PVC usage
kubectl get pvc -n mams-prod
kubectl exec <storage-pod> -- df -h /data

# Expand PVC if needed
kubectl edit pvc storage-data -n mams-prod
# Update spec.resources.requests.storage
```

### 3. Search Not Working

**Symptoms:**
- Search returns no results
- Search timeouts
- Inconsistent search results

**Common Causes:**
- OpenSearch index issues
- Indexing backlog
- Query syntax errors
- Permission problems

**Diagnosis:**
```bash
# Check OpenSearch health
curl -XGET 'http://opensearch-service:9200/_cluster/health?pretty'

# Check indices
curl -XGET 'http://opensearch-service:9200/_cat/indices?v'

# View indexing queue
kubectl logs deployment/search-engine -n mams-prod | grep -i "index"
```

**Solutions:**

1. **Reindex Assets:**
```bash
# Trigger reindexing
curl -X POST http://api-gateway:8000/api/v1/admin/reindex \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Monitor progress
watch -n 5 'curl -s http://opensearch-service:9200/assets/_count | jq'
```

2. **Fix Index Mapping:**
```bash
# Delete and recreate index
curl -X DELETE http://opensearch-service:9200/assets

# Create with correct mapping
curl -X PUT http://opensearch-service:9200/assets \
  -H 'Content-Type: application/json' \
  -d @index-mapping.json
```

### 4. Authentication Failures

**Symptoms:**
- "401 Unauthorized" errors
- Token expired messages
- Login failures

**Common Causes:**
- JWT secret mismatch
- Token expiration
- Clock skew between services
- Redis session issues

**Diagnosis:**
```bash
# Check JWT configuration
kubectl get secret mams-secrets -n mams-prod -o jsonpath='{.data.JWT_SECRET_KEY}' | base64 -d

# Verify time sync
kubectl exec deployment/api-gateway -n mams-prod -- date
kubectl exec deployment/user-management -n mams-prod -- date

# Check Redis connectivity
kubectl exec deployment/api-gateway -n mams-prod -- redis-cli -h redis-service ping
```

**Solutions:**

1. **JWT Secret Sync:**
```bash
# Ensure all services have same JWT secret
kubectl rollout restart deployment -n mams-prod
```

2. **Fix Clock Skew:**
```bash
# Install NTP in containers or use host time
kubectl edit deployment <service> -n mams-prod

# Add to pod spec
spec:
  hostNetwork: true
  dnsPolicy: ClusterFirstWithHostNet
```

## 🟡 Performance Issues

### 5. Slow Response Times

**Symptoms:**
- API requests taking >5 seconds
- Timeouts on complex queries
- UI feels sluggish

**Common Causes:**
- Database query performance
- Insufficient caching
- Network latency
- Resource constraints

**Diagnosis:**
```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://api.mams.example.com/api/v1/assets

# Monitor slow queries
kubectl logs deployment/postgres -n mams-prod | grep -E "duration: [0-9]{4,}"

# Check cache hit rate
kubectl exec deployment/redis -n mams-prod -- redis-cli info stats | grep hit
```

**Solutions:**

1. **Database Optimization:**
```sql
-- Add missing indexes
CREATE INDEX idx_assets_created_at ON assets(created_at DESC);
CREATE INDEX idx_assets_project_id ON assets(project_id) WHERE deleted_at IS NULL;

-- Analyze tables
ANALYZE assets;
VACUUM ANALYZE assets;
```

2. **Increase Cache TTL:**
```python
# Update cache configuration
CACHE_TTL_SECONDS = 3600  # 1 hour
CACHE_MAX_ENTRIES = 10000
```

3. **Enable Connection Pooling:**
```yaml
# Update database URL
DATABASE_URL: "postgresql://user:pass@postgres:5432/mams?pool_size=20&max_overflow=40"
```

### 6. High Memory Usage

**Symptoms:**
- Pods getting OOMKilled
- Memory alerts firing
- Gradual performance degradation

**Common Causes:**
- Memory leaks
- Large file processing
- Insufficient garbage collection
- Cache unbounded growth

**Diagnosis:**
```bash
# Check memory usage
kubectl top pods -n mams-prod

# Memory usage over time
kubectl exec <pod> -n mams-prod -- cat /proc/meminfo

# Python memory profiling
kubectl exec <pod> -n mams-prod -- python -m tracemalloc
```

**Solutions:**

1. **Increase Memory Limits:**
```yaml
resources:
  limits:
    memory: 8Gi
```

2. **Fix Memory Leaks:**
```python
# Add garbage collection
import gc
gc.collect()

# Use context managers
async with aiohttp.ClientSession() as session:
    # requests
```

3. **Limit Cache Size:**
```python
# Redis memory limit
CONFIG SET maxmemory 2gb
CONFIG SET maxmemory-policy allkeys-lru
```

## 🟢 Configuration Issues

### 7. Storage Backend Unreachable

**Symptoms:**
- Asset downloads fail
- Upload to S3 fails
- "Storage not available" errors

**Common Causes:**
- S3 credentials invalid
- Network connectivity
- Bucket permissions
- Endpoint misconfiguration

**Diagnosis:**
```bash
# Test S3 connectivity
kubectl exec deployment/storage-service -n mams-prod -- \
  aws s3 ls s3://mams-assets --endpoint-url=$S3_ENDPOINT

# Check credentials
kubectl get secret mams-secrets -n mams-prod -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d
```

**Solutions:**

1. **Update S3 Credentials:**
```bash
kubectl create secret generic mams-secrets \
  --from-literal=AWS_ACCESS_KEY_ID=new-key \
  --from-literal=AWS_SECRET_ACCESS_KEY=new-secret \
  --dry-run=client -o yaml | kubectl apply -f -
```

2. **Fix Bucket Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::123456789:user/mams"},
    "Action": ["s3:*"],
    "Resource": ["arn:aws:s3:::mams-assets/*"]
  }]
}
```

### 8. Email Notifications Not Sending

**Symptoms:**
- Users not receiving emails
- Password reset not working
- Workflow notifications missing

**Common Causes:**
- SMTP configuration
- Firewall blocking
- Invalid credentials
- Rate limiting

**Diagnosis:**
```bash
# Test SMTP connection
kubectl exec deployment/notification-service -n mams-prod -- \
  python -c "import smtplib; s=smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); print('Connected')"

# Check logs
kubectl logs deployment/notification-service -n mams-prod | grep -i smtp
```

**Solutions:**

1. **Update SMTP Config:**
```bash
kubectl set env deployment/notification-service -n mams-prod \
  SMTP_HOST=smtp.sendgrid.net \
  SMTP_PORT=587 \
  SMTP_USERNAME=apikey \
  SMTP_PASSWORD=$SENDGRID_API_KEY
```

2. **Use Email Service:**
```python
# Switch to API-based email
EMAIL_PROVIDER = "sendgrid"  # or "ses", "mailgun"
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")
```

## 🔧 Data Issues

### 9. Data Corruption

**Symptoms:**
- Assets showing incorrect metadata
- Database constraint violations
- Inconsistent search results

**Common Causes:**
- Failed migrations
- Concurrent updates
- Replication lag
- Application bugs

**Diagnosis:**
```sql
-- Check constraint violations
SELECT conname, conrelid::regclass
FROM pg_constraint
WHERE NOT convalidated;

-- Find orphaned records
SELECT a.* FROM assets a
LEFT JOIN projects p ON a.project_id = p.id
WHERE p.id IS NULL AND a.project_id IS NOT NULL;
```

**Solutions:**

1. **Data Cleanup:**
```sql
-- Fix orphaned assets
UPDATE assets SET project_id = NULL
WHERE project_id NOT IN (SELECT id FROM projects);

-- Rebuild constraints
ALTER TABLE assets VALIDATE CONSTRAINT assets_project_id_fkey;
```

2. **Reindex Data:**
```bash
# Full reindex
python manage.py reindex --model=all --batch-size=1000
```

### 10. Migration Failures

**Symptoms:**
- Deployment fails with migration errors
- Schema version mismatch
- "Column already exists" errors

**Common Causes:**
- Migrations run out of order
- Manual schema changes
- Failed rollback
- Multiple deployments

**Diagnosis:**
```bash
# Check migration status
kubectl exec deployment/api-gateway -n mams-prod -- alembic current

# View migration history
kubectl exec deployment/api-gateway -n mams-prod -- alembic history
```

**Solutions:**

1. **Fix Migration State:**
```bash
# Mark migration as complete
kubectl exec deployment/api-gateway -n mams-prod -- \
  alembic stamp <revision>

# Downgrade and retry
kubectl exec deployment/api-gateway -n mams-prod -- \
  alembic downgrade -1
kubectl exec deployment/api-gateway -n mams-prod -- \
  alembic upgrade head
```

## 📊 Monitoring Issues

### 11. Metrics Not Showing

**Symptoms:**
- Grafana dashboards empty
- Prometheus targets down
- No metrics data

**Common Causes:**
- Service discovery issues
- Metrics endpoint not exposed
- Prometheus scrape config
- Network policies

**Diagnosis:**
```bash
# Check Prometheus targets
curl http://prometheus:9090/api/v1/targets

# Test metrics endpoint
kubectl exec deployment/api-gateway -n mams-prod -- curl localhost:8000/metrics
```

**Solutions:**

1. **Fix Service Discovery:**
```yaml
# Add prometheus annotations
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"
```

2. **Update Prometheus Config:**
```yaml
scrape_configs:
  - job_name: 'mams-services'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: ['mams-prod']
```

## 🚨 Emergency Procedures

### Complete System Down

1. **Check Infrastructure:**
```bash
# Verify cluster nodes
kubectl get nodes

# Check core services
kubectl get pods -n kube-system
```

2. **Restore from Backup:**
```bash
# Restore database
kubectl exec postgres-backup -n mams-prod -- \
  pg_restore -h postgres-service -U mams_user -d mams_prod /backup/latest.dump

# Restore files from S3
aws s3 sync s3://mams-backups/files /data/restore
```

3. **Emergency Contacts:**
- DevOps On-Call: +1-555-0911
- Database Admin: +1-555-0912
- Security Team: +1-555-0913

### Data Recovery

1. **Point-in-Time Recovery:**
```bash
# PostgreSQL PITR
pg_basebackup -h postgres-primary -D /recovery -Fp -Xs -P

# Restore to specific time
recovery_target_time = '2024-01-15 14:30:00'
```

2. **Asset Recovery:**
```bash
# Recover from S3 versioning
aws s3api list-object-versions --bucket mams-assets --prefix "assets/"

# Restore specific version
aws s3api get-object --bucket mams-assets --key "assets/file.mp4" \
  --version-id "abc123" restored-file.mp4
```

---

For more help:
- [FAQ](./faq.md)
- [Debug Guide](./debugging.md)
- [Support Resources](./support.md)
- Emergency Hotline: +1-555-0911