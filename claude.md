# Claude Development Guide - MAMS Project

## Project Overview

**Project Name**: Digital Media Asset Management System (MAMS)  
**Type**: Enterprise-grade microservices-based media management platform  
**Purpose**: Comprehensive media asset management with integrated editorial workflow capabilities  
**Target Users**: Broadcast companies, production houses, news organizations, content creators

- always read planning.md at the start of every new conversation
- check tsks.md before starting your work
- mark completd tasksimmediately
- add newly discovered tasks

## Quick Start for Development

When implementing any MAMS component, follow this pattern:
1. Check this guide for architecture and standards
2. Reference the service-specific requirements below
3. Use the established patterns for consistency
4. Implement comprehensive error handling and logging
5. Include unit tests with minimum 90% coverage

## Core Architecture

### Microservices (12 Total)
```
1. API Gateway Service       - Central entry point, auth, rate limiting
2. User Management Service   - Users, roles, permissions, auth providers
3. Storage Abstraction       - Unified interface for multiple storage backends
4. Asset Management         - Core asset CRUD, versions, relationships, projects
5. Metadata Service         - Flexible schemas, extraction, enrichment
6. Search Engine           - Full-text, semantic, visual similarity search
7. Ingest Service          - Multi-source ingestion, validation, processing
8. Proxy Generation        - Video/audio proxies, thumbnails, waveforms
9. Workflow Engine         - Automation, approvals, custom workflows
10. AI/ML Service          - Auto-tagging, transcription, recommendations
11. Rights Management      - License tracking, compliance, usage rights
12. Monitoring & Logging   - System health, audit trails, analytics
13. Integration Service    - NLE/DAW exports, external system connectors
```

### Technology Stack

#### Backend
- **Framework**: FastAPI (all services)
- **Language**: Python 3.11+
- **Async**: asyncio, aiohttp, aiofiles
- **Validation**: Pydantic models
- **API Docs**: Auto-generated OpenAPI 3.0

#### Databases
- **Primary**: PostgreSQL 15+ (relational data)
- **Metadata**: MongoDB (flexible schemas)
- **Search**: OpenSearch (formerly Elasticsearch)
- **Cache**: Redis (sessions, rate limiting, caching)
- **Time-series**: TimescaleDB (metrics, analytics)

#### Infrastructure
- **Container**: Docker, Docker Compose
- **Orchestration**: Kubernetes (production)
- **Message Queue**: RabbitMQ or Redis Pub/Sub
- **Object Storage**: S3-compatible (MinIO for dev)
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (OpenSearch, Logstash, Kibana)

#### Frontend
- **Framework**: React 18 with TypeScript
- **State**: Redux Toolkit with RTK Query
- **UI**: Material-UI (MUI) v5
- **Build**: Vite
- **Testing**: Jest, React Testing Library

## Service Implementation Patterns

### Standard Service Structure
```python
project-root/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py        # FastAPI routes
│   │   └── dependencies.py  # Shared dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py       # Settings with Pydantic
│   │   ├── security.py     # Auth/security utilities
│   │   └── exceptions.py   # Custom exceptions
│   ├── models/
│   │   ├── __init__.py
│   │   ├── domain.py       # Business logic models
│   │   └── schemas.py      # Pydantic schemas
│   ├── services/
│   │   ├── __init__.py
│   │   └── {feature}.py    # Business logic
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py         # Database setup
│   │   └── models.py       # SQLAlchemy models
│   └── main.py             # FastAPI app entry
├── tests/
├── Dockerfile
├── requirements.txt
└── docker-compose.yml
```

### API Route Pattern
```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])

@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset: AssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new asset with proper error handling."""
    try:
        return await asset_service.create(db, asset, current_user)
    except DuplicateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create asset: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Database Models Pattern
```python
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    metadata = relationship("AssetMetadata", back_populates="asset", cascade="all, delete-orphan")
    versions = relationship("AssetVersion", back_populates="asset", order_by="desc(AssetVersion.version)")
```

## Key Design Decisions

### 1. Authentication & Authorization
- JWT tokens with 1-hour expiration and refresh tokens
- RBAC with fine-grained permissions
- Support for multiple auth providers (Local, LDAP, SAML, OAuth)
- Optional MFA for enterprise deployments

### 2. Storage Architecture
- Abstraction layer supporting multiple backends
- Storage tiers: hot, warm, cold, archive
- Transparent file access regardless of location
- Support for: Local FS, NAS, S3, Azure Blob, GCS, Dropbox, OneDrive

### 3. Project Structure
```sql
-- Hierarchical project organization
project_containers (id, name, type, parent_id)
  └── types: project, folder, bin, shotlist, sequence

-- Editorial workflow support  
shot_items (id, container_id, asset_id, in_point, out_point, metadata)
sequence_timeline (id, sequence_id, track_type, clip_id, start_time)
```

### 4. Search Strategy
- OpenSearch for full-text and metadata search
- AI-powered semantic search
- Visual similarity search for images
- Timecode-based search for video
- Natural language query processing

### 5. Media Processing
- FFmpeg for video/audio processing
- GPU acceleration when available
- Multiple proxy qualities (low, medium, edit)
- Progressive streaming support
- Thumbnail and waveform generation

## API Endpoint Patterns

### RESTful Conventions
```
GET    /api/v1/{resource}          # List with pagination
POST   /api/v1/{resource}          # Create new
GET    /api/v1/{resource}/{id}     # Get single
PUT    /api/v1/{resource}/{id}     # Update (full)
PATCH  /api/v1/{resource}/{id}     # Update (partial)
DELETE /api/v1/{resource}/{id}     # Delete

