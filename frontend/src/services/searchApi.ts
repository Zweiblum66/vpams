import { ApiError } from '../types/api';
import { Asset, AssetFilter, AssetListResponse } from '../types/asset';
import { logger } from '../utils/logger';

export interface SearchQuery {
  query: string;
  filters?: AssetFilter;
  facets?: string[];
  highlight?: boolean;
  fuzzy?: boolean;
  page?: number;
  pageSize?: number;
}

export interface SearchFacet {
  field: string;
  values: Array<{
    value: string;
    count: number;
  }>;
}

export interface SearchSuggestion {
  text: string;
  score: number;
  type: 'asset' | 'tag' | 'metadata';
}

export interface SearchResponse extends AssetListResponse {
  facets?: SearchFacet[];
  suggestions?: SearchSuggestion[];
  queryTime?: number;
  highlights?: Record<string, string[]>;
}

export interface SavedSearch {
  id: string;
  name: string;
  query: SearchQuery;
  createdAt: string;
  updatedAt?: string;
  isDefault?: boolean;
  isShared?: boolean;
}

export interface SearchHistory {
  id: string;
  query: string;
  timestamp: string;
  resultCount: number;
  filters?: AssetFilter;
}

class SearchApi {
  private baseUrl = '/api/v1/search';

  async search(query: SearchQuery): Promise<SearchResponse> {
    try {
      const params = new URLSearchParams();
      params.append('q', query.query);
      
      if (query.page) params.append('page', query.page.toString());
      if (query.pageSize) params.append('pageSize', query.pageSize.toString());
      if (query.highlight) params.append('highlight', 'true');
      if (query.fuzzy) params.append('fuzzy', 'true');
      
      if (query.filters) {
        Object.entries(query.filters).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            if (Array.isArray(value)) {
              value.forEach(v => params.append(`filter[${key}]`, v.toString()));
            } else {
              params.append(`filter[${key}]`, value.toString());
            }
          }
        });
      }
      
      if (query.facets) {
        query.facets.forEach(facet => params.append('facets', facet));
      }

      const response = await fetch(`${this.baseUrl}?${params}`, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new ApiError('Search failed', response.status);
      }

      const data = await response.json();
      
      logger.info('Search completed', {
        query: query.query,
        resultCount: data.total,
        queryTime: data.queryTime,
        actionType: 'search',
      });
      
      return data;
    } catch (error) {
      logger.error('Search error', {
        query: query.query,
        error,
        actionType: 'search_error',
      });
      throw error;
    }
  }

  async getSuggestions(prefix: string, limit = 10): Promise<SearchSuggestion[]> {
    try {
      const params = new URLSearchParams({
        prefix,
        limit: limit.toString(),
      });

      const response = await fetch(`${this.baseUrl}/suggestions?${params}`, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new ApiError('Failed to get suggestions', response.status);
      }

      return await response.json();
    } catch (error) {
      logger.error('Failed to get search suggestions', {
        prefix,
        error,
        actionType: 'suggestions_error',
      });
      throw error;
    }
  }

  async getSavedSearches(): Promise<SavedSearch[]> {
    try {
      const response = await fetch(`${this.baseUrl}/saved`, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new ApiError('Failed to get saved searches', response.status);
      }

      return await response.json();
    } catch (error) {
      logger.error('Failed to get saved searches', {
        error,
        actionType: 'saved_searches_error',
      });
      throw error;
    }
  }

  async saveSearch(search: Omit<SavedSearch, 'id' | 'createdAt'>): Promise<SavedSearch> {
    try {
      const response = await fetch(`${this.baseUrl}/saved`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(search),
      });

      if (!response.ok) {
        throw new ApiError('Failed to save search', response.status);
      }

      const savedSearch = await response.json();
      
      logger.info('Search saved', {
        searchName: search.name,
        searchId: savedSearch.id,
        actionType: 'save_search',
      });
      
      return savedSearch;
    } catch (error) {
      logger.error('Failed to save search', {
        searchName: search.name,
        error,
        actionType: 'save_search_error',
      });
      throw error;
    }
  }

  async deleteSavedSearch(id: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/saved/${id}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new ApiError('Failed to delete saved search', response.status);
      }
      
      logger.info('Saved search deleted', {
        searchId: id,
        actionType: 'delete_saved_search',
      });
    } catch (error) {
      logger.error('Failed to delete saved search', {
        searchId: id,
        error,
        actionType: 'delete_saved_search_error',
      });
      throw error;
    }
  }

  async getSearchHistory(limit = 20): Promise<SearchHistory[]> {
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
      });

      const response = await fetch(`${this.baseUrl}/history?${params}`, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new ApiError('Failed to get search history', response.status);
      }

      return await response.json();
    } catch (error) {
      logger.error('Failed to get search history', {
        error,
        actionType: 'search_history_error',
      });
      throw error;
    }
  }

  async clearSearchHistory(): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/history`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new ApiError('Failed to clear search history', response.status);
      }
      
      logger.info('Search history cleared', {
        actionType: 'clear_search_history',
      });
    } catch (error) {
      logger.error('Failed to clear search history', {
        error,
        actionType: 'clear_search_history_error',
      });
      throw error;
    }
  }
}

export const searchApi = new SearchApi();