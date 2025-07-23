/**
 * Voice Note Screen
 * 
 * Main interface for recording, managing, and playing voice notes
 * with waveform visualization and transcription features.
 */

import React, {useState, useEffect, useRef} from 'react';
import {
  View,
  StyleSheet,
  Dimensions,
  FlatList,
  Alert,
  Animated,
} from 'react-native';
import {
  Appbar,
  Card,
  Text,
  Button,
  IconButton,
  FAB,
  Chip,
  Surface,
  ProgressBar,
  Switch,
  List,
  Menu,
  Divider,
  ActivityIndicator,
  Snackbar,
} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import {useDispatch, useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import {Svg, Path, Line} from 'react-native-svg';

import {AppState} from '@/types';
import {
  initializeVoiceNotes,
  startRecording,
  stopRecording,
  pauseRecording,
  resumeRecording,
  playVoiceNote,
  stopPlayback,
  pausePlayback,
  resumePlayback,
  deleteVoiceNote,
  transcribeVoiceNote,
  updateVoiceNote,
  setShowWaveform,
  setShowTranscription,
  updateSettings,
  requestMicrophonePermission,
  updateRecordingState,
} from '@/store/slices/voiceNoteSlice';
import {VoiceNote} from '@/services/voiceNoteService';
import {colors, spacing, typography} from '@/constants/theme';

const {width: screenWidth, height: screenHeight} = Dimensions.get('window');

export const VoiceNoteScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  
  const {
    voiceNotes,
    currentNote,
    recordingState,
    audioVisualization,
    currentlyPlaying,
    config,
    isLoading,
    error,
    showWaveform,
    showTranscription,
    microphonePermission,
    settings,
  } = useSelector((state: AppState) => state.voiceNote);

  const [showMenu, setShowMenu] = useState(false);
  const [selectedNote, setSelectedNote] = useState<VoiceNote | null>(null);
  const [showSnackbar, setShowSnackbar] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  // Animation values
  const recordingAnimation = useRef(new Animated.Value(1)).current;
  const waveformAnimation = useRef(new Animated.Value(0)).current;

  // Update interval for recording state
  const updateInterval = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    initializeScreen();
    return cleanup;
  }, []);

  useEffect(() => {
    if (recordingState.isRecording) {
      startRecordingAnimation();
      startRecordingStateUpdates();
    } else {
      stopRecordingAnimation();
      stopRecordingStateUpdates();
    }
  }, [recordingState.isRecording]);

  useEffect(() => {
    if (error) {
      setSnackbarMessage(error);
      setShowSnackbar(true);
    }
  }, [error]);

  const initializeScreen = async () => {
    try {
      await dispatch(initializeVoiceNotes()).unwrap();
    } catch (error) {
      console.error('Failed to initialize voice notes:', error);
    }
  };

  const cleanup = () => {
    stopRecordingStateUpdates();
  };

  const startRecordingAnimation = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(recordingAnimation, {
          toValue: 0.3,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(recordingAnimation, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
      ])
    ).start();
  };

  const stopRecordingAnimation = () => {
    recordingAnimation.stopAnimation();
    Animated.timing(recordingAnimation, {
      toValue: 1,
      duration: 200,
      useNativeDriver: true,
    }).start();
  };

  const startRecordingStateUpdates = () => {
    updateInterval.current = setInterval(() => {
      dispatch(updateRecordingState());
    }, 100);
  };

  const stopRecordingStateUpdates = () => {
    if (updateInterval.current) {
      clearInterval(updateInterval.current);
      updateInterval.current = null;
    }
  };

  const handleStartRecording = async () => {
    try {
      if (!microphonePermission) {
        const granted = await dispatch(requestMicrophonePermission()).unwrap();
        if (!granted) {
          Alert.alert(
            'Permission Required',
            'Microphone permission is required to record voice notes.',
            [
              {text: 'Cancel'},
              {text: 'Settings', onPress: () => {/* Open settings */}},
            ]
          );
          return;
        }
      }

      await dispatch(startRecording()).unwrap();
    } catch (error) {
      console.error('Failed to start recording:', error);
    }
  };

  const handleStopRecording = async () => {
    try {
      await dispatch(stopRecording()).unwrap();
      setSnackbarMessage('Voice note saved successfully');
      setShowSnackbar(true);
    } catch (error) {
      console.error('Failed to stop recording:', error);
    }
  };

  const handlePauseResume = async () => {
    try {
      if (recordingState.isRecording) {
        await dispatch(pauseRecording()).unwrap();
      } else {
        await dispatch(resumeRecording()).unwrap();
      }
    } catch (error) {
      console.error('Failed to pause/resume recording:', error);
    }
  };

  const handlePlayVoiceNote = async (voiceNote: VoiceNote) => {
    try {
      if (currentlyPlaying === voiceNote.id) {
        if (recordingState.isPaused) {
          await dispatch(resumePlayback()).unwrap();
        } else {
          await dispatch(pausePlayback()).unwrap();
        }
      } else {
        await dispatch(stopPlayback()).unwrap();
        await dispatch(playVoiceNote(voiceNote)).unwrap();
      }
    } catch (error) {
      console.error('Failed to play voice note:', error);
    }
  };

  const handleStopPlayback = async () => {
    try {
      await dispatch(stopPlayback()).unwrap();
    } catch (error) {
      console.error('Failed to stop playback:', error);
    }
  };

  const handleDeleteVoiceNote = (voiceNote: VoiceNote) => {
    Alert.alert(
      'Delete Voice Note',
      `Are you sure you want to delete "${voiceNote.metadata.title || voiceNote.fileName}"?`,
      [
        {text: 'Cancel'},
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await dispatch(deleteVoiceNote(voiceNote)).unwrap();
              setSnackbarMessage('Voice note deleted');
              setShowSnackbar(true);
            } catch (error) {
              console.error('Failed to delete voice note:', error);
            }
          },
        },
      ]
    );
  };

  const handleTranscribeVoiceNote = async (voiceNote: VoiceNote) => {
    try {
      await dispatch(transcribeVoiceNote(voiceNote.id)).unwrap();
      setSnackbarMessage('Transcription completed');
      setShowSnackbar(true);
    } catch (error) {
      console.error('Failed to transcribe voice note:', error);
    }
  };

  const formatDuration = (milliseconds: number): string => {
    const totalSeconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const renderWaveform = () => {
    if (!showWaveform || audioVisualization.waveformData.length === 0) {
      return null;
    }

    const maxHeight = 60;
    const width = screenWidth - (spacing.md * 2);
    const barWidth = width / audioVisualization.waveformData.length;

    return (
      <Surface style={styles.waveformContainer}>
        <Svg width={width} height={maxHeight}>
          {audioVisualization.waveformData.map((level, index) => {
            const height = Math.max(2, (level / 100) * maxHeight);
            const x = index * barWidth;
            const y = (maxHeight - height) / 2;
            
            return (
              <Line
                key={index}
                x1={x}
                y1={y}
                x2={x}
                y2={y + height}
                stroke={colors.primary}
                strokeWidth={Math.max(1, barWidth - 1)}
                opacity={0.7}
              />
            );
          })}
        </Svg>
      </Surface>
    );
  };

  const renderRecordingControls = () => (
    <Surface style={styles.recordingControls}>
      <View style={styles.recordingInfo}>
        <Text style={styles.recordingTime}>
          {formatDuration(recordingState.currentTime)}
        </Text>
        <Text style={styles.maxDuration}>
          / {formatDuration(config.maxDuration)}
        </Text>
      </View>

      <ProgressBar
        progress={recordingState.currentTime / config.maxDuration}
        color={colors.primary}
        style={styles.progressBar}
      />

      {renderWaveform()}

      <View style={styles.controlButtons}>
        {recordingState.isRecording && (
          <IconButton
            icon="pause"
            mode="contained"
            size={24}
            onPress={handlePauseResume}
            style={styles.controlButton}
          />
        )}

        <Animated.View
          style={[
            styles.recordButton,
            {opacity: recordingAnimation},
          ]}>
          <IconButton
            icon={recordingState.isRecording ? "stop" : "mic"}
            mode="contained"
            size={32}
            onPress={recordingState.isRecording ? handleStopRecording : handleStartRecording}
            style={[
              styles.mainRecordButton,
              {backgroundColor: recordingState.isRecording ? colors.error : colors.primary},
            ]}
          />
        </Animated.View>

        <IconButton
          icon="settings"
          mode="outlined"
          size={24}
          onPress={() => setShowMenu(true)}
          style={styles.controlButton}
        />
      </View>
    </Surface>
  );

  const renderVoiceNoteItem = ({item}: {item: VoiceNote}) => {
    const isPlaying = currentlyPlaying === item.id;
    const isPaused = isPlaying && recordingState.isPaused;

    return (
      <Card style={styles.voiceNoteCard}>
        <Card.Content>
          <View style={styles.noteHeader}>
            <View style={styles.noteInfo}>
              <Text style={styles.noteTitle}>
                {item.metadata.title || item.fileName}
              </Text>
              <Text style={styles.noteDate}>
                {new Date(item.created_at).toLocaleDateString()}
              </Text>
            </View>
            
            <View style={styles.noteActions}>
              <IconButton
                icon={isPlaying ? (isPaused ? "play-arrow" : "pause") : "play-arrow"}
                size={20}
                onPress={() => handlePlayVoiceNote(item)}
              />
              <IconButton
                icon="more-vert"
                size={20}
                onPress={() => setSelectedNote(item)}
              />
            </View>
          </View>

          <View style={styles.noteMeta}>
            <Chip mode="outlined" compact style={styles.durationChip}>
              {formatDuration(item.duration)}
            </Chip>
            <Chip mode="outlined" compact style={styles.qualityChip}>
              {item.metadata.quality}
            </Chip>
            {item.transcription && (
              <Chip mode="outlined" compact style={styles.transcriptionChip}>
                Transcribed
              </Chip>
            )}
          </View>

          {isPlaying && (
            <View style={styles.playbackProgress}>
              <ProgressBar
                progress={recordingState.playTime / recordingState.duration}
                color={colors.primary}
                style={styles.playbackBar}
              />
              <Text style={styles.playbackTime}>
                {formatDuration(recordingState.playTime)} / {formatDuration(recordingState.duration)}
              </Text>
            </View>
          )}

          {showTranscription && item.transcription && (
            <View style={styles.transcriptionContainer}>
              <Text style={styles.transcriptionText}>
                {item.transcription}
              </Text>
            </View>
          )}
        </Card.Content>
      </Card>
    );
  };

  const renderSettingsMenu = () => (
    <Menu
      visible={showMenu}
      onDismiss={() => setShowMenu(false)}
      anchor={<View />}>
      
      <Menu.Item
        onPress={() => {
          dispatch(setShowWaveform(!showWaveform));
          setShowMenu(false);
        }}
        title="Show Waveform"
        leadingIcon={showWaveform ? "check-box" : "check-box-outline-blank"}
      />
      
      <Menu.Item
        onPress={() => {
          dispatch(setShowTranscription(!showTranscription));
          setShowMenu(false);
        }}
        title="Show Transcriptions"
        leadingIcon={showTranscription ? "check-box" : "check-box-outline-blank"}
      />
      
      <Divider />
      
      <Menu.Item
        onPress={() => {
          setShowMenu(false);
          navigation.navigate('VoiceNoteSettings' as never);
        }}
        title="Settings"
        leadingIcon="settings"
      />
    </Menu>
  );

  const renderNoteActionsMenu = () => {
    if (!selectedNote) return null;

    return (
      <Menu
        visible={!!selectedNote}
        onDismiss={() => setSelectedNote(null)}
        anchor={<View />}>
        
        <Menu.Item
          onPress={() => {
            handleTranscribeVoiceNote(selectedNote);
            setSelectedNote(null);
          }}
          title="Transcribe"
          leadingIcon="record-voice-over"
        />
        
        <Menu.Item
          onPress={() => {
            // Navigate to edit screen
            setSelectedNote(null);
          }}
          title="Edit"
          leadingIcon="edit"
        />
        
        <Menu.Item
          onPress={() => {
            // Share voice note
            setSelectedNote(null);
          }}
          title="Share"
          leadingIcon="share"
        />
        
        <Divider />
        
        <Menu.Item
          onPress={() => {
            handleDeleteVoiceNote(selectedNote);
            setSelectedNote(null);
          }}
          title="Delete"
          leadingIcon="delete"
          titleStyle={{color: colors.error}}
        />
      </Menu>
    );
  };

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title="Voice Notes" />
        <Appbar.Action
          icon="more-vert"
          onPress={() => setShowMenu(true)}
        />
      </Appbar.Header>

      <View style={styles.content}>
        {renderRecordingControls()}
        
        <View style={styles.notesSection}>
          <Text style={styles.sectionTitle}>
            My Voice Notes ({voiceNotes.length})
          </Text>
          
          {isLoading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color={colors.primary} />
              <Text style={styles.loadingText}>Loading voice notes...</Text>
            </View>
          ) : voiceNotes.length === 0 ? (
            <View style={styles.emptyState}>
              <Icon name="mic" size={64} color={colors.gray400} />
              <Text style={styles.emptyStateText}>No voice notes yet</Text>
              <Text style={styles.emptyStateSubtext}>
                Tap the microphone to record your first voice note
              </Text>
            </View>
          ) : (
            <FlatList
              data={voiceNotes}
              renderItem={renderVoiceNoteItem}
              keyExtractor={(item) => item.id}
              style={styles.notesList}
              contentContainerStyle={styles.notesListContent}
              showsVerticalScrollIndicator={false}
            />
          )}
        </View>
      </View>

      {renderSettingsMenu()}
      {renderNoteActionsMenu()}

      <Snackbar
        visible={showSnackbar}
        onDismiss={() => setShowSnackbar(false)}
        duration={3000}>
        {snackbarMessage}
      </Snackbar>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  appBar: {
    backgroundColor: colors.primary,
  },
  content: {
    flex: 1,
    padding: spacing.md,
  },
  recordingControls: {
    padding: spacing.lg,
    marginBottom: spacing.lg,
    borderRadius: 16,
    elevation: 2,
  },
  recordingInfo: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'baseline',
    marginBottom: spacing.md,
  },
  recordingTime: {
    ...typography.headlineMedium,
    color: colors.primary,
    fontWeight: 'bold',
  },
  maxDuration: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginLeft: spacing.xs,
  },
  progressBar: {
    height: 6,
    borderRadius: 3,
    marginBottom: spacing.lg,
  },
  waveformContainer: {
    height: 60,
    marginBottom: spacing.lg,
    borderRadius: 8,
    padding: spacing.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  controlButtons: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: spacing.lg,
  },
  controlButton: {
    backgroundColor: colors.surface,
  },
  recordButton: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  mainRecordButton: {
    width: 80,
    height: 80,
  },
  notesSection: {
    flex: 1,
  },
  sectionTitle: {
    ...typography.titleLarge,
    color: colors.onSurface,
    marginBottom: spacing.md,
    fontWeight: '600',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginTop: spacing.md,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  emptyStateText: {
    ...typography.headlineSmall,
    color: colors.onSurface,
    marginTop: spacing.md,
    textAlign: 'center',
  },
  emptyStateSubtext: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  notesList: {
    flex: 1,
  },
  notesListContent: {
    paddingBottom: spacing.xl,
  },
  voiceNoteCard: {
    marginBottom: spacing.md,
  },
  noteHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: spacing.sm,
  },
  noteInfo: {
    flex: 1,
  },
  noteTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    fontWeight: '500',
  },
  noteDate: {
    ...typography.bodySmall,
    color: colors.gray600,
    marginTop: spacing.xs,
  },
  noteActions: {
    flexDirection: 'row',
  },
  noteMeta: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
    marginBottom: spacing.sm,
  },
  durationChip: {
    height: 24,
  },
  qualityChip: {
    height: 24,
  },
  transcriptionChip: {
    height: 24,
  },
  playbackProgress: {
    marginTop: spacing.sm,
  },
  playbackBar: {
    height: 4,
    borderRadius: 2,
  },
  playbackTime: {
    ...typography.bodySmall,
    color: colors.gray600,
    textAlign: 'center',
    marginTop: spacing.xs,
  },
  transcriptionContainer: {
    marginTop: spacing.sm,
    padding: spacing.sm,
    backgroundColor: colors.surfaceVariant,
    borderRadius: 8,
  },
  transcriptionText: {
    ...typography.bodyMedium,
    color: colors.onSurfaceVariant,
    lineHeight: 20,
  },
});