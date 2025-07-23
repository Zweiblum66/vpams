# MAMS Adobe After Effects Integration

## Overview

The MAMS Adobe After Effects integration provides seamless connection between the MAMS media asset management system and Adobe After Effects. This integration enables motion graphics artists and compositors to browse, import, and manage MAMS assets directly within After Effects.

## Features

- **CEP Panel Integration**: Built using Adobe Common Extensibility Platform
- **Asset Browser**: Browse and search MAMS assets within After Effects
- **Composition Import**: Direct import to compositions with proper layer organization
- **Project Sync**: Synchronize After Effects projects with MAMS
- **Metadata Mapping**: Automatic translation between MAMS and After Effects metadata
- **Template Management**: Access and apply MAMS motion graphics templates
- **Render Queue Integration**: Export finished compositions back to MAMS
- **Script Integration**: ExtendScript automation for advanced workflows
- **Precomp Management**: Organize assets into precompositions automatically

## Architecture

The integration consists of several components:

1. **CEP Panel** (`panel/`): Main HTML/JavaScript interface
2. **ExtendScript** (`jsx/`): After Effects automation scripts
3. **MAMS Client** (`js/`): API communication layer
4. **Templates** (`templates/`): Motion graphics templates and presets
5. **Build System** (`build/`): Development and distribution tools

## Requirements

- Adobe After Effects CC 2018 or later
- Adobe CEP 8.0 or later
- Windows 10 or macOS 10.13 or later
- MAMS server access
- Network connectivity
- Minimum 16GB RAM (32GB recommended for 4K+)

## Installation

### Automatic Installation

1. Download the MAMS After Effects integration package
2. Run the installer:
   ```bash
   # Windows
   install.bat
   
   # macOS
   ./install.sh
   ```

### Manual Installation

1. Copy extension to CEP extensions folder:
   ```
   # Windows
   C:\Program Files (x86)\Common Files\Adobe\CEP\extensions\MAMS\
   
   # macOS
   /Library/Application Support/Adobe/CEP/extensions/MAMS/
   ```

2. Enable unsigned extensions (development):
   ```
   # Windows Registry
   HKEY_CURRENT_USER\Software\Adobe\CSXS.8\PlayerDebugMode = "1"
   
   # macOS Terminal
   defaults write com.adobe.CSXS.8 PlayerDebugMode 1
   ```

3. Restart After Effects

## Configuration

### Initial Setup

1. Open After Effects
2. Go to **Window** > **Extensions** > **MAMS**
3. Enter your MAMS server URL and credentials
4. Configure import preferences
5. Test connection

### Panel Access

The MAMS panel appears in the Extensions menu:
- **Window** > **Extensions** > **MAMS**

Available functions:
- **Asset Browser**: Browse and search MAMS assets
- **Import Assets**: Import selected assets to current composition
- **Sync Project**: Synchronize current project with MAMS
- **Template Library**: Access motion graphics templates
- **Render Queue**: Export compositions to MAMS
- **Settings**: Configure MAMS connection

## Usage

### Asset Browser

1. Open **Window** > **Extensions** > **MAMS**
2. Search for assets using keywords or filters
3. Preview assets in the browser
4. Select assets and click "Import to Composition"
5. Assets appear as layers with proper organization

### Template Management

1. Browse MAMS template library
2. Preview template animations
3. Apply templates to compositions
4. Customize template parameters
5. Save custom variations back to MAMS

### Composition Sync

1. Create compositions with MAMS assets
2. Use "Sync with MAMS" to upload project structure
3. Share compositions with team members
4. Version control for collaborative workflows

### Render Queue Integration

1. Add compositions to render queue
2. Select MAMS as output destination
3. Configure delivery formats
4. Queue renders with metadata
5. Automatic upload upon completion

## Workflow Examples

### Motion Graphics Workflow

1. Import brand assets from MAMS
2. Apply motion graphics templates
3. Customize animations and timing
4. Render and upload to MAMS
5. Share for review and approval

### Compositing Workflow

1. Import source footage from MAMS
2. Create complex compositions
3. Use MAMS assets for textures/overlays
4. Export intermediate renders
5. Final composite delivery

### Template Creation

1. Build parametric motion graphics
2. Save as MAMS template
3. Share with design team
4. Version control templates
5. Apply across multiple projects

### Collaborative Review

1. Create composition milestones
2. Export review versions to MAMS
3. Collect feedback and annotations
4. Iterate based on comments
5. Final approval workflow

## ExtendScript API Examples

### Basic Asset Import

```javascript
// Import MAMS asset to composition
function importMAMSAsset(assetId, compName) {
    var comp = app.project.items.addComp(compName, 1920, 1080, 1, 30, 25);
    
    // Get asset from MAMS
    var assetData = getMAMSAsset(assetId);
    var localPath = downloadAsset(assetId);
    
    // Import to After Effects
    var importFile = new ImportOptions(new File(localPath));
    var footageItem = app.project.importFile(importFile);
    
    // Add to composition
    var layer = comp.layers.add(footageItem);
    layer.name = assetData.name;
    
    // Apply metadata
    if (assetData.metadata) {
        layer.comment = assetData.metadata.description || '';
        layer.label = getLabelFromTags(assetData.metadata.tags);
    }
    
    return layer;
}
```

