/**
 * Edit Toolbar Component
 * 
 * Toolbar for selecting editing tools and operations
 */

import React from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import {Text} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {EditType} from '@/services/editingService';
import {colors, spacing, typography} from '@/constants/theme';

interface EditToolbarProps {
  currentTool: EditType | null;
  onToolSelect: (tool: EditType | null) => void;
  assetType: string;
}

interface Tool {
  type: EditType;
  icon: string;
  label: string;
  supportedTypes: string[];
}

const TOOLS: Tool[] = [
  {
    type: 'trim',
    icon: 'content-cut',
    label: 'Trim',
    supportedTypes: ['video/', 'audio/'],
  },
  {
    type: 'crop',
    icon: 'crop',
    label: 'Crop',
    supportedTypes: ['video/', 'image/'],
  },
  {
    type: 'rotate',
    icon: 'rotate-90-degrees-ccw',
    label: 'Rotate',
    supportedTypes: ['video/', 'image/'],
  },
  {
    type: 'filter',
    icon: 'filter',
    label: 'Filter',
    supportedTypes: ['video/', 'image/'],
  },
  {
    type: 'adjustment',
    icon: 'tune',
    label: 'Adjust',
    supportedTypes: ['video/', 'image/'],
  },
  {
    type: 'text',
    icon: 'text-fields',
    label: 'Text',
    supportedTypes: ['video/', 'image/'],
  },
  {
    type: 'audio',
    icon: 'volume-up',
    label: 'Audio',
    supportedTypes: ['video/'],
  },
  {
    type: 'speed',
    icon: 'speed',
    label: 'Speed',
    supportedTypes: ['video/'],
  },
];

export const EditToolbar: React.FC<EditToolbarProps> = ({
  currentTool,
  onToolSelect,
  assetType,
}) => {
  const availableTools = TOOLS.filter(tool =>
    tool.supportedTypes.some(type => assetType.startsWith(type))
  );

  const handleToolPress = (tool: Tool) => {
    if (currentTool === tool.type) {
      onToolSelect(null);
    } else {
      onToolSelect(tool.type);
    }
  };

  return (
    <View style={styles.container}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}>
        
        {availableTools.map((tool) => (
          <TouchableOpacity
            key={tool.type}
            style={[
              styles.tool,
              currentTool === tool.type && styles.toolActive,
            ]}
            onPress={() => handleToolPress(tool)}>
            <Icon
              name={tool.icon}
              size={24}
              color={
                currentTool === tool.type
                  ? colors.primary
                  : colors.onSurface
              }
            />
            <Text
              style={[
                styles.toolLabel,
                currentTool === tool.type && styles.toolLabelActive,
              ]}>
              {tool.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.gray300,
  },
  scrollContent: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.md,
  },
  tool: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    marginHorizontal: spacing.xs,
    borderRadius: 8,
  },
  toolActive: {
    backgroundColor: `${colors.primary}15`,
  },
  toolLabel: {
    ...typography.bodySmall,
    color: colors.onSurface,
    marginTop: spacing.xs,
  },
  toolLabelActive: {
    color: colors.primary,
    fontWeight: '600',
  },
});