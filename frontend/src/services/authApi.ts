import { apiClient } from './apiClient';
import { logger } from '../utils/logger';

export interface LoginRequest {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterRequest {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  acceptTerms: boolean;
  marketingEmails?: boolean;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    email: string;
    firstName: string;
    lastName: string;
    role: string;
    permissions: string[];
    isEmailVerified: boolean;
    lastLoginAt?: string;
    createdAt: string;
    updatedAt: string;
  };
}

export interface RefreshTokenResponse {
  access_token: string;
  expires_in: number;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetResponse {
  message: string;
}

export interface ResetPasswordRequest {
  token: string;
  password: string;
}

export interface ValidateTokenResponse {
  valid: boolean;
  email?: string;
}

export class AuthApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string
  ) {
    super(message);
    this.name = 'AuthApiError';
  }
}

class AuthApi {
  private readonly baseUrl = '/api/v1/auth';

  async login(credentials: LoginRequest): Promise<AuthResponse> {
    try {
      logger.info('AuthApi.login called', {
        email: credentials.email,
        rememberMe: credentials.rememberMe,
        actionType: 'auth_api_login',
      });

      const response = await apiClient.post<AuthResponse>(`${this.baseUrl}/login`, {
        email: credentials.email,
        password: credentials.password,
        remember_me: credentials.rememberMe,
      });

      logger.info('AuthApi.login successful', {
        userId: response.data.user.id,
        email: response.data.user.email,
        actionType: 'auth_api_login_success',
      });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.message || 'Login failed';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AuthApi.login failed', {
        email: credentials.email,
        statusCode,
        code,
        message,
        actionType: 'auth_api_login_error',
      }, error);

