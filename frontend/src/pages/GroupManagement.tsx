import React from 'react';
import { Box, Typography, Paper, Button } from '@mui/material';
import { Group as GroupIcon, Add as AddIcon } from '@mui/icons-material';

const GroupManagement: React.FC = () => {
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <GroupIcon sx={{ fontSize: 32, mr: 2, color: 'primary.main' }} />
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
          Group Management
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />}>
          Add Group
        </Button>
      </Box>

      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <GroupIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          Group Management Coming Soon
        </Typography>
        <Typography variant="body2" color="text.secondary">
          This feature will allow you to organize users into groups for easier permission management.
        </Typography>
      </Paper>
    </Box>
  );
};

export default GroupManagement;