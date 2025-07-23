import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export interface MarketplacePlugin {
  id: string;
  name: string;
  description: string;
  version: string;
  author: string;
  rating: number;
  download_count: number;
  category: string;
  plugin_type: string;
  price: number;
  screenshots: string[];
  tags: string[];
  created_at: string;
  updated_at?: string;
  featured: boolean;
}

export interface PluginCategory {
  id: string;
  name: string;
  description: string;
  icon: string;
  plugin_count: number;
}

export interface PluginDetails {
  id: string;
  name: string;
  description: string;
  long_description: string;
  version: string;
  author: string;
  author_verified: boolean;
  rating: number;
  download_count: number;
  category: string;
  plugin_type: string;
  price: number;
  screenshots: string[];
  tags: string[];
  requirements: Record<string, any>;
  changelog: Array<{
    version: string;
    changes: string[];
    date: string;
  }>;
  documentation_url?: string;
  support_url?: string;
  source_url?: string;
  license: string;
  created_at: string;
  updated_at: string;
  is_installed: boolean;
  installation_status?: string;
  reviews: Array<{
    id: string;
    rating: number;
    title: string;
    comment: string;
    author: string;
    created_at: string;
    helpful_count: number;
  }>;
  rating_distribution: Record<string, number>;
  total_reviews: number;
}

export interface MarketplaceStats {
  total_plugins: number;
  total_downloads: number;
  average_rating: number;
  total_categories: number;
  recent_plugins: number;
  marketplace_health: {
    active_plugins: number;
    avg_rating: number;
    growth_rate: string;
  };
}

export interface InstalledPlugin {
  installation_id: string;
  plugin_id: string;
  name: string;
  description: string;
  version: string;
  plugin_type: string;
  status: string;
  installed_at: string;
  last_used?: string;
  config: Record<string, any>;
  error_message?: string;
}

export interface SearchParams {
  query?: string;
  category?: string;
  plugin_type?: string;
  min_rating?: number;
  max_price?: number;
  free_only?: boolean;
  sort_by?: 'relevance' | 'rating' | 'downloads' | 'newest' | 'oldest' | 'price';
  page?: number;
  limit?: number;
}

export interface ReviewRequest {
  rating: number;
  title: string;
  comment: string;
}

export const marketplaceApi = createApi({
  reducerPath: 'marketplaceApi',
  baseQuery: fetchBaseQuery({
    baseUrl: '/api/v1/marketplace',
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as any).auth.token;
      if (token) {
        headers.set('authorization', `Bearer ${token}`);
      }
      return headers;
    },
  }),
  tagTypes: ['MarketplacePlugin', 'PluginCategory', 'InstalledPlugin', 'PluginDetails'],
  endpoints: (builder) => ({
    // Featured plugins
    getFeaturedPlugins: builder.query<MarketplacePlugin[], { limit?: number }>({
      query: ({ limit = 10 } = {}) => `featured?limit=${limit}`,
      providesTags: ['MarketplacePlugin'],
    }),

    // Popular plugins
    getPopularPlugins: builder.query<MarketplacePlugin[], { limit?: number; days?: number }>({
      query: ({ limit = 10, days = 30 } = {}) => `popular?limit=${limit}&days=${days}`,
      providesTags: ['MarketplacePlugin'],
    }),

    // Search plugins
    searchMarketplacePlugins: builder.query<MarketplacePlugin[], SearchParams>({
      query: (params) => {
        const searchParams = new URLSearchParams();
        
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            searchParams.append(key, value.toString());
          }
        });
        
        return `search?${searchParams.toString()}`;
      },
      providesTags: ['MarketplacePlugin'],
    }),

    // Get plugin categories
    getPluginCategories: builder.query<PluginCategory[], void>({
      query: () => 'categories',
      providesTags: ['PluginCategory'],
    }),

    // Get plugin details
    getPluginDetails: builder.query<PluginDetails, string>({
      query: (pluginId) => pluginId,
      providesTags: (result, error, pluginId) => [
        { type: 'PluginDetails', id: pluginId }
      ],
    }),

    // Install plugin
    installPluginFromMarketplace: builder.mutation<
      { message: string; installation_id: string },
      { plugin_id: string; config?: Record<string, any> }
    >({
      query: ({ plugin_id, config }) => ({
        url: `${plugin_id}/install`,
        method: 'POST',
        body: config ? { config } : undefined,
      }),
      invalidatesTags: ['InstalledPlugin', 'MarketplacePlugin'],
    }),

    // Uninstall plugin
    uninstallPluginFromMarketplace: builder.mutation<
      { message: string },
      { plugin_id: string }
    >({
      query: ({ plugin_id }) => ({
        url: `${plugin_id}/install`,
        method: 'DELETE',
      }),
      invalidatesTags: ['InstalledPlugin', 'MarketplacePlugin'],
    }),

    // Add plugin review
    addPluginReview: builder.mutation<
      { message: string },
      { plugin_id: string; review: ReviewRequest }
    >({
      query: ({ plugin_id, review }) => ({
        url: `${plugin_id}/reviews`,
        method: 'POST',
        body: review,
      }),
      invalidatesTags: (result, error, { plugin_id }) => [
        { type: 'PluginDetails', id: plugin_id },
        'MarketplacePlugin'
      ],
    }),

    // Get installed plugins
    getMyInstalledPlugins: builder.query<InstalledPlugin[], void>({
      query: () => 'my/installed',
      providesTags: ['InstalledPlugin'],
    }),

    // Get marketplace statistics
    getMarketplaceStats: builder.query<MarketplaceStats, void>({
      query: () => 'stats',
    }),

    // Browse by category
    getPluginsByCategory: builder.query<
      MarketplacePlugin[],
      { category: string; limit?: number; page?: number }
    >({
      query: ({ category, limit = 20, page = 1 }) =>
        `search?category=${encodeURIComponent(category)}&limit=${limit}&page=${page}`,
      providesTags: ['MarketplacePlugin'],
    }),

    // Get trending plugins
    getTrendingPlugins: builder.query<MarketplacePlugin[], { limit?: number }>({
      query: ({ limit = 8 } = {}) => `popular?limit=${limit}&days=7`,
      providesTags: ['MarketplacePlugin'],
    }),

    // Get recently added plugins
    getRecentPlugins: builder.query<MarketplacePlugin[], { limit?: number }>({
      query: ({ limit = 8 } = {}) => `search?sort_by=newest&limit=${limit}`,
      providesTags: ['MarketplacePlugin'],
    }),

    // Get plugin recommendations (based on installed plugins)
    getRecommendedPlugins: builder.query<MarketplacePlugin[], { limit?: number }>({
      query: ({ limit = 6 } = {}) => `search?sort_by=rating&limit=${limit}`,
      providesTags: ['MarketplacePlugin'],
    }),
  }),
});

export const {
  useGetFeaturedPluginsQuery,
  useGetPopularPluginsQuery,
  useSearchMarketplacePluginsQuery,
  useGetPluginCategoriesQuery,
  useGetPluginDetailsQuery,
  useInstallPluginFromMarketplaceMutation,
  useUninstallPluginFromMarketplaceMutation,
  useAddPluginReviewMutation,
  useGetMyInstalledPluginsQuery,
  useGetMarketplaceStatsQuery,
  useGetPluginsByCategoryQuery,
  useGetTrendingPluginsQuery,
  useGetRecentPluginsQuery,
  useGetRecommendedPluginsQuery,
} = marketplaceApi;