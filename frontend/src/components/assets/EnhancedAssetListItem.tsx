import React, { useState, useRef } from 'react';
import {
  ListItem,
  ListItemButton,
  Checkbox,
  Box,
  Typography,
  IconButton,
  Chip,
  Avatar,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Tooltip,
  TextField,
  Collapse,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  MoreVert as MoreVertIcon,
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
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Lock as LockedIcon,
  Schedule as ProcessingIcon,
  PlayArrow as PlayIcon,
  DragIndicator as DragIcon,
} from '@mui/icons-material';
import { useDrag } from 'react-dnd';
import { Asset } from '../../types/asset';
import { formatFileSize, formatDuration, formatDate } from '../../utils/formatters';

interface ColumnConfig {
  id: string;
  label: string;
  visible: boolean;
  width?: number;
  sortable?: boolean;
}

interface EnhancedAssetListItemProps {
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
  columns: ColumnConfig[];
  enableDrag: boolean;
}

const EnhancedAssetListItem: React.FC<EnhancedAssetListItemProps> = ({
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
  columns,
  enableDrag,
}) => {
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const dragRef = useRef<HTMLDivElement>(null);

  // Drag setup
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

  if (enableDrag) {
    drag(dragRef);
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

  const handleDoubleClick = (field: string, value: string) => {
    if (['name', 'tags'].includes(field)) {
      setEditingField(field);
      setEditValue(value);
    }
  };

  const handleEditSave = () => {
    // TODO: Implement inline editing save
    console.log('Save edit:', editingField, editValue);
    setEditingField(null);
  };

  const handleEditCancel = () => {
    setEditingField(null);
    setEditValue('');
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

  const renderCellContent = (columnId: string) => {
    switch (columnId) {
      case 'thumbnail':
        return (
          <Avatar
            variant="rounded"
            src={asset.thumbnailUrl}
            sx={{ width: 48, height: 36 }}
          >
            {getAssetIcon()}
          </Avatar>
        );

      case 'name':
        if (editingField === 'name') {
          return (
            <TextField
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={handleEditSave}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleEditSave();
                if (e.key === 'Escape') handleEditCancel();
              }}
              size="small"
              autoFocus
              fullWidth
              onClick={(e) => e.stopPropagation()}
            />
          );
        }
        return (
          <Box onDoubleClick={() => handleDoubleClick('name', asset.name)}>
            <Typography variant="body2" noWrap sx={{ fontWeight: selected ? 600 : 400 }}>
              {asset.name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {asset.fileName}
            </Typography>
          </Box>
        );

      case 'type':
        return (
          <Chip
            icon={getAssetIcon()}
            label={asset.type}
            size="small"
            variant="outlined"
          />
        );

      case 'size':
        return (
          <Typography variant="body2">
            {formatFileSize(asset.size)}
          </Typography>
        );

      case 'duration':
        return asset.type === 'video' && asset.duration ? (
          <Typography variant="body2">
            {formatDuration(asset.duration)}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary">—</Typography>
        );

      case 'createdAt':
        return (
          <Typography variant="body2">
            {formatDate(asset.createdAt)}
          </Typography>
        );

      case 'modifiedAt':
        return (
          <Typography variant="body2">
            {formatDate(asset.updatedAt)}
          </Typography>
        );

      case 'tags':
        if (editingField === 'tags') {
          return (
            <TextField
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={handleEditSave}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleEditSave();
                if (e.key === 'Escape') handleEditCancel();
              }}
              size="small"
              autoFocus
              fullWidth
              placeholder="tag1, tag2, tag3"
              onClick={(e) => e.stopPropagation()}
            />
          );
        }
        return (
          <Box
            sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}
            onDoubleClick={() => handleDoubleClick('tags', asset.tags.join(', '))}
          >
            {asset.tags.length > 0 ? (
              asset.tags.map((tag, index) => (
                <Chip key={index} label={tag} size="small" />
              ))
            ) : (
              <Typography variant="body2" color="text.secondary">—</Typography>
            )}
          </Box>
        );

      case 'status':
        return (
          <Chip
            label={asset.status}
            size="small"
            color={
              asset.status === 'ready' ? 'success' :
              asset.status === 'processing' ? 'warning' :
              asset.status === 'error' ? 'error' : 'default'
            }
            icon={
              asset.status === 'processing' ? <ProcessingIcon /> :
              asset.status === 'locked' ? <LockedIcon /> : undefined
            }
          />
        );

      case 'owner':
        return (
          <Typography variant="body2">
            {asset.createdBy || '—'}
          </Typography>
        );

      case 'project':
        return (
          <Typography variant="body2">
            {asset.projectId || '—'}
          </Typography>
        );

      case 'resolution':
        return asset.resolution ? (
          <Typography variant="body2">
            {asset.resolution.width}x{asset.resolution.height}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary">—</Typography>
        );

      case 'frameRate':
        return asset.frameRate ? (
          <Typography variant="body2">
            {asset.frameRate} fps
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary">—</Typography>
        );

      case 'codec':
        return asset.codec ? (
          <Typography variant="body2">
            {asset.codec}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary">—</Typography>
        );

      default:
        return null;
    }
  };

  return (
    <>
      <ListItem
        disablePadding
        sx={{
          opacity: isDragging ? 0.5 : 1,
          backgroundColor: selected ? 'action.selected' : 'inherit',
          '&:hover': {
            backgroundColor: 'action.hover',
          },
        }}
      >
        <ListItemButton
          onClick={() => onClick(asset)}
          sx={{ px: 1, py: 0.5 }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
            {/* Drag handle */}
            {enableDrag && (
              <Box ref={dragRef} sx={{ cursor: 'move', mr: 1 }}>
                <DragIcon color="action" />
              </Box>
            )}

            {/* Checkbox */}
            <Checkbox
              checked={selected}
              onChange={handleSelect}
              onClick={handleSelect}
              sx={{ mr: 1 }}
            />

            {/* Favorite */}
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                onToggleFavorite(asset.id);
              }}
              sx={{ mr: 1 }}
            >
              {isFavorite ? <StarIcon fontSize="small" color="warning" /> : <StarBorderIcon fontSize="small" />}
            </IconButton>

            {/* Column cells */}
            {columns.map((col) => (
              <Box
                key={col.id}
                sx={{
                  width: col.width || 100,
                  px: 1,
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                {renderCellContent(col.id)}
              </Box>
            ))}

            {/* Actions */}
            <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 0.5 }}>
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
                  setExpanded(!expanded);
                }}
              >
                {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </IconButton>
              <IconButton
                size="small"
                onClick={handleMenuOpen}
              >
                <MoreVertIcon fontSize="small" />
              </IconButton>
            </Box>
          </Box>
        </ListItemButton>
      </ListItem>

      {/* Expanded details */}
      <Collapse in={expanded} timeout="auto" unmountOnExit>
        <Box sx={{ px: 4, py: 2, backgroundColor: 'background.default' }}>
          <Typography variant="subtitle2" gutterBottom>
            Additional Information
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">File Path</Typography>
              <Typography variant="body2">{asset.filePath}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">MIME Type</Typography>
              <Typography variant="body2">{asset.mimeType}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">MD5 Hash</Typography>
              <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                {asset.md5Hash || '—'}
              </Typography>
            </Box>
            {asset.metadata && (
              <>
                <Box>
                  <Typography variant="caption" color="text.secondary">Bit Rate</Typography>
                  <Typography variant="body2">{asset.metadata.bitRate || '—'}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Sample Rate</Typography>
                  <Typography variant="body2">{asset.metadata.sampleRate || '—'}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Color Space</Typography>
                  <Typography variant="body2">{asset.metadata.colorSpace || '—'}</Typography>
                </Box>
              </>
            )}
          </Box>
        </Box>
      </Collapse>

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
            // Play preview
          }}
        >
          <ListItemIcon>
            <PlayIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Preview</ListItemText>
        </MenuItem>
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
    </>
  );
};

export default EnhancedAssetListItem;