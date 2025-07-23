/**
 * Offline Service
 * 
 * Handles offline data storage, sync operations,
 * and offline asset management using SQLite and file system.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import RNFS from 'react-native-fs';
import SQLite from 'react-native-sqlite-storage';
import {Asset, Project, SyncOperation, OfflineAsset} from '@/types';
import {apiClient} from './apiClient';
import {assetsApi} from './assetsApi';

// Enable SQLite debugging in development
if (__DEV__) {
  SQLite.DEBUG(true);
  SQLite.enablePromise(true);
}

interface OfflineData {
  assets: Record<string, OfflineAsset>;
  projects: Record<string, Project>;
  searches: Record<string, any>;
  pendingOperations: SyncOperation[];
  lastSyncTime: string | null;
}

interface StorageInfo {
  used: number;
  available: number;
  total: number;
}

class OfflineService {
  private db: SQLite.SQLiteDatabase | null = null;
  private offlineDir: string;
  private thumbnailsDir: string;
  private previewsDir: string;

  constructor() {
    this.offlineDir = `${RNFS.DocumentDirectoryPath}/offline`;
    this.thumbnailsDir = `${this.offlineDir}/thumbnails`;
    this.previewsDir = `${this.offlineDir}/previews`;
  }

  /**
   * Initialize offline service
   */
  async initialize(): Promise<void> {
    try {
      // Create offline directories
      await this.createDirectories();
      
      // Initialize SQLite database
      await this.initializeDatabase();
      
      console.log('Offline service initialized');
    } catch (error) {
      console.error('Failed to initialize offline service:', error);
      throw error;
    }
  }

  /**
   * Create necessary directories for offline storage
   */
  private async createDirectories(): Promise<void> {
    const directories = [
      this.offlineDir,
      this.thumbnailsDir,
      this.previewsDir,
    ];

    for (const dir of directories) {
      const exists = await RNFS.exists(dir);
      if (!exists) {
        await RNFS.mkdir(dir);
      }
    }
  }

  /**
   * Initialize SQLite database for offline data
   */
  private async initializeDatabase(): Promise<void> {
    try {
      this.db = await SQLite.openDatabase({
        name: 'mams_offline.db',
        location: 'default',
      });

      // Create tables
      await this.createTables();
    } catch (error) {
      console.error('Failed to initialize database:', error);
      throw error;
    }
  }

  /**
   * Create database tables
   */
  private async createTables(): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const createTablesSQL = `
      -- Offline assets table
      CREATE TABLE IF NOT EXISTS offline_assets (
        id TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        thumbnail_path TEXT,
        preview_path TEXT,
        original_path TEXT,
        downloaded_at TEXT NOT NULL,
        last_accessed TEXT NOT NULL,
        file_size INTEGER NOT NULL
      );

      -- Offline projects table
      CREATE TABLE IF NOT EXISTS offline_projects (
        id TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        downloaded_at TEXT NOT NULL,
        last_accessed TEXT NOT NULL
      );

      -- Pending operations table
      CREATE TABLE IF NOT EXISTS pending_operations (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        data TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        retry_count INTEGER DEFAULT 0
      );

      -- Search cache table
      CREATE TABLE IF NOT EXISTS search_cache (
        id TEXT PRIMARY KEY,
        query TEXT NOT NULL,
        filters TEXT,
        results TEXT NOT NULL,
        cached_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
      );

      -- Settings table
      CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      );
    `;

    await this.db.executeSql(createTablesSQL);
  }

  /**
   * Download asset for offline use
   */
  async downloadAsset(
    assetId: string,
    includePreview = false,
    quality: 'thumbnail' | 'low' | 'medium' | 'high' = 'thumbnail'
  ): Promise<{asset: OfflineAsset; storageInfo: StorageInfo}> {
    try {
      // Get asset details
      const assetResponse = await assetsApi.getAssetDetails(assetId);
      const asset = assetResponse.data;

      // Download thumbnail
      const thumbnailPath = await this.downloadThumbnail(assetId);
      
      // Download preview if requested
      let previewPath: string | undefined;
      if (includePreview) {
        previewPath = await this.downloadPreview(assetId, quality);
      }

      // Create offline asset
      const offlineAsset: OfflineAsset = {
        ...asset,
        offline_data: {
          thumbnail_path: thumbnailPath,
          preview_path: previewPath,
          downloaded_at: new Date().toISOString(),
          last_accessed: new Date().toISOString(),
          download_quality: quality,
          has_preview: !!previewPath,
        },
      };

      // Save to database
      await this.saveOfflineAsset(offlineAsset);

      // Get updated storage info
      const storageInfo = await this.getStorageInfo();

      return {asset: offlineAsset, storageInfo};
    } catch (error) {
      console.error('Failed to download asset for offline:', error);
      throw error;
    }
  }

  /**
   * Download asset thumbnail
   */
  private async downloadThumbnail(assetId: string): Promise<string> {
    try {
      const thumbnailUrl = await assetsApi.getThumbnailUrl(assetId);
      const thumbnailPath = `${this.thumbnailsDir}/${assetId}.jpg`;
      
      const downloadResult = await RNFS.downloadFile({
        fromUrl: thumbnailUrl.thumbnail_url,
        toFile: thumbnailPath,
      }).promise;

      if (downloadResult.statusCode === 200) {
        return thumbnailPath;
      } else {
        throw new Error(`Failed to download thumbnail: ${downloadResult.statusCode}`);
      }
    } catch (error) {
      console.error('Failed to download thumbnail:', error);
      throw error;
    }
  }

  /**
   * Download asset preview
   */
  private async downloadPreview(
    assetId: string,
    quality: 'low' | 'medium' | 'high'
  ): Promise<string> {
    try {
      const previewUrl = await assetsApi.getPreviewUrl(assetId, quality);
      const extension = this.getFileExtension(previewUrl.preview_url) || 'mp4';
      const previewPath = `${this.previewsDir}/${assetId}_${quality}.${extension}`;
      
      const downloadResult = await RNFS.downloadFile({
        fromUrl: previewUrl.preview_url,
        toFile: previewPath,
      }).promise;

      if (downloadResult.statusCode === 200) {
        return previewPath;
      } else {
        throw new Error(`Failed to download preview: ${downloadResult.statusCode}`);
      }
    } catch (error) {
      console.error('Failed to download preview:', error);
      throw error;
    }
  }

  /**
   * Save offline asset to database
   */
  private async saveOfflineAsset(asset: OfflineAsset): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const sql = `
      INSERT OR REPLACE INTO offline_assets 
      (id, data, thumbnail_path, preview_path, downloaded_at, last_accessed, file_size)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `;

    const params = [
      asset.id,
      JSON.stringify(asset),
      asset.offline_data?.thumbnail_path || null,
      asset.offline_data?.preview_path || null,
      asset.offline_data?.downloaded_at || new Date().toISOString(),
      asset.offline_data?.last_accessed || new Date().toISOString(),
      asset.file_size || 0,
    ];

    await this.db.executeSql(sql, params);
  }

  /**
   * Remove offline asset
   */
  async removeOfflineAsset(assetId: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    try {
      // Get asset data to find file paths
      const asset = await this.getOfflineAsset(assetId);
      
      if (asset?.offline_data) {
        // Delete thumbnail file
        if (asset.offline_data.thumbnail_path) {
          const thumbnailExists = await RNFS.exists(asset.offline_data.thumbnail_path);
          if (thumbnailExists) {
            await RNFS.unlink(asset.offline_data.thumbnail_path);
          }
        }

        // Delete preview file
        if (asset.offline_data.preview_path) {
          const previewExists = await RNFS.exists(asset.offline_data.preview_path);
          if (previewExists) {
            await RNFS.unlink(asset.offline_data.preview_path);
          }
        }
      }

      // Remove from database
      await this.db.executeSql(
        'DELETE FROM offline_assets WHERE id = ?',
        [assetId]
      );
    } catch (error) {
      console.error('Failed to remove offline asset:', error);
      throw error;
    }
  }

  /**
   * Get offline asset by ID
   */
  async getOfflineAsset(assetId: string): Promise<OfflineAsset | null> {
    if (!this.db) throw new Error('Database not initialized');

    try {
      const result = await this.db.executeSql(
        'SELECT data FROM offline_assets WHERE id = ?',
        [assetId]
      );

      if (result[0].rows.length > 0) {
        const assetData = JSON.parse(result[0].rows.item(0).data);
        
        // Update last accessed time
        await this.db.executeSql(
          'UPDATE offline_assets SET last_accessed = ? WHERE id = ?',
          [new Date().toISOString(), assetId]
        );

        return assetData;
      }

      return null;
    } catch (error) {
      console.error('Failed to get offline asset:', error);
      return null;
    }
  }

  /**
   * Get all offline assets
   */
  async getAllOfflineAssets(): Promise<Record<string, OfflineAsset>> {
    if (!this.db) throw new Error('Database not initialized');

    try {
      const result = await this.db.executeSql(
        'SELECT data FROM offline_assets ORDER BY last_accessed DESC'
      );

      const assets: Record<string, OfflineAsset> = {};
      
      for (let i = 0; i < result[0].rows.length; i++) {
        const assetData = JSON.parse(result[0].rows.item(i).data);
        assets[assetData.id] = assetData;
      }

      return assets;
    } catch (error) {
      console.error('Failed to get offline assets:', error);
      return {};
    }
  }

  /**
   * Save pending operation
   */
  async savePendingOperation(operation: SyncOperation): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const sql = `
      INSERT OR REPLACE INTO pending_operations 
      (id, type, data, timestamp, retry_count)
      VALUES (?, ?, ?, ?, ?)
    `;

    await this.db.executeSql(sql, [
      operation.id,
      operation.type,
      JSON.stringify(operation.data),
      operation.timestamp,
      operation.retry_count || 0,
    ]);
  }

  /**
   * Get pending operations
   */
  async getPendingOperations(): Promise<SyncOperation[]> {
    if (!this.db) throw new Error('Database not initialized');

    try {
      const result = await this.db.executeSql(
        'SELECT * FROM pending_operations ORDER BY timestamp ASC'
      );

      const operations: SyncOperation[] = [];
      
      for (let i = 0; i < result[0].rows.length; i++) {
        const row = result[0].rows.item(i);
        operations.push({
          id: row.id,
          type: row.type,
          data: JSON.parse(row.data),
          timestamp: row.timestamp,
          retry_count: row.retry_count,
        });
      }

      return operations;
    } catch (error) {
      console.error('Failed to get pending operations:', error);
      return [];
    }
  }

  /**
   * Process pending operations
   */
  async processPendingOperations(
    operations: SyncOperation[]
  ): Promise<{successful: string[]; failed: string[]}> {
    const successful: string[] = [];
    const failed: string[] = [];

    for (const operation of operations) {
      try {
        await this.processOperation(operation);
        successful.push(operation.id);
        
        // Remove successful operation
        await this.removePendingOperation(operation.id);
      } catch (error) {
        console.error(`Failed to process operation ${operation.id}:`, error);
        failed.push(operation.id);
        
        // Increment retry count
        await this.incrementOperationRetryCount(operation.id);
      }
    }

    return {successful, failed};
  }

  /**
   * Process single operation
   */
  private async processOperation(operation: SyncOperation): Promise<void> {
    switch (operation.type) {
      case 'upload_asset':
        // Handle asset upload
        break;
      
      case 'update_asset':
        await assetsApi.updateAsset(operation.data.assetId, operation.data.updates);
        break;
      
      case 'delete_asset':
        await assetsApi.deleteAsset(operation.data.assetId);
        break;
      
      case 'toggle_favorite':
        await assetsApi.toggleFavorite(operation.data.assetId, operation.data.isFavorite);
        break;
      
      default:
        throw new Error(`Unknown operation type: ${operation.type}`);
    }
  }

  /**
   * Remove pending operation
   */
  async removePendingOperation(operationId: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    await this.db.executeSql(
      'DELETE FROM pending_operations WHERE id = ?',
      [operationId]
    );
  }

  /**
   * Increment operation retry count
   */
  private async incrementOperationRetryCount(operationId: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    await this.db.executeSql(
      'UPDATE pending_operations SET retry_count = retry_count + 1 WHERE id = ?',
      [operationId]
    );
  }

  /**
   * Sync offline data with server
   */
  async syncOfflineData(): Promise<void> {
    try {
      // Sync recent assets
      await this.syncRecentAssets();
      
      // Sync user projects
      await this.syncUserProjects();
      
      // Clean up old cached data
      await this.cleanupOldData();
    } catch (error) {
      console.error('Failed to sync offline data:', error);
      throw error;
    }
  }

  /**
   * Sync recent assets
   */
  private async syncRecentAssets(): Promise<void> {
    try {
      const response = await assetsApi.getAssets({
        page: 1,
        limit: 50,
        sort_by: 'updated_at',
        sort_order: 'desc',
      });

      // Cache basic asset data
      await AsyncStorage.setItem(
        'offline_recent_assets',
        JSON.stringify(response.data)
      );
    } catch (error) {
      console.error('Failed to sync recent assets:', error);
    }
  }

  /**
   * Sync user projects
   */
  private async syncUserProjects(): Promise<void> {
    try {
      // This would call a projects API when implemented
      // const response = await projectsApi.getUserProjects();
      
      // For now, store empty array
      await AsyncStorage.setItem(
        'offline_projects',
        JSON.stringify([])
      );
    } catch (error) {
      console.error('Failed to sync projects:', error);
    }
  }

  /**
   * Clean up old cached data
   */
  private async cleanupOldData(): Promise<void> {
    if (!this.db) return;

    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const cutoffDate = thirtyDaysAgo.toISOString();

    try {
      // Get old assets to delete files
      const result = await this.db.executeSql(
        'SELECT id, data FROM offline_assets WHERE last_accessed < ?',
        [cutoffDate]
      );

      // Delete files for old assets
      for (let i = 0; i < result[0].rows.length; i++) {
        const assetData = JSON.parse(result[0].rows.item(i).data);
        if (assetData.offline_data) {
          await this.deleteAssetFiles(assetData.offline_data);
        }
      }

      // Remove old assets from database
      await this.db.executeSql(
        'DELETE FROM offline_assets WHERE last_accessed < ?',
        [cutoffDate]
      );

      // Remove old search cache
      await this.db.executeSql(
        'DELETE FROM search_cache WHERE expires_at < ?',
        [new Date().toISOString()]
      );
    } catch (error) {
      console.error('Failed to cleanup old data:', error);
    }
  }

  /**
   * Delete asset files
   */
  private async deleteAssetFiles(offlineData: any): Promise<void> {
    try {
      if (offlineData.thumbnail_path) {
        const thumbnailExists = await RNFS.exists(offlineData.thumbnail_path);
        if (thumbnailExists) {
          await RNFS.unlink(offlineData.thumbnail_path);
        }
      }

      if (offlineData.preview_path) {
        const previewExists = await RNFS.exists(offlineData.preview_path);
        if (previewExists) {
          await RNFS.unlink(offlineData.preview_path);
        }
      }
    } catch (error) {
      console.error('Failed to delete asset files:', error);
    }
  }

  /**
   * Get storage information
   */
  async getStorageInfo(): Promise<StorageInfo> {
    try {
      const freeSpace = await RNFS.getFSInfo();
      const offlineSize = await this.calculateOfflineStorageSize();

      return {
        used: offlineSize,
        available: freeSpace.freeSpace,
        total: freeSpace.totalSpace,
      };
    } catch (error) {
      console.error('Failed to get storage info:', error);
      return {used: 0, available: 0, total: 0};
    }
  }

  /**
   * Calculate offline storage size
   */
  private async calculateOfflineStorageSize(): Promise<number> {
    try {
      let totalSize = 0;
      
      // Calculate thumbnails size
      const thumbnailsExist = await RNFS.exists(this.thumbnailsDir);
      if (thumbnailsExist) {
        const thumbnails = await RNFS.readDir(this.thumbnailsDir);
        for (const file of thumbnails) {
          totalSize += file.size || 0;
        }
      }

      // Calculate previews size
      const previewsExist = await RNFS.exists(this.previewsDir);
      if (previewsExist) {
        const previews = await RNFS.readDir(this.previewsDir);
        for (const file of previews) {
          totalSize += file.size || 0;
        }
      }

      return totalSize;
    } catch (error) {
      console.error('Failed to calculate storage size:', error);
      return 0;
    }
  }

  /**
   * Clear all offline data
   */
  async clearAllOfflineData(): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    try {
      // Delete all files
      const thumbnailsExist = await RNFS.exists(this.thumbnailsDir);
      if (thumbnailsExist) {
        await RNFS.unlink(this.thumbnailsDir);
        await RNFS.mkdir(this.thumbnailsDir);
      }

      const previewsExist = await RNFS.exists(this.previewsDir);
      if (previewsExist) {
        await RNFS.unlink(this.previewsDir);
        await RNFS.mkdir(this.previewsDir);
      }

      // Clear database tables
      await this.db.executeSql('DELETE FROM offline_assets');
      await this.db.executeSql('DELETE FROM offline_projects');
      await this.db.executeSql('DELETE FROM pending_operations');
      await this.db.executeSql('DELETE FROM search_cache');

      // Clear AsyncStorage cache
      await AsyncStorage.multiRemove([
        'offline_recent_assets',
        'offline_projects',
        'last_sync_time',
      ]);
    } catch (error) {
      console.error('Failed to clear offline data:', error);
      throw error;
    }
  }

  /**
   * Load offline data for Redux store
   */
  async loadOfflineData(): Promise<OfflineData> {
    try {
      const assets = await this.getAllOfflineAssets();
      const pendingOperations = await this.getPendingOperations();
      const lastSyncTime = await AsyncStorage.getItem('last_sync_time');

      return {
        assets,
        projects: {}, // Will be implemented when projects are added
        searches: {}, // Will be implemented when search cache is added
        pendingOperations,
        lastSyncTime,
      };
    } catch (error) {
      console.error('Failed to load offline data:', error);
      return {
        assets: {},
        projects: {},
        searches: {},
        pendingOperations: [],
        lastSyncTime: null,
      };
    }
  }

  /**
   * Set last sync time
   */
  async setLastSyncTime(timestamp: string): Promise<void> {
    await AsyncStorage.setItem('last_sync_time', timestamp);
  }

  /**
   * Get file extension from URL
   */
  private getFileExtension(url: string): string | null {
    try {
      const pathname = new URL(url).pathname;
      const extension = pathname.split('.').pop();
      return extension || null;
    } catch {
      return null;
    }
  }
}

export const offlineService = new OfflineService();