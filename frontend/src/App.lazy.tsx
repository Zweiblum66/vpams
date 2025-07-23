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

// Lazy loaded components
import { LazyLoadWrapper } from './utils/lazyLoading';
import * as LazyPages from './router/lazyRoutes';
import { preloadCriticalRoutes } from './router/lazyRoutes';

// Non-lazy loaded critical components
import { Layout } from './components/layout';
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

  useEffect(() => {
    // Preload critical routes after authentication
    if (isAuthenticated && currentUser) {
      preloadCriticalRoutes(currentUser.role);
    }
  }, [isAuthenticated, currentUser]);

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
            {/* Public routes with lazy loading */}
            <Route 
              path={ROUTES.LOGIN} 
              element={
                isAuthenticated ? (
                  <Navigate to={ROUTES.DASHBOARD} replace />
                ) : (
                  <LazyLoadWrapper>
                    <LazyPages.LazyLoginPage />
                  </LazyLoadWrapper>
                )
              } 
            />
            <Route 
              path={ROUTES.REGISTER} 
              element={
                isAuthenticated ? (
                  <Navigate to={ROUTES.DASHBOARD} replace />
                ) : (
                  <LazyLoadWrapper>
                    <LazyPages.LazyRegisterPage />
                  </LazyLoadWrapper>
                )
              } 
            />
            <Route 
              path={ROUTES.FORGOT_PASSWORD} 
              element={
                isAuthenticated ? (
                  <Navigate to={ROUTES.DASHBOARD} replace />
                ) : (
                  <LazyLoadWrapper>
                    <LazyPages.LazyForgotPasswordPage />
                  </LazyLoadWrapper>
                )
              } 
            />
            <Route 
              path={ROUTES.RESET_PASSWORD} 
              element={
                isAuthenticated ? (
                  <Navigate to={ROUTES.DASHBOARD} replace />
                ) : (
                  <LazyLoadWrapper>
                    <LazyPages.LazyResetPasswordPage />
                  </LazyLoadWrapper>
                )
              } 
            />
            
            {/* Error pages with lazy loading */}
            <Route 
              path={ROUTES.UNAUTHORIZED} 
              element={
                <LazyLoadWrapper>
                  <LazyPages.LazyUnauthorizedPage />
                </LazyLoadWrapper>
              } 
            />
            <Route 
              path={ROUTES.SERVER_ERROR} 
              element={
                <LazyLoadWrapper>
                  <LazyPages.LazyServerErrorPage />
                </LazyLoadWrapper>
              } 
            />
            
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
              
              {/* Dashboard with lazy loading */}
              <Route path="dashboard" element={
                <RouteGuard requireAuth>
                  <LazyLoadWrapper>
                    <LazyPages.LazyDashboardPage />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              
              {/* Asset Management with lazy loading */}
              <Route path="assets" element={
                <RouteGuard requireAuth requiredPermissions={['assets.read']}>
                  <LazyLoadWrapper>
                    <LazyPages.LazyAssetBrowser />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="assets/upload" element={
                <RouteGuard requireAuth requiredPermissions={['assets.create']}>
                  <LazyLoadWrapper>
                    <LazyPages.LazyAssetUpload />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="assets/advanced" element={
                <RouteGuard requireAuth requiredPermissions={['assets.read']}>
                  <LazyLoadWrapper>
                    <LazyPages.LazyAdvancedAssetBrowser />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="assets/:id" element={
                <RouteGuard requireAuth requiredPermissions={['assets.read']}>
                  <LazyLoadWrapper>
                    <LazyPages.LazyAssetDetail />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              
              {/* Project Management with lazy loading */}
              <Route path="projects" element={
                <RouteGuard requireAuth requiredPermissions={['projects.read']}>
                  <LazyLoadWrapper>
                    <LazyPages.LazyProjectBrowser />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="projects/:id" element={
                <RouteGuard requireAuth requiredPermissions={['projects.read']}>
                  <LazyLoadWrapper>
                    <LazyPages.LazyProjectDetail />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="projects/:projectId/shotlists/:shotlistId" element={
                <RouteGuard requireAuth requiredPermissions={['projects.read']}>
                  <LazyLoadWrapper>
                    <LazyPages.LazyShotlistPage />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              
              {/* Search with lazy loading */}
              <Route path="search" element={
                <RouteGuard requireAuth requiredPermissions={['assets.read']}>
                  <LazyLoadWrapper>
                    <LazyPages.LazySearchPage />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              
              {/* Workflow Management with lazy loading */}
              <Route path="workflows" element={
                <RouteGuard requireAuth requiredPermissions={['workflow.read']}>
                  <LazyLoadWrapper>
                    <LazyPages.LazyWorkflowMarketplace />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="workflows/designer" element={
                <RouteGuard requireAuth requiredPermissions={['workflow.create']}>
                  <LazyLoadWrapper>
                    <LazyPages.LazyWorkflowDesigner />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="workflows/designer/:workflowId" element={
                <RouteGuard requireAuth requiredPermissions={['workflow.update']}>
                  <LazyLoadWrapper>
                    <LazyPages.LazyWorkflowDesigner />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="workflows/templates" element={
                <RouteGuard requireAuth requiredPermissions={['workflow.read']}>
                  <LazyLoadWrapper>
                    <LazyPages.LazyWorkflowMarketplace />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              
              {/* Admin with lazy loading */}
              <Route path="users" element={
                <RouteGuard requireAuth requireSuperuser>
                  <LazyLoadWrapper>
                    <LazyPages.LazyUserManagement />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="roles" element={
                <RouteGuard requireAuth requireSuperuser>
                  <LazyLoadWrapper>
                    <LazyPages.LazyRoleManagement />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="groups" element={
                <RouteGuard requireAuth requireSuperuser>
                  <LazyLoadWrapper>
                    <LazyPages.LazyGroupManagement />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="permissions" element={
                <RouteGuard requireAuth requireSuperuser>
                  <LazyLoadWrapper>
                    <LazyPages.LazyPermissionManagement />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="inheritance" element={
                <RouteGuard requireAuth requireSuperuser>
                  <LazyLoadWrapper>
                    <LazyPages.LazyInheritanceAnalysis />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="profile" element={
                <RouteGuard requireAuth>
                  <LazyLoadWrapper>
                    <LazyPages.LazyProfile />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
              <Route path="settings" element={
                <RouteGuard requireAuth>
                  <LazyLoadWrapper>
                    <LazyPages.LazySettings />
                  </LazyLoadWrapper>
                </RouteGuard>
              } />
            </Route>
            
            {/* Catch all route with lazy loading */}
            <Route 
              path="*" 
              element={
                <LazyLoadWrapper>
                  <LazyPages.LazyNotFoundPage />
                </LazyLoadWrapper>
              } 
            />
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