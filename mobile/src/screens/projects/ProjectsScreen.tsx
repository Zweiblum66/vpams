/**
 * Projects Screen
 * 
 * Displays user projects and allows project management.
 */

import React from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {Appbar, Card, Text} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';

import {colors, spacing, typography} from '@/constants/theme';
import {NotificationBadge} from '@/components/common/NotificationBadge';

export const ProjectsScreen: React.FC = () => {
  const navigation = useNavigation();

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.Content title="Projects" />
        <NotificationBadge color={colors.onPrimary} />
      </Appbar.Header>

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.title}>Projects</Text>
            <Text style={styles.subtitle}>Manage your media projects</Text>
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