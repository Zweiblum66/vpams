/**
 * Camera Service
 * 
 * Handles camera operations, image processing,
 * and media file management.
 */

import {launchCamera, launchImageLibrary, MediaType, ImagePickerResponse} from 'react-native-image-picker';
import {check, request, PERMISSIONS, RESULTS} from 'react-native-permissions';
import {Platform, Alert} from 'react-native';
import RNFS from 'react-native-fs';

export interface CameraOptions {
  mediaType: 'photo' | 'video' | 'mixed';
  quality: number; // 0.0 to 1.0
  maxWidth?: number;
  maxHeight?: number;
  videoQuality?: 'low' | 'medium' | 'high';
  durationLimit?: number; // seconds
  allowsEditing?: boolean;
  includeBase64?: boolean;
}

export interface MediaResult {
  uri: string;
  fileName: string;
  type: string;
  fileSize: number;
  width?: number;
  height?: number;
  duration?: number;
  timestamp?: string;
}

class CameraService {
  /**
   * Check if camera permissions are granted
   */
  async checkCameraPermissions(): Promise<boolean> {
    try {
      const cameraPermission = Platform.OS === 'ios' 
        ? await check(PERMISSIONS.IOS.CAMERA)
        : await check(PERMISSIONS.ANDROID.CAMERA);
      
      const micPermission = Platform.OS === 'ios'
        ? await check(PERMISSIONS.IOS.MICROPHONE)
        : await check(PERMISSIONS.ANDROID.RECORD_AUDIO);

      return (
        cameraPermission === RESULTS.GRANTED &&
        micPermission === RESULTS.GRANTED
      );
    } catch (error) {
      console.error('Error checking camera permissions:', error);
      return false;
    }
  }

  /**
   * Request camera permissions
   */
  async requestCameraPermissions(): Promise<boolean> {
    try {
      const cameraResult = Platform.OS === 'ios'
        ? await request(PERMISSIONS.IOS.CAMERA)
        : await request(PERMISSIONS.ANDROID.CAMERA);
      
      const micResult = Platform.OS === 'ios'
        ? await request(PERMISSIONS.IOS.MICROPHONE)
        : await request(PERMISSIONS.ANDROID.RECORD_AUDIO);

      return (
        cameraResult === RESULTS.GRANTED &&
        micResult === RESULTS.GRANTED
      );
    } catch (error) {
      console.error('Error requesting camera permissions:', error);
      return false;
    }
  }

  /**
   * Open camera to capture photo or video
   */
  async openCamera(options: CameraOptions = {mediaType: 'photo', quality: 0.8}): Promise<MediaResult | null> {
    try {
      // Check permissions first
      const hasPermission = await this.checkCameraPermissions();
      if (!hasPermission) {
        const granted = await this.requestCameraPermissions();
        if (!granted) {
          Alert.alert(
            'Camera Permission Required',
            'Please grant camera permissions to capture media.',
            [
              {text: 'Cancel'},
              {text: 'Settings', onPress: () => this.openSettings()},
            ]
          );
          return null;
        }
      }

      return new Promise((resolve) => {
        launchCamera(
          {
            mediaType: options.mediaType as MediaType,
            quality: options.quality,
            maxWidth: options.maxWidth,
            maxHeight: options.maxHeight,
            videoQuality: options.videoQuality,
            durationLimit: options.durationLimit,
            includeBase64: options.includeBase64 || false,
          },
          (response: ImagePickerResponse) => {
            if (response.didCancel || response.errorMessage) {
              resolve(null);
              return;
            }

            if (response.assets && response.assets[0]) {
              const asset = response.assets[0];
              const result: MediaResult = {
                uri: asset.uri!,
                fileName: asset.fileName || `capture_${Date.now()}.${options.mediaType === 'video' ? 'mp4' : 'jpg'}`,
                type: asset.type || (options.mediaType === 'video' ? 'video/mp4' : 'image/jpeg'),
                fileSize: asset.fileSize || 0,
                width: asset.width,
                height: asset.height,
                duration: asset.duration,
                timestamp: asset.timestamp,
              };
              resolve(result);
            } else {
              resolve(null);
            }
          }
        );
      });
    } catch (error) {
      console.error('Error opening camera:', error);
      return null;
    }
  }

  /**
   * Open photo library to select media
   */
  async openPhotoLibrary(options: CameraOptions & {selectionLimit?: number} = {
    mediaType: 'mixed',
    quality: 0.8,
    selectionLimit: 1,
  }): Promise<MediaResult[]> {
    try {
      return new Promise((resolve) => {
        launchImageLibrary(
          {
            mediaType: options.mediaType as MediaType,
            quality: options.quality,
            maxWidth: options.maxWidth,
            maxHeight: options.maxHeight,
            videoQuality: options.videoQuality,
            selectionLimit: options.selectionLimit || 1,
            includeBase64: options.includeBase64 || false,
          },
          (response: ImagePickerResponse) => {
            if (response.didCancel || response.errorMessage) {
              resolve([]);
              return;
            }

            if (response.assets) {
              const results: MediaResult[] = response.assets.map(asset => ({
                uri: asset.uri!,
                fileName: asset.fileName || `selected_${Date.now()}.${asset.type?.includes('video') ? 'mp4' : 'jpg'}`,
                type: asset.type || 'image/jpeg',
                fileSize: asset.fileSize || 0,
                width: asset.width,
                height: asset.height,
                duration: asset.duration,
                timestamp: asset.timestamp,
              }));
              resolve(results);
            } else {
              resolve([]);
            }
          }
        );
      });
    } catch (error) {
      console.error('Error opening photo library:', error);
      return [];
    }
  }

