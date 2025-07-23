import React from 'react';
import { Box, Typography, Alert } from '@mui/material';

const WhiteLabelAnalytics: React.FC = () => {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        White-Label Analytics
      </Typography>
      <Alert severity="info">
        Analytics dashboard for white-label usage will be available in a future update.
        This will show theme usage, branding configuration metrics, and more.
      </Alert>
    </Box>
  );
};

export default WhiteLabelAnalytics;