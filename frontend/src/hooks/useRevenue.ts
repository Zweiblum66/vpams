import { useState, useEffect, useCallback } from 'react';
import { useApi } from './useApi';

interface DeveloperInfo {
  id: string;
  revenue_share_percent: number;
  total_revenue: number;
  pending_payout: number;
}

interface RevenueOverview {
  total_revenue: number;
  current_month_revenue: number;
  pending_payout: number;
  total_sales: number;
  revenue_share_rate: number;
}

interface DailySale {
  date: string;
  revenue: number;
  sales_count: number;
}

interface TopPlugin {
  plugin_id: string;
  name: string;
  total_revenue: number;
  sales_count: number;
}

interface PaymentInfo {
  next_payout_date: string;
  minimum_payout: number;
  payment_methods: string[];
}

interface RevenueDashboard {
  developer_info: DeveloperInfo;
  overview: RevenueOverview;
  daily_sales: DailySale[];
  top_plugins: TopPlugin[];
  payment_info: PaymentInfo;
}

interface SaleHistory {
  sale_id: string;
  plugin_id: string;
  plugin_name: string;
  sale_price: number;
  revenue_share_amount: number;
  revenue_share_percent: number;
  customer_id: string;
  sale_date: string;
  payment_method: string;
  transaction_id: string;
  status: string;
}

interface Payout {
  id: string;
  developer_id: string;
  amount: number;
  currency: string;
  payout_method: string;
  status: string;
  status_message?: string;
  processed_at?: string;
  completed_at?: string;
  created_at: string;
}

interface PaymentMethod {
  id: string;
  developer_id: string;
  method_type: string;
  is_primary: boolean;
  is_verified: boolean;
  verification_status: string;
  created_at: string;
}

interface PayoutRequest {
  payout_id: string;
  amount: number;
  status: string;
  estimated_processing_time: string;
  message: string;
}

interface PluginRevenue {
  plugin_id: string;
  plugin_name: string;
  plugin_price: number;
  total_revenue: number;
  sales_count: number;
  avg_sale_price: number;
}

interface PaymentMethodAnalytics {
  payment_method: string;
  total_revenue: number;
  sales_count: number;
}

interface WeeklyRevenue {
  week: string;
  revenue: number;
  sales_count: number;
}

interface AnalyticsSummary {
  total_plugins: number;
  total_revenue: number;
  total_sales: number;
  avg_revenue_per_plugin: number;
}

interface RevenueAnalytics {
  period: {
    start_date: string;
    end_date: string;
    days: number;
  };
  plugin_revenue: PluginRevenue[];
  payment_methods: PaymentMethodAnalytics[];
  weekly_revenue: WeeklyRevenue[];
  summary: AnalyticsSummary;
}

interface TaxReport {
  year: number;
  developer_info: {
    id: string;
    company_name?: string;
    support_email?: string;
  };
  summary: {
    total_revenue: number;
    total_sales: number;
    total_payouts: number;
    payout_count: number;
    net_pending: number;
  };
  monthly_breakdown: Array<{
    month: number;
    month_name: string;
    revenue: number;
    sales_count: number;
  }>;
  tax_info: {
    currency: string;
    tax_year: number;
    generated_at: string;
    note: string;
  };
}

export const useRevenue = () => {
  const { apiCall } = useApi();
  const [dashboard, setDashboard] = useState<RevenueDashboard | null>(null);
  const [salesHistory, setSalesHistory] = useState<SaleHistory[]>([]);
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [analytics, setAnalytics] = useState<RevenueAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall('/api/v1/revenue/dashboard', 'GET');
      setDashboard(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const fetchSalesHistory = useCallback(async (params?: {
    plugin_id?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    limit?: number;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const queryParams = new URLSearchParams();
      if (params?.plugin_id) queryParams.append('plugin_id', params.plugin_id);
      if (params?.start_date) queryParams.append('start_date', params.start_date);
      if (params?.end_date) queryParams.append('end_date', params.end_date);
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.limit) queryParams.append('limit', params.limit.toString());

      const url = `/api/v1/revenue/sales${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      const response = await apiCall(url, 'GET');
      setSalesHistory(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch sales history');
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const fetchPayouts = useCallback(async (params?: {
    status?: string;
    page?: number;
    limit?: number;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const queryParams = new URLSearchParams();
      if (params?.status) queryParams.append('status', params.status);
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.limit) queryParams.append('limit', params.limit.toString());

      const url = `/api/v1/revenue/payouts${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      const response = await apiCall(url, 'GET');
      setPayouts(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch payouts');
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const requestPayout = useCallback(async (): Promise<PayoutRequest> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall('/api/v1/revenue/payouts/request', 'POST');
      // Refresh dashboard and payouts data
      await fetchDashboard();
      await fetchPayouts();
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to request payout');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall, fetchDashboard, fetchPayouts]);

  const fetchAnalytics = useCallback(async (days: number = 30) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(`/api/v1/revenue/analytics?days=${days}`, 'GET');
      setAnalytics(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch analytics');
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const generateTaxReport = useCallback(async (year: number): Promise<TaxReport> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(`/api/v1/revenue/tax-report?year=${year}`, 'GET');
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to generate tax report');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const addPaymentMethod = useCallback(async (paymentMethod: {
    method_type: string;
    payment_details: Record<string, any>;
    is_primary: boolean;
  }): Promise<PaymentMethod> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall('/api/v1/developer/payment-methods', 'POST', paymentMethod);
      // Refresh payment methods
      await fetchPaymentMethods();
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to add payment method');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const fetchPaymentMethods = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall('/api/v1/developer/payment-methods', 'GET');
      setPaymentMethods(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch payment methods');
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  // Auto-fetch data on hook initialization
  useEffect(() => {
    fetchDashboard();
    fetchSalesHistory();
    fetchPayouts();
    fetchPaymentMethods();
    fetchAnalytics();
  }, [fetchDashboard, fetchSalesHistory, fetchPayouts, fetchPaymentMethods, fetchAnalytics]);

  return {
    // Data
    dashboard,
    salesHistory,
    payouts,
    paymentMethods,
    analytics,
    
    // State
    loading,
    error,
    
    // Actions
    fetchDashboard,
    fetchSalesHistory,
    fetchPayouts,
    fetchPaymentMethods,
    fetchAnalytics,
    requestPayout,
    addPaymentMethod,
    generateTaxReport,
    
    // Utilities
    refetch: () => {
      fetchDashboard();
      fetchSalesHistory();
      fetchPayouts();
      fetchPaymentMethods();
      fetchAnalytics();
    }
  };
};