import React from 'react';
import { Box, Typography, Alert } from '@mui/material';

const MobileAppManager: React.FC = () => {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Mobile App Configuration
      </Typography>
      <Alert severity="info">
        Mobile app white-labeling functionality will be available in a future update.
        This will allow you to configure custom mobile apps with your branding.
      </Alert>
    </Box>
  );
};

export default MobileAppManager;