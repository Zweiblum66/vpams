import React, { useState } from 'react';
import { useNavigate, useLocation, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Container,
  Divider,
  FormControlLabel,
  Link,
  TextField,
  Typography,
  Alert,
  CircularProgress,
  InputAdornment,
  IconButton,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Login as LoginIcon,
  Google as GoogleIcon,
  Microsoft as MicrosoftIcon,
} from '@mui/icons-material';
import { useFormik } from 'formik';
import * as Yup from 'yup';

import { useAuth } from '../../hooks/useAuth';
import { useErrorHandler } from '../../hooks/useErrorHandler';
import { logger } from '../../utils/logger';
import { ROUTES } from '../../router/routes';

const validationSchema = Yup.object({
  email: Yup.string()
    .email('Invalid email address')
    .required('Email is required'),
  password: Yup.string()
    .min(8, 'Password must be at least 8 characters')
    .required('Password is required'),
  rememberMe: Yup.boolean(),
});

interface LoginFormValues {
  email: string;
  password: string;
  rememberMe: boolean;
}

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loginWithProvider, isLoading } = useAuth();
  const { handleError } = useErrorHandler();

  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Get the intended destination or default to dashboard
  const from = (location.state as any)?.from?.pathname || ROUTES.DASHBOARD;

  const formik = useFormik<LoginFormValues>({
    initialValues: {
      email: '',
      password: '',
      rememberMe: false,
    },
    validationSchema,
    onSubmit: async (values) => {
      try {
        setLoginError(null);
        logger.info('Login attempt started', {
          email: values.email,
          rememberMe: values.rememberMe,
          actionType: 'login_attempt',
        });

        await login({
          email: values.email,
          password: values.password,
          rememberMe: values.rememberMe,
        });

        logger.info('Login successful', {
          email: values.email,
          destination: from,
          actionType: 'login_success',
        });

        navigate(from, { replace: true });
      } catch (error: any) {
        const errorMessage = error?.message || 'Login failed. Please try again.';
        setLoginError(errorMessage);
        
        logger.error('Login failed', {
          email: values.email,
          error: errorMessage,
          actionType: 'login_error',
        }, error);

        handleError(error, {
          context: 'LoginPage.onSubmit',
          userMessage: 'Failed to log in. Please check your credentials and try again.',
        });
      }
    },
  });

  const handleProviderLogin = async (provider: 'google' | 'microsoft') => {
    try {
      setLoginError(null);
      logger.info('OAuth login attempt started', {
        provider,
        actionType: 'oauth_login_attempt',
      });

      await loginWithProvider(provider);

      logger.info('OAuth login successful', {
        provider,
        destination: from,
        actionType: 'oauth_login_success',
      });

      navigate(from, { replace: true });
    } catch (error: any) {
      const errorMessage = error?.message || `${provider} login failed. Please try again.`;
      setLoginError(errorMessage);
      
      logger.error('OAuth login failed', {
        provider,
        error: errorMessage,
        actionType: 'oauth_login_error',
      }, error);

      handleError(error, {
        context: `LoginPage.handleProviderLogin.${provider}`,
        userMessage: `Failed to log in with ${provider}. Please try again.`,
      });
    }
  };

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  return (
    <Container component="main" maxWidth="sm">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Card sx={{ width: '100%', maxWidth: 400 }}>
          <CardContent sx={{ p: 4 }}>
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                mb: 3,
              }}
            >
              <LoginIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography component="h1" variant="h4" align="center">
                Sign In
              </Typography>
              <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
                Access your MAMS account
              </Typography>
            </Box>

            {loginError && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {loginError}
              </Alert>
            )}

            <Box component="form" onSubmit={formik.handleSubmit} noValidate>
              <TextField
                margin="normal"
                required
                fullWidth
                id="email"
                label="Email Address"
                name="email"
                autoComplete="email"
                autoFocus
                value={formik.values.email}
                onChange={formik.handleChange}
                onBlur={formik.handleBlur}
                error={formik.touched.email && Boolean(formik.errors.email)}
                helperText={formik.touched.email && formik.errors.email}
                disabled={isLoading}
              />
              
              <TextField
                margin="normal"
                required
                fullWidth
                name="password"
                label="Password"
                type={showPassword ? 'text' : 'password'}
                id="password"
                autoComplete="current-password"
                value={formik.values.password}
                onChange={formik.handleChange}
                onBlur={formik.handleBlur}
                error={formik.touched.password && Boolean(formik.errors.password)}
                helperText={formik.touched.password && formik.errors.password}
                disabled={isLoading}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle password visibility"
                        onClick={togglePasswordVisibility}
                        edge="end"
                        disabled={isLoading}
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <FormControlLabel
                control={
                  <Checkbox
                    name="rememberMe"
                    checked={formik.values.rememberMe}
                    onChange={formik.handleChange}
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
                startIcon={isLoading ? <CircularProgress size={20} /> : <LoginIcon />}
              >
                {isLoading ? 'Signing In...' : 'Sign In'}
              </Button>

              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Link
                  component={RouterLink}
                  to={ROUTES.FORGOT_PASSWORD}
                  variant="body2"
                  color="primary"
                >
                  Forgot password?
                </Link>
                <Link
                  component={RouterLink}
                  to={ROUTES.REGISTER}
                  variant="body2"
                  color="primary"
                >
                  Don't have an account? Sign Up
                </Link>
              </Box>

              <Divider sx={{ my: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  Or continue with
                </Typography>
              </Divider>

              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<GoogleIcon />}
                  onClick={() => handleProviderLogin('google')}
                  disabled={isLoading}
                >
                  Google
                </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<MicrosoftIcon />}
                  onClick={() => handleProviderLogin('microsoft')}
                  disabled={isLoading}
                >
                  Microsoft
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>

        <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 4 }}>
          By signing in, you agree to our{' '}
          <Link href="#" color="primary">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link href="#" color="primary">
            Privacy Policy
          </Link>
        </Typography>
      </Box>
    </Container>
  );
};

export default LoginPage;