import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { logger } from '../utils/logger';

interface ApiClientConfig {
  baseURL?: string;
  timeout?: number;
  headers?: Record<string, string>;
}

interface RequestMetadata {
  startTime: number;
  method: string;
  url: string;
}

class ApiClient {
  private client: AxiosInstance;
  private tokenKey = 'auth_token';
  private refreshTokenKey = 'refresh_token';

  constructor(config: ApiClientConfig = {}) {
    this.client = axios.create({
      baseURL: config.baseURL || process.env.REACT_APP_API_URL || 'http://localhost:8000',
      timeout: config.timeout || 30000,
      headers: {
        'Content-Type': 'application/json',
        ...config.headers,
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getToken();
        if (token) {
          config.headers['Authorization'] = `Bearer ${token}`;
        }

        // Add request metadata
        const metadata: RequestMetadata = {
          startTime: Date.now(),
          method: config.method?.toUpperCase() || 'GET',
          url: config.url || '',
        };
        config.metadata = metadata;

        logger.debug('API Request', {
          method: metadata.method,
          url: metadata.url,
          headers: config.headers,
          data: config.data,
        });

        return config;
      },
      (error) => {
        logger.error('Request interceptor error', { error });
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        const metadata = response.config.metadata as RequestMetadata;
        const duration = Date.now() - metadata.startTime;

        logger.logApiCall(
          metadata.method,
          metadata.url,
          response.status,
          duration,
          {
            responseData: response.data,
          }
        );

        return response;
      },
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
        const metadata = originalRequest?.metadata as RequestMetadata;
        const duration = metadata ? Date.now() - metadata.startTime : 0;

        if (error.response) {
          logger.logApiCall(
            metadata?.method || 'UNKNOWN',
            metadata?.url || error.config?.url || 'UNKNOWN',
            error.response.status,
            duration,
            {
              error: error.response.data,
            }
          );

          // Handle 401 - Unauthorized
          if (error.response.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
              const refreshToken = this.getRefreshToken();
              if (refreshToken) {
                const response = await this.refreshAccessToken(refreshToken);
                this.setToken(response.data.access_token);
                
                if (response.data.refresh_token) {
                  this.setRefreshToken(response.data.refresh_token);
                }

                // Retry original request with new token
                if (originalRequest.headers) {
                  originalRequest.headers['Authorization'] = `Bearer ${response.data.access_token}`;
                }
                
                return this.client(originalRequest);
              }
            } catch (refreshError) {
              // Refresh failed, clear tokens and redirect to login
              this.clearTokens();
              window.location.href = '/login';
              return Promise.reject(refreshError);
            }
          }

          // Handle 403 - Forbidden
          if (error.response.status === 403) {
            logger.warn('Access forbidden', {
              url: metadata?.url,
              status: 403,
            });
          }

          // Handle 429 - Too Many Requests
          if (error.response.status === 429) {
            const retryAfter = error.response.headers['retry-after'];
            logger.warn('Rate limited', {
              url: metadata?.url,
              retryAfter,
            });
          }
        } else if (error.request) {
          // Network error
          logger.error('Network error', {
            url: metadata?.url,
            message: 'No response received from server',
          });
        } else {
          // Request setup error
          logger.error('Request setup error', {
            message: error.message,
          });
        }

        return Promise.reject(error);
      }
    );
  }

  private getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  private setToken(token: string): void {
    localStorage.setItem(this.tokenKey, token);
  }

  private getRefreshToken(): string | null {
    return localStorage.getItem(this.refreshTokenKey);
  }

  private setRefreshToken(token: string): void {
    localStorage.setItem(this.refreshTokenKey, token);
  }

  private clearTokens(): void {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.refreshTokenKey);
  }

  private async refreshAccessToken(refreshToken: string): Promise<AxiosResponse> {
    return this.client.post('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });
  }

  // Public methods
  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.get<T>(url, config);
  }

  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.post<T>(url, data, config);
  }

  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.put<T>(url, data, config);
  }

  async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.patch<T>(url, data, config);
  }

  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.delete<T>(url, config);
  }

  // File upload with progress
  async uploadFile<T = any>(
    url: string,
    formData: FormData,
    onProgress?: (progress: number) => void
  ): Promise<AxiosResponse<T>> {
    return this.client.post<T>(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
  }

  // Download file
  async downloadFile(url: string, filename?: string): Promise<void> {
    const response = await this.client.get(url, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }

  // Update auth token
  updateAuthToken(token: string): void {
    this.setToken(token);
  }

  // Clear auth
  clearAuth(): void {
    this.clearTokens();
  }

  // Get axios instance (for advanced use cases)
  getAxiosInstance(): AxiosInstance {
    return this.client;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for testing or multiple instances
export { ApiClient };

// Export types
export type { ApiClientConfig };