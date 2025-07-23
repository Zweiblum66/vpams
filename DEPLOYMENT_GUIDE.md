# MAMS Production Deployment Guide

## Server Information
- **IP Address**: 192.168.178.186
- **OS**: Ubuntu 24.04 LTS
- **Resources**: 16 cores, 64GB RAM
- **System Drive**: 100GB
- **Data Mount**: 1TB at /mnt/data (for assets, proxies, thumbnails)
- **User**: jens
- **Password**: Tr4umK3ks!!

## Prerequisites Completed
The server has been prepared with:
- Docker and Docker Compose installation
- System limits configuration
- Firewall setup
- Directory structure creation
- Monitoring tools installation

## Deployment Steps

### 1. Connect to the Server

```bash
ssh jens@192.168.178.186
```

### 2. Clone the MAMS Repository

First, create the project directory and clone your repository:

```bash
# Switch to root for initial setup
sudo su -

# Create project directory
mkdir -p /opt/mams
chown jens:jens /opt/mams
exit

# Clone repository (replace with your actual repository URL)
cd /opt
git clone https://github.com/your-org/mams.git mams
cd mams
```

### 3. Copy Configuration Files

You have two options for deploying:

**Option A: Use the automated remote deployment script**

```bash
# From your local MAMS directory
chmod +x scripts/deploy-remote.sh
./scripts/deploy-remote.sh
```

This script will automatically:
- Copy all necessary files to the server
- Run system setup if needed
- Deploy all MAMS services
- Verify the deployment

**Option B: Manual deployment**

```bash
# From your local machine, copy files to the server
scp .env.production jens@192.168.178.186:/opt/mams/
scp docker-compose.production.yml jens@192.168.178.186:/opt/mams/
scp -r nginx jens@192.168.178.186:/opt/mams/
scp -r monitoring jens@192.168.178.186:/opt/mams/
scp scripts/deploy-mams.sh jens@192.168.178.186:/opt/mams/scripts/
```

### 4. Run the Initial System Setup

On the server, run the system setup script:

```bash
cd /opt/mams
sudo bash scripts/deploy-production.sh
```

This script will:
- Update system packages
- Install Docker and Docker Compose
- Configure system limits
- Setup firewall rules
- Create necessary directories
- Install monitoring tools

### 5. Deploy MAMS Services

After the system setup is complete, deploy MAMS:

```bash
cd /opt/mams
chmod +x scripts/deploy-mams.sh
./scripts/deploy-mams.sh
```

This script will:
- Set up the environment configuration
- Generate secure passwords
- Pull all Docker images
- Initialize databases
- Start all services
- Run database migrations
- Configure MinIO storage
- Perform health checks

### 6. Verify Deployment

Check that all services are running:

```bash
cd /opt/mams
docker-compose -f docker-compose.production.yml ps
```

All services should show as "Up" status.

### 7. Access the Application

Once deployment is complete, you can access:

- **Frontend**: http://192.168.178.186:3000
- **API Gateway**: http://192.168.178.186:8080
- **API Documentation**: http://192.168.178.186:8080/docs
- **MinIO Console**: http://192.168.178.186:9001
- **Grafana Dashboard**: http://192.168.178.186:3001
- **RabbitMQ Management**: http://192.168.178.186:15672

### 8. Initial Admin Setup

1. Access the frontend at http://192.168.178according to documentation.186:3000
2. Click "Register" to create the first admin account
3. The first registered user automatically gets admin privileges

### 9. Configure Services

#### MinIO (Object Storage)
1. Access MinIO at http://192.168.178.186:9001
2. Login with credentials from `.env` file
3. Verify buckets are created:
   - mams-assets
   - mams-proxies
   - mams-thumbnails
   - mams-temp
   - mams-archive

#### Grafana (Monitoring)
1. Access Grafana at http://192.168.178.186:3001
2. Login with admin/(password from .env)
3. Import MAMS dashboards from Grafana marketplace or create custom ones

