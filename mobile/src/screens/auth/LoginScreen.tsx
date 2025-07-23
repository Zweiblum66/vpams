/**
 * Login Screen
 * 
 * Handles user authentication with support for
 * username/password login and biometric authentication.
 */

import React, {useState, useEffect} from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import {
  Text,
  TextInput,
  Button,
  Checkbox,
  Card,
  IconButton,
  Divider,
} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import {useDispatch, useSelector} from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';

import {AppState, LoginForm} from '@/types';
import {
  loginUser,
  authenticateWithBiometric,
  loadStoredAuth,
  clearError,
  setRememberLogin,
} from '@/store/slices/authSlice';
import {biometricService} from '@/services/biometricService';
import {colors, spacing, typography} from '@/constants/theme';
import {LoadingOverlay} from '@/components/LoadingOverlay';

export const LoginScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  const {isLoading, error, biometricEnabled, rememberLogin} = useSelector(
    (state: AppState) => state.auth
  );

  const [formData, setFormData] = useState<LoginForm>({
    username: '',
    password: '',
    remember_me: rememberLogin,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isBiometricAvailable, setIsBiometricAvailable] = useState(false);

  useEffect(() => {
    // Check for stored authentication
    dispatch(loadStoredAuth() as any);
    
    // Check biometric availability
    checkBiometricAvailability();
  }, [dispatch]);

  useEffect(() => {
    // Clear errors when user starts typing
    if (error) {
      const timer = setTimeout(() => {
        dispatch(clearError());
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, dispatch]);

  const checkBiometricAvailability = async () => {
    try {
      const isAvailable = await biometricService.isBiometricAvailable();
      setIsBiometricAvailable(isAvailable);
    } catch (error) {
      console.warn('Failed to check biometric availability:', error);
    }
  };

  const handleLogin = async () => {
    if (!formData.username.trim() || !formData.password.trim()) {
      Alert.alert('Error', 'Please enter both username and password');
      return;
    }

    try {
      await dispatch(loginUser(formData) as any).unwrap();
    } catch (error) {
      // Error is handled by Redux state
    }
  };

  const handleBiometricLogin = async () => {
    try {
      await dispatch(authenticateWithBiometric() as any).unwrap();
    } catch (error) {
      Alert.alert('Authentication Failed', 'Biometric authentication failed. Please try again.');
    }
  };

  const updateField = (field: keyof LoginForm, value: string | boolean) => {
    setFormData(prev => ({...prev, [field]: value}));
    
    if (field === 'remember_me') {
      dispatch(setRememberLogin(value as boolean));
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled">
        
        {/* Logo and Title */}
        <View style={styles.logoContainer}>
          <Icon name="movie" size={80} color={colors.primary} />
          <Text style={styles.title}>MAMS Mobile</Text>
          <Text style={styles.subtitle}>Digital Media Asset Management</Text>
        </View>

        {/* Login Form */}
        <Card style={styles.formCard}>
          <Card.Content style={styles.formContent}>
            <Text style={styles.formTitle}>Sign In</Text>
            
            {error && (
              <View style={styles.errorContainer}>
                <Icon name="error" size={16} color={colors.error} />
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}

            <TextInput
              label="Username or Email"
              value={formData.username}
              onChangeText={(text) => updateField('username', text)}
              mode="outlined"
              left={<TextInput.Icon icon="person" />}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="username"
              returnKeyType="next"
              style={styles.input}
            />

            <TextInput
              label="Password"
              value={formData.password}
              onChangeText={(text) => updateField('password', text)}
              mode="outlined"
              secureTextEntry={!showPassword}
              left={<TextInput.Icon icon="lock" />}
              right={
                <TextInput.Icon
                  icon={showPassword ? 'visibility-off' : 'visibility'}
                  onPress={() => setShowPassword(!showPassword)}
                />
              }
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="password"
              returnKeyType="done"
              onSubmitEditing={handleLogin}
              style={styles.input}
            />

            <View style={styles.checkboxContainer}>
              <Checkbox
                status={formData.remember_me ? 'checked' : 'unchecked'}
                onPress={() => updateField('remember_me', !formData.remember_me)}
              />
              <Text style={styles.checkboxLabel}>Remember me</Text>
            </View>

            <Button
              mode="contained"
              onPress={handleLogin}
              loading={isLoading}
              disabled={isLoading}
              style={styles.loginButton}
              contentStyle={styles.loginButtonContent}>
              Sign In
            </Button>

            {/* Biometric Login */}
            {isBiometricAvailable && biometricEnabled && (
              <>
                <View style={styles.dividerContainer}>
                  <Divider style={styles.divider} />
                  <Text style={styles.dividerText}>or</Text>
                  <Divider style={styles.divider} />
                </View>

                <Button
                  mode="outlined"
                  onPress={handleBiometricLogin}
                  disabled={isLoading}
                  icon="fingerprint"
                  style={styles.biometricButton}
                  contentStyle={styles.biometricButtonContent}>
                  Use Biometric Authentication
                </Button>
              </>
            )}

            {/* Forgot Password */}
            <Button
              mode="text"
              onPress={() => navigation.navigate('ForgotPassword' as never)}
              disabled={isLoading}
              style={styles.forgotButton}>
              Forgot Password?
            </Button>
          </Card.Content>
        </Card>

        {/* Register Link */}
        <View style={styles.registerContainer}>
          <Text style={styles.registerText}>Don't have an account? </Text>
          <Button
            mode="text"
            onPress={() => navigation.navigate('Register' as never)}
            disabled={isLoading}
            compact>
            Sign Up
          </Button>
        </View>
      </ScrollView>

      {isLoading && <LoadingOverlay />}
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.xl,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: spacing.xxxl,
  },
  title: {
    ...typography.headlineLarge,
    color: colors.primary,
    marginTop: spacing.md,
    fontWeight: '700',
  },
  subtitle: {
    ...typography.bodyMedium,
    color: colors.gray600,
    marginTop: spacing.xs,
    textAlign: 'center',
  },
  formCard: {
    marginBottom: spacing.lg,
  },
  formContent: {
    paddingVertical: spacing.lg,
  },
  formTitle: {
    ...typography.headlineSmall,
    color: colors.onSurface,
    textAlign: 'center',
    marginBottom: spacing.lg,
    fontWeight: '600',
  },
  errorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFEBEE',
    padding: spacing.md,
    borderRadius: 8,
    marginBottom: spacing.md,
  },
  errorText: {
    ...typography.bodySmall,
    color: colors.error,
    marginLeft: spacing.xs,
    flex: 1,
  },
  input: {
    marginBottom: spacing.md,
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  checkboxLabel: {
    ...typography.bodyMedium,
    color: colors.onSurface,
    marginLeft: spacing.xs,
  },
  loginButton: {
    marginBottom: spacing.md,
  },
  loginButtonContent: {
    paddingVertical: spacing.xs,
  },
  dividerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: spacing.md,
  },
  divider: {
    flex: 1,
  },
  dividerText: {
    ...typography.bodySmall,
    color: colors.gray500,
    marginHorizontal: spacing.md,
  },
  biometricButton: {
    marginBottom: spacing.md,
  },
  biometricButtonContent: {
    paddingVertical: spacing.xs,
  },
  forgotButton: {
    alignSelf: 'center',
  },
  registerContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: spacing.lg,
  },
  registerText: {
    ...typography.bodyMedium,
    color: colors.onBackground,
  },
});