/**
 * MAMS ExtendScript for Adobe Premiere Pro
 * This file contains all host-side scripting for the MAMS panel
 */

// Global variables
var MAMS = {
    config: {
        proxyFolder: null,
        currentProject: null,
        activeBin: null
    }
};

/**
 * Initialize the MAMS panel
 */
function initializeMAMS() {
    try {
        // Set up proxy folder
        MAMS.config.proxyFolder = Folder.selectDialog("Select MAMS proxy folder");
        if (!MAMS.config.proxyFolder) {
            MAMS.config.proxyFolder = Folder.temp;
        }
        
        // Get current project
        MAMS.config.currentProject = app.project;
        
        // Set up event listeners
        app.bind('onProjectChanged', onProjectChanged);
        app.bind('onActiveSequenceChanged', onActiveSequenceChanged);
        
        return {
            success: true,
            proxyPath: MAMS.config.proxyFolder.fsName,
            projectName: MAMS.config.currentProject.name
        };
    } catch (error) {
        return {
            success: false,
            error: error.toString()
        };
    }
}

/**
 * Import an asset into the project
 * @param {string} filePath - Path to the asset file
 * @param {string} assetName - Name for the imported asset
 */
function importAsset(filePath, assetName) {
    try {
        var project = app.project;
        if (!project) {
            return "error: No active project";
        }
        
        // Import the file
        var importSuccess = project.importFiles([filePath], 
            false, // suppressUI
            project.getInsertionBin(), // targetBin
            false // importAsNumberedStills
        );
        
        if (!importSuccess) {
            return "error: Import failed";
        }
        
        // Find the imported item and rename it
        var rootItem = project.rootItem;
        var importedItem = findItemByPath(rootItem, filePath);
        
        if (importedItem) {
            importedItem.name = assetName;
            
            // Add metadata
            addMAMSMetadata(importedItem, {
                source: 'MAMS',
                originalPath: filePath,
                importDate: new Date().toISOString()
            });
        }
        
        return "success";
    } catch (error) {
        return "error: " + error.toString();
    }
}

/**
 * Import asset directly to timeline
 * @param {string} filePath - Path to the asset file
 * @param {number} timecode - Timeline position in seconds
 */
function importToTimeline(filePath, timecode) {
    try {
        var activeSeq = app.project.activeSequence;
        if (!activeSeq) {
            return "error: No active sequence";
        }
        
        // Import file first
        var project = app.project;
        project.importFiles([filePath], false, project.getInsertionBin(), false);
        
        // Find imported item
        var importedItem = findItemByPath(project.rootItem, filePath);
        if (!importedItem) {
            return "error: Could not find imported item";
        }
        
        // Add to timeline
        var videoTrack = activeSeq.videoTracks[0];
        if (importedItem.type === ProjectItemType.CLIP) {
            videoTrack.insertClip(importedItem, timecode);
        }
        
        return "success";
    } catch (error) {
        return "error: " + error.toString();
    }
}

/**
 * Get current project information
 */
function getProjectInfo() {
    try {
        var project = app.project;
        if (!project) {
            return null;
        }
        
        var sequences = [];
        var bins = [];
        
        // Get all sequences
        var numSeqs = project.sequences.numSequences;
        for (var i = 0; i < numSeqs; i++) {
            var seq = project.sequences[i];
            sequences.push({
                id: seq.sequenceID,
                name: seq.name,
                framerate: seq.timebase,
                duration: seq.end - seq.zero
            });
        }
        
        // Get project structure
        traverseProjectItems(project.rootItem, bins);
        
        return {
            name: project.name,
            path: project.path,
            sequences: sequences,
            bins: bins,
            lastSaved: project.lastSaveTime
        };
    } catch (error) {
        return null;
    }
}

/**
 * Create a new bin in the project
 * @param {string} binName - Name for the new bin
 * @param {string} parentBinId - ID of parent bin (optional)
 */
function createBin(binName, parentBinId) {
    try {
        var project = app.project;
        var parentBin = parentBinId ? findItemById(project.rootItem, parentBinId) : project.rootItem;
        
        if (!parentBin || parentBin.type !== ProjectItemType.BIN) {
            parentBin = project.rootItem;
        }
        
        var newBin = parentBin.createBin(binName);
        return {
            success: true,
            binId: newBin.nodeId,
            binName: newBin.name
        };
    } catch (error) {
        return {
            success: false,
            error: error.toString()
        };
    }
}

/**
 * Export current sequence to MAMS
 * @param {object} exportSettings - Export configuration
 */
function exportToMAMS(exportSettings) {
    try {
        var activeSeq = app.project.activeSequence;
        if (!activeSeq) {
            return "error: No active sequence";
        }
        
        // Set up export path
        var exportPath = MAMS.config.proxyFolder.fsName + "/" + activeSeq.name + ".mp4";
        
        // Configure export preset
        var outputPresetPath = exportSettings.presetPath || "HD 1080p 25.epr";
        
        // Queue export
        app.encoder.bind('onEncoderJobComplete', onExportComplete);
        app.encoder.bind('onEncoderJobError', onExportError);
        
        var jobID = app.encoder.encodeSequence(
            activeSeq,
            exportPath,
            outputPresetPath,
            app.encoder.ENCODE_IN_TO_OUT,
            false // removeOnCompletion
        );
        
        return {
            success: true,
            jobId: jobID,
            outputPath: exportPath
        };
    } catch (error) {
        return {
            success: false,
            error: error.toString()
        };
    }
}

