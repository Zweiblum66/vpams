import React, { useRef, useEffect, useState } from 'react';
import {
  Box,
  IconButton,
  Slider,
  Typography,
  Paper,
  LinearProgress,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  VolumeUp as VolumeIcon,
  VolumeOff as MuteIcon,
  SkipNext as NextIcon,
  SkipPrevious as PrevIcon,
  Repeat as RepeatIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { formatDuration } from '../../utils/formatters';

interface AudioPlayerProps {
  src: string;
  title?: string;
  artist?: string;
  albumArt?: string;
  autoPlay?: boolean;
  onTimeUpdate?: (currentTime: number) => void;
  onDurationChange?: (duration: number) => void;
  onEnded?: () => void;
}

const AudioPlayer: React.FC<AudioPlayerProps> = ({
  src,
  title,
  artist,
  albumArt,
  autoPlay = false,
  onTimeUpdate,
  onDurationChange,
  onEnded,
}) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [isRepeat, setIsRepeat] = useState(false);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
      setIsLoading(false);
      if (onDurationChange) {
        onDurationChange(audio.duration);
      }
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      if (onTimeUpdate) {
        onTimeUpdate(audio.currentTime);
      }
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleEnded = () => {
      if (isRepeat) {
        audio.currentTime = 0;
        audio.play();
      } else {
        setIsPlaying(false);
        if (onEnded) {
          onEnded();
        }
      }
    };

    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [onTimeUpdate, onDurationChange, onEnded, isRepeat]);

  const handlePlayPause = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
  };

  const handleSeek = (_: Event, value: number | number[]) => {
    const audio = audioRef.current;
    if (!audio) return;

    const newTime = value as number;
    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleVolumeChange = (_: Event, value: number | number[]) => {
    const audio = audioRef.current;
    if (!audio) return;

    const newVolume = value as number;
    audio.volume = newVolume;
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  };

  const toggleMute = () => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.muted = !audio.muted;
    setIsMuted(audio.muted);
  };

  const changePlaybackRate = () => {
    const audio = audioRef.current;
    if (!audio) return;

    const rates = [0.5, 0.75, 1, 1.25, 1.5, 2];
    const currentIndex = rates.indexOf(playbackRate);
    const nextIndex = (currentIndex + 1) % rates.length;
    const newRate = rates[nextIndex];
    
    audio.playbackRate = newRate;
    setPlaybackRate(newRate);
  };

  const skipTime = (seconds: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = Math.max(0, Math.min(duration, audio.currentTime + seconds));
  };

  return (
    <Paper
      sx={{
        p: 3,
        backgroundColor: 'background.paper',
        borderRadius: 2,
      }}
      elevation={3}
    >
      <audio ref={audioRef} src={src} autoPlay={autoPlay} loop={isRepeat} />

      {/* Album Art and Info */}
      <Box sx={{ display: 'flex', gap: 3, mb: 3 }}>
        {albumArt && (
          <Box
            component="img"
            src={albumArt}
            alt="Album Art"
            sx={{
              width: 120,
              height: 120,
              borderRadius: 2,
              objectFit: 'cover',
            }}
          />
        )}
        <Box sx={{ flex: 1 }}>
          {title && (
            <Typography variant="h6" gutterBottom>
              {title}
            </Typography>
          )}
          {artist && (
            <Typography variant="body2" color="text.secondary">
              {artist}
            </Typography>
          )}
        </Box>
      </Box>

      {/* Progress Bar */}
      {isLoading ? (
        <LinearProgress sx={{ mb: 2 }} />
      ) : (
        <Box sx={{ mb: 2 }}>
          <Slider
            value={currentTime}
            min={0}
            max={duration || 1}
            onChange={handleSeek}
            sx={{
              '& .MuiSlider-thumb': {
                width: 16,
                height: 16,
              },
            }}
          />
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              {formatDuration(currentTime)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatDuration(duration)}
            </Typography>
          </Box>
        </Box>
      )}

      {/* Controls */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1, mb: 2 }}>
        <IconButton onClick={() => skipTime(-10)} disabled={isLoading}>
          <PrevIcon />
        </IconButton>

        <IconButton
          onClick={handlePlayPause}
          disabled={isLoading}
          sx={{
            backgroundColor: 'primary.main',
            color: 'primary.contrastText',
            '&:hover': {
              backgroundColor: 'primary.dark',
            },
          }}
        >
          {isPlaying ? <PauseIcon /> : <PlayIcon />}
        </IconButton>

        <IconButton onClick={() => skipTime(10)} disabled={isLoading}>
          <NextIcon />
        </IconButton>
      </Box>

      {/* Additional Controls */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        {/* Volume */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
          <IconButton onClick={toggleMute} size="small">
            {isMuted || volume === 0 ? <MuteIcon /> : <VolumeIcon />}
          </IconButton>
          <Slider
            value={isMuted ? 0 : volume}
            min={0}
            max={1}
            step={0.1}
            onChange={handleVolumeChange}
            sx={{
              width: 100,
              '& .MuiSlider-thumb': {
                width: 12,
                height: 12,
              },
            }}
          />
        </Box>

        {/* Playback Speed */}
        <IconButton onClick={changePlaybackRate} size="small">
          <Typography variant="caption">{playbackRate}x</Typography>
        </IconButton>

        {/* Repeat */}
        <IconButton
          onClick={() => setIsRepeat(!isRepeat)}
          size="small"
          color={isRepeat ? 'primary' : 'default'}
        >
          <RepeatIcon />
        </IconButton>
      </Box>
    </Paper>
  );
};

export default AudioPlayer;