  /**
   * Process captured image (resize, compress, etc.)
   */
  async processImage(
    uri: string,
    options: {
      maxWidth?: number;
      maxHeight?: number;
      quality?: number;
      format?: 'JPEG' | 'PNG';
    } = {}
  ): Promise<string> {
    try {
      // For now, return the original URI
      // In a production app, you would use a library like react-native-image-resizer
      // to process the image according to the options
      return uri;
    } catch (error) {
      console.error('Error processing image:', error);
      return uri;
    }
  }

  /**
   * Generate thumbnail from video
   */
  async generateVideoThumbnail(videoUri: string, timeStamp: number = 1): Promise<string | null> {
    try {
      // For now, return null
      // In a production app, you would use a library like react-native-create-thumbnail
      // to generate thumbnails from videos
      return null;
    } catch (error) {
      console.error('Error generating video thumbnail:', error);
      return null;
    }
  }

  /**
   * Get media file information
   */
  async getMediaInfo(uri: string): Promise<{
    size: number;
    width?: number;
    height?: number;
    duration?: number;
    format?: string;
  } | null> {
    try {
      const fileInfo = await RNFS.stat(uri);
      
      return {
        size: fileInfo.size,
        // Additional metadata would be extracted using a media info library
        // like react-native-media-meta
      };
    } catch (error) {
      console.error('Error getting media info:', error);
      return null;
    }
  }

  /**
   * Save media to device gallery
   */
  async saveToGallery(uri: string, type: 'photo' | 'video'): Promise<boolean> {
    try {
      // Check permissions
      const permission = Platform.OS === 'ios'
        ? PERMISSIONS.IOS.PHOTO_LIBRARY_ADD_ONLY
        : PERMISSIONS.ANDROID.WRITE_EXTERNAL_STORAGE;
      
      const result = await check(permission);
      if (result !== RESULTS.GRANTED) {
        const granted = await request(permission);
        if (granted !== RESULTS.GRANTED) {
          return false;
        }
      }

      // Save to gallery using react-native-cameraroll or similar library
      // For now, return true as placeholder
      return true;
    } catch (error) {
      console.error('Error saving to gallery:', error);
      return false;
    }
  }

  /**
   * Copy file to app's documents directory
   */
  async copyToDocuments(uri: string, fileName: string): Promise<string> {
    try {
      const documentsDir = RNFS.DocumentDirectoryPath;
      const destinationPath = `${documentsDir}/${fileName}`;
      
      await RNFS.copyFile(uri, destinationPath);
      return destinationPath;
    } catch (error) {
      console.error('Error copying file to documents:', error);
      throw error;
    }
  }

  /**
   * Delete temporary file
   */
  async deleteTempFile(uri: string): Promise<boolean> {
    try {
      const exists = await RNFS.exists(uri);
      if (exists) {
        await RNFS.unlink(uri);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error deleting temp file:', error);
      return false;
    }
  }

  /**
   * Get available camera devices
   */
  async getAvailableCameras(): Promise<string[]> {
    try {
      // This would typically use react-native-camera or camera APIs
      // to enumerate available camera devices
      return ['back', 'front'];
    } catch (error) {
      console.error('Error getting available cameras:', error);
      return ['back'];
    }
  }

  /**
   * Check if device has flash
   */
  async hasFlash(): Promise<boolean> {
    try {
      // This would check device capabilities
      // For now, assume most devices have flash
      return Platform.OS === 'ios' || Platform.OS === 'android';
    } catch (error) {
      console.error('Error checking flash availability:', error);
      return false;
    }
  }

  /**
   * Open device settings
   */
  private openSettings(): void {
    // This would open device settings
    // Implementation depends on platform and available libraries
    console.log('Opening device settings...');
  }

  /**
   * Validate media file
   */
  async validateMediaFile(uri: string, type: 'photo' | 'video'): Promise<{
    isValid: boolean;
    error?: string;
  }> {
    try {
      const exists = await RNFS.exists(uri);
      if (!exists) {
        return {isValid: false, error: 'File does not exist'};
      }

      const fileInfo = await RNFS.stat(uri);
      if (fileInfo.size === 0) {
        return {isValid: false, error: 'File is empty'};
      }

      // Additional validation based on file type
      if (type === 'photo') {
        // Validate image file
        if (fileInfo.size > 50 * 1024 * 1024) { // 50MB limit
          return {isValid: false, error: 'Image file too large'};
        }
      } else if (type === 'video') {
        // Validate video file
        if (fileInfo.size > 500 * 1024 * 1024) { // 500MB limit
          return {isValid: false, error: 'Video file too large'};
        }
      }

      return {isValid: true};
    } catch (error) {
      console.error('Error validating media file:', error);
      return {isValid: false, error: 'Validation failed'};
    }
  }
}

export const cameraService = new CameraService();