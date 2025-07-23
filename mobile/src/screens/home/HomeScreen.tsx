/**
 * Home Screen
 * 
 * Main dashboard showing recent assets, quick actions,
 * and notifications.
 */

import React from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {Appbar, Card, Text} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';

import {colors, spacing, typography} from '@/constants/theme';
import {NotificationBadge} from '@/components/common/NotificationBadge';

export const HomeScreen: React.FC = () => {
  const navigation = useNavigation();

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.Content title="MAMS" />
        <NotificationBadge color={colors.onPrimary} />
      </Appbar.Header>

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.title}>Welcome to MAMS</Text>
            <Text style={styles.subtitle}>Digital Media Asset Management System</Text>
          </Card.Content>
        </Card>
      </ScrollView>
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
  card: {
    marginBottom: spacing.md,
  },
  title: {
    ...typography.headlineMedium,
    color: colors.onSurface,
    fontWeight: '600',
  },
  subtitle: {
    ...typography.bodyLarge,
    color: colors.gray600,
    marginTop: spacing.sm,
  },
});