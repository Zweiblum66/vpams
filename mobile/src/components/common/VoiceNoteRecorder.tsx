/**
 * Voice Note Recorder Component
 * 
 * Reusable component for recording voice notes that can be
 * integrated into other screens like asset upload or comments.
 */

import React, {useState, useEffect, useRef} from 'react';
import {
  View,
  StyleSheet,
  Animated,
  Dimensions,
} from 'react-native';
import {
  Surface,
  IconButton,
  Text,
  ProgressBar,
  Chip,
  Portal,
  Modal,
  Button,
} from 'react-native-paper';
import {useDispatch, useSelector} from 'react-redux';
import {Svg, Line} from 'react-native-svg';

import {AppState} from '@/types';
import {
  startRecording,
  stopRecording,
  pauseRecording,
  resumeRecording,
  updateRecordingState,
  requestMicrophonePermission,
} from '@/store/slices/voiceNoteSlice';
import {VoiceNote, VoiceNoteConfig} from '@/services/voiceNoteService';
import {colors, spacing, typography} from '@/constants/theme';

interface VoiceNoteRecorderProps {
  onRecordingComplete?: (voiceNote: VoiceNote) => void;
  onRecordingStart?: () => void;
  onRecordingCancel?: () => void;
  config?: Partial<VoiceNoteConfig>;
  style?: any;
  compact?: boolean;
  showWaveform?: boolean;
}

export const VoiceNoteRecorder: React.FC<VoiceNoteRecorderProps> = ({
  onRecordingComplete,
  onRecordingStart,
  onRecordingCancel,
  config,
  style,
  compact = false,
  showWaveform = true,
}) => {
  const dispatch = useDispatch();
  
  const {
    recordingState,
    audioVisualization,
    microphonePermission,
    config: defaultConfig,
  } = useSelector((state: AppState) => state.voiceNote);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [recordingStarted, setRecordingStarted] = useState(false);

  // Animation values
  const recordingAnimation = useRef(new Animated.Value(1)).current;
  const pulseAnimation = useRef(new Animated.Value(1)).current;

  // Update interval
  const updateInterval = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (recordingState.isRecording) {
      startRecordingAnimations();
      startUpdates();
    } else {
      stopRecordingAnimations();
      stopUpdates();
    }
  }, [recordingState.isRecording]);

  useEffect(() => {
    return () => {
      stopUpdates();
    };
  }, []);

  const startRecordingAnimations = () => {
    // Pulsing red animation for recording
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

    // Pulse animation for the button
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnimation, {
          toValue: 1.2,
          duration: 800,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnimation, {
          toValue: 1,
          duration: 800,
          useNativeDriver: true,
        }),
      ])
    ).start();
  };

  const stopRecordingAnimations = () => {
    recordingAnimation.stopAnimation();
    pulseAnimation.stopAnimation();
    
    Animated.parallel([
      Animated.timing(recordingAnimation, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }),
      Animated.timing(pulseAnimation, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }),
    ]).start();
  };

  const startUpdates = () => {
    updateInterval.current = setInterval(() => {
      dispatch(updateRecordingState());
    }, 100);
  };

  const stopUpdates = () => {
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
          return;
        }
      }

      await dispatch(startRecording(config)).unwrap();
      setRecordingStarted(true);
      setIsModalOpen(!compact);
      onRecordingStart?.();
    } catch (error) {
      console.error('Failed to start recording:', error);
    }
  };

  const handleStopRecording = async () => {
    try {
      const voiceNote = await dispatch(stopRecording()).unwrap();
      setRecordingStarted(false);
      setIsModalOpen(false);
      onRecordingComplete?.(voiceNote);
    } catch (error) {
      console.error('Failed to stop recording:', error);
    }
  };

  const handleCancelRecording = async () => {
    try {
      // Stop recording without saving
      await dispatch(stopRecording()).unwrap();
      setRecordingStarted(false);
      setIsModalOpen(false);
      onRecordingCancel?.();
    } catch (error) {
      console.error('Failed to cancel recording:', error);
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

    const maxHeight = 40;
    const width = 200;
    const barWidth = width / Math.max(audioVisualization.waveformData.length, 1);

    return (
      <View style={styles.waveformContainer}>
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
                opacity={0.8}
              />
            );
          })}
        </Svg>
      </View>
    );
  };

  const renderCompactRecorder = () => (
    <View style={[styles.compactContainer, style]}>
      <Animated.View
        style={[
          styles.compactButton,
          {
            opacity: recordingAnimation,
            transform: [{scale: pulseAnimation}],
          },
        ]}>
        <IconButton
          icon={recordingStarted ? "stop" : "mic"}
          mode="contained"
          size={compact ? 20 : 24}
          onPress={recordingStarted ? handleStopRecording : handleStartRecording}
          style={[
            styles.recordButton,
            {
              backgroundColor: recordingStarted ? colors.error : colors.primary,
            },
          ]}
        />
      </Animated.View>
      
      {recordingStarted && (
        <View style={styles.compactInfo}>
          <Text style={styles.compactTime}>
            {formatDuration(recordingState.currentTime)}
          </Text>
          {!compact && (
            <IconButton
              icon="pause"
              size={16}
              onPress={handlePauseResume}
              style={styles.compactPauseButton}
            />
          )}
        </View>
      )}
    </View>
  );

  const renderFullRecorder = () => (
    <Portal>
      <Modal
        visible={isModalOpen}
        onDismiss={() => setIsModalOpen(false)}
        contentContainerStyle={styles.modalContainer}>
        
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Recording Voice Note</Text>
          <IconButton
            icon="close"
            size={20}
            onPress={() => setIsModalOpen(false)}
          />
        </View>

        <View style={styles.recordingDisplay}>
          <Animated.View
            style={[
              styles.recordingIndicator,
              {opacity: recordingAnimation},
            ]}>
            <View style={styles.recordingDot} />
            <Text style={styles.recordingText}>REC</Text>
          </Animated.View>

          <Text style={styles.recordingTime}>
            {formatDuration(recordingState.currentTime)}
          </Text>

          <Text style={styles.maxDurationText}>
            Max: {formatDuration((config?.maxDuration || defaultConfig.maxDuration))}
          </Text>

          <ProgressBar
            progress={recordingState.currentTime / (config?.maxDuration || defaultConfig.maxDuration)}
            color={colors.primary}
            style={styles.progressBar}
          />

          {renderWaveform()}

          <View style={styles.qualityInfo}>
            <Chip mode="outlined" compact>
              {(config?.quality || defaultConfig.quality).toUpperCase()}
            </Chip>
            <Chip mode="outlined" compact>
              {config?.format || defaultConfig.format}
            </Chip>
          </View>
        </View>

        <View style={styles.modalControls}>
          <Button
            mode="outlined"
            onPress={handleCancelRecording}
            style={styles.modalButton}>
            Cancel
          </Button>

          <Animated.View
            style={[
              styles.modalRecordButton,
              {transform: [{scale: pulseAnimation}]},
            ]}>
            <IconButton
              icon={recordingState.isRecording ? "pause" : "play-arrow"}
              mode="contained"
              size={32}
              onPress={handlePauseResume}
              style={[
                styles.mainRecordButton,
                {backgroundColor: colors.primary},
              ]}
            />
          </Animated.View>

          <Button
            mode="contained"
            onPress={handleStopRecording}
            style={styles.modalButton}>
            Save
          </Button>
        </View>
      </Modal>
    </Portal>
  );

  return (
    <>
      {renderCompactRecorder()}
      {!compact && renderFullRecorder()}
    </>
  );
};

