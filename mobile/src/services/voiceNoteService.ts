/**
 * Voice Note Service
 * 
 * Handles audio recording, playback, transcription,
 * and voice note management for the mobile app.
 */

import AudioRecorderPlayer, {
  AVEncoderAudioQualityIOSType,
  AVEncodingOption,
  AudioEncoderAndroidType,
  AudioSourceAndroidType,
  OutputFormatAndroidType,
} from 'react-native-audio-recorder-player';
import {check, request, PERMISSIONS, RESULTS} from 'react-native-permissions';
import {Platform, Alert} from 'react-native';
import RNFS from 'react-native-fs';
import {AudioSession} from 'react-native-audio-session';

export interface VoiceNoteConfig {
  maxDuration: number; // milliseconds
  quality: 'low' | 'medium' | 'high';
  format: 'mp4' | 'm4a' | 'wav' | 'aac';
  sampleRate: number;
  bitRate: number;
  channels: 1 | 2;
}

export interface VoiceNote {
  id: string;
  fileName: string;
  filePath: string;
  duration: number; // milliseconds
  size: number; // bytes
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
    quality: VoiceNoteConfig['quality'];
    format: VoiceNoteConfig['format'];
    sampleRate: number;
    bitRate: number;
  };
}

export interface RecordingState {
  isRecording: boolean;
  currentTime: number;
  isPlaying: boolean;
  isPaused: boolean;
  playTime: number;
  duration: number;
}

export interface AudioVisualization {
  currentLevel: number;
  averageLevel: number;
  peakLevel: number;
  waveformData: number[];
}

class VoiceNoteService {
  private audioRecorderPlayer: AudioRecorderPlayer;
  private currentRecordingPath: string | null = null;
  private recordingState: RecordingState = {
    isRecording: false,
    currentTime: 0,
    isPlaying: false,
    isPaused: false,
    playTime: 0,
    duration: 0,
  };

  private audioVisualization: AudioVisualization = {
    currentLevel: 0,
    averageLevel: 0,
    peakLevel: 0,
    waveformData: [],
  };

  private config: VoiceNoteConfig = {
    maxDuration: 300000, // 5 minutes
    quality: 'medium',
    format: 'm4a',
    sampleRate: 44100,
    bitRate: 128000,
    channels: 1,
  };

  constructor() {
    this.audioRecorderPlayer = new AudioRecorderPlayer();
    this.setupAudioSession();
  }

  /**
   * Setup audio session for recording and playback
   */
  private async setupAudioSession(): Promise<void> {
    try {
      await AudioSession.setCategory('playAndRecord', {
        mixWithOthers: false,
        allowBluetooth: true,
        allowBluetoothA2DP: false,
        allowAirPlay: false,
      });
      
      await AudioSession.setActive(true);
    } catch (error) {
      console.error('Error setting up audio session:', error);
    }
  }

  /**
   * Check microphone permissions
   */
  async checkMicrophonePermissions(): Promise<boolean> {
    try {
      const permission = Platform.OS === 'ios' 
        ? PERMISSIONS.IOS.MICROPHONE
        : PERMISSIONS.ANDROID.RECORD_AUDIO;
      
      const result = await check(permission);
      return result === RESULTS.GRANTED;
    } catch (error) {
      console.error('Error checking microphone permissions:', error);
      return false;
    }
  }

  /**
   * Request microphone permissions
   */
  async requestMicrophonePermissions(): Promise<boolean> {
    try {
      const permission = Platform.OS === 'ios'
        ? PERMISSIONS.IOS.MICROPHONE
        : PERMISSIONS.ANDROID.RECORD_AUDIO;
      
      const result = await request(permission);
      return result === RESULTS.GRANTED;
    } catch (error) {
      console.error('Error requesting microphone permissions:', error);
      return false;
    }
  }

