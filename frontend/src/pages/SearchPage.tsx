import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Box,
  Grid,
  Paper,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Pagination,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Drawer,
  IconButton,
  Tooltip,
  CircularProgress,
  Divider,
} from '@mui/material';
import {
  ViewList as ListIcon,
  ViewModule as GridIcon,
  FilterList as FilterIcon,
  Save as SaveIcon,
  History as HistoryIcon,
  Close as CloseIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';

import SearchBar from '../components/search/SearchBar';
import SearchFilters from '../components/search/SearchFilters';
import SearchResults from '../components/search/SearchResults';
import { searchApi, SearchQuery, SearchResponse, SavedSearch, SearchHistory } from '../services/searchApi';
import { Asset, AssetFilter } from '../types/asset';
import { logger } from '../utils/logger';

const SearchPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchQuery, setSearchQuery] = useState<SearchQuery>({
    query: '',
    filters: {},
    facets: ['type', 'tags', 'createdBy'],
    highlight: true,
    fuzzy: true,
    page: 1,
    pageSize: 20,
  });
  const [searchResults, setSearchResults] = useState<SearchResponse>({
    assets: [],
    total: 0,
    page: 1,
    pageSize: 20,
    totalPages: 0,
  });
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filtersDrawerOpen, setFiltersDrawerOpen] = useState(false);
  const [saveSearchDialogOpen, setSaveSearchDialogOpen] = useState(false);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [searchHistory, setSearchHistory] = useState<SearchHistory[]>([]);
  const [selectedAssets, setSelectedAssets] = useState<Set<string>>(new Set());
  const [searchName, setSearchName] = useState('');

  // Load search from URL params
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const q = params.get('q');
    if (q) {
      setSearchQuery(prev => ({ ...prev, query: q }));
    }
  }, [location]);

  // Load saved searches and history
  useEffect(() => {
    loadSavedSearches();
    loadSearchHistory();
  }, []);

  // Perform search when query changes
  useEffect(() => {
    if (searchQuery.query || Object.keys(searchQuery.filters || {}).length > 0) {
      performSearch();
    }
  }, [searchQuery]);

  const loadSavedSearches = async () => {
    try {
      const searches = await searchApi.getSavedSearches();
      setSavedSearches(searches);
    } catch (err) {
      logger.error('Failed to load saved searches', { error: err });
    }
  };

  const loadSearchHistory = async () => {
    try {
      const history = await searchApi.getSearchHistory();
      setSearchHistory(history);
    } catch (err) {
      logger.error('Failed to load search history', { error: err });
    }
  };

  const performSearch = async () => {
    try {
      setLoading(true);
      setError(null);
      const results = await searchApi.search(searchQuery);
      setSearchResults(results);
      
      // Update URL
      const params = new URLSearchParams();
      if (searchQuery.query) {
        params.set('q', searchQuery.query);
      }
      navigate(`${location.pathname}?${params.toString()}`, { replace: true });
      
      logger.info('Search performed', {
        query: searchQuery.query,
        resultCount: results.total,
        actionType: 'search_page',
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Search failed';
      setError(errorMessage);
      logger.error('Search failed', {
        query: searchQuery.query,
        error: err,
        actionType: 'search_page_error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (query: string) => {
    setSearchQuery(prev => ({
      ...prev,
      query,
      page: 1,
    }));
  };

  const handleFiltersChange = (filters: AssetFilter) => {
    setSearchQuery(prev => ({
      ...prev,
      filters,
      page: 1,
    }));
  };

  const handleClearFilters = () => {
    setSearchQuery(prev => ({
      ...prev,
      filters: {},
      page: 1,
    }));
  };

  const handlePageChange = (_: React.ChangeEvent<unknown>, page: number) => {
    setSearchQuery(prev => ({ ...prev, page }));
  };

  const handleViewModeChange = (_: React.MouseEvent<HTMLElement>, mode: 'grid' | 'list' | null) => {
    if (mode !== null) {
      setViewMode(mode);
    }
  };

  const handleAssetClick = (asset: Asset) => {
    navigate(`/assets/${asset.id}`);
  };

  const handleAssetSelect = (asset: Asset, selected: boolean) => {
    setSelectedAssets(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(asset.id);
      } else {
        newSet.delete(asset.id);
      }
      return newSet;
    });
  };

  const handleFacetClick = (field: string, value: string) => {
    const currentFilters = searchQuery.filters || {};
    const fieldValues = currentFilters[field as keyof AssetFilter] as string[] || [];
    
    if (fieldValues.includes(value)) {
      // Remove value
      const newValues = fieldValues.filter(v => v !== value);
      handleFiltersChange({
        ...currentFilters,
        [field]: newValues.length > 0 ? newValues : undefined,
      });
    } else {
      // Add value
      handleFiltersChange({
        ...currentFilters,
        [field]: [...fieldValues, value],
      });
    }
  };

  const handleSaveSearch = async () => {
    if (!searchName.trim()) return;
    
    try {
      const savedSearch = await searchApi.saveSearch({
        name: searchName,
        query: searchQuery,
      });
      setSavedSearches(prev => [...prev, savedSearch]);
      setSaveSearchDialogOpen(false);
      setSearchName('');
      
      logger.info('Search saved', {
        searchName,
        actionType: 'save_search',
      });
    } catch (err) {
      logger.error('Failed to save search', {
        searchName,
        error: err,
        actionType: 'save_search_error',
      });
    }
  };

  const handleLoadSavedSearch = (search: SavedSearch) => {
    setSearchQuery(search.query);
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Search Assets
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Search across all media assets using natural language queries and advanced filters
        </Typography>
      </Box>

      {/* Search Bar */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <SearchBar
          onSearch={handleSearch}
          onFilterClick={() => setFiltersDrawerOpen(true)}
          placeholder="Search by name, tags, metadata..."
          searchHistory={searchHistory}
          loading={loading}
        />
      </Paper>

      {/* Quick Actions */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {savedSearches.length > 0 && (
            <Button
              startIcon={<HistoryIcon />}
              variant="outlined"
              size="small"
            >
              Saved Searches ({savedSearches.length})
            </Button>
          )}
          {searchQuery.query && (
            <Button
              startIcon={<SaveIcon />}
              variant="outlined"
              size="small"
              onClick={() => setSaveSearchDialogOpen(true)}
            >
              Save Search
            </Button>
          )}
        </Box>
        
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={handleViewModeChange}
          size="small"
        >
          <ToggleButton value="grid">
            <GridIcon />
          </ToggleButton>
          <ToggleButton value="list">
            <ListIcon />
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Error Message */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Results */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <SearchResults
            results={searchResults}
            viewMode={viewMode}
            onAssetClick={handleAssetClick}
            onAssetSelect={handleAssetSelect}
            selectedAssets={selectedAssets}
            onFacetClick={handleFacetClick}
            showFacets={!filtersDrawerOpen}
          />

          {/* Pagination */}
          {searchResults.totalPages > 1 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <Pagination
                count={searchResults.totalPages}
                page={searchResults.page}
                onChange={handlePageChange}
                color="primary"
                showFirstButton
                showLastButton
              />
            </Box>
          )}
        </>
      )}

      {/* Filters Drawer */}
      <Drawer
        anchor="right"
        open={filtersDrawerOpen}
        onClose={() => setFiltersDrawerOpen(false)}
        sx={{
          '& .MuiDrawer-paper': {
            width: 400,
            maxWidth: '100%',
          },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">Filters</Typography>
            <IconButton onClick={() => setFiltersDrawerOpen(false)}>
              <CloseIcon />
            </IconButton>
          </Box>
          <SearchFilters
            filters={searchQuery.filters || {}}
            onFiltersChange={handleFiltersChange}
            onClearFilters={handleClearFilters}
            onSaveFilter={(name) => {
              setSearchName(name);
              setSaveSearchDialogOpen(true);
            }}
          />
        </Box>
      </Drawer>

      {/* Save Search Dialog */}
      <Dialog
        open={saveSearchDialogOpen}
        onClose={() => setSaveSearchDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Save Search</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Search Name"
            fullWidth
            value={searchName}
            onChange={(e) => setSearchName(e.target.value)}
            helperText="Give your search a name to easily find it later"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveSearchDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleSaveSearch}
            variant="contained"
            disabled={!searchName.trim()}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default SearchPage;