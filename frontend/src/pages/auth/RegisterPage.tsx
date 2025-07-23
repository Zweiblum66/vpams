import React, { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
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
  LinearProgress,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  PersonAdd as PersonAddIcon,
  Google as GoogleIcon,
  Microsoft as MicrosoftIcon,
  Check as CheckIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { useFormik } from 'formik';
import * as Yup from 'yup';

import { useAuth } from '../../hooks/useAuth';
import { useErrorHandler } from '../../hooks/useErrorHandler';
import { logger } from '../../utils/logger';
import { ROUTES } from '../../router/routes';

// Password strength validation
const passwordStrengthRegex = {
  minLength: /.{8,}/,
  hasUppercase: /[A-Z]/,
  hasLowercase: /[a-z]/,
  hasNumber: /\d/,
  hasSpecialChar: /[!@#$%^&*(),.?":{}|<>]/,
};

const validationSchema = Yup.object({
  firstName: Yup.string()
    .min(2, 'First name must be at least 2 characters')
    .max(50, 'First name must be less than 50 characters')
    .required('First name is required'),
  lastName: Yup.string()
    .min(2, 'Last name must be at least 2 characters')
    .max(50, 'Last name must be less than 50 characters')
    .required('Last name is required'),
  email: Yup.string()
    .email('Invalid email address')
    .required('Email is required'),
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
  acceptTerms: Yup.boolean()
    .oneOf([true], 'You must accept the terms and conditions'),
  marketingEmails: Yup.boolean(),
});

interface RegisterFormValues {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  confirmPassword: string;
  acceptTerms: boolean;
  marketingEmails: boolean;
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

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register, loginWithProvider, isLoading } = useAuth();
  const { handleError } = useErrorHandler();

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [registerError, setRegisterError] = useState<string | null>(null);

  const formik = useFormik<RegisterFormValues>({
    initialValues: {
      firstName: '',
      lastName: '',
      email: '',
      password: '',
      confirmPassword: '',
      acceptTerms: false,
      marketingEmails: false,
    },
    validationSchema,
    onSubmit: async (values) => {
      try {
        setRegisterError(null);
        logger.info('Registration attempt started', {
          email: values.email,
          firstName: values.firstName,
          lastName: values.lastName,
          marketingEmails: values.marketingEmails,
          actionType: 'registration_attempt',
        });

        await register({
          firstName: values.firstName,
          lastName: values.lastName,
          email: values.email,
          password: values.password,
          acceptTerms: values.acceptTerms,
          marketingEmails: values.marketingEmails,
        });

        logger.info('Registration successful', {
          email: values.email,
          actionType: 'registration_success',
        });

        navigate(ROUTES.DASHBOARD, { replace: true });
      } catch (error: any) {
        const errorMessage = error?.message || 'Registration failed. Please try again.';
        setRegisterError(errorMessage);
        
        logger.error('Registration failed', {
          email: values.email,
          error: errorMessage,
          actionType: 'registration_error',
        }, error);

        handleError(error, {
          context: 'RegisterPage.onSubmit',
          userMessage: 'Failed to create account. Please check your information and try again.',
        });
      }
    },
  });

  const handleProviderRegister = async (provider: 'google' | 'microsoft') => {
    try {
      setRegisterError(null);
      logger.info('OAuth registration attempt started', {
        provider,
        actionType: 'oauth_registration_attempt',
      });

      await loginWithProvider(provider);

      logger.info('OAuth registration successful', {
        provider,
        actionType: 'oauth_registration_success',
      });

      navigate(ROUTES.DASHBOARD, { replace: true });
    } catch (error: any) {
      const errorMessage = error?.message || `${provider} registration failed. Please try again.`;
      setRegisterError(errorMessage);
      
      logger.error('OAuth registration failed', {
        provider,
        error: errorMessage,
        actionType: 'oauth_registration_error',
      }, error);

      handleError(error, {
        context: `RegisterPage.handleProviderRegister.${provider}`,
        userMessage: `Failed to register with ${provider}. Please try again.`,
      });
    }
  };

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  const toggleConfirmPasswordVisibility = () => {
    setShowConfirmPassword(!showConfirmPassword);
  };

  return (
    <Container component="main" maxWidth="sm">
      <Box
        sx={{
          marginTop: 4,
          marginBottom: 4,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Card sx={{ width: '100%', maxWidth: 500 }}>
          <CardContent sx={{ p: 4 }}>
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                mb: 3,
              }}
            >
              <PersonAddIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography component="h1" variant="h4" align="center">
                Create Account
              </Typography>
              <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
                Join MAMS to manage your media assets
              </Typography>
            </Box>

            {registerError && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {registerError}
              </Alert>
            )}

            <Box component="form" onSubmit={formik.handleSubmit} noValidate>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  id="firstName"
                  label="First Name"
                  name="firstName"
                  autoComplete="given-name"
                  autoFocus
                  value={formik.values.firstName}
                  onChange={formik.handleChange}
                  onBlur={formik.handleBlur}
                  error={formik.touched.firstName && Boolean(formik.errors.firstName)}
                  helperText={formik.touched.firstName && formik.errors.firstName}
                  disabled={isLoading}
                />
                
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  id="lastName"
                  label="Last Name"
                  name="lastName"
                  autoComplete="family-name"
                  value={formik.values.lastName}
                  onChange={formik.handleChange}
                  onBlur={formik.handleBlur}
                  error={formik.touched.lastName && Boolean(formik.errors.lastName)}
                  helperText={formik.touched.lastName && formik.errors.lastName}
                  disabled={isLoading}
                />
              </Box>

              <TextField
                margin="normal"
                required
                fullWidth
                id="email"
                label="Email Address"
                name="email"
                autoComplete="email"
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
                autoComplete="new-password"
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
                label="Confirm Password"
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

              <FormControlLabel
                control={
                  <Checkbox
                    name="acceptTerms"
                    checked={formik.values.acceptTerms}
                    onChange={formik.handleChange}
                    color="primary"
                    disabled={isLoading}
                  />
                }
                label={
                  <Typography variant="body2">
                    I agree to the{' '}
                    <Link href="#" color="primary">
                      Terms of Service
                    </Link>{' '}
                    and{' '}
                    <Link href="#" color="primary">
                      Privacy Policy
                    </Link>
                  </Typography>
                }
                sx={{ mt: 2, alignItems: 'flex-start' }}
              />
              {formik.touched.acceptTerms && formik.errors.acceptTerms && (
                <Typography variant="caption" color="error" sx={{ ml: 4 }}>
                  {formik.errors.acceptTerms}
                </Typography>
              )}

              <FormControlLabel
                control={
                  <Checkbox
                    name="marketingEmails"
                    checked={formik.values.marketingEmails}
                    onChange={formik.handleChange}
                    color="primary"
                    disabled={isLoading}
                  />
                }
                label={
                  <Typography variant="body2">
                    Send me product updates and marketing emails (optional)
                  </Typography>
                }
                sx={{ mt: 1 }}
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={isLoading}
                startIcon={isLoading ? <CircularProgress size={20} /> : <PersonAddIcon />}
              >
                {isLoading ? 'Creating Account...' : 'Create Account'}
              </Button>

              <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                <Link
                  component={RouterLink}
                  to={ROUTES.LOGIN}
                  variant="body2"
                  color="primary"
                >
                  Already have an account? Sign In
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
                  onClick={() => handleProviderRegister('google')}
                  disabled={isLoading}
                >
                  Google
                </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<MicrosoftIcon />}
                  onClick={() => handleProviderRegister('microsoft')}
                  disabled={isLoading}
                >
                  Microsoft
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
};

export default RegisterPage;