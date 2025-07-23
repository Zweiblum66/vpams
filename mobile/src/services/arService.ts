/**
 * AR Service
 * 
 * Handles augmented reality preview functionality
 * for assets in the MAMS mobile application.
 */

import {Platform} from 'react-native';
import {Asset} from '@/types';

export interface ARCapabilities {
  isSupported: boolean;
  supportedFeatures: ARFeature[];
  requiredPermissions: string[];
  deviceModel: string;
}

export enum ARFeature {
  PLANE_DETECTION = 'plane_detection',
  IMAGE_TRACKING = 'image_tracking',
  OBJECT_PLACEMENT = 'object_placement',
  LIGHTING_ESTIMATION = 'lighting_estimation',
  FACE_TRACKING = 'face_tracking',
  MOTION_CAPTURE = 'motion_capture',
}

export interface ARSession {
  id: string;
  assetId: string;
  type: ARPreviewType;
  startTime: Date;
  isActive: boolean;
  configuration: ARConfiguration;
}

export type ARPreviewType = 
  | 'image_on_wall'
  | 'video_screen'
  | '3d_model'
  | 'document_viewer'
  | 'virtual_gallery';

export interface ARConfiguration {
  scale: number;
  position: {x: number; y: number; z: number};
  rotation: {x: number; y: number; z: number};
  lighting: boolean;
  shadows: boolean;
  occlusion: boolean;
  autoPlace: boolean;
}

export interface ARPlacement {
  id: string;
  assetId: string;
  position: {x: number; y: number; z: number};
  rotation: {x: number; y: number; z: number};
  scale: number;
  timestamp: Date;
  screenshot?: string;
}

class ARService {
  private currentSession: ARSession | null = null;
  private placements: Map<string, ARPlacement> = new Map();
  private capabilities: ARCapabilities | null = null;

  /**
   * Check if AR is supported on the current device
   */
  async checkARSupport(): Promise<ARCapabilities> {
    if (this.capabilities) {
      return this.capabilities;
    }

    const isIOS = Platform.OS === 'ios';
    const isAndroid = Platform.OS === 'android';

    let isSupported = false;
    let supportedFeatures: ARFeature[] = [];
    let requiredPermissions: string[] = ['camera'];

    if (isIOS) {
      // iOS 11+ with A9 chip or later supports ARKit
      const iosVersion = parseInt(Platform.Version as string, 10);
      isSupported = iosVersion >= 11;
      
      if (isSupported) {
        supportedFeatures = [
          ARFeature.PLANE_DETECTION,
          ARFeature.IMAGE_TRACKING,
          ARFeature.OBJECT_PLACEMENT,
          ARFeature.LIGHTING_ESTIMATION,
          ARFeature.FACE_TRACKING,
        ];
      }
    } else if (isAndroid) {
      // Android 7.0+ with ARCore support
      const androidVersion = Platform.Version as number;
      isSupported = androidVersion >= 24; // Android 7.0
      
      if (isSupported) {
        supportedFeatures = [
          ARFeature.PLANE_DETECTION,
          ARFeature.IMAGE_TRACKING,
          ARFeature.OBJECT_PLACEMENT,
          ARFeature.LIGHTING_ESTIMATION,
        ];
        requiredPermissions.push('android.permission.CAMERA');
      }
    }

    this.capabilities = {
      isSupported,
      supportedFeatures,
      requiredPermissions,
      deviceModel: Platform.constants?.Model || 'Unknown',
    };

    return this.capabilities;
  }

  /**
   * Determine the best AR preview type for an asset
   */
  getPreviewTypeForAsset(asset: Asset): ARPreviewType | null {
    if (!asset.metadata?.mime_type) return null;

    const mimeType = asset.metadata.mime_type;
    
    if (mimeType.startsWith('image/')) {
      return 'image_on_wall';
    } else if (mimeType.startsWith('video/')) {
      return 'video_screen';
    } else if (mimeType.includes('model') || mimeType.includes('3d')) {
      return '3d_model';
    } else if (mimeType.includes('pdf') || mimeType.includes('document')) {
      return 'document_viewer';
    }

    return null;
  }

  /**
   * Start an AR session for an asset
   */
  async startARSession(
    asset: Asset,
    type?: ARPreviewType
  ): Promise<ARSession> {
    const capabilities = await this.checkARSupport();
    
    if (!capabilities.isSupported) {
      throw new Error('AR is not supported on this device');
    }

    const previewType = type || this.getPreviewTypeForAsset(asset);
    if (!previewType) {
      throw new Error('No suitable AR preview type for this asset');
    }

    const defaultConfig = this.getDefaultConfiguration(previewType);

    this.currentSession = {
      id: `ar_session_${Date.now()}`,
      assetId: asset.id,
      type: previewType,
      startTime: new Date(),
      isActive: true,
      configuration: defaultConfig,
    };

    return this.currentSession;
  }

