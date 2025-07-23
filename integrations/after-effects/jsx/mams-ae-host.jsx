/*
MAMS After Effects Host Script (ExtendScript)
Provides integration between CEP panel and After Effects application
*/

// Global utilities
if (typeof JSON === "undefined") {
    JSON = {};
    JSON.stringify = function(obj) {
        return obj.toSource();
    };
    JSON.parse = function(str) {
        return eval("(" + str + ")");
    };
}

/**
 * MAMS After Effects Integration
 */
var MAMSAEIntegration = (function() {
    
    // Private variables
    var currentProject = null;
    var importSettings = {
        importAsFootage: true,
        createFolders: true,
        applyColorProfile: true
    };
    
    /**
     * Initialize the integration
     */
    function initialize() {
        currentProject = app.project;
        return {
            success: true,
            version: app.version,
            projectName: currentProject.file ? currentProject.file.name : "Untitled Project"
        };
    }
    
    /**
     * Get current After Effects application info
     */
    function getApplicationInfo() {
        return {
            version: app.version,
            language: app.isoLanguage,
            projectName: currentProject.file ? currentProject.file.name : "Untitled Project",
            activeItem: currentProject.activeItem ? {
                name: currentProject.activeItem.name,
                typeName: currentProject.activeItem.typeName,
                duration: currentProject.activeItem.duration || 0,
                width: currentProject.activeItem.width || 0,
                height: currentProject.activeItem.height || 0
            } : null
        };
    }
    
    /**
     * Import asset as footage item
     */
    function importAsFootage(filePath, name, metadata) {
        try {
            var file = new File(filePath);
            if (!file.exists) {
                return { success: false, error: "File not found: " + filePath };
            }
            
            var importOptions = new ImportOptions(file);
            var footageItem = currentProject.importFile(importOptions);
            
            if (footageItem) {
                // Apply metadata
                if (name) footageItem.name = name;
                if (metadata && metadata.comment) footageItem.comment = metadata.comment;
                
                // Organize in folder if specified
                if (importSettings.createFolders && metadata && metadata.project) {
                    var folder = getOrCreateFolder(metadata.project);
                    footageItem.parentFolder = folder;
                }
                
                return {
                    success: true,
                    itemId: footageItem.id,
                    name: footageItem.name,
                    typeName: footageItem.typeName,
                    duration: footageItem.duration || 0
                };
            } else {
                return { success: false, error: "Failed to import file" };
            }
        } catch (error) {
            return { success: false, error: error.toString() };
        }
    }
    
    /**
     * Import asset and create composition
     */
    function importAsComposition(filePath, name, metadata, compSettings) {
        try {
            // First import as footage
            var footageResult = importAsFootage(filePath, name + "_footage", metadata);
            if (!footageResult.success) {
                return footageResult;
            }
            
            var footageItem = currentProject.itemByID(footageResult.itemId);
            
            // Create composition
            var comp = currentProject.items.addComp(
                name || "MAMS Composition",
                compSettings.width || footageItem.width || 1920,
                compSettings.height || footageItem.height || 1080,
                compSettings.pixelAspect || 1.0,
                compSettings.duration || footageItem.duration || 10.0,
                compSettings.frameRate || 25
            );
            
            // Add footage to composition
            var layer = comp.layers.add(footageItem);
            layer.name = name || footageItem.name;
            
            // Apply metadata to layer
            if (metadata) {
                if (metadata.comment) layer.comment = metadata.comment;
                if (metadata.label) layer.label = parseInt(metadata.label) || 0;
            }
            
            return {
                success: true,
                compositionId: comp.id,
                layerId: layer.index,
                name: comp.name,
                duration: comp.duration
            };
        } catch (error) {
            return { success: false, error: error.toString() };
        }
    }
    
    /**
     * Create precomposition with imported asset
     */
    function importAsPrecomp(filePath, name, metadata) {
        try {
            // Get active composition
            var activeComp = currentProject.activeItem;
            if (!activeComp || !(activeComp instanceof CompItem)) {
                return { success: false, error: "No active composition" };
            }
            
            // Import footage
            var footageResult = importAsFootage(filePath, name + "_footage", metadata);
            if (!footageResult.success) {
                return footageResult;
            }
            
            var footageItem = currentProject.itemByID(footageResult.itemId);
            
            // Add to active composition
            var layer = activeComp.layers.add(footageItem);
            layer.name = name || footageItem.name;
            
            // Create precomposition
            var precompName = (name || footageItem.name) + " Precomp";
            var selectedLayers = [layer];
            
            var precomp = activeComp.layers.precompose(
                [layer.index],
                precompName,
                true // Move all attributes
            );
            
            return {
                success: true,
                precompId: precomp.id,
                layerIndex: activeComp.layers.length,
                name: precompName
            };
        } catch (error) {
            return { success: false, error: error.toString() };
        }
    }
    
    /**
     * Get or create project folder
     */
    function getOrCreateFolder(folderName) {
        // Look for existing folder
        for (var i = 1; i <= currentProject.numItems; i++) {
            var item = currentProject.item(i);
            if (item instanceof FolderItem && item.name === folderName) {
                return item;
            }
        }
        
        // Create new folder
        return currentProject.items.addFolder(folderName);
    }
    
    /**
     * Apply motion graphics template
     */
    function applyTemplate(templatePath, targetCompId, parameters) {
        try {
            var targetComp = currentProject.itemByID(targetCompId);
            if (!targetComp || !(targetComp instanceof CompItem)) {
                return { success: false, error: "Invalid target composition" };
            }
            
            // Import template project
            var templateFile = new File(templatePath);
            if (!templateFile.exists) {
                return { success: false, error: "Template file not found" };
            }
            
            var importOptions = new ImportOptions(templateFile);
            importOptions.importAs = ImportAsType.COMP;
            var templateComp = currentProject.importFile(importOptions);
            
            if (templateComp) {
                // Add template as layer to target composition
                var templateLayer = targetComp.layers.add(templateComp);
                templateLayer.name = templateComp.name;
                
                // Apply parameters if provided
                if (parameters) {
                    applyTemplateParameters(templateLayer, parameters);
                }
                
                return {
                    success: true,
                    layerIndex: templateLayer.index,
                    templateName: templateComp.name
                };
            } else {
                return { success: false, error: "Failed to import template" };
            }
        } catch (error) {
            return { success: false, error: error.toString() };
        }
    }
    
    /**
     * Apply template parameters to layer
     */
    function applyTemplateParameters(layer, parameters) {
        try {
            for (var paramName in parameters) {
                var value = parameters[paramName];
                
                // Try to find and set parameter
                if (layer.property(paramName)) {
                    var prop = layer.property(paramName);
                    if (prop.canSetValue) {
                        prop.setValue(value);
                    }
                }
                
                // Look in effects
                var effects = layer.property("Effects");
                if (effects) {
                    for (var i = 1; i <= effects.numProperties; i++) {
                        var effect = effects.property(i);
                        if (effect.property(paramName)) {
                            var effectProp = effect.property(paramName);
                            if (effectProp.canSetValue) {
                                effectProp.setValue(value);
                            }
                        }
                    }
                }
            }
        } catch (error) {
            // Parameter application errors are non-fatal
            $.writeln("Parameter application error: " + error.toString());
        }
    }
    
    /**
     * Add composition to render queue
     */
    function addToRenderQueue(compId, outputSettings) {
        try {
            var comp = currentProject.itemByID(compId);
            if (!comp || !(comp instanceof CompItem)) {
                return { success: false, error: "Invalid composition" };
            }
            
            var renderQueue = app.project.renderQueue;
            var renderItem = renderQueue.items.add(comp);
            
            // Configure output module
            var outputModule = renderItem.outputModules[1];
            
            if (outputSettings.template) {
                outputModule.applyTemplate(outputSettings.template);
            }
            
            if (outputSettings.outputPath) {
                outputModule.file = new File(outputSettings.outputPath);
            }
            
            // Set render settings if provided
            if (outputSettings.renderTemplate) {
                renderItem.applyTemplate(outputSettings.renderTemplate);
            }
            
            return {
                success: true,
                renderItemIndex: renderItem.index,
                outputPath: outputModule.file ? outputModule.file.fsName : null
            };
        } catch (error) {
            return { success: false, error: error.toString() };
        }
    }
    
    /**
     * Start render queue
     */
    function startRenderQueue() {
        try {
            app.project.renderQueue.render();
            return { success: true };
        } catch (error) {
            return { success: false, error: error.toString() };
        }
    }
    
    /**
     * Get current composition information
     */
    function getCurrentComposition() {
        try {
            var activeItem = currentProject.activeItem;
            if (activeItem && activeItem instanceof CompItem) {
                return {
                    success: true,
                    id: activeItem.id,
                    name: activeItem.name,
                    width: activeItem.width,
                    height: activeItem.height,
                    duration: activeItem.duration,
                    frameRate: activeItem.frameRate,
                    workAreaStart: activeItem.workAreaStart,
                    workAreaDuration: activeItem.workAreaDuration,
                    numLayers: activeItem.numLayers
                };
            } else {
                return { success: false, error: "No active composition" };
            }
        } catch (error) {
            return { success: false, error: error.toString() };
        }
    }
    
    /**
     * Export project structure to MAMS
     */
    function exportProjectStructure() {
        try {
            var projectData = {
                name: currentProject.file ? currentProject.file.name : "Untitled Project",
                compositions: [],
                assets: [],
                folders: []
            };
            
            // Gather project items
            for (var i = 1; i <= currentProject.numItems; i++) {
                var item = currentProject.item(i);
                
                if (item instanceof CompItem) {
                    var compData = {
                        id: item.id,
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
                            index: layer.index,
                            name: layer.name,
                            startTime: layer.startTime,
                            inPoint: layer.inPoint,
                            outPoint: layer.outPoint,
                            source: layer.source ? layer.source.name : null
                        });
                    }
                    
                    projectData.compositions.push(compData);
                    
                } else if (item instanceof FootageItem) {
                    projectData.assets.push({
                        id: item.id,
                        name: item.name,
                        filePath: item.file ? item.file.fsName : null,
                        duration: item.duration || 0,
                        width: item.width || 0,
                        height: item.height || 0
                    });
                    
                } else if (item instanceof FolderItem) {
                    projectData.folders.push({
                        id: item.id,
                        name: item.name,
                        numItems: item.numItems
                    });
                }
            }
            
            return {
                success: true,
                projectData: projectData
            };
        } catch (error) {
            return { success: false, error: error.toString() };
        }
    }
    
    /**
     * Update import settings
     */
    function updateImportSettings(settings) {
        try {
            if (settings.importAsFootage !== undefined) {
                importSettings.importAsFootage = settings.importAsFootage;
            }
            if (settings.createFolders !== undefined) {
                importSettings.createFolders = settings.createFolders;
            }
            if (settings.applyColorProfile !== undefined) {
                importSettings.applyColorProfile = settings.applyColorProfile;
            }
            
            return { success: true, settings: importSettings };
        } catch (error) {
            return { success: false, error: error.toString() };
        }
    }
    
    /**
     * Show After Effects alert
     */
    function showAlert(message, title) {
        alert(message, title || "MAMS");
        return { success: true };
    }
    
    // Public API
    return {
        initialize: initialize,
        getApplicationInfo: getApplicationInfo,
        importAsFootage: importAsFootage,
        importAsComposition: importAsComposition,
        importAsPrecomp: importAsPrecomp,
        applyTemplate: applyTemplate,
        addToRenderQueue: addToRenderQueue,
        startRenderQueue: startRenderQueue,
        getCurrentComposition: getCurrentComposition,
        exportProjectStructure: exportProjectStructure,
        updateImportSettings: updateImportSettings,
        showAlert: showAlert
    };
})();

// Initialize when script loads
MAMSAEIntegration.initialize();