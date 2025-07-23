# Installation Guide

## Overview

This guide covers the complete installation process for MAMS, including prerequisites, system requirements, and step-by-step installation instructions for different deployment scenarios.

## System Requirements

### Minimum Requirements

#### Hardware
- **CPU**: 8 cores (x86_64 or ARM64)
- **RAM**: 32GB
- **Storage**: 500GB SSD
- **Network**: 1Gbps connection

#### Software
- **OS**: Ubuntu 20.04+ / CentOS 8+ / macOS 12+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+
- **Node.js**: 18+ (for frontend)
- **PostgreSQL**: 15+ (if not using Docker)

### Recommended Production Requirements

#### Hardware
- **CPU**: 16+ cores
- **RAM**: 64GB+
- **Storage**: 2TB+ NVMe SSD
- **Network**: 10Gbps connection

#### Additional Requirements
- **Kubernetes**: 1.28+ (for K8s deployment)
- **Load Balancer**: NGINX or HAProxy
- **SSL Certificates**: Valid TLS certificates
- **DNS**: Properly configured domain

## Pre-Installation Setup

### 1. System Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required tools
sudo apt install -y \
  curl \
  git \
  build-essential \
  python3-pip \
  python3-venv \
  ffmpeg \
  imagemagick \
  redis-tools \
  postgresql-client

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Clone Repository

```bash
# Clone MAMS repository
git clone https://github.com/your-org/mams.git
cd mams

# Create necessary directories
mkdir -p data/{postgres,mongodb,opensearch,redis,minio,logs,backups}
chmod -R 755 data/
```

### 3. Environment Configuration

Create environment files:

```bash
# Copy example environment files
cp .env.example .env
cp frontend/.env.example frontend/.env

# Generate secure secrets
echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)" >> .env
echo "MONGODB_PASSWORD=$(openssl rand -base64 32)" >> .env
echo "OPENSEARCH_PASSWORD=$(openssl rand -base64 32)" >> .env
echo "MINIO_SECRET_KEY=$(openssl rand -base64 32)" >> .env
```

Edit `.env` file:
```bash
# MAMS Environment Configuration

# General Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
TIMEZONE=UTC

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=mams_dev
POSTGRES_USER=mams_user

MONGODB_HOST=mongodb
MONGODB_PORT=27017
MONGODB_DB=mams_metadata
MONGODB_USER=mams_user

# Search Configuration
OPENSEARCH_HOST=opensearch
OPENSEARCH_PORT=9200
OPENSEARCH_USER=admin

# Cache Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Storage Configuration
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=mams_access
MINIO_BUCKET=mams-assets

# Service URLs
API_GATEWAY_URL=http://api-gateway:8000
FRONTEND_URL=http://localhost:3000

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Security
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
SESSION_TIMEOUT_MINUTES=60
MAX_LOGIN_ATTEMPTS=5
```

## Installation Methods

### Method 1: Docker Compose (Recommended for Development)

#### 1. Build Services

```bash
# Build all services
docker-compose build

# Or build specific service
docker-compose build api-gateway
```

#### 2. Initialize Databases

```bash
# Start database services first
docker-compose up -d postgres mongodb opensearch redis

# Wait for databases to be ready
sleep 30

# Run database migrations
docker-compose run --rm api-gateway python manage.py migrate
docker-compose run --rm user-management python manage.py migrate
docker-compose run --rm asset-management python manage.py migrate

# Create initial admin user
docker-compose run --rm user-management python manage.py createsuperuser
```

#### 3. Start All Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

#### 4. Initialize Search Indices

```bash
# Create OpenSearch indices
docker-compose exec api-gateway python manage.py create_indices

# Verify indices
curl -X GET "http://localhost:9200/_cat/indices?v"
```

### Method 2: Kubernetes Installation

#### 1. Prepare Kubernetes Cluster

```bash
# Create namespace
kubectl create namespace mams

# Create secrets
kubectl create secret generic mams-secrets \
  --from-env-file=.env \
  -n mams

# Create ConfigMap
kubectl create configmap mams-config \
  --from-file=config/ \
  -n mams
```

#### 2. Install Using Helm

```bash
# Add MAMS Helm repository
helm repo add mams https://charts.mams.io
helm repo update

# Install MAMS
helm install mams mams/mams \
  --namespace mams \
  --values values.yaml \
  --set global.storageClass=fast-ssd
```

#### 3. Verify Installation

```bash
# Check pod status
kubectl get pods -n mams

# Wait for all pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=mams -n mams --timeout=600s

# Get service endpoints
kubectl get svc -n mams
```

### Method 3: Manual Installation

