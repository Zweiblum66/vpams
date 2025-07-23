import { apiClient } from './apiClient';
import { logger } from '../utils/logger';
import {
  UploadFile,
  UploadStatus,
  UploadSession,
  ChunkUploadProgress,
  UploadConfig,
  UploadMetadata,
} from '../types/upload';
import { v4 as uuidv4 } from 'uuid';

export class UploadServiceError extends Error {
  constructor(
    message: string,
    public code?: string,
    public fileId?: string
  ) {
    super(message);
    this.name = 'UploadServiceError';
  }
}

class UploadService {
  private activeUploads: Map<string, AbortController> = new Map();
  private uploadQueue: UploadFile[] = [];
  private config: UploadConfig = {
    maxFileSize: 10 * 1024 * 1024 * 1024, // 10GB
    chunkSize: 5 * 1024 * 1024, // 5MB
    maxConcurrentUploads: 3,
    supportedFileTypes: [
      'video/*',
      'audio/*',
      'image/*',
      'application/pdf',
      'application/zip',
      'text/*',
    ],
    autoRetry: true,
    retryAttempts: 3,
    retryDelay: 1000,
  };

  async createUploadSession(file: File): Promise<UploadSession> {
    try {
      logger.info('Creating upload session', {
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type,
        actionType: 'upload_create_session',
      });

      const response = await apiClient.post<UploadSession>('/api/v1/uploads/sessions', {
        fileName: file.name,
        fileSize: file.size,
        mimeType: file.type,
        chunkSize: this.config.chunkSize,
      });

      logger.info('Upload session created', {
        sessionId: response.data.id,
        totalChunks: response.data.totalChunks,
        actionType: 'upload_create_session_success',
      });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.message || 'Failed to create upload session';
      logger.error('Failed to create upload session', {
        error,
        fileName: file.name,
        actionType: 'upload_create_session_error',
      });
      throw new UploadServiceError(message, 'SESSION_CREATE_FAILED');
    }
  }

