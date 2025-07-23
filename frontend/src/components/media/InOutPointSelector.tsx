import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Slider,
  TextField,
  InputAdornment,
  Chip,
  Tooltip,
  Stack,
  FormControlLabel,
  Switch,
  Alert,
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  VolumeUp,
  VolumeOff,
  Fullscreen,
  FullscreenExit,
  SkipPrevious,
  SkipNext,
  Replay10,
  Forward10,
  Speed,
  CropFree,
  ContentCut,
  Loop,
  FiberManualRecord,
  Stop,
} from '@mui/icons-material';
import { Asset, MediaMarker } from '../../types';

interface InOutPointSelectorProps {
  asset: Asset;
  initialInPoint?: number;
  initialOutPoint?: number;
  onInPointChange?: (inPoint: number) => void;
  onOutPointChange?: (outPoint: number) => void;
  onSelectionChange?: (inPoint: number, outPoint: number) => void;
  showPreview?: boolean;
  readOnly?: boolean;
}

interface VideoState {
  currentTime: number;
  duration: number;
  playing: boolean;
  volume: number;
  muted: boolean;
  playbackRate: number;
  buffered: number;
  seeking: boolean;
  fullscreen: boolean;
  loaded: boolean;
  error: string | null;
}

const InOutPointSelector: React.FC<InOutPointSelectorProps> = ({
  asset,
  initialInPoint = 0,
  initialOutPoint = 0,
  onInPointChange,
  onOutPointChange,
  onSelectionChange,
  showPreview = true,
  readOnly = false,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [inPoint, setInPoint] = useState(initialInPoint);
  const [outPoint, setOutPoint] = useState(initialOutPoint);
  const [previewMode, setPreviewMode] = useState(false);
  const [loopPlayback, setLoopPlayback] = useState(false);
  const [snapToFrames, setSnapToFrames] = useState(true);
  const [videoState, setVideoState] = useState<VideoState>({
    currentTime: 0,
    duration: 0,
    playing: false,
    volume: 1,
    muted: false,
    playbackRate: 1,
    buffered: 0,
    seeking: false,
    fullscreen: false,
    loaded: false,
    error: null,
  });

  const frameRate = 25; // Default frame rate, should be read from asset metadata
  const frameDuration = 1 / frameRate;

  // Video event handlers
  const handleLoadedMetadata = useCallback(() => {
    if (videoRef.current) {
      const duration = videoRef.current.duration;
      setVideoState(prev => ({
        ...prev,
        duration,
        loaded: true,
      }));
      
      // Set initial out point to end of video if not specified
      if (initialOutPoint === 0) {
        setOutPoint(duration);
        onOutPointChange?.(duration);
      }
    }
  }, [initialOutPoint, onOutPointChange]);

  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current && !videoState.seeking) {
      const currentTime = videoRef.current.currentTime;
      setVideoState(prev => ({ ...prev, currentTime }));
      
      // Handle loop playback between in and out points
      if (loopPlayback && currentTime >= outPoint && outPoint > inPoint) {
        videoRef.current.currentTime = inPoint;
      }
    }
  }, [videoState.seeking, loopPlayback, inPoint, outPoint]);

  const handleProgress = useCallback(() => {
    if (videoRef.current) {
      const buffered = videoRef.current.buffered;
      if (buffered.length > 0) {
        const bufferedEnd = buffered.end(buffered.length - 1);
        const duration = videoRef.current.duration;
        setVideoState(prev => ({
          ...prev,
          buffered: (bufferedEnd / duration) * 100,
        }));
      }
    }
  }, []);

  const handleError = useCallback(() => {
    setVideoState(prev => ({
      ...prev,
      error: 'Failed to load video',
    }));
  }, []);

  // Playback controls
  const togglePlayPause = useCallback(() => {
    if (videoRef.current) {
      if (videoState.playing) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setVideoState(prev => ({ ...prev, playing: !prev.playing }));
    }
  }, [videoState.playing]);

  const seekTo = useCallback((time: number) => {
    if (videoRef.current) {
      const clampedTime = Math.max(0, Math.min(time, videoState.duration));
      videoRef.current.currentTime = clampedTime;
      setVideoState(prev => ({ ...prev, currentTime: clampedTime }));
    }
  }, [videoState.duration]);

  const skipFrames = useCallback((frames: number) => {
    const newTime = videoState.currentTime + (frames * frameDuration);
    seekTo(newTime);
  }, [videoState.currentTime, frameDuration, seekTo]);

  const goToInPoint = useCallback(() => {
    seekTo(inPoint);
  }, [inPoint, seekTo]);

  const goToOutPoint = useCallback(() => {
    seekTo(outPoint);
  }, [outPoint, seekTo]);

  const setInPointToCurrent = useCallback(() => {
    if (readOnly) return;
    const newInPoint = snapToFrames 
      ? Math.round(videoState.currentTime * frameRate) / frameRate
      : videoState.currentTime;
    
    setInPoint(newInPoint);
    onInPointChange?.(newInPoint);
    onSelectionChange?.(newInPoint, outPoint);
  }, [videoState.currentTime, outPoint, snapToFrames, frameRate, readOnly, onInPointChange, onSelectionChange]);

  const setOutPointToCurrent = useCallback(() => {
    if (readOnly) return;
    const newOutPoint = snapToFrames 
      ? Math.round(videoState.currentTime * frameRate) / frameRate
      : videoState.currentTime;
    
    setOutPoint(newOutPoint);
    onOutPointChange?.(newOutPoint);
    onSelectionChange?.(inPoint, newOutPoint);
  }, [videoState.currentTime, inPoint, snapToFrames, frameRate, readOnly, onOutPointChange, onSelectionChange]);

  const clearSelection = useCallback(() => {
    if (readOnly) return;
    setInPoint(0);
    setOutPoint(videoState.duration);
    onInPointChange?.(0);
    onOutPointChange?.(videoState.duration);
    onSelectionChange?.(0, videoState.duration);
  }, [videoState.duration, readOnly, onInPointChange, onOutPointChange, onSelectionChange]);

  const playSelection = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.currentTime = inPoint;
      videoRef.current.play();
      setVideoState(prev => ({ ...prev, playing: true }));
    }
  }, [inPoint]);

  const toggleMute = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.muted = !videoState.muted;
      setVideoState(prev => ({ ...prev, muted: !prev.muted }));
    }
  }, [videoState.muted]);

  const handleVolumeChange = useCallback((value: number) => {
    if (videoRef.current) {
      videoRef.current.volume = value;
      setVideoState(prev => ({ ...prev, volume: value }));
    }
  }, []);

  const handlePlaybackRateChange = useCallback((rate: number) => {
    if (videoRef.current) {
      videoRef.current.playbackRate = rate;
      setVideoState(prev => ({ ...prev, playbackRate: rate }));
    }
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (containerRef.current) {
      if (!videoState.fullscreen) {
        containerRef.current.requestFullscreen();
      } else {
        document.exitFullscreen();
      }
      setVideoState(prev => ({ ...prev, fullscreen: !prev.fullscreen }));
    }
  }, [videoState.fullscreen]);

  const formatTime = useCallback((seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const frames = Math.floor((seconds % 1) * frameRate);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`;
  }, [frameRate]);

  const parseTime = useCallback((timeString: string) => {
    const parts = timeString.split(':').map(Number);
    if (parts.length === 3) {
      // MM:SS:FF
      const [minutes, seconds, frames] = parts;
      return minutes * 60 + seconds + (frames / frameRate);
    } else if (parts.length === 4) {
      // HH:MM:SS:FF
      const [hours, minutes, seconds, frames] = parts;
      return hours * 3600 + minutes * 60 + seconds + (frames / frameRate);
    }
    return 0;
  }, [frameRate]);

  const duration = outPoint - inPoint;

  // Update internal state when props change
  useEffect(() => {
    setInPoint(initialInPoint);
    setOutPoint(initialOutPoint);
  }, [initialInPoint, initialOutPoint]);

  if (!asset || asset.asset_type !== 'video') {
    return (
      <Alert severity="error">
        Invalid asset. In/Out point selector only works with video assets.
      </Alert>
    );
  }

  return (
    <Box ref={containerRef} sx={{ width: '100%', bgcolor: 'background.paper' }}>
      <Paper sx={{ p: 2 }}>
        {/* Video Player */}
        <Box sx={{ position: 'relative', bgcolor: 'black', borderRadius: 1, mb: 2 }}>
          <video
            ref={videoRef}
            style={{
              width: '100%',
              height: 'auto',
              maxHeight: '400px',
              display: 'block',
            }}
            onLoadedMetadata={handleLoadedMetadata}
            onTimeUpdate={handleTimeUpdate}
            onProgress={handleProgress}
            onError={handleError}
            preload="metadata"
            crossOrigin="anonymous"
          >
            <source src={asset.proxy_path || asset.file_path} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
          
          {/* Video Overlay Controls */}
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              bgcolor: 'rgba(0, 0, 0, 0.3)',
              opacity: 0,
              transition: 'opacity 0.3s',
              '&:hover': { opacity: 1 },
            }}
          >
            <IconButton
              size="large"
              onClick={togglePlayPause}
              sx={{ color: 'white', bgcolor: 'rgba(0, 0, 0, 0.5)' }}
            >
              {videoState.playing ? <Pause /> : <PlayArrow />}
            </IconButton>
          </Box>
        </Box>

        {/* Timeline */}
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="body2" sx={{ minWidth: 60 }}>
              {formatTime(videoState.currentTime)}
            </Typography>
            <Box sx={{ flex: 1, position: 'relative' }}>
              <Slider
                value={videoState.currentTime}
                min={0}
                max={videoState.duration || 100}
                onChange={(_, value) => seekTo(value as number)}
                sx={{ height: 8 }}
                disabled={!videoState.loaded}
              />
              {/* In/Out Point Indicators */}
              <Box
                sx={{
                  position: 'absolute',
                  top: 0,
                  left: `${(inPoint / videoState.duration) * 100}%`,
                  width: 2,
                  height: '100%',
                  bgcolor: 'success.main',
                  zIndex: 1,
                }}
              />
              <Box
                sx={{
                  position: 'absolute',
                  top: 0,
                  left: `${(outPoint / videoState.duration) * 100}%`,
                  width: 2,
                  height: '100%',
                  bgcolor: 'error.main',
                  zIndex: 1,
                }}
              />
              {/* Selection Range */}
              <Box
                sx={{
                  position: 'absolute',
                  top: 0,
                  left: `${(inPoint / videoState.duration) * 100}%`,
                  width: `${((outPoint - inPoint) / videoState.duration) * 100}%`,
                  height: '100%',
                  bgcolor: 'primary.main',
                  opacity: 0.3,
                  zIndex: 0,
                }}
              />
            </Box>
            <Typography variant="body2" sx={{ minWidth: 60 }}>
              {formatTime(videoState.duration)}
            </Typography>
          </Box>
        </Box>

        {/* Transport Controls */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <IconButton onClick={() => skipFrames(-10)} disabled={!videoState.loaded}>
            <Replay10 />
          </IconButton>
          <IconButton onClick={() => skipFrames(-1)} disabled={!videoState.loaded}>
            <SkipPrevious />
          </IconButton>
          <IconButton onClick={togglePlayPause} disabled={!videoState.loaded}>
            {videoState.playing ? <Pause /> : <PlayArrow />}
          </IconButton>
          <IconButton onClick={() => skipFrames(1)} disabled={!videoState.loaded}>
            <SkipNext />
          </IconButton>
          <IconButton onClick={() => skipFrames(10)} disabled={!videoState.loaded}>
            <Forward10 />
          </IconButton>
          
          <Box sx={{ flex: 1 }} />
          
          <IconButton onClick={toggleMute}>
            {videoState.muted ? <VolumeOff /> : <VolumeUp />}
          </IconButton>
          <Slider
            value={videoState.volume}
            min={0}
            max={1}
            step={0.1}
            onChange={(_, value) => handleVolumeChange(value as number)}
            sx={{ width: 80 }}
          />
          <IconButton onClick={toggleFullscreen}>
            {videoState.fullscreen ? <FullscreenExit /> : <Fullscreen />}
          </IconButton>
        </Box>

        {/* In/Out Point Controls */}
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              In Point
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <TextField
                size="small"
                value={formatTime(inPoint)}
                onChange={(e) => {
                  const time = parseTime(e.target.value);
                  if (time >= 0 && time <= videoState.duration) {
                    setInPoint(time);
                    onInPointChange?.(time);
                  }
                }}
                disabled={readOnly}
                sx={{ width: 120 }}
              />
              <Button
                variant="outlined"
                size="small"
                onClick={setInPointToCurrent}
                disabled={readOnly}
                startIcon={<FiberManualRecord />}
              >
                Set In
              </Button>
              <Button
                variant="outlined"
                size="small"
                onClick={goToInPoint}
                disabled={!videoState.loaded}
              >
                Go To
              </Button>
            </Box>
          </Box>
          
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Out Point
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <TextField
                size="small"
                value={formatTime(outPoint)}
                onChange={(e) => {
                  const time = parseTime(e.target.value);
                  if (time >= 0 && time <= videoState.duration) {
                    setOutPoint(time);
                    onOutPointChange?.(time);
                  }
                }}
                disabled={readOnly}
                sx={{ width: 120 }}
              />
              <Button
                variant="outlined"
                size="small"
                onClick={setOutPointToCurrent}
                disabled={readOnly}
                startIcon={<Stop />}
              >
                Set Out
              </Button>
              <Button
                variant="outlined"
                size="small"
                onClick={goToOutPoint}
                disabled={!videoState.loaded}
              >
                Go To
              </Button>
            </Box>
          </Box>
        </Box>

        {/* Selection Info and Actions */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Chip
              label={`Duration: ${formatTime(duration)}`}
              variant="outlined"
              color="primary"
            />
            <Chip
              label={`In: ${formatTime(inPoint)}`}
              variant="outlined"
              color="success"
            />
            <Chip
              label={`Out: ${formatTime(outPoint)}`}
              variant="outlined"
              color="error"
            />
          </Box>
          
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              onClick={playSelection}
              disabled={!videoState.loaded}
              startIcon={<PlayArrow />}
            >
              Play Selection
            </Button>
            {!readOnly && (
              <Button
                variant="outlined"
                onClick={clearSelection}
                startIcon={<CropFree />}
              >
                Clear
              </Button>
            )}
          </Box>
        </Box>

        {/* Options */}
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControlLabel
            control={
              <Switch
                checked={loopPlayback}
                onChange={(e) => setLoopPlayback(e.target.checked)}
              />
            }
            label="Loop Selection"
          />
          <FormControlLabel
            control={
              <Switch
                checked={snapToFrames}
                onChange={(e) => setSnapToFrames(e.target.checked)}
              />
            }
            label="Snap to Frames"
          />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Speed />
            <Typography variant="body2">Speed:</Typography>
            <Button
              size="small"
              variant={videoState.playbackRate === 0.5 ? 'contained' : 'outlined'}
              onClick={() => handlePlaybackRateChange(0.5)}
            >
              0.5x
            </Button>
            <Button
              size="small"
              variant={videoState.playbackRate === 1 ? 'contained' : 'outlined'}
              onClick={() => handlePlaybackRateChange(1)}
            >
              1x
            </Button>
            <Button
              size="small"
              variant={videoState.playbackRate === 1.5 ? 'contained' : 'outlined'}
              onClick={() => handlePlaybackRateChange(1.5)}
            >
              1.5x
            </Button>
            <Button
              size="small"
              variant={videoState.playbackRate === 2 ? 'contained' : 'outlined'}
              onClick={() => handlePlaybackRateChange(2)}
            >
              2x
            </Button>
          </Box>
        </Box>

        {/* Error Display */}
        {videoState.error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {videoState.error}
          </Alert>
        )}
      </Paper>
    </Box>
  );
};

export default InOutPointSelector;