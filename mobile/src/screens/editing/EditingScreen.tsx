/**
 * Editing Screen
 * 
 * Main media editing interface with timeline, preview,
 * and editing controls.
 */

import React, {useState, useEffect, useRef} from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Dimensions,
  TouchableOpacity,
  Alert,
} from 'react-native';
import {
  Appbar,
  FAB,
  Text,
  IconButton,
  Chip,
  Dialog,
  Portal,
  List,
  Button,
  ProgressBar,
} from 'react-native-paper';
import {useNavigation, useRoute, RouteProp} from '@react-navigation/native';
import {useDispatch, useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import Video from 'react-native-video';
import FastImage from 'react-native-fast-image';

import {AppState, Asset} from '@/types';
import {editingService, EditType, Filter} from '@/services/editingService';
import {
  createProject,
  addEdit,
  removeEdit,
  toggleEdit,
  selectEdit,
  undo,
  redo,
  setPreviewUrl,
  setExporting,
  setExportProgress,
  clearEditing,
} from '@/store/slices/editingSlice';
import {EditToolbar} from '@/components/editing/EditToolbar';
import {Timeline} from '@/components/editing/Timeline';
import {FilterSelector} from '@/components/editing/FilterSelector';
import {AdjustmentPanel} from '@/components/editing/AdjustmentPanel';
import {TrimControls} from '@/components/editing/TrimControls';
import {ExportDialog} from '@/components/editing/ExportDialog';
import {colors, spacing, typography} from '@/constants/theme';

const {width: screenWidth, height: screenHeight} = Dimensions.get('window');

type EditingScreenRouteProp = RouteProp<{
  Editing: {assetId: string};
}, 'Editing'>;

export const EditingScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute<EditingScreenRouteProp>();
  const dispatch = useDispatch();
  const {assetId} = route.params;

  const asset = useSelector((state: AppState) => 
    state.assets.assets.find(a => a.id === assetId)
  );
  const {
    activeProject,
    selectedEditId,
    previewUrl,
    isExporting,
    exportProgress,
    undoStack,
    redoStack,
  } = useSelector((state: AppState) => state.editing);

  const [currentTool, setCurrentTool] = useState<EditType | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const videoRef = useRef<Video>(null);

  useEffect(() => {
    if (asset) {
      initializeProject();
    }

    return () => {
      dispatch(clearEditing());
    };
  }, [asset]);

  const initializeProject = async () => {
    if (!asset) return;

    try {
      const project = await editingService.createProject(asset);
      dispatch(createProject(project));
    } catch (error) {
      console.error('Failed to create project:', error);
      Alert.alert('Error', 'Failed to initialize editing project');
    }
  };

  const handleToolSelect = (tool: EditType | null) => {
    setCurrentTool(tool);
    dispatch(selectEdit(null));
  };

  const handleAddEdit = (type: EditType, parameters: any) => {
    if (!activeProject) return;

    const edit = editingService.addEdit(activeProject.id, {
      type,
      parameters,
      enabled: true,
    });

    dispatch(addEdit(edit));
    generatePreview();
  };

  const handleRemoveEdit = (editId: string) => {
    if (!activeProject) return;

    editingService.removeEdit(activeProject.id, editId);
    dispatch(removeEdit(editId));
    generatePreview();
  };

  const handleToggleEdit = (editId: string) => {
    if (!activeProject) return;

    editingService.toggleEdit(activeProject.id, editId);
    dispatch(toggleEdit(editId));
    generatePreview();
  };

  const generatePreview = async () => {
    if (!activeProject) return;

    try {
      const preview = await editingService.generatePreview(activeProject.id);
      dispatch(setPreviewUrl(preview));
    } catch (error) {
      console.error('Failed to generate preview:', error);
    }
  };

  const handleUndo = () => {
    dispatch(undo());
    generatePreview();
  };

  const handleRedo = () => {
    dispatch(redo());
    generatePreview();
  };

  const handleSave = async () => {
    if (!activeProject || !asset) return;

    setIsSaving(true);
    try {
      // Save edits to backend
      // This would typically involve an API call
      console.log('Saving project:', activeProject);
      
      Alert.alert(
        'Project Saved',
        'Your edits have been saved successfully.',
        [{text: 'OK'}]
      );
    } catch (error) {
      Alert.alert('Error', 'Failed to save project');
    } finally {
      setIsSaving(false);
    }
  };

  const handleExport = async (settings: any) => {
    if (!activeProject) return;

    dispatch(setExporting(true));
    dispatch(setExportProgress(0));

    try {
      const result = await editingService.exportProject(activeProject.id);
      
      dispatch(setExporting(false));
      dispatch(setExportProgress(100));
      
      Alert.alert(
        'Export Complete',
        `File saved to: ${result.path}\nSize: ${(result.size / 1024 / 1024).toFixed(2)} MB`,
        [
          {text: 'Share', onPress: () => shareExport(result.path)},
          {text: 'OK'},
        ]
      );
    } catch (error) {
      dispatch(setExporting(false));
      Alert.alert('Export Failed', 'Failed to export edited media');
    }
  };

  const shareExport = async (filePath: string) => {
    // Implement sharing functionality
    console.log('Share export:', filePath);
  };

  const renderPreview = () => {
    if (!asset) return null;

    const isVideo = asset.metadata?.mime_type?.startsWith('video/');
    const isImage = asset.metadata?.mime_type?.startsWith('image/');

    if (isVideo) {
      return (
        <Video
          ref={videoRef}
          source={{uri: previewUrl || asset.proxy_url || asset.file_path}}
          style={styles.preview}
          paused={!isPlaying}
          onLoad={(data) => setDuration(data.duration)}
          onProgress={(data) => setCurrentTime(data.currentTime)}
          onEnd={() => setIsPlaying(false)}
          resizeMode="contain"
          controls={false}
        />
      );
    }

    if (isImage) {
      return (
        <FastImage
          source={{uri: previewUrl || asset.proxy_url || asset.thumbnail_url}}
          style={styles.preview}
          resizeMode={FastImage.resizeMode.contain}
        />
      );
    }

    return null;
  };

  const renderEditPanel = () => {
    switch (currentTool) {
      case 'filter':
        return (
          <FilterSelector
            onSelectFilter={(filter) => {
              handleAddEdit('filter', {
                filterName: filter.id,
                intensity: 1.0,
              });
            }}
          />
        );

      case 'adjustment':
        return (
          <AdjustmentPanel
            onAdjustmentChange={(adjustments) => {
              handleAddEdit('adjustment', adjustments);
            }}
          />
        );

      case 'trim':
        return (
          <TrimControls
            duration={duration}
            onTrimChange={(startTime, endTime) => {
              handleAddEdit('trim', {startTime, endTime});
            }}
          />
        );

      default:
        return null;
    }
  };

  if (!asset || !activeProject) {
    return null;
  }

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title="Edit" subtitle={asset.name} />
        <Appbar.Action
          icon="undo"
          onPress={handleUndo}
          disabled={undoStack.length === 0}
        />
        <Appbar.Action
          icon="redo"
          onPress={handleRedo}
          disabled={redoStack.length === 0}
        />
        <Appbar.Action
          icon="save"
          onPress={handleSave}
          disabled={isSaving}
        />
      </Appbar.Header>

      <View style={styles.content}>
        {/* Preview */}
        <View style={styles.previewContainer}>
          {renderPreview()}
          
          {/* Playback controls for video */}
          {asset.metadata?.mime_type?.startsWith('video/') && (
            <View style={styles.playbackControls}>
              <IconButton
                icon={isPlaying ? 'pause' : 'play-arrow'}
                size={32}
                iconColor={colors.white}
                onPress={() => setIsPlaying(!isPlaying)}
              />
              <Text style={styles.timeText}>
                {formatTime(currentTime)} / {formatTime(duration)}
              </Text>
            </View>
          )}
        </View>

        {/* Timeline */}
        <Timeline
          edits={activeProject.edits}
          selectedEditId={selectedEditId}
          duration={duration}
          currentTime={currentTime}
          onSelectEdit={(editId) => dispatch(selectEdit(editId))}
          onRemoveEdit={handleRemoveEdit}
          onToggleEdit={handleToggleEdit}
        />

        {/* Edit toolbar */}
        <EditToolbar
          currentTool={currentTool}
          onToolSelect={handleToolSelect}
          assetType={asset.metadata?.mime_type || ''}
        />

        {/* Edit panel */}
        {currentTool && (
          <View style={styles.editPanel}>
            {renderEditPanel()}
          </View>
        )}
      </View>

      {/* Export FAB */}
      <FAB
        icon="export"
        label="Export"
        onPress={() => setShowExportDialog(true)}
        style={styles.exportFab}
        disabled={activeProject.edits.length === 0 || isExporting}
      />

      {/* Export dialog */}
      <Portal>
        <ExportDialog
          visible={showExportDialog}
          onDismiss={() => setShowExportDialog(false)}
          onExport={handleExport}
          project={activeProject}
          isExporting={isExporting}
          progress={exportProgress}
        />
      </Portal>

      {/* Export progress */}
      {isExporting && (
        <View style={styles.exportProgress}>
          <Text style={styles.exportProgressText}>
            Exporting... {Math.round(exportProgress)}%
          </Text>
          <ProgressBar progress={exportProgress / 100} />
        </View>
      )}
    </View>
  );
};

const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.black,
  },
  appBar: {
    backgroundColor: colors.surface,
    elevation: 4,
  },
  content: {
    flex: 1,
  },
  previewContainer: {
    height: screenHeight * 0.4,
    backgroundColor: colors.black,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  preview: {
    width: '100%',
    height: '100%',
  },
  playbackControls: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    paddingVertical: spacing.sm,
  },
  timeText: {
    ...typography.bodyMedium,
    color: colors.white,
    marginLeft: spacing.md,
  },
  editPanel: {
    position: 'absolute',
    bottom: 80,
    left: 0,
    right: 0,
    backgroundColor: colors.surface,
    maxHeight: screenHeight * 0.3,
  },
  exportFab: {
    position: 'absolute',
    margin: spacing.md,
    right: 0,
    bottom: 0,
    backgroundColor: colors.primary,
  },
  exportProgress: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: colors.surface,
    padding: spacing.md,
  },
  exportProgressText: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    marginBottom: spacing.sm,
  },
});