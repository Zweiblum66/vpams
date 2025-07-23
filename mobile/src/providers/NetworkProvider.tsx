/**
 * Network Provider
 * 
 * Provides network monitoring and offline functionality
 * initialization for the entire app.
 */

import React, {useEffect} from 'react';
import {useDispatch} from 'react-redux';
import {initializeOfflineMode} from '@/store/slices/offlineSlice';
import {initializeNotifications} from '@/store/slices/notificationsSlice';

interface NetworkProviderProps {
  children: React.ReactNode;
}

export const NetworkProvider: React.FC<NetworkProviderProps> = ({children}) => {
  const dispatch = useDispatch();

  useEffect(() => {
    // Initialize offline mode and network monitoring
    dispatch(initializeOfflineMode());
    
    // Initialize push notifications
    dispatch(initializeNotifications());
  }, [dispatch]);

  return <>{children}</>;
};