# MAMS Final Cut Pro X Extension

## Overview

The MAMS Final Cut Pro X extension provides seamless integration between the MAMS media asset management system and Final Cut Pro X. This extension enables editors to browse, import, and manage MAMS assets directly within Final Cut Pro X's interface.

## Features

- **Native Extension**: Built using Final Cut Pro X Extension API
- **Asset Browser**: Browse and search MAMS assets within FCPX
- **Event Integration**: Direct import to Events with metadata preservation
- **Timeline Integration**: Drag assets directly to timeline
- **Project Sync**: Synchronize FCPX projects with MAMS
- **Metadata Mapping**: Automatic translation between MAMS and FCPX metadata
- **Keyword Management**: Sync keywords and tags between systems
- **Library Management**: Organize assets across multiple libraries
- **Collaboration**: Share events and projects through MAMS

## Architecture

The extension consists of several components:

1. **Extension Bundle** (`MAMS.fxbundle/`): Main extension package
2. **HTML Interface** (`interface/`): Web-based UI using FCPX Extension API
3. **JavaScript Client** (`js/`): MAMS API client and extension logic
4. **CSS Styles** (`css/`): Extension styling following FCPX design guidelines
5. **Resources** (`resources/`): Icons, images, and other assets

## Requirements

- Final Cut Pro X 10.4 or later
- macOS 10.14 or later
- MAMS server access
- Network connectivity
- Minimum 8GB RAM (16GB recommended for 4K+)

## Installation

### Automatic Installation

1. Download the MAMS FCPX extension package
2. Run the installer:
   ```bash
   ./install.sh
   ```

### Manual Installation

1. Copy extension bundle to FCPX extensions folder:
   ```
   ~/Library/Application Support/ProApps/Extensions/
   ```

2. Restart Final Cut Pro X

3. Enable the extension:
   - Open Final Cut Pro X
   - Go to **Window** > **Extensions** > **MAMS**

## Configuration

### Initial Setup

1. Open Final Cut Pro X
2. Go to **Window** > **Extensions** > **MAMS**
3. Click the settings icon in the extension
4. Enter your MAMS server URL and credentials
5. Configure import preferences
6. Test connection

### Extension Access

The MAMS extension appears in the Extensions window:
- **Window** > **Extensions** > **MAMS**

Available functions:
- **Asset Browser**: Browse and search MAMS assets
- **Import Assets**: Import selected assets to current Event
- **Sync Project**: Synchronize current project with MAMS
- **Export Project**: Export project/event to MAMS
- **Settings**: Configure MAMS connection

## Usage

### Asset Browser

1. Open **Window** > **Extensions** > **MAMS**
2. Use the search bar to find assets
3. Apply filters by type, date, or tags
4. Preview assets in the browser
5. Select assets and click "Import to Event"
6. Assets appear in current Event with metadata

### Direct Import

1. In the extension, search for required footage
2. Select multiple clips with Cmd+click
3. Choose import quality (proxy/optimized/original)
4. Select target Event or create new one
5. Assets imported with full metadata and keywords

### Project Sync

1. Select a project or event in FCPX
2. Click "Sync with MAMS" in the extension
3. Choose sync direction (to/from MAMS)
4. Review changes before applying
5. Sync completes automatically

### Keyword Management

1. MAMS tags automatically become FCPX keywords
2. Keywords sync bidirectionally
3. Use keyword collections for organization
4. Search by keywords in both systems

## Metadata Mapping

The extension maps between MAMS and FCPX metadata:

| MAMS Field | FCPX Property | Notes |
|------------|---------------|-------|
| name | Name | Clip name |
| description | Notes | Clip notes |
| tags | Keywords | Searchable keywords |
| created_at | Date Created | Creation date |
| creator | Creator | Creator name |
| duration | Duration | Frame accurate |
| frame_rate | Frame Rate | Timeline frame rate |
| resolution | Video Properties | Video format |
| location | Shot/Location | Shooting location |
| color_space | Color Space | Color management |

## Workflow Examples

### Basic Import Workflow

1. Open MAMS extension in FCPX
2. Search for required footage
3. Preview clips in browser
4. Select clips with Cmd+click
5. Choose "Import to Event"
6. Select quality and Event
7. Assets appear with keywords

### Project Collaboration

1. Create shared project in MAMS
2. Import shared Event from MAMS
3. Edit with team assets
4. Export rough cuts to MAMS
5. Review and approve online

### Library Management

1. Organize Events by MAMS projects
2. Use keywords for easy searching
3. Sync libraries across workstations
4. Share libraries through MAMS

### News Workflow

1. Set up automated news Event
2. Import breaking news footage
3. Quick assembly with templates
4. Export to MAMS for distribution
5. Archive completed stories

## JavaScript API Examples

### Basic Asset Search

