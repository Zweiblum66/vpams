/**
 * MAMS Mobile Type Definitions
 * 
 * Centralized type definitions for the mobile application,
 * including API response types, navigation types, and app state types.
 */

// Navigation types
export type RootStackParamList = {
  // Auth stack
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
  
  // Main app stack
  MainTabs: undefined;
  
  // Asset related screens
  AssetDetail: {assetId: string};
  AssetViewer: {assetId: string; assetType: 'image' | 'video' | 'audio' | 'document'};
  AssetEditor: {assetId: string};
  
  // Upload screens
  Upload: undefined;
  CameraCapture: undefined;
  CameraScreen: undefined;
  
  // Project screens
  ProjectDetail: {projectId: string};
  ProjectAssets: {projectId: string};
  
  // Settings screens
  Settings: undefined;
  Profile: undefined;
  DownloadSettings: undefined;
  
  // Notification screens
  Notifications: undefined;
  NotificationSettings: undefined;
  
  // Search screens
  Search: {query?: string};
  SearchFilters: undefined;
  
  // Location screens
  LocationTagging: {
    assetId?: string;
    onLocationSelected?: (location: LocationTag) => void;
    mode?: 'select' | 'manage';
  };
  LocationSettings: undefined;
  
  // Voice Note screens
  VoiceNote: undefined;
  VoiceNoteSettings: undefined;
  
  // AR screens
  ARPreview: {assetId: string; previewType?: string};
  ARGallery: {initialAssetId?: string; projectId?: string};
  ARMeasure: {assetId: string};
  
  // Editing screens
  Editing: {assetId: string};
  EditingExport: {projectId: string};
};

export type MainTabParamList = {
  Home: undefined;
  Browse: undefined;
  Upload: undefined;
  Projects: undefined;
  Offline: undefined;
  Profile: undefined;
};

// API Types
export interface ApiResponse<T = any> {
  data: T;
  meta?: {
    page?: number;
    limit?: number;
    total?: number;
    pages?: number;
  };
  links?: {
    self?: string;
    next?: string;
    prev?: string;
  };
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
    timestamp: string;
    request_id?: string;
  };
}

// User types
export interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  avatar_url?: string;
  roles: Role[];
  groups: Group[];
  preferences: UserPreferences;
  created_at: string;
  updated_at: string;
  last_login?: string;
  is_active: boolean;
  is_verified: boolean;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
}

export interface Permission {
  id: string;
  name: string;
  description: string;
  resource: string;
  action: string;
}

export interface Group {
  id: string;
  name: string;
  description: string;
  parent_id?: string;
  roles: Role[];
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  timezone: string;
  notifications: NotificationPreferences;
  download_quality: 'original' | 'high' | 'medium' | 'low';
  auto_download: boolean;
  cellular_downloads: boolean;
}

export interface NotificationPreferences {
  push_enabled: boolean;
  email_enabled: boolean;
  asset_updates: boolean;
  project_updates: boolean;
  system_announcements: boolean;
  workflow_notifications: boolean;
}

// Asset types
export interface Asset {
  id: string;
  name: string;
  description?: string;
  file_name: string;
  file_size: number;
  file_path: string;
  mime_type: string;
  asset_type: AssetType;
  status: AssetStatus;
  metadata: AssetMetadata;
  thumbnails: Thumbnail[];
  proxies: Proxy[];
  tags: Tag[];
  custom_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by: User;
  project_id?: string;
  parent_asset_id?: string;
  version: number;
  checksum: string;
  upload_progress?: number;
  is_favorite: boolean;
  download_url?: string;
  streaming_url?: string;
}

export type AssetType = 'image' | 'video' | 'audio' | 'document' | 'archive' | 'other';

export type AssetStatus = 
  | 'uploading' 
  | 'processing' 
  | 'ready' 
  | 'failed' 
  | 'archived' 
  | 'deleted';

export interface AssetMetadata {
  width?: number;
  height?: number;
  duration?: number; // in seconds
  frame_rate?: number;
  bit_rate?: number;
  codec?: string;
  color_space?: string;
  format?: string;
  camera_make?: string;
  camera_model?: string;
  iso?: number;
  exposure_time?: string;
  f_number?: number;
  focal_length?: number;
  gps_coordinates?: {
    latitude: number;
    longitude: number;
  };
  location_tag?: LocationTag;
  created_date?: string;
  modified_date?: string;
}

