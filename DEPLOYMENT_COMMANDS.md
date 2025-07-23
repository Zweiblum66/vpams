# MAMS Production Deployment Commands

Execute these commands after connecting to the server via SSH:

```bash
ssh jens@192.168.178.186
```

## 1. Initial Setup

```bash
# Switch to root for initial setup
sudo su -

# Create project directory
mkdir -p /opt/mams
chown jens:jens /opt/mams
exit

# As user jens
cd /opt
```

## 2. Create Required Files

### Create .env.production file:

```bash
cat > /opt/mams/.env.production << 'EOF'
# MAMS Production Environment Configuration
# Server: 192.168.178.186 (Ubuntu 24.04 LTS)

# Server Configuration
SERVER_IP=192.168.178.186
ENVIRONMENT=production
LOG_LEVEL=INFO

# Security Keys (CHANGE THESE IN PRODUCTION!)
JWT_SECRET_KEY=mams_prod_jwt_secret_2024_change_this_immediately
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Database Credentials
POSTGRES_USER=mams
POSTGRES_PASSWORD=mams_postgres_prod_2024
POSTGRES_DB=mams_production

MONGO_ROOT_USERNAME=mams
MONGO_ROOT_PASSWORD=mams_mongo_prod_2024
MONGO_DATABASE=mams_production

REDIS_PASSWORD=mams_redis_prod_2024

# RabbitMQ
RABBITMQ_USER=mams
RABBITMQ_PASSWORD=mams_rabbit_prod_2024
RABBITMQ_VHOST=mams

# MinIO Object Storage
MINIO_ROOT_USER=mams_admin
MINIO_ROOT_PASSWORD=mams_minio_prod_2024
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=mams_admin
S3_SECRET_KEY=mams_minio_prod_2024

# OpenSearch
OPENSEARCH_ADMIN_PASSWORD=mams_opensearch_prod_2024

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=mams_grafana_prod_2024

# Email Configuration (Optional - configure if needed)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# External APIs (Optional)
OPENAI_API_KEY=

# Service URLs (Internal Docker Network)
DATABASE_URL=postgresql+asyncpg://mams:mams_postgres_prod_2024@postgres:5432/mams_production
MONGODB_URL=mongodb://mams:mams_mongo_prod_2024@mongodb:27017/mams_production?authSource=admin
REDIS_URL=redis://:mams_redis_prod_2024@redis:6379/0
RABBITMQ_URL=amqp://mams:mams_rabbit_prod_2024@rabbitmq:5672/mams
OPENSEARCH_URL=http://opensearch:9200

# Resource Limits
POSTGRES_MEMORY=8G
MONGODB_MEMORY=4G
OPENSEARCH_MEMORY=8G
REDIS_MEMORY=2G

# Storage Configuration
STORAGE_ROOT=/mnt/data
ASSETS_PATH=/mnt/data/assets
PROXIES_PATH=/mnt/data/proxies
THUMBNAILS_PATH=/mnt/data/thumbnails
TEMP_PATH=/mnt/data/temp
ARCHIVE_PATH=/mnt/data/archive
BACKUP_PATH=/mnt/data/backups

# Backup Configuration
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE="0 2 * * *"

# Feature Flags
ENABLE_AI_FEATURES=true
ENABLE_BLOCKCHAIN=false
ENABLE_HOLOGRAPHIC=true
ENABLE_METAVERSE=false
EOF
```

### Create docker-compose.production.yml:

```bash
# This file is too large to paste directly. Create it with:
mkdir -p /opt/mams
cd /opt/mams

# Download or create the docker-compose.production.yml file
# You'll need to copy this from your local machine
```

## 3. Run System Setup Script

```bash
# Create the setup script
cat > /opt/mams/setup-system.sh << 'SCRIPT'
#!/bin/bash
set -e

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Configure system limits
cat > /etc/sysctl.d/99-mams.conf <<EOF
vm.max_map_count=262144
fs.file-max=65536
net.core.somaxconn=32768
net.ipv4.tcp_max_syn_backlog=8096
net.ipv4.ip_local_port_range=1024 65535
EOF
sysctl -p /etc/sysctl.d/99-mams.conf

# Create directories
mkdir -p /var/lib/mams/{postgres,mongodb,opensearch,redis,rabbitmq,grafana,prometheus}
mkdir -p /var/log/mams/{nginx,services}
mkdir -p /mnt/data/{assets,proxies,thumbnails,temp,archive,backups,minio}

# Set permissions
chown -R 999:999 /var/lib/mams/postgres
chown -R 999:999 /var/lib/mams/mongodb
chown -R 1000:1000 /var/lib/mams/opensearch
chown -R 472:472 /var/lib/mams/grafana
chown -R jens:jens /mnt/data
chmod -R 755 /mnt/data

# Add user to docker group
usermod -aG docker jens

echo "System setup completed!"
SCRIPT

# Make it executable and run
chmod +x /opt/mams/setup-system.sh
sudo /opt/mams/setup-system.sh
```