const styles = StyleSheet.create({
  compactContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  compactButton: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  recordButton: {
    margin: 0,
  },
  compactInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  compactTime: {
    ...typography.bodySmall,
    color: colors.primary,
    fontWeight: '600',
    minWidth: 40,
  },
  compactPauseButton: {
    margin: 0,
  },
  modalContainer: {
    backgroundColor: colors.surface,
    margin: spacing.xl,
    borderRadius: 16,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing.lg,
    paddingBottom: spacing.md,
  },
  modalTitle: {
    ...typography.headlineSmall,
    color: colors.onSurface,
    fontWeight: '600',
  },
  recordingDisplay: {
    alignItems: 'center',
    padding: spacing.xl,
    paddingTop: spacing.lg,
  },
  recordingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  recordingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.error,
    marginRight: spacing.xs,
  },
  recordingText: {
    ...typography.bodySmall,
    color: colors.error,
    fontWeight: '600',
  },
  recordingTime: {
    ...typography.headlineLarge,
    color: colors.primary,
    fontWeight: 'bold',
    marginBottom: spacing.xs,
  },
  maxDurationText: {
    ...typography.bodySmall,
    color: colors.gray600,
    marginBottom: spacing.lg,
  },
  progressBar: {
    width: '100%',
    height: 6,
    borderRadius: 3,
    marginBottom: spacing.lg,
  },
  waveformContainer: {
    height: 40,
    marginBottom: spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  qualityInfo: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  modalControls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing.lg,
    paddingTop: spacing.md,
  },
  modalButton: {
    minWidth: 80,
  },
  modalRecordButton: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  mainRecordButton: {
    width: 64,
    height: 64,
  },
});