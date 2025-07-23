import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { SearchQuery, SearchResponse, SavedSearch, CreateSavedSearchRequest } from '../../types';
import { searchService } from '../../services/searchService';

interface SearchState {
  results: SearchResponse | null;
  loading: boolean;
  error: string | null;
  currentQuery: SearchQuery | null;
  searchHistory: SearchQuery[];
  savedSearches: SavedSearch[];
  suggestions: string[];
  suggestionsLoading: boolean;
  recentSearches: string[];
  activeFilters: Record<string, any>;
  facets: any[];
}

const initialState: SearchState = {
  results: null,
  loading: false,
  error: null,
  currentQuery: null,
  searchHistory: [],
  savedSearches: [],
  suggestions: [],
  suggestionsLoading: false,
  recentSearches: JSON.parse(localStorage.getItem('mams_recent_searches') || '[]'),
  activeFilters: {},
  facets: [],
};

// Async thunks
export const performSearch = createAsyncThunk(
  'search/performSearch',
  async (query: SearchQuery) => {
    const response = await searchService.search(query);
    return { response, query };
  }
);

export const performAdvancedSearch = createAsyncThunk(
  'search/performAdvancedSearch',
  async (query: SearchQuery) => {
    const response = await searchService.advancedSearch(query);
    return { response, query };
  }
);

export const performFilteredSearch = createAsyncThunk(
  'search/performFilteredSearch',
  async (query: SearchQuery) => {
    const response = await searchService.filteredSearch(query);
    return { response, query };
  }
);

export const fetchSearchSuggestions = createAsyncThunk(
  'search/fetchSearchSuggestions',
  async (query: string) => {
    const response = await searchService.getSuggestions(query);
    return response;
  }
);

export const fetchSavedSearches = createAsyncThunk(
  'search/fetchSavedSearches',
  async () => {
    const response = await searchService.getSavedSearches();
    return response;
  }
);

export const createSavedSearch = createAsyncThunk(
  'search/createSavedSearch',
  async (data: CreateSavedSearchRequest) => {
    const response = await searchService.createSavedSearch(data);
    return response;
  }
);

export const executeSavedSearch = createAsyncThunk(
  'search/executeSavedSearch',
  async (id: string) => {
    const response = await searchService.executeSavedSearch(id);
    return response;
  }
);

export const deleteSavedSearch = createAsyncThunk(
  'search/deleteSavedSearch',
  async (id: string) => {
    await searchService.deleteSavedSearch(id);
    return id;
  }
);

const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    clearResults: (state) => {
      state.results = null;
      state.currentQuery = null;
      state.error = null;
    },
    setActiveFilters: (state, action: PayloadAction<Record<string, any>>) => {
      state.activeFilters = action.payload;
    },
    addFilter: (state, action: PayloadAction<{ field: string; value: any }>) => {
      const { field, value } = action.payload;
      state.activeFilters[field] = value;
    },
    removeFilter: (state, action: PayloadAction<string>) => {
      const field = action.payload;
      delete state.activeFilters[field];
    },
    clearFilters: (state) => {
      state.activeFilters = {};
    },
    addToRecentSearches: (state, action: PayloadAction<string>) => {
      const query = action.payload;
      if (query.trim() === '') return;
      
      // Remove if already exists
      state.recentSearches = state.recentSearches.filter(q => q !== query);
      
      // Add to beginning
      state.recentSearches.unshift(query);
      
      // Keep only last 10
      state.recentSearches = state.recentSearches.slice(0, 10);
      
      // Save to localStorage
      localStorage.setItem('mams_recent_searches', JSON.stringify(state.recentSearches));
    },
    clearRecentSearches: (state) => {
      state.recentSearches = [];
      localStorage.removeItem('mams_recent_searches');
    },
    clearSuggestions: (state) => {
      state.suggestions = [];
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Perform search
      .addCase(performSearch.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(performSearch.fulfilled, (state, action) => {
        state.loading = false;
        state.results = action.payload.response;
        state.currentQuery = action.payload.query;
        state.searchHistory.unshift(action.payload.query);
        state.searchHistory = state.searchHistory.slice(0, 50); // Keep last 50 searches
      })
      .addCase(performSearch.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Search failed';
      })
      
      // Perform advanced search
      .addCase(performAdvancedSearch.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(performAdvancedSearch.fulfilled, (state, action) => {
        state.loading = false;
        state.results = action.payload.response;
        state.currentQuery = action.payload.query;
        state.searchHistory.unshift(action.payload.query);
        state.searchHistory = state.searchHistory.slice(0, 50);
      })
      .addCase(performAdvancedSearch.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Advanced search failed';
      })
      
      // Perform filtered search
      .addCase(performFilteredSearch.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(performFilteredSearch.fulfilled, (state, action) => {
        state.loading = false;
        state.results = action.payload.response;
        state.currentQuery = action.payload.query;
        state.facets = action.payload.response.facets || [];
        state.searchHistory.unshift(action.payload.query);
        state.searchHistory = state.searchHistory.slice(0, 50);
      })
      .addCase(performFilteredSearch.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Filtered search failed';
      })
      
      // Fetch suggestions
      .addCase(fetchSearchSuggestions.pending, (state) => {
        state.suggestionsLoading = true;
      })
      .addCase(fetchSearchSuggestions.fulfilled, (state, action) => {
        state.suggestionsLoading = false;
        state.suggestions = action.payload.suggestions.map((s: any) => s.text);
      })
      .addCase(fetchSearchSuggestions.rejected, (state, action) => {
        state.suggestionsLoading = false;
        state.suggestions = [];
      })
      
      // Fetch saved searches
      .addCase(fetchSavedSearches.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchSavedSearches.fulfilled, (state, action) => {
        state.loading = false;
        state.savedSearches = action.payload.data;
      })
      .addCase(fetchSavedSearches.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch saved searches';
      })
      
      // Create saved search
      .addCase(createSavedSearch.pending, (state) => {
        state.loading = true;
      })
      .addCase(createSavedSearch.fulfilled, (state, action) => {
        state.loading = false;
        state.savedSearches.unshift(action.payload);
      })
      .addCase(createSavedSearch.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to create saved search';
      })
      
      // Execute saved search
      .addCase(executeSavedSearch.pending, (state) => {
        state.loading = true;
      })
      .addCase(executeSavedSearch.fulfilled, (state, action) => {
        state.loading = false;
        state.results = action.payload;
      })
      .addCase(executeSavedSearch.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to execute saved search';
      })
      
      // Delete saved search
      .addCase(deleteSavedSearch.pending, (state) => {
        state.loading = true;
      })
      .addCase(deleteSavedSearch.fulfilled, (state, action) => {
        state.loading = false;
        state.savedSearches = state.savedSearches.filter(s => s.id !== action.payload);
      })
      .addCase(deleteSavedSearch.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to delete saved search';
      });
  },
});

export const {
  clearResults,
  setActiveFilters,
  addFilter,
  removeFilter,
  clearFilters,
  addToRecentSearches,
  clearRecentSearches,
  clearSuggestions,
  clearError,
} = searchSlice.actions;

export default searchSlice.reducer;