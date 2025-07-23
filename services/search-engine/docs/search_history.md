# Search History API Documentation

## Overview

The Search History feature tracks all searches performed by authenticated users, providing insights into search patterns and enabling users to revisit previous searches. This data is invaluable for improving search functionality and understanding user behavior.

## Features

- **Automatic Tracking**: All authenticated searches are automatically logged
- **User Privacy**: Each user can only see their own search history
- **Comprehensive Stats**: View search patterns and usage statistics
- **Cleanup Options**: Delete old entries or clear all history
- **Performance Metrics**: Track response times and result counts

## API Endpoints

### Get Search History
```http
GET /api/v1/search/history?page=1&per_page=20&search_type=filtered&query_filter=marketing
Authorization: Bearer {token}
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `search_type`: Filter by search type (optional)
- `query_filter`: Filter by query text (optional)

### Get Search History Statistics
```http
GET /api/v1/search/history/stats?days=30
Authorization: Bearer {token}
```

**Query Parameters:**
- `days`: Number of days to analyze (default: 30, max: 365)

### Delete Old Search History
```http
DELETE /api/v1/search/history?older_than_days=90
Authorization: Bearer {token}
```

**Query Parameters:**
- `older_than_days`: Delete entries older than this many days (default: 90)

### Clear All Search History
```http
DELETE /api/v1/search/history/clear
Authorization: Bearer {token}
```

## Response Models

### SearchHistoryEntry
```json
{
  "id": "history_123",
  "user_id": "user_456",
  "query": "marketing video",
  "search_type": "filtered",
  "indices": ["assets"],
  "filters": {
    "asset_type": "video",
    "created_at": {"gte": "2024-01-01"}
  },
  "results_count": 42,
  "response_time_ms": 125,
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### SearchHistoryList
```json
{
  "entries": [
    // Array of SearchHistoryEntry objects
  ],
  "total": 500,
  "page": 1,
  "per_page": 20,
  "total_pages": 25
}
```

### SearchHistoryStats
```json
{
  "total_searches": 1250,
  "unique_queries": 342,
  "avg_response_time_ms": 145,
  "avg_results_per_search": 28.5,
  "most_common_search_type": "filtered",
  "top_queries": [
    {"query": "marketing", "count": 45},
    {"query": "video production", "count": 38},
    {"query": "Q4 2023", "count": 32}
  ],
  "search_volume_by_day": {
    "2024-01-15": 42,
    "2024-01-14": 38,
    "2024-01-13": 51
  }
}
```

## Usage Examples

### Example 1: View Recent Searches
```python
import httpx

# Get the first page of search history
response = await client.get(
    "/api/v1/search/history",
    headers={"Authorization": f"Bearer {token}"}
)

history = response.json()
print(f"Total searches: {history['total']}")
for entry in history['entries']:
    print(f"{entry['timestamp']}: {entry['query']} ({entry['results_count']} results)")
```

### Example 2: Analyze Search Patterns
```python
# Get search statistics for the last 30 days
response = await client.get(
    "/api/v1/search/history/stats?days=30",
    headers={"Authorization": f"Bearer {token}"}
)

stats = response.json()
print(f"Total searches: {stats['total_searches']}")
print(f"Unique queries: {stats['unique_queries']}")
print(f"Average response time: {stats['avg_response_time_ms']}ms")

print("\nTop queries:")
for query in stats['top_queries']:
    print(f"  {query['query']}: {query['count']} times")
```

### Example 3: Clean Up Old History
```python
# Delete search history older than 180 days
response = await client.delete(
    "/api/v1/search/history?older_than_days=180",
    headers={"Authorization": f"Bearer {token}"}
)

result = response.json()
print(f"Deleted {result['message']}")
```

## Privacy and Data Retention

### Privacy Features
- Users can only access their own search history
- IP addresses are stored for security but can be anonymized
- User agents help identify device types for optimization

### Data Retention Policy
- Search history is retained for 365 days by default
- Users can delete their history at any time
- Administrators can configure system-wide retention policies
- Aggregated analytics are kept separately from individual history

## Performance Considerations

### Indexing
The search history collection is indexed on:
- `user_id` for fast user-specific queries
- `timestamp` for time-based filtering
- `query` for text search
- `search_type` for filtering

### Storage Optimization
- Old entries are automatically archived or deleted based on retention policy
- Response time and metadata are stored efficiently
- Aggregated statistics are pre-computed for performance

## Implementation Notes

- Search history is stored in MongoDB for flexibility
- Logging is asynchronous to avoid impacting search performance
- Statistics are calculated using MongoDB aggregation pipelines
- History entries include context like IP and user agent for security analysis