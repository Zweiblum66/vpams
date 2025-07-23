import React, { createContext, useContext, useEffect, ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';
import { User } from '../types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | undefined;
  login: (credentials: any) => Promise<any>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  clearAuthError: () => void;
  setReturnPath: (path: string) => void;
  hasPermission: (permission: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const auth = useAuth();

  // Set up automatic token refresh check
  useEffect(() => {
    if (!auth.isAuthenticated) return;

    // Check token expiration every 5 minutes
    const interval = setInterval(() => {
      auth.checkTokenExpiration();
    }, 5 * 60 * 1000);

    // Initial check
    auth.checkTokenExpiration();

    return () => clearInterval(interval);
  }, [auth.isAuthenticated, auth.checkTokenExpiration]);

  // Handle page visibility change to refresh token when page becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && auth.isAuthenticated) {
        auth.checkTokenExpiration();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [auth.isAuthenticated, auth.checkTokenExpiration]);

  // Handle beforeunload to clear sensitive data
  useEffect(() => {
    const handleBeforeUnload = () => {
      // Clear return path on page unload
      sessionStorage.removeItem('returnPath');
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, []);

  return (
    <AuthContext.Provider value={auth}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuthContext = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
};