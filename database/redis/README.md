# MAMS Redis Setup

This directory contains the Redis configuration and initialization scripts for the MAMS (Media Asset Management System) Redis cache.

## Overview

Redis is used in MAMS for:

- **Session Management**: User sessions and authentication tokens
- **Caching**: API responses, search results, and frequently accessed data
- **Queue Management**: Job queues for background processing
- **Real-time Data**: Live analytics and notifications
- **Rate Limiting**: API rate limiting and throttling
- **Pub/Sub**: Real-time event notifications

## Quick Start

1. **Start Redis**:
   ```bash
   cd database/redis
   docker-compose up -d
   ```

2. **Initialize with Sample Data**:
   ```bash
   # Install dependencies
   pip install redis

   # Run initialization script
   python data/init-redis.py
   ```

3. **Access Redis Commander**:
   - URL: http://localhost:8082
   - Username: admin
   - Password: redis_admin

## Configuration

### Redis Settings (`config/redis.conf`)

Key configuration settings for MAMS:

- **Memory**: 256MB max with LRU eviction
- **Persistence**: RDB snapshots + AOF logging
- **Networking**: Accessible on all interfaces
- **Databases**: 16 logical databases
- **Logging**: Notice level logging

### Database Layout

MAMS uses different Redis databases for different purposes:

- **Database 0**: Sessions and user data
- **Database 1**: API response cache
- **Database 2**: Search result cache
- **Database 3**: Asset metadata cache
- **Database 4**: Job queues
- **Database 5**: Real-time analytics
- **Database 6**: Feature flags and configuration
- **Database 7**: Rate limiting counters
- **Database 8**: Pub/sub channels
- **Database 9**: Temporary data

## Key Patterns

### Session Management
```
session:{session_id} -> JSON session data
user:preferences:{user_id} -> JSON user preferences
```

### Caching
```
cache:api:{endpoint}:{params_hash} -> JSON response
cache:search:{query_hash} -> JSON search results
cache:asset:{asset_id} -> JSON asset data
```

### Queues
```
queue:processing -> List of processing jobs
queue:workflow -> List of workflow tasks
queue:notifications -> List of notifications
```

### Rate Limiting
```
rate_limit:user:{user_id}:{endpoint} -> Counter with TTL
rate_limit:ip:{ip_address}:{endpoint} -> Counter with TTL
```

### Analytics
```
analytics:realtime -> JSON current metrics
ranking:popular_assets -> Sorted set of asset IDs by views
ranking:user_activity -> Sorted set of user IDs by activity
```

### Feature Flags
```
feature:flag:{feature_name} -> Boolean string
config:system -> JSON system configuration
```

## Data Structures

### Strings
- Session data (JSON)
- Cache entries (JSON)
- Feature flags (boolean)
- Configuration (JSON)

### Lists
- Job queues (FIFO)
- Recent activity logs
- Notification queues

### Sets
- User permissions
- Asset tags
- Active sessions

### Sorted Sets
- Popular assets (by view count)
- User activity scores
- Recent searches (by timestamp)

### Hashes
- Asset metadata
- User statistics
- System metrics

## Management Commands

### Connect to Redis
```bash
# Connect to Redis CLI
docker exec -it mams_redis redis-cli

# Connect to specific database
docker exec -it mams_redis redis-cli -n 1
```

### Common Operations
```bash
# List all keys
KEYS *

# Get key info
TYPE key_name
TTL key_name

# Memory usage
MEMORY USAGE key_name

# Database info
INFO keyspace
DBSIZE

# Clear database
FLUSHDB

# Clear all databases
FLUSHALL
```

### Queue Operations
```bash
# Add to queue
LPUSH queue:processing '{"job_id": "123", "type": "transcode"}'

# Get from queue
RPOP queue:processing

# Queue length
LLEN queue:processing

# View queue contents
LRANGE queue:processing 0 -1
```

### Cache Operations
```bash
# Set with expiration
SETEX cache:api:assets:list 300 '{"data": [], "total": 0}'

# Get cached value
GET cache:api:assets:list

# Check expiration
TTL cache:api:assets:list

# Delete cache
DEL cache:api:assets:list
```

## Monitoring

### Performance Metrics
```bash
# Server info
INFO server
INFO memory
INFO stats

# Slow queries
SLOWLOG GET 10

# Client connections
CLIENT LIST

# Monitor commands
MONITOR
```

### Memory Analysis
```bash
# Memory usage by key
MEMORY USAGE key_name

# Memory statistics
INFO memory

# Sample keys by memory usage
MEMORY DOCTOR
```

## Development Tips

### Testing Cache Performance
```python
import redis
import time

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Test set/get performance
start = time.time()
for i in range(1000):
    r.set(f"test:{i}", f"value_{i}")
print(f"Set 1000 keys: {time.time() - start:.2f}s")

start = time.time()
for i in range(1000):
    r.get(f"test:{i}")
print(f"Get 1000 keys: {time.time() - start:.2f}s")
```

### Pub/Sub Example
```python
import redis

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Publisher
r.publish('events:assets', '{"type": "upload", "asset_id": "123"}')

# Subscriber
pubsub = r.pubsub()
pubsub.subscribe('events:assets')
for message in pubsub.listen():
    if message['type'] == 'message':
        print(f"Received: {message['data']}")
```

### Rate Limiting Example
```python
import redis
import time

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

def rate_limit(user_id, endpoint, limit=100, window=60):
    """Rate limit implementation"""
    key = f"rate_limit:user:{user_id}:{endpoint}"
    
    # Get current count
    current = r.get(key)
    if current is None:
        # First request in window
        r.setex(key, window, 1)
        return True
    
    if int(current) >= limit:
        return False
    
    # Increment counter
    r.incr(key)
    return True

# Usage
if rate_limit('user123', 'search'):
    print("Request allowed")
else:
    print("Rate limit exceeded")
```

## Production Considerations

### Security
- Enable authentication (`requirepass`)
- Disable dangerous commands (`rename-command`)
- Use SSL/TLS for connections
- Implement proper access controls

### Performance
- Monitor memory usage and eviction
- Use pipelining for bulk operations
- Implement connection pooling
- Consider Redis Cluster for scaling

### Backup and Recovery
```bash
# Manual backup
docker exec mams_redis redis-cli BGSAVE

# Automatic backup via cron
0 2 * * * docker exec mams_redis redis-cli BGSAVE

# Restore from backup
docker cp backup.rdb mams_redis:/data/dump.rdb
docker restart mams_redis
```

### Monitoring and Alerting
- Set up Redis monitoring (Redis Insight, Prometheus)
- Alert on high memory usage
- Monitor slow queries
- Track connection counts

## Troubleshooting

### Common Issues

1. **Out of Memory**
   - Check `maxmemory` setting
   - Verify eviction policy
   - Identify large keys

2. **High Latency**
   - Check for slow queries (`SLOWLOG`)
   - Monitor network latency
   - Verify client connection pooling

3. **Connection Issues**
   - Check network connectivity
   - Verify Redis is running
   - Check client connection limits

### Debug Commands
```bash
# Check Redis status
docker exec mams_redis redis-cli ping

# View configuration
docker exec mams_redis redis-cli CONFIG GET '*'

# Monitor live commands
docker exec mams_redis redis-cli MONITOR

# Check memory usage
docker exec mams_redis redis-cli INFO memory
```

## Sample Data

The initialization script creates sample data for development:

- **Sessions**: Admin user session
- **Cache**: API responses and search results
- **Queues**: Processing and workflow jobs
- **Analytics**: Real-time metrics
- **Config**: Feature flags and system settings

This data helps with development and testing without requiring a full system setup.