import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Alert,
  Container,
  CircularProgress,
  Link,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import { LockOutlined as LockIcon } from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '../store';
import { login } from '../store/slices/authSlice';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const { isLoading, error } = useAppSelector(state => state.auth);

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    remember_me: false,
  });

  const from = location.state?.from?.pathname || '/dashboard';

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: e.target.type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await dispatch(login(formData)).unwrap();
      navigate(from, { replace: true });
    } catch (error) {
      // Error is handled by the slice
    }
  };

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                backgroundColor: 'primary.main',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mb: 2,
              }}
            >
              <LockIcon sx={{ color: 'white' }} />
            </Box>
            
            <Typography component="h1" variant="h5" gutterBottom>
              Sign in to MAMS
            </Typography>
            
            <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 3 }}>
              Digital Media Asset Management System
            </Typography>

            {error && (
              <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
                {error}
              </Alert>
            )}

            <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%' }}>
              <TextField
                margin="normal"
                required
                fullWidth
                id="email"
                label="Email Address"
                name="email"
                autoComplete="email"
                autoFocus
                value={formData.email}
                onChange={handleChange}
                disabled={isLoading}
              />
              
              <TextField
                margin="normal"
                required
                fullWidth
                name="password"
                label="Password"
                type="password"
                id="password"
                autoComplete="current-password"
                value={formData.password}
                onChange={handleChange}
                disabled={isLoading}
              />
              
              <FormControlLabel
                control={
                  <Checkbox
                    name="remember_me"
                    checked={formData.remember_me}
                    onChange={handleChange}
                    color="primary"
                    disabled={isLoading}
                  />
                }
                label="Remember me"
                sx={{ mt: 1 }}
              />
              
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={isLoading}
              >
                {isLoading ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  'Sign In'
                )}
              </Button>
              
              <Box sx={{ textAlign: 'center', mt: 2 }}>
                <Link href="#" variant="body2">
                  Forgot password?
                </Link>
              </Box>
            </Box>
          </Box>
        </Paper>
        
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            © 2024 MAMS. All rights reserved.
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default LoginPage;