```javascript
// Search for assets
async function searchAssets(query, filters = {}) {
    const params = new URLSearchParams({
        q: query,
        ...filters
    });
    
    const response = await fetch(`${serverUrl}/api/v1/assets/search?${params}`, {
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        }
    });
    
    return response.json();
}

// Import to current Event
async function importToEvent(assetIds, eventName) {
    for (const assetId of assetIds) {
        const asset = await getAsset(assetId);
        const localPath = await downloadAsset(assetId, 'edit');
        
        // Use FCPX API to import
        FinalCutPro.importMedia({
            filePath: localPath,
            eventName: eventName,
            metadata: {
                name: asset.name,
                notes: asset.description,
                keywords: asset.tags
            }
        });
    }
}
```

### Project Export

```javascript
// Export current project
async function exportProject() {
    const project = FinalCutPro.getCurrentProject();
    
    const projectData = {
        name: project.name,
        description: project.description,
        events: [],
        timelines: []
    };
    
    // Get all events in project
    for (const event of project.events) {
        const eventData = {
            name: event.name,
            clips: [],
            keywords: event.keywords
        };
        
        // Get clips in event
        for (const clip of event.clips) {
            eventData.clips.push({
                name: clip.name,
                file_path: clip.filePath,
                keywords: clip.keywords,
                notes: clip.notes,
                duration: clip.duration
            });
        }
        
        projectData.events.push(eventData);
    }
    
    // Upload to MAMS
    const response = await fetch(`${serverUrl}/api/v1/projects`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(projectData)
    });
    
    return response.json();
}
```

### Keyword Sync

```javascript
// Sync keywords between MAMS and FCPX
async function syncKeywords(clipId, mamsAssetId) {
    const clip = FinalCutPro.getClipById(clipId);
    const asset = await getAsset(mamsAssetId);
    
    // Get current keywords
    const fcpxKeywords = clip.keywords || [];
    const mamsKeywords = asset.tags || [];
    
    // Merge keywords
    const allKeywords = [...new Set([...fcpxKeywords, ...mamsKeywords])];
    
    // Update FCPX
    clip.setKeywords(allKeywords);
    
    // Update MAMS
    await updateAssetMetadata(mamsAssetId, {
        tags: allKeywords
    });
}
```

## Extension Development

### Project Structure

```
MAMS.fxbundle/
├── Contents/
│   ├── Info.plist                 # Extension metadata
│   ├── Resources/
│   │   ├── Main.html             # Main interface
│   │   ├── js/
│   │   │   ├── app.js           # Main application logic
│   │   │   ├── mams-client.js   # MAMS API client
│   │   │   └── fcpx-api.js      # FCPX integration
│   │   ├── css/
│   │   │   ├── main.css         # Main styles
│   │   │   └── components.css   # Component styles
│   │   └── images/
│   │       ├── icon.png         # Extension icon
│   │       └── assets/          # UI assets
│   └── MacOS/                    # (empty for HTML extensions)
```

### Building the Extension

```bash
# Build extension bundle
./build.sh

# Install for development
./install-dev.sh

# Package for distribution
./package.sh
```

### Debugging

1. Enable development mode in FCPX:
   ```bash
   defaults write com.apple.FinalCut FFExtensionDebuggingEnabled -bool YES
   ```

2. Use Safari Web Inspector:
   - Open Safari
   - Develop > Extension Name > Main.html

3. Console logging:
   ```javascript
   console.log('Debug message');
   ```

## Troubleshooting

### Extension Not Appearing

- Check extension is in correct folder
- Verify Info.plist is valid
- Restart Final Cut Pro X
- Check Console.app for errors

### Connection Issues

- Test MAMS server URL in browser
- Check API credentials
- Verify network connectivity
- Review firewall settings

### Import Failures

- Check available storage space
- Verify file permissions
- Test with smaller files first
- Check codec compatibility

### Performance Issues

- Use proxy media for editing
- Optimize media cache settings
- Monitor system resources
- Close unused applications

## Advanced Features

### Custom Workflows

```javascript
// News workflow automation
async function newsWorkflow() {
    const today = new Date().toISOString().split('T')[0];
    
    // Search for today's footage
    const footage = await searchAssets(`date:${today} tag:news`);
    
    // Create new Event
    const eventName = `News_${today}`;
    FinalCutPro.createEvent(eventName);
    
    // Import footage
    await importToEvent(footage.map(f => f.id), eventName);
    
    // Apply news template
    FinalCutPro.applyTemplate('News_Template');
}
```

### Batch Operations

```javascript
// Batch keyword application
async function batchApplyKeywords(clipIds, keywords) {
    for (const clipId of clipIds) {
        const clip = FinalCutPro.getClipById(clipId);
        const existingKeywords = clip.keywords || [];
        const newKeywords = [...new Set([...existingKeywords, ...keywords])];
        clip.setKeywords(newKeywords);
    }
}
```

## Support

- Documentation: https://docs.mams.io/fcpx
- Support Email: support@mams.io
- Community Forum: https://community.mams.io/fcpx
- GitHub Issues: https://github.com/mams/fcpx-extension/issues

## License

Copyright (c) 2024 MAMS. All rights reserved.

This extension is provided under the MAMS Enterprise License.
Unauthorized copying or distribution is prohibited.