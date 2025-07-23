import React from 'react';
import { Box, CircularProgress, Typography, Skeleton } from '@mui/material';

interface RTKQueryLoadingProps {
  isLoading: boolean;
  isError?: boolean;
  isFetching?: boolean;
  children: React.ReactNode;
  loadingComponent?: React.ReactNode;
  skeletonVariant?: 'text' | 'circular' | 'rectangular';
  skeletonHeight?: number;
  skeletonWidth?: number | string;
  skeletonCount?: number;
  showFetchingIndicator?: boolean;
  minHeight?: number;
}

const RTKQueryLoading: React.FC<RTKQueryLoadingProps> = ({
  isLoading,
  isError = false,
  isFetching = false,
  children,
  loadingComponent,
  skeletonVariant = 'rectangular',
  skeletonHeight = 40,
  skeletonWidth = '100%',
  skeletonCount = 3,
  showFetchingIndicator = true,
  minHeight = 200,
}) => {
  // Show loading state for initial load
  if (isLoading) {
    if (loadingComponent) {
      return <>{loadingComponent}</>;
    }

    return (
      <Box sx={{ minHeight, display: 'flex', flexDirection: 'column', gap: 1 }}>
        {Array.from({ length: skeletonCount }).map((_, index) => (
          <Skeleton
            key={index}
            variant={skeletonVariant}
            height={skeletonHeight}
            width={skeletonWidth}
            animation="wave"
          />
        ))}
      </Box>
    );
  }

  // Show error state
  if (isError) {
    return (
      <Box sx={{ minHeight, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography variant="body2" color="error">
          Failed to load data
        </Typography>
      </Box>
    );
  }

  // Show content with optional fetching indicator
  return (
    <Box sx={{ position: 'relative' }}>
      {showFetchingIndicator && isFetching && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            right: 0,
            zIndex: 1000,
            p: 1,
          }}
        >
          <CircularProgress size={20} />
        </Box>
      )}
      {children}
    </Box>
  );
};

export default RTKQueryLoading;