import React from 'react';
import {
  Card,
  CardContent,
  Box,
  Typography,
  Chip,
  Skeleton,
  useTheme,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
  isLoading?: boolean;
  onClick?: () => void;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  change,
  changeType = 'neutral',
  color = 'primary',
  isLoading = false,
  onClick,
}) => {
  const theme = useTheme();

  const getChangeColor = () => {
    switch (changeType) {
      case 'positive':
        return 'success';
      case 'negative':
        return 'error';
      default:
        return 'default';
    }
  };

  const getChangeIcon = () => {
    switch (changeType) {
      case 'positive':
        return <TrendingUpIcon sx={{ fontSize: 16 }} />;
      case 'negative':
        return <TrendingDownIcon sx={{ fontSize: 16 }} />;
      default:
        return null;
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
            <Skeleton variant="rectangular" width={40} height={40} sx={{ mr: 2 }} />
            <Box sx={{ flex: 1 }}>
              <Skeleton variant="text" width="60%" height={32} />
              <Skeleton variant="text" width="80%" height={20} />
              <Skeleton variant="text" width="40%" height={16} />
            </Box>
          </Box>
          <Skeleton variant="rectangular" width={80} height={24} />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card 
      sx={{ 
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': onClick ? { 
          boxShadow: 4,
          transform: 'translateY(-2px)',
        } : {},
        transition: 'all 0.3s ease-in-out',
        height: '100%',
      }}
      onClick={onClick}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
          <Box 
            sx={{ 
              p: 1,
              borderRadius: 2,
              backgroundColor: `${color}.light`,
              color: `${color}.contrastText`,
              mr: 2,
            }}
          >
            {icon}
          </Box>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography 
              variant="h4" 
              component="div" 
              fontWeight="bold"
              sx={{ 
                color: `${color}.main`,
                lineHeight: 1.2,
              }}
            >
              {value}
            </Typography>
            <Typography 
              variant="body2" 
              color="text.secondary"
              sx={{ fontWeight: 500 }}
            >
              {title}
            </Typography>
            {subtitle && (
              <Typography 
                variant="caption" 
                color="text.secondary"
                sx={{ display: 'block', mt: 0.5 }}
              >
                {subtitle}
              </Typography>
            )}
          </Box>
        </Box>
        
        {change && (
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Chip
              label={change}
              color={getChangeColor() as any}
              size="small"
              icon={getChangeIcon() || undefined}
              sx={{ 
                fontWeight: 'medium',
                '& .MuiChip-icon': {
                  fontSize: 16,
                },
              }}
            />
            <Typography 
              variant="caption" 
              color="text.secondary" 
              sx={{ ml: 1 }}
            >
              vs last month
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default StatCard;