/**
 * Asset List Item Component
 * 
 * List view item for displaying assets in a horizontal
 * layout with thumbnail, metadata, and actions.
 */

import React from 'react';
import {View, StyleSheet, TouchableOpacity, Image} from 'react-native';
import {Text, IconButton, Chip} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {Asset, AssetType} from '@/types';
import {colors, spacing, typography, borderRadius} from '@/constants/theme';
import {formatFileSize, formatDuration, formatDate} from '@/utils/formatters';

interface AssetListItemProps {
  asset: Asset;
  onPress: () => void;
  onLongPress?: () => void;
  onMenuPress?: () => void;
  selected?: boolean;
  showCheckbox?: boolean;
}

export const AssetListItem: React.FC<AssetListItemProps> = ({
  asset,
  onPress,
  onLongPress,
  onMenuPress,
  selected = false,
  showCheckbox = false,
}) => {
  const getAssetTypeIcon = (type: AssetType): string => {
    switch (type) {
      case 'image':
        return 'image';
      case 'video':
        return 'play-circle-filled';
      case 'audio':
        return 'audiotrack';
      case 'document':
        return 'description';
      case 'archive':
        return 'archive';
      default:
        return 'insert-drive-file';
    }
  };

  const getAssetTypeColor = (type: AssetType): string => {
    switch (type) {
      case 'image':
        return colors.image;
      case 'video':
        return colors.video;
      case 'audio':
        return colors.audio;
      case 'document':
        return colors.document;
      default:
        return colors.gray500;
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'processing':
        return colors.processing;
      case 'ready':
        return colors.approved;
      case 'failed':
        return colors.rejected;
      case 'uploading':
        return colors.warning;
      default:
        return colors.gray500;
    }
  };

  const getThumbnailUrl = (): string | null => {
    if (asset.thumbnails && asset.thumbnails.length > 0) {
      // Find small size thumbnail for list view
      const smallThumb = asset.thumbnails.find(t => t.size === 'small');
      const anyThumb = asset.thumbnails[0];
      return (smallThumb || anyThumb)?.url || null;
    }
    return null;
  };

  const renderThumbnail = () => {
    const thumbnailUrl = getThumbnailUrl();

    if (thumbnailUrl) {
      return (
        <View style={styles.thumbnailContainer}>
          <Image
            source={{uri: thumbnailUrl}}
            style={styles.thumbnail}
            resizeMode="cover"
          />
          {/* Type overlay for videos/audio */}
          {(asset.asset_type === 'video' || asset.asset_type === 'audio') && (
            <View style={styles.thumbnailOverlay}>
              <Icon
                name={getAssetTypeIcon(asset.asset_type)}
                size={20}
                color={colors.onPrimary}
              />
            </View>
          )}
        </View>
      );
    }

    // Fallback icon when no thumbnail
    return (
      <View style={[styles.thumbnailPlaceholder, {backgroundColor: getAssetTypeColor(asset.asset_type)}]}>
        <Icon
          name={getAssetTypeIcon(asset.asset_type)}
          size={24}
          color={colors.onPrimary}
        />
      </View>
    );
  };

  const renderMetadata = () => {
    const metadata = [];

    // File size
    metadata.push(formatFileSize(asset.file_size));

    // Duration for video/audio
    if ((asset.asset_type === 'video' || asset.asset_type === 'audio') && asset.metadata.duration) {
      metadata.push(formatDuration(asset.metadata.duration));
    }

    // Resolution for images/videos
    if ((asset.asset_type === 'image' || asset.asset_type === 'video') &&
        asset.metadata.width && asset.metadata.height) {
      metadata.push(`${asset.metadata.width}×${asset.metadata.height}`);
    }

    return metadata.join(' • ');
  };

  return (
    <TouchableOpacity
      onPress={onPress}
      onLongPress={onLongPress}
      activeOpacity={0.8}
      style={[styles.container, selected && styles.selectedContainer]}>
      
      {/* Selection Checkbox */}
      {showCheckbox && (
        <IconButton
          icon={selected ? 'check-circle' : 'radio-button-unchecked'}
          iconColor={selected ? colors.primary : colors.gray400}
          size={24}
          style={styles.checkbox}
        />
      )}

      {/* Thumbnail */}
      {renderThumbnail()}

      {/* Content */}
      <View style={styles.content}>
        {/* Header Row */}
        <View style={styles.headerRow}>
          <Text style={styles.assetName} numberOfLines={1}>
            {asset.name || asset.file_name}
          </Text>
          <View style={styles.headerIcons}>
            {asset.is_favorite && (
              <Icon
                name="favorite"
                size={16}
                color={colors.secondary}
                style={styles.favoriteIcon}
              />
            )}
            {asset.status !== 'ready' && (
              <View style={[styles.statusDot, {backgroundColor: getStatusColor(asset.status)}]} />
            )}
          </View>
        </View>

        {/* Metadata Row */}
        <Text style={styles.metadata} numberOfLines={1}>
          {renderMetadata()}
        </Text>

        {/* Footer Row */}
        <View style={styles.footerRow}>
          <View style={styles.leftFooter}>
            <Chip
              mode="flat"
              compact
              textStyle={styles.chipText}
              style={[styles.typeChip, {backgroundColor: getAssetTypeColor(asset.asset_type)}]}>
              {asset.asset_type.toUpperCase()}
            </Chip>
            <Text style={styles.uploadDate}>
              {formatDate(asset.created_at)}
            </Text>
          </View>

          {/* Upload Progress */}
          {asset.upload_progress !== undefined && asset.upload_progress < 100 && (
            <View style={styles.progressContainer}>
              <View style={styles.progressTrack}>
                <View style={[styles.progressBar, {width: `${asset.upload_progress}%`}]} />
              </View>
              <Text style={styles.progressText}>{asset.upload_progress}%</Text>
            </View>
          )}
        </View>
      </View>

      {/* Menu Button */}
      <IconButton
        icon="more-vert"
        iconColor={colors.gray600}
        size={20}
        onPress={onMenuPress}
        style={styles.menuButton}
      />
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: borderRadius.md,
    marginHorizontal: spacing.md,
  },
  selectedContainer: {
    backgroundColor: colors.primaryContainer || colors.gray100,
    borderWidth: 1,
    borderColor: colors.primary,
  },
  checkbox: {
    marginRight: spacing.sm,
  },
  thumbnailContainer: {
    position: 'relative',
    width: 56,
    height: 56,
    borderRadius: borderRadius.md,
    overflow: 'hidden',
    marginRight: spacing.md,
  },
  thumbnail: {
    width: '100%',
    height: '100%',
  },
  thumbnailOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  thumbnailPlaceholder: {
    width: 56,
    height: 56,
    borderRadius: borderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing.md,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  assetName: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    fontWeight: '500',
    flex: 1,
    marginRight: spacing.sm,
  },
  headerIcons: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  favoriteIcon: {
    marginLeft: spacing.xs,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginLeft: spacing.xs,
  },
  metadata: {
    ...typography.bodySmall,
    color: colors.gray600,
    marginBottom: spacing.xs,
  },
  footerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  leftFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  typeChip: {
    height: 20,
    marginRight: spacing.sm,
  },
  chipText: {
    ...typography.labelSmall,
    color: colors.onPrimary,
    fontSize: 8,
  },
  uploadDate: {
    ...typography.labelSmall,
    color: colors.gray500,
    fontSize: 10,
  },
  progressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  progressTrack: {
    width: 60,
    height: 4,
    backgroundColor: colors.gray200,
    borderRadius: 2,
    marginRight: spacing.xs,
  },
  progressBar: {
    height: '100%',
    backgroundColor: colors.primary,
    borderRadius: 2,
  },
  progressText: {
    ...typography.labelSmall,
    color: colors.gray600,
    fontSize: 10,
    minWidth: 30,
    textAlign: 'right',
  },
  menuButton: {
    marginLeft: spacing.sm,
  },
});