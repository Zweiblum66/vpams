# MAMS DaVinci Resolve Integration

## Overview

The MAMS DaVinci Resolve integration provides seamless connection between the MAMS media asset management system and DaVinci Resolve. This integration enables editors and colorists to browse, import, and manage MAMS assets directly within DaVinci Resolve.

## Features

- **Script-based Integration**: Uses DaVinci Resolve's Python API for deep integration
- **Asset Browser**: Browse and search MAMS assets within Resolve's interface
- **Media Pool Import**: Direct import to Media Pool with metadata preservation
- **Timeline Integration**: Drag assets directly to timeline
- **Project Sync**: Synchronize Resolve projects with MAMS
- **Metadata Mapping**: Automatic translation between MAMS and Resolve metadata
- **Color Pipeline**: Manage color profiles and LUTs through MAMS
- **Render Queue**: Export finished content back to MAMS
- **Collaboration**: Share bins and timelines through MAMS

## Architecture

The integration consists of several components:

1. **Fusion Scripts** (`fusion-scripts/`): Scripts for Fusion page integration
2. **Python Scripts** (`scripts/`): Main integration scripts using Resolve API
3. **UI Components** (`ui/`): Custom UI panels and dialogs
4. **Utilities** (`utils/`): Helper functions and MAMS API client

## Requirements

- DaVinci Resolve 17.0 or later (Studio recommended)
- Python 3.6+ (included with Resolve)
- MAMS server access
- Network connectivity
- Minimum 16GB RAM (32GB recommended for 4K+)

## Installation

### Automatic Installation

1. Download the MAMS Resolve integration package
2. Run the installer:
   ```bash
   python install.py
   ```

### Manual Installation

1. Copy scripts to Resolve scripts folder:
   ```
   # Windows
   %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Scripts\MAMS\
   
   # macOS
   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Scripts/MAMS/
   
   # Linux
   ~/.local/share/DaVinciResolve/scripts/MAMS/
   ```

2. Copy Fusion scripts:
   ```
   # Windows
   %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\MAMS\
   
   # macOS
   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/MAMS/
   
   # Linux
   ~/.local/share/DaVinciResolve/Fusion/Scripts/MAMS/
   ```

3. Restart DaVinci Resolve

## Configuration

### Initial Setup

1. Open DaVinci Resolve
2. Go to **Workspace** > **Scripts** > **MAMS** > **Settings**
3. Enter your MAMS server URL and credentials
4. Configure import preferences
5. Test connection

### Script Access

Access MAMS functions through the Scripts menu:
- **Workspace** > **Scripts** > **MAMS**

Available scripts:
- **Asset Browser**: Browse and search MAMS assets
- **Import Assets**: Import selected assets to Media Pool
- **Sync Project**: Synchronize current project with MAMS
- **Export to MAMS**: Export timeline/clips to MAMS
- **Settings**: Configure MAMS connection

## Usage

### Asset Browser

1. Open **Scripts** > **MAMS** > **Asset Browser**
2. Search for assets using keywords or filters
3. Preview assets in the browser
4. Select assets and click "Import to Media Pool"
5. Assets appear in current bin with metadata

### Direct Import

1. Right-click in Media Pool
2. Select **MAMS** > **Import from MAMS**
3. Search and select assets
4. Choose import options (copy/link/proxy)
5. Assets imported with full metadata

### Project Sync

1. Use **Scripts** > **MAMS** > **Sync Project**
2. Choose sync direction (to/from MAMS)
3. Select items to sync
4. Review and confirm changes
5. Sync completes automatically

### Timeline Integration

1. Import assets to Media Pool
2. Drag assets to timeline as normal
3. Timeline edits tracked automatically
4. Export final timeline to MAMS

## Metadata Mapping

The integration maps between MAMS and Resolve metadata:

| MAMS Field | Resolve Property | Notes |
|------------|------------------|-------|
| name | Clip Name | Media pool name |
| description | Comments | Clip comments |
| tags | Keywords | Searchable keywords |
| created_at | Date Created | Original creation date |
| creator | Shot | Creator name |
| duration | Duration | Frame accurate |
| frame_rate | FPS | Timeline frame rate |
| resolution | Format | Video format |
| color_space | Color Space | Color management |
| location | Scene | Shooting location |

## Workflow Examples

### Basic Import Workflow

1. Open Asset Browser from Scripts menu
2. Search for required footage
3. Select multiple clips with Ctrl/Cmd
4. Click "Import to Media Pool"
5. Choose bin and import options
6. Assets appear with metadata

### Color Workflow

1. Import camera RAW files from MAMS
2. Apply color corrections in Color page
3. Save color versions back to MAMS
4. Share color decisions with team
5. Apply consistent looks across projects

### Collaborative Editing

1. Create shared project in MAMS
2. Import shared bins to Resolve
3. Edit timeline with team assets
4. Export rough cuts back to MAMS
5. Review and approve in MAMS interface

