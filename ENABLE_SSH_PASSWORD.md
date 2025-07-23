# Enable SSH Password Authentication on Ubuntu 24.04

## On the Ubuntu Server (via VMware Console):

### 1. Check SSH service name and status:
```bash
# The service is called 'ssh' on Ubuntu (not 'sshd')
sudo systemctl status ssh
```

### 2. Enable password authentication:
```bash
# Edit SSH configuration
sudo nano /etc/ssh/sshd_config

# Find and change these lines:
# PasswordAuthentication no → PasswordAuthentication yes
# KbdInteractiveAuthentication no → KbdInteractiveAuthentication yes

# Or use sed to do it automatically:
sudo sed -i 's/#PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
sudo sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
sudo sed -i 's/KbdInteractiveAuthentication no/KbdInteractiveAuthentication yes/' /etc/ssh/sshd_config
```

### 3. Restart SSH service (correct command for Ubuntu):
```bash
sudo systemctl restart ssh
```

### 4. Verify SSH is running:
```bash
sudo systemctl status ssh
```

### 5. Check if firewall allows SSH:
```bash
sudo ufw status
# If needed, allow SSH:
sudo ufw allow ssh
```

## Alternative: Direct Deployment via Console

If you prefer to deploy directly from the VMware console without SSH:

### 1. Create the deployment script on the server:
```bash
# Create directory
sudo mkdir -p /opt/mams
sudo chown $USER:$USER /opt/mams
cd /opt/mams

# Create setup script
cat > setup.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting MAMS setup..."

# Update system
sudo apt-get update
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker $USER
fi

# Create directories
sudo mkdir -p /var/lib/mams/{postgres,mongodb,opensearch,redis,rabbitmq,grafana,prometheus}
sudo mkdir -p /var/log/mams/{nginx,services}
sudo mkdir -p /mnt/data/{assets,proxies,thumbnails,temp,archive,backups,minio}

# Set permissions
sudo chown -R 999:999 /var/lib/mams/postgres
sudo chown -R 999:999 /var/lib/mams/mongodb
sudo chown -R 1000:1000 /var/lib/mams/opensearch
sudo chown -R 472:472 /var/lib/mams/grafana
sudo chown -R $USER:$USER /mnt/data
sudo chmod -R 755 /mnt/data

echo "System setup completed!"
echo "Please log out and back in for docker group membership to take effect"
EOF

chmod +x setup.sh
```

### 2. Run the setup:
```bash
bash setup.sh
```

### 3. Log out and back in:
```bash
exit
# Log back in via VMware console
```

### 4. Continue with deployment:
```bash
cd /opt/mams

# Create docker-compose.yml for basic services
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: mams-postgres
    restart: always
    environment:
      POSTGRES_USER: mams
      POSTGRES_PASSWORD: mams_postgres_2024
      POSTGRES_DB: mams_production
    volumes:
      - /var/lib/mams/postgres:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  mongodb:
    image: mongo:7.0
    container_name: mams-mongodb
    restart: always
    environment:
      MONGO_INITDB_ROOT_USERNAME: mams
      MONGO_INITDB_ROOT_PASSWORD: mams_mongo_2024
      MONGO_INITDB_DATABASE: mams_production
    volumes:
      - /var/lib/mams/mongodb:/data/db
    ports:
      - "27017:27017"

  redis:
    image: redis:7-alpine
    container_name: mams-redis
    restart: always
    command: redis-server --appendonly yes --requirepass mams_redis_2024
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
      MINIO_ROOT_PASSWORD: mams_minio_2024
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
      RABBITMQ_DEFAULT_PASS: mams_rabbit_2024
      RABBITMQ_DEFAULT_VHOST: mams
    volumes:
      - /var/lib/mams/rabbitmq:/var/lib/rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"
EOF

# Start services
docker compose up -d

# Check status
docker compose ps
```

## Access Services

Once running, you can access:
- MinIO Console: http://192.168.178.186:9001
  - User: mams_admin
  - Pass: mams_minio_2024
- RabbitMQ: http://192.168.178.186:15672
  - User: mams
  - Pass: mams_rabbit_2024