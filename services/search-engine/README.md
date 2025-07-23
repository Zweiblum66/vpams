# Search Engine Service

## Overview

The Search Engine Service provides powerful search capabilities for the MAMS platform, enabling users to find media assets through various search methods including full-text search, metadata field search, and advanced boolean queries.

## Features

- **Natural language search** with AI-powered query understanding
- **Advanced fuzzy search** with configurable algorithms and performance modes
- **Phonetic search** with multiple algorithms (Soundex, Metaphone, NYSIIS, Phonex)
- **Synonym search** with multiple expansion strategies and sources (WordNet, custom, contextual)
- **Full-text search** across all indexed content
- **Metadata field search** for targeted searches on specific fields
- **Advanced search** with boolean operators (AND, OR, NOT)
- **Multiple search types**: basic, phrase, fuzzy, fuzzy_phrase, fuzzy_cross_field, wildcard
- **Advanced filtering** with 8 different filter types
- **Faceted search** with 6 aggregation types for data exploration
- **Post-filtering** for UI-driven refinement without affecting facets
- **Real-time indexing** of assets and metadata
- **Search suggestions** for auto-completion
- **Fuzzy suggestions** for typo correction and alternative spellings
- **Search analytics** for comprehensive tracking and reporting
- **Saved searches** for reusable query templates
- **Search history** for user search tracking
- **Multi-index support** (assets, metadata, content)
- **Custom ranking algorithms** with configurable weights
- **Highlighting** of matched terms
- **Source field filtering** for optimized responses
- **Intent detection** for natural language queries
- **Entity extraction** (people, dates, projects, etc.)
- **Temporal understanding** (today, last week, etc.)
- **Technical specification parsing** (4K, 60fps, etc.)
- **Performance analysis** for fuzzy search optimization
- **Adaptive fuzzy matching** that adjusts based on query characteristics

## Architecture

The service is built on:
- **OpenSearch**: Distributed search and analytics engine
- **FastAPI**: Modern Python web framework
- **Async/await**: For high-performance concurrent operations

## API Endpoints

### Search Operations
- `POST /api/v1/search` - Basic search
- `POST /api/v1/search/advanced` - Advanced boolean search
- `POST /api/v1/search/metadata-fields` - Metadata field-specific search
- `POST /api/v1/search/natural-language` - Natural language search with AI
- `POST /api/v1/search/filtered` - Filtered search with facets
- `POST /api/v1/search/fuzzy` - Advanced fuzzy search with configurable parameters
- `POST /api/v1/search/fuzzy/suggestions` - Get fuzzy suggestions for typo correction
- `POST /api/v1/search/phonetic` - Phonetic search for sound-alike matching
- `POST /api/v1/search/phonetic/suggestions` - Get phonetic suggestions and variations
- `POST /api/v1/search/synonym` - Synonym-enhanced search with configurable expansion
- `POST /api/v1/search/synonym/suggestions` - Get synonym suggestions for terms
- `GET /api/v1/search/synonym/stats` - Get synonym usage statistics
- `GET /api/v1/search/suggestions` - Get search suggestions

### Indexing Operations
- `POST /api/v1/index/document` - Index a single document
- `POST /api/v1/index/bulk` - Bulk index documents
- `DELETE /api/v1/index/document/{index_name}/{document_id}` - Delete document
- `POST /api/v1/indices/{index_name}/refresh` - Refresh index

### Analytics & Stats
- `GET /api/v1/analytics/popular-queries` - Get popular search queries
- `GET /api/v1/analytics/search-trends` - Get search trends
- `GET /api/v1/indices/stats` - Get all indices statistics
- `GET /api/v1/indices/{index_name}/stats` - Get specific index statistics

### Pipeline Operations
- `POST /api/v1/pipeline/asset-created` - Handle asset creation events
- `POST /api/v1/pipeline/asset-updated` - Handle asset update events
- `POST /api/v1/pipeline/asset-deleted` - Handle asset deletion events
- `POST /api/v1/pipeline/metadata-updated` - Handle metadata updates
- `POST /api/v1/pipeline/content-extracted` - Handle content extraction

## Quick Start

### Running the Service

```bash
# Using Docker
docker-compose up search-engine

# For development
cd services/search-engine
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8005
```

### Basic Search Example

```bash
curl -X POST http://localhost:8005/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "video production",
    "search_type": "basic",
    "size": 20,
    "highlight": true
  }'
```

### Natural Language Search Example