  /**
   * Start recording voice note
   */
  async startRecording(config?: Partial<VoiceNoteConfig>): Promise<string | null> {
    try {
      // Check permissions
      const hasPermission = await this.checkMicrophonePermissions();
      if (!hasPermission) {
        const granted = await this.requestMicrophonePermissions();
        if (!granted) {
          Alert.alert(
            'Microphone Permission Required',
            'Please grant microphone permissions to record voice notes.',
            [
              {text: 'Cancel'},
              {text: 'Settings', onPress: () => this.openSettings()},
            ]
          );
          return null;
        }
      }

      // Update config if provided
      if (config) {
        this.config = {...this.config, ...config};
      }

      // Generate unique file path
      const timestamp = Date.now();
      const fileName = `voice_note_${timestamp}.${this.config.format}`;
      const documentsPath = RNFS.DocumentDirectoryPath;
      const filePath = `${documentsPath}/voice_notes/${fileName}`;

      // Ensure directory exists
      await RNFS.mkdir(`${documentsPath}/voice_notes`);

      // Setup recording options
      const audioSet = {
        AudioEncoderAndroid: AudioEncoderAndroidType.AAC,
        AudioSourceAndroid: AudioSourceAndroidType.MIC,
        AVEncoderAudioQualityKeyIOS: this.getIOSQuality(),
        AVNumberOfChannelsKeyIOS: this.config.channels,
        AVFormatIDKeyIOS: AVEncodingOption.aac,
        OutputFormatAndroid: OutputFormatAndroidType.AAC_ADTS,
        AudioSamplingRateAndroid: this.config.sampleRate,
        AudioEncodingBitRateAndroid: this.config.bitRate,
      };

      // Start recording
      const result = await this.audioRecorderPlayer.startRecorder(filePath, audioSet);
      
      this.currentRecordingPath = result;
      this.recordingState.isRecording = true;
      this.recordingState.currentTime = 0;

      // Setup recording progress updates
      this.audioRecorderPlayer.addRecordBackListener((e) => {
        this.recordingState.currentTime = e.currentPosition;
        this.updateAudioVisualization(e.currentMetering || 0);
        
        // Auto-stop at max duration
        if (e.currentPosition >= this.config.maxDuration) {
          this.stopRecording();
        }
      });

      return result;
    } catch (error) {
      console.error('Error starting recording:', error);
      return null;
    }
  }

  /**
   * Stop recording
   */
  async stopRecording(): Promise<VoiceNote | null> {
    try {
      if (!this.recordingState.isRecording || !this.currentRecordingPath) {
        return null;
      }

      await this.audioRecorderPlayer.stopRecorder();
      this.audioRecorderPlayer.removeRecordBackListener();

      this.recordingState.isRecording = false;
      const recordingPath = this.currentRecordingPath;
      this.currentRecordingPath = null;

      // Get file info
      const fileInfo = await RNFS.stat(recordingPath);
      const fileName = recordingPath.split('/').pop() || 'voice_note.m4a';

      // Create voice note object
      const voiceNote: VoiceNote = {
        id: `voice_${Date.now()}`,
        fileName,
        filePath: recordingPath,
        duration: this.recordingState.currentTime,
        size: fileInfo.size,
        waveformData: [...this.audioVisualization.waveformData],
        created_at: new Date().toISOString(),
        metadata: {
          quality: this.config.quality,
          format: this.config.format,
          sampleRate: this.config.sampleRate,
          bitRate: this.config.bitRate,
        },
      };

      // Reset audio visualization
      this.audioVisualization = {
        currentLevel: 0,
        averageLevel: 0,
        peakLevel: 0,
        waveformData: [],
      };

      return voiceNote;
    } catch (error) {
      console.error('Error stopping recording:', error);
      return null;
    }
  }

  /**
   * Pause recording
   */
  async pauseRecording(): Promise<boolean> {
    try {
      if (!this.recordingState.isRecording) {
        return false;
      }

      await this.audioRecorderPlayer.pauseRecorder();
      return true;
    } catch (error) {
      console.error('Error pausing recording:', error);
      return false;
    }
  }

