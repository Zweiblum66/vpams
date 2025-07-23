import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Box,
  Paper,
  IconButton,
  Typography,
  Slider,
  Button,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Divider,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  Select,
  InputLabel,
  CircularProgress,
  Fade,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  VolumeUp as VolumeIcon,
  VolumeOff as VolumeMuteIcon,
  SkipNext as SkipNextIcon,
  SkipPrevious as SkipPreviousIcon,
  Speed as SpeedIcon,
  Settings as SettingsIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  Crop as RegionIcon,
  Bookmark as MarkerIcon,
  Loop as LoopIcon,
  Repeat as RepeatIcon,
  Shuffle as ShuffleIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  ContentCut as TrimIcon,
  Waves as WaveIcon,
  GraphicEq as SpectrumIcon,
} from '@mui/icons-material';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.js';
import SpectrogramPlugin from 'wavesurfer.js/dist/plugins/spectrogram.js';
import { Asset } from '../../types/asset';
import { formatDuration } from '../../utils/formatters';

interface WaveformPlayerProps {
  asset: Asset;
  height?: number;
  onTimeUpdate?: (currentTime: number) => void;
  onRegionCreate?: (region: any) => void;
  onMarkerAdd?: (time: number, text: string) => void;
  onTrimExport?: (startTime: number, endTime: number) => void;
}

interface Region {
  id: string;
  start: number;
  end: number;
  color: string;
  text?: string;
}

interface Marker {
  id: string;
  time: number;
  text: string;
  color: string;
}

