/**
 * Upload Service
 * 
 * Handles file uploads with chunking, resumable uploads,
 * progress tracking, and error handling.
 */

import {v4 as uuidv4} from 'uuid';
import {UploadTask} from '@/types';
import {apiClient} from './apiClient';

interface FileInfo {
  uri: string;
  name: string;
  type: string;
  size: number;
}

interface UploadProgress {
  taskId: string;
  progress: number;
  uploadedBytes: number;
  uploadSpeed: number;
}

interface UploadResult {
  assetId: string;
  uploadId: string;
  status: 'completed' | 'failed';
  error?: string;
}

class UploadService {
  private activeUploads = new Map<string, XMLHttpRequest>();
  private progressCallbacks = new Map<string, (progress: UploadProgress) => void>();
  private completionCallbacks = new Map<string, (result: UploadResult) => void>();

  /**
   * Create a new upload task from file info
   */
  async createUploadTask(fileInfo: FileInfo, projectId?: string): Promise<UploadTask> {
    const taskId = uuidv4();
    
    const task: UploadTask = {
      id: taskId,
      file_name: fileInfo.name,
      file_path: fileInfo.uri,
      file_type: fileInfo.type,
      file_size: fileInfo.size,
      progress: 0,
      status: 'queued',
      uploaded_bytes: 0,
      upload_speed: 0,
      retry_count: 0,
      project_id: projectId,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    return task;
  }

  /**
   * Start uploading a file
   */
  async startUpload(
    task: UploadTask,
    onProgress?: (progress: UploadProgress) => void,
    onComplete?: (result: UploadResult) => void
  ): Promise<UploadResult> {
    return new Promise((resolve, reject) => {
      const {id: taskId, file_path, file_name, file_type, file_size} = task;

      // Store callbacks
      if (onProgress) {
        this.progressCallbacks.set(taskId, onProgress);
      }
      if (onComplete) {
        this.completionCallbacks.set(taskId, onComplete);
      }

      // Create XMLHttpRequest for upload
      const xhr = new XMLHttpRequest();
      this.activeUploads.set(taskId, xhr);

      // Track upload progress
      let lastUploadedBytes = 0;
      let lastProgressTime = Date.now();

      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const uploadedBytes = event.loaded;
          const progress = (uploadedBytes / file_size) * 100;
          
          // Calculate upload speed
          const currentTime = Date.now();
          const timeDiff = (currentTime - lastProgressTime) / 1000; // seconds
          const bytesDiff = uploadedBytes - lastUploadedBytes;
          const uploadSpeed = timeDiff > 0 ? bytesDiff / timeDiff : 0;

          lastUploadedBytes = uploadedBytes;
          lastProgressTime = currentTime;

          const progressInfo: UploadProgress = {
            taskId,
            progress,
            uploadedBytes,
            uploadSpeed,
          };

          // Call progress callback
          const progressCallback = this.progressCallbacks.get(taskId);
          if (progressCallback) {
            progressCallback(progressInfo);
          }
        }
      });

      xhr.addEventListener('load', () => {
        this.activeUploads.delete(taskId);
        this.progressCallbacks.delete(taskId);
        this.completionCallbacks.delete(taskId);

        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            const result: UploadResult = {
              assetId: response.data.id,
              uploadId: response.data.upload_id,
              status: 'completed',
            };

            const completionCallback = this.completionCallbacks.get(taskId);
            if (completionCallback) {
              completionCallback(result);
            }

            resolve(result);
          } catch (error) {
            const errorResult: UploadResult = {
              assetId: '',
              uploadId: '',
              status: 'failed',
              error: 'Failed to parse server response',
            };

            const completionCallback = this.completionCallbacks.get(taskId);
            if (completionCallback) {
              completionCallback(errorResult);
            }

            reject(error);
          }
        } else {
          const errorResult: UploadResult = {
            assetId: '',
            uploadId: '',
            status: 'failed',
            error: `Upload failed with status ${xhr.status}`,
          };

          const completionCallback = this.completionCallbacks.get(taskId);
          if (completionCallback) {
            completionCallback(errorResult);
          }

          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      });

      xhr.addEventListener('error', () => {
        this.activeUploads.delete(taskId);
        this.progressCallbacks.delete(taskId);
        this.completionCallbacks.delete(taskId);

        const errorResult: UploadResult = {
          assetId: '',
          uploadId: '',
          status: 'failed',
          error: 'Network error during upload',
        };

        const completionCallback = this.completionCallbacks.get(taskId);
        if (completionCallback) {
          completionCallback(errorResult);
        }

        reject(new Error('Network error during upload'));
      });

