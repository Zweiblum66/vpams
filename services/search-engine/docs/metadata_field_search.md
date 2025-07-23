# Metadata Field Search Documentation

## Overview

The Metadata Field Search feature allows users to perform targeted searches on specific metadata fields within the MAMS system. This provides more precise search capabilities compared to general text search, enabling users to find assets based on specific metadata attributes.

## Features

- **Field-specific searching**: Search within specific metadata fields like title, keywords, creator, etc.
- **Boolean operators**: Combine multiple field queries using AND/OR operators
- **Fuzzy matching**: Enable typo-tolerant searching with fuzzy matching
- **Field boosting**: Assign different importance weights to different fields
- **Keyword field support**: Exact matching for keyword-type fields
- **Filtering**: Apply additional filters alongside field searches
- **Aggregations**: Get metadata-specific aggregations in search results

## API Endpoint

### POST `/api/v1/search/metadata-fields`

Perform a search on specific metadata fields.

#### Request Body

```json
{
  "field_queries": [
    {
      "field": "title",
      "value": "video production"
    },
    {
      "field": "keywords",
      "value": "test"
    }
  ],
  "operator": "AND",
  "indices": ["metadata"],
  "filters": {
    "language": "en",
    "format": ["MP4", "MOV"]
  },
  "size": 20,
  "from": 0,
  "sort_by": "created_at",
  "sort_order": "desc",
  "highlight": true,
  "include_aggregations": true,
  "fuzzy": false,
  "boost_fields": {
    "title": 2.0,
    "description": 1.5
  }
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| field_queries | Array | Yes | - | List of field-value pairs to search |
| operator | String | No | "AND" | How to combine field queries (AND/OR) |
| indices | Array | No | ["metadata"] | Which indices to search |
| filters | Object | No | null | Additional filters to apply |
| size | Integer | No | 20 | Number of results to return (1-1000) |
| from | Integer | No | 0 | Offset for pagination |
| sort_by | String | No | null | Field to sort by |
| sort_order | String | No | "desc" | Sort order (asc/desc) |
| highlight | Boolean | No | true | Whether to highlight matches |
| include_aggregations | Boolean | No | false | Include aggregations in response |
| fuzzy | Boolean | No | false | Enable fuzzy matching |
| boost_fields | Object | No | null | Field boosting weights |

#### Field Query Structure

Each field query must contain:
- `field`: The metadata field name to search in
- `value`: The value to search for

#### Response

```json
{
  "query": "Metadata field search: AND operator",
  "total_hits": 42,
  "max_score": 2.5,
  "hits": [
    {
      "id": "asset-123_metadata",
      "index": "mams_metadata",
      "score": 2.5,
      "source": {
        "asset_id": "asset-123",
        "title": "Test Video Production",
        "description": "A sample video for testing",
        "keywords": ["test", "video", "sample"],
        "creator": "John Doe",
        "format": "MP4",
        "language": "en"
      },
      "highlight": {
        "title": ["<mark>Test</mark> <mark>Video</mark> Production"],
        "keywords": ["<mark>test</mark>"]
      }
    }
  ],
  "aggregations": [
    {
      "name": "file_formats",
      "buckets": [
        {"key": "MP4", "doc_count": 25},
        {"key": "MOV", "doc_count": 10}
      ]
    }
  ],
  "took": 15,
  "timed_out": false,
  "page": 1,
  "per_page": 20,
  "total_pages": 3
}
```

## Usage Examples

### 1. Basic Field Search

Search for videos with specific title and keywords:

```bash
curl -X POST http://localhost:8005/api/v1/search/metadata-fields \
  -H "Content-Type: application/json" \
  -d '{
    "field_queries": [
      {"field": "title", "value": "production"},
      {"field": "keywords", "value": "corporate"}
    ],
    "operator": "AND"
  }'
```

### 2. OR Operator Search

Find assets in multiple formats:

```bash
curl -X POST http://localhost:8005/api/v1/search/metadata-fields \
  -H "Content-Type: application/json" \
  -d '{
    "field_queries": [
      {"field": "format", "value": "MP4"},
      {"field": "format", "value": "MOV"}
    ],
    "operator": "OR"
  }'
```

### 3. Fuzzy Search with Boosting

Search with typo tolerance and field importance:

```bash
curl -X POST http://localhost:8005/api/v1/search/metadata-fields \
  -H "Content-Type: application/json" \
  -d '{
    "field_queries": [
      {"field": "title", "value": "vido"},
      {"field": "creator", "value": "Jon"}
    ],
    "operator": "AND",
    "fuzzy": true,
    "boost_fields": {
      "title": 3.0,
      "creator": 1.5
    }
  }'
```

### 4. Exact Match with Keyword Fields

Search for exact creator name:

```bash
curl -X POST http://localhost:8005/api/v1/search/metadata-fields \
  -H "Content-Type: application/json" \
  -d '{
    "field_queries": [
      {"field": "creator.keyword", "value": "John Doe"}
    ]
  }'
```

### 5. Complex Search with Filters

Combine field search with additional filters:

```bash
curl -X POST http://localhost:8005/api/v1/search/metadata-fields \
  -H "Content-Type: application/json" \
  -d '{
    "field_queries": [
      {"field": "subject", "value": "education"}
    ],
    "filters": {
      "language": "en",
      "format": ["MP4", "MOV"],
      "date_created": {
        "gte": "2024-01-01",
        "lte": "2024-12-31"
      }
    },
    "include_aggregations": true
  }'
```

## Supported Metadata Fields

Common metadata fields that can be searched:

- **title**: Asset title
- **description**: Asset description
- **keywords**: Array of keywords
- **creator**: Content creator name
- **subject**: Subject/category
- **format**: File format (MP4, MOV, etc.)
- **language**: Content language
- **publisher**: Publisher name
- **contributor**: Contributors
- **rights**: Usage rights
- **coverage**: Geographical/temporal coverage
- **custom_fields.***: Any custom metadata fields

For exact matching, append `.keyword` to text fields:
- **creator.keyword**: Exact creator name
- **subject.keyword**: Exact subject match

## Best Practices

1. **Use specific fields**: Target specific fields rather than searching all fields
2. **Combine with filters**: Use filters to narrow down results further
3. **Enable fuzzy for user input**: When searching based on user input, enable fuzzy matching
4. **Use keyword fields for exact matches**: For filtering by exact values like names or IDs
5. **Boost important fields**: Give higher weight to fields that are more likely to contain relevant results
6. **Include aggregations sparingly**: Only when you need faceted search results

## Error Handling

Common error responses:

- **400 Bad Request**: Invalid field queries or parameters
- **404 Not Found**: Specified field doesn't exist in the index
- **500 Internal Server Error**: Search service error

Example error response:
```json
{
  "detail": "At least one field query is required"
}
```

## Performance Considerations

- Field-specific searches are generally faster than full-text searches
- Using keyword fields for exact matches is more efficient
- Fuzzy matching increases search time
- Large result sets should use pagination
- Aggregations add overhead to the search

## Integration with Other MAMS Components

The metadata field search integrates with:

- **Asset Management Service**: Search results link to asset IDs
- **Metadata Service**: Searches are performed on metadata indexed from this service
- **Workflow Engine**: Can trigger workflows based on search results
- **Rights Management**: Respects access controls on metadata