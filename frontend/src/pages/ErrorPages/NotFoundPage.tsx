import React from 'react';
import { Box, Typography, Button, Container } from '@mui/material';
import { Home as HomeIcon, ArrowBack as ArrowBackIcon } from '@mui/icons-material';
import { useNavigation } from '../../hooks/useNavigation';

const NotFoundPage: React.FC = () => {
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
        <Typography
          variant="h1"
          sx={{
            fontSize: '6rem',
            fontWeight: 'bold',
            color: 'primary.main',
            mb: 2,
          }}
        >
          404
        </Typography>
        
        <Typography variant="h4" component="h1" gutterBottom>
          Page Not Found
        </Typography>
        
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4, maxWidth: '500px' }}>
          The page you're looking for doesn't exist. It might have been moved, deleted, or you entered the wrong URL.
        </Typography>
        
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

export default NotFoundPage;