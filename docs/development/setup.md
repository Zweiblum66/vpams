# Development Setup Guide

## Overview

This guide covers setting up a local development environment for MAMS, including IDE configuration, debugging setup, and development best practices.

## Prerequisites

### Required Software

- **Git**: 2.30+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+
- **Node.js**: 18+ (LTS)
- **PostgreSQL Client**: 15+
- **Redis CLI**: 6.2+

### Recommended IDEs

- **Backend**: PyCharm Professional / VS Code with Python extension
- **Frontend**: WebStorm / VS Code with React extensions
- **Database**: DataGrip / pgAdmin / DBeaver

## Initial Setup

### 1. Clone Repository

```bash
# Clone with SSH (recommended)
git clone git@github.com:your-org/mams.git
cd mams

# Or with HTTPS
git clone https://github.com/your-org/mams.git
cd mams
```

### 2. Set Up Git Hooks

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Install commit message hook
cp scripts/commit-msg .git/hooks/
chmod +x .git/hooks/commit-msg
```

### 3. Environment Setup

```bash
# Copy environment templates
cp .env.example .env
cp frontend/.env.example frontend/.env

# Generate development secrets
./scripts/generate-dev-secrets.sh

# Create necessary directories
mkdir -p data/{postgres,mongodb,opensearch,redis,minio,logs}
```

## Backend Development

### 1. Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
pip install -e .  # Install package in editable mode
```

### 2. IDE Configuration (VS Code)

Create `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "88"],
  "python.sortImports.args": ["--profile", "black"],
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".pytest_cache": true,
    ".mypy_cache": true
  }
}
```

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "API Gateway",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "cwd": "${workspaceFolder}/services/api-gateway",
      "envFile": "${workspaceFolder}/.env",
      "console": "integratedTerminal"
    },
    {
      "name": "Debug Current Service",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--reload"
      ],
      "cwd": "${fileDirname}",
      "envFile": "${workspaceFolder}/.env",
      "console": "integratedTerminal"
    }
  ]
}
```

### 3. Running Services Locally

#### Option 1: Docker Compose (Recommended)

```bash
# Start all services
docker-compose up

# Start specific services
docker-compose up api-gateway user-management

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f api-gateway

# Rebuild after changes
docker-compose build api-gateway
docker-compose up api-gateway
```

#### Option 2: Native Python

```bash
# Start databases with Docker
docker-compose up -d postgres mongodb opensearch redis minio

# Run service natively
cd services/api-gateway
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# In another terminal
cd services/user-management
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 4. Database Management

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U mams_user -d mams_dev

# Run migrations
cd services/api-gateway
alembic upgrade head

# Create new migration
alembic revision -m "Add new table"

# Rollback migration
alembic downgrade -1
```

### 5. Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_auth.py::test_login

# Run tests in watch mode
ptw

# Run tests in parallel
pytest -n auto
```

## Frontend Development

### 1. Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# The app will be available at http://localhost:3000
```

### 2. VS Code Configuration

Create `frontend/.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.tsdk": "node_modules/typescript/lib",
  "typescript.enablePromptUseWorkspaceTsdk": true,
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### 3. Component Development

```bash
# Generate new component
npm run generate:component MyComponent

# Run Storybook for component development
npm run storybook

# Run tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run E2E tests
npm run test:e2e
```

### 4. State Management

Using Redux Toolkit:

```typescript
// src/store/slices/assetSlice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { assetApi } from '../../api/assetApi';

export const fetchAssets = createAsyncThunk(
  'assets/fetchAssets',
  async (params: AssetParams) => {
    const response = await assetApi.getAssets(params);
    return response.data;
  }
);

const assetSlice = createSlice({
  name: 'assets',
  initialState: {
    items: [],
    loading: false,
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchAssets.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchAssets.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload;
      })
      .addCase(fetchAssets.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      });
  },
});
```

## Development Workflow

### 1. Branch Strategy

```bash
# Create feature branch
git checkout -b feature/SERVICE-123-add-user-export

# Create bugfix branch
git checkout -b bugfix/SERVICE-456-fix-login-error

# Create hotfix branch
git checkout -b hotfix/SERVICE-789-security-patch
```

### 2. Commit Convention

Follow Conventional Commits:

```bash
# Features
git commit -m "feat(user): add bulk user import functionality"

# Bug fixes
git commit -m "fix(auth): resolve token expiration issue"

# Documentation
git commit -m "docs(api): update authentication endpoints"

# Performance
git commit -m "perf(search): optimize query performance"

# Refactoring
git commit -m "refactor(storage): simplify file upload logic"
```

### 3. Code Quality

```bash
# Run linting
flake8 services/
black services/ --check
isort services/ --check-only
mypy services/

# Run security checks
bandit -r services/
safety check

# Run all checks
./scripts/quality-check.sh
```

