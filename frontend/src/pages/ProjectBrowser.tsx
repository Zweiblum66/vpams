import React from 'react';
import { Typography, Box } from '@mui/material';

const ProjectBrowser: React.FC = () => {
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Project Browser
      </Typography>
      <Typography variant="body1" color="text.secondary">
        Browse and manage your media projects here.
      </Typography>
    </Box>
  );
};

export default ProjectBrowser;