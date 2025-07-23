# Module 2: Technical Architecture Deep Dive

## Duration: 6 hours

## Learning Objectives
By the end of this module, trainees will be able to:
1. Understand the microservices architecture
2. Identify service dependencies and communication patterns
3. Explain data flow through the system
4. Troubleshoot service-level issues
5. Use monitoring and logging tools

## 1. Architecture Overview

### Microservices Design
```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                      │
├─────────────────────────────────────────────────────────────┤
│   Web App │ Mobile Apps │ Desktop Apps │ NLE Plugins       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       API Gateway                           │
│                   (Authentication & Routing)                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Microservices Layer                      │
├─────────────────────────────────────────────────────────────┤
│  User Mgmt │ Asset Mgmt │ Search │ Storage │ Workflow     │
│  Metadata  │ Ingest     │ Proxy  │ AI/ML   │ Rights       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                             │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL │ MongoDB │ OpenSearch │ Redis │ MinIO        │
└─────────────────────────────────────────────────────────────┘
```

### Key Principles
1. **Service Independence**: Each service can be deployed independently
2. **API-First**: All communication through well-defined APIs
3. **Fault Tolerance**: System continues despite individual failures
4. **Scalability**: Services scale based on demand
5. **Observability**: Comprehensive monitoring and logging

## 2. Service Deep Dive

### API Gateway Service
**Port**: 8000  
**Purpose**: Central entry point for all requests

**Key Functions**:
- Authentication and authorization
- Request routing
- Rate limiting
- Load balancing
- SSL termination

**Common Issues**:
- 502 Bad Gateway → Backend service down
- 429 Too Many Requests → Rate limit hit
- 401 Unauthorized → Token expired

**Troubleshooting**:
```bash
# Check service health
curl http://api-gateway:8000/health

# View logs
docker logs mams-api-gateway

# Check rate limits
curl http://api-gateway:8000/api/v1/rate-limit
```

### User Management Service
**Port**: 8001  
**Purpose**: Handle authentication and user operations

**Key Functions**:
- User registration/login
- Role-based access control (RBAC)
- Session management
- MFA support
- External auth (LDAP, SAML, OAuth)

**Database**: PostgreSQL - users, roles, permissions tables

**Common Issues**:
- Login failures → Check credentials, account status
- Permission denied → Verify user roles
- Session timeout → Check token expiration

**Troubleshooting**:
```sql
-- Check user status
SELECT email, status, last_login FROM users WHERE email = 'user@example.com';

-- View user roles
SELECT u.email, r.name FROM users u 
JOIN user_roles ur ON u.id = ur.user_id 
JOIN roles r ON ur.role_id = r.id;

-- Check failed login attempts
SELECT * FROM login_attempts WHERE email = 'user@example.com' ORDER BY created_at DESC;
```

### Storage Abstraction Service
**Port**: 8002  
**Purpose**: Unified interface for multiple storage backends

**Supported Backends**:
- Local filesystem
- AWS S3
- Azure Blob Storage
- Google Cloud Storage
- MinIO (development)

**Storage Tiers**:
- **Hot**: Frequently accessed (SSD)
- **Warm**: Occasional access (HDD)
- **Cold**: Rare access (Cloud)
- **Archive**: Long-term storage

**Common Issues**:
- Upload failures → Check quotas, permissions
- Slow downloads → Check tier placement
- Missing files → Verify storage backend

**Troubleshooting**:
```bash
# Check storage usage
curl http://storage:8002/api/v1/usage

# Test storage connectivity
curl http://storage:8002/api/v1/backends/health

# View storage logs
docker logs mams-storage-abstraction
```

### Asset Management Service
**Port**: 8004  
**Purpose**: Core asset CRUD operations

**Key Functions**:
- Asset creation and updates
- Version control
- Relationship management
- Project organization
- Bulk operations

**Database**: PostgreSQL - assets, versions, projects tables

**Common Issues**:
- Duplicate assets → Check deduplication settings
- Version conflicts → Review version history
- Missing metadata → Check extraction status

**Troubleshooting**:
```sql
-- Find asset by ID
SELECT * FROM assets WHERE id = 'asset-uuid';

-- Check asset versions
SELECT * FROM asset_versions WHERE asset_id = 'asset-uuid' ORDER BY version DESC;

-- View project assets
SELECT a.* FROM assets a 
JOIN project_assets pa ON a.id = pa.asset_id 
WHERE pa.project_id = 'project-uuid';
```

### Search Engine Service
**Port**: 8006  
**Purpose**: Full-text and advanced search capabilities

**Search Types**:
- Full-text search
- Metadata search
- Visual similarity
- Facial recognition
- Natural language

**Backend**: OpenSearch

**Common Issues**:
- No results → Check indexing status
- Slow searches → Optimize queries
- Stale results → Reindex required

**Troubleshooting**:
```bash
# Check OpenSearch health
curl http://opensearch:9200/_cluster/health

# View index status
curl http://opensearch:9200/_cat/indices?v

# Reindex specific asset
curl -X POST http://search:8006/api/v1/reindex/asset-uuid
```

## 3. Data Flow Patterns

