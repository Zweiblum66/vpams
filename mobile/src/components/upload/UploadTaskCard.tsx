/**
 * Upload Task Card Component
 * 
 * Displays individual upload task with progress,
 * status, controls, and metadata.
 */

import React from 'react';
import {View, StyleSheet, TouchableOpacity} from 'react-native';
import {
  Card,
  Text,
  ProgressBar,
  IconButton,
  Chip,
  Button,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {UploadTask} from '@/types';
import {colors, spacing, typography} from '@/constants/theme';
import {
  formatFileSize,
  formatUploadSpeed,
  formatTimeRemaining,
  formatPercentage,
  truncateText,
} from '@/utils/formatters';

interface UploadTaskCardProps {
  task: UploadTask;
  onAction: (action: string) => void;
}

export const UploadTaskCard: React.FC<UploadTaskCardProps> = ({
  task,
  onAction,
}) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'uploading':
        return colors.primary;
      case 'completed':
        return colors.success;
      case 'failed':
        return colors.error;
      case 'paused':
        return colors.warning;
      case 'queued':
        return colors.gray500;
      default:
        return colors.gray400;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'uploading':
        return 'cloud-upload';
      case 'completed':
        return 'check-circle';
      case 'failed':
        return 'error';
      case 'paused':
        return 'pause-circle';
      case 'queued':
        return 'schedule';
      default:
        return 'help';
    }
  };

  const getFileTypeIcon = (mimeType: string) => {
    if (mimeType.startsWith('image/')) return 'image';
    if (mimeType.startsWith('video/')) return 'videocam';
    if (mimeType.startsWith('audio/')) return 'audiotrack';
    return 'insert-drive-file';
  };

  const renderProgressInfo = () => {
    if (task.status === 'completed') {
      return (
        <View style={styles.progressInfo}>
          <Text style={styles.progressText}>
            {formatFileSize(task.file_size)} • Completed
          </Text>
        </View>
      );
    }

    if (task.status === 'failed') {
      return (
        <View style={styles.progressInfo}>
          <Text style={[styles.progressText, {color: colors.error}]}>
            Failed: {task.error || 'Upload failed'}
          </Text>
        </View>
      );
    }

    if (task.status === 'queued') {
      return (
        <View style={styles.progressInfo}>
          <Text style={styles.progressText}>
            {formatFileSize(task.file_size)} • Queued
          </Text>
        </View>
      );
    }

    if (task.status === 'paused') {
      return (
        <View style={styles.progressInfo}>
          <Text style={styles.progressText}>
            {formatPercentage(task.progress / 100)} • Paused
          </Text>
        </View>
      );
    }

    // Uploading
    const uploadedSize = (task.file_size * task.progress) / 100;
    const timeRemaining = task.upload_speed > 0 
      ? (task.file_size - uploadedSize) / task.upload_speed 
      : 0;

    return (
      <View style={styles.progressInfo}>
        <Text style={styles.progressText}>
          {formatFileSize(uploadedSize)} / {formatFileSize(task.file_size)}
        </Text>
        {task.upload_speed > 0 && (
          <Text style={styles.speedText}>
            {formatUploadSpeed(task.upload_speed)} • {formatTimeRemaining(timeRemaining)}
          </Text>
        )}
      </View>
    );
  };

  const renderActions = () => {
    const actions = [];

    if (task.status === 'uploading') {
      actions.push(
        <IconButton
          key="pause"
          icon="pause"
          size={20}
          onPress={() => onAction('pause')}
          iconColor={colors.warning}
        />
      );
    }

    if (task.status === 'paused') {
      actions.push(
        <IconButton
          key="resume"
          icon="play-arrow"
          size={20}
          onPress={() => onAction('resume')}
          iconColor={colors.success}
        />
      );
    }

    if (task.status === 'failed') {
      actions.push(
        <IconButton
          key="retry"
          icon="refresh"
          size={20}
          onPress={() => onAction('retry')}
          iconColor={colors.primary}
        />
      );
    }

    if (['uploading', 'paused', 'queued', 'failed'].includes(task.status)) {
      actions.push(
        <IconButton
          key="cancel"
          icon="close"
          size={20}
          onPress={() => onAction('cancel')}
          iconColor={colors.error}
        />
      );
    }

    return actions.length > 0 ? (
      <View style={styles.actions}>
        {actions}
      </View>
    ) : null;
  };

  return (
    <Card style={styles.card}>
      <TouchableOpacity 
        style={styles.cardContent}
        activeOpacity={0.7}
        onPress={() => onAction('details')}>
        
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.fileInfo}>
            <Icon
              name={getFileTypeIcon(task.file_type)}
              size={24}
              color={colors.primary}
              style={styles.fileIcon}
            />
            
            <View style={styles.fileDetails}>
              <Text style={styles.fileName} numberOfLines={1}>
                {truncateText(task.file_name, 30)}
              </Text>
              
              <View style={styles.metaRow}>
                <Chip
                  mode="flat"
                  compact
                  style={[
                    styles.statusChip,
                    {backgroundColor: getStatusColor(task.status) + '20'}
                  ]}>
                  <View style={styles.statusContent}>
                    <Icon
                      name={getStatusIcon(task.status)}
                      size={12}
                      color={getStatusColor(task.status)}
                    />
                    <Text style={[styles.statusText, {color: getStatusColor(task.status)}]}>
                      {task.status.toUpperCase()}
                    </Text>
                  </View>
                </Chip>
                
                {task.project_id && (
                  <Text style={styles.projectText} numberOfLines={1}>
                    • {task.project_name || 'Project'}
                  </Text>
                )}
              </View>
            </View>
          </View>
          
          {renderActions()}
        </View>

        {/* Progress Bar */}
        {task.status !== 'completed' && task.status !== 'failed' && (
          <ProgressBar
            progress={task.progress / 100}
            color={getStatusColor(task.status)}
            style={styles.progressBar}
          />
        )}

        {/* Progress Info */}
        {renderProgressInfo()}

        {/* Additional Info for Failed Uploads */}
        {task.status === 'failed' && task.retry_count > 0 && (
          <View style={styles.retryInfo}>
            <Text style={styles.retryText}>
              Retry attempt {task.retry_count} of 3
            </Text>
          </View>
        )}
      </TouchableOpacity>
    </Card>
  );
};

