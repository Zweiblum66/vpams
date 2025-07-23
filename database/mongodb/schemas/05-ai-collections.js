// AI/ML Service Collections Schema
use('mams_ai');

// AI models registry
db.createCollection('ai_models', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'model_type', 'version', 'status'],
      properties: {
        name: {
          bsonType: 'string',
          description: 'Model name'
        },
        model_type: {
          bsonType: 'string',
          enum: ['object_detection', 'image_classification', 'speech_recognition', 'transcription', 'translation', 'content_moderation', 'face_recognition', 'scene_detection', 'sentiment_analysis', 'auto_tagging'],
          description: 'Type of AI model'
        },
        version: {
          bsonType: 'string',
          description: 'Model version'
        },
        description: {
          bsonType: 'string',
          description: 'Model description'
        },
        provider: {
          bsonType: 'string',
          enum: ['openai', 'azure', 'aws', 'google', 'huggingface', 'custom'],
          description: 'Model provider'
        },
        status: {
          bsonType: 'string',
          enum: ['available', 'loading', 'error', 'deprecated'],
          description: 'Model status'
        },
        capabilities: {
          bsonType: 'array',
          items: { bsonType: 'string' },
          description: 'Model capabilities'
        },
        supported_formats: {
          bsonType: 'array',
          items: { bsonType: 'string' },
          description: 'Supported input formats'
        },
        configuration: {
          bsonType: 'object',
          description: 'Model configuration parameters'
        },
        performance_metrics: {
          bsonType: 'object',
          properties: {
            accuracy: { bsonType: 'number' },
            precision: { bsonType: 'number' },
            recall: { bsonType: 'number' },
            f1_score: { bsonType: 'number' },
            latency_ms: { bsonType: 'number' }
          }
        },
        usage_stats: {
          bsonType: 'object',
          properties: {
            total_requests: { bsonType: 'number' },
            successful_requests: { bsonType: 'number' },
            failed_requests: { bsonType: 'number' },
            average_processing_time: { bsonType: 'number' }
          }
        },
        created_at: {
          bsonType: 'date',
          description: 'Model registration timestamp'
        },
        updated_at: {
          bsonType: 'date',
          description: 'Last update timestamp'
        }
      }
    }
  }
});

// AI processing jobs
db.createCollection('ai_jobs', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['asset_id', 'model_name', 'job_type', 'status', 'created_at'],
      properties: {
        asset_id: {
          bsonType: 'string',
          description: 'Asset UUID'
        },
        model_name: {
          bsonType: 'string',
          description: 'AI model used'
        },
        model_version: {
          bsonType: 'string',
          description: 'Model version used'
        },
        job_type: {
          bsonType: 'string',
          enum: ['transcription', 'translation', 'object_detection', 'face_recognition', 'scene_analysis', 'content_moderation', 'auto_tagging', 'sentiment_analysis'],
          description: 'Type of AI job'
        },
        status: {
          bsonType: 'string',
          enum: ['queued', 'processing', 'completed', 'failed', 'cancelled'],
          description: 'Job status'
        },
        priority: {
          bsonType: 'number',
          minimum: 1,
          maximum: 10,
          description: 'Job priority'
        },
        input_params: {
          bsonType: 'object',
          description: 'Job input parameters'
        },
        results: {
          bsonType: 'object',
          description: 'AI processing results'
        },
        confidence_score: {
          bsonType: 'number',
          minimum: 0,
          maximum: 1,
          description: 'Overall confidence score'
        },
        processing_time_ms: {
          bsonType: 'number',
          description: 'Processing time in milliseconds'
        },
        cost_cents: {
          bsonType: 'number',
          description: 'Processing cost in cents'
        },
        error_details: {
          bsonType: 'object',
          properties: {
            error_code: { bsonType: 'string' },
            error_message: { bsonType: 'string' },
            retry_count: { bsonType: 'number' }
          }
        },
        created_at: {
          bsonType: 'date',
          description: 'Job creation timestamp'
        },
        started_at: {
          bsonType: 'date',
          description: 'Job start timestamp'
        },
        completed_at: {
          bsonType: 'date',
          description: 'Job completion timestamp'
        }
      }
    }
  }
});