  /**
   * Resume recording
   */
  async resumeRecording(): Promise<boolean> {
    try {
      if (!this.recordingState.isRecording) {
        return false;
      }

      await this.audioRecorderPlayer.resumeRecorder();
      return true;
    } catch (error) {
      console.error('Error resuming recording:', error);
      return false;
    }
  }

  /**
   * Play voice note
   */
  async playVoiceNote(voiceNote: VoiceNote): Promise<boolean> {
    try {
      // Check if file exists
      const exists = await RNFS.exists(voiceNote.filePath);
      if (!exists) {
        Alert.alert('Error', 'Voice note file not found');
        return false;
      }

      // Start playback
      await this.audioRecorderPlayer.startPlayer(voiceNote.filePath);

      this.recordingState.isPlaying = true;
      this.recordingState.isPaused = false;
      this.recordingState.duration = voiceNote.duration;

      // Setup playback progress updates
      this.audioRecorderPlayer.addPlayBackListener((e) => {
        this.recordingState.playTime = e.currentPosition;
        
        // Auto-stop at end
        if (e.currentPosition >= e.duration) {
          this.stopPlayback();
        }
      });

      return true;
    } catch (error) {
      console.error('Error playing voice note:', error);
      return false;
    }
  }

  /**
   * Stop playback
   */
  async stopPlayback(): Promise<void> {
    try {
      await this.audioRecorderPlayer.stopPlayer();
      this.audioRecorderPlayer.removePlayBackListener();

      this.recordingState.isPlaying = false;
      this.recordingState.isPaused = false;
      this.recordingState.playTime = 0;
    } catch (error) {
      console.error('Error stopping playback:', error);
    }
  }

  /**
   * Pause playback
   */
  async pausePlayback(): Promise<boolean> {
    try {
      if (!this.recordingState.isPlaying) {
        return false;
      }

      await this.audioRecorderPlayer.pausePlayer();
      this.recordingState.isPaused = true;
      return true;
    } catch (error) {
      console.error('Error pausing playback:', error);
      return false;
    }
  }

  /**
   * Resume playback
   */
  async resumePlayback(): Promise<boolean> {
    try {
      if (!this.recordingState.isPlaying || !this.recordingState.isPaused) {
        return false;
      }

      await this.audioRecorderPlayer.resumePlayer();
      this.recordingState.isPaused = false;
      return true;
    } catch (error) {
      console.error('Error resuming playback:', error);
      return false;
    }
  }

  /**
   * Seek to position in playback
   */
  async seekTo(position: number): Promise<boolean> {
    try {
      if (!this.recordingState.isPlaying) {
        return false;
      }

      await this.audioRecorderPlayer.seekToPlayer(position);
      return true;
    } catch (error) {
      console.error('Error seeking:', error);
      return false;
    }
  }

  /**
   * Delete voice note file
   */
  async deleteVoiceNote(voiceNote: VoiceNote): Promise<boolean> {
    try {
      const exists = await RNFS.exists(voiceNote.filePath);
      if (exists) {
        await RNFS.unlink(voiceNote.filePath);
      }
      return true;
    } catch (error) {
      console.error('Error deleting voice note:', error);
      return false;
    }
  }

  /**
   * Get all voice notes from storage
   */
  async getAllVoiceNotes(): Promise<VoiceNote[]> {
    try {
      const documentsPath = RNFS.DocumentDirectoryPath;
      const voiceNotesPath = `${documentsPath}/voice_notes`;
      
      const exists = await RNFS.exists(voiceNotesPath);
      if (!exists) {
        return [];
      }

      const files = await RNFS.readDir(voiceNotesPath);
      const voiceNotes: VoiceNote[] = [];

      for (const file of files) {
        if (file.isFile() && this.isAudioFile(file.name)) {
          const voiceNote = await this.createVoiceNoteFromFile(file);
          if (voiceNote) {
            voiceNotes.push(voiceNote);
          }
        }
      }

      return voiceNotes.sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    } catch (error) {
      console.error('Error getting voice notes:', error);
      return [];
    }
  }

