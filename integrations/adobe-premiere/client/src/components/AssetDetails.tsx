import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  IconButton,
  TextField,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  CircularProgress,
  Alert,
  Paper,
  Tooltip,
  Grid,
} from '@mui/material';
import {
  ArrowBack,
  Edit,
  Save,
  Cancel,
  GetApp,
  Timeline,
  ContentCopy,
  Label,
  VideoLibrary,
  Image,
  AudioFile,
  Description,
  DateRange,
  Storage,
  Code,
  AspectRatio,
  Speed,
} from '@mui/icons-material';
import { Asset } from '../types';
import { MAMSClient } from '../services/mamsClient';

interface AssetDetailsProps {
  asset: Asset;
  onImport: (asset: Asset) => void;
  onClose: () => void;
}

const AssetDetails: React.FC<AssetDetailsProps> = ({
  asset,
  onImport,
  onClose,
}) => {
  const [metadata, setMetadata] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editedData, setEditedData] = useState({
    description: '',
    tags: [] as string[],
  });

  useEffect(() => {
    loadMetadata();
  }, [asset.id]);

  const loadMetadata = async () => {
    try {
      setLoading(true);
      const data = await MAMSClient.getInstance().getAssetMetadata(asset.id);
      setMetadata(data);
      setEditedData({
        description: data.description || '',
        tags: data.tags || [],
      });
    } catch (err) {
      setError('Failed to load metadata');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      await MAMSClient.getInstance().updateAssetMetadata(asset.id, editedData);
      setMetadata({ ...metadata, ...editedData });
      setEditing(false);
    } catch (err) {
      setError('Failed to save changes');
    }
  };

  const handleCopyPath = () => {
    navigator.clipboard.writeText(asset.url);
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getAssetIcon = () => {
    switch (asset.type) {
      case 'video':
        return <VideoLibrary />;
      case 'image':
        return <Image />;
      case 'audio':
        return <AudioFile />;
      default:
        return <Description />;
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton onClick={onClose} sx={{ mr: 2 }}>
          <ArrowBack />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center' }}>
            {getAssetIcon()}
            <Box component="span" sx={{ ml: 1 }}>
              {asset.name}
            </Box>
          </Typography>
        </Box>
        {!editing ? (
          <IconButton onClick={() => setEditing(true)}>
            <Edit />
          </IconButton>
        ) : (
          <>
            <IconButton onClick={handleSave} color="primary">
              <Save />
            </IconButton>
            <IconButton onClick={() => setEditing(false)}>
              <Cancel />
            </IconButton>
          </>
        )}
      </Box>

      {/* Actions */}
      <Box sx={{ mb: 3 }}>
        <Button
          variant="contained"
          startIcon={<GetApp />}
          onClick={() => onImport(asset)}
          sx={{ mr: 1 }}
        >
          Import to Project
        </Button>
        <Button
          variant="outlined"
          startIcon={<Timeline />}
          onClick={() => onImport(asset)}
          sx={{ mr: 1 }}
        >
          Import to Timeline
        </Button>
        <Button
          variant="outlined"
          startIcon={<ContentCopy />}
          onClick={handleCopyPath}
        >
          Copy Path
        </Button>
      </Box>

      <Divider sx={{ mb: 3 }} />

      {/* Metadata Grid */}
      <Grid container spacing={3}>
        {/* Basic Information */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Basic Information
            </Typography>
            <List dense>
              <ListItem>
                <ListItemIcon>
                  <Storage />
                </ListItemIcon>
                <ListItemText
                  primary="File Size"
                  secondary={formatFileSize(asset.size)}
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <Code />
                </ListItemIcon>
                <ListItemText
                  primary="Format"
                  secondary={metadata?.format || 'Unknown'}
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <DateRange />
                </ListItemIcon>
                <ListItemText
                  primary="Created"
                  secondary={formatDate(asset.createdAt)}
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <DateRange />
                </ListItemIcon>
                <ListItemText
                  primary="Modified"
                  secondary={formatDate(asset.updatedAt)}
                />
              </ListItem>
            </List>
          </Paper>
        </Grid>

        {/* Technical Details */}
        {asset.type === 'video' && (
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Video Details
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemIcon>
                    <AspectRatio />
                  </ListItemIcon>
                  <ListItemText
                    primary="Resolution"
                    secondary={metadata?.resolution || 'Unknown'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <Speed />
                  </ListItemIcon>
                  <ListItemText
                    primary="Frame Rate"
                    secondary={metadata?.framerate ? `${metadata.framerate} fps` : 'Unknown'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <Code />
                  </ListItemIcon>
                  <ListItemText
                    primary="Codec"
                    secondary={metadata?.codec || 'Unknown'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <Storage />
                  </ListItemIcon>
                  <ListItemText
                    primary="Bitrate"
                    secondary={metadata?.bitrate ? `${metadata.bitrate} Mbps` : 'Unknown'}
                  />
                </ListItem>
              </List>
            </Paper>
          </Grid>
        )}

        {/* Description */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Description
            </Typography>
            {editing ? (
              <TextField
                fullWidth
                multiline
                rows={3}
                value={editedData.description}
                onChange={(e) => setEditedData({ ...editedData, description: e.target.value })}
                placeholder="Add a description..."
              />
            ) : (
              <Typography variant="body2" color={metadata?.description ? 'text.primary' : 'text.secondary'}>
                {metadata?.description || 'No description available'}
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* Tags */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Tags
            </Typography>
            {editing ? (
              <TextField
                fullWidth
                value={editedData.tags.join(', ')}
                onChange={(e) => setEditedData({
                  ...editedData,
                  tags: e.target.value.split(',').map(t => t.trim()).filter(t => t)
                })}
                placeholder="Enter tags separated by commas..."
                helperText="Separate tags with commas"
              />
            ) : (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {metadata?.tags && metadata.tags.length > 0 ? (
                  metadata.tags.map((tag: string, index: number) => (
                    <Chip
                      key={index}
                      label={tag}
                      icon={<Label />}
                      variant="outlined"
                    />
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No tags
                  </Typography>
                )}
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Custom Metadata */}
        {metadata?.custom && Object.keys(metadata.custom).length > 0 && (
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Custom Metadata
              </Typography>
              <List dense>
                {Object.entries(metadata.custom).map(([key, value]) => (
                  <ListItem key={key}>
                    <ListItemText
                      primary={key}
                      secondary={String(value)}
                    />
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default AssetDetails;