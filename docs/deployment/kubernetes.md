# Kubernetes Deployment Guide

## Overview

This guide covers deploying MAMS on Kubernetes, including cluster setup, service deployment, scaling, and production considerations.

## Prerequisites

- Kubernetes cluster (1.28+)
- kubectl configured
- Helm 3.0+
- Container registry access
- Storage provisioner (for PVCs)
- Ingress controller (NGINX recommended)
- cert-manager (for TLS)

## Cluster Requirements

### Minimum Cluster Size
- **Nodes**: 3 worker nodes
- **CPU**: 8 vCPU per node
- **Memory**: 32GB per node
- **Storage**: 500GB SSD per node

### Recommended Production Size
- **Nodes**: 5+ worker nodes
- **CPU**: 16 vCPU per node
- **Memory**: 64GB per node
- **Storage**: 1TB NVMe SSD per node

## Namespace Setup

Create dedicated namespaces:

```bash
# Create namespaces
kubectl create namespace mams-prod
kubectl create namespace mams-storage
kubectl create namespace mams-monitoring

# Set default namespace
kubectl config set-context --current --namespace=mams-prod
```

## Storage Configuration

### Storage Classes

Create storage classes for different tiers:

```yaml
# storage-classes.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: mams-fast-ssd
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  iops: "10000"
  throughput: "250"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true

---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: mams-standard
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp2
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

Apply storage classes:
```bash
kubectl apply -f storage-classes.yaml
```

### Persistent Volume Claims

Create PVCs for databases and storage:

```yaml
# database-pvcs.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
  namespace: mams-prod
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: mams-fast-ssd
  resources:
    requests:
      storage: 500Gi

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mongodb-data
  namespace: mams-prod
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: mams-fast-ssd
  resources:
    requests:
      storage: 500Gi

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: opensearch-data
  namespace: mams-prod
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: mams-fast-ssd
  resources:
    requests:
      storage: 1Ti
```

## ConfigMaps and Secrets

### ConfigMap for Service Configuration

```yaml
# mams-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mams-config
  namespace: mams-prod
data:
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "production"
  
  # Database connections
  POSTGRES_HOST: "postgres-service"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "mams_prod"
  
  MONGODB_HOST: "mongodb-service"
  MONGODB_PORT: "27017"
  MONGODB_DB: "mams_metadata"
  
  OPENSEARCH_HOST: "opensearch-service"
  OPENSEARCH_PORT: "9200"
  
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  
  # Service discovery
  API_GATEWAY_URL: "http://api-gateway-service:8000"
  USER_SERVICE_URL: "http://user-management-service:8001"
  ASSET_SERVICE_URL: "http://asset-management-service:8004"
  STORAGE_SERVICE_URL: "http://storage-abstraction-service:8003"
```

### Secrets for Sensitive Data

```yaml
# mams-secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: mams-secrets
  namespace: mams-prod
type: Opaque
stringData:
  # Database credentials
  POSTGRES_USER: "mams_user"
  POSTGRES_PASSWORD: "your-secure-password"
  
  MONGODB_USER: "mams_user"
  MONGODB_PASSWORD: "your-secure-password"
  
  OPENSEARCH_USER: "admin"
  OPENSEARCH_PASSWORD: "your-secure-password"
  
  # JWT secrets
  JWT_SECRET_KEY: "your-very-long-random-secret-key"
  
  # S3 credentials
  AWS_ACCESS_KEY_ID: "your-access-key"
  AWS_SECRET_ACCESS_KEY: "your-secret-key"
  
  # API keys
  SMTP_PASSWORD: "your-smtp-password"
```

## Database Deployments

### PostgreSQL Deployment

```yaml
# postgres-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: mams-prod
spec:
  replicas: 1
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
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        envFrom:
        - configMapRef:
            name: mams-config
        - secretRef:
            name: mams-secrets
        env:
        - name: POSTGRES_DB
          value: "mams_prod"
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: 2
            memory: 4Gi
          limits:
            cpu: 4
            memory: 8Gi
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-data

