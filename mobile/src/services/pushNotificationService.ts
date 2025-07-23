/**
 * Push Notification Service
 * 
 * Handles push notification setup, registration,
 * message handling, and notification preferences.
 */

import PushNotification from 'react-native-push-notification';
import PushNotificationIOS from '@react-native-community/push-notification-ios';
import {Platform, Alert} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {apiClient} from './apiClient';

export interface NotificationData {
  id: string;
  type: 'asset_upload' | 'asset_ready' | 'project_update' | 'system_alert' | 'workflow_complete';
  title: string;
  message: string;
  data?: Record<string, any>;
  timestamp: string;
}

export interface NotificationPreferences {
  enabled: boolean;
  types: {
    asset_upload: boolean;
    asset_ready: boolean;
    project_update: boolean;
    system_alert: boolean;
    workflow_complete: boolean;
  };
  quiet_hours: {
    enabled: boolean;
    start: string; // HH:MM format
    end: string;   // HH:MM format
  };
  sound_enabled: boolean;
  vibration_enabled: boolean;
}

class PushNotificationService {
  private deviceToken: string | null = null;
  private preferences: NotificationPreferences | null = null;

  /**
   * Initialize push notification service
   */
  async initialize(): Promise<void> {
    try {
      // Configure push notifications
      this.configurePushNotifications();
      
      // Load saved preferences
      await this.loadPreferences();
      
      // Request permissions
      await this.requestPermissions();
      
      console.log('Push notification service initialized');
    } catch (error) {
      console.error('Failed to initialize push notifications:', error);
    }
  }

  /**
   * Configure push notification settings
   */
  private configurePushNotifications(): void {
    PushNotification.configure({
      // Called when token is generated
      onRegister: (token) => {
        console.log('Device token received:', token);
        this.deviceToken = token.token;
        this.registerDeviceToken(token.token);
      },

      // Called when a remote notification is received
      onNotification: (notification) => {
        console.log('Notification received:', notification);
        this.handleNotification(notification);
        
        // Required on iOS only
        if (Platform.OS === 'ios') {
          notification.finish(PushNotificationIOS.FetchResult.NoData);
        }
      },

      // Called when a remote notification is received while app is in background
      onBackgroundMessage: (remoteMessage) => {
        console.log('Background notification received:', remoteMessage);
        this.handleBackgroundNotification(remoteMessage);
      },

      // IOS settings
      permissions: {
        alert: true,
        badge: true,
        sound: true,
      },
      popInitialNotification: true,
      requestPermissions: false, // We'll request manually
    });

    // Create default notification channels for Android
    if (Platform.OS === 'android') {
      this.createNotificationChannels();
    }
  }

  /**
   * Create notification channels for Android
   */
  private createNotificationChannels(): void {
    PushNotification.createChannel(
      {
        channelId: 'mams-default',
        channelName: 'MAMS Notifications',
        channelDescription: 'General MAMS notifications',
        playSound: true,
        soundName: 'default',
        importance: 4,
        vibrate: true,
      },
      (created) => console.log(`Default channel created: ${created}`)
    );

    PushNotification.createChannel(
      {
        channelId: 'mams-urgent',
        channelName: 'MAMS Urgent',
        channelDescription: 'Urgent MAMS notifications',
        playSound: true,
        soundName: 'default',
        importance: 5,
        vibrate: true,
      },
      (created) => console.log(`Urgent channel created: ${created}`)
    );

    PushNotification.createChannel(
      {
        channelId: 'mams-upload',
        channelName: 'MAMS Uploads',
        channelDescription: 'Upload progress and completion notifications',
        playSound: false,
        importance: 3,
        vibrate: false,
      },
      (created) => console.log(`Upload channel created: ${created}`)
    );
  }

