import React from 'react';
import { FetchBaseQueryError } from '@reduxjs/toolkit/query';
import { SerializedError } from '@reduxjs/toolkit';
import { Alert, AlertTitle } from '@mui/material';

interface RTKQueryErrorProps {
  error: FetchBaseQueryError | SerializedError | undefined;
  title?: string;
  showDetails?: boolean;
}

const RTKQueryErrorHandler: React.FC<RTKQueryErrorProps> = ({ 
  error, 
  title = 'An error occurred',
  showDetails = false
}) => {
  if (!error) return null;

  const getErrorMessage = (error: FetchBaseQueryError | SerializedError): string => {
    if ('status' in error) {
      // FetchBaseQueryError
      if (error.status === 'FETCH_ERROR') {
        return 'Network error. Please check your connection.';
      }
      if (error.status === 'TIMEOUT_ERROR') {
        return 'Request timed out. Please try again.';
      }
      if (error.status === 'PARSING_ERROR') {
        return 'Unable to parse server response.';
      }
      if (typeof error.status === 'number') {
        const data = error.data as any;
        if (data?.error?.message) {
          return data.error.message;
        }
        if (data?.message) {
          return data.message;
        }
        if (data?.detail) {
          return data.detail;
        }
        // Default messages for common HTTP status codes
        switch (error.status) {
          case 400:
            return 'Bad request. Please check your input.';
          case 401:
            return 'Unauthorized. Please log in again.';
          case 403:
            return 'Forbidden. You don\'t have permission to access this resource.';
          case 404:
            return 'Resource not found.';
          case 409:
            return 'Conflict. The resource already exists or is in use.';
          case 422:
            return 'Validation error. Please check your input.';
          case 429:
            return 'Too many requests. Please wait before trying again.';
          case 500:
            return 'Internal server error. Please try again later.';
          case 502:
            return 'Bad gateway. The server is temporarily unavailable.';
          case 503:
            return 'Service unavailable. Please try again later.';
          default:
            return `Request failed with status ${error.status}`;
        }
      }
      return 'An unknown error occurred';
    } else {
      // SerializedError
      return error.message || 'An unknown error occurred';
    }
  };

  const getErrorDetails = (error: FetchBaseQueryError | SerializedError): string | null => {
    if (!showDetails) return null;
    
    if ('status' in error) {
      return `Status: ${error.status}\n${JSON.stringify(error.data, null, 2)}`;
    } else {
      return `Code: ${error.code}\nName: ${error.name}\nStack: ${error.stack}`;
    }
  };

  const getSeverity = (error: FetchBaseQueryError | SerializedError): 'error' | 'warning' => {
    if ('status' in error) {
      if (typeof error.status === 'number' && error.status >= 500) {
        return 'error';
      }
      if (error.status === 'FETCH_ERROR' || error.status === 'TIMEOUT_ERROR') {
        return 'error';
      }
      return 'warning';
    }
    return 'error';
  };

  const message = getErrorMessage(error);
  const details = getErrorDetails(error);
  const severity = getSeverity(error);

  return (
    <Alert severity={severity} sx={{ mb: 2 }}>
      <AlertTitle>{title}</AlertTitle>
      {message}
      {details && (
        <pre style={{ 
          marginTop: 8, 
          fontSize: '0.75rem', 
          backgroundColor: 'rgba(0,0,0,0.05)',
          padding: '8px',
          borderRadius: '4px',
          overflow: 'auto'
        }}>
          {details}
        </pre>
      )}
    </Alert>
  );
};

export default RTKQueryErrorHandler;