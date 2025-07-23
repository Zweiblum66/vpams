/**
 * Notifications Screen
 * 
 * Displays user notifications with read/unread status,
 * action handling, and notification management.
 */

import React, {useState, useEffect, useCallback} from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
} from 'react-native';
import {
  Appbar,
  Card,
  Text,
  List,
  IconButton,
  Chip,
  Button,
  Menu,
  Divider,
  Switch,
} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import {useDispatch, useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {AppState, Notification} from '@/types';
import {
  fetchNotifications,
  markAsRead,
  markAllAsRead,
  deleteNotification,
  clearAllNotifications,
  requestNotificationPermissions,
} from '@/store/slices/notificationsSlice';
import {colors, spacing, typography} from '@/constants/theme';
import {formatDate, formatTime} from '@/utils/formatters';
import {EmptyState} from '@/components/common/EmptyState';
import {pushNotificationService} from '@/services/pushNotificationService';

export const NotificationsScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  
  const {
    notifications,
    unreadCount,
    isLoading,
    error,
    permissionsGranted,
  } = useSelector((state: AppState) => state.notifications);

  const [refreshing, setRefreshing] = useState(false);
  const [menuVisible, setMenuVisible] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'unread'>('all');

  const filteredNotifications = notifications.filter(notification => {
    if (selectedFilter === 'unread') {
      return !notification.read_at;
    }
    return true;
  });

  useEffect(() => {
    // Fetch notifications on mount
    dispatch(fetchNotifications());
  }, [dispatch]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await dispatch(fetchNotifications());
    setRefreshing(false);
  }, [dispatch]);

  const handleNotificationPress = useCallback((notification: Notification) => {
    // Mark as read if unread
    if (!notification.read_at) {
      dispatch(markAsRead(notification.id));
    }

    // Navigate based on notification type
    switch (notification.type) {
      case 'asset_upload':
      case 'asset_ready':
        if (notification.data?.assetId) {
          navigation.navigate('AssetDetails', {
            assetId: notification.data.assetId,
          } as never);
        }
        break;
      
      case 'project_update':
        if (notification.data?.projectId) {
          navigation.navigate('ProjectDetails', {
            projectId: notification.data.projectId,
          } as never);
        }
        break;
      
      case 'workflow_complete':
        if (notification.data?.workflowId) {
          navigation.navigate('WorkflowDetails', {
            workflowId: notification.data.workflowId,
          } as never);
        }
        break;
      
      default:
        // Do nothing for system alerts
        break;
    }
  }, [dispatch, navigation]);

  const handleDeleteNotification = useCallback((notificationId: string) => {
    Alert.alert(
      'Delete Notification',
      'Are you sure you want to delete this notification?',
      [
        {text: 'Cancel', style: 'cancel'},
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => dispatch(deleteNotification(notificationId)),
        },
      ]
    );
  }, [dispatch]);

  const handleMarkAllAsRead = useCallback(() => {
    if (unreadCount > 0) {
      dispatch(markAllAsRead());
    }
  }, [dispatch, unreadCount]);

  const handleClearAll = useCallback(() => {
    Alert.alert(
      'Clear All Notifications',
      'This will delete all notifications. This action cannot be undone.',
      [
        {text: 'Cancel', style: 'cancel'},
        {
          text: 'Clear All',
          style: 'destructive',
          onPress: () => dispatch(clearAllNotifications()),
        },
      ]
    );
  }, [dispatch]);

  const handleRequestPermissions = useCallback(async () => {
    const granted = await dispatch(requestNotificationPermissions());
    if (!granted) {
      Alert.alert(
        'Permissions Required',
        'Please enable notifications in your device settings to receive push notifications.',
        [
          {text: 'Cancel'},
          {
            text: 'Open Settings',
            onPress: () => pushNotificationService.openSettings(),
          },
        ]
      );
    }
  }, [dispatch]);

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'asset_upload':
        return 'cloud-upload';
      case 'asset_ready':
        return 'check-circle';
      case 'project_update':
        return 'folder';
      case 'workflow_complete':
        return 'assignment-turned-in';
      case 'system_alert':
        return 'warning';
      default:
        return 'notifications';
    }
  };

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'asset_upload':
        return colors.info;
      case 'asset_ready':
        return colors.success;
      case 'project_update':
        return colors.primary;
      case 'workflow_complete':
        return colors.success;
      case 'system_alert':
        return colors.warning;
      default:
        return colors.gray500;
    }
  };

  const renderNotification = (notification: Notification) => {
    const isUnread = !notification.read_at;
    const iconName = getNotificationIcon(notification.type);
    const iconColor = getNotificationColor(notification.type);

    return (
      <Card
        key={notification.id}
        style={[
          styles.notificationCard,
          isUnread && styles.unreadCard,
        ]}
        onPress={() => handleNotificationPress(notification)}>
        
        <Card.Content style={styles.cardContent}>
          <View style={styles.notificationHeader}>
            <View style={styles.iconContainer}>
              <Icon name={iconName} size={24} color={iconColor} />
              {isUnread && <View style={styles.unreadDot} />}
            </View>
            
            <View style={styles.notificationContent}>
              <Text style={styles.notificationTitle} numberOfLines={1}>
                {notification.title}
              </Text>
              
              <Text style={styles.notificationMessage} numberOfLines={2}>
                {notification.message}
              </Text>
              
              <View style={styles.notificationMeta}>
                <Chip
                  mode="flat"
                  compact
                  style={[styles.typeChip, {backgroundColor: iconColor + '20'}]}>
                  <Text style={[styles.typeText, {color: iconColor}]}>
                    {notification.type.replace('_', ' ').toUpperCase()}
                  </Text>
                </Chip>
                
                <Text style={styles.timestampText}>
                  {formatDate(notification.created_at)} • {formatTime(notification.created_at)}
                </Text>
              </View>
            </View>
            
            <IconButton
              icon="delete"
              size={20}
              onPress={() => handleDeleteNotification(notification.id)}
              style={styles.deleteButton}
            />
          </View>
        </Card.Content>
      </Card>
    );
  };

  const renderPermissionPrompt = () => {
    if (permissionsGranted) return null;

    return (
      <Card style={styles.permissionCard}>
        <Card.Content>
          <View style={styles.permissionContent}>
            <Icon name="notifications-off" size={32} color={colors.warning} />
            
            <View style={styles.permissionText}>
              <Text style={styles.permissionTitle}>
                Enable Notifications
              </Text>
              <Text style={styles.permissionMessage}>
                Get notified about uploads, project updates, and important alerts.
              </Text>
            </View>
            
            <Button
              mode="contained"
              onPress={handleRequestPermissions}
              style={styles.permissionButton}>
              Enable
            </Button>
          </View>
        </Card.Content>
      </Card>
    );
  };

  const renderFilterBar = () => (
    <View style={styles.filterBar}>
      <View style={styles.filterButtons}>
        <Button
          mode={selectedFilter === 'all' ? 'contained' : 'outlined'}
          onPress={() => setSelectedFilter('all')}
          compact
          style={styles.filterButton}>
          All ({notifications.length})
        </Button>
        
        <Button
          mode={selectedFilter === 'unread' ? 'contained' : 'outlined'}
          onPress={() => setSelectedFilter('unread')}
          compact
          style={styles.filterButton}>
          Unread ({unreadCount})
        </Button>
      </View>
      
      {unreadCount > 0 && (
        <Button
          mode="text"
          onPress={handleMarkAllAsRead}
          compact>
          Mark All Read
        </Button>
      )}
    </View>
  );

  const renderEmptyState = () => {
    if (selectedFilter === 'unread') {
      return (
        <EmptyState
          icon="mark-email-read"
          title="All Caught Up!"
          message="You have no unread notifications"
          actionLabel="View All"
          onAction={() => setSelectedFilter('all')}
        />
      );
    }

    return (
      <EmptyState
        icon="notifications-none"
        title="No Notifications"
        message="You'll see notifications about your uploads, projects, and system updates here"
        actionLabel="Refresh"
        onAction={handleRefresh}
        actionIcon="refresh"
      />
    );
  };

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title="Notifications" />
        
        <Menu
          visible={menuVisible}
          onDismiss={() => setMenuVisible(false)}
          anchor={
            <Appbar.Action
              icon="more-vert"
              onPress={() => setMenuVisible(true)}
            />
          }>
          
          <Menu.Item
            leadingIcon="mark-email-read"
            onPress={() => {
              handleMarkAllAsRead();
              setMenuVisible(false);
            }}
            title="Mark All Read"
            disabled={unreadCount === 0}
          />
          
          <Divider />
          
          <Menu.Item
            leadingIcon="delete-sweep"
            onPress={() => {
              handleClearAll();
              setMenuVisible(false);
            }}
            title="Clear All"
            disabled={notifications.length === 0}
          />
          
          <Divider />
          
          <Menu.Item
            leadingIcon="settings"
            onPress={() => {
              navigation.navigate('NotificationSettings' as never);
              setMenuVisible(false);
            }}
            title="Settings"
          />
        </Menu>
      </Appbar.Header>

      {renderPermissionPrompt()}

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={[colors.primary]}
          />
        }
        showsVerticalScrollIndicator={false}>
        
        {notifications.length > 0 && renderFilterBar()}
        
        {filteredNotifications.length === 0 ? (
          renderEmptyState()
        ) : (
          filteredNotifications.map(renderNotification)
        )}
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
  permissionCard: {
    margin: spacing.md,
    marginBottom: 0,
  },
  permissionContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  permissionText: {
    flex: 1,
    marginLeft: spacing.md,
  },
  permissionTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    fontWeight: '600',
  },
  permissionMessage: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginTop: spacing.xs,
  },
  permissionButton: {
    marginLeft: spacing.md,
  },
  filterBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  filterButtons: {
    flexDirection: 'row',
  },
  filterButton: {
    marginRight: spacing.sm,
  },
  notificationCard: {
    marginBottom: spacing.sm,
    elevation: 1,
  },
  unreadCard: {
    borderLeftWidth: 4,
    borderLeftColor: colors.primary,
  },
  cardContent: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
  },
  notificationHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  iconContainer: {
    position: 'relative',
    padding: spacing.sm,
    marginRight: spacing.sm,
  },
  unreadDot: {
    position: 'absolute',
    top: 4,
    right: 4,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.primary,
  },
  notificationContent: {
    flex: 1,
  },
  notificationTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    fontWeight: '600',
    marginBottom: spacing.xs,
  },
  notificationMessage: {
    ...typography.bodyMedium,
    color: colors.gray700,
    lineHeight: 20,
    marginBottom: spacing.sm,
  },
  notificationMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  typeChip: {
    height: 20,
    flex: 0,
  },
  typeText: {
    ...typography.labelSmall,
    fontSize: 10,
    fontWeight: '600',
  },
  timestampText: {
    ...typography.bodySmall,
    color: colors.gray500,
    flex: 1,
    textAlign: 'right',
  },
  deleteButton: {
    margin: 0,
  },
});