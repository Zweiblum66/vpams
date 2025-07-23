/**
 * Upload Screen
 * 
 * Full-featured upload screen with advanced options,
 * project selection, metadata editing, and batch upload.
 */

import React, {useState, useCallback} from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import {
  Appbar,
  Card,
  Text,
  TextInput,
  Button,
  Chip,
  Switch,
  SegmentedButtons,
  Divider,
  List,
  FAB,
} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import {useDispatch, useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import DocumentPicker from 'react-native-document-picker';
import {launchImageLibrary, launchCamera, MediaType} from 'react-native-image-picker';
import {cameraService} from '@/services/cameraService';

import {AppState, UploadTask, Project, LocationTag, VoiceNote} from '@/types';
import {addUploadTask, updateUploadSettings} from '@/store/slices/uploadsSlice';
import {colors, spacing, typography} from '@/constants/theme';
import {uploadService} from '@/services/uploadService';
import {formatFileSize} from '@/utils/formatters';
import {LocationPicker} from '@/components/common/LocationPicker';
import {VoiceNoteRecorder} from '@/components/common/VoiceNoteRecorder';

interface SelectedFile {
  uri: string;
  name: string;
  type: string;
  size: number;
}

export const UploadScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  
  const {settings} = useSelector((state: AppState) => state.uploads);
  const {projects} = useSelector((state: AppState) => state.projects);
  const {user} = useSelector((state: AppState) => state.auth);

  const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadDescription, setUploadDescription] = useState('');
  const [uploadTags, setUploadTags] = useState<string[]>([]);
  const [currentTag, setCurrentTag] = useState('');
  const [qualityPreference, setQualityPreference] = useState(settings.quality_preference);
  const [isPrivate, setIsPrivate] = useState(false);
  const [autoGenerateMetadata, setAutoGenerateMetadata] = useState(true);
  const [sourceType, setSourceType] = useState('files');
  const [selectedLocation, setSelectedLocation] = useState<LocationTag | null>(null);
  const [attachedVoiceNotes, setAttachedVoiceNotes] = useState<VoiceNote[]>([]);

  const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);
  const canUpload = selectedFiles.length > 0;

  const handleSelectFiles = useCallback(async () => {
    try {
      const results = await DocumentPicker.pick({
        type: [DocumentPicker.types.allFiles],
        allowMultiSelection: true,
        copyTo: 'cachesDirectory',
      });

      const newFiles = results.map(file => ({
        uri: file.fileCopyUri || file.uri,
        name: file.name || 'Unknown',
        type: file.type || 'application/octet-stream',
        size: file.size || 0,
      }));

      setSelectedFiles(prev => [...prev, ...newFiles]);
    } catch (error: any) {
      if (!DocumentPicker.isCancel(error)) {
        Alert.alert('Error', 'Failed to select files');
      }
    }
  }, []);

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
          const newFile: SelectedFile = {
            uri: asset.uri!,
            name: asset.fileName || `photo_${Date.now()}.jpg`,
            type: asset.type || 'image/jpeg',
            size: asset.fileSize || 0,
          };
          setSelectedFiles(prev => [...prev, newFile]);
        }
      }
    );
  }, []);

  const handleSelectFromLibrary = useCallback(() => {
    launchImageLibrary(
      {
        mediaType: 'mixed' as MediaType,
        quality: 0.8,
        selectionLimit: 0, // No limit
        includeBase64: false,
      },
      (response) => {
        if (response.assets) {
          const newFiles = response.assets.map(asset => ({
            uri: asset.uri!,
            name: asset.fileName || `media_${Date.now()}`,
            type: asset.type || 'application/octet-stream',
            size: asset.fileSize || 0,
          }));
          setSelectedFiles(prev => [...prev, ...newFiles]);
        }
      }
    );
  }, []);

  const handleRemoveFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const handleAddTag = useCallback(() => {
    if (currentTag.trim() && !uploadTags.includes(currentTag.trim())) {
      setUploadTags(prev => [...prev, currentTag.trim()]);
      setCurrentTag('');
    }
  }, [currentTag, uploadTags]);

  const handleRemoveTag = useCallback((tag: string) => {
    setUploadTags(prev => prev.filter(t => t !== tag));
  }, []);

  const handleVoiceNoteComplete = useCallback((voiceNote: VoiceNote) => {
    setAttachedVoiceNotes(prev => [...prev, voiceNote]);
  }, []);

  const handleRemoveVoiceNote = useCallback((voiceNoteId: string) => {
    setAttachedVoiceNotes(prev => prev.filter(note => note.id !== voiceNoteId));
  }, []);

  const handleStartUpload = useCallback(async () => {
    if (!canUpload) return;

    try {
      // Update upload settings
      dispatch(updateUploadSettings({
        quality_preference: qualityPreference,
      }));

      // Create upload tasks for each file
      for (const file of selectedFiles) {
        const uploadTask = await uploadService.createUploadTask(
          file,
          selectedProject?.id
        );

        // Add metadata
        uploadTask.metadata = {
          title: uploadTitle || file.name,
          description: uploadDescription,
          tags: uploadTags,
          is_private: isPrivate,
          auto_generate_metadata: autoGenerateMetadata,
          uploaded_by: user?.id,
          source_type: sourceType,
          location_tag: selectedLocation,
          voice_notes: attachedVoiceNotes.map(note => ({
            id: note.id,
            fileName: note.fileName,
            duration: note.duration,
            transcription: note.transcription,
          })),
        };

        dispatch(addUploadTask(uploadTask));
      }

      // Navigate back to upload tab
      navigation.goBack();
      
      Alert.alert(
        'Upload Started',
        `${selectedFiles.length} file(s) added to upload queue.`,
        [{text: 'OK'}]
      );
    } catch (error) {
      Alert.alert('Error', 'Failed to start upload. Please try again.');
    }
  }, [
    canUpload,
    selectedFiles,
    selectedProject,
    uploadTitle,
    uploadDescription,
    uploadTags,
    isPrivate,
    autoGenerateMetadata,
    qualityPreference,
    sourceType,
    user,
    dispatch,
    navigation,
  ]);

  const renderSourceSelection = () => (
    <Card style={styles.card}>
      <Card.Content>
        <Text style={styles.sectionTitle}>Source</Text>
        
        <SegmentedButtons
          value={sourceType}
          onValueChange={setSourceType}
          buttons={[
            {
              value: 'files',
              label: 'Files',
              icon: 'folder',
            },
            {
              value: 'camera',
              label: 'Camera',
              icon: 'camera',
            },
            {
              value: 'gallery',
              label: 'Gallery',
              icon: 'photo-library',
            },
          ]}
          style={styles.segmentedButtons}
        />
        
        <View style={styles.sourceActions}>
          {sourceType === 'files' && (
            <Button
              mode="outlined"
              icon="folder"
              onPress={handleSelectFiles}
              style={styles.sourceButton}>
              Select Files
            </Button>
          )}
          
          {sourceType === 'camera' && (
            <View style={styles.cameraActions}>
              <Button
                mode="outlined"
                icon="camera"
                onPress={handleTakePhoto}
                style={styles.sourceButton}>
                Quick Photo
              </Button>
              
              <Button
                mode="contained"
                icon="camera-enhance"
                onPress={() => navigation.navigate('CameraScreen' as never)}
                style={[styles.sourceButton, {marginTop: spacing.sm}]}>
                Pro Camera
              </Button>
            </View>
          )}
          
          {sourceType === 'gallery' && (
            <Button
              mode="outlined"
              icon="photo-library"
              onPress={handleSelectFromLibrary}
              style={styles.sourceButton}>
              Select from Gallery
            </Button>
          )}
        </View>
      </Card.Content>
    </Card>
  );

  const renderSelectedFiles = () => {
    if (selectedFiles.length === 0) return null;

    return (
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>
              Selected Files ({selectedFiles.length})
            </Text>
            <Text style={styles.totalSize}>
              {formatFileSize(totalSize)}
            </Text>
          </View>
          
          {selectedFiles.map((file, index) => (
            <List.Item
              key={index}
              title={file.name}
              description={`${file.type} • ${formatFileSize(file.size)}`}
              left={(props) => (
                <Icon
                  {...props}
                  name={file.type.startsWith('image/') ? 'image' : 
                        file.type.startsWith('video/') ? 'videocam' : 
                        file.type.startsWith('audio/') ? 'audiotrack' : 'insert-drive-file'}
                  size={24}
                  color={colors.primary}
                />
              )}
              right={(props) => (
                <Button
                  {...props}
                  mode="text"
                  icon="close"
                  onPress={() => handleRemoveFile(index)}
                  compact
                />
              )}
              style={styles.fileItem}
            />
          ))}
        </Card.Content>
      </Card>
    );
  };

  const renderProjectSelection = () => (
    <Card style={styles.card}>
      <Card.Content>
        <Text style={styles.sectionTitle}>Project (Optional)</Text>
        
        <Button
          mode="outlined"
          icon="folder"
          onPress={() => {
            // Navigate to project selection screen
            navigation.navigate('ProjectSelect' as never);
          }}
          style={styles.projectButton}>
          {selectedProject ? selectedProject.name : 'Select Project'}
        </Button>
        
        {selectedProject && (
          <Chip
            mode="flat"
            icon="folder"
            onClose={() => setSelectedProject(null)}
            style={styles.projectChip}>
            {selectedProject.name}
          </Chip>
        )}
      </Card.Content>
    </Card>
  );

  const renderMetadata = () => (
    <Card style={styles.card}>
      <Card.Content>
        <Text style={styles.sectionTitle}>Metadata</Text>
        
        <TextInput
          label="Title (Optional)"
          value={uploadTitle}
          onChangeText={setUploadTitle}
          style={styles.input}
          placeholder="Upload title"
        />
        
        <TextInput
          label="Description (Optional)"
          value={uploadDescription}
          onChangeText={setUploadDescription}
          multiline
          numberOfLines={3}
          style={styles.input}
          placeholder="Describe your upload"
        />
        
        <View style={styles.tagsContainer}>
          <TextInput
            label="Add Tags"
            value={currentTag}
            onChangeText={setCurrentTag}
            style={styles.tagInput}
            placeholder="Enter tag name"
            onSubmitEditing={handleAddTag}
            returnKeyType="done"
          />
          <Button
            mode="outlined"
            onPress={handleAddTag}
            disabled={!currentTag.trim()}
            style={styles.addTagButton}>
            Add
          </Button>
        </View>
        
        {uploadTags.length > 0 && (
          <View style={styles.tagsDisplay}>
            {uploadTags.map((tag, index) => (
              <Chip
                key={index}
                mode="flat"
                onClose={() => handleRemoveTag(tag)}
                style={styles.tag}>
                {tag}
              </Chip>
            ))}
          </View>
        )}
      </Card.Content>
    </Card>
  );

  const renderSettings = () => (
    <Card style={styles.card}>
      <Card.Content>
        <Text style={styles.sectionTitle}>Upload Settings</Text>
        
        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Quality Preference</Text>
            <Text style={styles.settingDescription}>
              Higher quality takes longer to upload
            </Text>
          </View>
          <SegmentedButtons
            value={qualityPreference}
            onValueChange={setQualityPreference}
            buttons={[
              {value: 'low', label: 'Low'},
              {value: 'medium', label: 'Medium'},
              {value: 'high', label: 'High'},
              {value: 'original', label: 'Original'},
            ]}
            style={styles.qualityButtons}
          />
        </View>
        
        <Divider style={styles.divider} />
        
        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Private Upload</Text>
            <Text style={styles.settingDescription}>
              Only you can see this content
            </Text>
          </View>
          <Switch
            value={isPrivate}
            onValueChange={setIsPrivate}
          />
        </View>
        
        <Divider style={styles.divider} />
        
        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Auto-generate Metadata</Text>
            <Text style={styles.settingDescription}>
              Automatically extract metadata from files
            </Text>
          </View>
          <Switch
            value={autoGenerateMetadata}
            onValueChange={setAutoGenerateMetadata}
          />
        </View>
      </Card.Content>
    </Card>
  );

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      
      <Appbar.Header style={styles.appBar}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title="Upload Files" />
        <Appbar.Action
          icon="settings"
          onPress={() => navigation.navigate('UploadSettings' as never)}
        />
      </Appbar.Header>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled">
        
        {renderSourceSelection()}
        {renderSelectedFiles()}
        {renderProjectSelection()}
        {renderMetadata()}
        
        {/* Location Picker */}
        <LocationPicker
          selectedLocation={selectedLocation}
          onLocationChange={setSelectedLocation}
          showNearby={true}
          allowCreate={true}
        />
        
        {/* Voice Notes */}
        <Card style={styles.card}>
          <Card.Content>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Voice Notes</Text>
              <Text style={styles.totalCount}>
                {attachedVoiceNotes.length} attached
              </Text>
            </View>
            
            <VoiceNoteRecorder
              onRecordingComplete={handleVoiceNoteComplete}
              compact={true}
              showWaveform={false}
              config={{
                maxDuration: 60000, // 1 minute for upload comments
                quality: 'medium',
                format: 'm4a',
              }}
            />
            
            {attachedVoiceNotes.length > 0 && (
              <View style={styles.voiceNotesDisplay}>
                {attachedVoiceNotes.map(note => (
                  <Chip
                    key={note.id}
                    mode="flat"
                    icon="mic"
                    onClose={() => handleRemoveVoiceNote(note.id)}
                    style={styles.voiceNoteChip}>
                    {note.metadata.title || `Voice note (${Math.floor(note.duration / 1000)}s)`}
                  </Chip>
                ))}
              </View>
            )}
          </Card.Content>
        </Card>
        
        {renderSettings()}
        
        <View style={styles.bottomSpace} />
      </ScrollView>

      {/* Upload FAB */}
      <FAB
        icon="cloud-upload"
        label={`Upload ${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''}`}
        disabled={!canUpload}
        onPress={handleStartUpload}
        style={[
          styles.uploadFab,
          !canUpload && styles.uploadFabDisabled,
        ]}
      />
    </KeyboardAvoidingView>
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
  card: {
    marginBottom: spacing.md,
  },
  sectionTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    marginBottom: spacing.md,
    fontWeight: '600',
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  totalSize: {
    ...typography.bodyMedium,
    color: colors.gray600,
    fontWeight: '500',
  },
  totalCount: {
    ...typography.bodyMedium,
    color: colors.gray600,
    fontWeight: '500',
  },
  segmentedButtons: {
    marginBottom: spacing.md,
  },
  sourceActions: {
    alignItems: 'center',
  },
  sourceButton: {
    width: '100%',
  },
  cameraActions: {
    width: '100%',
  },
  fileItem: {
    paddingHorizontal: 0,
    marginBottom: spacing.xs,
  },
  projectButton: {
    marginBottom: spacing.sm,
  },
  projectChip: {
    alignSelf: 'flex-start',
  },
  input: {
    marginBottom: spacing.md,
    backgroundColor: colors.surface,
  },
  tagsContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginBottom: spacing.sm,
  },
  tagInput: {
    flex: 1,
    marginRight: spacing.sm,
    backgroundColor: colors.surface,
  },
  addTagButton: {
    minWidth: 80,
  },
  tagsDisplay: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  tag: {
    marginRight: spacing.sm,
    marginBottom: spacing.xs,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  settingInfo: {
    flex: 1,
    marginRight: spacing.md,
  },
  settingLabel: {
    ...typography.bodyLarge,
    color: colors.onSurface,
    fontWeight: '500',
  },
  settingDescription: {
    ...typography.bodySmall,
    color: colors.gray600,
    marginTop: spacing.xs,
  },
  qualityButtons: {
    flex: 1,
  },
  divider: {
    marginVertical: spacing.sm,
  },
  bottomSpace: {
    height: 100, // Space for FAB
  },
  uploadFab: {
    position: 'absolute',
    margin: spacing.md,
    right: 0,
    bottom: 0,
    backgroundColor: colors.primary,
  },
  uploadFabDisabled: {
    backgroundColor: colors.gray400,
  },
  voiceNotesDisplay: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: spacing.md,
  },
  voiceNoteChip: {
    marginRight: spacing.sm,
    marginBottom: spacing.xs,
  },
});