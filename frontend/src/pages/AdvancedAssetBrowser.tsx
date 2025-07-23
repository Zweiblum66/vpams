import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  Box,
  Container,
  Grid,
  Pagination,
  Paper,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Button,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Snackbar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Chip,
  CircularProgress,
  List,
  Slider,
  Tooltip,
  Popover,
  Switch,
  FormControlLabel,
  TextField,
  Checkbox,
  Backdrop,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
  Fade,
  Grow,
  Zoom,
  Badge,
  LinearProgress,
  Stack,
} from '@mui/material';
import {
  ViewModule as GridViewIcon,
  ViewList as ListViewIcon,
  ViewComfy as ComfyViewIcon,
  Upload as UploadIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  Label as TagIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  CheckBox as SelectAllIcon,
  CheckBoxOutlineBlank as DeselectAllIcon,
  FilterList as FilterIcon,
  PhotoSizeSelectActual as ThumbnailSizeIcon,
  DragIndicator as DragIcon,
  Folder as FolderIcon,
  CreateNewFolder as CreateFolderIcon,
  Settings as SettingsIcon,
  Keyboard as KeyboardIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  ViewColumn as ColumnsIcon,
  Sort as SortIcon,
  MoreVert as MoreVertIcon,
  PlayArrow as PreviewIcon,
  Info as InfoIcon,
  Edit as EditIcon,
  ContentCopy as DuplicateIcon,
  DriveFileMove as MoveIcon,
  LocalOffer as TagsIcon,
  Timeline as TimelineIcon,
  CloudUpload as CloudUploadIcon,
  FolderOpen as FolderOpenIcon,
  SelectAll as SelectAllPageIcon,
  DeselectAll as DeselectAllPageIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { VariableSizeGrid as Grid2 } from 'react-window';
import AutoSizer from 'react-virtualized-auto-sizer';
import { useHotkeys } from 'react-hotkeys-hook';

import AssetCard from '../components/assets/AssetCard';
import AssetListItem from '../components/assets/AssetListItem';
import DraggableAssetCard from '../components/assets/DraggableAssetCard';
import EnhancedAssetListItem from '../components/assets/EnhancedAssetListItem';
import AssetFilters from '../components/assets/AssetFilters';
import { assetApi, AssetApiError } from '../services/assetApi';
import {
  Asset,
  AssetFilter,
  AssetSort,
  AssetListResponse,
  AssetBulkAction,
} from '../types/asset';
import { logger } from '../utils/logger';
import { formatFileSize, formatDuration, formatDate } from '../utils/formatters';

type ViewMode = 'grid' | 'list' | 'comfy';
type ThumbnailSize = 'small' | 'medium' | 'large' | 'xlarge';

interface DragItem {
  type: 'asset' | 'assets';
  id?: string;
  ids?: string[];
  asset?: Asset;
  assets?: Asset[];
}

interface ColumnConfig {
  id: string;
  label: string;
  visible: boolean;
  width?: number;
  sortable?: boolean;
}

const defaultColumns: ColumnConfig[] = [
  { id: 'thumbnail', label: 'Thumbnail', visible: true, width: 60, sortable: false },
  { id: 'name', label: 'Name', visible: true, width: 200, sortable: true },
  { id: 'type', label: 'Type', visible: true, width: 100, sortable: true },
  { id: 'size', label: 'Size', visible: true, width: 100, sortable: true },
  { id: 'duration', label: 'Duration', visible: true, width: 100, sortable: true },
  { id: 'createdAt', label: 'Created', visible: true, width: 150, sortable: true },
  { id: 'modifiedAt', label: 'Modified', visible: true, width: 150, sortable: true },
  { id: 'tags', label: 'Tags', visible: true, width: 200, sortable: false },
  { id: 'status', label: 'Status', visible: true, width: 100, sortable: true },
  { id: 'owner', label: 'Owner', visible: false, width: 150, sortable: true },
  { id: 'project', label: 'Project', visible: false, width: 150, sortable: true },
  { id: 'resolution', label: 'Resolution', visible: false, width: 120, sortable: false },
  { id: 'frameRate', label: 'Frame Rate', visible: false, width: 100, sortable: false },
  { id: 'codec', label: 'Codec', visible: false, width: 100, sortable: false },
];

const thumbnailSizes = {
  small: { width: 120, height: 90 },
  medium: { width: 200, height: 150 },
  large: { width: 320, height: 240 },
  xlarge: { width: 480, height: 360 },
};

const AdvancedAssetBrowser: React.FC = () => {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const [draggedOverFolder, setDraggedOverFolder] = useState<string | null>(null);
  
  // State
  const [assets, setAssets] = useState<Asset[]>([]);
  const [totalAssets, setTotalAssets] = useState(0);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [selectedAssets, setSelectedAssets] = useState<Set<string>>(new Set());
  const [lastSelectedIndex, setLastSelectedIndex] = useState<number>(-1);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [filter, setFilter] = useState<AssetFilter>({});
  const [sort, setSort] = useState<AssetSort>({ field: 'createdAt', order: 'desc' });
  const [bulkMenuAnchor, setBulkMenuAnchor] = useState<null | HTMLElement>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [moveDialogOpen, setMoveDialogOpen] = useState(false);
  const [tagDialogOpen, setTagDialogOpen] = useState(false);
  const [columnsMenuAnchor, setColumnsMenuAnchor] = useState<null | HTMLElement>(null);
  const [thumbnailSize, setThumbnailSize] = useState<ThumbnailSize>('medium');
  const [showPreviewOnHover, setShowPreviewOnHover] = useState(true);
  const [enableDragDrop, setEnableDragDrop] = useState(true);
  const [columns, setColumns] = useState<ColumnConfig[]>(defaultColumns);
  const [keyboardShortcutsOpen, setKeyboardShortcutsOpen] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);
  const [bulkOperationProgress, setBulkOperationProgress] = useState<{
    active: boolean;
    progress: number;
    message: string;
  }>({ active: false, progress: 0, message: '' });
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({ open: false, message: '', severity: 'info' });
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());

  // Keyboard shortcuts
  useHotkeys('ctrl+a, cmd+a', (e) => {
    e.preventDefault();
    handleSelectAllPage();
  }, [assets]);

  useHotkeys('ctrl+d, cmd+d', (e) => {
    e.preventDefault();
    setSelectedAssets(new Set());
  }, []);

  useHotkeys('delete', () => {
    if (selectedAssets.size > 0) {
      setDeleteDialogOpen(true);
    }
  }, [selectedAssets]);

  useHotkeys('ctrl+c, cmd+c', (e) => {
    if (selectedAssets.size > 0) {
      e.preventDefault();
      handleCopyAssets();
    }
  }, [selectedAssets]);

  useHotkeys('ctrl+x, cmd+x', (e) => {
    if (selectedAssets.size > 0) {
      e.preventDefault();
      handleCutAssets();
    }
  }, [selectedAssets]);

  useHotkeys('g', () => setViewMode('grid'), []);
  useHotkeys('l', () => setViewMode('list'), []);
  useHotkeys('c', () => setViewMode('comfy'), []);
  
  useHotkeys('shift+?', () => setKeyboardShortcutsOpen(true), []);
  
  useHotkeys('space', (e) => {
    e.preventDefault();
    setSelectionMode(!selectionMode);
  }, [selectionMode]);

  useHotkeys('arrow-up', (e) => {
    e.preventDefault();
    navigateAssets('up');
  }, [assets, selectedAssets, viewMode]);

  useHotkeys('arrow-down', (e) => {
    e.preventDefault();
    navigateAssets('down');
  }, [assets, selectedAssets, viewMode]);

  useHotkeys('arrow-left', (e) => {
    e.preventDefault();
    navigateAssets('left');
  }, [assets, selectedAssets, viewMode]);

  useHotkeys('arrow-right', (e) => {
    e.preventDefault();
    navigateAssets('right');
  }, [assets, selectedAssets, viewMode]);

  useHotkeys('enter', () => {
    if (selectedAssets.size === 1) {
      const assetId = Array.from(selectedAssets)[0];
      const asset = assets.find(a => a.id === assetId);
      if (asset) {
        handleAssetClick(asset);
      }
    }
  }, [selectedAssets, assets]);

  // Fetch assets
  const fetchAssets = useCallback(async () => {
    try {
      setLoading(true);
      logger.info('Fetching assets', {
        filter,
        sort,
        page,
        pageSize,
        actionType: 'advanced_asset_browse_fetch',
      });

      const response: AssetListResponse = await assetApi.getAssets(filter, sort, page, pageSize);
      
      setAssets(response.assets);
      setTotalAssets(response.total);
      
      // Extract unique tags for filter component
      const tags = new Set<string>();
      response.assets.forEach(asset => {
        asset.tags.forEach(tag => tags.add(tag));
      });
      setAvailableTags(Array.from(tags));

      logger.info('Assets fetched successfully', {
        count: response.assets.length,
        total: response.total,
        actionType: 'advanced_asset_browse_fetch_success',
      });
    } catch (error) {
      logger.error('Failed to fetch assets', {
        error,
        actionType: 'advanced_asset_browse_fetch_error',
      });
      
      setSnackbar({
        open: true,
        message: error instanceof AssetApiError ? error.message : 'Failed to load assets',
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  }, [filter, sort, page, pageSize]);

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  // Load saved preferences
  useEffect(() => {
    const savedPrefs = localStorage.getItem('assetBrowserPrefs');
    if (savedPrefs) {
      const prefs = JSON.parse(savedPrefs);
      if (prefs.viewMode) setViewMode(prefs.viewMode);
      if (prefs.thumbnailSize) setThumbnailSize(prefs.thumbnailSize);
      if (prefs.columns) setColumns(prefs.columns);
      if (prefs.showPreviewOnHover !== undefined) setShowPreviewOnHover(prefs.showPreviewOnHover);
      if (prefs.pageSize) setPageSize(prefs.pageSize);
    }
  }, []);

  // Save preferences
  useEffect(() => {
    const prefs = {
      viewMode,
      thumbnailSize,
      columns,
      showPreviewOnHover,
      pageSize,
    };
    localStorage.setItem('assetBrowserPrefs', JSON.stringify(prefs));
  }, [viewMode, thumbnailSize, columns, showPreviewOnHover, pageSize]);

  // Navigation functions
  const navigateAssets = (direction: 'up' | 'down' | 'left' | 'right') => {
    if (assets.length === 0) return;

    const currentIndex = selectedAssets.size === 1 
      ? assets.findIndex(a => a.id === Array.from(selectedAssets)[0])
      : -1;

    let newIndex = currentIndex;
    const itemsPerRow = viewMode === 'list' ? 1 : Math.floor(containerRef.current?.clientWidth! / thumbnailSizes[thumbnailSize].width) || 4;

    switch (direction) {
      case 'up':
        newIndex = viewMode === 'list' 
          ? Math.max(0, currentIndex - 1)
          : Math.max(0, currentIndex - itemsPerRow);
        break;
      case 'down':
        newIndex = viewMode === 'list'
          ? Math.min(assets.length - 1, currentIndex + 1)
          : Math.min(assets.length - 1, currentIndex + itemsPerRow);
        break;
      case 'left':
        newIndex = Math.max(0, currentIndex - 1);
        break;
      case 'right':
        newIndex = Math.min(assets.length - 1, currentIndex + 1);
        break;
    }

    if (newIndex !== currentIndex && newIndex >= 0) {
      setSelectedAssets(new Set([assets[newIndex].id]));
      setLastSelectedIndex(newIndex);
    }
  };

  // Handlers
  const handleViewModeChange = (event: React.MouseEvent<HTMLElement>, newMode: ViewMode | null) => {
    if (newMode !== null) {
      setViewMode(newMode);
      logger.info('View mode changed', {
        viewMode: newMode,
        actionType: 'advanced_asset_browse_view_mode_change',
      });
    }
  };

  const handleAssetSelect = (assetId: string, selected: boolean, event?: React.MouseEvent) => {
    const assetIndex = assets.findIndex(a => a.id === assetId);
    
    if (event?.shiftKey && lastSelectedIndex !== -1 && assetIndex !== -1) {
      // Range selection
      const start = Math.min(lastSelectedIndex, assetIndex);
      const end = Math.max(lastSelectedIndex, assetIndex);
      const rangeIds = assets.slice(start, end + 1).map(a => a.id);
      
      setSelectedAssets(prev => {
        const newSet = new Set(prev);
        rangeIds.forEach(id => newSet.add(id));
        return newSet;
      });
    } else if (event?.ctrlKey || event?.metaKey) {
      // Toggle selection
      setSelectedAssets(prev => {
        const newSet = new Set(prev);
        if (selected) {
          newSet.add(assetId);
        } else {
          newSet.delete(assetId);
        }
        return newSet;
      });
    } else {
      // Single selection
      setSelectedAssets(new Set(selected ? [assetId] : []));
    }
    
    if (selected) {
      setLastSelectedIndex(assetIndex);
    }
  };

  const handleSelectAllPage = () => {
    setSelectedAssets(new Set(assets.map(asset => asset.id)));
  };

  const handleDeselectAll = () => {
    setSelectedAssets(new Set());
  };

  const handleAssetClick = (asset: Asset) => {
    if (!selectionMode) {
      navigate(`/assets/${asset.id}`);
    } else {
      handleAssetSelect(asset.id, !selectedAssets.has(asset.id));
    }
  };

  const handleAssetEdit = (asset: Asset) => {
    navigate(`/assets/${asset.id}/edit`);
  };

  const handleAssetDownload = async (asset: Asset) => {
    try {
      logger.info('Downloading asset', {
        assetId: asset.id,
        assetName: asset.name,
        actionType: 'advanced_asset_browse_download',
      });

      const blob = await assetApi.downloadAsset(asset.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = asset.fileName;
      a.click();
      window.URL.revokeObjectURL(url);

      setSnackbar({
        open: true,
        message: `Downloaded ${asset.name}`,
        severity: 'success',
      });
    } catch (error) {
      logger.error('Failed to download asset', {
        assetId: asset.id,
        error,
        actionType: 'advanced_asset_browse_download_error',
      });
      
      setSnackbar({
        open: true,
        message: 'Failed to download asset',
        severity: 'error',
      });
    }
  };

  const handleAssetShare = (asset: Asset) => {
    // TODO: Implement share functionality
    setSnackbar({
      open: true,
      message: 'Share functionality coming soon',
      severity: 'info',
    });
  };

  const handleCopyAssets = () => {
    // Store selected asset IDs in clipboard (mock implementation)
    navigator.clipboard.writeText(JSON.stringify(Array.from(selectedAssets)));
    setSnackbar({
      open: true,
      message: `Copied ${selectedAssets.size} asset${selectedAssets.size > 1 ? 's' : ''} to clipboard`,
      severity: 'success',
    });
  };

  const handleCutAssets = () => {
    // Store selected asset IDs in clipboard with cut flag (mock implementation)
    navigator.clipboard.writeText(JSON.stringify({ 
      action: 'cut',
      assetIds: Array.from(selectedAssets) 
    }));
    setSnackbar({
      open: true,
      message: `Cut ${selectedAssets.size} asset${selectedAssets.size > 1 ? 's' : ''}`,
      severity: 'success',
    });
  };

  const handleBulkDelete = async () => {
    try {
      setBulkOperationProgress({
        active: true,
        progress: 0,
        message: 'Deleting assets...',
      });

      logger.info('Bulk deleting assets', {
        count: selectedAssets.size,
        actionType: 'advanced_asset_browse_bulk_delete',
      });

      const action: AssetBulkAction = {
        action: 'delete',
        assetIds: Array.from(selectedAssets),
      };

      // Simulate progress
      const total = selectedAssets.size;
      for (let i = 0; i < total; i++) {
        setBulkOperationProgress({
          active: true,
          progress: ((i + 1) / total) * 100,
          message: `Deleting asset ${i + 1} of ${total}...`,
        });
        await new Promise(resolve => setTimeout(resolve, 100)); // Simulate API call
      }

      await assetApi.bulkAction(action);

      setBulkOperationProgress({ active: false, progress: 0, message: '' });

      setSnackbar({
        open: true,
        message: `Deleted ${selectedAssets.size} assets`,
        severity: 'success',
      });

      setSelectedAssets(new Set());
      setDeleteDialogOpen(false);
      fetchAssets();
    } catch (error) {
      setBulkOperationProgress({ active: false, progress: 0, message: '' });
      
      logger.error('Failed to delete assets', {
        error,
        actionType: 'advanced_asset_browse_bulk_delete_error',
      });
      
      setSnackbar({
        open: true,
        message: 'Failed to delete assets',
        severity: 'error',
      });
    }
  };

  const handleBulkArchive = async () => {
    try {
      setBulkOperationProgress({
        active: true,
        progress: 0,
        message: 'Archiving assets...',
      });

      logger.info('Bulk archiving assets', {
        count: selectedAssets.size,
        actionType: 'advanced_asset_browse_bulk_archive',
      });

      const action: AssetBulkAction = {
        action: 'archive',
        assetIds: Array.from(selectedAssets),
      };

      await assetApi.bulkAction(action);

      setBulkOperationProgress({ active: false, progress: 0, message: '' });

      setSnackbar({
        open: true,
        message: `Archived ${selectedAssets.size} assets`,
        severity: 'success',
      });

      setSelectedAssets(new Set());
      setBulkMenuAnchor(null);
      fetchAssets();
    } catch (error) {
      setBulkOperationProgress({ active: false, progress: 0, message: '' });
      
      logger.error('Failed to archive assets', {
        error,
        actionType: 'advanced_asset_browse_bulk_archive_error',
      });
      
      setSnackbar({
        open: true,
        message: 'Failed to archive assets',
        severity: 'error',
      });
    }
  };

  const handleBulkTag = () => {
    setTagDialogOpen(true);
    setBulkMenuAnchor(null);
  };

  const handleBulkDownload = async () => {
    setBulkOperationProgress({
      active: true,
      progress: 0,
      message: 'Preparing download...',
    });

    // TODO: Implement bulk download with zip
    setTimeout(() => {
      setBulkOperationProgress({ active: false, progress: 0, message: '' });
      setSnackbar({
        open: true,
        message: 'Bulk download coming soon',
        severity: 'info',
      });
    }, 1000);
    
    setBulkMenuAnchor(null);
  };

  const handleBulkMove = () => {
    setMoveDialogOpen(true);
    setBulkMenuAnchor(null);
  };

  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    window.scrollTo(0, 0);
  };

  const handleFilterChange = (newFilter: AssetFilter) => {
    setFilter(newFilter);
    setPage(1); // Reset to first page when filter changes
  };

  const handleFilterClear = () => {
    setFilter({});
    setPage(1);
  };

  const handleUploadClick = () => {
    navigate('/assets/upload');
  };

  const handleColumnToggle = (columnId: string) => {
    setColumns(prev => prev.map(col => 
      col.id === columnId ? { ...col, visible: !col.visible } : col
    ));
  };

  const handleDrop = useCallback((item: DragItem, targetId?: string) => {
    if (!enableDragDrop) return;

    const assetIds = item.ids || (item.id ? [item.id] : []);
    
    if (targetId) {
      // Move to folder/project
      logger.info('Moving assets to target', {
        assetIds,
        targetId,
        actionType: 'advanced_asset_browse_drag_drop',
      });
      
      // TODO: Implement move to folder/project
      setSnackbar({
        open: true,
        message: `Moving ${assetIds.length} asset${assetIds.length > 1 ? 's' : ''} to folder`,
        severity: 'info',
      });
    }
  }, [enableDragDrop]);

  const handleToggleFavorite = (assetId: string) => {
    setFavorites(prev => {
      const newFavorites = new Set(prev);
      if (newFavorites.has(assetId)) {
        newFavorites.delete(assetId);
      } else {
        newFavorites.add(assetId);
      }
      return newFavorites;
    });
  };

  const totalPages = Math.ceil(totalAssets / pageSize);

  // Render helpers
  const renderGridView = () => {
    if (viewMode !== 'grid') return null;

    return (
      <Grid container spacing={2}>
        {assets.map((asset) => (
          <Grid 
            item 
            key={asset.id}
            xs={thumbnailSize === 'small' ? 6 : 12}
            sm={thumbnailSize === 'small' ? 4 : thumbnailSize === 'medium' ? 6 : 12}
            md={thumbnailSize === 'small' ? 3 : thumbnailSize === 'medium' ? 4 : 6}
            lg={thumbnailSize === 'small' ? 2 : thumbnailSize === 'medium' ? 3 : 4}
            xl={thumbnailSize === 'xlarge' ? 4 : thumbnailSize === 'large' ? 3 : 2}
          >
            <DraggableAssetCard
              asset={asset}
              selected={selectedAssets.has(asset.id)}
              onSelect={handleAssetSelect}
              onClick={handleAssetClick}
              onEdit={handleAssetEdit}
              onDelete={(asset) => {
                setSelectedAssets(new Set([asset.id]));
                setDeleteDialogOpen(true);
              }}
              onDownload={handleAssetDownload}
              onShare={handleAssetShare}
              onToggleFavorite={handleToggleFavorite}
              isFavorite={favorites.has(asset.id)}
              thumbnailSize={thumbnailSize}
              showPreviewOnHover={showPreviewOnHover}
              enableDrag={enableDragDrop && !selectionMode}
            />
          </Grid>
        ))}
      </Grid>
    );
  };

  const renderListView = () => {
    if (viewMode !== 'list') return null;

    const visibleColumns = columns.filter(col => col.visible);

    return (
      <Paper>
        <Box sx={{ overflowX: 'auto' }}>
          <List sx={{ minWidth: visibleColumns.reduce((sum, col) => sum + (col.width || 100), 0) }}>
            {/* Header */}
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                p: 1,
                borderBottom: 1,
                borderColor: 'divider',
                bgcolor: 'background.default',
                position: 'sticky',
                top: 0,
                zIndex: 1,
              }}
            >
              <Checkbox
                checked={selectedAssets.size === assets.length && assets.length > 0}
                indeterminate={selectedAssets.size > 0 && selectedAssets.size < assets.length}
                onChange={() => selectedAssets.size === assets.length ? handleDeselectAll() : handleSelectAllPage()}
                sx={{ mr: 1 }}
              />
              {visibleColumns.map((col) => (
                <Box
                  key={col.id}
                  sx={{
                    width: col.width || 100,
                    px: 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5,
                  }}
                >
                  <Typography variant="caption" fontWeight="bold">
                    {col.label}
                  </Typography>
                  {col.sortable && (
                    <IconButton
                      size="small"
                      onClick={() => setSort({
                        field: col.id,
                        order: sort.field === col.id && sort.order === 'asc' ? 'desc' : 'asc',
                      })}
                    >
                      <SortIcon fontSize="small" />
                    </IconButton>
                  )}
                </Box>
              ))}
            </Box>

            {/* Rows */}
            {assets.map((asset, index) => (
              <React.Fragment key={asset.id}>
                {index > 0 && <Divider />}
                <EnhancedAssetListItem
                  asset={asset}
                  selected={selectedAssets.has(asset.id)}
                  onSelect={handleAssetSelect}
                  onClick={handleAssetClick}
                  onEdit={handleAssetEdit}
                  onDelete={(asset) => {
                    setSelectedAssets(new Set([asset.id]));
                    setDeleteDialogOpen(true);
                  }}
                  onDownload={handleAssetDownload}
                  onShare={handleAssetShare}
                  onToggleFavorite={handleToggleFavorite}
                  isFavorite={favorites.has(asset.id)}
                  columns={visibleColumns}
                  enableDrag={enableDragDrop && !selectionMode}
                />
              </React.Fragment>
            ))}
          </List>
        </Box>
      </Paper>
    );
  };

  const renderComfyView = () => {
    if (viewMode !== 'comfy') return null;

    return (
      <Grid container spacing={3}>
        {assets.map((asset) => (
          <Grid item xs={12} md={6} key={asset.id}>
            <ComfyAssetCard
              asset={asset}
              selected={selectedAssets.has(asset.id)}
              onSelect={handleAssetSelect}
              onClick={handleAssetClick}
              onEdit={handleAssetEdit}
              onDelete={(asset) => {
                setSelectedAssets(new Set([asset.id]));
                setDeleteDialogOpen(true);
              }}
              onDownload={handleAssetDownload}
              onShare={handleAssetShare}
              onToggleFavorite={handleToggleFavorite}
              isFavorite={favorites.has(asset.id)}
              showPreviewOnHover={showPreviewOnHover}
              enableDrag={enableDragDrop && !selectionMode}
            />
          </Grid>
        ))}
      </Grid>
    );
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <Container maxWidth={false} sx={{ py: 3 }} ref={containerRef}>
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h4" component="h1">
              Advanced Asset Browser
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              {selectedAssets.size > 0 && (
                <>
                  <Chip
                    label={`${selectedAssets.size} selected`}
                    onDelete={handleDeselectAll}
                    color="primary"
                  />
                  
                  <Button
                    variant="outlined"
                    startIcon={<MoreVertIcon />}
                    onClick={(e) => setBulkMenuAnchor(e.currentTarget)}
                    id="bulk-actions-button"
                  >
                    Bulk Actions
                  </Button>
                </>
              )}

              <FormControlLabel
                control={
                  <Switch
                    checked={selectionMode}
                    onChange={(e) => setSelectionMode(e.target.checked)}
                  />
                }
                label="Selection Mode"
              />
              
              <Button
                variant="contained"
                startIcon={<UploadIcon />}
                onClick={handleUploadClick}
              >
                Upload
              </Button>

              <IconButton onClick={() => setKeyboardShortcutsOpen(true)}>
                <KeyboardIcon />
              </IconButton>
            </Box>
          </Box>

          {/* Filters */}
          <AssetFilters
            filter={filter}
            onChange={handleFilterChange}
            onClear={handleFilterClear}
            availableTags={availableTags}
          />
        </Box>

        {/* View controls and options */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="body2" color="text.secondary">
                {totalAssets} assets found
              </Typography>
              
              {assets.length > 0 && (
                <Stack direction="row" spacing={1}>
                  <Button
                    size="small"
                    startIcon={<SelectAllPageIcon />}
                    onClick={handleSelectAllPage}
                  >
                    Select Page
                  </Button>
                  <Button
                    size="small"
                    startIcon={<DeselectAllPageIcon />}
                    onClick={handleDeselectAll}
                    disabled={selectedAssets.size === 0}
                  >
                    Deselect All
                  </Button>
                </Stack>
              )}
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {/* Thumbnail size slider for grid view */}
              {viewMode === 'grid' && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 200 }}>
                  <ZoomOutIcon fontSize="small" />
                  <Slider
                    value={['small', 'medium', 'large', 'xlarge'].indexOf(thumbnailSize)}
                    onChange={(e, value) => {
                      const sizes: ThumbnailSize[] = ['small', 'medium', 'large', 'xlarge'];
                      setThumbnailSize(sizes[value as number]);
                    }}
                    step={1}
                    marks
                    min={0}
                    max={3}
                    sx={{ flex: 1 }}
                  />
                  <ZoomInIcon fontSize="small" />
                </Box>
              )}

              {/* Column selector for list view */}
              {viewMode === 'list' && (
                <IconButton onClick={(e) => setColumnsMenuAnchor(e.currentTarget)}>
                  <ColumnsIcon />
                </IconButton>
              )}

              {/* View mode toggle */}
              <ToggleButtonGroup
                value={viewMode}
                exclusive
                onChange={handleViewModeChange}
                size="small"
              >
                <ToggleButton value="grid">
                  <Tooltip title="Grid View">
                    <GridViewIcon />
                  </Tooltip>
                </ToggleButton>
                <ToggleButton value="list">
                  <Tooltip title="List View">
                    <ListViewIcon />
                  </Tooltip>
                </ToggleButton>
                <ToggleButton value="comfy">
                  <Tooltip title="Comfortable View">
                    <ComfyViewIcon />
                  </Tooltip>
                </ToggleButton>
              </ToggleButtonGroup>

              {/* Settings menu */}
              <IconButton>
                <SettingsIcon />
              </IconButton>
            </Box>
          </Box>
        </Paper>

        {/* Bulk operation progress */}
        {bulkOperationProgress.active && (
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="body2" gutterBottom>
              {bulkOperationProgress.message}
            </Typography>
            <LinearProgress variant="determinate" value={bulkOperationProgress.progress} />
          </Paper>
        )}

        {/* Assets display */}
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : assets.length === 0 ? (
          <Paper sx={{ p: 8, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No assets found
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              {filter.search || filter.types?.length || filter.status?.length
                ? 'Try adjusting your filters'
                : 'Upload your first asset to get started'}
            </Typography>
            {!filter.search && !filter.types?.length && !filter.status?.length && (
              <Button variant="contained" startIcon={<UploadIcon />} onClick={handleUploadClick}>
                Upload Assets
              </Button>
            )}
          </Paper>
        ) : (
          <>
            {renderGridView()}
            {renderListView()}
            {renderComfyView()}
          </>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <Pagination
              count={totalPages}
              page={page}
              onChange={handlePageChange}
              color="primary"
              size="large"
              showFirstButton
              showLastButton
            />
          </Box>
        )}

        {/* Floating action button for quick actions */}
        <SpeedDial
          ariaLabel="Quick actions"
          sx={{ position: 'fixed', bottom: 16, right: 16 }}
          icon={<SpeedDialIcon />}
        >
          <SpeedDialAction
            icon={<UploadIcon />}
            tooltipTitle="Upload"
            onClick={handleUploadClick}
          />
          <SpeedDialAction
            icon={<CreateFolderIcon />}
            tooltipTitle="New Folder"
            onClick={() => setSnackbar({ open: true, message: 'Folder creation coming soon', severity: 'info' })}
          />
          <SpeedDialAction
            icon={<FilterIcon />}
            tooltipTitle="Quick Filter"
            onClick={() => document.getElementById('asset-search')?.focus()}
          />
        </SpeedDial>

        {/* Bulk actions menu */}
        <Menu
          anchorEl={bulkMenuAnchor}
          open={Boolean(bulkMenuAnchor)}
          onClose={() => setBulkMenuAnchor(null)}
        >
          <MenuItem onClick={handleBulkDownload}>
            <ListItemIcon>
              <DownloadIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Download Selected</ListItemText>
          </MenuItem>
          <MenuItem onClick={handleBulkTag}>
            <ListItemIcon>
              <TagIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Tag Selected</ListItemText>
          </MenuItem>
          <MenuItem onClick={handleBulkMove}>
            <ListItemIcon>
              <MoveIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Move Selected</ListItemText>
          </MenuItem>
          <MenuItem onClick={handleBulkArchive}>
            <ListItemIcon>
              <ArchiveIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Archive Selected</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => handleCopyAssets()}>
            <ListItemIcon>
              <ContentCopy fontSize="small" />
            </ListItemIcon>
            <ListItemText>Copy Selected</ListItemText>
          </MenuItem>
          <Divider />
          <MenuItem
            onClick={() => {
              setBulkMenuAnchor(null);
              setDeleteDialogOpen(true);
            }}
            sx={{ color: 'error.main' }}
          >
            <ListItemIcon>
              <DeleteIcon fontSize="small" color="error" />
            </ListItemIcon>
            <ListItemText>Delete Selected</ListItemText>
          </MenuItem>
        </Menu>

        {/* Column selector menu */}
        <Menu
          anchorEl={columnsMenuAnchor}
          open={Boolean(columnsMenuAnchor)}
          onClose={() => setColumnsMenuAnchor(null)}
        >
          <MenuItem disabled>
            <Typography variant="subtitle2">Show/Hide Columns</Typography>
          </MenuItem>
          <Divider />
          {columns.map((col) => (
            <MenuItem key={col.id} onClick={() => handleColumnToggle(col.id)}>
              <Checkbox checked={col.visible} />
              <ListItemText>{col.label}</ListItemText>
            </MenuItem>
          ))}
        </Menu>

        {/* Delete confirmation dialog */}
        <Dialog
          open={deleteDialogOpen}
          onClose={() => setDeleteDialogOpen(false)}
        >
          <DialogTitle>Delete Assets?</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Are you sure you want to delete {selectedAssets.size} asset{selectedAssets.size > 1 ? 's' : ''}?
              This action cannot be undone.
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleBulkDelete} color="error" variant="contained">
              Delete
            </Button>
          </DialogActions>
        </Dialog>

        {/* Move dialog */}
        <Dialog
          open={moveDialogOpen}
          onClose={() => setMoveDialogOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Move Assets</DialogTitle>
          <DialogContent>
            <DialogContentText sx={{ mb: 2 }}>
              Select a destination folder for the {selectedAssets.size} selected asset{selectedAssets.size > 1 ? 's' : ''}.
            </DialogContentText>
            {/* TODO: Add folder tree selector */}
            <Typography color="text.secondary">
              Folder selection coming soon...
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setMoveDialogOpen(false)}>Cancel</Button>
            <Button onClick={() => setMoveDialogOpen(false)} variant="contained">
              Move
            </Button>
          </DialogActions>
        </Dialog>

        {/* Tag dialog */}
        <Dialog
          open={tagDialogOpen}
          onClose={() => setTagDialogOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Tag Assets</DialogTitle>
          <DialogContent>
            <DialogContentText sx={{ mb: 2 }}>
              Add tags to the {selectedAssets.size} selected asset{selectedAssets.size > 1 ? 's' : ''}.
            </DialogContentText>
            <TextField
              autoFocus
              margin="dense"
              label="Tags"
              fullWidth
              variant="outlined"
              placeholder="Enter tags separated by commas"
              helperText="e.g., project-x, review, final"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setTagDialogOpen(false)}>Cancel</Button>
            <Button onClick={() => setTagDialogOpen(false)} variant="contained">
              Add Tags
            </Button>
          </DialogActions>
        </Dialog>

        {/* Keyboard shortcuts dialog */}
        <Dialog
          open={keyboardShortcutsOpen}
          onClose={() => setKeyboardShortcutsOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
          <DialogContent>
            <List dense>
              <ListItem>
                <ListItemText primary="Select All" secondary="Ctrl/Cmd + A" />
              </ListItem>
              <ListItem>
                <ListItemText primary="Deselect All" secondary="Ctrl/Cmd + D" />
              </ListItem>
              <ListItem>
                <ListItemText primary="Delete Selected" secondary="Delete" />
              </ListItem>
              <ListItem>
                <ListItemText primary="Copy Selected" secondary="Ctrl/Cmd + C" />
              </ListItem>
              <ListItem>
                <ListItemText primary="Cut Selected" secondary="Ctrl/Cmd + X" />
              </ListItem>
              <ListItem>
                <ListItemText primary="Grid View" secondary="G" />
              </ListItem>
              <ListItem>
                <ListItemText primary="List View" secondary="L" />
              </ListItem>
              <ListItem>
                <ListItemText primary="Comfortable View" secondary="C" />
              </ListItem>
              <ListItem>
                <ListItemText primary="Toggle Selection Mode" secondary="Space" />
              </ListItem>
              <ListItem>
                <ListItemText primary="Navigate" secondary="Arrow Keys" />
              </ListItem>
              <ListItem>
                <ListItemText primary="Open Asset" secondary="Enter" />
              </ListItem>
              <ListItem>
                <ListItemText primary="Show Shortcuts" secondary="Shift + ?" />
              </ListItem>
            </List>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setKeyboardShortcutsOpen(false)}>Close</Button>
          </DialogActions>
        </Dialog>

        {/* Snackbar for notifications */}
        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
        >
          <Alert
            onClose={() => setSnackbar({ ...snackbar, open: false })}
            severity={snackbar.severity}
            sx={{ width: '100%' }}
          >
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Container>
    </DndProvider>
  );
};

