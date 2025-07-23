# Search Engine Service Documentation

## Overview

This directory contains comprehensive documentation for the MAMS Search Engine Service, providing detailed guides for all search capabilities, API endpoints, and integration patterns.

## Documentation Index

### 📋 Core Documentation

- **[API Documentation](./API.md)** - Complete API reference with examples and usage patterns
- **[OpenAPI Specification](./openapi.yaml)** - Machine-readable API specification for code generation and testing

### 🔍 Search Features

- **[Filters and Facets Guide](./FILTERS_AND_FACETS.md)** - Advanced filtering and faceting capabilities
- **[Search Ranking](./search_ranking.md)** - Custom ranking algorithms and relevance tuning
- **[Search Suggestions](./search_suggestions.md)** - Autocomplete and search suggestions
- **[Metadata Field Search](./metadata_field_search.md)** - Metadata-specific searching patterns

### 🚀 Quick Start

1. **First Time Setup**
   - Review the [API Documentation](./API.md) for endpoint overview
   - Check [OpenAPI Specification](./openapi.yaml) for detailed schemas
   - Set up your development environment using the main [README](../README.md)

2. **Basic Usage**
   - Start with simple searches using the `/search` endpoint
   - Explore filtering using the [Filters and Facets Guide](./FILTERS_AND_FACETS.md)
   - Implement suggestions using the [Search Suggestions](./search_suggestions.md) guide

3. **Advanced Features**
   - Customize ranking using the [Search Ranking](./search_ranking.md) guide
   - Use metadata searches with the [Metadata Field Search](./metadata_field_search.md) guide
   - Implement analytics and saved searches from the [API Documentation](./API.md)

## Interactive Documentation

When the service is running, you can access interactive documentation:

- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

## API Reference Summary

### Core Search Endpoints

