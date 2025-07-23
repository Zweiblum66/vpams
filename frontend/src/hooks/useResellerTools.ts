import { useState, useCallback } from 'react';
import { useAppDispatch, useAppSelector } from './redux';
import { api } from '../services/api';

interface DashboardData {
  total_leads: number;
  qualified_leads: number;
  active_customers: number;
  total_revenue: number;
  pending_commissions: number;
  conversion_rate: number;
  average_deal_size: number;
  pipeline_value: number;
}

interface Customer {
  id: string;
  company_name: string;
  contact_name: string;
  email: string;
  phone?: string;
  status: string;
  industry?: string;
  contract_value: number;
  monthly_value: number;
  created_at: string;
  updated_at?: string;
}

interface Lead {
  id: string;
  company_name: string;
  contact_name: string;
  email: string;
  phone?: string;
  status: string;
  source?: string;
  estimated_value: number;
  probability: number;
  temperature: string;
  created_at: string;
  updated_at?: string;
}

interface Commission {
  id: string;
  order_id?: string;
  product_name?: string;
  sale_amount: number;
  commission_rate: number;
  commission_amount: number;
  payment_status: string;
  sale_date: string;
  due_date?: string;
  payment_date?: string;
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

export const useResellerTools = () => {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const dispatch = useAppDispatch();
  const currentUser = useAppSelector(state => state.auth.user);

  // Dashboard operations
  const refreshDashboard = useCallback(async () => {
    if (!currentUser?.reseller_id) return;
    
    setLoading(true);
    try {
      const response = await api.get(`/reseller-tools/api/v1/resellers/${currentUser.reseller_id}/dashboard`);
      setDashboard(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, [currentUser?.reseller_id]);

  // Customer operations
  const getCustomers = useCallback(async (params: QueryParams = {}): Promise<PaginatedResponse<Customer>> => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.get('/reseller-tools/api/v1/customers', {
      params: {
        reseller_id: currentUser.reseller_id,
        ...params
      }
    });
    return response.data;
  }, [currentUser?.reseller_id]);

  const createCustomer = useCallback(async (customerData: Partial<Customer>) => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.post('/reseller-tools/api/v1/customers', {
      ...customerData,
      reseller_id: currentUser.reseller_id
    });
    return response.data;
  }, [currentUser?.reseller_id]);

  const updateCustomer = useCallback(async (customerId: string, customerData: Partial<Customer>) => {
    const response = await api.put(`/reseller-tools/api/v1/customers/${customerId}`, customerData);
    return response.data;
  }, []);

  const deleteCustomer = useCallback(async (customerId: string) => {
    await api.delete(`/reseller-tools/api/v1/customers/${customerId}`);
  }, []);

  const getCustomerStats = useCallback(async () => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.get(`/reseller-tools/api/v1/customers/stats/${currentUser.reseller_id}`);
    return response.data;
  }, [currentUser?.reseller_id]);

  // Lead operations
  const getLeads = useCallback(async (params: QueryParams = {}): Promise<PaginatedResponse<Lead>> => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.get('/reseller-tools/api/v1/leads', {
      params: {
        reseller_id: currentUser.reseller_id,
        ...params
      }
    });
    return response.data;
  }, [currentUser?.reseller_id]);