```bash
curl -X POST http://localhost:8005/api/v1/search/natural-language \
  -H "Content-Type: application/json" \
  -d '{
    "query": "find all 4K videos from last week tagged as nature",
    "size": 20
  }'
```

### Fuzzy Search Example

```bash
curl -X POST http://localhost:8005/api/v1/search/fuzzy \
  -H "Content-Type: application/json" \
  -d '{
    "query": "vidoe tutorial",
    "match_type": "adaptive",
    "fuzziness": "AUTO",
    "performance_mode": "moderate",
    "include_suggestions": true,
    "include_performance_info": true,
    "size": 20
  }'
```

### Fuzzy Suggestions Example

```bash
curl -X POST http://localhost:8005/api/v1/search/fuzzy/suggestions \
  -H "Content-Type: application/json" \
  -d '{
    "text": "documnet",
    "field": "title",
    "size": 5,
    "fuzziness": "AUTO",
    "include_popular": true
  }'
```

### Metadata Field Search Example

```bash
curl -X POST http://localhost:8005/api/v1/search/metadata-fields \
  -H "Content-Type: application/json" \
  -d '{
    "field_queries": [
      {"field": "title", "value": "tutorial"},
      {"field": "format", "value": "MP4"}
    ],
    "operator": "AND",
    "fuzzy": true
  }'
```

### Filtered Search with Facets Example

```bash
curl -X POST http://localhost:8005/api/v1/search/filtered \
  -H "Content-Type: application/json" \
  -d '{
    "query": "marketing video",
    "filters": [
      {
        "field": "asset_type",
        "type": "term",
        "value": "video"
      },
      {
        "field": "duration",
        "type": "range",
        "value": {"gte": 60, "lte": 300}
      }
    ],
    "facets": [
      {
        "name": "file_types",
        "field": "file_extension",
        "type": "terms",
        "size": 10
      },
      {
        "name": "monthly_uploads",
        "field": "created_at",
        "type": "date_histogram",
        "interval": "month"
      }
    ],
    "size": 20,
    "sort_by": "created_at",
    "sort_order": "desc"
  }'
```

### Phonetic Search Example

```bash
curl -X POST http://localhost:8005/api/v1/search/phonetic \
  -H "Content-Type: application/json" \
  -d '{
    "query": "John Smith",
    "algorithm": "soundex",
    "match_type": "adaptive",
    "boost_exact_matches": 2.0,
    "boost_phonetic_matches": 1.0,
    "min_similarity": 0.6,
    "use_fallback_search": true,
    "include_suggestions": true,
    "include_phonetic_analysis": true,
    "size": 20
  }'
```

### Phonetic Suggestions Example

```bash
curl -X POST http://localhost:8005/api/v1/search/phonetic/suggestions \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Smyth",
    "field": "name",
    "size": 5,
    "algorithm": "soundex",
    "include_similar": true,
    "include_common": true,
    "min_similarity": 0.7
  }'
```

### Synonym Search Example

```bash
curl -X POST http://localhost:8005/api/v1/search/synonym \
  -H "Content-Type: application/json" \
  -d '{
    "query": "video tutorial",
    "synonym_config": {
      "synonym_type": "hybrid",
      "expansion_strategy": "expand",
      "max_synonyms_per_term": 5,
      "boost_original_terms": 2.0,
      "boost_synonyms": 1.5,
      "domain_context": "media"
    },
    "include_synonym_analysis": true,
    "size": 20
  }'
```

### Synonym Suggestions Example

```bash
curl -X POST http://localhost:8005/api/v1/search/synonym/suggestions \
  -H "Content-Type: application/json" \
  -d '{
    "term": "video",
    "synonym_type": "hybrid",
    "size": 10,
    "min_similarity": 0.7,
    "domain_context": "media",
    "include_definitions": true
  }'
```

## Configuration

Environment variables:

```env
# Service configuration
SERVICE_NAME=search-engine
SERVICE_PORT=8005
LOG_LEVEL=INFO

# OpenSearch configuration
OPENSEARCH_HOSTS=http://opensearch:9200
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=admin

# Index names
ASSETS_INDEX_NAME=mams_assets
METADATA_INDEX_NAME=mams_metadata
CONTENT_INDEX_NAME=mams_content
LOGS_INDEX_NAME=mams_logs

# Search settings
SEARCH_TIMEOUT=30
MAX_SEARCH_RESULTS=10000
DEFAULT_PAGE_SIZE=20

# Redis configuration (for caching)
REDIS_URL=redis://redis:6379/0
```

