import { BaseQueryFn, FetchArgs, fetchBaseQuery, FetchBaseQueryError } from '@reduxjs/toolkit/query/react';
import { RootState } from '../store';
import { clearAuth, setTokens } from '../store/slices/authSlice';
import { Navigation } from '../router/navigation';
import { AuthPersistence } from './authPersistence';

const baseQuery = fetchBaseQuery({
  baseUrl: '/api/v1',
  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.token;
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    headers.set('Content-Type', 'application/json');
    return headers;
  },
});

export const baseQueryWithReauth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  let result = await baseQuery(args, api, extraOptions);

  if (result.error && result.error.status === 401) {
    // Try to refresh the token
    const refreshToken = AuthPersistence.getRefreshToken();
    
    if (refreshToken) {
      const refreshResult = await baseQuery({
        url: '/auth/refresh',
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${refreshToken}`,
        },
      }, api, extraOptions);

      if (refreshResult.data) {
        const { access_token } = refreshResult.data as { access_token: string };
        
        // Store new token
        AuthPersistence.setAccessToken(access_token);
        api.dispatch(setTokens({
          accessToken: access_token,
          refreshToken: refreshToken
        }));
        
        // Retry the original query
        result = await baseQuery(args, api, extraOptions);
      } else {
        // Refresh failed, clear auth state
        api.dispatch(clearAuth());
        
        // Redirect to login if we're not already there
        if (window.location.pathname !== Navigation.login()) {
          window.location.href = Navigation.login();
        }
      }
    } else {
      // No refresh token, clear auth state
      api.dispatch(clearAuth());
      
      // Redirect to login if we're not already there
      if (window.location.pathname !== Navigation.login()) {
        window.location.href = Navigation.login();
      }
    }
  }

  return result;
};

// Token utility functions
export const getTokenPayload = (token: string): any => {
  try {
    return JSON.parse(atob(token.split('.')[1]));
  } catch (error) {
    return null;
  }
};

export const isTokenExpired = (token: string): boolean => {
  const payload = getTokenPayload(token);
  if (!payload) return true;
  
  const now = Math.floor(Date.now() / 1000);
  return payload.exp <= now;
};

export const getTokenExpirationTime = (token: string): number => {
  const payload = getTokenPayload(token);
  return payload ? payload.exp : 0;
};

export const shouldRefreshToken = (token: string, thresholdMinutes: number = 5): boolean => {
  const payload = getTokenPayload(token);
  if (!payload) return false;
  
  const now = Math.floor(Date.now() / 1000);
  const timeUntilExpiry = payload.exp - now;
  
  return timeUntilExpiry < (thresholdMinutes * 60);
};