  /**
   * Get default AR configuration based on preview type
   */
  private getDefaultConfiguration(type: ARPreviewType): ARConfiguration {
    const baseConfig: ARConfiguration = {
      scale: 1.0,
      position: {x: 0, y: 0, z: -1},
      rotation: {x: 0, y: 0, z: 0},
      lighting: true,
      shadows: true,
      occlusion: true,
      autoPlace: true,
    };

    switch (type) {
      case 'image_on_wall':
        return {
          ...baseConfig,
          scale: 0.5, // 50cm default size
          position: {x: 0, y: 0, z: -1.5},
        };
      
      case 'video_screen':
        return {
          ...baseConfig,
          scale: 1.0, // 1m screen
          position: {x: 0, y: 0.5, z: -2},
        };
      
      case '3d_model':
        return {
          ...baseConfig,
          scale: 0.3,
          position: {x: 0, y: 0, z: -1},
        };
      
      case 'document_viewer':
        return {
          ...baseConfig,
          scale: 0.8,
          position: {x: 0, y: 0.3, z: -1.2},
          shadows: false,
        };
      
      case 'virtual_gallery':
        return {
          ...baseConfig,
          scale: 2.0,
          position: {x: 0, y: 0, z: -3},
        };
      
      default:
        return baseConfig;
    }
  }

  /**
   * Update AR configuration
   */
  updateConfiguration(config: Partial<ARConfiguration>): ARConfiguration | null {
    if (!this.currentSession) return null;

    this.currentSession.configuration = {
      ...this.currentSession.configuration,
      ...config,
    };

    return this.currentSession.configuration;
  }

  /**
   * Place an asset in AR space
   */
  async placeAsset(
    assetId: string,
    position: {x: number; y: number; z: number},
    rotation?: {x: number; y: number; z: number},
    scale?: number
  ): Promise<ARPlacement> {
    const placement: ARPlacement = {
      id: `placement_${Date.now()}`,
      assetId,
      position,
      rotation: rotation || {x: 0, y: 0, z: 0},
      scale: scale || 1.0,
      timestamp: new Date(),
    };

    this.placements.set(placement.id, placement);
    return placement;
  }

  /**
   * Remove a placement
   */
  removePlacement(placementId: string): boolean {
    return this.placements.delete(placementId);
  }

  /**
   * Get all placements
   */
  getAllPlacements(): ARPlacement[] {
    return Array.from(this.placements.values());
  }

  /**
   * Take a screenshot of the AR scene
   */
  async takeARScreenshot(): Promise<string> {
    // This would be implemented with native AR framework
    // Returns base64 or file path of screenshot
    return `ar_screenshot_${Date.now()}.jpg`;
  }

  /**
   * Share AR experience
   */
  async shareARExperience(placement: ARPlacement): Promise<void> {
    const screenshot = await this.takeARScreenshot();
    placement.screenshot = screenshot;
    
    // Would implement native sharing here
    console.log('Sharing AR experience:', placement);
  }

  /**
   * End the current AR session
   */
  endSession(): void {
    if (this.currentSession) {
      this.currentSession.isActive = false;
      this.currentSession = null;
    }
  }

  /**
   * Get current session
   */
  getCurrentSession(): ARSession | null {
    return this.currentSession;
  }

  /**
   * Calculate real-world dimensions for asset
   */
  calculateRealWorldDimensions(
    asset: Asset,
    scale: number
  ): {width: number; height: number; depth?: number} {
    // Default dimensions in meters
    let width = 1.0;
    let height = 1.0;
    let depth: number | undefined;

    if (asset.metadata?.width && asset.metadata?.height) {
      // Convert pixels to meters (assuming 72 DPI)
      const pixelsPerMeter = 72 * 39.37; // 72 DPI * inches per meter
      width = (asset.metadata.width / pixelsPerMeter) * scale;
      height = (asset.metadata.height / pixelsPerMeter) * scale;
    }

    if (asset.metadata?.mime_type?.includes('3d')) {
      depth = width; // Assume cubic for now
    }

    return {width, height, depth};
  }

  /**
   * Get AR hints for better placement
   */
  getPlacementHints(type: ARPreviewType): string[] {
    switch (type) {
      case 'image_on_wall':
        return [
          'Point at a wall to place the image',
          'Tap to confirm placement',
          'Pinch to resize',
          'Rotate with two fingers',
        ];
      
      case 'video_screen':
        return [
          'Find a flat surface',
          'The video will play on a virtual screen',
          'Tap the screen to play/pause',
          'Adjust size for optimal viewing',
        ];
      
      case '3d_model':
        return [
          'Scan the floor to detect surfaces',
          'Tap to place the model',
          'Walk around to view from all angles',
          'Use gestures to rotate and scale',
        ];
      
      case 'document_viewer':
        return [
          'Place the document at comfortable reading distance',
          'Swipe to turn pages',
          'Pinch to zoom in/out',
          'Double-tap to reset view',
        ];
      
      case 'virtual_gallery':
        return [
          'Scan a large open space',
          'Walk through your virtual gallery',
          'Tap artworks for details',
          'Take screenshots to share',
        ];
      
      default:
        return ['Scan your environment', 'Tap to place content'];
    }
  }
}

export const arService = new ARService();