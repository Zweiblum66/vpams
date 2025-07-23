// User types
export interface User {
  user_id: string;
  email: string;
  username?: string;
  first_name: string;
  last_name: string;
  display_name?: string;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  last_login_at?: string;
  created_at: string;
  updated_at: string;
  permissions?: string[];
  roles?: string[];
  groups?: string[];
}

export interface UserProfile {
  user_id: string;
  phone?: string;
  department?: string;
  job_title?: string;
  organization?: string;
  location?: string;
  timezone?: string;
  language?: string;
  avatar_url?: string;
  bio?: string;
  website?: string;
  preferences?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface UserCreateRequest {
  email: string;
  password: string;
  confirm_password: string;
  first_name: string;
  last_name: string;
  username?: string;
  organization?: string;
  department?: string;
  job_title?: string;
  phone?: string;
  timezone?: string;
  language?: string;
}

export interface UserUpdateRequest {
  first_name?: string;
  last_name?: string;
  display_name?: string;
  username?: string;
  phone?: string;
  department?: string;
  job_title?: string;
  organization?: string;
  location?: string;
  timezone?: string;
  language?: string;
  bio?: string;
  website?: string;
  preferences?: Record<string, any>;
}

// Role types
export interface Role {
  role_id: string;
  name: string;
  display_name: string;
  description?: string;
  role_type: string;
  is_active: boolean;
  created_at: string;
}

export interface RoleCreateRequest {
  name: string;
  display_name: string;
  description?: string;
  role_type: string;
  parent_role_id?: string;
}

export interface RoleUpdateRequest {
  display_name?: string;
  description?: string;
  parent_role_id?: string;
  is_active?: boolean;
}

// Permission types
export interface Permission {
  permission_id: string;
  name: string;
  display_name: string;
  description?: string;
  resource: string;
  action: string;
  category: string;
  scope: string;
}

export interface PermissionCreateRequest {
  name: string;
  display_name: string;
  description?: string;
  resource: string;
  action: string;
  category: string;
  scope: string;
}

export interface PermissionUpdateRequest {
  display_name?: string;
  description?: string;
  category?: string;
  scope?: string;
  is_active?: boolean;
}

// Group types
export interface Group {
  group_id: string;
  name: string;
  display_name: string;
  description?: string;
  group_type: string;
  parent_group_id?: string;
  max_members?: number;
  is_active: boolean;
  is_system: boolean;
  member_count?: number;
  created_at: string;
  updated_at: string;
}

export interface GroupCreateRequest {
  name: string;
  display_name: string;
  description?: string;
  group_type: string;
  parent_group_id?: string;
  max_members?: number;
}

export interface GroupUpdateRequest {
  display_name?: string;
  description?: string;
  parent_group_id?: string;
  max_members?: number;
  is_active?: boolean;
}

// Inheritance types
export interface PermissionSource {
  permission_name: string;
  source_type: string;
  source_id: string;
  source_name: string;
  priority: number;
  granted_at?: string;
  granted_by?: string;
}

export interface InheritanceStatistics {
  total_permissions: number;
  source_breakdown: Record<string, number>;
  max_role_inheritance_depth: number;
  max_group_inheritance_depth: number;
  inheritance_complexity: number;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
  error?: any;
}

export interface PaginatedResponse<T> {
  success: boolean;
  message?: string;
  data: T[];
  meta: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

// UI State types
export interface LoadingState {
  isLoading: boolean;
  error?: string;
}

export interface TableState {
  page: number;
  pageSize: number;
  sortModel: Array<{
    field: string;
    sort: 'asc' | 'desc';
  }>;
  filterModel: Record<string, any>;
}

// Form types
export interface FormErrors {
  [key: string]: string;
}

export interface FormState<T> {
  values: T;
  errors: FormErrors;
  touched: Record<string, boolean>;
  isSubmitting: boolean;
  isValid: boolean;
}

// Auth types
export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface LoginResponse {
  user: User;
  tokens: {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
  };
}

// Notification types
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

// Asset-related types
export interface Asset {
  id: string;
  name: string;
  description?: string;
  asset_type: AssetType;
  mime_type: string;
  file_size: number;
  file_path: string;
  thumbnail_path?: string;
  proxy_path?: string;
  duration?: number;
  width?: number;
  height?: number;
  frame_rate?: number;
  bit_rate?: number;
  checksum: string;
  status: AssetStatus;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
  metadata?: AssetMetadata;
  tags: string[];
  project_id?: string;
  container_id?: string;
}

export type AssetType = 'video' | 'audio' | 'image' | 'document' | 'other';
export type AssetStatus = 'processing' | 'ready' | 'failed' | 'archived';

export interface AssetMetadata {
  [key: string]: any;
  title?: string;
  description?: string;
  keywords?: string[];
  creator?: string;
  subject?: string;
  format?: string;
  language?: string;
  copyright?: string;
  creation_date?: string;
  location?: string;
  camera?: string;
  lens?: string;
  iso?: number;
  aperture?: string;
  shutter_speed?: string;
  focal_length?: number;
}

export interface CreateAssetRequest {
  name: string;
  description?: string;
  asset_type: AssetType;
  project_id?: string;
  container_id?: string;
  tags?: string[];
  metadata?: AssetMetadata;
}

export interface UpdateAssetRequest {
  name?: string;
  description?: string;
  tags?: string[];
  metadata?: AssetMetadata;
  project_id?: string;
  container_id?: string;
}

// Project-related types
export interface Project {
  id: string;
  name: string;
  description?: string;
  status: ProjectStatus;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
  start_date?: string;
  end_date?: string;
  containers: ProjectContainer[];
  assets_count: number;
  storage_used: number;
}

export type ProjectStatus = 'active' | 'archived' | 'completed' | 'on_hold';

export interface ProjectContainer {
  id: string;
  name: string;
  type: ContainerType;
  parent_id?: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  assets_count: number;
  children?: ProjectContainer[];
}

export type ContainerType = 'folder' | 'bin' | 'shotlist' | 'sequence';

export interface CreateProjectRequest {
  name: string;
  description?: string;
  start_date?: string;
  end_date?: string;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  status?: ProjectStatus;
  start_date?: string;
  end_date?: string;
}

// Search-related types
export interface SearchQuery {
  query: string;
  search_type?: 'basic' | 'advanced' | 'fuzzy' | 'semantic';
  indices?: string[];
  filters?: Record<string, any>;
  size?: number;
  from?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  highlight?: boolean;
}

export interface SearchResult {
  id: string;
  index: string;
  score: number;
  source: Record<string, any>;
  highlight?: Record<string, string[]>;
}

export interface SearchResponse {
  query: string;
  total_hits: number;
  max_score: number;
  took: number;
  timed_out: boolean;
  hits: SearchResult[];
  page: number;
  per_page: number;
  total_pages: number;
  facets?: FacetResult[];
  applied_filters?: FilterCondition[];
}

export interface FacetResult {
  name: string;
  type: string;
  buckets: FacetBucket[];
}

export interface FacetBucket {
  key: string;
  doc_count: number;
  from?: number;
  to?: number;
}

export interface FilterCondition {
  field: string;
  type: string;
  value: any;
  nested_path?: string;
}

export interface SavedSearch {
  id: string;
  name: string;
  description?: string;
  query: SearchQuery;
  is_public: boolean;
  tags: string[];
  alert_enabled: boolean;
  user_id: string;
  created_at: string;
  updated_at: string;
  usage_count: number;
  last_used_at?: string;
}

export interface CreateSavedSearchRequest {
  name: string;
  description?: string;
  query: SearchQuery;
  is_public?: boolean;
  tags?: string[];
  alert_enabled?: boolean;
}

// Upload-related types
export interface UploadProgress {
  filename: string;
  progress: number;
  speed: number;
  eta: number;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  error?: string;
}

export interface UploadSession {
  id: string;
  filename: string;
  file_size: number;
  chunk_size: number;
  total_chunks: number;
  uploaded_chunks: number;
  created_at: string;
  expires_at: string;
  status: 'active' | 'completed' | 'failed' | 'expired';
}

// Media Player types
export interface MediaPlayerState {
  playing: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  muted: boolean;
  playbackRate: number;
  seeking: boolean;
  buffered: TimeRange[];
  error?: string;
}

export interface TimeRange {
  start: number;
  end: number;
}

export interface MediaMarker {
  id: string;
  time: number;
  type: 'cue' | 'chapter' | 'annotation';
  title: string;
  description?: string;
  color?: string;
}

// Shotlist types
export interface ShotlistItem {
  id: string;
  asset_id: string;
  in_point: number;
  out_point: number;
  duration: number;
  order: number;
  title?: string;
  description?: string;
  notes?: string;
  color?: string;
  created_at: string;
  updated_at: string;
  asset: Asset;
}

export interface CreateShotlistItemRequest {
  asset_id: string;
  in_point: number;
  out_point: number;
  title?: string;
  description?: string;
  notes?: string;
  color?: string;
}

// Storage types
export interface StorageDriver {
  type: 'local' | 's3' | 'azure' | 'gcs' | 'dropbox' | 'onedrive' | 'ftp' | 'sftp';
  name: string;
  config: Record<string, any>;
  is_active: boolean;
  is_default: boolean;
  tier: 'hot' | 'warm' | 'cold' | 'archive';
  created_at: string;
  updated_at: string;
}

export interface StorageStats {
  total_size: number;
  used_size: number;
  available_size: number;
  file_count: number;
  by_type: Record<string, number>;
  by_tier: Record<string, number>;
}

// UI State types
export interface ViewMode {
  type: 'grid' | 'list' | 'table';
  itemsPerPage: number;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
}

export interface FilterState {
  active: boolean;
  filters: Record<string, any>;
  facets: FacetResult[];
}

export interface SelectionState {
  selectedItems: string[];
  lastSelected?: string;
  selectAll: boolean;
}

// Theme types
export interface ThemeState {
  mode: 'light' | 'dark';
  primaryColor: string;
  sidebarOpen: boolean;
}

// Timeline types
export interface Timeline {
  id: string;
  name: string;
  description?: string;
  project_id: string;
  duration: number;
  frame_rate: number;
  resolution: string;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
  tracks: TimelineTrack[];
  version: number;
  status: 'draft' | 'in_progress' | 'completed' | 'archived';
}

export interface TimelineTrack {
  id: string;
  name: string;
  type: 'video' | 'audio' | 'subtitle' | 'graphics';
  visible: boolean;
  locked: boolean;
  muted: boolean;
  solo: boolean;
  height: number;
  color: string;
  clips: TimelineClip[];
  order: number;
  groupId?: string;
  effects?: TrackEffect[];
  volume?: number;
  pan?: number;
}

export interface TimelineClip {
  id: string;
  name: string;
  asset_id: string;
  track_id: string;
  start_time: number;
  end_time: number;
  duration: number;
  in_point: number;
  out_point: number;
  speed: number;
  volume: number;
  color: string;
  effects: TimelineEffect[];
  transitions: TimelineTransition[];
  asset: {
    id: string;
    name: string;
    asset_type: string;
    thumbnail_path?: string;
    duration?: number;
  };
  enabled?: boolean;
  opacity?: number;
  blend_mode?: string;
}

export interface TimelineEffect {
  id: string;
  name: string;
  type: string;
  parameters: Record<string, any>;
  enabled: boolean;
  keyframes?: Keyframe[];
  start_time?: number;
  end_time?: number;
}

export interface TimelineTransition {
  id: string;
  name: string;
  type: string;
  duration: number;
  parameters: Record<string, any>;
  position: 'in' | 'out';
}

export interface TrackEffect {
  id: string;
  name: string;
  type: string;
  parameters: Record<string, any>;
  enabled: boolean;
  bypass?: boolean;
}

export interface TrackGroup {
  id: string;
  name: string;
  color: string;
  collapsed: boolean;
  muted: boolean;
  solo: boolean;
  tracks: string[];
  order: number;
  visible?: boolean;
  locked?: boolean;
}

export interface Keyframe {
  time: number;
  value: any;
  interpolation?: 'linear' | 'bezier' | 'hold';
  in_tangent?: number;
  out_tangent?: number;
}

export interface TimelineMarker {
  id: string;
  time: number;
  type: 'cue' | 'chapter' | 'edit' | 'sync';
  title: string;
  description?: string;
  color?: string;
  duration?: number;
}

export interface TimelineSettings {
  frame_rate: number;
  resolution: string;
  audio_sample_rate: number;
  audio_channels: number;
  timecode_format: 'drop_frame' | 'non_drop_frame';
  default_transition_duration: number;
  snap_to_grid: boolean;
  grid_size: number;
  auto_save_interval: number;
}

export interface TimelineExportOptions {
  format: 'aaf' | 'xml' | 'edl' | 'otio' | 'resolve';
  include_media: boolean;
  include_effects: boolean;
  include_audio: boolean;
  frame_rate?: number;
  resolution?: string;
  start_time?: number;
  end_time?: number;
  tracks?: string[];
}

export interface TimelineVersion {
  id: string;
  version: number;
  timeline_id: string;
  description?: string;
  created_by: string;
  created_at: string;
  is_current: boolean;
  data_snapshot: string;
}

export interface TimelineComment {
  id: string;
  timeline_id: string;
  user_id: string;
  timestamp: number;
  track_id?: string;
  clip_id?: string;
  text: string;
  resolved: boolean;
  created_at: string;
  updated_at: string;
  user: {
    id: string;
    name: string;
    avatar_url?: string;
  };
  replies?: TimelineComment[];
}

// Re-export workflow types
export * from './workflow';