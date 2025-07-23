# MAMS API Gateway - Deployment Guide

This guide provides comprehensive instructions for deploying the MAMS API Gateway service in different environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Production Deployment](#production-deployment)
6. [Configuration Management](#configuration-management)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Security Considerations](#security-considerations)
9. [Troubleshooting](#troubleshooting)
10. [Backup and Recovery](#backup-and-recovery)

## Prerequisites

### System Requirements

- **CPU**: 2+ cores (4+ recommended for production)
- **RAM**: 4GB minimum (8GB+ recommended for production)
- **Storage**: 20GB minimum (SSD recommended)
- **Network**: 1Gbps network interface

### Software Dependencies

- **Docker**: 20.10+ or compatible container runtime
- **Docker Compose**: 2.0+ (for local development)
- **Kubernetes**: 1.24+ (for production deployment)
- **Python**: 3.11+ (for local development)
- **Redis**: 6.0+ (for rate limiting and caching)
- **PostgreSQL**: 15+ (for gateway metadata)

### External Services

- **Service Discovery**: Consul, Eureka, or Kubernetes DNS
- **Load Balancer**: HAProxy, NGINX, or cloud provider LB
- **Monitoring**: Prometheus, Grafana
- **Logging**: ELK Stack or similar

## Environment Setup

### Development Environment

```bash
# Clone the repository
git clone https://github.com/your-org/mams-api-gateway.git
cd mams-api-gateway

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Edit environment variables
nano .env
```

### Environment Variables

Create a `.env` file with the following configuration:

```env
# Application Settings
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here-32-characters-minimum
HOST=0.0.0.0
PORT=8000

# Database Configuration
DATABASE_URL=postgresql://mams_app:password@localhost:5432/mams_gateway

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Service Discovery
SERVICE_DISCOVERY_URL=http://localhost:8500

# Downstream Services
SERVICES={"user-management":"http://localhost:8001","asset-management":"http://localhost:8002"}

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_BURST=20

# Security
JWT_EXPIRATION_MINUTES=60
REFRESH_TOKEN_EXPIRATION_DAYS=30

# OpenAPI Documentation
OPENAPI_ENABLED=true
DOCS_URL=/docs
REDOC_URL=/redoc

# Logging
LOG_LEVEL=INFO
ENABLE_METRICS=true

# Health Checks
HEALTH_CHECK_TIMEOUT=5
HEALTH_CHECK_INTERVAL=30
```

## Docker Deployment

### Single Container Deployment

```bash
# Build the Docker image
docker build -t mams-api-gateway:latest .

# Run the container
docker run -d \
  --name mams-api-gateway \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e SECRET_KEY=your-production-secret-key \
  -e DATABASE_URL=postgresql://user:pass@db:5432/mams_gateway \
  -e REDIS_URL=redis://redis:6379/0 \
  --restart unless-stopped \
  mams-api-gateway:latest
```

### Docker Compose Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api-gateway:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql://mams_app:${DB_PASSWORD}@postgres:5432/mams_gateway
      - REDIS_URL=redis://redis:6379/0
      - SERVICE_DISCOVERY_URL=http://consul:8500
    depends_on:
      - postgres
      - redis
      - consul
    restart: unless-stopped
    networks:
      - mams-network

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=mams_gateway
      - POSTGRES_USER=mams_app
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - mams-network

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - mams-network

  consul:
    image: consul:1.15
    ports:
      - "8500:8500"
    command: consul agent -dev -client=0.0.0.0
    restart: unless-stopped
    networks:
      - mams-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api-gateway
    restart: unless-stopped
    networks:
      - mams-network

volumes:
  postgres_data:
  redis_data:

networks:
  mams-network:
    driver: bridge
```

### NGINX Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream api_gateway {
        server api-gateway:8000;
    }

    server {
        listen 80;
        server_name api.mams.example.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name api.mams.example.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        client_max_body_size 100M;

        location / {
            proxy_pass http://api_gateway;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 60s;
            proxy_read_timeout 60s;
            proxy_send_timeout 60s;
        }

        location /health {
            proxy_pass http://api_gateway/health;
            access_log off;
        }
    }
}
```

### Deployment Commands

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api-gateway

# Scale API Gateway
docker-compose up -d --scale api-gateway=3

# Stop services
docker-compose down

# Remove volumes (data will be lost)
docker-compose down -v
```

## Kubernetes Deployment

### Namespace and ConfigMap

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mams
  labels:
    name: mams
---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-gateway-config
  namespace: mams
data:
  ENVIRONMENT: "production"
  HOST: "0.0.0.0"
  PORT: "8000"
  LOG_LEVEL: "INFO"
  ENABLE_METRICS: "true"
  OPENAPI_ENABLED: "true"
  DOCS_URL: "/docs"
  REDOC_URL: "/redoc"
  RATE_LIMIT_REQUESTS: "1000"
  RATE_LIMIT_WINDOW: "60"
  HEALTH_CHECK_TIMEOUT: "5"
  HEALTH_CHECK_INTERVAL: "30"
```

### Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-gateway-secrets
  namespace: mams
type: Opaque
data:
  SECRET_KEY: <base64-encoded-secret-key>
  DATABASE_URL: <base64-encoded-database-url>
  REDIS_URL: <base64-encoded-redis-url>
```

### Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: mams
  labels:
    app: api-gateway
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
        image: mams-api-gateway:latest
        ports:
        - containerPort: 8000
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: api-gateway-secrets
              key: SECRET_KEY
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: api-gateway-secrets
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: api-gateway-secrets
              key: REDIS_URL
        envFrom:
        - configMapRef:
            name: api-gateway-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: api-gateway-config
```

### Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-service
  namespace: mams
  labels:
    app: api-gateway
spec:
  selector:
    app: api-gateway
  ports:
  - name: http
    port: 80
    targetPort: 8000
    protocol: TCP
  type: ClusterIP
```

### Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-gateway-ingress
  namespace: mams
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.mams.example.com
    secretName: api-gateway-tls
  rules:
  - host: api.mams.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-gateway-service
            port:
              number: 80
```

### HorizontalPodAutoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
  namespace: mams
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Deployment Commands

```bash
# Apply all configurations
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml

# Check deployment status
kubectl get pods -n mams
kubectl get services -n mams
kubectl get ingress -n mams

# View logs
kubectl logs -f deployment/api-gateway -n mams

# Scale deployment
kubectl scale deployment api-gateway --replicas=5 -n mams

# Rolling update
kubectl set image deployment/api-gateway api-gateway=mams-api-gateway:v2.0.0 -n mams
```

## Production Deployment

### High Availability Setup

```yaml
# Redis Cluster Configuration
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cluster
  namespace: mams
spec:
  serviceName: redis-cluster
  replicas: 6
  selector:
    matchLabels:
      app: redis-cluster
  template:
    metadata:
      labels:
        app: redis-cluster
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        - containerPort: 16379
        command:
        - redis-server
        - /etc/redis/redis.conf
        - --cluster-enabled
        - "yes"
        - --cluster-config-file
        - /data/nodes.conf
        - --cluster-node-timeout
        - "5000"
        - --appendonly
        - "yes"
        volumeMounts:
        - name: redis-data
          mountPath: /data
        - name: redis-config
          mountPath: /etc/redis
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

### Database Configuration

```yaml
# PostgreSQL StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: mams
spec:
  serviceName: postgres
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: "mams_gateway"
        - name: POSTGRES_USER
          value: "mams_app"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: password
        - name: POSTGRES_REPLICATION_USER
          value: "replicator"
        - name: POSTGRES_REPLICATION_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: replication-password
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
        - name: postgres-config
          mountPath: /etc/postgresql
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
```

### Load Balancer Configuration

```yaml
# Load Balancer Service
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-lb
  namespace: mams
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: http
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-path: /health
spec:
  type: LoadBalancer
  selector:
    app: api-gateway
  ports:
  - name: http
    port: 80
    targetPort: 8000
  - name: https
    port: 443
    targetPort: 8000
```

### Monitoring Setup

```yaml
# Prometheus ServiceMonitor
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: api-gateway-metrics
  namespace: mams
spec:
  selector:
    matchLabels:
      app: api-gateway
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

## Configuration Management

### Environment-Specific Configurations

#### Development
```env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
RATE_LIMIT_REQUESTS=1000
CORS_ORIGINS=*
OPENAPI_ENABLED=true
```

#### Staging
```env
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
RATE_LIMIT_REQUESTS=500
CORS_ORIGINS=https://staging.mams.example.com
OPENAPI_ENABLED=true
```

#### Production
```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
RATE_LIMIT_REQUESTS=100
CORS_ORIGINS=https://mams.example.com
OPENAPI_ENABLED=false
```

### Configuration Validation

```bash
# Validate configuration
python -c "
from core.config import get_settings
settings = get_settings()
print('Configuration valid')
print(f'Environment: {settings.environment}')
print(f'Debug: {settings.debug}')
print(f'Services: {list(settings.services.keys())}')
"
```

## Monitoring and Logging

### Prometheus Metrics

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'api-gateway'
    static_configs:
      - targets: ['api-gateway:9090']
    metrics_path: /metrics
    scrape_interval: 30s
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "MAMS API Gateway",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_seconds_bucket)",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ]
      }
    ]
  }
}
```

### Log Aggregation

```yaml
# Fluentd DaemonSet
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
  namespace: mams