// Comfortable view card component
const ComfyAssetCard: React.FC<any> = (props) => {
  const { asset, selected, onSelect, onClick, onEdit, onDelete, onDownload, onShare, onToggleFavorite, isFavorite } = props;
  
  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', gap: 2 }}>
        <Box sx={{ position: 'relative' }}>
          <Checkbox
            checked={selected}
            onChange={(e) => {
              e.stopPropagation();
              onSelect(asset.id, !selected, e);
            }}
            sx={{ position: 'absolute', top: 0, left: 0, zIndex: 1 }}
          />
          <Box 
            sx={{ 
              width: 200, 
              height: 150, 
              bgcolor: 'grey.200', 
              borderRadius: 1,
              backgroundImage: asset.thumbnailUrl ? `url(${asset.thumbnailUrl})` : 'none',
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer'
            }}
            onClick={() => onClick(asset)}
          >
            {!asset.thumbnailUrl && (
              asset.type === 'video' ? <VideoIcon sx={{ fontSize: 48, color: 'grey.500' }} /> :
              asset.type === 'image' ? <ImageIcon sx={{ fontSize: 48, color: 'grey.500' }} /> :
              asset.type === 'audio' ? <AudioIcon sx={{ fontSize: 48, color: 'grey.500' }} /> :
              <FileIcon sx={{ fontSize: 48, color: 'grey.500' }} />
            )}
          </Box>
        </Box>
        <Box sx={{ flex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="h6">{asset.name}</Typography>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                onToggleFavorite(asset.id);
              }}
            >
              {isFavorite ? <StarIcon fontSize="small" color="warning" /> : <StarBorderIcon fontSize="small" />}
            </IconButton>
          </Box>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {asset.type} • {formatFileSize(asset.size)} • {formatDate(asset.createdAt)}
            {asset.duration && ` • ${formatDuration(asset.duration)}`}
            {asset.resolution && ` • ${asset.resolution.width}x${asset.resolution.height}`}
          </Typography>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1, mb: 2 }}>
            {asset.tags.map((tag: string, index: number) => (
              <Chip key={index} label={tag} size="small" />
            ))}
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              size="small"
              startIcon={<DownloadIcon />}
              onClick={(e) => {
                e.stopPropagation();
                onDownload(asset);
              }}
            >
              Download
            </Button>
            <Button
              size="small"
              startIcon={<EditIcon />}
              onClick={(e) => {
                e.stopPropagation();
                onEdit(asset);
              }}
            >
              Edit
            </Button>
            <Button
              size="small"
              startIcon={<ShareIcon />}
              onClick={(e) => {
                e.stopPropagation();
                onShare(asset);
              }}
            >
              Share
            </Button>
            <Button
              size="small"
              startIcon={<DeleteIcon />}
              color="error"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(asset);
              }}
            >
              Delete
            </Button>
          </Box>
        </Box>
      </Box>
    </Paper>
  );
};

export default AdvancedAssetBrowser;