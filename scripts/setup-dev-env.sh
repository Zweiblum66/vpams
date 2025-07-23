#!/bin/bash

# Development Environment Setup Script for MAMS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== MAMS Development Environment Setup ===${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command_exists docker; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

if ! command_exists python3; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.11+.${NC}"
    exit 1
fi

if ! command_exists node; then
    echo -e "${RED}Node.js is not installed. Please install Node.js 20+.${NC}"
    exit 1
fi

echo -e "${GREEN}All prerequisites are installed!${NC}"

# Create virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
python3 -m venv .venv
source .venv/bin/activate

# Install Python development dependencies
echo -e "${YELLOW}Installing Python development dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements-dev.txt

# Install pre-commit hooks
echo -e "${YELLOW}Setting up pre-commit hooks...${NC}"
pre-commit install

# Copy environment file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please update .env file with your configuration${NC}"
fi

# Create necessary directories
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p logs
mkdir -p uploads
mkdir -p models

# Start infrastructure services
echo -e "${YELLOW}Starting infrastructure services...${NC}"
make up

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 15

# Initialize databases
echo -e "${YELLOW}Initializing databases...${NC}"
./scripts/init-databases.sh

# Create sample requirements.txt for services
echo -e "${YELLOW}Creating sample requirements.txt for services...${NC}"
for service in services/*/; do
    if [ ! -f "$service/requirements.txt" ]; then
        cat > "$service/requirements.txt" << EOF
# Core dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
alembic==1.12.1

# Redis
redis[hiredis]==5.0.1

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# HTTP client
httpx==0.25.2

# Logging
structlog==23.2.0

# Monitoring
prometheus-client==0.19.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2
EOF
        echo "Created requirements.txt for $service"
    fi
done

# Create sample main.py for services
echo -e "${YELLOW}Creating sample main.py for services...${NC}"
for service in services/*/; do
    mkdir -p "$service/src"
    if [ ! -f "$service/src/main.py" ]; then
        service_name=$(basename "$service")
        cat > "$service/src/main.py" << EOF
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import structlog

# Configure structured logging
logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title="${service_name} Service",
    description="Microservice for ${service_name}",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.on_event("startup")
async def startup_event():
    logger.info("${service_name} service starting up")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("${service_name} service shutting down")

@app.get("/")
async def root():
    return {"service": "${service_name}", "status": "operational"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "${service_name}"}

@app.get("/api/v1/info")
async def service_info():
    return {
        "service": "${service_name}",
        "version": "0.1.0",
        "description": "Microservice for ${service_name}"
    }
EOF
        echo "Created main.py for $service"
    fi
done

# Setup frontend
echo -e "${YELLOW}Setting up frontend...${NC}"
if [ ! -f "frontend/package.json" ]; then
    cat > "frontend/package.json" << EOF
{
  "name": "mams-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:ci": "vitest run --coverage",
    "lint": "eslint src --ext ts,tsx",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@reduxjs/toolkit": "^2.0.0",
    "react-redux": "^9.0.0",
    "@mui/material": "^5.15.0",
    "@emotion/react": "^11.11.0",
    "@emotion/styled": "^11.11.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@typescript-eslint/eslint-plugin": "^6.13.0",
    "@typescript-eslint/parser": "^6.13.0",
    "@vitejs/plugin-react": "^4.2.0",
    "eslint": "^8.55.0",
    "eslint-plugin-react": "^7.33.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "vitest": "^1.0.0",
    "@vitest/coverage-v8": "^1.0.0"
  }
}
EOF
    echo "Created package.json for frontend"
fi

# Create nginx config for frontend
if [ ! -f "frontend/nginx.conf" ]; then
    cat > "frontend/nginx.conf" << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    
    sendfile on;
    keepalive_timeout 65;
    
    server {
        listen 3000;
        server_name localhost;
        root /usr/share/nginx/html;
        index index.html;
        
        location / {
            try_files $uri $uri/ /index.html;
        }
        
        location /api {
            proxy_pass http://api-gateway:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }
    }
}
EOF
    echo "Created nginx.conf for frontend"
fi

echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo "1. Update .env file with your configuration"
echo "2. Run 'make build-all' to build all Docker images"
echo "3. Run 'make up-all' to start all services"
echo "4. Access the application at http://localhost:3000"
echo ""
echo -e "${YELLOW}Development commands:${NC}"
echo "  make up-all      - Start all services"
echo "  make down-all    - Stop all services"
echo "  make logs-all    - View logs for all services"
echo "  make test        - Run tests"
echo "  make lint        - Run linting"
echo ""
echo -e "${GREEN}Happy coding!${NC}"