import { createLazyComponent, registerRoutePreload } from '../utils/lazyLoading';
import { ROUTES } from './routes';

/**
 * Lazy loaded page components with route preloading
 */

// Auth pages
export const LazyLoginPage = createLazyComponent(
  () => import('../pages/auth/LoginPage'),
  { preload: true } // Preload login page as it's commonly accessed
);

export const LazyRegisterPage = createLazyComponent(
  () => import('../pages/auth/RegisterPage')
);

export const LazyForgotPasswordPage = createLazyComponent(
  () => import('../pages/auth/ForgotPasswordPage')
);

export const LazyResetPasswordPage = createLazyComponent(
  () => import('../pages/auth/ResetPasswordPage')
);

// Main pages
export const LazyDashboardPage = createLazyComponent(
  () => import('../pages/DashboardPage'),
  { preload: true } // Preload dashboard as it's the main landing page
);

// Asset Management pages
export const LazyAssetBrowser = createLazyComponent(
  () => import('../pages/AssetBrowser')
);

export const LazyAssetDetail = createLazyComponent(
  () => import('../pages/AssetDetail')
);

export const LazyAssetUpload = createLazyComponent(
  () => import('../pages/AssetUpload')
);

export const LazyAdvancedAssetBrowser = createLazyComponent(
  () => import('../pages/AdvancedAssetBrowser')
);

// Project Management pages
export const LazyProjectBrowser = createLazyComponent(
  () => import('../pages/ProjectBrowser')
);

export const LazyProjectDetail = createLazyComponent(
  () => import('../pages/ProjectDetail')
);

export const LazyShotlistPage = createLazyComponent(
  () => import('../pages/ShotlistPage')
);

// Search page
export const LazySearchPage = createLazyComponent(
  () => import('../pages/SearchPage')
);

// Workflow pages
export const LazyWorkflowDesigner = createLazyComponent(
  () => import('../pages/WorkflowDesigner')
);

export const LazyWorkflowMarketplace = createLazyComponent(
  () => import('../pages/WorkflowMarketplace')
);

// Admin pages
export const LazyUserManagement = createLazyComponent(
  () => import('../pages/UserManagement')
);

export const LazyRoleManagement = createLazyComponent(
  () => import('../pages/RoleManagement')
);

export const LazyGroupManagement = createLazyComponent(
  () => import('../pages/GroupManagement')
);

export const LazyPermissionManagement = createLazyComponent(
  () => import('../pages/PermissionManagement')
);

export const LazyInheritanceAnalysis = createLazyComponent(
  () => import('../pages/InheritanceAnalysis')
);

// User pages
export const LazyProfile = createLazyComponent(
  () => import('../pages/Profile')
);

export const LazySettings = createLazyComponent(
  () => import('../pages/Settings')
);

// Tenant Management pages
export const LazyTenantManagement = createLazyComponent(
  () => import('../pages/TenantManagement')
);

export const LazyTenantDetail = createLazyComponent(
  () => import('../pages/TenantDetail')
);

// Error pages
export const LazyNotFoundPage = createLazyComponent(
  () => import('../pages/ErrorPages/NotFoundPage')
);

export const LazyUnauthorizedPage = createLazyComponent(
  () => import('../pages/ErrorPages/UnauthorizedPage')
);

export const LazyServerErrorPage = createLazyComponent(
  () => import('../pages/ErrorPages/ServerErrorPage')
);

// Register route preloading
registerRoutePreload(ROUTES.DASHBOARD, () => import('../pages/DashboardPage'));
registerRoutePreload(ROUTES.ASSETS, () => import('../pages/AssetBrowser'));
registerRoutePreload(ROUTES.PROJECTS, () => import('../pages/ProjectBrowser'));
registerRoutePreload(ROUTES.SEARCH, () => import('../pages/SearchPage'));

/**
 * Preload critical routes based on user role
 */
export function preloadCriticalRoutes(userRole?: string) {
  // Always preload dashboard
  import('../pages/DashboardPage');
  
  // Preload based on role
  if (userRole === 'admin' || userRole === 'superuser') {
    import('../pages/UserManagement');
    import('../pages/RoleManagement');
  }
  
  // Preload commonly used pages
  import('../pages/AssetBrowser');
  import('../pages/SearchPage');
}