  /**
   * Request notification permissions
   */
  async requestPermissions(): Promise<boolean> {
    try {
      if (Platform.OS === 'ios') {
        const permissions = await PushNotificationIOS.requestPermissions({
          alert: true,
          badge: true,
          sound: true,
          critical: false,
        });
        
        return permissions.alert && permissions.badge && permissions.sound;
      } else {
        // Android permissions are handled automatically
        return true;
      }
    } catch (error) {
      console.error('Failed to request permissions:', error);
      return false;
    }
  }

  /**
   * Register device token with server
   */
  private async registerDeviceToken(token: string): Promise<void> {
    try {
      await apiClient.post('/api/v1/notifications/register', {
        device_token: token,
        platform: Platform.OS,
        app_version: '1.0.0', // Should be dynamic
      });
      
      console.log('Device token registered with server');
    } catch (error) {
      console.error('Failed to register device token:', error);
    }
  }

  /**
   * Handle incoming notification
   */
  private handleNotification(notification: any): void {
    const {title, message, data, userInteraction} = notification;
    
    // Only handle if user tapped the notification
    if (userInteraction) {
      this.navigateToNotificationTarget(data);
    }
    
    // Update badge count on iOS
    if (Platform.OS === 'ios') {
      this.updateBadgeCount();
    }
  }

  /**
   * Handle background notification
   */
  private handleBackgroundNotification(remoteMessage: any): void {
    console.log('Handling background notification:', remoteMessage);
    
    // Process notification data if needed
    // This is called when app is in background
  }

  /**
   * Navigate to appropriate screen based on notification data
   */
  private navigateToNotificationTarget(data: any): void {
    if (!data) return;

    // Navigation logic based on notification type
    switch (data.type) {
      case 'asset_upload':
      case 'asset_ready':
        if (data.assetId) {
          // Navigate to asset details
          // NavigationService.navigate('AssetDetails', {assetId: data.assetId});
        }
        break;
      
      case 'project_update':
        if (data.projectId) {
          // Navigate to project details
          // NavigationService.navigate('ProjectDetails', {projectId: data.projectId});
        }
        break;
      
      case 'workflow_complete':
        if (data.workflowId) {
          // Navigate to workflow details
          // NavigationService.navigate('WorkflowDetails', {workflowId: data.workflowId});
        }
        break;
      
      default:
        // Navigate to notifications screen
        // NavigationService.navigate('Notifications');
        break;
    }
  }

  /**
   * Show local notification
   */
  showLocalNotification(notification: NotificationData): void {
    // Check if notifications are enabled
    if (!this.preferences?.enabled) {
      return;
    }

    // Check if this notification type is enabled
    if (!this.preferences.types[notification.type]) {
      return;
    }

    // Check quiet hours
    if (this.isQuietHours()) {
      return;
    }

    const channelId = this.getChannelId(notification.type);

    PushNotification.localNotification({
      id: notification.id,
      title: notification.title,
      message: notification.message,
      playSound: this.preferences.sound_enabled,
      soundName: 'default',
      vibrate: this.preferences.vibration_enabled,
      channelId,
      userInfo: notification.data,
      // Android specific
      importance: 'default',
      priority: 'default',
      // iOS specific
      category: notification.type,
    });
  }

  /**
   * Cancel notification by ID
   */
  cancelNotification(notificationId: string): void {
    PushNotification.cancelLocalNotifications({id: notificationId});
  }

  /**
   * Cancel all notifications
   */
  cancelAllNotifications(): void {
    PushNotification.cancelAllLocalNotifications();
  }

  /**
   * Get notification channel ID based on type
   */
  private getChannelId(type: string): string {
    switch (type) {
      case 'system_alert':
        return 'mams-urgent';
      case 'asset_upload':
        return 'mams-upload';
      default:
        return 'mams-default';
    }
  }

  /**
   * Check if current time is within quiet hours
   */
  private isQuietHours(): boolean {
    if (!this.preferences?.quiet_hours.enabled) {
      return false;
    }

    const now = new Date();
    const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    
    const {start, end} = this.preferences.quiet_hours;
    
    // Handle overnight quiet hours (e.g., 22:00 to 08:00)
    if (start > end) {
      return currentTime >= start || currentTime <= end;
    } else {
      return currentTime >= start && currentTime <= end;
    }
  }