### Asset Upload Flow
```
1. Client → API Gateway (auth check)
2. API Gateway → Storage Service (get upload URL)
3. Client → Storage (direct upload)
4. Storage → Asset Service (register asset)
5. Asset Service → Ingest Service (queue processing)
6. Ingest Service → Proxy Service (generate previews)
7. Proxy Service → Metadata Service (extract metadata)
8. Metadata Service → Search Service (index asset)
```

### Search Flow
```
1. Client → API Gateway (search request)
2. API Gateway → Search Service (query)
3. Search Service → OpenSearch (execute search)
4. Search Service → Asset Service (get details)
5. Asset Service → Storage Service (get URLs)
6. API Gateway → Client (results)
```

## 4. Monitoring & Observability

### Prometheus Metrics
Access: http://prometheus:9090

**Key Metrics**:
- `http_requests_total` - Request count by service
- `http_request_duration_seconds` - Response times
- `service_up` - Service availability
- `error_rate` - Error percentage

**Useful Queries**:
```promql
# Request rate by service
rate(http_requests_total[5m])

# 95th percentile response time
histogram_quantile(0.95, http_request_duration_seconds_bucket)

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Grafana Dashboards
Access: http://grafana:3000

**Available Dashboards**:
- System Overview
- Service Health
- Database Performance
- Storage Metrics
- User Activity

### Logging with ELK Stack

**Log Format**:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "ERROR",
  "service": "asset-management",
  "trace_id": "abc-123",
  "message": "Failed to process asset",
  "error": "Storage quota exceeded",
  "user_id": "user-123",
  "asset_id": "asset-456"
}
```

**Kibana Queries**:
```
# Find errors for specific service
service:"asset-management" AND level:"ERROR"

# Track user activity
user_id:"user-123" AND timestamp:[now-1h TO now]

# Find slow operations
duration:>5000
```

## 5. Service Communication

### Synchronous (HTTP/REST)
- Client to API Gateway
- API Gateway to services
- Service to service (when needed)

### Asynchronous (Message Queue)
- Asset processing jobs
- Email notifications
- Workflow triggers
- Background tasks

**RabbitMQ Queues**:
- `ingest.process` - New uploads
- `proxy.generate` - Proxy creation
- `workflow.execute` - Workflow tasks
- `notification.send` - Notifications

### Service Discovery
- Docker Compose: Service names
- Kubernetes: DNS-based
- Development: localhost:port

## 6. Troubleshooting Techniques

### Service Health Checks
```bash
# Check all services
for port in 8000 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8011; do
  echo "Checking port $port"
  curl -s http://localhost:$port/health | jq .
done
```

### Database Connectivity
```bash
# PostgreSQL
psql -h postgres -U mams_user -d mams_db -c "SELECT 1"

# MongoDB
mongosh mongodb://mongo:27017/mams --eval "db.stats()"

# Redis
redis-cli -h redis ping
```

### Log Analysis
```bash
# Tail logs across services
docker-compose logs -f --tail=100

# Search for errors
docker-compose logs | grep ERROR

# Service-specific logs
docker logs mams-asset-management --since 1h
```

### Performance Analysis
```bash
# CPU and memory usage
docker stats

# Network connections
docker exec mams-api-gateway netstat -an

# Database queries
docker exec mams-postgres pg_stat_activity
```

## 7. Common Issues & Solutions

### Issue: Service Won't Start
**Symptoms**: Container exits immediately  
**Causes**: 
- Database connection failure
- Missing environment variables
- Port conflicts

**Solution**:
1. Check logs: `docker logs <container>`
2. Verify environment: `docker exec <container> env`
3. Test connections: `nc -zv <host> <port>`

### Issue: Slow Performance
**Symptoms**: High response times  
**Causes**:
- Database queries
- Network latency
- Resource constraints

**Solution**:
1. Check metrics in Grafana
2. Analyze slow queries
3. Scale services if needed

### Issue: Data Inconsistency
**Symptoms**: Missing or wrong data  
**Causes**:
- Failed transactions
- Sync issues
- Cache problems

**Solution**:
1. Check service logs
2. Verify database state
3. Clear caches if needed

## Hands-On Exercises

### Exercise 1: Service Discovery (45 minutes)
1. List all running services
2. Check health of each service
3. View service configurations
4. Test inter-service communication

### Exercise 2: Log Analysis (45 minutes)
1. Generate test errors
2. Find errors in logs
3. Trace request flow
4. Create log queries

### Exercise 3: Monitoring (45 minutes)
1. Access Grafana dashboards
2. Create custom queries
3. Set up alerts
4. Export metrics

### Exercise 4: Troubleshooting (60 minutes)
1. Simulate service failure
2. Diagnose the issue
3. Implement fix
4. Verify resolution

## Knowledge Check

### Quiz Questions
1. What is the purpose of the API Gateway?
2. Which database stores user information?
3. Name three storage tiers and their use cases
4. How do services communicate asynchronously?
5. What tool is used for log aggregation?

### Practical Tasks
1. Draw the data flow for asset download
2. Write a Prometheus query for error rate
3. List steps to troubleshoot login failures
4. Explain how to scale a service

## Summary

In this module, you learned:
- Microservices architecture and principles
- Individual service responsibilities
- Data flow patterns
- Monitoring and logging tools
- Troubleshooting techniques

Next Module: [Common Issues and Solutions](./03-common-issues.md)