export interface Thumbnail {
  id: string;
  url: string;
  size: 'small' | 'medium' | 'large';
  width: number;
  height: number;
  mime_type: string;
}

export interface Proxy {
  id: string;
  url: string;
  quality: 'low' | 'medium' | 'high' | 'edit';
  format: string;
  size: number;
  resolution?: string;
  codec?: string;
  bit_rate?: number;
}

export interface Tag {
  id: string;
  name: string;
  color?: string;
  category?: string;
}

// Project types
export interface Project {
  id: string;
  name: string;
  description?: string;
  type: ProjectType;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  created_by: User;
  members: ProjectMember[];
  asset_count: number;
  total_size: number;
  thumbnail_url?: string;
  deadline?: string;
  client?: string;
  tags: Tag[];
}

export type ProjectType = 'video' | 'photo' | 'audio' | 'mixed' | 'archive';

export type ProjectStatus = 'active' | 'completed' | 'archived' | 'cancelled';

export interface ProjectMember {
  user: User;
  role: 'owner' | 'editor' | 'viewer';
  added_at: string;
}

// Upload types
export interface UploadTask {
  id: string;
  file_name: string;
  file_size: number;
  file_path: string;
  mime_type: string;
  asset_type: AssetType;
  project_id?: string;
  status: UploadStatus;
  progress: number;
  error_message?: string;
  created_at: string;
  estimated_completion?: string;
  upload_speed?: number; // bytes per second
  chunk_size: number;
  chunks_uploaded: number;
  total_chunks: number;
  retry_count: number;
  metadata?: Partial<AssetMetadata>;
  tags?: string[];
}

export type UploadStatus = 
  | 'queued' 
  | 'uploading' 
  | 'processing' 
  | 'completed' 
  | 'failed' 
  | 'cancelled' 
  | 'paused';

export interface UploadSession {
  id: string;
  upload_url: string;
  expires_at: string;
  chunk_size: number;
  signed_headers?: Record<string, string>;
}

// Search types
export interface SearchFilters {
  asset_types?: AssetType[];
  mime_types?: string[];
  projects?: string[];
  tags?: string[];
  created_after?: string;
  created_before?: string;
  updated_after?: string;
  updated_before?: string;
  file_size_min?: number;
  file_size_max?: number;
  duration_min?: number;
  duration_max?: number;
  resolution_min?: string;
  resolution_max?: string;
  created_by?: string[];
  status?: AssetStatus[];
  has_location?: boolean;
  sort_by?: 'created_at' | 'updated_at' | 'name' | 'file_size' | 'relevance';
  sort_order?: 'asc' | 'desc';
}

