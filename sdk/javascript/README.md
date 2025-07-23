# MAMS JavaScript/TypeScript SDK

The official JavaScript/TypeScript SDK for MAMS (Media Asset Management System).

## Installation

```bash
npm install @mams/sdk
# or
yarn add @mams/sdk
# or
pnpm add @mams/sdk
```

## Quick Start

### JavaScript (ES6+)

```javascript
import { MAMSClient } from '@mams/sdk';

const client = new MAMSClient({
  apiKey: 'your-api-key',
  baseURL: 'https://api.mams.io'
});

// List assets
const assets = await client.assets.list({ limit: 10 });
console.log('Assets:', assets);

// Upload an asset
const file = new File(['content'], 'video.mp4', { type: 'video/mp4' });
const asset = await client.assets.upload({
  file,
  name: 'video.mp4',
  type: 'video'
});
```

### TypeScript

```typescript
import { MAMSClient, Asset, Project } from '@mams/sdk';

const client = new MAMSClient({
  apiKey: 'your-api-key',
  baseURL: 'https://api.mams.io'
});

// Type-safe operations
const assets: Asset[] = await client.assets.list({ limit: 10 });
const project: Project = await client.projects.create({
  name: 'My Project',
  description: 'A TypeScript project'
});
```

### Node.js

```javascript
const { MAMSClient } = require('@mams/sdk');
const fs = require('fs');

const client = new MAMSClient({
  apiKey: process.env.MAMS_API_KEY,
  baseURL: 'https://api.mams.io'
});

// Upload from file system
const fileStream = fs.createReadStream('video.mp4');
const asset = await client.assets.uploadFromStream({
  stream: fileStream,
  name: 'video.mp4',
  type: 'video'
});
```

## Authentication

### API Key

```javascript
import { MAMSClient } from '@mams/sdk';

const client = new MAMSClient({
  apiKey: 'your-api-key'
});
```

### JWT Token

```javascript
import { MAMSClient } from '@mams/sdk';

const client = new MAMSClient({
  jwt: 'your-jwt-token'
});
```

### OAuth2

```javascript
import { MAMSClient, OAuth2Provider } from '@mams/sdk';

const oauth2 = new OAuth2Provider({
  clientId: 'your-client-id',
  clientSecret: 'your-client-secret',
  redirectUri: 'http://localhost:3000/callback'
});

// Get authorization URL
const authUrl = oauth2.getAuthorizationUrl();
console.log('Visit:', authUrl);

// Exchange code for tokens (after callback)
const tokens = await oauth2.exchangeCode('authorization-code');

const client = new MAMSClient({
  oauth2Provider: oauth2
});
```

## Core Features

### Assets

```javascript
// List assets
const assets = await client.assets.list({
  limit: 20,
  offset: 0,
  type: 'video'
});

// Get single asset
const asset = await client.assets.get('asset-id');

// Upload asset
const asset = await client.assets.upload({
  file: fileInput.files[0],
  name: 'my-video.mp4',
  type: 'video',
  projectId: 'project-id',
  metadata: {
    description: 'A demo video',
    tags: ['demo', 'test']
  }
});

// Download asset
const blob = await client.assets.download('asset-id');

// Update metadata
await client.assets.updateMetadata('asset-id', {
  title: 'Updated Title',
  processed: true
});

// Search assets
const results = await client.assets.search({
  query: 'demo video',
  filters: { type: 'video' },
  limit: 10
});
```

### Projects

```javascript
// Create project
const project = await client.projects.create({
  name: 'My Project',
  description: 'Project description',
  frameRate: 25,
  resolution: '1920x1080'
});

// Add asset to project
await client.projects.addAsset(project.id, 'asset-id');

// Create sequence
const sequence = await client.projects.createSequence(project.id, {
  name: 'Main Sequence',
  frameRate: 25,
  resolution: '1920x1080'
});

// Add clip to timeline
await client.projects.addClipToTimeline(project.id, sequence.id, {
  assetId: 'asset-id',
  trackType: 'video',
  trackIndex: 0,
  startTime: 0,
  inPoint: 10,
  outPoint: 60
});

// Export project
const exportJob = await client.projects.export(project.id, {
  format: 'xml',
  options: { includeMedia: true }
});
```

