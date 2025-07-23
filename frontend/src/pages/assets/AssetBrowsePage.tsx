import React, { useState, useEffect, useCallback } from 'react';
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
} from '@mui/material';
import {
  ViewModule as GridViewIcon,
  ViewList as ListViewIcon,
  Upload as UploadIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  Label as TagIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  CheckBox as SelectAllIcon,
  CheckBoxOutlineBlank as DeselectAllIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

import AssetCard from '../../components/assets/AssetCard';
import AssetListItem from '../../components/assets/AssetListItem';
import AssetFilters from '../../components/assets/AssetFilters';
import { assetApi, AssetApiError } from '../../services/assetApi';
import {
  Asset,
  AssetFilter,
  AssetSort,
  AssetListResponse,
  AssetBulkAction,
} from '../../types/asset';
import { logger } from '../../utils/logger';

type ViewMode = 'grid' | 'list';

const AssetBrowsePage: React.FC = () => {
  const navigate = useNavigate();
  
  // State
  const [assets, setAssets] = useState<Asset[]>([]);
  const [totalAssets, setTotalAssets] = useState(0);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [selectedAssets, setSelectedAssets] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [filter, setFilter] = useState<AssetFilter>({});
  const [sort, setSort] = useState<AssetSort>({ field: 'createdAt', order: 'desc' });
  const [bulkMenuAnchor, setBulkMenuAnchor] = useState<null | HTMLElement>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({ open: false, message: '', severity: 'info' });
  const [availableTags, setAvailableTags] = useState<string[]>([]);

  // Fetch assets
  const fetchAssets = useCallback(async () => {
    try {
      setLoading(true);
      logger.info('Fetching assets', {
        filter,
        sort,
        page,
        pageSize,
        actionType: 'asset_browse_fetch',
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
        actionType: 'asset_browse_fetch_success',
      });
    } catch (error) {
      logger.error('Failed to fetch assets', {
        error,
        actionType: 'asset_browse_fetch_error',
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

  // Handlers
  const handleViewModeChange = (event: React.MouseEvent<HTMLElement>, newMode: ViewMode | null) => {
    if (newMode !== null) {
      setViewMode(newMode);
      logger.info('View mode changed', {
        viewMode: newMode,
        actionType: 'asset_browse_view_mode_change',
      });
    }
  };

  const handleAssetSelect = (assetId: string, selected: boolean) => {
    setSelectedAssets(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(assetId);
      } else {
        newSet.delete(assetId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedAssets.size === assets.length) {
      setSelectedAssets(new Set());
    } else {
      setSelectedAssets(new Set(assets.map(asset => asset.id)));
    }
  };

  const handleAssetClick = (asset: Asset) => {
    navigate(`/assets/${asset.id}`);
  };

  const handleAssetEdit = (asset: Asset) => {
    navigate(`/assets/${asset.id}/edit`);
  };

  const handleAssetDownload = async (asset: Asset) => {
    try {
      logger.info('Downloading asset', {
        assetId: asset.id,
        assetName: asset.name,
        actionType: 'asset_browse_download',
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
        actionType: 'asset_browse_download_error',
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

  const handleBulkDelete = async () => {
    try {
      logger.info('Bulk deleting assets', {
        count: selectedAssets.size,
        actionType: 'asset_browse_bulk_delete',
      });

      const action: AssetBulkAction = {
        action: 'delete',
        assetIds: Array.from(selectedAssets),
      };

      await assetApi.bulkAction(action);

      setSnackbar({
        open: true,
        message: `Deleted ${selectedAssets.size} assets`,
        severity: 'success',
      });

      setSelectedAssets(new Set());
      setDeleteDialogOpen(false);
      fetchAssets();
    } catch (error) {
      logger.error('Failed to delete assets', {
        error,
        actionType: 'asset_browse_bulk_delete_error',
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
      logger.info('Bulk archiving assets', {
        count: selectedAssets.size,
        actionType: 'asset_browse_bulk_archive',
      });

      const action: AssetBulkAction = {
        action: 'archive',
        assetIds: Array.from(selectedAssets),
      };

      await assetApi.bulkAction(action);

      setSnackbar({
        open: true,
        message: `Archived ${selectedAssets.size} assets`,
        severity: 'success',
      });

      setSelectedAssets(new Set());
      setBulkMenuAnchor(null);
      fetchAssets();
    } catch (error) {
      logger.error('Failed to archive assets', {
        error,
        actionType: 'asset_browse_bulk_archive_error',
      });
      
      setSnackbar({
        open: true,
        message: 'Failed to archive assets',
        severity: 'error',
      });
    }
  };

  const handleBulkTag = () => {
    // TODO: Implement bulk tagging
    setSnackbar({
      open: true,
      message: 'Bulk tagging coming soon',
      severity: 'info',
    });
    setBulkMenuAnchor(null);
  };

  const handleBulkDownload = () => {
    // TODO: Implement bulk download
    setSnackbar({
      open: true,
      message: 'Bulk download coming soon',
      severity: 'info',
    });
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

  const totalPages = Math.ceil(totalAssets / pageSize);

  return (
    <Container maxWidth={false} sx={{ py: 3 }}>
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4" component="h1">
            Assets
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            {selectedAssets.size > 0 && (
              <>
                <Chip
                  label={`${selectedAssets.size} selected`}
                  onDelete={() => setSelectedAssets(new Set())}
                  color="primary"
                />
                
                <Button
                  variant="outlined"
                  startIcon={<DeleteIcon />}
                  onClick={() => setBulkMenuAnchor(document.getElementById('bulk-actions-button'))}
                  id="bulk-actions-button"
                >
                  Bulk Actions
                </Button>
              </>
            )}
            
            <Button
              variant="contained"
              startIcon={<UploadIcon />}
              onClick={handleUploadClick}
            >
              Upload
            </Button>
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

      {/* View controls and selection */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" color="text.secondary">
              {totalAssets} assets
            </Typography>
            
            {assets.length > 0 && (
              <Button
                size="small"
                startIcon={selectedAssets.size === assets.length ? <DeselectAllIcon /> : <SelectAllIcon />}
                onClick={handleSelectAll}
              >
                {selectedAssets.size === assets.length ? 'Deselect All' : 'Select All'}
              </Button>
            )}
          </Box>

          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={handleViewModeChange}
            size="small"
          >
            <ToggleButton value="grid">
              <GridViewIcon />
            </ToggleButton>
            <ToggleButton value="list">
              <ListViewIcon />
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Paper>

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
              Upload Asset
            </Button>
          )}
        </Paper>
      ) : viewMode === 'grid' ? (
        <Grid container spacing={3}>
          {assets.map((asset) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={asset.id}>
              <AssetCard
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
              />
            </Grid>
          ))}
        </Grid>
      ) : (
        <Paper>
          <List>
            {assets.map((asset, index) => (
              <React.Fragment key={asset.id}>
                {index > 0 && <Divider />}
                <AssetListItem
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
                />
              </React.Fragment>
            ))}
          </List>
        </Paper>
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
          />
        </Box>
      )}

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
        <MenuItem onClick={handleBulkArchive}>
          <ListItemIcon>
            <ArchiveIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Archive Selected</ListItemText>
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
  );
};

export default AssetBrowsePage;