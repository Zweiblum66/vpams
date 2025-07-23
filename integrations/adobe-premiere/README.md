# MAMS Adobe Premiere Pro Panel

## Overview

The MAMS Premiere Pro Panel is a CEP (Common Extensibility Platform) extension that integrates MAMS directly into Adobe Premiere Pro. It allows editors to browse, search, preview, and import MAMS assets without leaving their editing environment.

## Features

### Asset Management
- Browse MAMS media library directly in Premiere
- Advanced search with filters and metadata
- Preview videos, images, and audio files
- View detailed metadata and technical specs
- Download proxies or high-res files on demand

### Import & Timeline
- Direct import to project bins
- Drag-and-drop to timeline
- Automatic proxy/high-res switching
- Maintain metadata through import
- Link to original MAMS assets

### Collaboration
- Check-in/check-out assets
- View asset history and versions
- Add comments and annotations
- Share sequences back to MAMS
- Track usage and rights

### Workflow Integration
- Project synchronization
- Auto-save to MAMS
- Export presets integration
- Render queue management
- Status updates to MAMS

## Architecture

The extension consists of:
- **CEP Panel**: HTML/CSS/JavaScript UI
- **ExtendScript**: Adobe-specific scripting
- **Node.js Backend**: API communication
- **WebSocket**: Real-time updates
- **Local Cache**: Performance optimization

## Installation

### Requirements
- Adobe Premiere Pro CC 2019 or later
- MAMS account with API access
- Windows 10/11 or macOS 10.14+
- Internet connection

### Manual Installation
1. Download the extension package
2. Extract to CEP extensions folder:
   - Windows: `C:\Program Files (x86)\Common Files\Adobe\CEP\extensions\`
   - macOS: `/Library/Application Support/Adobe/CEP/extensions/`
3. Enable unsigned extensions (development only)
4. Restart Premiere Pro
5. Access via Window > Extensions > MAMS

### ZXP Installation
1. Download Adobe Extension Manager
2. Install the .zxp package
3. Restart Premiere Pro
4. Access via Window > Extensions > MAMS

## Configuration

### API Settings
```json
{
  "api_endpoint": "https://mams.company.com/api/v1",
  "api_key": "your-api-key",
  "workspace_id": "default",
  "proxy_quality": "medium",
  "cache_size_gb": 10,
  "auto_sync": true
}
```

### User Preferences
- Default import settings
- Proxy preferences
- UI theme (light/dark)
- Keyboard shortcuts
- Auto-refresh interval

## Usage

### Basic Workflow
1. Open MAMS panel in Premiere Pro
2. Login with your MAMS credentials
3. Browse or search for assets
4. Preview media files
5. Drag assets to timeline or project
6. Edit as normal
7. Export back to MAMS

### Advanced Features
- **Smart Collections**: Create dynamic asset groups
- **Metadata Mapping**: Customize field mappings
- **Batch Operations**: Process multiple assets
- **Offline Mode**: Work with cached content
- **Version Control**: Track and revert changes

## Development

### Technology Stack
- CEP (Common Extensibility Platform)
- ExtendScript for Premiere Pro API
- React for UI components
- Node.js for backend services
- TypeScript for type safety

### Project Structure
```
adobe-premiere/
├── CSXS/               # CEP manifest
├── client/             # Panel UI (React)
├── host/               # ExtendScript files
├── server/             # Node.js backend
├── shared/             # Shared utilities
├── build/              # Build scripts
└── dist/               # Distribution files
```

### Building from Source
```bash
# Install dependencies
npm install

# Development mode
npm run dev

# Production build
npm run build

# Package as ZXP
npm run package
```

### Debugging
1. Enable debug mode in CEP
2. Open Chrome DevTools at localhost:9999
3. Use ExtendScript Toolkit for host debugging
4. Check logs in CEP folder

## API Integration

### Authentication
```javascript
// Initialize MAMS client
const mamsClient = new MAMSClient({
  endpoint: config.api_endpoint,
  apiKey: config.api_key
});

// Authenticate user
await mamsClient.authenticate(username, password);
```

### Asset Operations
```javascript
// Search assets
const results = await mamsClient.search({
  query: 'nature',
  type: 'video',
  limit: 50
});

// Get asset details
const asset = await mamsClient.getAsset(assetId);

// Download proxy
const proxyPath = await mamsClient.downloadProxy(assetId);

// Import to Premiere
app.project.importFiles([proxyPath]);
```

## Troubleshooting

### Common Issues
1. **Panel not appearing**: Check CEP installation and permissions
2. **API connection failed**: Verify network and credentials
3. **Import errors**: Check file format compatibility
4. **Performance issues**: Adjust cache settings
5. **Sync problems**: Check workspace permissions

### Debug Mode
Enable debug mode for detailed logging:
1. Set `PlayerDebugMode` to 1 in registry/plist
2. Check debug console for errors
3. Review network requests in DevTools

## Support

- Documentation: https://docs.mams.io/premiere-panel
- Support: support@mams.io
- Issues: https://github.com/mams/premiere-panel/issues