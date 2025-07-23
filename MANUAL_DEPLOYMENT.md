# Manual MAMS Deployment Instructions

Since the automated deployment had issues, please follow these manual steps by connecting to your server via SSH or VMware console:

```bash
ssh jens@192.168.178.186
```

## Step 1: Create the MAMS directory

```bash
sudo mkdir -p /opt/mams
sudo chown jens:jens /opt/mams
cd /opt/mams
```

## Step 2: Create the .env file

```bash
cat > /opt/mams/.env << 'EOF'
# MAMS Production Environment Configuration
SERVER_IP=192.168.178.186
ENVIRONMENT=production
LOG_LEVEL=INFO

# Security Keys
JWT_SECRET_KEY=mams_prod_jwt_secret_2024_change_this
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

# Storage Configuration
STORAGE_ROOT=/mnt/data
ASSETS_PATH=/mnt/data/assets
PROXIES_PATH=/mnt/data/proxies
THUMBNAILS_PATH=/mnt/data/thumbnails
TEMP_PATH=/mnt/data/temp
ARCHIVE_PATH=/mnt/data/archive
BACKUP_PATH=/mnt/data/backups
EOF
```

## Step 3: Create docker-compose.yml

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

## Step 4: Start the services

```bash
# Make sure you're in the right directory
cd /opt/mams

# Start all services
sudo docker-compose up -d

# Check if services are running
sudo docker ps

# View logs if needed
sudo docker-compose logs -f
```

## Step 5: Initialize MinIO buckets

Wait about 30 seconds for services to start, then:

```bash
# Create MinIO alias
sudo docker exec mams-minio mc alias set myminio http://localhost:9000 mams_admin mams_minio_prod_2024

# Create buckets
sudo docker exec mams-minio mc mb myminio/mams-assets --ignore-existing
sudo docker exec mams-minio mc mb myminio/mams-proxies --ignore-existing
sudo docker exec mams-minio mc mb myminio/mams-thumbnails --ignore-existing
sudo docker exec mams-minio mc mb myminio/mams-temp --ignore-existing
sudo docker exec mams-minio mc mb myminio/mams-archive --ignore-existing
```

## Step 6: Open firewall ports

```bash
# Allow access to services
sudo ufw allow 9001/tcp    # MinIO Console
sudo ufw allow 15672/tcp   # RabbitMQ Management
sudo ufw allow 3000/tcp    # Frontend (when deployed)
sudo ufw allow 8080/tcp    # API Gateway (when deployed)
```

## Step 7: Verify deployment

Check if you can access:
- MinIO Console: http://192.168.178.186:9001
  - Username: mams_admin
  - Password: mams_minio_prod_2024
- RabbitMQ Management: http://192.168.178.186:15672
  - Username: mams
  - Password: mams_rabbit_prod_2024

## Troubleshooting

If services don't start:
```bash
# Check logs
sudo docker-compose logs postgres
sudo docker-compose logs mongodb
sudo docker-compose logs minio

# Restart a specific service
sudo docker-compose restart minio

# Stop and start everything
sudo docker-compose down
sudo docker-compose up -d
```

## Next Steps

1. **Change all passwords** in the .env file
2. Copy the full docker-compose.production.yml when ready to deploy all services
3. Add your MAMS service code to /opt/mams/services/
4. Set up SSL certificates for production use