## Debugging

### 1. Backend Debugging (VS Code)

Add breakpoints in code and use launch configuration:

```python
# Add debugging statements
import pdb; pdb.set_trace()  # For terminal debugging

# Or use VS Code breakpoints
# Click on line number to add breakpoint
```

### 2. Frontend Debugging

```javascript
// Chrome DevTools
debugger;  // Pause execution

// Console logging with styling
console.log('%c Debug Info ', 'background: #222; color: #bada55', data);

// React DevTools
// Install React Developer Tools Chrome extension
```

### 3. Database Debugging

```sql
-- Enable query logging in PostgreSQL
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();

-- View slow queries
SELECT query, calls, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### 4. Docker Debugging

```bash
# Enter running container
docker-compose exec api-gateway bash

# View container processes
docker-compose exec api-gateway ps aux

# Check container resources
docker stats

# Debug networking
docker-compose exec api-gateway netstat -tulpn
```

## Performance Profiling

### 1. Python Profiling

```python
# Using cProfile
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
result = expensive_operation()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

### 2. Frontend Profiling

```javascript
// React Profiler
import { Profiler } from 'react';

function onRenderCallback(id, phase, actualDuration) {
  console.log(`${id} (${phase}) took ${actualDuration}ms`);
}

<Profiler id="AssetList" onRender={onRenderCallback}>
  <AssetList />
</Profiler>
```

### 3. Database Query Analysis

```sql
-- Explain query plan
EXPLAIN ANALYZE
SELECT * FROM assets
WHERE project_id = '123'
AND created_at > '2024-01-01';

-- Find missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
AND n_distinct > 100
AND correlation < 0.1
ORDER BY n_distinct DESC;
```

## Local Services Configuration

### 1. MinIO (S3-compatible storage)

```bash
# Access MinIO console
# URL: http://localhost:9001
# Username: minioadmin
# Password: minioadmin

# Create buckets via CLI
docker-compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker-compose exec minio mc mb local/mams-assets
docker-compose exec minio mc mb local/mams-temp
```

### 2. OpenSearch

```bash
# Access OpenSearch Dashboard
# URL: http://localhost:5601
# Username: admin
# Password: admin

# Create indices
curl -X PUT "localhost:9200/assets" -H 'Content-Type: application/json' -d @mappings/assets.json
```

### 3. Redis

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Monitor Redis commands
docker-compose exec redis redis-cli monitor

# Check memory usage
docker-compose exec redis redis-cli info memory
```

## Development Tools

### 1. API Testing (HTTPie)

```bash
# Install HTTPie
pip install httpie

# Test endpoints
http POST localhost:8000/api/v1/auth/login email=test@example.com password=password

# With authentication
http GET localhost:8000/api/v1/assets "Authorization: Bearer $TOKEN"

# Upload file
http --form POST localhost:8000/api/v1/assets/upload \
  "Authorization: Bearer $TOKEN" \
  file@/path/to/file.mp4 \
  name="Test Video"
```

### 2. Database GUI

```bash
# pgAdmin
docker run -d \
  -p 5050:80 \
  -e PGADMIN_DEFAULT_EMAIL=admin@example.com \
  -e PGADMIN_DEFAULT_PASSWORD=admin \
  dpage/pgadmin4

# Access at http://localhost:5050
```

### 3. Load Testing

```bash
# Install Locust
pip install locust

# Create locustfile.py
from locust import HttpUser, task, between

class MAMSUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def list_assets(self):
        self.client.get("/api/v1/assets")
    
    @task
    def search_assets(self):
        self.client.get("/api/v1/search?q=video")

# Run load test
locust -f locustfile.py --host=http://localhost:8000
```

## Troubleshooting Development Issues

### Common Problems

1. **Port already in use**
   ```bash
   # Find process using port
   lsof -i :8000
   # Kill process
   kill -9 <PID>
   ```

2. **Docker compose issues**
   ```bash
   # Clean up everything
   docker-compose down -v
   docker system prune -a
   ```

3. **Python dependency conflicts**
   ```bash
   # Recreate virtual environment
   deactivate
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements-dev.txt
   ```

4. **Database connection errors**
   ```bash
   # Check if postgres is running
   docker-compose ps postgres
   # Check logs
   docker-compose logs postgres
   ```

## Best Practices

1. **Always work in a virtual environment**
2. **Run tests before committing**
3. **Use pre-commit hooks**
4. **Keep dependencies up to date**
5. **Document your code**
6. **Follow the style guide**
7. **Review your own code first**
8. **Write meaningful commit messages**

---

For more information:
- [Code Style Guide](./code-style.md)
- [Testing Guide](./testing.md)
- [API Development](./api-development.md)
- [Contributing Guidelines](../CONTRIBUTING.md)