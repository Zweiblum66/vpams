import React, { useEffect, useRef, useState } from 'react';
import { Box, CircularProgress } from '@mui/material';
import videojs from 'video.js';
import Player from 'video.js/dist/types/player';
import 'video.js/dist/video-js.css';

// Import HLS support
import 'videojs-contrib-hls';

interface VideoJsPlayerProps {
  src: string;
  poster?: string;
  height?: string | number;
  autoplay?: boolean;
  controls?: boolean;
  muted?: boolean;
  loop?: boolean;
  preload?: 'auto' | 'metadata' | 'none';
  // Additional props for advanced features
  sources?: Array<{
    src: string;
    type: string;
    label?: string;
    resolution?: number;
  }>;
  tracks?: Array<{
    kind: 'subtitles' | 'captions' | 'descriptions' | 'chapters' | 'metadata';
    src: string;
    srclang: string;
    label: string;
    default?: boolean;
  }>;
  onReady?: (player: Player) => void;
  onPlay?: () => void;
  onPause?: () => void;
  onEnded?: () => void;
  onTimeUpdate?: (currentTime: number) => void;
  onError?: (error: any) => void;
  // Frame-accurate playback support
  frameRate?: number;
  timecodeDisplay?: boolean;
  // Marker support
  markers?: Array<{
    time: number;
    text: string;
    class?: string;
  }>;
}

