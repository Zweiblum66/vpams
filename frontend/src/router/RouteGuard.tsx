import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Box, Typography, Alert } from '@mui/material';
import { useAppSelector } from '../store';
import { ROUTES } from './routes';

interface RouteGuardProps {
  children: React.ReactNode;
  requiredPermissions?: string[];
  requireAuth?: boolean;
  requireSuperuser?: boolean;
  fallbackRoute?: string;
}

const RouteGuard: React.FC<RouteGuardProps> = ({
  children,
  requiredPermissions = [],
  requireAuth = true,
  requireSuperuser = false,
  fallbackRoute = ROUTES.DASHBOARD,
}) => {
  const { isAuthenticated, user } = useAppSelector(state => state.auth);
  const location = useLocation();

  // Check authentication
  if (requireAuth && !isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} state={{ from: location }} replace />;
  }

  // Check if user is loaded
  if (requireAuth && !user) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">Loading user information...</Alert>
      </Box>
    );
  }

  // Check superuser requirement
  if (requireSuperuser && user && !user.is_superuser) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          <Typography variant="h6">Access Denied</Typography>
          <Typography>You need superuser privileges to access this page.</Typography>
        </Alert>
      </Box>
    );
  }

  // Check required permissions
  if (requiredPermissions.length > 0 && user) {
    const hasPermission = checkUserPermissions(user, requiredPermissions);
    
    if (!hasPermission) {
      return (
        <Box sx={{ p: 3 }}>
          <Alert severity="error">
            <Typography variant="h6">Access Denied</Typography>
            <Typography>
              You don't have the required permissions to access this page.
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              Required permissions: {requiredPermissions.join(', ')}
            </Typography>
          </Alert>
        </Box>
      );
    }
  }

  return <>{children}</>;
};

// Helper function to check user permissions
function checkUserPermissions(user: any, requiredPermissions: string[]): boolean {
  // If user is superuser, allow all permissions
  if (user.is_superuser) {
    return true;
  }

  // TODO: Implement proper permission checking logic
  // This would integrate with your RBAC system
  // For now, we'll return true to allow access
  return true;
}

export default RouteGuard;