  async uploadChunk(
    sessionId: string,
    chunkIndex: number,
    chunk: Blob,
    onProgress?: (progress: ChunkUploadProgress) => void
  ): Promise<void> {
    const abortController = new AbortController();
    this.activeUploads.set(`${sessionId}-${chunkIndex}`, abortController);

    try {
      logger.debug('Uploading chunk', {
        sessionId,
        chunkIndex,
        chunkSize: chunk.size,
        actionType: 'upload_chunk',
      });

      const formData = new FormData();
      formData.append('chunk', chunk);
      formData.append('chunkIndex', chunkIndex.toString());

      await apiClient.post(
        `/api/v1/uploads/sessions/${sessionId}/chunks`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          signal: abortController.signal,
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total && onProgress) {
              const progress: ChunkUploadProgress = {
                chunkIndex,
                bytesUploaded: progressEvent.loaded,
                totalBytes: progressEvent.total,
                progress: (progressEvent.loaded / progressEvent.total) * 100,
              };
              onProgress(progress);
            }
          },
        }
      );

      logger.debug('Chunk uploaded successfully', {
        sessionId,
        chunkIndex,
        actionType: 'upload_chunk_success',
      });
    } catch (error: any) {
      if (error.name === 'CanceledError') {
        logger.info('Chunk upload cancelled', {
          sessionId,
          chunkIndex,
          actionType: 'upload_chunk_cancelled',
        });
        throw new UploadServiceError('Upload cancelled', 'UPLOAD_CANCELLED');
      }

      logger.error('Failed to upload chunk', {
        sessionId,
        chunkIndex,
        error,
        actionType: 'upload_chunk_error',
      });

      throw new UploadServiceError(
        error.response?.data?.message || 'Failed to upload chunk',
        'CHUNK_UPLOAD_FAILED'
      );
    } finally {
      this.activeUploads.delete(`${sessionId}-${chunkIndex}`);
    }
  }

  async completeUpload(
    sessionId: string,
    metadata?: UploadMetadata
  ): Promise<{ assetId: string }> {
    try {
      logger.info('Completing upload', {
        sessionId,
        actionType: 'upload_complete',
      });

      const response = await apiClient.post<{ assetId: string }>(
        `/api/v1/uploads/sessions/${sessionId}/complete`,
        metadata || {}
      );

      logger.info('Upload completed successfully', {
        sessionId,
        assetId: response.data.assetId,
        actionType: 'upload_complete_success',
      });

      return response.data;
    } catch (error: any) {
      logger.error('Failed to complete upload', {
        sessionId,
        error,
        actionType: 'upload_complete_error',
      });

      throw new UploadServiceError(
        error.response?.data?.message || 'Failed to complete upload',
        'UPLOAD_COMPLETE_FAILED'
      );
    }
  }

  async uploadFile(
    file: File,
    metadata?: UploadMetadata,
    onProgress?: (progress: number) => void
  ): Promise<string> {
    const uploadId = uuidv4();

    try {
      // Validate file
      this.validateFile(file);

      // Create upload session
      const session = await this.createUploadSession(file);

      // Calculate chunks
      const totalChunks = Math.ceil(file.size / this.config.chunkSize);
      let uploadedChunks = 0;

      // Upload chunks
      for (let i = 0; i < totalChunks; i++) {
        const start = i * this.config.chunkSize;
        const end = Math.min(start + this.config.chunkSize, file.size);
        const chunk = file.slice(start, end);

        await this.uploadChunk(session.id, i, chunk, (chunkProgress) => {
          const overallProgress =
            ((uploadedChunks + chunkProgress.progress / 100) / totalChunks) * 100;
          onProgress?.(overallProgress);
        });

        uploadedChunks++;
        onProgress?.((uploadedChunks / totalChunks) * 100);
      }

      // Complete upload
      const { assetId } = await this.completeUpload(session.id, metadata);

      return assetId;
    } catch (error) {
      logger.error('File upload failed', {
        uploadId,
        fileName: file.name,
        error,
        actionType: 'upload_file_error',
      });
      throw error;
    }
  }

  async resumeUpload(
    sessionId: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<string> {
    try {
      logger.info('Resuming upload', {
        sessionId,
        fileName: file.name,
        actionType: 'upload_resume',
      });

      // Get session status
      const response = await apiClient.get<UploadSession>(
        `/api/v1/uploads/sessions/${sessionId}`
      );
      const session = response.data;

      // Validate session
      if (session.status === UploadStatus.COMPLETED) {
        throw new UploadServiceError('Upload already completed', 'ALREADY_COMPLETED');
      }

      if (session.fileName !== file.name || session.fileSize !== file.size) {
        throw new UploadServiceError('File mismatch', 'FILE_MISMATCH');
      }

      // Resume from last uploaded chunk
      const startChunk = session.uploadedChunks;
      const totalChunks = session.totalChunks;

      for (let i = startChunk; i < totalChunks; i++) {
        const start = i * session.chunkSize;
        const end = Math.min(start + session.chunkSize, file.size);
        const chunk = file.slice(start, end);

        await this.uploadChunk(session.id, i, chunk, (chunkProgress) => {
          const overallProgress =
            ((startChunk + i - startChunk + chunkProgress.progress / 100) / totalChunks) * 100;
          onProgress?.(overallProgress);
        });
      }

      // Complete upload
      const { assetId } = await this.completeUpload(session.id);

      logger.info('Upload resumed successfully', {
        sessionId,
        assetId,
        actionType: 'upload_resume_success',
      });

      return assetId;
    } catch (error: any) {
      logger.error('Failed to resume upload', {
        sessionId,
        error,
        actionType: 'upload_resume_error',
      });
      throw error;
    }
  }

  cancelUpload(uploadId: string): void {
    const controller = this.activeUploads.get(uploadId);
    if (controller) {
      controller.abort();
      this.activeUploads.delete(uploadId);
      logger.info('Upload cancelled', {
        uploadId,
        actionType: 'upload_cancel',
      });
    }
  }

  cancelAllUploads(): void {
    this.activeUploads.forEach((controller, uploadId) => {
      controller.abort();
      logger.info('Upload cancelled', {
        uploadId,
        actionType: 'upload_cancel_all',
      });
    });
    this.activeUploads.clear();
  }

  validateFile(file: File): void {
    // Check file size
    if (file.size > this.config.maxFileSize) {
      throw new UploadServiceError(
        `File size exceeds maximum allowed size of ${this.formatFileSize(this.config.maxFileSize)}`,
        'FILE_TOO_LARGE'
      );
    }

    // Check file type
    const isSupported = this.config.supportedFileTypes.some((type) => {
      if (type.endsWith('/*')) {
        const category = type.split('/')[0];
        return file.type.startsWith(category + '/');
      }
      return file.type === type;
    });

    if (!isSupported) {
      throw new UploadServiceError(
        `File type "${file.type}" is not supported`,
        'UNSUPPORTED_FILE_TYPE'
      );
    }
  }

  private formatFileSize(bytes: number): string {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${size.toFixed(2)} ${units[unitIndex]}`;
  }

  getConfig(): UploadConfig {
    return { ...this.config };
  }

  updateConfig(config: Partial<UploadConfig>): void {
    this.config = { ...this.config, ...config };
    logger.info('Upload config updated', {
      config,
      actionType: 'upload_config_update',
    });
  }

  isFileSupported(file: File): boolean {
    try {
      this.validateFile(file);
      return true;
    } catch {
      return false;
    }
  }
}

export const uploadService = new UploadService();