### Finishing Workflow

1. Complete edit and color grade
2. Use **Export to MAMS** script
3. Choose delivery formats
4. Queue renders with MAMS metadata
5. Finished content uploaded automatically

## Python API Examples

### Basic Asset Search

```python
import DaVinciResolveScript as dvr_script
from mams_client import MAMSClient

# Initialize
resolve = dvr_script.scriptapp("Resolve")
mams = MAMSClient()

# Search for assets
results = mams.search_assets("interview", filters={
    "type": "video",
    "tags": ["news", "2024"]
})

# Import to current bin
project = resolve.GetProjectManager().GetCurrentProject()
media_pool = project.GetMediaPool()
current_bin = media_pool.GetCurrentFolder()

for asset in results:
    # Download or link asset
    local_path = mams.get_asset_path(asset['id'])
    
    # Import to Resolve
    media_pool.ImportMedia([{
        "FilePath": local_path,
        "ClipName": asset['name']
    }])
```

### Timeline Export

```python
# Get current timeline
timeline = project.GetCurrentTimeline()

# Export timeline data
timeline_data = {
    "name": timeline.GetName(),
    "frame_rate": timeline.GetSetting("timelineFrameRate"),
    "clips": []
}

# Get all clips
for track_index in range(1, timeline.GetTrackCount("video") + 1):
    clips = timeline.GetItemsInTrack("video", track_index)
    
    for clip in clips:
        clip_data = {
            "name": clip.GetName(),
            "start": clip.GetStart(),
            "end": clip.GetEnd(),
            "media_pool_item": clip.GetMediaPoolItem().GetClipProperty("File Path")
        }
        timeline_data["clips"].append(clip_data)

# Upload to MAMS
mams.create_timeline(timeline_data)
```

### Custom Color Pipeline

```python
# Apply LUT from MAMS
def apply_mams_lut(clip, lut_name):
    lut_path = mams.download_lut(lut_name)
    
    # Get color page
    resolve.OpenPage("color")
    
    # Apply LUT to clip
    clip.SetLUT(1, lut_path)
    
    return True

# Save color version to MAMS
def save_color_version(clip, version_name):
    # Export still or clip with color
    export_path = f"/tmp/{version_name}.dpx"
    
    timeline.GrabStill()
    # Upload to MAMS
    mams.upload_color_version(clip.GetMediaPoolItem().GetClipProperty("File Path"), 
                             export_path, version_name)
```

## Fusion Integration

### Fusion Scripts

The integration includes Fusion scripts for compositor workflow:

```lua
-- Fusion script example
comp = fu:GetCurrentComp()

-- Import MAMS asset as Loader
function ImportMAMSAsset(asset_id)
    local asset_path = MAMSClient:GetAssetPath(asset_id)
    local loader = comp:AddTool("Loader", -32768, -32768)
    loader:LoadFile(asset_path)
    return loader
end

-- Save composition to MAMS
function SaveCompToMAMS(comp_name)
    local comp_path = comp:MapPath(comp_name .. ".comp")
    comp:Save(comp_path)
    MAMSClient:UploadComposition(comp_path)
end
```

## Troubleshooting

### Script Not Appearing

- Check script installation path
- Verify Python dependencies
- Restart DaVinci Resolve
- Check console for errors

### Connection Issues

- Test MAMS server URL in browser
- Verify API credentials
- Check firewall settings
- Review network configuration

### Import Failures

- Check available storage space
- Verify file permissions
- Test with smaller files first
- Review codec compatibility

### Performance Issues

- Increase proxy cache size
- Use optimized media formats
- Check GPU acceleration settings
- Monitor system resources

## Advanced Features

### Custom Workflows

Create custom scripts for specific workflows:

```python
# Custom news workflow
def news_workflow():
    # Search for today's footage
    today = datetime.now().strftime("%Y-%m-%d")
    footage = mams.search_assets(f"date:{today} tag:news")
    
    # Create new project
    project_manager = resolve.GetProjectManager()
    project = project_manager.CreateProject("News_" + today)
    
    # Import footage
    media_pool = project.GetMediaPool()
    for asset in footage:
        import_asset(asset, media_pool)
    
    # Create timeline template
    create_news_timeline_template()
```

### Batch Operations

```python
# Batch color correction
def batch_color_correct(clip_list, lut_name):
    for clip in clip_list:
        apply_color_correction(clip, lut_name)
        save_color_version(clip, f"{clip.GetName()}_graded")
```

## Support

- Documentation: https://docs.mams.io/resolve
- Support Email: support@mams.io
- Community Forum: https://community.mams.io/resolve
- GitHub Issues: https://github.com/mams/resolve-integration/issues

## License

Copyright (c) 2024 MAMS. All rights reserved.

This integration is provided under the MAMS Enterprise License.
Unauthorized copying or distribution is prohibited.