const WaveformPlayer: React.FC<WaveformPlayerProps> = ({
  asset,
  height = 200,
  onTimeUpdate,
  onRegionCreate,
  onMarkerAdd,
  onTrimExport,
}) => {
  const waveformRef = useRef<HTMLDivElement>(null);
  const wavesurfer = useRef<WaveSurfer | null>(null);
  const regionsPlugin = useRef<RegionsPlugin | null>(null);
  const spectrogramPlugin = useRef<SpectrogramPlugin | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [repeat, setRepeat] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [showSpectrogram, setShowSpectrogram] = useState(false);
  const [regions, setRegions] = useState<Region[]>([]);
  const [markers, setMarkers] = useState<Marker[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [settingsAnchor, setSettingsAnchor] = useState<null | HTMLElement>(null);
  const [markerDialogOpen, setMarkerDialogOpen] = useState(false);
  const [markerText, setMarkerText] = useState('');
  const [trimDialogOpen, setTrimDialogOpen] = useState(false);
  const [trimStart, setTrimStart] = useState(0);
  const [trimEnd, setTrimEnd] = useState(0);
  const [waveformColor, setWaveformColor] = useState('#3f51b5');
  const [progressColor, setProgressColor] = useState('#1976d2');

  useEffect(() => {
    if (!waveformRef.current) return;

    // Initialize WaveSurfer
    wavesurfer.current = WaveSurfer.create({
      container: waveformRef.current,
      height,
      waveColor: waveformColor,
      progressColor: progressColor,
      backgroundColor: 'transparent',
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      responsive: true,
      normalize: true,
      backend: 'WebAudio',
      cursorColor: '#ff0000',
      cursorWidth: 2,
      fillParent: true,
      interact: true,
      hideScrollbar: true,
      minPxPerSec: 50,
      pixelRatio: window.devicePixelRatio || 1,
    });

    // Initialize Regions plugin
    regionsPlugin.current = RegionsPlugin.create({
      regions: [],
      dragSelection: {
        slop: 5,
      },
    });

    // Initialize Spectrogram plugin
    spectrogramPlugin.current = SpectrogramPlugin.create({
      labels: true,
      height,
      fftSamples: 512,
      windowFunc: 'hann',
      alpha: 0.6,
    });

    // Register plugins
    wavesurfer.current.registerPlugin(regionsPlugin.current);
    if (showSpectrogram) {
      wavesurfer.current.registerPlugin(spectrogramPlugin.current);
    }

    // Event listeners
    wavesurfer.current.on('ready', () => {
      setIsLoading(false);
      setDuration(wavesurfer.current?.getDuration() || 0);
      setTrimEnd(wavesurfer.current?.getDuration() || 0);
    });

    wavesurfer.current.on('audioprocess', (time) => {
      setCurrentTime(time);
      onTimeUpdate?.(time);
    });

    wavesurfer.current.on('play', () => setIsPlaying(true));
    wavesurfer.current.on('pause', () => setIsPlaying(false));
    wavesurfer.current.on('finish', () => {
      setIsPlaying(false);
      if (repeat) {
        wavesurfer.current?.seekTo(0);
        wavesurfer.current?.play();
      }
    });

    wavesurfer.current.on('zoom', (minPxPerSec) => {
      setZoom(minPxPerSec / 50);
    });

    wavesurfer.current.on('error', (error) => {
      console.error('WaveSurfer error:', error);
      setIsLoading(false);
    });

    // Region events
    regionsPlugin.current.on('region-created', (region) => {
      const newRegion: Region = {
        id: region.id,
        start: region.start,
        end: region.end,
        color: region.color,
        text: region.attributes?.text || '',
      };
      setRegions(prev => [...prev, newRegion]);
      onRegionCreate?.(newRegion);
    });

    regionsPlugin.current.on('region-updated', (region) => {
      setRegions(prev => prev.map(r => 
        r.id === region.id 
          ? { ...r, start: region.start, end: region.end }
          : r
      ));
    });

    regionsPlugin.current.on('region-clicked', (region) => {
      setSelectedRegion(region.id);
      wavesurfer.current?.setTime(region.start);
    });

    regionsPlugin.current.on('region-removed', (region) => {
      setRegions(prev => prev.filter(r => r.id !== region.id));
    });

    // Load audio
    const audioUrl = asset.previewUrl || asset.originalUrl;
    if (audioUrl) {
      setIsLoading(true);
      wavesurfer.current.load(audioUrl);
    }

    // Cleanup
    return () => {
      wavesurfer.current?.destroy();
    };
  }, [asset, height, showSpectrogram, waveformColor, progressColor]);

  const handlePlayPause = () => {
    if (wavesurfer.current) {
      if (isPlaying) {
        wavesurfer.current.pause();
      } else {
        wavesurfer.current.play();
      }
    }
  };

  const handleStop = () => {
    if (wavesurfer.current) {
      wavesurfer.current.stop();
      setIsPlaying(false);
    }
  };

  const handleSeek = (time: number) => {
    if (wavesurfer.current) {
      wavesurfer.current.seekTo(time / duration);
    }
  };

  const handleVolumeChange = (newVolume: number) => {
    setVolume(newVolume);
    if (wavesurfer.current) {
      wavesurfer.current.setVolume(newVolume);
    }
  };

  const handleMute = () => {
    setMuted(!muted);
    if (wavesurfer.current) {
      wavesurfer.current.setMuted(!muted);
    }
  };

  const handlePlaybackRateChange = (rate: number) => {
    setPlaybackRate(rate);
    if (wavesurfer.current) {
      wavesurfer.current.setPlaybackRate(rate);
    }
  };

  const handleZoomIn = () => {
    const newZoom = Math.min(zoom * 2, 10);
    setZoom(newZoom);
    if (wavesurfer.current) {
      wavesurfer.current.zoom(newZoom * 50);
    }
  };

  const handleZoomOut = () => {
    const newZoom = Math.max(zoom / 2, 0.1);
    setZoom(newZoom);
    if (wavesurfer.current) {
      wavesurfer.current.zoom(newZoom * 50);
    }
  };

  const handleAddMarker = () => {
    if (!markerText.trim()) return;

    const newMarker: Marker = {
      id: Date.now().toString(),
      time: currentTime,
      text: markerText,
      color: '#ff9800',
    };

    setMarkers([...markers, newMarker]);
    onMarkerAdd?.(currentTime, markerText);
    setMarkerText('');
    setMarkerDialogOpen(false);
  };

  const handleDeleteMarker = (id: string) => {
    setMarkers(markers.filter(m => m.id !== id));
  };

  const handleAddRegion = () => {
    if (regionsPlugin.current) {
      const start = currentTime;
      const end = Math.min(currentTime + 5, duration);
      
      regionsPlugin.current.addRegion({
        start,
        end,
        color: `rgba(${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, 0.3)`,
        drag: true,
        resize: true,
      });
    }
  };

  const handleDeleteRegion = (id: string) => {
    if (regionsPlugin.current) {
      regionsPlugin.current.getRegions().forEach(region => {
        if (region.id === id) {
          region.remove();
        }
      });
    }
  };

  const handleTrimExport = () => {
    onTrimExport?.(trimStart, trimEnd);
    setTrimDialogOpen(false);
  };

  const handleSkipBackward = () => {
    const newTime = Math.max(0, currentTime - 10);
    handleSeek(newTime);
  };

  const handleSkipForward = () => {
    const newTime = Math.min(duration, currentTime + 10);
    handleSeek(newTime);
  };

  const toggleSpectrogram = () => {
    setShowSpectrogram(!showSpectrogram);
  };

  return (
    <Box>
      <Paper sx={{ p: 2 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box>
            <Typography variant="h6" noWrap>
              {asset.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {formatDuration(duration)} • {asset.metadata?.codec} • {asset.metadata?.sampleRate}Hz
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Add Region">
              <IconButton onClick={handleAddRegion} size="small">
                <RegionIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Add Marker">
              <IconButton onClick={() => setMarkerDialogOpen(true)} size="small">
                <MarkerIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Export Trim">
              <IconButton onClick={() => setTrimDialogOpen(true)} size="small">
                <TrimIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Settings">
              <IconButton onClick={(e) => setSettingsAnchor(e.currentTarget)} size="small">
                <SettingsIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Waveform */}
        <Box sx={{ position: 'relative', mb: 2 }}>
          {isLoading && (
            <Box
              sx={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                zIndex: 1,
              }}
            >
              <CircularProgress />
            </Box>
          )}
          <div ref={waveformRef} style={{ width: '100%' }} />
          
          {/* Markers overlay */}
          {markers.map((marker) => (
            <Box
              key={marker.id}
              sx={{
                position: 'absolute',
                top: 0,
                left: `${(marker.time / duration) * 100}%`,
                width: 2,
                height: '100%',
                bgcolor: marker.color,
                cursor: 'pointer',
                zIndex: 2,
                '&:hover': {
                  width: 4,
                },
              }}
              onClick={() => handleSeek(marker.time)}
            />
          ))}
        </Box>

        {/* Controls */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IconButton onClick={handleSkipBackward} disabled={isLoading}>
              <SkipPreviousIcon />
            </IconButton>
            <IconButton onClick={handlePlayPause} disabled={isLoading}>
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
            </IconButton>
            <IconButton onClick={handleStop} disabled={isLoading}>
              <StopIcon />
            </IconButton>
            <IconButton onClick={handleSkipForward} disabled={isLoading}>
              <SkipNextIcon />
            </IconButton>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
            <Typography variant="body2" sx={{ minWidth: 60 }}>
              {formatDuration(currentTime)}
            </Typography>
            <Slider
              value={currentTime}
              min={0}
              max={duration}
              onChange={(_, value) => handleSeek(value as number)}
              size="small"
              sx={{ flex: 1 }}
            />
            <Typography variant="body2" sx={{ minWidth: 60 }}>
              {formatDuration(duration)}
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IconButton onClick={handleMute}>
              {muted ? <VolumeMuteIcon /> : <VolumeIcon />}
            </IconButton>
            <Slider
              value={volume}
              min={0}
              max={1}
              step={0.1}
              onChange={(_, value) => handleVolumeChange(value as number)}
              size="small"
              sx={{ width: 80 }}
            />
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Tooltip title="Zoom Out">
              <IconButton onClick={handleZoomOut} size="small">
                <ZoomOutIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Zoom In">
              <IconButton onClick={handleZoomIn} size="small">
                <ZoomInIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Toggle Spectrogram">
              <IconButton 
                onClick={toggleSpectrogram} 
                size="small"
                color={showSpectrogram ? 'primary' : 'default'}
              >
                <SpectrumIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Repeat">
              <IconButton 
                onClick={() => setRepeat(!repeat)} 
                size="small"
                color={repeat ? 'primary' : 'default'}
              >
                <RepeatIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Playback rate */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}>
          <Typography variant="body2">Speed:</Typography>
          <ToggleButtonGroup
            value={playbackRate}
            exclusive
            onChange={(_, value) => value && handlePlaybackRateChange(value)}
            size="small"
          >
            <ToggleButton value={0.5}>0.5x</ToggleButton>
            <ToggleButton value={0.75}>0.75x</ToggleButton>
            <ToggleButton value={1}>1x</ToggleButton>
            <ToggleButton value={1.25}>1.25x</ToggleButton>
            <ToggleButton value={1.5}>1.5x</ToggleButton>
            <ToggleButton value={2}>2x</ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {/* Regions and Markers */}
        {(regions.length > 0 || markers.length > 0) && (
          <Box sx={{ mt: 2 }}>
            {regions.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Regions
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {regions.map((region) => (
                    <Chip
                      key={region.id}
                      label={`${formatDuration(region.start)} - ${formatDuration(region.end)}`}
                      onDelete={() => handleDeleteRegion(region.id)}
                      onClick={() => handleSeek(region.start)}
                      size="small"
                      color={selectedRegion === region.id ? 'primary' : 'default'}
                    />
                  ))}
                </Box>
              </Box>
            )}

            {markers.length > 0 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Markers
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {markers.map((marker) => (
                    <Chip
                      key={marker.id}
                      label={`${formatDuration(marker.time)}: ${marker.text}`}
                      onDelete={() => handleDeleteMarker(marker.id)}
                      onClick={() => handleSeek(marker.time)}
                      size="small"
                    />
                  ))}
                </Box>
              </Box>
            )}
          </Box>
        )}
      </Paper>

      {/* Settings Menu */}
      <Menu
        anchorEl={settingsAnchor}
        open={Boolean(settingsAnchor)}
        onClose={() => setSettingsAnchor(null)}
      >
        <MenuItem>
          <ListItemIcon>
            <WaveIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>
            <input
              type="color"
              value={waveformColor}
              onChange={(e) => setWaveformColor(e.target.value)}
              style={{ width: '100%' }}
            />
          </ListItemText>
        </MenuItem>
        <MenuItem>
          <ListItemIcon>
            <SpectrumIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>
            Toggle Spectrogram
          </ListItemText>
        </MenuItem>
      </Menu>

      {/* Marker Dialog */}
      <Dialog
        open={markerDialogOpen}
        onClose={() => setMarkerDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Marker</DialogTitle>
        <DialogContent>
          <Typography variant="body2" gutterBottom>
            Add a marker at {formatDuration(currentTime)}
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
          <Button onClick={() => setMarkerDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleAddMarker} variant="contained">
            Add
          </Button>
        </DialogActions>
      </Dialog>

      {/* Trim Dialog */}
      <Dialog
        open={trimDialogOpen}
        onClose={() => setTrimDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Export Audio Trim</DialogTitle>
        <DialogContent>
          <Typography variant="body2" gutterBottom>
            Set the trim range for export
          </Typography>
          <Box sx={{ mt: 2 }}>
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                label="Start Time"
                value={formatDuration(trimStart)}
                InputProps={{ readOnly: true }}
                fullWidth
              />
              <Button onClick={() => setTrimStart(currentTime)}>
                Set Current
              </Button>
            </Box>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="End Time"
                value={formatDuration(trimEnd)}
                InputProps={{ readOnly: true }}
                fullWidth
              />
              <Button onClick={() => setTrimEnd(currentTime)}>
                Set Current
              </Button>
            </Box>
            <Typography variant="caption" display="block" sx={{ mt: 2 }}>
              Duration: {formatDuration(trimEnd - trimStart)}
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTrimDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleTrimExport} variant="contained">
            Export
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default WaveformPlayer;