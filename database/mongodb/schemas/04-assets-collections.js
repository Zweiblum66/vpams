// Asset Management Collections Schema
use('mams_assets');

// Asset processing jobs
db.createCollection('processing_jobs', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['asset_id', 'job_type', 'status', 'created_at'],
      properties: {
        asset_id: {
          bsonType: 'string',
          description: 'Asset UUID'
        },
        job_type: {
          bsonType: 'string',
          enum: ['ingest', 'transcode', 'proxy', 'thumbnail', 'analysis', 'validation', 'publish'],
          description: 'Type of processing job'
        },
        status: {
          bsonType: 'string',
          enum: ['queued', 'running', 'completed', 'failed', 'cancelled', 'retrying'],
          description: 'Job status'
        },
        priority: {
          bsonType: 'number',
          minimum: 1,
          maximum: 10,
          description: 'Job priority (1 = highest, 10 = lowest)'
        },
        progress: {
          bsonType: 'number',
          minimum: 0,
          maximum: 100,
          description: 'Job progress percentage'
        },
        input_params: {
          bsonType: 'object',
          description: 'Job input parameters'
        },
        output_data: {
          bsonType: 'object',
          description: 'Job output data'
        },
        error_details: {
          bsonType: 'object',
          properties: {
            error_code: { bsonType: 'string' },
            error_message: { bsonType: 'string' },
            stack_trace: { bsonType: 'string' },
            retry_count: { bsonType: 'number' }
          }
        },
        worker_id: {
          bsonType: 'string',
          description: 'ID of worker processing the job'
        },
        estimated_duration_ms: {
          bsonType: 'number',
          description: 'Estimated processing time'
        },
        actual_duration_ms: {
          bsonType: 'number',
          description: 'Actual processing time'
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
        },
        expires_at: {
          bsonType: 'date',
          description: 'Job expiration timestamp'
        }
      }
    }
  }
});

