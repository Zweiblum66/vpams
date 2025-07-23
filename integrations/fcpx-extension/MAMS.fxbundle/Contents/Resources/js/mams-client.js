/**
 * MAMS Client for Final Cut Pro X Extension
 * Handles communication with MAMS server
 */

class MAMSClient {
    constructor() {
        this.baseUrl = '';
        this.apiKey = '';
        this.accessToken = '';
        this.isConnected = false;
        this.settings = {};
        
        // Load configuration
        this.loadConfig();
    }

    /**
     * Load configuration from localStorage
     */
    loadConfig() {
        try {
            const config = localStorage.getItem('mams_config');
            if (config) {
                const parsed = JSON.parse(config);
                this.baseUrl = parsed.serverUrl || '';
                this.apiKey = parsed.apiKey || '';
                this.accessToken = parsed.accessToken || '';
                this.settings = parsed.settings || {};
            }
        } catch (error) {
            console.error('Error loading config:', error);
        }
    }

    /**
     * Save configuration to localStorage
     */
    saveConfig(config) {
        try {
            const currentConfig = JSON.parse(localStorage.getItem('mams_config') || '{}');
            const newConfig = { ...currentConfig, ...config };
            localStorage.setItem('mams_config', JSON.stringify(newConfig));
            
            // Update instance variables
            if (config.serverUrl) this.baseUrl = config.serverUrl;
            if (config.apiKey) this.apiKey = config.apiKey;
            if (config.accessToken) this.accessToken = config.accessToken;
            if (config.settings) this.settings = { ...this.settings, ...config.settings };
        } catch (error) {
            console.error('Error saving config:', error);
        }
    }

    /**
     * Make HTTP request to MAMS API
     */
    async request(method, endpoint, options = {}) {
        const url = `${this.baseUrl.replace(/\/$/, '')}${endpoint}`;
        
        const headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'MAMS-FCPX/1.0',
            ...options.headers
        };

