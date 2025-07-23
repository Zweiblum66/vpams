/**
 * MAMS Panel Main Application
 * Handles UI interactions and coordinates between Avid and MAMS
 */

class MAMSPanel {
    constructor() {
        this.currentView = 'grid';
        this.currentAssets = [];
        this.selectedAsset = null;
        this.filters = {
            type: '',
            dateFrom: '',
            dateTo: '',
            tags: []
        };
        
        this.initializeUI();
        this.bindEvents();
        this.checkConnection();
    }
    
    initializeUI() {
        // Load saved settings
        const serverUrl = localStorage.getItem('mams_server_url');
        const apiKey = localStorage.getItem('mams_api_key');
        
        if (serverUrl) {
            document.getElementById('server-url').value = serverUrl;
            MAMSClient.setServerUrl(serverUrl);
        }
        
        if (apiKey) {
            document.getElementById('api-key').value = apiKey;
            MAMSClient.setApiKey(apiKey);
        }
    }
    
    bindEvents() {
        // Search
        document.getElementById('search-button').addEventListener('click', () => this.performSearch());
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        
        // Filters
        document.getElementById('filter-button').addEventListener('click', () => this.toggleFilters());
        document.getElementById('apply-filters').addEventListener('click', () => this.applyFilters());
        document.getElementById('clear-filters').addEventListener('click', () => this.clearFilters());
        
        // View toggle
        document.getElementById('grid-view').addEventListener('click', () => this.setView('grid'));
        document.getElementById('list-view').addEventListener('click', () => this.setView('list'));
        
        // Settings
        document.getElementById('settings-button').addEventListener('click', () => this.showSettings());
        document.getElementById('save-settings').addEventListener('click', () => this.saveSettings());
        document.getElementById('cancel-settings').addEventListener('click', () => this.hideSettings());
        
        // Other actions
        document.getElementById('sync-project').addEventListener('click', () => this.syncProject());
        document.getElementById('help-button').addEventListener('click', () => this.showHelp());
        
        // Modal close
        document.querySelector('.close').addEventListener('click', () => this.closePreview());
        document.getElementById('preview-modal').addEventListener('click', (e) => {
            if (e.target.id === 'preview-modal') this.closePreview();
        });
    }
    
    async checkConnection() {
        const connected = await MAMSClient.testConnection();
        this.updateConnectionStatus(connected);
        
        if (!connected && MAMSClient.baseUrl) {
            this.showMessage('Unable to connect to MAMS server', 'error');
        }
    }
    
    updateConnectionStatus(connected) {
        const indicator = document.querySelector('.status-indicator');
        const text = document.querySelector('.status-text');
        
        if (connected) {
            indicator.classList.add('connected');
            text.textContent = 'Connected';
        } else {
            indicator.classList.remove('connected');
            text.textContent = 'Disconnected';
        }
    }
    
