import React, { useCallback, useState } from 'react';
import { useDropzone, FileRejection } from 'react-dropzone';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  Chip,
  LinearProgress,
  Alert,
  Button,
  Collapse,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  InsertDriveFile as FileIcon,
  VideoLibrary as VideoIcon,
  AudioFile as AudioIcon,
  Image as ImageIcon,
  Description as DocumentIcon,
  Delete as DeleteIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';

import { uploadService } from '../../services/uploadService';
import { UploadFile, UploadStatus } from '../../types/upload';
import { formatFileSize } from '../../utils/formatters';
import { logger } from '../../utils/logger';

interface FileUploadDropzoneProps {
  onUploadComplete?: (assetId: string, file: UploadFile) => void;
  onUploadError?: (error: Error, file: UploadFile) => void;
  maxFiles?: number;
  projectId?: string;
  folderId?: string;
  autoUpload?: boolean;
}

const FileUploadDropzone: React.FC<FileUploadDropzoneProps> = ({
  onUploadComplete,
  onUploadError,
  maxFiles = 10,
  projectId,
  folderId,
  autoUpload = true,
}) => {
  const [uploadFiles, setUploadFiles] = useState<Map<string, UploadFile>>(new Map());
  const [showCompleted, setShowCompleted] = useState(true);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
      logger.info('Files dropped', {
        accepted: acceptedFiles.length,
        rejected: rejectedFiles.length,
        actionType: 'upload_drop',
      });

      // Handle rejected files
      rejectedFiles.forEach((rejection) => {
        const errorMessage = rejection.errors.map((e) => e.message).join(', ');
        logger.warn('File rejected', {
          fileName: rejection.file.name,
          errors: errorMessage,
          actionType: 'upload_file_rejected',
        });
      });

      // Process accepted files
      const newFiles = new Map(uploadFiles);
      
      acceptedFiles.forEach((file) => {
        const uploadFile: UploadFile = {
          id: `${Date.now()}-${Math.random()}`,
          file,
          name: file.name,
          size: file.size,
          type: file.type,
          status: UploadStatus.PENDING,
          progress: 0,
          metadata: {
            projectId,
            folderId,
          },
        };

        newFiles.set(uploadFile.id, uploadFile);

        if (autoUpload) {
          startUpload(uploadFile);
        }
      });

      setUploadFiles(newFiles);
    },
    [uploadFiles, projectId, folderId, autoUpload]
  );

  const startUpload = async (uploadFile: UploadFile) => {
    try {
      setUploadFiles((prev) => {
        const updated = new Map(prev);
        updated.set(uploadFile.id, {
          ...uploadFile,
          status: UploadStatus.UPLOADING,
          startedAt: new Date().toISOString(),
        });
        return updated;
      });

      const assetId = await uploadService.uploadFile(
        uploadFile.file,
        uploadFile.metadata,
        (progress) => {
          setUploadFiles((prev) => {
            const updated = new Map(prev);
            const file = updated.get(uploadFile.id);
            if (file) {
              updated.set(uploadFile.id, {
                ...file,
                progress,
                status: progress === 100 ? UploadStatus.PROCESSING : UploadStatus.UPLOADING,
              });
            }
            return updated;
          });
        }
      );

      setUploadFiles((prev) => {
        const updated = new Map(prev);
        const file = updated.get(uploadFile.id);
        if (file) {
          const completedFile = {
            ...file,
            status: UploadStatus.COMPLETED,
            progress: 100,
            assetId,
            completedAt: new Date().toISOString(),
          };
          updated.set(uploadFile.id, completedFile);
          onUploadComplete?.(assetId, completedFile);
        }
        return updated;
      });

      logger.info('File upload completed', {
        fileId: uploadFile.id,
        fileName: uploadFile.name,
        assetId,
        actionType: 'upload_complete',
      });
    } catch (error: any) {
      logger.error('File upload failed', {
        fileId: uploadFile.id,
        fileName: uploadFile.name,
        error,
        actionType: 'upload_error',
      });

      setUploadFiles((prev) => {
        const updated = new Map(prev);
        const file = updated.get(uploadFile.id);
        if (file) {
          const errorFile = {
            ...file,
            status: UploadStatus.ERROR,
            error: error.message,
          };
          updated.set(uploadFile.id, errorFile);
          onUploadError?.(error, errorFile);
        }
        return updated;
      });
    }
  };

  const handleRetry = (uploadFile: UploadFile) => {
    setUploadFiles((prev) => {
      const updated = new Map(prev);
      updated.set(uploadFile.id, {
        ...uploadFile,
        status: UploadStatus.PENDING,
        progress: 0,
        error: undefined,
      });
      return updated;
    });
    startUpload(uploadFile);
  };

  const handleRemove = (fileId: string) => {
    uploadService.cancelUpload(fileId);
    setUploadFiles((prev) => {
      const updated = new Map(prev);
      updated.delete(fileId);
      return updated;
    });
  };

  const handleClearCompleted = () => {
    setUploadFiles((prev) => {
      const updated = new Map(prev);
      Array.from(updated.entries()).forEach(([id, file]) => {
        if (file.status === UploadStatus.COMPLETED) {
          updated.delete(id);
        }
      });
      return updated;
    });
  };

  const getFileIcon = (type: string) => {
    if (type.startsWith('video/')) return <VideoIcon />;
    if (type.startsWith('audio/')) return <AudioIcon />;
    if (type.startsWith('image/')) return <ImageIcon />;
    return <DocumentIcon />;
  };

  const getStatusIcon = (status: UploadStatus) => {
    switch (status) {
      case UploadStatus.COMPLETED:
        return <CompleteIcon color="success" />;
      case UploadStatus.ERROR:
        return <ErrorIcon color="error" />;
      case UploadStatus.UPLOADING:
      case UploadStatus.PROCESSING:
        return null;
      default:
        return <WarningIcon color="warning" />;
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
      'audio/*': ['.mp3', '.wav', '.flac', '.aac', '.ogg'],
      'image/*': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'],
      'application/pdf': ['.pdf'],
    },
  });

  const files = Array.from(uploadFiles.values());
  const activeUploads = files.filter(
    (f) => f.status === UploadStatus.UPLOADING || f.status === UploadStatus.PROCESSING
  );
  const completedUploads = files.filter((f) => f.status === UploadStatus.COMPLETED);
  const hasErrors = files.some((f) => f.status === UploadStatus.ERROR);

  return (
    <Box>
      <Paper
        {...getRootProps()}
        sx={{
          p: 4,
          mb: 2,
          textAlign: 'center',
          cursor: 'pointer',
          backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'divider',
          transition: 'all 0.2s',
          '&:hover': {
            borderColor: 'primary.main',
            backgroundColor: 'action.hover',
          },
        }}
      >
        <input {...getInputProps()} />
        <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          or click to browse files
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          Supported: Video, Audio, Images, PDFs (max {maxFiles} files)
        </Typography>
      </Paper>

      {hasErrors && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Some files failed to upload. Please check the errors below and try again.
        </Alert>
      )}

      {activeUploads.length > 0 && (
        <Paper sx={{ mb: 2 }}>
          <Box sx={{ p: 2, pb: 1 }}>
            <Typography variant="subtitle2">
              Uploading ({activeUploads.length} file{activeUploads.length > 1 ? 's' : ''})
            </Typography>
          </Box>
          <List>
            {activeUploads.map((file) => (
              <ListItem key={file.id}>
                <ListItemIcon>{getFileIcon(file.type)}</ListItemIcon>
                <ListItemText
                  primary={file.name}
                  secondary={
                    <Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          {formatFileSize(file.size)}
                        </Typography>
                        {file.status === UploadStatus.PROCESSING && (
                          <Chip label="Processing" size="small" color="info" />
                        )}
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={file.progress}
                        sx={{ mt: 1 }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        {Math.round(file.progress)}%
                      </Typography>
                    </Box>
                  }
                />
                <IconButton
                  edge="end"
                  onClick={() => handleRemove(file.id)}
                  size="small"
                >
                  <PauseIcon />
                </IconButton>
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      {files.filter((f) => f.status === UploadStatus.ERROR).map((file) => (
        <Paper key={file.id} sx={{ mb: 1 }}>
          <ListItem>
            <ListItemIcon>
              <ErrorIcon color="error" />
            </ListItemIcon>
            <ListItemText
              primary={file.name}
              secondary={
                <Box>
                  <Typography variant="caption" color="error">
                    {file.error || 'Upload failed'}
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    <Button
                      size="small"
                      onClick={() => handleRetry(file)}
                      sx={{ mr: 1 }}
                    >
                      Retry
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      onClick={() => handleRemove(file.id)}
                    >
                      Remove
                    </Button>
                  </Box>
                </Box>
              }
            />
          </ListItem>
        </Paper>
      ))}

      {completedUploads.length > 0 && (
        <Paper sx={{ mb: 2 }}>
          <Box
            sx={{
              p: 2,
              pb: 1,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <Typography variant="subtitle2">
              Completed ({completedUploads.length})
            </Typography>
            <Box>
              <Button
                size="small"
                onClick={() => setShowCompleted(!showCompleted)}
                sx={{ mr: 1 }}
              >
                {showCompleted ? 'Hide' : 'Show'}
              </Button>
              <Button size="small" onClick={handleClearCompleted}>
                Clear All
              </Button>
            </Box>
          </Box>
          <Collapse in={showCompleted}>
            <List>
              {completedUploads.map((file) => (
                <ListItem key={file.id}>
                  <ListItemIcon>
                    <CompleteIcon color="success" />
                  </ListItemIcon>
                  <ListItemText
                    primary={file.name}
                    secondary={`${formatFileSize(file.size)} • Uploaded successfully`}
                  />
                  <IconButton
                    edge="end"
                    onClick={() => handleRemove(file.id)}
                    size="small"
                  >
                    <DeleteIcon />
                  </IconButton>
                </ListItem>
              ))}
            </List>
          </Collapse>
        </Paper>
      )}
    </Box>
  );
};

export default FileUploadDropzone;