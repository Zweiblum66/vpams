/**
 * Voice Note Redux Slice
 * 
 * Manages voice note state, recordings, and playback
 * for the mobile application.
 */

import {createSlice, createAsyncThunk, PayloadAction} from '@reduxjs/toolkit';
import {voiceNoteService, VoiceNote, VoiceNoteConfig, RecordingState, AudioVisualization} from '@/services/voiceNoteService';

export interface VoiceNoteState {
  // Voice notes data
  voiceNotes: VoiceNote[];
  currentNote: VoiceNote | null;
  
  // Recording state
  recordingState: RecordingState;
  audioVisualization: AudioVisualization;
  
  // Playback state
  currentlyPlaying: string | null;
  
  // Configuration
  config: VoiceNoteConfig;
  
  // UI state
  isLoading: boolean;
  error: string | null;
  showWaveform: boolean;
  showTranscription: boolean;
  
  // Permissions
  microphonePermission: boolean;
  
  // Settings
  settings: {
    autoTranscribe: boolean;
    saveToGallery: boolean;
    enhanceAudio: boolean;
    noiseReduction: boolean;
    defaultQuality: VoiceNoteConfig['quality'];
    maxDuration: number;
    autoStopOnSilence: boolean;
    silenceThreshold: number;
  };
}

const initialState: VoiceNoteState = {
  voiceNotes: [],
  currentNote: null,
  
  recordingState: {
    isRecording: false,
    currentTime: 0,
    isPlaying: false,
    isPaused: false,
    playTime: 0,
    duration: 0,
  },
  
  audioVisualization: {
    currentLevel: 0,
    averageLevel: 0,
    peakLevel: 0,
    waveformData: [],
  },
  
  currentlyPlaying: null,
  
  config: {
    maxDuration: 300000, // 5 minutes
    quality: 'medium',
    format: 'm4a',
    sampleRate: 44100,
    bitRate: 128000,
    channels: 1,
  },
  
  isLoading: false,
  error: null,
  showWaveform: true,
  showTranscription: false,
  
  microphonePermission: false,
  
  settings: {
    autoTranscribe: false,
    saveToGallery: false,
    enhanceAudio: true,
    noiseReduction: true,
    defaultQuality: 'medium',
    maxDuration: 300000,
    autoStopOnSilence: false,
    silenceThreshold: -40,
  },
};

// Async thunks
export const initializeVoiceNotes = createAsyncThunk(
  'voiceNote/initialize',
  async (_, {dispatch}) => {
    try {
      // Check microphone permissions
      const hasPermission = await voiceNoteService.checkMicrophonePermissions();
      dispatch(setMicrophonePermission(hasPermission));
      
      // Load existing voice notes
      const voiceNotes = await voiceNoteService.getAllVoiceNotes();
      
      return {voiceNotes, hasPermission};
    } catch (error) {
      throw new Error('Failed to initialize voice notes');
    }
  }
);

export const requestMicrophonePermission = createAsyncThunk(
  'voiceNote/requestPermission',
  async () => {
    const granted = await voiceNoteService.requestMicrophonePermissions();
    return granted;
  }
);

export const startRecording = createAsyncThunk(
  'voiceNote/startRecording',
  async (config?: Partial<VoiceNoteConfig>, {getState, dispatch}) => {
    const state = getState() as {voiceNote: VoiceNoteState};
    
    // Update config if provided
    if (config) {
      const newConfig = {...state.voiceNote.config, ...config};
      voiceNoteService.updateConfig(newConfig);
      dispatch(updateConfig(newConfig));
    }
    
    const recordingPath = await voiceNoteService.startRecording();
    if (!recordingPath) {
      throw new Error('Failed to start recording');
    }
    
    return recordingPath;
  }
);

export const stopRecording = createAsyncThunk(
  'voiceNote/stopRecording',
  async (_, {getState, dispatch}) => {
    const voiceNote = await voiceNoteService.stopRecording();
    if (!voiceNote) {
      throw new Error('Failed to stop recording');
    }
    
    const state = getState() as {voiceNote: VoiceNoteState};
    
    // Auto-transcribe if enabled
    if (state.voiceNote.settings.autoTranscribe) {
      dispatch(transcribeVoiceNote(voiceNote.id));
    }
    
    return voiceNote;
  }
);

export const pauseRecording = createAsyncThunk(
  'voiceNote/pauseRecording',
  async () => {
    const success = await voiceNoteService.pauseRecording();
    if (!success) {
      throw new Error('Failed to pause recording');
    }
    return true;
  }
);

