/**
 * Notification Settings Screen
 * 
 * Allows users to configure notification preferences,
 * quiet hours, and notification types.
 */

import React, {useState, useEffect} from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import {
  Appbar,
  Card,
  Text,
  Switch,
  List,
  Button,
  TextInput,
  Divider,
  Chip,
} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import {useDispatch, useSelector} from 'react-redux';
import DateTimePickerModal from 'react-native-modal-datetime-picker';

import {AppState, NotificationPreferences} from '@/types';
import {updateNotificationPreferences} from '@/store/slices/notificationsSlice';
import {colors, spacing, typography} from '@/constants/theme';
import {pushNotificationService} from '@/services/pushNotificationService';

export const NotificationSettingsScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  
  const {preferences, permissionsGranted} = useSelector(
    (state: AppState) => state.notifications
  );

  const [localPreferences, setLocalPreferences] = useState<NotificationPreferences>(preferences);
  const [isTimePickerVisible, setTimePickerVisible] = useState(false);
  const [timePickerMode, setTimePickerMode] = useState<'start' | 'end'>('start');
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    setLocalPreferences(preferences);
  }, [preferences]);

  const handlePreferenceChange = (key: keyof NotificationPreferences, value: any) => {
    setLocalPreferences(prev => ({
      ...prev,
      [key]: value,
    }));
    setHasChanges(true);
  };

  const handleTypeChange = (type: keyof NotificationPreferences['types'], value: boolean) => {
    setLocalPreferences(prev => ({
      ...prev,
      types: {
        ...prev.types,
        [type]: value,
      },
    }));
    setHasChanges(true);
  };

  const handleQuietHoursChange = (key: keyof NotificationPreferences['quiet_hours'], value: any) => {
    setLocalPreferences(prev => ({
      ...prev,
      quiet_hours: {
        ...prev.quiet_hours,
        [key]: value,
      },
    }));
    setHasChanges(true);
  };

  const handleTimeSelect = (date: Date) => {
    const time = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    
    if (timePickerMode === 'start') {
      handleQuietHoursChange('start', time);
    } else {
      handleQuietHoursChange('end', time);
    }
    
    setTimePickerVisible(false);
  };

  const showTimePicker = (mode: 'start' | 'end') => {
    setTimePickerMode(mode);
    setTimePickerVisible(true);
  };

  const getTimeDate = (timeString: string): Date => {
    const [hours, minutes] = timeString.split(':').map(Number);
    const date = new Date();
    date.setHours(hours);
    date.setMinutes(minutes);
    return date;
  };

  const handleSave = async () => {
    try {
      await dispatch(updateNotificationPreferences(localPreferences));
      setHasChanges(false);
      Alert.alert('Success', 'Notification preferences updated successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to update notification preferences');
    }
  };

  const handleReset = () => {
    Alert.alert(
      'Reset Preferences',
      'Are you sure you want to reset all notification preferences to default?',
      [
        {text: 'Cancel', style: 'cancel'},
        {
          text: 'Reset',
          style: 'destructive',
          onPress: () => {
            const defaultPreferences = pushNotificationService.getPreferences();
            setLocalPreferences(defaultPreferences);
            setHasChanges(true);
          },
        },
      ]
    );
  };

  const handleOpenSystemSettings = () => {
    Alert.alert(
      'System Settings',
      'Open device notification settings to enable/disable notifications for MAMS.',
      [
        {text: 'Cancel'},
        {
          text: 'Open Settings',
          onPress: () => pushNotificationService.openSettings(),
        },
      ]
    );
  };

  const renderGeneralSettings = () => (
    <Card style={styles.card}>
      <Card.Content>
        <Text style={styles.sectionTitle}>General</Text>
        
        <List.Item
          title="Enable Notifications"
          description="Receive push notifications from MAMS"
          right={() => (
            <Switch
              value={localPreferences.enabled}
              onValueChange={(value) => handlePreferenceChange('enabled', value)}
            />
          )}
        />
        
        <Divider />
        
        <List.Item
          title="Sound"
          description="Play sound for notifications"
          right={() => (
            <Switch
              value={localPreferences.sound_enabled}
              onValueChange={(value) => handlePreferenceChange('sound_enabled', value)}
              disabled={!localPreferences.enabled}
            />
          )}
        />
        
        <Divider />
        
        <List.Item
          title="Vibration"
          description="Vibrate for notifications"
          right={() => (
            <Switch
              value={localPreferences.vibration_enabled}
              onValueChange={(value) => handlePreferenceChange('vibration_enabled', value)}
              disabled={!localPreferences.enabled}
            />
          )}
        />
        
        <Divider />
        
        <List.Item
          title="System Settings"
          description="Configure device notification settings"
          right={() => <List.Icon icon="open-in-new" />}
          onPress={handleOpenSystemSettings}
        />
      </Card.Content>
    </Card>
  );

  const renderNotificationTypes = () => (
    <Card style={styles.card}>
      <Card.Content>
        <Text style={styles.sectionTitle}>Notification Types</Text>
        
        <List.Item
          title="Asset Uploads"
          description="Notify when assets are being uploaded"
          right={() => (
            <Switch
              value={localPreferences.types.asset_upload}
              onValueChange={(value) => handleTypeChange('asset_upload', value)}
              disabled={!localPreferences.enabled}
            />
          )}
        />
        
        <Divider />
        
        <List.Item
          title="Asset Ready"
          description="Notify when assets are processed and ready"
          right={() => (
            <Switch
              value={localPreferences.types.asset_ready}
              onValueChange={(value) => handleTypeChange('asset_ready', value)}
              disabled={!localPreferences.enabled}
            />
          )}
        />
        
        <Divider />
        
        <List.Item
          title="Project Updates"
          description="Notify about project changes and comments"
          right={() => (
            <Switch
              value={localPreferences.types.project_update}
              onValueChange={(value) => handleTypeChange('project_update', value)}
              disabled={!localPreferences.enabled}
            />
          )}
        />
        
        <Divider />
        
        <List.Item
          title="Workflow Complete"
          description="Notify when workflows are completed"
          right={() => (
            <Switch
              value={localPreferences.types.workflow_complete}
              onValueChange={(value) => handleTypeChange('workflow_complete', value)}
              disabled={!localPreferences.enabled}
            />
          )}
        />
        
        <Divider />
        
        <List.Item
          title="System Alerts"
          description="Important system notifications and alerts"
          right={() => (
            <Switch
              value={localPreferences.types.system_alert}
              onValueChange={(value) => handleTypeChange('system_alert', value)}
              disabled={!localPreferences.enabled}
            />
          )}
        />
      </Card.Content>
    </Card>
  );

  const renderQuietHours = () => (
    <Card style={styles.card}>
      <Card.Content>
        <Text style={styles.sectionTitle}>Quiet Hours</Text>
        
        <List.Item
          title="Enable Quiet Hours"
          description="Silence notifications during specified hours"
          right={() => (
            <Switch
              value={localPreferences.quiet_hours.enabled}
              onValueChange={(value) => handleQuietHoursChange('enabled', value)}
              disabled={!localPreferences.enabled}
            />
          )}
        />
        
        {localPreferences.quiet_hours.enabled && (
          <>
            <Divider />
            
            <View style={styles.timeSection}>
              <Text style={styles.timeLabel}>Quiet Hours Period</Text>
              
              <View style={styles.timeRow}>
                <View style={styles.timeInput}>
                  <Text style={styles.timeInputLabel}>From</Text>
                  <Button
                    mode="outlined"
                    onPress={() => showTimePicker('start')}
                    style={styles.timeButton}>
                    {localPreferences.quiet_hours.start}
                  </Button>
                </View>
                
                <View style={styles.timeInput}>
                  <Text style={styles.timeInputLabel}>To</Text>
                  <Button
                    mode="outlined"
                    onPress={() => showTimePicker('end')}
                    style={styles.timeButton}>
                    {localPreferences.quiet_hours.end}
                  </Button>
                </View>
              </View>
              
              <Text style={styles.timeNote}>
                Notifications will be silenced during these hours.
                {localPreferences.quiet_hours.start > localPreferences.quiet_hours.end && 
                  ' This spans overnight.'
                }
              </Text>
            </View>
          </>
        )}
      </Card.Content>
    </Card>
  );

  const renderPermissionStatus = () => {
    if (permissionsGranted) return null;

    return (
      <Card style={[styles.card, styles.warningCard]}>
        <Card.Content>
          <View style={styles.permissionStatus}>
            <Text style={styles.permissionTitle}>Permissions Required</Text>
            <Text style={styles.permissionDescription}>
              Notification permissions are disabled. Enable them in your device settings to receive push notifications.
            </Text>
            <Button
              mode="contained"
              onPress={handleOpenSystemSettings}
              style={styles.permissionButton}>
              Open Settings
            </Button>
          </View>
        </Card.Content>
      </Card>
    );
  };

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title="Notification Settings" />
        {hasChanges && (
          <Appbar.Action
            icon="content-save"
            onPress={handleSave}
          />
        )}
      </Appbar.Header>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}>
        
        {renderPermissionStatus()}
        {renderGeneralSettings()}
        {renderNotificationTypes()}
        {renderQuietHours()}
        
        <View style={styles.actionButtons}>
          <Button
            mode="outlined"
            onPress={handleReset}
            style={styles.actionButton}>
            Reset to Default
          </Button>
          
          <Button
            mode="contained"
            onPress={handleSave}
            disabled={!hasChanges}
            style={styles.actionButton}>
            Save Changes
          </Button>
        </View>
      </ScrollView>

      <DateTimePickerModal
        isVisible={isTimePickerVisible}
        mode="time"
        date={getTimeDate(
          timePickerMode === 'start' 
            ? localPreferences.quiet_hours.start 
            : localPreferences.quiet_hours.end
        )}
        onConfirm={handleTimeSelect}
        onCancel={() => setTimePickerVisible(false)}
        is24Hour={true}
      />
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
  warningCard: {
    backgroundColor: colors.warning + '10',
    borderColor: colors.warning,
    borderWidth: 1,
  },
  sectionTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    marginBottom: spacing.md,
    fontWeight: '600',
  },
  permissionStatus: {
    alignItems: 'center',
    padding: spacing.md,
  },
  permissionTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    fontWeight: '600',
    marginBottom: spacing.sm,
  },
  permissionDescription: {
    ...typography.bodyMedium,
    color: colors.gray600,
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  permissionButton: {
    marginTop: spacing.sm,
  },
  timeSection: {
    padding: spacing.md,
  },
  timeLabel: {
    ...typography.bodyLarge,
    color: colors.onSurface,
    fontWeight: '500',
    marginBottom: spacing.md,
  },
  timeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.md,
  },
  timeInput: {
    flex: 1,
    marginHorizontal: spacing.sm,
  },
  timeInputLabel: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginBottom: spacing.sm,
  },
  timeButton: {
    borderColor: colors.gray300,
  },
  timeNote: {
    ...typography.bodySmall,
    color: colors.gray500,
    fontStyle: 'italic',
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.lg,
    marginBottom: spacing.xl,
  },
  actionButton: {
    flex: 1,
    marginHorizontal: spacing.sm,
  },
});