  /**
   * Transcribe voice note (placeholder for future implementation)
   */
  async transcribeVoiceNote(voiceNote: VoiceNote): Promise<string | null> {
    try {
      // This would integrate with a speech-to-text service
      // For now, return a placeholder
      return `Transcription for ${voiceNote.fileName} (not yet implemented)`;
    } catch (error) {
      console.error('Error transcribing voice note:', error);
      return null;
    }
  }

  /**
   * Update voice note metadata
   */
  async updateVoiceNote(voiceNote: VoiceNote): Promise<boolean> {
    try {
      // In a full implementation, this would save metadata to a database
      // For now, we'll just validate the update
      return true;
    } catch (error) {
      console.error('Error updating voice note:', error);
      return false;
    }
  }

  /**
   * Get recording state
   */
  getRecordingState(): RecordingState {
    return {...this.recordingState};
  }

  /**
   * Get audio visualization data
   */
  getAudioVisualization(): AudioVisualization {
    return {...this.audioVisualization};
  }

  /**
   * Update recording configuration
   */
  updateConfig(newConfig: Partial<VoiceNoteConfig>): void {
    this.config = {...this.config, ...newConfig};
  }

  /**
   * Get current configuration
   */
  getConfig(): VoiceNoteConfig {
    return {...this.config};
  }

  /**
   * Format duration for display
   */
  formatDuration(milliseconds: number): string {
    const totalSeconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }

  /**
   * Get iOS audio quality setting
   */
  private getIOSQuality(): AVEncoderAudioQualityIOSType {
    switch (this.config.quality) {
      case 'high':
        return AVEncoderAudioQualityIOSType.high;
      case 'medium':
        return AVEncoderAudioQualityIOSType.medium;
      case 'low':
        return AVEncoderAudioQualityIOSType.low;
      default:
        return AVEncoderAudioQualityIOSType.medium;
    }
  }

  /**
   * Update audio visualization during recording
   */
  private updateAudioVisualization(level: number): void {
    this.audioVisualization.currentLevel = level;
    this.audioVisualization.waveformData.push(level);
    
    // Keep only last 100 samples for waveform
    if (this.audioVisualization.waveformData.length > 100) {
      this.audioVisualization.waveformData.shift();
    }
    
    // Update average and peak levels
    const recent = this.audioVisualization.waveformData.slice(-10);
    this.audioVisualization.averageLevel = recent.reduce((a, b) => a + b, 0) / recent.length;
    this.audioVisualization.peakLevel = Math.max(...recent);
  }

  /**
   * Check if file is an audio file
   */
  private isAudioFile(fileName: string): boolean {
    const audioExtensions = ['.m4a', '.mp4', '.wav', '.aac', '.mp3'];
    const extension = fileName.toLowerCase().substring(fileName.lastIndexOf('.'));
    return audioExtensions.includes(extension);
  }

  /**
   * Create voice note object from file
   */
  private async createVoiceNoteFromFile(file: any): Promise<VoiceNote | null> {
    try {
      const voiceNote: VoiceNote = {
        id: `voice_${file.mtime}`,
        fileName: file.name,
        filePath: file.path,
        duration: 0, // Would need to be extracted from audio file
        size: file.size,
        created_at: new Date(file.mtime).toISOString(),
        metadata: {
          quality: 'medium',
          format: 'm4a',
          sampleRate: 44100,
          bitRate: 128000,
        },
      };

      return voiceNote;
    } catch (error) {
      console.error('Error creating voice note from file:', error);
      return null;
    }
  }

  /**
   * Open device settings
   */
  private openSettings(): void {
    // This would open device settings
    console.log('Opening device settings...');
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.audioRecorderPlayer.removeRecordBackListener();
    this.audioRecorderPlayer.removePlayBackListener();
  }
}

export const voiceNoteService = new VoiceNoteService();