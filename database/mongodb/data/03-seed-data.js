// MongoDB Seed Data for MAMS Development
print('Seeding MongoDB with sample data...');

// Search engine sample data
use('mams_search');

// Insert sample search indices
db.search_indices.insertMany([
  {
    name: 'main_text_index',
    type: 'text',
    status: 'ready',
    settings: {
      analyzer: 'standard',
      boost_factors: {
        title: 2.0,
        description: 1.5,
        keywords: 1.2
      }
    },
    statistics: {
      document_count: 0,
      index_size_bytes: 0,
      last_updated: new Date()
    },
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'visual_similarity_index',
    type: 'visual',
    status: 'ready',
    settings: {
      model: 'clip-vit-base-patch32',
      dimensions: 512
    },
    statistics: {
      document_count: 0,
      index_size_bytes: 0,
      last_updated: new Date()
    },
    created_at: new Date(),
    updated_at: new Date()
  }
]);

// Insert sample saved searches
db.saved_searches.insertMany([
  {
    name: 'Recent Videos',
    description: 'Videos uploaded in the last 7 days',
    query: {
      content_type: 'video',
      date_filter: {
        field: 'upload_date',
        range: '7d'
      }
    },
    user_id: '00000000-0000-0000-0000-000000000100',
    is_public: true,
    alert_enabled: false,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'High-Resolution Images',
    description: 'Images with resolution > 1920x1080',
    query: {
      content_type: 'image',
      metadata_filters: {
        width: { $gt: 1920 },
        height: { $gt: 1080 }
      }
    },
    user_id: '00000000-0000-0000-0000-000000000101',
    is_public: false,
    alert_enabled: true,
    created_at: new Date(),
    updated_at: new Date()
  }
]);

// Metadata service sample data
use('mams_metadata');

// Insert sample metadata templates
db.metadata_templates.insertMany([
  {
    name: 'Video Production Template',
    description: 'Standard template for video production assets',
    category: 'production',
    template_data: {
      title: '',
      description: '',
      director: '',
      producer: '',
      camera_operator: '',
      location: '',
      shoot_date: null,
      keywords: [],
      copyright_holder: '',
      usage_rights: 'internal'
    },
    applies_to: ['video'],
    is_default: true,
    usage_count: 0,
    created_by: '00000000-0000-0000-0000-000000000100',
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'Stock Photo Template',
    description: 'Template for stock photography metadata',
    category: 'stock',
    template_data: {
      title: '',
      description: '',
      photographer: '',
      location: '',
      creation_date: null,
      keywords: [],
      model_released: false,
      property_released: false,
      usage_rights: 'royalty_free'
    },
    applies_to: ['image'],
    is_default: false,
    usage_count: 0,
    created_by: '00000000-0000-0000-0000-000000000100',
    created_at: new Date(),
    updated_at: new Date()
  }
]);

// Insert sample validation rules
db.validation_rules.insertMany([
  {
    name: 'Required Title',
    description: 'Ensure all assets have a title',
    rule_type: 'validation',
    conditions: {
      field: 'title',
      operator: 'exists',
      value: true
    },
    actions: [
      {
        type: 'error',
        message: 'Title is required for all assets'
      }
    ],
    priority: 1,
    is_active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'Auto-tag from filename',
    description: 'Extract tags from filename',
    rule_type: 'enrichment',
    conditions: {
      field: 'filename',
      operator: 'regex',
      value: '^([A-Z]+)_([0-9]+)_(.+)\\.(mp4|mov|avi)$'
    },
    actions: [
      {
        type: 'extract_tags',
        source: 'filename',
        pattern: '^([A-Z]+)_([0-9]+)_(.+)\\.(mp4|mov|avi)$',
        mappings: {
          1: 'project_code',
          2: 'sequence_number',
          3: 'scene_description'
        }
      }
    ],
    priority: 5,
    is_active: true,
    created_at: new Date(),
    updated_at: new Date()
  }
]);

// AI service sample data
use('mams_ai');