---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: mams-prod
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

### MongoDB Deployment

```yaml
# mongodb-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mongodb
  namespace: mams-prod
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mongodb
  template:
    metadata:
      labels:
        app: mongodb
    spec:
      containers:
      - name: mongodb
        image: mongo:7
        ports:
        - containerPort: 27017
        envFrom:
        - secretRef:
            name: mams-secrets
        env:
        - name: MONGO_INITDB_ROOT_USERNAME
          valueFrom:
            secretKeyRef:
              name: mams-secrets
              key: MONGODB_USER
        - name: MONGO_INITDB_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mams-secrets
              key: MONGODB_PASSWORD
        volumeMounts:
        - name: mongodb-storage
          mountPath: /data/db
        resources:
          requests:
            cpu: 2
            memory: 4Gi
          limits:
            cpu: 4
            memory: 8Gi
      volumes:
      - name: mongodb-storage
        persistentVolumeClaim:
          claimName: mongodb-data

---
apiVersion: v1
kind: Service
metadata:
  name: mongodb-service
  namespace: mams-prod
spec:
  selector:
    app: mongodb
  ports:
  - port: 27017
    targetPort: 27017
```

## Microservice Deployments

### API Gateway Deployment

```yaml
# api-gateway-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: mams-prod
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
        envFrom:
        - configMapRef:
            name: mams-config
        - secretRef:
            name: mams-secrets
        env:
        - name: SERVICE_NAME
          value: "api-gateway"
        - name: SERVICE_PORT
          value: "8000"
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
            memory: 1Gi
          limits:
            cpu: 2
            memory: 2Gi

---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-service
  namespace: mams-prod
spec:
  selector:
    app: api-gateway
  ports:
  - port: 8000
    targetPort: 8000
```

### Asset Management Service Deployment

```yaml
# asset-management-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: asset-management
  namespace: mams-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: asset-management
  template:
    metadata:
      labels:
        app: asset-management
    spec:
      containers:
      - name: asset-management
        image: mams/asset-management:latest
        ports:
        - containerPort: 8004
        envFrom:
        - configMapRef:
            name: mams-config
        - secretRef:
            name: mams-secrets
        env:
        - name: SERVICE_NAME
          value: "asset-management"
        - name: SERVICE_PORT
          value: "8004"
        - name: DATABASE_URL
          value: "postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@postgres-service:5432/mams_assets"
        livenessProbe:
          httpGet:
            path: /health
            port: 8004
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8004
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            cpu: 1
            memory: 2Gi
          limits:
            cpu: 4
            memory: 4Gi

---
apiVersion: v1
kind: Service
metadata:
  name: asset-management-service
  namespace: mams-prod
spec:
  selector:
    app: asset-management
  ports:
  - port: 8004
    targetPort: 8004
```

## Ingress Configuration

### NGINX Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mams-ingress
  namespace: mams-prod
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "5000m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
spec:
  tls:
  - hosts:
    - api.mams.example.com
    - app.mams.example.com
    secretName: mams-tls
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
              number: 8000
  - host: app.mams.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-frontend-service
            port:
              number: 3000
```

## Horizontal Pod Autoscaling

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
  namespace: mams-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 3
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

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: asset-management-hpa
  namespace: mams-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: asset-management
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
```

## Monitoring Setup

### Prometheus and Grafana

```bash
# Install Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace mams-monitoring \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

# Access Grafana
kubectl port-forward -n mams-monitoring svc/prometheus-grafana 3000:80
```

### Service Monitor for MAMS

