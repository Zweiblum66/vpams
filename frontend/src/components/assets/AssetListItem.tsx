import React, { useState } from 'react';
import {
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Menu,
  MenuItem,
  Chip,
  Box,
  Checkbox,
  Typography,
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
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';

import { Asset, AssetType } from '../../types/asset';
import { formatFileSize } from '../../utils/formatters';

interface AssetListItemProps {
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

const AssetListItem: React.FC<AssetListItemProps> = ({
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
    const iconProps = { sx: { fontSize: 40, color: 'text.secondary' } };
    
    switch (asset.type) {
      case AssetType.VIDEO:
        return <VideoIcon {...iconProps} />;
      case AssetType.AUDIO:
        return <AudioIcon {...iconProps} />;
      case AssetType.IMAGE:
        return <ImageIcon {...iconProps} />;
      case AssetType.DOCUMENT:
        return <DocumentIcon {...iconProps} />;
      default:
        return <FolderIcon {...iconProps} />;
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
      <ListItem>
        <ListItemIcon>
          <Skeleton variant="circular" width={40} height={40} />
        </ListItemIcon>
        <ListItemText
          primary={<Skeleton variant="text" width="60%" />}
          secondary={<Skeleton variant="text" width="40%" />}
        />
        <ListItemSecondaryAction>
          <Skeleton variant="text" width={100} />
        </ListItemSecondaryAction>
      </ListItem>
    );
  }

  return (
    <>
      <ListItem
        button
        selected={selected}
        onClick={() => onClick?.(asset)}
        sx={{
          '&:hover': {
            backgroundColor: 'action.hover',
          },
          ...(selected && {
            backgroundColor: 'action.selected',
          }),
        }}
      >
        {onSelect && (
          <Checkbox
            checked={selected}
            onChange={handleSelect}
            onClick={(e) => e.stopPropagation()}
            sx={{ mr: 1 }}
          />
        )}

        <ListItemIcon>
          {asset.thumbnailUrl ? (
            <Box
              component="img"
              src={asset.thumbnailUrl}
              alt={asset.name}
              sx={{
                width: 40,
                height: 40,
                objectFit: 'cover',
                borderRadius: 1,
              }}
            />
          ) : (
            getAssetIcon()
          )}
        </ListItemIcon>

        <ListItemText
          primary={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {asset.name}
              </Typography>
              {asset.duration && (
                <Typography variant="caption" color="text.secondary">
                  ({formatDuration(asset.duration)})
                </Typography>
              )}
            </Box>
          }
          secondary={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
              <Typography variant="caption" color="text.secondary">
                {formatFileSize(asset.fileSize)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                •
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {asset.metadata.format || asset.type.toUpperCase()}
              </Typography>
              {asset.dimensions && (
                <>
                  <Typography variant="caption" color="text.secondary">
                    •
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {asset.dimensions.width}×{asset.dimensions.height}
                  </Typography>
                </>
              )}
              <Typography variant="caption" color="text.secondary">
                •
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {formatDistanceToNow(new Date(asset.createdAt), { addSuffix: true })}
              </Typography>
            </Box>
          }
        />

        <ListItemSecondaryAction>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {asset.tags.length > 0 && (
              <Box sx={{ display: 'flex', gap: 0.5 }}>
                {asset.tags.slice(0, 2).map((tag) => (
                  <Chip key={tag} label={tag} size="small" />
                ))}
                {asset.tags.length > 2 && (
                  <Chip label={`+${asset.tags.length - 2}`} size="small" />
                )}
              </Box>
            )}
            
            <IconButton edge="end" onClick={handleMenuOpen}>
              <MoreVertIcon />
            </IconButton>
          </Box>
        </ListItemSecondaryAction>
      </ListItem>

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
    </>
  );
};

export default AssetListItem;