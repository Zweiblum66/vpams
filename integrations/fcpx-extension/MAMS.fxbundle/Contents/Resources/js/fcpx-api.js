/**
 * Final Cut Pro X API Integration
 * Handles communication with FCPX through the Extension API
 */

class FCPXApi {
    constructor() {
        this.isConnected = false;
        this.currentLibrary = null;
        this.currentEvent = null;
        this.currentProject = null;
        
        // Initialize FCPX API if available
        this.initialize();
    }

    /**
     * Initialize FCPX Extension API
     */
    initialize() {
        // Check if FCPX Extension API is available
        if (typeof FinalCutPro !== 'undefined') {
            this.isConnected = true;
            this.setupEventListeners();
            this.updateCurrentContext();
        } else {
            console.warn('Final Cut Pro Extension API not available');
            this.isConnected = false;
        }
    }

    /**
     * Setup event listeners for FCPX events
     */
    setupEventListeners() {
        if (!this.isConnected) return;

        try {
            // Listen for library changes
            FinalCutPro.addEventListener('libraryChanged', (event) => {
                this.currentLibrary = event.library;
                this.dispatchEvent('libraryChanged', event);
            });

            // Listen for event changes
            FinalCutPro.addEventListener('eventChanged', (event) => {
                this.currentEvent = event.event;
                this.dispatchEvent('eventChanged', event);
            });

            // Listen for project changes
            FinalCutPro.addEventListener('projectChanged', (event) => {
                this.currentProject = event.project;
                this.dispatchEvent('projectChanged', event);
            });

            // Listen for selection changes
            FinalCutPro.addEventListener('selectionChanged', (event) => {
                this.dispatchEvent('selectionChanged', event);
            });
        } catch (error) {
            console.error('Error setting up FCPX event listeners:', error);
        }
    }

    /**
     * Update current context (library, event, project)
     */
    async updateCurrentContext() {
        if (!this.isConnected) return;

        try {
            this.currentLibrary = await FinalCutPro.getCurrentLibrary();
            this.currentEvent = await FinalCutPro.getCurrentEvent();
            this.currentProject = await FinalCutPro.getCurrentProject();
        } catch (error) {
            console.error('Error updating FCPX context:', error);
        }
    }

    /**
     * Get all libraries
     */
    async getLibraries() {
        if (!this.isConnected) return [];

        try {
            return await FinalCutPro.getLibraries();
        } catch (error) {
            console.error('Error getting libraries:', error);
            return [];
        }
    }

    /**
     * Get events in current library
     */
    async getEvents(library = null) {
        if (!this.isConnected) return [];

        try {
            const targetLibrary = library || this.currentLibrary;
            if (!targetLibrary) return [];

            return await targetLibrary.getEvents();
        } catch (error) {
            console.error('Error getting events:', error);
            return [];
        }
    }

    /**
     * Get projects in current event
     */
    async getProjects(event = null) {
        if (!this.isConnected) return [];

        try {
            const targetEvent = event || this.currentEvent;
            if (!targetEvent) return [];

            return await targetEvent.getProjects();
        } catch (error) {
            console.error('Error getting projects:', error);
            return [];
        }
    }

    /**
     * Create new event
     */
    async createEvent(name, library = null) {
        if (!this.isConnected) throw new Error('FCPX API not available');

        try {
            const targetLibrary = library || this.currentLibrary;
            if (!targetLibrary) throw new Error('No library available');

            const event = await targetLibrary.createEvent(name);
            this.currentEvent = event;
            return event;
        } catch (error) {
            console.error('Error creating event:', error);
            throw error;
        }
    }

    /**
     * Import media to event
     */
    async importMedia(mediaItems, event = null, options = {}) {
        if (!this.isConnected) throw new Error('FCPX API not available');

        try {
            const targetEvent = event || this.currentEvent;
            if (!targetEvent) throw new Error('No event available');

            const importOptions = {
                copyToEvent: options.copyToEvent !== false,
                createOptimizedMedia: options.createOptimizedMedia || false,
                createProxyMedia: options.createProxyMedia || false,
                ...options
            };

            const results = [];
            for (const mediaItem of mediaItems) {
                try {
                    const imported = await targetEvent.importMedia(mediaItem, importOptions);
                    results.push(imported);
                } catch (error) {
                    console.error(`Failed to import ${mediaItem.filePath}:`, error);
                    results.push(null);
                }
            }

            return results;
        } catch (error) {
            console.error('Error importing media:', error);
            throw error;
        }
    }

