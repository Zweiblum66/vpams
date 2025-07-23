# Search Analytics API Documentation

## Overview

The Search Analytics feature provides comprehensive insights into search behavior across the entire MAMS platform. It tracks both authenticated and anonymous searches, enabling data-driven improvements to search functionality and content discovery.

## Features

- **Comprehensive Tracking**: Captures all search interactions including queries, filters, and clicks
- **Performance Monitoring**: Tracks response times and system performance
- **Trend Analysis**: Identifies search patterns and trends over time
- **User Segmentation**: Analyzes different user behavior patterns
- **Click-Through Tracking**: Measures search result effectiveness
- **Custom Reports**: Generate detailed analytics reports

## API Endpoints

### Get Search Analytics
```http
POST /api/v1/analytics/search
Content-Type: application/json

{
  "start_time": "2024-01-01T00:00:00Z",
  "end_time": "2024-01-31T23:59:59Z",
  "interval": "1d",
  "filters": {
    "search_type": "filtered",
    "query_contains": "marketing",
    "min_results": 10,
    "indices": ["assets"]
  }
}
```

### Get Performance Metrics
```http
POST /api/v1/analytics/search/performance
Content-Type: application/json

{
  "start_time": "2024-01-01T00:00:00Z",
  "end_time": "2024-01-31T23:59:59Z"
}
```

### Get Search Trends
```http
POST /api/v1/analytics/search/trends
Content-Type: application/json

{
  "start_time": "2024-01-01T00:00:00Z",
  "end_time": "2024-01-31T23:59:59Z",
  "interval": "1h"
}
```

### Generate Analytics Report
```http
POST /api/v1/analytics/search/report
Content-Type: application/json

{
  "start_time": "2024-01-01T00:00:00Z",
  "end_time": "2024-01-31T23:59:59Z",
  "interval": "1d"
}
```

### Get User Segments
```http
POST /api/v1/analytics/search/segments
Content-Type: application/json

{
  "start_time": "2024-01-01T00:00:00Z",
  "end_time": "2024-01-31T23:59:59Z"
}
```

### Log Search Click
```http
POST /api/v1/analytics/search/click
Content-Type: application/json

{
  "search_id": "search_123",
  "asset_id": "asset_456",
  "session_id": "session_789"
}
```

### Cleanup Old Analytics
```http
DELETE /api/v1/analytics/search/cleanup?older_than_days=365
Authorization: Bearer {admin_token}
```

## Request Models

### SearchAnalyticsTimeRange
```json
{
  "start_time": "2024-01-01T00:00:00Z",
  "end_time": "2024-01-31T23:59:59Z",
  "interval": "1d"  // Options: 1h, 1d, 1w, 1M
}
```

### SearchAnalyticsFilter
```json
{
  "search_type": "filtered",
  "user_id": "user_123",
  "query_contains": "marketing",
  "min_results": 10,
  "max_results": 1000,
  "min_response_time": 100,
  "max_response_time": 5000,
  "indices": ["assets", "metadata"],
  "has_clicks": true
}
```

## Response Models

### SearchAnalyticsAggregation
```json
{
  "total_searches": 12500,
  "unique_queries": 3421,
  "unique_users": 256,
  "unique_sessions": 4532,
  "avg_response_time_ms": 145,
  "avg_results_per_search": 28.5,
  "avg_clicks_per_search": 2.3,
  "click_through_rate": 0.65,
  "zero_result_rate": 0.12,
  "top_queries": [
    {"query": "marketing video", "count": 234, "avg_results": 42},
    {"query": "Q4 report", "count": 189, "avg_results": 15}
  ],
  "top_filters": [
    {"filter": "asset_type:video", "count": 567},
    {"filter": "created_at:[2024-01-01 TO *]", "count": 432}
  ],
  "search_patterns": [
    {
      "pattern": "refinement",
      "description": "Users refining searches",
      "percentage": 34.5
    }
  ],
  "performance_metrics": {
    "p50_response_time": 120,
    "p95_response_time": 450,
    "p99_response_time": 1200
  }
}
```

### SearchPerformanceMetrics
```json
{
  "avg_response_time_ms": 145,
  "p50_response_time_ms": 120,
  "p95_response_time_ms": 450,
  "p99_response_time_ms": 1200,
  "slowest_queries": [
    {"query": "complex aggregation", "response_time_ms": 2345},
    {"query": "large dataset search", "response_time_ms": 1890}
  ],
  "fastest_queries": [
    {"query": "simple term search", "response_time_ms": 45},
    {"query": "cached results", "response_time_ms": 52}
  ],
  "error_rate": 0.002,
  "timeout_rate": 0.0005
}
```

### SearchTrendData
```json
{
  "timestamp": "2024-01-15T00:00:00Z",
  "search_count": 432,
  "unique_users": 87,
  "avg_response_time_ms": 142,
  "avg_results": 26.7,
  "click_through_rate": 0.68
}
```

