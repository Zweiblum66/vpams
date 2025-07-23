import React, { useState, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardMedia,
  CardContent,
  CardActions,
  Typography,
  IconButton,
  Chip,
  Skeleton,
  Alert,
  Menu,
  MenuItem,
  Tooltip,
  TextField,
  Select,
  FormControl,
  InputLabel,
  Checkbox,
  ListItemText,
} from '@mui/material';
import {
  PlayCircleOutline,
  GetApp,
  Info,
  MoreVert,
  VideoLibrary,
  Image,
  AudioFile,
  Folder,
  FilterList,
} from '@mui/icons-material';
import { Asset, AssetType } from '../types';
import AssetPreview from './AssetPreview';

interface AssetBrowserProps {
  assets: Asset[];
  loading: boolean;
  error: string | null;
  onAssetSelect: (asset: Asset) => void;
  onAssetImport: (asset: Asset) => void;
}

const AssetBrowser: React.FC<AssetBrowserProps> = ({
  assets,
  loading,
  error,
  onAssetSelect,
  onAssetImport,
}) => {
  const [previewAsset, setPreviewAsset] = useState<Asset | null>(null);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [filters, setFilters] = useState({
    type: [] as AssetType[],
    tags: [] as string[],
    dateRange: 'all',
  });
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, asset: Asset) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
    setSelectedAsset(asset);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedAsset(null);
  };

  const handlePreview = (asset: Asset) => {
    setPreviewAsset(asset);
    handleMenuClose();
  };

  const handleImport = (asset: Asset) => {
    onAssetImport(asset);
    handleMenuClose();
  };

  const handleDragStart = (event: React.DragEvent, asset: Asset) => {
    // Set drag data for Premiere Pro
    event.dataTransfer.effectAllowed = 'copy';
    event.dataTransfer.setData('text/uri-list', asset.url);
    event.dataTransfer.setData('application/x-mams-asset', JSON.stringify(asset));
  };

  const getAssetIcon = (type: AssetType) => {
    switch (type) {
      case 'video':
        return <VideoLibrary />;
      case 'image':
        return <Image />;
      case 'audio':
        return <AudioFile />;
      case 'project':
        return <Folder />;
      default:
        return <Folder />;
    }
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  // Filter assets
  const filteredAssets = assets.filter(asset => {
    if (filters.type.length > 0 && !filters.type.includes(asset.type)) {
      return false;
    }
    
    if (filters.tags.length > 0) {
      const assetTags = asset.metadata?.tags || [];
      if (!filters.tags.some(tag => assetTags.includes(tag))) {
        return false;
      }
    }
    
    // Add date filtering logic here
    
    return true;
  });

  // Get unique tags from all assets
  const allTags = Array.from(
    new Set(assets.flatMap(asset => asset.metadata?.tags || []))
  );

  if (loading) {
    return (
      <Grid container spacing={2}>
        {[...Array(6)].map((_, index) => (
          <Grid item xs={12} sm={6} md={4} key={index}>
            <Card>
              <Skeleton variant="rectangular" height={140} />
              <CardContent>
                <Skeleton variant="text" />
                <Skeleton variant="text" width="60%" />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  return (
    <Box>
      {/* Filters */}
      <Box sx={{ mb: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Type</InputLabel>
          <Select
            multiple
            value={filters.type}
            onChange={(e) => setFilters({ ...filters, type: e.target.value as AssetType[] })}
            renderValue={(selected) => selected.join(', ')}
          >
            {['video', 'image', 'audio', 'project'].map((type) => (
              <MenuItem key={type} value={type}>
                <Checkbox checked={filters.type.includes(type as AssetType)} />
                <ListItemText primary={type.charAt(0).toUpperCase() + type.slice(1)} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Tags</InputLabel>
          <Select
            multiple
            value={filters.tags}
            onChange={(e) => setFilters({ ...filters, tags: e.target.value as string[] })}
            renderValue={(selected) => selected.join(', ')}
          >
            {allTags.map((tag) => (
              <MenuItem key={tag} value={tag}>
                <Checkbox checked={filters.tags.includes(tag)} />
                <ListItemText primary={tag} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Box sx={{ flexGrow: 1 }} />

        <IconButton
          size="small"
          onClick={() => setFilters({ type: [], tags: [], dateRange: 'all' })}
        >
          <FilterList />
        </IconButton>
      </Box>

      {/* Asset Grid */}
      <Grid container spacing={2}>
        {filteredAssets.map((asset) => (
          <Grid item xs={12} sm={6} md={4} key={asset.id}>
            <Card
              sx={{
                cursor: 'pointer',
                '&:hover': {
                  boxShadow: 4,
                },
              }}
              onClick={() => onAssetSelect(asset)}
              draggable
              onDragStart={(e) => handleDragStart(e, asset)}
            >
              {/* Thumbnail */}
              <CardMedia
                sx={{
                  height: 140,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: 'action.hover',
                  position: 'relative',
                }}
              >
                {asset.thumbnailUrl ? (
                  <img
                    src={asset.thumbnailUrl}
                    alt={asset.name}
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                    }}
                  />
                ) : (
                  <Box sx={{ color: 'text.secondary', fontSize: 48 }}>
                    {getAssetIcon(asset.type)}
                  </Box>
                )}
                
                {/* Duration overlay for videos */}
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
              </CardMedia>

              {/* Content */}
              <CardContent sx={{ pb: 1 }}>
                <Typography variant="subtitle2" noWrap>
                  {asset.name}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                  <Chip
                    label={asset.type}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                  <Typography variant="caption" color="text.secondary">
                    {formatFileSize(asset.size)}
                  </Typography>
                </Box>
                
                {/* Tags */}
                {asset.metadata?.tags && asset.metadata.tags.length > 0 && (
                  <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {asset.metadata.tags.slice(0, 3).map((tag, index) => (
                      <Chip
                        key={index}
                        label={tag}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: '0.7rem' }}
                      />
                    ))}
                    {asset.metadata.tags.length > 3 && (
                      <Chip
                        label={`+${asset.metadata.tags.length - 3}`}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: '0.7rem' }}
                      />
                    )}
                  </Box>
                )}
              </CardContent>

              {/* Actions */}
              <CardActions sx={{ justifyContent: 'space-between', pt: 0 }}>
                <Box>
                  <Tooltip title="Preview">
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePreview(asset);
                      }}
                    >
                      <PlayCircleOutline />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Import">
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleImport(asset);
                      }}
                    >
                      <GetApp />
                    </IconButton>
                  </Tooltip>
                </Box>
                <IconButton
                  size="small"
                  onClick={(e) => handleMenuClick(e, asset)}
                >
                  <MoreVert />
                </IconButton>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => selectedAsset && handlePreview(selectedAsset)}>
          Preview
        </MenuItem>
        <MenuItem onClick={() => selectedAsset && handleImport(selectedAsset)}>
          Import to Project
        </MenuItem>
        <MenuItem onClick={() => selectedAsset && onAssetSelect(selectedAsset)}>
          View Details
        </MenuItem>
        <MenuItem>Download High-Res</MenuItem>
        <MenuItem>Copy Link</MenuItem>
      </Menu>

      {/* Preview Dialog */}
      {previewAsset && (
        <AssetPreview
          asset={previewAsset}
          open={Boolean(previewAsset)}
          onClose={() => setPreviewAsset(null)}
          onImport={handleImport}
        />
      )}
    </Box>
  );
};

export default AssetBrowser;