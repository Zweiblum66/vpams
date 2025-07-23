import { useState, useEffect, useCallback } from 'react';
import { useApi } from './useApi';

interface PartnerInfo {
  id: string;
  company_name: string;
  partner_code: string;
  partner_type: string;
  partner_tier: string;
  status: string;
  primary_contact_name?: string;
  primary_contact_email?: string;
  website?: string;
  industry?: string;
  onboarding_completed: boolean;
  certification_status: string;
  created_at: string;
  updated_at?: string;
}

interface PartnerActivity {
  id: string;
  activity_type: string;
  activity_category?: string;
  title?: string;
  description?: string;
  user_email?: string;
  created_at: string;
}

interface PartnerDeal {
  id: string;
  deal_name: string;
  customer_name: string;
  deal_value: number;
  currency: string;
  stage: string;
  probability: number;
  expected_close_date?: string;
  actual_close_date?: string;
  description?: string;
  created_at: string;
}

interface PartnerCertification {
  id: string;
  name: string;
  type: string;
  status: string;
  completion_date?: string;
  expiry_date?: string;
}

interface PartnerStatistics {
  deals: {
    total: number;
    active: number;
    won: number;
    win_rate: number;
    total_value: number;
    total_commission: number;
  };
  activity: {
    recent_count: number;
  };
  certifications: {
    active: number;
  };
}

interface PartnerDashboard {
  partner_info: PartnerInfo;
  statistics: PartnerStatistics;
  recent_activities: PartnerActivity[];
  active_deals: PartnerDeal[];
  certifications: PartnerCertification[];
  resources_count: number;
  contacts_count: number;
}

interface AnalyticsTrends {
  deal_trends: Array<{
    date: string;
    total_value: number;
    deal_count: number;
  }>;
  activity_trends: Array<{
    date: string;
    activity_type: string;
    count: number;
  }>;
}

interface PartnerPerformance {
  period: {
    start_date: string;
    end_date: string;
    days: number;
  };
  deal_performance: {
    total_deals: number;
    total_value: number;
    avg_deal_value: number;
    total_commission: number;
    stage_distribution: Record<string, number>;
  };
  activity_performance: Record<string, number>;
  resource_engagement: {
    total_downloads: number;
    total_views: number;
    resource_count: number;
  };
}

interface PartnerContact {
  id: string;
  first_name: string;
  last_name: string;
  title?: string;
  department?: string;
  email: string;
  phone?: string;
  contact_type: string;
  is_primary: boolean;
  is_active: boolean;
  portal_access: boolean;
  admin_access: boolean;
  created_at: string;
}

interface PartnerApplication {
  id: string;
  application_type: string;
  requested_tier: string;
  status: string;
  business_plan: string;
  submitted_at?: string;
  review_notes?: string;
  created_at: string;
}

