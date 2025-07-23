/**
 * Auth Provider
 * 
 * Provides authentication context and state management
 * for the entire app.
 */

import React, {useEffect} from 'react';
import {useDispatch, useSelector} from 'react-redux';
import {AppState} from '@/types';
import {loadStoredAuth} from '@/store/slices/authSlice';

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({children}) => {
  const dispatch = useDispatch();
  const {isAuthenticated, token} = useSelector((state: AppState) => state.auth);

  useEffect(() => {
    // Load stored authentication on app start
    dispatch(loadStoredAuth());
  }, [dispatch]);

  return <>{children}</>;
};