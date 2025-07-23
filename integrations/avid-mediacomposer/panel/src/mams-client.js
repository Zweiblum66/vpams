/**
 * MAMS Client for Avid Panel
 * Handles communication with MAMS server
 */

class MAMSClient {
    constructor() {
        this.baseUrl = localStorage.getItem('mams_server_url') || '';
        this.apiKey = localStorage.getItem('mams_api_key') || '';
        this.connected = false;
    }
    
    setServerUrl(url) {
        this.baseUrl = url.replace(/\/$/, ''); // Remove trailing slash
        localStorage.setItem('mams_server_url', this.baseUrl);
    }
    
    setApiKey(key) {
        this.apiKey = key;
        localStorage.setItem('mams_api_key', this.apiKey);
    }
    
    async testConnection() {
        try {
            const response = await this.request('/api/v1/health');
            this.connected = response.status === 'healthy';
            return this.connected;
        } catch (error) {
            this.connected = false;
            return false;
        }
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': this.apiKey
            }
        };
        
        const response = await fetch(url, {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return response.json();
    }
    
    // Asset operations
    
    async searchAssets(query, filters = {}) {
        const params = new URLSearchParams({
            q: query,
            ...filters
        });
        
        return this.request(`/api/v1/assets/search?${params}`);
    }
    
    async getAsset(assetId) {
        return this.request(`/api/v1/assets/${assetId}`);
    }
    
    async getAssetMetadata(assetId) {
        return this.request(`/api/v1/assets/${assetId}/metadata`);
    }
    
    async getProxyUrl(assetId) {
        const response = await this.request(`/api/v1/assets/${assetId}/proxy`);
        return response.url;
    }
    
    async getDownloadUrl(assetId, quality = 'original') {
        const response = await this.request(`/api/v1/assets/${assetId}/download?quality=${quality}`);
        return response.url;
    }
    
    // Project operations
    
    async getProjects() {
        return this.request('/api/v1/projects');
    }
    
    async getProjectAssets(projectId) {
        return this.request(`/api/v1/projects/${projectId}/assets`);
    }
    
    async syncProject(projectData) {
        return this.request('/api/v1/projects/sync', {
            method: 'POST',
            body: JSON.stringify(projectData)
        });
    }
    
    // Collection operations
    
    async getCollections() {
        return this.request('/api/v1/collections');
    }
    
    async getCollectionAssets(collectionId) {
        return this.request(`/api/v1/collections/${collectionId}/assets`);
    }
    
    // Format asset data for display
    
    formatAsset(asset) {
        return {
            id: asset.id,
            name: asset.name,
            type: asset.type,
            thumbnailUrl: asset.thumbnail_url || this.getDefaultThumbnail(asset.type),
            duration: this.formatDuration(asset.metadata?.duration),
            size: this.formatFileSize(asset.size),
            format: asset.metadata?.format || 'Unknown',
            resolution: asset.metadata?.resolution || '',
            created: new Date(asset.created_at).toLocaleDateString(),
            tags: asset.metadata?.tags || []
        };
    }
    
    getDefaultThumbnail(type) {
        const thumbnails = {
            video: 'assets/video-thumbnail.svg',
            audio: 'assets/audio-thumbnail.svg',
            image: 'assets/image-thumbnail.svg',
            project: 'assets/project-thumbnail.svg'
        };
        return thumbnails[type] || 'assets/default-thumbnail.svg';
    }
    
    formatDuration(seconds) {
        if (!seconds) return '';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
    
    formatFileSize(bytes) {
        if (!bytes) return '';
        
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let size = bytes;
        let unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }
}

// Create global instance
window.MAMSClient = new MAMSClient();