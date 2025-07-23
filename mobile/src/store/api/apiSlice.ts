/**
 * RTK Query API Slice
 * 
 * Centralized API definitions using RTK Query
 * for caching and state management.
 */

import {createApi, fetchBaseQuery} from '@reduxjs/toolkit/query/react';
import {RootState} from '../index';

// Define base query with auth
const baseQuery = fetchBaseQuery({
  baseUrl: '/api/v1',
  prepareHeaders: (headers, {getState}) => {
    const token = (getState() as RootState).auth.tokens?.access_token;
    if (token) {
      headers.set('authorization', `Bearer ${token}`);
    }
    return headers;
  },
});

export const apiSlice = createApi({
  reducerPath: 'api',
  baseQuery,
  tagTypes: ['Asset', 'Project', 'User', 'Notification'],
  endpoints: (builder) => ({
    // Asset endpoints
    getAssets: builder.query({
      query: (params) => ({
        url: '/assets',
        params,
      }),
      providesTags: ['Asset'],
    }),
    
    // Project endpoints
    getProjects: builder.query({
      query: (params) => ({
        url: '/projects',
        params,
      }),
      providesTags: ['Project'],
    }),
    
    // Notification endpoints
    getNotifications: builder.query({
      query: (params) => ({
        url: '/notifications',
        params,
      }),
      providesTags: ['Notification'],
    }),
  }),
});

export const {
  useGetAssetsQuery,
  useGetProjectsQuery,
  useGetNotificationsQuery,
} = apiSlice;