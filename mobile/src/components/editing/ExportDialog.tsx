/**
 * Export Dialog Component
 * 
 * Settings and options for exporting edited media
 */

import React, {useState} from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
} from 'react-native';
import {
  Dialog,
  Portal,
  Text,
  RadioButton,
  List,
  Button,
  ProgressBar,
  Divider,
} from 'react-native-paper';

import {EditProject, ExportSettings} from '@/services/editingService';
import {colors, spacing, typography} from '@/constants/theme';

interface ExportDialogProps {
  visible: boolean;
  onDismiss: () => void;
  onExport: (settings: ExportSettings) => void;
  project: EditProject;
  isExporting: boolean;
  progress: number;
}

export const ExportDialog: React.FC<ExportDialogProps> = ({
  visible,
  onDismiss,
  onExport,
  project,
  isExporting,
  progress,
}) => {
  const [format, setFormat] = useState<ExportSettings['format']>(
    project.exportSettings.format
  );
  const [quality, setQuality] = useState<ExportSettings['quality']>(
    project.exportSettings.quality
  );
  const [resolution, setResolution] = useState<string>('original');

  const isVideo = project.originalAsset.metadata?.mime_type?.startsWith('video/');
  const isImage = project.originalAsset.metadata?.mime_type?.startsWith('image/');

  const getFormatOptions = () => {
    if (isVideo) {
      return ['mp4', 'mov', 'gif'];
    } else if (isImage) {
      return ['jpg', 'png'];
    }
    return ['mp4'];
  };

  const getResolutionOptions = () => {
    return [
      {label: 'Original', value: 'original', width: 0, height: 0},
      {label: '4K (3840×2160)', value: '4k', width: 3840, height: 2160},
      {label: '1080p (1920×1080)', value: '1080p', width: 1920, height: 1080},
      {label: '720p (1280×720)', value: '720p', width: 1280, height: 720},
      {label: '480p (854×480)', value: '480p', width: 854, height: 480},
    ];
  };

  const handleExport = () => {
    const selectedResolution = getResolutionOptions().find(r => r.value === resolution);
    
    const settings: ExportSettings = {
      format,
      quality,
      resolution: selectedResolution && selectedResolution.value !== 'original'
        ? {width: selectedResolution.width, height: selectedResolution.height}
        : undefined,
    };

    onExport(settings);
  };

  const getEstimatedSize = () => {
    // Rough estimation based on quality and resolution
    const baseSize = project.originalAsset.file_size || 0;
    let multiplier = 1;

    switch (quality) {
      case 'low': multiplier = 0.3; break;
      case 'medium': multiplier = 0.6; break;
      case 'high': multiplier = 0.9; break;
      case 'original': multiplier = 1.2; break;
    }

    switch (resolution) {
      case '480p': multiplier *= 0.3; break;
      case '720p': multiplier *= 0.5; break;
      case '1080p': multiplier *= 0.7; break;
      case '4k': multiplier *= 1.5; break;
    }

    const estimatedSize = baseSize * multiplier;
    return (estimatedSize / 1024 / 1024).toFixed(1);
  };

  return (
    <Portal>
      <Dialog
        visible={visible}
        onDismiss={onDismiss}
        style={styles.dialog}>
        <Dialog.Title>Export Settings</Dialog.Title>
        
        <Dialog.ScrollArea>
          <ScrollView contentContainerStyle={styles.scrollContent}>
            {!isExporting ? (
              <>
                {/* Format selection */}
                <List.Section>
                  <List.Subheader>Format</List.Subheader>
                  <RadioButton.Group
                    value={format}
                    onValueChange={(value) => setFormat(value as ExportSettings['format'])}>
                    {getFormatOptions().map((fmt) => (
                      <List.Item
                        key={fmt}
                        title={fmt.toUpperCase()}
                        left={() => (
                          <RadioButton value={fmt} />
                        )}
                      />
                    ))}
                  </RadioButton.Group>
                </List.Section>

                <Divider />

                {/* Quality selection */}
                <List.Section>
                  <List.Subheader>Quality</List.Subheader>
                  <RadioButton.Group
                    value={quality}
                    onValueChange={(value) => setQuality(value as ExportSettings['quality'])}>
                    <List.Item
                      title="Low"
                      description="Smaller file size, faster export"
                      left={() => <RadioButton value="low" />}
                    />
                    <List.Item
                      title="Medium"
                      description="Balanced quality and size"
                      left={() => <RadioButton value="medium" />}
                    />
                    <List.Item
                      title="High"
                      description="Better quality, larger file"
                      left={() => <RadioButton value="high" />}
                    />
                    <List.Item
                      title="Original"
                      description="Best quality, largest file"
                      left={() => <RadioButton value="original" />}
                    />
                  </RadioButton.Group>
                </List.Section>

                <Divider />

                {/* Resolution selection (video only) */}
                {isVideo && (
                  <>
                    <List.Section>
                      <List.Subheader>Resolution</List.Subheader>
                      <RadioButton.Group
                        value={resolution}
                        onValueChange={setResolution}>
                        {getResolutionOptions().map((res) => (
                          <List.Item
                            key={res.value}
                            title={res.label}
                            left={() => <RadioButton value={res.value} />}
                          />
                        ))}
                      </RadioButton.Group>
                    </List.Section>

                    <Divider />
                  </>
                )}

                {/* Export info */}
                <View style={styles.exportInfo}>
                  <Text style={styles.infoLabel}>Estimated Size:</Text>
                  <Text style={styles.infoValue}>{getEstimatedSize()} MB</Text>
                </View>

                <View style={styles.exportInfo}>
                  <Text style={styles.infoLabel}>Number of Edits:</Text>
                  <Text style={styles.infoValue}>
                    {project.edits.filter(e => e.enabled).length}
                  </Text>
                </View>
              </>
            ) : (
              <View style={styles.progressContainer}>
                <Text style={styles.progressTitle}>Exporting...</Text>
                <ProgressBar
                  progress={progress / 100}
                  style={styles.progressBar}
                />
                <Text style={styles.progressText}>
                  {Math.round(progress)}%
                </Text>
              </View>
            )}
          </ScrollView>
        </Dialog.ScrollArea>

        <Dialog.Actions>
          <Button onPress={onDismiss} disabled={isExporting}>
            Cancel
          </Button>
          <Button
            onPress={handleExport}
            disabled={isExporting}
            mode="contained">
            Export
          </Button>
        </Dialog.Actions>
      </Dialog>
    </Portal>
  );
};

const styles = StyleSheet.create({
  dialog: {
    maxHeight: '80%',
  },
  scrollContent: {
    paddingBottom: spacing.md,
  },
  exportInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  infoLabel: {
    ...typography.bodyMedium,
    color: colors.gray600,
  },
  infoValue: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    fontWeight: '500',
  },
  progressContainer: {
    padding: spacing.xl,
    alignItems: 'center',
  },
  progressTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    marginBottom: spacing.md,
  },
  progressBar: {
    width: '100%',
    height: 8,
    marginBottom: spacing.sm,
  },
  progressText: {
    ...typography.bodyLarge,
    color: colors.primary,
    fontWeight: '600',
  },
});