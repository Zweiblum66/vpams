/**
 * Loading Overlay Component
 * 
 * Semi-transparent overlay with loading indicator
 * that appears on top of other content.
 */

import React from 'react';
import {View, StyleSheet} from 'react-native';
import {ActivityIndicator, Text} from 'react-native-paper';

import {colors, spacing, typography} from '@/constants/theme';

interface LoadingOverlayProps {
  message?: string;
  visible?: boolean;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  message = 'Loading...',
  visible = true,
}) => {
  if (!visible) {
    return null;
  }

  return (
    <View style={styles.overlay}>
      <View style={styles.container}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.message}>{message}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  container: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.xl,
    alignItems: 'center',
    minWidth: 120,
  },
  message: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    marginTop: spacing.md,
    textAlign: 'center',
  },
});