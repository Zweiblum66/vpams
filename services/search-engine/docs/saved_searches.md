# Saved Searches API Documentation

## Overview

The Saved Searches feature allows users to save frequently used search queries along with their filters, sorting preferences, and other settings. Saved searches can be made public for sharing across the organization or kept private for personal use.

## Features

- **Save Complex Searches**: Store complete search queries with all parameters
- **Public/Private Sharing**: Control visibility of saved searches
- **Tagging System**: Organize saved searches with tags
- **Usage Tracking**: Monitor how often searches are used
- **Notifications**: Optional alerts for new matching results
- **Parameter Overrides**: Execute saved searches with modified parameters

## API Endpoints

### Create Saved Search
```http
POST /api/v1/search/saved
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "Recent Marketing Videos",
  "description": "Videos uploaded in the last 30 days with marketing tags",
  "query": {
    "query": "marketing",
    "search_type": "filtered",
    "indices": ["assets"],
    "filters": [
      {
        "field": "asset_type",
        "type": "term",
        "value": "video"
      },
      {
        "field": "created_at",
        "type": "range",
        "value": {
          "gte": "now-30d"
        }
      }
    ],
    "size": 20,
    "sort_by": "created_at",
    "sort_order": "desc"
  },
  "is_public": true,
  "tags": ["marketing", "video", "recent"],
  "notify_on_new_results": true
}
```

### List Saved Searches
```http
GET /api/v1/search/saved?page=1&per_page=20&include_public=true
Authorization: Bearer {token}
```

Returns both user's own saved searches and optionally public searches from other users.

### Get Popular Saved Searches
```http
GET /api/v1/search/saved/popular?limit=10
```

Returns the most frequently used public saved searches.

### Search by Tags
```http
GET /api/v1/search/saved/by-tags?tags=marketing&tags=video&page=1&per_page=20
```

Find public saved searches with specific tags.

### Get Specific Saved Search
```http
GET /api/v1/search/saved/{search_id}
Authorization: Bearer {token}
```

### Update Saved Search
```http
PUT /api/v1/search/saved/{search_id}
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "Updated Search Name",
  "description": "Updated description",
  "is_public": false,
  "tags": ["updated", "tags"]
}
```

### Delete Saved Search
```http
DELETE /api/v1/search/saved/{search_id}
Authorization: Bearer {token}
```

### Execute Saved Search
```http
POST /api/v1/search/saved/{search_id}/execute
Content-Type: application/json
Authorization: Bearer {token}

{
  "size": 50,
  "from": 0,
  "sort_by": "relevance",
  "sort_order": "desc",
  "additional_filters": [
    {
      "field": "status",
      "type": "term",
      "value": "published"
    }
  ]
}
```

## Response Models

### SavedSearch
```json
{
  "id": "search_123",
  "user_id": "user_456",
  "name": "Recent Marketing Videos",
  "description": "Videos uploaded in the last 30 days",
  "query": {
    // Complete FilteredSearchQuery object
  },
  "is_public": true,
  "tags": ["marketing", "video"],
  "notify_on_new_results": true,
  "usage_count": 42,
  "last_used_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-01T09:00:00Z",
  "updated_at": "2024-01-10T14:30:00Z"
}
```

### SavedSearchList
```json
{
  "searches": [
    // Array of SavedSearch objects
  ],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "total_pages": 5
}
```

## Usage Examples

### Example 1: Save a Complex Search
```python
import httpx

saved_search = {
    "name": "High-res Images from Last Week",
    "query": {
        "query": "",
        "filters": [
            {"field": "asset_type", "type": "term", "value": "image"},
            {"field": "width", "type": "range", "value": {"gte": 1920}},
            {"field": "created_at", "type": "range", "value": {"gte": "now-7d"}}
        ],
        "sort_by": "file_size",
        "sort_order": "desc"
    },
    "tags": ["high-res", "recent", "images"]
}

response = await client.post(
    "/api/v1/search/saved",
    json=saved_search,
    headers={"Authorization": f"Bearer {token}"}
)
```

### Example 2: Execute with Overrides
```python
# Execute a saved search but change the size and add a filter
execute_params = {
    "size": 100,
    "additional_filters": [
        {"field": "project_id", "type": "term", "value": "proj_789"}
    ]
}

response = await client.post(
    f"/api/v1/search/saved/{search_id}/execute",
    json=execute_params,
    headers={"Authorization": f"Bearer {token}"}
)
```

## Best Practices

1. **Naming Convention**: Use descriptive names that clearly indicate what the search does
2. **Tags**: Use consistent tags to make searches discoverable
3. **Public vs Private**: Only make searches public if they're useful to others
4. **Maintenance**: Regularly review and update saved searches to ensure they remain relevant
5. **Notifications**: Use sparingly to avoid notification fatigue

## Implementation Notes

- Saved searches are stored in MongoDB for flexibility
- Usage statistics are tracked for popularity ranking
- Names must be unique per user
- Public searches are discoverable by all users
- Notifications are processed asynchronously via message queue