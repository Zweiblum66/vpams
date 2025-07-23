import { useLocation } from 'react-router-dom';
import { useMemo } from 'react';
import { ROUTE_METADATA, ROUTES } from '../router/routes';

export const useRouteMetadata = () => {
  const location = useLocation();

  const metadata = useMemo(() => {
    // Find exact match first
    const exactMatch = Object.entries(ROUTES).find(([_, route]) => route === location.pathname);
    
    if (exactMatch) {
      const [routeKey, routePath] = exactMatch;
      return ROUTE_METADATA[routePath as keyof typeof ROUTE_METADATA];
    }

    // Find pattern match for dynamic routes
    const patternMatch = Object.entries(ROUTES).find(([_, route]) => {
      if (route.includes(':')) {
        const routePattern = route.replace(/:\w+/g, '[^/]+');
        const regex = new RegExp(`^${routePattern}$`);
        return regex.test(location.pathname);
      }
      return false;
    });

    if (patternMatch) {
      const [routeKey, routePath] = patternMatch;
      return ROUTE_METADATA[routePath as keyof typeof ROUTE_METADATA];
    }

    // Default metadata for unknown routes
    return {
      title: 'MAMS',
      breadcrumb: 'Unknown',
      description: 'Media Asset Management System',
    };
  }, [location.pathname]);

  return metadata;
};

export default useRouteMetadata;