```yaml
# service-monitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: mams-services
  namespace: mams-prod
spec:
  selector:
    matchLabels:
      app: mams
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

## Backup and Disaster Recovery

### Database Backup CronJob

```yaml
# postgres-backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: mams-prod
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15-alpine
            command:
            - /bin/sh
            - -c
            - |
              DATE=$(date +%Y%m%d_%H%M%S)
              pg_dump -h postgres-service -U $POSTGRES_USER -d mams_prod | \
              gzip > /backup/mams_prod_$DATE.sql.gz
              
              # Upload to S3
              aws s3 cp /backup/mams_prod_$DATE.sql.gz \
              s3://mams-backups/postgres/mams_prod_$DATE.sql.gz
              
              # Keep only last 30 backups locally
              find /backup -name "*.sql.gz" -mtime +30 -delete
            envFrom:
            - secretRef:
                name: mams-secrets
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
```

## Security Policies

### Network Policies

```yaml
# network-policies.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mams-network-policy
  namespace: mams-prod
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: mams-prod
    - namespaceSelector:
        matchLabels:
          name: mams-monitoring
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: mams-prod
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53  # DNS
```

### Pod Security Policy

```yaml
# pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: mams-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
  - ALL
  volumes:
  - 'configMap'
  - 'emptyDir'
  - 'projected'
  - 'secret'
  - 'downwardAPI'
  - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

## Deployment Commands

### Full Deployment

```bash
# 1. Create namespaces
kubectl apply -f namespaces.yaml

# 2. Apply storage classes and PVCs
kubectl apply -f storage-classes.yaml
kubectl apply -f database-pvcs.yaml

# 3. Create ConfigMaps and Secrets
kubectl apply -f mams-config.yaml
kubectl apply -f mams-secrets.yaml

# 4. Deploy databases
kubectl apply -f postgres-deployment.yaml
kubectl apply -f mongodb-deployment.yaml
kubectl apply -f opensearch-deployment.yaml
kubectl apply -f redis-deployment.yaml

# 5. Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n mams-prod --timeout=300s
kubectl wait --for=condition=ready pod -l app=mongodb -n mams-prod --timeout=300s

# 6. Deploy microservices
kubectl apply -f api-gateway-deployment.yaml
kubectl apply -f user-management-deployment.yaml
kubectl apply -f asset-management-deployment.yaml
# ... deploy all services

# 7. Apply HPA
kubectl apply -f hpa.yaml

# 8. Configure Ingress
kubectl apply -f ingress.yaml

# 9. Apply security policies
kubectl apply -f network-policies.yaml
```

### Verification

```bash
# Check pod status
kubectl get pods -n mams-prod

# Check services
kubectl get svc -n mams-prod

# Check ingress
kubectl get ingress -n mams-prod

# View logs
kubectl logs -f deployment/api-gateway -n mams-prod

# Check HPA status
kubectl get hpa -n mams-prod
```

## Production Checklist

- [ ] TLS certificates configured
- [ ] Resource limits set for all containers
- [ ] HPA configured for scalable services
- [ ] Database backups scheduled
- [ ] Monitoring and alerting configured
- [ ] Network policies applied
- [ ] Security scanning enabled
- [ ] Disaster recovery tested
- [ ] Documentation updated

## Troubleshooting

### Common Issues

1. **Pods not starting**
   ```bash
   kubectl describe pod <pod-name> -n mams-prod
   kubectl logs <pod-name> -n mams-prod --previous
   ```

2. **Database connection issues**
   ```bash
   # Test connection from a pod
   kubectl run -it --rm debug --image=postgres:15-alpine --restart=Never -- psql -h postgres-service -U mams_user
   ```

3. **Storage issues**
   ```bash
   kubectl get pvc -n mams-prod
   kubectl describe pvc <pvc-name> -n mams-prod
   ```

4. **Ingress not working**
   ```bash
   kubectl describe ingress mams-ingress -n mams-prod
   kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
   ```

---

For more deployment options:
- [Docker Deployment](./docker.md)
- [Cloud Deployment](./cloud.md)
- [High Availability Setup](./high-availability.md)