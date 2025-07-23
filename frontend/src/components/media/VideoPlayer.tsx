import React, { useRef, useEffect, useState } from 'react';
import {
  Box,
  IconButton,
  Slider,
  Typography,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  VolumeUp as VolumeIcon,
  VolumeOff as MuteIcon,
  Fullscreen as FullscreenIcon,
  FullscreenExit as ExitFullscreenIcon,
  Settings as SettingsIcon,
  PictureInPictureAlt as PipIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { formatDuration } from '../../utils/formatters';

interface VideoPlayerProps {
  src: string;
  poster?: string;
  width?: string | number;
  height?: string | number;
  autoPlay?: boolean;
  controls?: boolean;
  onTimeUpdate?: (currentTime: number) => void;
  onDurationChange?: (duration: number) => void;
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  src,
  poster,
  width = '100%',
  height = 'auto',
  autoPlay = false,
  controls = true,
  onTimeUpdate,
  onDurationChange,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [showControls, setShowControls] = useState(true);
  const controlsTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      setDuration(video.duration);
      setIsLoading(false);
      if (onDurationChange) {
        onDurationChange(video.duration);
      }
    };

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      if (onTimeUpdate) {
        onTimeUpdate(video.currentTime);
      }
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleVolumeChange = () => {
      setVolume(video.volume);
      setIsMuted(video.muted);
    };

    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('volumechange', handleVolumeChange);

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('volumechange', handleVolumeChange);
    };
  }, [onTimeUpdate, onDurationChange]);

  const handlePlayPause = () => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      video.pause();
    } else {
      video.play();
    }
  };

  const handleSeek = (_: Event, value: number | number[]) => {
    const video = videoRef.current;
    if (!video) return;

    const newTime = value as number;
    video.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleVolumeChange = (_: Event, value: number | number[]) => {
    const video = videoRef.current;
    if (!video) return;

    const newVolume = value as number;
    video.volume = newVolume;
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  };

  const toggleMute = () => {
    const video = videoRef.current;
    if (!video) return;

    video.muted = !video.muted;
    setIsMuted(video.muted);
  };

  const toggleFullscreen = async () => {
    const container = containerRef.current;
    if (!container) return;

    if (!isFullscreen) {
      if (container.requestFullscreen) {
        await container.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        await document.exitFullscreen();
      }
    }
    setIsFullscreen(!isFullscreen);
  };

  const togglePictureInPicture = async () => {
    const video = videoRef.current;
    if (!video) return;

    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture();
      } else {
        await video.requestPictureInPicture();
      }
    } catch (error) {
      console.error('PiP not supported', error);
    }
  };

  const changePlaybackRate = () => {
    const video = videoRef.current;
    if (!video) return;

    const rates = [0.5, 0.75, 1, 1.25, 1.5, 2];
    const currentIndex = rates.indexOf(playbackRate);
    const nextIndex = (currentIndex + 1) % rates.length;
    const newRate = rates[nextIndex];
    
    video.playbackRate = newRate;
    setPlaybackRate(newRate);
  };

  const handleMouseMove = () => {
    setShowControls(true);
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    controlsTimeoutRef.current = setTimeout(() => {
      if (isPlaying) {
        setShowControls(false);
      }
    }, 3000);
  };

  return (
    <Box
      ref={containerRef}
      sx={{
        position: 'relative',
        width,
        height,
        backgroundColor: 'black',
        cursor: showControls ? 'default' : 'none',
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => isPlaying && setShowControls(false)}
    >
      <video
        ref={videoRef}
        src={src}
        poster={poster}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
        }}
        autoPlay={autoPlay}
      />

      {isLoading && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
          }}
        >
          <CircularProgress size={60} />
        </Box>
      )}

      {controls && (
        <Box
          sx={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%)',
            p: 2,
            opacity: showControls ? 1 : 0,
            transition: 'opacity 0.3s',
          }}
        >
          {/* Progress Bar */}
          <Slider
            value={currentTime}
            min={0}
            max={duration || 1}
            onChange={handleSeek}
            sx={{
              mb: 1,
              '& .MuiSlider-thumb': {
                width: 12,
                height: 12,
              },
            }}
          />

          {/* Controls */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Play/Pause */}
            <IconButton onClick={handlePlayPause} size="small" sx={{ color: 'white' }}>
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
            </IconButton>

            {/* Time */}
            <Typography variant="caption" sx={{ color: 'white', minWidth: 100 }}>
              {formatDuration(currentTime)} / {formatDuration(duration)}
            </Typography>

            {/* Volume */}
            <IconButton onClick={toggleMute} size="small" sx={{ color: 'white' }}>
              {isMuted || volume === 0 ? <MuteIcon /> : <VolumeIcon />}
            </IconButton>
            <Slider
              value={isMuted ? 0 : volume}
              min={0}
              max={1}
              step={0.1}
              onChange={handleVolumeChange}
              sx={{
                width: 80,
                color: 'white',
                '& .MuiSlider-thumb': {
                  width: 12,
                  height: 12,
                },
              }}
            />

            <Box sx={{ flex: 1 }} />

            {/* Playback Speed */}
            <Tooltip title="Playback Speed">
              <IconButton onClick={changePlaybackRate} size="small" sx={{ color: 'white' }}>
                <Typography variant="caption">{playbackRate}x</Typography>
              </IconButton>
            </Tooltip>

            {/* Picture in Picture */}
            <Tooltip title="Picture in Picture">
              <IconButton onClick={togglePictureInPicture} size="small" sx={{ color: 'white' }}>
                <PipIcon />
              </IconButton>
            </Tooltip>

            {/* Fullscreen */}
            <Tooltip title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}>
              <IconButton onClick={toggleFullscreen} size="small" sx={{ color: 'white' }}>
                {isFullscreen ? <ExitFullscreenIcon /> : <FullscreenIcon />}
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default VideoPlayer;