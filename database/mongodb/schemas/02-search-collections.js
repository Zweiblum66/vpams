// Search Engine Collections Schema
use('mams_search');

// Search index configuration
db.createCollection('search_indices', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'type', 'status', 'created_at'],
      properties: {
        name: {
          bsonType: 'string',
          description: 'Index name must be a string'
        },
        type: {
          bsonType: 'string',
          enum: ['text', 'metadata', 'visual', 'audio', 'combined'],
          description: 'Index type must be one of the specified values'
        },
        status: {
          bsonType: 'string',
          enum: ['building', 'ready', 'error', 'rebuilding'],
          description: 'Index status'
        },
        settings: {
          bsonType: 'object',
          description: 'Index configuration settings'
        },
        statistics: {
          bsonType: 'object',
          properties: {
            document_count: { bsonType: 'number' },
            index_size_bytes: { bsonType: 'number' },
            last_updated: { bsonType: 'date' }
          }
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation timestamp'
        },
        updated_at: {
          bsonType: 'date',
          description: 'Last update timestamp'
        }
      }
    }
  }
});

// Search documents (denormalized for performance)
db.createCollection('search_documents', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['asset_id', 'title', 'content_type', 'indexed_at'],
      properties: {
        asset_id: {
          bsonType: 'string',
          description: 'Asset UUID'
        },
        title: {
          bsonType: 'string',
          description: 'Asset title'
        },
        description: {
          bsonType: 'string',
          description: 'Asset description'
        },
        content_type: {
          bsonType: 'string',
          enum: ['video', 'audio', 'image', 'document', 'other'],
          description: 'Asset content type'
        },
        keywords: {
          bsonType: 'array',
          items: { bsonType: 'string' },
          description: 'Asset keywords/tags'
        },
        metadata: {
          bsonType: 'object',
          description: 'Searchable metadata fields'
        },
        transcription: {
          bsonType: 'object',
          properties: {
            text: { bsonType: 'string' },
            segments: {
              bsonType: 'array',
              items: {
                bsonType: 'object',
                properties: {
                  start: { bsonType: 'number' },
                  end: { bsonType: 'number' },
                  text: { bsonType: 'string' },
                  confidence: { bsonType: 'number' }
                }
              }
            },
            language: { bsonType: 'string' }
          }
        },
        visual_features: {
          bsonType: 'object',
          properties: {
            colors: { bsonType: 'array' },
            objects: { bsonType: 'array' },
            faces: { bsonType: 'array' },
            text_detected: { bsonType: 'array' },
            scene_description: { bsonType: 'string' }
          }
        },
        audio_features: {
          bsonType: 'object',
          properties: {
            tempo: { bsonType: 'number' },
            key: { bsonType: 'string' },
            energy: { bsonType: 'number' },
            mood: { bsonType: 'string' },
            genre: { bsonType: 'string' }
          }
        },
        indexed_at: {
          bsonType: 'date',
          description: 'When document was indexed'
        },
        index_version: {
          bsonType: 'number',
          description: 'Index version for updates'
        }
      }
    }
  }
});

// Search queries log
db.createCollection('search_queries', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['query_text', 'user_id', 'timestamp'],
      properties: {
        query_text: {
          bsonType: 'string',
          description: 'Search query text'
        },
        user_id: {
          bsonType: 'string',
          description: 'User who performed the search'
        },
        filters: {
          bsonType: 'object',
          description: 'Applied filters'
        },
        results_count: {
          bsonType: 'number',
          description: 'Number of results returned'
        },
        response_time_ms: {
          bsonType: 'number',
          description: 'Query response time in milliseconds'
        },
        clicked_results: {
          bsonType: 'array',
          items: { bsonType: 'string' },
          description: 'Asset IDs that were clicked'
        },
        session_id: {
          bsonType: 'string',
          description: 'Search session ID'
        },
        timestamp: {
          bsonType: 'date',
          description: 'Query timestamp'
        }
      }
    }
  }
});

// Saved searches
db.createCollection('saved_searches', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'query', 'user_id', 'created_at'],
      properties: {
        name: {
          bsonType: 'string',
          description: 'Search name'
        },
        description: {
          bsonType: 'string',
          description: 'Search description'
        },
        query: {
          bsonType: 'object',
          description: 'Search query configuration'
        },
        user_id: {
          bsonType: 'string',
          description: 'User who created the search'
        },
        is_public: {
          bsonType: 'bool',
          description: 'Whether search is public'
        },
        alert_enabled: {
          bsonType: 'bool',
          description: 'Whether to alert on new results'
        },
        last_run: {
          bsonType: 'date',
          description: 'Last time search was executed'
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation timestamp'
        },
        updated_at: {
          bsonType: 'date',
          description: 'Last update timestamp'
        }
      }
    }
  }
});

// Create indexes for search collections
db.search_documents.createIndex({ asset_id: 1 }, { unique: true });
db.search_documents.createIndex({ content_type: 1 });
db.search_documents.createIndex({ keywords: 1 });
db.search_documents.createIndex({ indexed_at: 1 });

// Text search indexes
db.search_documents.createIndex({
  title: 'text',
  description: 'text',
  'transcription.text': 'text',
  'visual_features.scene_description': 'text'
}, {
  name: 'full_text_search',
  weights: {
    title: 10,
    description: 5,
    'transcription.text': 3,
    'visual_features.scene_description': 2
  }
});

// Query performance indexes
db.search_queries.createIndex({ user_id: 1, timestamp: -1 });
db.search_queries.createIndex({ query_text: 1 });
db.search_queries.createIndex({ timestamp: 1 });

// Saved searches indexes
db.saved_searches.createIndex({ user_id: 1, name: 1 }, { unique: true });
db.saved_searches.createIndex({ is_public: 1 });

print('Search collections and indexes created successfully!');