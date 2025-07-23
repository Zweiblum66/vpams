import React from 'react';
import { Box, Typography, Button, Divider } from '@mui/material';
import { useRouteMetadata } from '../../hooks/useRouteMetadata';
import Breadcrumbs from '../Breadcrumbs/Breadcrumbs';

interface PageHeaderProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  showBreadcrumbs?: boolean;
  children?: React.ReactNode;
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  actions,
  showBreadcrumbs = true,
  children,
}) => {
  const routeMetadata = useRouteMetadata();

  const displayTitle = title || routeMetadata?.title || 'Page';
  const displaySubtitle = subtitle || routeMetadata?.description;

  return (
    <Box sx={{ mb: 3 }}>
      {showBreadcrumbs && <Breadcrumbs />}
      
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            {displayTitle}
          </Typography>
          {displaySubtitle && (
            <Typography variant="body1" color="text.secondary" sx={{ mb: 1 }}>
              {displaySubtitle}
            </Typography>
          )}
        </Box>
        
        {actions && (
          <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
            {actions}
          </Box>
        )}
      </Box>
      
      {children}
      
      <Divider sx={{ mt: 2 }} />
    </Box>
  );
};

export default PageHeader;