import React, { useState, useCallback, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Card,
  CardContent,
  CardMedia,
  Grid,
  Chip,
  Menu,
  MenuItem,
  Divider,
  Alert,
  Snackbar,
  LinearProgress,
  Badge,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  ListItemSecondaryAction,
  Avatar,
  Skeleton,
  FormControl,
  InputLabel,
  Select,
  SelectChangeEvent,
  Switch,
  FormControlLabel,
  Slider,
  Stack,
} from '@mui/material';
import {
  Add,
  Delete,
  Edit,
  DragIndicator,
  PlayArrow,
  Pause,
  ContentCopy,
  GetApp,
  FileUpload,
  Search,
  FilterList,
  ViewList,
  ViewModule,
  MoreVert,
  Schedule,
  Movie,
  Image,
  AudioFile,
  Description,
  Palette,
  Visibility,
  VisibilityOff,
  Timer,
  Straighten,
} from '@mui/icons-material';
import { DragDropContext, Droppable, Draggable, DropResult } from 'react-beautiful-dnd';
import { useParams } from 'react-router-dom';
import {
  useGetShotlistItemsQuery,
  useCreateShotlistItemMutation,
  useUpdateShotlistItemMutation,
  useDeleteShotlistItemMutation,
  useReorderShotlistItemsMutation,
  useDuplicateShotlistItemMutation,
  useAddAssetsToShotlistMutation,
  useGetShotlistStatsQuery,
  useExportShotlistMutation,
  useImportShotlistMutation,
} from '../../store/api/shotlistApi';
import { InOutPointSelector } from '../media';
import { useGetAssetsQuery } from '../../store/api/assetApi';
import { ShotlistItem, Asset, CreateShotlistItemRequest } from '../../types';

interface ShotlistBuilderProps {
  shotlistId: string;
  projectId: string;
  onItemSelect?: (item: ShotlistItem) => void;
  selectedItems?: string[];
  readOnly?: boolean;
}

interface ShotlistItemFormData {
  asset_id: string;
  in_point: number;
  out_point: number;
  title: string;
  description: string;
  notes: string;
  color: string;
}

const COLORS = [
  '#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5',
  '#2196f3', '#03a9f4', '#00bcd4', '#009688', '#4caf50',
  '#8bc34a', '#cddc39', '#ffeb3b', '#ffc107', '#ff9800',
  '#ff5722', '#795548', '#9e9e9e', '#607d8b', '#000000'
];

