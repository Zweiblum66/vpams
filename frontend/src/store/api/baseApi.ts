import { createApi } from '@reduxjs/toolkit/query/react';
import { baseQueryWithReauth } from '../../utils/tokenInterceptor';

// Create the base API slice
export const baseApi = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithReauth,
  tagTypes: [
    'User',
    'Role',
    'Permission',
    'Group',
    'Asset',
    'Project',
    'Container',
    'Search',
    'SavedSearch',
    'Metadata',
    'Storage',
    'Upload',
  ],
  endpoints: () => ({}),
});