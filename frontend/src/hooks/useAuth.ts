import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../store';
import { clearAuth, setUser, setTokens, clearError } from '../store/slices/authSlice';
import { authApi, LoginRequest, RegisterRequest, AuthApiError } from '../services/authApi';
import { User } from '../types';
import { Navigation } from '../router/navigation';
import { AuthPersistence } from '../utils/authPersistence';

export const useAuth = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { user, token, isAuthenticated, error } = useAppSelector(state => state.auth);
  
  const [isLoading, setIsLoading] = useState(false);

  // Login function
  const login = useCallback(async (credentials: LoginRequest) => {
    setIsLoading(true);
    try {
      const result = await authApi.login(credentials);
      
      // Store tokens and user data
      AuthPersistence.setTokens(result.access_token, result.refresh_token);
      AuthPersistence.setUserData(result.user);
      if (credentials.rememberMe) {
        AuthPersistence.setRememberMe(true);
      }
      
      // Update state
      dispatch(setTokens({
        accessToken: result.access_token,
        refreshToken: result.refresh_token
      }));
      dispatch(setUser(result.user));
      
      return result;
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [dispatch]);

  // Register function
  const register = useCallback(async (userData: RegisterRequest) => {
    setIsLoading(true);
    try {
      const result = await authApi.register(userData);
      
      // Store tokens and user data
      AuthPersistence.setTokens(result.access_token, result.refresh_token);
      AuthPersistence.setUserData(result.user);
      if (userData.marketingEmails) {
        AuthPersistence.setRememberMe(true);
      }
      
      // Update state
      dispatch(setTokens({
        accessToken: result.access_token,
        refreshToken: result.refresh_token
      }));
      dispatch(setUser(result.user));
      
      return result;
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [dispatch]);

  // OAuth login function
  const loginWithProvider = useCallback(async (provider: 'google' | 'microsoft') => {
    setIsLoading(true);
    try {
      const result = await authApi.loginWithProvider(provider);
      
      // Store tokens and user data
      AuthPersistence.setTokens(result.access_token, result.refresh_token);
      AuthPersistence.setUserData(result.user);
      
      // Update state
      dispatch(setTokens({
        accessToken: result.access_token,
        refreshToken: result.refresh_token
      }));
      dispatch(setUser(result.user));
      
      return result;
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [dispatch]);

  // Logout function
  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      // Call logout endpoint if we have a token
      if (token) {
        await authApi.logout();
      }
    } catch (error) {
      console.error('Logout error:', error);
      // Continue with logout even if API call fails
    } finally {
      // Clear auth state and persistence regardless of API result
      AuthPersistence.clearAll();
      dispatch(clearAuth());
      setIsLoading(false);
    }
  }, [token, dispatch]);

  // Refresh token function
  const refreshToken = useCallback(async () => {
    const refreshTokenValue = AuthPersistence.getRefreshToken();
    if (!refreshTokenValue) {
      dispatch(clearAuth());
      return false;
    }

    try {
      const result = await authApi.refreshToken(refreshTokenValue);
      AuthPersistence.setAccessToken(result.access_token);
      dispatch(setTokens({
        accessToken: result.access_token,
        refreshToken: refreshTokenValue
      }));
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      AuthPersistence.clearAll();
      dispatch(clearAuth());
      return false;
    }
  }, [dispatch]);

  // Check token expiration and refresh if needed
  const checkTokenExpiration = useCallback(() => {
    if (!token) return;

    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const now = Math.floor(Date.now() / 1000);
      const timeUntilExpiry = payload.exp - now;

      // Refresh token if it expires within 5 minutes
      if (timeUntilExpiry < 300) {
        refreshToken();
      }
    } catch (error) {
      console.error('Error checking token expiration:', error);
      dispatch(clearAuth());
    }
  }, [token, refreshToken, dispatch]);

  // Check user permissions
  const hasPermission = useCallback((permission: string): boolean => {
    if (!user) return false;
    
    // Superuser has all permissions
    if (user.is_superuser) return true;
    
    // Check specific permission
    return user.permissions?.includes(permission) || false;
  }, [user]);

  // Check if user has any of the specified permissions
  const hasAnyPermission = useCallback((permissions: string[]): boolean => {
    return permissions.some(permission => hasPermission(permission));
  }, [hasPermission]);

  // Check if user has all of the specified permissions
  const hasAllPermissions = useCallback((permissions: string[]): boolean => {
    return permissions.every(permission => hasPermission(permission));
  }, [hasPermission]);

  // Clear error function
  const clearAuthError = useCallback(() => {
    dispatch(clearError());
  }, [dispatch]);

  // Set return path for login redirect
  const setReturnPath = useCallback((path: string) => {
    AuthPersistence.setReturnPath(path);
  }, []);

  return {
    // State
    user,
    token,
    isAuthenticated,
    isLoading,
    error,
    
    // Actions
    login,
    register,
    loginWithProvider,
    logout,
    refreshToken,
    clearAuthError,
    setReturnPath,
    
    // Permission checks
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    
    // Utilities
    checkTokenExpiration,
  };
};