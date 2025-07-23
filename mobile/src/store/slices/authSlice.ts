/**
 * Authentication Redux Slice
 * 
 * Manages authentication state including user data,
 * tokens, biometric settings, and login persistence.
 */

import {createSlice, createAsyncThunk, PayloadAction} from '@reduxjs/toolkit';
import {AuthState, User, LoginForm, RegisterForm} from '@/types';
import {authService} from '@/services/authService';
import {storageService} from '@/services/storageService';
import {biometricService} from '@/services/biometricService';

const initialState: AuthState = {
  isAuthenticated: false,
  user: null,
  tokens: null,
  isLoading: false,
  error: null,
  biometricEnabled: false,
  rememberLogin: false,
};

// Async thunks
export const loginUser = createAsyncThunk(
  'auth/loginUser',
  async (credentials: LoginForm, {rejectWithValue}) => {
    try {
      const response = await authService.login(credentials);
      
      // Store tokens securely
      if (credentials.remember_me) {
        await storageService.storeTokens(response.tokens);
      }
      
      return response;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const registerUser = createAsyncThunk(
  'auth/registerUser',
  async (userData: RegisterForm, {rejectWithValue}) => {
    try {
      const response = await authService.register(userData);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const refreshToken = createAsyncThunk(
  'auth/refreshToken',
  async (_, {getState, rejectWithValue}) => {
    try {
      const state = getState() as any;
      const refreshToken = state.auth.tokens?.refresh_token;
      
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }
      
      const response = await authService.refreshToken(refreshToken);
      await storageService.storeTokens(response.tokens);
      
      return response;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const logoutUser = createAsyncThunk(
  'auth/logoutUser',
  async (_, {getState}) => {
    const state = getState() as any;
    const accessToken = state.auth.tokens?.access_token;
    
    try {
      if (accessToken) {
        await authService.logout(accessToken);
      }
    } catch (error) {
      // Continue with logout even if API call fails
      console.warn('Failed to logout from server:', error);
    }
    
    // Clear stored tokens
    await storageService.clearTokens();
    await storageService.clearBiometricData();
  }
);

export const enableBiometric = createAsyncThunk(
  'auth/enableBiometric',
  async (_, {getState, rejectWithValue}) => {
    try {
      const state = getState() as any;
      const user = state.auth.user;
      const tokens = state.auth.tokens;
      
      if (!user || !tokens) {
        throw new Error('User not authenticated');
      }
      
      const isSupported = await biometricService.isBiometricSupported();
      if (!isSupported) {
        throw new Error('Biometric authentication not supported');
      }
      
      await biometricService.storeBiometricData(user.id, tokens);
      return true;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const authenticateWithBiometric = createAsyncThunk(
  'auth/authenticateWithBiometric',
  async (_, {rejectWithValue}) => {
    try {
      const isAvailable = await biometricService.isBiometricAvailable();
      if (!isAvailable) {
        throw new Error('Biometric data not available');
      }
      
      const authenticated = await biometricService.authenticate('Authenticate to access MAMS');
      if (!authenticated) {
        throw new Error('Biometric authentication failed');
      }
      
      const biometricData = await biometricService.getBiometricData();
      if (!biometricData) {
        throw new Error('Failed to retrieve biometric data');
      }
      
      // Verify tokens are still valid
      const isValid = await authService.verifyToken(biometricData.tokens.access_token);
      if (!isValid) {
        // Try to refresh token
        const refreshed = await authService.refreshToken(biometricData.tokens.refresh_token);
        return {
          user: biometricData.user,
          tokens: refreshed.tokens,
        };
      }
      
      return biometricData;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const loadStoredAuth = createAsyncThunk(
  'auth/loadStoredAuth',
  async (_, {rejectWithValue}) => {
    try {
      const tokens = await storageService.getTokens();
      if (!tokens) {
        return null;
      }
      
      // Verify token is still valid
      const isValid = await authService.verifyToken(tokens.access_token);
      if (!isValid) {
        // Try to refresh
        try {
          const refreshed = await authService.refreshToken(tokens.refresh_token);
          await storageService.storeTokens(refreshed.tokens);
          return refreshed;
        } catch (refreshError) {
          // Clear invalid tokens
          await storageService.clearTokens();
          return null;
        }
      }
      
      // Get current user data
      const user = await authService.getCurrentUser(tokens.access_token);
      return {user, tokens};
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

// Auth slice
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    updateUser: (state, action: PayloadAction<Partial<User>>) => {
      if (state.user) {
        state.user = {...state.user, ...action.payload};
      }
    },
    setRememberLogin: (state, action: PayloadAction<boolean>) => {
      state.rememberLogin = action.payload;
    },
    disableBiometric: (state) => {
      state.biometricEnabled = false;
    },
  },
  extraReducers: (builder) => {
    // Login
    builder
      .addCase(loginUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.tokens = action.payload.tokens;
        state.error = null;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Register
    builder
      .addCase(registerUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(registerUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.tokens = action.payload.tokens;
        state.error = null;
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Refresh token
    builder
      .addCase(refreshToken.fulfilled, (state, action) => {
        state.tokens = action.payload.tokens;
        if (action.payload.user) {
          state.user = action.payload.user;
        }
      })
      .addCase(refreshToken.rejected, (state) => {
        // Token refresh failed, logout user
        state.isAuthenticated = false;
        state.user = null;
        state.tokens = null;
      });

    // Logout
    builder.addCase(logoutUser.fulfilled, (state) => {
      state.isAuthenticated = false;
      state.user = null;
      state.tokens = null;
      state.biometricEnabled = false;
      state.rememberLogin = false;
      state.error = null;
    });

    // Enable biometric
    builder
      .addCase(enableBiometric.fulfilled, (state) => {
        state.biometricEnabled = true;
      })
      .addCase(enableBiometric.rejected, (state, action) => {
        state.error = action.payload as string;
      });

    // Biometric authentication
    builder
      .addCase(authenticateWithBiometric.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(authenticateWithBiometric.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.tokens = action.payload.tokens;
        state.biometricEnabled = true;
        state.error = null;
      })
      .addCase(authenticateWithBiometric.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });

    // Load stored auth
    builder
      .addCase(loadStoredAuth.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(loadStoredAuth.fulfilled, (state, action) => {
        state.isLoading = false;
        if (action.payload) {
          state.isAuthenticated = true;
          state.user = action.payload.user;
          state.tokens = action.payload.tokens;
          state.rememberLogin = true;
        }
      })
      .addCase(loadStoredAuth.rejected, (state) => {
        state.isLoading = false;
      });
  },
});

export const {clearError, updateUser, setRememberLogin, disableBiometric} = authSlice.actions;
export default authSlice.reducer;