/**
 * SDK Exceptions
 */

import { AxiosResponse } from 'axios';

export class MAMSError extends Error {
  public readonly statusCode?: number;
  public readonly response?: AxiosResponse;
  public readonly errorCode?: string;
  public readonly details?: Record<string, any>;
  public readonly requestId?: string;

  constructor(
    message: string,
    statusCode?: number,
    response?: AxiosResponse,
    errorCode?: string,
    details?: Record<string, any>
  ) {
    super(message);
    this.name = 'MAMSError';
    this.statusCode = statusCode;
    this.response = response;
    this.errorCode = errorCode;
    this.details = details || {};
    this.requestId = response?.headers?.['x-request-id'];

    // Maintain proper stack trace
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, MAMSError);
    }
  }
}

export class AuthenticationError extends MAMSError {
  constructor(message: string, statusCode?: number, response?: AxiosResponse, errorCode?: string, details?: Record<string, any>) {
    super(message, statusCode, response, errorCode, details);
    this.name = 'AuthenticationError';
  }
}

export class NotFoundError extends MAMSError {
  constructor(message: string, statusCode?: number, response?: AxiosResponse, errorCode?: string, details?: Record<string, any>) {
    super(message, statusCode, response, errorCode, details);
    this.name = 'NotFoundError';
  }
}

export class ValidationError extends MAMSError {
  public readonly errors: Record<string, any>;

  constructor(
    message: string, 
    errors: Record<string, any> = {}, 
    statusCode?: number, 
    response?: AxiosResponse, 
    errorCode?: string, 
    details?: Record<string, any>
  ) {
    super(message, statusCode, response, errorCode, details);
    this.name = 'ValidationError';
    this.errors = errors;
  }
}

export class RateLimitError extends MAMSError {
  public readonly retryAfter?: number;

  constructor(
    message: string, 
    retryAfter?: number, 
    statusCode?: number, 
    response?: AxiosResponse, 
    errorCode?: string, 
    details?: Record<string, any>
  ) {
    super(message, statusCode, response, errorCode, details);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

export class ServerError extends MAMSError {
  constructor(message: string, statusCode?: number, response?: AxiosResponse, errorCode?: string, details?: Record<string, any>) {
    super(message, statusCode, response, errorCode, details);
    this.name = 'ServerError';
  }
}

export class ConflictError extends MAMSError {
  constructor(message: string, statusCode?: number, response?: AxiosResponse, errorCode?: string, details?: Record<string, any>) {
    super(message, statusCode, response, errorCode, details);
    this.name = 'ConflictError';
  }
}

export class PermissionError extends MAMSError {
  constructor(message: string, statusCode?: number, response?: AxiosResponse, errorCode?: string, details?: Record<string, any>) {
    super(message, statusCode, response, errorCode, details);
    this.name = 'PermissionError';
  }
}

export class NetworkError extends MAMSError {
  constructor(message: string, originalError?: Error) {
    super(message);
    this.name = 'NetworkError';
    this.stack = originalError?.stack;
  }
}

export class TimeoutError extends MAMSError {
  constructor(message: string = 'Request timeout') {
    super(message);
    this.name = 'TimeoutError';
  }
}

export class UploadError extends MAMSError {
  public readonly progress?: number;

  constructor(message: string, progress?: number, statusCode?: number, response?: AxiosResponse) {
    super(message, statusCode, response);
    this.name = 'UploadError';
    this.progress = progress;
  }
}

/**
 * Handle error response from API
 */
export function handleErrorResponse(response: AxiosResponse): never {
  const status = response.status;
  let message = 'Unknown error';
  let errorCode: string | undefined;
  let details: Record<string, any> = {};

  try {
    const errorData = response.data;
    if (errorData?.error) {
      message = errorData.error.message || message;
      errorCode = errorData.error.code;
      details = errorData.error.details || {};
    } else if (errorData?.message) {
      message = errorData.message;
    }
  } catch {
    message = `HTTP ${status}: ${response.statusText}`;
  }

  // Map status codes to specific exceptions
  switch (status) {
    case 401:
      throw new AuthenticationError(message, status, response, errorCode, details);
    case 403:
      throw new PermissionError(message, status, response, errorCode, details);
    case 404:
      throw new NotFoundError(message, status, response, errorCode, details);
    case 409:
      throw new ConflictError(message, status, response, errorCode, details);
    case 422:
      const validationErrors = details.errors || {};
      throw new ValidationError(message, validationErrors, status, response, errorCode, details);
    case 429:
      const retryAfter = response.headers['retry-after'];
      throw new RateLimitError(
        message, 
        retryAfter ? parseInt(retryAfter, 10) : undefined, 
        status, 
        response, 
        errorCode, 
        details
      );
    default:
      if (status >= 500) {
        throw new ServerError(message, status, response, errorCode, details);
      } else {
        throw new MAMSError(message, status, response, errorCode, details);
      }
  }
}