export interface SearchResult {
  assets: Asset[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
  facets?: SearchFacets;
  query_time: number;
}

export interface SearchFacets {
  asset_types: FacetItem[];
  projects: FacetItem[];
  tags: FacetItem[];
  created_by: FacetItem[];
  file_formats: FacetItem[];
}

export interface FacetItem {
  value: string;
  count: number;
  label: string;
}

// Location types (imported from locationService)
export interface LocationTag {
  id: string;
  coordinates: {
    latitude: number;
    longitude: number;
    accuracy: number;
    altitude?: number;
    heading?: number;
    speed?: number;
    timestamp: number;
  };
  address: {
    address: string;
    city?: string;
    state?: string;
    country?: string;
    postalCode?: string;
    formattedAddress: string;
  };
  name?: string;
  category?: 'home' | 'work' | 'event' | 'travel' | 'custom';
  created_at: string;
  used_count: number;
}

export interface LocationState {
  currentLocation: {
    latitude: number;
    longitude: number;
    accuracy: number;
    altitude?: number;
    heading?: number;
    speed?: number;
    timestamp: number;
  } | null;
  isTracking: boolean;
  savedLocations: LocationTag[];
  recentLocations: LocationTag[];
  isLoading: boolean;
  error: string | null;
  settings: {
    autoTag: boolean;
    highAccuracy: boolean;
    trackingEnabled: boolean;
    saveFrequentLocations: boolean;
    nearbyRadius: number;
    backgroundTracking: boolean;
  };
  permissionsGranted: boolean;
  locationServicesEnabled: boolean;
}

export interface VoiceNoteState {
  voiceNotes: VoiceNote[];
  currentNote: VoiceNote | null;
  recordingState: {
    isRecording: boolean;
    currentTime: number;
    isPlaying: boolean;
    isPaused: boolean;
    playTime: number;
    duration: number;
  };
  audioVisualization: {
    currentLevel: number;
    averageLevel: number;
    peakLevel: number;
    waveformData: number[];
  };
  currentlyPlaying: string | null;
  config: {
    maxDuration: number;
    quality: 'low' | 'medium' | 'high';
    format: 'mp4' | 'm4a' | 'wav' | 'aac';
    sampleRate: number;
    bitRate: number;
    channels: 1 | 2;
  };
  isLoading: boolean;
  error: string | null;
  showWaveform: boolean;
  showTranscription: boolean;
  microphonePermission: boolean;
  settings: {
    autoTranscribe: boolean;
    saveToGallery: boolean;
    enhanceAudio: boolean;
    noiseReduction: boolean;
    defaultQuality: 'low' | 'medium' | 'high';
    maxDuration: number;
    autoStopOnSilence: boolean;
    silenceThreshold: number;
  };
}

export interface VoiceNote {
  id: string;
  fileName: string;
  filePath: string;
  duration: number;
  size: number;
  transcription?: string;
  waveformData?: number[];
  created_at: string;
  metadata: {
    title?: string;
    tags?: string[];
    location?: {
      latitude: number;
      longitude: number;
    };
    quality: 'low' | 'medium' | 'high';
    format: 'mp4' | 'm4a' | 'wav' | 'aac';
    sampleRate: number;
    bitRate: number;
  };
}

// App state types
export interface AppState {
  auth: AuthState;
  assets: AssetState;
  projects: ProjectState;
  uploads: UploadState;
  search: SearchState;
  settings: SettingsState;
  offline: OfflineState;
  notifications: NotificationState;
  location: LocationState;
  voiceNote: VoiceNoteState;
  editing: EditingState;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  tokens: {
    access_token?: string;
    refresh_token?: string;
    expires_at?: string;
  } | null;
  isLoading: boolean;
  error: string | null;
  biometricEnabled: boolean;
  rememberLogin: boolean;
}

export interface AssetState {
  items: Record<string, Asset>;
  favorites: string[];
  recent: string[];
  cache: AssetCache;
  isLoading: boolean;
  error: string | null;
  lastSyncTime?: string;
}

export interface AssetCache {
  thumbnails: Record<string, string>; // assetId -> local file path
  proxies: Record<string, string>;
  metadata: Record<string, CachedMetadata>;
}

export interface CachedMetadata {
  asset_id: string;
  cached_at: string;
  expires_at: string;
  data: AssetMetadata;
}

export interface ProjectState {
  projects: Record<string, Project>;
  currentProject: Project | null;
  isLoading: boolean;
  error: string | null;
}

export interface UploadState {
  tasks: Record<string, UploadTask>;
  queue: string[];
  activeUploads: string[];
  settings: UploadSettings;
  isUploading: boolean;
  totalProgress: number;
  networkType: NetworkType;
}

export interface UploadSettings {
  auto_upload: boolean;
  wifi_only: boolean;
  max_concurrent: number;
  chunk_size: number;
  retry_attempts: number;
  compress_images: boolean;
  image_quality: number;
  video_quality: 'original' | 'high' | 'medium' | 'low';
}

export type NetworkType = 'wifi' | 'cellular' | 'none' | 'unknown';

export interface SearchState {
  query: string;
  filters: SearchFilters;
  results: any[];
  history: string[];
  savedSearches: any[];
  isLoading: boolean;
  error: string | null;
}

export interface SettingsState {
  theme: 'light' | 'dark' | 'system';
  language: string;
  auto_sync: boolean;
  cache_size_limit: number;
  video_quality: string;
  offline_mode: boolean;
  analytics_enabled: boolean;
  crash_reporting: boolean;
  usage_statistics: boolean;
  location_tracking: boolean;
}

export interface CacheSettings {
  max_size_mb: number;
  auto_cleanup: boolean;
  cleanup_threshold: number;
  cache_thumbnails: boolean;
  cache_proxies: boolean;
  cache_offline_days: number;
}

export interface DownloadSettings {
  default_quality: 'original' | 'high' | 'medium' | 'low';
  auto_download_favorites: boolean;
  wifi_only: boolean;
  max_downloads: number;
  download_location: string;
}

export interface PrivacySettings {
  analytics_enabled: boolean;
  crash_reporting: boolean;
  usage_statistics: boolean;
  location_tracking: boolean;
}

export interface OfflineState {
  isOnline: boolean;
  isConnected: boolean;
  connectionType: string;
  isInternetReachable: boolean | null;
  
