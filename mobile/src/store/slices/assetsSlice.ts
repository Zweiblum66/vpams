/**
 * Assets Redux Slice
 * 
 * Manages asset state including listing, filtering,
 * caching, and favorites management.
 */

import {createSlice, createAsyncThunk, PayloadAction} from '@reduxjs/toolkit';
import {AssetState, Asset, SearchFilters, PaginationParams} from '@/types';
import {assetsApi} from '@/services/assetsApi';

const initialState: AssetState = {
  items: {},
  favorites: [],
  recent: [],
  cache: {
    thumbnails: {},
    proxies: {},
    metadata: {},
  },
  isLoading: false,
  error: null,
  lastSyncTime: undefined,
  // Pagination state
  currentPage: 1,
  hasNextPage: false,
  totalCount: 0,
  // Filter state
  filters: {
    sort_by: 'created_at',
    sort_order: 'desc',
  },
};

// Async thunks
export const fetchAssets = createAsyncThunk(
  'assets/fetchAssets',
  async (
    params: {
      page?: number;
      limit?: number;
      search?: string;
      filters?: SearchFilters;
      append?: boolean;
    },
    {rejectWithValue}
  ) => {
    try {
      const response = await assetsApi.getAssets({
        page: params.page || 1,
        limit: params.limit || 20,
        search: params.search,
        ...params.filters,
      });
      
      return {
        ...response,
        append: params.append || false,
        page: params.page || 1,
      };
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const fetchAssetDetails = createAsyncThunk(
  'assets/fetchAssetDetails',
  async (assetId: string, {rejectWithValue}) => {
    try {
      const response = await assetsApi.getAssetDetails(assetId);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const toggleFavorite = createAsyncThunk(
  'assets/toggleFavorite',
  async (assetId: string, {getState, rejectWithValue}) => {
    try {
      const state = getState() as any;
      const asset = state.assets.items[assetId];
      const newFavoriteStatus = !asset.is_favorite;
      
      await assetsApi.toggleFavorite(assetId, newFavoriteStatus);
      
      return {assetId, is_favorite: newFavoriteStatus};
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const deleteAsset = createAsyncThunk(
  'assets/deleteAsset',
  async (assetId: string, {rejectWithValue}) => {
    try {
      await assetsApi.deleteAsset(assetId);
      return assetId;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const searchAssets = createAsyncThunk(
  'assets/searchAssets',
  async (
    params: {
      query: string;
      filters?: SearchFilters;
      page?: number;
      limit?: number;
    },
    {rejectWithValue}
  ) => {
    try {
      const response = await assetsApi.searchAssets({
        query: params.query,
        page: params.page || 1,
        limit: params.limit || 20,
        ...params.filters,
      });
      
      return {
        ...response,
        page: params.page || 1,
      };
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const downloadAsset = createAsyncThunk(
  'assets/downloadAsset',
  async (
    params: {
      assetId: string;
      quality?: 'original' | 'high' | 'medium' | 'low';
    },
    {rejectWithValue}
  ) => {
    try {
      const response = await assetsApi.getDownloadUrl(params.assetId, params.quality);
      return {
        assetId: params.assetId,
        downloadUrl: response.download_url,
        expiresAt: response.expires_at,
      };
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

// Assets slice
const assetsSlice = createSlice({
  name: 'assets',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setAssetFilters: (state, action: PayloadAction<SearchFilters>) => {
      state.filters = action.payload;
      // Reset pagination when filters change
      state.currentPage = 1;
      state.hasNextPage = false;
    },
    clearAssetFilters: (state) => {
      state.filters = {
        sort_by: 'created_at',
        sort_order: 'desc',
      };
      state.currentPage = 1;
      state.hasNextPage = false;
    },
    addToRecent: (state, action: PayloadAction<string>) => {
      const assetId = action.payload;
      // Remove if already exists
      state.recent = state.recent.filter(id => id !== assetId);
      // Add to beginning
      state.recent.unshift(assetId);
      // Keep only last 20 items
      state.recent = state.recent.slice(0, 20);
    },
    updateAsset: (state, action: PayloadAction<Partial<Asset> & {id: string}>) => {
      const {id, ...updates} = action.payload;
      if (state.items[id]) {
        state.items[id] = {...state.items[id], ...updates};
      }
    },
    cacheAssetThumbnail: (
      state,
      action: PayloadAction<{assetId: string; localPath: string}>
    ) => {
      state.cache.thumbnails[action.payload.assetId] = action.payload.localPath;
    },
    cacheAssetProxy: (
      state,
      action: PayloadAction<{assetId: string; quality: string; localPath: string}>
    ) => {
      const key = `${action.payload.assetId}_${action.payload.quality}`;
      state.cache.proxies[key] = action.payload.localPath;
    },
    clearCache: (state) => {
      state.cache = {
        thumbnails: {},
        proxies: {},
        metadata: {},
      };
    },
    setLastSyncTime: (state) => {
      state.lastSyncTime = new Date().toISOString();
    },
  },
  extraReducers: (builder) => {
    // Fetch assets
    builder
      .addCase(fetchAssets.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchAssets.fulfilled, (state, action) => {
        state.isLoading = false;
        
        const {data, meta, append, page} = action.payload;
        
        if (append) {
          // Append to existing items
          data.forEach((asset: Asset) => {
            state.items[asset.id] = asset;
          });
        } else {
          // Replace items
          state.items = {};
          data.forEach((asset: Asset) => {
            state.items[asset.id] = asset;
          });
        }
        
        state.currentPage = page;
        state.hasNextPage = meta?.page ? meta.page < (meta.pages || 1) : false;
        state.totalCount = meta?.total || 0;
        state.lastSyncTime = new Date().toISOString();
      })
      .addCase(fetchAssets.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Fetch asset details
    builder
      .addCase(fetchAssetDetails.fulfilled, (state, action) => {
        const asset = action.payload;
        state.items[asset.id] = asset;
      })
      .addCase(fetchAssetDetails.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // Toggle favorite
    builder
      .addCase(toggleFavorite.fulfilled, (state, action) => {
        const {assetId, is_favorite} = action.payload;
        
        if (state.items[assetId]) {
          state.items[assetId].is_favorite = is_favorite;
        }
        
        if (is_favorite) {
          if (!state.favorites.includes(assetId)) {
            state.favorites.push(assetId);
          }
        } else {
          state.favorites = state.favorites.filter(id => id !== assetId);
        }
      })
      .addCase(toggleFavorite.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // Delete asset
    builder
      .addCase(deleteAsset.fulfilled, (state, action) => {
        const assetId = action.payload;
        
        // Remove from items
        delete state.items[assetId];
        
        // Remove from favorites
        state.favorites = state.favorites.filter(id => id !== assetId);
        
        // Remove from recent
        state.recent = state.recent.filter(id => id !== assetId);
        
        // Remove from cache
        delete state.cache.thumbnails[assetId];
        Object.keys(state.cache.proxies).forEach(key => {
          if (key.startsWith(assetId)) {
            delete state.cache.proxies[key];
          }
        });
        delete state.cache.metadata[assetId];
        
        // Update total count
        state.totalCount = Math.max(0, state.totalCount - 1);
      })
      .addCase(deleteAsset.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // Search assets
    builder
      .addCase(searchAssets.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(searchAssets.fulfilled, (state, action) => {
        state.isLoading = false;
        
        const {data, meta, page} = action.payload;
        
        // Replace items with search results
        state.items = {};
        data.forEach((asset: Asset) => {
          state.items[asset.id] = asset;
        });
        
        state.currentPage = page;
        state.hasNextPage = meta?.page ? meta.page < (meta.pages || 1) : false;
        state.totalCount = meta?.total || 0;
      })
      .addCase(searchAssets.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Download asset
    builder
      .addCase(downloadAsset.fulfilled, (state, action) => {
        const {assetId, downloadUrl} = action.payload;
        if (state.items[assetId]) {
          state.items[assetId].download_url = downloadUrl;
        }
      })
      .addCase(downloadAsset.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const {
  clearError,
  setAssetFilters,
  clearAssetFilters,
  addToRecent,
  updateAsset,
  cacheAssetThumbnail,
  cacheAssetProxy,
  clearCache,
  setLastSyncTime,
} = assetsSlice.actions;

export default assetsSlice.reducer;