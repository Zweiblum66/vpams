/**
 * Editing Service
 * 
 * Handles media editing operations for the mobile app
 * including trimming, filters, adjustments, and exports.
 */

import {Platform} from 'react-native';
import RNFS from 'react-native-fs';
import {FFmpegKit, FFmpegKitConfig, ReturnCode} from 'ffmpeg-kit-react-native';
import {Asset} from '@/types';

export interface EditProject {
  id: string;
  assetId: string;
  originalAsset: Asset;
  edits: Edit[];
  preview?: string;
  created_at: Date;
  updated_at: Date;
  exportSettings: ExportSettings;
}

export interface Edit {
  id: string;
  type: EditType;
  parameters: EditParameters;
  timestamp: Date;
  enabled: boolean;
}

export type EditType = 
  | 'trim'
  | 'crop'
  | 'rotate'
  | 'filter'
  | 'adjustment'
  | 'text'
  | 'audio'
  | 'transition'
  | 'speed';

export interface EditParameters {
  // Trim parameters
  startTime?: number;
  endTime?: number;
  
  // Crop parameters
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  
  // Rotate parameters
  angle?: number;
  
  // Filter parameters
  filterName?: string;
  intensity?: number;
  
  // Adjustment parameters
  brightness?: number;
  contrast?: number;
  saturation?: number;
  hue?: number;
  
  // Text parameters
  text?: string;
  fontFamily?: string;
  fontSize?: number;
  color?: string;
  position?: {x: number; y: number};
  duration?: number;
  
  // Audio parameters
  volume?: number;
  fadeIn?: number;
  fadeOut?: number;
  mute?: boolean;
  
  // Speed parameters
  speed?: number;
}

export interface ExportSettings {
  format: 'mp4' | 'mov' | 'gif' | 'jpg' | 'png';
  quality: 'low' | 'medium' | 'high' | 'original';
  resolution?: {width: number; height: number};
  frameRate?: number;
  bitrate?: number;
  codec?: string;
}

export interface Filter {
  id: string;
  name: string;
  preview: string;
  category: 'basic' | 'vintage' | 'artistic' | 'color';
  ffmpegFilter: string;
}

const AVAILABLE_FILTERS: Filter[] = [
  {
    id: 'none',
    name: 'None',
    preview: 'none',
    category: 'basic',
    ffmpegFilter: '',
  },
  {
    id: 'grayscale',
    name: 'Grayscale',
    preview: 'grayscale',
    category: 'basic',
    ffmpegFilter: 'colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3',
  },
  {
    id: 'sepia',
    name: 'Sepia',
    preview: 'sepia',
    category: 'vintage',
    ffmpegFilter: 'colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131',
  },
  {
    id: 'vintage',
    name: 'Vintage',
    preview: 'vintage',
    category: 'vintage',
    ffmpegFilter: 'curves=vintage',
  },
  {
    id: 'noir',
    name: 'Noir',
    preview: 'noir',
    category: 'artistic',
    ffmpegFilter: 'colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3,curves=preset=darker',
  },
  {
    id: 'vibrant',
    name: 'Vibrant',
    preview: 'vibrant',
    category: 'color',
    ffmpegFilter: 'eq=saturation=1.5:contrast=1.1',
  },
  {
    id: 'cool',
    name: 'Cool',
    preview: 'cool',
    category: 'color',
    ffmpegFilter: 'colorbalance=rs=-0.1:gs=0:bs=0.1',
  },
  {
    id: 'warm',
    name: 'Warm',
    preview: 'warm',
    category: 'color',
    ffmpegFilter: 'colorbalance=rs=0.1:gs=0:bs=-0.1',
  },
];

class EditingService {
  private projects: Map<string, EditProject> = new Map();
  private tempDir: string;

  constructor() {
    this.tempDir = `${RNFS.CachesDirectoryPath}/editing`;
    this.ensureTempDirectory();
  }

  private async ensureTempDirectory() {
    const exists = await RNFS.exists(this.tempDir);
    if (!exists) {
      await RNFS.mkdir(this.tempDir);
    }
  }

  /**
   * Create a new edit project
   */
  async createProject(asset: Asset): Promise<EditProject> {
    const project: EditProject = {
      id: `edit_${Date.now()}`,
      assetId: asset.id,
      originalAsset: asset,
      edits: [],
      created_at: new Date(),
      updated_at: new Date(),
      exportSettings: {
        format: this.getDefaultFormat(asset),
        quality: 'high',
      },
    };

    this.projects.set(project.id, project);
    return project;
  }

