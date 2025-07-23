import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

interface IntegrationFilters {
  search?: string;
  category?: string;
  integration_type?: string;
  status?: string;
  is_featured?: boolean;
  is_free?: boolean;
  provider?: string;
  tags?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

interface Integration {
  id: string;
  name: string;
  display_name: string;
  description: string;
  short_description?: string;
  version: string;
  integration_type: string;
  category: string;
  subcategory?: string;
  provider_name: string;
  provider_website?: string;
  provider_support_url?: string;
  status: string;
  is_featured: boolean;
  is_verified: boolean;
  is_free: boolean;
  protocol?: string;
  base_url?: string;
  documentation_url?: string;
  api_reference_url?: string;
  auth_type?: string;
  setup_complexity: string;
  setup_time_minutes?: number;
  tags: string[];
  use_cases: string[];
  industries: string[];
  logo_url?: string;
  banner_url?: string;
  screenshots: string[];
  video_url?: string;
  pricing_model: string;
  pricing_details: Record<string, any>;
  rating: number;
  review_count: number;
  install_count: number;
  endpoints?: IntegrationEndpoint[];
  recent_reviews?: IntegrationReview[];
  published_at?: string;
  created_at: string;
  updated_at: string;
}

interface IntegrationEndpoint {
  id: string;
  path: string;
  method: string;
  operation_id?: string;
  summary?: string;
  description?: string;
  parameters: any[];
  request_body?: any;
  responses: Record<string, any>;
  requires_auth: boolean;
  rate_limit?: any;
  examples: any[];
  tags: string[];
  is_deprecated: boolean;
}

interface IntegrationReview {
  id: string;
  rating: number;
  title?: string;
  comment?: string;
  ease_of_use?: number;
  documentation_quality?: number;
  support_quality?: number;
  reliability?: number;
  verified_installation: boolean;
  helpful_count: number;
  created_at: string;
}

interface IntegrationCategory {
  id: string;
  name: string;
  slug: string;
  display_name: string;
  description?: string;
  parent_id?: string;
  icon?: string;
  color?: string;
  display_order: number;
  integration_count: number;
}

interface IntegrationsResponse {
  integrations: Integration[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
  filters: IntegrationFilters;
}

interface CatalogStats {
  total_integrations: number;
  by_category: Record<string, number>;
  by_type: Record<string, number>;
  by_pricing: {
    free: number;
    paid: number;
  };
  top_providers: Array<{
    name: string;
    count: number;
  }>;
}

interface InstallationRequest {
  integration_id: string;
  environment: string;
  config: Record<string, any>;
}

interface Installation {
  id: string;
  integration_id: string;
  organization_id: string;
  user_id: string;
  environment: string;
  config: Record<string, any>;
  status: string;
  health_status: string;
  last_used_at?: string;
  total_requests: number;
  error_count: number;
  installed_at: string;
  integration: {
    name: string;
    display_name: string;
    version: string;
    provider_name: string;
    logo_url?: string;
    category: string;
  };
}

const API_BASE = '/api/v1/integration-catalog';

export const useIntegrationCatalog = (filters: IntegrationFilters = {}) => {
  const queryClient = useQueryClient();
  const [searchSuggestions, setSearchSuggestions] = useState<string[]>([]);

  // Fetch integrations with filters
  const {
    data: integrations,
    isLoading: integrationsLoading,
    error: integrationsError,
    refetch: refetchIntegrations
  } = useQuery<IntegrationsResponse>({
    queryKey: ['integrations', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });

      const response = await fetch(`${API_BASE}/catalog?${params}`);
      if (!response.ok) {
        throw new Error('Failed to fetch integrations');
      }
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch categories
  const {
    data: categories,
    isLoading: categoriesLoading
  } = useQuery<IntegrationCategory[]>({
    queryKey: ['integration-categories'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/catalog/categories`);
      if (!response.ok) {
        throw new Error('Failed to fetch categories');
      }
      return response.json();
    },
    staleTime: 30 * 60 * 1000, // 30 minutes
  });

  // Fetch featured integrations
  const {
    data: featuredIntegrations,
    isLoading: featuredLoading
  } = useQuery<Integration[]>({
    queryKey: ['featured-integrations'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/catalog/featured`);
      if (!response.ok) {
        throw new Error('Failed to fetch featured integrations');
      }
      return response.json();
    },
    staleTime: 15 * 60 * 1000, // 15 minutes
  });

  // Fetch popular integrations
  const {
    data: popularIntegrations,
    isLoading: popularLoading
  } = useQuery<Integration[]>({
    queryKey: ['popular-integrations'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/catalog/popular`);
      if (!response.ok) {
        throw new Error('Failed to fetch popular integrations');
      }
      return response.json();
    },
    staleTime: 15 * 60 * 1000, // 15 minutes
  });

  // Fetch catalog statistics
  const {
    data: stats,
    isLoading: statsLoading
  } = useQuery<CatalogStats>({
    queryKey: ['catalog-stats'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/catalog/stats`);
      if (!response.ok) {
        throw new Error('Failed to fetch catalog stats');
      }
      return response.json();
    },
    staleTime: 60 * 60 * 1000, // 1 hour
  });

