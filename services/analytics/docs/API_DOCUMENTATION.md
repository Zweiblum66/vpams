# MAMS Analytics API Documentation

## Overview

The MAMS Analytics API provides comprehensive analytics capabilities including event tracking, user behavior analysis, custom reporting, and real-time insights. This RESTful API is designed for high-performance analytics workloads with enterprise-grade features.

**Base URL**: `https://api.mams.example.com`
**API Version**: v1
**Authentication**: JWT Bearer Token

## Table of Contents

1. [Authentication](#authentication)
2. [Rate Limits](#rate-limits)
3. [Core Analytics API](#core-analytics-api)
4. [User Behavior API](#user-behavior-api)
5. [Custom Reports API](#custom-reports-api)
6. [Real-time Analytics API](#real-time-analytics-api)
7. [Usage Analytics API](#usage-analytics-api)
8. [Error Handling](#error-handling)
9. [SDKs and Libraries](#sdks-and-libraries)

## Authentication

All API requests require authentication using JWT Bearer tokens.

```http
Authorization: Bearer <your-jwt-token>
```

### Required Permissions

- `analytics.view` - View analytics data
- `analytics.create_reports` - Create and manage reports
- `analytics.export` - Export analytics data
- `analytics.admin` - Administrative access
- `analytics.view_executive` - Executive dashboard access

## Rate Limits

| Endpoint Category | Rate Limit |
|------------------|------------|
| Event Tracking | 1000 requests/hour per user |
| Batch Event Tracking | 100 batches/hour per user |
| Analytics Queries | 100 requests/hour per user |
| Data Export | 10 requests/day per user |
| Report Generation | 50 requests/day per user |

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Request limit per window
- `X-RateLimit-Remaining`: Remaining requests in window
- `X-RateLimit-Reset`: Unix timestamp when window resets

## Core Analytics API

### Get Analytics Overview

Get a comprehensive overview of analytics data.

```http
GET /api/v1/analytics/overview
```

**Parameters:**
- `timeframe` (query, optional): Time range (`1h`, `24h`, `7d`, `30d`) - Default: `24h`
- `segment` (query, optional): User segment filter

**Response:**
```json
{
  "timeframe": "24h",
  "total_events": 15420,
  "unique_users": 1250,
  "active_sessions": 320,
  "top_events": [
    {
      "event_name": "page_view",
      "count": 8500,
      "percentage": 55.1
    }
  ],
  "user_segments": {
    "power_user": 125,
    "casual_user": 980,
    "new_user": 145
  },
  "key_metrics": {
    "avg_session_duration_minutes": 18.5,
    "bounce_rate_percent": 12.3,
    "conversion_rate_percent": 4.7,
    "retention_rate_percent": 67.8
  },
  "trends": {
    "total_events_change_percent": 15.2,
    "unique_users_change_percent": 8.7
  },
  "generated_at": "2025-07-19T10:00:00Z"
}
```

### Track Event

Track a single analytics event.

```http
POST /api/v1/analytics/events/track
```

**Request Body:**
```json
{
  "event_type": "user_action",
  "event_name": "asset_upload",
  "category": "content",
  "properties": {
    "asset_id": "asset-123",
    "file_size": 1024000,
    "file_type": "video"
  },
  "session_id": "sess-456",
  "duration_ms": 1500
}
```

**Response:**
```json
{
  "status": "accepted",
  "message": "Event tracking queued",
  "timestamp": "2025-07-19T10:00:00Z"
}
```

### Track Events Batch

Track multiple events in a single request.

```http
POST /api/v1/analytics/events/batch
```

**Request Body:**
```json
[
  {
    "event_type": "page_view",
    "event_name": "dashboard",
    "category": "navigation",
    "properties": {
      "page": "/dashboard",
      "referrer": "/login"
    }
  },
  {
    "event_type": "user_action",
    "event_name": "search",
    "category": "search",
    "properties": {
      "query": "video files",
      "results_count": 25
    }
  }
]
```

**Response:**
```json
{
  "status": "accepted",
  "message": "Batch of 2 events queued",
  "timestamp": "2025-07-19T10:00:00Z"
}
```

### Query Metrics

Query analytics metrics with flexible parameters.

```http
POST /api/v1/analytics/metrics/query
```

**Request Body:**
```json
{
  "metric_names": ["page_views", "user_sessions"],
  "start_date": "2025-07-12T00:00:00Z",
  "end_date": "2025-07-19T00:00:00Z",
  "granularity": "day",
  "group_by": ["date", "user_segment"],
  "filters": {
    "user_segment": ["power_user", "casual_user"]
  }
}
```

**Response:**
```json
{
  "metrics": [
    {
      "metric_name": "page_views",
      "data": [
        {
          "timestamp": "2025-07-19T00:00:00Z",
          "value": 1250,
          "dimensions": {
            "date": "2025-07-19",
            "user_segment": "power_user"
          }
        }
      ]
    }
  ],
  "query_parameters": {
    "metric_names": ["page_views", "user_sessions"],
    "start_date": "2025-07-12T00:00:00Z",
    "end_date": "2025-07-19T00:00:00Z",
    "granularity": "day",
    "group_by": ["date", "user_segment"],
    "filters": {
      "user_segment": ["power_user", "casual_user"]
    }
  },
  "generated_at": "2025-07-19T10:00:00Z"
}
```

### Get Available Metrics

Get list of all available metrics.

```http
GET /api/v1/analytics/metrics/available
```

**Response:**
```json
{
  "metrics": [
    {
      "name": "page_views",
      "description": "Total page views",
      "type": "counter",
      "dimensions": ["page", "user_id", "session_id"]
    },
    {
      "name": "user_sessions",
      "description": "Active user sessions",
      "type": "gauge",
      "dimensions": ["device_type", "browser", "country"]
    }
  ]
}
```

### Get Trends

Get trend analysis for a specific metric.

```http
GET /api/v1/analytics/trends
```

**Parameters:**
- `metric` (query, required): Metric to analyze
- `timeframe` (query, optional): Time range (`1h`, `24h`, `7d`, `30d`) - Default: `7d`
- `granularity` (query, optional): Data granularity (`1h`, `1d`) - Default: `1h`
- `comparison` (query, optional): Include period comparison - Default: `false`

**Response:**
```json
{
  "metric": "page_views",
  "timeframe": "7d",
  "granularity": "1h",
  "data": [
    {
      "timestamp": "2025-07-19T09:00:00Z",
      "value": 125
    },
    {
      "timestamp": "2025-07-19T10:00:00Z",
      "value": 142
    }
  ],
  "comparison": {
    "period": "2025-07-05T10:00:00Z to 2025-07-12T10:00:00Z",
    "data": [
      {
        "timestamp": "2025-07-12T09:00:00Z",
        "value": 98
      }
    ]
  },
  "generated_at": "2025-07-19T10:00:00Z"
}
```

### Executive Dashboard

Get executive dashboard with high-level KPIs.

```http
GET /api/v1/analytics/dashboards/executive
```

**Parameters:**
- `period` (query, optional): Reporting period (`7d`, `30d`, `90d`) - Default: `30d`

**Response:**
```json
{
  "period": "30d",
  "kpis": {
    "total_users": 2450,
    "active_users": 1820,
    "user_growth": 12.5,
    "engagement_score": 18.7,
    "retention_rate": 67.8,
    "feature_adoption": {
      "search": 85.4,
      "upload": 62.3,
      "download": 78.9
    }
  },
  "user_distribution": {
    "by_segment": {
      "power_user": 245,
      "casual_user": 1470,
      "new_user": 735
    },
    "by_activity": {
      "high": 420,
      "medium": 980,
      "low": 1050
    }
  },
  "trends": {
    "total_events_growth": 15.2,
    "unique_users_growth": 8.7
  },
  "generated_at": "2025-07-19T10:00:00Z"
}
```

### Operational Dashboard

Get operational dashboard with system health metrics.

```http
GET /api/v1/analytics/dashboards/operational
```

**Parameters:**
- `timeframe` (query, optional): Time range (`1h`, `24h`, `7d`) - Default: `24h`

**Response:**
```json
{
  "timeframe": "24h",
  "system_health": {
    "api_response_time_ms": 150,
    "error_rate_percent": 0.1,
    "throughput_requests_per_second": 45,
    "database_connection_pool_usage": 65,
    "memory_usage_percent": 72,
    "cpu_usage_percent": 45
  },
  "traffic_metrics": {
    "total_requests": 52000,
    "unique_visitors": 1250,
    "page_views": 18500,
    "bounce_rate": 12.3
  },
  "user_activity": {
    "active_sessions": 320,
    "avg_session_duration": 18.5,
    "top_pages": [
      {
        "page": "/dashboard",
        "views": 5200,
        "percentage": 28.1
      }
    ],
    "top_events": [
      {
        "event": "page_view",
        "count": 8500,
        "percentage": 55.1
      }
    ]
  },
  "alerts": [
    {
      "level": "warning",
      "message": "API response time above normal",
      "metric": "api_response_time_ms",
      "value": 150,
      "threshold": 200
    }
  ],
  "generated_at": "2025-07-19T10:00:00Z"
}
```

### Export Data

Export analytics data in various formats.

```http
GET /api/v1/analytics/export
```

**Parameters:**
- `format` (query, optional): Export format (`csv`, `json`, `excel`) - Default: `csv`
- `start_date` (query, optional): Start date (ISO format)
- `end_date` (query, optional): End date (ISO format)
- `data_types` (query, optional): Data types to export (`events`, `sessions`, `interactions`)

**Response:**
```json
{
  "export_id": "exp_123456",
  "format": "csv",
  "data_types": ["events", "sessions"],
  "date_range": {
    "start": "2025-07-12T00:00:00Z",
    "end": "2025-07-19T00:00:00Z"
  },
  "download_url": "https://api.mams.example.com/exports/exp_123456/download",
  "expires_at": "2025-07-20T10:00:00Z",
  "generated_at": "2025-07-19T10:00:00Z"
}
```

## User Behavior API

### Track User Action

Track user behavior for analysis.

```http
POST /api/v1/behavior/track
```

**Request Body:**
```json
{
  "action": "asset_upload",
  "context": {
    "asset_id": "asset-123",
    "file_size": 1024000
  },
  "session_id": "sess-456"
}
```

### Get User Insights

Get detailed behavior insights for a user.

```http
GET /api/v1/behavior/insights/{user_id}
```

**Response:**
```json
{
  "user_id": "user-123",
  "segment": "power_user",
  "activity_level": "high",
  "current_metrics": {
    "sessions_count": 25,
    "total_time_minutes": 480,
    "actions_count": 150
  },
  "trends": {
    "sessions_trend": 5,
    "time_trend": 60,
    "activity_trend": 25
  },
  "feature_usage": {
    "search": 50,
    "upload": 15,
    "download": 25
  },
  "recent_activity": [
    {
      "timestamp": "2025-07-19T10:00:00Z",
      "action": "asset_upload",
      "category": "content"
    }
  ],
  "recommendations": [
    "Try creating automated workflows",
    "Explore advanced search features"
  ]
}
```

### Get User Segmentation

Get user segmentation data.

```http
GET /api/v1/behavior/segments
```

**Response:**
```json
{
  "segments": {
    "power_user": ["user1", "user2"],
    "casual_user": ["user3", "user4"],
    "new_user": ["user5"]
  },
  "total_users": 5,
  "segmentation_timestamp": "2025-07-19T10:00:00Z"
}
```

### Get Engagement Metrics

Get overall user engagement metrics.

```http
GET /api/v1/behavior/engagement
```

**Response:**
```json
{
  "total_active_users": 150,
  "avg_session_duration_minutes": 18.5,
  "segments_distribution": {
    "power_user": 25,
    "casual_user": 80,
    "new_user": 45
  },
  "feature_adoption_rates": {
    "search": 85.5,
    "upload": 62.3,
    "workflow": 34.7
  },
  "retention_metrics": {
    "week_7_retention_percent": 45.2,
    "month_30_retention_percent": 28.8
  },
  "generated_at": "2025-07-19T10:00:00Z"
}
```

## Custom Reports API

### Create Report Definition

Create a new custom report definition.

```http
POST /api/v1/reports/definitions
```

**Request Body:**
```json
{
  "name": "User Activity Report",
  "description": "Daily user activity metrics",
  "report_type": "user_activity",
  "data_sources": ["events", "user_sessions"],
  "filters": [
    {
      "field": "event_type",
      "operator": "eq",
      "value": "user_action"
    }
  ],
  "date_range": {
    "relative": "last_7d"
  },
  "charts": [
    {
      "chart_type": "line",
      "title": "Daily Active Users",
      "x_axis": "date",
      "y_axis": "user_count",
      "data_source": "events",
      "group_by": "date",
      "aggregation": "count"
    }
  ],
  "format": "json",
  "tags": ["user", "activity"],
  "is_public": false
}
```

**Response:**
```json
{
  "id": "report-123",
  "message": "Report definition created successfully",
  "created_at": "2025-07-19T10:00:00Z"
}
```

### List Report Definitions

Get list of available report definitions.

```http
GET /api/v1/reports/definitions
```

**Parameters:**
- `created_by` (query, optional): Filter by creator
- `is_public` (query, optional): Filter by public status
- `tags` (query, optional): Filter by tags (comma-separated)

**Response:**
```json
[
  {
    "id": "report-123",
    "name": "User Activity Report",
    "description": "Daily user activity metrics",
    "report_type": "user_activity",
    "created_by": "user-456",
    "created_at": "2025-07-19T10:00:00Z",
    "format": "json",
    "is_public": false,
    "last_generated": null,
    "tags": ["user", "activity"]
  }
]
```

### Generate Report

Generate a report based on definition.

```http
POST /api/v1/reports/generate
```

**Request Body:**
```json
{
  "definition_id": "report-123",
  "custom_filters": [
    {
      "field": "user_segment",
      "operator": "eq",
      "value": "power_user"
    }
  ]
}
```

**Response:**
```json
{
  "status": "completed",
  "generated_at": "2025-07-19T10:00:00Z",
  "report": {
    "report_id": "report-123",
    "name": "User Activity Report",
    "data": {
      "events": [...]
    },
    "charts": [...]
  }
}
```

### Get Report Templates

Get available report templates.

```http
GET /api/v1/reports/templates
```

**Response:**
```json
[
  {
    "id": "user_activity_summary",
    "name": "User Activity Summary",
    "description": "Overview of user activity metrics",
    "report_type": "user_activity",
    "data_sources": ["events", "user_sessions"],
    "charts": [...]
  }
]
```

## Error Handling

All API endpoints return standardized error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "timeframe",
      "issue": "Must be one of: 1h, 24h, 7d, 30d"
    },
    "timestamp": "2025-07-19T10:00:00Z",
    "request_id": "req_abc123"
  }
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `AUTHENTICATION_REQUIRED` | 401 | Authentication required |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `INTERNAL_SERVER_ERROR` | 500 | Internal server error |

## Event Types

The following event types are supported:

- `page_view` - Page view events
- `user_action` - User interaction events
- `api_call` - API call events
- `asset_upload` - Asset upload events
- `asset_download` - Asset download events
- `asset_view` - Asset view events
- `search_query` - Search query events
- `workflow_start` - Workflow start events
- `workflow_complete` - Workflow completion events
- `login` - User login events
- `logout` - User logout events
- `error` - Error events
- `system_event` - System-generated events

## SDKs and Libraries

### JavaScript/TypeScript SDK

```bash
npm install @mams/analytics-sdk
```

```javascript
import { AnalyticsClient } from '@mams/analytics-sdk';

const analytics = new AnalyticsClient({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.mams.example.com'
});

// Track event
await analytics.track('page_view', {
  page: '/dashboard',
  referrer: '/login'
});

// Get overview
const overview = await analytics.getOverview('24h');
```

### Python SDK

```bash
pip install mams-analytics-sdk
```

```python
from mams_analytics import AnalyticsClient

analytics = AnalyticsClient(
    api_key='your-api-key',
    base_url='https://api.mams.example.com'
)

# Track event
analytics.track('user_action', 'asset_upload', {
    'asset_id': 'asset-123',
    'file_size': 1024000
})

# Get overview
overview = analytics.get_overview(timeframe='24h')
```

### Go SDK

```bash
go get github.com/mams/analytics-go
```

```go
import "github.com/mams/analytics-go"

client := analytics.NewClient("your-api-key", "https://api.mams.example.com")

// Track event
err := client.Track("page_view", map[string]interface{}{
    "page": "/dashboard",
    "referrer": "/login",
})

// Get overview
overview, err := client.GetOverview("24h")
```

## Best Practices

1. **Event Tracking**
   - Use descriptive event names
   - Include relevant context in properties
   - Batch events when possible for better performance
   - Implement client-side queuing for reliability

2. **Performance**
   - Use appropriate timeframes for queries
   - Implement caching for frequently accessed data
   - Use background tasks for heavy analytics processing
   - Monitor rate limits and implement backoff

3. **Data Quality**
   - Validate event data before sending
   - Use consistent naming conventions
   - Include user and session identifiers
   - Handle edge cases gracefully

4. **Security**
   - Never expose sensitive data in event properties
   - Use proper authentication and authorization
   - Implement data retention policies
   - Audit access to analytics data

## Support

For technical support and questions:
- Email: analytics-support@mams.example.com
- Documentation: https://docs.mams.example.com/analytics
- GitHub Issues: https://github.com/mams/analytics/issues