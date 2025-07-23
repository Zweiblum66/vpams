import React, { useState, useRef } from 'react';
import {
  Card,
  CardContent,
  CardMedia,
  CardActions,
  Typography,
  IconButton,
  Checkbox,
  Box,
  Chip,
  Skeleton,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Fade,
  Badge,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  MoreVert as MoreVertIcon,
  PlayArrow as PlayIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Info as InfoIcon,
  ContentCopy as DuplicateIcon,
  DriveFileMove as MoveIcon,
  LocalOffer as TagIcon,
  VideoLibrary as VideoIcon,
  Image as ImageIcon,
  AudioFile as AudioIcon,
  InsertDriveFile as FileIcon,
  Lock as LockedIcon,
  Schedule as ProcessingIcon,
} from '@mui/icons-material';
import { useDrag, useDrop } from 'react-dnd';
import { Asset } from '../../types/asset';
import { formatFileSize, formatDuration } from '../../utils/formatters';

interface DraggableAssetCardProps {
  asset: Asset;
  selected: boolean;
  onSelect: (assetId: string, selected: boolean, event?: React.MouseEvent) => void;
  onClick: (asset: Asset) => void;
  onEdit: (asset: Asset) => void;
  onDelete: (asset: Asset) => void;
  onDownload: (asset: Asset) => void;
  onShare: (asset: Asset) => void;
  onToggleFavorite: (assetId: string) => void;
  isFavorite: boolean;
  thumbnailSize: 'small' | 'medium' | 'large' | 'xlarge';
  showPreviewOnHover: boolean;
  enableDrag: boolean;
}

