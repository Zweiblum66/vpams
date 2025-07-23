"""
Tenant Management API slice using RTK Query.

Handles all tenant-related API operations including:
- Tenant CRUD operations
- Domain management
- Configuration management
- Usage tracking
"""

import { createApi } from '@reduxjs/toolkit/query/react';
import { baseQuery } from './baseApi';

// Types
export interface Tenant {
  tenant_id: string;
  name: string;
  subdomain: string;
  status: 'pending' | 'active' | 'suspended' | 'deleted';
  plan: 'free' | 'starter' | 'standard' | 'professional' | 'enterprise';
  created_at: string;
  admin_email: string;
  metadata?: Record<string, any>;
}

export interface TenantCreate {
  name: string;
  subdomain: string;
  admin_email: string;
  plan?: string;
  metadata?: Record<string, any>;
}

export interface TenantUpdate {
  name?: string;
  metadata?: Record<string, any>;
}

export interface DomainInfo {
  domain: string;
  subdomain?: string;
  is_verified: boolean;
  verification_token?: string;
  ssl_enabled: boolean;
  ssl_certificate_id?: string;
  created_at: string;
  verified_at?: string;
  dns_records: Array<{
    type: string;
    name: string;
    value: string;
    ttl: number;
    purpose: string;
  }>;
}

export interface TenantConfig {
  tenant_id: string;
  branding: {
    logo_url?: string;
    favicon_url?: string;
    primary_color: string;
    secondary_color: string;
    font_family: string;
    custom_css?: string;
  };
  features: {
    ai_enabled: boolean;
    workflow_automation: boolean;
    advanced_search: boolean;
    custom_metadata: boolean;
    api_access: boolean;
    mobile_app: boolean;
    collaboration: boolean;
    version_control: boolean;
    audit_logging: boolean;
    custom_reports: boolean;
  };
  integrations: {
    slack_enabled: boolean;
    teams_enabled: boolean;
    ldap_enabled: boolean;
    sso_enabled: boolean;
    webhook_enabled: boolean;
    api_rate_limit: number;
    allowed_domains: string[];
  };
  security: {
    password_policy: Record<string, any>;
    session_timeout_minutes: number;
    mfa_required: boolean;
    ip_whitelist: string[];
    allowed_countries: string[];
    max_login_attempts: number;
  };
  notifications: {
    email_enabled: boolean;
    slack_enabled: boolean;
    teams_enabled: boolean;
    webhook_enabled: boolean;
    notification_preferences: Record<string, string[]>;
  };
  workflows: {
    auto_tagging: boolean;
    auto_transcription: boolean;
    approval_required: boolean;
    default_workflow: string;
    custom_workflows: Record<string, any>;
  };
  version: number;
  created_at: string;
  updated_at: string;
}

export interface TenantUsage {
  tenant_id: string;
  period_start: string;
  period_end: string;
  storage_gb: number;
  bandwidth_gb: number;
  api_calls: number;
  active_users: number;
  asset_count: number;
  cost_estimate?: number;
}

export interface ConfigTemplate {
  name: string;
  description: string;
  category: string;
  is_default: boolean;
  tags: string[];
}

