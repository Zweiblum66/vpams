/**
 * Avid API Interface for MAMS Panel
 * Provides communication between the web panel and Avid Media Composer
 */

class AvidAPI {
    constructor() {
        this.isAvailable = false;
        this.callbacks = {};
        this.messageId = 0;
        
        // Check if running inside Avid
        this.detectAvidEnvironment();
    }
    
    detectAvidEnvironment() {
        // Check for Avid-specific objects
        if (window.external && window.external.AvidInterface) {
            this.isAvailable = true;
            this.interface = window.external.AvidInterface;
            this.setupMessageHandlers();
        } else {
            console.warn('Avid API not available - running in standalone mode');
        }
    }
    
    setupMessageHandlers() {
        // Listen for messages from Avid
        window.addEventListener('message', (event) => {
            if (event.data && event.data.type === 'AvidResponse') {
                this.handleResponse(event.data);
            }
        });
    }
    
    handleResponse(data) {
        const { id, result, error } = data;
        const callback = this.callbacks[id];
        
        if (callback) {
            if (error) {
                callback.reject(new Error(error));
            } else {
                callback.resolve(result);
            }
            delete this.callbacks[id];
        }
    }
    
    sendCommand(command, params = {}) {
        return new Promise((resolve, reject) => {
            if (!this.isAvailable) {
                // Simulate responses in standalone mode
                setTimeout(() => {
                    resolve(this.getMockResponse(command, params));
                }, 100);
                return;
            }
            
            const id = ++this.messageId;
            this.callbacks[id] = { resolve, reject };
            
            try {
                this.interface.sendCommand(JSON.stringify({
                    id,
                    command,
                    params
                }));
            } catch (error) {
                delete this.callbacks[id];
                reject(error);
            }
        });
    }
    
    // Avid-specific commands
    
    async getCurrentProject() {
        return this.sendCommand('getCurrentProject');
    }
    
    async getCurrentBin() {
        return this.sendCommand('getCurrentBin');
    }
    
    async getCurrentSequence() {
        return this.sendCommand('getCurrentSequence');
    }
    
    async importAsset(assetPath, binPath, options = {}) {
        return this.sendCommand('importAsset', {
            assetPath,
            binPath,
            options
        });
    }
    
    async createAMALink(amaUrl, binPath) {
        return this.sendCommand('createAMALink', {
            amaUrl,
            binPath
        });
    }
    
    async exportSequence(sequencePath, outputPath, format) {
        return this.sendCommand('exportSequence', {
            sequencePath,
            outputPath,
            format
        });
    }
    
    async getMediaInfo(mediaPath) {
        return this.sendCommand('getMediaInfo', {
            mediaPath
        });
    }
    
    async createBin(name, parentPath) {
        return this.sendCommand('createBin', {
            name,
            parentPath
        });
    }
    
    async refreshBin(binPath) {
        return this.sendCommand('refreshBin', {
            binPath
        });
    }
    
    async showMessage(message, type = 'info') {
        return this.sendCommand('showMessage', {
            message,
            type
        });
    }
    
    // Mock responses for standalone testing
    getMockResponse(command, params) {
        const mockResponses = {
            getCurrentProject: {
                name: 'Test Project',
                path: '/Volumes/Media/Projects/TestProject.avp',
                created: '2024-01-15T10:00:00Z'
            },
            getCurrentBin: {
                name: 'Current Bin',
                path: '/CurrentBin',
                itemCount: 5
            },
            getCurrentSequence: {
                name: 'Test Sequence',
                path: '/TestSequence',
                duration: 3600,
                framerate: 29.97
            },
            importAsset: {
                success: true,
                clipName: params.assetPath.split('/').pop()
            },
            createAMALink: {
                success: true,
                linkName: 'AMA Link'
            },
            createBin: {
                success: true,
                binPath: `/${params.name}`
            }
        };
        
        return mockResponses[command] || { success: true };
    }
}

// Create global instance
window.AvidAPI = new AvidAPI();