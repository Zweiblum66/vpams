/**
 * Notification Badge Component
 * 
 * Displays a notification bell icon with unread count badge
 * that can be used in headers or navigation.
 */

import React from 'react';
import {View, StyleSheet, TouchableOpacity} from 'react-native';
import {Text, Badge} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import {useSelector} from 'react-redux';
import {useNavigation} from '@react-navigation/native';

import {AppState} from '@/types';
import {colors, spacing} from '@/constants/theme';

interface NotificationBadgeProps {
  color?: string;
  size?: number;
}

export const NotificationBadge: React.FC<NotificationBadgeProps> = ({
  color = colors.onSurface,
  size = 24,
}) => {
  const navigation = useNavigation();
  const unreadCount = useSelector((state: AppState) => state.notifications.unreadCount);
  const hasUnread = unreadCount > 0;

  const handlePress = () => {
    navigation.navigate('Notifications' as never);
  };

  return (
    <TouchableOpacity onPress={handlePress} style={styles.container}>
      <Icon
        name={hasUnread ? 'notifications' : 'notifications-none'}
        size={size}
        color={color}
      />
      
      {hasUnread && (
        <View style={styles.badgeContainer}>
          <Badge
            size={16}
            style={[styles.badge, {backgroundColor: colors.error}]}>
            {unreadCount > 99 ? '99+' : unreadCount.toString()}
          </Badge>
        </View>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'relative',
    padding: spacing.xs,
  },
  badgeContainer: {
    position: 'absolute',
    top: 0,
    right: 0,
  },
  badge: {
    fontSize: 10,
    fontWeight: '600',
    color: colors.onError,
  },
});