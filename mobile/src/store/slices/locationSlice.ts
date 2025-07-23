/**
 * Location Redux Slice
 * 
 * Manages location state, saved locations,
 * and location tagging preferences.
 */

import {createSlice, createAsyncThunk, PayloadAction} from '@reduxjs/toolkit';
import {locationService, LocationData, LocationTag, LocationAddress} from '@/services/locationService';

export interface LocationState {
  currentLocation: LocationData | null;
  isTracking: boolean;
  savedLocations: LocationTag[];
  recentLocations: LocationTag[];
  isLoading: boolean;
  error: string | null;
  
  // Location settings
  settings: {
    autoTag: boolean;
    highAccuracy: boolean;
    trackingEnabled: boolean;
    saveFrequentLocations: boolean;
    nearbyRadius: number; // meters
    backgroundTracking: boolean;
  };
  
  // Permissions
  permissionsGranted: boolean;
  locationServicesEnabled: boolean;
}

const initialState: LocationState = {
  currentLocation: null,
  isTracking: false,
  savedLocations: [],
  recentLocations: [],
  isLoading: false,
  error: null,
  
  settings: {
    autoTag: true,
    highAccuracy: true,
    trackingEnabled: false,
    saveFrequentLocations: true,
    nearbyRadius: 1000,
    backgroundTracking: false,
  },
  
  permissionsGranted: false,
  locationServicesEnabled: false,
};

// Async thunks
export const initializeLocation = createAsyncThunk(
  'location/initialize',
  async (_, {dispatch}) => {
    try {
      const hasPermissions = await locationService.checkLocationPermissions();
      const servicesEnabled = await locationService.isLocationServicesEnabled();
      
      dispatch(setPermissionsGranted(hasPermissions));
      dispatch(setLocationServicesEnabled(servicesEnabled));
      
      if (hasPermissions && servicesEnabled) {
        const location = await locationService.getCurrentLocation();
        if (location) {
          dispatch(setCurrentLocation(location));
        }
      }
      
      return {hasPermissions, servicesEnabled};
    } catch (error) {
      throw error;
    }
  }
);

export const getCurrentLocation = createAsyncThunk(
  'location/getCurrentLocation',
  async (options: {
    timeout?: number;
    maximumAge?: number;
    enableHighAccuracy?: boolean;
  } = {}) => {
    const location = await locationService.getCurrentLocation(options);
    if (!location) {
      throw new Error('Failed to get current location');
    }
    return location;
  }
);

export const createLocationTag = createAsyncThunk(
  'location/createLocationTag',
  async ({name, category}: {name?: string; category?: LocationTag['category']}) => {
    const locationTag = await locationService.createLocationTag(name, category);
    if (!locationTag) {
      throw new Error('Failed to create location tag');
    }
    return locationTag;
  }
);

export const reverseGeocode = createAsyncThunk(
  'location/reverseGeocode',
  async ({latitude, longitude}: {latitude: number; longitude: number}) => {
    const address = await locationService.getAddressFromCoordinates(latitude, longitude);
    return {coordinates: {latitude, longitude}, address};
  }
);

export const forwardGeocode = createAsyncThunk(
  'location/forwardGeocode',
  async (address: string) => {
    const coordinates = await locationService.getCoordinatesFromAddress(address);
    if (!coordinates) {
      throw new Error('Address not found');
    }
    return {address, coordinates};
  }
);

export const startLocationTracking = createAsyncThunk(
  'location/startTracking',
  async (_, {dispatch, getState}) => {
    const state = getState() as {location: LocationState};
    const {settings} = state.location;
    
    const success = locationService.startLocationTracking(
      (location) => {
        dispatch(setCurrentLocation(location));
        
        // Auto-save frequent locations if enabled
        if (settings.saveFrequentLocations) {
          dispatch(addRecentLocation(location));
        }
      },
      {
        enableHighAccuracy: settings.highAccuracy,
        distanceFilter: 10,
        interval: 5000,
      }
    );
    
    if (!success) {
      throw new Error('Failed to start location tracking');
    }
    
    return true;
  }
);

export const stopLocationTracking = createAsyncThunk(
  'location/stopTracking',
  async () => {
    locationService.stopLocationTracking();
    return true;
  }
);

