import React, { useState } from 'react';
import {
  Box,
  IconButton,
  Typography,
  Slider,
  Tooltip,
  Paper,
} from '@mui/material';
import {
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  Fullscreen as FullscreenIcon,
  RotateRight as RotateIcon,
  Crop as CropIcon,
  Download as DownloadIcon,
  FitScreen as FitIcon,
} from '@mui/icons-material';

interface ImageViewerProps {
  src: string;
  alt?: string;
  title?: string;
  width?: string | number;
  height?: string | number;
  onDownload?: () => void;
}

const ImageViewer: React.FC<ImageViewerProps> = ({
  src,
  alt,
  title,
  width = '100%',
  height = 'auto',
  onDownload,
}) => {
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const handleZoomIn = () => {
    setZoom((prev) => Math.min(prev + 25, 300));
  };

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(prev - 25, 25));
  };

  const handleZoomChange = (_: Event, value: number | number[]) => {
    setZoom(value as number);
  };

  const handleRotate = () => {
    setRotation((prev) => (prev + 90) % 360);
  };

  const handleReset = () => {
    setZoom(100);
    setRotation(0);
    setPosition({ x: 0, y: 0 });
  };

  const handleFullscreen = () => {
    const element = document.getElementById('image-viewer-container');
    if (element?.requestFullscreen) {
      element.requestFullscreen();
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoom > 100) {
      setIsDragging(true);
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y,
      });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && zoom > 100) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  return (
    <Paper
      id="image-viewer-container"
      sx={{
        width,
        height,
        position: 'relative',
        overflow: 'hidden',
        backgroundColor: 'grey.100',
        borderRadius: 2,
      }}
      elevation={3}
    >
      {/* Image Container */}
      <Box
        sx={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: zoom > 100 ? (isDragging ? 'grabbing' : 'grab') : 'default',
          userSelect: 'none',
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <Box
          component="img"
          src={src}
          alt={alt || title}
          sx={{
            maxWidth: '100%',
            maxHeight: '100%',
            transform: `scale(${zoom / 100}) rotate(${rotation}deg) translate(${position.x}px, ${position.y}px)`,
            transition: isDragging ? 'none' : 'transform 0.3s ease',
            pointerEvents: 'none',
          }}
        />
      </Box>

      {/* Controls */}
      <Box
        sx={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%)',
          p: 2,
        }}
      >
        {/* Title */}
        {title && (
          <Typography variant="subtitle1" sx={{ color: 'white', mb: 1 }}>
            {title}
          </Typography>
        )}

        {/* Zoom Controls */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
          <IconButton onClick={handleZoomOut} size="small" sx={{ color: 'white' }}>
            <ZoomOutIcon />
          </IconButton>
          
          <Slider
            value={zoom}
            min={25}
            max={300}
            step={25}
            onChange={handleZoomChange}
            sx={{
              flex: 1,
              color: 'white',
              '& .MuiSlider-thumb': {
                width: 16,
                height: 16,
              },
            }}
          />
          
          <IconButton onClick={handleZoomIn} size="small" sx={{ color: 'white' }}>
            <ZoomInIcon />
          </IconButton>
          
          <Typography variant="caption" sx={{ color: 'white', minWidth: 50 }}>
            {zoom}%
          </Typography>
        </Box>

        {/* Action Buttons */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Rotate">
            <IconButton onClick={handleRotate} size="small" sx={{ color: 'white' }}>
              <RotateIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Fit to Screen">
            <IconButton onClick={handleReset} size="small" sx={{ color: 'white' }}>
              <FitIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Fullscreen">
            <IconButton onClick={handleFullscreen} size="small" sx={{ color: 'white' }}>
              <FullscreenIcon />
            </IconButton>
          </Tooltip>

          {onDownload && (
            <Tooltip title="Download">
              <IconButton onClick={onDownload} size="small" sx={{ color: 'white' }}>
                <DownloadIcon />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Box>
    </Paper>
  );
};

export default ImageViewer;