  /**
   * Get default export format based on asset type
   */
  private getDefaultFormat(asset: Asset): ExportSettings['format'] {
    const mimeType = asset.metadata?.mime_type || '';
    
    if (mimeType.startsWith('video/')) {
      return 'mp4';
    } else if (mimeType.startsWith('image/gif')) {
      return 'gif';
    } else if (mimeType.startsWith('image/')) {
      return 'jpg';
    }
    
    return 'mp4';
  }

  /**
   * Add an edit to the project
   */
  addEdit(projectId: string, edit: Omit<Edit, 'id' | 'timestamp'>): Edit {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error('Project not found');
    }

    const newEdit: Edit = {
      ...edit,
      id: `edit_${Date.now()}`,
      timestamp: new Date(),
    };

    project.edits.push(newEdit);
    project.updated_at = new Date();
    
    return newEdit;
  }

  /**
   * Update an existing edit
   */
  updateEdit(projectId: string, editId: string, parameters: Partial<EditParameters>): void {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error('Project not found');
    }

    const edit = project.edits.find(e => e.id === editId);
    if (!edit) {
      throw new Error('Edit not found');
    }

    edit.parameters = {...edit.parameters, ...parameters};
    project.updated_at = new Date();
  }

  /**
   * Remove an edit
   */
  removeEdit(projectId: string, editId: string): void {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error('Project not found');
    }

    project.edits = project.edits.filter(e => e.id !== editId);
    project.updated_at = new Date();
  }

  /**
   * Toggle edit enabled state
   */
  toggleEdit(projectId: string, editId: string): void {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error('Project not found');
    }

    const edit = project.edits.find(e => e.id === editId);
    if (edit) {
      edit.enabled = !edit.enabled;
      project.updated_at = new Date();
    }
  }

  /**
   * Get available filters
   */
  getFilters(): Filter[] {
    return AVAILABLE_FILTERS;
  }

  /**
   * Generate preview for current edits
   */
  async generatePreview(projectId: string): Promise<string> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error('Project not found');
    }

    const outputPath = `${this.tempDir}/preview_${projectId}.jpg`;
    const command = await this.buildFFmpegCommand(project, outputPath, true);

    return new Promise((resolve, reject) => {
      FFmpegKit.execute(command).then(async (session) => {
        const returnCode = await session.getReturnCode();
        
        if (ReturnCode.isSuccess(returnCode)) {
          project.preview = outputPath;
          resolve(outputPath);
        } else {
          reject(new Error('Failed to generate preview'));
        }
      });
    });
  }

  /**
   * Export the edited media
   */
  async exportProject(
    projectId: string,
    outputPath?: string
  ): Promise<{path: string; size: number; duration?: number}> {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error('Project not found');
    }

    const format = project.exportSettings.format;
    const finalOutputPath = outputPath || 
      `${this.tempDir}/export_${projectId}.${format}`;

    const command = await this.buildFFmpegCommand(project, finalOutputPath, false);

    return new Promise((resolve, reject) => {
      FFmpegKit.execute(command).then(async (session) => {
        const returnCode = await session.getReturnCode();
        
        if (ReturnCode.isSuccess(returnCode)) {
          const stats = await RNFS.stat(finalOutputPath);
          
          // Get duration for video/audio
          let duration: number | undefined;
          if (format === 'mp4' || format === 'mov') {
            duration = await this.getMediaDuration(finalOutputPath);
          }
          
          resolve({
            path: finalOutputPath,
            size: parseInt(stats.size, 10),
            duration,
          });
        } else {
          const logs = await session.getLogs();
          reject(new Error(`Export failed: ${logs}`));
        }
      });
    });
  }

  /**
   * Build FFmpeg command from edits
   */
  private async buildFFmpegCommand(
    project: EditProject,
    outputPath: string,
    isPreview: boolean
  ): Promise<string> {
    const inputPath = project.originalAsset.file_path || 
                     project.originalAsset.proxy_url;
    
    let command = `-i "${inputPath}"`;
    const enabledEdits = project.edits.filter(e => e.enabled);
    
    // Video filters
    const videoFilters: string[] = [];
    
    // Audio filters
    const audioFilters: string[] = [];
    
    // Process each edit type
    for (const edit of enabledEdits) {
      switch (edit.type) {
        case 'trim':
          if (edit.parameters.startTime !== undefined) {
            command = `-ss ${edit.parameters.startTime} ${command}`;
          }
          if (edit.parameters.endTime !== undefined && 
              edit.parameters.startTime !== undefined) {
            const duration = edit.parameters.endTime - edit.parameters.startTime;
            command += ` -t ${duration}`;
          }
          break;
          
        case 'crop':
          const {x = 0, y = 0, width, height} = edit.parameters;
          if (width && height) {
            videoFilters.push(`crop=${width}:${height}:${x}:${y}`);
          }
          break;
          
        case 'rotate':
          const angle = edit.parameters.angle || 0;
          if (angle === 90) {
            videoFilters.push('transpose=1');
          } else if (angle === 180) {
            videoFilters.push('transpose=2,transpose=2');
          } else if (angle === 270) {
            videoFilters.push('transpose=2');
          } else if (angle !== 0) {
            videoFilters.push(`rotate=${angle}*PI/180`);
          }
          break;
          
        case 'filter':
          const filter = AVAILABLE_FILTERS.find(
            f => f.id === edit.parameters.filterName
          );
          if (filter && filter.ffmpegFilter) {
            videoFilters.push(filter.ffmpegFilter);
          }
          break;
          
        case 'adjustment':
          const adjustments: string[] = [];
          const {brightness, contrast, saturation, hue} = edit.parameters;
          
          if (brightness !== undefined) {
            adjustments.push(`brightness=${brightness}`);
          }
          if (contrast !== undefined) {
            adjustments.push(`contrast=${contrast}`);
          }
          if (saturation !== undefined) {
            adjustments.push(`saturation=${saturation}`);
          }
          if (hue !== undefined) {
            adjustments.push(`hue=${hue}`);
          }
          
          if (adjustments.length > 0) {
            videoFilters.push(`eq=${adjustments.join(':')}`);
          }
          break;
          
        case 'speed':
          const speed = edit.parameters.speed || 1.0;
          if (speed !== 1.0) {
            videoFilters.push(`setpts=${1/speed}*PTS`);
            audioFilters.push(`atempo=${speed}`);
          }
          break;
          
        case 'audio':
          if (edit.parameters.volume !== undefined) {
            audioFilters.push(`volume=${edit.parameters.volume}`);
          }
          if (edit.parameters.mute) {
            audioFilters.push('volume=0');
          }
          break;
      }
    }
    
    // Apply filters
    if (videoFilters.length > 0) {
      command += ` -vf "${videoFilters.join(',')}"`;
    }
    
    if (audioFilters.length > 0) {
      command += ` -af "${audioFilters.join(',')}"`;
    }
    
    // Output settings
    if (isPreview) {
      command += ' -vframes 1 -q:v 2';
    } else {
      command += this.getExportSettings(project.exportSettings);
    }
    
    command += ` -y "${outputPath}"`;
    
    return command;
  }

  /**
   * Get export settings for FFmpeg
   */
  private getExportSettings(settings: ExportSettings): string {
    let params = '';
    
    // Quality presets
    switch (settings.quality) {
      case 'low':
        params += ' -crf 28 -preset faster';
        break;
      case 'medium':
        params += ' -crf 23 -preset medium';
        break;
      case 'high':
        params += ' -crf 18 -preset slow';
        break;
      case 'original':
        params += ' -crf 0';
        break;
    }
    
    // Resolution
    if (settings.resolution) {
      params += ` -s ${settings.resolution.width}x${settings.resolution.height}`;
    }
    
    // Frame rate
    if (settings.frameRate) {
      params += ` -r ${settings.frameRate}`;
    }
    
    // Bitrate
    if (settings.bitrate) {
      params += ` -b:v ${settings.bitrate}k`;
    }
    
    // Format-specific settings
    switch (settings.format) {
      case 'mp4':
        params += ' -c:v libx264 -c:a aac';
        break;
      case 'mov':
        params += ' -c:v libx264 -c:a aac -f mov';
        break;
      case 'gif':
        params += ' -f gif';
        break;
      case 'jpg':
      case 'png':
        params += ' -vframes 1';
        break;
    }
    
    return params;
  }

  /**
   * Get media duration using FFmpeg
   */
  private async getMediaDuration(path: string): Promise<number> {
    return new Promise((resolve) => {
      FFmpegKitConfig.getMediaInformation(path).then(async (info) => {
        const duration = await info.getDuration();
        resolve(parseFloat(duration || '0'));
      }).catch(() => {
        resolve(0);
      });
    });
  }

  /**
   * Clean up temporary files
   */
  async cleanup(projectId?: string): Promise<void> {
    if (projectId) {
      const project = this.projects.get(projectId);
      if (project?.preview && await RNFS.exists(project.preview)) {
        await RNFS.unlink(project.preview);
      }
      this.projects.delete(projectId);
    } else {
      // Clean all temp files
      const files = await RNFS.readDir(this.tempDir);
      for (const file of files) {
        if (file.isFile()) {
          await RNFS.unlink(file.path);
        }
      }
      this.projects.clear();
    }
  }

  /**
   * Get project by ID
   */
  getProject(projectId: string): EditProject | undefined {
    return this.projects.get(projectId);
  }

  /**
   * Get all projects
   */
  getAllProjects(): EditProject[] {
    return Array.from(this.projects.values());
  }
}

export const editingService = new EditingService();