        // Add authentication
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        } else if (this.accessToken) {
            headers['Authorization'] = `Bearer ${this.accessToken}`;
        }

        const requestOptions = {
            method,
            headers,
            ...options
        };

        // Add body for non-GET requests
        if (method !== 'GET' && options.data) {
            requestOptions.body = JSON.stringify(options.data);
        }

        try {
            const response = await fetch(url, requestOptions);
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error(`Request failed: ${method} ${url}`, error);
            throw error;
        }
    }

    /**
     * Test connection to MAMS server
     */
    async testConnection() {
        try {
            await this.request('GET', '/api/v1/health');
            this.isConnected = true;
            return true;
        } catch (error) {
            this.isConnected = false;
            console.error('Connection test failed:', error);
            return false;
        }
    }

    /**
     * Login to MAMS server
     */
    async login(username, password) {
        try {
            const response = await this.request('POST', '/api/v1/auth/login', {
                data: { username, password }
            });
            
            if (response.access_token) {
                this.accessToken = response.access_token;
                this.saveConfig({ accessToken: response.access_token });
                this.isConnected = true;
                return true;
            }
            
            return false;
        } catch (error) {
            console.error('Login failed:', error);
            return false;
        }
    }

    /**
     * Logout from MAMS server
     */
    async logout() {
        try {
            if (this.accessToken) {
                await this.request('POST', '/api/v1/auth/logout');
            }
        } catch (error) {
            console.warn('Logout request failed:', error);
        } finally {
            this.accessToken = '';
            this.isConnected = false;
            this.saveConfig({ accessToken: '' });
        }
    }

    /**
     * Search for assets
     */
    async searchAssets(query = '', filters = {}, page = 1, limit = 20) {
        const params = new URLSearchParams({
            q: query,
            page: page.toString(),
            limit: limit.toString(),
            ...filters
        });

        try {
            const response = await this.request('GET', `/api/v1/assets/search?${params}`);
            return {
                assets: response.data || [],
                total: response.meta?.total || 0,
                page: response.meta?.page || 1,
                pages: response.meta?.pages || 1
            };
        } catch (error) {
            console.error('Asset search failed:', error);
            return { assets: [], total: 0, page: 1, pages: 1 };
        }
    }

    /**
     * Get asset details by ID
     */
    async getAsset(assetId) {
        try {
            const response = await this.request('GET', `/api/v1/assets/${assetId}`);
            return response.data || response;
        } catch (error) {
            console.error(`Failed to get asset ${assetId}:`, error);
            return null;
        }
    }

    /**
     * Get asset metadata
     */
    async getAssetMetadata(assetId) {
        try {
            const response = await this.request('GET', `/api/v1/assets/${assetId}/metadata`);
            return response.data || response;
        } catch (error) {
            console.error(`Failed to get metadata for asset ${assetId}:`, error);
            return {};
        }
    }

    /**
     * Download asset
     */
    async downloadAsset(assetId, quality = 'proxy') {
        try {
            const response = await this.request('GET', `/api/v1/assets/${assetId}/download`, {
                data: { quality }
            });
            
            if (response.url) {
                return {
                    url: response.url,
                    filename: response.filename,
                    size: response.size
                };
            }
            
            return null;
        } catch (error) {
            console.error(`Failed to download asset ${assetId}:`, error);
            return null;
        }
    }

    /**
     * Get asset proxy URL for streaming
     */
    async getProxyUrl(assetId) {
        try {
            const response = await this.request('GET', `/api/v1/assets/${assetId}/proxy`);
            return response.url || null;
        } catch (error) {
            console.error(`Failed to get proxy URL for asset ${assetId}:`, error);
            return null;
        }
    }

    /**
     * Upload asset to MAMS
     */
    async uploadAsset(file, metadata = {}) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('metadata', JSON.stringify(metadata));

            const headers = {};
            if (this.apiKey) {
                headers['X-API-Key'] = this.apiKey;
            } else if (this.accessToken) {
                headers['Authorization'] = `Bearer ${this.accessToken}`;
            }

            const response = await fetch(`${this.baseUrl}/api/v1/assets/upload`, {
                method: 'POST',
                headers,
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const result = await response.json();
            return result.data || result;
        } catch (error) {
            console.error('Asset upload failed:', error);
            throw error;
        }
    }

    /**
     * Update asset metadata
     */
    async updateAssetMetadata(assetId, metadata) {
        try {
            const response = await this.request('PATCH', `/api/v1/assets/${assetId}/metadata`, {
                data: metadata
            });
            return response.data || response;
        } catch (error) {
            console.error(`Failed to update metadata for asset ${assetId}:`, error);
            return false;
        }
    }

    /**
     * Create project in MAMS
     */
    async createProject(projectData) {
        try {
            const response = await this.request('POST', '/api/v1/projects', {
                data: projectData
            });
            return response.data || response;
        } catch (error) {
            console.error('Failed to create project:', error);
            return null;
        }
    }

    /**
     * Get list of projects
     */
    async getProjects(page = 1, limit = 50) {
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                limit: limit.toString()
            });

            const response = await this.request('GET', `/api/v1/projects?${params}`);
            return {
                projects: response.data || [],
                total: response.meta?.total || 0,
                page: response.meta?.page || 1,
                pages: response.meta?.pages || 1
            };
        } catch (error) {
            console.error('Failed to get projects:', error);
            return { projects: [], total: 0, page: 1, pages: 1 };
        }
    }

    /**
     * Sync project with MAMS
     */
    async syncProject(projectData) {
        try {
            const response = await this.request('POST', '/api/v1/projects/sync', {
                data: projectData
            });
            return response.success || response.status === 'success';
        } catch (error) {
            console.error('Failed to sync project:', error);
            return false;
        }
    }

    /**
     * Get collections
     */
    async getCollections() {
        try {
            const response = await this.request('GET', '/api/v1/collections');
            return response.data || [];
        } catch (error) {
            console.error('Failed to get collections:', error);
            return [];
        }
    }

    /**
     * Get keywords/tags
     */
    async getKeywords() {
        try {
            const response = await this.request('GET', '/api/v1/keywords');
            return response.data || [];
        } catch (error) {
            console.error('Failed to get keywords:', error);
            return [];
        }
    }

    /**
     * Download LUT file
     */
    async downloadLUT(lutName) {
        try {
            const response = await this.request('GET', `/api/v1/luts/${lutName}/download`);
            return response.url || null;
        } catch (error) {
            console.error(`Failed to download LUT ${lutName}:`, error);
            return null;
        }
    }

    /**
     * Get user profile
     */
    async getUserProfile() {
        try {
            const response = await this.request('GET', '/api/v1/auth/profile');
            return response.data || response;
        } catch (error) {
            console.error('Failed to get user profile:', error);
            return null;
        }
    }

    /**
     * Create event in MAMS
     */
    async createEvent(eventData) {
        try {
            const response = await this.request('POST', '/api/v1/events', {
                data: eventData
            });
            return response.data || response;
        } catch (error) {
            console.error('Failed to create event:', error);
            return null;
        }
    }

    /**
     * Export timeline to MAMS
     */
    async exportTimeline(timelineData) {
        try {
            const response = await this.request('POST', '/api/v1/timelines', {
                data: timelineData
            });
            return response.data || response;
        } catch (error) {
            console.error('Failed to export timeline:', error);
            return null;
        }
    }

    /**
     * Get server info
     */
    async getServerInfo() {
        try {
            const response = await this.request('GET', '/api/v1/info');
            return response.data || response;
        } catch (error) {
            console.error('Failed to get server info:', error);
            return null;
        }
    }

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Format duration from seconds
     */
    formatDuration(seconds) {
        if (!seconds || seconds <= 0) return '00:00:00';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        return [hours, minutes, secs]
            .map(v => v.toString().padStart(2, '0'))
            .join(':');
    }

    /**
     * Parse timecode to seconds
     */
    parseTimecode(timecode) {
        if (!timecode) return 0;
        
        const parts = timecode.split(':').map(Number);
        if (parts.length === 3) {
            return parts[0] * 3600 + parts[1] * 60 + parts[2];
        } else if (parts.length === 4) {
            // HH:MM:SS:FF format - ignore frames for now
            return parts[0] * 3600 + parts[1] * 60 + parts[2];
        }
        
        return 0;
    }

    /**
     * Get asset type icon
     */
    getAssetTypeIcon(type) {
        const icons = {
            video: 'icon-play',
            audio: 'icon-volume',
            image: 'icon-image',
            project: 'icon-folder',
            sequence: 'icon-film',
            timeline: 'icon-timeline'
        };
        
        return icons[type] || 'icon-file';
    }

    /**
     * Validate configuration
     */
    validateConfig() {
        const errors = [];
        
        if (!this.baseUrl) {
            errors.push('Server URL is required');
        } else {
            try {
                new URL(this.baseUrl);
            } catch {
                errors.push('Invalid server URL format');
            }
        }
        
        if (!this.apiKey && !this.accessToken) {
            errors.push('API key or access token is required');
        }
        
        return errors;
    }

    /**
     * Get connection status
     */
    getConnectionStatus() {
        return {
            connected: this.isConnected,
            serverUrl: this.baseUrl,
            hasAuth: !!(this.apiKey || this.accessToken)
        };
    }
}

// Export as global for use in extension
window.MAMSClient = MAMSClient;