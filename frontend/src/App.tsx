import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import { useAppDispatch, useAppSelector } from './store';
import { clearAuth } from './store/slices/authSlice';
import { addNotification } from './store/slices/uiSlice';
import { useGetCurrentUserQuery } from './store/api/authApi';

// Router components
import { ROUTES } from './router/routes';
import RouteGuard from './router/RouteGuard';

// Layout components
import { Layout } from './components/layout';
import { LoginPage, RegisterPage, ForgotPasswordPage, ResetPasswordPage } from './pages/auth';
import DashboardPage from './pages/DashboardPage';
import NotFoundPage from './pages/ErrorPages/NotFoundPage';
import UnauthorizedPage from './pages/ErrorPages/UnauthorizedPage';
import ServerErrorPage from './pages/ErrorPages/ServerErrorPage';

// Admin pages
import UserManagement from './pages/UserManagement';
import RoleManagement from './pages/RoleManagement';
import GroupManagement from './pages/GroupManagement';
import PermissionManagement from './pages/PermissionManagement';
import InheritanceAnalysis from './pages/InheritanceAnalysis';
import TenantManagement from './pages/TenantManagement';
import TenantDetail from './pages/TenantDetail';
import Dashboard from './pages/Dashboard';
import Profile from './pages/Profile';
import Settings from './pages/Settings';

// MAMS pages
import AssetBrowser from './pages/AssetBrowser';
import AssetDetail from './pages/AssetDetail';
import AssetUpload from './pages/AssetUpload';
import AdvancedAssetBrowser from './pages/AdvancedAssetBrowser';
import ProjectBrowser from './pages/ProjectBrowser';
import ProjectDetail from './pages/ProjectDetail';
import SearchPage from './pages/SearchPage';
import WorkflowDesigner from './pages/WorkflowDesigner';
import WorkflowMarketplace from './pages/WorkflowMarketplace';
import ShotlistPage from './pages/ShotlistPage';

// Components
import ProtectedRoute from './components/ProtectedRoute';
import NotificationContainer from './components/NotificationContainer';
import ErrorBoundary from './components/ErrorBoundary';
import { AuthProvider } from './components/AuthProvider';
import SessionTimeout from './components/SessionTimeout';
import GlobalErrorHandler from './components/GlobalErrorHandler';
import DebugToggle from './components/DebugToggle';

