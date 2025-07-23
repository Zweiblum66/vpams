# Quick Start Guide

Get MAMS up and running in minutes with Docker Compose. This guide will help you deploy a development instance of MAMS on your local machine.

## Prerequisites

Before you begin, ensure you have:
- Docker Engine 24.0+
- Docker Compose 2.20+
- 16GB+ RAM available
- 50GB+ free disk space
- Git

## 🚀 5-Minute Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/mams.git
cd mams
```

### 2. Configure Environment

```bash
# Copy example environment files
cp .env.example .env

# Edit the .env file with your settings
nano .env
```

Key settings to configure:
- `JWT_SECRET_KEY` - Change from default
- `ADMIN_EMAIL` - Your admin email
- `ADMIN_PASSWORD` - Secure admin password

### 3. Start MAMS

```bash
# Start all services
docker-compose up -d

# Wait for services to be ready (about 2-3 minutes)
docker-compose ps

# Check logs if needed
docker-compose logs -f
```

### 4. Verify Installation

Open your browser and navigate to:
- **Web Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs

Default credentials:
- Username: `admin@mams.local`
- Password: `changeme123!`

### 5. Initial Setup

1. **Login** with default credentials
2. **Change password** immediately
3. **Create your first project**
4. **Upload a test asset**

## 📦 What's Included

This quick start deployment includes:

### Core Services
- ✅ API Gateway
- ✅ User Management
- ✅ Asset Management
- ✅ Storage Abstraction
- ✅ Search Engine
- ✅ Metadata Service
- ✅ Proxy Generation
- ✅ Basic Workflow Engine

### Infrastructure
- ✅ PostgreSQL Database
- ✅ MongoDB for Metadata
- ✅ OpenSearch for Search
- ✅ Redis for Caching
- ✅ MinIO for Object Storage
- ✅ RabbitMQ for Messaging

### Monitoring
- ✅ Prometheus
- ✅ Grafana (http://localhost:3001)

## 🎯 Next Steps

### Upload Your First Asset

1. Click **"New Asset"** in the web interface
2. Select a video, image, or document
3. Add metadata tags
4. Click **"Upload"**

The system will automatically:
- Generate proxies
- Extract metadata
- Index for search
- Create thumbnails

### Create a Project

1. Navigate to **Projects**
2. Click **"Create Project"**
3. Name your project
4. Start organizing assets

### Explore Features

Try these features:
- **Search**: Use the search bar to find assets
- **Preview**: Click any asset to preview
- **Share**: Generate sharing links
- **Workflow**: Create a simple approval workflow

## 🛠️ Basic Configuration

### Storage Configuration

Edit `docker-compose.yml` to add external storage:

```yaml
services:
  storage-abstraction:
    environment:
      - STORAGE_TYPE=s3
      - S3_ENDPOINT=https://s3.amazonaws.com
      - S3_ACCESS_KEY=${AWS_ACCESS_KEY}
      - S3_SECRET_KEY=${AWS_SECRET_KEY}
      - S3_BUCKET=your-bucket
```

### User Management

Create additional users via the API:

```bash
curl -X POST "http://localhost:8000/api/v1/users" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword",
    "role": "editor"
  }'
```

### Enable Additional Services

To enable AI features:

```bash
# Edit docker-compose.yml and uncomment:
# ai-ml-service:
#   build: ./services/ai-ml
#   ...

docker-compose up -d ai-ml-service
```

## 🔍 Troubleshooting

### Services Not Starting

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs service-name

# Restart a service
docker-compose restart service-name
```

### Port Conflicts

If you get port conflict errors:

1. Check what's using the port:
   ```bash
   lsof -i :8000  # API Gateway
   lsof -i :3000  # Web UI
   ```

2. Either stop the conflicting service or change MAMS ports in `.env`

### Database Connection Issues

```bash
# Reset the database
docker-compose down -v
docker-compose up -d
```

### Performance Issues

For better performance:
1. Increase Docker memory allocation (Docker Desktop → Preferences → Resources)
2. Disable services you don't need in `docker-compose.yml`

## 📊 Resource Usage

Typical resource usage for development instance:
- **CPU**: 2-4 cores under normal load
- **Memory**: 8-12GB total
- **Disk I/O**: Moderate (depends on asset uploads)
- **Network**: Minimal (local only)

## 🔒 Security Notes

⚠️ **This quick start configuration is for development only!**

Before deploying to production:
- Change all default passwords
- Generate secure JWT keys
- Enable HTTPS
- Configure firewall rules
- Review security documentation

## 📚 Learn More

- [Installation Guide](./installation.md) - Detailed installation instructions
- [Architecture Overview](../architecture/overview.md) - Understand the system
- [API Documentation](../api-reference/rest-api.md) - Integrate with MAMS
- [Troubleshooting](../troubleshooting/common-issues.md) - Common issues

## 💡 Tips

1. **Use keyboard shortcuts**:
   - `Ctrl+K` - Quick search
   - `Ctrl+N` - New asset
   - `Ctrl+/` - Show shortcuts

2. **Bulk operations**:
   - Select multiple assets with `Shift+Click`
   - Drag and drop multiple files

3. **Advanced search**:
   - Use quotes for exact match: `"project alpha"`
   - Use operators: `type:video AND created:>2024-01-01`

---

🎉 **Congratulations!** You now have MAMS running locally. Explore the interface and check out our other guides to learn more about the platform's capabilities.