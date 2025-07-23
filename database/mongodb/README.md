# MAMS MongoDB Setup

This directory contains the MongoDB schema and initialization scripts for the MAMS (Media Asset Management System) MongoDB databases.

## Database Structure

MAMS uses MongoDB for flexible, document-based storage for the following services:

- **mams_search**: Search indices, queries, and saved searches
- **mams_metadata**: Flexible metadata storage and extraction history
- **mams_assets**: Asset processing jobs, derivatives, and analytics
- **mams_ai**: AI/ML models, jobs, and inference cache
- **mams_cache**: General caching, API responses, and session data

## Quick Start

1. **Start MongoDB**:
   ```bash
   cd database/mongodb
   docker-compose up -d
   ```

2. **Verify Database Creation**:
   ```bash
   docker exec -it mams_mongodb mongosh --eval "show dbs"
   ```

3. **Access Mongo Express**:
   - URL: http://localhost:8081
   - Username: admin
   - Password: express_password

## Database Users

- **admin**: Root user (password: admin_password)
- **mams_app**: Application user (password: mams_dev_password)
- **mams_readonly**: Read-only user (password: mams_readonly_password)
- **mams_backup**: Backup user (password: mams_backup_password)

## Collections Overview

### Search Database (mams_search)
- **search_indices**: Search index configurations
- **search_documents**: Denormalized search documents
- **search_queries**: Search query logs
- **saved_searches**: User-saved search configurations

### Metadata Database (mams_metadata)
- **asset_metadata**: Flexible metadata storage
- **extraction_history**: Metadata extraction job history
- **validation_rules**: Metadata validation and enrichment rules
- **metadata_templates**: Reusable metadata templates

### Assets Database (mams_assets)
- **processing_jobs**: Asset processing job queue
- **asset_derivatives**: Proxies, thumbnails, and derivatives
- **asset_timelines**: Timeline data for video/audio assets
- **asset_analytics**: Usage analytics and events
- **asset_collaboration**: Comments, annotations, and collaboration

### AI Database (mams_ai)
- **ai_models**: AI model registry and configurations
- **ai_jobs**: AI processing job queue
- **training_datasets**: Training data and datasets
- **inference_cache**: AI inference result cache
- **model_analytics**: Model performance metrics

### Cache Database (mams_cache)
- **general_cache**: General purpose caching
- **api_cache**: API response caching
- **search_cache**: Search result caching
- **thumbnail_cache**: Thumbnail caching
- **session_cache**: User session data

## Schema Validation

All collections use JSON Schema validation to ensure data integrity:

```javascript
// Example validation schema
{
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['asset_id', 'metadata_type', 'data'],
      properties: {
        asset_id: {
          bsonType: 'string',
          description: 'Asset UUID'
        },
        metadata_type: {
          bsonType: 'string',
          enum: ['technical', 'descriptive', 'administrative'],
          description: 'Type of metadata'
        }
      }
    }
  }
}
```

## Indexes

Comprehensive indexing strategy for optimal performance:

- **Primary indexes**: Unique identifiers and foreign keys
- **Compound indexes**: Multi-field queries
- **Text indexes**: Full-text search capabilities
- **TTL indexes**: Automatic document expiration
- **Geospatial indexes**: Location-based queries (where applicable)

## Management Scripts

### Connect to MongoDB
```bash
# Connect to MongoDB shell
docker exec -it mams_mongodb mongosh

# Connect to specific database
docker exec -it mams_mongodb mongosh mams_search
```

### Database Operations
```javascript
// Switch to database
use('mams_search');

// List collections
show collections;

// Check collection stats
db.search_documents.stats();

// Query documents
db.search_documents.find({content_type: 'video'}).limit(10);

// Create index
db.search_documents.createIndex({title: 'text'});

// Drop collection
db.search_documents.drop();
```