spec:
  selector:
    matchLabels:
      name: fluentd
  template:
    metadata:
      labels:
        name: fluentd
    spec:
      containers:
      - name: fluentd
        image: fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch
        env:
        - name: FLUENT_ELASTICSEARCH_HOST
          value: "elasticsearch.logging.svc.cluster.local"
        - name: FLUENT_ELASTICSEARCH_PORT
          value: "9200"
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
```

## Security Considerations

### SSL/TLS Configuration

```bash
# Generate SSL certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=api.mams.example.com"

# Create Kubernetes TLS secret
kubectl create secret tls api-gateway-tls \
  --cert=cert.pem \
  --key=key.pem \
  -n mams
```

### Security Headers

The API Gateway automatically adds security headers:

```python
# Configured in SecurityHeadersMiddleware
{
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}
```

### IP Whitelisting

```env
# Enable IP whitelisting
IP_WHITELIST_ENABLED=true
IP_WHITELIST_MODE=whitelist
IP_WHITELIST_ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8
IP_WHITELIST_ADMIN_IPS=192.168.1.100,10.0.0.1
```

### Rate Limiting

```env
# Rate limiting configuration
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_BURST=20
```

## Troubleshooting

### Common Issues

#### 1. Service Discovery Issues

```bash
# Check service registration
curl http://consul:8500/v1/catalog/services