const ShotlistBuilder: React.FC<ShotlistBuilderProps> = ({
  shotlistId,
  projectId,
  onItemSelect,
  selectedItems = [],
  readOnly = false,
}) => {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showAssetSelector, setShowAssetSelector] = useState(false);
  const [showInOutSelector, setShowInOutSelector] = useState(false);
  const [editingItem, setEditingItem] = useState<ShotlistItem | null>(null);
  const [selectedAssets, setSelectedAssets] = useState<string[]>([]);
  const [selectedAssetForInOut, setSelectedAssetForInOut] = useState<Asset | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [filterBy, setFilterBy] = useState('all');
  const [sortBy, setSortBy] = useState('order');
  const [contextMenuAnchor, setContextMenuAnchor] = useState<null | HTMLElement>(null);
  const [contextMenuItem, setContextMenuItem] = useState<ShotlistItem | null>(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'info' });
  const [formData, setFormData] = useState<ShotlistItemFormData>({
    asset_id: '',
    in_point: 0,
    out_point: 0,
    title: '',
    description: '',
    notes: '',
    color: COLORS[0],
  });

  // API hooks
  const { data: shotlistItems, isLoading: itemsLoading, error: itemsError } = useGetShotlistItemsQuery(shotlistId);
  const { data: assets } = useGetAssetsQuery({ project_id: projectId });
  const { data: stats } = useGetShotlistStatsQuery(shotlistId);
  const [createShotlistItem] = useCreateShotlistItemMutation();
  const [updateShotlistItem] = useUpdateShotlistItemMutation();
  const [deleteShotlistItem] = useDeleteShotlistItemMutation();
  const [reorderShotlistItems] = useReorderShotlistItemsMutation();
  const [duplicateShotlistItem] = useDuplicateShotlistItemMutation();
  const [addAssetsToShotlist] = useAddAssetsToShotlistMutation();
  const [exportShotlist] = useExportShotlistMutation();

  // Filtered and sorted items
  const filteredItems = useMemo(() => {
    if (!shotlistItems) return [];
    
    let filtered = [...shotlistItems];
    
    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(item => 
        item.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.notes?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.asset.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    
    // Filter by type
    if (filterBy !== 'all') {
      filtered = filtered.filter(item => item.asset.asset_type === filterBy);
    }
    
    // Sort items
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'order':
          return a.order - b.order;
        case 'title':
          return (a.title || '').localeCompare(b.title || '');
        case 'duration':
          return a.duration - b.duration;
        case 'created_at':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        default:
          return 0;
      }
    });
    
    return filtered;
  }, [shotlistItems, searchTerm, filterBy, sortBy]);

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

  const handleCreateItem = useCallback(async () => {
    if (!formData.asset_id) return;
    
    try {
      const newItem: CreateShotlistItemRequest = {
        asset_id: formData.asset_id,
        in_point: formData.in_point,
        out_point: formData.out_point,
        title: formData.title,
        description: formData.description,
        notes: formData.notes,
        color: formData.color,
      };
      
      await createShotlistItem({ shotlistId, item: newItem }).unwrap();
      setShowAddDialog(false);
      setFormData({
        asset_id: '',
        in_point: 0,
        out_point: 0,
        title: '',
        description: '',
        notes: '',
        color: COLORS[0],
      });
      setSnackbar({ open: true, message: 'Shot added successfully', severity: 'success' });
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to add shot', severity: 'error' });
    }
  }, [formData, shotlistId, createShotlistItem]);

  const handleUpdateItem = useCallback(async () => {
    if (!editingItem) return;
    
    try {
      await updateShotlistItem({
        shotlistId,
        item: {
          id: editingItem.id,
          in_point: formData.in_point,
          out_point: formData.out_point,
          title: formData.title,
          description: formData.description,
          notes: formData.notes,
          color: formData.color,
        },
      }).unwrap();
      setShowEditDialog(false);
      setEditingItem(null);
      setSnackbar({ open: true, message: 'Shot updated successfully', severity: 'success' });
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to update shot', severity: 'error' });
    }
  }, [editingItem, formData, shotlistId, updateShotlistItem]);

  const handleDeleteItem = useCallback(async (itemId: string) => {
    try {
      await deleteShotlistItem({ shotlistId, itemId }).unwrap();
      setSnackbar({ open: true, message: 'Shot deleted successfully', severity: 'success' });
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to delete shot', severity: 'error' });
    }
  }, [shotlistId, deleteShotlistItem]);

  const handleDuplicateItem = useCallback(async (itemId: string) => {
    try {
      await duplicateShotlistItem({ shotlistId, itemId }).unwrap();
      setSnackbar({ open: true, message: 'Shot duplicated successfully', severity: 'success' });
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to duplicate shot', severity: 'error' });
    }
  }, [shotlistId, duplicateShotlistItem]);

  const handleDragEnd = useCallback(async (result: DropResult) => {
    if (!result.destination || !shotlistItems) return;
    
    const items = Array.from(shotlistItems);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);
    
    const reorderData = items.map((item, index) => ({
      id: item.id,
      new_order: index + 1,
    }));
    
    try {
      await reorderShotlistItems({ shotlistId, items: reorderData }).unwrap();
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to reorder shots', severity: 'error' });
    }
  }, [shotlistItems, shotlistId, reorderShotlistItems]);

  const handleAddAssetsToShotlist = useCallback(async () => {
    if (selectedAssets.length === 0) return;
    
    try {
      await addAssetsToShotlist({ shotlistId, assetIds: selectedAssets }).unwrap();
      setSelectedAssets([]);
      setShowAssetSelector(false);
      setSnackbar({ open: true, message: `${selectedAssets.length} assets added to shotlist`, severity: 'success' });
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to add assets to shotlist', severity: 'error' });
    }
  }, [selectedAssets, shotlistId, addAssetsToShotlist]);

  const handleOpenInOutSelector = useCallback((asset: Asset) => {
    setSelectedAssetForInOut(asset);
    setShowInOutSelector(true);
  }, []);

  const handleInOutPointChange = useCallback((inPoint: number, outPoint: number) => {
    setFormData(prev => ({
      ...prev,
      in_point: inPoint,
      out_point: outPoint,
    }));
  }, []);

  const handleExport = useCallback(async (format: 'aaf' | 'xml' | 'edl' | 'otio' | 'csv') => {
    try {
      const blob = await exportShotlist({
        shotlist_id: shotlistId,
        format,
        include_metadata: true,
        include_thumbnails: true,
      }).unwrap();
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `shotlist_${shotlistId}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      
      setSnackbar({ open: true, message: 'Shotlist exported successfully', severity: 'success' });
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to export shotlist', severity: 'error' });
    }
  }, [shotlistId, exportShotlist]);

  const handleContextMenu = useCallback((event: React.MouseEvent<HTMLElement>, item: ShotlistItem) => {
    event.preventDefault();
    setContextMenuAnchor(event.currentTarget);
    setContextMenuItem(item);
  }, []);

  const handleContextMenuClose = useCallback(() => {
    setContextMenuAnchor(null);
    setContextMenuItem(null);
  }, []);

  const handleEditItem = useCallback((item: ShotlistItem) => {
    setEditingItem(item);
    setFormData({
      asset_id: item.asset_id,
      in_point: item.in_point,
      out_point: item.out_point,
      title: item.title || '',
      description: item.description || '',
      notes: item.notes || '',
      color: item.color || COLORS[0],
    });
    setShowEditDialog(true);
    handleContextMenuClose();
  }, [handleContextMenuClose]);

  const renderShotlistItem = useCallback((item: ShotlistItem, index: number) => {
    const isSelected = selectedItems.includes(item.id);
    const assetTypeIcon = {
      video: <Movie />,
      audio: <AudioFile />,
      image: <Image />,
      document: <Description />,
      other: <Description />,
    }[item.asset.asset_type];

    return (
      <Draggable key={item.id} draggableId={item.id} index={index} isDragDisabled={readOnly}>
        {(provided, snapshot) => (
          <Card
            ref={provided.innerRef}
            {...provided.draggableProps}
            sx={{
              mb: 1,
              opacity: snapshot.isDragging ? 0.8 : 1,
              backgroundColor: isSelected ? 'action.selected' : 'background.paper',
              border: item.color ? `2px solid ${item.color}` : undefined,
            }}
            onClick={() => onItemSelect?.(item)}
            onContextMenu={(e) => !readOnly && handleContextMenu(e, item)}
          >
            <CardContent sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {!readOnly && (
                  <Box {...provided.dragHandleProps}>
                    <DragIndicator sx={{ color: 'text.secondary' }} />
                  </Box>
                )}
                
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="h6" sx={{ minWidth: 30 }}>
                    {item.order}
                  </Typography>
                  {assetTypeIcon}
                </Box>
                
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 'medium' }}>
                    {item.title || item.asset.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {item.asset.name} • {formatDuration(item.duration)}
                  </Typography>
                  {item.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      {item.description}
                    </Typography>
                  )}
                </Box>
                
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip
                    label={`${formatTimecode(item.in_point)} - ${formatTimecode(item.out_point)}`}
                    size="small"
                    variant="outlined"
                  />
                  <Typography variant="body2" color="text.secondary">
                    {formatDuration(item.duration)}
                  </Typography>
                  {!readOnly && (
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleContextMenu(e, item);
                      }}
                    >
                      <MoreVert />
                    </IconButton>
                  )}
                </Box>
              </Box>
            </CardContent>
          </Card>
        )}
      </Draggable>
    );
  }, [selectedItems, onItemSelect, handleContextMenu, readOnly]);

  const renderAssetSelector = useCallback(() => (
    <Dialog open={showAssetSelector} onClose={() => setShowAssetSelector(false)} maxWidth="md" fullWidth>
      <DialogTitle>Add Assets to Shotlist</DialogTitle>
      <DialogContent>
        <Grid container spacing={2}>
          {assets?.data.map((asset) => (
            <Grid item xs={12} sm={6} md={4} key={asset.id}>
              <Card
                sx={{
                  cursor: 'pointer',
                  backgroundColor: selectedAssets.includes(asset.id) ? 'action.selected' : 'background.paper',
                }}
                onClick={() => {
                  setSelectedAssets(prev => 
                    prev.includes(asset.id) 
                      ? prev.filter(id => id !== asset.id)
                      : [...prev, asset.id]
                  );
                }}
              >
                <CardMedia
                  component="img"
                  height="120"
                  image={asset.thumbnail_path || '/placeholder.jpg'}
                  alt={asset.name}
                />
                <CardContent>
                  <Typography variant="subtitle2">{asset.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {asset.asset_type} • {asset.duration ? formatDuration(asset.duration) : 'N/A'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setShowAssetSelector(false)}>Cancel</Button>
        <Button onClick={handleAddAssetsToShotlist} variant="contained">
          Add {selectedAssets.length} Assets
        </Button>
      </DialogActions>
    </Dialog>
  ), [showAssetSelector, assets, selectedAssets, handleAddAssetsToShotlist]);

  if (itemsLoading) {
    return (
      <Box sx={{ p: 3 }}>
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} variant="rectangular" height={80} sx={{ mb: 1 }} />
        ))}
      </Box>
    );
  }

  if (itemsError) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        Failed to load shotlist items. Please try again.
      </Alert>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Shotlist Builder</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {!readOnly && (
              <>
                <Button
                  variant="contained"
                  startIcon={<Add />}
                  onClick={() => setShowAddDialog(true)}
                >
                  Add Shot
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Add />}
                  onClick={() => setShowAssetSelector(true)}
                >
                  Add Assets
                </Button>
              </>
            )}
            <Button
              variant="outlined"
              startIcon={<GetApp />}
              onClick={() => handleExport('xml')}
            >
              Export
            </Button>
          </Box>
        </Box>

        {/* Stats */}
        {stats && (
          <Box sx={{ display: 'flex', gap: 3, mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              {stats.total_items} shots
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Total duration: {formatDuration(stats.total_duration)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Average: {formatDuration(stats.avg_duration)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {stats.unique_assets} unique assets
            </Typography>
          </Box>
        )}

        {/* Controls */}
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <TextField
            size="small"
            placeholder="Search shots..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: <Search sx={{ mr: 1 }} />,
            }}
            sx={{ minWidth: 200 }}
          />
          
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Filter by</InputLabel>
            <Select
              value={filterBy}
              onChange={(e) => setFilterBy(e.target.value)}
              label="Filter by"
            >
              <MenuItem value="all">All Types</MenuItem>
              <MenuItem value="video">Video</MenuItem>
              <MenuItem value="audio">Audio</MenuItem>
              <MenuItem value="image">Image</MenuItem>
              <MenuItem value="document">Document</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Sort by</InputLabel>
            <Select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              label="Sort by"
            >
              <MenuItem value="order">Order</MenuItem>
              <MenuItem value="title">Title</MenuItem>
              <MenuItem value="duration">Duration</MenuItem>
              <MenuItem value="created_at">Created</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="List View">
              <IconButton
                size="small"
                color={viewMode === 'list' ? 'primary' : 'default'}
                onClick={() => setViewMode('list')}
              >
                <ViewList />
              </IconButton>
            </Tooltip>
            <Tooltip title="Grid View">
              <IconButton
                size="small"
                color={viewMode === 'grid' ? 'primary' : 'default'}
                onClick={() => setViewMode('grid')}
              >
                <ViewModule />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
      </Paper>

      {/* Shotlist Items */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {filteredItems.length === 0 ? (
          <Alert severity="info" sx={{ m: 2 }}>
            No shots found. {!readOnly && 'Click "Add Shot" to get started.'}
          </Alert>
        ) : (
          <DragDropContext onDragEnd={handleDragEnd}>
            <Droppable droppableId="shotlist">
              {(provided) => (
                <Box
                  {...provided.droppableProps}
                  ref={provided.innerRef}
                  sx={{ p: 2 }}
                >
                  {filteredItems.map((item, index) => renderShotlistItem(item, index))}
                  {provided.placeholder}
                </Box>
              )}
            </Droppable>
          </DragDropContext>
        )}
      </Box>

      {/* Add/Edit Dialog */}
      <Dialog open={showAddDialog || showEditDialog} onClose={() => {
        setShowAddDialog(false);
        setShowEditDialog(false);
        setEditingItem(null);
      }} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingItem ? 'Edit Shot' : 'Add Shot'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            {!editingItem && (
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Asset</InputLabel>
                  <Select
                    value={formData.asset_id}
                    onChange={(e) => setFormData({ ...formData, asset_id: e.target.value })}
                    label="Asset"
                  >
                    {assets?.data.map((asset) => (
                      <MenuItem key={asset.id} value={asset.id}>
                        {asset.name} ({asset.asset_type})
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            )}
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="In Point (seconds)"
                type="number"
                value={formData.in_point}
                onChange={(e) => setFormData({ ...formData, in_point: Number(e.target.value) })}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Out Point (seconds)"
                type="number"
                value={formData.out_point}
                onChange={(e) => setFormData({ ...formData, out_point: Number(e.target.value) })}
              />
            </Grid>
            
            <Grid item xs={12}>
              <Button
                variant="outlined"
                onClick={() => {
                  const asset = assets?.data.find(a => a.id === formData.asset_id);
                  if (asset && asset.asset_type === 'video') {
                    handleOpenInOutSelector(asset);
                  }
                }}
                disabled={!formData.asset_id || !assets?.data.find(a => a.id === formData.asset_id && a.asset_type === 'video')}
                startIcon={<ContentCut />}
                fullWidth
              >
                Set In/Out Points with Video Player
              </Button>
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                multiline
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Notes"
                multiline
                rows={2}
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              />
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>Color</Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {COLORS.map((color) => (
                  <Box
                    key={color}
                    sx={{
                      width: 32,
                      height: 32,
                      backgroundColor: color,
                      border: formData.color === color ? '3px solid #000' : '1px solid #ccc',
                      cursor: 'pointer',
                      borderRadius: 1,
                    }}
                    onClick={() => setFormData({ ...formData, color })}
                  />
                ))}
              </Box>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setShowAddDialog(false);
            setShowEditDialog(false);
            setEditingItem(null);
          }}>
            Cancel
          </Button>
          <Button
            onClick={editingItem ? handleUpdateItem : handleCreateItem}
            variant="contained"
            disabled={!formData.asset_id}
          >
            {editingItem ? 'Update' : 'Add'} Shot
          </Button>
        </DialogActions>
      </Dialog>

      {/* Asset Selector */}
      {renderAssetSelector()}

      {/* Context Menu */}
      <Menu
        anchorEl={contextMenuAnchor}
        open={Boolean(contextMenuAnchor)}
        onClose={handleContextMenuClose}
      >
        <MenuItem onClick={() => contextMenuItem && handleEditItem(contextMenuItem)}>
          <Edit sx={{ mr: 1 }} />
          Edit
        </MenuItem>
        <MenuItem onClick={() => contextMenuItem && handleDuplicateItem(contextMenuItem.id)}>
          <ContentCopy sx={{ mr: 1 }} />
          Duplicate
        </MenuItem>
        <Divider />
        <MenuItem 
          onClick={() => contextMenuItem && handleDeleteItem(contextMenuItem.id)}
          sx={{ color: 'error.main' }}
        >
          <Delete sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>

      {/* In/Out Point Selector Dialog */}
      <Dialog
        open={showInOutSelector}
        onClose={() => setShowInOutSelector(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: { height: '90vh' }
        }}
      >
        <DialogTitle>
          Set In/Out Points
          {selectedAssetForInOut && ` - ${selectedAssetForInOut.name}`}
        </DialogTitle>
        <DialogContent>
          {selectedAssetForInOut && (
            <InOutPointSelector
              asset={selectedAssetForInOut}
              initialInPoint={formData.in_point}
              initialOutPoint={formData.out_point}
              onSelectionChange={handleInOutPointChange}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowInOutSelector(false)}>Cancel</Button>
          <Button
            onClick={() => {
              setShowInOutSelector(false);
              setSnackbar({ open: true, message: 'In/Out points updated', severity: 'success' });
            }}
            variant="contained"
          >
            Apply
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ShotlistBuilder;