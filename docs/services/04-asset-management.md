# Asset Management Service

## Overview

The Asset Management Service is the core of MAMS, responsible for managing the lifecycle of all digital media assets. It provides comprehensive CRUD operations, version control, relationship management, and project organization capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Asset Management Service                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   API Layer  │  │Service Layer │  │ Repository Layer│  │
│  │             │  │              │  │                 │  │
│  │  - Routes   │  │ - Business   │  │ - Asset DAO     │  │
│  │  - Validation│  │   Logic      │  │ - Version DAO   │  │
│  │  - Auth     │  │ - Workflows  │  │ - Project DAO   │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                  Database Layer                       │  │
│  │         PostgreSQL (Assets, Versions, Projects)      │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                Integration Layer                      │  │
│  │   Storage Service │ Metadata Service │ Search Service│  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Asset Lifecycle Management
- **Creation**: Upload and registration of new assets
- **Updates**: Metadata and file updates with version tracking
- **Archival**: Move assets to long-term storage
- **Deletion**: Soft and hard delete with retention policies

### 2. Version Control
- Automatic versioning on updates
- Version comparison and diff
- Rollback to previous versions
- Branch and merge capabilities

### 3. Relationship Management
- Parent-child relationships
- Asset collections and groups
- Cross-references and links
- Dependency tracking

### 4. Project Organization
- Hierarchical project structure
- Folders and bins
- Shared project spaces
- Access control per project

## API Endpoints

### Asset Operations

#### Create Asset
```http
POST /api/v1/assets
Content-Type: multipart/form-data
Authorization: Bearer {token}

Form Data:
- file: (binary)
- name: string
- project_id: uuid (optional)
- metadata: json (optional)
- auto_process: boolean (default: true)
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "marketing-video.mp4",
  "type": "video",
  "mime_type": "video/mp4",
  "size": 52428800,
  "status": "processing",
  "storage_location": "s3://mams-assets/2024/01/550e8400.mp4",
  "created_at": "2024-01-15T10:30:00Z",
  "created_by": "user-123",
  "project_id": "660e8400-e29b-41d4-a716-446655440000",
  "version": 1,
  "processing_status": {
    "proxy_generation": "pending",
    "metadata_extraction": "pending",
    "virus_scan": "completed"
  }
}
```

#### Get Asset
```http
GET /api/v1/assets/{asset_id}
Authorization: Bearer {token}

Query Parameters:
- include: string (comma-separated: metadata,versions,permissions,project)
- version: integer (specific version number)
```

#### Update Asset
```http
PUT /api/v1/assets/{asset_id}
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "Updated Name",
  "description": "New description",
  "metadata": {
    "custom_field": "value"
  },
  "create_version": true
}
```

#### Delete Asset
```http
DELETE /api/v1/assets/{asset_id}
Authorization: Bearer {token}

Query Parameters:
- permanent: boolean (default: false)
- delete_versions: boolean (default: false)
```

### Batch Operations

#### Batch Update
```http
POST /api/v1/assets/batch/update
Content-Type: application/json
Authorization: Bearer {token}

{
  "asset_ids": ["id1", "id2", "id3"],
  "updates": {
    "metadata": {
      "status": "approved"
    },
    "tags": ["reviewed", "final"]
  }
}
```

#### Batch Move
```http
POST /api/v1/assets/batch/move
Content-Type: application/json
Authorization: Bearer {token}

{
  "asset_ids": ["id1", "id2", "id3"],
  "target_project_id": "project-id",
  "target_folder_id": "folder-id"
}
```

### Version Management

#### List Versions
```http
GET /api/v1/assets/{asset_id}/versions
Authorization: Bearer {token}
```

#### Create Version
```http
POST /api/v1/assets/{asset_id}/versions
Content-Type: multipart/form-data
Authorization: Bearer {token}

Form Data:
- file: (binary)
- comment: string
- is_major_version: boolean
```

#### Restore Version
```http
POST /api/v1/assets/{asset_id}/versions/{version_number}/restore
Authorization: Bearer {token}
```

