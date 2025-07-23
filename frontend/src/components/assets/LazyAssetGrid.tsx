import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardMedia,
  CardContent,
  Typography,
  Skeleton,
  IconButton,
  Chip,
  Tooltip,
} from '@mui/material';
import {
  PlayArrow,
  Image as ImageIcon,
  AudioFile,
  Description,
  Folder,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';

import { useLazyLoad, LazyImage } from '../../utils/lazyLoading';
import { Asset } from '../../types';
import { formatFileSize } from '../../utils/format';

interface LazyAssetGridProps {
  assets: Asset[];
  onLoadMore?: () => void;
  hasMore?: boolean;
  loading?: boolean;
  onAssetClick?: (asset: Asset) => void;
  selectedAssets?: string[];
  onAssetSelect?: (assetId: string, selected: boolean) => void;
  viewMode?: 'grid' | 'list';
}

/**
 * Asset card component with lazy loading
 */
const LazyAssetCard: React.FC<{
  asset: Asset;
  onClick?: () => void;
  selected?: boolean;
  onSelect?: (selected: boolean) => void;
}> = ({ asset, onClick, selected, onSelect }) => {
  const [imageLoaded, setImageLoaded] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  // Use intersection observer to detect when card is visible
  useLazyLoad(
    cardRef,
    () => setIsVisible(true),
    { rootMargin: '100px' }
  );

  const getAssetIcon = () => {
    switch (asset.type) {
      case 'video':
        return <PlayArrow />;
      case 'image':
        return <ImageIcon />;
      case 'audio':
        return <AudioFile />;
      case 'document':
        return <Description />;
      default:
        return <Folder />;
    }
  };

  const getThumbnailUrl = () => {
    if (asset.thumbnails?.medium) {
      return asset.thumbnails.medium;
    }
    if (asset.thumbnails?.small) {
      return asset.thumbnails.small;
    }
    return null;
  };

  return (
    <Card
      ref={cardRef}
      sx={{
        cursor: 'pointer',
        transition: 'all 0.2s',
        border: selected ? '2px solid' : '1px solid',
        borderColor: selected ? 'primary.main' : 'divider',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: 3,
        },
      }}
      onClick={onClick}
    >
      {isVisible ? (
        <>
          <Box sx={{ position: 'relative', paddingTop: '56.25%' }}>
            {getThumbnailUrl() ? (
              <LazyImage
                src={getThumbnailUrl()!}
                alt={asset.name}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                }}
                onLoad={() => setImageLoaded(true)}
              />
            ) : (
              <Box
                sx={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: 'grey.200',
                  color: 'grey.600',
                }}
              >
                {getAssetIcon()}
              </Box>
            )}
            
            {/* Asset type overlay */}
            <Chip
              icon={getAssetIcon()}
              label={asset.type}
              size="small"
              sx={{
                position: 'absolute',
                top: 8,
                left: 8,
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                color: 'white',
              }}
            />
            
            {/* Duration for videos */}
            {asset.type === 'video' && asset.metadata?.duration && (
              <Chip
                label={formatDuration(asset.metadata.duration)}
                size="small"
                sx={{
                  position: 'absolute',
                  bottom: 8,
                  right: 8,
                  backgroundColor: 'rgba(0, 0, 0, 0.7)',
                  color: 'white',
                }}
              />
            )}
          </Box>
          
          <CardContent sx={{ p: 2 }}>
            <Tooltip title={asset.name}>
              <Typography
                variant="body2"
                noWrap
                sx={{ fontWeight: 500, mb: 0.5 }}
              >
                {asset.name}
              </Typography>
            </Tooltip>
            
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="caption" color="text.secondary">
                {formatFileSize(asset.size)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {formatDistanceToNow(new Date(asset.createdAt), { addSuffix: true })}
              </Typography>
            </Box>
          </CardContent>
        </>
      ) : (
        // Skeleton while not visible
        <>
          <Skeleton variant="rectangular" sx={{ paddingTop: '56.25%' }} />
          <CardContent>
            <Skeleton variant="text" />
            <Skeleton variant="text" width="60%" />
          </CardContent>
        </>
      )}
    </Card>
  );
};

/**
 * Lazy loading asset grid component
 */
export const LazyAssetGrid: React.FC<LazyAssetGridProps> = ({
  assets,
  onLoadMore,
  hasMore = false,
  loading = false,
  onAssetClick,
  selectedAssets = [],
  onAssetSelect,
  viewMode = 'grid',
}) => {
  const navigate = useNavigate();
  const loadMoreRef = useRef<HTMLDivElement>(null);
  
  // Infinite scroll trigger
  useLazyLoad(
    loadMoreRef,
    () => {
      if (hasMore && !loading && onLoadMore) {
        onLoadMore();
      }
    },
    { rootMargin: '200px' }
  );

  const handleAssetClick = useCallback((asset: Asset) => {
    if (onAssetClick) {
      onAssetClick(asset);
    } else {
      navigate(`/assets/${asset.id}`);
    }
  }, [navigate, onAssetClick]);

  const handleAssetSelect = useCallback((assetId: string, selected: boolean) => {
    if (onAssetSelect) {
      onAssetSelect(assetId, selected);
    }
  }, [onAssetSelect]);

  return (
    <Box>
      <Grid container spacing={2}>
        {assets.map((asset) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={asset.id}>
            <LazyAssetCard
              asset={asset}
              onClick={() => handleAssetClick(asset)}
              selected={selectedAssets.includes(asset.id)}
              onSelect={(selected) => handleAssetSelect(asset.id, selected)}
            />
          </Grid>
        ))}
      </Grid>
      
      {/* Loading indicator */}
      {loading && (
        <Grid container spacing={2} sx={{ mt: 2 }}>
          {Array.from({ length: 8 }).map((_, index) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={`skeleton-${index}`}>
              <Card>
                <Skeleton variant="rectangular" sx={{ paddingTop: '56.25%' }} />
                <CardContent>
                  <Skeleton variant="text" />
                  <Skeleton variant="text" width="60%" />
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
      
      {/* Infinite scroll trigger */}
      {hasMore && !loading && (
        <Box ref={loadMoreRef} sx={{ height: 1, mt: 4 }} />
      )}
    </Box>
  );
};

/**
 * Format duration in seconds to human readable format
 */
function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

export default LazyAssetGrid;