// Training data and datasets
db.createCollection('training_datasets', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'dataset_type', 'status', 'created_at'],
      properties: {
        name: {
          bsonType: 'string',
          description: 'Dataset name'
        },
        description: {
          bsonType: 'string',
          description: 'Dataset description'
        },
        dataset_type: {
          bsonType: 'string',
          enum: ['classification', 'detection', 'segmentation', 'transcription', 'translation'],
          description: 'Type of training dataset'
        },
        status: {
          bsonType: 'string',
          enum: ['building', 'ready', 'training', 'completed', 'error'],
          description: 'Dataset status'
        },
        samples: {
          bsonType: 'array',
          items: {
            bsonType: 'object',
            properties: {
              asset_id: { bsonType: 'string' },
              label: { bsonType: 'string' },
              annotations: { bsonType: 'object' },
              verified: { bsonType: 'bool' }
            }
          },
          description: 'Training samples'
        },
        statistics: {
          bsonType: 'object',
          properties: {
            total_samples: { bsonType: 'number' },
            verified_samples: { bsonType: 'number' },
            label_distribution: { bsonType: 'object' }
          }
        },
        created_by: {
          bsonType: 'string',
          description: 'User who created the dataset'
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

// Model inference cache
db.createCollection('inference_cache', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['cache_key', 'model_name', 'results', 'created_at'],
      properties: {
        cache_key: {
          bsonType: 'string',
          description: 'Unique cache key based on input'
        },
        asset_id: {
          bsonType: 'string',
          description: 'Asset UUID'
        },
        model_name: {
          bsonType: 'string',
          description: 'AI model used'
        },
        model_version: {
          bsonType: 'string',
          description: 'Model version'
        },
        input_hash: {
          bsonType: 'string',
          description: 'Hash of input data'
        },
        results: {
          bsonType: 'object',
          description: 'Cached inference results'
        },
        confidence_score: {
          bsonType: 'number',
          minimum: 0,
          maximum: 1,
          description: 'Result confidence score'
        },
        hit_count: {
          bsonType: 'number',
          description: 'Number of times cache was hit'
        },
        last_accessed: {
          bsonType: 'date',
          description: 'Last access timestamp'
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

// Model performance analytics
db.createCollection('model_analytics', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['model_name', 'metric_type', 'value', 'timestamp'],
      properties: {
        model_name: {
          bsonType: 'string',
          description: 'AI model name'
        },
        model_version: {
          bsonType: 'string',
          description: 'Model version'
        },
        metric_type: {
          bsonType: 'string',
          enum: ['accuracy', 'precision', 'recall', 'f1_score', 'latency', 'throughput', 'error_rate', 'confidence_distribution'],
          description: 'Type of performance metric'
        },
        value: {
          bsonType: 'number',
          description: 'Metric value'
        },
        context: {
          bsonType: 'object',
          description: 'Additional context for the metric'
        },
        timestamp: {
          bsonType: 'date',
          description: 'Metric timestamp'
        }
      }
    }
  }
});

// Create indexes for AI collections
db.ai_models.createIndex({ name: 1, version: 1 }, { unique: true });
db.ai_models.createIndex({ model_type: 1 });
db.ai_models.createIndex({ provider: 1 });
db.ai_models.createIndex({ status: 1 });

db.ai_jobs.createIndex({ asset_id: 1 });
db.ai_jobs.createIndex({ model_name: 1 });
db.ai_jobs.createIndex({ job_type: 1 });
db.ai_jobs.createIndex({ status: 1 });
db.ai_jobs.createIndex({ priority: 1 });
db.ai_jobs.createIndex({ created_at: -1 });

db.training_datasets.createIndex({ name: 1 }, { unique: true });
db.training_datasets.createIndex({ dataset_type: 1 });
db.training_datasets.createIndex({ status: 1 });
db.training_datasets.createIndex({ created_by: 1 });

db.inference_cache.createIndex({ cache_key: 1 }, { unique: true });
db.inference_cache.createIndex({ asset_id: 1 });
db.inference_cache.createIndex({ model_name: 1 });
db.inference_cache.createIndex({ expires_at: 1 });
db.inference_cache.createIndex({ last_accessed: 1 });

db.model_analytics.createIndex({ model_name: 1, timestamp: -1 });
db.model_analytics.createIndex({ metric_type: 1 });
db.model_analytics.createIndex({ timestamp: -1 });

print('AI collections and indexes created successfully!');