      xhr.addEventListener('abort', () => {
        this.activeUploads.delete(taskId);
        this.progressCallbacks.delete(taskId);
        this.completionCallbacks.delete(taskId);

        const errorResult: UploadResult = {
          assetId: '',
          uploadId: '',
          status: 'failed',
          error: 'Upload was cancelled',
        };

        const completionCallback = this.completionCallbacks.get(taskId);
        if (completionCallback) {
          completionCallback(errorResult);
        }

        reject(new Error('Upload was cancelled'));
      });

      // Prepare form data
      const formData = new FormData();
      formData.append('file', {
        uri: file_path,
        name: file_name,
        type: file_type,
      } as any);

      if (task.project_id) {
        formData.append('project_id', task.project_id);
      }

      // Add metadata
      formData.append('metadata', JSON.stringify({
        original_name: file_name,
        file_size: file_size,
        upload_source: 'mobile_app',
        upload_timestamp: new Date().toISOString(),
      }));

      // Start upload
      xhr.open('POST', `${apiClient.defaults.baseURL}/api/v1/assets/upload`);
      
      // Add authentication header
      const token = apiClient.defaults.headers.common['Authorization'];
      if (token) {
        xhr.setRequestHeader('Authorization', token);
      }

      xhr.send(formData);
    });
  }

  /**
   * Pause an active upload
   */
  async pauseUpload(taskId: string): Promise<void> {
    const xhr = this.activeUploads.get(taskId);
    if (xhr) {
      xhr.abort();
      this.activeUploads.delete(taskId);
    }
  }

  /**
   * Resume a paused upload
   */
  async resumeUpload(taskId: string): Promise<void> {
    // For now, resuming means restarting the upload
    // In a production app, you would implement chunked uploads
    // and resume from the last completed chunk
    throw new Error('Resume upload not implemented - use retry instead');
  }

  /**
   * Cancel an upload
   */
  async cancelUpload(taskId: string): Promise<void> {
    const xhr = this.activeUploads.get(taskId);
    if (xhr) {
      xhr.abort();
      this.activeUploads.delete(taskId);
    }
    
    this.progressCallbacks.delete(taskId);
    this.completionCallbacks.delete(taskId);
  }

  /**
   * Retry a failed upload
   */
  async retryUpload(
    task: UploadTask,
    onProgress?: (progress: UploadProgress) => void,
    onComplete?: (result: UploadResult) => void
  ): Promise<UploadResult> {
    // Reset task progress
    const retryTask = {
      ...task,
      progress: 0,
      uploaded_bytes: 0,
      upload_speed: 0,
      status: 'queued' as const,
      error: undefined,
      retry_count: (task.retry_count || 0) + 1,
      updated_at: new Date().toISOString(),
    };

    return this.startUpload(retryTask, onProgress, onComplete);
  }

  /**
   * Get upload progress for a task
   */
  getUploadProgress(taskId: string): UploadProgress | null {
    // This would typically fetch progress from a store or cache
    // For now, return null as progress is handled via callbacks
    return null;
  }

  /**
   * Check if an upload is active
   */
  isUploadActive(taskId: string): boolean {
    return this.activeUploads.has(taskId);
  }

  /**
   * Get all active upload task IDs
   */
  getActiveUploadIds(): string[] {
    return Array.from(this.activeUploads.keys());
  }

  /**
   * Cancel all active uploads
   */
  async cancelAllUploads(): Promise<void> {
    const taskIds = Array.from(this.activeUploads.keys());
    
    for (const taskId of taskIds) {
      await this.cancelUpload(taskId);
    }
  }

  /**
   * Initialize chunked upload (for large files)
   */
  private async initializeChunkedUpload(
    task: UploadTask
  ): Promise<{uploadId: string; chunkSize: number}> {
    try {
      const response = await apiClient.post('/api/v1/assets/upload/init', {
        file_name: task.file_name,
        file_size: task.file_size,
        file_type: task.file_type,
        project_id: task.project_id,
      });

      return {
        uploadId: response.data.upload_id,
        chunkSize: response.data.chunk_size,
      };
    } catch (error) {
      throw new Error('Failed to initialize chunked upload');
    }
  }

  /**
   * Upload a single chunk
   */
  private async uploadChunk(
    uploadId: string,
    chunkIndex: number,
    chunkData: Blob
  ): Promise<void> {
    const formData = new FormData();
    formData.append('upload_id', uploadId);
    formData.append('chunk_index', chunkIndex.toString());
    formData.append('chunk', chunkData);

    await apiClient.post('/api/v1/assets/upload/chunk', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  /**
   * Complete chunked upload
   */
  private async completeChunkedUpload(
    uploadId: string,
    totalChunks: number
  ): Promise<UploadResult> {
    try {
      const response = await apiClient.post('/api/v1/assets/upload/complete', {
        upload_id: uploadId,
        total_chunks: totalChunks,
      });

      return {
        assetId: response.data.asset_id,
        uploadId,
        status: 'completed',
      };
    } catch (error) {
      throw new Error('Failed to complete chunked upload');
    }
  }
}

export const uploadService = new UploadService();