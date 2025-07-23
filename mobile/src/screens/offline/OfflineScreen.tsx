/**
 * Offline Screen
 * 
 * Shows offline content, download management,
 * sync status, and offline settings.
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
  Button,
  ProgressBar,
  List,
  Switch,
  Chip,
  IconButton,
  Divider,
  FAB,
} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import {useDispatch, useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {AppState, OfflineAsset} from '@/types';
import {
  startSync,
  removeOfflineAsset,
  clearOfflineData,
  updateOfflineSettings,
  downloadAssetForOffline,
} from '@/store/slices/offlineSlice';
import {colors, spacing, typography} from '@/constants/theme';
import {formatFileSize, formatDate} from '@/utils/formatters';
import {EmptyState} from '@/components/common/EmptyState';

export const OfflineScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  
  const {
    isOnline,
    isConnected,
    connectionType,
    offlineAssets,
    isSyncing,
    lastSyncTime,
    syncProgress,
    downloadQueue,
    downloadProgress,
    settings,
    storageUsed,
    storageAvailable,
  } = useSelector((state: AppState) => state.offline);

  const [refreshing, setRefreshing] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const offlineAssetsList = Object.values(offlineAssets);
  const totalAssets = offlineAssetsList.length;
  const downloadQueueCount = downloadQueue.length;

  useEffect(() => {
    // Auto-sync when coming online if enabled
    if (isOnline && settings.auto_sync && !isSyncing) {
      handleSync();
    }
  }, [isOnline, settings.auto_sync, isSyncing]);

  const handleSync = useCallback(async () => {
    if (!isOnline) {
      Alert.alert(
        'No Connection',
        'Cannot sync while offline. Please check your internet connection.',
        [{text: 'OK'}]
      );
      return;
    }

    dispatch(startSync());
  }, [isOnline, dispatch]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    if (isOnline) {
      await handleSync();
    }
    setRefreshing(false);
  }, [isOnline, handleSync]);

  const handleRemoveAsset = useCallback((assetId: string) => {
    Alert.alert(
      'Remove Offline Asset',
      'This will remove the asset from offline storage. You can download it again later.',
      [
        {text: 'Cancel', style: 'cancel'},
        {
          text: 'Remove',
          style: 'destructive',
          onPress: () => dispatch(removeOfflineAsset(assetId)),
        },
      ]
    );
  }, [dispatch]);

  const handleClearAllData = useCallback(() => {
    Alert.alert(
      'Clear All Offline Data',
      'This will remove all offline assets and cached data. This action cannot be undone.',
      [
        {text: 'Cancel', style: 'cancel'},
        {
          text: 'Clear All',
          style: 'destructive',
          onPress: () => dispatch(clearOfflineData()),
        },
      ]
    );
  }, [dispatch]);

  const handleSettingChange = useCallback((key: string, value: any) => {
    dispatch(updateOfflineSettings({[key]: value}));
  }, [dispatch]);

  const renderConnectionStatus = () => (
    <Card style={styles.card}>
      <Card.Content>
        <View style={styles.statusHeader}>
          <Icon
            name={isOnline ? 'wifi' : 'wifi-off'}
            size={24}
            color={isOnline ? colors.success : colors.error}
          />
          <View style={styles.statusInfo}>
            <Text style={styles.statusTitle}>
              {isOnline ? 'Online' : 'Offline'}
            </Text>
            <Text style={styles.statusSubtitle}>
              {isConnected ? `Connected via ${connectionType}` : 'No connection'}
            </Text>
          </View>
          
          {isOnline && (
            <Button
              mode="outlined"
              onPress={handleSync}
              disabled={isSyncing}
              loading={isSyncing}
              compact>
              Sync
            </Button>
          )}
        </View>

        {isSyncing && (
          <View style={styles.syncProgress}>
            <Text style={styles.syncText}>Syncing...</Text>
            <ProgressBar
              progress={syncProgress / 100}
              color={colors.primary}
              style={styles.progressBar}
            />
          </View>
        )}

        {lastSyncTime && (
          <Text style={styles.lastSyncText}>
            Last sync: {formatDate(lastSyncTime)}
          </Text>
        )}
      </Card.Content>
    </Card>
  );

  const renderStorageInfo = () => (
    <Card style={styles.card}>
      <Card.Content>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Storage</Text>
          <Text style={styles.storageUsed}>
            {formatFileSize(storageUsed)} used
          </Text>
        </View>

        <ProgressBar
          progress={storageUsed / Math.max(settings.max_offline_storage, 1)}
          color={colors.primary}
          style={styles.progressBar}
        />

        <View style={styles.storageDetails}>
          <Text style={styles.storageText}>
            {totalAssets} assets • {formatFileSize(storageAvailable)} available
          </Text>
          
          {downloadQueueCount > 0 && (
            <Chip mode="flat" icon="download" style={styles.downloadChip}>
              {downloadQueueCount} downloading
            </Chip>
          )}
        </View>
      </Card.Content>
    </Card>
  );

  const renderOfflineSettings = () => {
    if (!showSettings) return null;

    return (
      <Card style={styles.card}>
        <Card.Content>
          <Text style={styles.sectionTitle}>Offline Settings</Text>
          
          <List.Item
            title="Auto Sync"
            description="Automatically sync when coming online"
            right={() => (
              <Switch
                value={settings.auto_sync}
                onValueChange={(value) => handleSettingChange('auto_sync', value)}
              />
            )}
          />
          
          <Divider />
          
          <List.Item
            title="WiFi Only Sync"
            description="Only sync when connected to WiFi"
            right={() => (
              <Switch
                value={settings.sync_on_wifi_only}
                onValueChange={(value) => handleSettingChange('sync_on_wifi_only', value)}
              />
            )}
          />
          
          <Divider />
          
          <List.Item
            title="Download Thumbnails"
            description="Download thumbnails for offline viewing"
            right={() => (
              <Switch
                value={settings.download_thumbnails}
                onValueChange={(value) => handleSettingChange('download_thumbnails', value)}
              />
            )}
          />
          
          <Divider />
          
          <List.Item
            title="Download Previews"
            description="Download preview files (uses more storage)"
            right={() => (
              <Switch
                value={settings.download_previews}
                onValueChange={(value) => handleSettingChange('download_previews', value)}
              />
            )}
          />
        </Card.Content>
      </Card>
    );
  };

  const renderOfflineAsset = (asset: OfflineAsset) => {
    const downloadingProgress = downloadProgress[asset.id];
    const isDownloading = downloadQueue.includes(asset.id);

    return (
      <List.Item
        key={asset.id}
        title={asset.name}
        description={`${asset.type} • ${formatFileSize(asset.file_size)} • Downloaded ${formatDate(asset.offline_data?.downloaded_at || '')}`}
        left={(props) => (
          <View style={styles.assetIcon}>
            <Icon
              {...props}
              name={asset.type?.startsWith('image/') ? 'image' : 
                    asset.type?.startsWith('video/') ? 'videocam' : 
                    asset.type?.startsWith('audio/') ? 'audiotrack' : 'insert-drive-file'}
              size={24}
              color={colors.primary}
            />
            {asset.offline_data?.has_preview && (
              <Icon
                name="preview"
                size={12}
                color={colors.success}
                style={styles.previewIndicator}
              />
            )}
          </View>
        )}
        right={(props) => (
          <View style={styles.assetActions}>
            {isDownloading && (
              <View style={styles.downloadProgress}>
                <Text style={styles.progressText}>
                  {Math.round(downloadingProgress || 0)}%
                </Text>
                <ProgressBar
                  progress={(downloadingProgress || 0) / 100}
                  color={colors.primary}
                  style={styles.miniProgressBar}
                />
              </View>
            )}
            <IconButton
              {...props}
              icon="delete"
              size={20}
              onPress={() => handleRemoveAsset(asset.id)}
            />
          </View>
        )}
        onPress={() => {
          // Navigate to asset details
          navigation.navigate('AssetDetails', {assetId: asset.id} as never);
        }}
      />
    );
  };

  const renderOfflineAssets = () => {
    if (totalAssets === 0) {
      return (
        <EmptyState
          icon="cloud-download"
          title="No Offline Content"
          message="Download assets to view them offline"
          actionLabel="Browse Assets"
          onAction={() => navigation.navigate('Browse' as never)}
          actionIcon="explore"
        />
      );
    }

    return (
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>
              Offline Assets ({totalAssets})
            </Text>
            <Button
              mode="text"
              onPress={handleClearAllData}
              textColor={colors.error}
              compact>
              Clear All
            </Button>
          </View>
          
          {offlineAssetsList.map(renderOfflineAsset)}
        </Card.Content>
      </Card>
    );
  };

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.appBar}>
        <Appbar.Content title="Offline" />
        <Appbar.Action
          icon={showSettings ? 'settings' : 'settings-outline'}
          onPress={() => setShowSettings(!showSettings)}
        />
      </Appbar.Header>

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
        
        {renderConnectionStatus()}
        {renderStorageInfo()}
        {renderOfflineSettings()}
        {renderOfflineAssets()}
      </ScrollView>

      {/* Sync FAB */}
      {isOnline && !isSyncing && (
        <FAB
          icon="sync"
          label="Sync Now"
          onPress={handleSync}
          style={styles.syncFab}
        />
      )}
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
  statusHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusInfo: {
    flex: 1,
    marginLeft: spacing.md,
  },
  statusTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    fontWeight: '600',
  },
  statusSubtitle: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginTop: spacing.xs,
  },
  syncProgress: {
    marginTop: spacing.md,
  },
  syncText: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  progressBar: {
    height: 4,
    borderRadius: 2,
  },
  lastSyncText: {
    ...typography.bodySmall,
    color: colors.gray500,
    marginTop: spacing.sm,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  sectionTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    fontWeight: '600',
  },
  storageUsed: {
    ...typography.bodyMedium,
    color: colors.gray600,
    fontWeight: '500',
  },
  storageDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  storageText: {
    ...typography.bodyMedium,
    color: colors.gray600,
  },
  downloadChip: {
    height: 24,
  },
  assetIcon: {
    position: 'relative',
    padding: spacing.sm,
  },
  previewIndicator: {
    position: 'absolute',
    top: 2,
    right: 2,
  },
  assetActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  downloadProgress: {
    alignItems: 'center',
    marginRight: spacing.sm,
    minWidth: 40,
  },
  progressText: {
    ...typography.bodySmall,
    color: colors.onSurface,
    fontSize: 10,
  },
  miniProgressBar: {
    width: 30,
    height: 2,
    marginTop: 2,
  },
  syncFab: {
    position: 'absolute',
    margin: spacing.md,
    right: 0,
    bottom: 0,
  },
});