### SearchAnalyticsReport
```json
{
  "summary": {
    // SearchAnalyticsAggregation object
  },
  "trends": [
    // Array of SearchTrendData objects
  ],
  "performance": {
    // SearchPerformanceMetrics object
  },
  "top_queries": [
    {
      "query": "marketing",
      "count": 543,
      "trend": "increasing",
      "avg_ctr": 0.72
    }
  ],
  "search_patterns": [
    {
      "pattern": "morning_peak",
      "description": "High search volume 9-11 AM",
      "impact": "high"
    }
  ],
  "user_segments": [
    {
      "segment": "power_users",
      "user_count": 45,
      "avg_searches_per_day": 25.3,
      "characteristics": ["complex_queries", "high_filter_usage"]
    }
  ],
  "generated_at": "2024-01-31T15:30:00Z",
  "time_range": {
    // SearchAnalyticsTimeRange object
  }
}
```

## Usage Examples

### Example 1: Monitor Search Performance
```python
import httpx
from datetime import datetime, timedelta

# Get performance metrics for the last 24 hours
time_range = {
    "start_time": (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z",
    "end_time": datetime.utcnow().isoformat() + "Z",
    "interval": "1h"
}

response = await client.post(
    "/api/v1/analytics/search/performance",
    json=time_range
)

metrics = response.json()
print(f"Average response time: {metrics['avg_response_time_ms']}ms")
print(f"95th percentile: {metrics['p95_response_time_ms']}ms")
print(f"Error rate: {metrics['error_rate'] * 100:.2f}%")
```

### Example 2: Analyze Search Trends
```python
# Get hourly search trends for the last week
time_range = {
    "start_time": (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z",
    "end_time": datetime.utcnow().isoformat() + "Z",
    "interval": "1h"
}

response = await client.post(
    "/api/v1/analytics/search/trends",
    json=time_range
)

trends = response.json()
for trend in trends:
    print(f"{trend['timestamp']}: {trend['search_count']} searches, "
          f"CTR: {trend['click_through_rate']:.2%}")
```

### Example 3: Generate Monthly Report
```python
# Generate a comprehensive report for the previous month
from dateutil.relativedelta import relativedelta

end_date = datetime.utcnow().replace(day=1) - timedelta(days=1)
start_date = end_date.replace(day=1)

report_request = {
    "start_time": start_date.isoformat() + "Z",
    "end_time": end_date.isoformat() + "Z",
    "interval": "1d",
    "filters": {
        "min_results": 1  # Exclude searches with no results
    }
}

response = await client.post(
    "/api/v1/analytics/search/report",
    json=report_request
)

report = response.json()
print(f"Total searches: {report['summary']['total_searches']}")
print(f"Click-through rate: {report['summary']['click_through_rate']:.2%}")
print("\nTop queries:")
for query in report['top_queries'][:5]:
    print(f"  {query['query']}: {query['count']} searches")
```

### Example 4: Track Click-Through Rate
```python
# Log a click when user selects a search result
async def on_search_result_click(search_id: str, asset_id: str):
    await client.post(
        "/api/v1/analytics/search/click",
        json={
            "search_id": search_id,
            "asset_id": asset_id,
            "session_id": get_session_id()
        }
    )
```

## Analytics Insights

### Key Metrics to Monitor

1. **Search Volume**: Total searches and unique queries
2. **Performance**: Response times (p50, p95, p99)
3. **Effectiveness**: Click-through rate and zero-result rate
4. **User Behavior**: Search refinement patterns
5. **Content Gaps**: Common searches with few results

### Search Patterns

The system automatically identifies patterns such as:
- **Peak Usage Times**: When search volume is highest
- **Query Refinement**: Users modifying searches for better results
- **Filter Usage**: Most common filter combinations
- **Abandonment**: Searches with no clicks
- **Navigation**: Multi-page result browsing

### User Segmentation

Users are automatically segmented into:
- **Power Users**: High search volume, complex queries
- **Regular Users**: Moderate usage, standard queries
- **Casual Users**: Infrequent searches, simple queries
- **New Users**: Recently started using search

## Data Privacy and Retention

### Privacy Considerations
- Anonymous searches are tracked with session IDs only
- IP addresses are hashed for privacy
- User-specific data requires authentication to access
- Aggregated data is anonymized

### Data Retention
- Raw analytics data: 365 days (configurable)
- Aggregated daily stats: 2 years
- Monthly summaries: 5 years
- Hourly data: 90 days

## Implementation Notes

- Analytics are collected asynchronously to avoid impacting search performance
- Data is stored in MongoDB with time-series optimizations
- Aggregations are pre-computed for common time ranges
- Click tracking uses a separate collection for performance
- Session tracking works for both authenticated and anonymous users