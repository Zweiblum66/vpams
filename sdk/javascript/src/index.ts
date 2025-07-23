/**
 * MAMS JavaScript/TypeScript SDK
 * 
 * Official SDK for MAMS (Media Asset Management System)
 */

// Main client
export { MAMSClient } from './client';

// Authentication
export { 
  APIKeyAuth, 
  JWTAuth, 
  OAuth2Provider,
  type AuthProvider 
} from './auth';

// Configuration
export { type Config } from './config';

// Types
export * from './types';

// Exceptions
export * from './exceptions';

// Resources (for advanced usage)
export { AssetsResource } from './resources/assets';
export { ProjectsResource } from './resources/projects';
export { WorkflowsResource } from './resources/workflows';
export { IntegrationsResource } from './resources/integrations';
export { UsersResource } from './resources/users';
export { MetadataResource } from './resources/metadata';
export { SearchResource } from './resources/search';

// Version
export const VERSION = '1.0.0';