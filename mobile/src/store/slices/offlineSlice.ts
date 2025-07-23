/**
 * Offline Redux Slice
 * 
 * Manages offline state including network status,
 * offline data storage, and sync operations.
 */

import {createSlice, createAsyncThunk, PayloadAction} from '@reduxjs/toolkit';
import {OfflineState, SyncOperation, OfflineAsset} from '@/types';
import {offlineService} from '@/services/offlineService';
import NetInfo from '@react-native-community/netinfo';

const initialState: OfflineState = {
  isOnline: true,
  isConnected: true,
  connectionType: 'unknown',
  isInternetReachable: null,
  
  // Offline data
  offlineAssets: {},
  offlineProjects: {},
  offlineSearches: {},
  
  // Sync state
  pendingOperations: [],
  isSyncing: false,
  lastSyncTime: null,
  syncProgress: 0,
  
  // Download state
  downloadQueue: [],
  downloadProgress: {},
  
  // Settings
  settings: {
    auto_sync: true,
    sync_on_wifi_only: true,
    download_thumbnails: true,
    download_previews: false,
    max_offline_storage: 1024 * 1024 * 1024, // 1GB
    sync_interval: 30, // minutes
  },
  
  // Storage info
  storageUsed: 0,
  storageAvailable: 0,
};

// Async thunks
export const initializeOfflineMode = createAsyncThunk(
  'offline/initialize',
  async (_, {dispatch}) => {
    // Initialize network monitoring
    dispatch(startNetworkMonitoring());
    
    // Initialize offline storage
    await offlineService.initialize();
    
    // Get storage info
    const storageInfo = await offlineService.getStorageInfo();
    
    // Load offline data
    const offlineData = await offlineService.loadOfflineData();
    
    return {
      storageInfo,
      offlineData,
    };
  }
);

export const startNetworkMonitoring = createAsyncThunk(
  'offline/startNetworkMonitoring',
  async (_, {dispatch}) => {
    // Subscribe to network state changes
    const unsubscribe = NetInfo.addEventListener(state => {
      dispatch(updateNetworkState({
        isConnected: state.isConnected || false,
        isInternetReachable: state.isInternetReachable,
        type: state.type,
        details: state.details,
      }));
      
      // Auto-sync when coming back online
      if (state.isConnected && state.isInternetReachable) {
        dispatch(startSync());
      }
    });
    
    // Get initial network state
    const netInfo = await NetInfo.fetch();
    dispatch(updateNetworkState({
      isConnected: netInfo.isConnected || false,
      isInternetReachable: netInfo.isInternetReachable,
      type: netInfo.type,
      details: netInfo.details,
    }));
    
    return unsubscribe;
  }
);

