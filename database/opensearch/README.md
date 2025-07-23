# MAMS OpenSearch Setup

This directory contains the OpenSearch configuration and initialization scripts for the MAMS (Media Asset Management System) search engine.

## Overview

OpenSearch is used in MAMS for:

- **Full-text Search**: Advanced search across all asset metadata and content
- **Faceted Search**: Multi-dimensional filtering and aggregations
- **Analytics**: Search analytics and usage patterns
- **Audit Logging**: Centralized log storage and analysis
- **Real-time Dashboards**: Kibana-style data visualization
- **Auto-completion**: Search suggestions and auto-complete

## Quick Start

1. **Start OpenSearch**:
   ```bash
   cd database/opensearch
   docker-compose up -d
   ```

2. **Initialize with Sample Data**:
   ```bash
   # Install dependencies
   pip install requests

   # Run initialization script
   python data/init-opensearch.py
   ```

3. **Access OpenSearch Dashboards**:
   - URL: http://localhost:5601
   - No authentication required (development mode)

4. **Direct API Access**:
   - URL: http://localhost:9200
   - Example: `curl http://localhost:9200/_cluster/health`

## Configuration

### OpenSearch Settings (`config/opensearch.yml`)

Key configuration settings for MAMS:

- **Cluster**: Single-node setup for development
- **Memory**: 1GB heap size
- **Security**: Disabled for development
- **Discovery**: Single-node discovery
- **Performance**: Optimized for search workloads

### Index Structure

MAMS uses the following indices:

- **mams-assets**: Asset metadata and content
- **mams-metadata**: Flexible metadata storage
- **mams-audit-logs**: System audit logs
- **mams-search-analytics**: Search usage analytics

## Index Mappings

### Assets Index (`mams-assets`)

Stores searchable asset data with:
- Full-text search on title, description, keywords
- Faceted search on content type, tags, dates
- Autocomplete suggestions
- Nested transcription data
- AI analysis results

### Metadata Index (`mams-metadata`)

Flexible metadata storage with:
- Dynamic field mapping
- Multi-language support
- Validation tracking
- Schema versioning

### Audit Logs Index (`mams-audit-logs`)

System logging with:
- Time-based partitioning
- Security event tracking
- Performance metrics
- User activity monitoring

### Search Analytics Index (`mams-search-analytics`)

Search behavior analysis with:
- Query performance tracking
- User interaction patterns
- Click-through analysis
- Search intent detection

## Sample Data

The initialization script creates comprehensive sample data:

- **50 Assets**: Mixed content types (video, image, audio, document)
- **100 Metadata**: Flexible metadata examples
- **100 Audit Logs**: System activity logs
- **200 Search Analytics**: Search usage patterns

## Common Operations

### Basic Search
```bash
# Search all assets
curl -X GET "localhost:9200/mams-assets/_search" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match_all": {}}}'

# Text search
curl -X GET "localhost:9200/mams-assets/_search" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match": {"title": "video"}}}'

# Filtered search
curl -X GET "localhost:9200/mams-assets/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "bool": {
        "must": [{"match": {"title": "sample"}}],
        "filter": [{"term": {"content_type": "video"}}]
      }
    }
  }'
```

### Aggregations
```bash
# Count by content type
curl -X GET "localhost:9200/mams-assets/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 0,
    "aggs": {
      "content_types": {
        "terms": {"field": "content_type"}
      }
    }
  }'

# Date histogram
curl -X GET "localhost:9200/mams-assets/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 0,
    "aggs": {
      "uploads_over_time": {
        "date_histogram": {
          "field": "uploaded_at",
          "calendar_interval": "day"
        }
      }
    }
  }'
```

### Auto-complete
```bash
# Suggest completions
curl -X GET "localhost:9200/mams-assets/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "suggest": {
      "asset_suggest": {
        "prefix": "sam",
        "completion": {
          "field": "suggest",
          "contexts": {
            "content_type": "video"
          }
        }
      }
    }
  }'
```

## Advanced Features

### Multi-language Search
```bash
# Search with language detection
curl -X GET "localhost:9200/mams-metadata/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "multi_match": {
        "query": "video production",
        "fields": ["field_value", "multilingual.*"]
      }
    }
  }'
```

### Nested Queries
```bash
# Search transcription segments
curl -X GET "localhost:9200/mams-assets/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "nested": {
        "path": "transcription.segments",
        "query": {
          "bool": {
            "must": [
              {"match": {"transcription.segments.text": "sample"}},
              {"range": {"transcription.segments.confidence": {"gte": 0.8}}}
            ]
          }
        }
      }
    }
  }'
```

### Geo Queries
```bash
# Search by location (if geo data available)
curl -X GET "localhost:9200/mams-audit-logs/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "geo_distance": {
        "distance": "100km",
        "location.coordinates": {
          "lat": 40.7128,
          "lon": -74.0060
        }
      }
    }
  }'
```

