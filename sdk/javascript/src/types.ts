/**
 * Type definitions for MAMS SDK
 */

// Base types
export interface BaseEntity {
  id: string;
  createdAt: string;
  updatedAt?: string;
}

// Asset types
export interface Asset extends BaseEntity {
  name: string;
  type: 'video' | 'audio' | 'image' | 'document';
  filePath: string;
  sizeBytes: number;
  checksum?: string;
  mimeType?: string;
  
  // Media properties
  duration?: number;
  width?: number;
  height?: number;
  frameRate?: number;
  bitrate?: number;
  
  // Status
  status: 'active' | 'archived' | 'deleted';
  processingStatus: 'pending' | 'processing' | 'completed' | 'failed';
  
  // Relationships
  projectId?: string;
  parentId?: string;
  version: number;
  
  // Metadata
  metadata: Record<string, any>;
  tags: string[];
}

export interface AssetCreate {
  name: string;
  type: 'video' | 'audio' | 'image' | 'document';
  filePath?: string;
  projectId?: string;
  metadata?: Record<string, any>;
  tags?: string[];
}

export interface AssetUpdate {
  name?: string;
  status?: string;
  metadata?: Record<string, any>;
  tags?: string[];
}

// Project types
export interface Project extends BaseEntity {
  name: string;
  description?: string;
  status: 'active' | 'archived' | 'completed';
  
  // Settings
  frameRate: number;
  resolution: string;
  colorSpace: string;
  
  // Metadata
  metadata: Record<string, any>;
  
  // Relationships
  ownerId: string;
  teamMembers: string[];
}

export interface ProjectCreate {
  name: string;
  description?: string;
  frameRate?: number;
  resolution?: string;
  colorSpace?: string;
  metadata?: Record<string, any>;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  status?: string;
  metadata?: Record<string, any>;
}

// Workflow types
export interface Workflow extends BaseEntity {
  name: string;
  description?: string;
  status: 'active' | 'inactive' | 'deprecated';
  
  // Definition
  definition: Record<string, any>;
  version: number;
  
  // Settings
  timeout?: number;
  maxRetries: number;
  
  // Metadata
  metadata: Record<string, any>;
  
  // Relationships
  createdBy: string;
  templateId?: string;
}

export interface WorkflowCreate {
  name: string;
  description?: string;
  definition: Record<string, any>;
  timeout?: number;
  maxRetries?: number;
  metadata?: Record<string, any>;
}

export interface WorkflowUpdate {
  name?: string;
  description?: string;
  status?: string;
  definition?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface WorkflowExecution {
  id: string;
  workflowId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  context: Record<string, any>;
  startedAt: string;
  completedAt?: string;
  error?: string;
}

// Integration types
export interface Integration extends BaseEntity {
  name: string;
  type: string;
  status: 'active' | 'inactive' | 'error';
  
  // Configuration
  config: Record<string, any>;
  
  // Settings
  enabled: boolean;
  autoSync: boolean;
  syncInterval: number;
  
  // Status
  lastSync?: string;
  lastError?: string;
  
  // Metadata
  metadata: Record<string, any>;
  
  // Relationships
  createdBy: string;
}

export interface IntegrationCreate {
  name: string;
  type: string;
  config: Record<string, any>;
  enabled?: boolean;
  autoSync?: boolean;
  syncInterval?: number;
  metadata?: Record<string, any>;
}

export interface IntegrationUpdate {
  name?: string;
  status?: string;
  config?: Record<string, any>;
  enabled?: boolean;
  autoSync?: boolean;
  syncInterval?: number;
  metadata?: Record<string, any>;
}

// User types
export interface User extends BaseEntity {
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  
  // Status
  isActive: boolean;
  isVerified: boolean;
  
  // Profile
  avatarUrl?: string;
  timezone: string;
  language: string;
  
  // Metadata
  metadata: Record<string, any>;
  
  // Timestamps
  lastLogin?: string;
}

export interface UserCreate {
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  password: string;
  timezone?: string;
  language?: string;
  metadata?: Record<string, any>;
}

export interface UserUpdate {
  email?: string;
  firstName?: string;
  lastName?: string;
  avatarUrl?: string;
  timezone?: string;
  language?: string;
  metadata?: Record<string, any>;
}

// Search types
export interface SearchQuery {
  query: string;
  index?: 'assets' | 'projects' | 'users';
  filters?: Record<string, any>;
  sort?: Array<{ field: string; order: 'asc' | 'desc' }>;
  limit?: number;
  offset?: number;
  highlight?: boolean;
}

export interface SearchResult<T = any> {
  hits: T[];
  total: number;
  facets?: Record<string, any>;
  suggestions?: string[];
  took: number;
}

// API response types
export interface ListResponse<T> {
  data: T[];
  meta: {
    page?: number;
    limit?: number;
    total?: number;
    pages?: number;
  };
  links?: {
    self?: string;
    next?: string;
    prev?: string;
    first?: string;
    last?: string;
  };
}

export interface SingleResponse<T> {
  data: T;
}

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
    timestamp: string;
    requestId?: string;
  };
}

// Request options
export interface ListOptions {
  limit?: number;
  offset?: number;
  sort?: string;
  order?: 'asc' | 'desc';
  include?: string[];
  fields?: string[];
  [key: string]: any; // For filters
}

export interface UploadOptions {
  file: File | Blob | Buffer;
  name: string;
  type: 'video' | 'audio' | 'image' | 'document';
  projectId?: string;
  metadata?: Record<string, any>;
  onProgress?: (progress: number) => void;
}

export interface DownloadOptions {
  assetId: string;
  quality?: 'original' | 'high' | 'medium' | 'low';
  format?: string;
}

// Webhook types
export interface Webhook {
  id: string;
  url: string;
  events: string[];
  secret?: string;
  headers?: Record<string, string>;
  isActive: boolean;
  createdAt: string;
  lastTriggered?: string;
}

export interface WebhookCreate {
  url: string;
  events: string[];
  secret?: string;
  headers?: Record<string, string>;
}

// Timeline types
export interface TimelineClip {
  id: string;
  assetId: string;
  trackType: 'video' | 'audio';
  trackIndex: number;
  startTime: number;
  duration: number;
  inPoint?: number;
  outPoint?: number;
  metadata?: Record<string, any>;
}

export interface Sequence {
  id: string;
  name: string;
  frameRate: number;
  resolution: string;
  duration?: number;
  clips: TimelineClip[];
  metadata?: Record<string, any>;
}

// Export types
export interface ExportOptions {
  format: 'aaf' | 'xml' | 'edl' | 'otio';
  options?: Record<string, any>;
}

export interface ExportJob {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  format: string;
  downloadUrl?: string;
  error?: string;
  progress?: number;
  createdAt: string;
  completedAt?: string;
}