import React, { useState, useEffect, useRef } from 'react';
import {
  Paper,
  InputBase,
  IconButton,
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Popper,
  Chip,
  Tooltip,
  Divider,
  Typography,
  CircularProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  Clear as ClearIcon,
  History as HistoryIcon,
  Tag as TagIcon,
  Description as MetadataIcon,
  VideoLibrary as AssetIcon,
  FilterList as FilterIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import { useDebounce } from '../../hooks/useDebounce';
import { SearchSuggestion, SearchHistory } from '../../services/searchApi';
import { searchApi } from '../../services/searchApi';

interface SearchBarProps {
  onSearch: (query: string) => void;
  onFilterClick?: () => void;
  placeholder?: string;
  autoFocus?: boolean;
  showHistory?: boolean;
  showSuggestions?: boolean;
  showFilters?: boolean;
  searchHistory?: SearchHistory[];
  loading?: boolean;
}

const SearchBar: React.FC<SearchBarProps> = ({
  onSearch,
  onFilterClick,
  placeholder = 'Search assets...',
  autoFocus = false,
  showHistory = true,
  showSuggestions = true,
  showFilters = true,
  searchHistory = [],
  loading = false,
}) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const anchorRef = useRef<HTMLDivElement>(null);
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery && showSuggestions) {
      loadSuggestions(debouncedQuery);
    } else {
      setSuggestions([]);
    }
  }, [debouncedQuery, showSuggestions]);

  const loadSuggestions = async (searchQuery: string) => {
    try {
      setLoadingSuggestions(true);
      const results = await searchApi.getSuggestions(searchQuery);
      setSuggestions(results);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const handleSearch = (searchQuery?: string) => {
    const finalQuery = searchQuery || query;
    if (finalQuery.trim()) {
      onSearch(finalQuery);
      setShowDropdown(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
      inputRef.current?.blur();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    setShowDropdown(true);
  };

  const handleSuggestionClick = (suggestion: SearchSuggestion) => {
    setQuery(suggestion.text);
    handleSearch(suggestion.text);
  };

  const handleHistoryClick = (item: SearchHistory) => {
    setQuery(item.query);
    handleSearch(item.query);
  };

  const handleClear = () => {
    setQuery('');
    setShowDropdown(false);
    inputRef.current?.focus();
  };

  const getIconForType = (type: string) => {
    switch (type) {
      case 'tag':
        return <TagIcon fontSize="small" />;
      case 'metadata':
        return <MetadataIcon fontSize="small" />;
      case 'asset':
      default:
        return <AssetIcon fontSize="small" />;
    }
  };

  const dropdownContent = () => {
    const hasHistory = showHistory && searchHistory.length > 0 && !query;
    const hasSuggestions = suggestions.length > 0;

    if (!hasHistory && !hasSuggestions && !loadingSuggestions) {
      return null;
    }

    return (
      <Paper sx={{ mt: 1, maxHeight: 400, overflow: 'auto' }}>
        {loadingSuggestions && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}

        {hasHistory && (
          <>
            <Typography variant="caption" sx={{ px: 2, pt: 1, display: 'block', color: 'text.secondary' }}>
              Recent Searches
            </Typography>
            <List dense>
              {searchHistory.slice(0, 5).map((item) => (
                <ListItem
                  key={item.id}
                  button
                  onClick={() => handleHistoryClick(item)}
                >
                  <ListItemIcon>
                    <HistoryIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText
                    primary={item.query}
                    secondary={`${item.resultCount} results`}
                  />
                </ListItem>
              ))}
            </List>
            {hasSuggestions && <Divider />}
          </>
        )}

        {hasSuggestions && (
          <>
            <Typography variant="caption" sx={{ px: 2, pt: 1, display: 'block', color: 'text.secondary' }}>
              Suggestions
            </Typography>
            <List dense>
              {suggestions.map((suggestion, index) => (
                <ListItem
                  key={index}
                  button
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  <ListItemIcon>
                    {getIconForType(suggestion.type)}
                  </ListItemIcon>
                  <ListItemText
                    primary={suggestion.text}
                    secondary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip
                          label={suggestion.type}
                          size="small"
                          sx={{ height: 16, fontSize: '0.7rem' }}
                        />
                        <Typography variant="caption" color="text.secondary">
                          Score: {(suggestion.score * 100).toFixed(0)}%
                        </Typography>
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </>
        )}
      </Paper>
    );
  };

  return (
    <Box ref={anchorRef} sx={{ position: 'relative', width: '100%' }}>
      <Paper
        sx={{
          p: '2px 4px',
          display: 'flex',
          alignItems: 'center',
          position: 'relative',
        }}
        elevation={showDropdown ? 4 : 1}
      >
        <IconButton sx={{ p: '10px' }} aria-label="search">
          <SearchIcon />
        </IconButton>
        <InputBase
          ref={inputRef}
          sx={{ ml: 1, flex: 1 }}
          placeholder={placeholder}
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => setShowDropdown(true)}
          autoFocus={autoFocus}
        />
        {loading && (
          <CircularProgress size={20} sx={{ mr: 1 }} />
        )}
        {query && (
          <IconButton onClick={handleClear} sx={{ p: '10px' }}>
            <ClearIcon />
          </IconButton>
        )}
        {showFilters && onFilterClick && (
          <Tooltip title="Advanced Filters">
            <IconButton onClick={onFilterClick} sx={{ p: '10px' }}>
              <FilterIcon />
            </IconButton>
          </Tooltip>
        )}
      </Paper>

      <Popper
        open={showDropdown && !!dropdownContent()}
        anchorEl={anchorRef.current}
        placement="bottom-start"
        style={{ width: anchorRef.current?.offsetWidth, zIndex: 1300 }}
      >
        {dropdownContent()}
      </Popper>
    </Box>
  );
};

export default SearchBar;