  // Offline data
  offlineAssets: Record<string, OfflineAsset>;
  offlineProjects: Record<string, Project>;
  offlineSearches: Record<string, any>;
  
  // Sync state
  pendingOperations: SyncOperation[];
  isSyncing: boolean;
  lastSyncTime: string | null;
  syncProgress: number;
  
  // Download state
  downloadQueue: string[];
  downloadProgress: Record<string, number>;
  
  // Settings
  settings: {
    auto_sync: boolean;
    sync_on_wifi_only: boolean;
    download_thumbnails: boolean;
    download_previews: boolean;
    max_offline_storage: number;
    sync_interval: number;
  };
  
  // Storage info
  storageUsed: number;
  storageAvailable: number;
}

export interface OfflineAsset extends Asset {
  offline_data?: {
    thumbnail_path?: string;
    preview_path?: string;
    downloaded_at: string;
    last_accessed: string;
    download_quality: 'thumbnail' | 'low' | 'medium' | 'high';
    has_preview: boolean;
  };
}

export interface SyncOperation {
  id: string;
  type: 'upload_asset' | 'update_asset' | 'delete_asset' | 'toggle_favorite';
  data: any;
  timestamp: string;
  retry_count?: number;
}

// Notification types
export interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
  preferences: NotificationPreferences;
  deviceToken: string | null;
  permissionsGranted: boolean;
}

export interface Notification {
  id: string;
  type: 'asset_upload' | 'asset_ready' | 'project_update' | 'system_alert' | 'workflow_complete';
  title: string;
  message: string;
  data?: Record<string, any>;
  read_at?: string;
  created_at: string;
  updated_at: string;
}

export interface NotificationPreferences {
  enabled: boolean;
  types: {
    asset_upload: boolean;
    asset_ready: boolean;
    project_update: boolean;
    system_alert: boolean;
    workflow_complete: boolean;
  };
  quiet_hours: {
    enabled: boolean;
    start: string; // HH:MM format
    end: string;   // HH:MM format
  };
  sound_enabled: boolean;
  vibration_enabled: boolean;
}

export interface EditingState {
  activeProject: any | null; // Would import EditProject type
  projects: any[];
  isExporting: boolean;
  exportProgress: number;
  previewUrl: string | null;
  selectedEditId: string | null;
  undoStack: any[][];
  redoStack: any[][];
}

// Utility types
export interface PaginationParams {
  page?: number;
  limit?: number;
}

export interface SortParams {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface TimeRange {
  start: string;
  end: string;
}

export interface GeoLocation {
  latitude: number;
  longitude: number;
  accuracy?: number;
  altitude?: number;
  heading?: number;
  speed?: number;
}

export interface DeviceInfo {
  model: string;
  brand: string;
  system_name: string;
  system_version: string;
  app_version: string;
  build_number: string;
  device_id: string;
  install_id: string;
}

// Form types
export interface LoginForm {
  username: string;
  password: string;
  remember_me: boolean;
}

export interface RegisterForm {
  username: string;
  email: string;
  password: string;
  confirm_password: string;
  first_name: string;
  last_name: string;
  terms_accepted: boolean;
}

export interface AssetEditForm {
  name: string;
  description?: string;
  tags: string[];
  custom_metadata: Record<string, any>;
  project_id?: string;
}

export interface ProjectCreateForm {
  name: string;
  description?: string;
  type: ProjectType;
  client?: string;
  deadline?: string;
  tags: string[];
}

// Error types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
  context?: {
    screen?: string;
    action?: string;
    user_id?: string;
    asset_id?: string;
    project_id?: string;
  };
}

export type ErrorSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface ErrorReport {
  error: AppError;
  severity: ErrorSeverity;
  device_info: DeviceInfo;
  app_state?: Partial<AppState>;
  stack_trace?: string;
  user_feedback?: string;
}

// Analytics types
export interface AnalyticsEvent {
  event_name: string;
  properties?: Record<string, any>;
  user_id?: string;
  session_id: string;
  timestamp: string;
  screen?: string;
}

export interface PerformanceMetric {
  metric_name: string;
  value: number;
  unit: string;
  timestamp: string;
  context?: Record<string, any>;
}