const DraggableAssetCard: React.FC<DraggableAssetCardProps> = ({
  asset,
  selected,
  onSelect,
  onClick,
  onEdit,
  onDelete,
  onDownload,
  onShare,
  onToggleFavorite,
  isFavorite,
  thumbnailSize,
  showPreviewOnHover,
  enableDrag,
}) => {
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [imageError, setImageError] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [previewPlaying, setPreviewPlaying] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout>();

  const thumbnailSizes = {
    small: { width: 120, height: 90 },
    medium: { width: 200, height: 150 },
    large: { width: 320, height: 240 },
    xlarge: { width: 480, height: 360 },
  };

  const size = thumbnailSizes[thumbnailSize];

  // Drag and drop setup
  const [{ isDragging }, drag, preview] = useDrag({
    type: 'asset',
    item: () => ({
      type: 'asset',
      id: asset.id,
      asset,
    }),
    canDrag: enableDrag,
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const [{ isOver, canDrop }, drop] = useDrop({
    accept: 'asset',
    canDrop: (item: any) => item.id !== asset.id && asset.type === 'folder',
    drop: (item: any) => {
      // Handle drop on folder
      console.log('Dropped on folder:', asset.id, item);
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  });

  // Combine drag and drop refs
  const cardRef = useRef<HTMLDivElement>(null);
  if (enableDrag) {
    drag(drop(cardRef));
  }

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handleSelect = (event: React.MouseEvent) => {
    event.stopPropagation();
    onSelect(asset.id, !selected, event);
  };

  const handleMouseEnter = () => {
    setHovering(true);
    if (showPreviewOnHover && asset.type === 'video' && asset.proxyUrl) {
      hoverTimeoutRef.current = setTimeout(() => {
        setPreviewPlaying(true);
        if (videoRef.current) {
          videoRef.current.play().catch(() => {
            // Ignore autoplay errors
          });
        }
      }, 500);
    }
  };

  const handleMouseLeave = () => {
    setHovering(false);
    setPreviewPlaying(false);
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
  };

  const getAssetIcon = () => {
    switch (asset.type) {
      case 'video':
        return <VideoIcon />;
      case 'image':
        return <ImageIcon />;
      case 'audio':
        return <AudioIcon />;
      default:
        return <FileIcon />;
    }
  };

  const getStatusColor = () => {
    switch (asset.status) {
      case 'ready':
        return 'success';
      case 'processing':
        return 'warning';
      case 'error':
        return 'error';
      case 'archived':
        return 'default';
      default:
        return 'primary';
    }
  };

  const opacity = isDragging ? 0.5 : 1;
  const borderColor = isOver && canDrop ? 'primary.main' : selected ? 'primary.main' : 'transparent';
  const borderWidth = isOver && canDrop ? 2 : selected ? 2 : 0;

  return (
    <Card
      ref={cardRef}
      sx={{
        opacity,
        border: borderWidth,
        borderColor,
        cursor: enableDrag ? 'move' : 'pointer',
        transition: 'all 0.2s',
        transform: hovering ? 'translateY(-2px)' : 'none',
        boxShadow: hovering ? 4 : 1,
        position: 'relative',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={() => onClick(asset)}
    >
      {/* Selection checkbox */}
      <Box
        sx={{
          position: 'absolute',
          top: 8,
          left: 8,
          zIndex: 2,
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          borderRadius: 1,
        }}
      >
        <Checkbox
          checked={selected}
          onChange={handleSelect}
          onClick={handleSelect}
          sx={{ color: 'white', p: 0.5 }}
        />
      </Box>

      {/* Favorite button */}
      <IconButton
        sx={{
          position: 'absolute',
          top: 8,
          right: 8,
          zIndex: 2,
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          color: 'white',
          '&:hover': {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
          },
        }}
        size="small"
        onClick={(e) => {
          e.stopPropagation();
          onToggleFavorite(asset.id);
        }}
      >
        {isFavorite ? <StarIcon fontSize="small" /> : <StarBorderIcon fontSize="small" />}
      </IconButton>

      {/* Thumbnail */}
      <Box sx={{ position: 'relative', paddingTop: `${(size.height / size.width) * 100}%` }}>
        {showPreviewOnHover && previewPlaying && asset.type === 'video' ? (
          <video
            ref={videoRef}
            src={asset.proxyUrl}
            muted
            loop
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        ) : (
          <CardMedia
            component="img"
            image={imageError ? '/placeholder-asset.png' : asset.thumbnailUrl || '/placeholder-asset.png'}
            alt={asset.name}
            onError={() => setImageError(true)}
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        )}

        {/* Asset type overlay */}
        <Box
          sx={{
            position: 'absolute',
            bottom: 8,
            left: 8,
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            color: 'white',
            borderRadius: 1,
            px: 1,
            py: 0.5,
            display: 'flex',
            alignItems: 'center',
            gap: 0.5,
            fontSize: '0.75rem',
          }}
        >
          {getAssetIcon()}
          {asset.type === 'video' && asset.duration && (
            <Typography variant="caption">{formatDuration(asset.duration)}</Typography>
          )}
        </Box>

        {/* Status indicators */}
        {asset.status !== 'ready' && (
          <Box
            sx={{
              position: 'absolute',
              top: 8,
              left: 48,
              display: 'flex',
              gap: 0.5,
            }}
          >
            {asset.status === 'processing' && (
              <Chip
                icon={<ProcessingIcon />}
                label="Processing"
                size="small"
                color="warning"
                sx={{ height: 24 }}
              />
            )}
            {asset.status === 'locked' && (
              <Chip
                icon={<LockedIcon />}
                label="Locked"
                size="small"
                color="default"
                sx={{ height: 24 }}
              />
            )}
          </Box>
        )}
      </Box>

      {/* Content */}
      <CardContent sx={{ flexGrow: 1, py: 1.5, px: 2 }}>
        <Typography
          variant="body2"
          noWrap
          gutterBottom
          sx={{ fontWeight: selected ? 600 : 400 }}
        >
          {asset.name}
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
          <Typography variant="caption" color="text.secondary">
            {formatFileSize(asset.size)}
          </Typography>
          {asset.resolution && (
            <>
              <Typography variant="caption" color="text.secondary">•</Typography>
              <Typography variant="caption" color="text.secondary">
                {asset.resolution.width}x{asset.resolution.height}
              </Typography>
            </>
          )}
        </Box>

        {/* Tags */}
        {asset.tags.length > 0 && (
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
            {asset.tags.slice(0, thumbnailSize === 'small' ? 2 : 3).map((tag, index) => (
              <Chip
                key={index}
                label={tag}
                size="small"
                sx={{ height: 20, fontSize: '0.7rem' }}
              />
            ))}
            {asset.tags.length > (thumbnailSize === 'small' ? 2 : 3) && (
              <Chip
                label={`+${asset.tags.length - (thumbnailSize === 'small' ? 2 : 3)}`}
                size="small"
                sx={{ height: 20, fontSize: '0.7rem' }}
              />
            )}
          </Box>
        )}
      </CardContent>

      {/* Actions */}
      <CardActions sx={{ p: 1, pt: 0 }}>
        <IconButton
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            onDownload(asset);
          }}
        >
          <DownloadIcon fontSize="small" />
        </IconButton>
        <IconButton
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            onEdit(asset);
          }}
        >
          <EditIcon fontSize="small" />
        </IconButton>
        <IconButton
          size="small"
          onClick={handleMenuOpen}
        >
          <MoreVertIcon fontSize="small" />
        </IconButton>
      </CardActions>

      {/* Context menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
        onClick={(e) => e.stopPropagation()}
      >
        <MenuItem
          onClick={() => {
            handleMenuClose();
            // Open asset details
          }}
        >
          <ListItemIcon>
            <InfoIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>View Details</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleMenuClose();
            onEdit(asset);
          }}
        >
          <ListItemIcon>
            <EditIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Edit</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleMenuClose();
            // Duplicate asset
          }}
        >
          <ListItemIcon>
            <DuplicateIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Duplicate</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleMenuClose();
            // Move asset
          }}
        >
          <ListItemIcon>
            <MoveIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Move to...</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleMenuClose();
            // Add tags
          }}
        >
          <ListItemIcon>
            <TagIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Add Tags</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleMenuClose();
            onShare(asset);
          }}
        >
          <ListItemIcon>
            <ShareIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Share</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleMenuClose();
            onDelete(asset);
          }}
          sx={{ color: 'error.main' }}
        >
          <ListItemIcon>
            <DeleteIcon fontSize="small" color="error" />
          </ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>
    </Card>
  );
};

export default DraggableAssetCard;