# RTK Query Integration Guide

This document explains how RTK Query is integrated into the MAMS frontend application.

## Overview

RTK Query is the official data fetching and caching solution for Redux Toolkit. It provides:
- Automatic caching with intelligent re-fetching
- Optimistic updates
- Background refetching
- Automatic request deduplication
- TypeScript support out of the box

## Architecture

### Base API Configuration

The base API is configured in `src/store/api/baseApi.ts`:

```typescript
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

const baseQuery = fetchBaseQuery({
  baseUrl: '/api/v1',
  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.token;
    if (token) {
      headers.set('authorization', `Bearer ${token}`);
    }
    return headers;
  },
});

export const baseApi = createApi({
  reducerPath: 'api',
  baseQuery,
  tagTypes: ['User', 'Asset', 'Project', 'Search', /* ... */],
  endpoints: () => ({}),
});
```

### API Slices

Each domain has its own API slice that extends the base API:

- `assetApi.ts` - Asset management endpoints
- `authApi.ts` - Authentication endpoints
- `projectApi.ts` - Project management endpoints
- `searchApi.ts` - Search endpoints
- `userApi.ts` - User management endpoints

## Usage Examples

### Basic Query

```typescript
import { useGetAssetsQuery } from '../store/api/assetApi';

const AssetList = () => {
  const { data, isLoading, isError, error } = useGetAssetsQuery({
    page: 1,
    limit: 20,
    sortBy: 'created_at',
    sortOrder: 'desc',
  });

  if (isLoading) return <div>Loading...</div>;
  if (isError) return <div>Error: {error.message}</div>;

  return (
    <div>
      {data.data.map(asset => (
        <div key={asset.id}>{asset.name}</div>
      ))}
    </div>
  );
};
```

### Mutations

```typescript
import { useCreateAssetMutation } from '../store/api/assetApi';

const CreateAssetForm = () => {
  const [createAsset, { isLoading, isError, error }] = useCreateAssetMutation();

  const handleSubmit = async (formData) => {
    try {
      await createAsset(formData).unwrap();
      // Success handling
    } catch (error) {
      // Error handling
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields */}
      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Creating...' : 'Create Asset'}
      </button>
    </form>
  );
};
```

### Conditional Queries

```typescript
const UserProfile = ({ userId }) => {
  const { data, isLoading } = useGetUserByIdQuery(userId, {
    skip: !userId, // Skip query if no userId
  });

  // Component logic
};
```

### Manual Refetching

```typescript
const AssetList = () => {
  const { data, isLoading, refetch } = useGetAssetsQuery();

  return (
    <div>
      <button onClick={() => refetch()}>Refresh</button>
      {/* List content */}
    </div>
  );
};
```

## Error Handling

### Using RTKQueryErrorHandler Component

```typescript
import RTKQueryErrorHandler from '../components/ErrorBoundary/RTKQueryErrorHandler';

const MyComponent = () => {
  const { data, isError, error } = useGetAssetsQuery();

  return (
    <div>
      {isError && (
        <RTKQueryErrorHandler
          error={error}
          title="Failed to load assets"
          showDetails={process.env.NODE_ENV === 'development'}
        />
      )}
      {/* Component content */}
    </div>
  );
};
```

## Loading States

### Using RTKQueryLoading Component

```typescript
import RTKQueryLoading from '../components/Loading/RTKQueryLoading';

const MyComponent = () => {
  const { data, isLoading, isError, isFetching } = useGetAssetsQuery();

  return (
    <RTKQueryLoading
      isLoading={isLoading}
      isError={isError}
      isFetching={isFetching}
      showFetchingIndicator={true}
      skeletonCount={6}
      skeletonHeight={200}
    >
      {/* Component content */}
    </RTKQueryLoading>
  );
};
```

## Cache Management

### Tags and Invalidation

RTK Query uses tags to manage cache invalidation:

