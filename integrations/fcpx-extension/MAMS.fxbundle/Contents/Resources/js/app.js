/**
 * MAMS Final Cut Pro X Extension - Main Application
 * Handles UI interactions and coordinates between MAMS and FCPX APIs
 */

class MAMSExtensionApp {
    constructor() {
        this.mamsClient = new MAMSClient();
        this.fcpxApi = new FCPXApi();
        this.selectedAssets = new Set();
        this.currentSearchResults = [];
        this.currentPage = 1;
        this.totalPages = 1;
        this.isLoading = false;
        
        this.initialize();
    }

    /**
     * Initialize the application
     */
    async initialize() {
        this.setupEventListeners();
        this.setupFCPXEventListeners();
        this.updateConnectionStatus();
        this.loadSettings();
        
        // Test initial connection
        await this.testConnection();
    }

    /**
     * Setup UI event listeners
     */
    setupEventListeners() {
        // Search functionality
        document.getElementById('searchBtn').addEventListener('click', () => this.performSearch());
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });

        // Filter controls
        document.getElementById('clearFiltersBtn').addEventListener('click', () => this.clearFilters());
        document.getElementById('typeFilter').addEventListener('change', () => this.performSearch());
        document.getElementById('tagsFilter').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });

        // View controls
        document.getElementById('gridViewBtn').addEventListener('click', () => this.setViewMode('grid'));
        document.getElementById('listViewBtn').addEventListener('click', () => this.setViewMode('list'));

        // Header actions
        document.getElementById('refreshBtn').addEventListener('click', () => this.performSearch());
        document.getElementById('settingsBtn').addEventListener('click', () => this.showSettings());

        // Footer actions
        document.getElementById('importSelectedBtn').addEventListener('click', () => this.showImportModal());
        document.getElementById('syncProjectBtn').addEventListener('click', () => this.syncProject());

        // Modal controls
        this.setupModalEventListeners();

        // Load more
        document.getElementById('loadMoreBtn').addEventListener('click', () => this.loadMoreResults());
    }

    /**
     * Setup modal event listeners
     */
    setupModalEventListeners() {
        // Settings modal
        document.getElementById('closeSettingsBtn').addEventListener('click', () => this.hideModal('settingsModal'));
        document.getElementById('saveSettingsBtn').addEventListener('click', () => this.saveSettings());
        document.getElementById('testConnectionBtn').addEventListener('click', () => this.testConnection());

        // Preview modal
        document.getElementById('closePreviewBtn').addEventListener('click', () => this.hideModal('previewModal'));
        document.getElementById('importPreviewBtn').addEventListener('click', () => this.importPreviewAsset());
        document.getElementById('downloadPreviewBtn').addEventListener('click', () => this.downloadPreviewAsset());

        // Import modal
        document.getElementById('closeImportBtn').addEventListener('click', () => this.hideModal('importModal'));
        document.getElementById('startImportBtn').addEventListener('click', () => this.startImport());
        document.getElementById('cancelImportBtn').addEventListener('click', () => this.cancelImport());
        document.getElementById('targetEvent').addEventListener('change', (e) => {
            document.getElementById('newEventGroup').style.display = 
                e.target.value === 'new' ? 'block' : 'none';
        });

        // Click outside modal to close
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModal(modal.id);
                }
            });
        });
    }

    /**
     * Setup FCPX event listeners
     */
    setupFCPXEventListeners() {
        this.fcpxApi.addEventListener('libraryChanged', (e) => {
            console.log('Library changed:', e.detail);
            this.updateFCPXStatus();
        });

        this.fcpxApi.addEventListener('eventChanged', (e) => {
            console.log('Event changed:', e.detail);
            this.updateFCPXStatus();
        });

        this.fcpxApi.addEventListener('projectChanged', (e) => {
            console.log('Project changed:', e.detail);
            this.updateFCPXStatus();
        });
    }

    /**
     * Update connection status
     */
    updateConnectionStatus() {
        const statusElement = document.getElementById('connectionStatus');
        const statusText = statusElement.querySelector('.status-text');
        
        const mamsStatus = this.mamsClient.getConnectionStatus();
        const fcpxStatus = this.fcpxApi.getConnectionStatus();

        if (mamsStatus.connected && fcpxStatus.connected) {
            statusElement.className = 'connection-status connected';
            statusText.textContent = 'Connected';
        } else if (mamsStatus.connected || fcpxStatus.connected) {
            statusElement.className = 'connection-status connecting';
            statusText.textContent = 'Partially Connected';
        } else {
            statusElement.className = 'connection-status disconnected';
            statusText.textContent = 'Disconnected';
        }
    }

    /**
     * Update FCPX status information
     */
    updateFCPXStatus() {
        const fcpxStatus = this.fcpxApi.getConnectionStatus();
        console.log('FCPX Status:', fcpxStatus);
        // Update UI elements that show current FCPX context
    }

    /**
     * Perform asset search
     */
    async performSearch(page = 1) {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading(true);

        try {
            const query = document.getElementById('searchInput').value.trim();
            const type = document.getElementById('typeFilter').value;
            const tags = document.getElementById('tagsFilter').value.trim();

            const filters = {};
            if (type) filters.type = type;
            if (tags) filters.tags = tags.split(',').map(t => t.trim()).filter(t => t);

            const result = await this.mamsClient.searchAssets(query, filters, page, 20);
            
            if (page === 1) {
                this.currentSearchResults = result.assets;
                this.selectedAssets.clear();
            } else {
                this.currentSearchResults.push(...result.assets);
            }

            this.currentPage = result.page;
            this.totalPages = result.pages;

            this.displaySearchResults();
            this.updateResultsInfo(result.total);
            this.updateLoadMoreButton();
        } catch (error) {
            console.error('Search failed:', error);
            this.showNotification('Search failed. Please check your connection.', 'error');
        } finally {
            this.isLoading = false;
            this.showLoading(false);
        }
    }

    /**
     * Display search results
     */
    displaySearchResults() {
        const container = document.getElementById('assetContainer');
        const viewMode = container.classList.contains('grid-view') ? 'grid' : 'list';

        if (this.currentSearchResults.length === 0) {
            container.innerHTML = `
                <div class="no-results">
                    <svg class="icon icon-large">
                        <use href="#icon-search"></use>
                    </svg>
                    <p>No assets found. Try adjusting your search criteria.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.currentSearchResults
            .map(asset => this.createAssetCard(asset, viewMode))
            .join('');

        // Add event listeners to asset cards
        this.setupAssetCardListeners();
    }

    /**
     * Create asset card HTML
     */
    createAssetCard(asset, viewMode) {
        const isSelected = this.selectedAssets.has(asset.id);
        const duration = asset.duration ? this.mamsClient.formatDuration(asset.duration) : '';
        const fileSize = asset.file_size ? this.mamsClient.formatFileSize(asset.file_size) : '';
        
        return `
            <div class="asset-card ${viewMode}-item ${isSelected ? 'selected' : ''}" 
                 data-asset-id="${asset.id}">
                <div class="asset-selection">
                    <input type="checkbox" class="asset-checkbox" 
                           ${isSelected ? 'checked' : ''} 
                           data-asset-id="${asset.id}">
                </div>
                
                <div class="asset-thumbnail">
                    ${asset.thumbnail_url ? 
                        `<img src="${asset.thumbnail_url}" alt="${asset.name}">` : 
                        `<svg class="placeholder-icon"><use href="#${this.mamsClient.getAssetTypeIcon(asset.type)}"></use></svg>`
                    }
                    
                    <div class="asset-type-indicator ${asset.type}">${asset.type}</div>
                    
                    ${duration ? `<div class="asset-duration">${duration}</div>` : ''}
                    
                    <div class="asset-actions">
                        <button class="asset-action-btn preview-btn" data-asset-id="${asset.id}" title="Preview">
                            <svg class="icon"><use href="#icon-search"></use></svg>
                        </button>
                    </div>
                </div>
                
                <div class="asset-info">
                    <div class="asset-title" title="${asset.name}">${asset.name}</div>
                    <div class="asset-metadata">
                        ${asset.resolution ? `<div class="metadata-item">${asset.resolution}</div>` : ''}
                        ${fileSize ? `<div class="metadata-item">${fileSize}</div>` : ''}
                        ${asset.created_at ? `<div class="metadata-item">${new Date(asset.created_at).toLocaleDateString()}</div>` : ''}
                    </div>
                    ${asset.tags && asset.tags.length > 0 ? `
                        <div class="asset-tags">
                            ${asset.tags.slice(0, 3).map(tag => `<span class="asset-tag">${tag}</span>`).join('')}
                            ${asset.tags.length > 3 ? `<span class="asset-tag">+${asset.tags.length - 3}</span>` : ''}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Setup asset card event listeners
     */
    setupAssetCardListeners() {
        // Asset selection
        document.querySelectorAll('.asset-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const assetId = e.target.dataset.assetId;
                if (e.target.checked) {
                    this.selectedAssets.add(assetId);
                } else {
                    this.selectedAssets.delete(assetId);
                }
                this.updateSelectionUI();
            });
        });

        // Asset card clicks
        document.querySelectorAll('.asset-card').forEach(card => {
            card.addEventListener('click', (e) => {
                // Skip if clicking on checkbox or action buttons
                if (e.target.type === 'checkbox' || e.target.closest('.asset-action-btn')) {
                    return;
                }
                
                const assetId = card.dataset.assetId;
                this.showAssetPreview(assetId);
            });
        });

        // Preview buttons
        document.querySelectorAll('.preview-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const assetId = btn.dataset.assetId;
                this.showAssetPreview(assetId);
            });
        });
    }

    /**
     * Update selection UI
     */
    updateSelectionUI() {
        const count = this.selectedAssets.size;
        document.getElementById('selectedCount').textContent = count;
        document.getElementById('importSelectedBtn').disabled = count === 0;
    }

    /**
     * Show asset preview modal
     */
    async showAssetPreview(assetId) {
        const asset = this.currentSearchResults.find(a => a.id === assetId);
        if (!asset) return;

        const modal = document.getElementById('previewModal');
        const title = document.getElementById('previewTitle');
        const media = document.getElementById('previewMedia');
        const details = document.getElementById('previewDetails');

        title.textContent = asset.name;

        // Setup preview media
        if (asset.proxy_url) {
            if (asset.type === 'video') {
                media.innerHTML = `<video controls><source src="${asset.proxy_url}" type="video/mp4"></video>`;
            } else if (asset.type === 'audio') {
                media.innerHTML = `<audio controls><source src="${asset.proxy_url}" type="audio/mpeg"></audio>`;
            } else if (asset.type === 'image') {
                media.innerHTML = `<img src="${asset.proxy_url}" alt="${asset.name}">`;
            }
        } else {
            media.innerHTML = `
                <div class="preview-placeholder">
                    <svg class="icon"><use href="#${this.mamsClient.getAssetTypeIcon(asset.type)}"></use></svg>
                    <p>Preview not available</p>
                </div>
            `;
        }

        // Setup asset details
        details.innerHTML = `
            <div class="detail-section">
                <h4>Basic Information</h4>
                <ul class="detail-list">
                    <li class="detail-item">
                        <span class="detail-label">Type:</span>
                        <span class="detail-value">${asset.type}</span>
                    </li>
                    <li class="detail-item">
                        <span class="detail-label">Duration:</span>
                        <span class="detail-value">${asset.duration ? this.mamsClient.formatDuration(asset.duration) : 'N/A'}</span>
                    </li>
                    <li class="detail-item">
                        <span class="detail-label">File Size:</span>
                        <span class="detail-value">${asset.file_size ? this.mamsClient.formatFileSize(asset.file_size) : 'N/A'}</span>
                    </li>
                    <li class="detail-item">
                        <span class="detail-label">Resolution:</span>
                        <span class="detail-value">${asset.resolution || 'N/A'}</span>
                    </li>
                    <li class="detail-item">
                        <span class="detail-label">Created:</span>
                        <span class="detail-value">${asset.created_at ? new Date(asset.created_at).toLocaleString() : 'N/A'}</span>
                    </li>
                </ul>
            </div>
            
            ${asset.description ? `
                <div class="detail-section">
                    <h4>Description</h4>
                    <p>${asset.description}</p>
                </div>
            ` : ''}
            
            ${asset.tags && asset.tags.length > 0 ? `
                <div class="detail-section">
                    <h4>Keywords</h4>
                    <div class="asset-tags">
                        ${asset.tags.map(tag => `<span class="asset-tag">${tag}</span>`).join('')}
                    </div>
                </div>
            ` : ''}
        `;

        // Store current asset for import/download
        modal.dataset.assetId = assetId;
        this.showModal('previewModal');
    }

    /**
     * Import preview asset
     */
    async importPreviewAsset() {
        const modal = document.getElementById('previewModal');
        const assetId = modal.dataset.assetId;
        
        if (assetId) {
            this.selectedAssets.clear();
            this.selectedAssets.add(assetId);
            this.hideModal('previewModal');
            this.showImportModal();
        }
    }

    /**
     * Download preview asset
     */
    async downloadPreviewAsset() {
        const modal = document.getElementById('previewModal');
        const assetId = modal.dataset.assetId;
        
        if (assetId) {
            await this.downloadAsset(assetId);
        }
    }

    /**
     * Show import modal
     */
    showImportModal() {
        if (this.selectedAssets.size === 0) {
            this.showNotification('No assets selected', 'warning');
            return;
        }

        const modal = document.getElementById('importModal');
        const assetsList = document.getElementById('importAssetsList');
        
        // Populate selected assets
        const selectedAssetData = this.currentSearchResults.filter(a => this.selectedAssets.has(a.id));
        assetsList.innerHTML = selectedAssetData.map(asset => `
            <div class="import-asset-item">
                <div class="import-asset-thumbnail">
                    <svg class="icon"><use href="#${this.mamsClient.getAssetTypeIcon(asset.type)}"></use></svg>
                </div>
                <div class="import-asset-info">
                    <div class="import-asset-name">${asset.name}</div>
                    <div class="import-asset-meta">${asset.type} • ${asset.duration ? this.mamsClient.formatDuration(asset.duration) : 'Unknown duration'}</div>
                </div>
            </div>
        `).join('');

        this.showModal('importModal');
    }

    /**
     * Start import process
     */
    async startImport() {
        const targetEvent = document.getElementById('targetEvent').value;
        const newEventName = document.getElementById('newEventName').value.trim();
        const quality = document.getElementById('importQuality').value;
        const importMetadata = document.getElementById('importMetadata').checked;

        // Validation
        if (targetEvent === 'new' && !newEventName) {
            this.showNotification('Please enter a name for the new event', 'warning');
            return;
        }

        // Show progress
        document.getElementById('importProgress').style.display = 'block';
        document.getElementById('startImportBtn').disabled = true;

        try {
            // Create new event if needed
            let event = null;
            if (targetEvent === 'new') {
                event = await this.fcpxApi.createEvent(newEventName);
                this.showNotification(`Created new event: ${newEventName}`, 'success');
            }

            // Import selected assets
            const selectedAssetData = this.currentSearchResults.filter(a => this.selectedAssets.has(a.id));
            let successCount = 0;

            for (const asset of selectedAssetData) {
                try {
                    const downloadInfo = await this.mamsClient.downloadAsset(asset.id, quality);
                    if (downloadInfo && downloadInfo.url) {
                        await this.fcpxApi.importAssetFromMAMS(asset, downloadInfo.url, event, {
                            createOptimizedMedia: quality === 'optimized',
                            createProxyMedia: quality === 'proxy',
                            importMetadata
                        });
                        successCount++;
                        
                        // Update progress
                        const progress = (successCount / selectedAssetData.length) * 100;
                        document.querySelector('.progress-fill').style.width = `${progress}%`;
                        document.querySelector('.progress-text').textContent = 
                            `Importing... ${successCount}/${selectedAssetData.length}`;
                    }
                } catch (error) {
                    console.error(`Failed to import asset ${asset.name}:`, error);
                }
            }

            this.showNotification(`Successfully imported ${successCount}/${selectedAssetData.length} assets`, 'success');
            
            // Clear selection and close modal
            this.selectedAssets.clear();
            this.updateSelectionUI();
            this.hideModal('importModal');

        } catch (error) {
            console.error('Import failed:', error);
            this.showNotification('Import failed. Please try again.', 'error');
        } finally {
            // Reset UI
            document.getElementById('importProgress').style.display = 'none';
            document.getElementById('startImportBtn').disabled = false;
            document.querySelector('.progress-fill').style.width = '0%';
            document.querySelector('.progress-text').textContent = 'Importing...';
        }
    }

    /**
     * Cancel import
     */
    cancelImport() {
        this.hideModal('importModal');
    }

    /**
     * Sync project with MAMS
     */
    async syncProject() {
        if (!this.fcpxApi.isConnected) {
            this.showNotification('FCPX not connected', 'error');
            return;
        }

        try {
            const projectData = await this.fcpxApi.exportProjectForMAMS();
            if (projectData) {
                const success = await this.mamsClient.syncProject(projectData);
                if (success) {
                    this.showNotification('Project synchronized with MAMS', 'success');
                } else {
                    this.showNotification('Failed to sync project', 'error');
                }
            } else {
                this.showNotification('No project to sync', 'warning');
            }
        } catch (error) {
            console.error('Project sync failed:', error);
            this.showNotification('Project sync failed', 'error');
        }
    }

    /**
     * Download asset
     */
    async downloadAsset(assetId) {
        try {
            const downloadInfo = await this.mamsClient.downloadAsset(assetId, 'original');
            if (downloadInfo && downloadInfo.url) {
                // Create download link
                const link = document.createElement('a');
                link.href = downloadInfo.url;
                link.download = downloadInfo.filename || 'asset';
                link.click();
                
                this.showNotification('Download started', 'success');
            } else {
                this.showNotification('Download failed', 'error');
            }
        } catch (error) {
            console.error('Download failed:', error);
            this.showNotification('Download failed', 'error');
        }
    }

    /**
     * Clear search filters
     */
    clearFilters() {
        document.getElementById('searchInput').value = '';
        document.getElementById('typeFilter').value = '';
        document.getElementById('tagsFilter').value = '';
        this.performSearch();
    }

    /**
     * Set view mode (grid/list)
     */
    setViewMode(mode) {
        const container = document.getElementById('assetContainer');
        const gridBtn = document.getElementById('gridViewBtn');
        const listBtn = document.getElementById('listViewBtn');

        if (mode === 'grid') {
            container.className = 'asset-container grid-view';
            gridBtn.classList.add('active');
            listBtn.classList.remove('active');
        } else {
            container.className = 'asset-container list-view';
            listBtn.classList.add('active');
            gridBtn.classList.remove('active');
        }

        this.displaySearchResults();
    }

    /**
     * Load more search results
     */
    async loadMoreResults() {
        if (this.currentPage < this.totalPages && !this.isLoading) {
            await this.performSearch(this.currentPage + 1);
        }
    }

    /**
     * Update results info
     */
    updateResultsInfo(total) {
        document.getElementById('resultsCount').textContent = 
            `${total} asset${total !== 1 ? 's' : ''} found`;
    }

    /**
     * Update load more button
     */
    updateLoadMoreButton() {
        const container = document.getElementById('loadMoreContainer');
        if (this.currentPage < this.totalPages) {
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    }

    /**
     * Show loading state
     */
    showLoading(show) {
        const container = document.getElementById('assetContainer');
        if (show) {
            container.innerHTML = `
                <div class="loading">
                    <div class="loading-spinner"></div>
                    <span>Searching assets...</span>
                </div>
            `;
        }
    }

    /**
     * Show settings modal
     */
    showSettings() {
        const form = document.getElementById('settingsForm');
        const config = JSON.parse(localStorage.getItem('mams_config') || '{}');
        
        // Populate form with current settings
        form.serverUrl.value = config.serverUrl || '';
        form.apiKey.value = config.apiKey || '';
        form.username.value = config.username || '';
        form.autoLogin.checked = config.autoLogin || false;
        form.downloadQuality.value = config.downloadQuality || 'proxy';
        form.importLocation.value = config.importLocation || 'current_event';
        form.syncMetadata.checked = config.syncMetadata !== false;
        form.createKeywords.checked = config.createKeywords !== false;
        form.cacheSize.value = config.cacheSize || '10GB';
        form.resultsPerPage.value = config.resultsPerPage || '20';

        this.showModal('settingsModal');
    }

    /**
     * Save settings
     */
    async saveSettings() {
        const form = document.getElementById('settingsForm');
        const formData = new FormData(form);
        
        const config = {
            serverUrl: formData.get('serverUrl'),
            apiKey: formData.get('apiKey'),
            username: formData.get('username'),
            autoLogin: formData.has('autoLogin'),
            downloadQuality: formData.get('downloadQuality'),
            importLocation: formData.get('importLocation'),
            syncMetadata: formData.has('syncMetadata'),
            createKeywords: formData.has('createKeywords'),
            cacheSize: formData.get('cacheSize'),
            resultsPerPage: formData.get('resultsPerPage')
        };

        this.mamsClient.saveConfig(config);
        this.showNotification('Settings saved', 'success');
        this.hideModal('settingsModal');
        
        // Update connection status
        await this.testConnection();
    }

    /**
     * Load settings
     */
    loadSettings() {
        const config = JSON.parse(localStorage.getItem('mams_config') || '{}');
        
        // Auto-login if enabled
        if (config.autoLogin && config.username) {
            // Would need password storage for full auto-login
            console.log('Auto-login enabled for:', config.username);
        }
    }

    /**
     * Test connection to MAMS
     */
    async testConnection() {
        try {
            const connected = await this.mamsClient.testConnection();
            if (connected) {
                this.showNotification('Connection successful', 'success');
            } else {
                this.showNotification('Connection failed', 'error');
            }
        } catch (error) {
            console.error('Connection test error:', error);
            this.showNotification('Connection failed', 'error');
        } finally {
            this.updateConnectionStatus();
        }
    }

    /**
     * Show modal
     */
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.add('show');
    }

    /**
     * Hide modal
     */
    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.remove('show');
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        notification.innerHTML = `
            <div class="notification-header">
                <span class="notification-title">${type.charAt(0).toUpperCase() + type.slice(1)}</span>
                <button class="notification-close">
                    <svg class="icon"><use href="#icon-close"></use></svg>
                </button>
            </div>
            <div class="notification-body">${message}</div>
        `;

        document.body.appendChild(notification);

        // Show notification
        setTimeout(() => notification.classList.add('show'), 100);

        // Auto-hide after 5 seconds
        const hideTimeout = setTimeout(() => this.hideNotification(notification), 5000);

        // Close button
        notification.querySelector('.notification-close').addEventListener('click', () => {
            clearTimeout(hideTimeout);
            this.hideNotification(notification);
        });
    }

    /**
     * Hide notification
     */
    hideNotification(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mamsApp = new MAMSExtensionApp();
});