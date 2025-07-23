/**
 * Asset Card Component
 * 
 * Grid view card for displaying asset thumbnails with
 * metadata overlay and interactive elements.
 */

import React from 'react';
import {View, StyleSheet, TouchableOpacity, Image} from 'react-native';
import {Text, Card, IconButton, Chip} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {Asset, AssetType} from '@/types';
import {colors, spacing, typography, borderRadius} from '@/constants/theme';
import {formatFileSize, formatDuration} from '@/utils/formatters';

interface AssetCardProps {
  asset: Asset;
  size: number;
  onPress: () => void;
  onLongPress?: () => void;
  selected?: boolean;
  showCheckbox?: boolean;
}

export const AssetCard: React.FC<AssetCardProps> = ({
  asset,
  size,
  onPress,
  onLongPress,
  selected = false,
  showCheckbox = false,
}) => {
  const getAssetTypeIcon = (type: AssetType): string => {
    switch (type) {
      case 'image':
        return 'image';
      case 'video':
        return 'play-circle';
      case 'audio':
        return 'audiotrack';
      case 'document':
        return 'description';
      case 'archive':
        return 'archive';
      default:
        return 'file-copy';
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

  const getThumbnailUrl = (): string | null => {
    if (asset.thumbnails && asset.thumbnails.length > 0) {
      // Find medium size thumbnail first, fallback to any size
      const mediumThumb = asset.thumbnails.find(t => t.size === 'medium');
      const anyThumb = asset.thumbnails[0];
      return (mediumThumb || anyThumb)?.url || null;
    }
    return null;
  };

  const renderThumbnail = () => {
    const thumbnailUrl = getThumbnailUrl();

    if (thumbnailUrl) {
      return (
        <Image
          source={{uri: thumbnailUrl}}
          style={styles.thumbnail}
          resizeMode="cover"
        />
      );
    }

    // Fallback icon when no thumbnail
    return (
      <View style={[styles.thumbnailPlaceholder, {backgroundColor: getAssetTypeColor(asset.asset_type)}]}>
        <Icon
          name={getAssetTypeIcon(asset.asset_type)}
          size={32}
          color={colors.onPrimary}
        />
      </View>
    );
  };

  const renderOverlay = () => (
    <View style={styles.overlay}>
      {/* Top Row */}
      <View style={styles.topRow}>
        {/* Asset Type Badge */}
        <Chip
          mode="flat"
          compact
          textStyle={styles.chipText}
          style={[styles.typeChip, {backgroundColor: getAssetTypeColor(asset.asset_type)}]}>
          {asset.asset_type.toUpperCase()}
        </Chip>

        {/* Selection Checkbox */}
        {showCheckbox && (
          <IconButton
            icon={selected ? 'check-circle' : 'radio-button-unchecked'}
            iconColor={selected ? colors.primary : colors.onPrimary}
            size={20}
            style={styles.checkbox}
          />
        )}

        {/* Favorite Icon */}
        {asset.is_favorite && (
          <Icon
            name="favorite"
            size={16}
            color={colors.secondary}
            style={styles.favoriteIcon}
          />
        )}
      </View>

      {/* Bottom Row */}
      <View style={styles.bottomRow}>
        {/* Duration for video/audio */}
        {(asset.asset_type === 'video' || asset.asset_type === 'audio') && asset.metadata.duration && (
          <View style={styles.durationContainer}>
            <Icon name="schedule" size={12} color={colors.onPrimary} />
            <Text style={styles.durationText}>
              {formatDuration(asset.metadata.duration)}
            </Text>
          </View>
        )}

        {/* Resolution for images/videos */}
        {(asset.asset_type === 'image' || asset.asset_type === 'video') &&
          asset.metadata.width &&
          asset.metadata.height && (
            <View style={styles.resolutionContainer}>
              <Text style={styles.resolutionText}>
                {asset.metadata.width}×{asset.metadata.height}
              </Text>
            </View>
          )}

        {/* Upload Progress */}
        {asset.upload_progress !== undefined && asset.upload_progress < 100 && (
          <View style={styles.progressContainer}>
            <View style={[styles.progressBar, {width: `${asset.upload_progress}%`}]} />
            <Text style={styles.progressText}>{asset.upload_progress}%</Text>
          </View>
        )}
      </View>
    </View>
  );

  const renderFooter = () => (
    <View style={styles.footer}>
      <Text style={styles.assetName} numberOfLines={2}>
        {asset.name || asset.file_name}
      </Text>
      <View style={styles.footerRow}>
        <Text style={styles.fileSize}>{formatFileSize(asset.file_size)}</Text>
        <Text style={styles.uploadDate}>
          {new Date(asset.created_at).toLocaleDateString()}
        </Text>
      </View>
    </View>
  );

  return (
    <TouchableOpacity
      onPress={onPress}
      onLongPress={onLongPress}
      activeOpacity={0.8}
      style={[styles.container, {width: size}, selected && styles.selectedContainer]}>
      <Card style={[styles.card, selected && styles.selectedCard]}>
        {/* Thumbnail Container */}
        <View style={[styles.thumbnailContainer, {height: size * 0.75}]}>
          {renderThumbnail()}
          {renderOverlay()}
        </View>

        {/* Footer */}
        {renderFooter()}
      </Card>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: spacing.sm,
  },
  selectedContainer: {
    transform: [{scale: 0.95}],
  },
  card: {
    overflow: 'hidden',
  },
  selectedCard: {
    borderWidth: 2,
    borderColor: colors.primary,
  },
  thumbnailContainer: {
    position: 'relative',
    overflow: 'hidden',
  },
  thumbnail: {
    width: '100%',
    height: '100%',
  },
  thumbnailPlaceholder: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'space-between',
    padding: spacing.xs,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  typeChip: {
    height: 20,
  },
  chipText: {
    ...typography.labelSmall,
    color: colors.onPrimary,
    fontSize: 8,
  },
  checkbox: {
    margin: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderRadius: borderRadius.full,
  },
  favoriteIcon: {
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderRadius: borderRadius.full,
    padding: 2,
  },
  bottomRow: {
    alignItems: 'flex-end',
  },
  durationContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: spacing.xs,
    paddingVertical: 2,
    borderRadius: borderRadius.sm,
    marginBottom: spacing.xs,
  },
  durationText: {
    ...typography.labelSmall,
    color: colors.onPrimary,
    marginLeft: 2,
    fontSize: 10,
  },
  resolutionContainer: {
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: spacing.xs,
    paddingVertical: 2,
    borderRadius: borderRadius.sm,
    marginBottom: spacing.xs,
  },
  resolutionText: {
    ...typography.labelSmall,
    color: colors.onPrimary,
    fontSize: 9,
  },
  progressContainer: {
    position: 'relative',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    borderRadius: borderRadius.sm,
    height: 16,
    alignSelf: 'stretch',
    justifyContent: 'center',
    alignItems: 'center',
  },
  progressBar: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    backgroundColor: colors.primary,
    borderRadius: borderRadius.sm,
  },
  progressText: {
    ...typography.labelSmall,
    color: colors.onPrimary,
    fontSize: 9,
  },
  footer: {
    padding: spacing.sm,
  },
  assetName: {
    ...typography.bodySmall,
    color: colors.onSurface,
    fontWeight: '500',
    marginBottom: spacing.xs,
  },
  footerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  fileSize: {
    ...typography.labelSmall,
    color: colors.gray600,
    fontSize: 10,
  },
  uploadDate: {
    ...typography.labelSmall,
    color: colors.gray600,
    fontSize: 10,
  },
});