/**
 * Get metadata from a project item
 * @param {string} itemId - Project item ID
 */
function getItemMetadata(itemId) {
    try {
        var item = findItemById(app.project.rootItem, itemId);
        if (!item) {
            return null;
        }
        
        var metadata = {
            name: item.name,
            type: item.type,
            mediaPath: item.getMediaPath(),
            duration: item.getOutPoint() - item.getInPoint(),
            framerate: item.getFootageInterpretation().frameRate,
            hasVideo: item.hasVideo(),
            hasAudio: item.hasAudio()
        };
        
        // Get XMP metadata
        if (item.type === ProjectItemType.CLIP) {
            var xmp = item.getXMPMetadata();
            if (xmp) {
                metadata.xmp = xmp;
            }
        }
        
        return metadata;
    } catch (error) {
        return null;
    }
}

/**
 * Add MAMS metadata to a project item
 * @param {ProjectItem} item - The project item
 * @param {object} metadata - Metadata to add
 */
function addMAMSMetadata(item, metadata) {
    try {
        if (item.type !== ProjectItemType.CLIP) {
            return false;
        }
        
        var xmpMeta = new XMPMeta();
        var mamsNamespace = "http://mams.io/xmp/1.0/";
        XMPMeta.registerNamespace(mamsNamespace, "mams:");
        
        for (var key in metadata) {
            if (metadata.hasOwnProperty(key)) {
                xmpMeta.setProperty(mamsNamespace, key, metadata[key]);
            }
        }
        
        item.setXMPMetadata(xmpMeta.serialize());
        return true;
    } catch (error) {
        return false;
    }
}

/**
 * Sync project with MAMS
 */
function syncProject() {
    try {
        var project = app.project;
        var projectData = {
            name: project.name,
            path: project.path,
            items: [],
            sequences: []
        };
        
        // Collect all project items
        traverseProjectItems(project.rootItem, function(item) {
            if (item.type === ProjectItemType.CLIP) {
                projectData.items.push({
                    id: item.nodeId,
                    name: item.name,
                    path: item.getMediaPath(),
                    type: item.type,
                    metadata: getItemMetadata(item.nodeId)
                });
            }
        });
        
        // Collect sequences
        for (var i = 0; i < project.sequences.numSequences; i++) {
            var seq = project.sequences[i];
            projectData.sequences.push({
                id: seq.sequenceID,
                name: seq.name,
                markers: getSequenceMarkers(seq)
            });
        }
        
        return projectData;
    } catch (error) {
        return null;
    }
}

// Helper Functions

/**
 * Find project item by file path
 */
function findItemByPath(rootItem, filePath) {
    for (var i = 0; i < rootItem.children.numItems; i++) {
        var child = rootItem.children[i];
        
        if (child.type === ProjectItemType.CLIP) {
            if (child.getMediaPath() === filePath) {
                return child;
            }
        } else if (child.type === ProjectItemType.BIN) {
            var found = findItemByPath(child, filePath);
            if (found) return found;
        }
    }
    return null;
}

/**
 * Find project item by ID
 */
function findItemById(rootItem, itemId) {
    if (rootItem.nodeId === itemId) {
        return rootItem;
    }
    
    for (var i = 0; i < rootItem.children.numItems; i++) {
        var child = rootItem.children[i];
        if (child.nodeId === itemId) {
            return child;
        }
        
        if (child.type === ProjectItemType.BIN) {
            var found = findItemById(child, itemId);
            if (found) return found;
        }
    }
    return null;
}

/**
 * Traverse project items recursively
 */
function traverseProjectItems(rootItem, callback) {
    callback(rootItem);
    
    for (var i = 0; i < rootItem.children.numItems; i++) {
        var child = rootItem.children[i];
        if (child.type === ProjectItemType.BIN) {
            traverseProjectItems(child, callback);
        } else {
            callback(child);
        }
    }
}

/**
 * Get markers from a sequence
 */
function getSequenceMarkers(sequence) {
    var markers = [];
    var markerCount = sequence.markers.numMarkers;
    
    for (var i = 0; i < markerCount; i++) {
        var marker = sequence.markers[i];
        markers.push({
            name: marker.name,
            comment: marker.comments,
            start: marker.start.seconds,
            end: marker.end.seconds,
            color: marker.getColorByIndex()
        });
    }
    
    return markers;
}

// Event Handlers

function onProjectChanged() {
    // Notify panel of project change
    var event = new CSXSEvent();
    event.type = "com.mams.projectChanged";
    event.data = getProjectInfo();
    event.dispatch();
}

function onActiveSequenceChanged() {
    // Notify panel of sequence change
    var event = new CSXSEvent();
    event.type = "com.mams.sequenceChanged";
    event.data = {
        sequenceId: app.project.activeSequence ? app.project.activeSequence.sequenceID : null
    };
    event.dispatch();
}

function onExportComplete(jobID, outputFilePath) {
    // Notify panel of export completion
    var event = new CSXSEvent();
    event.type = "com.mams.exportComplete";
    event.data = {
        jobId: jobID,
        outputPath: outputFilePath
    };
    event.dispatch();
}

function onExportError(jobID, error) {
    // Notify panel of export error
    var event = new CSXSEvent();
    event.type = "com.mams.exportError";
    event.data = {
        jobId: jobID,
        error: error
    };
    event.dispatch();
}