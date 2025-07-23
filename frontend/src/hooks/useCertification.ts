import { useState, useEffect, useCallback } from 'react';
import { useApi } from './useApi';

interface CertificationStats {
  total_submissions: number;
  certified_plugins: number;
  pending_reviews: number;
  average_score: number;
  certification_rate: number;
}

interface CertificationLevel {
  level: string;
  title: string;
  description: string;
  requirements: string[];
  benefits: string[];
  min_score: number;
  review_time: string;
}

interface CertificationStatus {
  certification_id?: string;
  plugin_id: string;
  certification_status: string;
  certification_level?: string;
  submitted_at?: string;
  reviewed_at?: string;
  expires_at?: string;
  overall_score?: number;
  reviewer_notes?: string;
  test_results?: TestResult[];
  next_steps?: string[];
}

interface TestResult {
  test_name: string;
  test_type: string;
  status: string;
  score: number;
  details: any;
  completed_at?: string;
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  suggestions: string[];
}

interface CertificationSubmission {
  certification_id: string;
  plugin_id: string;
  status: string;
  message: string;
  estimated_review_time: string;
}

interface CertificationBadge {
  type: string;
  level?: string;
  title: string;
  description: string;
  issued_date?: string;
  expires_date?: string;
  score?: number;
  badge_url: string;
}

interface BadgeResponse {
  plugin_id: string;
  certified: boolean;
  badges: CertificationBadge[];
  certification_url?: string;
}

export const useCertification = () => {
  const { apiCall } = useApi();
  const [certificationStats, setCertificationStats] = useState<CertificationStats | null>(null);
  const [certificationLevels, setCertificationLevels] = useState<CertificationLevel[]>([]);
  const [certificationStatuses, setCertificationStatuses] = useState<Record<string, CertificationStatus>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCertificationStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall('/api/v1/certification/stats', 'GET');
      setCertificationStats(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch certification stats');
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const fetchCertificationLevels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall('/api/v1/certification/levels', 'GET');
      setCertificationLevels(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch certification levels');
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const getCertificationStatus = useCallback(async (pluginId: string): Promise<CertificationStatus> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(`/api/v1/certification/status/${pluginId}`, 'GET');
      const status = response.data;
      setCertificationStatuses(prev => ({ ...prev, [pluginId]: status }));
      return status;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch certification status');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const submitForCertification = useCallback(async (pluginId: string): Promise<CertificationSubmission> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(`/api/v1/certification/submit/${pluginId}`, 'POST');
      
      // Refresh stats and status after submission
      await fetchCertificationStats();
      await getCertificationStatus(pluginId);
      
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to submit for certification');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall, fetchCertificationStats, getCertificationStatus]);

  const validatePlugin = useCallback(async (pluginId: string): Promise<ValidationResult> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall(`/api/v1/certification/tests/validate/${pluginId}`, 'GET');
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to validate plugin');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const getCertificationBadges = useCallback(async (pluginId: string): Promise<BadgeResponse> => {
    setError(null);
    try {
      const response = await apiCall(`/api/v1/certification/badges/${pluginId}`, 'GET');
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch certification badges');
      throw err;
    }
  }, [apiCall]);

  const getCertificationQueue = useCallback(async (params?: {
    status?: string;
    level?: string;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const queryParams = new URLSearchParams();
      if (params?.status) queryParams.append('status', params.status);
      if (params?.level) queryParams.append('level', params.level);

      const url = `/api/v1/certification/admin/queue${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      const response = await apiCall(url, 'GET');
      return response.data;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch certification queue');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  const refreshCertificationData = useCallback(async () => {
    try {
      await Promise.all([
        fetchCertificationStats(),
        fetchCertificationLevels()
      ]);
    } catch (error) {
      console.error('Failed to refresh certification data:', error);
    }
  }, [fetchCertificationStats, fetchCertificationLevels]);

  // Auto-fetch data on hook initialization
  useEffect(() => {
    refreshCertificationData();
  }, [refreshCertificationData]);

  // Helper functions
  const getCertificationLevel = useCallback((score: number): string => {
    if (score >= 90) return 'premium';
    if (score >= 75) return 'standard';
    if (score >= 60) return 'basic';
    return 'none';
  }, []);

  const getCertificationColor = useCallback((level: string): string => {
    switch (level) {
      case 'premium': return '#gold';
      case 'standard': return '#silver';
      case 'basic': return '#bronze';
      default: return '#gray';
    }
  }, []);

  const isPluginCertified = useCallback((pluginId: string): boolean => {
    const status = certificationStatuses[pluginId];
    return status?.certification_status === 'certified';
  }, [certificationStatuses]);

  const canSubmitForCertification = useCallback((pluginId: string): boolean => {
    const status = certificationStatuses[pluginId];
    return !status || !['pending', 'in_review', 'certified'].includes(status.certification_status);
  }, [certificationStatuses]);

  const getNextCertificationStep = useCallback((pluginId: string): string => {
    const status = certificationStatuses[pluginId];
    if (!status) return 'Submit for certification';
    
    switch (status.certification_status) {
      case 'not_submitted': return 'Submit for certification';
      case 'pending': return 'Waiting for review to start';
      case 'in_review': return 'Under review';
      case 'certified': return 'Certified - maintain quality';
      case 'rejected': return 'Address issues and resubmit';
      case 'failed': return 'Fix technical issues and resubmit';
      default: return 'Check status';
    }
  }, [certificationStatuses]);

  return {
    // Data
    certificationStats,
    certificationLevels,
    certificationStatuses,
    
    // State
    loading,
    error,
    
    // Actions
    fetchCertificationStats,
    fetchCertificationLevels,
    getCertificationStatus,
    submitForCertification,
    validatePlugin,
    getCertificationBadges,
    getCertificationQueue,
    refreshCertificationData,
    
    // Helper functions
    getCertificationLevel,
    getCertificationColor,
    isPluginCertified,
    canSubmitForCertification,
    getNextCertificationStep,
    
    // Utilities
    refetch: refreshCertificationData
  };
};