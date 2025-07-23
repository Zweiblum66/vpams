import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Button,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Switch,
  Slider,
  Select,
  FormControl,
  InputLabel,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Bookmark as BookmarkIcon,
  BookmarkBorder as BookmarkBorderIcon,
  ContentCut as TrimIcon,
  Timeline as TimelineIcon,
  Subtitles as SubtitlesIcon,
  Speed as SpeedIcon,
  HighQuality as QualityIcon,
  Info as InfoIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  AspectRatio as AspectRatioIcon,
  Crop as CropIcon,
  NavigateBefore as PreviousIcon,
  NavigateNext as NextIcon,
  SkipPrevious as SkipPreviousIcon,
  SkipNext as SkipNextIcon,
  Loop as LoopIcon,
} from '@mui/icons-material';
import VideoJsPlayer from './VideoJsPlayer';
import Player from 'video.js/dist/types/player';
import { Asset } from '../../types/asset';
import { formatDuration, formatFileSize } from '../../utils/formatters';

interface AdvancedVideoPlayerProps {
  asset: Asset;
  sources?: Array<{
    src: string;
    type: string;
    label?: string;
    resolution?: number;
  }>;
  height?: string | number;
  onTimeUpdate?: (currentTime: number) => void;
  onMarkerAdd?: (time: number, text: string) => void;
  onTrimExport?: (startTime: number, endTime: number) => void;
}

interface Marker {
  id: string;
  time: number;
  text: string;
  class?: string;
}

interface LoopRange {
  start: number;
  end: number;
}

