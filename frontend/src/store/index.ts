import { configureStore } from '@reduxjs/toolkit';
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';
import { setupListeners } from '@reduxjs/toolkit/query';

import { baseApi } from './api/baseApi';
import authSlice from './slices/authSlice';
import userSlice from './slices/userSlice';
import roleSlice from './slices/roleSlice';
import permissionSlice from './slices/permissionSlice';
import groupSlice from './slices/groupSlice';
import inheritanceSlice from './slices/inheritanceSlice';
import uiSlice from './slices/uiSlice';
import assetSlice from './slices/assetSlice';
import searchSlice from './slices/searchSlice';
import projectSlice from './slices/projectSlice';

export const store = configureStore({
  reducer: {
    [baseApi.reducerPath]: baseApi.reducer,
    auth: authSlice,
    users: userSlice,
    roles: roleSlice,
    permissions: permissionSlice,
    groups: groupSlice,
    inheritance: inheritanceSlice,
    ui: uiSlice,
    assets: assetSlice,
    search: searchSlice,
    projects: projectSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
        ignoredActionsPaths: ['meta.arg', 'payload.timestamp'],
      },
    }).concat(baseApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// Enable automatic refetching on focus, reconnect, etc.
setupListeners(store.dispatch);