export const resumeRecording = createAsyncThunk(
  'voiceNote/resumeRecording',
  async () => {
    const success = await voiceNoteService.resumeRecording();
    if (!success) {
      throw new Error('Failed to resume recording');
    }
    return true;
  }
);

export const playVoiceNote = createAsyncThunk(
  'voiceNote/playVoiceNote',
  async (voiceNote: VoiceNote) => {
    const success = await voiceNoteService.playVoiceNote(voiceNote);
    if (!success) {
      throw new Error('Failed to play voice note');
    }
    return voiceNote;
  }
);

export const stopPlayback = createAsyncThunk(
  'voiceNote/stopPlayback',
  async () => {
    await voiceNoteService.stopPlayback();
    return true;
  }
);

export const pausePlayback = createAsyncThunk(
  'voiceNote/pausePlayback',
  async () => {
    const success = await voiceNoteService.pausePlayback();
    if (!success) {
      throw new Error('Failed to pause playback');
    }
    return true;
  }
);

export const resumePlayback = createAsyncThunk(
  'voiceNote/resumePlayback',
  async () => {
    const success = await voiceNoteService.resumePlayback();
    if (!success) {
      throw new Error('Failed to resume playback');
    }
    return true;
  }
);

export const seekToPosition = createAsyncThunk(
  'voiceNote/seekToPosition',
  async (position: number) => {
    const success = await voiceNoteService.seekTo(position);
    if (!success) {
      throw new Error('Failed to seek to position');
    }
    return position;
  }
);

export const deleteVoiceNote = createAsyncThunk(
  'voiceNote/deleteVoiceNote',
  async (voiceNote: VoiceNote) => {
    const success = await voiceNoteService.deleteVoiceNote(voiceNote);
    if (!success) {
      throw new Error('Failed to delete voice note');
    }
    return voiceNote.id;
  }
);

export const transcribeVoiceNote = createAsyncThunk(
  'voiceNote/transcribeVoiceNote',
  async (voiceNoteId: string, {getState}) => {
    const state = getState() as {voiceNote: VoiceNoteState};
    const voiceNote = state.voiceNote.voiceNotes.find(note => note.id === voiceNoteId);
    
    if (!voiceNote) {
      throw new Error('Voice note not found');
    }
    
    const transcription = await voiceNoteService.transcribeVoiceNote(voiceNote);
    return {voiceNoteId, transcription};
  }
);

export const updateVoiceNote = createAsyncThunk(
  'voiceNote/updateVoiceNote',
  async (voiceNote: VoiceNote) => {
    const success = await voiceNoteService.updateVoiceNote(voiceNote);
    if (!success) {
      throw new Error('Failed to update voice note');
    }
    return voiceNote;
  }
);

export const refreshVoiceNotes = createAsyncThunk(
  'voiceNote/refreshVoiceNotes',
  async () => {
    const voiceNotes = await voiceNoteService.getAllVoiceNotes();
    return voiceNotes;
  }
);

// Create interval thunk for real-time updates
export const updateRecordingState = createAsyncThunk(
  'voiceNote/updateRecordingState',
  async () => {
    const recordingState = voiceNoteService.getRecordingState();
    const audioVisualization = voiceNoteService.getAudioVisualization();
    return {recordingState, audioVisualization};
  }
);

