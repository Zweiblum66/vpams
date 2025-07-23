# Search Engine - Filters and Facets Guide

## Overview

The MAMS Search Engine provides advanced filtering and faceting capabilities that enable users to refine search results and explore data through aggregations. This guide covers the implementation and usage of these features.

## Table of Contents

1. [Filters](#filters)
2. [Facets](#facets)
3. [API Usage](#api-usage)
4. [Implementation Details](#implementation-details)
5. [Best Practices](#best-practices)

## Filters

Filters allow you to narrow down search results based on specific criteria without affecting the relevance scoring.

### Filter Types

#### 1. Term Filter
Exact match on a single value.

```json
{
  "field": "asset_type",
  "type": "term",
  "value": "video"
}
```

#### 2. Terms Filter
Match any of multiple values (OR operation).

```json
{
  "field": "tags",
  "type": "terms",
  "value": ["marketing", "tutorial", "product"]
}
```

#### 3. Range Filter
Filter numeric or date values within a range.

```json
{
  "field": "duration",
  "type": "range",
  "value": {
    "gte": 60,
    "lte": 300
  }
}
```

Supported operators:
- `gte`: Greater than or equal
- `gt`: Greater than
- `lte`: Less than or equal
- `lt`: Less than

#### 4. Exists Filter
Check if a field exists in the document.

```json
{
  "field": "thumbnail",
  "type": "exists",
  "value": true
}
```

#### 5. Prefix Filter
Match values that start with a specific prefix.

```json
{
  "field": "file_name",
  "type": "prefix",
  "value": "IMG_"
}
```

#### 6. Wildcard Filter
Pattern matching with `*` (any characters) and `?` (single character).

```json
{
  "field": "file_name",
  "type": "wildcard",
  "value": "*.mp4"
}
```

#### 7. Regexp Filter
Regular expression matching.

```json
{
  "field": "asset_id",
  "type": "regexp",
  "value": "[0-9]{4}-[0-9]{6}"
}
```

#### 8. Nested Filter
Filter on nested object fields.

```json
{
  "field": "metadata.tags.name",
  "type": "term",
  "value": "important",
  "nested_path": "metadata.tags"
}
```

### Filters vs Post-Filters

- **Filters**: Applied during query execution, affect facet counts
- **Post-Filters**: Applied after aggregations, don't affect facet counts

Use post-filters when you want facets to show counts for all results, not just filtered ones.

## Facets

Facets (aggregations) provide summarized data about your search results, enabling drill-down navigation and data analysis.

### Facet Types

#### 1. Terms Facet
Count occurrences of distinct values.

```json
{
  "name": "asset_types",
  "field": "asset_type",
  "type": "terms",
  "size": 10
}
```

Response:
```json
{
  "name": "asset_types",
  "type": "terms",
  "buckets": [
    {"key": "video", "doc_count": 150},
    {"key": "image", "doc_count": 100},
    {"key": "audio", "doc_count": 50}
  ]
}
```

#### 2. Range Facet
Count documents in predefined ranges.

```json
{
  "name": "file_size_ranges",
  "field": "file_size",
  "type": "range",
  "ranges": [
    {"to": 1048576, "key": "< 1MB"},
    {"from": 1048576, "to": 10485760, "key": "1MB - 10MB"},
    {"from": 10485760, "key": "> 10MB"}
  ]
}
```

#### 3. Date Histogram Facet
Count documents by time intervals.

```json
{
  "name": "monthly_uploads",
  "field": "created_at",
  "type": "date_histogram",
  "interval": "month"
}
```

Supported intervals: `year`, `quarter`, `month`, `week`, `day`, `hour`

#### 4. Histogram Facet
Count documents in numeric intervals.

```json
{
  "name": "duration_distribution",
  "field": "duration",
  "type": "histogram",
  "interval": 60
}
```

#### 5. Stats Facet
Calculate statistics for numeric fields.

```json
{
  "name": "file_size_stats",
  "field": "file_size",
  "type": "stats"
}
```

Response includes: `min`, `max`, `avg`, `sum`, `count`

#### 6. Cardinality Facet
Count distinct values (approximate).

```json
{
  "name": "unique_users",
  "field": "created_by",
  "type": "cardinality"
}
```

## API Usage

### Filtered Search Endpoint

`POST /api/v1/search/filtered`

### Request Example

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
    },
    {
      "field": "status",
      "type": "term",
      "value": "published"
    }
  ],
  
  "post_filters": [
    {
      "field": "department",
      "type": "term",
      "value": "marketing"
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
    },
    {
      "name": "duration_ranges",
      "field": "duration",
      "type": "range",
      "ranges": [
        {"to": 60, "key": "Short (< 1min)"},
        {"from": 60, "to": 300, "key": "Medium (1-5min)"},
        {"from": 300, "key": "Long (> 5min)"}
      ]
    }
  ],
  
  "size": 20,
  "from": 0,
  "sort_by": "created_at",
  "sort_order": "desc",
  "highlight": true,
  "include_source": true,
  "source_fields": ["id", "name", "asset_type", "duration", "created_at"]
}
```

### Response Example

```json
{
  "query": "marketing video",
  "total_hits": 42,
  "max_score": 2.5,
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
  "facets": [
    {
      "name": "file_types",
      "type": "terms",
      "buckets": [
        {"key": "mp4", "doc_count": 25},
        {"key": "mov", "doc_count": 10},
        {"key": "avi", "doc_count": 7}
      ]
    },
    {
      "name": "monthly_distribution",
      "type": "date_histogram",
      "buckets": [
        {"key": "2024-01", "doc_count": 15},
        {"key": "2024-02", "doc_count": 20},
        {"key": "2024-03", "doc_count": 7}
      ]
    },
    {
      "name": "duration_ranges",
      "type": "range",
      "buckets": [
        {"key": "Short (< 1min)", "to": 60, "doc_count": 5},
        {"key": "Medium (1-5min)", "from": 60, "to": 300, "doc_count": 30},
        {"key": "Long (> 5min)", "from": 300, "doc_count": 7}
      ]
    }
  ],
  "applied_filters": [
    {"field": "asset_type", "type": "term", "value": "video"},
    {"field": "duration", "type": "range", "value": {"gte": 60, "lte": 300}},
    {"field": "status", "type": "term", "value": "published"}
  ],
  "took": 45,
  "timed_out": false,
  "page": 1,
  "per_page": 20,
  "total_pages": 3
}
```

## Implementation Details

### Architecture

1. **FacetService**: Handles facet/aggregation operations
   - Builds OpenSearch aggregations from facet configurations
   - Parses aggregation results into structured responses
   - Validates fields for aggregation support

2. **SearchService**: Enhanced with filtered search capabilities
   - Integrates FacetService for aggregations
   - Handles filter and post-filter application
   - Manages facet computation alongside search

3. **Schema Models**: Comprehensive type definitions
   - `FilterCondition`: Defines filter structure
   - `FacetConfig`: Configures facet behavior
   - `FilteredSearchQuery`: Complete query model
   - `FilteredSearchResponse`: Enhanced response with facets

### Default Facets

When no facets are specified, the system provides these defaults:
- Asset types
- File extensions
- File size ranges
- Created dates (monthly)
- MIME types
- Status

### Performance Considerations

1. **Facet Size**: Limit the number of buckets to avoid memory issues
2. **Cardinality**: Use cardinality aggregations carefully on high-cardinality fields
3. **Nested Aggregations**: Have performance overhead, use judiciously
4. **Post-Filters**: More efficient for UI filtering without recomputing facets

## Best Practices

### 1. Filter Selection
- Use term filters for exact matches on keyword fields
- Use range filters for numeric and date ranges
- Combine multiple filters for complex criteria

### 2. Facet Design
- Choose appropriate facet types for your data
- Limit facet sizes to improve performance
- Use meaningful names and keys for facets

### 3. Query Optimization
- Apply filters that reduce the result set most effectively first
- Use post-filters for UI-driven filtering
- Consider caching facet results for static data

### 4. Field Mapping
- Ensure fields used for faceting are properly mapped (keyword, numeric, date)
- Text fields need `.keyword` subfield for terms aggregations
- Nested fields require proper nested mapping

### 5. User Experience
- Provide clear facet labels and counts
- Allow multiple filter selections
- Show applied filters clearly
- Enable filter removal

## Examples

### E-commerce Product Search
```json
{
  "query": "laptop",
  "filters": [
    {"field": "category", "type": "term", "value": "computers"},
    {"field": "price", "type": "range", "value": {"gte": 500, "lte": 1500}},
    {"field": "in_stock", "type": "term", "value": true}
  ],
  "facets": [
    {"name": "brands", "field": "brand", "type": "terms", "size": 20},
    {"name": "price_ranges", "field": "price", "type": "range", "ranges": [
      {"to": 500, "key": "Budget"},
      {"from": 500, "to": 1000, "key": "Mid-range"},
      {"from": 1000, "key": "Premium"}
    ]},
    {"name": "ratings", "field": "rating", "type": "terms", "size": 5}
  ]
}
```

### Media Asset Search
```json
{
  "query": "presentation",
  "filters": [
    {"field": "project_id", "type": "term", "value": "proj_123"},
    {"field": "created_at", "type": "range", "value": {"gte": "2024-01-01"}}
  ],
  "facets": [
    {"name": "asset_types", "field": "asset_type", "type": "terms"},
    {"name": "creators", "field": "created_by", "type": "terms", "size": 50},
    {"name": "tags", "field": "tags", "type": "terms", "size": 100}
  ]
}
```

### Log Analysis
```json
{
  "query": "error",
  "filters": [
    {"field": "level", "type": "term", "value": "ERROR"},
    {"field": "timestamp", "type": "range", "value": {"gte": "now-24h"}}
  ],
  "facets": [
    {"name": "error_timeline", "field": "timestamp", "type": "date_histogram", "interval": "hour"},
    {"name": "error_sources", "field": "source", "type": "terms", "size": 20},
    {"name": "error_codes", "field": "error_code", "type": "terms", "size": 50}
  ]
}
```

## Troubleshooting

### Common Issues

1. **Empty Facet Results**
   - Check if the field exists and has values
   - Verify field mapping (text vs keyword)
   - Ensure documents match your filters

2. **Incorrect Counts**
   - Verify filter vs post-filter usage
   - Check for nested field handling
   - Ensure proper aggregation configuration

3. **Performance Issues**
   - Reduce facet sizes
   - Limit the number of facets
   - Use post-filters when appropriate
   - Consider index optimization

4. **Validation Errors**
   - Ensure filter types match field types
   - Provide required range parameters
   - Use correct nested paths

For more information, see the [API Documentation](./API.md) or contact the development team.