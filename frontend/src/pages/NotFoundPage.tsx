import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Container,
  Paper,
} from '@mui/material';
import { Home as HomeIcon, ArrowBack as ArrowBackIcon } from '@mui/icons-material';

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  const handleGoHome = () => {
    navigate('/dashboard');
  };

  const handleGoBack = () => {
    navigate(-1);
  };

  return (
    <Container maxWidth="md" sx={{ mt: 8 }}>
      <Paper elevation={3} sx={{ p: 6, textAlign: 'center' }}>
        <Typography variant="h1" component="h1" sx={{ fontSize: '8rem', fontWeight: 'bold', color: 'primary.main' }}>
          404
        </Typography>
        
        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 2, mb: 2 }}>
          Page Not Found
        </Typography>
        
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            startIcon={<HomeIcon />}
            onClick={handleGoHome}
            size="large"
          >
            Go to Dashboard
          </Button>
          
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={handleGoBack}
            size="large"
          >
            Go Back
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default NotFoundPage;