### Template Application

```javascript
// Apply motion graphics template
function applyMAMSTemplate(templateId, targetComp) {
    var templateData = getMAMSTemplate(templateId);
    var templatePath = downloadTemplate(templateId);
    
    // Import template composition
    var importFile = new ImportOptions(new File(templatePath));
    var templateComp = app.project.importFile(importFile);
    
    // Create precomp in target composition
    var precompLayer = targetComp.layers.add(templateComp);
    precompLayer.name = templateData.name;
    
    // Apply template parameters
    if (templateData.parameters) {
        applyTemplateParameters(precompLayer, templateData.parameters);
    }
    
    return precompLayer;
}
```

### Render Queue Integration

```javascript
// Add composition to render queue with MAMS output
function renderToMAMS(comp, outputSettings) {
    var renderQueue = app.project.renderQueue;
    var renderItem = renderQueue.items.add(comp);
    
    // Configure output module
    var outputModule = renderItem.outputModules[1];
    outputModule.applyTemplate(outputSettings.template);
    
    // Set temporary output path
    var tempPath = getTempPath(comp.name + ".mov");
    outputModule.file = new File(tempPath);
    
    // Add post-render script to upload to MAMS
    renderItem.onRenderFinished = function() {
        uploadToMAMS(tempPath, outputSettings.metadata);
    };
    
    // Start render
    renderQueue.render();
}
```

### Project Sync

```javascript
// Export project structure to MAMS
function syncProjectWithMAMS() {
    var projectData = {
        name: app.project.file ? app.project.file.name : "Untitled Project",
        compositions: [],
        assets: [],
        version: app.version
    };
    
    // Gather compositions
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        
        if (item instanceof CompItem) {
            var compData = {
                name: item.name,
                width: item.width,
                height: item.height,
                duration: item.duration,
                frameRate: item.frameRate,
                layers: []
            };
            
            // Gather layers
            for (var j = 1; j <= item.numLayers; j++) {
                var layer = item.layer(j);
                compData.layers.push({
                    name: layer.name,
                    startTime: layer.startTime,
                    inPoint: layer.inPoint,
                    outPoint: layer.outPoint,
                    source: layer.source ? layer.source.name : null
                });
            }
            
            projectData.compositions.push(compData);
        }
    }
    
    // Upload to MAMS
    return uploadProjectData(projectData);
}
```

## CEP Panel Development

### HTML Structure

```html
<!DOCTYPE html>
<html>
<head>
    <title>MAMS Asset Manager</title>
    <link rel="stylesheet" href="css/main.css">
</head>
<body>
    <div id="app">
        <!-- Search Interface -->
        <div class="search-section">
            <input type="text" id="searchInput" placeholder="Search assets...">
            <button id="searchBtn">Search</button>
        </div>
        
        <!-- Asset Grid -->
        <div id="assetGrid" class="asset-grid">
            <!-- Assets populated dynamically -->
        </div>
        
        <!-- Import Options -->
        <div class="import-section">
            <select id="importMode">
                <option value="footage">Import as Footage</option>
                <option value="composition">Import as Composition</option>
                <option value="precomp">Create Precomposition</option>
            </select>
            <button id="importBtn">Import Selected</button>
        </div>
    </div>
    
    <script src="js/CSInterface.js"></script>
    <script src="js/mams-client.js"></script>
    <script src="js/ae-integration.js"></script>
    <script src="js/app.js"></script>
</body>
</html>
```

### JavaScript Integration

```javascript
// After Effects integration via CSInterface
class AEIntegration {
    constructor() {
        this.csInterface = new CSInterface();
        this.extensionId = this.csInterface.getExtensionID();
    }
    
    // Execute ExtendScript in After Effects
    evalScript(script, callback) {
        this.csInterface.evalScript(script, callback);
    }
    
    // Import asset to current composition
    importAsset(assetData, mode = 'footage') {
        const script = `
            (function() {
                var result = importMAMSAsset('${assetData.id}', '${mode}');
                return JSON.stringify(result);
            })();
        `;
        
        this.evalScript(script, (result) => {
            if (result) {
                console.log('Asset imported:', result);
            }
        });
    }
    
    // Get current composition info
    getCurrentComp(callback) {
        const script = `
            (function() {
                var comp = app.project.activeItem;
                if (comp && comp instanceof CompItem) {
                    return JSON.stringify({
                        name: comp.name,
                        width: comp.width,
                        height: comp.height,
                        duration: comp.duration
                    });
                }
                return null;
            })();
        `;
        
        this.evalScript(script, callback);
    }
}
```

## Template System

### Template Structure

