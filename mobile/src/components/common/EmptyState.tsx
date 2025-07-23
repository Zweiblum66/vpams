/**
 * Empty State Component
 * 
 * Displays a centered empty state with icon, title,
 * message, and optional action button.
 */

import React from 'react';
import {View, StyleSheet} from 'react-native';
import {Text, Button} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {colors, spacing, typography} from '@/constants/theme';

interface EmptyStateProps {
  icon: string;
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  actionIcon?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  message,
  actionLabel,
  onAction,
  actionIcon,
}) => {
  return (
    <View style={styles.container}>
      <Icon name={icon} size={64} color={colors.gray400} />
      
      <Text style={styles.title}>{title}</Text>
      
      <Text style={styles.message}>{message}</Text>
      
      {actionLabel && onAction && (
        <Button
          mode="contained"
          onPress={onAction}
          icon={actionIcon}
          style={styles.actionButton}
          contentStyle={styles.actionButtonContent}>
          {actionLabel}
        </Button>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.xxxl,
  },
  title: {
    ...typography.headlineSmall,
    color: colors.onSurface,
    textAlign: 'center',
    marginTop: spacing.lg,
    marginBottom: spacing.md,
    fontWeight: '600',
  },
  message: {
    ...typography.bodyLarge,
    color: colors.gray600,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: spacing.xl,
  },
  actionButton: {
    marginTop: spacing.md,
  },
  actionButtonContent: {
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
  },
});