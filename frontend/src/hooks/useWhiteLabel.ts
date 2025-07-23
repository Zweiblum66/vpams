import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

interface Theme {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  theme_type: string;
  is_default: boolean;
  is_active: boolean;
  primary_color?: string;
  secondary_color?: string;
  accent_color?: string;
  background_color?: string;
  text_color?: string;
  link_color?: string;
  primary_font?: string;
  secondary_font?: string;
  font_sizes?: Record<string, string>;
  font_weights?: Record<string, string | number>;
  border_radius?: string;
  spacing_unit?: string;
  grid_columns?: number;
  breakpoints?: Record<string, string>;
  button_styles?: Record<string, any>;
  card_styles?: Record<string, any>;
  navigation_styles?: Record<string, any>;
  form_styles?: Record<string, any>;
  custom_css?: string;
  css_variables?: Record<string, string>;
  component_overrides?: Record<string, any>;
  logo_url?: string;
  favicon_url?: string;
  background_image_url?: string;
  custom_images?: string[];
  supports_dark_mode: boolean;
  dark_mode_colors?: Record<string, string>;
  animation_settings?: Record<string, any>;
  transition_settings?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

interface Branding {
  id: string;
  tenant_id: string;
  theme_id?: string;
  status: string;
  company_name: string;
  company_tagline?: string;
  company_description?: string;
  company_website?: string;
  contact_email?: string;
  support_email?: string;
  phone_number?: string;
  address?: Record<string, string>;
  terms_of_service_url?: string;
  privacy_policy_url?: string;
  copyright_text?: string;
  legal_entity_name?: string;
  social_media_links?: Record<string, string>;
  platform_name?: string;
  welcome_message?: string;
  login_message?: string;
  footer_text?: string;
  feature_visibility?: Record<string, boolean>;
  navigation_menu?: Array<Record<string, any>>;
  from_email?: string;
  from_name?: string;
  reply_to_email?: string;
  email_signature?: string;
  api_documentation_title?: string;
  api_description?: string;
  api_contact_info?: Record<string, string>;
  created_at: string;
  updated_at?: string;
  activated_at?: string;
}

interface ThemeCreate {
  name: string;
  display_name?: string;
  description?: string;
  theme_type?: string;
  primary_color?: string;
  secondary_color?: string;
  accent_color?: string;
  background_color?: string;
  text_color?: string;
  link_color?: string;
  primary_font?: string;
  secondary_font?: string;
  font_sizes?: Record<string, string>;
  font_weights?: Record<string, string | number>;
  border_radius?: string;
  spacing_unit?: string;
  grid_columns?: number;
  breakpoints?: Record<string, string>;
  button_styles?: Record<string, any>;
  card_styles?: Record<string, any>;
  navigation_styles?: Record<string, any>;
  form_styles?: Record<string, any>;
  custom_css?: string;
  css_variables?: Record<string, string>;
  component_overrides?: Record<string, any>;
  logo_url?: string;
  favicon_url?: string;
  background_image_url?: string;
  custom_images?: string[];
  supports_dark_mode?: boolean;
  dark_mode_colors?: Record<string, string>;
  animation_settings?: Record<string, any>;
  transition_settings?: Record<string, any>;
}

interface ThemeUpdate extends Partial<ThemeCreate> {
  is_active?: boolean;
}

interface BrandingCreate {
  company_name: string;
  company_tagline?: string;
  company_description?: string;
  company_website?: string;
  contact_email?: string;
  support_email?: string;
  phone_number?: string;
  address?: {
    street?: string;
    city?: string;
    state?: string;
    country?: string;
    zip_code?: string;
  };
  terms_of_service_url?: string;
  privacy_policy_url?: string;
  copyright_text?: string;
  legal_entity_name?: string;
  social_media_links?: Record<string, string>;
  platform_name?: string;
  welcome_message?: string;
  login_message?: string;
  footer_text?: string;
  feature_visibility?: Record<string, boolean>;
  navigation_menu?: Array<Record<string, any>>;
  from_email?: string;
  from_name?: string;
  reply_to_email?: string;
  email_signature?: string;
  api_documentation_title?: string;
  api_description?: string;
  api_contact_info?: Record<string, string>;
  theme_id?: string;
}

interface BrandingUpdate extends Partial<BrandingCreate> {
  status?: string;
}

const API_BASE = '/api/v1/white-label';

// Get current tenant ID (this would typically come from auth context)
const getCurrentTenantId = () => {
  // TODO: Get from actual auth context
  return 'current-tenant-id';
};

export const useWhiteLabel = () => {
  const queryClient = useQueryClient();
  const tenantId = getCurrentTenantId();

  // Fetch themes
  const {
    data: themes,
    isLoading: themesLoading,
    error: themesError,
    refetch: refetchThemes
  } = useQuery<Theme[]>({
    queryKey: ['themes', tenantId],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/themes?tenant_id=${tenantId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch themes');
      }
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch branding
  const {
    data: branding,
    isLoading: brandingLoading,
    error: brandingError,
    refetch: refetchBranding
  } = useQuery<Branding | null>({
    queryKey: ['branding', tenantId],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/branding?tenant_id=${tenantId}`);
      if (!response.ok) {
        if (response.status === 404) {
          return null; // No branding configuration yet
        }
        throw new Error('Failed to fetch branding');
      }
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Get default theme
  const {
    data: defaultTheme,
    isLoading: defaultThemeLoading
  } = useQuery<Theme | null>({
    queryKey: ['default-theme', tenantId],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/themes/default/current?tenant_id=${tenantId}`);
      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        throw new Error('Failed to fetch default theme');
      }
      return response.json();
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  // Create theme mutation
  const createThemeMutation = useMutation({
    mutationFn: async (themeData: ThemeCreate) => {
      const response = await fetch(`${API_BASE}/themes?tenant_id=${tenantId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(themeData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create theme');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['themes'] });
    },
  });

  // Update theme mutation
  const updateThemeMutation = useMutation({
    mutationFn: async ({ themeId, themeData }: { themeId: string; themeData: ThemeUpdate }) => {
      const response = await fetch(`${API_BASE}/themes/${themeId}?tenant_id=${tenantId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(themeData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update theme');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['themes'] });
    },
  });

  // Delete theme mutation
  const deleteThemeMutation = useMutation({
    mutationFn: async (themeId: string) => {
      const response = await fetch(`${API_BASE}/themes/${themeId}?tenant_id=${tenantId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete theme');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['themes'] });
    },
  });

  // Set default theme mutation
  const setDefaultThemeMutation = useMutation({
    mutationFn: async (themeId: string) => {
      const response = await fetch(`${API_BASE}/themes/${themeId}/set-default?tenant_id=${tenantId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to set default theme');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['themes'] });
      queryClient.invalidateQueries({ queryKey: ['default-theme'] });
    },
  });

  // Duplicate theme mutation
  const duplicateThemeMutation = useMutation({
    mutationFn: async ({ themeId, newName }: { themeId: string; newName: string }) => {
      const response = await fetch(`${API_BASE}/themes/${themeId}/duplicate?tenant_id=${tenantId}&new_name=${encodeURIComponent(newName)}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to duplicate theme');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['themes'] });
    },
  });

  // Generate theme CSS
  const generateThemeCSS = useCallback(async (themeId: string): Promise<string> => {
    const response = await fetch(`${API_BASE}/themes/${themeId}/css?tenant_id=${tenantId}`);
    if (!response.ok) {
      throw new Error('Failed to generate theme CSS');
    }
    return response.text();
  }, [tenantId]);

  // Create branding mutation
  const createBrandingMutation = useMutation({
    mutationFn: async (brandingData: BrandingCreate) => {
      const response = await fetch(`${API_BASE}/branding?tenant_id=${tenantId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(brandingData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create branding');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['branding'] });
    },
  });

  // Update branding mutation
  const updateBrandingMutation = useMutation({
    mutationFn: async (brandingData: BrandingUpdate) => {
      const response = await fetch(`${API_BASE}/branding?tenant_id=${tenantId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(brandingData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update branding');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['branding'] });
    },
  });

  // Activate branding mutation
  const activateBrandingMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(`${API_BASE}/branding/activate?tenant_id=${tenantId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to activate branding');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['branding'] });
    },
  });

  // Get public branding
  const getPublicBranding = useCallback(async () => {
    const response = await fetch(`${API_BASE}/branding/public?tenant_id=${tenantId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch public branding');
    }
    return response.json();
  }, [tenantId]);

  // Validate branding
  const validateBranding = useCallback(async () => {
    const response = await fetch(`${API_BASE}/branding/validate?tenant_id=${tenantId}`);
    if (!response.ok) {
      throw new Error('Failed to validate branding');
    }
    return response.json();
  }, [tenantId]);

  const isLoading = themesLoading || brandingLoading || defaultThemeLoading;
  const error = themesError || brandingError;

  return {
    // Data
    themes: themes || [],
    branding,
    defaultTheme,

    // Loading states
    isLoading,
    error,

    // Refetch functions
    refetchThemes,
    refetchBranding,

    // Theme operations
    createTheme: createThemeMutation.mutateAsync,
    updateTheme: (themeId: string, themeData: ThemeUpdate) => 
      updateThemeMutation.mutateAsync({ themeId, themeData }),
    deleteTheme: deleteThemeMutation.mutateAsync,
    setDefaultTheme: setDefaultThemeMutation.mutateAsync,
    duplicateTheme: (themeId: string, newName: string) => 
      duplicateThemeMutation.mutateAsync({ themeId, newName }),
    generateThemeCSS,

    // Branding operations
    createBranding: createBrandingMutation.mutateAsync,
    updateBranding: updateBrandingMutation.mutateAsync,
    activateBranding: activateBrandingMutation.mutateAsync,
    getPublicBranding,
    validateBranding,

    // Mutation states
    isCreatingTheme: createThemeMutation.isPending,
    isUpdatingTheme: updateThemeMutation.isPending,
    isDeletingTheme: deleteThemeMutation.isPending,
    isSettingDefaultTheme: setDefaultThemeMutation.isPending,
    isDuplicatingTheme: duplicateThemeMutation.isPending,
    isCreatingBranding: createBrandingMutation.isPending,
    isUpdatingBranding: updateBrandingMutation.isPending,
    isActivatingBranding: activateBrandingMutation.isPending,
  };
};