export const downloadAssetForOffline = createAsyncThunk(
  'offline/downloadAsset',
  async (
    params: {
      assetId: string;
      includePreview?: boolean;
      quality?: 'thumbnail' | 'low' | 'medium' | 'high';
    },
    {rejectWithValue}
  ) => {
    try {
      const result = await offlineService.downloadAsset(
        params.assetId,
        params.includePreview,
        params.quality
      );
      
      return result;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const startSync = createAsyncThunk(
  'offline/startSync',
  async (_, {getState, dispatch}) => {
    const state = getState() as any;
    const {pendingOperations, settings} = state.offline;
    
    if (!state.offline.isOnline || state.offline.isSyncing) {
      return null;
    }
    
    try {
      // Process pending operations
      const results = await offlineService.processPendingOperations(pendingOperations);
      
      // Download new data if enabled
      if (settings.auto_sync) {
        await offlineService.syncOfflineData();
      }
      
      // Update last sync time
      const lastSyncTime = new Date().toISOString();
      await offlineService.setLastSyncTime(lastSyncTime);
      
      return {
        results,
        lastSyncTime,
      };
    } catch (error) {
      throw error;
    }
  }
);

export const addPendingOperation = createAsyncThunk(
  'offline/addPendingOperation',
  async (operation: Omit<SyncOperation, 'id' | 'timestamp'>) => {
    const syncOperation: SyncOperation = {
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      ...operation,
    };
    
    await offlineService.savePendingOperation(syncOperation);
    return syncOperation;
  }
);

export const removeOfflineAsset = createAsyncThunk(
  'offline/removeOfflineAsset',
  async (assetId: string) => {
    await offlineService.removeOfflineAsset(assetId);
    const storageInfo = await offlineService.getStorageInfo();
    
    return {
      assetId,
      storageInfo,
    };
  }
);

export const clearOfflineData = createAsyncThunk(
  'offline/clearOfflineData',
  async () => {
    await offlineService.clearAllOfflineData();
    const storageInfo = await offlineService.getStorageInfo();
    
    return storageInfo;
  }
);

// Offline slice
const offlineSlice = createSlice({
  name: 'offline',
  initialState,
  reducers: {
    updateNetworkState: (
      state,
      action: PayloadAction<{
        isConnected: boolean;
        isInternetReachable: boolean | null;
        type: string;
        details?: any;
      }>
    ) => {
      const {isConnected, isInternetReachable, type} = action.payload;
      
      state.isConnected = isConnected;
      state.isInternetReachable = isInternetReachable;
      state.connectionType = type;
      
      // Determine if truly online (connected AND internet reachable)
      state.isOnline = isConnected && (isInternetReachable !== false);
    },
    
    setOfflineAsset: (state, action: PayloadAction<OfflineAsset>) => {
      const asset = action.payload;
      state.offlineAssets[asset.id] = asset;
    },
    
    removeOfflineAssetLocal: (state, action: PayloadAction<string>) => {
      const assetId = action.payload;
      delete state.offlineAssets[assetId];
    },
    
    updateDownloadProgress: (
      state,
      action: PayloadAction<{assetId: string; progress: number}>
    ) => {
      const {assetId, progress} = action.payload;
      state.downloadProgress[assetId] = progress;
    },
    
    addToDownloadQueue: (state, action: PayloadAction<string>) => {
      const assetId = action.payload;
      if (!state.downloadQueue.includes(assetId)) {
        state.downloadQueue.push(assetId);
      }
    },
    
    removeFromDownloadQueue: (state, action: PayloadAction<string>) => {
      const assetId = action.payload;
      state.downloadQueue = state.downloadQueue.filter(id => id !== assetId);
      delete state.downloadProgress[assetId];
    },
    
    updateOfflineSettings: (
      state,
      action: PayloadAction<Partial<OfflineState['settings']>>
    ) => {
      state.settings = {...state.settings, ...action.payload};
    },
    
    setSyncProgress: (state, action: PayloadAction<number>) => {
      state.syncProgress = action.payload;
    },
    
    clearPendingOperations: (state) => {
      state.pendingOperations = [];
    },
    
    removePendingOperation: (state, action: PayloadAction<string>) => {
      state.pendingOperations = state.pendingOperations.filter(
        op => op.id !== action.payload
      );
    },
    
    updateStorageInfo: (
      state,
      action: PayloadAction<{used: number; available: number}>
    ) => {
      state.storageUsed = action.payload.used;
      state.storageAvailable = action.payload.available;
    },
  },
  extraReducers: (builder) => {
    // Initialize offline mode
    builder
      .addCase(initializeOfflineMode.fulfilled, (state, action) => {
        const {storageInfo, offlineData} = action.payload;
        
        state.storageUsed = storageInfo.used;
        state.storageAvailable = storageInfo.available;
        
        state.offlineAssets = offlineData.assets || {};
        state.offlineProjects = offlineData.projects || {};
        state.offlineSearches = offlineData.searches || {};
        state.pendingOperations = offlineData.pendingOperations || [];
        state.lastSyncTime = offlineData.lastSyncTime;
      });

    // Download asset for offline use
    builder
      .addCase(downloadAssetForOffline.pending, (state, action) => {
        const assetId = action.meta.arg.assetId;
        state.downloadProgress[assetId] = 0;
        if (!state.downloadQueue.includes(assetId)) {
          state.downloadQueue.push(assetId);
        }
      })
      .addCase(downloadAssetForOffline.fulfilled, (state, action) => {
        const {asset, storageInfo} = action.payload;
        
        state.offlineAssets[asset.id] = asset;
        state.downloadQueue = state.downloadQueue.filter(id => id !== asset.id);
        delete state.downloadProgress[asset.id];
        
        state.storageUsed = storageInfo.used;
        state.storageAvailable = storageInfo.available;
      })
      .addCase(downloadAssetForOffline.rejected, (state, action) => {
        const assetId = action.meta.arg.assetId;
        state.downloadQueue = state.downloadQueue.filter(id => id !== assetId);
        delete state.downloadProgress[assetId];
      });

    // Start sync
    builder
      .addCase(startSync.pending, (state) => {
        state.isSyncing = true;
        state.syncProgress = 0;
      })
      .addCase(startSync.fulfilled, (state, action) => {
        state.isSyncing = false;
        state.syncProgress = 100;
        
        if (action.payload) {
          state.lastSyncTime = action.payload.lastSyncTime;
          // Clear successful operations
          state.pendingOperations = state.pendingOperations.filter(
            op => !action.payload.results.successful.includes(op.id)
          );
        }
      })
      .addCase(startSync.rejected, (state) => {
        state.isSyncing = false;
        state.syncProgress = 0;
      });

    // Add pending operation
    builder
      .addCase(addPendingOperation.fulfilled, (state, action) => {
        state.pendingOperations.push(action.payload);
      });

    // Remove offline asset
    builder
      .addCase(removeOfflineAsset.fulfilled, (state, action) => {
        const {assetId, storageInfo} = action.payload;
        delete state.offlineAssets[assetId];
        state.storageUsed = storageInfo.used;
        state.storageAvailable = storageInfo.available;
      });

    // Clear offline data
    builder
      .addCase(clearOfflineData.fulfilled, (state, action) => {
        state.offlineAssets = {};
        state.offlineProjects = {};
        state.offlineSearches = {};
        state.pendingOperations = [];
        state.downloadQueue = [];
        state.downloadProgress = {};
        state.lastSyncTime = null;
        
        state.storageUsed = action.payload.used;
        state.storageAvailable = action.payload.available;
      });
  },
});

export const {
  updateNetworkState,
  setOfflineAsset,
  removeOfflineAssetLocal,
  updateDownloadProgress,
  addToDownloadQueue,
  removeFromDownloadQueue,
  updateOfflineSettings,
  setSyncProgress,
  clearPendingOperations,
  removePendingOperation,
  updateStorageInfo,
} = offlineSlice.actions;

export default offlineSlice.reducer;