/**
 * Utility Functions for Formatting Data
 * 
 * Common formatting functions for displaying
 * file sizes, durations, dates, and other data.
 */

/**
 * Format file size in bytes to human-readable format
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const size = bytes / Math.pow(1024, i);
  
  return `${size.toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`;
};

/**
 * Format duration in seconds to HH:MM:SS or MM:SS format
 */
export const formatDuration = (seconds: number): string => {
  if (isNaN(seconds) || seconds < 0) return '0:00';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  } else {
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  }
};

/**
 * Format date to relative time or absolute date
 */
export const formatDate = (dateString: string, relative = true): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffInMs = now.getTime() - date.getTime();
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));
  
  if (relative && diffInDays === 0) {
    const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));
    const diffInMinutes = Math.floor(diffInMs / (1000 * 60));
    
    if (diffInHours === 0) {
      if (diffInMinutes === 0) {
        return 'Just now';
      } else {
        return `${diffInMinutes}m ago`;
      }
    } else {
      return `${diffInHours}h ago`;
    }
  } else if (relative && diffInDays === 1) {
    return 'Yesterday';
  } else if (relative && diffInDays < 7) {
    return `${diffInDays}d ago`;
  }
  
  return date.toLocaleDateString();
};

/**
 * Format date to short format (MMM DD, YYYY)
 */
export const formatDateShort = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

/**
 * Format time to 12-hour format
 */
export const formatTime = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
};

/**
 * Format number with thousand separators
 */
export const formatNumber = (num: number): string => {
  return num.toLocaleString();
};

/**
 * Format percentage with specified decimal places
 */
export const formatPercentage = (value: number, decimals = 1): string => {
  return `${(value * 100).toFixed(decimals)}%`;
};

/**
 * Format resolution string (e.g., "1920x1080")
 */
export const formatResolution = (width?: number, height?: number): string => {
  if (!width || !height) return '';
  return `${width}×${height}`;
};

/**
 * Format bit rate to human-readable format
 */
export const formatBitRate = (bitRate: number): string => {
  if (bitRate < 1000) {
    return `${bitRate} bps`;
  } else if (bitRate < 1000000) {
    return `${(bitRate / 1000).toFixed(1)} Kbps`;
  } else {
    return `${(bitRate / 1000000).toFixed(1)} Mbps`;
  }
};

/**
 * Format frame rate to display format
 */
export const formatFrameRate = (frameRate: number): string => {
  if (frameRate % 1 === 0) {
    return `${frameRate} fps`;
  } else {
    return `${frameRate.toFixed(2)} fps`;
  }
};

/**
 * Truncate text to specified length with ellipsis
 */
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
};

/**
 * Capitalize first letter of string
 */
export const capitalize = (str: string): string => {
  return str.charAt(0).toUpperCase() + str.slice(1);
};

/**
 * Convert camelCase to Title Case
 */
export const camelToTitle = (str: string): string => {
  return str
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, (s) => s.toUpperCase())
    .trim();
};

/**
 * Format camera settings (ISO, aperture, etc.)
 */
export const formatCameraSettings = (iso?: number, fNumber?: number, exposureTime?: string): string => {
  const settings = [];
  
  if (iso) settings.push(`ISO ${iso}`);
  if (fNumber) settings.push(`f/${fNumber}`);
  if (exposureTime) settings.push(exposureTime);
  
  return settings.join(' • ');
};

/**
 * Format GPS coordinates to readable format
 */
export const formatCoordinates = (latitude: number, longitude: number): string => {
  const lat = Math.abs(latitude);
  const lng = Math.abs(longitude);
  const latDir = latitude >= 0 ? 'N' : 'S';
  const lngDir = longitude >= 0 ? 'E' : 'W';
  
  return `${lat.toFixed(6)}°${latDir}, ${lng.toFixed(6)}°${lngDir}`;
};

/**
 * Format asset tags for display
 */
export const formatTags = (tags: Array<{name: string}>, maxTags = 3): string => {
  if (tags.length === 0) return '';
  
  const tagNames = tags.map(tag => tag.name);
  if (tagNames.length <= maxTags) {
    return tagNames.join(', ');
  }
  
  const visibleTags = tagNames.slice(0, maxTags);
  const remainingCount = tagNames.length - maxTags;
  
  return `${visibleTags.join(', ')} +${remainingCount}`;
};

/**
 * Format upload speed to human-readable format
 */
export const formatUploadSpeed = (bytesPerSecond: number): string => {
  if (bytesPerSecond < 1024) {
    return `${bytesPerSecond.toFixed(0)} B/s`;
  } else if (bytesPerSecond < 1024 * 1024) {
    return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`;
  } else {
    return `${(bytesPerSecond / (1024 * 1024)).toFixed(1)} MB/s`;
  }
};

/**
 * Format estimated time remaining
 */
export const formatTimeRemaining = (seconds: number): string => {
  if (seconds < 60) {
    return `${Math.ceil(seconds)}s`;
  } else if (seconds < 3600) {
    const minutes = Math.ceil(seconds / 60);
    return `${minutes}m`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.ceil((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  }
};