#### 1. Install Python Services

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies for each service
cd services/api-gateway
pip install -r requirements.txt

cd ../user-management
pip install -r requirements.txt

cd ../asset-management
pip install -r requirements.txt
# ... repeat for all services
```

#### 2. Install Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build frontend
npm run build

# Or for development
npm run dev
```

#### 3. Configure Services

Create systemd service files for each microservice:

```bash
# /etc/systemd/system/mams-api-gateway.service
[Unit]
Description=MAMS API Gateway
After=network.target

[Service]
Type=simple
User=mams
WorkingDirectory=/opt/mams/services/api-gateway
Environment="PATH=/opt/mams/venv/bin"
ExecStart=/opt/mams/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 4. Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start services
sudo systemctl start mams-api-gateway
sudo systemctl start mams-user-management
sudo systemctl start mams-asset-management
# ... start all services

# Enable auto-start
sudo systemctl enable mams-api-gateway
sudo systemctl enable mams-user-management
# ... enable all services
```

## Post-Installation Configuration

### 1. Configure Storage

```bash
# Create MinIO buckets
docker-compose exec minio mc alias set mams http://localhost:9000 mams_access $MINIO_SECRET_KEY
docker-compose exec minio mc mb mams/mams-assets
docker-compose exec minio mc mb mams/mams-proxies
docker-compose exec minio mc mb mams/mams-backups

# Set bucket policies
docker-compose exec minio mc policy set public mams/mams-proxies
```

### 2. Configure NGINX (Production)

Create `/etc/nginx/sites-available/mams`:

```nginx
upstream mams_api {
    server localhost:8000;
}

upstream mams_frontend {
    server localhost:3000;
}

server {
    listen 80;
    server_name mams.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mams.example.com;

    ssl_certificate /etc/letsencrypt/live/mams.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mams.example.com/privkey.pem;

    client_max_body_size 5G;

    location /api {
        proxy_pass http://mams_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Upload timeout
        proxy_read_timeout 3600;
        proxy_send_timeout 3600;
    }

    location / {
        proxy_pass http://mams_frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://mams_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/mams /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Setup SSL Certificates

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d mams.example.com -d api.mams.example.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### 4. Configure Firewall

```bash
# Allow necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 5432/tcp  # PostgreSQL (if external access needed)
sudo ufw allow 9200/tcp  # OpenSearch (if external access needed)

# Enable firewall
sudo ufw enable
```

## Verification

### 1. Health Checks

```bash
# Check API Gateway
curl http://localhost:8000/health

# Check all services
for port in 8000 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8011; do
  echo "Checking service on port $port"
  curl -s http://localhost:$port/health | jq .
done
```

### 2. Frontend Access

Open your browser and navigate to:
- Development: http://localhost:3000
- Production: https://mams.example.com

### 3. API Documentation

Access the interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 4. Run Test Suite

```bash
# Run backend tests
docker-compose run --rm api-gateway pytest
docker-compose run --rm asset-management pytest

# Run frontend tests
cd frontend
npm test

# Run E2E tests
npm run test:e2e
```

## Troubleshooting

### Common Issues

#### 1. Port Conflicts
```bash
# Check for port usage
sudo lsof -i :8000
sudo lsof -i :3000

# Stop conflicting services or change MAMS ports in .env
```

#### 2. Database Connection Issues
```bash
# Test database connection
docker-compose exec postgres psql -U mams_user -d mams_dev

# Check database logs
docker-compose logs postgres
```

#### 3. Permission Issues
```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/
chmod -R 755 data/
```

#### 4. Service Not Starting
```bash
# Check service logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]

# Rebuild service
docker-compose build --no-cache [service-name]
```

### Reset Installation

If you need to start fresh:

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: This deletes all data)
docker-compose down -v

# Remove data directory
rm -rf data/

# Start fresh installation
./scripts/install.sh
```

## Backup Before Updates

Always backup before updating MAMS:

```bash
# Backup databases
./scripts/backup.sh

# Backup configuration
cp -r .env config/ backups/

# Backup uploaded files
rsync -av data/minio/ backups/minio/
```

## Next Steps

1. [Configure User Authentication](../configuration/authentication.md)
2. [Set Up Storage Backends](../configuration/storage.md)
3. [Configure Email Notifications](../configuration/email.md)
4. [Set Up Monitoring](../operations/monitoring.md)
5. [Review Security Settings](../security/hardening.md)

---

For additional help:
- [Troubleshooting Guide](../troubleshooting/common-issues.md)
- [FAQ](../faq.md)
- [Community Support](https://community.mams.io)