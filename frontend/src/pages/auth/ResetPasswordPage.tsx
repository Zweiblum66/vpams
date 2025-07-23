import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link as RouterLink } from 'react-router-dom';
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
  InputAdornment,
  IconButton,
  LinearProgress,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  LockReset as LockResetIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { useFormik } from 'formik';
import * as Yup from 'yup';

import { useErrorHandler } from '../../hooks/useErrorHandler';
import { logger } from '../../utils/logger';
import { ROUTES } from '../../router/routes';
import { authApi } from '../../services/authApi';

// Password strength validation
const passwordStrengthRegex = {
  minLength: /.{8,}/,
  hasUppercase: /[A-Z]/,
  hasLowercase: /[a-z]/,
  hasNumber: /\d/,
  hasSpecialChar: /[!@#$%^&*(),.?":{}|<>]/,
};

const validationSchema = Yup.object({
  password: Yup.string()
    .min(8, 'Password must be at least 8 characters')
    .matches(passwordStrengthRegex.hasUppercase, 'Password must contain at least one uppercase letter')
    .matches(passwordStrengthRegex.hasLowercase, 'Password must contain at least one lowercase letter')
    .matches(passwordStrengthRegex.hasNumber, 'Password must contain at least one number')
    .matches(passwordStrengthRegex.hasSpecialChar, 'Password must contain at least one special character')
    .required('Password is required'),
  confirmPassword: Yup.string()
    .oneOf([Yup.ref('password')], 'Passwords must match')
    .required('Please confirm your password'),
});

interface ResetPasswordFormValues {
  password: string;
  confirmPassword: string;
}

interface PasswordStrengthProps {
  password: string;
}

const PasswordStrength: React.FC<PasswordStrengthProps> = ({ password }) => {
  const checks = [
    { regex: passwordStrengthRegex.minLength, label: 'At least 8 characters' },
    { regex: passwordStrengthRegex.hasUppercase, label: 'One uppercase letter' },
    { regex: passwordStrengthRegex.hasLowercase, label: 'One lowercase letter' },
    { regex: passwordStrengthRegex.hasNumber, label: 'One number' },
    { regex: passwordStrengthRegex.hasSpecialChar, label: 'One special character' },
  ];

  const passedChecks = checks.filter(check => check.regex.test(password)).length;
  const strengthPercentage = (passedChecks / checks.length) * 100;
  
  const getStrengthColor = () => {
    if (strengthPercentage < 40) return 'error';
    if (strengthPercentage < 80) return 'warning';
    return 'success';
  };

  const getStrengthLabel = () => {
    if (strengthPercentage < 40) return 'Weak';
    if (strengthPercentage < 80) return 'Medium';
    return 'Strong';
  };

  if (!password) return null;

  return (
    <Box sx={{ mt: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Typography variant="caption" color="text.secondary">
          Password strength:
        </Typography>
        <Typography variant="caption" color={`${getStrengthColor()}.main`} fontWeight="medium">
          {getStrengthLabel()}
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={strengthPercentage}
        color={getStrengthColor()}
        sx={{ height: 4, borderRadius: 2 }}
      />
      <Box sx={{ mt: 1 }}>
        {checks.map((check, index) => {
          const passed = check.regex.test(password);
          return (
            <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {passed ? (
                <CheckIcon sx={{ fontSize: 14, color: 'success.main' }} />
              ) : (
                <CloseIcon sx={{ fontSize: 14, color: 'error.main' }} />
              )}
              <Typography
                variant="caption"
                color={passed ? 'success.main' : 'error.main'}
              >
                {check.label}
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};

const ResetPasswordPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { handleError } = useErrorHandler();

  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [tokenValid, setTokenValid] = useState<boolean | null>(null);

  const token = searchParams.get('token');

  // Validate token on component mount
  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setError('Invalid or missing reset token');
        setTokenValid(false);
        return;
      }

      try {
        await authApi.validateResetToken(token);
        setTokenValid(true);
        logger.info('Password reset token validated', {
          actionType: 'password_reset_token_validation_success',
        });
      } catch (error: any) {
        setError('Invalid or expired reset token');
        setTokenValid(false);
        logger.error('Password reset token validation failed', {
          error: error?.message,
          actionType: 'password_reset_token_validation_error',
        }, error);
      }
    };

    validateToken();
  }, [token]);

  const formik = useFormik<ResetPasswordFormValues>({
    initialValues: {
      password: '',
      confirmPassword: '',
    },
    validationSchema,
    onSubmit: async (values) => {
      if (!token) {
        setError('Invalid reset token');
        return;
      }

      try {
        setIsLoading(true);
        setError(null);
        
        logger.info('Password reset attempt started', {
          actionType: 'password_reset_attempt',
        });

        await authApi.resetPassword(token, values.password);

        logger.info('Password reset successful', {
          actionType: 'password_reset_success',
        });

        setIsSuccess(true);
      } catch (error: any) {
        const errorMessage = error?.message || 'Failed to reset password. Please try again.';
        setError(errorMessage);
        
        logger.error('Password reset failed', {
          error: errorMessage,
          actionType: 'password_reset_error',
        }, error);

        handleError(error, {
          context: 'ResetPasswordPage.onSubmit',
          userMessage: 'Failed to reset password. Please try again.',
        });
      } finally {
        setIsLoading(false);
      }
    },
  });

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  const toggleConfirmPasswordVisibility = () => {
    setShowConfirmPassword(!showConfirmPassword);
  };

  // Show loading state while validating token
  if (tokenValid === null) {
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
                  gap: 2,
                }}
              >
                <CircularProgress />
                <Typography variant="body1" color="text.secondary">
                  Validating reset token...
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Box>
      </Container>
    );
  }

  // Show success state
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
                  Password Reset Complete
                </Typography>
                <Typography variant="body1" color="text.secondary" align="center" sx={{ mt: 2 }}>
                  Your password has been successfully reset. You can now sign in with your new password.
                </Typography>
              </Box>

              <Button
                component={RouterLink}
                to={ROUTES.LOGIN}
                variant="contained"
                fullWidth
              >
                Sign In
              </Button>
            </CardContent>
          </Card>
        </Box>
      </Container>
    );
  }

  // Show error state for invalid token
  if (!tokenValid) {
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
                <CloseIcon sx={{ fontSize: 48, color: 'error.main', mb: 2 }} />
                <Typography component="h1" variant="h4" align="center">
                  Invalid Reset Link
                </Typography>
                <Typography variant="body1" color="text.secondary" align="center" sx={{ mt: 2 }}>
                  This password reset link is invalid or has expired.
                </Typography>
              </Box>

              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Button
                  component={RouterLink}
                  to={ROUTES.FORGOT_PASSWORD}
                  variant="contained"
                  fullWidth
                >
                  Request New Reset Link
                </Button>
                
                <Button
                  component={RouterLink}
                  to={ROUTES.LOGIN}
                  variant="outlined"
                  fullWidth
                >
                  Back to Sign In
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Box>
      </Container>
    );
  }

  // Show reset password form
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
                Reset Password
              </Typography>
              <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
                Enter your new password below
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
                name="password"
                label="New Password"
                type={showPassword ? 'text' : 'password'}
                id="password"
                autoComplete="new-password"
                autoFocus
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

              <PasswordStrength password={formik.values.password} />

              <TextField
                margin="normal"
                required
                fullWidth
                name="confirmPassword"
                label="Confirm New Password"
                type={showConfirmPassword ? 'text' : 'password'}
                id="confirmPassword"
                autoComplete="new-password"
                value={formik.values.confirmPassword}
                onChange={formik.handleChange}
                onBlur={formik.handleBlur}
                error={formik.touched.confirmPassword && Boolean(formik.errors.confirmPassword)}
                helperText={formik.touched.confirmPassword && formik.errors.confirmPassword}
                disabled={isLoading}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle confirm password visibility"
                        onClick={toggleConfirmPasswordVisibility}
                        edge="end"
                        disabled={isLoading}
                      >
                        {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={isLoading}
                startIcon={isLoading ? <CircularProgress size={20} /> : <LockResetIcon />}
              >
                {isLoading ? 'Resetting Password...' : 'Reset Password'}
              </Button>

              <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                <Link
                  component={RouterLink}
                  to={ROUTES.LOGIN}
                  variant="body2"
                  color="primary"
                >
                  Back to Sign In
                </Link>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
};

export default ResetPasswordPage;