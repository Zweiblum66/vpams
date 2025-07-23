import { baseApi } from './baseApi';
import { LoginRequest, LoginResponse, User } from '../../types';

export const authApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    login: builder.mutation<LoginResponse, LoginRequest>({
      query: (credentials) => ({
        url: '/auth/login',
        method: 'POST',
        body: credentials,
      }),
    }),

    logout: builder.mutation<void, void>({
      query: () => ({
        url: '/auth/logout',
        method: 'POST',
      }),
    }),

    getCurrentUser: builder.query<User, void>({
      query: () => ({
        url: '/auth/me',
        method: 'GET',
      }),
      providesTags: ['User'],
    }),

    refreshToken: builder.mutation<{ access_token: string }, void>({
      query: () => ({
        url: '/auth/refresh',
        method: 'POST',
      }),
    }),

    register: builder.mutation<User, {
      email: string;
      password: string;
      confirm_password: string;
      first_name: string;
      last_name: string;
      username?: string;
    }>({
      query: (userData) => ({
        url: '/auth/register',
        method: 'POST',
        body: userData,
      }),
    }),

    requestPasswordReset: builder.mutation<void, { email: string }>({
      query: (data) => ({
        url: '/auth/password-reset/request',
        method: 'POST',
        body: data,
      }),
    }),

    resetPassword: builder.mutation<void, {
      token: string;
      new_password: string;
      confirm_password: string;
    }>({
      query: (data) => ({
        url: '/auth/password-reset/confirm',
        method: 'POST',
        body: data,
      }),
    }),

    changePassword: builder.mutation<void, {
      current_password: string;
      new_password: string;
      confirm_password: string;
    }>({
      query: (data) => ({
        url: '/auth/password-change',
        method: 'POST',
        body: data,
      }),
    }),

    verifyEmail: builder.mutation<void, { token: string }>({
      query: (data) => ({
        url: '/auth/verify-email',
        method: 'POST',
        body: data,
      }),
    }),

    resendVerificationEmail: builder.mutation<void, { email: string }>({
      query: (data) => ({
        url: '/auth/resend-verification',
        method: 'POST',
        body: data,
      }),
    }),

    // MFA endpoints
    enableMFA: builder.mutation<{ secret: string; qr_code: string }, void>({
      query: () => ({
        url: '/auth/mfa/enable',
        method: 'POST',
      }),
    }),

    confirmMFA: builder.mutation<{ backup_codes: string[] }, { token: string }>({
      query: (data) => ({
        url: '/auth/mfa/confirm',
        method: 'POST',
        body: data,
      }),
    }),

    disableMFA: builder.mutation<void, { password: string }>({
      query: (data) => ({
        url: '/auth/mfa/disable',
        method: 'POST',
        body: data,
      }),
    }),

    verifyMFA: builder.mutation<{ access_token: string }, { token: string }>({
      query: (data) => ({
        url: '/auth/mfa/verify',
        method: 'POST',
        body: data,
      }),
    }),

    generateBackupCodes: builder.mutation<{ backup_codes: string[] }, void>({
      query: () => ({
        url: '/auth/mfa/backup-codes',
        method: 'POST',
      }),
    }),

    // External auth endpoints
    getExternalAuthProviders: builder.query<Array<{
      name: string;
      display_name: string;
      auth_url: string;
      enabled: boolean;
    }>, void>({
      query: () => ({
        url: '/auth/external/providers',
        method: 'GET',
      }),
    }),

    initiateExternalAuth: builder.mutation<{ auth_url: string }, { provider: string }>({
      query: ({ provider }) => ({
        url: `/auth/external/${provider}/initiate`,
        method: 'POST',
      }),
    }),

    completeExternalAuth: builder.mutation<LoginResponse, {
      provider: string;
      code: string;
      state?: string;
    }>({
      query: ({ provider, code, state }) => ({
        url: `/auth/external/${provider}/callback`,
        method: 'POST',
        body: { code, state },
      }),
    }),

    linkExternalAccount: builder.mutation<void, {
      provider: string;
      code: string;
    }>({
      query: ({ provider, code }) => ({
        url: `/auth/external/${provider}/link`,
        method: 'POST',
        body: { code },
      }),
    }),

    unlinkExternalAccount: builder.mutation<void, { provider: string }>({
      query: ({ provider }) => ({
        url: `/auth/external/${provider}/unlink`,
        method: 'POST',
      }),
    }),
  }),
});

export const {
  useLoginMutation,
  useLogoutMutation,
  useGetCurrentUserQuery,
  useRefreshTokenMutation,
  useRegisterMutation,
  useRequestPasswordResetMutation,
  useResetPasswordMutation,
  useChangePasswordMutation,
  useVerifyEmailMutation,
  useResendVerificationEmailMutation,
  useEnableMFAMutation,
  useConfirmMFAMutation,
  useDisableMFAMutation,
  useVerifyMFAMutation,
  useGenerateBackupCodesMutation,
  useGetExternalAuthProvidersQuery,
  useInitiateExternalAuthMutation,
  useCompleteExternalAuthMutation,
  useLinkExternalAccountMutation,
  useUnlinkExternalAccountMutation,
} = authApi;