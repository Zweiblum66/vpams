import React from 'react';
import { Breadcrumbs as MuiBreadcrumbs, Link, Typography, Box } from '@mui/material';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { Home as HomeIcon, ChevronRight as ChevronRightIcon } from '@mui/icons-material';
import { ROUTES, ROUTE_METADATA } from '../../router/routes';
import { Navigation } from '../../router/navigation';

interface BreadcrumbItem {
  label: string;
  path?: string;
  icon?: React.ReactNode;
}

const Breadcrumbs: React.FC = () => {
  const location = useLocation();

  const generateBreadcrumbs = (): BreadcrumbItem[] => {
    const pathSegments = location.pathname.split('/').filter(Boolean);
    const breadcrumbs: BreadcrumbItem[] = [];

    // Always start with Home
    breadcrumbs.push({
      label: 'Home',
      path: Navigation.dashboard(),
      icon: <HomeIcon sx={{ fontSize: 18 }} />,
    });

    // Build breadcrumb items from path segments
    let currentPath = '';
    pathSegments.forEach((segment, index) => {
      currentPath += `/${segment}`;
      
      // Get route metadata for current path
      const routeMetadata = getRouteMetadata(currentPath);
      
      if (routeMetadata) {
        breadcrumbs.push({
          label: routeMetadata.breadcrumb,
          path: index === pathSegments.length - 1 ? undefined : currentPath,
        });
      } else {
        // For dynamic segments (like IDs), create a generic breadcrumb
        breadcrumbs.push({
          label: segment.charAt(0).toUpperCase() + segment.slice(1),
          path: index === pathSegments.length - 1 ? undefined : currentPath,
        });
      }
    });

    return breadcrumbs;
  };

  const getRouteMetadata = (path: string) => {
    // Check for exact match
    const exactMatch = Object.entries(ROUTES).find(([_, route]) => route === path);
    if (exactMatch) {
      const [, routePath] = exactMatch;
      return ROUTE_METADATA[routePath as keyof typeof ROUTE_METADATA];
    }

    // Check for pattern match
    const patternMatch = Object.entries(ROUTES).find(([_, route]) => {
      if (route.includes(':')) {
        const routePattern = route.replace(/:\w+/g, '[^/]+');
        const regex = new RegExp(`^${routePattern}$`);
        return regex.test(path);
      }
      return false;
    });

    if (patternMatch) {
      const [, routePath] = patternMatch;
      return ROUTE_METADATA[routePath as keyof typeof ROUTE_METADATA];
    }

    return null;
  };

  const breadcrumbs = generateBreadcrumbs();

  // Don't show breadcrumbs for root/dashboard
  if (location.pathname === '/' || location.pathname === '/dashboard') {
    return null;
  }

  return (
    <Box sx={{ mb: 2 }}>
      <MuiBreadcrumbs 
        separator={<ChevronRightIcon fontSize="small" />}
        aria-label="breadcrumb"
        sx={{ mb: 1 }}
      >
        {breadcrumbs.map((item, index) => {
          const isLast = index === breadcrumbs.length - 1;
          
          if (isLast || !item.path) {
            return (
              <Typography
                key={index}
                color="text.primary"
                sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
              >
                {item.icon}
                {item.label}
              </Typography>
            );
          }

          return (
            <Link
              key={index}
              component={RouterLink}
              to={item.path}
              color="inherit"
              underline="hover"
              sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
            >
              {item.icon}
              {item.label}
            </Link>
          );
        })}
      </MuiBreadcrumbs>
    </Box>
  );
};

export default Breadcrumbs;