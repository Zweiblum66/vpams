# MAMS Development Environment Setup Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Service Architecture](#service-architecture)
5. [Development Workflow](#development-workflow)
6. [Troubleshooting](#troubleshooting)
7. [IDE Configuration](#ide-configuration)

## Prerequisites

### Required Software
- **Docker Desktop** >= 24.0 ([Download](https://www.docker.com/products/docker-desktop))
- **Docker Compose** >= 2.23 (included with Docker Desktop)
- **Python** >= 3.11 ([Download](https://www.python.org/downloads/))
- **Node.js** >= 20.0 LTS ([Download](https://nodejs.org/))
- **Git** >= 2.40 ([Download](https://git-scm.com/))

### Recommended Tools
- **VS Code** with recommended extensions
- **Postman** or **Insomnia** for API testing
- **DBeaver** for database management
- **Make** (included on Linux/macOS, use WSL on Windows)

### System Requirements
- **RAM**: Minimum 16GB (32GB recommended)
- **Storage**: 50GB free space
- **CPU**: 4+ cores recommended

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MyVideoMAM
   ```

2. **Run the setup script**
   ```bash
   ./scripts/setup-dev-env.sh
   ```

3. **Start all services**
   ```bash
   make up-all
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - API Gateway: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Detailed Setup

### 1. Environment Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

Key environment variables to configure:
```env
# Security (MUST change for production)
JWT_SECRET_KEY=your-super-secret-key-change-in-production

# Database passwords (change if needed)
POSTGRES_PASSWORD=dev_password
MONGODB_PASSWORD=dev_password

# External services (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 2. Python Virtual Environment

Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

### 3. Pre-commit Hooks

Install pre-commit hooks for code quality:
```bash
pre-commit install
```

This will automatically run:
- **Black** - Code formatting
- **Ruff** - Linting
- **MyPy** - Type checking
- **Prettier** - Frontend formatting

### 4. Database Initialization

Start infrastructure services:
```bash
make up
```

Initialize databases:
```bash
./scripts/init-databases.sh
```

This creates:
- PostgreSQL databases for each service
- MongoDB collections
- OpenSearch indices
- MinIO storage buckets
- RabbitMQ exchanges

### 5. Building Services

Build all Docker images:
```bash
make build-all
```

Or build a specific service:
```bash
docker-compose build api-gateway
```

## Service Architecture

### Infrastructure Services

| Service | Port | Purpose | Access URL |
|---------|------|---------|------------|
| PostgreSQL | 5432 | Relational database | `postgresql://localhost:5432` |
| MongoDB | 27017 | Document database | `mongodb://localhost:27017` |
| Redis | 6379 | Cache & sessions | `redis://localhost:6379` |
| OpenSearch | 9200 | Search engine | http://localhost:9200 |
| MinIO | 9000/9001 | Object storage | http://localhost:9001 (console) |
| RabbitMQ | 5672/15672 | Message queue | http://localhost:15672 (management) |
| Prometheus | 9090 | Metrics | http://localhost:9090 |
| Grafana | 3001 | Monitoring dashboards | http://localhost:3001 |

### Microservices

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | Central entry point, authentication, rate limiting |
| User Management | 8001 | User authentication and authorization |
| Storage Abstraction | 8002 | Unified storage interface |
| Asset Management | 8003 | Core asset CRUD operations |
| Metadata Service | 8004 | Flexible metadata management |
| Search Engine | 8005 | Full-text and semantic search |
| Ingest Service | 8006 | File ingestion and validation |
| Proxy Generation | 8007 | Media proxy and thumbnail generation |
| Workflow Engine | 8008 | Automation and approvals |
| AI/ML Service | 8009 | Machine learning features |
| Rights Management | 8010 | License and compliance tracking |
| Monitoring & Logging | 8011 | System health and audit trails |
| Integration Service | 8012 | External system connectors |

## Development Workflow

### 1. Starting Development

Start all services:
```bash
make up-all
```

Watch logs:
```bash
make logs-all
# Or for specific service:
docker-compose logs -f api-gateway
```

### 2. Making Changes

The services are configured with hot-reload:
- **Backend**: Changes to Python files automatically restart the service
- **Frontend**: Changes are instantly reflected via Vite HMR

### 3. Running Tests

Run all tests:
```bash
make test
```

Run tests for a specific service:
```bash
cd services/api-gateway
pytest tests/
```

Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

### 4. Code Quality

Format code:
```bash
make format
```

Run linting:
```bash
make lint
```

### 5. Database Migrations

Create a new migration:
```bash
cd services/user-management
alembic revision --autogenerate -m "Add user preferences table"
```

Apply migrations:
```bash
alembic upgrade head
```

### 6. Debugging

#### Backend Services

1. Add breakpoint in code:
   ```python
   import pdb; pdb.set_trace()
   ```

2. Attach to container:
   ```bash
   docker attach mams-api-gateway
   ```

#### Frontend

Use browser DevTools or VS Code debugger with the following configuration:
```json
{
  "type": "chrome",
  "request": "launch",
  "name": "Debug Frontend",
  "url": "http://localhost:3000",
  "webRoot": "${workspaceFolder}/frontend/src"
}
```

## Troubleshooting

### Common Issues

#### 1. Services not starting
```bash
# Check service status
make ps-all

# View logs
docker-compose logs <service-name>

# Restart specific service
docker-compose restart <service-name>
```

#### 2. Database connection errors
```bash
# Ensure databases are initialized
./scripts/init-databases.sh

# Check database is running
docker exec -it mams-postgres psql -U mams -d mams_dev
```

#### 3. Port conflicts
```bash
# Find process using port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Change port in docker-compose.yml if needed
```

#### 4. Storage issues
```bash
# Clean up Docker volumes
make clean

# Remove all containers and volumes
docker-compose down -v
```

### Performance Issues

1. **Increase Docker resources**
   - Docker Desktop → Preferences → Resources
   - Allocate at least 8GB RAM and 4 CPUs

2. **Disable unnecessary services**
   ```bash
   # Start only core services
   docker-compose up postgres mongodb redis minio
   ```

3. **Use production builds**
   ```bash
   NODE_ENV=production make build-all
   ```

## IDE Configuration

### VS Code

1. **Open workspace**
   ```bash
   code mams.code-workspace
   ```

2. **Install recommended extensions**
   - When prompted, click "Install All"

3. **Configure Python interpreter**
   - `Cmd/Ctrl + Shift + P` → "Python: Select Interpreter"
   - Choose `.venv/bin/python`

### PyCharm

1. **Open project**
   - File → Open → Select project root

2. **Configure interpreter**
   - Preferences → Project → Python Interpreter
   - Add → Existing Environment → `.venv/bin/python`

3. **Mark directories**
   - Right-click `services/*/src` → Mark as → Sources Root

### Environment Variables in IDE

Create `.env` file in service directory:
```env
PYTHONPATH=/app
DATABASE_URL=postgresql+asyncpg://mams:dev_password@localhost:5432/mams_dev
REDIS_URL=redis://localhost:6379/0
```

## Additional Resources

- [API Documentation](http://localhost:8000/docs)
- [Architecture Overview](../planning.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [Service-specific READMEs](../services/)

## Getting Help

1. Check service logs: `docker-compose logs <service>`
2. Review [Troubleshooting](#troubleshooting) section
3. Search existing GitHub issues
4. Create a new issue with:
   - Error messages
   - Steps to reproduce
   - Environment details

---

Happy coding! 🚀