    /**
     * Import single asset from MAMS
     */
    async importAssetFromMAMS(asset, downloadUrl, event = null, options = {}) {
        if (!this.isConnected) throw new Error('FCPX API not available');

        try {
            // Download asset to temporary location
            const tempPath = await this.downloadAssetToTemp(downloadUrl, asset.name);
            
            const mediaItem = {
                filePath: tempPath,
                name: asset.name,
                metadata: {
                    notes: asset.description || '',
                    keywords: asset.tags || [],
                    creator: asset.creator || '',
                    location: asset.location || '',
                    date: asset.created_at ? new Date(asset.created_at) : new Date(),
                    // MAMS specific metadata
                    mamsAssetId: asset.id,
                    mamsAssetType: asset.type,
                    mamsOriginalPath: asset.file_path
                }
            };

            // Set keywords
            if (asset.tags && asset.tags.length > 0) {
                await this.ensureKeywords(asset.tags, event);
            }

            const imported = await this.importMedia([mediaItem], event, options);
            
            // Clean up temporary file
            await this.cleanupTempFile(tempPath);
            
            return imported[0];
        } catch (error) {
            console.error('Error importing asset from MAMS:', error);
            throw error;
        }
    }

    /**
     * Download asset to temporary location
     */
    async downloadAssetToTemp(downloadUrl, filename) {
        try {
            const response = await fetch(downloadUrl);
            if (!response.ok) throw new Error(`Download failed: ${response.statusText}`);
            
            const blob = await response.blob();
            
            // Create temporary file URL
            const tempUrl = URL.createObjectURL(blob);
            
            // Note: In a real extension, you'd use FCPX's temporary file APIs
            // This is a simplified implementation
            return tempUrl;
        } catch (error) {
            console.error('Error downloading asset:', error);
            throw error;
        }
    }

    /**
     * Clean up temporary file
     */
    async cleanupTempFile(filePath) {
        try {
            // In a real implementation, clean up the temporary file
            if (filePath.startsWith('blob:')) {
                URL.revokeObjectURL(filePath);
            }
        } catch (error) {
            console.warn('Error cleaning up temp file:', error);
        }
    }

    /**
     * Ensure keywords exist in FCPX
     */
    async ensureKeywords(keywords, event = null) {
        if (!this.isConnected || !keywords || keywords.length === 0) return;

        try {
            const targetEvent = event || this.currentEvent;
            if (!targetEvent) return;

            for (const keyword of keywords) {
                try {
                    await targetEvent.createKeyword(keyword);
                } catch (error) {
                    // Keyword might already exist, ignore error
                    console.warn(`Keyword '${keyword}' might already exist:`, error);
                }
            }
        } catch (error) {
            console.error('Error ensuring keywords:', error);
        }
    }

    /**
     * Create new project
     */
    async createProject(name, event = null) {
        if (!this.isConnected) throw new Error('FCPX API not available');

        try {
            const targetEvent = event || this.currentEvent;
            if (!targetEvent) throw new Error('No event available');

            const project = await targetEvent.createProject(name);
            this.currentProject = project;
            return project;
        } catch (error) {
            console.error('Error creating project:', error);
            throw error;
        }
    }

    /**
     * Export project data for MAMS
     */
    async exportProjectForMAMS(project = null) {
        if (!this.isConnected) return null;

        try {
            const targetProject = project || this.currentProject;
            if (!targetProject) return null;

            const projectData = {
                name: targetProject.name,
                description: targetProject.description || '',
                created_at: new Date().toISOString(),
                fcpx_project_id: targetProject.id,
                settings: {
                    frameRate: targetProject.frameRate,
                    resolution: targetProject.resolution,
                    colorSpace: targetProject.colorSpace
                },
                events: [],
                timelines: []
            };

            // Get associated event
            const event = await targetProject.getEvent();
            if (event) {
                const eventData = await this.exportEventForMAMS(event);
                projectData.events.push(eventData);
            }

            // Get timelines
            const timelines = await targetProject.getTimelines();
            for (const timeline of timelines) {
                const timelineData = await this.exportTimelineForMAMS(timeline);
                projectData.timelines.push(timelineData);
            }

            return projectData;
        } catch (error) {
            console.error('Error exporting project for MAMS:', error);
            return null;
        }
    }

