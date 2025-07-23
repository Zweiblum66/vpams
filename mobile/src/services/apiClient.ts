/**
 * API Client Configuration
 * 
 * Axios-based HTTP client with authentication,
 * error handling, and request/response interceptors.
 */

import axios, {AxiosInstance, AxiosError, AxiosResponse} from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {Alert} from 'react-native';

// API Configuration
const API_BASE_URL = __DEV__ 
  ? 'http://localhost:8000'  // Development
  : 'https://api.mams.example.com';  // Production

const API_TIMEOUT = 30000; // 30 seconds

interface ApiError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
  request_id: string;
}

class ApiClient {
  private client: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (value?: any) => void;
    reject: (error?: any) => void;
  }> = [];

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: API_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Client-Platform': 'mobile',
        'X-Client-Version': '1.0.0',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor for authentication
    this.client.interceptors.request.use(
      async (config) => {
        try {
          const token = await AsyncStorage.getItem('access_token');
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        } catch (error) {
          console.error('Failed to get access token:', error);
        }

        // Add request ID for tracking
        config.headers['X-Request-ID'] = this.generateRequestId();

        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling and token refresh
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        return response;
      },
      async (error: AxiosError) => {
        const originalRequest = error.config as any;

        // Handle 401 errors with token refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            // Queue the request if refresh is in progress
            return new Promise((resolve, reject) => {
              this.failedQueue.push({resolve, reject});
            }).then((token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              return this.client(originalRequest);
            }).catch((err) => {
              return Promise.reject(err);
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            const refreshToken = await AsyncStorage.getItem('refresh_token');
            if (refreshToken) {
              const response = await this.refreshAccessToken(refreshToken);
              const newToken = response.access_token;

              await AsyncStorage.setItem('access_token', newToken);
              await AsyncStorage.setItem('refresh_token', response.refresh_token);

              // Process queued requests
              this.processFailedQueue(newToken, null);

              // Retry original request
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            this.processFailedQueue(null, refreshError);
            await this.handleAuthFailure();
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        // Handle other errors
        return Promise.reject(this.handleApiError(error));
      }
    );
  }

  private generateRequestId(): string {
    return Math.random().toString(36).substring(2, 15) + 
           Math.random().toString(36).substring(2, 15);
  }

  private async refreshAccessToken(refreshToken: string): Promise<{
    access_token: string;
    refresh_token: string;
  }> {
    const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
      refresh_token: refreshToken,
    });

    return response.data;
  }

  private processFailedQueue(token: string | null, error: any) {
    this.failedQueue.forEach(({resolve, reject}) => {
      if (error) {
        reject(error);
      } else {
        resolve(token);
      }
    });

    this.failedQueue = [];
  }

  private async handleAuthFailure() {
    // Clear stored tokens
    await AsyncStorage.multiRemove(['access_token', 'refresh_token', 'user_data']);
    
    // Navigate to login screen
    // This would typically be handled by a navigation service
    // For now, just show an alert
    Alert.alert(
      'Session Expired',
      'Your session has expired. Please log in again.',
      [
        {
          text: 'OK',
          onPress: () => {
            // Navigate to login screen
            // NavigationService.reset('Auth');
          },
        },
      ]
    );
  }

  private handleApiError(error: AxiosError): Error {
    if (error.response) {
      // Server responded with error status
      const apiError = error.response.data as ApiError;
      
      // Log error for debugging
      console.error('API Error:', {
        status: error.response.status,
        code: apiError?.code,
        message: apiError?.message,
        url: error.config?.url,
        method: error.config?.method,
      });

      // Handle specific error types
      switch (error.response.status) {
        case 400:
          return new Error(apiError?.message || 'Bad request');
        case 401:
          return new Error('Unauthorized access');
        case 403:
          return new Error('Access forbidden');
        case 404:
          return new Error('Resource not found');
        case 422:
          return new Error(apiError?.message || 'Validation error');
        case 429:
          return new Error('Too many requests. Please try again later.');
        case 500:
          return new Error('Server error. Please try again later.');
        case 503:
          return new Error('Service temporarily unavailable');
        default:
          return new Error(apiError?.message || 'An unexpected error occurred');
      }
    } else if (error.request) {
      // Network error
      console.error('Network Error:', error.message);
      return new Error('Network error. Please check your connection.');
    } else {
      // Request setup error
      console.error('Request Error:', error.message);
      return new Error('Request failed. Please try again.');
    }
  }

  // Public API methods
  get defaults() {
    return this.client.defaults;
  }

  async get(url: string, config?: any) {
    return this.client.get(url, config);
  }

  async post(url: string, data?: any, config?: any) {
    return this.client.post(url, data, config);
  }

  async put(url: string, data?: any, config?: any) {
    return this.client.put(url, data, config);
  }

  async patch(url: string, data?: any, config?: any) {
    return this.client.patch(url, data, config);
  }

  async delete(url: string, config?: any) {
    return this.client.delete(url, config);
  }

  // Utility methods
  async setAuthToken(token: string) {
    await AsyncStorage.setItem('access_token', token);
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  async clearAuthToken() {
    await AsyncStorage.removeItem('access_token');
    delete this.client.defaults.headers.common['Authorization'];
  }

  async isAuthenticated(): Promise<boolean> {
    try {
      const token = await AsyncStorage.getItem('access_token');
      return !!token;
    } catch (error) {
      return false;
    }
  }

  // Upload with progress support
  async uploadWithProgress(
    url: string,
    formData: FormData,
    onProgress?: (progress: number) => void
  ) {
    return this.client.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100;
          onProgress(progress);
        }
      },
    });
  }

  // Download with progress support
  async downloadWithProgress(
    url: string,
    onProgress?: (progress: number) => void
  ) {
    return this.client.get(url, {
      responseType: 'blob',
      onDownloadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100;
          onProgress(progress);
        }
      },
    });
  }

  // Health check
  async healthCheck(): Promise<{status: string; timestamp: string}> {
    const response = await this.client.get('/api/v1/health');
    return response.data;
  }
}

export const apiClient = new ApiClient();