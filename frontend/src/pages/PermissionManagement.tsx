import React from 'react';
import { Box, Typography, Paper, Button } from '@mui/material';
import { VpnKey as VpnKeyIcon, Add as AddIcon } from '@mui/icons-material';

const PermissionManagement: React.FC = () => {
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <VpnKeyIcon sx={{ fontSize: 32, mr: 2, color: 'primary.main' }} />
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
          Permission Management
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />}>
          Add Permission
        </Button>
      </Box>

      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <VpnKeyIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          Permission Management Coming Soon
        </Typography>
        <Typography variant="body2" color="text.secondary">
          This feature will allow you to define and manage granular permissions for different system resources.
        </Typography>
      </Paper>
    </Box>
  );
};

export default PermissionManagement;