export const findNearbyLocations = createAsyncThunk(
  'location/findNearby',
  async (_, {getState}) => {
    const state = getState() as {location: LocationState};
    const {currentLocation, savedLocations, settings} = state.location;
    
    if (!currentLocation) {
      throw new Error('Current location not available');
    }
    
    const nearbyLocations = await locationService.getNearbyLocations(
      currentLocation,
      savedLocations,
      settings.nearbyRadius
    );
    
    return nearbyLocations;
  }
);

const locationSlice = createSlice({
  name: 'location',
  initialState,
  reducers: {
    setCurrentLocation: (state, action: PayloadAction<LocationData>) => {
      state.currentLocation = action.payload;
      state.error = null;
    },
    
    setPermissionsGranted: (state, action: PayloadAction<boolean>) => {
      state.permissionsGranted = action.payload;
    },
    
    setLocationServicesEnabled: (state, action: PayloadAction<boolean>) => {
      state.locationServicesEnabled = action.payload;
    },
    
    addSavedLocation: (state, action: PayloadAction<LocationTag>) => {
      const existing = state.savedLocations.find(loc => loc.id === action.payload.id);
      if (!existing) {
        state.savedLocations.push(action.payload);
      }
    },
    
    removeSavedLocation: (state, action: PayloadAction<string>) => {
      state.savedLocations = state.savedLocations.filter(loc => loc.id !== action.payload);
    },
    
    updateSavedLocation: (state, action: PayloadAction<LocationTag>) => {
      const index = state.savedLocations.findIndex(loc => loc.id === action.payload.id);
      if (index !== -1) {
        state.savedLocations[index] = action.payload;
      }
    },
    
    incrementLocationUsage: (state, action: PayloadAction<string>) => {
      const location = state.savedLocations.find(loc => loc.id === action.payload);
      if (location) {
        location.used_count += 1;
      }
    },
    
    addRecentLocation: (state, action: PayloadAction<LocationData>) => {
      const locationTag: LocationTag = {
        id: `recent_${Date.now()}`,
        coordinates: action.payload,
        address: {
          address: 'Recent location',
          formattedAddress: `${action.payload.latitude}, ${action.payload.longitude}`,
        },
        name: 'Recent Location',
        category: 'custom',
        created_at: new Date().toISOString(),
        used_count: 1,
      };
      
      // Add to recent locations (keep last 20)
      state.recentLocations.unshift(locationTag);
      if (state.recentLocations.length > 20) {
        state.recentLocations = state.recentLocations.slice(0, 20);
      }
    },
    
    clearRecentLocations: (state) => {
      state.recentLocations = [];
    },
    
    updateLocationSettings: (state, action: PayloadAction<Partial<LocationState['settings']>>) => {
      state.settings = {...state.settings, ...action.payload};
    },
    
    setTrackingStatus: (state, action: PayloadAction<boolean>) => {
      state.isTracking = action.payload;
    },
    
    clearLocationError: (state) => {
      state.error = null;
    },
    
    resetLocationState: () => initialState,
  },
  
  extraReducers: (builder) => {
    builder
      // Initialize location
      .addCase(initializeLocation.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(initializeLocation.fulfilled, (state) => {
        state.isLoading = false;
      })
      .addCase(initializeLocation.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to initialize location';
      })
      
      // Get current location
      .addCase(getCurrentLocation.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(getCurrentLocation.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentLocation = action.payload;
      })
      .addCase(getCurrentLocation.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to get current location';
      })
      
      // Create location tag
      .addCase(createLocationTag.fulfilled, (state, action) => {
        state.savedLocations.push(action.payload);
      })
      .addCase(createLocationTag.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to create location tag';
      })
      
      // Start tracking
      .addCase(startLocationTracking.fulfilled, (state) => {
        state.isTracking = true;
        state.error = null;
      })
      .addCase(startLocationTracking.rejected, (state, action) => {
        state.isTracking = false;
        state.error = action.error.message || 'Failed to start location tracking';
      })
      
      // Stop tracking
      .addCase(stopLocationTracking.fulfilled, (state) => {
        state.isTracking = false;
      });
  },
});

export const {
  setCurrentLocation,
  setPermissionsGranted,
  setLocationServicesEnabled,
  addSavedLocation,
  removeSavedLocation,
  updateSavedLocation,
  incrementLocationUsage,
  addRecentLocation,
  clearRecentLocations,
  updateLocationSettings,
  setTrackingStatus,
  clearLocationError,
  resetLocationState,
} = locationSlice.actions;

export default locationSlice.reducer;