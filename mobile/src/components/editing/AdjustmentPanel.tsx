/**
 * Adjustment Panel Component
 * 
 * Controls for color and image adjustments
 */

import React, {useState} from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
} from 'react-native';
import {Text, Slider} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {colors, spacing, typography} from '@/constants/theme';

interface AdjustmentPanelProps {
  onAdjustmentChange: (adjustments: {
    brightness?: number;
    contrast?: number;
    saturation?: number;
    hue?: number;
  }) => void;
}

interface Adjustment {
  key: 'brightness' | 'contrast' | 'saturation' | 'hue';
  label: string;
  icon: string;
  min: number;
  max: number;
  default: number;
  step: number;
}

const ADJUSTMENTS: Adjustment[] = [
  {
    key: 'brightness',
    label: 'Brightness',
    icon: 'brightness-6',
    min: -1,
    max: 1,
    default: 0,
    step: 0.01,
  },
  {
    key: 'contrast',
    label: 'Contrast',
    icon: 'contrast',
    min: 0,
    max: 2,
    default: 1,
    step: 0.01,
  },
  {
    key: 'saturation',
    label: 'Saturation',
    icon: 'palette',
    min: 0,
    max: 2,
    default: 1,
    step: 0.01,
  },
  {
    key: 'hue',
    label: 'Hue',
    icon: 'lens',
    min: -180,
    max: 180,
    default: 0,
    step: 1,
  },
];

export const AdjustmentPanel: React.FC<AdjustmentPanelProps> = ({
  onAdjustmentChange,
}) => {
  const [values, setValues] = useState<Record<string, number>>({
    brightness: 0,
    contrast: 1,
    saturation: 1,
    hue: 0,
  });

  const handleValueChange = (key: string, value: number) => {
    const newValues = {...values, [key]: value};
    setValues(newValues);
    onAdjustmentChange(newValues);
  };

  const handleReset = (key: string, defaultValue: number) => {
    handleValueChange(key, defaultValue);
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}>
      
      {ADJUSTMENTS.map((adjustment) => (
        <View key={adjustment.key} style={styles.adjustmentItem}>
          <View style={styles.adjustmentHeader}>
            <View style={styles.adjustmentTitle}>
              <Icon
                name={adjustment.icon}
                size={20}
                color={colors.onSurface}
              />
              <Text style={styles.adjustmentLabel}>
                {adjustment.label}
              </Text>
            </View>
            
            <View style={styles.adjustmentValue}>
              <Text style={styles.valueText}>
                {values[adjustment.key].toFixed(
                  adjustment.step < 1 ? 2 : 0
                )}
              </Text>
              <Icon
                name="refresh"
                size={16}
                color={colors.gray600}
                onPress={() => handleReset(adjustment.key, adjustment.default)}
              />
            </View>
          </View>
          
          <Slider
            value={values[adjustment.key]}
            onValueChange={(value) => handleValueChange(adjustment.key, value)}
            minimumValue={adjustment.min}
            maximumValue={adjustment.max}
            step={adjustment.step}
            style={styles.slider}
          />
        </View>
      ))}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.surface,
  },
  content: {
    padding: spacing.md,
  },
  adjustmentItem: {
    marginBottom: spacing.lg,
  },
  adjustmentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  adjustmentTitle: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  adjustmentLabel: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    marginLeft: spacing.sm,
    fontWeight: '500',
  },
  adjustmentValue: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  valueText: {
    ...typography.bodySmall,
    color: colors.gray600,
    marginRight: spacing.sm,
    minWidth: 40,
    textAlign: 'right',
  },
  slider: {
    marginHorizontal: -spacing.sm,
  },
});