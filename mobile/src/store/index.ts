/**
 * Redux Store Configuration
 * 
 * Configures the main Redux store with RTK, persistence,
 * and middleware for the MAMS mobile application.
 */

import {configureStore, combineReducers} from '@reduxjs/toolkit';
import {persistStore, persistReducer} from 'redux-persist';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  FLUSH,
  REHYDRATE,
  PAUSE,
  PERSIST,
  PURGE,
  REGISTER,
} from 'redux-persist';

// Import slice reducers
import authReducer from './slices/authSlice';
import assetsReducer from './slices/assetsSlice';
import projectsReducer from './slices/projectsSlice';
import uploadsReducer from './slices/uploadsSlice';
import searchReducer from './slices/searchSlice';
import settingsReducer from './slices/settingsSlice';
import offlineReducer from './slices/offlineSlice';
import notificationsReducer from './slices/notificationsSlice';
import locationReducer from './slices/locationSlice';
import voiceNoteReducer from './slices/voiceNoteSlice';
import editingReducer from './slices/editingSlice';

// Import API slice
import {apiSlice} from './api/apiSlice';

// Root reducer
const rootReducer = combineReducers({
  auth: authReducer,
  assets: assetsReducer,
  projects: projectsReducer,
  uploads: uploadsReducer,
  search: searchReducer,
  settings: settingsReducer,
  offline: offlineReducer,
  notifications: notificationsReducer,
  location: locationReducer,
  voiceNote: voiceNoteReducer,
  editing: editingReducer,
  api: apiSlice.reducer,
});

// Persist configuration
const persistConfig = {
  key: 'root',
  version: 1,
  storage: AsyncStorage,
  whitelist: [
    'auth',
    'settings',
    'assets', // Cache asset metadata
    'projects', // Cache project data
    'search', // Cache search history
    'notifications', // Cache notification preferences
    'location', // Cache location settings and saved locations
    'voiceNote', // Cache voice note settings and recordings list
  ],
  blacklist: [
    'uploads', // Don't persist upload state
    'offline', // Don't persist offline state
    'api', // Don't persist API cache
  ],
};

// Create persisted reducer
const persistedReducer = persistReducer(persistConfig, rootReducer);

// Configure store
export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
      },
    }).concat(apiSlice.middleware),
  devTools: __DEV__,
});

// Create persistor
export const persistor = persistStore(store);

// Export types
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Export typed hooks
import {useDispatch, useSelector, TypedUseSelectorHook} from 'react-redux';

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;