      throw new AuthApiError(message, statusCode, code);
    }
  }

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    try {
      logger.info('AuthApi.register called', {
        email: userData.email,
        firstName: userData.firstName,
        lastName: userData.lastName,
        marketingEmails: userData.marketingEmails,
        actionType: 'auth_api_register',
      });

      const response = await apiClient.post<AuthResponse>(`${this.baseUrl}/register`, {
        first_name: userData.firstName,
        last_name: userData.lastName,
        email: userData.email,
        password: userData.password,
        accept_terms: userData.acceptTerms,
        marketing_emails: userData.marketingEmails,
      });

      logger.info('AuthApi.register successful', {
        userId: response.data.user.id,
        email: response.data.user.email,
        actionType: 'auth_api_register_success',
      });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.message || 'Registration failed';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AuthApi.register failed', {
        email: userData.email,
        statusCode,
        code,
        message,
        actionType: 'auth_api_register_error',
      }, error);

      throw new AuthApiError(message, statusCode, code);
    }
  }

  async refreshToken(refreshToken: string): Promise<RefreshTokenResponse> {
    try {
      logger.info('AuthApi.refreshToken called', {
        actionType: 'auth_api_refresh_token',
      });

      const response = await apiClient.post<RefreshTokenResponse>(`${this.baseUrl}/refresh`, {
        refresh_token: refreshToken,
      });

      logger.info('AuthApi.refreshToken successful', {
        actionType: 'auth_api_refresh_token_success',
      });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.message || 'Token refresh failed';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AuthApi.refreshToken failed', {
        statusCode,
        code,
        message,
        actionType: 'auth_api_refresh_token_error',
      }, error);

      throw new AuthApiError(message, statusCode, code);
    }
  }

  async logout(): Promise<void> {
    try {
      logger.info('AuthApi.logout called', {
        actionType: 'auth_api_logout',
      });

      await apiClient.post(`${this.baseUrl}/logout`);

      logger.info('AuthApi.logout successful', {
        actionType: 'auth_api_logout_success',
      });
    } catch (error: any) {
      // Log the error but don't throw it, as logout should always succeed locally
      logger.warn('AuthApi.logout failed', {
        error: error.message,
        actionType: 'auth_api_logout_error',
      }, error);
    }
  }

  async requestPasswordReset(email: string): Promise<PasswordResetResponse> {
    try {
      logger.info('AuthApi.requestPasswordReset called', {
        email,
        actionType: 'auth_api_password_reset_request',
      });

      const response = await apiClient.post<PasswordResetResponse>(`${this.baseUrl}/forgot-password`, {
        email,
      });

      logger.info('AuthApi.requestPasswordReset successful', {
        email,
        actionType: 'auth_api_password_reset_request_success',
      });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.message || 'Password reset request failed';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AuthApi.requestPasswordReset failed', {
        email,
        statusCode,
        code,
        message,
        actionType: 'auth_api_password_reset_request_error',
      }, error);

      throw new AuthApiError(message, statusCode, code);
    }
  }

  async validateResetToken(token: string): Promise<ValidateTokenResponse> {
    try {
      logger.info('AuthApi.validateResetToken called', {
        actionType: 'auth_api_validate_reset_token',
      });

      const response = await apiClient.get<ValidateTokenResponse>(`${this.baseUrl}/reset-password/validate`, {
        params: { token },
      });

      logger.info('AuthApi.validateResetToken successful', {
        valid: response.data.valid,
        actionType: 'auth_api_validate_reset_token_success',
      });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.message || 'Token validation failed';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AuthApi.validateResetToken failed', {
        statusCode,
        code,
        message,
        actionType: 'auth_api_validate_reset_token_error',
      }, error);

      throw new AuthApiError(message, statusCode, code);
    }
  }

  async resetPassword(token: string, password: string): Promise<void> {
    try {
      logger.info('AuthApi.resetPassword called', {
        actionType: 'auth_api_reset_password',
      });

      await apiClient.post(`${this.baseUrl}/reset-password`, {
        token,
        password,
      });

      logger.info('AuthApi.resetPassword successful', {
        actionType: 'auth_api_reset_password_success',
      });
    } catch (error: any) {
      const message = error.response?.data?.message || 'Password reset failed';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AuthApi.resetPassword failed', {
        statusCode,
        code,
        message,
        actionType: 'auth_api_reset_password_error',
      }, error);

      throw new AuthApiError(message, statusCode, code);
    }
  }

  async loginWithProvider(provider: 'google' | 'microsoft'): Promise<AuthResponse> {
    try {
      logger.info('AuthApi.loginWithProvider called', {
        provider,
        actionType: 'auth_api_oauth_login',
      });

      // For OAuth, we typically redirect to the provider's auth URL
      // This is a simplified implementation - in a real app, you'd handle the OAuth flow
      const response = await apiClient.post<AuthResponse>(`${this.baseUrl}/oauth/${provider}`);

      logger.info('AuthApi.loginWithProvider successful', {
        provider,
        userId: response.data.user.id,
        email: response.data.user.email,
        actionType: 'auth_api_oauth_login_success',
      });

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.message || `${provider} login failed`;
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AuthApi.loginWithProvider failed', {
        provider,
        statusCode,
        code,
        message,
        actionType: 'auth_api_oauth_login_error',
      }, error);

      throw new AuthApiError(message, statusCode, code);
    }
  }

  async getCurrentUser(): Promise<AuthResponse['user']> {
    try {
      logger.info('AuthApi.getCurrentUser called', {
        actionType: 'auth_api_get_current_user',
      });

      const response = await apiClient.get<{ user: AuthResponse['user'] }>(`${this.baseUrl}/me`);

      logger.info('AuthApi.getCurrentUser successful', {
        userId: response.data.user.id,
        email: response.data.user.email,
        actionType: 'auth_api_get_current_user_success',
      });

      return response.data.user;
    } catch (error: any) {
      const message = error.response?.data?.message || 'Failed to get current user';
      const statusCode = error.response?.status;
      const code = error.response?.data?.code;

      logger.error('AuthApi.getCurrentUser failed', {
        statusCode,
        code,
        message,
        actionType: 'auth_api_get_current_user_error',
      }, error);

      throw new AuthApiError(message, statusCode, code);
    }
  }
}

export const authApi = new AuthApi();