const AdvancedVideoPlayer: React.FC<AdvancedVideoPlayerProps> = ({
  asset,
  sources: propSources,
  height = '500px',
  onTimeUpdate,
  onMarkerAdd,
  onTrimExport,
}) => {
  const [player, setPlayer] = useState<Player | null>(null);
  const [settingsAnchor, setSettingsAnchor] = useState<null | HTMLElement>(null);
  const [markers, setMarkers] = useState<Marker[]>([]);
  const [showMarkerDialog, setShowMarkerDialog] = useState(false);
  const [markerText, setMarkerText] = useState('');
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showInfo, setShowInfo] = useState(false);
  const [frameRate, setFrameRate] = useState(asset.frameRate || 24);
  const [timecodeDisplay, setTimecodeDisplay] = useState(false);
  const [loopEnabled, setLoopEnabled] = useState(false);
  const [loopRange, setLoopRange] = useState<LoopRange | null>(null);
  const [trimStart, setTrimStart] = useState(0);
  const [trimEnd, setTrimEnd] = useState(0);
  const [showTrimDialog, setShowTrimDialog] = useState(false);
  const [aspectRatio, setAspectRatio] = useState('16:9');

  // Generate sources from asset if not provided
  const sources = propSources || [
    ...(asset.proxyUrls ? Object.entries(asset.proxyUrls).map(([quality, url]) => ({
      src: url,
      type: url.includes('.m3u8') ? 'application/x-mpegURL' : 'video/mp4',
      label: quality.charAt(0).toUpperCase() + quality.slice(1),
      resolution: quality === 'low' ? 360 : quality === 'medium' ? 720 : 1080,
    })) : []),
    {
      src: asset.originalUrl || asset.previewUrl,
      type: asset.mimeType || 'video/mp4',
      label: 'Original',
      resolution: asset.resolution?.height || 1080,
    },
  ].filter(source => source.src);

  // Get subtitles/captions tracks
  const tracks = asset.subtitles?.map(sub => ({
    kind: 'subtitles' as const,
    src: sub.url,
    srclang: sub.language,
    label: sub.label || sub.language,
    default: sub.default || false,
  })) || [];

  const handlePlayerReady = useCallback((p: Player) => {
    setPlayer(p);
    setDuration(p.duration() || 0);
    
    // Listen for duration change
    p.on('durationchange', () => {
      setDuration(p.duration() || 0);
      setTrimEnd(p.duration() || 0);
    });

    // Set up loop range if enabled
    if (loopEnabled && loopRange) {
      p.on('timeupdate', () => {
        const time = p.currentTime() || 0;
        if (time >= loopRange.end) {
          p.currentTime(loopRange.start);
        }
      });
    }
  }, [loopEnabled, loopRange]);

  const handleTimeUpdate = useCallback((time: number) => {
    setCurrentTime(time);
    onTimeUpdate?.(time);
  }, [onTimeUpdate]);

  const handleAddMarker = () => {
    if (!markerText.trim()) return;

    const newMarker: Marker = {
      id: Date.now().toString(),
      time: currentTime,
      text: markerText,
      class: 'user-marker',
    };

    setMarkers([...markers, newMarker]);
    onMarkerAdd?.(currentTime, markerText);
    setMarkerText('');
    setShowMarkerDialog(false);
  };

  const handleDeleteMarker = (id: string) => {
    setMarkers(markers.filter(m => m.id !== id));
  };

  const handleSetTrimStart = () => {
    setTrimStart(currentTime);
  };

  const handleSetTrimEnd = () => {
    setTrimEnd(currentTime);
  };

  const handleExportTrim = () => {
    onTrimExport?.(trimStart, trimEnd);
    setShowTrimDialog(false);
  };

  const handleLoopToggle = () => {
    if (!loopEnabled) {
      setLoopRange({ start: currentTime, end: Math.min(currentTime + 10, duration) });
    } else {
      setLoopRange(null);
    }
    setLoopEnabled(!loopEnabled);
  };

  const handleAspectRatioChange = (ratio: string) => {
    setAspectRatio(ratio);
    // Apply aspect ratio to player
    if (player) {
      const [width, height] = ratio.split(':').map(Number);
      player.aspectRatio(`${width}:${height}`);
    }
  };

  const formatTimecode = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const frames = Math.floor((seconds % 1) * frameRate);

    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`;
  };

  const handleFrameStep = (forward: boolean) => {
    if (!player) return;
    const frameTime = 1 / frameRate;
    const newTime = forward 
      ? Math.min(duration, currentTime + frameTime)
      : Math.max(0, currentTime - frameTime);
    player.currentTime(newTime);
  };

  return (
    <Box>
      <Paper sx={{ overflow: 'hidden', position: 'relative' }}>
        <VideoJsPlayer
          src={sources[0]?.src || asset.previewUrl}
          poster={asset.thumbnailUrl}
          height={height}
          sources={sources}
          tracks={tracks}
          onReady={handlePlayerReady}
          onTimeUpdate={handleTimeUpdate}
          frameRate={frameRate}
          timecodeDisplay={timecodeDisplay}
          markers={markers}
        />

        {/* Overlay controls */}
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            right: 0,
            p: 2,
            display: 'flex',
            gap: 1,
          }}
        >
          <IconButton
            sx={{ bgcolor: 'rgba(0, 0, 0, 0.5)', color: 'white' }}
            onClick={() => setShowInfo(!showInfo)}
          >
            <InfoIcon />
          </IconButton>
          <IconButton
            sx={{ bgcolor: 'rgba(0, 0, 0, 0.5)', color: 'white' }}
            onClick={(e) => setSettingsAnchor(e.currentTarget)}
          >
            <SettingsIcon />
          </IconButton>
        </Box>

        {/* Info overlay */}
        {showInfo && (
          <Box
            sx={{
              position: 'absolute',
              top: 60,
              right: 16,
              bgcolor: 'rgba(0, 0, 0, 0.8)',
              color: 'white',
              p: 2,
              borderRadius: 1,
              minWidth: 250,
            }}
          >
            <Typography variant="subtitle2" gutterBottom>
              Video Information
            </Typography>
            <Divider sx={{ my: 1, borderColor: 'rgba(255, 255, 255, 0.2)' }} />
            <Typography variant="caption" display="block">
              Resolution: {asset.resolution?.width}x{asset.resolution?.height}
            </Typography>
            <Typography variant="caption" display="block">
              Frame Rate: {frameRate} fps
            </Typography>
            <Typography variant="caption" display="block">
              Duration: {formatDuration(duration)}
            </Typography>
            <Typography variant="caption" display="block">
              Codec: {asset.codec || 'Unknown'}
            </Typography>
            <Typography variant="caption" display="block">
              Bitrate: {asset.bitrate ? `${(asset.bitrate / 1000000).toFixed(2)} Mbps` : 'Unknown'}
            </Typography>
            <Typography variant="caption" display="block">
              File Size: {formatFileSize(asset.size)}
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Control bar */}
      <Paper sx={{ p: 2, mt: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <Typography variant="body2">
              {formatTimecode(currentTime)} / {formatTimecode(duration)}
            </Typography>
            <Chip label={`${frameRate} fps`} size="small" />
          </Box>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Previous Frame">
              <IconButton size="small" onClick={() => handleFrameStep(false)}>
                <SkipPreviousIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Next Frame">
              <IconButton size="small" onClick={() => handleFrameStep(true)}>
                <SkipNextIcon />
              </IconButton>
            </Tooltip>
            
            <Divider orientation="vertical" flexItem />
            
            <Tooltip title="Add Marker">
              <IconButton
                size="small"
                onClick={() => setShowMarkerDialog(true)}
              >
                <BookmarkBorderIcon />
              </IconButton>
            </Tooltip>
            
            <Tooltip title="Set Trim Range">
              <IconButton
                size="small"
                onClick={() => setShowTrimDialog(true)}
              >
                <TrimIcon />
              </IconButton>
            </Tooltip>
            
            <Tooltip title={loopEnabled ? 'Disable Loop' : 'Enable Loop'}>
              <IconButton
                size="small"
                onClick={handleLoopToggle}
                color={loopEnabled ? 'primary' : 'default'}
              >
                <LoopIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Markers list */}
        {markers.length > 0 && (
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Markers
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {markers.map((marker) => (
                <Chip
                  key={marker.id}
                  label={`${formatTimecode(marker.time)}: ${marker.text}`}
                  onDelete={() => handleDeleteMarker(marker.id)}
                  onClick={() => player?.currentTime(marker.time)}
                  size="small"
                />
              ))}
            </Box>
          </Box>
        )}

        {/* Loop range display */}
        {loopEnabled && loopRange && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Loop Range
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <TextField
                size="small"
                label="Start"
                value={formatTimecode(loopRange.start)}
                InputProps={{ readOnly: true }}
              />
              <Typography>to</Typography>
              <TextField
                size="small"
                label="End"
                value={formatTimecode(loopRange.end)}
                InputProps={{ readOnly: true }}
              />
              <Button
                size="small"
                onClick={() => setLoopRange({ start: currentTime, end: loopRange.end })}
              >
                Set Start
              </Button>
              <Button
                size="small"
                onClick={() => setLoopRange({ start: loopRange.start, end: currentTime })}
              >
                Set End
              </Button>
            </Box>
          </Box>
        )}
      </Paper>

      {/* Settings menu */}
      <Menu
        anchorEl={settingsAnchor}
        open={Boolean(settingsAnchor)}
        onClose={() => setSettingsAnchor(null)}
      >
        <MenuItem>
          <ListItemIcon>
            <TimelineIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>
            <FormControlLabel
              control={
                <Switch
                  checked={timecodeDisplay}
                  onChange={(e) => setTimecodeDisplay(e.target.checked)}
                  size="small"
                />
              }
              label="Show Timecode"
            />
          </ListItemText>
        </MenuItem>
        
        <MenuItem>
          <ListItemIcon>
            <SpeedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>
            <FormControl size="small" fullWidth>
              <InputLabel>Frame Rate</InputLabel>
              <Select
                value={frameRate}
                onChange={(e) => setFrameRate(Number(e.target.value))}
                label="Frame Rate"
              >
                <MenuItem value={23.976}>23.976 fps</MenuItem>
                <MenuItem value={24}>24 fps</MenuItem>
                <MenuItem value={25}>25 fps</MenuItem>
                <MenuItem value={29.97}>29.97 fps</MenuItem>
                <MenuItem value={30}>30 fps</MenuItem>
                <MenuItem value={50}>50 fps</MenuItem>
                <MenuItem value={59.94}>59.94 fps</MenuItem>
                <MenuItem value={60}>60 fps</MenuItem>
              </Select>
            </FormControl>
          </ListItemText>
        </MenuItem>
        
        <MenuItem>
          <ListItemIcon>
            <AspectRatioIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>
            <ToggleButtonGroup
              value={aspectRatio}
              exclusive
              onChange={(e, value) => value && handleAspectRatioChange(value)}
              size="small"
            >
              <ToggleButton value="16:9">16:9</ToggleButton>
              <ToggleButton value="4:3">4:3</ToggleButton>
              <ToggleButton value="21:9">21:9</ToggleButton>
              <ToggleButton value="1:1">1:1</ToggleButton>
            </ToggleButtonGroup>
          </ListItemText>
        </MenuItem>
      </Menu>

      {/* Marker dialog */}
      <Dialog
        open={showMarkerDialog}
        onClose={() => setShowMarkerDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Marker</DialogTitle>
        <DialogContent>
          <Typography variant="body2" gutterBottom>
            Add a marker at {formatTimecode(currentTime)}
          </Typography>
          <TextField
            autoFocus
            margin="dense"
            label="Marker Text"
            fullWidth
            variant="outlined"
            value={markerText}
            onChange={(e) => setMarkerText(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') handleAddMarker();
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowMarkerDialog(false)}>Cancel</Button>
          <Button onClick={handleAddMarker} variant="contained">
            Add
          </Button>
        </DialogActions>
      </Dialog>

      {/* Trim dialog */}
      <Dialog
        open={showTrimDialog}
        onClose={() => setShowTrimDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Trim Video</DialogTitle>
        <DialogContent>
          <Typography variant="body2" gutterBottom>
            Set the trim range for export
          </Typography>
          <Box sx={{ mt: 2 }}>
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                label="Start Time"
                value={formatTimecode(trimStart)}
                InputProps={{ readOnly: true }}
                fullWidth
              />
              <Button onClick={handleSetTrimStart}>
                Set Current
              </Button>
            </Box>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="End Time"
                value={formatTimecode(trimEnd)}
                InputProps={{ readOnly: true }}
                fullWidth
              />
              <Button onClick={handleSetTrimEnd}>
                Set Current
              </Button>
            </Box>
            <Typography variant="caption" display="block" sx={{ mt: 2 }}>
              Duration: {formatDuration(trimEnd - trimStart)}
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowTrimDialog(false)}>Cancel</Button>
          <Button onClick={handleExportTrim} variant="contained">
            Export Trim
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AdvancedVideoPlayer;