### Relationships

#### Create Relationship
```http
POST /api/v1/assets/{asset_id}/relationships
Content-Type: application/json
Authorization: Bearer {token}

{
  "related_asset_id": "related-asset-id",
  "relationship_type": "derived_from",
  "metadata": {
    "description": "Color corrected version"
  }
}
```

#### Get Related Assets
```http
GET /api/v1/assets/{asset_id}/related
Authorization: Bearer {token}

Query Parameters:
- type: string (relationship type filter)
- direction: string (incoming, outgoing, both)
```

## Data Models

### Asset Model
```typescript
interface Asset {
  id: string;
  name: string;
  type: AssetType;
  mime_type: string;
  size: number;
  checksum: string;
  status: AssetStatus;
  storage_location: string;
  storage_tier: StorageTier;
  
  // Metadata
  description?: string;
  tags: string[];
  custom_metadata: Record<string, any>;
  
  // Technical metadata
  technical_metadata?: {
    width?: number;
    height?: number;
    duration?: number;
    fps?: number;
    codec?: string;
    bitrate?: number;
  };
  
  // Relationships
  project_id?: string;
  folder_id?: string;
  parent_asset_id?: string;
  
  // Version info
  version: number;
  version_comment?: string;
  is_latest_version: boolean;
  
  // Audit fields
  created_at: Date;
  created_by: string;
  updated_at: Date;
  updated_by: string;
  deleted_at?: Date;
  deleted_by?: string;
}
```

### Version Model
```typescript
interface AssetVersion {
  id: string;
  asset_id: string;
  version_number: number;
  file_size: number;
  checksum: string;
  storage_location: string;
  
  // Version metadata
  comment?: string;
  is_major_version: boolean;
  changes: VersionChange[];
  
  // Audit
  created_at: Date;
  created_by: string;
}
```

## Configuration

### Environment Variables
```bash
# Service configuration
ASSET_SERVICE_PORT=8004
ASSET_SERVICE_NAME=asset-management

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/mams_assets

# Storage
DEFAULT_STORAGE_TIER=hot
ARCHIVE_AFTER_DAYS=90

# Processing
AUTO_PROCESS_UPLOADS=true
MAX_UPLOAD_SIZE_GB=50

# Versioning
ENABLE_AUTO_VERSIONING=true
MAX_VERSIONS_PER_ASSET=100
VERSION_RETENTION_DAYS=365
```

### Service Configuration
```yaml
asset_management:
  upload:
    max_size_gb: 50
    allowed_types:
      - video/*
      - image/*
      - audio/*
      - application/pdf
    chunk_size_mb: 10
    
  storage:
    default_tier: hot
    tiers:
      hot:
        max_age_days: 30
      warm:
        max_age_days: 90
      cold:
        max_age_days: 365
      archive:
        max_age_days: null
        
  versioning:
    enabled: true
    auto_version_on_update: true
    max_versions: 100
    retention_policy:
      keep_major_versions: true
      keep_last_n_versions: 10
      
  processing:
    auto_extract_metadata: true
    auto_generate_proxy: true
    auto_index_search: true
```

## Integration Points

### Storage Service Integration
```python
async def store_asset(file_data: bytes, asset: Asset) -> str:
    """Store asset file via Storage Abstraction Service"""
    storage_client = StorageClient()
    
    location = await storage_client.store(
        file_data=file_data,
        key=f"assets/{asset.id}/original",
        tier=asset.storage_tier,
        metadata={
            "asset_id": asset.id,
            "content_type": asset.mime_type,
            "checksum": asset.checksum
        }
    )
    
    return location
```

### Metadata Service Integration
```python
async def extract_metadata(asset: Asset) -> dict:
    """Extract metadata via Metadata Service"""
    metadata_client = MetadataClient()
    
    metadata = await metadata_client.extract(
        file_location=asset.storage_location,
        file_type=asset.type,
        options={
            "extract_technical": True,
            "extract_embedded": True,
            "extract_ai_tags": True
        }
    )
    
    return metadata
```

