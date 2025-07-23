import { baseApi } from './baseApi';
import { SearchQuery, SearchResponse, SavedSearch, CreateSavedSearchRequest, PaginatedResponse } from '../../types';

export const searchApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    performSearch: builder.mutation<SearchResponse, SearchQuery>({
      query: (query) => ({
        url: '/search',
        method: 'POST',
        body: query,
      }),
    }),

    performAdvancedSearch: builder.mutation<SearchResponse, SearchQuery>({
      query: (query) => ({
        url: '/search/advanced',
        method: 'POST',
        body: query,
      }),
    }),

    performFilteredSearch: builder.mutation<SearchResponse, SearchQuery>({
      query: (query) => ({
        url: '/search/filtered',
        method: 'POST',
        body: query,
      }),
    }),

    performSemanticSearch: builder.mutation<SearchResponse, SearchQuery>({
      query: (query) => ({
        url: '/search/semantic',
        method: 'POST',
        body: query,
      }),
    }),

    performVisualSearch: builder.mutation<SearchResponse, { image: File; threshold?: number }>({
      query: ({ image, threshold }) => {
        const formData = new FormData();
        formData.append('image', image);
        if (threshold) {
          formData.append('threshold', threshold.toString());
        }

        return {
          url: '/search/visual',
          method: 'POST',
          body: formData,
        };
      },
    }),

    getSearchSuggestions: builder.query<{ suggestions: Array<{ text: string; score: number }> }, string>({
      query: (query) => ({
        url: `/search/suggestions?q=${encodeURIComponent(query)}`,
        method: 'GET',
      }),
    }),

    getSearchHistory: builder.query<SearchQuery[], void>({
      query: () => ({
        url: '/search/history',
        method: 'GET',
      }),
      providesTags: [{ type: 'Search', id: 'HISTORY' }],
    }),

    clearSearchHistory: builder.mutation<void, void>({
      query: () => ({
        url: '/search/history',
        method: 'DELETE',
      }),
      invalidatesTags: [{ type: 'Search', id: 'HISTORY' }],
    }),

    getSavedSearches: builder.query<PaginatedResponse<SavedSearch>, void>({
      query: () => ({
        url: '/search/saved',
        method: 'GET',
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.data.map(({ id }) => ({ type: 'SavedSearch' as const, id })),
              { type: 'SavedSearch', id: 'LIST' },
            ]
          : [{ type: 'SavedSearch', id: 'LIST' }],
    }),

    createSavedSearch: builder.mutation<SavedSearch, CreateSavedSearchRequest>({
      query: (data) => ({
        url: '/search/saved',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'SavedSearch', id: 'LIST' }],
    }),

    updateSavedSearch: builder.mutation<SavedSearch, { id: string; data: Partial<CreateSavedSearchRequest> }>({
      query: ({ id, data }) => ({
        url: `/search/saved/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'SavedSearch', id },
        { type: 'SavedSearch', id: 'LIST' },
      ],
    }),

    deleteSavedSearch: builder.mutation<void, string>({
      query: (id) => ({
        url: `/search/saved/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'SavedSearch', id },
        { type: 'SavedSearch', id: 'LIST' },
      ],
    }),

    executeSavedSearch: builder.mutation<SearchResponse, string>({
      query: (id) => ({
        url: `/search/saved/${id}/execute`,
        method: 'POST',
      }),
    }),

    getSearchAnalytics: builder.query<any, {
      start_date?: string;
      end_date?: string;
      user_id?: string;
    }>({
      query: (params = {}) => {
        const searchParams = new URLSearchParams();
        
        if (params.start_date) searchParams.append('start_date', params.start_date);
        if (params.end_date) searchParams.append('end_date', params.end_date);
        if (params.user_id) searchParams.append('user_id', params.user_id);

        return {
          url: `/search/analytics?${searchParams}`,
          method: 'GET',
        };
      },
      providesTags: [{ type: 'Search', id: 'ANALYTICS' }],
    }),

    getPopularSearches: builder.query<Array<{ query: string; count: number }>, number>({
      query: (limit = 10) => ({
        url: `/search/popular?limit=${limit}`,
        method: 'GET',
      }),
      providesTags: [{ type: 'Search', id: 'POPULAR' }],
    }),

    getFacets: builder.query<any, string[] | undefined>({
      query: (indices) => ({
        url: `/search/facets${indices ? `?indices=${indices.join(',')}` : ''}`,
        method: 'GET',
      }),
      providesTags: [{ type: 'Search', id: 'FACETS' }],
    }),
  }),
});

export const {
  usePerformSearchMutation,
  usePerformAdvancedSearchMutation,
  usePerformFilteredSearchMutation,
  usePerformSemanticSearchMutation,
  usePerformVisualSearchMutation,
  useGetSearchSuggestionsQuery,
  useGetSearchHistoryQuery,
  useClearSearchHistoryMutation,
  useGetSavedSearchesQuery,
  useCreateSavedSearchMutation,
  useUpdateSavedSearchMutation,
  useDeleteSavedSearchMutation,
  useExecuteSavedSearchMutation,
  useGetSearchAnalyticsQuery,
  useGetPopularSearchesQuery,
  useGetFacetsQuery,
} = searchApi;