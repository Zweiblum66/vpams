export type AssetType = 'video' | 'audio' | 'image' | 'project' | 'other';

export interface Asset {
  id: string;
  name: string;
  type: AssetType;
  size: number;
  url: string;
  proxyUrl?: string;
  thumbnailUrl?: string;
  createdAt: string;
  updatedAt: string;
  metadata?: AssetMetadata;
}

export interface AssetMetadata {
  description?: string;
  tags?: string[];
  duration?: number;
  resolution?: string;
  framerate?: number;
  codec?: string;
  format?: string;
  bitrate?: number;
  waveformUrl?: string;
  custom?: Record<string, any>;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  permissions: string[];
}

export interface SearchParams {
  query?: string;
  type?: AssetType[];
  tags?: string[];
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  limit?: number;
  sort?: 'name' | 'date' | 'size';
  order?: 'asc' | 'desc';
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface ExportSettings {
  name: string;
  format: string;
  preset?: string;
  destination: 'mams' | 'local';
  metadata?: Record<string, any>;
}