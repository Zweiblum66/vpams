import { useCallback, useEffect, useRef } from 'react';
import { useAppDispatch } from '../store';
import { addNotification } from '../store/slices/uiSlice';
import { logger } from '../utils/logger';

export interface ErrorHandlerOptions {
  showNotification?: boolean;
  logError?: boolean;
  notificationMessage?: string;
  notificationDuration?: number;
  context?: Record<string, any>;
}

export interface AsyncErrorHandler {
  execute: <T>(promise: Promise<T>, options?: ErrorHandlerOptions) => Promise<T | null>;
  handleError: (error: any, options?: ErrorHandlerOptions) => void;
  isLoading: boolean;
  error: any;
  clearError: () => void;
}

export const useErrorHandler = (): AsyncErrorHandler => {
  const dispatch = useAppDispatch();
  const isLoadingRef = useRef<boolean>(false);
  const errorRef = useRef<any>(null);

  const handleError = useCallback((error: any, options: ErrorHandlerOptions = {}) => {
    const {
      showNotification = true,
      logError = true,
      notificationMessage,
      notificationDuration = 5000,
      context = {}
    } = options;

    errorRef.current = error;

    // Log the error
    if (logError) {
      const errorMessage = error?.message || error?.toString() || 'Unknown error';
      const errorContext = {
        ...context,
        errorType: error?.name || 'Error',
        statusCode: error?.status || error?.response?.status,
        url: error?.config?.url || error?.url,
        method: error?.config?.method || error?.method,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url_current: window.location.href,
      };

      logger.error('Error handled by useErrorHandler', errorContext, error);
    }

    // Show notification
    if (showNotification) {
      let message = notificationMessage;
      
      if (!message) {
        if (error?.response?.data?.message) {
          message = error.response.data.message;
        } else if (error?.message) {
          message = error.message;
        } else if (error?.status) {
          message = `Request failed with status ${error.status}`;
        } else {
          message = 'An unexpected error occurred';
        }
      }

      dispatch(addNotification({
        type: 'error',
        message,
        duration: notificationDuration,
      }));
    }
  }, [dispatch]);

  const execute = useCallback(async <T>(
    promise: Promise<T>,
    options: ErrorHandlerOptions = {}
  ): Promise<T | null> => {
    isLoadingRef.current = true;
    errorRef.current = null;

    try {
      const result = await promise;
      isLoadingRef.current = false;
      return result;
    } catch (error) {
      isLoadingRef.current = false;
      handleError(error, options);
      return null;
    }
  }, [handleError]);

  const clearError = useCallback(() => {
    errorRef.current = null;
  }, []);

  return {
    execute,
    handleError,
    isLoading: isLoadingRef.current,
    error: errorRef.current,
    clearError,
  };
};

// Hook for form error handling
export const useFormErrorHandler = () => {
  const { handleError } = useErrorHandler();

  const handleFormError = useCallback((error: any, fieldName?: string) => {
    // Handle validation errors
    if (error?.response?.data?.errors) {
      const errors = error.response.data.errors;
      
      // Handle field-specific errors
      if (fieldName && errors[fieldName]) {
        return errors[fieldName][0]; // Return first error for the field
      }
      
      // Handle general validation errors
      const firstError = Object.values(errors)[0];
      if (Array.isArray(firstError)) {
        handleError(new Error(firstError[0]), { 
          showNotification: true,
          context: { errorType: 'validation', fieldName }
        });
      }
    } else {
      handleError(error, { 
        showNotification: true,
        context: { errorType: 'form', fieldName }
      });
    }
  }, [handleError]);

  return { handleFormError };
};

// Hook for API error handling
export const useApiErrorHandler = () => {
  const { handleError } = useErrorHandler();

  const handleApiError = useCallback((error: any, endpoint?: string) => {
    const context = {
      errorType: 'api',
      endpoint,
      statusCode: error?.response?.status,
      statusText: error?.response?.statusText,
    };

    // Handle different HTTP status codes
    let message = 'An error occurred while processing your request';
    
    if (error?.response?.status) {
      switch (error.response.status) {
        case 400:
          message = 'Bad request. Please check your input and try again.';
          break;
        case 401:
          message = 'You are not authorized to perform this action.';
          break;
        case 403:
          message = 'You do not have permission to access this resource.';
          break;
        case 404:
          message = 'The requested resource was not found.';
          break;
        case 409:
          message = 'A conflict occurred. The resource may already exist.';
          break;
        case 422:
          message = 'The data provided is invalid. Please check and try again.';
          break;
        case 429:
          message = 'Too many requests. Please wait a moment and try again.';
          break;
        case 500:
          message = 'Internal server error. Please try again later.';
          break;
        case 502:
          message = 'Service temporarily unavailable. Please try again later.';
          break;
        case 503:
          message = 'Service is currently unavailable. Please try again later.';
          break;
        default:
          message = `Request failed with status ${error.response.status}`;
      }
    } else if (error?.code === 'NETWORK_ERROR') {
      message = 'Network error. Please check your connection and try again.';
    } else if (error?.code === 'TIMEOUT') {
      message = 'Request timed out. Please try again.';
    }

    handleError(error, { 
      showNotification: true,
      notificationMessage: message,
      context
    });
  }, [handleError]);

  return { handleApiError };
};

// Hook for component error handling
export const useComponentErrorHandler = (componentName: string) => {
  const { handleError } = useErrorHandler();

  const handleComponentError = useCallback((error: any, action?: string) => {
    handleError(error, {
      showNotification: false, // Don't show notification for component errors
      logError: true,
      context: {
        errorType: 'component',
        componentName,
        action,
      }
    });
  }, [handleError, componentName]);

  // Auto-log component mount/unmount errors
  useEffect(() => {
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      handleComponentError(event.reason, 'unhandled_rejection');
    };

    window.addEventListener('unhandledrejection', handleUnhandledRejection);
    
    return () => {
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [handleComponentError]);

  return { handleComponentError };
};