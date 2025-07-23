import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Link,
  TextField,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  LockReset as LockResetIcon,
  ArrowBack as ArrowBackIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { useFormik } from 'formik';
import * as Yup from 'yup';

import { useErrorHandler } from '../../hooks/useErrorHandler';
import { logger } from '../../utils/logger';
import { ROUTES } from '../../router/routes';
import { authApi } from '../../services/authApi';

const validationSchema = Yup.object({
  email: Yup.string()
    .email('Invalid email address')
    .required('Email is required'),
});

interface ForgotPasswordFormValues {
  email: string;
}

const ForgotPasswordPage: React.FC = () => {
  const { handleError } = useErrorHandler();
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formik = useFormik<ForgotPasswordFormValues>({
    initialValues: {
      email: '',
    },
    validationSchema,
    onSubmit: async (values) => {
      try {
        setIsLoading(true);
        setError(null);
        
        logger.info('Password reset request started', {
          email: values.email,
          actionType: 'password_reset_request',
        });

        await authApi.requestPasswordReset(values.email);

        logger.info('Password reset request successful', {
          email: values.email,
          actionType: 'password_reset_request_success',
        });

        setIsSuccess(true);
      } catch (error: any) {
        const errorMessage = error?.message || 'Failed to send password reset email. Please try again.';
        setError(errorMessage);
        
        logger.error('Password reset request failed', {
          email: values.email,
          error: errorMessage,
          actionType: 'password_reset_request_error',
        }, error);

        handleError(error, {
          context: 'ForgotPasswordPage.onSubmit',
          userMessage: 'Failed to send password reset email. Please try again.',
        });
      } finally {
        setIsLoading(false);
      }
    },
  });

  if (isSuccess) {
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
                <CheckCircleIcon sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
                <Typography component="h1" variant="h4" align="center">
                  Check Your Email
                </Typography>
                <Typography variant="body1" color="text.secondary" align="center" sx={{ mt: 2 }}>
                  We've sent a password reset link to{' '}
                  <Typography component="span" fontWeight="medium">
                    {formik.values.email}
                  </Typography>
                </Typography>
              </Box>

              <Alert severity="info" sx={{ mb: 3 }}>
                <Typography variant="body2">
                  If you don't see the email in your inbox, please check your spam folder.
                  The link will expire in 1 hour.
                </Typography>
              </Alert>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Button
                  component={RouterLink}
                  to={ROUTES.LOGIN}
                  variant="contained"
                  fullWidth
                  startIcon={<ArrowBackIcon />}
                >
                  Back to Sign In
                </Button>
                
                <Button
                  variant="outlined"
                  fullWidth
                  onClick={() => {
                    setIsSuccess(false);
                    formik.resetForm();
                  }}
                >
                  Send Another Email
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Box>
      </Container>
    );
  }

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
              <LockResetIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography component="h1" variant="h4" align="center">
                Forgot Password?
              </Typography>
              <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
                Enter your email address and we'll send you a link to reset your password
              </Typography>
            </Box>

            {error && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
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

              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={isLoading}
                startIcon={isLoading ? <CircularProgress size={20} /> : <LockResetIcon />}
              >
                {isLoading ? 'Sending...' : 'Send Reset Link'}
              </Button>

              <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                <Link
                  component={RouterLink}
                  to={ROUTES.LOGIN}
                  variant="body2"
                  color="primary"
                  sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
                >
                  <ArrowBackIcon fontSize="small" />
                  Back to Sign In
                </Link>
              </Box>
            </Box>
          </CardContent>
        </Card>

        <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 4 }}>
          Remember your password?{' '}
          <Link component={RouterLink} to={ROUTES.LOGIN} color="primary">
            Sign In
          </Link>
        </Typography>
      </Box>
    </Container>
  );
};

export default ForgotPasswordPage;