// Insert sample AI models
db.ai_models.insertMany([
  {
    name: 'whisper-large-v3',
    model_type: 'transcription',
    version: '3.0',
    description: 'OpenAI Whisper large model for speech recognition',
    provider: 'openai',
    status: 'available',
    capabilities: ['speech_to_text', 'language_detection', 'timestamp_alignment'],
    supported_formats: ['mp3', 'wav', 'mp4', 'mov'],
    configuration: {
      language: 'auto',
      temperature: 0.2,
      chunk_length: 30
    },
    performance_metrics: {
      accuracy: 0.95,
      latency_ms: 2000
    },
    usage_stats: {
      total_requests: 0,
      successful_requests: 0,
      failed_requests: 0,
      average_processing_time: 0
    },
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'yolo-v8',
    model_type: 'object_detection',
    version: '8.0',
    description: 'YOLO v8 object detection model',
    provider: 'custom',
    status: 'available',
    capabilities: ['object_detection', 'bounding_boxes', 'confidence_scores'],
    supported_formats: ['jpg', 'png', 'mp4', 'mov'],
    configuration: {
      confidence_threshold: 0.5,
      iou_threshold: 0.45,
      max_detections: 100
    },
    performance_metrics: {
      accuracy: 0.89,
      precision: 0.92,
      recall: 0.87,
      f1_score: 0.89,
      latency_ms: 150
    },
    usage_stats: {
      total_requests: 0,
      successful_requests: 0,
      failed_requests: 0,
      average_processing_time: 0
    },
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'clip-vit-base-patch32',
    model_type: 'image_classification',
    version: '1.0',
    description: 'CLIP Vision Transformer for image understanding',
    provider: 'huggingface',
    status: 'available',
    capabilities: ['image_classification', 'text_image_similarity', 'zero_shot_classification'],
    supported_formats: ['jpg', 'png', 'gif', 'webp'],
    configuration: {
      embedding_dimension: 512,
      patch_size: 32
    },
    performance_metrics: {
      accuracy: 0.76,
      latency_ms: 300
    },
    usage_stats: {
      total_requests: 0,
      successful_requests: 0,
      failed_requests: 0,
      average_processing_time: 0
    },
    created_at: new Date(),
    updated_at: new Date()
  }
]);

// Assets service sample data
use('mams_assets');

// Insert sample processing job templates
db.processing_jobs.insertMany([
  {
    asset_id: '00000000-0000-0000-0000-000000000001',
    job_type: 'ingest',
    status: 'completed',
    priority: 1,
    progress: 100,
    input_params: {
      source_path: '/uploads/demo_video.mp4',
      destination_path: '/assets/demo_video.mp4'
    },
    output_data: {
      file_size: 1024000,
      duration: 120.5,
      width: 1920,
      height: 1080,
      codec: 'h264',
      bitrate: 5000000
    },
    actual_duration_ms: 5000,
    created_at: new Date(Date.now() - 86400000), // 1 day ago
    started_at: new Date(Date.now() - 86400000 + 1000),
    completed_at: new Date(Date.now() - 86400000 + 6000)
  },
  {
    asset_id: '00000000-0000-0000-0000-000000000002',
    job_type: 'proxy',
    status: 'running',
    priority: 2,
    progress: 45,
    input_params: {
      source_asset_id: '00000000-0000-0000-0000-000000000002',
      proxy_quality: 'medium',
      target_bitrate: 2000000
    },
    worker_id: 'worker-001',
    estimated_duration_ms: 30000,
    created_at: new Date(Date.now() - 3600000), // 1 hour ago
    started_at: new Date(Date.now() - 3000000) // 50 minutes ago
  }
]);

// Cache service sample data
use('mams_cache');

// Insert sample cache entries
db.general_cache.insertMany([
  {
    key: 'user_preferences_00000000-0000-0000-0000-000000000100',
    value: {
      theme: 'dark',
      language: 'en',
      items_per_page: 20,
      auto_play_preview: true
    },
    namespace: 'user_preferences',
    tags: ['user', 'preferences'],
    ttl_seconds: 86400,
    created_at: new Date(),
    expires_at: new Date(Date.now() + 86400000),
    last_accessed: new Date(),
    access_count: 1
  },
  {
    key: 'system_config',
    value: {
      max_file_size: 5368709120,
      supported_formats: ['mp4', 'mov', 'avi', 'jpg', 'png'],
      ai_processing_enabled: true,
      auto_transcription: true
    },
    namespace: 'system',
    tags: ['system', 'config'],
    ttl_seconds: 3600,
    created_at: new Date(),
    expires_at: new Date(Date.now() + 3600000),
    last_accessed: new Date(),
    access_count: 1
  }
]);

// Insert sample API cache entries
db.api_cache.insertMany([
  {
    cache_key: 'GET_/api/v1/assets?page=1&limit=20',
    endpoint: '/api/v1/assets',
    method: 'GET',
    query_params: {
      page: 1,
      limit: 20
    },
    response_data: {
      data: [],
      meta: {
        page: 1,
        limit: 20,
        total: 0
      }
    },
    status_code: 200,
    user_id: '00000000-0000-0000-0000-000000000100',
    organization_id: '00000000-0000-0000-0000-000000000001',
    hit_count: 1,
    last_hit: new Date(),
    created_at: new Date(),
    expires_at: new Date(Date.now() + 300000) // 5 minutes
  }
]);

print('MongoDB seed data inserted successfully!');