# Nested resources
GET    /api/v1/{resource}/{id}/{nested}
POST   /api/v1/{resource}/{id}/{nested}

# Actions
POST   /api/v1/{resource}/{id}/{action}
```

### Standard Query Parameters
- `?page=1&limit=20` - Pagination
- `?sort=created_at&order=desc` - Sorting
- `?filter[status]=active` - Filtering
- `?include=metadata,versions` - Relationship loading
- `?fields=id,name,created_at` - Field selection

### Response Format
```json
{
  "data": {...} or [...],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  },
  "links": {
    "self": "...",
    "next": "...",
    "prev": "..."
  }
}
```

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Asset not found",
    "details": {
      "asset_id": "123e4567-e89b-12d3-a456-426614174000"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

### HTTP Status Codes
- 200: Success
- 201: Created
- 204: No Content (successful delete)
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 409: Conflict
- 422: Validation Error
- 429: Rate Limited
- 500: Internal Server Error

## Testing Standards

### Unit Test Example
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_asset(client: AsyncClient, auth_headers):
    """Test asset creation with valid data."""
    data = {
        "name": "test_video.mp4",
        "file_path": "/storage/test_video.mp4",
        "type": "video"
    }
    
    response = await client.post(
        "/api/v1/assets",
        json=data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    assert response.json()["data"]["name"] == data["name"]
```

### Test Coverage Requirements
- Minimum 90% code coverage
- All API endpoints must have tests
- Include edge cases and error scenarios
- Mock external dependencies

## Integration Points

### NLE/DAW Export Formats
- **AAF**: Avid Media Composer
- **XML**: Adobe Premiere Pro (FCP7 XML)
- **EDL**: Traditional edit decision lists
- **OTIO**: OpenTimelineIO (DaVinci Resolve)
- **OMF**: Pro Tools and audio DAWs

### External Systems
- **Storage**: S3, Azure, GCS APIs
- **Auth**: LDAP, SAML, OAuth2 providers
- **Newsroom**: MOS protocol
- **Streaming**: HLS, DASH, SRT
- **Archive**: Archiware, Telestream DIVA

## Development Workflow

### 1. Feature Development
```bash
# Create feature branch
git checkout -b feature/SERVICE-STORY_ID-description

# Development with hot reload
docker-compose up service-name

# Run tests
docker-compose run service-name pytest

# Commit with conventional commits
git commit -m "feat(service): add new capability"
```

### 2. Environment Variables
```env
# Service configuration
SERVICE_NAME=asset-management
SERVICE_PORT=8001
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/mams
MONGODB_URL=mongodb://mongo:27017/mams
REDIS_URL=redis://redis:6379/0

# Storage
STORAGE_TYPE=s3
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

# Auth
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
```

### 3. Docker Compose Services
```yaml
version: '3.8'
services:
  service-name:
    build: ./services/service-name
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./services/service-name:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Performance Considerations

### 1. Database
- Use connection pooling
- Implement query optimization
- Add appropriate indexes
- Use async database operations

### 2. Caching Strategy
- Redis for session data
- Cache frequently accessed metadata
- Implement cache invalidation
- Use ETags for HTTP caching

### 3. File Operations
- Chunked uploads/downloads
- Async file operations
- Progress tracking
- Resume capability

### 4. Scaling
- Horizontal scaling for services
- Load balancing with health checks
- Message queue for async tasks
- Database read replicas

## Security Guidelines

### 1. Authentication
- Secure password hashing (bcrypt)
- JWT token rotation
- Session management
- Rate limiting per user/IP

### 2. Authorization
- Role-based access control (RBAC)
- Resource-level permissions
- API key management
- Audit all access

### 3. Data Protection
- Encryption at rest
- TLS for all communications
- Input validation
- SQL injection prevention

### 4. Compliance
- GDPR data handling
- Right to deletion
- Data export capabilities
- Audit trail maintenance

## Monitoring & Logging

### 1. Structured Logging
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "asset_created",
    asset_id=asset.id,
    user_id=current_user.id,
    size_bytes=file_size,
    duration_ms=processing_time
)
```

### 2. Metrics Collection
```python
from prometheus_client import Counter, Histogram

asset_uploads = Counter('mams_asset_uploads_total', 'Total asset uploads')
upload_duration = Histogram('mams_upload_duration_seconds', 'Upload duration')

@upload_duration.time()
async def upload_asset():
    asset_uploads.inc()
    # ... upload logic
```

### 3. Health Checks
```python
@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute("SELECT 1")
        return {"status": "healthy", "service": "asset-management"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )
```

## Quick Reference

### Common Imports
```python
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
```

### Database Session
```python
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### Current User Dependency
```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # Validate token and return user
    pass
```

### Pagination
```python
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit
```

## Notes for Future Sessions

1. **Always check this guide first** when implementing new features
2. **Maintain consistency** with established patterns
3. **Include comprehensive error handling** in all endpoints
4. **Write tests** for all new functionality
5. **Document** any deviations from these patterns
6. **Update this guide** when making architectural changes

Remember: MAMS is an enterprise system - prioritize reliability, scalability, and maintainability over quick solutions.
