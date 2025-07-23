export interface Asset {
  id: string;
  name: string;
  fileName: string;
  fileSize: number;
  mimeType: string;
  type: AssetType;
  status: AssetStatus;
  thumbnailUrl?: string;
  previewUrl?: string;
  originalUrl: string;
  metadata: AssetMetadata;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  updatedBy?: string;
  projectId?: string;
  folderId?: string;
  permissions: AssetPermissions;
  duration?: number; // For video/audio in seconds
  dimensions?: {
    width: number;
    height: number;
  };
  versions?: AssetVersion[];
  
  // Video-specific properties
  proxyUrls?: {
    low?: string;
    medium?: string;
    high?: string;
    original: string;
  };
  resolution?: {
    width: number;
    height: number;
  };
  subtitles?: SubtitleTrack[];
}

export enum AssetType {
  VIDEO = 'video',
  AUDIO = 'audio',
  IMAGE = 'image',
  DOCUMENT = 'document',
  OTHER = 'other'
}

export enum AssetStatus {
  UPLOADING = 'uploading',
  PROCESSING = 'processing',
  READY = 'ready',
  ERROR = 'error',
  ARCHIVED = 'archived'
}

export interface AssetMetadata {
  format?: string;
  codec?: string;
  bitrate?: number;
  frameRate?: number;
  sampleRate?: number;
  channels?: number;
  colorSpace?: string;
  camera?: string;
  lens?: string;
  location?: {
    latitude: number;
    longitude: number;
  };
  customFields?: Record<string, any>;
}

export interface AssetVersion {
  id: string;
  version: number;
  fileName: string;
  fileSize: number;
  createdAt: string;
  createdBy: string;
  comment?: string;
}

export interface AssetPermissions {
  canView: boolean;
  canEdit: boolean;
  canDelete: boolean;
  canShare: boolean;
  canDownload: boolean;
}

export interface AssetFilter {
  search?: string;
  types?: AssetType[];
  status?: AssetStatus[];
  tags?: string[];
  projectId?: string;
  folderId?: string;
  dateFrom?: string;
  dateTo?: string;
  sizeMin?: number;
  sizeMax?: number;
  createdBy?: string;
}

export interface AssetSort {
  field: 'name' | 'createdAt' | 'updatedAt' | 'fileSize' | 'type';
  order: 'asc' | 'desc';
}

export interface AssetListResponse {
  assets: Asset[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface AssetUploadRequest {
  file: File;
  name?: string;
  tags?: string[];
  projectId?: string;
  folderId?: string;
  metadata?: Partial<AssetMetadata>;
}

export interface AssetUpdateRequest {
  name?: string;
  tags?: string[];
  metadata?: Partial<AssetMetadata>;
}

export interface AssetBulkAction {
  action: 'delete' | 'archive' | 'tag' | 'move' | 'share';
  assetIds: string[];
  data?: any;
}

export interface SubtitleTrack {
  id: string;
  language: string;
  label: string;
  kind: 'subtitles' | 'captions' | 'descriptions' | 'chapters' | 'metadata';
  src: string;
  srclang: string;
  default?: boolean;
}