### Search Service Integration
```python
async def index_asset(asset: Asset) -> None:
    """Index asset in Search Service"""
    search_client = SearchClient()
    
    await search_client.index(
        index="assets",
        document_id=asset.id,
        document={
            "id": asset.id,
            "name": asset.name,
            "type": asset.type,
            "tags": asset.tags,
            "metadata": asset.custom_metadata,
            "created_at": asset.created_at,
            "project_id": asset.project_id
        }
    )
```

## Workflows

### Upload Workflow
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant AssetService
    participant Storage
    participant Queue
    participant Processors
    
    Client->>API: Upload file
    API->>AssetService: Create asset
    AssetService->>Storage: Store file
    Storage-->>AssetService: Storage location
    AssetService->>Queue: Queue processing jobs
    AssetService-->>API: Asset created
    API-->>Client: Asset ID & status
    
    Queue->>Processors: Process jobs
    Processors->>AssetService: Update metadata
    Processors->>Client: Notify completion
```

### Version Creation Workflow
```mermaid
sequenceDiagram
    participant User
    participant API
    participant AssetService
    participant VersionControl
    participant Storage
    
    User->>API: Upload new version
    API->>AssetService: Create version request
    AssetService->>VersionControl: Create version
    VersionControl->>Storage: Store new file
    VersionControl->>VersionControl: Update version chain
    VersionControl-->>AssetService: Version created
    AssetService-->>API: Version details
    API-->>User: Success response
```

## Performance Optimization

### 1. Database Optimization
- Indexes on frequently queried fields
- Partitioning for large tables
- Connection pooling
- Query optimization

### 2. Caching Strategy
```python
# Redis caching for asset metadata
@cache(ttl=300)  # 5 minutes
async def get_asset(asset_id: str) -> Asset:
    return await db.get_asset(asset_id)

# Cache invalidation on updates
async def update_asset(asset_id: str, updates: dict) -> Asset:
    asset = await db.update_asset(asset_id, updates)
    await cache.delete(f"asset:{asset_id}")
    return asset
```

### 3. Batch Processing
- Bulk operations for multiple assets
- Parallel processing for independent operations
- Queue-based asynchronous processing

### 4. Storage Optimization
- Automatic tiering based on access patterns
- Compression for appropriate file types
- Deduplication at storage level

## Monitoring

### Key Metrics
- Upload success rate
- Average upload time
- Storage usage by tier
- Version creation rate
- API response times
- Error rates by endpoint

### Health Checks
```http
GET /health

Response:
{
  "status": "healthy",
  "version": "1.2.3",
  "checks": {
    "database": "ok",
    "storage": "ok",
    "cache": "ok"
  }
}
```

### Logging
- Structured logging with correlation IDs
- Audit logs for all modifications
- Performance logs for slow operations

## Security

### Access Control
- RBAC for asset operations
- Project-based permissions
- Field-level access control

### Data Protection
- Encryption at rest
- Checksum validation
- Virus scanning on upload
- Input validation

### Audit Trail
- All operations logged
- Immutable audit records
- Compliance reporting

## Troubleshooting

### Common Issues

1. **Upload Failures**
   - Check file size limits
   - Verify allowed file types
   - Check storage quota

2. **Version Conflicts**
   - Use optimistic locking
   - Implement conflict resolution
   - Clear version cache

3. **Performance Issues**
   - Monitor database queries
   - Check cache hit rates
   - Review storage tier distribution

### Debug Endpoints
```http
GET /api/v1/assets/{asset_id}/debug
Authorization: Bearer {admin_token}

Response includes:
- Storage details
- Processing status
- Version history
- Cache status
- Recent operations
```

---

For more information:
- [Storage Abstraction Service](./03-storage-abstraction.md)
- [Metadata Service](./05-metadata.md)
- [Search Engine Service](./06-search-engine.md)
- [API Reference](../api-reference/rest-api.md)