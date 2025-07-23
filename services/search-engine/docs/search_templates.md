# Search Templates

The Search Templates feature allows users to create, manage, and execute reusable search configurations. This enables consistent search experiences across teams and provides a way to save complex search setups for repeated use.

## Overview

Search Templates are structured configurations that define:
- Search query patterns with parameter substitution
- Default filters and facets
- Search type and ranking preferences
- Index targeting and field specifications
- Execution parameters and validation rules

## Core Features

### Template Types

1. **Basic Templates** - Simple keyword searches with basic filters
2. **Advanced Templates** - Complex queries with multiple conditions
3. **Filtered Templates** - Searches with predefined filter sets
4. **Fuzzy Templates** - Approximate matching with configurable fuzziness
5. **Phonetic Templates** - Sound-based matching for names and titles
6. **Synonym Templates** - Expanded searches using synonyms
7. **Natural Language Templates** - AI-powered query understanding
8. **Metadata-Focused Templates** - Searches targeting specific metadata fields
9. **Custom Templates** - User-defined search logic

### Template Categories

- **General** - Universal search templates
- **Media Type** - Video, audio, image-specific searches
- **Workflow** - Production, editorial, review workflows
- **Technical** - Format, quality, technical specifications
- **Editorial** - Content, story, editorial workflows
- **Archive** - Historical, archival content searches
- **Rights** - License, usage rights, compliance searches
- **Custom** - Organization-specific categories

### Template Management

#### Creating Templates

```python
from src.models.schemas import SearchTemplateCreate, SearchTemplateConfig

# Define template configuration
config = SearchTemplateConfig(
    search_type="basic",
    default_query="videos about {topic}",
    indices=["assets", "metadata"],
    fields=["title", "description", "tags"],
    default_filters=[
        {
            "field": "asset_type",
            "type": "term",
            "value": "video"
        }
    ]
)

# Create template
template = SearchTemplateCreate(
    name="Video Topic Search",
    description="Search for videos about specific topics",
    category="media_type",
    template_type="basic",
    config=config,
    parameters=[
        {
            "name": "topic",
            "type": "string",
            "description": "Topic to search for",
            "required": True
        }
    ],
    tags=["video", "topic", "content"],
    is_public=False
)
```

#### Parameter Substitution

Templates support parameter substitution using `{parameter_name}` syntax:

```json
{
    "config": {
        "default_query": "find {content_type} from {date_range}",
        "default_filters": [
            {
                "field": "created_by",
                "type": "term",
                "value": "{user_id}"
            }
        ]
    },
    "parameters": [
        {
            "name": "content_type",
            "type": "string",
            "description": "Type of content to search for",
            "required": true
        },
        {
            "name": "date_range",
            "type": "string",
            "description": "Date range for content",
            "required": false,
            "default": "last week"
        },
        {
            "name": "user_id",
            "type": "string",
            "description": "User ID filter",
            "required": false
        }
    ]
}
```

## API Endpoints

### Template Management

#### Create Template
```http
POST /search/templates
Content-Type: application/json

{
    "name": "Video Production Search",
    "description": "Search for video assets in production",
    "category": "workflow",
    "template_type": "filtered",
    "config": {
        "search_type": "advanced",
        "default_query": "{query}",
        "indices": ["assets"],
        "fields": ["title", "description"],
        "default_filters": [
            {
                "field": "asset_type",
                "type": "term",
                "value": "video"
            },
            {
                "field": "status",
                "type": "term",
                "value": "in_production"
            }
        ]
    },
    "parameters": [
        {
            "name": "query",
            "type": "string",
            "description": "Search query",
            "required": true
        }
    ],
    "tags": ["video", "production"],
    "is_public": false
}
```

#### List Templates
```http
GET /search/templates?category=workflow&template_type=filtered&page=1&limit=20
```

#### Get Template
```http
GET /search/templates/{template_id}
```

#### Update Template
```http
PUT /search/templates/{template_id}
Content-Type: application/json

{
    "name": "Updated Template Name",
    "description": "Updated description",
    "is_public": true
}
```

#### Delete Template
```http
DELETE /search/templates/{template_id}
```

### Template Execution

#### Execute Template
```http
POST /search/templates/{template_id}/execute
Content-Type: application/json

{
    "parameters": {
        "query": "marketing campaign",
        "page": 1,
        "limit": 20
    }
}
```

Response:
```json
{
    "template_id": "template-123",
    "template_name": "Video Production Search",
    "search_response": {
        "hits": [...],
        "total": 150,
        "took": 45,
        "aggregations": {...}
    },
    "execution_time": 0.234,
    "executed_at": "2024-01-15T10:30:00Z"
}
```

### Template Favorites

#### Add to Favorites
```http
POST /search/templates/{template_id}/favorites
```

#### Remove from Favorites
```http
DELETE /search/templates/{template_id}/favorites
```

### Template Statistics