## Performance Optimization

### Index Settings
```bash
# Update refresh interval
curl -X PUT "localhost:9200/mams-assets/_settings" \
  -H 'Content-Type: application/json' \
  -d '{"index": {"refresh_interval": "30s"}}'

# Update number of replicas
curl -X PUT "localhost:9200/mams-assets/_settings" \
  -H 'Content-Type: application/json' \
  -d '{"index": {"number_of_replicas": 1}}'
```

### Query Optimization
```bash
# Use source filtering
curl -X GET "localhost:9200/mams-assets/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "_source": ["asset_id", "title", "content_type"],
    "query": {"match_all": {}}
  }'

# Use scroll for large result sets
curl -X GET "localhost:9200/mams-assets/_search?scroll=1m" \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 100,
    "query": {"match_all": {}}
  }'
```

## Monitoring and Maintenance

### Cluster Health
```bash
# Check cluster health
curl -X GET "localhost:9200/_cluster/health"

# Check node information
curl -X GET "localhost:9200/_cat/nodes?v"

# Check index information
curl -X GET "localhost:9200/_cat/indices?v"
```

### Index Management
```bash
# Create index alias
curl -X POST "localhost:9200/_aliases" \
  -H 'Content-Type: application/json' \
  -d '{
    "actions": [
      {"add": {"index": "mams-assets", "alias": "assets-current"}}
    ]
  }'

# Reindex data
curl -X POST "localhost:9200/_reindex" \
  -H 'Content-Type: application/json' \
  -d '{
    "source": {"index": "mams-assets-old"},
    "dest": {"index": "mams-assets-new"}
  }'
```

### Performance Monitoring
```bash
# Check slow queries
curl -X GET "localhost:9200/_cat/nodes?v&h=name,search.query_time_in_millis,search.query_current"

# Check index statistics
curl -X GET "localhost:9200/mams-assets/_stats"

# Monitor search performance
curl -X GET "localhost:9200/_nodes/stats/indices/search"
```

## Development Tips

### Testing Search Queries
```python
import requests
import json

# Test search function
def test_search(query, index='mams-assets'):
    url = f'http://localhost:9200/{index}/_search'
    response = requests.get(url, json=query)
    return response.json()

# Example usage
query = {
    "query": {
        "multi_match": {
            "query": "sample video",
            "fields": ["title^2", "description", "keywords"]
        }
    },
    "highlight": {
        "fields": {
            "title": {},
            "description": {}
        }
    }
}

result = test_search(query)
print(json.dumps(result, indent=2))
```

### Bulk Operations
```python
import requests
import json

def bulk_index(index, documents):
    """Bulk index documents"""
    bulk_data = []
    for doc_id, doc in documents.items():
        bulk_data.append(json.dumps({"index": {"_index": index, "_id": doc_id}}))
        bulk_data.append(json.dumps(doc))
    
    bulk_body = '\n'.join(bulk_data) + '\n'
    
    response = requests.post(
        'http://localhost:9200/_bulk',
        headers={'Content-Type': 'application/x-ndjson'},
        data=bulk_body
    )
    
    return response.json()
```

## Production Considerations

### Security
- Enable authentication and authorization
- Use HTTPS for all communications
- Implement field-level security
- Regular security updates

### Scaling
- Multi-node cluster setup
- Index sharding strategy
- Replica configuration
- Load balancing

### Backup and Recovery
```bash
# Create snapshot repository
curl -X PUT "localhost:9200/_snapshot/backup_repo" \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "fs",
    "settings": {
      "location": "/backup/opensearch"
    }
  }'

# Create snapshot
curl -X PUT "localhost:9200/_snapshot/backup_repo/snapshot_1" \
  -H 'Content-Type: application/json' \
  -d '{
    "indices": "mams-*",
    "include_global_state": false
  }'
```

### Monitoring
- Set up index lifecycle management
- Monitor query performance
- Track storage usage
- Set up alerting for cluster health

## Troubleshooting

### Common Issues

1. **Index Not Found**: Check if index exists and is properly created
2. **Search Too Slow**: Optimize queries, add more shards, or improve hardware
3. **Out of Memory**: Increase heap size or optimize mappings
4. **Mapping Conflicts**: Review field mappings and data types

### Debug Commands
```bash
# Explain query performance
curl -X GET "localhost:9200/mams-assets/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "explain": true,
    "query": {"match": {"title": "video"}}
  }'

# Analyze text
curl -X GET "localhost:9200/mams-assets/_analyze" \
  -H 'Content-Type: application/json' \
  -d '{
    "analyzer": "asset_analyzer",
    "text": "Sample Video Production"
  }'

# Profile search
curl -X GET "localhost:9200/mams-assets/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "profile": true,
    "query": {"match": {"title": "video"}}
  }'
```

This setup provides a comprehensive search solution for MAMS with advanced features, performance optimization, and production-ready capabilities.