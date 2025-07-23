/**
 * Uploads Redux Slice
 * 
 * Manages upload state including queue management,
 * progress tracking, and upload settings.
 */

import {createSlice, createAsyncThunk, PayloadAction} from '@reduxjs/toolkit';
import {UploadState, UploadTask, UploadSettings} from '@/types';
import {uploadService} from '@/services/uploadService';

const initialState: UploadState = {
  tasks: {},
  queue: [],
  activeUploads: {},
  settings: {
    max_concurrent_uploads: 2,
    chunk_size: 1024 * 1024, // 1MB
    auto_retry: true,
    max_retries: 3,
    wifi_only: false,
    auto_pause_on_cellular: true,
    quality_preference: 'original',
    auto_upload: false,
    notification_enabled: true,
  },
  isUploading: false,
  totalProgress: 0,
  networkType: 'unknown',
};

// Async thunks
export const startUpload = createAsyncThunk(
  'uploads/startUpload',
  async (taskId: string, {getState, rejectWithValue}) => {
    try {
      const state = getState() as any;
      const task = state.uploads.tasks[taskId];
      
      if (!task) {
        throw new Error('Upload task not found');
      }
      
      const result = await uploadService.startUpload(task);
      return {taskId, result};
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const pauseUploadAsync = createAsyncThunk(
  'uploads/pauseUploadAsync',
  async (taskId: string, {rejectWithValue}) => {
    try {
      await uploadService.pauseUpload(taskId);
      return taskId;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const resumeUploadAsync = createAsyncThunk(
  'uploads/resumeUploadAsync',
  async (taskId: string, {rejectWithValue}) => {
    try {
      await uploadService.resumeUpload(taskId);
      return taskId;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const cancelUploadAsync = createAsyncThunk(
  'uploads/cancelUploadAsync',
  async (taskId: string, {rejectWithValue}) => {
    try {
      await uploadService.cancelUpload(taskId);
      return taskId;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const retryUploadAsync = createAsyncThunk(
  'uploads/retryUploadAsync',
  async (taskId: string, {getState, rejectWithValue}) => {
    try {
      const state = getState() as any;
      const task = state.uploads.tasks[taskId];
      
      if (!task) {
        throw new Error('Upload task not found');
      }
      
      const result = await uploadService.retryUpload(task);
      return {taskId, result};
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const processUploadQueue = createAsyncThunk(
  'uploads/processUploadQueue',
  async (_, {getState, dispatch}) => {
    const state = getState() as any;
    const {queue, activeUploads, settings} = state.uploads;
    
    // Check if we can start more uploads
    const activeCount = Object.keys(activeUploads).length;
    const maxConcurrent = settings.max_concurrent_uploads;
    
    if (activeCount < maxConcurrent && queue.length > 0) {
      const nextTaskId = queue[0];
      dispatch(startUpload(nextTaskId));
    }
    
    return null;
  }
);

export const updateNetworkType = createAsyncThunk(
  'uploads/updateNetworkType',
  async (networkType: string, {getState, dispatch}) => {
    const state = getState() as any;
    const {settings, activeUploads} = state.uploads;
    
    // Auto-pause on cellular if enabled
    if (networkType === 'cellular' && settings.auto_pause_on_cellular) {
      Object.keys(activeUploads).forEach(taskId => {
        dispatch(pauseUpload(taskId));
      });
    }
    
    return networkType;
  }
);

// Uploads slice
const uploadsSlice = createSlice({
  name: 'uploads',
  initialState,
  reducers: {
    addUploadTask: (state, action: PayloadAction<UploadTask>) => {
      const task = action.payload;
      state.tasks[task.id] = task;
      
      // Add to queue if not already uploading
      if (task.status === 'queued' && !state.queue.includes(task.id)) {
        state.queue.push(task.id);
      }
    },
    
    removeUploadTask: (state, action: PayloadAction<string>) => {
      const taskId = action.payload;
      
      // Remove from tasks
      delete state.tasks[taskId];
      
      // Remove from queue
      state.queue = state.queue.filter(id => id !== taskId);
      
      // Remove from active uploads
      delete state.activeUploads[taskId];
      
      // Recalculate total progress
      state.totalProgress = calculateTotalProgress(state.tasks);
    },
    
    updateUploadProgress: (
      state,
      action: PayloadAction<{
        taskId: string;
        progress: number;
        uploadedBytes: number;
        uploadSpeed?: number;
      }>
    ) => {
      const {taskId, progress, uploadedBytes, uploadSpeed} = action.payload;
      const task = state.tasks[taskId];
      
      if (task) {
        task.progress = progress;
        task.uploaded_bytes = uploadedBytes;
        if (uploadSpeed !== undefined) {
          task.upload_speed = uploadSpeed;
        }
        task.updated_at = new Date().toISOString();
        
        // Update total progress
        state.totalProgress = calculateTotalProgress(state.tasks);
      }
    },
    
    setUploadStatus: (
      state,
      action: PayloadAction<{
        taskId: string;
        status: UploadTask['status'];
        error?: string;
      }>
    ) => {
      const {taskId, status, error} = action.payload;
      const task = state.tasks[taskId];
      
      if (task) {
        task.status = status;
        task.updated_at = new Date().toISOString();
        
        if (error) {
          task.error = error;
        }
        
        // Handle status changes
        if (status === 'uploading') {
          state.activeUploads[taskId] = true;
          state.queue = state.queue.filter(id => id !== taskId);
        } else if (['completed', 'failed', 'cancelled'].includes(status)) {
          delete state.activeUploads[taskId];
          state.queue = state.queue.filter(id => id !== taskId);
          
          if (status === 'completed') {
            task.progress = 100;
            task.uploaded_bytes = task.file_size;
          }
        } else if (status === 'paused') {
          delete state.activeUploads[taskId];
        } else if (status === 'queued') {
          delete state.activeUploads[taskId];
          if (!state.queue.includes(taskId)) {
            state.queue.push(taskId);
          }
        }
        
        // Update global uploading state
        state.isUploading = Object.keys(state.activeUploads).length > 0;
        
        // Update total progress
        state.totalProgress = calculateTotalProgress(state.tasks);
      }
    },
    
    pauseUpload: (state, action: PayloadAction<string>) => {
      const taskId = action.payload;
      const task = state.tasks[taskId];
      
      if (task && task.status === 'uploading') {
        task.status = 'paused';
        task.updated_at = new Date().toISOString();
        delete state.activeUploads[taskId];
        state.isUploading = Object.keys(state.activeUploads).length > 0;
      }
    },
    
    resumeUpload: (state, action: PayloadAction<string>) => {
      const taskId = action.payload;
      const task = state.tasks[taskId];
      
      if (task && task.status === 'paused') {
        task.status = 'queued';
        task.updated_at = new Date().toISOString();
        
        if (!state.queue.includes(taskId)) {
          state.queue.unshift(taskId); // Add to front of queue
        }
      }
    },
    
    cancelUpload: (state, action: PayloadAction<string>) => {
      const taskId = action.payload;
      const task = state.tasks[taskId];
      
      if (task) {
        task.status = 'cancelled';
        task.updated_at = new Date().toISOString();
        
        // Remove from queue and active uploads
        state.queue = state.queue.filter(id => id !== taskId);
        delete state.activeUploads[taskId];
        state.isUploading = Object.keys(state.activeUploads).length > 0;
        
        // Update total progress
        state.totalProgress = calculateTotalProgress(state.tasks);
      }
    },
    
    retryUpload: (state, action: PayloadAction<string>) => {
      const taskId = action.payload;
      const task = state.tasks[taskId];
      
      if (task && task.status === 'failed') {
        task.status = 'queued';
        task.error = undefined;
        task.retry_count = (task.retry_count || 0) + 1;
        task.updated_at = new Date().toISOString();
        
        if (!state.queue.includes(taskId)) {
          state.queue.push(taskId);
        }
      }
    },
    
    clearCompletedUploads: (state) => {
      Object.keys(state.tasks).forEach(taskId => {
        const task = state.tasks[taskId];
        if (task.status === 'completed') {
          delete state.tasks[taskId];
        }
      });
      
      state.totalProgress = calculateTotalProgress(state.tasks);
    },
    
    clearFailedUploads: (state) => {
      Object.keys(state.tasks).forEach(taskId => {
        const task = state.tasks[taskId];
        if (task.status === 'failed') {
          delete state.tasks[taskId];
        }
      });
      
      state.queue = state.queue.filter(id => state.tasks[id]);
      state.totalProgress = calculateTotalProgress(state.tasks);
    },
    
    updateUploadSettings: (state, action: PayloadAction<Partial<UploadSettings>>) => {
      state.settings = {...state.settings, ...action.payload};
    },
    
    setNetworkType: (state, action: PayloadAction<string>) => {
      state.networkType = action.payload;
    },
    
    reorderQueue: (state, action: PayloadAction<string[]>) => {
      state.queue = action.payload;
    },
    
    prioritizeUpload: (state, action: PayloadAction<string>) => {
      const taskId = action.payload;
      
      // Remove from current position and add to front
      state.queue = state.queue.filter(id => id !== taskId);
      state.queue.unshift(taskId);
    },
  },
  extraReducers: (builder) => {
    // Start upload
    builder
      .addCase(startUpload.fulfilled, (state, action) => {
        const {taskId} = action.payload;
        const task = state.tasks[taskId];
        
        if (task) {
          task.status = 'uploading';
          task.started_at = new Date().toISOString();
          task.updated_at = new Date().toISOString();
          state.activeUploads[taskId] = true;
          state.queue = state.queue.filter(id => id !== taskId);
          state.isUploading = true;
        }
      })
      .addCase(startUpload.rejected, (state, action) => {
        // Handle start upload failure
        console.error('Failed to start upload:', action.payload);
      });

    // Pause upload
    builder
      .addCase(pauseUploadAsync.fulfilled, (state, action) => {
        const taskId = action.payload;
        const task = state.tasks[taskId];
        
        if (task) {
          task.status = 'paused';
          task.updated_at = new Date().toISOString();
          delete state.activeUploads[taskId];
          state.isUploading = Object.keys(state.activeUploads).length > 0;
        }
      });

    // Resume upload
    builder
      .addCase(resumeUploadAsync.fulfilled, (state, action) => {
        const taskId = action.payload;
        const task = state.tasks[taskId];
        
        if (task) {
          task.status = 'queued';
          task.updated_at = new Date().toISOString();
          
          if (!state.queue.includes(taskId)) {
            state.queue.unshift(taskId);
          }
        }
      });

    // Cancel upload
    builder
      .addCase(cancelUploadAsync.fulfilled, (state, action) => {
        const taskId = action.payload;
        const task = state.tasks[taskId];
        
        if (task) {
          task.status = 'cancelled';
          task.updated_at = new Date().toISOString();
          
          state.queue = state.queue.filter(id => id !== taskId);
          delete state.activeUploads[taskId];
          state.isUploading = Object.keys(state.activeUploads).length > 0;
          state.totalProgress = calculateTotalProgress(state.tasks);
        }
      });

    // Retry upload
    builder
      .addCase(retryUploadAsync.fulfilled, (state, action) => {
        const {taskId} = action.payload;
        const task = state.tasks[taskId];
        
        if (task) {
          task.status = 'queued';
          task.error = undefined;
          task.retry_count = (task.retry_count || 0) + 1;
          task.updated_at = new Date().toISOString();
          
          if (!state.queue.includes(taskId)) {
            state.queue.push(taskId);
          }
        }
      });

    // Update network type
    builder
      .addCase(updateNetworkType.fulfilled, (state, action) => {
        state.networkType = action.payload;
      });
  },
});

// Helper function to calculate total progress
const calculateTotalProgress = (tasks: Record<string, UploadTask>): number => {
  const taskList = Object.values(tasks);
  
  if (taskList.length === 0) return 0;
  
  const totalBytes = taskList.reduce((sum, task) => sum + task.file_size, 0);
  const uploadedBytes = taskList.reduce((sum, task) => {
    return sum + (task.file_size * (task.progress / 100));
  }, 0);
  
  return totalBytes > 0 ? (uploadedBytes / totalBytes) * 100 : 0;
};

export const {
  addUploadTask,
  removeUploadTask,
  updateUploadProgress,
  setUploadStatus,
  pauseUpload,
  resumeUpload,
  cancelUpload,
  retryUpload,
  clearCompletedUploads,
  clearFailedUploads,
  updateUploadSettings,
  setNetworkType,
  reorderQueue,
  prioritizeUpload,
} = uploadsSlice.actions;

export default uploadsSlice.reducer;