```javascript
// MAMS Motion Graphics Template
{
    "name": "Logo Animation",
    "description": "Animated logo with customizable text",
    "version": "1.0.0",
    "category": "branding",
    "duration": 5.0,
    "frameRate": 25,
    "resolution": {
        "width": 1920,
        "height": 1080
    },
    "parameters": [
        {
            "name": "logoFile",
            "type": "file",
            "label": "Logo File",
            "required": true
        },
        {
            "name": "companyName",
            "type": "text",
            "label": "Company Name",
            "default": "Your Company"
        },
        {
            "name": "animationStyle",
            "type": "dropdown",
            "label": "Animation Style",
            "options": ["Fade In", "Slide In", "Scale Up"],
            "default": "Fade In"
        }
    ],
    "assets": [
        "template_composition.aep",
        "preview.mp4",
        "thumbnail.jpg"
    ]
}
```

### Template Application

```javascript
// Apply template with custom parameters
function applyTemplate(templateId, parameters) {
    const template = getMAMSTemplate(templateId);
    
    // Download template files
    const templatePath = downloadTemplateFiles(templateId);
    
    // Import template composition
    const importOptions = new ImportOptions();
    importOptions.file = new File(templatePath + "/template_composition.aep");
    const templateItem = app.project.importFile(importOptions);
    
    // Apply parameters
    template.parameters.forEach(param => {
        const value = parameters[param.name] || param.default;
        applyParameterToTemplate(templateItem, param, value);
    });
    
    return templateItem;
}
```

## Render Integration

### MAMS Output Module

```javascript
// Custom output module for MAMS delivery
class MAMSOutputModule {
    constructor(renderItem, settings) {
        this.renderItem = renderItem;
        this.settings = settings;
        this.setupOutputModule();
    }
    
    setupOutputModule() {
        const outputModule = this.renderItem.outputModules[1];
        
        // Apply render settings
        outputModule.applyTemplate(this.settings.template);
        
        // Set output path
        const outputPath = this.getTempOutputPath();
        outputModule.file = new File(outputPath);
        
        // Configure post-render upload
        this.renderItem.onRenderFinished = () => {
            this.uploadToMAMS(outputPath);
        };
    }
    
    async uploadToMAMS(filePath) {
        try {
            const metadata = {
                project: app.project.file ? app.project.file.name : 'Untitled',
                composition: this.renderItem.comp.name,
                renderDate: new Date().toISOString(),
                settings: this.settings
            };
            
            const result = await mamsClient.uploadAsset(filePath, metadata);
            if (result) {
                this.showNotification('Upload completed successfully');
            }
        } catch (error) {
            this.showNotification('Upload failed: ' + error.message, 'error');
        }
    }
}
```

## Troubleshooting

### Panel Not Appearing

- Check CEP version compatibility
- Verify extension installation path
- Enable unsigned extensions for development
- Restart After Effects completely

### Script Errors

- Check ExtendScript syntax
- Verify After Effects API compatibility
- Enable ExtendScript debugging
- Check console for error messages

### Connection Issues

- Test MAMS server URL in browser
- Verify API credentials
- Check firewall settings
- Review network configuration

### Import Failures

- Check available disk space
- Verify file permissions
- Test with smaller files first
- Check codec compatibility

## Advanced Features

### Custom Expressions

```javascript
// MAMS-powered expressions
function createMAMSExpression(assetId, property) {
    const expression = `
        // Get data from MAMS asset
        var mamsData = getMAMSAssetData('${assetId}');
        var animationData = mamsData.animation['${property}'];
        
        // Apply animation curve
        if (animationData && animationData.keyframes) {
            linear(time, 
                   animationData.keyframes.map(k => k.time),
                   animationData.keyframes.map(k => k.value)
            );
        } else {
            value; // Default value
        }
    `;
    
    return expression;
}
```

### Batch Processing

```javascript
// Batch process multiple assets
function batchProcessAssets(assetIds, templateId) {
    const results = [];
    
    assetIds.forEach(assetId => {
        try {
            // Create new composition
            const comp = app.project.items.addComp(
                `Processed_${assetId}`, 1920, 1080, 1, 25, 10
            );
            
            // Import asset
            const layer = importMAMSAsset(assetId, comp);
            
            // Apply template
            if (templateId) {
                applyMAMSTemplate(templateId, comp);
            }
            
            // Add to render queue
            const renderItem = addToRenderQueue(comp);
            
            results.push({
                assetId: assetId,
                composition: comp.name,
                status: 'queued'
            });
            
        } catch (error) {
            results.push({
                assetId: assetId,
                status: 'error',
                error: error.message
            });
        }
    });
    
    return results;
}
```

## Support

- Documentation: https://docs.mams.io/after-effects
- Support Email: support@mams.io
- Community Forum: https://community.mams.io/after-effects
- GitHub Issues: https://github.com/mams/after-effects-integration/issues

## License

Copyright (c) 2024 MAMS. All rights reserved.

This integration is provided under the MAMS Enterprise License.
Unauthorized copying or distribution is prohibited.