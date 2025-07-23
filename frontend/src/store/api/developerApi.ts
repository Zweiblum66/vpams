import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export interface DeveloperDashboard {
  developer_info: {
    id: string;
    company_name?: string;
    website?: string;
    support_email?: string;
    verified: boolean;
    created_at: string;
  };
  plugin_stats: {
    total_plugins: number;
    active_plugins: number;
    total_downloads: number;
    total_executions: number;
    avg_execution_time: number;
    success_rate: number;
  };
  recent_reviews: Array<{
    plugin_id: string;
    rating: number;
    comment: string;
    created_at: string;
  }>;
  plugins: Array<{
    id: string;
    name: string;
    version: string;
    status: string;
    downloads: number;
    rating: number;
    last_updated: string;
  }>;
}

export interface PluginTemplate {
  id: string;
  name: string;
  description: string;
  plugin_type: string;
  files: Record<string, string>;
}

export interface PluginAnalytics {
  period: {
    start_date: string;
    end_date: string;
  };
  overview: {
    total_plugins: number;
    total_downloads: number;
    avg_rating: number;
    total_reviews: number;
    positive_review_rate: number;
  };
  daily_analytics: Array<{
    date: string;
    executions: number;
    avg_execution_time: number;
    success_rate: number;
  }>;
  plugin_breakdown: Array<{
    id: string;
    name: string;
    downloads: number;
    rating: number;
    status: string;
  }>;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  suggestions: string[];
}

export interface DeveloperPlugin {
  id: string;
  name: string;
  version: string;
  description: string;
  plugin_type: string;
  status: string;
  download_count: number;
  rating: number;
  created_at: string;
  updated_at: string;
  marketplace_status: string;
  metadata: Record<string, any>;
}

export const developerApi = createApi({
  reducerPath: 'developerApi',
  baseQuery: fetchBaseQuery({
    baseUrl: '/api/v1/developer/portal',
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as any).auth.token;
      if (token) {
        headers.set('authorization', `Bearer ${token}`);
      }
      return headers;
    },
  }),
  tagTypes: ['DeveloperDashboard', 'DeveloperPlugin', 'PluginTemplate', 'PluginAnalytics'],
  endpoints: (builder) => ({
    // Dashboard
    getDeveloperDashboard: builder.query<DeveloperDashboard, void>({
      query: () => 'dashboard',
      providesTags: ['DeveloperDashboard'],
    }),

    // Plugins Management
    getDeveloperPlugins: builder.query<DeveloperPlugin[], void>({
      query: () => 'plugins',
      providesTags: ['DeveloperPlugin'],
    }),

    createPluginDraft: builder.mutation<
      { message: string; plugin_id: string },
      { plugin_data: Record<string, any> }
    >({
      query: ({ plugin_data }) => ({
        url: 'plugins',
        method: 'POST',
        body: plugin_data,
      }),
      invalidatesTags: ['DeveloperPlugin', 'DeveloperDashboard'],
    }),

    updatePluginDraft: builder.mutation<
      { message: string },
      { pluginId: string; plugin_data: Record<string, any> }
    >({
      query: ({ pluginId, plugin_data }) => ({
        url: `plugins/${pluginId}`,
        method: 'PUT',
        body: plugin_data,
      }),
      invalidatesTags: ['DeveloperPlugin', 'DeveloperDashboard'],
    }),

    publishPlugin: builder.mutation<
      { message: string; status: string },
      { plugin_id: string }
    >({
      query: ({ plugin_id }) => ({
        url: 'publish',
        method: 'POST',
        body: { plugin_id },
      }),
      invalidatesTags: ['DeveloperPlugin', 'DeveloperDashboard'],
    }),

    // Analytics
    getPluginAnalytics: builder.query<
      PluginAnalytics,
      { plugin_id?: string; days?: number }
    >({
      query: ({ plugin_id, days = 30 }) => {
        const params = new URLSearchParams();
        if (plugin_id) params.append('plugin_id', plugin_id);
        params.append('days', days.toString());
        return `analytics?${params.toString()}`;
      },
      providesTags: ['PluginAnalytics'],
    }),

    // Templates
    getPluginTemplates: builder.query<PluginTemplate[], void>({
      query: () => 'templates',
      providesTags: ['PluginTemplate'],
    }),

    // Validation
    validatePluginCode: builder.mutation<
      ValidationResult,
      { plugin_code: Record<string, string> }
    >({
      query: ({ plugin_code }) => ({
        url: 'validate',
        method: 'POST',
        body: plugin_code,
      }),
    }),

    // Documentation
    getDeveloperDocumentation: builder.query<Record<string, any>, void>({
      query: () => 'documentation',
    }),

    // Developer Account Management
    registerDeveloper: builder.mutation<
      any,
      {
        company_name?: string;
        website?: string;
        support_email?: string;
      }
    >({
      query: (data) => ({
        url: '/api/v1/developer/register',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: ['DeveloperDashboard'],
    }),

    getDeveloperAccount: builder.query<any, void>({
      query: () => '/api/v1/developer/account',
    }),

    // Webhooks
    createWebhook: builder.mutation<
      any,
      {
        plugin_id: string;
        event_types: string[];
        url: string;
      }
    >({
      query: (data) => ({
        url: '/api/v1/webhooks',
        method: 'POST',
        body: data,
      }),
    }),

    getWebhooks: builder.query<any[], { plugin_id?: string }>({
      query: ({ plugin_id }) => {
        const params = plugin_id ? `?plugin_id=${plugin_id}` : '';
        return `/api/v1/webhooks${params}`;
      },
    }),

    deleteWebhook: builder.mutation<{ message: string }, { webhook_id: string }>({
      query: ({ webhook_id }) => ({
        url: `/api/v1/webhooks/${webhook_id}`,
        method: 'DELETE',
      }),
    }),
  }),
});

export const {
  useGetDeveloperDashboardQuery,
  useGetDeveloperPluginsQuery,
  useCreatePluginDraftMutation,
  useUpdatePluginDraftMutation,
  usePublishPluginMutation,
  useGetPluginAnalyticsQuery,
  useGetPluginTemplatesQuery,
  useValidatePluginCodeMutation,
  useGetDeveloperDocumentationQuery,
  useRegisterDeveloperMutation,
  useGetDeveloperAccountQuery,
  useCreateWebhookMutation,
  useGetWebhooksQuery,
  useDeleteWebhookMutation,
} = developerApi;