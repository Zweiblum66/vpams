import React, { useState, useRef, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Button,
  IconButton,
  Typography,
  Chip,
  Divider,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Close,
  PlayArrow,
  Pause,
  GetApp,
  Timeline,
  Folder,
} from '@mui/icons-material';
import { Asset } from '../types';

interface AssetPreviewProps {
  asset: Asset;
  open: boolean;
  onClose: () => void;
  onImport: (asset: Asset) => void;
}

const AssetPreview: React.FC<AssetPreviewProps> = ({
  asset,
  open,
  onClose,
  onImport,
}) => {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (open) {
      setLoading(true);
      setError(null);
      setPlaying(false);
    }
  }, [open, asset]);

  const handlePlayPause = () => {
    const mediaElement = videoRef.current || audioRef.current;
    if (!mediaElement) return;

    if (playing) {
      mediaElement.pause();
    } else {
      mediaElement.play();
    }
    setPlaying(!playing);
  };

  const handleLoadedData = () => {
    setLoading(false);
  };

  const handleError = () => {
    setError('Failed to load preview');
    setLoading(false);
  };

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const renderPreview = () => {
    if (error) {
      return <Alert severity="error">{error}</Alert>;
    }

    switch (asset.type) {
      case 'video':
        return (
          <Box sx={{ position: 'relative', backgroundColor: '#000' }}>
            <video
              ref={videoRef}
              src={asset.proxyUrl || asset.url}
              style={{ width: '100%', maxHeight: '400px' }}
              onLoadedData={handleLoadedData}
              onError={handleError}
              onEnded={() => setPlaying(false)}
              controls={false}
            />
            {loading && (
              <Box
                sx={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                }}
              >
                <CircularProgress />
              </Box>
            )}
            <Box
              sx={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                background: 'linear-gradient(transparent, rgba(0,0,0,0.8))',
                p: 2,
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <IconButton onClick={handlePlayPause} sx={{ color: 'white' }}>
                {playing ? <Pause /> : <PlayArrow />}
              </IconButton>
              {asset.metadata?.duration && (
                <Typography variant="body2" sx={{ color: 'white', ml: 2 }}>
                  {formatDuration(asset.metadata.duration)}
                </Typography>
              )}
            </Box>
          </Box>
        );

      case 'audio':
        return (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <audio
              ref={audioRef}
              src={asset.proxyUrl || asset.url}
              onLoadedData={handleLoadedData}
              onError={handleError}
              onEnded={() => setPlaying(false)}
              controls
              style={{ width: '100%' }}
            />
            {asset.metadata?.waveformUrl && (
              <img
                src={asset.metadata.waveformUrl}
                alt="Waveform"
                style={{ width: '100%', marginTop: 16 }}
              />
            )}
          </Box>
        );

      case 'image':
        return (
          <Box sx={{ textAlign: 'center' }}>
            <img
              src={asset.proxyUrl || asset.url}
              alt={asset.name}
              style={{ maxWidth: '100%', maxHeight: '400px' }}
              onLoad={handleLoadedData}
              onError={handleError}
            />
          </Box>
        );

      default:
        return (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Folder sx={{ fontSize: 64, color: 'text.secondary' }} />
            <Typography variant="body1" sx={{ mt: 2 }}>
              Preview not available for this file type
            </Typography>
          </Box>
        );
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: '60vh' }
      }}
    >
      <DialogTitle sx={{ pr: 6 }}>
        <Typography variant="h6" noWrap>
          {asset.name}
        </Typography>
        <IconButton
          onClick={onClose}
          sx={{ position: 'absolute', right: 8, top: 8 }}
        >
          <Close />
        </IconButton>
      </DialogTitle>
      
      <DialogContent dividers>
        {renderPreview()}
        
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            File Information
          </Typography>
          
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
            <Chip label={asset.type} size="small" color="primary" />
            <Chip label={formatFileSize(asset.size)} size="small" />
            {asset.metadata?.format && (
              <Chip label={asset.metadata.format} size="small" />
            )}
            {asset.metadata?.resolution && (
              <Chip label={asset.metadata.resolution} size="small" />
            )}
            {asset.metadata?.framerate && (
              <Chip label={`${asset.metadata.framerate} fps`} size="small" />
            )}
            {asset.metadata?.codec && (
              <Chip label={asset.metadata.codec} size="small" />
            )}
          </Box>

          {asset.metadata?.description && (
            <>
              <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
                Description
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {asset.metadata.description}
              </Typography>
            </>
          )}

          {asset.metadata?.tags && asset.metadata.tags.length > 0 && (
            <>
              <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
                Tags
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {asset.metadata.tags.map((tag, index) => (
                  <Chip key={index} label={tag} size="small" variant="outlined" />
                ))}
              </Box>
            </>
          )}
        </Box>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>
          Close
        </Button>
        <Button
          variant="contained"
          startIcon={<GetApp />}
          onClick={() => {
            onImport(asset);
            onClose();
          }}
        >
          Import to Project
        </Button>
        <Button
          variant="outlined"
          startIcon={<Timeline />}
          onClick={() => {
            // TODO: Implement direct timeline import
            onImport(asset);
            onClose();
          }}
        >
          Import to Timeline
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AssetPreview;