export const usePartnerPortal = () => {
  const { apiCall } = useApi();
  const [dashboard, setDashboard] = useState<PartnerDashboard | null>(null);
  const [partnerInfo, setPartnerInfo] = useState<PartnerInfo | null>(null);
  const [analytics, setAnalytics] = useState<PartnerPerformance | null>(null);
  const [contacts, setContacts] = useState<PartnerContact[]>([]);
  const [applications, setApplications] = useState<PartnerApplication[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async (partnerId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(`/api/v1/dashboard/partner/${partnerId}`, 'GET');
      setDashboard(response.data);
      setPartnerInfo(response.data.partner_info);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const fetchAnalytics = useCallback(async (partnerId: string, days: number = 90) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(`/api/v1/dashboard/partner/${partnerId}/performance?days=${days}`, 'GET');
      setAnalytics(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch analytics data');
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const fetchOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall('/api/v1/dashboard/overview', 'GET');
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch overview data');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const fetchTrends = useCallback(async (days: number = 30) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(`/api/v1/dashboard/analytics/trends?days=${days}`, 'GET');
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch trends data');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const fetchPartners = useCallback(async (params?: {
    page?: number;
    limit?: number;
    search?: string;
    partner_type?: string;
    status?: string;
    tier?: string;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const queryParams = new URLSearchParams();
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.limit) queryParams.append('limit', params.limit.toString());
      if (params?.search) queryParams.append('search', params.search);
      if (params?.partner_type) queryParams.append('partner_type', params.partner_type);
      if (params?.status) queryParams.append('status', params.status);
      if (params?.tier) queryParams.append('tier', params.tier);

      const url = `/api/v1/partners${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      const response = await apiCall(url, 'GET');
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch partners');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const createPartner = useCallback(async (partnerData: {
    company_name: string;
    partner_type: string;
    primary_contact_name: string;
    primary_contact_email: string;
    website?: string;
    industry?: string;
    address_line1?: string;
    city?: string;
    country?: string;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall('/api/v1/partners', 'POST', partnerData);
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to create partner');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const updatePartner = useCallback(async (partnerId: string, partnerData: {
    company_name?: string;
    website?: string;
    industry?: string;
    specializations?: string[];
    tags?: string[];
    notes?: string;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(`/api/v1/partners/${partnerId}`, 'PUT', partnerData);
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to update partner');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const fetchContacts = useCallback(async (partnerId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(`/api/v1/partners/${partnerId}/contacts`, 'GET');
      setContacts(response.data);
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch contacts');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const createContact = useCallback(async (partnerId: string, contactData: {
    first_name: string;
    last_name: string;
    email: string;
    title?: string;
    department?: string;
    phone?: string;
    contact_type?: string;
    is_primary?: boolean;
    portal_access?: boolean;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(`/api/v1/partners/${partnerId}/contacts`, 'POST', contactData);
      // Refresh contacts list
      await fetchContacts(partnerId);
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to create contact');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall, fetchContacts]);

  const updateContact = useCallback(async (partnerId: string, contactId: string, contactData: {
    first_name?: string;
    last_name?: string;
    title?: string;
    department?: string;
    phone?: string;
    contact_type?: string;
    is_primary?: boolean;
    portal_access?: boolean;
    is_active?: boolean;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(`/api/v1/partners/${partnerId}/contacts/${contactId}`, 'PUT', contactData);
      // Refresh contacts list
      await fetchContacts(partnerId);
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to update contact');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall, fetchContacts]);

  const deleteContact = useCallback(async (partnerId: string, contactId: string) => {
    setLoading(true);
    setError(null);
    try {
      await apiCall(`/api/v1/partners/${partnerId}/contacts/${contactId}`, 'DELETE');
      // Refresh contacts list
      await fetchContacts(partnerId);
    } catch (err: any) {
      setError(err.message || 'Failed to delete contact');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall, fetchContacts]);

  const submitApplication = useCallback(async (partnerId: string, applicationData: {
    application_type: string;
    requested_tier: string;
    business_plan: string;
    technical_capabilities?: any;
    market_focus?: string[];
    customer_references?: any[];
  }) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall('/api/v1/applications', 'POST', {
        partner_id: partnerId,
        ...applicationData
      });
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to submit application');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const refreshData = useCallback(async (partnerId?: string) => {
    if (partnerId) {
      await Promise.all([
        fetchDashboard(partnerId),
        fetchAnalytics(partnerId)
      ]);
    }
  }, [fetchDashboard, fetchAnalytics]);

  return {
    // Data
    dashboard,
    partnerInfo,
    analytics,
    contacts,
    applications,
    
    // State
    loading,
    error,
    
    // Actions
    fetchDashboard,
    fetchAnalytics,
    fetchOverview,
    fetchTrends,
    fetchPartners,
    createPartner,
    updatePartner,
    fetchContacts,
    createContact,
    updateContact,
    deleteContact,
    submitApplication,
    refreshData,
    
    // Utilities
    refetch: refreshData
  };
};