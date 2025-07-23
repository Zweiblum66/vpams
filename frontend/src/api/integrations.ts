/**
 * Integration Service API Client
 */

import { apiClient } from './client';
import { 
  Integration, 
  IntegrationCreate, 
  IntegrationUpdate,
  APIListing,
  MarketplaceStats,
  APICategory
} from '../types/integration';

export const integrationApi = {
  // Integration CRUD
  getIntegrations: async (params?: any) => {
    const response = await apiClient.get('/integrations', { params });
    return response.data;
  },

  getIntegration: async (id: string) => {
    const response = await apiClient.get(`/integrations/${id}`);
    return response.data;
  },

  createIntegration: async (data: IntegrationCreate) => {
    const response = await apiClient.post('/integrations', data);
    return response.data;
  },

  updateIntegration: async (id: string, data: IntegrationUpdate) => {
    const response = await apiClient.patch(`/integrations/${id}`, data);
    return response.data;
  },

  deleteIntegration: async (id: string) => {
    await apiClient.delete(`/integrations/${id}`);
  },

  // Integration Actions
  enableIntegration: async (id: string) => {
    const response = await apiClient.post(`/integrations/${id}/enable`);
    return response.data;
  },

  disableIntegration: async (id: string) => {
    const response = await apiClient.post(`/integrations/${id}/disable`);
    return response.data;
  },

  testIntegration: async (id: string) => {
    const response = await apiClient.post(`/integrations/${id}/test`);
    return response.data;
  },

  syncIntegration: async (id: string, fullSync: boolean = false) => {
    const response = await apiClient.post(`/integrations/${id}/sync`, { full_sync: fullSync });
    return response.data;
  },

  // Webhooks
  getWebhooks: async (integrationId: string) => {
    const response = await apiClient.get(`/integrations/${integrationId}/webhooks`);
    return response.data;
  },

  createWebhook: async (integrationId: string, data: any) => {
    const response = await apiClient.post(`/integrations/${integrationId}/webhooks`, data);
    return response.data;
  },

  updateWebhook: async (integrationId: string, webhookId: string, data: any) => {
    const response = await apiClient.patch(`/integrations/${integrationId}/webhooks/${webhookId}`, data);
    return response.data;
  },

  deleteWebhook: async (integrationId: string, webhookId: string) => {
    await apiClient.delete(`/integrations/${integrationId}/webhooks/${webhookId}`);
  },

  testWebhook: async (integrationId: string, webhookId: string, eventType: string = 'test') => {
    const response = await apiClient.post(`/integrations/${integrationId}/webhooks/${webhookId}/test`, {
      event_type: eventType
    });
    return response.data;
  },

  // Integration Logs
  getIntegrationLogs: async (integrationId: string, params?: any) => {
    const response = await apiClient.get(`/integrations/${integrationId}/logs`, { params });
    return response.data;
  },

  // Integration Metrics
  getIntegrationMetrics: async (integrationId: string, params?: any) => {
    const response = await apiClient.get(`/integrations/${integrationId}/metrics`, { params });
    return response.data;
  },

  // Marketplace
  getMarketplaceListings: async (params?: {
    category?: string;
    featured?: boolean;
    provider?: string;
    search?: string;
    sort?: string;
    order?: string;
    limit?: number;
    offset?: number;
  }) => {
    const response = await apiClient.get('/marketplace', { params });
    return response.data;
  },

  getMarketplaceListing: async (id: string) => {
    const response = await apiClient.get(`/marketplace/${id}`);
    return response.data;
  },

  getMarketplaceCategories: async (): Promise<APICategory[]> => {
    const response = await apiClient.get('/marketplace/categories');
    return response.data;
  },

  getMarketplaceStats: async (): Promise<MarketplaceStats> => {
    const response = await apiClient.get('/marketplace/stats');
    return response.data.data;
  },

  // Marketplace Actions
  installMarketplaceIntegration: async (listingId: string, config: any) => {
    const response = await apiClient.post(`/marketplace/${listingId}/install`, config);
    return response.data;
  },

  rateMarketplaceListing: async (listingId: string, rating: number, review?: string) => {
    const response = await apiClient.post(`/marketplace/${listingId}/rate`, null, {
      params: { rating, review }
    });
    return response.data;
  },

  getMarketplaceReviews: async (listingId: string, params?: any) => {
    const response = await apiClient.get(`/marketplace/${listingId}/reviews`, { params });
    return response.data;
  },

  testMarketplaceIntegration: async (listingId: string, config: any) => {
    const response = await apiClient.post(`/marketplace/${listingId}/test`, config);
    return response.data;
  },

  getMarketplaceDocumentation: async (listingId: string) => {
    const response = await apiClient.get(`/marketplace/${listingId}/documentation`);
    return response.data;
  },

  // User's Marketplace Listings
  getMyMarketplaceListings: async (params?: any) => {
    const response = await apiClient.get('/marketplace/my/listings', { params });
    return response.data;
  },

  createMarketplaceListing: async (data: any) => {
    const response = await apiClient.post('/marketplace', data);
    return response.data;
  },

  updateMarketplaceListing: async (id: string, data: any) => {
    const response = await apiClient.patch(`/marketplace/${id}`, data);
    return response.data;
  },

  deleteMarketplaceListing: async (id: string) => {
    await apiClient.delete(`/marketplace/${id}`);
  },

  // Integration Types and Schemas
  getIntegrationTypes: async () => {
    const response = await apiClient.get('/integrations/types');
    return response.data;
  },

  getIntegrationSchema: async (type: string) => {
    const response = await apiClient.get(`/integrations/types/${type}/schema`);
    return response.data;
  },

  // Export functionality
  exportTimeline: async (timelineId: string, format: string, options?: any) => {
    const response = await apiClient.post('/export/timeline', {
      timeline_id: timelineId,
      format,
      ...options
    });
    return response.data;
  },

  getExportStatus: async (exportId: string) => {
    const response = await apiClient.get(`/export/status/${exportId}`);
    return response.data;
  },

  getExportHistory: async (params?: any) => {
    const response = await apiClient.get('/export/history', { params });
    return response.data;
  },

  // NLE Export
  exportToNLE: async (timelineId: string, nleType: string, format: string, options?: any) => {
    const response = await apiClient.post('/export/nle', {
      timeline_id: timelineId,
      nle_type: nleType,
      format,
      ...options
    });
    return response.data;
  },

  // GraphQL
  executeGraphQLQuery: async (query: string, variables?: any) => {
    const response = await apiClient.post('/graphql', {
      query,
      variables
    });
    return response.data;
  },

  getGraphQLSchema: async () => {
    const response = await apiClient.get('/graphql/schema');
    return response.data;
  },

  // gRPC
  listGRPCServices: async () => {
    const response = await apiClient.get('/grpc/services');
    return response.data;
  },

  getGRPCServiceInfo: async (serviceName: string) => {
    const response = await apiClient.get(`/grpc/services/${serviceName}`);
    return response.data;
  },

  callGRPCMethod: async (serviceName: string, methodName: string, data: any) => {
    const response = await apiClient.post(`/grpc/services/${serviceName}/${methodName}`, data);
    return response.data;
  }
};