    /**
     * Export event data for MAMS
     */
    async exportEventForMAMS(event) {
        try {
            const eventData = {
                name: event.name,
                description: event.description || '',
                fcpx_event_id: event.id,
                clips: [],
                keywords: []
            };

            // Get clips in event
            const clips = await event.getClips();
            for (const clip of clips) {
                const clipData = {
                    name: clip.name,
                    file_path: clip.filePath,
                    duration: clip.duration,
                    frame_rate: clip.frameRate,
                    keywords: clip.keywords || [],
                    notes: clip.notes || '',
                    mams_asset_id: clip.metadata?.mamsAssetId || null
                };
                eventData.clips.push(clipData);
            }

            // Get keywords
            const keywords = await event.getKeywords();
            eventData.keywords = keywords.map(k => k.name);

            return eventData;
        } catch (error) {
            console.error('Error exporting event for MAMS:', error);
            return { name: event.name, clips: [], keywords: [] };
        }
    }

    /**
     * Export timeline data for MAMS
     */
    async exportTimelineForMAMS(timeline) {
        try {
            const timelineData = {
                name: timeline.name,
                duration: timeline.duration,
                frame_rate: timeline.frameRate,
                fcpx_timeline_id: timeline.id,
                clips: []
            };

            // Get clips in timeline
            const clips = await timeline.getClips();
            for (const clip of clips) {
                const clipData = {
                    name: clip.name,
                    start_time: clip.startTime,
                    duration: clip.duration,
                    in_point: clip.inPoint,
                    out_point: clip.outPoint,
                    track_index: clip.trackIndex,
                    mams_asset_id: clip.metadata?.mamsAssetId || null
                };
                timelineData.clips.push(clipData);
            }

            return timelineData;
        } catch (error) {
            console.error('Error exporting timeline for MAMS:', error);
            return { name: timeline.name, clips: [] };
        }
    }

    /**
     * Get current selection
     */
    async getCurrentSelection() {
        if (!this.isConnected) return null;

        try {
            return await FinalCutPro.getCurrentSelection();
        } catch (error) {
            console.error('Error getting current selection:', error);
            return null;
        }
    }

    /**
     * Show notification in FCPX
     */
    async showNotification(message, type = 'info') {
        if (!this.isConnected) return;

        try {
            await FinalCutPro.showNotification({
                message,
                type,
                duration: 3000
            });
        } catch (error) {
            console.error('Error showing notification:', error);
        }
    }

    /**
     * Custom event dispatcher
     */
    dispatchEvent(eventName, data) {
        const event = new CustomEvent(`fcpx:${eventName}`, {
            detail: data
        });
        document.dispatchEvent(event);
    }

    /**
     * Add event listener for FCPX events
     */
    addEventListener(eventName, callback) {
        document.addEventListener(`fcpx:${eventName}`, callback);
    }

    /**
     * Remove event listener
     */
    removeEventListener(eventName, callback) {
        document.removeEventListener(`fcpx:${eventName}`, callback);
    }

    /**
     * Get FCPX version info
     */
    async getVersionInfo() {
        if (!this.isConnected) return null;

        try {
            return await FinalCutPro.getVersionInfo();
        } catch (error) {
            console.error('Error getting version info:', error);
            return null;
        }
    }

    /**
     * Check if feature is supported
     */
    isFeatureSupported(feature) {
        if (!this.isConnected) return false;

        try {
            return FinalCutPro.isFeatureSupported(feature);
        } catch (error) {
            console.error(`Error checking feature support for ${feature}:`, error);
            return false;
        }
    }

    /**
     * Get connection status
     */
    getConnectionStatus() {
        return {
            connected: this.isConnected,
            currentLibrary: this.currentLibrary?.name || null,
            currentEvent: this.currentEvent?.name || null,
            currentProject: this.currentProject?.name || null
        };
    }
}

// Export as global for use in extension
window.FCPXApi = FCPXApi;