| Endpoint | Description | Documentation |
|----------|-------------|---------------|
| `POST /search` | Basic search with relevance scoring | [API Docs](./API.md#basic-search) |
| `POST /search/advanced` | Advanced search with boolean operators | [API Docs](./API.md#advanced-search) |
| `POST /search/filtered` | Filtered search with facets | [Filters Guide](./FILTERS_AND_FACETS.md) |
| `POST /search/metadata` | Metadata field-specific search | [Metadata Guide](./metadata_field_search.md) |
| `POST /search/ranked` | Search with custom ranking | [Ranking Guide](./search_ranking.md) |

### Search Management

| Endpoint | Description | Documentation |
|----------|-------------|---------------|
| `POST /searches/saved` | Create saved search | [API Docs](./API.md#saved-searches) |
| `GET /searches/saved` | Get saved searches | [API Docs](./API.md#saved-searches) |
| `GET /searches/history` | Get search history | [API Docs](./API.md#search-history) |
| `GET /searches/history/stats` | Get search statistics | [API Docs](./API.md#search-history) |

### Analytics & Reporting

| Endpoint | Description | Documentation |
|----------|-------------|---------------|
| `POST /analytics/search` | Get search analytics | [API Docs](./API.md#analytics-endpoints) |
| `POST /analytics/search/performance` | Get performance metrics | [API Docs](./API.md#analytics-endpoints) |
| `POST /analytics/search/trends` | Get search trends | [API Docs](./API.md#analytics-endpoints) |
| `POST /analytics/search/report` | Generate analytics report | [API Docs](./API.md#analytics-endpoints) |

### Suggestions & Autocomplete

| Endpoint | Description | Documentation |
|----------|-------------|---------------|
| `POST /suggestions` | Get search suggestions | [Suggestions Guide](./search_suggestions.md) |
| `POST /suggestions/fields` | Get field-specific suggestions | [Suggestions Guide](./search_suggestions.md) |

### Indexing Operations

| Endpoint | Description | Documentation |
|----------|-------------|---------------|
| `POST /index` | Index single document | [API Docs](./API.md#indexing-operations) |
| `POST /index/bulk` | Bulk index documents | [API Docs](./API.md#indexing-operations) |
| `DELETE /index/{index}/{document_id}` | Delete document | [API Docs](./API.md#indexing-operations) |
| `GET /index/{index}/stats` | Get index statistics | [API Docs](./API.md#indexing-operations) |

## Example Usage Patterns

### 1. Basic Search Implementation

```python
# Basic search with highlighting
response = requests.post('http://localhost:8001/api/v1/search', json={
    "query": "marketing video",
    "search_type": "basic",
    "highlight": true,
    "size": 20
})
```

### 2. Advanced Filtering

```python
# Search with filters and facets
response = requests.post('http://localhost:8001/api/v1/search/filtered', json={
    "query": "product demo",
    "filters": [
        {"field": "asset_type", "type": "term", "value": "video"},
        {"field": "duration", "type": "range", "value": {"gte": 60, "lte": 300}}
    ],
    "facets": [
        {"name": "file_types", "field": "file_extension", "type": "terms", "size": 10}
    ]
})
```

### 3. Analytics Integration

```python
# Get search analytics
response = requests.post('http://localhost:8001/api/v1/analytics/search', json={
    "time_range": {
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-31T23:59:59Z",
        "interval": "1d"
    }
})
```

### 4. Saved Search Management

```python
# Create saved search
response = requests.post('http://localhost:8001/api/v1/searches/saved', json={
    "name": "Marketing Videos",
    "description": "All marketing video assets",
    "query": {
        "query": "marketing",
        "filters": {"asset_type": "video"}
    },
    "tags": ["marketing", "video"]
})
```

## Search Types and Use Cases

### Basic Search
- **Use Case**: General text search across all indexed content
- **Best For**: User-facing search interfaces, quick content discovery
- **Features**: Relevance scoring, highlighting, pagination

### Advanced Search
- **Use Case**: Complex queries with boolean operators
- **Best For**: Power users, detailed content filtering
- **Features**: AND/OR/NOT operators, field-specific conditions, boost factors

### Filtered Search
- **Use Case**: Faceted search with drill-down navigation
- **Best For**: E-commerce style interfaces, data exploration
- **Features**: Multiple filter types, aggregations, post-filtering

### Metadata Search
- **Use Case**: Searching specific metadata fields
- **Best For**: Structured data queries, metadata-driven applications
- **Features**: Field-specific queries, metadata schema support

### Ranked Search
- **Use Case**: Custom relevance scoring
- **Best For**: Personalized search, business-specific ranking
- **Features**: Configurable ranking profiles, boost factors

## Error Handling

All endpoints return standardized error responses:

```json
{
  "error": {
    "code": "SEARCH_ERROR",
    "message": "Search query failed",
    "details": {"query": "invalid query", "reason": "syntax error"},
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

Common error codes:
- `SEARCH_ERROR` (400): Invalid search query
- `VALIDATION_ERROR` (422): Request validation failed
- `NOT_FOUND` (404): Resource not found
- `RATE_LIMIT_EXCEEDED` (429): Too many requests
- `INTERNAL_SERVER_ERROR` (500): Unexpected server error

## Performance Considerations

### Search Optimization
- Use specific indices instead of searching all
- Apply filters before queries when possible
- Limit facet sizes to improve performance
- Use source field filtering for large documents

### Indexing Optimization
- Use bulk indexing for multiple documents
- Set appropriate refresh intervals
- Monitor index health and performance
- Consider shard and replica configuration

### Caching Strategy
- Cache frequently accessed search results
- Use Redis for session-based caching
- Implement cache invalidation for real-time updates
- Consider CDN for static suggestion data

## Security Considerations

### Authentication
- JWT tokens required for most endpoints
- Role-based access control for analytics
- Session management for search history

### Data Protection
- Sensitive fields excluded from indexing
- User permission-based result filtering
- Audit logging for search activities
- SSL/TLS for all communications

## Troubleshooting

### Common Issues

1. **Search Returns No Results**
   - Check index health: `GET /health`
   - Verify query syntax and parameters
   - Confirm documents exist in indices

2. **Slow Search Performance**
   - Review query complexity and filters
   - Check OpenSearch cluster health
   - Monitor resource usage and scaling

3. **Indexing Failures**
   - Verify document schema matches mapping
   - Check OpenSearch connectivity
   - Review error logs for specific issues

4. **Analytics Data Missing**
   - Confirm MongoDB connectivity
   - Check analytics service configuration
   - Verify user authentication for tracking

### Debug Endpoints

- `GET /health` - Service health check
- `GET /info` - Service information and capabilities
- `GET /index/{index}/stats` - Index statistics and health

## Support and Resources

### Getting Help
- **Documentation**: This directory contains comprehensive guides
- **Interactive Docs**: Available at `/docs` endpoint when service is running
- **Issues**: Report bugs and feature requests through the project repository
- **Development Team**: Contact for technical support and questions

### External Resources
- **OpenSearch Documentation**: https://opensearch.org/docs/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **MongoDB Documentation**: https://docs.mongodb.com/

### Development Resources
- **Testing**: Use the test suite in `/tests` directory
- **Scripts**: Utility scripts in `/scripts` directory
- **Docker**: Development setup with Docker Compose
- **Monitoring**: Prometheus metrics and health checks

---

*Last updated: January 2024*
*Service Version: 1.0.0*