export interface UploadFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  status: UploadStatus;
  progress: number;
  error?: string;
  assetId?: string;
  uploadedAt?: string;
  startedAt?: string;
  completedAt?: string;
  chunkSize?: number;
  totalChunks?: number;
  uploadedChunks?: number;
  sessionId?: string;
  metadata?: UploadMetadata;
}

export enum UploadStatus {
  PENDING = 'pending',
  PREPARING = 'preparing',
  UPLOADING = 'uploading',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  ERROR = 'error',
  CANCELLED = 'cancelled',
  PAUSED = 'paused'
}

export interface UploadMetadata {
  title?: string;
  description?: string;
  tags?: string[];
  projectId?: string;
  folderId?: string;
  customFields?: Record<string, any>;
}

export interface UploadSession {
  id: string;
  fileId: string;
  fileName: string;
  fileSize: number;
  chunkSize: number;
  totalChunks: number;
  uploadedChunks: number;
  uploadedBytes: number;
  status: UploadStatus;
  createdAt: string;
  expiresAt: string;
  uploadUrl?: string;
  checksum?: string;
}

export interface ChunkUploadProgress {
  chunkIndex: number;
  bytesUploaded: number;
  totalBytes: number;
  progress: number;
}

export interface UploadConfig {
  maxFileSize: number; // in bytes
  chunkSize: number; // in bytes
  maxConcurrentUploads: number;
  supportedFileTypes: string[];
  autoRetry: boolean;
  retryAttempts: number;
  retryDelay: number; // in milliseconds
}

export interface UploadQueueItem {
  file: UploadFile;
  priority: number;
  addedAt: string;
}

export interface UploadStats {
  totalFiles: number;
  totalBytes: number;
  uploadedFiles: number;
  uploadedBytes: number;
  failedFiles: number;
  averageSpeed: number; // bytes per second
  remainingTime: number; // in seconds
}