### Workflows

```javascript
// List workflows
const workflows = await client.workflows.list();

// Start workflow
const execution = await client.workflows.start('workflow-id', {
  context: {
    assetId: 'asset-id',
    action: 'transcode'
  }
});

// Monitor execution
const status = await client.workflows.getExecution(execution.id);

// Approve step
await client.workflows.approveStep(execution.id, 'step-id', {
  comment: 'Approved'
});
```

### Search

```javascript
// Basic search
const results = await client.search.search({
  query: 'nature documentary',
  index: 'assets',
  limit: 20
});

// Semantic search
const semanticResults = await client.search.semantic({
  query: 'mountain landscape footage',
  threshold: 0.7
});

// Visual search
const visualResults = await client.search.visual({
  imageAssetId: 'reference-image-id',
  threshold: 0.8
});

// Get suggestions
const suggestions = await client.search.suggestions('doc');
```

### Users

```javascript
// Get current user
const user = await client.users.getCurrent();

// Update profile
await client.users.updateCurrent({
  firstName: 'John',
  lastName: 'Doe',
  timezone: 'UTC'
});

// Change password
await client.users.changePassword({
  currentPassword: 'old-password',
  newPassword: 'new-password'
});
```

## Error Handling

```javascript
import { MAMSError, NotFoundError, ValidationError } from '@mams/sdk';

try {
  const asset = await client.assets.get('invalid-id');
} catch (error) {
  if (error instanceof NotFoundError) {
    console.log('Asset not found');
  } else if (error instanceof ValidationError) {
    console.log('Validation errors:', error.errors);
  } else if (error instanceof MAMSError) {
    console.log('MAMS API error:', error.message);
  } else {
    console.log('Unexpected error:', error);
  }
}
```

## Configuration

```javascript
const client = new MAMSClient({
  // Authentication
  apiKey: 'your-api-key',
  // or jwt: 'your-jwt-token',
  // or oauth2Provider: oauth2Provider,
  
  // API settings
  baseURL: 'https://api.mams.io',
  apiVersion: 'v1',
  timeout: 30000,
  
  // Retry settings
  maxRetries: 3,
  retryDelay: 1000,
  
  // Upload settings
  chunkSize: 8 * 1024 * 1024, // 8MB
  maxUploadSize: 5 * 1024 * 1024 * 1024, // 5GB
  
  // Custom headers
  headers: {
    'X-Custom-Header': 'value'
  }
});
```

## Browser Support

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Node.js Support

- Node.js 14+

## TypeScript Support

This SDK is written in TypeScript and includes full type definitions. All API responses and request parameters are fully typed.

```typescript
import { Asset, Project, Workflow, SearchResult } from '@mams/sdk';

// All types are available for import
```

## Examples

See the [examples](./examples) directory for complete usage examples:

- [Basic Usage](./examples/basic-usage.js)
- [File Upload](./examples/file-upload.js)
- [Project Management](./examples/project-management.js)
- [Workflow Automation](./examples/workflow-automation.js)
- [Search Operations](./examples/search-operations.js)

## Development

```bash
# Install dependencies
npm install

# Run tests
npm test

# Build the SDK
npm run build

# Watch for changes during development
npm run build:watch

# Run linting
npm run lint

# Format code
npm run format
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

MIT License. See [LICENSE](LICENSE) for details.

## Support

- [Documentation](https://docs.mams.io)
- [API Reference](https://api.mams.io/docs)
- [GitHub Issues](https://github.com/mams-io/mams-sdk-js/issues)
- [Community Forum](https://community.mams.io)