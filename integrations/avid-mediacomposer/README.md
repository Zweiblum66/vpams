# MAMS Avid Media Composer Plugin

## Overview

The MAMS Avid Media Composer plugin provides seamless integration between the MAMS media asset management system and Avid Media Composer. This plugin enables editors to browse, search, import, and sync assets directly from within Media Composer.

## Features

- **Asset Browser**: Browse and search MAMS assets within Media Composer
- **Direct Import**: Import assets directly to bins with metadata preservation
- **Project Sync**: Synchronize Media Composer projects with MAMS
- **Metadata Mapping**: Automatic metadata translation between MAMS and Avid
- **Proxy Workflow**: Work with low-res proxies and relink to high-res
- **Background Sync**: Automatic project backup to MAMS
- **Collaborative Features**: Share bins and sequences through MAMS
- **Search Integration**: Use MAMS advanced search within Media Composer

## Architecture

The plugin consists of three main components:

1. **AMA Plugin** (`ama-plugin/`): Provides direct media access without importing
2. **Console Plugin** (`console-plugin/`): Adds MAMS commands to Avid Console
3. **Panel UI** (`panel/`): Web-based UI panel for asset browsing

## Requirements

- Avid Media Composer 2018.12 or later
- Windows 10/11 or macOS 10.14+
- MAMS server access
- Network connectivity
- Minimum 8GB RAM

## Installation

### Windows

1. Close Media Composer if running
2. Copy the plugin files to:
   ```
   C:\Program Files\Avid\AVX2_Plug-ins\MAMS\
   ```
3. Copy the AMA plugin to:
   ```
   C:\Program Files\Avid\AMA_Plug-ins\MAMS\
   ```
4. Register the plugin:
   ```cmd
   cd "C:\Program Files\Avid\AVX2_Plug-ins\MAMS"
   regsvr32 MAMSPlugin.dll
   ```
5. Restart Media Composer

### macOS

1. Close Media Composer if running
2. Copy the plugin bundle to:
   ```
   /Library/Application Support/Avid/AVX2/Plug-ins/MAMS.avx
   ```
3. Copy the AMA plugin to:
   ```
   /Library/Application Support/Avid/AMA/Plug-ins/MAMS.bundle
   ```
4. Set permissions:
   ```bash
   sudo chmod -R 755 /Library/Application Support/Avid/AVX2/Plug-ins/MAMS.avx
   sudo chmod -R 755 /Library/Application Support/Avid/AMA/Plug-ins/MAMS.bundle
   ```
5. Restart Media Composer

## Configuration

### Initial Setup

1. Open Media Composer
2. Go to **Tools** > **MAMS** > **Settings**
3. Enter your MAMS server URL
4. Log in with your MAMS credentials
5. Configure default import settings

### Preferences

- **Import Location**: Choose default bin for imports
- **Proxy Quality**: Select proxy resolution (DNxHD 36, DNxHD 145, etc.)
- **Metadata Mapping**: Configure field mappings
- **Sync Interval**: Set automatic sync frequency
- **Cache Size**: Configure local cache for performance

## Usage

### Asset Browser

1. Open the MAMS panel: **Tools** > **MAMS** > **Asset Browser**
2. Search for assets using keywords, metadata, or filters
3. Preview assets by double-clicking
4. Drag assets to bins to import

### Console Commands

Access MAMS functions through the Avid Console:

```
MAMS.Search "keyword"           # Search for assets
MAMS.Import <asset_id>          # Import specific asset
MAMS.Sync                       # Sync current project
MAMS.Link <path>               # Link to MAMS asset
MAMS.Export <sequence>         # Export sequence to MAMS
```

### AMA Linking

1. Right-click in a bin
2. Select **Link to AMA Volume** > **MAMS**
3. Browse and select assets
4. Assets appear as AMA-linked clips

### Project Sync

1. Enable auto-sync in settings
2. Manual sync: **Tools** > **MAMS** > **Sync Project**
3. View sync status in the MAMS panel
4. Resolve conflicts through the UI

## Metadata Mapping

The plugin automatically maps between MAMS and Avid metadata:

| MAMS Field | Avid Column | Notes |
|------------|-------------|-------|
| name | Name | Clip name |
| description | Comments | Long description |
| tags | Keywords | Comma-separated |
| created_at | Creation Date | UTC timestamp |
| creator | Cameraman | User who uploaded |
| duration | Duration | Frame accurate |
| format | Video Format | Codec info |
| frame_rate | Frame Rate | FPS |
| resolution | Raster | Width x Height |
| location | Shoot Location | GPS or text |

## Workflow Examples

### Basic Import Workflow

1. Open MAMS Asset Browser
2. Search for required footage
3. Select multiple assets with Ctrl/Cmd
4. Drag to a bin or click Import
5. Choose import options (copy/link/proxy)
6. Assets appear in bin with metadata

### Proxy Workflow

1. Import as "Proxy Only" for offline editing
2. Edit with lightweight proxies
3. When ready to finish:
   - **Tools** > **MAMS** > **Relink to High-Res**
   - Select sequences to relink
   - MAMS downloads and relinks automatically

### Collaborative Workflow

1. Create a shared bin in Media Composer
2. Right-click > **Share to MAMS**
3. Set permissions for team members
4. Team receives notification
5. Others can **Import from MAMS** > **Shared Bins**

## Troubleshooting

### Plugin Not Appearing

- Verify installation paths are correct
- Check plugin permissions
- Look for errors in Console
- Reinstall Visual C++ Redistributables (Windows)

### Connection Issues

- Test MAMS server URL in browser
- Check firewall settings
- Verify network connectivity
- Review proxy settings

### Import Failures

- Check available disk space
- Verify file permissions
- Review Console for error messages
- Try importing smaller batches

### Performance Issues

- Increase cache size in settings
- Use proxy workflow for large files
- Check network bandwidth
- Close unnecessary applications

## API Reference

### JavaScript API (Panel)

```javascript
// Initialize MAMS connection
MAMS.init({
  serverUrl: 'https://mams.example.com',
  apiKey: 'your-api-key'
});

// Search for assets
MAMS.search('keyword', {
  type: 'video',
  tags: ['news', 'sports']
}).then(results => {
  console.log(results);
});

// Import asset
MAMS.importAsset(assetId, {
  destination: '/path/to/bin',
  copyLocal: true,
  importMetadata: true
});

// Sync project
MAMS.syncProject({
  projectPath: AvidAPI.getCurrentProject(),
  includeMedia: false,
  includeBins: true
});
```

### C++ API (Plugin)

```cpp
// Get MAMS interface
IMAMSInterface* pMAMS = GetMAMSInterface();

// Search assets
MAMSSearchParams params;
params.query = "interview";
params.type = MAMS_TYPE_VIDEO;
MAMSResults* results = pMAMS->Search(params);

// Import asset
MAMSImportOptions options;
options.copyLocal = true;
options.createProxy = true;
pMAMS->ImportAsset(assetId, binPath, options);
```

## Support

- Documentation: https://docs.mams.io/avid
- Support Email: support@mams.io
- Community Forum: https://community.mams.io/avid
- Issue Tracker: https://github.com/mams/avid-plugin/issues

## License

Copyright (c) 2024 MAMS. All rights reserved.

This plugin is provided under the MAMS Enterprise License.
Unauthorized copying or distribution is prohibited.