import React from 'react';
import {
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Box,
  Typography,
  Chip,
  Skeleton,
  LinearProgress,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

export interface SystemHealthItem {
  service: string;
  status: 'healthy' | 'warning' | 'error' | 'maintenance';
  lastCheck: string;
  uptime: string;
  responseTime?: number;
  description?: string;
}

interface SystemHealthListProps {
  services: SystemHealthItem[];
  isLoading?: boolean;
  showDetails?: boolean;
}

const SystemHealthList: React.FC<SystemHealthListProps> = ({
  services,
  isLoading = false,
  showDetails = false,
}) => {
  const getStatusIcon = (status: SystemHealthItem['status']) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon color="success" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'error':
        return <ErrorIcon color="error" />;
      case 'maintenance':
        return <InfoIcon color="info" />;
      default:
        return <CheckCircleIcon color="success" />;
    }
  };

  const getStatusColor = (status: SystemHealthItem['status']) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
      case 'maintenance':
        return 'info';
      default:
        return 'success';
    }
  };

  const getStatusLabel = (status: SystemHealthItem['status']) => {
    switch (status) {
      case 'healthy':
        return 'Healthy';
      case 'warning':
        return 'Warning';
      case 'error':
        return 'Error';
      case 'maintenance':
        return 'Maintenance';
      default:
        return 'Unknown';
    }
  };

  const getUptimeProgress = (uptime: string): number => {
    // Extract percentage from uptime string (e.g., "99.9%" -> 99.9)
    const match = uptime.match(/(\d+\.?\d*)%/);
    return match ? parseFloat(match[1]) : 0;
  };

  if (isLoading) {
    return (
      <Box>
        {Array.from({ length: 4 }).map((_, index) => (
          <Box key={index} sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Skeleton variant="circular" width={24} height={24} sx={{ mr: 2 }} />
              <Box sx={{ flex: 1 }}>
                <Skeleton variant="text" width="60%" height={24} />
                <Skeleton variant="text" width="40%" height={20} />
              </Box>
              <Skeleton variant="rectangular" width={60} height={24} />
            </Box>
            {index < 3 && <Divider sx={{ mt: 2 }} />}
          </Box>
        ))}
      </Box>
    );
  }

  if (services.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body2" color="text.secondary">
          No service data available
        </Typography>
      </Box>
    );
  }

  return (
    <List sx={{ py: 0 }}>
      {services.map((service, index) => (
        <React.Fragment key={service.service}>
          <ListItem sx={{ px: 0, py: 1.5 }}>
            <ListItemIcon sx={{ minWidth: 40 }}>
              {getStatusIcon(service.status)}
            </ListItemIcon>
            
            <ListItemText
              primary={
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {service.service}
                  </Typography>
                  <Chip
                    label={getStatusLabel(service.status)}
                    color={getStatusColor(service.status) as any}
                    size="small"
                    sx={{ minWidth: 80 }}
                  />
                </Box>
              }
              secondary={
                <Box sx={{ mt: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">
                      Uptime: {service.uptime}
                    </Typography>
                    {service.responseTime && (
                      <Typography variant="caption" color="text.secondary">
                        Response: {service.responseTime}ms
                      </Typography>
                    )}
                  </Box>
                  
                  {showDetails && (
                    <>
                      <LinearProgress
                        variant="determinate"
                        value={getUptimeProgress(service.uptime)}
                        color={getStatusColor(service.status) as any}
                        sx={{ 
                          height: 4, 
                          borderRadius: 2,
                          mb: 0.5,
                          backgroundColor: 'action.hover',
                        }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        Last check: {service.lastCheck}
                      </Typography>
                      {service.description && (
                        <Typography 
                          variant="caption" 
                          color="text.secondary" 
                          sx={{ display: 'block', mt: 0.5 }}
                        >
                          {service.description}
                        </Typography>
                      )}
                    </>
                  )}
                  
                  {!showDetails && (
                    <Typography variant="caption" color="text.secondary">
                      Last check: {service.lastCheck}
                    </Typography>
                  )}
                </Box>
              }
            />
          </ListItem>
          {index < services.length - 1 && <Divider />}
        </React.Fragment>
      ))}
    </List>
  );
};

export default SystemHealthList;