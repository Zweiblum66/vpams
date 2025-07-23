/**
 * SDK Configuration
 */

export interface Config {
  // API settings
  baseURL: string;
  apiVersion: string;
  timeout: number;
  
  // Authentication
  apiKey?: string;
  jwt?: string;
  
  // Retry settings
  maxRetries: number;
  retryDelay: number;
  retryStatusCodes: number[];
  
  // File operations
  chunkSize: number;
  maxUploadSize: number;
  
  // Request settings
  headers: Record<string, string>;
  validateStatus: (status: number) => boolean;
  
  // Advanced settings
  transformRequest?: Array<(data: any, headers: Record<string, string>) => any>;
  transformResponse?: Array<(data: any) => any>;
}

export const defaultConfig: Config = {
  baseURL: 'https://api.mams.io',
  apiVersion: 'v1',
  timeout: 30000,
  
  maxRetries: 3,
  retryDelay: 1000,
  retryStatusCodes: [429, 500, 502, 503, 504],
  
  chunkSize: 8 * 1024 * 1024, // 8MB
  maxUploadSize: 5 * 1024 * 1024 * 1024, // 5GB
  
  headers: {
    'Content-Type': 'application/json',
    'User-Agent': 'MAMS-SDK-JS/1.0.0'
  },
  
  validateStatus: (status: number) => status >= 200 && status < 300
};

export function createConfig(options: Partial<Config>): Config {
  return {
    ...defaultConfig,
    ...options,
    headers: {
      ...defaultConfig.headers,
      ...options.headers
    }
  };
}