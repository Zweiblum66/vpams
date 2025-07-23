import { useState, useEffect } from 'react';
import { MAMSClient } from '../services/mamsClient';
import { User } from '../types';

export const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const currentUser = await MAMSClient.getInstance().getCurrentUser();
      setUser(currentUser);
      setIsAuthenticated(true);
    } catch (err) {
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    const loggedInUser = await MAMSClient.getInstance().login(username, password);
    setUser(loggedInUser);
    setIsAuthenticated(true);
    
    // Save credentials if enabled
    const settings = JSON.parse(localStorage.getItem('mams_settings') || '{}');
    if (settings.rememberCredentials) {
      localStorage.setItem('mams_credentials', JSON.stringify({ username, password }));
    }
  };

  const logout = async () => {
    await MAMSClient.getInstance().logout();
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('mams_credentials');
  };

  return {
    isAuthenticated,
    user,
    loading,
    login,
    logout,
  };
};