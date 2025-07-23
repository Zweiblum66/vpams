/**
 * Loading Screen Component
 * 
 * Displays a full-screen loading indicator with MAMS branding.
 */

import React from 'react';
import {View, StyleSheet} from 'react-native';
import {ActivityIndicator, Text} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {colors, spacing, typography} from '@/constants/theme';

export const LoadingScreen: React.FC = () => {
  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Icon name="movie" size={80} color={colors.primary} />
        <Text style={styles.title}>MAMS Mobile</Text>
        <ActivityIndicator
          size="large"
          color={colors.primary}
          style={styles.spinner}
        />
        <Text style={styles.subtitle}>Loading...</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    alignItems: 'center',
  },
  title: {
    ...typography.headlineMedium,
    color: colors.primary,
    marginTop: spacing.md,
    marginBottom: spacing.xl,
    fontWeight: '700',
  },
  spinner: {
    marginBottom: spacing.lg,
  },
  subtitle: {
    ...typography.bodyLarge,
    color: colors.gray600,
  },
});