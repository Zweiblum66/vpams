import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardMedia,
  Typography,
  IconButton,
  Chip,
  Tooltip,
  Menu,
  MenuItem,
  Divider,
  alpha,
} from '@mui/material';
import {
  DragIndicator,
  PlayArrow,
  MoreVert,
  Edit,
  ContentCopy,
  Delete,
  Movie,
  AudioFile,
  Image,
  Description,
  Schedule,
  Straighten,
} from '@mui/icons-material';
import { ShotlistItem } from '../../types';

interface ShotItemProps {
  item: ShotlistItem;
  index: number;
  isSelected?: boolean;
  isPlaying?: boolean;
  isDragging?: boolean;
  readOnly?: boolean;
  onPlay?: (item: ShotlistItem) => void;
  onEdit?: (item: ShotlistItem) => void;
  onDuplicate?: (item: ShotlistItem) => void;
  onDelete?: (item: ShotlistItem) => void;
  onClick?: (item: ShotlistItem) => void;
  dragHandleProps?: any;
}

const ShotItem: React.FC<ShotItemProps> = ({
  item,
  index,
  isSelected = false,
  isPlaying = false,
  isDragging = false,
  readOnly = false,
  onPlay,
  onEdit,
  onDuplicate,
  onDelete,
  onClick,
  dragHandleProps,
}) => {
  const [contextMenuAnchor, setContextMenuAnchor] = useState<null | HTMLElement>(null);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatTimecode = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const frames = Math.floor((seconds % 1) * 25); // Assuming 25fps
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`;
  };

  const getAssetTypeIcon = (type: string) => {
    switch (type) {
      case 'video':
        return <Movie fontSize="small" />;
      case 'audio':
        return <AudioFile fontSize="small" />;
      case 'image':
        return <Image fontSize="small" />;
      case 'document':
        return <Description fontSize="small" />;
      default:
        return <Description fontSize="small" />;
    }
  };

  const handleContextMenu = (event: React.MouseEvent<HTMLElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setContextMenuAnchor(event.currentTarget);
  };

  const handleContextMenuClose = () => {
    setContextMenuAnchor(null);
  };

  const handleMenuAction = (action: () => void) => {
    action();
    handleContextMenuClose();
  };

  return (
    <>
      <Card
        sx={{
          mb: 1,
          opacity: isDragging ? 0.8 : 1,
          backgroundColor: isSelected 
            ? alpha('#1976d2', 0.1) 
            : 'background.paper',
          border: item.color ? `2px solid ${item.color}` : undefined,
          borderLeft: isPlaying ? '4px solid #4caf50' : undefined,
          cursor: 'pointer',
          transition: 'all 0.2s',
          '&:hover': {
            elevation: 2,
            backgroundColor: isSelected 
              ? alpha('#1976d2', 0.15) 
              : alpha('#000', 0.02),
          },
        }}
        onClick={() => onClick?.(item)}
        onContextMenu={readOnly ? undefined : handleContextMenu}
      >
        <CardContent sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {/* Drag Handle */}
            {!readOnly && (
              <Box {...dragHandleProps} sx={{ cursor: 'grab' }}>
                <DragIndicator sx={{ color: 'text.secondary' }} />
              </Box>
            )}
            
            {/* Shot Number */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="h6" sx={{ minWidth: 30, fontWeight: 'bold' }}>
                {item.order}
              </Typography>
              {getAssetTypeIcon(item.asset.asset_type)}
            </Box>
            
            {/* Thumbnail */}
            {item.asset.thumbnail_path && (
              <Box sx={{ position: 'relative' }}>
                <CardMedia
                  component="img"
                  sx={{
                    width: 80,
                    height: 45,
                    objectFit: 'cover',
                    borderRadius: 1,
                  }}
                  image={item.asset.thumbnail_path}
                  alt={item.asset.name}
                />
                {onPlay && (
                  <IconButton
                    size="small"
                    sx={{
                      position: 'absolute',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)',
                      backgroundColor: 'rgba(0, 0, 0, 0.7)',
                      color: 'white',
                      '&:hover': {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                      },
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onPlay(item);
                    }}
                  >
                    <PlayArrow fontSize="small" />
                  </IconButton>
                )}
              </Box>
            )}
            
            {/* Content */}
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 'medium' }} noWrap>
                {item.title || item.asset.name}
              </Typography>
              <Typography variant="body2" color="text.secondary" noWrap>
                {item.asset.name}
              </Typography>
              {item.description && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }} noWrap>
                  {item.description}
                </Typography>
              )}
            </Box>
            
            {/* Timing Information */}
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <Schedule fontSize="small" color="disabled" />
                <Typography variant="body2" color="text.secondary">
                  {formatDuration(item.duration)}
                </Typography>
              </Box>
              <Chip
                label={`${formatTimecode(item.in_point)} - ${formatTimecode(item.out_point)}`}
                size="small"
                variant="outlined"
                sx={{ fontSize: '0.7rem' }}
              />
            </Box>
            
            {/* Actions */}
            {!readOnly && (
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  handleContextMenu(e);
                }}
              >
                <MoreVert />
              </IconButton>
            )}
          </Box>
          
          {/* Notes */}
          {item.notes && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1, fontStyle: 'italic' }}>
              {item.notes}
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* Context Menu */}
      <Menu
        anchorEl={contextMenuAnchor}
        open={Boolean(contextMenuAnchor)}
        onClose={handleContextMenuClose}
      >
        {onEdit && (
          <MenuItem onClick={() => handleMenuAction(() => onEdit(item))}>
            <Edit sx={{ mr: 1 }} />
            Edit
          </MenuItem>
        )}
        {onDuplicate && (
          <MenuItem onClick={() => handleMenuAction(() => onDuplicate(item))}>
            <ContentCopy sx={{ mr: 1 }} />
            Duplicate
          </MenuItem>
        )}
        {onPlay && (
          <MenuItem onClick={() => handleMenuAction(() => onPlay(item))}>
            <PlayArrow sx={{ mr: 1 }} />
            Play
          </MenuItem>
        )}
        {(onEdit || onDuplicate || onPlay) && onDelete && <Divider />}
        {onDelete && (
          <MenuItem 
            onClick={() => handleMenuAction(() => onDelete(item))}
            sx={{ color: 'error.main' }}
          >
            <Delete sx={{ mr: 1 }} />
            Delete
          </MenuItem>
        )}
      </Menu>
    </>
  );
};

export default ShotItem;