import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthContext } from './AuthProvider';
import { Navigation } from '../router/navigation';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermission?: string;
  requiredPermissions?: string[];
  requireSuperuser?: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  requiredPermission,
  requiredPermissions,
  requireSuperuser = false
}) => {
  const { isAuthenticated, user, hasPermission, hasAllPermissions, setReturnPath } = useAuthContext();
  const location = useLocation();

  if (!isAuthenticated) {
    // Store the attempted path for redirect after login
    setReturnPath(location.pathname);
    return <Navigate to={Navigation.login()} state={{ from: location }} replace />;
  }

  if (!user) {
    return <Navigate to={Navigation.login()} replace />;
  }

  // Check superuser requirement
  if (requireSuperuser && !user.is_superuser) {
    return <Navigate to={Navigation.unauthorized()} replace />;
  }

  // Check single permission
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Navigate to={Navigation.unauthorized()} replace />;
  }

  // Check multiple permissions (all required)
  if (requiredPermissions && !hasAllPermissions(requiredPermissions)) {
    return <Navigate to={Navigation.unauthorized()} replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;