# Manual service registration
curl -X PUT http://consul:8500/v1/agent/service/register \
  -d '{
    "ID": "api-gateway-1",
    "Name": "api-gateway",
    "Address": "192.168.1.100",
    "Port": 8000,
    "Check": {
      "HTTP": "http://192.168.1.100:8000/health",
      "Interval": "10s"
    }
  }'
```

#### 2. Database Connection Issues

```bash
# Test database connection
python -c "
import asyncio
import asyncpg
async def test():
    conn = await asyncpg.connect('postgresql://user:pass@host:5432/db')
    result = await conn.fetchrow('SELECT 1')
    print('Database connection OK')
    await conn.close()
asyncio.run(test())
"
```

#### 3. Redis Connection Issues

```bash
# Test Redis connection
redis-cli -h redis-host -p 6379 ping

# Check Redis cluster status
redis-cli -h redis-host -p 6379 cluster nodes
```

#### 4. High Memory Usage

```bash
# Check memory usage
kubectl top pods -n mams

# Adjust memory limits
kubectl patch deployment api-gateway -n mams -p '{"spec":{"template":{"spec":{"containers":[{"name":"api-gateway","resources":{"limits":{"memory":"2Gi"}}}]}}}}'
```

### Debugging Commands

```bash
# Check API Gateway logs
kubectl logs -f deployment/api-gateway -n mams

# Check specific pod logs
kubectl logs -f pod/api-gateway-xxx -n mams

# Execute commands in pod
kubectl exec -it pod/api-gateway-xxx -n mams -- /bin/bash

# Check service endpoints
kubectl get endpoints -n mams

# Check ingress status
kubectl describe ingress api-gateway-ingress -n mams

# Check HPA status
kubectl get hpa -n mams
```

### Performance Tuning

```yaml
# Optimized deployment configuration
spec:
  replicas: 5
  template:
    spec:
      containers:
      - name: api-gateway
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        env:
        - name: UVICORN_WORKERS
          value: "4"
        - name: UVICORN_WORKER_CLASS
          value: "uvicorn.workers.UvicornWorker"
        - name: REDIS_POOL_SIZE
          value: "50"
        - name: REQUEST_TIMEOUT
          value: "60"
```

## Backup and Recovery

### Database Backup

```bash
# Create database backup
kubectl exec -it postgres-0 -n mams -- pg_dump -U mams_app mams_gateway > backup.sql

# Restore database
kubectl exec -i postgres-0 -n mams -- psql -U mams_app mams_gateway < backup.sql
```

### Redis Backup

```bash
# Create Redis backup
kubectl exec -it redis-0 -n mams -- redis-cli BGSAVE

# Copy backup file
kubectl cp redis-0:/data/dump.rdb ./redis-backup.rdb -n mams
```

### Configuration Backup

```bash
# Backup all configurations
kubectl get configmaps -n mams -o yaml > configmaps-backup.yaml
kubectl get secrets -n mams -o yaml > secrets-backup.yaml
kubectl get deployments -n mams -o yaml > deployments-backup.yaml
```

### Disaster Recovery

```bash
# Restore from backup
kubectl apply -f configmaps-backup.yaml
kubectl apply -f secrets-backup.yaml
kubectl apply -f deployments-backup.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=api-gateway -n mams --timeout=300s

# Verify service health
kubectl get pods -n mams
curl https://api.mams.example.com/health
```

## Health Checks

### Endpoint Health Checks

```bash
# Basic health check
curl http://api.mams.example.com/health

# Detailed health check
curl http://api.mams.example.com/health/detailed

# Service status
curl http://api.mams.example.com/api/status
```

### Monitoring Health

```bash
# Check Prometheus metrics
curl http://api.mams.example.com/metrics

# Check service discovery
curl http://consul:8500/v1/health/service/api-gateway
```

## Scaling

### Horizontal Scaling

```bash
# Scale deployment
kubectl scale deployment api-gateway --replicas=10 -n mams

# Auto-scaling configuration
kubectl autoscale deployment api-gateway --cpu-percent=70 --min=2 --max=20 -n mams
```

### Vertical Scaling

```bash
# Update resource limits
kubectl patch deployment api-gateway -n mams -p '{"spec":{"template":{"spec":{"containers":[{"name":"api-gateway","resources":{"limits":{"memory":"4Gi","cpu":"2000m"}}}]}}}}'
```

This deployment guide provides comprehensive instructions for deploying the MAMS API Gateway in various environments. Follow the appropriate section based on your deployment target and requirements.