// Asset derivatives (proxies, thumbnails, etc.)
db.createCollection('asset_derivatives', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['asset_id', 'derivative_type', 'storage_path', 'created_at'],
      properties: {
        asset_id: {
          bsonType: 'string',
          description: 'Parent asset UUID'
        },
        derivative_type: {
          bsonType: 'string',
          enum: ['proxy_low', 'proxy_medium', 'proxy_high', 'thumbnail', 'waveform', 'subtitle', 'captions'],
          description: 'Type of derivative'
        },
        format: {
          bsonType: 'string',
          description: 'File format (mp4, jpg, vtt, etc.)'
        },
        storage_path: {
          bsonType: 'string',
          description: 'Storage path for the derivative'
        },
        file_size: {
          bsonType: 'number',
          description: 'File size in bytes'
        },
        technical_specs: {
          bsonType: 'object',
          properties: {
            width: { bsonType: 'number' },
            height: { bsonType: 'number' },
            duration: { bsonType: 'number' },
            bitrate: { bsonType: 'number' },
            codec: { bsonType: 'string' },
            frame_rate: { bsonType: 'number' }
          }
        },
        generation_params: {
          bsonType: 'object',
          description: 'Parameters used to generate derivative'
        },
        status: {
          bsonType: 'string',
          enum: ['generating', 'ready', 'failed', 'outdated'],
          description: 'Derivative status'
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

// Asset timeline data (for video/audio assets)
db.createCollection('asset_timelines', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['asset_id', 'timeline_type', 'data'],
      properties: {
        asset_id: {
          bsonType: 'string',
          description: 'Asset UUID'
        },
        timeline_type: {
          bsonType: 'string',
          enum: ['audio_waveform', 'video_thumbnails', 'subtitle_segments', 'chapter_markers', 'scene_detection', 'motion_vectors'],
          description: 'Type of timeline data'
        },
        data: {
          bsonType: 'array',
          items: {
            bsonType: 'object',
            properties: {
              timestamp: { bsonType: 'number' },
              duration: { bsonType: 'number' },
              value: {},
              metadata: { bsonType: 'object' }
            }
          },
          description: 'Timeline data points'
        },
        resolution: {
          bsonType: 'number',
          description: 'Data resolution (points per second)'
        },
        total_duration: {
          bsonType: 'number',
          description: 'Total asset duration in seconds'
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

// Asset usage analytics
db.createCollection('asset_analytics', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['asset_id', 'event_type', 'timestamp'],
      properties: {
        asset_id: {
          bsonType: 'string',
          description: 'Asset UUID'
        },
        event_type: {
          bsonType: 'string',
          enum: ['view', 'download', 'share', 'edit', 'comment', 'like', 'search_result', 'stream'],
          description: 'Type of analytics event'
        },
        user_id: {
          bsonType: 'string',
          description: 'User who performed the action'
        },
        session_id: {
          bsonType: 'string',
          description: 'User session ID'
        },
        context: {
          bsonType: 'object',
          properties: {
            referrer: { bsonType: 'string' },
            user_agent: { bsonType: 'string' },
            ip_address: { bsonType: 'string' },
            country: { bsonType: 'string' },
            device_type: { bsonType: 'string' }
          }
        },
        event_data: {
          bsonType: 'object',
          description: 'Event-specific data'
        },
        timestamp: {
          bsonType: 'date',
          description: 'Event timestamp'
        }
      }
    }
  }
});

// Asset collaboration data
db.createCollection('asset_collaboration', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['asset_id', 'collaboration_type', 'user_id', 'created_at'],
      properties: {
        asset_id: {
          bsonType: 'string',
          description: 'Asset UUID'
        },
        collaboration_type: {
          bsonType: 'string',
          enum: ['comment', 'annotation', 'review', 'approval', 'share', 'mention'],
          description: 'Type of collaboration'
        },
        user_id: {
          bsonType: 'string',
          description: 'User who performed the action'
        },
        content: {
          bsonType: 'string',
          description: 'Collaboration content (comment text, etc.)'
        },
        timecode: {
          bsonType: 'number',
          description: 'Timecode for time-based comments'
        },
        coordinates: {
          bsonType: 'object',
          properties: {
            x: { bsonType: 'number' },
            y: { bsonType: 'number' },
            width: { bsonType: 'number' },
            height: { bsonType: 'number' }
          },
          description: 'Spatial coordinates for visual annotations'
        },
        status: {
          bsonType: 'string',
          enum: ['active', 'resolved', 'archived'],
          description: 'Collaboration status'
        },
        parent_id: {
          bsonType: 'string',
          description: 'Parent collaboration ID for threaded discussions'
        },
        mentions: {
          bsonType: 'array',
          items: { bsonType: 'string' },
          description: 'User IDs mentioned in the collaboration'
        },
        attachments: {
          bsonType: 'array',
          items: {
            bsonType: 'object',
            properties: {
              filename: { bsonType: 'string' },
              storage_path: { bsonType: 'string' },
              mime_type: { bsonType: 'string' },
              file_size: { bsonType: 'number' }
            }
          },
          description: 'Attached files'
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

// Create indexes for asset collections
db.processing_jobs.createIndex({ asset_id: 1 });
db.processing_jobs.createIndex({ status: 1 });
db.processing_jobs.createIndex({ job_type: 1 });
db.processing_jobs.createIndex({ priority: 1 });
db.processing_jobs.createIndex({ created_at: -1 });
db.processing_jobs.createIndex({ worker_id: 1 });

db.asset_derivatives.createIndex({ asset_id: 1, derivative_type: 1 });
db.asset_derivatives.createIndex({ status: 1 });
db.asset_derivatives.createIndex({ created_at: -1 });

db.asset_timelines.createIndex({ asset_id: 1, timeline_type: 1 });
db.asset_timelines.createIndex({ timeline_type: 1 });

db.asset_analytics.createIndex({ asset_id: 1 });
db.asset_analytics.createIndex({ event_type: 1 });
db.asset_analytics.createIndex({ user_id: 1 });
db.asset_analytics.createIndex({ timestamp: -1 });

db.asset_collaboration.createIndex({ asset_id: 1 });
db.asset_collaboration.createIndex({ user_id: 1 });
db.asset_collaboration.createIndex({ collaboration_type: 1 });
db.asset_collaboration.createIndex({ status: 1 });
db.asset_collaboration.createIndex({ parent_id: 1 });
db.asset_collaboration.createIndex({ created_at: -1 });

print('Asset collections and indexes created successfully!');