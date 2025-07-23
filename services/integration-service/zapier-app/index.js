/**
 * MAMS Zapier App Definition
 * 
 * This file defines the MAMS app for the Zapier platform
 */

const authentication = require('./authentication');
const assetCreatedTrigger = require('./triggers/assetCreated');
const workflowCompletedTrigger = require('./triggers/workflowCompleted');
const projectCreatedTrigger = require('./triggers/projectCreated');
const searchAssetsSearch = require('./searches/searchAssets');
const searchProjectsSearch = require('./searches/searchProjects');
const createAssetAction = require('./creates/createAsset');
const updateMetadataAction = require('./creates/updateMetadata');

// Define the App
const App = {
  version: require('./package.json').version,
  platformVersion: require('zapier-platform-core').version,
  
  authentication: authentication,
  
  beforeRequest: [
    (request, z, bundle) => {
      // Add API key to all requests
      if (bundle.authData.apiKey) {
        request.headers['X-API-Key'] = bundle.authData.apiKey;
      }
      return request;
    }
  ],
  
  afterResponse: [
    (response, z, bundle) => {
      // Handle common error responses
      if (response.status === 401) {
        throw new z.errors.RefreshAuthError('Invalid API Key');
      }
      if (response.status === 429) {
        throw new z.errors.ThrottledError('Rate limit exceeded');
      }
      return response;
    }
  ],
  
  // Triggers - Events from MAMS
  triggers: {
    [assetCreatedTrigger.key]: assetCreatedTrigger,
    [workflowCompletedTrigger.key]: workflowCompletedTrigger,
    [projectCreatedTrigger.key]: projectCreatedTrigger
  },
  
  // Searches - Find data in MAMS
  searches: {
    [searchAssetsSearch.key]: searchAssetsSearch,
    [searchProjectsSearch.key]: searchProjectsSearch
  },
  
  // Creates - Actions in MAMS
  creates: {
    [createAssetAction.key]: createAssetAction,
    [updateMetadataAction.key]: updateMetadataAction
  },
  
  // Resources (if using REST Hooks)
  resources: {}
};

module.exports = App;