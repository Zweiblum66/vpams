# Metadata Service

The Metadata Service handles flexible metadata schemas, extraction, and enrichment for the MAMS platform. It provides a MongoDB-based storage system for custom metadata schemas and supports automatic extraction of technical metadata from media files.

## Features

- **Flexible Schema Management**: Create and manage custom metadata schemas
- **MongoDB Storage**: Leverages MongoDB for flexible, document-based metadata storage
- **Technical Metadata Extraction**: Automatic extraction using FFprobe and ExifTool
- **Schema Validation**: Strict validation of metadata against defined schemas
- **Search Integration**: Full-text and structured search capabilities
- **Caching**: Redis-based caching for improved performance
- **Asset Integration**: Seamless integration with Asset Management Service

## API Endpoints

### Schema Management
- `GET /api/v1/schemas` - List metadata schemas
- `POST /api/v1/schemas` - Create new schema
- `GET /api/v1/schemas/{schema_id}` - Get specific schema
- `PUT /api/v1/schemas/{schema_id}` - Update schema
- `DELETE /api/v1/schemas/{schema_id}` - Delete schema

### Metadata Operations
- `GET /api/v1/metadata/asset/{asset_id}` - Get metadata for asset
- `POST /api/v1/metadata` - Create metadata
- `PUT /api/v1/metadata/{metadata_id}` - Update metadata
- `DELETE /api/v1/metadata/{metadata_id}` - Delete metadata

### Extraction
- `POST /api/v1/extract/technical/{asset_id}` - Extract technical metadata

### Search
- `POST /api/v1/search/metadata` - Search metadata with MongoDB queries

## Configuration

Copy `.env.example` to `.env` and update values:

```bash
cp .env.example .env
```

Key configurations:
- `MONGODB_URL`: MongoDB connection string
- `REDIS_URL`: Redis connection for caching
- `JWT_SECRET_KEY`: Secret key for JWT validation
- `ENABLE_AUTO_EXTRACTION`: Enable automatic metadata extraction

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run with hot reload
uvicorn src.main:app --reload --port 8005
```

### Running with Docker

```bash
# Build image
docker build -t mams-metadata-service .

# Run container
docker run -p 8005:8005 --env-file .env mams-metadata-service
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_schemas.py
```

## Schema Definition Example

```json
{
  "name": "video_metadata",
  "description": "Standard metadata schema for video assets",
  "asset_types": ["video"],
  "fields": [
    {
      "name": "title",
      "display_name": "Title",
      "field_type": "string",
      "required": true,
      "searchable": true
    },
    {
      "name": "duration",
      "display_name": "Duration",
      "field_type": "float",
      "required": false,
      "validation_rules": {
        "min": 0
      }
    },
    {
      "name": "tags",
      "display_name": "Tags",
      "field_type": "array",
      "array_type": "string",
      "searchable": true,
      "facetable": true
    }
  ]
}
```

## MongoDB Collections

- `metadata_schemas`: Schema definitions
- `metadata`: Actual metadata documents
- `technical_metadata`: Extracted technical metadata
- `extraction_tasks`: Async extraction task tracking

## Integration Points

### Asset Management Service
- Validates asset existence before metadata operations
- Subscribes to asset deletion events for cleanup

### Storage Service
- Retrieves files for metadata extraction
- Accesses file information for technical metadata

### Search Engine
- Indexes metadata for full-text search
- Provides faceted search capabilities

## Performance Considerations

- MongoDB indexes on frequently queried fields
- Redis caching for schema definitions
- Batch operations for bulk metadata updates
- Async extraction processing

## Security

- JWT token validation for all endpoints
- Schema-based validation to prevent injection
- Rate limiting per user
- Audit logging for all operations