# MAMS Search Engine API Documentation

## Overview

The MAMS Search Engine Service provides comprehensive search capabilities for the Digital Media Asset Management System. This service offers full-text search, metadata search, advanced filtering, faceting, analytics, and search management features.

**Base URL**: `http://localhost:8001/api/v1`  
**Service Version**: 1.0.0  
**OpenAPI Documentation**: Available at `/docs` and `/redoc`

## Table of Contents

1. [Authentication](#authentication)
2. [Core Search Endpoints](#core-search-endpoints)
3. [Advanced Search Features](#advanced-search-features)
4. [Search Management](#search-management)
5. [Analytics Endpoints](#analytics-endpoints)
6. [Indexing Operations](#indexing-operations)
7. [Suggestions and Autocomplete](#suggestions-and-autocomplete)
8. [Data Pipeline](#data-pipeline)
9. [Error Handling](#error-handling)
10. [Rate Limiting](#rate-limiting)
11. [Examples](#examples)

## Authentication

Most endpoints require authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <jwt_token>
```

Some endpoints support optional authentication for enhanced features:
- Search history (requires authentication)
- Saved searches (requires authentication)
- Analytics (admin access required)

## Core Search Endpoints

### Basic Search

**Endpoint**: `POST /search`

Performs a basic search across MAMS indices with relevance scoring.

**Request Body**:
```json
{
  "query": "marketing video",
  "search_type": "basic",
  "indices": ["assets", "metadata"],
  "filters": {
    "asset_type": "video",
    "status": "published"
  },
  "size": 20,
  "from": 0,
  "sort_by": "created_at",
  "sort_order": "desc",
  "highlight": true
}
```

**Response**:
```json
{
  "query": "marketing video",
  "total_hits": 42,
  "max_score": 2.5,
  "took": 45,
  "timed_out": false,
  "hits": [
    {
      "id": "asset_123",
      "index": "assets",
      "score": 2.5,
      "source": {
        "id": "asset_123",
        "name": "Marketing Campaign Video.mp4",
        "asset_type": "video",
        "duration": 180,
        "created_at": "2024-01-15T10:30:00Z"
      },
      "highlight": {
        "name": ["<mark>Marketing</mark> Campaign <mark>Video</mark>.mp4"]
      }
    }
  ],
  "page": 1,
  "per_page": 20,
  "total_pages": 3
}
```

### Advanced Search

**Endpoint**: `POST /search/advanced`

Supports complex queries with multiple conditions, boolean operators, and field-specific searching.

**Request Body**:
```json
{
  "conditions": [
    {
      "field": "name",
      "operator": "contains",
      "value": "marketing",
      "boost": 2.0
    },
    {
      "field": "tags",
      "operator": "any",
      "value": ["video", "tutorial"],
      "boost": 1.5
    }
  ],
  "operator": "and",
  "indices": ["assets", "metadata"],
  "size": 20,
  "from": 0,
  "sort_by": "relevance",
  "highlight": true
}
```

### Metadata Field Search

**Endpoint**: `POST /search/metadata`

Searches within specific metadata fields with field-aware scoring.

**Request Body**:
```json
{
  "field_queries": [
    {
      "field": "title",
      "query": "marketing campaign",
      "boost": 2.0
    },
    {
      "field": "description",
      "query": "product launch",
      "boost": 1.5
    }
  ],
  "metadata_type": "dublin_core",
  "indices": ["metadata"],
  "size": 20,
  "from": 0
}
```

### Filtered Search with Facets

**Endpoint**: `POST /search/filtered`

Advanced search with filtering, faceting, and aggregations. See [Filters and Facets Guide](./FILTERS_AND_FACETS.md) for detailed usage.

**Request Body**:
```json
{
  "query": "marketing video",
  "search_type": "basic",
  "indices": ["assets", "metadata"],
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
      "size": 20
    },
    {
      "name": "monthly_distribution",
      "field": "created_at",
      "type": "date_histogram",
      "interval": "month"
    }
  ],
  "size": 20,
  "from": 0
}
```

## Advanced Search Features

### Ranking and Relevance

**Endpoint**: `POST /search/ranked`

Search with advanced relevance scoring and ranking algorithms.

**Request Body**:
```json
{
  "query": "marketing video",
  "ranking_profile": "default",
  "boost_factors": {
    "recency": 0.3,
    "popularity": 0.2,
    "quality": 0.1
  },
  "indices": ["assets"],
  "size": 20
}
```

### Fuzzy Search

**Endpoint**: `POST /search/fuzzy`

Handles typos and approximate matches.

**Request Body**:
```json
{
  "query": "markting vidoe",
  "fuzziness": "AUTO",
  "indices": ["assets"],
  "size": 20
}
```

### Semantic Search

**Endpoint**: `POST /search/semantic`

AI-powered semantic search for meaning-based matching.

**Request Body**:
```json
{
  "query": "happy customers using our product",
  "semantic_model": "sentence-transformers",
  "indices": ["assets"],
  "size": 20
}
```

## Search Management

### Saved Searches

Saved searches allow users to store and reuse complex search queries. See [Saved Searches Guide](./saved_searches.md) for detailed documentation.

Key endpoints:
- `POST /search/saved` - Create a new saved search
- `GET /search/saved` - List saved searches
- `GET /search/saved/{search_id}` - Get specific saved search
- `PUT /search/saved/{search_id}` - Update saved search
- `DELETE /search/saved/{search_id}` - Delete saved search
- `POST /search/saved/{search_id}/execute` - Execute saved search
- `GET /search/saved/popular` - Get popular public searches
- `GET /search/saved/by-tags` - Search by tags

### Search History

Search history tracks all searches performed by authenticated users. See [Search History Guide](./search_history.md) for detailed documentation.

Key endpoints:
- `GET /search/history` - Get user's search history
- `GET /search/history/stats` - Get search statistics
- `DELETE /search/history` - Delete old history entries
- `DELETE /search/history/clear` - Clear all history

## Analytics Endpoints

### Search Analytics

Search analytics provides comprehensive insights into search behavior and performance. See [Search Analytics Guide](./search_analytics.md) for detailed documentation.

Key endpoints:
- `POST /analytics/search` - Get aggregated search analytics
- `POST /analytics/search/performance` - Get performance metrics
- `POST /analytics/search/trends` - Get search trends over time
- `POST /analytics/search/report` - Generate comprehensive report
- `POST /analytics/search/segments` - Get user segment analysis
- `POST /analytics/search/click` - Log search result click
- `DELETE /analytics/search/cleanup` - Clean up old analytics data

## Indexing Operations

### Index Document
**Endpoint**: `POST /index`

```json
{
  "index": "assets",
  "document": {
    "id": "asset_123",
    "name": "Marketing Video.mp4",
    "asset_type": "video",
    "file_size": 52428800,
    "duration": 180,
    "created_at": "2024-01-15T10:30:00Z",
    "metadata": {
      "title": "Product Launch Video",
      "description": "Marketing video for Q1 product launch",
      "tags": ["marketing", "product", "launch"]
    }
  }
}
```

### Bulk Index
**Endpoint**: `POST /index/bulk`

```json
{
  "index": "assets",
  "documents": [
    {
      "id": "asset_123",
      "name": "Video 1.mp4",
      "asset_type": "video"
    },
    {
      "id": "asset_124",
      "name": "Image 1.jpg",
      "asset_type": "image"
    }
  ]
}
```

### Delete Document
**Endpoint**: `DELETE /index/{index}/{document_id}`

### Get Index Statistics
**Endpoint**: `GET /index/{index}/stats`

**Response**:
```json
{
  "index": "assets",
  "document_count": 10000,
  "size_in_bytes": 1073741824,
  "last_updated": "2024-01-15T10:30:00Z",
  "health": "green"
}
```

## Suggestions and Autocomplete

### Get Search Suggestions
**Endpoint**: `POST /suggestions`

```json
{
  "query": "mark",
  "indices": ["assets"],
  "size": 10,
  "suggestion_types": ["completion", "phrase", "term"]
}
```

**Response**:
```json
{
  "suggestions": [
    {
      "text": "marketing",
      "score": 0.9,
      "type": "completion"
    },
    {
      "text": "market research",
      "score": 0.8,
      "type": "phrase"
    }
  ]
}
```

### Get Field Suggestions
**Endpoint**: `POST /suggestions/fields`

```json
{
  "field": "tags",
  "query": "mark",
  "indices": ["assets"],
  "size": 10
}
```

## Data Pipeline

### Trigger Pipeline Processing
**Endpoint**: `POST /pipeline/process`

```json
{
  "pipeline_name": "asset_enrichment",
  "data": {
    "asset_id": "asset_123",
    "file_path": "/storage/video.mp4"
  }
}
```

### Get Pipeline Status
**Endpoint**: `GET /pipeline/status/{pipeline_id}`

### List Available Pipelines
**Endpoint**: `GET /pipeline/list`

## Error Handling

### Error Response Format

All errors follow this standard format:

```json
{
  "error": {
    "code": "SEARCH_ERROR",
    "message": "Search query failed",
    "details": {
      "query": "invalid query",
      "reason": "syntax error"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `SEARCH_ERROR` | 400 | Invalid search query or parameters |
| `INDEX_ERROR` | 400 | Indexing operation failed |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error |

## Rate Limiting

Rate limiting is applied per IP address and authenticated user:

- **Anonymous users**: 100 requests per minute
- **Authenticated users**: 500 requests per minute
- **Admin users**: 1000 requests per minute

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset time (Unix timestamp)

## Examples

### Complete Search Workflow

```python
import requests
import json

# Base URL
base_url = "http://localhost:8001/api/v1"

# Authentication
headers = {
    "Authorization": "Bearer your-jwt-token",
    "Content-Type": "application/json"
}

# 1. Basic search
search_request = {
    "query": "marketing video",
    "search_type": "basic",
    "indices": ["assets"],
    "size": 20
}

response = requests.post(
    f"{base_url}/search",
    headers=headers,
    json=search_request
)
search_results = response.json()

# 2. Advanced search with filters
filtered_search = {
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
        }
    ],
    "size": 20
}

response = requests.post(
    f"{base_url}/search/filtered",
    headers=headers,
    json=filtered_search
)
filtered_results = response.json()

# 3. Save successful search
if filtered_results["total_hits"] > 0:
    saved_search = {
        "name": "Marketing Videos",
        "description": "All marketing video assets",
        "query": filtered_search,
        "is_public": False,
        "tags": ["marketing", "video"]
    }
    
    response = requests.post(
        f"{base_url}/searches/saved",
        headers=headers,
        json=saved_search
    )
    saved_search_id = response.json()["id"]

# 4. Get search analytics
analytics_request = {
    "time_range": {
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-31T23:59:59Z",
        "interval": "1d"
    }
}

response = requests.post(
    f"{base_url}/analytics/search",
    headers=headers,
    json=analytics_request
)
analytics_data = response.json()

print(f"Found {search_results['total_hits']} results")
print(f"Analytics: {analytics_data['total_searches']} searches this month")
```

### JavaScript/Frontend Integration

```javascript
class SearchClient {
  constructor(baseUrl, authToken) {
    this.baseUrl = baseUrl;
    this.authToken = authToken;
  }

  async search(query, options = {}) {
    const response = await fetch(`${this.baseUrl}/search`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query,
        search_type: options.searchType || 'basic',
        indices: options.indices || ['assets'],
        size: options.size || 20,
        from: options.from || 0,
        highlight: options.highlight !== false
      })
    });

    if (!response.ok) {
      throw new Error(`Search failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getSearchSuggestions(query) {
    const response = await fetch(`${this.baseUrl}/suggestions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query,
        indices: ['assets'],
        size: 10
      })
    });

    return response.json();
  }

  async getSavedSearches() {
    const response = await fetch(`${this.baseUrl}/searches/saved`, {
      headers: {
        'Authorization': `Bearer ${this.authToken}`
      }
    });

    return response.json();
  }
}

// Usage
const client = new SearchClient('http://localhost:8001/api/v1', 'your-jwt-token');

// Perform search
const results = await client.search('marketing video', {
  searchType: 'basic',
  size: 20,
  highlight: true
});

// Get suggestions for autocomplete
const suggestions = await client.getSearchSuggestions('mark');
```

## API Versioning

The API uses URL versioning:
- Current version: `/api/v1`
- Future versions: `/api/v2`, etc.

### Version Compatibility

- **v1**: Current stable version
- Breaking changes will introduce new versions
- Deprecated versions will be supported for 6 months

## Testing

### Health Check
**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "service": "search-engine",
  "opensearch_status": "green",
  "version": "1.0.0"
}
```

### Service Information
**Endpoint**: `GET /info`

**Response**:
```json
{
  "service": "search-engine",
  "version": "1.0.0",
  "opensearch_version": "2.11.0",
  "supported_indices": ["assets", "metadata", "projects"],
  "features": [
    "basic_search",
    "advanced_search",
    "filtered_search",
    "faceting",
    "analytics",
    "suggestions"
  ]
}
```

## Support

For additional help:
- **Documentation**: See related guides in the `/docs` directory
- **OpenAPI Spec**: Available at `/docs` endpoint
- **Issues**: Report bugs and feature requests through the project repository
- **Contact**: Development team at [team@example.com](mailto:team@example.com)

## Related Documentation

- [Filters and Facets Guide](./FILTERS_AND_FACETS.md)
- [Search Ranking Documentation](./search_ranking.md)
- [Search Suggestions Guide](./search_suggestions.md)
- [Metadata Field Search](./metadata_field_search.md)
- [Saved Searches Guide](./saved_searches.md)
- [Search History Guide](./search_history.md)
- [Search Analytics Guide](./search_analytics.md)

---

*Last updated: January 2024*
*API Version: 1.0.0*