## Index Structure

### Assets Index
```json
{
  "asset_id": "string",
  "name": "text",
  "description": "text",
  "file_path": "keyword",
  "file_name": "text",
  "file_extension": "keyword",
  "mime_type": "keyword",
  "file_size": "long",
  "tags": "keyword[]",
  "created_at": "date",
  "updated_at": "date"
}
```

### Metadata Index
```json
{
  "asset_id": "keyword",
  "title": "text",
  "description": "text",
  "keywords": "keyword[]",
  "creator": "text/keyword",
  "subject": "text/keyword",
  "format": "keyword",
  "language": "keyword",
  "custom_fields": "object",
  "created_at": "date"
}
```

### Content Index
```json
{
  "asset_id": "keyword",
  "content": "text",
  "transcript": "text",
  "ocr_text": "text",
  "all_text": "text",
  "extracted_at": "date"
}
```

## Development

### Project Structure
```
search-engine/
├── src/
│   ├── api/
│   │   ├── routes.py          # Main API routes
│   │   └── pipeline_routes.py # Pipeline event routes
│   ├── core/
│   │   ├── config.py          # Configuration
│   │   └── exceptions.py      # Custom exceptions
│   ├── db/
│   │   └── opensearch.py      # OpenSearch client
│   ├── models/
│   │   └── schemas.py         # Pydantic models
│   ├── services/
│   │   ├── search_service.py     # Search operations
│   │   ├── indexing_service.py   # Indexing operations
│   │   ├── facet_service.py      # Facet/aggregation operations
│   │   ├── ranking_service.py    # Custom ranking algorithms
│   │   ├── data_pipeline.py      # Event processing
│   │   ├── suggestion_service.py # Search suggestions
│   │   ├── analytics_service.py  # Search analytics
│   │   ├── nlp_search_service.py # Natural language processing
│   │   ├── phonetic_service.py   # Phonetic search operations
│   │   └── synonym_service.py    # Synonym search operations
│   └── main.py                # FastAPI application
├── tests/
│   ├── test_search_service.py
│   ├── test_indexing_service.py
│   ├── test_metadata_field_search.py
│   ├── test_facet_service.py
│   ├── test_filtered_search.py
│   ├── test_filtered_search_integration.py
│   ├── test_data_pipeline.py
│   ├── test_phonetic_search.py
│   ├── test_phonetic_search_api.py
│   ├── test_synonym_search.py
│   └── test_synonym_search_api.py
├── scripts/
│   └── setup_indices.py       # Index setup script
├── docs/
│   ├── metadata_field_search.md
│   └── FILTERS_AND_FACETS.md  # Filter and facet documentation
├── requirements.txt
├── Dockerfile
└── README.md
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_metadata_field_search.py
```

### Setting Up Indices

```bash
# Run the setup script
python scripts/setup_indices.py
```

## Monitoring

The service exposes metrics at `/metrics` for Prometheus scraping:

- `search_requests_total` - Total number of search requests
- `search_request_duration_seconds` - Search request duration
- `indexing_operations_total` - Total indexing operations
- `index_document_count` - Number of documents per index

## Performance Tuning

### Search Performance
- Use specific indices instead of searching all
- Enable caching for frequently searched terms
- Use filters instead of queries when possible
- Limit aggregations to necessary fields

### Indexing Performance
- Use bulk indexing for multiple documents
- Set appropriate refresh intervals
- Use async indexing for non-critical updates

## Integration

The Search Engine Service integrates with:

- **Asset Management Service**: Indexes asset information
- **Metadata Service**: Indexes metadata changes
- **Ingest Service**: Indexes new content
- **Proxy Generation Service**: Indexes extracted text
- **AI/ML Service**: Receives enriched content for indexing

## Troubleshooting

### Common Issues

1. **Search returns no results**
   - Check if indices exist and contain documents
   - Verify search query syntax
   - Check index refresh status

2. **Slow search performance**
   - Review query complexity
   - Check OpenSearch cluster health
   - Consider adding more shards/replicas

3. **Indexing failures**
   - Check document structure matches mapping
   - Verify OpenSearch connectivity
   - Review error logs for details

### Health Check

```bash
curl http://localhost:8005/health
```

## Security

- All API endpoints require authentication (when integrated with API Gateway)
- Search results respect user permissions
- Sensitive fields can be excluded from indexing
- SSL/TLS encryption for OpenSearch communication

## License

Part of the MAMS (Media Asset Management System) platform.