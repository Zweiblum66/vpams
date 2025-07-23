import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Asset, CreateAssetRequest, UpdateAssetRequest, PaginatedResponse } from '../../types';
import { assetService } from '../../services/assetService';

interface AssetState {
  assets: Asset[];
  currentAsset: Asset | null;
  loading: boolean;
  error: string | null;
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
  filters: Record<string, any>;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  selectedAssets: string[];
  uploadProgress: Record<string, number>;
}

const initialState: AssetState = {
  assets: [],
  currentAsset: null,
  loading: false,
  error: null,
  pagination: {
    page: 1,
    limit: 20,
    total: 0,
    pages: 0,
  },
  filters: {},
  sortBy: 'created_at',
  sortOrder: 'desc',
  selectedAssets: [],
  uploadProgress: {},
};

// Async thunks
export const fetchAssets = createAsyncThunk(
  'assets/fetchAssets',
  async (params: {
    page?: number;
    limit?: number;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
    filters?: Record<string, any>;
    search?: string;
  } = {}) => {
    const response = await assetService.getAssets(params);
    return response;
  }
);

export const fetchAssetById = createAsyncThunk(
  'assets/fetchAssetById',
  async (id: string) => {
    const response = await assetService.getAssetById(id);
    return response;
  }
);

export const createAsset = createAsyncThunk(
  'assets/createAsset',
  async (data: CreateAssetRequest) => {
    const response = await assetService.createAsset(data);
    return response;
  }
);

export const updateAsset = createAsyncThunk(
  'assets/updateAsset',
  async ({ id, data }: { id: string; data: UpdateAssetRequest }) => {
    const response = await assetService.updateAsset(id, data);
    return response;
  }
);

export const deleteAsset = createAsyncThunk(
  'assets/deleteAsset',
  async (id: string) => {
    await assetService.deleteAsset(id);
    return id;
  }
);

export const uploadAsset = createAsyncThunk(
  'assets/uploadAsset',
  async (
    {
      file,
      metadata,
      onProgress,
    }: {
      file: File;
      metadata: CreateAssetRequest;
      onProgress?: (progress: number) => void;
    },
    { dispatch }
  ) => {
    const filename = file.name;
    
    // Initialize upload progress
    if (onProgress) {
      dispatch(setUploadProgress({ filename, progress: 0 }));
    }

    const response = await assetService.uploadAsset(file, metadata, (progress) => {
      if (onProgress) {
        onProgress(progress);
      }
      dispatch(setUploadProgress({ filename, progress }));
    });

    // Complete upload
    dispatch(setUploadProgress({ filename, progress: 100 }));
    
    return response;
  }
);

const assetSlice = createSlice({
  name: 'assets',
  initialState,
  reducers: {
    setCurrentAsset: (state, action: PayloadAction<Asset | null>) => {
      state.currentAsset = action.payload;
    },
    setFilters: (state, action: PayloadAction<Record<string, any>>) => {
      state.filters = action.payload;
    },
    setSorting: (state, action: PayloadAction<{ sortBy: string; sortOrder: 'asc' | 'desc' }>) => {
      state.sortBy = action.payload.sortBy;
      state.sortOrder = action.payload.sortOrder;
    },
    setSelectedAssets: (state, action: PayloadAction<string[]>) => {
      state.selectedAssets = action.payload;
    },
    toggleAssetSelection: (state, action: PayloadAction<string>) => {
      const assetId = action.payload;
      const index = state.selectedAssets.indexOf(assetId);
      if (index > -1) {
        state.selectedAssets.splice(index, 1);
      } else {
        state.selectedAssets.push(assetId);
      }
    },
    clearSelection: (state) => {
      state.selectedAssets = [];
    },
    setUploadProgress: (state, action: PayloadAction<{ filename: string; progress: number }>) => {
      const { filename, progress } = action.payload;
      state.uploadProgress[filename] = progress;
      
      // Remove completed uploads after a delay
      if (progress === 100) {
        setTimeout(() => {
          delete state.uploadProgress[filename];
        }, 3000);
      }
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch assets
      .addCase(fetchAssets.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAssets.fulfilled, (state, action) => {
        state.loading = false;
        state.assets = action.payload.data;
        state.pagination = action.payload.meta;
      })
      .addCase(fetchAssets.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch assets';
      })
      
      // Fetch asset by ID
      .addCase(fetchAssetById.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAssetById.fulfilled, (state, action) => {
        state.loading = false;
        state.currentAsset = action.payload;
      })
      .addCase(fetchAssetById.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch asset';
      })
      
      // Create asset
      .addCase(createAsset.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createAsset.fulfilled, (state, action) => {
        state.loading = false;
        state.assets.unshift(action.payload);
        state.pagination.total += 1;
      })
      .addCase(createAsset.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to create asset';
      })
      
      // Update asset
      .addCase(updateAsset.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateAsset.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.assets.findIndex(asset => asset.id === action.payload.id);
        if (index !== -1) {
          state.assets[index] = action.payload;
        }
        if (state.currentAsset?.id === action.payload.id) {
          state.currentAsset = action.payload;
        }
      })
      .addCase(updateAsset.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to update asset';
      })
      
      // Delete asset
      .addCase(deleteAsset.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteAsset.fulfilled, (state, action) => {
        state.loading = false;
        state.assets = state.assets.filter(asset => asset.id !== action.payload);
        state.pagination.total -= 1;
        if (state.currentAsset?.id === action.payload) {
          state.currentAsset = null;
        }
        // Remove from selection
        state.selectedAssets = state.selectedAssets.filter(id => id !== action.payload);
      })
      .addCase(deleteAsset.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to delete asset';
      })
      
      // Upload asset
      .addCase(uploadAsset.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(uploadAsset.fulfilled, (state, action) => {
        state.loading = false;
        state.assets.unshift(action.payload);
        state.pagination.total += 1;
      })
      .addCase(uploadAsset.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to upload asset';
      });
  },
});

export const {
  setCurrentAsset,
  setFilters,
  setSorting,
  setSelectedAssets,
  toggleAssetSelection,
  clearSelection,
  setUploadProgress,
  clearError,
} = assetSlice.actions;

export default assetSlice.reducer;