/**
 * Test Dialog for Testing API Integrations
 */

import React, { useState } from 'react';
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
  CircularProgress,
  Chip,
  Divider
} from '@mui/material';
import { LoadingButton } from '@mui/lab';
import { 
  TestTube, 
  CheckCircle, 
  Error, 
  Warning,
  PlayArrow,
  Code
} from '@mui/icons-material';
import { useMutation } from '@tanstack/react-query';

import { integrationApi } from '../../api/integrations';
import { APIListing } from '../../types/integration';


interface TestDialogProps {
  open: boolean;
  onClose: () => void;
  listing: APIListing;
}

interface TestResult {
  status: 'success' | 'error' | 'warning';
  message: string;
  details?: any;
}

export const TestDialog: React.FC<TestDialogProps> = ({
  open,
  onClose,
  listing
}) => {
  const [testConfig, setTestConfig] = useState<Record<string, any>>({});
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  // Test integration mutation
  const testMutation = useMutation({
    mutationFn: (config: any) => integrationApi.testMarketplaceIntegration(listing.id, config),
    onSuccess: (data) => {
      setTestResult({
        status: data.status === 'success' ? 'success' : 'error',
        message: data.message,
        details: data.details
      });
    },
    onError: (error: any) => {
      setTestResult({
        status: 'error',
        message: error.response?.data?.message || 'Test failed',
        details: error.response?.data?.details
      });
    }
  });

  const handleConfigChange = (field: string, value: any) => {
    setTestConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleTest = () => {
    setTestResult(null);
    testMutation.mutate(testConfig);
  };

  const handleClose = () => {
    setTestConfig({});
    setTestResult(null);
    onClose();
  };

  const renderTestField = (fieldName: string, fieldSchema: any) => {
    const value = testConfig[fieldName] || '';

    if (fieldSchema.type === 'boolean') {
      return (
        <Box key={fieldName} mb={2}>
          <Typography variant="body2" gutterBottom>
            {fieldSchema.title || fieldName}
          </Typography>
          <Box display="flex" gap={1}>
            <Chip
              label="True"
              variant={value === true ? 'filled' : 'outlined'}
              onClick={() => handleConfigChange(fieldName, true)}
              size="small"
            />
            <Chip
              label="False"
              variant={value === false ? 'filled' : 'outlined'}
              onClick={() => handleConfigChange(fieldName, false)}
              size="small"
            />
          </Box>
        </Box>
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
        helperText={fieldSchema.description}
        type={fieldSchema.format === 'password' ? 'password' : 'text'}
        placeholder={fieldSchema.example || `Enter ${fieldName}`}
      />
    );
  };

  const getTestResultIcon = () => {
    if (!testResult) return null;
    
    switch (testResult.status) {
      case 'success':
        return <CheckCircle color="success" />;
      case 'error':
        return <Error color="error" />;
      case 'warning':
        return <Warning color="warning" />;
      default:
        return null;
    }
  };

  const getTestResultColor = () => {
    if (!testResult) return 'info';
    
    switch (testResult.status) {
      case 'success':
        return 'success';
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'info';
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={2}>
          <TestTube color="primary" />
          <Box>
            <Typography variant="h6">Test Integration</Typography>
            <Typography variant="body2" color="text.secondary">
              {listing.name}
            </Typography>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Alert severity="info" sx={{ mb: 3 }}>
          Test the integration configuration before installing to ensure it works correctly.
        </Alert>

        {/* Integration Info */}
        <Box mb={3}>
          <Typography variant="subtitle2" gutterBottom>
            Integration Details
          </Typography>
          <Box display="flex" gap={2} flexWrap="wrap">
            <Chip
              icon={<Code />}
              label={`${listing.api_type.toUpperCase()} API`}
              size="small"
              variant="outlined"
            />
            <Chip
              label={listing.authentication_type}
              size="small"
              variant="outlined"
            />
            <Chip
              label={`v${listing.version}`}
              size="small"
              variant="outlined"
            />
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Test Configuration */}
        <Typography variant="subtitle2" gutterBottom>
          Test Configuration
        </Typography>

        {listing.config_schema?.properties ? (
          <Box>
            {Object.entries(listing.config_schema.properties).map(([fieldName, fieldSchema]: [string, any]) =>
              renderTestField(fieldName, fieldSchema)
            )}
          </Box>
        ) : (
          <Alert severity="warning" sx={{ mb: 2 }}>
            No configuration schema available. Basic connectivity test will be performed.
          </Alert>
        )}

        {/* Test Results */}
        {(testMutation.isPending || testResult) && (
          <Box mt={3}>
            <Divider sx={{ mb: 2 }} />
            <Typography variant="subtitle2" gutterBottom>
              Test Results
            </Typography>
            
            {testMutation.isPending && (
              <Box display="flex" alignItems="center" gap={2} p={2}>
                <CircularProgress size={20} />
                <Typography variant="body2">
                  Testing integration configuration...
                </Typography>
              </Box>
            )}

            {testResult && (
              <Alert
                severity={getTestResultColor() as any}
                icon={getTestResultIcon()}
                sx={{ mb: 2 }}
              >
                <Typography variant="body2" fontWeight="medium">
                  {testResult.message}
                </Typography>
                {testResult.details && (
                  <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                    {JSON.stringify(testResult.details, null, 2)}
                  </Typography>
                )}
              </Alert>
            )}
          </Box>
        )}

        {/* Additional Test Info */}
        {listing.base_url && (
          <Box mt={2} p={2} bgcolor="grey.50" borderRadius={1}>
            <Typography variant="caption" color="text.secondary">
              Test Endpoint: {listing.base_url}
            </Typography>
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>
          Close
        </Button>
        <LoadingButton
          onClick={handleTest}
          variant="contained"
          startIcon={<PlayArrow />}
          loading={testMutation.isPending}
        >
          Run Test
        </LoadingButton>
      </DialogActions>
    </Dialog>
  );
};