## 4. Create Minimal docker-compose.yml for Initial Services

```bash
cat > /opt/mams/docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: mams-postgres
    restart: always
    environment:
      POSTGRES_USER: mams
      POSTGRES_PASSWORD: mams_postgres_prod_2024
      POSTGRES_DB: mams_production
    volumes:
      - /var/lib/mams/postgres:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mams"]
      interval: 10s
      timeout: 5s
      retries: 5

  mongodb:
    image: mongo:7.0
    container_name: mams-mongodb
    restart: always
    environment:
      MONGO_INITDB_ROOT_USERNAME: mams
      MONGO_INITDB_ROOT_PASSWORD: mams_mongo_prod_2024
      MONGO_INITDB_DATABASE: mams_production
    volumes:
      - /var/lib/mams/mongodb:/data/db
    ports:
      - "27017:27017"

  redis:
    image: redis:7-alpine
    container_name: mams-redis
    restart: always
    command: redis-server --appendonly yes --requirepass mams_redis_prod_2024
    volumes:
      - /var/lib/mams/redis:/data
    ports:
      - "6379:6379"

  minio:
    image: minio/minio:latest
    container_name: mams-minio
    restart: always
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: mams_admin
      MINIO_ROOT_PASSWORD: mams_minio_prod_2024
    volumes:
      - /mnt/data/minio:/data
    ports:
      - "9000:9000"
      - "9001:9001"

  rabbitmq:
    image: rabbitmq:3.12-management
    container_name: mams-rabbitmq
    restart: always
    environment:
      RABBITMQ_DEFAULT_USER: mams
      RABBITMQ_DEFAULT_PASS: mams_rabbit_prod_2024
      RABBITMQ_DEFAULT_VHOST: mams
    volumes:
      - /var/lib/mams/rabbitmq:/var/lib/rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"
EOF
```

## 5. Start Infrastructure Services

```bash
cd /opt/mams

# Copy .env file
cp .env.production .env

# Start infrastructure services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## 6. Initialize MinIO Buckets

```bash
# Wait for MinIO to start
sleep 30

# Access MinIO container
docker exec -it mams-minio mc alias set myminio http://localhost:9000 mams_admin mams_minio_prod_2024

# Create buckets
docker exec -it mams-minio mc mb myminio/mams-assets --ignore-existing
docker exec -it mams-minio mc mb myminio/mams-proxies --ignore-existing
docker exec -it mams-minio mc mb myminio/mams-thumbnails --ignore-existing
docker exec -it mams-minio mc mb myminio/mams-temp --ignore-existing
docker exec -it mams-minio mc mb myminio/mams-archive --ignore-existing
```

## 7. Verify Services

```bash
# Check all services are running
docker ps

# Test PostgreSQL
docker exec -it mams-postgres psql -U mams -d mams_production -c "SELECT 1"

# Test MongoDB
docker exec -it mams-mongodb mongosh --eval "db.adminCommand('ping')"

# Test Redis
docker exec -it mams-redis redis-cli -a mams_redis_prod_2024 ping

# Check MinIO
curl http://localhost:9000/minio/health/live
```

## 8. Access Points

After successful deployment:
- MinIO Console: http://192.168.178.186:9001
  - Username: mams_admin
  - Password: mams_minio_prod_2024
- RabbitMQ Management: http://192.168.178.186:15672
  - Username: mams
  - Password: mams_rabbit_prod_2024

## 9. Security - Update Passwords

```bash
# Generate secure passwords
openssl rand -base64 32

# Edit .env file and update all passwords
nano /opt/mams/.env

# Restart services after password changes
docker compose down
docker compose up -d
```

## Troubleshooting

If you encounter issues:

```bash
# Check Docker status
systemctl status docker

# Check disk space
df -h

# Check service logs
docker compose logs postgres
docker compose logs mongodb
docker compose logs minio

# Restart specific service
docker compose restart postgres
```