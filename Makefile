.PHONY: help up down restart logs ps clean build test lint format

# Default target
help:
	@echo "MAMS Development Commands:"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - Show logs for all services"
	@echo "  make ps          - Show running services"
	@echo "  make clean       - Clean up volumes and containers"
	@echo "  make build       - Build all Docker images"
	@echo "  make test        - Run all tests"
	@echo "  make lint        - Run linting checks"
	@echo "  make format      - Format code"
	@echo "  make init-db     - Initialize databases"
	@echo "  make dev-install - Install development dependencies"

# Docker commands
up:
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@echo "Services are running!"
	@echo "API Gateway: http://localhost:8000"
	@echo "MinIO Console: http://localhost:9001"
	@echo "RabbitMQ Management: http://localhost:15672"
	@echo "OpenSearch Dashboards: http://localhost:5601"
	@echo "Grafana: http://localhost:3001"
	@echo "Prometheus: http://localhost:9090"

up-all:
	docker-compose -f docker-compose.yml -f docker-compose.services.yml up -d
	@echo "Waiting for all services to be healthy..."
	@sleep 20
	@echo "All services are running!"
	@echo "Frontend: http://localhost:3000"
	@echo "API Gateway: http://localhost:8000"
	@echo "Services running on ports 8001-8012"

down:
	docker-compose down

down-all:
	docker-compose -f docker-compose.yml -f docker-compose.services.yml down

restart:
	docker-compose restart

restart-all:
	docker-compose -f docker-compose.yml -f docker-compose.services.yml restart

logs:
	docker-compose logs -f

logs-all:
	docker-compose -f docker-compose.yml -f docker-compose.services.yml logs -f

ps:
	docker-compose ps

ps-all:
	docker-compose -f docker-compose.yml -f docker-compose.services.yml ps

clean:
	docker-compose -f docker-compose.yml -f docker-compose.services.yml down -v
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:
	docker-compose build

build-all:
	docker-compose -f docker-compose.yml -f docker-compose.services.yml build

# Development commands
test:
	@echo "Running tests for all services..."
	@for service in services/*/; do \
		if [ -f "$$service/requirements.txt" ]; then \
			echo "Testing $$service..."; \
			cd $$service && python -m pytest tests/ && cd ../..; \
		fi \
	done

lint:
	@echo "Running linting checks..."
	@python -m ruff check services/
	@python -m black --check services/
	@python -m mypy services/

format:
	@echo "Formatting code..."
	@python -m black services/
	@python -m ruff check --fix services/

# Database initialization
init-db:
	@echo "Initializing databases..."
	@./scripts/init-databases.sh

# Development setup
dev-install:
	@echo "Installing development dependencies..."
	pip install -r requirements-dev.txt
	cd frontend && npm install

# Service-specific commands
api-gateway:
	cd services/api-gateway && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

user-management:
	cd services/user-management && uvicorn src.main:app --reload --host 0.0.0.0 --port 8001

frontend-dev:
	cd frontend && npm run dev