#### Get Template Stats
```http
GET /search/templates/{template_id}/stats
```

Response:
```json
{
    "template_id": "template-123",
    "usage_count": 45,
    "favorite_count": 12,
    "last_used": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-01T00:00:00Z"
}
```

### Template Sharing

#### Export Template
```http
GET /search/templates/{template_id}/export
```

#### Import Template
```http
POST /search/templates/import
Content-Type: application/json

{
    "template": {
        "name": "Imported Template",
        "description": "Template imported from another system",
        "category": "general",
        "template_type": "basic",
        "config": {...},
        "parameters": [...],
        "tags": ["imported"],
        "is_public": false
    },
    "format_version": "1.0"
}
```

#### Share Template
```http
POST /search/templates/{template_id}/share
Content-Type: application/json

{
    "shared_with": ["user1", "user2"],
    "permissions": ["read", "execute"]
}
```

## Advanced Features

### Template Validation

Templates are validated for:
- Required fields and proper structure
- Parameter type checking
- Query syntax validation
- Filter compatibility
- Performance optimization

### Template Versioning

Templates maintain version history:
- Automatic version increments on updates
- Version tracking for audit trails
- Rollback capabilities (future feature)

### Template Analytics

Track template usage and performance:
- Execution count and frequency
- Average execution time
- User adoption metrics
- Success/failure rates

### Template Inheritance

Templates can inherit from other templates:
- Base template configuration
- Parameter overrides
- Configuration extensions
- Hierarchical organization

## Security and Access Control

### Permission Levels

1. **Owner** - Full control (create, read, update, delete, share)
2. **Shared User** - Limited access based on shared permissions
3. **Public Reader** - Read and execute public templates
4. **Anonymous** - Execute public templates only

### Sharing Permissions

- **read** - View template configuration
- **execute** - Run template searches
- **duplicate** - Create copies of the template
- **share** - Share template with other users

## Best Practices

### Template Design

1. **Use Clear Names** - Descriptive, searchable names
2. **Add Descriptions** - Explain template purpose and usage
3. **Tag Appropriately** - Use relevant tags for discovery
4. **Define Parameters** - Clear parameter descriptions and types
5. **Test Thoroughly** - Validate templates before sharing

### Performance Optimization

1. **Limit Scope** - Target specific indices when possible
2. **Use Filters** - Apply filters to reduce result sets
3. **Optimize Queries** - Use efficient query patterns
4. **Cache Results** - Consider caching for frequent templates
5. **Monitor Performance** - Track execution times and optimize

### Organization

1. **Use Categories** - Organize templates by purpose
2. **Consistent Naming** - Follow naming conventions
3. **Version Control** - Track template changes
4. **Documentation** - Maintain template documentation
5. **Regular Cleanup** - Remove unused templates

## Error Handling

### Common Error Scenarios

1. **Template Not Found** - Template ID doesn't exist
2. **Access Denied** - User lacks permission
3. **Invalid Parameters** - Missing or invalid parameter values
4. **Query Execution Error** - Search service errors
5. **Validation Error** - Template configuration issues

### Error Response Format

```json
{
    "error": {
        "code": "TEMPLATE_NOT_FOUND",
        "message": "Search template not found",
        "details": {
            "template_id": "template-123"
        },
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "req_abc123"
    }
}
```

## Integration Examples

### Frontend Integration

```javascript
// Execute search template
const executeTemplate = async (templateId, parameters) => {
    const response = await fetch(`/search/templates/${templateId}/execute`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ parameters })
    });
    
    if (!response.ok) {
        throw new Error(`Template execution failed: ${response.statusText}`);
    }
    
    return response.json();
};

// Use template
const results = await executeTemplate('template-123', {
    query: 'product launch',
    date_range: 'last month'
});
```

### Workflow Integration

```python
# Automated template execution in workflow
async def process_content_search(content_type, project_id):
    template_id = get_template_for_content_type(content_type)
    
    execution_data = SearchTemplateExecute(
        parameters={
            'content_type': content_type,
            'project_id': project_id,
            'status': 'ready_for_review'
        }
    )
    
    results = await search_template_service.execute_template(
        template_id=template_id,
        execution_data=execution_data,
        user_id=current_user.id
    )
    
    return results.search_response
```

## Migration and Backup

### Template Export/Import

Templates can be exported for:
- Backup and disaster recovery
- Environment migration (dev to prod)
- Template sharing across organizations
- Version control integration

### Bulk Operations

```python
# Export all templates
templates = await search_template_service.list_templates(
    user_id=user_id,
    limit=1000
)

exports = []
for template in templates.templates:
    export = await search_template_service.export_template(
        template_id=template.id,
        user_id=user_id
    )
    exports.append(export)

# Save to backup system
save_template_backup(exports)
```

This comprehensive search templates system provides powerful capabilities for creating, managing, and executing reusable search configurations, enabling consistent and efficient search experiences across the MAMS platform.