  // Get integration details
  const getIntegrationDetails = useCallback(async (integrationId: string): Promise<Integration> => {
    const response = await fetch(`${API_BASE}/catalog/${integrationId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch integration details');
    }
    return response.json();
  }, []);

  // Install integration mutation
  const installMutation = useMutation({
    mutationFn: async (request: InstallationRequest & { organization_id: string; user_id: string }) => {
      const params = new URLSearchParams({
        organization_id: request.organization_id,
        user_id: request.user_id
      });

      const response = await fetch(`${API_BASE}/installations?${params}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          integration_id: request.integration_id,
          environment: request.environment,
          config: request.config
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Installation failed');
      }

      return response.json();
    },
    onSuccess: () => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['integrations'] });
      queryClient.invalidateQueries({ queryKey: ['installations'] });
      queryClient.invalidateQueries({ queryKey: ['catalog-stats'] });
    },
  });

  // Fetch search suggestions
  const fetchSearchSuggestions = useCallback(async (query: string) => {
    if (query.length < 2) {
      setSearchSuggestions([]);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/catalog/search/suggestions?q=${encodeURIComponent(query)}`);
      if (response.ok) {
        const suggestions = await response.json();
        setSearchSuggestions(suggestions);
      }
    } catch (error) {
      console.error('Failed to fetch search suggestions:', error);
    }
  }, []);

  // Debounced search suggestions
  useEffect(() => {
    if (filters.search) {
      const timeoutId = setTimeout(() => {
        fetchSearchSuggestions(filters.search!);
      }, 300);

      return () => clearTimeout(timeoutId);
    } else {
      setSearchSuggestions([]);
    }
  }, [filters.search, fetchSearchSuggestions]);

  const isLoading = integrationsLoading || categoriesLoading || featuredLoading || popularLoading || statsLoading;
  const error = integrationsError;

  return {
    // Data
    integrations,
    categories,
    featuredIntegrations,
    popularIntegrations,
    stats,
    searchSuggestions,

    // Loading states
    isLoading,
    error,

    // Actions
    refetchIntegrations,
    getIntegrationDetails,
    installIntegration: (request: InstallationRequest) => {
      // TODO: Get actual organization_id and user_id from auth context
      return installMutation.mutateAsync({
        ...request,
        organization_id: 'current-org-id',
        user_id: 'current-user-id'
      });
    },
    
    // Installation state
    isInstalling: installMutation.isPending,
    installError: installMutation.error,
  };
};

// Hook for managing installations
export const useIntegrationInstallations = (organizationId: string) => {
  const queryClient = useQueryClient();

  // Fetch installations
  const {
    data: installations,
    isLoading,
    error
  } = useQuery<{
    installations: Installation[];
    pagination: any;
  }>({
    queryKey: ['installations', organizationId],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/installations?organization_id=${organizationId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch installations');
      }
      return response.json();
    },
    enabled: !!organizationId,
  });

  // Uninstall mutation
  const uninstallMutation = useMutation({
    mutationFn: async (installationId: string) => {
      const response = await fetch(
        `${API_BASE}/installations/${installationId}?organization_id=${organizationId}`,
        { method: 'DELETE' }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Uninstallation failed');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['installations'] });
      queryClient.invalidateQueries({ queryKey: ['catalog-stats'] });
    },
  });

  // Health check mutation
  const healthCheckMutation = useMutation({
    mutationFn: async (installationId: string) => {
      const response = await fetch(
        `${API_BASE}/installations/${installationId}/health-check?organization_id=${organizationId}`,
        { method: 'POST' }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Health check failed');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['installations'] });
    },
  });

  return {
    installations: installations?.installations || [],
    isLoading,
    error,
    uninstallIntegration: uninstallMutation.mutateAsync,
    performHealthCheck: healthCheckMutation.mutateAsync,
    isUninstalling: uninstallMutation.isPending,
    isPerformingHealthCheck: healthCheckMutation.isPending,
  };
};