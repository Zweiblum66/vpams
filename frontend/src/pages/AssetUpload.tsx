import React, { useState } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Stepper,
  Step,
  StepLabel,
  Button,
  TextField,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Alert,
  Divider,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  NavigateNext as NextIcon,
  NavigateBefore as BackIcon,
  Check as CheckIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

import FileUploadDropzone from '../components/upload/FileUploadDropzone';
import UploadManager from '../components/upload/UploadManager';
import { UploadFile, UploadMetadata } from '../types/upload';
import { logger } from '../utils/logger';

const steps = ['Upload Files', 'Add Metadata', 'Review & Submit'];

const AssetUpload: React.FC = () => {
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  const [uploadedFiles, setUploadedFiles] = useState<Map<string, UploadFile>>(new Map());
  const [metadata, setMetadata] = useState<UploadMetadata>({
    tags: [],
  });
  const [tagInput, setTagInput] = useState('');
  const [uploadManagerMinimized, setUploadManagerMinimized] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleNext = () => {
    if (activeStep === steps.length - 1) {
      // Final step - navigate to assets
      setShowSuccess(true);
      setTimeout(() => {
        navigate('/assets');
      }, 2000);
    } else {
      setActiveStep((prevStep) => prevStep + 1);
    }
  };

  const handleBack = () => {
    setActiveStep((prevStep) => prevStep - 1);
  };

  const handleUploadComplete = (assetId: string, file: UploadFile) => {
    logger.info('File upload completed', {
      assetId,
      fileName: file.name,
      actionType: 'upload_page_complete',
    });

    setUploadedFiles((prev) => {
      const updated = new Map(prev);
      updated.set(file.id, { ...file, assetId });
      return updated;
    });
  };

  const handleUploadError = (error: Error, file: UploadFile) => {
    logger.error('File upload error', {
      fileName: file.name,
      error,
      actionType: 'upload_page_error',
    });
  };

  const handleMetadataChange = (field: keyof UploadMetadata, value: any) => {
    setMetadata((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleAddTag = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && tagInput.trim()) {
      event.preventDefault();
      const newTag = tagInput.trim();
      if (!metadata.tags?.includes(newTag)) {
        handleMetadataChange('tags', [...(metadata.tags || []), newTag]);
      }
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    handleMetadataChange(
      'tags',
      metadata.tags?.filter((tag) => tag !== tagToRemove) || []
    );
  };

  const handleClearCompleted = () => {
    setUploadedFiles((prev) => {
      const updated = new Map(prev);
      Array.from(updated.entries()).forEach(([id, file]) => {
        if (file.status === 'completed') {
          updated.delete(id);
        }
      });
      return updated;
    });
  };

  const completedUploads = Array.from(uploadedFiles.values()).filter(
    (f) => f.status === 'completed'
  );

  const canProceed = () => {
    switch (activeStep) {
      case 0:
        return completedUploads.length > 0;
      case 1:
        return metadata.title && metadata.title.trim().length > 0;
      case 2:
        return true;
      default:
        return false;
    }
  };

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Upload Your Media Files
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Drag and drop files or click to browse. You can upload multiple files at once.
            </Typography>
            
            <FileUploadDropzone
              onUploadComplete={handleUploadComplete}
              onUploadError={handleUploadError}
              projectId={metadata.projectId}
              folderId={metadata.folderId}
              maxFiles={20}
            />

            {completedUploads.length > 0 && (
              <Alert severity="success" sx={{ mt: 2 }}>
                {completedUploads.length} file{completedUploads.length > 1 ? 's' : ''} uploaded successfully
              </Alert>
            )}
          </Box>
        );

      case 1:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Add Metadata
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Add information about your uploaded files. This metadata will be applied to all files.
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <TextField
                label="Title"
                fullWidth
                value={metadata.title || ''}
                onChange={(e) => handleMetadataChange('title', e.target.value)}
                required
                helperText="A descriptive title for your assets"
              />

              <TextField
                label="Description"
                fullWidth
                multiline
                rows={4}
                value={metadata.description || ''}
                onChange={(e) => handleMetadataChange('description', e.target.value)}
                helperText="Detailed description of the content"
              />

              <Box>
                <TextField
                  label="Add Tags"
                  fullWidth
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={handleAddTag}
                  helperText="Press Enter to add tags"
                  sx={{ mb: 1 }}
                />
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {metadata.tags?.map((tag) => (
                    <Chip
                      key={tag}
                      label={tag}
                      onDelete={() => handleRemoveTag(tag)}
                    />
                  ))}
                </Box>
              </Box>

              <FormControl fullWidth>
                <InputLabel>Project</InputLabel>
                <Select
                  value={metadata.projectId || ''}
                  onChange={(e: SelectChangeEvent) =>
                    handleMetadataChange('projectId', e.target.value)
                  }
                >
                  <MenuItem value="">None</MenuItem>
                  <MenuItem value="project1">Project Alpha</MenuItem>
                  <MenuItem value="project2">Project Beta</MenuItem>
                  <MenuItem value="project3">Project Gamma</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </Box>
        );

      case 2:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Review Your Upload
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Please review the information before submitting.
            </Typography>

            <Paper variant="outlined" sx={{ p: 3 }}>
              <Typography variant="subtitle1" gutterBottom>
                Files Uploaded
              </Typography>
              <Box sx={{ mb: 3 }}>
                {completedUploads.map((file) => (
                  <Typography key={file.id} variant="body2" color="text.secondary">
                    • {file.name}
                  </Typography>
                ))}
              </Box>

              <Divider sx={{ my: 2 }} />

              <Typography variant="subtitle1" gutterBottom>
                Metadata
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {metadata.title && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Title
                    </Typography>
                    <Typography variant="body2">{metadata.title}</Typography>
                  </Box>
                )}
                {metadata.description && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Description
                    </Typography>
                    <Typography variant="body2">{metadata.description}</Typography>
                  </Box>
                )}
                {metadata.tags && metadata.tags.length > 0 && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Tags
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                      {metadata.tags.map((tag) => (
                        <Chip key={tag} label={tag} size="small" />
                      ))}
                    </Box>
                  </Box>
                )}
              </Box>
            </Paper>

            {showSuccess && (
              <Alert severity="success" sx={{ mt: 2 }}>
                Assets uploaded successfully! Redirecting to asset browser...
              </Alert>
            )}
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 4 }}>
          <UploadIcon sx={{ fontSize: 32, color: 'primary.main' }} />
          <Typography variant="h4">Upload Assets</Typography>
        </Box>

        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        <Box sx={{ minHeight: 400 }}>
          {renderStepContent()}
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
          <Button
            disabled={activeStep === 0}
            onClick={handleBack}
            startIcon={<BackIcon />}
          >
            Back
          </Button>
          <Button
            variant="contained"
            onClick={handleNext}
            disabled={!canProceed()}
            endIcon={
              activeStep === steps.length - 1 ? <CheckIcon /> : <NextIcon />
            }
          >
            {activeStep === steps.length - 1 ? 'Complete' : 'Next'}
          </Button>
        </Box>
      </Paper>

      {/* Upload Manager */}
      {uploadedFiles.size > 0 && (
        <UploadManager
          uploads={uploadedFiles}
          onUploadComplete={handleUploadComplete}
          onUploadError={handleUploadError}
          onClearCompleted={handleClearCompleted}
          minimized={uploadManagerMinimized}
          onToggleMinimize={() => setUploadManagerMinimized(!uploadManagerMinimized)}
        />
      )}
    </Container>
  );
};

export default AssetUpload;