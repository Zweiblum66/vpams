import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Tabs,
  Tab,
  Chip,
  Button,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  Breadcrumbs,
  Link,
  Menu,
  MenuItem,
  Tooltip,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Edit as EditIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  Delete as DeleteIcon,
  MoreVert as MoreIcon,
  Info as InfoIcon,
  History as HistoryIcon,
  Folder as FolderIcon,
  Person as PersonIcon,
  CalendarToday as DateIcon,
  Storage as SizeIcon,
  VideoLibrary as VideoIcon,
  AudioFile as AudioIcon,
  Image as ImageIcon,
  Description as DocumentIcon,
  Lock as LockIcon,
  LockOpen as UnlockIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';

import VideoPlayer from '../components/media/VideoPlayer';
import AdvancedVideoPlayer from '../components/media/AdvancedVideoPlayer';
import AudioPlayer from '../components/media/AudioPlayer';
import WaveformPlayer from '../components/media/WaveformPlayer';
import ImageViewer from '../components/media/ImageViewer';
import DocumentViewer from '../components/media/DocumentViewer';
import { assetApi } from '../services/assetApi';
import { Asset, AssetType, AssetStatus, AssetUpdateRequest } from '../types/asset';
import { formatFileSize, formatDuration, formatDate } from '../utils/formatters';
import { logger } from '../utils/logger';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`asset-tabpanel-${index}`}
      aria-labelledby={`asset-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
};

const AssetDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [asset, setAsset] = useState<Asset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [moreMenuAnchor, setMoreMenuAnchor] = useState<null | HTMLElement>(null);
  const [editForm, setEditForm] = useState<AssetUpdateRequest>({});
  const [tagInput, setTagInput] = useState('');

  useEffect(() => {
    if (id) {
      loadAsset();
    }
  }, [id]);

  const loadAsset = async () => {
    if (!id) return;
    
    try {
      setLoading(true);
      setError(null);
      const data = await assetApi.getAsset(id);
      setAsset(data);
      setEditForm({
        name: data.name,
        tags: data.tags,
        metadata: data.metadata,
      });
      logger.info('Asset loaded', {
        assetId: id,
        assetType: data.type,
        actionType: 'asset_detail_view',
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load asset';
      setError(errorMessage);
      logger.error('Failed to load asset', {
        assetId: id,
        error: err,
        actionType: 'asset_detail_error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleDownload = async () => {
    if (!asset) return;
    
    try {
      const blob = await assetApi.downloadAsset(asset.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = asset.fileName;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      logger.info('Asset downloaded', {
        assetId: asset.id,
        fileName: asset.fileName,
        actionType: 'asset_download',
      });
    } catch (err) {
      logger.error('Failed to download asset', {
        assetId: asset.id,
        error: err,
        actionType: 'asset_download_error',
      });
    }
  };

  const handleEdit = async () => {
    if (!asset) return;
    
    try {
      const updated = await assetApi.updateAsset(asset.id, editForm);
      setAsset(updated);
      setEditDialogOpen(false);
      
      logger.info('Asset updated', {
        assetId: asset.id,
        changes: editForm,
        actionType: 'asset_update',
      });
    } catch (err) {
      logger.error('Failed to update asset', {
        assetId: asset.id,
        error: err,
        actionType: 'asset_update_error',
      });
    }
  };

  const handleDelete = async () => {
    if (!asset) return;
    
    try {
      await assetApi.deleteAsset(asset.id);
      logger.info('Asset deleted', {
        assetId: asset.id,
        actionType: 'asset_delete',
      });
      navigate('/assets');
    } catch (err) {
      logger.error('Failed to delete asset', {
        assetId: asset.id,
        error: err,
        actionType: 'asset_delete_error',
      });
    }
  };

  const handleAddTag = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && tagInput.trim()) {
      event.preventDefault();
      const newTag = tagInput.trim();
      if (!editForm.tags?.includes(newTag)) {
        setEditForm({
          ...editForm,
          tags: [...(editForm.tags || []), newTag],
        });
      }
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setEditForm({
      ...editForm,
      tags: editForm.tags?.filter((tag) => tag !== tagToRemove) || [],
    });
  };

  const getAssetIcon = (type: AssetType) => {
    switch (type) {
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

  const getStatusColor = (status: AssetStatus) => {
    switch (status) {
      case AssetStatus.READY:
        return 'success';
      case AssetStatus.PROCESSING:
        return 'info';
      case AssetStatus.ERROR:
        return 'error';
      case AssetStatus.ARCHIVED:
        return 'warning';
      default:
        return 'default';
    }
  };

  const renderMediaPreview = () => {
    if (!asset) return null;

    switch (asset.type) {
      case AssetType.VIDEO:
        return (
          <AdvancedVideoPlayer
            asset={asset}
            height={500}
            onMarkerAdd={(time, text) => {
              logger.info('Marker added', { time, text });
              // TODO: Save marker to backend
            }}
            onTrimExport={(start, end) => {
              logger.info('Trim export requested', { start, end });
              // TODO: Implement trim export functionality
            }}
          />
        );
      case AssetType.AUDIO:
        return (
          <WaveformPlayer
            asset={asset}
            height={200}
            onMarkerAdd={(time, text) => {
              logger.info('Audio marker added', { time, text });
              // TODO: Save marker to backend
            }}
            onTrimExport={(start, end) => {
              logger.info('Audio trim export requested', { start, end });
              // TODO: Implement audio trim export functionality
            }}
            onRegionCreate={(region) => {
              logger.info('Audio region created', region);
              // TODO: Save region to backend
            }}
          />
        );
      case AssetType.IMAGE:
        return (
          <ImageViewer
            src={asset.previewUrl || asset.originalUrl}
            alt={asset.name}
            title={asset.name}
            height={500}
            onDownload={handleDownload}
          />
        );
      case AssetType.DOCUMENT:
        return (
          <DocumentViewer
            src={asset.previewUrl || asset.originalUrl}
            title={asset.name}
            type={asset.metadata.format}
            height={500}
            onDownload={handleDownload}
          />
        );
      default:
        return (
          <Box
            sx={{
              height: 300,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'grey.100',
              borderRadius: 2,
            }}
          >
            <Typography variant="h6" color="text.secondary">
              Preview not available
            </Typography>
          </Box>
        );
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !asset) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">
          {error || 'Asset not found'}
        </Alert>
        <Button
          startIcon={<BackIcon />}
          onClick={() => navigate('/assets')}
          sx={{ mt: 2 }}
        >
          Back to Assets
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Breadcrumb */}
      <Breadcrumbs sx={{ mb: 3 }}>
        <Link component={RouterLink} to="/" color="inherit">
          Home
        </Link>
        <Link component={RouterLink} to="/assets" color="inherit">
          Assets
        </Link>
        <Typography color="text.primary">{asset.name}</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <IconButton onClick={() => navigate('/assets')}>
            <BackIcon />
          </IconButton>
          
          <Box sx={{ flex: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              {getAssetIcon(asset.type)}
              <Typography variant="h4">{asset.name}</Typography>
              <Chip
                label={asset.status}
                size="small"
                color={getStatusColor(asset.status) as any}
              />
            </Box>
            <Typography variant="body2" color="text.secondary">
              {asset.fileName} • {formatFileSize(asset.fileSize)}
            </Typography>
          </Box>

          {/* Actions */}
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="contained"
              startIcon={<DownloadIcon />}
              onClick={handleDownload}
              disabled={!asset.permissions.canDownload}
            >
              Download
            </Button>
            <Button
              variant="outlined"
              startIcon={<ShareIcon />}
              onClick={() => setShareDialogOpen(true)}
              disabled={!asset.permissions.canShare}
            >
              Share
            </Button>
            <IconButton onClick={(e) => setMoreMenuAnchor(e.currentTarget)}>
              <MoreIcon />
            </IconButton>
          </Box>
        </Box>

        {/* Tags */}
        {asset.tags.length > 0 && (
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {asset.tags.map((tag) => (
              <Chip key={tag} label={tag} size="small" />
            ))}
          </Box>
        )}
      </Paper>

      {/* Main Content */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            {renderMediaPreview()}
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Tabs value={tabValue} onChange={handleTabChange}>
              <Tab label="Details" />
              <Tab label="Metadata" />
              <Tab label="History" />
            </Tabs>

            <TabPanel value={tabValue} index={0}>
              <List>
                <ListItem>
                  <ListItemIcon>
                    <PersonIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Created by"
                    secondary={asset.createdBy}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <DateIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Created on"
                    secondary={formatDate(asset.createdAt)}
                  />
                </ListItem>
                {asset.updatedBy && (
                  <ListItem>
                    <ListItemIcon>
                      <PersonIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary="Last modified by"
                      secondary={asset.updatedBy}
                    />
                  </ListItem>
                )}
                <ListItem>
                  <ListItemIcon>
                    <DateIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Last modified"
                    secondary={formatDate(asset.updatedAt)}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <SizeIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="File size"
                    secondary={formatFileSize(asset.fileSize)}
                  />
                </ListItem>
                {asset.duration && (
                  <ListItem>
                    <ListItemIcon>
                      <HistoryIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary="Duration"
                      secondary={formatDuration(asset.duration)}
                    />
                  </ListItem>
                )}
                {asset.dimensions && (
                  <ListItem>
                    <ListItemIcon>
                      <ImageIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary="Dimensions"
                      secondary={`${asset.dimensions.width} × ${asset.dimensions.height} px`}
                    />
                  </ListItem>
                )}
              </List>
            </TabPanel>

            <TabPanel value={tabValue} index={1}>
              <List>
                <ListItem>
                  <ListItemText
                    primary="MIME Type"
                    secondary={asset.mimeType}
                  />
                </ListItem>
                {asset.metadata.format && (
                  <ListItem>
                    <ListItemText
                      primary="Format"
                      secondary={asset.metadata.format}
                    />
                  </ListItem>
                )}
                {asset.metadata.codec && (
                  <ListItem>
                    <ListItemText
                      primary="Codec"
                      secondary={asset.metadata.codec}
                    />
                  </ListItem>
                )}
                {asset.metadata.bitrate && (
                  <ListItem>
                    <ListItemText
                      primary="Bitrate"
                      secondary={`${(asset.metadata.bitrate / 1000).toFixed(0)} kbps`}
                    />
                  </ListItem>
                )}
                {asset.metadata.frameRate && (
                  <ListItem>
                    <ListItemText
                      primary="Frame Rate"
                      secondary={`${asset.metadata.frameRate} fps`}
                    />
                  </ListItem>
                )}
                {asset.metadata.sampleRate && (
                  <ListItem>
                    <ListItemText
                      primary="Sample Rate"
                      secondary={`${asset.metadata.sampleRate} Hz`}
                    />
                  </ListItem>
                )}
                {asset.metadata.channels && (
                  <ListItem>
                    <ListItemText
                      primary="Channels"
                      secondary={asset.metadata.channels === 2 ? 'Stereo' : `${asset.metadata.channels} channels`}
                    />
                  </ListItem>
                )}
              </List>
            </TabPanel>

            <TabPanel value={tabValue} index={2}>
              {asset.versions && asset.versions.length > 0 ? (
                <List>
                  {asset.versions.map((version) => (
                    <ListItem key={version.id}>
                      <ListItemText
                        primary={`Version ${version.version}`}
                        secondary={
                          <>
                            {version.comment && <>{version.comment} • </>}
                            {formatDate(version.createdAt)} by {version.createdBy}
                          </>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No version history available
                </Typography>
              )}
            </TabPanel>
          </Paper>
        </Grid>
      </Grid>

      {/* More Menu */}
      <Menu
        anchorEl={moreMenuAnchor}
        open={Boolean(moreMenuAnchor)}
        onClose={() => setMoreMenuAnchor(null)}
      >
        <MenuItem
          onClick={() => {
            setEditDialogOpen(true);
            setMoreMenuAnchor(null);
          }}
          disabled={!asset.permissions.canEdit}
        >
          <EditIcon sx={{ mr: 1 }} />
          Edit Details
        </MenuItem>
        <MenuItem
          onClick={() => {
            navigator.clipboard.writeText(window.location.href);
            setMoreMenuAnchor(null);
          }}
        >
          <CopyIcon sx={{ mr: 1 }} />
          Copy Link
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={() => {
            setDeleteDialogOpen(true);
            setMoreMenuAnchor(null);
          }}
          disabled={!asset.permissions.canDelete}
        >
          <DeleteIcon sx={{ mr: 1 }} color="error" />
          Delete Asset
        </MenuItem>
      </Menu>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Asset Details</DialogTitle>
        <DialogContent>
          <TextField
            label="Name"
            fullWidth
            value={editForm.name || ''}
            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
            margin="normal"
          />
          <Box sx={{ mt: 2 }}>
            <TextField
              label="Add Tags"
              fullWidth
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleAddTag}
              helperText="Press Enter to add tags"
            />
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
              {editForm.tags?.map((tag) => (
                <Chip
                  key={tag}
                  label={tag}
                  onDelete={() => handleRemoveTag(tag)}
                />
              ))}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleEdit} variant="contained">
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Asset</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{asset.name}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Share Dialog */}
      <Dialog open={shareDialogOpen} onClose={() => setShareDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Share Asset</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Share this asset with others by copying the link below:
          </Typography>
          <TextField
            fullWidth
            value={window.location.href}
            margin="normal"
            InputProps={{
              readOnly: true,
              endAdornment: (
                <IconButton
                  onClick={() => {
                    navigator.clipboard.writeText(window.location.href);
                  }}
                >
                  <CopyIcon />
                </IconButton>
              ),
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShareDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default AssetDetail;