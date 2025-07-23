import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { AuthState, User } from '../../types';
import { authApi } from '../api/authApi';
import { AuthPersistence } from '../../utils/authPersistence';
import { isTokenExpired } from '../../utils/tokenInterceptor';

const initialState: AuthState = {
  user: AuthPersistence.getUserData(),
  token: AuthPersistence.getAccessToken(),
  isAuthenticated: false,
  isLoading: false,
  error: undefined,
};

// Helper function to check if token is valid and not expired
const isTokenValid = (token: string | null): boolean => {
  if (!token) return false;
  return !isTokenExpired(token);
};

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    ...initialState,
    isAuthenticated: AuthPersistence.isAuthenticated(),
  },
  reducers: {
    clearError: (state) => {
      state.error = undefined;
    },
    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload;
      state.isAuthenticated = true;
      AuthPersistence.setUserData(action.payload);
    },
    setToken: (state, action: PayloadAction<string>) => {
      state.token = action.payload;
      state.isAuthenticated = isTokenValid(action.payload);
      AuthPersistence.setAccessToken(action.payload);
    },
    setTokens: (state, action: PayloadAction<{ accessToken: string; refreshToken: string }>) => {
      state.token = action.payload.accessToken;
      state.isAuthenticated = isTokenValid(action.payload.accessToken);
      AuthPersistence.setTokens(action.payload.accessToken, action.payload.refreshToken);
    },
    clearAuth: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.error = undefined;
      AuthPersistence.clearAll();
    },
    setRememberMe: (state, action: PayloadAction<boolean>) => {
      AuthPersistence.setRememberMe(action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(authApi.endpoints.login.matchPending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(authApi.endpoints.login.matchFulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload.user;
        state.token = action.payload.tokens.access_token;
        state.isAuthenticated = true;
        state.error = undefined;
        AuthPersistence.setUserData(action.payload.user);
        AuthPersistence.setTokens(action.payload.tokens.access_token, action.payload.tokens.refresh_token);
      })
      .addCase(authApi.endpoints.login.matchRejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Login failed';
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
      })
      // Logout
      .addCase(authApi.endpoints.logout.matchPending, (state) => {
        state.isLoading = true;
      })
      .addCase(authApi.endpoints.logout.matchFulfilled, (state) => {
        state.isLoading = false;
        state.user = null;
        state.token = null;
        state.isAuthenticated = false;
        state.error = undefined;
        AuthPersistence.clearAll();
      })
      .addCase(authApi.endpoints.logout.matchRejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Logout failed';
        // Clear auth state even if logout fails
        state.user = null;
        state.token = null;
        state.isAuthenticated = false;
        AuthPersistence.clearAll();
      })
      // Get current user
      .addCase(authApi.endpoints.getCurrentUser.matchPending, (state) => {
        state.isLoading = true;
      })
      .addCase(authApi.endpoints.getCurrentUser.matchFulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
        state.error = undefined;
        AuthPersistence.setUserData(action.payload);
      })
      .addCase(authApi.endpoints.getCurrentUser.matchRejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to get current user';
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
        AuthPersistence.clearAll();
      })
      // Refresh token
      .addCase(authApi.endpoints.refreshToken.matchPending, (state) => {
        state.isLoading = true;
      })
      .addCase(authApi.endpoints.refreshToken.matchFulfilled, (state, action) => {
        state.isLoading = false;
        state.token = action.payload.access_token;
        state.error = undefined;
        AuthPersistence.setAccessToken(action.payload.access_token);
      })
      .addCase(authApi.endpoints.refreshToken.matchRejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Token refresh failed';
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
        AuthPersistence.clearAll();
      });
  },
});

export const { clearError, setUser, setToken, setTokens, clearAuth, setRememberMe } = authSlice.actions;
export default authSlice.reducer;