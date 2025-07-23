/**
 * Settings Redux Slice
 * 
 * Manages app settings including user preferences,
 * theme, and configuration options.
 */

import {createSlice, PayloadAction} from '@reduxjs/toolkit';
import {SettingsState} from '@/types';

const initialState: SettingsState = {
  theme: 'light',
  language: 'en',
  auto_sync: true,
  cache_size_limit: 1024 * 1024 * 1024, // 1GB
  video_quality: 'auto',
  offline_mode: false,
  analytics_enabled: true,
  crash_reporting: true,
  usage_statistics: true,
  location_tracking: false,
};

const settingsSlice = createSlice({
  name: 'settings',
  initialState,
  reducers: {
    updateSetting: (state, action: PayloadAction<{key: keyof SettingsState; value: any}>) => {
      const {key, value} = action.payload;
      (state as any)[key] = value;
    },
    
    updateSettings: (state, action: PayloadAction<Partial<SettingsState>>) => {
      return {...state, ...action.payload};
    },
    
    resetSettings: () => {
      return initialState;
    },
  },
});

export const {
  updateSetting,
  updateSettings,
  resetSettings,
} = settingsSlice.actions;

export default settingsSlice.reducer;