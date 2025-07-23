import React from 'react';
import { Box, Typography, Alert } from '@mui/material';

const DomainManager: React.FC = () => {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Custom Domain Management
      </Typography>
      <Alert severity="info">
        Custom domain management functionality will be available in a future update.
        This will allow you to configure custom domains for your white-labeled platform.
      </Alert>
    </Box>
  );
};

export default DomainManager;