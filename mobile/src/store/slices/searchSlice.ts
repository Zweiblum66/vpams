/**
 * Search Redux Slice
 * 
 * Manages search state including search history,
 * saved searches, and search results.
 */

import {createSlice, PayloadAction} from '@reduxjs/toolkit';
import {SearchState, SearchFilters} from '@/types';

const initialState: SearchState = {
  query: '',
  filters: {},
  results: [],
  history: [],
  savedSearches: [],
  isLoading: false,
  error: null,
};

const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    setQuery: (state, action: PayloadAction<string>) => {
      state.query = action.payload;
    },
    
    setFilters: (state, action: PayloadAction<SearchFilters>) => {
      state.filters = action.payload;
    },
    
    setResults: (state, action: PayloadAction<any[]>) => {
      state.results = action.payload;
    },
    
    addToHistory: (state, action: PayloadAction<string>) => {
      const query = action.payload;
      // Remove if already exists
      state.history = state.history.filter(h => h !== query);
      // Add to beginning
      state.history.unshift(query);
      // Keep only last 20
      state.history = state.history.slice(0, 20);
    },
    
    clearHistory: (state) => {
      state.history = [];
    },
  },
});

export const {
  setQuery,
  setFilters,
  setResults,
  addToHistory,
  clearHistory,
} = searchSlice.actions;

export default searchSlice.reducer;