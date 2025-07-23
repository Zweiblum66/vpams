import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Alert,
  Paper,
  Breadcrumbs,
  Link,
  Chip,
  Stack,
  Button,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Timeline,
  Home,
  Movie,
  Save,
  Undo,
  Redo,
  Settings,
  Share,
  PlayArrow,
  Stop,
  Pause,
  History,
  Add,
  Edit,
  Delete,
  Import,
  Export,
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { TimelineUI } from '../components/timeline';
import { useGetTimelineQuery, useUpdateTimelineMutation } from '../store/api/timelineApi';
import { TimelineTrack, TimelineClip, Asset } from '../types';

interface TimelinePageProps {
  readOnly?: boolean;
}

const TimelinePage: React.FC<TimelinePageProps> = ({ readOnly = false }) => {
  const { timelineId } = useParams<{ timelineId: string }>();
  const navigate = useNavigate();
  
  const [currentTime, setCurrentTime] = useState(0);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [playbackState, setPlaybackState] = useState<'playing' | 'paused' | 'stopped'>('stopped');
  const [showSettings, setShowSettings] = useState(false);
  const [showShareDialog, setShowShareDialog] = useState(false);
  const [autoSave, setAutoSave] = useState(true);
  const [snapToGrid, setSnapToGrid] = useState(true);
  const [rippleEdit, setRippleEdit] = useState(false);
  const [unsavedChanges, setUnsavedChanges] = useState(false);

  // API hooks
  const { data: timeline, isLoading, error } = useGetTimelineQuery(timelineId || '');
  const [updateTimeline] = useUpdateTimelineMutation();

  // Mock data for demonstration
  const mockTracks: TimelineTrack[] = [
    {
      id: 'track-1',
      name: 'Video 1',
      type: 'video',
      visible: true,
      locked: false,
      muted: false,
      solo: false,
      height: 80,
      color: '#2196f3',
      order: 1,
      clips: [
        {
          id: 'clip-1',
          name: 'Opening Scene',
          asset_id: 'asset-1',
          track_id: 'track-1',
          start_time: 0,
          end_time: 10,
          duration: 10,
          in_point: 0,
          out_point: 10,
          speed: 1,
          volume: 1,
          color: '#2196f3',
          effects: [],
          transitions: [],
          asset: {
            id: 'asset-1',
            name: 'opening_scene.mp4',
            asset_type: 'video',
            thumbnail_path: '/thumbnails/opening_scene.jpg',
            duration: 30,
          },
        },
        {
          id: 'clip-2',
          name: 'Main Content',
          asset_id: 'asset-2',
          track_id: 'track-1',
          start_time: 10,
          end_time: 25,
          duration: 15,
          in_point: 5,
          out_point: 20,
          speed: 1,
          volume: 1,
          color: '#4caf50',
          effects: [],
          transitions: [],
          asset: {
            id: 'asset-2',
            name: 'main_content.mp4',
            asset_type: 'video',
            thumbnail_path: '/thumbnails/main_content.jpg',
            duration: 45,
          },
        },
      ],
    },
    {
      id: 'track-2',
      name: 'Audio 1',
      type: 'audio',
      visible: true,
      locked: false,
      muted: false,
      solo: false,
      height: 40,
      color: '#ff9800',
      order: 2,
      clips: [
        {
          id: 'clip-3',
          name: 'Background Music',
          asset_id: 'asset-3',
          track_id: 'track-2',
          start_time: 0,
          end_time: 25,
          duration: 25,
          in_point: 0,
          out_point: 25,
          speed: 1,
          volume: 0.7,
          color: '#ff9800',
          effects: [],
          transitions: [],
          asset: {
            id: 'asset-3',
            name: 'background_music.mp3',
            asset_type: 'audio',
            duration: 120,
          },
        },
      ],
    },
    {
      id: 'track-3',
      name: 'Titles',
      type: 'graphics',
      visible: true,
      locked: false,
      muted: false,
      solo: false,
      height: 60,
      color: '#9c27b0',
      order: 3,
      clips: [
        {
          id: 'clip-4',
          name: 'Opening Title',
          asset_id: 'asset-4',
          track_id: 'track-3',
          start_time: 2,
          end_time: 8,
          duration: 6,
          in_point: 0,
          out_point: 6,
          speed: 1,
          volume: 1,
          color: '#9c27b0',
          effects: [],
          transitions: [],
          asset: {
            id: 'asset-4',
            name: 'opening_title.png',
            asset_type: 'image',
            thumbnail_path: '/thumbnails/opening_title.png',
          },
        },
      ],
    },
  ];

  const totalDuration = Math.max(...mockTracks.flatMap(track => 
    track.clips.map(clip => clip.end_time)
  ));

  const handleTimeChange = useCallback((time: number) => {
    setCurrentTime(time);
  }, []);

  const handleZoomChange = useCallback((zoom: number) => {
    setZoomLevel(zoom);
  }, []);

  const handlePlay = useCallback(() => {
    setPlaybackState('playing');
    // Implement actual playback logic here
  }, []);

  const handlePause = useCallback(() => {
    setPlaybackState('paused');
  }, []);

  const handleStop = useCallback(() => {
    setPlaybackState('stopped');
    setCurrentTime(0);
  }, []);

  const handleTrackAdd = useCallback((type: string) => {
    // Implement track addition logic
    setUnsavedChanges(true);
  }, []);

  const handleTrackDelete = useCallback((trackId: string) => {
    // Implement track deletion logic
    setUnsavedChanges(true);
  }, []);

  const handleTrackUpdate = useCallback((trackId: string, updates: Partial<TimelineTrack>) => {
    // Implement track update logic
    setUnsavedChanges(true);
  }, []);

  const handleClipAdd = useCallback((trackId: string, assetId: string, position: number) => {
    // Implement clip addition logic
    setUnsavedChanges(true);
  }, []);

  const handleClipUpdate = useCallback((clipId: string, updates: Partial<TimelineClip>) => {
    // Implement clip update logic
    setUnsavedChanges(true);
  }, []);

  const handleClipDelete = useCallback((clipId: string) => {
    // Implement clip deletion logic
    setUnsavedChanges(true);
  }, []);

  const handleClipMove = useCallback((clipId: string, trackId: string, position: number) => {
    // Implement clip move logic
    setUnsavedChanges(true);
  }, []);

  const handleSave = useCallback(async () => {
    if (!timelineId) return;
    
    try {
      await updateTimeline({
        id: timelineId,
        tracks: mockTracks, // In real implementation, use actual track data
      }).unwrap();
      setUnsavedChanges(false);
    } catch (error) {
      console.error('Failed to save timeline:', error);
    }
  }, [timelineId, updateTimeline, mockTracks]);

  const handleExport = useCallback(() => {
    // Implement timeline export logic
    console.log('Exporting timeline...');
  }, []);

  const handleImport = useCallback(() => {
    // Implement timeline import logic
    console.log('Importing timeline...');
  }, []);

  // Auto-save functionality
  useEffect(() => {
    if (autoSave && unsavedChanges) {
      const timer = setTimeout(() => {
        handleSave();
      }, 5000); // Auto-save after 5 seconds of inactivity
      
      return () => clearTimeout(timer);
    }
  }, [autoSave, unsavedChanges, handleSave]);

  if (isLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Typography>Loading timeline...</Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Alert severity="error">
          Failed to load timeline. Please try again.
        </Alert>
      </Container>
    );
  }

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper sx={{ p: 2, borderRadius: 0 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Breadcrumbs>
              <Link 
                component="button" 
                variant="body2" 
                onClick={() => navigate('/')}
                sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
              >
                <Home fontSize="small" />
                Home
              </Link>
              <Link 
                component="button" 
                variant="body2" 
                onClick={() => navigate('/timelines')}
                sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
              >
                <Timeline fontSize="small" />
                Timelines
              </Link>
              <Typography variant="body2" color="text.primary">
                {timeline?.name || 'Timeline Editor'}
              </Typography>
            </Breadcrumbs>
            
            {unsavedChanges && (
              <Chip 
                label="Unsaved changes" 
                color="warning" 
                size="small"
                icon={<Edit />}
              />
            )}
          </Box>

          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <Stack direction="row" spacing={1}>
              <Tooltip title="Undo">
                <IconButton size="small" disabled>
                  <Undo />
                </IconButton>
              </Tooltip>
              <Tooltip title="Redo">
                <IconButton size="small" disabled>
                  <Redo />
                </IconButton>
              </Tooltip>
              <Tooltip title="Save">
                <IconButton 
                  size="small" 
                  onClick={handleSave}
                  color={unsavedChanges ? 'warning' : 'default'}
                >
                  <Save />
                </IconButton>
              </Tooltip>
              <Tooltip title="Import">
                <IconButton size="small" onClick={handleImport}>
                  <Import />
                </IconButton>
              </Tooltip>
              <Tooltip title="Export">
                <IconButton size="small" onClick={handleExport}>
                  <Export />
                </IconButton>
              </Tooltip>
              <Tooltip title="Share">
                <IconButton size="small" onClick={() => setShowShareDialog(true)}>
                  <Share />
                </IconButton>
              </Tooltip>
              <Tooltip title="Settings">
                <IconButton size="small" onClick={() => setShowSettings(true)}>
                  <Settings />
                </IconButton>
              </Tooltip>
            </Stack>
          </Box>
        </Box>
      </Paper>

      {/* Timeline Editor */}
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        <TimelineUI
          timelineId={timelineId || ''}
          tracks={mockTracks}
          currentTime={currentTime}
          duration={totalDuration}
          zoomLevel={zoomLevel}
          onTimeChange={handleTimeChange}
          onZoomChange={handleZoomChange}
          onTrackAdd={handleTrackAdd}
          onTrackDelete={handleTrackDelete}
          onTrackUpdate={handleTrackUpdate}
          onClipAdd={handleClipAdd}
          onClipUpdate={handleClipUpdate}
          onClipDelete={handleClipDelete}
          onClipMove={handleClipMove}
          onPlay={handlePlay}
          onPause={handlePause}
          onStop={handleStop}
          readOnly={readOnly}
        />
      </Box>

      {/* Settings Dialog */}
      <Dialog open={showSettings} onClose={() => setShowSettings(false)}>
        <DialogTitle>Timeline Settings</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={autoSave}
                  onChange={(e) => setAutoSave(e.target.checked)}
                />
              }
              label="Auto-save"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={snapToGrid}
                  onChange={(e) => setSnapToGrid(e.target.checked)}
                />
              }
              label="Snap to grid"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={rippleEdit}
                  onChange={(e) => setRippleEdit(e.target.checked)}
                />
              }
              label="Ripple edit"
            />
            <FormControl fullWidth>
              <InputLabel>Default track height</InputLabel>
              <Select defaultValue="medium" label="Default track height">
                <MenuItem value="small">Small</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="large">Large</MenuItem>
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSettings(false)}>Cancel</Button>
          <Button onClick={() => setShowSettings(false)} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Share Dialog */}
      <Dialog open={showShareDialog} onClose={() => setShowShareDialog(false)}>
        <DialogTitle>Share Timeline</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              fullWidth
              label="Share URL"
              value={`${window.location.origin}/timelines/${timelineId}`}
              InputProps={{
                readOnly: true,
              }}
            />
            <FormControl fullWidth>
              <InputLabel>Permission</InputLabel>
              <Select defaultValue="view" label="Permission">
                <MenuItem value="view">View only</MenuItem>
                <MenuItem value="edit">Can edit</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowShareDialog(false)}>Cancel</Button>
          <Button onClick={() => setShowShareDialog(false)} variant="contained">
            Share
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TimelinePage;