const VideoJsPlayer: React.FC<VideoJsPlayerProps> = ({
  src,
  poster,
  height = '100%',
  autoplay = false,
  controls = true,
  muted = false,
  loop = false,
  preload = 'metadata',
  sources,
  tracks,
  onReady,
  onPlay,
  onPause,
  onEnded,
  onTimeUpdate,
  onError,
  frameRate = 24,
  timecodeDisplay = false,
  markers,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const playerRef = useRef<Player | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!videoRef.current) return;

    // Video.js options
    const options: any = {
      autoplay,
      controls,
      muted,
      loop,
      preload,
      fluid: true,
      responsive: true,
      playbackRates: [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2],
      controlBar: {
        playToggle: { order: 0 },
        volumePanel: {
          inline: false,
          order: 1,
        },
        currentTimeDisplay: { order: 2 },
        timeDivider: { order: 3 },
        durationDisplay: { order: 4 },
        progressControl: { order: 5 },
        liveDisplay: { order: 6 },
        seekToLive: { order: 7 },
        remainingTimeDisplay: { order: 8 },
        customControlSpacer: { order: 9 },
        playbackRateMenuButton: {
          order: 10,
          playbackRates: [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2],
        },
        chaptersButton: { order: 11 },
        descriptionsButton: { order: 12 },
        subsCapsButton: { order: 13 },
        audioTrackButton: { order: 14 },
        pictureInPictureToggle: { order: 15 },
        fullscreenToggle: { order: 16 },
      },
      // Enable HLS support
      html5: {
        vhs: {
          overrideNative: true,
          enableLowInitialPlaylist: true,
          smoothQualityChange: true,
          fastQualityChange: true,
        },
        nativeVideoTracks: false,
        nativeAudioTracks: false,
        nativeTextTracks: false,
      },
    };

    // Add poster if provided
    if (poster) {
      options.poster = poster;
    }

    // Configure sources
    if (sources && sources.length > 0) {
      options.sources = sources;
    } else {
      options.sources = [{
        src,
        type: getVideoType(src),
      }];
    }

    // Add text tracks
    if (tracks && tracks.length > 0) {
      options.tracks = tracks;
    }

    // Initialize Video.js player
    playerRef.current = videojs(videoRef.current, options, function onPlayerReady() {
      const player = this as Player;
      
      setIsLoading(false);

      // Add quality menu button if multiple sources
      if (sources && sources.length > 1) {
        addQualitySelector(player, sources);
      }

      // Add frame-accurate controls
      if (timecodeDisplay) {
        addTimecodeDisplay(player, frameRate);
      }

      // Add markers
      if (markers && markers.length > 0) {
        addMarkers(player, markers);
      }

      // Event handlers
      player.on('play', () => onPlay?.());
      player.on('pause', () => onPause?.());
      player.on('ended', () => onEnded?.());
      player.on('timeupdate', () => {
        const currentTime = player.currentTime();
        onTimeUpdate?.(currentTime || 0);
      });
      player.on('error', (error: any) => onError?.(error));
      
      // Callback when ready
      onReady?.(player);

      // Keyboard shortcuts
      player.on('keydown', (e: KeyboardEvent) => {
        handleKeyboardShortcuts(e, player, frameRate);
      });
    });

    // Cleanup
    return () => {
      if (playerRef.current && !playerRef.current.isDisposed()) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [src, sources, poster, autoplay, controls, muted, loop, preload, frameRate]);

  // Helper function to determine video type
  const getVideoType = (url: string): string => {
    if (url.includes('.m3u8')) return 'application/x-mpegURL';
    if (url.includes('.mpd')) return 'application/dash+xml';
    if (url.includes('.mp4')) return 'video/mp4';
    if (url.includes('.webm')) return 'video/webm';
    if (url.includes('.ogv')) return 'video/ogg';
    return 'video/mp4'; // default
  };

  // Add quality selector for multiple sources
  const addQualitySelector = (player: Player, sources: any[]) => {
    const qualityLevels = player.qualityLevels();
    
    // Enable quality level selection
    qualityLevels.on('change', () => {
      console.log('Quality changed to:', qualityLevels[qualityLevels.selectedIndex]);
    });

    // Create quality menu button
    const MenuButton = videojs.getComponent('MenuButton');
    const MenuItem = videojs.getComponent('MenuItem');

    class QualityMenuItem extends MenuItem {
      constructor(player: Player, options: any) {
        super(player, options);
        this.on('click', () => {
          // Change source
          player.src(options.source);
          
          // Update selected state
          const qualityMenuButton = player.controlBar.getChild('qualityMenuButton');
          if (qualityMenuButton) {
            const items = (qualityMenuButton as any).items;
            items.forEach((item: any) => {
              item.selected(item.options_.source.src === options.source.src);
            });
          }
        });
      }
    }

    class QualityMenuButton extends MenuButton {
      constructor(player: Player, options: any) {
        super(player, options);
        this.controlText('Quality');
        this.addClass('vjs-quality-button');
      }

      createItems() {
        const items = [];
        const currentSrc = player.currentSrc();

        for (const source of sources) {
          items.push(new QualityMenuItem(player, {
            label: source.label || `${source.resolution}p`,
            source,
            selected: source.src === currentSrc,
          }));
        }

        return items;
      }
    }

    // Register and add the button
    videojs.registerComponent('QualityMenuButton', QualityMenuButton);
    player.controlBar.addChild('qualityMenuButton', {}, 10);
  };

  // Add timecode display for frame-accurate playback
  const addTimecodeDisplay = (player: Player, fps: number) => {
    const Component = videojs.getComponent('Component');

    class TimecodeDisplay extends Component {
      constructor(player: Player, options: any) {
        super(player, options);
        this.addClass('vjs-timecode-display');
        this.on(player, 'timeupdate', this.updateDisplay);
      }

      createEl() {
        return videojs.dom.createEl('div', {
          className: 'vjs-timecode vjs-time-control vjs-control',
          innerHTML: '<span class="vjs-control-text">Timecode</span><span>00:00:00:00</span>',
        });
      }

      updateDisplay() {
        const time = player.currentTime() || 0;
        const timecode = secondsToTimecode(time, fps);
        this.el().querySelector('span:last-child')!.textContent = timecode;
      }
    }

    videojs.registerComponent('TimecodeDisplay', TimecodeDisplay);
    player.controlBar.addChild('timecodeDisplay', {}, 3);
  };

  // Add markers support
  const addMarkers = (player: Player, markers: any[]) => {
    const markerDiv = videojs.dom.createEl('div', {
      className: 'vjs-markers',
    });

    player.el().appendChild(markerDiv);

    markers.forEach((marker) => {
      const markerEl = videojs.dom.createEl('div', {
        className: `vjs-marker ${marker.class || ''}`,
        innerHTML: `<span>${marker.text}</span>`,
      });

      const duration = player.duration() || 0;
      if (duration > 0) {
        const percent = (marker.time / duration) * 100;
        markerEl.style.left = `${percent}%`;
      }

      markerEl.addEventListener('click', () => {
        player.currentTime(marker.time);
      });

      markerDiv.appendChild(markerEl);
    });
  };

  // Handle keyboard shortcuts
  const handleKeyboardShortcuts = (e: KeyboardEvent, player: Player, fps: number) => {
    const currentTime = player.currentTime() || 0;
    const duration = player.duration() || 0;

    switch (e.key) {
      case 'k':
      case ' ':
        e.preventDefault();
        if (player.paused()) {
          player.play();
        } else {
          player.pause();
        }
        break;
      
      case 'j':
        e.preventDefault();
        player.currentTime(Math.max(0, currentTime - 10));
        break;
      
      case 'l':
        e.preventDefault();
        player.currentTime(Math.min(duration, currentTime + 10));
        break;
      
      case 'ArrowLeft':
        e.preventDefault();
        if (e.shiftKey) {
          // Frame backward
          player.currentTime(Math.max(0, currentTime - (1 / fps)));
        } else {
          player.currentTime(Math.max(0, currentTime - 5));
        }
        break;
      
      case 'ArrowRight':
        e.preventDefault();
        if (e.shiftKey) {
          // Frame forward
          player.currentTime(Math.min(duration, currentTime + (1 / fps)));
        } else {
          player.currentTime(Math.min(duration, currentTime + 5));
        }
        break;
      
      case 'ArrowUp':
        e.preventDefault();
        player.volume(Math.min(1, player.volume() + 0.1));
        break;
      
      case 'ArrowDown':
        e.preventDefault();
        player.volume(Math.max(0, player.volume() - 0.1));
        break;
      
      case 'm':
        e.preventDefault();
        player.muted(!player.muted());
        break;
      
      case 'f':
        e.preventDefault();
        if (player.isFullscreen()) {
          player.exitFullscreen();
        } else {
          player.requestFullscreen();
        }
        break;
      
      case '0':
      case 'Home':
        e.preventDefault();
        player.currentTime(0);
        break;
      
      case 'End':
        e.preventDefault();
        player.currentTime(duration);
        break;
      
      case '1':
      case '2':
      case '3':
      case '4':
      case '5':
      case '6':
      case '7':
      case '8':
      case '9':
        e.preventDefault();
        const percent = parseInt(e.key) * 10;
        player.currentTime(duration * (percent / 100));
        break;
    }
  };

  // Convert seconds to timecode format
  const secondsToTimecode = (seconds: number, fps: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const frames = Math.floor((seconds % 1) * fps);

    return [
      hours.toString().padStart(2, '0'),
      minutes.toString().padStart(2, '0'),
      secs.toString().padStart(2, '0'),
      frames.toString().padStart(2, '0'),
    ].join(':');
  };

  return (
    <Box
      sx={{
        position: 'relative',
        width: '100%',
        height,
        backgroundColor: 'black',
        '& .video-js': {
          width: '100%',
          height: '100%',
        },
        '& .vjs-big-play-button': {
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
        },
        '& .vjs-timecode': {
          fontFamily: 'monospace',
          minWidth: '110px',
        },
        '& .vjs-markers': {
          position: 'absolute',
          bottom: '3em',
          left: 0,
          right: 0,
          height: '5px',
        },
        '& .vjs-marker': {
          position: 'absolute',
          width: '5px',
          height: '5px',
          backgroundColor: 'yellow',
          cursor: 'pointer',
          '&:hover span': {
            display: 'block',
          },
          '& span': {
            display: 'none',
            position: 'absolute',
            bottom: '10px',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            color: 'white',
            padding: '2px 5px',
            borderRadius: '3px',
            fontSize: '12px',
            whiteSpace: 'nowrap',
          },
        },
      }}
    >
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
      <video
        ref={videoRef}
        className="video-js vjs-big-play-centered vjs-theme-default"
      />
    </Box>
  );
};

export default VideoJsPlayer;