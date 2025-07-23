import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch } from '../store';
import { addNotification } from '../store/slices/uiSlice';
import { clearAuth } from '../store/slices/authSlice';
import { logger } from '../utils/logger';
import { Navigation } from '../router/navigation';

const GlobalErrorHandler: React.FC = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  useEffect(() => {
    // Handle global fetch errors
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      try {
        const response = await originalFetch(...args);
        
        // Log successful API calls
        if (response.ok) {
          logger.info('API call successful', {
            url: args[0],
            status: response.status,
            method: args[1]?.method || 'GET',
            actionType: 'api_call'
          });
        } else {
          // Log failed API calls
          logger.error('API call failed', {
            url: args[0],
            status: response.status,
            statusText: response.statusText,
            method: args[1]?.method || 'GET',
            actionType: 'api_call'
          });

          // Handle specific error cases
          if (response.status === 401) {
            dispatch(clearAuth());
            navigate(Navigation.login());
            dispatch(addNotification({
              type: 'error',
              message: 'Your session has expired. Please log in again.',
              duration: 5000,
            }));
          } else if (response.status === 403) {
            dispatch(addNotification({
              type: 'error',
              message: 'You do not have permission to perform this action.',
              duration: 5000,
            }));
          } else if (response.status >= 500) {
            dispatch(addNotification({
              type: 'error',
              message: 'Server error. Please try again later.',
              duration: 5000,
            }));
          }
        }
        
        return response;
      } catch (error) {
        logger.error('Network error', {
          url: args[0],
          method: args[1]?.method || 'GET',
          actionType: 'network_error'
        }, error);
        
        dispatch(addNotification({
          type: 'error',
          message: 'Network error. Please check your connection.',
          duration: 5000,
        }));
        
        throw error;
      }
    };

    // Handle uncaught errors
    const handleError = (event: ErrorEvent) => {
      logger.error('Uncaught error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        stack: event.error?.stack,
        actionType: 'uncaught_error'
      }, event.error);

      dispatch(addNotification({
        type: 'error',
        message: 'An unexpected error occurred.',
        duration: 5000,
      }));
    };

    // Handle unhandled promise rejections
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      logger.error('Unhandled promise rejection', {
        reason: event.reason,
        promise: event.promise,
        stack: event.reason?.stack,
        actionType: 'unhandled_rejection'
      }, event.reason);

      dispatch(addNotification({
        type: 'error',
        message: 'An unexpected error occurred.',
        duration: 5000,
      }));
    };

    // Handle online/offline events
    const handleOnline = () => {
      logger.info('Network connection restored', { actionType: 'network_status' });
      dispatch(addNotification({
        type: 'success',
        message: 'Network connection restored.',
        duration: 3000,
      }));
    };

    const handleOffline = () => {
      logger.warn('Network connection lost', { actionType: 'network_status' });
      dispatch(addNotification({
        type: 'warning',
        message: 'Network connection lost. Some features may not work.',
        duration: 5000,
      }));
    };

    // Handle visibility change for performance monitoring
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        logger.info('Page became visible', { actionType: 'page_visibility' });
      } else {
        logger.info('Page became hidden', { actionType: 'page_visibility' });
      }
    };

    // Handle page unload for cleanup
    const handleBeforeUnload = () => {
      logger.info('Page unloading', { actionType: 'page_unload' });
      
      // Flush any pending logs
      logger.flush();
    };

    // Handle console errors
    const originalConsoleError = console.error;
    console.error = (...args) => {
      originalConsoleError.apply(console, args);
      
      // Log console errors
      logger.error('Console error', {
        args: args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : String(arg)),
        actionType: 'console_error'
      });
    };

    // Handle console warnings
    const originalConsoleWarn = console.warn;
    console.warn = (...args) => {
      originalConsoleWarn.apply(console, args);
      
      // Log console warnings
      logger.warn('Console warning', {
        args: args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : String(arg)),
        actionType: 'console_warning'
      });
    };

    // Add event listeners
    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', handleBeforeUnload);

    // Initial network status check
    if (!navigator.onLine) {
      handleOffline();
    }

    // Cleanup function
    return () => {
      // Restore original functions
      window.fetch = originalFetch;
      console.error = originalConsoleError;
      console.warn = originalConsoleWarn;
      
      // Remove event listeners
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [dispatch, navigate]);

  return null; // This component doesn't render anything
};

export default GlobalErrorHandler;