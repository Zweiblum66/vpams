/**
 * Notifications Redux Slice
 * 
 * Manages notification state including unread notifications,
 * preferences, and push notification settings.
 */

import {createSlice, createAsyncThunk, PayloadAction} from '@reduxjs/toolkit';
import {NotificationState, Notification, NotificationPreferences} from '@/types';
import {apiClient} from '@/services/apiClient';
import {pushNotificationService} from '@/services/pushNotificationService';

const initialState: NotificationState = {
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  error: null,
  preferences: {
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
  },
  deviceToken: null,
  permissionsGranted: false,
};

// Async thunks
export const initializeNotifications = createAsyncThunk(
  'notifications/initialize',
  async (_, {dispatch}) => {
    try {
      // Initialize push notification service
      await pushNotificationService.initialize();
      
      // Load preferences
      const preferences = await pushNotificationService.loadPreferences();
      
      // Check permissions
      const permissions = await pushNotificationService.checkPermissions();
      const permissionsGranted = permissions.alert && permissions.badge && permissions.sound;
      
      // Get device token
      const deviceToken = pushNotificationService.getDeviceToken();
      
      // Fetch notifications from server
      dispatch(fetchNotifications());
      dispatch(fetchUnreadCount());
      
      return {
        preferences,
        permissionsGranted,
        deviceToken,
      };
    } catch (error: any) {
      throw new Error(error.message);
    }
  }
);

export const fetchNotifications = createAsyncThunk(
  'notifications/fetchNotifications',
  async (params: {page?: number; limit?: number} = {}) => {
    try {
      const response = await apiClient.get('/api/v1/notifications', {
        params: {
          page: params.page || 1,
          limit: params.limit || 20,
        },
      });
      
      return response.data;
    } catch (error: any) {
      throw new Error(error.message);
    }
  }
);

export const fetchUnreadCount = createAsyncThunk(
  'notifications/fetchUnreadCount',
  async () => {
    try {
      const response = await apiClient.get('/api/v1/notifications/unread-count');
      return response.data.count;
    } catch (error: any) {
      throw new Error(error.message);
    }
  }
);

export const markAsRead = createAsyncThunk(
  'notifications/markAsRead',
  async (notificationId: string) => {
    try {
      await apiClient.patch(`/api/v1/notifications/${notificationId}/read`);
      return notificationId;
    } catch (error: any) {
      throw new Error(error.message);
    }
  }
);

export const markAllAsRead = createAsyncThunk(
  'notifications/markAllAsRead',
  async () => {
    try {
      await apiClient.patch('/api/v1/notifications/mark-all-read');
      return true;
    } catch (error: any) {
      throw new Error(error.message);
    }
  }
);

export const deleteNotification = createAsyncThunk(
  'notifications/deleteNotification',
  async (notificationId: string) => {
    try {
      await apiClient.delete(`/api/v1/notifications/${notificationId}`);
      return notificationId;
    } catch (error: any) {
      throw new Error(error.message);
    }
  }
);

export const updateNotificationPreferences = createAsyncThunk(
  'notifications/updatePreferences',
  async (preferences: Partial<NotificationPreferences>) => {
    try {
      await pushNotificationService.updatePreferences(preferences);
      return pushNotificationService.getPreferences();
    } catch (error: any) {
      throw new Error(error.message);
    }
  }
);

export const requestNotificationPermissions = createAsyncThunk(
  'notifications/requestPermissions',
  async () => {
    try {
      const granted = await pushNotificationService.requestPermissions();
      return granted;
    } catch (error: any) {
      throw new Error(error.message);
    }
  }
);

export const registerDeviceToken = createAsyncThunk(
  'notifications/registerDeviceToken',
  async (token: string) => {
    try {
      await apiClient.post('/api/v1/notifications/register', {
        device_token: token,
        platform: 'mobile',
      });
      
      return token;
    } catch (error: any) {
      throw new Error(error.message);
    }
  }
);

