/**
 * Timeline Component
 * 
 * Visual timeline showing edits and playback position
 */

import React from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import {Text, IconButton, Chip} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {Edit} from '@/services/editingService';
import {colors, spacing, typography} from '@/constants/theme';

const {width: screenWidth} = Dimensions.get('window');

interface TimelineProps {
  edits: Edit[];
  selectedEditId: string | null;
  duration: number;
  currentTime: number;
  onSelectEdit: (editId: string | null) => void;
  onRemoveEdit: (editId: string) => void;
  onToggleEdit: (editId: string) => void;
}

export const Timeline: React.FC<TimelineProps> = ({
  edits,
  selectedEditId,
  duration,
  currentTime,
  onSelectEdit,
  onRemoveEdit,
  onToggleEdit,
}) => {
  const getEditIcon = (type: Edit['type']): string => {
    switch (type) {
      case 'trim': return 'content-cut';
      case 'crop': return 'crop';
      case 'rotate': return 'rotate-90-degrees-ccw';
      case 'filter': return 'filter';
      case 'adjustment': return 'tune';
      case 'text': return 'text-fields';
      case 'audio': return 'volume-up';
      case 'speed': return 'speed';
      default: return 'edit';
    }
  };

  const getEditLabel = (edit: Edit): string => {
    switch (edit.type) {
      case 'trim':
        return `Trim ${edit.parameters.startTime?.toFixed(1)}s - ${edit.parameters.endTime?.toFixed(1)}s`;
      case 'filter':
        return `Filter: ${edit.parameters.filterName}`;
      case 'adjustment':
        return 'Color adjustment';
      case 'speed':
        return `Speed: ${edit.parameters.speed}x`;
      default:
        return edit.type.charAt(0).toUpperCase() + edit.type.slice(1);
    }
  };

  const playheadPosition = duration > 0 ? (currentTime / duration) * (screenWidth - 40) : 0;

  return (
    <View style={styles.container}>
      {/* Timeline track */}
      <View style={styles.timelineTrack}>
        <View style={styles.trackBackground} />
        
        {/* Playhead */}
        <View
          style={[
            styles.playhead,
            {left: playheadPosition},
          ]}
        />
      </View>

      {/* Edits list */}
      <ScrollView
        style={styles.editsList}
        contentContainerStyle={styles.editsContent}
        showsVerticalScrollIndicator={false}>
        
        {edits.length === 0 ? (
          <View style={styles.emptyState}>
            <Icon name="edit" size={32} color={colors.gray400} />
            <Text style={styles.emptyText}>
              No edits yet. Select a tool to start editing.
            </Text>
          </View>
        ) : (
          edits.map((edit) => (
            <TouchableOpacity
              key={edit.id}
              style={[
                styles.editItem,
                selectedEditId === edit.id && styles.editItemSelected,
                !edit.enabled && styles.editItemDisabled,
              ]}
              onPress={() => onSelectEdit(edit.id)}>
              
              <View style={styles.editContent}>
                <Icon
                  name={getEditIcon(edit.type)}
                  size={20}
                  color={
                    !edit.enabled
                      ? colors.gray400
                      : selectedEditId === edit.id
                      ? colors.primary
                      : colors.onSurface
                  }
                />
                
                <Text
                  style={[
                    styles.editLabel,
                    !edit.enabled && styles.editLabelDisabled,
                  ]}>
                  {getEditLabel(edit)}
                </Text>
              </View>
              
              <View style={styles.editActions}>
                <IconButton
                  icon={edit.enabled ? 'visibility' : 'visibility-off'}
                  size={20}
                  onPress={() => onToggleEdit(edit.id)}
                />
                <IconButton
                  icon="close"
                  size={20}
                  onPress={() => onRemoveEdit(edit.id)}
                />
              </View>
            </TouchableOpacity>
          ))
        )}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.gray300,
    height: 180,
  },
  timelineTrack: {
    height: 40,
    paddingHorizontal: spacing.lg,
    justifyContent: 'center',
  },
  trackBackground: {
    height: 4,
    backgroundColor: colors.gray300,
    borderRadius: 2,
  },
  playhead: {
    position: 'absolute',
    width: 2,
    height: 20,
    backgroundColor: colors.primary,
    borderRadius: 1,
    top: 10,
  },
  editsList: {
    flex: 1,
  },
  editsContent: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
  },
  emptyText: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  editItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.xs,
    backgroundColor: colors.gray100,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.gray300,
  },
  editItemSelected: {
    borderColor: colors.primary,
    backgroundColor: `${colors.primary}10`,
  },
  editItemDisabled: {
    opacity: 0.5,
  },
  editContent: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  editLabel: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    marginLeft: spacing.sm,
    flex: 1,
  },
  editLabelDisabled: {
    color: colors.gray600,
  },
  editActions: {
    flexDirection: 'row',
  },
});