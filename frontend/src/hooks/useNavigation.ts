import { useNavigate, useLocation, useParams } from 'react-router-dom';
import { useCallback } from 'react';
import { Navigation } from '../router/navigation';

export const useNavigation = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();

  const goBack = useCallback(() => {
    navigate(-1);
  }, [navigate]);

  const goForward = useCallback(() => {
    navigate(1);
  }, [navigate]);

  const goTo = useCallback((path: string, options?: { replace?: boolean; state?: any }) => {
    navigate(path, options);
  }, [navigate]);

  const reload = useCallback(() => {
    navigate(location.pathname + location.search, { replace: true });
  }, [navigate, location]);

  return {
    // Navigation methods
    navigate,
    goBack,
    goForward,
    goTo,
    reload,
    
    // Current location info
    location,
    params,
    pathname: location.pathname,
    search: location.search,
    hash: location.hash,
    state: location.state,
    
    // Navigation shortcuts
    nav: Navigation,
    
    // Utility methods
    isCurrentPath: (path: string) => location.pathname === path,
    isCurrentPathStartsWith: (path: string) => location.pathname.startsWith(path),
    getQueryParam: (key: string) => new URLSearchParams(location.search).get(key),
    getAllQueryParams: () => new URLSearchParams(location.search),
    
    // Navigation with query parameters
    navigateWithQuery: (path: string, query: Record<string, string>) => {
      const searchParams = new URLSearchParams(query);
      navigate(`${path}?${searchParams.toString()}`);
    },
    
    // Update query parameters without navigation
    updateQuery: (query: Record<string, string | null>) => {
      const searchParams = new URLSearchParams(location.search);
      
      Object.entries(query).forEach(([key, value]) => {
        if (value === null) {
          searchParams.delete(key);
        } else {
          searchParams.set(key, value);
        }
      });
      
      navigate(`${location.pathname}?${searchParams.toString()}`, { replace: true });
    },
  };
};

export default useNavigation;