```typescript
// In API slice
getAssets: builder.query({
  query: (params) => ({ url: '/assets', params }),
  providesTags: (result) =>
    result
      ? [
          ...result.data.map(({ id }) => ({ type: 'Asset' as const, id })),
          { type: 'Asset', id: 'LIST' },
        ]
      : [{ type: 'Asset', id: 'LIST' }],
}),

createAsset: builder.mutation({
  query: (data) => ({
    url: '/assets',
    method: 'POST',
    body: data,
  }),
  invalidatesTags: [{ type: 'Asset', id: 'LIST' }],
}),
```

### Manual Cache Updates

```typescript
const dispatch = useAppDispatch();

// Update cache manually
dispatch(
  baseApi.util.updateQueryData('getAssets', { page: 1 }, (draft) => {
    draft.data.push(newAsset);
  })
);
```

## Authentication Integration

RTK Query is integrated with the auth slice for token management:

```typescript
// In authSlice.ts
extraReducers: (builder) => {
  builder
    .addCase(authApi.endpoints.login.matchFulfilled, (state, action) => {
      state.token = action.payload.tokens.access_token;
      localStorage.setItem('access_token', action.payload.tokens.access_token);
    })
    .addCase(authApi.endpoints.logout.matchFulfilled, (state) => {
      state.token = null;
      localStorage.removeItem('access_token');
    });
},
```

## Best Practices

### 1. Use Query Parameters for Dynamic Queries

```typescript
const { data } = useGetAssetsQuery({
  page,
  limit,
  search: searchTerm,
  filters,
});
```

### 2. Handle Loading States Properly

```typescript
const { data, isLoading, isError, isFetching } = useGetAssetsQuery();

// isLoading: true for initial load
// isFetching: true for any request (including refetch)
// isError: true if the request failed
```

### 3. Use Optimistic Updates for Better UX

```typescript
const [updateAsset] = useUpdateAssetMutation();

const handleUpdate = async (id, updates) => {
  try {
    await updateAsset({ id, data: updates }).unwrap();
  } catch (error) {
    // Error handling
  }
};
```

### 4. Implement Proper Error Boundaries

```typescript
// Global error handling
const baseQuery = fetchBaseQuery({
  baseUrl: '/api/v1',
  prepareHeaders: /* ... */,
});

const baseQueryWithReauth = async (args, api, extraOptions) => {
  const result = await baseQuery(args, api, extraOptions);
  
  if (result.error && result.error.status === 401) {
    // Token expired, attempt refresh
    const refreshResult = await baseQuery('/auth/refresh', api, extraOptions);
    
    if (refreshResult.data) {
      // Retry original request
      return baseQuery(args, api, extraOptions);
    } else {
      // Redirect to login
      api.dispatch(clearAuth());
    }
  }
  
  return result;
};
```

## Testing

### Mock RTK Query in Tests

```typescript
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

// Create mock API for testing
const mockApi = createApi({
  reducerPath: 'mockApi',
  baseQuery: fetchBaseQuery({ baseUrl: '/mock' }),
  endpoints: (builder) => ({
    getAssets: builder.query({
      query: () => '/assets',
    }),
  }),
});

// Use in tests
const { useGetAssetsQuery } = mockApi;
```

## Performance Optimization

### 1. Use selectFromResult for Derived Data

```typescript
const { sortedAssets } = useGetAssetsQuery(undefined, {
  selectFromResult: ({ data, ...other }) => ({
    ...other,
    sortedAssets: data?.data.sort((a, b) => a.name.localeCompare(b.name)),
  }),
});
```

### 2. Implement Background Refetching

```typescript
const { data } = useGetAssetsQuery(undefined, {
  pollingInterval: 60000, // Refetch every minute
  refetchOnFocus: true,
  refetchOnReconnect: true,
});
```

### 3. Use Skip for Conditional Queries

```typescript
const { data } = useGetAssetByIdQuery(assetId, {
  skip: !assetId,
});
```

This guide covers the essential aspects of using RTK Query in the MAMS frontend application. For more advanced usage, refer to the official RTK Query documentation.