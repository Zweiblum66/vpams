import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
  Divider,
  Chip,
  Slider,
  TextField,
  FormControl,
  InputLabel,
  Select,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Snackbar,
  Stack,
  Card,
  CardContent,
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  Stop,
  SkipPrevious,
  SkipNext,
  ZoomIn,
  ZoomOut,
  Add,
  Delete,
  Edit,
  ContentCopy,
  Visibility,
  VisibilityOff,
  Lock,
  LockOpen,
  VolumeUp,
  VolumeOff,
  Settings,
  Straighten,
  Schedule,
  Movie,
  AudioFile,
  Image,
  Description,
  MoreVert,
  DragIndicator,
  CropFree,
  ContentCut,
  Layers,
} from '@mui/icons-material';
import { DragDropContext, Droppable, Draggable, DropResult } from 'react-beautiful-dnd';

interface TimelineTrack {
  id: string;
  name: string;
  type: 'video' | 'audio' | 'subtitle' | 'graphics';
  visible: boolean;
  locked: boolean;
  muted: boolean;
  solo: boolean;
  height: number;
  color: string;
  clips: TimelineClip[];
  order: number;
}

interface TimelineClip {
  id: string;
  name: string;
  asset_id: string;
  track_id: string;
  start_time: number;
  end_time: number;
  duration: number;
  in_point: number;
  out_point: number;
  speed: number;
  volume: number;
  color: string;
  effects: TimelineEffect[];
  transitions: TimelineTransition[];
  asset: {
    id: string;
    name: string;
    asset_type: string;
    thumbnail_path?: string;
    duration?: number;
  };
}

interface TimelineEffect {
  id: string;
  name: string;
  type: string;
  parameters: Record<string, any>;
  enabled: boolean;
}

interface TimelineTransition {
  id: string;
  name: string;
  type: string;
  duration: number;
  parameters: Record<string, any>;
}

interface TimelineUIProps {
  timelineId: string;
  tracks: TimelineTrack[];
  currentTime: number;
  duration: number;
  zoomLevel: number;
  onTimeChange?: (time: number) => void;
  onZoomChange?: (zoom: number) => void;
  onTrackAdd?: (type: string) => void;
  onTrackDelete?: (trackId: string) => void;
  onTrackUpdate?: (trackId: string, updates: Partial<TimelineTrack>) => void;
  onClipAdd?: (trackId: string, assetId: string, position: number) => void;
  onClipUpdate?: (clipId: string, updates: Partial<TimelineClip>) => void;
  onClipDelete?: (clipId: string) => void;
  onClipMove?: (clipId: string, trackId: string, position: number) => void;
  onPlay?: () => void;
  onPause?: () => void;
  onStop?: () => void;
  readOnly?: boolean;
}

const TRACK_COLORS = [
  '#2196f3', '#4caf50', '#ff9800', '#f44336', '#9c27b0',
  '#00bcd4', '#8bc34a', '#ffc107', '#795548', '#607d8b'
];

const TRACK_HEIGHTS = {
  video: 80,
  audio: 40,
  subtitle: 30,
  graphics: 60,
};

