/**
 * Upload Tab Screen
 * 
 * Main upload interface accessible from the bottom tab,
 * showing upload queue, progress, and quick upload options.
 */

import React, {useState, useCallback} from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import {
  Appbar,
  Card,
  Button,
  Text,
  IconButton,
  ProgressBar,
  FAB,
  Chip,
} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import {useDispatch, useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import {launchImageLibrary, launchCamera, MediaType} from 'react-native-image-picker';
import DocumentPicker from 'react-native-document-picker';

import {AppState, UploadTask} from '@/types';
import {
  addUploadTask,
  pauseUpload,
  resumeUpload,
  cancelUpload,
  retryUpload,
} from '@/store/slices/uploadsSlice';
import {UploadTaskCard} from '@/components/upload/UploadTaskCard';
import {EmptyState} from '@/components/common/EmptyState';
import {colors, spacing, typography} from '@/constants/theme';
import {uploadService} from '@/services/uploadService';
import {formatFileSize, formatUploadSpeed} from '@/utils/formatters';

export const UploadTabScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  
  const {
    tasks,
    queue,
    activeUploads,
    settings,
    isUploading,
    totalProgress,
    networkType,
  } = useSelector((state: AppState) => state.uploads);

  const [showCompleted, setShowCompleted] = useState(false);

  const uploadTasks = Object.values(tasks);
  const queuedTasks = uploadTasks.filter(task => task.status === 'queued');
  const activeTasks = uploadTasks.filter(task => 
    task.status === 'uploading' || task.status === 'processing'
  );
  const completedTasks = uploadTasks.filter(task => task.status === 'completed');
  const failedTasks = uploadTasks.filter(task => task.status === 'failed');

  const totalTasks = uploadTasks.length;
  const completedCount = completedTasks.length;

  const handleSelectFiles = useCallback(async () => {
    try {
      const results = await DocumentPicker.pick({
        type: [DocumentPicker.types.allFiles],
        allowMultiSelection: true,
        copyTo: 'cachesDirectory',
      });

      for (const file of results) {
        const uploadTask = await uploadService.createUploadTask({
          uri: file.fileCopyUri || file.uri,
          name: file.name || 'Unknown',
          type: file.type || 'application/octet-stream',
          size: file.size || 0,
        });

        dispatch(addUploadTask(uploadTask));
      }
    } catch (error: any) {
      if (!DocumentPicker.isCancel(error)) {
        Alert.alert('Error', 'Failed to select files');
      }
    }
  }, [dispatch]);

  const handleTakePhoto = useCallback(() => {
    launchCamera(
      {
        mediaType: 'photo' as MediaType,
        quality: 0.8,
        includeBase64: false,
      },
      (response) => {
        if (response.assets && response.assets[0]) {
          const asset = response.assets[0];
          uploadService.createUploadTask({
            uri: asset.uri!,
            name: asset.fileName || `photo_${Date.now()}.jpg`,
            type: asset.type || 'image/jpeg',
            size: asset.fileSize || 0,
          }).then(uploadTask => {
            dispatch(addUploadTask(uploadTask));
          });
        }
      }
    );
  }, [dispatch]);

  const handleSelectFromLibrary = useCallback(() => {
    launchImageLibrary(
      {
        mediaType: 'mixed' as MediaType,
        quality: 0.8,
        selectionLimit: 10,
        includeBase64: false,
      },
      (response) => {
        if (response.assets) {
          response.assets.forEach(asset => {
            uploadService.createUploadTask({
              uri: asset.uri!,
              name: asset.fileName || `media_${Date.now()}`,
              type: asset.type || 'application/octet-stream',
              size: asset.fileSize || 0,
            }).then(uploadTask => {
              dispatch(addUploadTask(uploadTask));
            });
          });
        }
      }
    );
  }, [dispatch]);

  const handleTaskAction = useCallback((taskId: string, action: string) => {
    switch (action) {
      case 'pause':
        dispatch(pauseUpload(taskId));
        break;
      case 'resume':
        dispatch(resumeUpload(taskId));
        break;
      case 'cancel':
        dispatch(cancelUpload(taskId));
        break;
      case 'retry':
        dispatch(retryUpload(taskId));
        break;
    }
  }, [dispatch]);

  const renderUploadSummary = () => {
    if (totalTasks === 0) return null;

    const totalSize = uploadTasks.reduce((sum, task) => sum + task.file_size, 0);
    const uploadedSize = uploadTasks.reduce((sum, task) => {
      return sum + (task.file_size * (task.progress / 100));
    }, 0);

    return (
      <Card style={styles.summaryCard}>
        <Card.Content>
          <Text style={styles.summaryTitle}>Upload Summary</Text>
          
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Progress:</Text>
            <Text style={styles.summaryValue}>
              {completedCount} / {totalTasks} files
            </Text>
          </View>
          
          <ProgressBar
            progress={totalProgress / 100}
            color={colors.primary}
            style={styles.progressBar}
          />
          
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Size:</Text>
            <Text style={styles.summaryValue}>
              {formatFileSize(uploadedSize)} / {formatFileSize(totalSize)}
            </Text>
          </View>
          
          {isUploading && (
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Network:</Text>
              <Chip
                mode="flat"
                compact
                style={[
                  styles.networkChip,
                  {backgroundColor: networkType === 'wifi' ? colors.success : colors.warning}
                ]}>
                {networkType.toUpperCase()}
              </Chip>
            </View>
          )}
        </Card.Content>
      </Card>
    );
  };

  const renderQuickActions = () => (
    <Card style={styles.actionsCard}>
      <Card.Content>
        <Text style={styles.sectionTitle}>Quick Upload</Text>
        
        <View style={styles.actionsGrid}>
          <Button
            mode="outlined"
            icon="camera"
            onPress={handleTakePhoto}
            style={styles.actionButton}
            contentStyle={styles.actionButtonContent}>
            Camera
          </Button>
          
          <Button
            mode="outlined"
            icon="photo-library"
            onPress={handleSelectFromLibrary}
            style={styles.actionButton}
            contentStyle={styles.actionButtonContent}>
            Gallery
          </Button>
          
          <Button
            mode="outlined"
            icon="folder"
            onPress={handleSelectFiles}
            style={styles.actionButton}
            contentStyle={styles.actionButtonContent}>
            Files
          </Button>
          
          <Button
            mode="outlined"
            icon="add-circle"
            onPress={() => navigation.navigate('Upload' as never)}
            style={styles.actionButton}
            contentStyle={styles.actionButtonContent}>
            More
          </Button>
        </View>
      </Card.Content>
    </Card>
  );

  const renderTaskList = (tasks: UploadTask[], title: string) => {
    if (tasks.length === 0) return null;

    return (
      <View style={styles.taskSection}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>{title}</Text>
          <Text style={styles.sectionCount}>({tasks.length})</Text>
        </View>
        
        {tasks.map(task => (
          <UploadTaskCard
            key={task.id}
            task={task}
            onAction={(action) => handleTaskAction(task.id, action)}
          />
        ))}
      </View>
    );
  };

  const renderEmptyState = () => (
    <EmptyState
      icon="cloud-upload"
      title="No uploads"
      message="Start uploading your media files to MAMS"
      actionLabel="Select Files"
      onAction={handleSelectFiles}
      actionIcon="folder"
    />
  );

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.Content title="Uploads" />
        <Appbar.Action
          icon="settings"
          onPress={() => navigation.navigate('UploadSettings' as never)}
        />
      </Appbar.Header>

      {totalTasks === 0 ? (
        renderEmptyState()
      ) : (
        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}>
          
          {renderUploadSummary()}
          {renderQuickActions()}
          
          {/* Active Uploads */}
          {renderTaskList(activeTasks, 'Uploading')}
          
          {/* Queued Uploads */}
          {renderTaskList(queuedTasks, 'Queue')}
          
          {/* Failed Uploads */}
          {renderTaskList(failedTasks, 'Failed')}
          
          {/* Completed Uploads */}
          {showCompleted && renderTaskList(completedTasks, 'Completed')}
          
          {completedTasks.length > 0 && (
            <Button
              mode="text"
              onPress={() => setShowCompleted(!showCompleted)}
              style={styles.toggleButton}>
              {showCompleted ? 'Hide' : 'Show'} Completed ({completedCount})
            </Button>
          )}
        </ScrollView>
      )}

      {/* Floating Action Button */}
      <FAB
        icon="add"
        label="Upload"
        style={styles.fab}
        onPress={() => navigation.navigate('Upload' as never)}
      />
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
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: spacing.md,
  },
  summaryCard: {
    marginBottom: spacing.md,
  },
  summaryTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    marginBottom: spacing.md,
    fontWeight: '600',
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  summaryLabel: {
    ...typography.bodyMedium,
    color: colors.gray600,
  },
  summaryValue: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    fontWeight: '500',
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
    marginVertical: spacing.sm,
  },
  networkChip: {
    height: 24,
  },
  actionsCard: {
    marginBottom: spacing.lg,
  },
  sectionTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    marginBottom: spacing.md,
    fontWeight: '600',
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  actionButton: {
    width: '48%',
    marginBottom: spacing.sm,
  },
  actionButtonContent: {
    paddingVertical: spacing.sm,
  },
  taskSection: {
    marginBottom: spacing.lg,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  sectionCount: {
    ...typography.bodySmall,
    color: colors.gray500,
    marginLeft: spacing.xs,
  },
  toggleButton: {
    alignSelf: 'center',
    marginTop: spacing.md,
  },
  fab: {
    position: 'absolute',
    margin: spacing.md,
    right: 0,
    bottom: 0,
  },
});