    async performSearch() {
        const query = document.getElementById('search-input').value.trim();
        if (!query) return;
        
        this.showLoading(true);
        
        try {
            const response = await MAMSClient.searchAssets(query, this.filters);
            this.displayResults(response.data || []);
        } catch (error) {
            this.showMessage('Search failed: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    displayResults(assets) {
        this.currentAssets = assets;
        const container = document.getElementById('results');
        container.innerHTML = '';
        
        if (assets.length === 0) {
            container.innerHTML = '<p class="no-results">No assets found</p>';
            return;
        }
        
        assets.forEach(asset => {
            const formatted = MAMSClient.formatAsset(asset);
            const element = this.createAssetElement(formatted);
            container.appendChild(element);
        });
    }
    
    createAssetElement(asset) {
        const div = document.createElement('div');
        div.className = 'asset-item';
        div.dataset.assetId = asset.id;
        
        div.innerHTML = `
            <div class="asset-thumbnail">
                <img src="${asset.thumbnailUrl}" alt="${asset.name}" />
            </div>
            <div class="asset-info">
                <div class="asset-name">${asset.name}</div>
                <div class="asset-meta">
                    ${asset.type} • ${asset.size}
                    ${asset.duration ? ' • ' + asset.duration : ''}
                </div>
            </div>
        `;
        
        div.addEventListener('click', () => this.previewAsset(asset));
        div.addEventListener('dblclick', () => this.importAsset(asset));
        
        return div;
    }
    
    async previewAsset(asset) {
        this.selectedAsset = asset;
        const modal = document.getElementById('preview-modal');
        const mediaContainer = document.getElementById('preview-media');
        const title = document.getElementById('preview-title');
        const metadata = document.getElementById('preview-metadata');
        
        title.textContent = asset.name;
        
        // Clear previous content
        mediaContainer.innerHTML = '';
        metadata.innerHTML = '';
        
        // Load preview based on type
        if (asset.type === 'video') {
            const proxyUrl = await MAMSClient.getProxyUrl(asset.id);
            mediaContainer.innerHTML = `
                <video controls autoplay>
                    <source src="${proxyUrl}" type="video/mp4">
                </video>
            `;
        } else if (asset.type === 'audio') {
            const proxyUrl = await MAMSClient.getProxyUrl(asset.id);
            mediaContainer.innerHTML = `
                <audio controls autoplay>
                    <source src="${proxyUrl}" type="audio/mp3">
                </audio>
            `;
        } else if (asset.type === 'image') {
            mediaContainer.innerHTML = `<img src="${asset.thumbnailUrl}" alt="${asset.name}" />`;
        }
        
        // Display metadata
        const fullAsset = await MAMSClient.getAsset(asset.id);
        this.displayMetadata(fullAsset);
        
        // Bind import actions
        document.getElementById('import-asset').onclick = () => this.importAsset(asset);
        document.getElementById('link-asset').onclick = () => this.linkAsset(asset);
        
        modal.style.display = 'block';
    }
    
    displayMetadata(asset) {
        const container = document.getElementById('preview-metadata');
        const metadata = asset.metadata || {};
        
        const fields = [
            { label: 'Format', value: metadata.format },
            { label: 'Resolution', value: metadata.resolution },
            { label: 'Frame Rate', value: metadata.framerate },
            { label: 'Duration', value: MAMSClient.formatDuration(metadata.duration) },
            { label: 'Size', value: MAMSClient.formatFileSize(asset.size) },
            { label: 'Created', value: new Date(asset.created_at).toLocaleString() },
            { label: 'Tags', value: (metadata.tags || []).join(', ') }
        ];
        
        fields.forEach(field => {
            if (field.value) {
                const div = document.createElement('div');
                div.className = 'metadata-item';
                div.innerHTML = `
                    <span class="metadata-label">${field.label}:</span>
                    <span class="metadata-value">${field.value}</span>
                `;
                container.appendChild(div);
            }
        });
    }
    
    async importAsset(asset) {
        try {
            const currentBin = await AvidAPI.getCurrentBin();
            const downloadUrl = await MAMSClient.getDownloadUrl(asset.id);
            
            const result = await AvidAPI.importAsset(downloadUrl, currentBin.path, {
                name: asset.name,
                copyLocal: true
            });
            
            if (result.success) {
                this.showMessage(`Imported "${asset.name}" successfully`, 'success');
                this.closePreview();
            } else {
                throw new Error('Import failed');
            }
        } catch (error) {
            this.showMessage('Failed to import asset: ' + error.message, 'error');
        }
    }
    
    async linkAsset(asset) {
        try {
            const currentBin = await AvidAPI.getCurrentBin();
            const amaUrl = `mams://asset/${asset.id}`;
            
            const result = await AvidAPI.createAMALink(amaUrl, currentBin.path);
            
            if (result.success) {
                this.showMessage(`Linked "${asset.name}" as AMA`, 'success');
                this.closePreview();
            } else {
                throw new Error('Link creation failed');
            }
        } catch (error) {
            this.showMessage('Failed to create AMA link: ' + error.message, 'error');
        }
    }
    
    closePreview() {
        document.getElementById('preview-modal').style.display = 'none';
        this.selectedAsset = null;
    }
    
    setView(view) {
        this.currentView = view;
        const container = document.getElementById('results');
        
        document.getElementById('grid-view').classList.toggle('active', view === 'grid');
        document.getElementById('list-view').classList.toggle('active', view === 'list');
        
        container.className = `results ${view}-view`;
    }
    
    toggleFilters() {
        const panel = document.getElementById('filter-panel');
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
    
    applyFilters() {
        this.filters = {
            type: document.getElementById('filter-type').value,
            dateFrom: document.getElementById('filter-date-from').value,
            dateTo: document.getElementById('filter-date-to').value,
            tags: document.getElementById('filter-tags').value.split(',').map(t => t.trim()).filter(t => t)
        };
        
        this.toggleFilters();
        this.performSearch();
    }
    
    clearFilters() {
        document.getElementById('filter-type').value = '';
        document.getElementById('filter-date-from').value = '';
        document.getElementById('filter-date-to').value = '';
        document.getElementById('filter-tags').value = '';
        
        this.filters = {
            type: '',
            dateFrom: '',
            dateTo: '',
            tags: []
        };
    }
    
    showSettings() {
        document.getElementById('settings-panel').style.display = 'block';
    }
    
    hideSettings() {
        document.getElementById('settings-panel').style.display = 'none';
    }
    
    async saveSettings() {
        const serverUrl = document.getElementById('server-url').value;
        const apiKey = document.getElementById('api-key').value;
        
        MAMSClient.setServerUrl(serverUrl);
        MAMSClient.setApiKey(apiKey);
        
        const connected = await MAMSClient.testConnection();
        this.updateConnectionStatus(connected);
        
        if (connected) {
            this.showMessage('Settings saved successfully', 'success');
            this.hideSettings();
        } else {
            this.showMessage('Failed to connect with these settings', 'error');
        }
    }
    
    async syncProject() {
        try {
            const project = await AvidAPI.getCurrentProject();
            const result = await MAMSClient.syncProject({
                name: project.name,
                path: project.path,
                timestamp: new Date().toISOString()
            });
            
            this.showMessage('Project synced successfully', 'success');
        } catch (error) {
            this.showMessage('Failed to sync project: ' + error.message, 'error');
        }
    }
    
    showHelp() {
        window.open('https://docs.mams.io/avid', '_blank');
    }
    
    showLoading(show) {
        document.getElementById('loading').style.display = show ? 'flex' : 'none';
    }
    
    showMessage(message, type = 'info') {
        // Use Avid's message system if available
        if (AvidAPI.isAvailable) {
            AvidAPI.showMessage(message, type);
        } else {
            // Fallback to console
            console[type === 'error' ? 'error' : 'log'](message);
        }
    }
}

// Initialize panel when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.mamsPanel = new MAMSPanel();
});