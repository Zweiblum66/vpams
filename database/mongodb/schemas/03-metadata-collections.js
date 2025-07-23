// Metadata Service Collections Schema
use('mams_metadata');

// Flexible metadata storage
db.createCollection('asset_metadata', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['asset_id', 'metadata_type', 'data', 'created_at'],
      properties: {
        asset_id: {
          bsonType: 'string',
          description: 'Asset UUID'
        },
        metadata_type: {
          bsonType: 'string',
          enum: ['technical', 'descriptive', 'administrative', 'rights', 'preservation', 'custom'],
          description: 'Type of metadata'
        },
        schema_id: {
          bsonType: 'string',
          description: 'Reference to metadata schema'
        },
        data: {
          bsonType: 'object',
          description: 'Metadata fields and values'
        },
        source: {
          bsonType: 'string',
          enum: ['manual', 'extracted', 'ai', 'imported', 'workflow'],
          description: 'How metadata was created'
        },
        confidence: {
          bsonType: 'number',
          minimum: 0,
          maximum: 1,
          description: 'Confidence score for AI-generated metadata'
        },
        version: {
          bsonType: 'number',
          description: 'Metadata version'
        },
        created_by: {
          bsonType: 'string',
          description: 'User who created the metadata'
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

// Metadata extraction history
db.createCollection('extraction_history', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['asset_id', 'extractor', 'status', 'started_at'],
      properties: {
        asset_id: {
          bsonType: 'string',
          description: 'Asset UUID'
        },
        extractor: {
          bsonType: 'string',
          description: 'Name of metadata extractor'
        },
        extractor_version: {
          bsonType: 'string',
          description: 'Version of extractor used'
        },
        status: {
          bsonType: 'string',
          enum: ['pending', 'running', 'completed', 'failed', 'cancelled'],
          description: 'Extraction status'
        },
        extracted_data: {
          bsonType: 'object',
          description: 'Raw extracted data'
        },
        error_message: {
          bsonType: 'string',
          description: 'Error message if failed'
        },
        processing_time_ms: {
          bsonType: 'number',
          description: 'Processing time in milliseconds'
        },
        started_at: {
          bsonType: 'date',
          description: 'Extraction start time'
        },
        completed_at: {
          bsonType: 'date',
          description: 'Extraction completion time'
        }
      }
    }
  }
});

// Metadata validation rules
db.createCollection('validation_rules', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'rule_type', 'conditions', 'actions'],
      properties: {
        name: {
          bsonType: 'string',
          description: 'Rule name'
        },
        description: {
          bsonType: 'string',
          description: 'Rule description'
        },
        rule_type: {
          bsonType: 'string',
          enum: ['validation', 'enrichment', 'transformation', 'quality_check'],
          description: 'Type of validation rule'
        },
        conditions: {
          bsonType: 'object',
          description: 'Conditions that trigger the rule'
        },
        actions: {
          bsonType: 'array',
          items: { bsonType: 'object' },
          description: 'Actions to perform when conditions are met'
        },
        priority: {
          bsonType: 'number',
          description: 'Rule execution priority'
        },
        is_active: {
          bsonType: 'bool',
          description: 'Whether rule is active'
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

// Metadata templates
db.createCollection('metadata_templates', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'template_data', 'created_by'],
      properties: {
        name: {
          bsonType: 'string',
          description: 'Template name'
        },
        description: {
          bsonType: 'string',
          description: 'Template description'
        },
        category: {
          bsonType: 'string',
          description: 'Template category'
        },
        template_data: {
          bsonType: 'object',
          description: 'Template field values'
        },
        applies_to: {
          bsonType: 'array',
          items: { bsonType: 'string' },
          description: 'Asset types this template applies to'
        },
        is_default: {
          bsonType: 'bool',
          description: 'Whether this is a default template'
        },
        usage_count: {
          bsonType: 'number',
          description: 'How many times template has been used'
        },
        created_by: {
          bsonType: 'string',
          description: 'User who created the template'
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

// Create indexes for metadata collections
db.asset_metadata.createIndex({ asset_id: 1, metadata_type: 1 });
db.asset_metadata.createIndex({ schema_id: 1 });
db.asset_metadata.createIndex({ source: 1 });
db.asset_metadata.createIndex({ created_at: -1 });

// Dynamic field indexes for common metadata fields
db.asset_metadata.createIndex({ 'data.title': 1 });
db.asset_metadata.createIndex({ 'data.description': 'text' });
db.asset_metadata.createIndex({ 'data.tags': 1 });
db.asset_metadata.createIndex({ 'data.creation_date': 1 });
db.asset_metadata.createIndex({ 'data.location': 1 });

// Extraction history indexes
db.extraction_history.createIndex({ asset_id: 1, extractor: 1 });
db.extraction_history.createIndex({ status: 1 });
db.extraction_history.createIndex({ started_at: -1 });

// Validation rules indexes
db.validation_rules.createIndex({ rule_type: 1 });
db.validation_rules.createIndex({ is_active: 1 });
db.validation_rules.createIndex({ priority: 1 });

// Templates indexes
db.metadata_templates.createIndex({ name: 1 }, { unique: true });
db.metadata_templates.createIndex({ category: 1 });
db.metadata_templates.createIndex({ applies_to: 1 });
db.metadata_templates.createIndex({ is_default: 1 });
db.metadata_templates.createIndex({ usage_count: -1 });

print('Metadata collections and indexes created successfully!');