#### RabbitMQ (Message Queue)
1. Access RabbitMQ at http://192.168.178.186:15672
2. Login with mams/(password from .env)
3. Verify queues are created for async operations

## Storage Configuration

The deployment automatically configures storage across two locations:

### System Storage (100GB system drive)
- PostgreSQL database: `/var/lib/mams/postgres`
- MongoDB database: `/var/lib/mams/mongodb`
- OpenSearch indices: `/var/lib/mams/opensearch`
- Redis data: `/var/lib/mams/redis`
- Application logs: `/var/log/mams/`

### Data Storage (1TB at /mnt/data)
- Media assets: `/mnt/data/assets`
- Video/audio proxies: `/mnt/data/proxies`
- Thumbnails: `/mnt/data/thumbnails`
- Temporary files: `/mnt/data/temp`
- Archive storage: `/mnt/data/archive`
- MinIO object storage: `/mnt/data/minio`
- Backups: `/mnt/data/backups`

## Post-Deployment Tasks

### 1. Security Hardening

Update all default passwords in the `.env` file:

```bash
cd /opt/mams
nano .env
# Update all password fields with secure values
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d
```

### 2. SSL/TLS Configuration

For production use, configure SSL certificates:

```bash
# Install Certbot
sudo apt-get install certbot

# Obtain certificate (replace with your domain)
sudo certbot certonly --standalone -d mams.yourdomain.com

# Update nginx configuration to use SSL
# Edit /opt/mams/nginx/nginx.conf and uncomment HTTPS server block
```

### 3. Backup Configuration

Set up automated backups:

```bash
# Create backup script
sudo nano /opt/mams/scripts/backup.sh

# Add to crontab for daily backups at 2 AM
crontab -e
# Add: 0 2 * * * /opt/mams/scripts/backup.sh
```

### 4. Monitoring Setup

Configure alerts in Grafana:
1. Go to Alerting > Alert rules
2. Create alerts for:
   - Service downtime
   - High CPU/Memory usage
   - Disk space warnings
   - Database connection issues

## Maintenance Commands

### View Logs
```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f api-gateway
```

### Restart Services
```bash
# All services
docker-compose -f docker-compose.production.yml restart

# Specific service
docker-compose -f docker-compose.production.yml restart api-gateway
```

### Update Services
```bash
cd /opt/mams
git pull origin main
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

### Database Backup
```bash
# PostgreSQL
docker-compose -f docker-compose.production.yml exec postgres \
  pg_dump -U mams mams_production > backup_$(date +%Y%m%d).sql

# MongoDB
docker-compose -f docker-compose.production.yml exec mongodb \
  mongodump --uri="mongodb://mams:password@localhost:27017/mams_production?authSource=admin" \
  --out=/backup/$(date +%Y%m%d)
```

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs [service-name]

# Check resource usage
docker stats

# Restart Docker daemon
sudo systemctl restart docker
```

### Database Connection Issues
```bash
# Test PostgreSQL connection
docker-compose -f docker-compose.production.yml exec postgres \
  psql -U mams -d mams_production -c "SELECT 1"

# Test MongoDB connection
docker-compose -f docker-compose.production.yml exec mongodb \
  mongosh --eval "db.adminCommand('ping')"
```

### Performance Issues
1. Check Grafana dashboards for resource bottlenecks
2. Review service logs for errors
3. Scale services if needed by adjusting resource limits

## Support

For issues or questions:
1. Check service logs first
2. Review Grafana metrics
3. Consult the MAMS documentation
4. Contact the development team

## Security Notes

⚠️ **Important Security Steps**:
1. Change ALL default passwords in `.env` immediately
2. Configure firewall rules for your network
3. Set up SSL/TLS certificates
4. Enable audit logging
5. Configure backup encryption
6. Implement network segmentation if possible
7. Set up intrusion detection monitoring

Remember to regularly:
- Update system packages
- Review security logs
- Test backup restoration
- Monitor for unusual activity