// Notifications slice
const notificationsSlice = createSlice({
  name: 'notifications',
  initialState,
  reducers: {
    addNotification: (state, action: PayloadAction<Notification>) => {
      const notification = action.payload;
      
      // Add to beginning of array
      state.notifications.unshift(notification);
      
      // Update unread count if notification is unread
      if (!notification.read_at) {
        state.unreadCount += 1;
      }
      
      // Keep only last 100 notifications
      state.notifications = state.notifications.slice(0, 100);
    },
    
    removeNotification: (state, action: PayloadAction<string>) => {
      const notificationId = action.payload;
      const notification = state.notifications.find(n => n.id === notificationId);
      
      // Update unread count if notification was unread
      if (notification && !notification.read_at) {
        state.unreadCount = Math.max(0, state.unreadCount - 1);
      }
      
      // Remove notification
      state.notifications = state.notifications.filter(n => n.id !== notificationId);
    },
    
    markNotificationAsRead: (state, action: PayloadAction<string>) => {
      const notificationId = action.payload;
      const notification = state.notifications.find(n => n.id === notificationId);
      
      if (notification && !notification.read_at) {
        notification.read_at = new Date().toISOString();
        state.unreadCount = Math.max(0, state.unreadCount - 1);
      }
    },
    
    clearAllNotifications: (state) => {
      state.notifications = [];
      state.unreadCount = 0;
    },
    
    setUnreadCount: (state, action: PayloadAction<number>) => {
      state.unreadCount = action.payload;
    },
    
    updatePreferences: (state, action: PayloadAction<Partial<NotificationPreferences>>) => {
      state.preferences = {...state.preferences, ...action.payload};
    },
    
    setDeviceToken: (state, action: PayloadAction<string | null>) => {
      state.deviceToken = action.payload;
    },
    
    setPermissionsGranted: (state, action: PayloadAction<boolean>) => {
      state.permissionsGranted = action.payload;
    },
    
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Initialize notifications
    builder
      .addCase(initializeNotifications.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(initializeNotifications.fulfilled, (state, action) => {
        state.isLoading = false;
        state.preferences = action.payload.preferences;
        state.permissionsGranted = action.payload.permissionsGranted;
        state.deviceToken = action.payload.deviceToken;
      })
      .addCase(initializeNotifications.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to initialize notifications';
      });

    // Fetch notifications
    builder
      .addCase(fetchNotifications.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchNotifications.fulfilled, (state, action) => {
        state.isLoading = false;
        state.notifications = action.payload.data;
      })
      .addCase(fetchNotifications.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to fetch notifications';
      });

    // Fetch unread count
    builder
      .addCase(fetchUnreadCount.fulfilled, (state, action) => {
        state.unreadCount = action.payload;
      });

    // Mark as read
    builder
      .addCase(markAsRead.fulfilled, (state, action) => {
        const notificationId = action.payload;
        const notification = state.notifications.find(n => n.id === notificationId);
        
        if (notification && !notification.read_at) {
          notification.read_at = new Date().toISOString();
          state.unreadCount = Math.max(0, state.unreadCount - 1);
        }
      })
      .addCase(markAsRead.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to mark notification as read';
      });

    // Mark all as read
    builder
      .addCase(markAllAsRead.fulfilled, (state) => {
        state.notifications.forEach(notification => {
          if (!notification.read_at) {
            notification.read_at = new Date().toISOString();
          }
        });
        state.unreadCount = 0;
      })
      .addCase(markAllAsRead.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to mark all notifications as read';
      });

    // Delete notification
    builder
      .addCase(deleteNotification.fulfilled, (state, action) => {
        const notificationId = action.payload;
        const notification = state.notifications.find(n => n.id === notificationId);
        
        // Update unread count if notification was unread
        if (notification && !notification.read_at) {
          state.unreadCount = Math.max(0, state.unreadCount - 1);
        }
        
        // Remove notification
        state.notifications = state.notifications.filter(n => n.id !== notificationId);
      })
      .addCase(deleteNotification.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to delete notification';
      });

    // Update preferences
    builder
      .addCase(updateNotificationPreferences.fulfilled, (state, action) => {
        state.preferences = action.payload;
      })
      .addCase(updateNotificationPreferences.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to update notification preferences';
      });

    // Request permissions
    builder
      .addCase(requestNotificationPermissions.fulfilled, (state, action) => {
        state.permissionsGranted = action.payload;
      })
      .addCase(requestNotificationPermissions.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to request notification permissions';
      });

    // Register device token
    builder
      .addCase(registerDeviceToken.fulfilled, (state, action) => {
        state.deviceToken = action.payload;
      })
      .addCase(registerDeviceToken.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to register device token';
      });
  },
});

export const {
  addNotification,
  removeNotification,
  markNotificationAsRead,
  clearAllNotifications,
  setUnreadCount,
  updatePreferences,
  setDeviceToken,
  setPermissionsGranted,
  clearError,
} = notificationsSlice.actions;

export default notificationsSlice.reducer;