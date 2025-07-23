import React from 'react';
import { Typography, Box } from '@mui/material';
import { useParams } from 'react-router-dom';

const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Project Detail
      </Typography>
      <Typography variant="body1" color="text.secondary">
        View and edit project details for project ID: {id}
      </Typography>
    </Box>
  );
};

export default ProjectDetail;