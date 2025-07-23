import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  LinearProgress,
  Chip,
  Button,
  Collapse,
  Alert,
  Menu,
  MenuItem,
  Divider,
  Badge,
  Tooltip,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Pause as PauseIcon,
  PlayArrow as ResumeIcon,
  Delete as DeleteIcon,
  Clear as ClearIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Speed as SpeedIcon,
  Schedule as TimeIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';

import { uploadService } from '../../services/uploadService';
import { UploadFile, UploadStatus, UploadStats } from '../../types/upload';
import { formatFileSize, formatDuration } from '../../utils/formatters';
import { logger } from '../../utils/logger';

interface UploadManagerProps {
  uploads: Map<string, UploadFile>;
  onUploadComplete?: (assetId: string, file: UploadFile) => void;
  onUploadError?: (error: Error, file: UploadFile) => void;
  onClearCompleted?: () => void;
  minimized?: boolean;
  onToggleMinimize?: () => void;
}

const UploadManager: React.FC<UploadManagerProps> = ({
  uploads,
  onUploadComplete,
  onUploadError,
  onClearCompleted,
  minimized = false,
  onToggleMinimize,
}) => {
  const [stats, setStats] = useState<UploadStats>({
    totalFiles: 0,
    totalBytes: 0,
    uploadedFiles: 0,
    uploadedBytes: 0,
    failedFiles: 0,
    averageSpeed: 0,
    remainingTime: 0,
  });
  const [speedHistory, setSpeedHistory] = useState<number[]>([]);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);

  useEffect(() => {
    // Calculate stats
    const files = Array.from(uploads.values());
    
    const totalFiles = files.length;
    const totalBytes = files.reduce((sum, file) => sum + file.size, 0);
    const uploadedFiles = files.filter(f => f.status === UploadStatus.COMPLETED).length;
    const uploadedBytes = files.reduce((sum, file) => {
      if (file.status === UploadStatus.COMPLETED) return sum + file.size;
      if (file.status === UploadStatus.UPLOADING) return sum + (file.size * file.progress / 100);
      return sum;
    }, 0);
    const failedFiles = files.filter(f => f.status === UploadStatus.ERROR).length;

    // Calculate average speed from history
    const averageSpeed = speedHistory.length > 0
      ? speedHistory.reduce((sum, speed) => sum + speed, 0) / speedHistory.length
      : 0;

    // Calculate remaining time
    const remainingBytes = totalBytes - uploadedBytes;
    const remainingTime = averageSpeed > 0 ? remainingBytes / averageSpeed : 0;

    setStats({
      totalFiles,
      totalBytes,
      uploadedFiles,
      uploadedBytes,
      failedFiles,
      averageSpeed,
      remainingTime,
    });
  }, [uploads, speedHistory]);

  const handlePauseUpload = (fileId: string) => {
    const file = uploads.get(fileId);
    if (file && file.status === UploadStatus.UPLOADING) {
      uploadService.cancelUpload(fileId);
      // Update file status to paused
      logger.info('Upload paused', {
        fileId,
        fileName: file.name,
        actionType: 'upload_pause',
      });
    }
  };

  const handleResumeUpload = async (fileId: string) => {
    const file = uploads.get(fileId);
    if (file && file.sessionId) {
      try {
        await uploadService.resumeUpload(
          file.sessionId,
          file.file,
          (progress) => {
            // Progress callback
          }
        );
      } catch (error) {
        logger.error('Failed to resume upload', {
          fileId,
          error,
          actionType: 'upload_resume_error',
        });
      }
    }
  };

  const handleRemoveUpload = (fileId: string) => {
    uploadService.cancelUpload(fileId);
    // Remove from uploads map
  };

  const handleCancelAll = () => {
    uploadService.cancelAllUploads();
    setMenuAnchor(null);
  };

  const handleRetryFailed = () => {
    const failedUploads = Array.from(uploads.values()).filter(
      f => f.status === UploadStatus.ERROR
    );
    failedUploads.forEach(file => {
      // Retry logic
    });
    setMenuAnchor(null);
  };

  const getStatusColor = (status: UploadStatus): string => {
    switch (status) {
      case UploadStatus.COMPLETED:
        return 'success';
      case UploadStatus.ERROR:
        return 'error';
      case UploadStatus.UPLOADING:
      case UploadStatus.PROCESSING:
        return 'info';
      case UploadStatus.PAUSED:
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: UploadStatus) => {
    switch (status) {
      case UploadStatus.COMPLETED:
        return <SuccessIcon fontSize="small" />;
      case UploadStatus.ERROR:
        return <ErrorIcon fontSize="small" />;
      case UploadStatus.PAUSED:
        return <WarningIcon fontSize="small" />;
      default:
        return null;
    }
  };

  const activeUploads = Array.from(uploads.values()).filter(
    f => f.status === UploadStatus.UPLOADING || f.status === UploadStatus.PROCESSING
  );

  const overallProgress = stats.totalBytes > 0
    ? (stats.uploadedBytes / stats.totalBytes) * 100
    : 0;

  return (
    <Paper
      sx={{
        position: 'fixed',
        bottom: 20,
        right: 20,
        width: minimized ? 300 : 400,
        maxHeight: minimized ? 60 : 500,
        zIndex: 1300,
        transition: 'all 0.3s',
      }}
      elevation={8}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'primary.main',
          color: 'primary.contrastText',
          cursor: 'pointer',
        }}
        onClick={onToggleMinimize}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Badge badgeContent={activeUploads.length} color="error">
            <UploadIcon />
          </Badge>
          <Typography variant="subtitle1">
            Upload Manager
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {stats.failedFiles > 0 && (
            <Chip
              label={`${stats.failedFiles} failed`}
              size="small"
              color="error"
              sx={{ height: 20 }}
            />
          )}
          <IconButton size="small" sx={{ color: 'inherit' }}>
            {minimized ? <ExpandIcon /> : <CollapseIcon />}
          </IconButton>
        </Box>
      </Box>

      <Collapse in={!minimized}>
        {/* Progress Overview */}
        <Box sx={{ p: 2, pb: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2">
              {stats.uploadedFiles} of {stats.totalFiles} files
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {Math.round(overallProgress)}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={overallProgress}
            sx={{ mb: 1 }}
          />
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Tooltip title="Upload Speed">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <SpeedIcon fontSize="small" color="action" />
                  <Typography variant="caption" color="text.secondary">
                    {formatFileSize(stats.averageSpeed)}/s
                  </Typography>
                </Box>
              </Tooltip>
              {stats.remainingTime > 0 && (
                <Tooltip title="Estimated Time Remaining">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <TimeIcon fontSize="small" color="action" />
                    <Typography variant="caption" color="text.secondary">
                      {formatDuration(stats.remainingTime)}
                    </Typography>
                  </Box>
                </Tooltip>
              )}
            </Box>
            <IconButton
              size="small"
              onClick={(e) => setMenuAnchor(e.currentTarget)}
            >
              <ExpandIcon />
            </IconButton>
          </Box>
        </Box>

        <Divider />

        {/* Upload List */}
        <List sx={{ maxHeight: 300, overflow: 'auto' }}>
          {Array.from(uploads.values()).map((file) => (
            <ListItem key={file.id} dense>
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getStatusIcon(file.status)}
                    <Typography variant="body2" noWrap sx={{ flex: 1 }}>
                      {file.name}
                    </Typography>
                    <Chip
                      label={file.status}
                      size="small"
                      color={getStatusColor(file.status) as any}
                      sx={{ height: 20, textTransform: 'capitalize' }}
                    />
                  </Box>
                }
                secondary={
                  <Box>
                    {(file.status === UploadStatus.UPLOADING ||
                      file.status === UploadStatus.PROCESSING) && (
                      <>
                        <LinearProgress
                          variant="determinate"
                          value={file.progress}
                          sx={{ mt: 0.5 }}
                        />
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                          <Typography variant="caption" color="text.secondary">
                            {formatFileSize(file.size * file.progress / 100)} / {formatFileSize(file.size)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {Math.round(file.progress)}%
                          </Typography>
                        </Box>
                      </>
                    )}
                    {file.status === UploadStatus.ERROR && (
                      <Typography variant="caption" color="error">
                        {file.error}
                      </Typography>
                    )}
                    {file.status === UploadStatus.COMPLETED && (
                      <Typography variant="caption" color="text.secondary">
                        Completed • {formatFileSize(file.size)}
                      </Typography>
                    )}
                  </Box>
                }
              />
              <ListItemSecondaryAction>
                {file.status === UploadStatus.UPLOADING && (
                  <IconButton
                    edge="end"
                    size="small"
                    onClick={() => handlePauseUpload(file.id)}
                  >
                    <PauseIcon />
                  </IconButton>
                )}
                {file.status === UploadStatus.PAUSED && (
                  <IconButton
                    edge="end"
                    size="small"
                    onClick={() => handleResumeUpload(file.id)}
                  >
                    <ResumeIcon />
                  </IconButton>
                )}
                {(file.status === UploadStatus.ERROR ||
                  file.status === UploadStatus.COMPLETED) && (
                  <IconButton
                    edge="end"
                    size="small"
                    onClick={() => handleRemoveUpload(file.id)}
                  >
                    <DeleteIcon />
                  </IconButton>
                )}
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>

        {/* Actions Menu */}
        <Menu
          anchorEl={menuAnchor}
          open={Boolean(menuAnchor)}
          onClose={() => setMenuAnchor(null)}
        >
          <MenuItem onClick={handleCancelAll}>
            <ClearIcon sx={{ mr: 1 }} fontSize="small" />
            Cancel All Uploads
          </MenuItem>
          {stats.failedFiles > 0 && (
            <MenuItem onClick={handleRetryFailed}>
              <ResumeIcon sx={{ mr: 1 }} fontSize="small" />
              Retry Failed Uploads
            </MenuItem>
          )}
          {stats.uploadedFiles > 0 && (
            <MenuItem onClick={onClearCompleted}>
              <DeleteIcon sx={{ mr: 1 }} fontSize="small" />
              Clear Completed
            </MenuItem>
          )}
        </Menu>
      </Collapse>
    </Paper>
  );
};

export default UploadManager;