// API slice
export const tenantApi = createApi({
  reducerPath: 'tenantApi',
  baseQuery,
  tagTypes: ['Tenant', 'Domain', 'Config', 'Usage', 'Template'],
  endpoints: (builder) => ({
    // Tenant Management
    getTenants: builder.query<Tenant[], { skip?: number; limit?: number; status?: string }>({
      query: ({ skip = 0, limit = 100, status }) => ({
        url: '/api/v1/tenants',
        params: { skip, limit, status },
      }),
      providesTags: ['Tenant'],
    }),

    getTenant: builder.query<Tenant, string>({
      query: (tenantId) => `/api/v1/tenants/${tenantId}`,
      providesTags: (_result, _error, tenantId) => [{ type: 'Tenant', id: tenantId }],
    }),

    createTenant: builder.mutation<Tenant, TenantCreate>({
      query: (tenant) => ({
        url: '/api/v1/tenants',
        method: 'POST',
        body: tenant,
      }),
      invalidatesTags: ['Tenant'],
    }),

    updateTenant: builder.mutation<Tenant, { tenantId: string; update: TenantUpdate }>({
      query: ({ tenantId, update }) => ({
        url: `/api/v1/tenants/${tenantId}`,
        method: 'PUT',
        body: update,
      }),
      invalidatesTags: (_result, _error, { tenantId }) => [
        { type: 'Tenant', id: tenantId },
        'Tenant',
      ],
    }),

    deleteTenant: builder.mutation<void, string>({
      query: (tenantId) => ({
        url: `/api/v1/tenants/${tenantId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Tenant'],
    }),

    // Domain Management
    getTenantDomains: builder.query<DomainInfo[], string>({
      query: (tenantId) => `/api/v1/tenants/${tenantId}/domains`,
      providesTags: (_result, _error, tenantId) => [{ type: 'Domain', id: tenantId }],
    }),

    addDomain: builder.mutation<DomainInfo, { tenantId: string; domain: string; auto_verify?: boolean; auto_ssl?: boolean }>({
      query: ({ tenantId, ...body }) => ({
        url: `/api/v1/tenants/${tenantId}/domains`,
        method: 'POST',
        body,
      }),
      invalidatesTags: (_result, _error, { tenantId }) => [{ type: 'Domain', id: tenantId }],
    }),

    verifyDomain: builder.mutation<{ verified: boolean; message: string }, { tenantId: string; domain: string; method?: string }>({
      query: ({ tenantId, domain, method = 'dns' }) => ({
        url: `/api/v1/tenants/${tenantId}/domains/${domain}/verify`,
        method: 'POST',
        params: { method },
      }),
      invalidatesTags: (_result, _error, { tenantId }) => [{ type: 'Domain', id: tenantId }],
    }),

    removeDomain: builder.mutation<void, { tenantId: string; domain: string }>({
      query: ({ tenantId, domain }) => ({
        url: `/api/v1/tenants/${tenantId}/domains/${domain}`,
        method: 'DELETE',
      }),
      invalidatesTags: (_result, _error, { tenantId }) => [{ type: 'Domain', id: tenantId }],
    }),

    // Configuration Management
    getTenantConfig: builder.query<TenantConfig, string>({
      query: (tenantId) => `/api/v1/tenants/${tenantId}/config`,
      providesTags: (_result, _error, tenantId) => [{ type: 'Config', id: tenantId }],
    }),

    updateTenantConfig: builder.mutation<TenantConfig, { tenantId: string; config: Partial<TenantConfig> }>({
      query: ({ tenantId, config }) => ({
        url: `/api/v1/tenants/${tenantId}/config`,
        method: 'PUT',
        body: config,
      }),
      invalidatesTags: (_result, _error, { tenantId }) => [{ type: 'Config', id: tenantId }],
    }),

    getConfigTemplates: builder.query<ConfigTemplate[], string | undefined>({
      query: (category) => ({
        url: '/api/v1/config/templates',
        params: category ? { category } : undefined,
      }),
      providesTags: ['Template'],
    }),

    applyConfigTemplate: builder.mutation<TenantConfig, { tenantId: string; templateName: string; merge?: boolean }>({
      query: ({ tenantId, templateName, merge = true }) => ({
        url: `/api/v1/tenants/${tenantId}/config/apply-template`,
        method: 'POST',
        params: { template_name: templateName, merge },
      }),
      invalidatesTags: (_result, _error, { tenantId }) => [{ type: 'Config', id: tenantId }],
    }),

    rollbackConfig: builder.mutation<TenantConfig, { tenantId: string; version?: number }>({
      query: ({ tenantId, version }) => ({
        url: `/api/v1/tenants/${tenantId}/config/rollback`,
        method: 'POST',
        params: version ? { version } : undefined,
      }),
      invalidatesTags: (_result, _error, { tenantId }) => [{ type: 'Config', id: tenantId }],
    }),

    getConfigDiff: builder.query<Record<string, any>, { tenantId: string; version1?: number; version2?: number }>({
      query: ({ tenantId, version1, version2 }) => ({
        url: `/api/v1/tenants/${tenantId}/config/diff`,
        params: { version1, version2 },
      }),
    }),

    exportConfig: builder.mutation<Record<string, any>, string>({
      query: (tenantId) => ({
        url: `/api/v1/tenants/${tenantId}/config/export`,
        method: 'POST',
      }),
    }),

    importConfig: builder.mutation<TenantConfig, { tenantId: string; config: Record<string, any> }>({
      query: ({ tenantId, config }) => ({
        url: `/api/v1/tenants/${tenantId}/config/import`,
        method: 'POST',
        body: config,
      }),
      invalidatesTags: (_result, _error, { tenantId }) => [{ type: 'Config', id: tenantId }],
    }),

    // Usage and Analytics
    getTenantUsage: builder.query<TenantUsage, { tenantId: string; startDate?: string; endDate?: string }>({
      query: ({ tenantId, startDate, endDate }) => ({
        url: `/api/v1/tenants/${tenantId}/usage`,
        params: { start_date: startDate, end_date: endDate },
      }),
      providesTags: (_result, _error, { tenantId }) => [{ type: 'Usage', id: tenantId }],
    }),
  }),
});

// Export hooks
export const {
  // Tenant Management
  useGetTenantsQuery,
  useGetTenantQuery,
  useCreateTenantMutation,
  useUpdateTenantMutation,
  useDeleteTenantMutation,
  
  // Domain Management
  useGetTenantDomainsQuery,
  useAddDomainMutation,
  useVerifyDomainMutation,
  useRemoveDomainMutation,
  
  // Configuration Management
  useGetTenantConfigQuery,
  useUpdateTenantConfigMutation,
  useGetConfigTemplatesQuery,
  useApplyConfigTemplateMutation,
  useRollbackConfigMutation,
  useGetConfigDiffQuery,
  useExportConfigMutation,
  useImportConfigMutation,
  
  // Usage and Analytics
  useGetTenantUsageQuery,
} = tenantApi;