const TimelineUI: React.FC<TimelineUIProps> = ({
  timelineId,
  tracks,
  currentTime,
  duration,
  zoomLevel,
  onTimeChange,
  onZoomChange,
  onTrackAdd,
  onTrackDelete,
  onTrackUpdate,
  onClipAdd,
  onClipUpdate,
  onClipDelete,
  onClipMove,
  onPlay,
  onPause,
  onStop,
  readOnly = false,
}) => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const [selectedClips, setSelectedClips] = useState<string[]>([]);
  const [playbackState, setPlaybackState] = useState<'playing' | 'paused' | 'stopped'>('stopped');
  const [showAddTrackDialog, setShowAddTrackDialog] = useState(false);
  const [contextMenu, setContextMenu] = useState<{
    mouseX: number;
    mouseY: number;
    trackId?: string;
    clipId?: string;
  } | null>(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' as 'success' | 'error' | 'info' });
  const [dragTarget, setDragTarget] = useState<{ trackId: string; position: number } | null>(null);

  // Timeline dimensions
  const pixelsPerSecond = zoomLevel * 10; // Base scale
  const timelineWidth = duration * pixelsPerSecond;
  const playheadPosition = currentTime * pixelsPerSecond;

  // Format time display
  const formatTime = useCallback((seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const frames = Math.floor((seconds % 1) * 25); // 25fps
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`;
  }, []);

  // Handle timeline click to seek
  const handleTimelineClick = useCallback((event: React.MouseEvent) => {
    if (readOnly) return;
    
    const rect = timelineRef.current?.getBoundingClientRect();
    if (!rect) return;
    
    const x = event.clientX - rect.left;
    const newTime = Math.max(0, Math.min(x / pixelsPerSecond, duration));
    onTimeChange?.(newTime);
  }, [pixelsPerSecond, duration, onTimeChange, readOnly]);

  // Handle playback controls
  const handlePlay = useCallback(() => {
    setPlaybackState('playing');
    onPlay?.();
  }, [onPlay]);

  const handlePause = useCallback(() => {
    setPlaybackState('paused');
    onPause?.();
  }, [onPause]);

  const handleStop = useCallback(() => {
    setPlaybackState('stopped');
    onStop?.();
  }, [onStop]);

  // Handle track operations
  const handleTrackToggleVisibility = useCallback((trackId: string) => {
    const track = tracks.find(t => t.id === trackId);
    if (track) {
      onTrackUpdate?.(trackId, { visible: !track.visible });
    }
  }, [tracks, onTrackUpdate]);

  const handleTrackToggleLock = useCallback((trackId: string) => {
    const track = tracks.find(t => t.id === trackId);
    if (track) {
      onTrackUpdate?.(trackId, { locked: !track.locked });
    }
  }, [tracks, onTrackUpdate]);

  const handleTrackToggleMute = useCallback((trackId: string) => {
    const track = tracks.find(t => t.id === trackId);
    if (track) {
      onTrackUpdate?.(trackId, { muted: !track.muted });
    }
  }, [tracks, onTrackUpdate]);

  // Handle clip selection
  const handleClipSelect = useCallback((clipId: string, multiSelect = false) => {
    if (multiSelect) {
      setSelectedClips(prev => 
        prev.includes(clipId) 
          ? prev.filter(id => id !== clipId)
          : [...prev, clipId]
      );
    } else {
      setSelectedClips([clipId]);
    }
  }, []);

  // Handle context menu
  const handleContextMenu = useCallback((event: React.MouseEvent, trackId?: string, clipId?: string) => {
    event.preventDefault();
    setContextMenu({
      mouseX: event.clientX - 2,
      mouseY: event.clientY - 4,
      trackId,
      clipId,
    });
  }, []);

  const handleContextMenuClose = useCallback(() => {
    setContextMenu(null);
  }, []);

  // Handle drag and drop
  const handleDragEnd = useCallback((result: DropResult) => {
    if (!result.destination) return;
    
    const { source, destination } = result;
    
    if (source.droppableId !== destination.droppableId) {
      // Moving clip between tracks
      const clipId = result.draggableId;
      const newTrackId = destination.droppableId;
      const newPosition = destination.index * 10; // Rough position calculation
      
      onClipMove?.(clipId, newTrackId, newPosition);
    } else {
      // Reordering within the same track
      // Implementation depends on your track structure
    }
  }, [onClipMove]);

  // Render track header
  const renderTrackHeader = useCallback((track: TimelineTrack) => (
    <Box
      key={track.id}
      sx={{
        width: 200,
        height: TRACK_HEIGHTS[track.type],
        display: 'flex',
        alignItems: 'center',
        p: 1,
        borderRight: '1px solid #e0e0e0',
        borderBottom: '1px solid #e0e0e0',
        bgcolor: track.color,
        color: 'white',
      }}
    >
      <Box sx={{ flex: 1 }}>
        <Typography variant="body2" noWrap>
          {track.name}
        </Typography>
        <Typography variant="caption" sx={{ opacity: 0.8 }}>
          {track.type}
        </Typography>
      </Box>
      
      <Box sx={{ display: 'flex', gap: 0.5 }}>
        <Tooltip title={track.visible ? 'Hide' : 'Show'}>
          <IconButton
            size="small"
            onClick={() => handleTrackToggleVisibility(track.id)}
            sx={{ color: 'white' }}
          >
            {track.visible ? <Visibility /> : <VisibilityOff />}
          </IconButton>
        </Tooltip>
        
        <Tooltip title={track.locked ? 'Unlock' : 'Lock'}>
          <IconButton
            size="small"
            onClick={() => handleTrackToggleLock(track.id)}
            sx={{ color: 'white' }}
          >
            {track.locked ? <Lock /> : <LockOpen />}
          </IconButton>
        </Tooltip>
        
        {track.type === 'audio' && (
          <Tooltip title={track.muted ? 'Unmute' : 'Mute'}>
            <IconButton
              size="small"
              onClick={() => handleTrackToggleMute(track.id)}
              sx={{ color: 'white' }}
            >
              {track.muted ? <VolumeOff /> : <VolumeUp />}
            </IconButton>
          </Tooltip>
        )}
        
        <Tooltip title="Settings">
          <IconButton
            size="small"
            onClick={(e) => handleContextMenu(e, track.id)}
            sx={{ color: 'white' }}
          >
            <Settings />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  ), [handleTrackToggleVisibility, handleTrackToggleLock, handleTrackToggleMute, handleContextMenu]);

  // Render timeline clip
  const renderTimelineClip = useCallback((clip: TimelineClip, trackId: string) => {
    const clipWidth = clip.duration * pixelsPerSecond;
    const clipLeft = clip.start_time * pixelsPerSecond;
    const isSelected = selectedClips.includes(clip.id);
    
    const getAssetTypeIcon = (type: string) => {
      switch (type) {
        case 'video': return <Movie fontSize="small" />;
        case 'audio': return <AudioFile fontSize="small" />;
        case 'image': return <Image fontSize="small" />;
        default: return <Description fontSize="small" />;
      }
    };

    return (
      <Box
        key={clip.id}
        sx={{
          position: 'absolute',
          left: clipLeft,
          width: clipWidth,
          height: TRACK_HEIGHTS[tracks.find(t => t.id === trackId)?.type || 'video'] - 4,
          top: 2,
          bgcolor: clip.color || '#2196f3',
          border: isSelected ? '2px solid #ff9800' : '1px solid #1976d2',
          borderRadius: 1,
          display: 'flex',
          alignItems: 'center',
          px: 1,
          cursor: 'pointer',
          overflow: 'hidden',
          '&:hover': {
            bgcolor: clip.color ? `${clip.color}dd` : '#1976d2dd',
          },
        }}
        onClick={(e) => handleClipSelect(clip.id, e.ctrlKey || e.metaKey)}
        onContextMenu={(e) => handleContextMenu(e, trackId, clip.id)}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'white' }}>
          {getAssetTypeIcon(clip.asset.asset_type)}
          <Typography variant="caption" noWrap>
            {clip.name}
          </Typography>
        </Box>
        
        {/* Clip handles for resizing */}
        <Box
          sx={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 4,
            height: '100%',
            bgcolor: 'rgba(255, 255, 255, 0.8)',
            cursor: 'w-resize',
            opacity: isSelected ? 1 : 0,
            '&:hover': { opacity: 1 },
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            right: 0,
            top: 0,
            width: 4,
            height: '100%',
            bgcolor: 'rgba(255, 255, 255, 0.8)',
            cursor: 'e-resize',
            opacity: isSelected ? 1 : 0,
            '&:hover': { opacity: 1 },
          }}
        />
      </Box>
    );
  }, [pixelsPerSecond, selectedClips, tracks, handleClipSelect, handleContextMenu]);

  // Render timeline track
  const renderTimelineTrack = useCallback((track: TimelineTrack) => (
    <Box
      key={track.id}
      sx={{
        position: 'relative',
        height: TRACK_HEIGHTS[track.type],
        width: timelineWidth,
        borderBottom: '1px solid #e0e0e0',
        bgcolor: track.visible ? 'transparent' : 'rgba(0, 0, 0, 0.1)',
        opacity: track.visible ? 1 : 0.5,
      }}
      onContextMenu={(e) => handleContextMenu(e, track.id)}
    >
      {/* Track background */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          bgcolor: 'rgba(0, 0, 0, 0.02)',
        }}
      />
      
      {/* Track clips */}
      {track.clips.map((clip) => renderTimelineClip(clip, track.id))}
      
      {/* Drop zone indicator */}
      {dragTarget?.trackId === track.id && (
        <Box
          sx={{
            position: 'absolute',
            left: dragTarget.position * pixelsPerSecond,
            top: 0,
            width: 2,
            height: '100%',
            bgcolor: '#ff9800',
            zIndex: 1000,
          }}
        />
      )}
    </Box>
  ), [timelineWidth, renderTimelineClip, handleContextMenu, dragTarget, pixelsPerSecond]);

  // Render time ruler
  const renderTimeRuler = useCallback(() => {
    const majorTicks = [];
    const minorTicks = [];
    const tickInterval = Math.max(1, Math.floor(60 / zoomLevel)); // Adjust based on zoom
    
    for (let i = 0; i <= duration; i += tickInterval) {
      const position = i * pixelsPerSecond;
      majorTicks.push(
        <Box
          key={i}
          sx={{
            position: 'absolute',
            left: position,
            top: 0,
            width: 1,
            height: 20,
            bgcolor: '#666',
          }}
        />
      );
      
      if (i % (tickInterval * 5) === 0) {
        majorTicks.push(
          <Typography
            key={`label-${i}`}
            variant="caption"
            sx={{
              position: 'absolute',
              left: position + 4,
              top: 2,
              color: '#666',
            }}
          >
            {formatTime(i)}
          </Typography>
        );
      }
    }
    
    return (
      <Box
        sx={{
          position: 'relative',
          height: 30,
          width: timelineWidth,
          bgcolor: '#f5f5f5',
          borderBottom: '1px solid #e0e0e0',
        }}
        onClick={handleTimelineClick}
      >
        {majorTicks}
        {minorTicks}
      </Box>
    );
  }, [duration, pixelsPerSecond, zoomLevel, formatTime, handleTimelineClick, timelineWidth]);

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Timeline Header */}
      <Paper sx={{ p: 2, mb: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Timeline</Typography>
          
          {/* Playback Controls */}
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <IconButton onClick={handleStop} disabled={playbackState === 'stopped'}>
              <Stop />
            </IconButton>
            <IconButton onClick={() => onTimeChange?.(Math.max(0, currentTime - 1))}>
              <SkipPrevious />
            </IconButton>
            <IconButton onClick={playbackState === 'playing' ? handlePause : handlePlay}>
              {playbackState === 'playing' ? <Pause /> : <PlayArrow />}
            </IconButton>
            <IconButton onClick={() => onTimeChange?.(Math.min(duration, currentTime + 1))}>
              <SkipNext />
            </IconButton>
            
            <Typography variant="body2" sx={{ mx: 2 }}>
              {formatTime(currentTime)} / {formatTime(duration)}
            </Typography>
            
            <Divider orientation="vertical" flexItem />
            
            <IconButton onClick={() => onZoomChange?.(Math.max(0.1, zoomLevel - 0.1))}>
              <ZoomOut />
            </IconButton>
            <Typography variant="body2" sx={{ mx: 1 }}>
              {Math.round(zoomLevel * 100)}%
            </Typography>
            <IconButton onClick={() => onZoomChange?.(Math.min(5, zoomLevel + 0.1))}>
              <ZoomIn />
            </IconButton>
            
            {!readOnly && (
              <>
                <Divider orientation="vertical" flexItem />
                <Button
                  variant="outlined"
                  startIcon={<Add />}
                  onClick={() => setShowAddTrackDialog(true)}
                >
                  Add Track
                </Button>
              </>
            )}
          </Box>
        </Box>
      </Paper>

      {/* Timeline Content */}
      <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Track Headers */}
        <Box sx={{ width: 200, flexShrink: 0 }}>
          {/* Time ruler header */}
          <Box sx={{ height: 30, bgcolor: '#f5f5f5', borderBottom: '1px solid #e0e0e0' }} />
          
          {/* Track headers */}
          {tracks.map(renderTrackHeader)}
        </Box>

        {/* Timeline Tracks */}
        <Box
          ref={timelineRef}
          sx={{
            flex: 1,
            overflow: 'auto',
            position: 'relative',
          }}
        >
          {/* Time ruler */}
          {renderTimeRuler()}
          
          {/* Playhead */}
          <Box
            sx={{
              position: 'absolute',
              left: playheadPosition,
              top: 0,
              bottom: 0,
              width: 2,
              bgcolor: '#ff0000',
              zIndex: 1000,
              pointerEvents: 'none',
            }}
          />
          
          {/* Tracks */}
          <DragDropContext onDragEnd={handleDragEnd}>
            {tracks.map(renderTimelineTrack)}
          </DragDropContext>
        </Box>
      </Box>

      {/* Add Track Dialog */}
      <Dialog open={showAddTrackDialog} onClose={() => setShowAddTrackDialog(false)}>
        <DialogTitle>Add Track</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Track Type</InputLabel>
            <Select defaultValue="video" label="Track Type">
              <MenuItem value="video">Video</MenuItem>
              <MenuItem value="audio">Audio</MenuItem>
              <MenuItem value="subtitle">Subtitle</MenuItem>
              <MenuItem value="graphics">Graphics</MenuItem>
            </Select>
          </FormControl>
          <TextField
            fullWidth
            label="Track Name"
            margin="normal"
            defaultValue={`Track ${tracks.length + 1}`}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAddTrackDialog(false)}>Cancel</Button>
          <Button onClick={() => {
            onTrackAdd?.('video');
            setShowAddTrackDialog(false);
          }} variant="contained">
            Add
          </Button>
        </DialogActions>
      </Dialog>

      {/* Context Menu */}
      <Menu
        open={contextMenu !== null}
        onClose={handleContextMenuClose}
        anchorReference="anchorPosition"
        anchorPosition={
          contextMenu !== null
            ? { top: contextMenu.mouseY, left: contextMenu.mouseX }
            : undefined
        }
      >
        {contextMenu?.clipId && [
          <MenuItem key="edit" onClick={handleContextMenuClose}>
            <Edit sx={{ mr: 1 }} />
            Edit Clip
          </MenuItem>,
          <MenuItem key="copy" onClick={handleContextMenuClose}>
            <ContentCopy sx={{ mr: 1 }} />
            Copy
          </MenuItem>,
          <MenuItem key="cut" onClick={handleContextMenuClose}>
            <ContentCut sx={{ mr: 1 }} />
            Cut
          </MenuItem>,
          <Divider key="divider" />,
          <MenuItem key="delete" onClick={handleContextMenuClose} sx={{ color: 'error.main' }}>
            <Delete sx={{ mr: 1 }} />
            Delete
          </MenuItem>,
        ]}
        
        {contextMenu?.trackId && !contextMenu.clipId && [
          <MenuItem key="add-clip" onClick={handleContextMenuClose}>
            <Add sx={{ mr: 1 }} />
            Add Clip
          </MenuItem>,
          <MenuItem key="track-settings" onClick={handleContextMenuClose}>
            <Settings sx={{ mr: 1 }} />
            Track Settings
          </MenuItem>,
          <Divider key="divider" />,
          <MenuItem key="delete-track" onClick={handleContextMenuClose} sx={{ color: 'error.main' }}>
            <Delete sx={{ mr: 1 }} />
            Delete Track
          </MenuItem>,
        ]}
      </Menu>

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

export default TimelineUI;