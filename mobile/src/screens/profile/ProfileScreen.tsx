/**
 * Profile Screen
 * 
 * Displays user profile information and account settings.
 */

import React from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {Appbar, Card, Text, List} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';

import {colors, spacing, typography} from '@/constants/theme';
import {NotificationBadge} from '@/components/common/NotificationBadge';

export const ProfileScreen: React.FC = () => {
  const navigation = useNavigation();

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.Content title="Profile" />
        <NotificationBadge color={colors.onPrimary} />
      </Appbar.Header>

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.title}>Profile Settings</Text>
            
            <List.Item
              title="Notifications"
              description="Manage notification preferences"
              left={(props) => <List.Icon {...props} icon="notifications" />}
              right={(props) => <List.Icon {...props} icon="chevron-right" />}
              onPress={() => navigation.navigate('Notifications' as never)}
            />
            
            <List.Item
              title="Notification Settings"
              description="Configure notification types and quiet hours"
              left={(props) => <List.Icon {...props} icon="tune" />}
              right={(props) => <List.Icon {...props} icon="chevron-right" />}
              onPress={() => navigation.navigate('NotificationSettings' as never)}
            />
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
    marginBottom: spacing.md,
  },
});