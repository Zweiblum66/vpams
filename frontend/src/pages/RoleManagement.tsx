import React from 'react';
import { Box, Typography, Paper, Button } from '@mui/material';
import { Security as SecurityIcon, Add as AddIcon } from '@mui/icons-material';

const RoleManagement: React.FC = () => {
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <SecurityIcon sx={{ fontSize: 32, mr: 2, color: 'primary.main' }} />
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
          Role Management
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />}>
          Add Role
        </Button>
      </Box>

      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <SecurityIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          Role Management Coming Soon
        </Typography>
        <Typography variant="body2" color="text.secondary">
          This feature will allow you to create and manage user roles with different permission levels.
        </Typography>
      </Paper>
    </Box>
  );
};

export default RoleManagement;