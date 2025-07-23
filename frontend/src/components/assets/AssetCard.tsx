import React, { useState } from 'react';
import {
  Card,
  CardMedia,
  CardContent,
  CardActions,
  Typography,
  IconButton,
  Menu,
  MenuItem,
  Chip,
  Box,
  Checkbox,
  Tooltip,
  Skeleton,
} from '@mui/material';
import {
  MoreVert as MoreVertIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  VideoLibrary as VideoIcon,
  AudioFile as AudioIcon,
  Image as ImageIcon,
  Description as DocumentIcon,
  Folder as FolderIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ProcessingIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';

import { Asset, AssetType, AssetStatus } from '../../types/asset';
import { formatFileSize } from '../../utils/formatters';

interface AssetCardProps {
  asset: Asset;
  selected?: boolean;
  onSelect?: (assetId: string, selected: boolean) => void;
  onClick?: (asset: Asset) => void;
  onEdit?: (asset: Asset) => void;
  onDelete?: (asset: Asset) => void;
  onDownload?: (asset: Asset) => void;
  onShare?: (asset: Asset) => void;
  loading?: boolean;
  highlight?: string[];
}

const AssetCard: React.FC<AssetCardProps> = ({
  asset,
  selected = false,
  onSelect,
  onClick,
  onEdit,
  onDelete,
  onDownload,
  onShare,
  loading = false,
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    event.stopPropagation();
    onSelect?.(asset.id, event.target.checked);
  };

  const handleAction = (action: () => void) => {
    handleMenuClose();
    action();
  };

  const getAssetIcon = () => {
    switch (asset.type) {
      case AssetType.VIDEO:
        return <VideoIcon />;
      case AssetType.AUDIO:
        return <AudioIcon />;
      case AssetType.IMAGE:
        return <ImageIcon />;
      case AssetType.DOCUMENT:
        return <DocumentIcon />;
      default:
        return <FolderIcon />;
    }
  };

  const getStatusIcon = () => {
    switch (asset.status) {
      case AssetStatus.READY:
        return <CheckCircleIcon fontSize="small" color="success" />;
      case AssetStatus.ERROR:
        return <ErrorIcon fontSize="small" color="error" />;
      case AssetStatus.PROCESSING:
      case AssetStatus.UPLOADING:
        return <ProcessingIcon fontSize="small" color="warning" />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (asset.status) {
      case AssetStatus.READY:
        return 'success';
      case AssetStatus.ERROR:
        return 'error';
      case AssetStatus.PROCESSING:
      case AssetStatus.UPLOADING:
        return 'warning';
      case AssetStatus.ARCHIVED:
        return 'default';
      default:
        return 'default';
    }
  };

  const formatDuration = (seconds?: number): string => {
    if (!seconds) return '';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Skeleton variant="rectangular" height={200} />
        <CardContent>
          <Skeleton variant="text" width="80%" />
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="text" width="40%" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s',
        ...(selected && {
          borderColor: 'primary.main',
          borderWidth: 2,
          borderStyle: 'solid',
        }),
        '&:hover': {
          boxShadow: 4,
          transform: 'translateY(-2px)',
        },
      }}
      onClick={() => onClick?.(asset)}
    >
      {/* Selection Checkbox */}
      {onSelect && (
        <Checkbox
          checked={selected}
          onChange={handleSelect}
          sx={{
            position: 'absolute',
            top: 8,
            left: 8,
            zIndex: 1,
            backgroundColor: 'rgba(255, 255, 255, 0.8)',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.9)',
            },
          }}
          onClick={(e) => e.stopPropagation()}
        />
      )}

      {/* More Actions Menu */}
      <IconButton
        sx={{
          position: 'absolute',
          top: 8,
          right: 8,
          zIndex: 1,
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          '&:hover': {
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
          },
        }}
        onClick={handleMenuOpen}
      >
        <MoreVertIcon />
      </IconButton>

      {/* Thumbnail/Preview */}
      <CardMedia
        sx={{
          height: 200,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'grey.100',
          position: 'relative',
        }}
      >
        {asset.thumbnailUrl ? (
          <Box
            component="img"
            src={asset.thumbnailUrl}
            alt={asset.name}
            sx={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        ) : (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 1,
            }}
          >
            {React.cloneElement(getAssetIcon(), {
              sx: { fontSize: 48, color: 'text.secondary' },
            })}
            <Typography variant="caption" color="text.secondary">
              {asset.metadata.format || asset.type.toUpperCase()}
            </Typography>
          </Box>
        )}

        {/* Duration for video/audio */}
        {asset.duration && (
          <Typography
            variant="caption"
            sx={{
              position: 'absolute',
              bottom: 4,
              right: 4,
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              color: 'white',
              px: 1,
              py: 0.5,
              borderRadius: 1,
            }}
          >
            {formatDuration(asset.duration)}
          </Typography>
        )}
      </CardMedia>

      {/* Content */}
      <CardContent sx={{ flexGrow: 1, pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
          <Typography
            variant="subtitle2"
            component="h3"
            sx={{
              flexGrow: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
            }}
            title={asset.name}
          >
            {asset.name}
          </Typography>
          {getStatusIcon()}
        </Box>

        <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
          <Chip
            label={asset.status}
            size="small"
            color={getStatusColor() as any}
            sx={{ textTransform: 'capitalize' }}
          />
          <Chip
            label={formatFileSize(asset.fileSize)}
            size="small"
            variant="outlined"
          />
          {asset.dimensions && (
            <Chip
              label={`${asset.dimensions.width}×${asset.dimensions.height}`}
              size="small"
              variant="outlined"
            />
          )}
        </Box>

        <Typography variant="caption" color="text.secondary">
          {formatDistanceToNow(new Date(asset.createdAt), { addSuffix: true })}
        </Typography>

        {asset.tags.length > 0 && (
          <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {asset.tags.slice(0, 3).map((tag) => (
              <Chip key={tag} label={tag} size="small" sx={{ fontSize: '0.7rem' }} />
            ))}
            {asset.tags.length > 3 && (
              <Chip
                label={`+${asset.tags.length - 3}`}
                size="small"
                sx={{ fontSize: '0.7rem' }}
              />
            )}
          </Box>
        )}
      </CardContent>

      {/* Actions Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        onClick={(e) => e.stopPropagation()}
      >
        {asset.permissions.canDownload && onDownload && (
          <MenuItem onClick={() => handleAction(() => onDownload(asset))}>
            <DownloadIcon sx={{ mr: 1 }} fontSize="small" />
            Download
          </MenuItem>
        )}
        {asset.permissions.canShare && onShare && (
          <MenuItem onClick={() => handleAction(() => onShare(asset))}>
            <ShareIcon sx={{ mr: 1 }} fontSize="small" />
            Share
          </MenuItem>
        )}
        {asset.permissions.canEdit && onEdit && (
          <MenuItem onClick={() => handleAction(() => onEdit(asset))}>
            <EditIcon sx={{ mr: 1 }} fontSize="small" />
            Edit
          </MenuItem>
        )}
        {asset.permissions.canDelete && onDelete && (
          <MenuItem
            onClick={() => handleAction(() => onDelete(asset))}
            sx={{ color: 'error.main' }}
          >
            <DeleteIcon sx={{ mr: 1 }} fontSize="small" />
            Delete
          </MenuItem>
        )}
      </Menu>
    </Card>
  );
};

export default AssetCard;