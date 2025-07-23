import React from 'react';
import { Box, Typography, Alert } from '@mui/material';

const EmailTemplateManager: React.FC = () => {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Email Template Management
      </Typography>
      <Alert severity="info">
        Email template customization functionality will be available in a future update.
        This will allow you to customize email templates with your branding.
      </Alert>
    </Box>
  );
};

export default EmailTemplateManager;