  const createLead = useCallback(async (leadData: Partial<Lead>) => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.post('/reseller-tools/api/v1/leads', {
      ...leadData,
      reseller_id: currentUser.reseller_id
    });
    return response.data;
  }, [currentUser?.reseller_id]);

  const updateLead = useCallback(async (leadId: string, leadData: Partial<Lead>) => {
    const response = await api.put(`/reseller-tools/api/v1/leads/${leadId}`, leadData);
    return response.data;
  }, []);

  const deleteLead = useCallback(async (leadId: string) => {
    await api.delete(`/reseller-tools/api/v1/leads/${leadId}`);
  }, []);

  const convertLeadToCustomer = useCallback(async (leadId: string, customerData: Partial<Customer>) => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.post(`/reseller-tools/api/v1/customers/convert-lead/${leadId}`, {
      ...customerData,
      reseller_id: currentUser.reseller_id
    });
    return response.data;
  }, [currentUser?.reseller_id]);

  // Commission operations
  const getCommissions = useCallback(async (params: QueryParams = {}): Promise<PaginatedResponse<Commission>> => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.get('/reseller-tools/api/v1/commissions', {
      params: {
        reseller_id: currentUser.reseller_id,
        ...params
      }
    });
    return response.data;
  }, [currentUser?.reseller_id]);

  const createCommission = useCallback(async (commissionData: Partial<Commission>) => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.post('/reseller-tools/api/v1/commissions', {
      ...commissionData,
      reseller_id: currentUser.reseller_id
    });
    return response.data;
  }, [currentUser?.reseller_id]);

  const markCommissionPaid = useCallback(async (commissionId: string, paymentReference: string) => {
    await api.post(`/reseller-tools/api/v1/commissions/${commissionId}/mark-paid`, null, {
      params: { payment_reference: paymentReference }
    });
  }, []);

  // Pricing operations
  const getPricingTiers = useCallback(async (activeOnly: boolean = true) => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.get('/reseller-tools/api/v1/pricing-tiers', {
      params: {
        reseller_id: currentUser.reseller_id,
        active_only: activeOnly
      }
    });
    return response.data;
  }, [currentUser?.reseller_id]);

  const createPricingTier = useCallback(async (pricingData: any) => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.post('/reseller-tools/api/v1/pricing-tiers', {
      ...pricingData,
      reseller_id: currentUser.reseller_id
    });
    return response.data;
  }, [currentUser?.reseller_id]);

  const updatePricingTier = useCallback(async (tierId: string, pricingData: any) => {
    const response = await api.put(`/reseller-tools/api/v1/pricing-tiers/${tierId}`, pricingData);
    return response.data;
  }, []);

  // Analytics operations
  const getAnalytics = useCallback(async (startDate?: string, endDate?: string) => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.get(`/reseller-tools/api/v1/analytics/reseller/${currentUser.reseller_id}/metrics`, {
      params: { start_date: startDate, end_date: endDate }
    });
    return response.data;
  }, [currentUser?.reseller_id]);

  const getPipelineAnalysis = useCallback(async () => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.get(`/reseller-tools/api/v1/analytics/reseller/${currentUser.reseller_id}/pipeline`);
    return response.data;
  }, [currentUser?.reseller_id]);

  // Export operations
  const exportData = useCallback(async (type: string, format: string = 'csv') => {
    try {
      const response = await api.get(`/reseller-tools/api/v1/export/${type}`, {
        params: { format },
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${type}-export-${new Date().toISOString().split('T')[0]}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      throw error;
    }
  }, []);

  const exportCustomers = useCallback(() => exportData('customers'), [exportData]);
  const exportLeads = useCallback(() => exportData('leads'), [exportData]);
  const exportCommissions = useCallback(() => exportData('commissions'), [exportData]);

  // Activity operations
  const addCustomerActivity = useCallback(async (customerId: string, activityData: any) => {
    const response = await api.post(`/reseller-tools/api/v1/customers/${customerId}/activities`, {
      ...activityData,
      customer_id: customerId
    });
    return response.data;
  }, []);

  const addLeadActivity = useCallback(async (leadId: string, activityData: any) => {
    const response = await api.post(`/reseller-tools/api/v1/leads/${leadId}/activities`, {
      ...activityData,
      lead_id: leadId
    });
    return response.data;
  }, []);

  const getCustomerActivities = useCallback(async (customerId: string, params: QueryParams = {}) => {
    const response = await api.get(`/reseller-tools/api/v1/customers/${customerId}/activities`, {
      params
    });
    return response.data;
  }, []);

  const getLeadActivities = useCallback(async (leadId: string, params: QueryParams = {}) => {
    const response = await api.get(`/reseller-tools/api/v1/leads/${leadId}/activities`, {
      params
    });
    return response.data;
  }, []);

  // Notification operations
  const getNotifications = useCallback(async (unreadOnly: boolean = false, limit: number = 50) => {
    if (!currentUser?.reseller_id) throw new Error('No reseller ID found');
    
    const response = await api.get(`/reseller-tools/api/v1/notifications/${currentUser.reseller_id}`, {
      params: { unread_only: unreadOnly, limit }
    });
    return response.data;
  }, [currentUser?.reseller_id]);

  const markNotificationRead = useCallback(async (notificationId: string) => {
    await api.post(`/reseller-tools/api/v1/notifications/${notificationId}/mark-read`);
  }, []);

  const acknowledgeNotification = useCallback(async (notificationId: string) => {
    await api.post(`/reseller-tools/api/v1/notifications/${notificationId}/acknowledge`);
  }, []);

  return {
    // State
    dashboard,
    loading,
    error,
    
    // Dashboard operations
    refreshDashboard,
    
    // Customer operations
    getCustomers,
    createCustomer,
    updateCustomer,
    deleteCustomer,
    getCustomerStats,
    exportCustomers,
    
    // Lead operations
    getLeads,
    createLead,
    updateLead,
    deleteLead,
    convertLeadToCustomer,
    exportLeads,
    
    // Commission operations
    getCommissions,
    createCommission,
    markCommissionPaid,
    exportCommissions,
    
    // Pricing operations
    getPricingTiers,
    createPricingTier,
    updatePricingTier,
    
    // Analytics operations
    getAnalytics,
    getPipelineAnalysis,
    
    // Activity operations
    addCustomerActivity,
    addLeadActivity,
    getCustomerActivities,
    getLeadActivities,
    
    // Notification operations
    getNotifications,
    markNotificationRead,
    acknowledgeNotification,
    
    // Export operations
    exportData
  };
};