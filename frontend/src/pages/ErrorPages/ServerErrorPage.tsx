import React from 'react';
import { Box, Typography, Button, Container, Alert } from '@mui/material';
import { Home as HomeIcon, ArrowBack as ArrowBackIcon, ErrorOutline as ErrorIcon } from '@mui/icons-material';
import { useNavigation } from '../../hooks/useNavigation';

const ServerErrorPage: React.FC = () => {
  const { goBack, nav } = useNavigation();

  return (
    <Container maxWidth="md">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '60vh',
          textAlign: 'center',
        }}
      >
        <ErrorIcon
          sx={{
            fontSize: '4rem',
            color: 'error.main',
            mb: 2,
          }}
        />
        
        <Typography variant="h4" component="h1" gutterBottom>
          Server Error
        </Typography>
        
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3, maxWidth: '500px' }}>
          Something went wrong on our end. Our team has been notified and is working to fix the issue.
        </Typography>
        
        <Alert severity="error" sx={{ mb: 4, maxWidth: '500px' }}>
          <Typography variant="body2">
            <strong>Error Code:</strong> 500 - Internal Server Error
          </Typography>
        </Alert>
        
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
          <Button
            variant="contained"
            startIcon={<HomeIcon />}
            onClick={() => window.location.href = nav.dashboard()}
            size="large"
          >
            Go to Dashboard
          </Button>
          
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={goBack}
            size="large"
          >
            Go Back
          </Button>
        </Box>
      </Box>
    </Container>
  );
};

export default ServerErrorPage;