const voiceNoteSlice = createSlice({
  name: 'voiceNote',
  initialState,
  reducers: {
    setMicrophonePermission: (state, action: PayloadAction<boolean>) => {
      state.microphonePermission = action.payload;
    },
    
    setCurrentNote: (state, action: PayloadAction<VoiceNote | null>) => {
      state.currentNote = action.payload;
    },
    
    updateConfig: (state, action: PayloadAction<VoiceNoteConfig>) => {
      state.config = action.payload;
    },
    
    updateSettings: (state, action: PayloadAction<Partial<VoiceNoteState['settings']>>) => {
      state.settings = {...state.settings, ...action.payload};
    },
    
    setShowWaveform: (state, action: PayloadAction<boolean>) => {
      state.showWaveform = action.payload;
    },
    
    setShowTranscription: (state, action: PayloadAction<boolean>) => {
      state.showTranscription = action.payload;
    },
    
    updateRecordingStateSync: (state, action: PayloadAction<RecordingState>) => {
      state.recordingState = action.payload;
    },
    
    updateAudioVisualizationSync: (state, action: PayloadAction<AudioVisualization>) => {
      state.audioVisualization = action.payload;
    },
    
    clearError: (state) => {
      state.error = null;
    },
    
    resetVoiceNoteState: () => initialState,
  },
  
  extraReducers: (builder) => {
    builder
      // Initialize voice notes
      .addCase(initializeVoiceNotes.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(initializeVoiceNotes.fulfilled, (state, action) => {
        state.isLoading = false;
        state.voiceNotes = action.payload.voiceNotes;
        state.microphonePermission = action.payload.hasPermission;
      })
      .addCase(initializeVoiceNotes.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to initialize voice notes';
      })
      
      // Request microphone permission
      .addCase(requestMicrophonePermission.fulfilled, (state, action) => {
        state.microphonePermission = action.payload;
      })
      
      // Start recording
      .addCase(startRecording.pending, (state) => {
        state.error = null;
      })
      .addCase(startRecording.fulfilled, (state) => {
        state.recordingState.isRecording = true;
        state.recordingState.currentTime = 0;
      })
      .addCase(startRecording.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to start recording';
      })
      
      // Stop recording
      .addCase(stopRecording.fulfilled, (state, action) => {
        state.recordingState.isRecording = false;
        state.recordingState.currentTime = 0;
        state.voiceNotes.unshift(action.payload);
        state.currentNote = action.payload;
        state.audioVisualization = {
          currentLevel: 0,
          averageLevel: 0,
          peakLevel: 0,
          waveformData: [],
        };
      })
      .addCase(stopRecording.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to stop recording';
      })
      
      // Play voice note
      .addCase(playVoiceNote.fulfilled, (state, action) => {
        state.currentlyPlaying = action.payload.id;
        state.recordingState.isPlaying = true;
        state.recordingState.isPaused = false;
        state.recordingState.duration = action.payload.duration;
      })
      .addCase(playVoiceNote.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to play voice note';
      })
      
      // Stop playback
      .addCase(stopPlayback.fulfilled, (state) => {
        state.currentlyPlaying = null;
        state.recordingState.isPlaying = false;
        state.recordingState.isPaused = false;
        state.recordingState.playTime = 0;
      })
      
      // Pause/resume playback
      .addCase(pausePlayback.fulfilled, (state) => {
        state.recordingState.isPaused = true;
      })
      .addCase(resumePlayback.fulfilled, (state) => {
        state.recordingState.isPaused = false;
      })
      
      // Delete voice note
      .addCase(deleteVoiceNote.fulfilled, (state, action) => {
        state.voiceNotes = state.voiceNotes.filter(note => note.id !== action.payload);
        if (state.currentNote?.id === action.payload) {
          state.currentNote = null;
        }
        if (state.currentlyPlaying === action.payload) {
          state.currentlyPlaying = null;
          state.recordingState.isPlaying = false;
        }
      })
      .addCase(deleteVoiceNote.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to delete voice note';
      })
      
      // Transcribe voice note
      .addCase(transcribeVoiceNote.fulfilled, (state, action) => {
        const {voiceNoteId, transcription} = action.payload;
        const voiceNote = state.voiceNotes.find(note => note.id === voiceNoteId);
        if (voiceNote && transcription) {
          voiceNote.transcription = transcription;
        }
      })
      
      // Update voice note
      .addCase(updateVoiceNote.fulfilled, (state, action) => {
        const index = state.voiceNotes.findIndex(note => note.id === action.payload.id);
        if (index !== -1) {
          state.voiceNotes[index] = action.payload;
        }
        if (state.currentNote?.id === action.payload.id) {
          state.currentNote = action.payload;
        }
      })
      
      // Refresh voice notes
      .addCase(refreshVoiceNotes.fulfilled, (state, action) => {
        state.voiceNotes = action.payload;
      })
      
      // Update recording state
      .addCase(updateRecordingState.fulfilled, (state, action) => {
        state.recordingState = action.payload.recordingState;
        state.audioVisualization = action.payload.audioVisualization;
      });
  },
});

export const {
  setMicrophonePermission,
  setCurrentNote,
  updateConfig,
  updateSettings,
  setShowWaveform,
  setShowTranscription,
  updateRecordingStateSync,
  updateAudioVisualizationSync,
  clearError,
  resetVoiceNoteState,
} = voiceNoteSlice.actions;

export default voiceNoteSlice.reducer;