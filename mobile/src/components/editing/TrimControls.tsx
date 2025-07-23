/**
 * Trim Controls Component
 * 
 * Interface for trimming video/audio clips
 */

import React, {useState} from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import {Text, Button} from 'react-native-paper';
import Slider from '@react-native-community/slider';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {colors, spacing, typography} from '@/constants/theme';

interface TrimControlsProps {
  duration: number;
  onTrimChange: (startTime: number, endTime: number) => void;
}

export const TrimControls: React.FC<TrimControlsProps> = ({
  duration,
  onTrimChange,
}) => {
  const [startTime, setStartTime] = useState(0);
  const [endTime, setEndTime] = useState(duration);
  const [isSettingStart, setIsSettingStart] = useState(true);

  const handleTimeChange = (value: number) => {
    if (isSettingStart) {
      setStartTime(Math.min(value, endTime - 0.1));
    } else {
      setEndTime(Math.max(value, startTime + 0.1));
    }
  };

  const handleApplyTrim = () => {
    onTrimChange(startTime, endTime);
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
  };

  const trimDuration = endTime - startTime;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Trim Clip</Text>
        <Text style={styles.duration}>
          Duration: {formatTime(trimDuration)}
        </Text>
      </View>

      <View style={styles.controls}>
        <View style={styles.timeSelectors}>
          <TouchableOpacity
            style={[
              styles.timeSelector,
              isSettingStart && styles.timeSelectorActive,
            ]}
            onPress={() => setIsSettingStart(true)}>
            <Icon 
              name="start" 
              size={20} 
              color={isSettingStart ? colors.primary : colors.gray600} 
            />
            <Text style={[
              styles.timeSelectorLabel,
              isSettingStart && styles.timeSelectorLabelActive,
            ]}>
              Start
            </Text>
            <Text style={styles.timeSelectorValue}>
              {formatTime(startTime)}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.timeSelector,
              !isSettingStart && styles.timeSelectorActive,
            ]}
            onPress={() => setIsSettingStart(false)}>
            <Icon 
              name="stop" 
              size={20} 
              color={!isSettingStart ? colors.primary : colors.gray600} 
            />
            <Text style={[
              styles.timeSelectorLabel,
              !isSettingStart && styles.timeSelectorLabelActive,
            ]}>
              End
            </Text>
            <Text style={styles.timeSelectorValue}>
              {formatTime(endTime)}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.sliderContainer}>
          <Text style={styles.sliderLabel}>
            {isSettingStart ? 'Set Start Time' : 'Set End Time'}
          </Text>
          <Slider
            style={styles.slider}
            minimumValue={0}
            maximumValue={duration}
            value={isSettingStart ? startTime : endTime}
            onValueChange={handleTimeChange}
            minimumTrackTintColor={colors.primary}
            maximumTrackTintColor={colors.gray300}
            thumbTintColor={colors.primary}
          />
          <View style={styles.sliderLabels}>
            <Text style={styles.sliderTime}>0:00</Text>
            <Text style={styles.sliderTime}>{formatTime(duration)}</Text>
          </View>
        </View>

        <View style={styles.trimVisualization}>
          <View style={styles.trimTrack}>
            <View
              style={[
                styles.trimArea,
                {
                  left: `${(startTime / duration) * 100}%`,
                  width: `${((endTime - startTime) / duration) * 100}%`,
                },
              ]}
            />
          </View>
        </View>

        <Button
          mode="contained"
          onPress={handleApplyTrim}
          style={styles.applyButton}>
          Apply Trim
        </Button>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    padding: spacing.md,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  title: {
    ...typography.titleMedium,
    color: colors.onSurface,
    fontWeight: '600',
  },
  duration: {
    ...typography.bodyMedium,
    color: colors.gray600,
  },
  controls: {
    paddingTop: spacing.sm,
  },
  timeSelectors: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: spacing.lg,
  },
  timeSelector: {
    alignItems: 'center',
    padding: spacing.md,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.gray300,
    minWidth: 120,
  },
  timeSelectorActive: {
    borderColor: colors.primary,
    backgroundColor: `${colors.primary}10`,
  },
  timeSelectorLabel: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginVertical: spacing.xs,
  },
  timeSelectorLabelActive: {
    color: colors.primary,
    fontWeight: '600',
  },
  timeSelectorValue: {
    ...typography.bodyLarge,
    color: colors.onSurface,
    fontWeight: '500',
  },
  sliderContainer: {
    marginBottom: spacing.lg,
  },
  sliderLabel: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    marginBottom: spacing.sm,
  },
  slider: {
    height: 40,
    marginHorizontal: -spacing.sm,
  },
  sliderLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.xs,
  },
  sliderTime: {
    ...typography.bodySmall,
    color: colors.gray600,
  },
  trimVisualization: {
    height: 40,
    marginBottom: spacing.lg,
  },
  trimTrack: {
    flex: 1,
    backgroundColor: colors.gray200,
    borderRadius: 4,
    overflow: 'hidden',
  },
  trimArea: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    backgroundColor: colors.primary,
    opacity: 0.3,
  },
  applyButton: {
    marginTop: spacing.sm,
  },
});