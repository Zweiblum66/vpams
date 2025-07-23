import axios, { AxiosInstance } from 'axios';
import { Asset, User, SearchParams, UploadProgress, ExportSettings } from '../types';

export class MAMSClient {
  private static instance: MAMSClient;
  private api: AxiosInstance;
  private wsConnection: WebSocket | null = null;
  private config: {
    endpoint: string;
    apiKey?: string;
    token?: string;
  };

  private constructor() {
    // Load configuration
    this.config = this.loadConfig();
    
    // Initialize axios instance
    this.api = axios.create({
      baseURL: this.config.endpoint,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth interceptor
    this.api.interceptors.request.use((config) => {
      if (this.config.token) {
        config.headers.Authorization = `Bearer ${this.config.token}`;
      } else if (this.config.apiKey) {
        config.headers['X-API-Key'] = this.config.apiKey;
      }
      return config;
    });

    // Add response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.handleAuthError();
        }
        return Promise.reject(error);
      }
    );
  }

  public static getInstance(): MAMSClient {
    if (!MAMSClient.instance) {
      MAMSClient.instance = new MAMSClient();
    }
    return MAMSClient.instance;
  }

  // Configuration
  private loadConfig() {
    const saved = localStorage.getItem('mams_config');
    if (saved) {
      return JSON.parse(saved);
    }
    return {
      endpoint: 'http://localhost:8000/api/v1',
    };
  }

  public saveConfig(config: Partial<typeof this.config>) {
    this.config = { ...this.config, ...config };
    localStorage.setItem('mams_config', JSON.stringify(this.config));
    
    // Update axios base URL if endpoint changed
    if (config.endpoint) {
      this.api.defaults.baseURL = config.endpoint;
    }
  }

  // Authentication
  public async login(username: string, password: string): Promise<User> {
    const response = await this.api.post('/auth/login', { username, password });
    this.config.token = response.data.access_token;
    this.saveConfig(this.config);
    
    // Connect WebSocket for real-time updates
    this.connectWebSocket();
    
    return response.data.user;
  }

  public async logout(): Promise<void> {
    try {
      await this.api.post('/auth/logout');
    } finally {
      this.config.token = undefined;
      this.saveConfig(this.config);
      this.disconnectWebSocket();
    }
  }

  public async getCurrentUser(): Promise<User> {
    const response = await this.api.get('/auth/me');
    return response.data;
  }

  // Asset Operations
  public async searchAssets(params: SearchParams): Promise<{ assets: Asset[]; total: number }> {
    const response = await this.api.get('/assets/search', { params });
    return response.data;
  }

  public async getAsset(assetId: string): Promise<Asset> {
    const response = await this.api.get(`/assets/${assetId}`);
    return response.data;
  }

  public async getAssetMetadata(assetId: string): Promise<any> {
    const response = await this.api.get(`/assets/${assetId}/metadata`);
    return response.data;
  }

  public async downloadAsset(assetId: string, quality: 'proxy' | 'high' = 'proxy'): Promise<string> {
    // Get download URL
    const response = await this.api.get(`/assets/${assetId}/download`, {
      params: { quality },
    });
    
    const downloadUrl = response.data.url;
    const filename = response.data.filename;
    
    // Download to local cache
    const localPath = await this.downloadFile(downloadUrl, filename);
    
    // Track in local database
    this.trackDownload(assetId, localPath, quality);
    
    return localPath;
  }

  public async uploadAsset(file: File, metadata: any, onProgress?: (progress: UploadProgress) => void): Promise<Asset> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('metadata', JSON.stringify(metadata));

    const response = await this.api.post('/assets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          onProgress({
            loaded: progressEvent.loaded,
            total: progressEvent.total,
            percentage: Math.round((progressEvent.loaded * 100) / progressEvent.total),
          });
        }
      },
    });

    return response.data;
  }

  public async updateAssetMetadata(assetId: string, metadata: any): Promise<Asset> {
    const response = await this.api.patch(`/assets/${assetId}/metadata`, metadata);
    return response.data;
  }

  // Project Sync
  public async syncProject(projectData: any): Promise<void> {
    await this.api.post('/projects/sync', projectData);
  }

  public async getProjectAssets(projectId: string): Promise<Asset[]> {
    const response = await this.api.get(`/projects/${projectId}/assets`);
    return response.data;
  }

  public async exportToMAMS(exportSettings: ExportSettings): Promise<{ jobId: string }> {
    const response = await this.api.post('/exports', exportSettings);
    return response.data;
  }

  public async getExportStatus(jobId: string): Promise<any> {
    const response = await this.api.get(`/exports/${jobId}/status`);
    return response.data;
  }

  // Collections
  public async getCollections(): Promise<any[]> {
    const response = await this.api.get('/collections');
    return response.data;
  }

  public async createCollection(name: string, assetIds: string[]): Promise<any> {
    const response = await this.api.post('/collections', { name, assetIds });
    return response.data;
  }

  // WebSocket Connection
  private connectWebSocket() {
    if (this.wsConnection) {
      return;
    }

    const wsUrl = this.config.endpoint.replace(/^http/, 'ws') + '/ws';
    this.wsConnection = new WebSocket(wsUrl);

    this.wsConnection.onopen = () => {
      console.log('WebSocket connected');
      // Authenticate WebSocket connection
      this.wsConnection?.send(JSON.stringify({
        type: 'auth',
        token: this.config.token,
      }));
    };

    this.wsConnection.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleWebSocketMessage(message);
    };

    this.wsConnection.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.wsConnection.onclose = () => {
      console.log('WebSocket disconnected');
      this.wsConnection = null;
      
      // Attempt to reconnect after delay
      if (this.config.token) {
        setTimeout(() => this.connectWebSocket(), 5000);
      }
    };
  }

  private disconnectWebSocket() {
    if (this.wsConnection) {
      this.wsConnection.close();
      this.wsConnection = null;
    }
  }

  private handleWebSocketMessage(message: any) {
    switch (message.type) {
      case 'asset.updated':
        // Notify UI of asset update
        window.dispatchEvent(new CustomEvent('mams:asset:updated', { detail: message.data }));
        break;
      
      case 'export.complete':
        // Notify UI of export completion
        window.dispatchEvent(new CustomEvent('mams:export:complete', { detail: message.data }));
        break;
      
      case 'project.synced':
        // Notify UI of project sync
        window.dispatchEvent(new CustomEvent('mams:project:synced', { detail: message.data }));
        break;
      
      default:
        console.log('Unknown WebSocket message:', message);
    }
  }

  // Helper Methods
  private async downloadFile(url: string, filename: string): Promise<string> {
    // Use CEP file system APIs to download
    const cep = (window as any).cep;
    const fs = cep.fs;
    
    // Get cache directory
    const cacheDir = fs.getSystemPath(fs.SystemPath.USER_DATA) + '/MAMS/cache';
    
    // Ensure cache directory exists
    if (fs.makedir(cacheDir) !== fs.NO_ERROR) {
      // Directory might already exist, continue
    }
    
    const localPath = `${cacheDir}/${filename}`;
    
    // Download file
    const response = await axios.get(url, {
      responseType: 'arraybuffer',
      headers: this.config.token ? { Authorization: `Bearer ${this.config.token}` } : {},
    });
    
    // Write to file
    const result = fs.writeFile(localPath, response.data, fs.WRITE_BINARY);
    if (result.err !== fs.NO_ERROR) {
      throw new Error('Failed to write file: ' + result.err);
    }
    
    return localPath;
  }

  private trackDownload(assetId: string, localPath: string, quality: string) {
    // Store in local IndexedDB for offline access
    const downloads = JSON.parse(localStorage.getItem('mams_downloads') || '[]');
    downloads.push({
      assetId,
      localPath,
      quality,
      timestamp: new Date().toISOString(),
    });
    
    // Keep only last 100 downloads
    if (downloads.length > 100) {
      downloads.splice(0, downloads.length - 100);
    }
    
    localStorage.setItem('mams_downloads', JSON.stringify(downloads));
  }

  private handleAuthError() {
    // Clear token and redirect to login
    this.config.token = undefined;
    this.saveConfig(this.config);
    window.dispatchEvent(new CustomEvent('mams:auth:required'));
  }

  // Cache Management
  public async clearCache(): Promise<void> {
    const cep = (window as any).cep;
    const fs = cep.fs;
    const cacheDir = fs.getSystemPath(fs.SystemPath.USER_DATA) + '/MAMS/cache';
    
    // Delete cache directory
    fs.deleteFile(cacheDir);
    
    // Clear download tracking
    localStorage.removeItem('mams_downloads');
  }

  public async getCacheSize(): Promise<number> {
    const downloads = JSON.parse(localStorage.getItem('mams_downloads') || '[]');
    let totalSize = 0;
    
    const cep = (window as any).cep;
    const fs = cep.fs;
    
    for (const download of downloads) {
      const stat = fs.stat(download.localPath);
      if (stat.err === fs.NO_ERROR) {
        totalSize += stat.data.size;
      }
    }
    
    return totalSize;
  }
}