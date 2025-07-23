import { useState, useCallback } from 'react';
import { useAppDispatch, useAppSelector } from './redux';
import { api } from '../services/api';

interface APIKey {
  id: string;
  key_id: string;
  name: string;
  description?: string;
  status: 'active' | 'inactive' | 'revoked' | 'expired';
  tier: 'basic' | 'standard' | 'premium' | 'enterprise';
  scopes: string[];
  allowed_features: string[];
  allowed_api_versions: string[];
  rate_limit: string;
  burst_limit: number;
  current_usage: number;
  last_used_at?: string;
  created_at: string;
  updated_at?: string;
}

interface Webhook {
  id: string;
  api_key_id: string;
  name: string;
  url: string;
  description?: string;
  status: 'active' | 'inactive' | 'failed' | 'suspended';
  events: string[];
  secret?: string;
  timeout_seconds: number;
  retry_attempts: number;
  retry_delay_seconds: number;
  headers?: Record<string, string>;
  total_deliveries: number;
  successful_deliveries: number;
  failed_deliveries: number;
  last_delivery_at?: string;
  created_at: string;
  updated_at?: string;
}

interface UsageStats {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  success_rate: number;
  avg_response_time_ms: number;
  total_response_size_bytes: number;
  unique_endpoints: number;
  period_start?: string;
  period_end?: string;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

interface QueryParams {
  page?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  search?: string;
  status?: string;
  [key: string]: any;
}

export const usePartnerAPIs = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const dispatch = useAppDispatch();
  const currentUser = useAppSelector(state => state.auth.user);

  // API Key operations
  const getAPIKeys = useCallback(async (params: QueryParams = {}): Promise<PaginatedResponse<APIKey>> => {
    const response = await api.get('/partner-apis/api/v1/api-keys', { params });
    return response.data;
  }, []);

  const getAPIKey = useCallback(async (apiKeyId: string): Promise<APIKey> => {
    const response = await api.get(`/partner-apis/api/v1/api-keys/${apiKeyId}`);
    return response.data;
  }, []);

  const createAPIKey = useCallback(async (apiKeyData: Partial<APIKey>): Promise<APIKey & { api_key: string }> => {
    const response = await api.post('/partner-apis/api/v1/api-keys', apiKeyData);
    return response.data;
  }, []);

  const updateAPIKey = useCallback(async (apiKeyId: string, apiKeyData: Partial<APIKey>): Promise<APIKey> => {
    const response = await api.put(`/partner-apis/api/v1/api-keys/${apiKeyId}`, apiKeyData);
    return response.data;
  }, []);

  const deleteAPIKey = useCallback(async (apiKeyId: string): Promise<void> => {
    await api.delete(`/partner-apis/api/v1/api-keys/${apiKeyId}`);
  }, []);

  const regenerateAPIKey = useCallback(async (apiKeyId: string): Promise<{ api_key: string }> => {
    const response = await api.post(`/partner-apis/api/v1/api-keys/${apiKeyId}/regenerate`);
    return response.data;
  }, []);

  // Webhook operations
  const getWebhooks = useCallback(async (apiKeyId: string, params: QueryParams = {}): Promise<PaginatedResponse<Webhook>> => {
    const response = await api.get(`/partner-apis/api/v1/api-keys/${apiKeyId}/webhooks`, { params });
    return response.data;
  }, []);

  const getWebhook = useCallback(async (webhookId: string): Promise<Webhook> => {
    const response = await api.get(`/partner-apis/api/v1/webhooks/${webhookId}`);
    return response.data;
  }, []);

  const createWebhook = useCallback(async (apiKeyId: string, webhookData: Partial<Webhook>): Promise<Webhook> => {
    const response = await api.post(`/partner-apis/api/v1/api-keys/${apiKeyId}/webhooks`, webhookData);
    return response.data;
  }, []);

  const updateWebhook = useCallback(async (webhookId: string, webhookData: Partial<Webhook>): Promise<Webhook> => {
    const response = await api.put(`/partner-apis/api/v1/webhooks/${webhookId}`, webhookData);
    return response.data;
  }, []);

  const deleteWebhook = useCallback(async (webhookId: string): Promise<void> => {
    await api.delete(`/partner-apis/api/v1/webhooks/${webhookId}`);
  }, []);

  const testWebhook = useCallback(async (webhookId: string, testData?: any): Promise<any> => {
    const response = await api.post(`/partner-apis/api/v1/webhooks/${webhookId}/test`, testData || {});
    return response.data;
  }, []);

  // Analytics operations
  const getUsageStats = useCallback(async (
    apiKeyId: string,
    startDate?: string,
    endDate?: string
  ): Promise<UsageStats> => {
    const params: any = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    
    const response = await api.get(`/partner-apis/api/v1/api-keys/${apiKeyId}/usage-stats`, { params });
    return response.data;
  }, []);

  const getUsageByEndpoint = useCallback(async (
    apiKeyId: string,
    startDate?: string,
    endDate?: string,
    limit: number = 20
  ): Promise<any[]> => {
    const params: any = { limit };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    
    const response = await api.get(`/partner-apis/api/v1/api-keys/${apiKeyId}/usage-by-endpoint`, { params });
    return response.data;
  }, []);

