/**
 * Asset Created Trigger
 * 
 * Triggers when a new asset is created in MAMS
 */

const perform = async (z, bundle) => {
  const response = await z.request({
    url: `${bundle.authData.baseUrl}/api/v1/integrations/zapier/sample-data/asset.created`,
    method: 'GET'
  });
  
  // In a real implementation, this would fetch recent assets
  // For now, return sample data
  const sample = response.json;
  
  return [sample]; // Zapier expects an array
};

const performSubscribe = async (z, bundle) => {
  // Subscribe to webhook
  const response = await z.request({
    url: `${bundle.authData.baseUrl}/api/v1/integrations/zapier/triggers`,
    method: 'POST',
    body: {
      event_types: ['asset.created'],
      target_url: bundle.targetUrl
    }
  });
  
  return response.json;
};

const performUnsubscribe = async (z, bundle) => {
  // Unsubscribe from webhook
  const response = await z.request({
    url: `${bundle.authData.baseUrl}/api/v1/integrations/zapier/triggers/${bundle.subscribeData.trigger_id}`,
    method: 'DELETE'
  });
  
  return response.json;
};

const performList = async (z, bundle) => {
  // This runs when webhook is triggered
  return [bundle.cleanedRequest];
};

module.exports = {
  key: 'assetCreated',
  noun: 'Asset',
  
  display: {
    label: 'New Asset',
    description: 'Triggers when a new asset is created in MAMS.',
    hidden: false,
    important: true
  },
  
  operation: {
    type: 'hook',
    
    inputFields: [
      {
        key: 'asset_type',
        label: 'Asset Type',
        type: 'string',
        helpText: 'Filter by asset type (video, image, audio, document)',
        choices: {
          'all': 'All Types',
          'video': 'Video',
          'image': 'Image', 
          'audio': 'Audio',
          'document': 'Document'
        },
        default: 'all',
        required: false
      },
      {
        key: 'project_id',
        label: 'Project',
        type: 'string',
        dynamic: 'projectList.id.name',
        helpText: 'Filter by specific project',
        required: false
      }
    ],
    
    perform: performList,
    performSubscribe: performSubscribe,
    performUnsubscribe: performUnsubscribe,
    
    sample: {
      id: 'evt_sample_asset_created',
      type: 'asset.created',
      timestamp: '2024-01-15T10:30:00Z',
      asset_id: 'asset_abc123def456',
      asset_name: 'sample_video.mp4',
      asset_type: 'video',
      file_size: 104857600,
      file_path: '/storage/videos/2024/01/sample_video.mp4',
      data_duration: 120.5,
      data_resolution: '1920x1080',
      meta_project_id: 'proj_xyz789',
      meta_uploaded_by: 'user@example.com'
    },
    
    outputFields: [
      {key: 'id', label: 'Event ID'},
      {key: 'asset_id', label: 'Asset ID'},
      {key: 'asset_name', label: 'Asset Name'},
      {key: 'asset_type', label: 'Asset Type'},
      {key: 'file_size', label: 'File Size (bytes)'},
      {key: 'file_path', label: 'File Path'},
      {key: 'data_duration', label: 'Duration (seconds)'},
      {key: 'data_resolution', label: 'Resolution'},
      {key: 'meta_project_id', label: 'Project ID'},
      {key: 'meta_uploaded_by', label: 'Uploaded By'}
    ]
  }
};