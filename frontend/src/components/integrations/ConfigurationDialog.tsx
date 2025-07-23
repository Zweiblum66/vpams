/**
 * Configuration Dialog for API Integration Installation
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Divider,
  CircularProgress
} from '@mui/material';
import { LoadingButton } from '@mui/lab';
import { GetApp, Security, Settings } from '@mui/icons-material';

import { APIListing } from '../../types/integration';


interface ConfigurationDialogProps {
  open: boolean;
  onClose: () => void;
  listing: APIListing;
  onConfirm: (config: any) => void;
  isInstalling: boolean;
}

export const ConfigurationDialog: React.FC<ConfigurationDialogProps> = ({
  open,
  onClose,
  listing,
  onConfirm,
  isInstalling
}) => {
  const [config, setConfig] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    // Reset config when dialog opens
    if (open) {
      setConfig({});
      setErrors({});
    }
  }, [open]);

  const handleConfigChange = (field: string, value: any) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const validateConfig = () => {
    const newErrors: Record<string, string> = {};
    
    if (listing.config_schema?.required) {
      listing.config_schema.required.forEach((field: string) => {
        if (!config[field]) {
          newErrors[field] = 'This field is required';
        }
      });
    }

    // Custom validation based on field types
    Object.entries(config).forEach(([field, value]) => {
      const fieldSchema = listing.config_schema?.properties?.[field];
      
      if (fieldSchema?.type === 'string' && fieldSchema.minLength && value.length < fieldSchema.minLength) {
        newErrors[field] = `Minimum length is ${fieldSchema.minLength}`;
      }
      
      if (fieldSchema?.pattern && !new RegExp(fieldSchema.pattern).test(value)) {
        newErrors[field] = 'Invalid format';
      }
      
      if (fieldSchema?.type === 'number' && isNaN(Number(value))) {
        newErrors[field] = 'Must be a number';
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleConfirm = () => {
    if (validateConfig()) {
      onConfirm(config);
    }
  };

  const renderField = (fieldName: string, fieldSchema: any) => {
    const value = config[fieldName] || '';
    const error = errors[fieldName];
    const isRequired = listing.config_schema?.required?.includes(fieldName);

    switch (fieldSchema.type) {
      case 'string':
        if (fieldSchema.enum) {
          return (
            <FormControl fullWidth key={fieldName} margin="normal">
              <InputLabel required={isRequired}>
                {fieldSchema.title || fieldName}
              </InputLabel>
              <Select
                value={value}
                onChange={(e) => handleConfigChange(fieldName, e.target.value)}
                label={fieldSchema.title || fieldName}
                error={!!error}
              >
                {fieldSchema.enum.map((option: string) => (
                  <MenuItem key={option} value={option}>
                    {option}
                  </MenuItem>
                ))}
              </Select>
              {error && (
                <Typography variant="caption" color="error">
                  {error}
                </Typography>
              )}
            </FormControl>
          );
        }
        
        return (
          <TextField
            key={fieldName}
            fullWidth
            margin="normal"
            label={fieldSchema.title || fieldName}
            value={value}
            onChange={(e) => handleConfigChange(fieldName, e.target.value)}
            required={isRequired}
            error={!!error}
            helperText={error || fieldSchema.description}
            type={fieldSchema.format === 'password' ? 'password' : 'text'}
            multiline={fieldSchema.format === 'textarea'}
            rows={fieldSchema.format === 'textarea' ? 3 : 1}
          />
        );

      case 'number':
        return (
          <TextField
            key={fieldName}
            fullWidth
            margin="normal"
            label={fieldSchema.title || fieldName}
            value={value}
            onChange={(e) => handleConfigChange(fieldName, Number(e.target.value))}
            required={isRequired}
            error={!!error}
            helperText={error || fieldSchema.description}
            type="number"
          />
        );

      case 'boolean':
        return (
          <FormControlLabel
            key={fieldName}
            control={
              <Switch
                checked={!!value}
                onChange={(e) => handleConfigChange(fieldName, e.target.checked)}
              />
            }
            label={fieldSchema.title || fieldName}
          />
        );

      default:
        return (
          <TextField
            key={fieldName}
            fullWidth
            margin="normal"
            label={fieldSchema.title || fieldName}
            value={value}
            onChange={(e) => handleConfigChange(fieldName, e.target.value)}
            required={isRequired}
            error={!!error}
            helperText={error || fieldSchema.description}
          />
        );
    }
  };

  const hasConfigSchema = listing.config_schema?.properties;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={2}>
          <Settings color="primary" />
          <Box>
            <Typography variant="h6">Configure Integration</Typography>
            <Typography variant="body2" color="text.secondary">
              {listing.name}
            </Typography>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Alert severity="info" sx={{ mb: 3 }}>
          Configure the integration settings below. All required fields must be filled out.
        </Alert>

        {listing.authentication_type && (
          <Box mb={3}>
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              <Security fontSize="small" />
              <Typography variant="subtitle2">Authentication</Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              This integration uses {listing.authentication_type} authentication.
            </Typography>
          </Box>
        )}

        <Divider sx={{ my: 2 }} />

        {hasConfigSchema ? (
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Configuration Fields
            </Typography>
            {Object.entries(listing.config_schema.properties).map(([fieldName, fieldSchema]: [string, any]) =>
              renderField(fieldName, fieldSchema)
            )}
          </Box>
        ) : (
          <Alert severity="warning">
            No configuration schema available for this integration.
          </Alert>
        )}

        {listing.pricing_model !== 'free' && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            This is a {listing.pricing_model} integration. Additional charges may apply.
          </Alert>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={isInstalling}>
          Cancel
        </Button>
        <LoadingButton
          onClick={handleConfirm}
          variant="contained"
          startIcon={<GetApp />}
          loading={isInstalling}
          disabled={!hasConfigSchema}
        >
          Install Integration
        </LoadingButton>
      </DialogActions>
    </Dialog>
  );
};