const styles = StyleSheet.create({
  card: {
    marginBottom: spacing.sm,
    elevation: 1,
  },
  cardContent: {
    padding: spacing.md,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: spacing.sm,
  },
  fileInfo: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  fileIcon: {
    marginRight: spacing.sm,
    marginTop: 2,
  },
  fileDetails: {
    flex: 1,
  },
  fileName: {
    ...typography.bodyLarge,
    color: colors.onSurface,
    fontWeight: '600',
    marginBottom: spacing.xs,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  statusChip: {
    height: 24,
    marginRight: spacing.sm,
  },
  statusContent: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.xs,
  },
  statusText: {
    ...typography.labelSmall,
    marginLeft: spacing.xs,
    fontWeight: '600',
  },
  projectText: {
    ...typography.bodySmall,
    color: colors.gray600,
    flex: 1,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  progressBar: {
    height: 4,
    borderRadius: 2,
    marginBottom: spacing.sm,
  },
  progressInfo: {
    marginBottom: spacing.xs,
  },
  progressText: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    fontWeight: '500',
  },
  speedText: {
    ...typography.bodySmall,
    color: colors.gray600,
    marginTop: spacing.xs,
  },
  retryInfo: {
    marginTop: spacing.xs,
    paddingTop: spacing.xs,
    borderTopWidth: 1,
    borderTopColor: colors.gray200,
  },
  retryText: {
    ...typography.bodySmall,
    color: colors.warning,
    fontStyle: 'italic',
  },
});