const App: React.FC = () => {
  const dispatch = useAppDispatch();
  const { isAuthenticated, token } = useAppSelector(state => state.auth);

  // Use RTK Query to get current user if token exists
  const {
    data: currentUser,
    isLoading,
    isError,
    error,
  } = useGetCurrentUserQuery(undefined, {
    skip: !token || !isAuthenticated,
  });

  useEffect(() => {
    // Handle auth errors
    if (isError && token) {
      dispatch(clearAuth());
      dispatch(addNotification({
        type: 'error',
        message: 'Session expired. Please login again.',
      }));
    }
  }, [dispatch, isError, token]);

  // Show loading spinner while checking authentication
  if (isLoading && token) {
    return (
      <Box 
        className="full-height flex-center"
        sx={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center',
          height: '100vh'
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <ErrorBoundary>
      <AuthProvider>
        <div className="App">
          <Routes>
          {/* Public routes */}
          <Route 
            path={ROUTES.LOGIN} 
            element={
              isAuthenticated ? <Navigate to={ROUTES.DASHBOARD} replace /> : <LoginPage />
            } 
          />
          <Route 
            path={ROUTES.REGISTER} 
            element={
              isAuthenticated ? <Navigate to={ROUTES.DASHBOARD} replace /> : <RegisterPage />
            } 
          />
          <Route 
            path={ROUTES.FORGOT_PASSWORD} 
            element={
              isAuthenticated ? <Navigate to={ROUTES.DASHBOARD} replace /> : <ForgotPasswordPage />
            } 
          />
          <Route 
            path={ROUTES.RESET_PASSWORD} 
            element={
              isAuthenticated ? <Navigate to={ROUTES.DASHBOARD} replace /> : <ResetPasswordPage />
            } 
          />
          
          {/* Error pages */}
          <Route path={ROUTES.UNAUTHORIZED} element={<UnauthorizedPage />} />
          <Route path={ROUTES.SERVER_ERROR} element={<ServerErrorPage />} />
          
          {/* Protected routes */}
          <Route 
            path="/" 
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to={ROUTES.DASHBOARD} replace />} />
            
            {/* Dashboard */}
            <Route path="dashboard" element={
              <RouteGuard requireAuth>
                <DashboardPage />
              </RouteGuard>
            } />
            
            {/* Asset Management */}
            <Route path="assets" element={
              <RouteGuard requireAuth requiredPermissions={['assets.read']}>
                <AssetBrowser />
              </RouteGuard>
            } />
            <Route path="assets/upload" element={
              <RouteGuard requireAuth requiredPermissions={['assets.create']}>
                <AssetUpload />
              </RouteGuard>
            } />
            <Route path="assets/advanced" element={
              <RouteGuard requireAuth requiredPermissions={['assets.read']}>
                <AdvancedAssetBrowser />
              </RouteGuard>
            } />
            <Route path="assets/:id" element={
              <RouteGuard requireAuth requiredPermissions={['assets.read']}>
                <AssetDetail />
              </RouteGuard>
            } />
            
            {/* Project Management */}
            <Route path="projects" element={
              <RouteGuard requireAuth requiredPermissions={['projects.read']}>
                <ProjectBrowser />
              </RouteGuard>
            } />
            <Route path="projects/:id" element={
              <RouteGuard requireAuth requiredPermissions={['projects.read']}>
                <ProjectDetail />
              </RouteGuard>
            } />
            <Route path="projects/:projectId/shotlists/:shotlistId" element={
              <RouteGuard requireAuth requiredPermissions={['projects.read']}>
                <ShotlistPage />
              </RouteGuard>
            } />
            
            {/* Search */}
            <Route path="search" element={
              <RouteGuard requireAuth requiredPermissions={['assets.read']}>
                <SearchPage />
              </RouteGuard>
            } />
            
            {/* Workflow Management */}
            <Route path="workflows" element={
              <RouteGuard requireAuth requiredPermissions={['workflow.read']}>
                <WorkflowMarketplace />
              </RouteGuard>
            } />
            <Route path="workflows/designer" element={
              <RouteGuard requireAuth requiredPermissions={['workflow.create']}>
                <WorkflowDesigner />
              </RouteGuard>
            } />
            <Route path="workflows/designer/:workflowId" element={
              <RouteGuard requireAuth requiredPermissions={['workflow.update']}>
                <WorkflowDesigner />
              </RouteGuard>
            } />
            <Route path="workflows/templates" element={
              <RouteGuard requireAuth requiredPermissions={['workflow.read']}>
                <WorkflowMarketplace />
              </RouteGuard>
            } />
            
            {/* Admin */}
            <Route path="users" element={
              <RouteGuard requireAuth requireSuperuser>
                <UserManagement />
              </RouteGuard>
            } />
            <Route path="roles" element={
              <RouteGuard requireAuth requireSuperuser>
                <RoleManagement />
              </RouteGuard>
            } />
            <Route path="groups" element={
              <RouteGuard requireAuth requireSuperuser>
                <GroupManagement />
              </RouteGuard>
            } />
            <Route path="permissions" element={
              <RouteGuard requireAuth requireSuperuser>
                <PermissionManagement />
              </RouteGuard>
            } />
            <Route path="inheritance" element={
              <RouteGuard requireAuth requireSuperuser>
                <InheritanceAnalysis />
              </RouteGuard>
            } />
            <Route path="tenants" element={
              <RouteGuard requireAuth requireSuperuser>
                <TenantManagement />
              </RouteGuard>
            } />
            <Route path="tenants/:tenantId" element={
              <RouteGuard requireAuth requireSuperuser>
                <TenantDetail />
              </RouteGuard>
            } />
            <Route path="profile" element={
              <RouteGuard requireAuth>
                <Profile />
              </RouteGuard>
            } />
            <Route path="settings" element={
              <RouteGuard requireAuth>
                <Settings />
              </RouteGuard>
            } />
          </Route>
          
          {/* Catch all route */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
        
          <NotificationContainer />
          <SessionTimeout />
          <GlobalErrorHandler />
          <DebugToggle />
        </div>
      </AuthProvider>
    </ErrorBoundary>
  );
};

export default App;