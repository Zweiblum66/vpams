# MAMS - Digital Media Asset Management System

## Overview

MAMS (Media Asset Management System) is an enterprise-grade, cloud-native platform designed to revolutionize how organizations manage, process, and distribute digital media content. Built with a microservices architecture, it combines traditional MAM capabilities with modern AI-driven features and seamless editorial workflow integration.

## Architecture

MAMS is built using a microservices architecture with the following core services:

1. **API Gateway Service** - Central entry point, authentication, rate limiting
2. **User Management Service** - Users, roles, permissions, auth providers
3. **Storage Abstraction** - Unified interface for multiple storage backends
4. **Asset Management** - Core asset CRUD, versions, relationships, projects
5. **Metadata Service** - Flexible schemas, extraction, enrichment
6. **Search Engine** - Full-text, semantic, visual similarity search
7. **Ingest Service** - Multi-source ingestion, validation, processing
8. **Proxy Generation** - Video/audio proxies, thumbnails, waveforms
9. **Workflow Engine** - Automation, approvals, custom workflows
10. **AI/ML Service** - Auto-tagging, transcription, recommendations
11. **Rights Management** - License tracking, compliance, usage rights
12. **Monitoring & Logging** - System health, audit trails, analytics
13. **Integration Service** - NLE/DAW exports, external system connectors

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Databases**: PostgreSQL, MongoDB, OpenSearch, Redis, TimescaleDB
- **Message Queue**: RabbitMQ
- **Container**: Docker, Kubernetes

### Frontend
- **Framework**: React 18 with TypeScript
- **State Management**: Redux Toolkit
- **UI Library**: Material-UI (MUI) v5
- **Build Tool**: Vite

## Getting Started

### Prerequisites
- Docker >= 24.0
- Docker Compose >= 2.23
- Python >= 3.11
- Node.js >= 20.0 LTS
- Git >= 2.40

### Local Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd MyVideoMAM
```

2. Start the development environment:
```bash
docker-compose up -d
```

3. Initialize the databases:
```bash
./scripts/init-databases.sh
```

4. Access the services:
- API Gateway: http://localhost:8000
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/docs

## Project Structure

```
MyVideoMAM/
├── services/              # Microservices
│   ├── api-gateway/
│   ├── user-management/
│   ├── storage-abstraction/
│   └── ...
├── frontend/             # React frontend application
├── infrastructure/       # Docker, K8s, Terraform configs
├── scripts/             # Utility scripts
├── docs/                # Documentation
└── docker-compose.yml   # Local development orchestration
```

## Documentation

- [Planning Document](./planning.md) - Detailed project planning and roadmap
- [Development Guide](./CLAUDE.md) - Development standards and patterns
- [Tasks](./tasks.md) - Complete task breakdown by milestone

## License

Copyright (c) 2024 MAMS Project. All rights reserved.