### Backup and Restore
```bash
# Backup all databases
docker exec mams_mongodb mongodump --out /tmp/backup

# Backup specific database
docker exec mams_mongodb mongodump --db mams_search --out /tmp/backup

# Restore database
docker exec mams_mongodb mongorestore /tmp/backup
```

## Performance Optimization

### Indexing Best Practices
1. **Compound indexes**: Order fields by selectivity
2. **Text indexes**: Use for full-text search
3. **TTL indexes**: Automatic cleanup of expired documents
4. **Partial indexes**: Index only matching documents

### Query Optimization
```javascript
// Use explain() to analyze query performance
db.search_documents.find({content_type: 'video'}).explain('executionStats');

// Use hint() to force index usage
db.search_documents.find({title: 'demo'}).hint({title: 'text'});

// Use aggregation pipeline for complex queries
db.search_documents.aggregate([
  {$match: {content_type: 'video'}},
  {$group: {_id: '$keywords', count: {$sum: 1}}},
  {$sort: {count: -1}}
]);
```

### Monitoring
```javascript
// Check current operations
db.currentOp();

// Database statistics
db.stats();

// Collection statistics
db.search_documents.stats();

// Index usage statistics
db.search_documents.aggregate([{$indexStats: {}}]);
```

## Development Tips

1. **Schema Evolution**: Use `$jsonSchema` for validation while allowing flexibility
2. **Embedding vs. Referencing**: Embed for 1:1 relationships, reference for 1:many
3. **Denormalization**: Store frequently accessed data together
4. **Aggregation Pipelines**: Use for complex data transformations

## Production Considerations

### Security
- Enable authentication and authorization
- Use TLS/SSL for connections
- Implement field-level encryption for sensitive data
- Regular security audits

### Scaling
- Implement sharding for horizontal scaling
- Use read replicas for read-heavy workloads
- Monitor and optimize slow queries
- Implement connection pooling

### Monitoring
- Set up MongoDB monitoring tools
- Track key metrics: operations/second, memory usage, disk I/O
- Monitor replication lag
- Set up alerting for critical events

## Troubleshooting

### Common Issues
1. **High memory usage**: Check for missing indexes
2. **Slow queries**: Use explain() and create appropriate indexes
3. **Connection issues**: Verify network connectivity and authentication
4. **Disk space**: Monitor storage usage and implement cleanup policies

### Debugging Queries
```javascript
// Enable profiling
db.setProfilingLevel(2);

// View slow queries
db.system.profile.find().sort({ts: -1}).limit(10);

// Check index usage
db.search_documents.find({title: 'demo'}).explain('executionStats');
```

### Performance Monitoring
```javascript
// Server status
db.serverStatus();

// Database statistics
db.stats();

// Current operations
db.currentOp();

// Kill long-running operation
db.killOp(operationId);
```

## Sample Queries

### Search Operations
```javascript
// Text search
db.search_documents.find({$text: {$search: 'video production'}});

// Metadata search
db.asset_metadata.find({'data.title': /demo/i});

// Aggregation pipeline
db.asset_analytics.aggregate([
  {$match: {event_type: 'view'}},
  {$group: {_id: '$asset_id', views: {$sum: 1}}},
  {$sort: {views: -1}},
  {$limit: 10}
]);
```

### AI Operations
```javascript
// Find available AI models
db.ai_models.find({status: 'available'});

// Get processing job status
db.ai_jobs.find({status: 'processing'});

// Cache lookup
db.inference_cache.findOne({cache_key: 'object_detection_hash123'});
```

### Analytics Queries
```javascript
// Asset usage over time
db.asset_analytics.aggregate([
  {$match: {
    timestamp: {
      $gte: ISODate('2024-01-01'),
      $lt: ISODate('2024-02-01')
    }
  }},
  {$group: {
    _id: {$dateToString: {format: '%Y-%m-%d', date: '$timestamp'}},
    count: {$sum: 1}
  }},
  {$sort: {_id: 1}}
]);
```