# Asset Management Service

Core service for managing digital media assets in MAMS.

## Features

- **Asset CRUD Operations**: Create, read, update, and delete assets
- **Version Control**: Track all versions of assets with full history
- **Chunked Upload**: Support for large file uploads with resumable capability
- **Bulk Operations**: Update, delete, tag, or move multiple assets at once
- **File Validation**: Comprehensive validation including size, type, and security checks
- **File Type Detection**: Automatic detection using MIME types and file signatures
- **Duplicate Detection**: Identify duplicate assets by hash, name, and size
- **Metadata Management**: Flexible technical metadata storage
- **Tagging System**: Organize assets with tags and collections
- **Hierarchical Organization**: Projects, folders, bins, shotlists, sequences
- **Editorial Workflow**: Shot items, timelines, and sequence editing
- **Project Templates**: Reusable project structures and settings
- **Sharing & Permissions**: Share containers with users/groups with granular permissions
- **Soft Delete**: Safe deletion with recovery option
- **Storage Integration**: Works with Storage Abstraction Service

## API Endpoints

### Upload Operations
- `POST /api/v1/assets/upload/initiate` - Start upload session
- `POST /api/v1/assets/upload/complete` - Complete upload and create asset

### Asset Operations
- `GET /api/v1/assets` - List assets with filtering
- `GET /api/v1/assets/{id}` - Get asset details
- `PATCH /api/v1/assets/{id}` - Update asset metadata
- `DELETE /api/v1/assets/{id}` - Delete asset (soft/hard)

### Bulk Operations
- `POST /api/v1/assets/bulk/update` - Update multiple assets
- `POST /api/v1/assets/bulk/delete` - Delete multiple assets
- `POST /api/v1/assets/bulk/tag` - Add/remove tags on multiple assets
- `POST /api/v1/assets/bulk/move` - Move assets to different project

### Version Management
- `POST /api/v1/assets/{id}/versions/upload/initiate` - Start version upload
- `GET /api/v1/assets/{id}/versions` - List all versions
- `GET /api/v1/assets/{id}/versions/{version}` - Get specific version
- `POST /api/v1/assets/{id}/versions/{version}/set-current` - Set current version
- `DELETE /api/v1/assets/{id}/versions/{version}` - Delete version

### Validation
- `POST /api/v1/assets/validate/filename` - Validate filename before upload
- `POST /api/v1/assets/validate/upload` - Pre-validate upload parameters

### Duplicate Detection
- `POST /api/v1/assets/duplicates/check` - Check for duplicates before upload
- `GET /api/v1/assets/duplicates/statistics` - Get duplicate statistics
- `GET /api/v1/assets/duplicates/groups` - Find duplicate groups
- `POST /api/v1/assets/duplicates/{hash}/suggest-removal` - Get removal suggestions

### Project Containers
- `POST /api/v1/containers` - Create project container
- `GET /api/v1/containers` - List containers with filtering
- `GET /api/v1/containers/{id}` - Get container details
- `GET /api/v1/containers/{id}/tree` - Get container with full hierarchy
- `GET /api/v1/containers/{id}/breadcrumb` - Get breadcrumb navigation trail
- `PATCH /api/v1/containers/{id}` - Update container properties
- `DELETE /api/v1/containers/{id}` - Delete container (soft/hard)
- `POST /api/v1/containers/{id}/move` - Move container to new parent
- `POST /api/v1/containers/from-template` - Create from template
- `GET /api/v1/containers/{id}/stats` - Get container statistics

### Shot Items (Editorial)
- `POST /api/v1/shots` - Create shot item
- `GET /api/v1/containers/{id}/shots` - List shots in container
- `GET /api/v1/shots/{id}` - Get shot details
- `PATCH /api/v1/shots/{id}` - Update shot
- `DELETE /api/v1/shots/{id}` - Delete shot
- `POST /api/v1/shots/bulk/reorder` - Reorder shots

### Sequences & Timelines
- `POST /api/v1/sequences/{id}/timeline` - Add clip to timeline
- `GET /api/v1/sequences/{id}/timeline` - Get sequence timeline
- `PATCH /api/v1/timeline/{id}` - Update timeline item
- `DELETE /api/v1/timeline/{id}` - Remove from timeline
- `POST /api/v1/sequences/{id}/export` - Export sequence

### Project Templates
- `GET /api/v1/templates` - List available templates
- `POST /api/v1/templates` - Create custom template
- `GET /api/v1/templates/categories` - Get all template categories
- `GET /api/v1/templates/{id}` - Get template details
- `PATCH /api/v1/templates/{id}` - Update template
- `DELETE /api/v1/templates/{id}` - Delete template
- `POST /api/v1/templates/{id}/duplicate` - Duplicate template
- `POST /api/v1/templates/system` - Initialize system templates
- `POST /api/v1/containers/from-template` - Create project from template

### Container Sharing
- `POST /api/v1/shares` - Share a container with user/group
- `GET /api/v1/shares` - List user's shares (received/given)
- `GET /api/v1/shares/container/{id}` - List shares for a container
- `GET /api/v1/shares/{id}` - Get share details
- `PATCH /api/v1/shares/{id}` - Update share permissions
- `DELETE /api/v1/shares/{id}` - Revoke share
- `POST /api/v1/shares/cleanup` - Clean up expired shares

### Health Check
- `GET /health` - Service health status

## Configuration

Key environment variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/mams_assets

# Storage Service
STORAGE_SERVICE_URL=http://storage-service:8002

# Security
JWT_SECRET_KEY=your-secret-key

# Upload Settings
MAX_UPLOAD_SIZE=10737418240  # 10GB
CHUNK_SIZE=5242880  # 5MB
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start service
uvicorn src.main:app --reload --port 8003
```

## Docker

```bash
# Build image
docker build -t mams-asset-management .

# Run container
docker run -p 8003:8003 --env-file .env mams-asset-management
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=src --cov-report=html
```