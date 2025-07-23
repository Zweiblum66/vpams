// Cache Service Collections Schema
use('mams_cache');

// General purpose cache
db.createCollection('general_cache', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['key', 'value', 'created_at'],
      properties: {
        key: {
          bsonType: 'string',
          description: 'Cache key'
        },
        value: {
          description: 'Cached value (any type)'
        },
        namespace: {
          bsonType: 'string',
          description: 'Cache namespace'
        },
        tags: {
          bsonType: 'array',
          items: { bsonType: 'string' },
          description: 'Cache tags for bulk operations'
        },
        ttl_seconds: {
          bsonType: 'number',
          description: 'Time to live in seconds'
        },
        created_at: {
          bsonType: 'date',
          description: 'Cache creation timestamp'
        },
        expires_at: {
          bsonType: 'date',
          description: 'Cache expiration timestamp'
        },
        last_accessed: {
          bsonType: 'date',
          description: 'Last access timestamp'
        },
        access_count: {
          bsonType: 'number',
          description: 'Number of times accessed'
        }
      }
    }
  }
});

// API response cache
db.createCollection('api_cache', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['cache_key', 'endpoint', 'response_data', 'created_at'],
      properties: {
        cache_key: {
          bsonType: 'string',
          description: 'Unique cache key'
        },
        endpoint: {
          bsonType: 'string',
          description: 'API endpoint'
        },
        method: {
          bsonType: 'string',
          enum: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
          description: 'HTTP method'
        },
        query_params: {
          bsonType: 'object',
          description: 'Query parameters'
        },
        response_data: {
          bsonType: 'object',
          description: 'Cached response data'
        },
        status_code: {
          bsonType: 'number',
          description: 'HTTP status code'
        },
        headers: {
          bsonType: 'object',
          description: 'Response headers'
        },
        user_id: {
          bsonType: 'string',
          description: 'User ID for user-specific caching'
        },
        organization_id: {
          bsonType: 'string',
          description: 'Organization ID for tenant-specific caching'
        },
        hit_count: {
          bsonType: 'number',
          description: 'Number of cache hits'
        },
        last_hit: {
          bsonType: 'date',
          description: 'Last cache hit timestamp'
        },
        created_at: {
          bsonType: 'date',
          description: 'Cache creation timestamp'
        },
        expires_at: {
          bsonType: 'date',
          description: 'Cache expiration timestamp'
        }
      }
    }
  }
});

// Search results cache
db.createCollection('search_cache', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['search_key', 'query', 'results', 'created_at'],
      properties: {
        search_key: {
          bsonType: 'string',
          description: 'Search query hash'
        },
        query: {
          bsonType: 'object',
          description: 'Search query parameters'
        },
        results: {
          bsonType: 'array',
          items: { bsonType: 'object' },
          description: 'Search results'
        },
        total_count: {
          bsonType: 'number',
          description: 'Total number of results'
        },
        facets: {
          bsonType: 'object',
          description: 'Search facets'
        },
        search_time_ms: {
          bsonType: 'number',
          description: 'Search execution time'
        },
        user_id: {
          bsonType: 'string',
          description: 'User ID for personalized results'
        },
        hit_count: {
          bsonType: 'number',
          description: 'Number of times results were served'
        },
        created_at: {
          bsonType: 'date',
          description: 'Cache creation timestamp'
        },
        expires_at: {
          bsonType: 'date',
          description: 'Cache expiration timestamp'
        }
      }
    }
  }
});

// Thumbnail cache
db.createCollection('thumbnail_cache', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['asset_id', 'thumbnail_type', 'storage_path', 'created_at'],
      properties: {
        asset_id: {
          bsonType: 'string',
          description: 'Asset UUID'
        },
        thumbnail_type: {
          bsonType: 'string',
          enum: ['small', 'medium', 'large', 'timeline'],
          description: 'Thumbnail size/type'
        },
        storage_path: {
          bsonType: 'string',
          description: 'Storage path for thumbnail'
        },
        width: {
          bsonType: 'number',
          description: 'Thumbnail width'
        },
        height: {
          bsonType: 'number',
          description: 'Thumbnail height'
        },
        file_size: {
          bsonType: 'number',
          description: 'File size in bytes'
        },
        mime_type: {
          bsonType: 'string',
          description: 'MIME type'
        },
        timecode: {
          bsonType: 'number',
          description: 'Timecode for video thumbnails'
        },
        access_count: {
          bsonType: 'number',
          description: 'Number of times accessed'
        },
        last_accessed: {
          bsonType: 'date',
          description: 'Last access timestamp'
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation timestamp'
        },
        expires_at: {
          bsonType: 'date',
          description: 'Expiration timestamp'
        }
      }
    }
  }
});

// Session cache
db.createCollection('session_cache', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['session_id', 'user_id', 'data', 'created_at'],
      properties: {
        session_id: {
          bsonType: 'string',
          description: 'Session identifier'
        },
        user_id: {
          bsonType: 'string',
          description: 'User UUID'
        },
        data: {
          bsonType: 'object',
          description: 'Session data'
        },
        ip_address: {
          bsonType: 'string',
          description: 'User IP address'
        },
        user_agent: {
          bsonType: 'string',
          description: 'User agent string'
        },
        last_activity: {
          bsonType: 'date',
          description: 'Last activity timestamp'
        },
        created_at: {
          bsonType: 'date',
          description: 'Session creation timestamp'
        },
        expires_at: {
          bsonType: 'date',
          description: 'Session expiration timestamp'
        }
      }
    }
  }
});

// Create indexes for cache collections
db.general_cache.createIndex({ key: 1 }, { unique: true });
db.general_cache.createIndex({ namespace: 1 });
db.general_cache.createIndex({ tags: 1 });
db.general_cache.createIndex({ expires_at: 1 });

db.api_cache.createIndex({ cache_key: 1 }, { unique: true });
db.api_cache.createIndex({ endpoint: 1 });
db.api_cache.createIndex({ user_id: 1 });
db.api_cache.createIndex({ organization_id: 1 });
db.api_cache.createIndex({ expires_at: 1 });

db.search_cache.createIndex({ search_key: 1 }, { unique: true });
db.search_cache.createIndex({ user_id: 1 });
db.search_cache.createIndex({ expires_at: 1 });

db.thumbnail_cache.createIndex({ asset_id: 1, thumbnail_type: 1 }, { unique: true });
db.thumbnail_cache.createIndex({ expires_at: 1 });
db.thumbnail_cache.createIndex({ last_accessed: 1 });

db.session_cache.createIndex({ session_id: 1 }, { unique: true });
db.session_cache.createIndex({ user_id: 1 });
db.session_cache.createIndex({ expires_at: 1 });
db.session_cache.createIndex({ last_activity: 1 });

// Create TTL indexes for automatic cleanup
db.general_cache.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });
db.api_cache.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });
db.search_cache.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });
db.thumbnail_cache.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });
db.session_cache.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });

print('Cache collections and indexes created successfully!');