  /**
   * Update notification preferences
   */
  async updatePreferences(preferences: Partial<NotificationPreferences>): Promise<void> {
    try {
      // Merge with existing preferences
      this.preferences = {
        ...this.getDefaultPreferences(),
        ...this.preferences,
        ...preferences,
      };

      // Save to local storage
      await AsyncStorage.setItem(
        'notification_preferences',
        JSON.stringify(this.preferences)
      );

      // Send to server
      await apiClient.put('/api/v1/notifications/preferences', this.preferences);
      
      console.log('Notification preferences updated');
    } catch (error) {
      console.error('Failed to update notification preferences:', error);
      throw error;
    }
  }

  /**
   * Load notification preferences
   */
  async loadPreferences(): Promise<NotificationPreferences> {
    try {
      // Try to load from local storage first
      const stored = await AsyncStorage.getItem('notification_preferences');
      if (stored) {
        this.preferences = JSON.parse(stored);
      }

      // Fetch latest from server
      try {
        const response = await apiClient.get('/api/v1/notifications/preferences');
        this.preferences = response.data;
        
        // Update local storage
        await AsyncStorage.setItem(
          'notification_preferences',
          JSON.stringify(this.preferences)
        );
      } catch (serverError) {
        console.warn('Failed to fetch preferences from server, using local');
      }

      // Use defaults if no preferences found
      if (!this.preferences) {
        this.preferences = this.getDefaultPreferences();
      }

      return this.preferences;
    } catch (error) {
      console.error('Failed to load notification preferences:', error);
      this.preferences = this.getDefaultPreferences();
      return this.preferences;
    }
  }

  /**
   * Get default notification preferences
   */
  private getDefaultPreferences(): NotificationPreferences {
    return {
      enabled: true,
      types: {
        asset_upload: true,
        asset_ready: true,
        project_update: true,
        system_alert: true,
        workflow_complete: true,
      },
      quiet_hours: {
        enabled: false,
        start: '22:00',
        end: '08:00',
      },
      sound_enabled: true,
      vibration_enabled: true,
    };
  }

  /**
   * Get current notification preferences
   */
  getPreferences(): NotificationPreferences {
    return this.preferences || this.getDefaultPreferences();
  }

  /**
   * Update badge count (iOS only)
   */
  private async updateBadgeCount(): Promise<void> {
    if (Platform.OS !== 'ios') return;

    try {
      // Get unread count from server
      const response = await apiClient.get('/api/v1/notifications/unread-count');
      const unreadCount = response.data.count;
      
      PushNotificationIOS.setApplicationIconBadgeNumber(unreadCount);
    } catch (error) {
      console.error('Failed to update badge count:', error);
    }
  }

  /**
   * Clear badge count
   */
  clearBadgeCount(): void {
    if (Platform.OS === 'ios') {
      PushNotificationIOS.setApplicationIconBadgeNumber(0);
    }
  }

  /**
   * Get device token
   */
  getDeviceToken(): string | null {
    return this.deviceToken;
  }

  /**
   * Check if notifications are enabled
   */
  async checkPermissions(): Promise<{
    alert: boolean;
    badge: boolean;
    sound: boolean;
  }> {
    if (Platform.OS === 'ios') {
      return new Promise((resolve) => {
        PushNotificationIOS.checkPermissions((permissions) => {
          resolve(permissions);
        });
      });
    } else {
      // Android doesn't have a direct way to check, assume enabled
      return {alert: true, badge: true, sound: true};
    }
  }

  /**
   * Open notification settings
   */
  openSettings(): void {
    if (Platform.OS === 'ios') {
      PushNotificationIOS.openSettings();
    } else {
      PushNotification.openSettings();
    }
  }
}

export const pushNotificationService = new PushNotificationService();