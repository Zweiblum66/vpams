/**
 * Asset Detail Screen
 * 
 * Displays detailed information about an asset including
 * metadata, preview, actions, and AR viewing options.
 */

import React, {useState, useEffect} from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Dimensions,
  TouchableOpacity,
} from 'react-native';
import {
  Appbar,
  Card,
  Text,
  Chip,
  Button,
  List,
  Divider,
  FAB,
  Portal,
  Dialog,
} from 'react-native-paper';
import {useNavigation, useRoute, RouteProp} from '@react-navigation/native';
import {useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import FastImage from 'react-native-fast-image';
import Video from 'react-native-video';

import {AppState, Asset} from '@/types';
import {ARViewer} from '@/components/ar/ARViewer';
import {colors, spacing, typography} from '@/constants/theme';
import {formatFileSize, formatDate} from '@/utils/formatters';
import {shareService} from '@/services/shareService';
import {downloadService} from '@/services/downloadService';

const {width: screenWidth} = Dimensions.get('window');

type AssetDetailScreenRouteProp = RouteProp<{
  AssetDetail: {assetId: string};
}, 'AssetDetail'>;

export const AssetDetailScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute<AssetDetailScreenRouteProp>();
  const {assetId} = route.params;

  const asset = useSelector((state: AppState) => 
    state.assets.assets.find(a => a.id === assetId)
  );

  const [showActions, setShowActions] = useState(false);
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);

  if (!asset) {
    return null;
  }

  const isImage = asset.metadata?.mime_type?.startsWith('image/');
  const isVideo = asset.metadata?.mime_type?.startsWith('video/');
  const isAudio = asset.metadata?.mime_type?.startsWith('audio/');

  const handleShare = async () => {
    try {
      await shareService.shareAsset(asset);
    } catch (error) {
      console.error('Failed to share asset:', error);
    }
  };

  const handleDownload = async () => {
    try {
      await downloadService.downloadAsset(asset);
    } catch (error) {
      console.error('Failed to download asset:', error);
    }
  };

  const renderPreview = () => {
    if (isImage) {
      return (
        <FastImage
          source={{uri: asset.proxy_url || asset.thumbnail_url}}
          style={styles.preview}
          resizeMode={FastImage.resizeMode.contain}
        />
      );
    }

    if (isVideo) {
      return (
        <TouchableOpacity
          style={styles.preview}
          onPress={() => setIsVideoPlaying(!isVideoPlaying)}>
          <Video
            source={{uri: asset.proxy_url}}
            style={styles.video}
            paused={!isVideoPlaying}
            controls={isVideoPlaying}
            resizeMode="contain"
          />
          {!isVideoPlaying && (
            <View style={styles.playOverlay}>
              <Icon name="play-circle-filled" size={64} color={colors.white} />
            </View>
          )}
        </TouchableOpacity>
      );
    }

    return (
      <View style={[styles.preview, styles.placeholderPreview]}>
        <Icon 
          name={isAudio ? 'audiotrack' : 'insert-drive-file'} 
          size={64} 
          color={colors.gray400} 
        />
        <Text style={styles.placeholderText}>{asset.name}</Text>
      </View>
    );
  };

  const renderMetadata = () => (
    <Card style={styles.card}>
      <Card.Content>
        <Text style={styles.sectionTitle}>Details</Text>
        
        <List.Item
          title="File Size"
          description={formatFileSize(asset.file_size)}
          left={(props) => <List.Icon {...props} icon="storage" />}
        />
        
        {asset.metadata?.width && asset.metadata?.height && (
          <List.Item
            title="Dimensions"
            description={`${asset.metadata.width} × ${asset.metadata.height}`}
            left={(props) => <List.Icon {...props} icon="aspect-ratio" />}
          />
        )}
        
        {asset.metadata?.duration && (
          <List.Item
            title="Duration"
            description={`${Math.floor(asset.metadata.duration / 60)}:${(asset.metadata.duration % 60).toString().padStart(2, '0')}`}
            left={(props) => <List.Icon {...props} icon="timer" />}
          />
        )}
        
        <List.Item
          title="Format"
          description={asset.metadata?.mime_type || 'Unknown'}
          left={(props) => <List.Icon {...props} icon="description" />}
        />
        
        <List.Item
          title="Created"
          description={formatDate(asset.created_at)}
          left={(props) => <List.Icon {...props} icon="event" />}
        />
        
        {asset.project && (
          <List.Item
            title="Project"
            description={asset.project.name}
            left={(props) => <List.Icon {...props} icon="folder" />}
            onPress={() => navigation.navigate('ProjectDetail' as never, {
              projectId: asset.project!.id
            } as never)}
          />
        )}
      </Card.Content>
    </Card>
  );

  const renderTags = () => {
    if (!asset.tags || asset.tags.length === 0) return null;

    return (
      <Card style={styles.card}>
        <Card.Content>
          <Text style={styles.sectionTitle}>Tags</Text>
          <View style={styles.tagsContainer}>
            {asset.tags.map(tag => (
              <Chip
                key={tag}
                mode="flat"
                style={styles.tag}
                onPress={() => navigation.navigate('Search' as never, {
                  query: tag
                } as never)}>
                {tag}
              </Chip>
            ))}
          </View>
        </Card.Content>
      </Card>
    );
  };

  const renderActions = () => (
    <Portal>
      <Dialog
        visible={showActions}
        onDismiss={() => setShowActions(false)}>
        <Dialog.Title>Asset Actions</Dialog.Title>
        <Dialog.Content>
          <List.Section>
            <List.Item
              title="Download"
              description="Save to device"
              left={(props) => <List.Icon {...props} icon="download" />}
              onPress={() => {
                setShowActions(false);
                handleDownload();
              }}
            />
            <List.Item
              title="Share"
              description="Share with others"
              left={(props) => <List.Icon {...props} icon="share" />}
              onPress={() => {
                setShowActions(false);
                handleShare();
              }}
            />
            <List.Item
              title="Add to Project"
              description="Organize in project"
              left={(props) => <List.Icon {...props} icon="folder-plus" />}
              onPress={() => {
                setShowActions(false);
                navigation.navigate('ProjectSelect' as never);
              }}
            />
            <List.Item
              title="Edit Metadata"
              description="Update asset information"
              left={(props) => <List.Icon {...props} icon="edit" />}
              onPress={() => {
                setShowActions(false);
                navigation.navigate('AssetEditor' as never, {
                  assetId: asset.id
                } as never);
              }}
            />
            {(asset.metadata?.mime_type?.startsWith('video/') || 
              asset.metadata?.mime_type?.startsWith('image/')) && (
              <List.Item
                title="Edit Media"
                description="Trim, filter, and adjust"
                left={(props) => <List.Icon {...props} icon="movie-edit" />}
                onPress={() => {
                  setShowActions(false);
                  navigation.navigate('Editing' as never, {
                    assetId: asset.id
                  } as never);
                }}
              />
            )}
          </List.Section>
        </Dialog.Content>
        <Dialog.Actions>
          <Button onPress={() => setShowActions(false)}>Cancel</Button>
        </Dialog.Actions>
      </Dialog>
    </Portal>
  );

  return (
    <View style={styles.container}>
      <Appbar.Header>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title={asset.name} />
        <Appbar.Action icon="share" onPress={handleShare} />
        <Appbar.Action icon="download" onPress={handleDownload} />
      </Appbar.Header>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}>
        
        {renderPreview()}
        
        {/* AR Viewer Component */}
        <ARViewer asset={asset} />
        
        {renderMetadata()}
        {renderTags()}
        
        {asset.metadata?.description && (
          <Card style={styles.card}>
            <Card.Content>
              <Text style={styles.sectionTitle}>Description</Text>
              <Text style={styles.description}>
                {asset.metadata.description}
              </Text>
            </Card.Content>
          </Card>
        )}
      </ScrollView>

      <FAB
        icon="dots-vertical"
        onPress={() => setShowActions(true)}
        style={styles.fab}
      />

      {renderActions()}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 100,
  },
  preview: {
    width: screenWidth,
    height: screenWidth,
    backgroundColor: colors.black,
    justifyContent: 'center',
    alignItems: 'center',
  },
  video: {
    width: '100%',
    height: '100%',
  },
  playOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  placeholderPreview: {
    backgroundColor: colors.gray100,
  },
  placeholderText: {
    ...typography.bodyLarge,
    color: colors.gray600,
    marginTop: spacing.md,
    paddingHorizontal: spacing.lg,
    textAlign: 'center',
  },
  card: {
    margin: spacing.md,
  },
  sectionTitle: {
    ...typography.titleMedium,
    color: colors.onSurface,
    marginBottom: spacing.md,
    fontWeight: '600',
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  tag: {
    marginRight: spacing.sm,
    marginBottom: spacing.xs,
  },
  description: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    lineHeight: 22,
  },
  fab: {
    position: 'absolute',
    margin: spacing.md,
    right: 0,
    bottom: 0,
  },
});