  const getDailyUsage = useCallback(async (
    apiKeyId: string,
    days: number = 30
  ): Promise<any[]> => {
    const response = await api.get(`/partner-apis/api/v1/api-keys/${apiKeyId}/daily-usage`, {
      params: { days }
    });
    return response.data;
  }, []);

  const getErrorAnalysis = useCallback(async (
    apiKeyId: string,
    startDate?: string,
    endDate?: string
  ): Promise<any> => {
    const params: any = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    
    const response = await api.get(`/partner-apis/api/v1/api-keys/${apiKeyId}/error-analysis`, { params });
    return response.data;
  }, []);

  // API Documentation
  const getAPIDocumentation = useCallback(async (version: string = 'v1'): Promise<any> => {
    const response = await api.get(`/partner-apis/partner/${version}/docs`);
    return response.data;
  }, []);

  const getEndpointDocumentation = useCallback(async (
    version: string = 'v1',
    endpoint?: string
  ): Promise<any> => {
    const params = endpoint ? { endpoint } : {};
    const response = await api.get(`/partner-apis/api/v1/endpoints`, { params });
    return response.data;
  }, []);

  // Service health checks
  const checkServiceHealth = useCallback(async (): Promise<any> => {
    const response = await api.get('/partner-apis/health');
    return response.data;
  }, []);

  const getServiceInfo = useCallback(async (): Promise<any> => {
    const response = await api.get('/partner-apis/');
    return response.data;
  }, []);

  // Rate limit information
  const getRateLimitInfo = useCallback(async (apiKeyId: string): Promise<any> => {
    const response = await api.get(`/partner-apis/api/v1/api-keys/${apiKeyId}/rate-limit`);
    return response.data;
  }, []);

  const resetRateLimit = useCallback(async (apiKeyId: string): Promise<void> => {
    await api.post(`/partner-apis/api/v1/api-keys/${apiKeyId}/reset-rate-limit`);
  }, []);

  // Partner configuration
  const getPartnerConfig = useCallback(async (): Promise<any> => {
    if (!currentUser?.partner_id) throw new Error('No partner ID found');
    
    const response = await api.get(`/partner-apis/api/v1/partners/${currentUser.partner_id}/config`);
    return response.data;
  }, [currentUser?.partner_id]);

  const updatePartnerConfig = useCallback(async (configData: any): Promise<any> => {
    if (!currentUser?.partner_id) throw new Error('No partner ID found');
    
    const response = await api.put(`/partner-apis/api/v1/partners/${currentUser.partner_id}/config`, configData);
    return response.data;
  }, [currentUser?.partner_id]);

  // Export operations
  const exportUsageData = useCallback(async (
    apiKeyId: string,
    format: string = 'csv',
    startDate?: string,
    endDate?: string
  ): Promise<void> => {
    try {
      const params: any = { format };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      
      const response = await api.get(`/partner-apis/api/v1/api-keys/${apiKeyId}/export-usage`, {
        params,
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `usage-data-${apiKeyId}-${new Date().toISOString().split('T')[0]}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      throw error;
    }
  }, []);

  const exportWebhookLogs = useCallback(async (
    webhookId: string,
    format: string = 'csv',
    startDate?: string,
    endDate?: string
  ): Promise<void> => {
    try {
      const params: any = { format };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      
      const response = await api.get(`/partner-apis/api/v1/webhooks/${webhookId}/export-logs`, {
        params,
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `webhook-logs-${webhookId}-${new Date().toISOString().split('T')[0]}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      throw error;
    }
  }, []);

  // Webhook delivery operations
  const getWebhookDeliveries = useCallback(async (
    webhookId: string,
    params: QueryParams = {}
  ): Promise<PaginatedResponse<any>> => {
    const response = await api.get(`/partner-apis/api/v1/webhooks/${webhookId}/deliveries`, { params });
    return response.data;
  }, []);

  const retryWebhookDelivery = useCallback(async (deliveryId: string): Promise<any> => {
    const response = await api.post(`/partner-apis/api/v1/webhook-deliveries/${deliveryId}/retry`);
    return response.data;
  }, []);

  return {
    // State
    loading,
    error,
    
    // API Key operations
    getAPIKeys,
    getAPIKey,
    createAPIKey,
    updateAPIKey,
    deleteAPIKey,
    regenerateAPIKey,
    
    // Webhook operations
    getWebhooks,
    getWebhook,
    createWebhook,
    updateWebhook,
    deleteWebhook,
    testWebhook,
    
    // Analytics operations
    getUsageStats,
    getUsageByEndpoint,
    getDailyUsage,
    getErrorAnalysis,
    
    // Documentation
    getAPIDocumentation,
    getEndpointDocumentation,
    
    // Service health
    checkServiceHealth,
    getServiceInfo,
    
    // Rate limiting
    getRateLimitInfo,
    resetRateLimit,
    
    // Partner configuration
    getPartnerConfig,
    updatePartnerConfig,
    
    // Export operations
    exportUsageData,
    exportWebhookLogs,
    
    // Webhook deliveries
    getWebhookDeliveries,
    retryWebhookDelivery
  };
};