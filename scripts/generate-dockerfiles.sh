#!/bin/bash

# Script to generate Dockerfiles for all services

SERVICES=(
    "api-gateway:8000"
    "user-management:8001"
    "storage-abstraction:8002"
    "asset-management:8003"
    "metadata-service:8004"
    "search-engine:8005"
    "ingest-service:8006"
    "proxy-generation:8007"
    "workflow-engine:8008"
    "ai-ml-service:8009"
    "rights-management:8010"
    "monitoring-logging:8011"
    "integration-service:8012"
)

# Template for Python service Dockerfile
create_python_dockerfile() {
    local service=$1
    local port=$2
    
    cat > "services/$service/Dockerfile" << EOF
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONPATH=/app \\
    SERVICE_NAME=$service \\
    SERVICE_PORT=$port

# Expose port
EXPOSE $port

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:$port/health || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "$port"]
EOF
    
    echo "Created Dockerfile for $service"
}

# Template for dockerignore
create_dockerignore() {
    local service=$1
    
    cat > "services/$service/.dockerignore" << 'EOF'
**/__pycache__
**/*.pyc
**/*.pyo
**/*.pyd
.Python
*.egg-info/
.pytest_cache/
.mypy_cache/
.coverage
htmlcov/
.env
.venv
env/
venv/
ENV/
.git/
.gitignore
.dockerignore
Dockerfile
docker-compose*.yml
README.md
tests/
docs/
.vscode/
.idea/
*.log
*.sqlite3
*.db
EOF
    
    echo "Created .dockerignore for $service"
}

# Generate files for each service
for service_config in "${SERVICES[@]}"; do
    IFS=':' read -r service port <<< "$service_config"
    create_python_dockerfile "$service" "$port"
    create_dockerignore "$service"
done

# Create frontend Dockerfile
cat > "frontend/Dockerfile" << 'EOF'
# Build stage
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build application
RUN npm run build

# Runtime stage
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
EOF

echo "Created Dockerfile for frontend"

# Create frontend dockerignore
cat > "frontend/.dockerignore" << 'EOF'
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.git/
.gitignore
.dockerignore
Dockerfile
README.md
.env
.env.local
dist/
build/
coverage/
.vscode/
.idea/
*.log
EOF

echo "Created .dockerignore for frontend"

echo "All Dockerfiles generated successfully!"