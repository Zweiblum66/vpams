import React, { useState } from 'react';
import { Box, Container, Paper, Typography, Button, Breadcrumbs, Link } from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowBack } from '@mui/icons-material';
import { ShotlistBuilder } from '../components/shotlist';
import { useGetProjectByIdQuery, useGetProjectContainersQuery } from '../store/api/projectApi';
import { ShotlistItem } from '../types';

const ShotlistPage: React.FC = () => {
  const { projectId, shotlistId } = useParams<{ projectId: string; shotlistId: string }>();
  const navigate = useNavigate();
  const [selectedItems, setSelectedItems] = useState<string[]>([]);

  const { data: project } = useGetProjectByIdQuery(projectId!, { skip: !projectId });
  const { data: containers } = useGetProjectContainersQuery(projectId!, { skip: !projectId });

  const shotlist = containers?.find(c => c.id === shotlistId && c.type === 'shotlist');

  const handleItemSelect = (item: ShotlistItem) => {
    setSelectedItems(prev => 
      prev.includes(item.id) 
        ? prev.filter(id => id !== item.id)
        : [...prev, item.id]
    );
  };

  const handleBackToProject = () => {
    navigate(`/projects/${projectId}`);
  };

  if (!projectId || !shotlistId) {
    return (
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h6" color="error">
          Invalid project or shotlist ID
        </Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 3, height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Button
                startIcon={<ArrowBack />}
                onClick={handleBackToProject}
                variant="outlined"
                size="small"
              >
                Back to Project
              </Button>
            </Box>
            <Breadcrumbs>
              <Link
                color="inherit"
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  navigate('/projects');
                }}
              >
                Projects
              </Link>
              <Link
                color="inherit"
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  navigate(`/projects/${projectId}`);
                }}
              >
                {project?.name || 'Project'}
              </Link>
              <Typography color="text.primary">
                {shotlist?.name || 'Shotlist'}
              </Typography>
            </Breadcrumbs>
            <Typography variant="h4" sx={{ mt: 1 }}>
              {shotlist?.name || 'Shotlist'}
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', gap: 1 }}>
            {selectedItems.length > 0 && (
              <Typography variant="body2" color="text.secondary">
                {selectedItems.length} selected
              </Typography>
            )}
          </Box>
        </Box>
      </Paper>

      {/* Shotlist Builder */}
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        <ShotlistBuilder
          shotlistId={shotlistId}
          projectId={projectId}
          onItemSelect={handleItemSelect}
          selectedItems={selectedItems}
        />
      </Box>
    </Container>
  );
};

export default ShotlistPage;