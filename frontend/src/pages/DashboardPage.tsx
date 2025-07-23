import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  LinearProgress,
  Alert,
  IconButton,
  Skeleton,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  VideoLibrary as VideoLibraryIcon,
  Folder as FolderIcon,
  Storage as StorageIcon,
  People as PeopleIcon,
  Search as SearchIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
  Refresh as RefreshIcon,
  PlayArrow as PlayArrowIcon,
  MovieFilter as MovieFilterIcon,
  Analytics as AnalyticsIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { logger } from '../utils/logger';
import { ROUTES } from '../router/routes';
import { StatCard, ActivityList, SystemHealthList } from '../components/common';
import type { ActivityItem, SystemHealthItem } from '../components/common';

interface DashboardStats {
  totalAssets: number;
  totalStorage: string;
  activeProjects: number;
  totalUsers: number;
  recentUploads: number;
  processingJobs: number;
}


interface QuickAction {
  title: string;
  description: string;
  icon: React.ReactNode;
  route: string;
  permission?: string;
}

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, hasPermission } = useAuth();
  const { handleError } = useErrorHandler();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentActivity, setRecentActivity] = useState<ActivityItem[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealthItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Quick actions based on user permissions
  const quickActions: QuickAction[] = [
    {
      title: 'Upload Assets',
      description: 'Add new media files to your library',
      icon: <CloudUploadIcon />,
      route: ROUTES.ASSET_UPLOAD,
      permission: 'assets.create',
    },
    {
      title: 'Browse Assets',
      description: 'Explore your media library',
      icon: <VideoLibraryIcon />,
      route: ROUTES.ASSETS,
      permission: 'assets.read',
    },
    {
      title: 'Create Project',
      description: 'Start a new media project',
      icon: <FolderIcon />,
      route: ROUTES.PROJECT_CREATE,
      permission: 'projects.create',
    },
    {
      title: 'Search Media',
      description: 'Find assets using AI-powered search',
      icon: <SearchIcon />,
      route: ROUTES.SEARCH,
      permission: 'assets.read',
    },
    {
      title: 'View Projects',
      description: 'Manage your active projects',
      icon: <MovieFilterIcon />,
      route: ROUTES.PROJECTS,
      permission: 'projects.read',
    },
    {
      title: 'Analytics',
      description: 'View usage and performance metrics',
      icon: <AnalyticsIcon />,
      route: ROUTES.ANALYTICS,
      permission: 'analytics.read',
    },
  ].filter(action => !action.permission || hasPermission(action.permission));

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      logger.info('Loading dashboard data', {
        userId: user?.id,
        actionType: 'dashboard_load',
      });

      // Simulate API calls - replace with actual API calls
      await Promise.all([
        loadStats(),
        loadRecentActivity(),
        loadSystemHealth(),
      ]);

      setLastRefresh(new Date());
      logger.info('Dashboard data loaded successfully', {
        userId: user?.id,
        actionType: 'dashboard_load_success',
      });
    } catch (error: any) {
      logger.error('Failed to load dashboard data', {
        userId: user?.id,
        error: error.message,
        actionType: 'dashboard_load_error',
      }, error);

      handleError(error, {
        context: 'DashboardPage.loadDashboardData',
        userMessage: 'Failed to load dashboard data. Please try again.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadStats = async () => {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 500));
    
    setStats({
      totalAssets: 12847,
      totalStorage: '2.4 TB',
      activeProjects: 156,
      totalUsers: 234,
      recentUploads: 23,
      processingJobs: 5,
    });
  };

  const loadRecentActivity = async () => {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 300));
    
    setRecentActivity([
      {
        id: '1',
        type: 'upload',
        message: 'New video asset "Interview_Final.mp4" uploaded',
        timestamp: '5 minutes ago',
        user: 'John Doe',
        assetId: 'asset_123',
      },
      {
        id: '2',
        type: 'project',
        message: 'Project "Summer Campaign 2024" created',
        timestamp: '20 minutes ago',
        user: 'Sarah Wilson',
      },
      {
        id: '3',
        type: 'processing',
        message: 'Proxy generation completed for "Product_Demo.mov"',
        timestamp: '35 minutes ago',
      },
      {
        id: '4',
        type: 'search',
        message: 'Advanced search performed: "outdoor scenes"',
        timestamp: '45 minutes ago',
        user: 'Mike Johnson',
      },
      {
        id: '5',
        type: 'user',
        message: 'New user Maria Garcia added to system',
        timestamp: '1 hour ago',
        user: 'Admin',
      },
    ]);
  };

  const loadSystemHealth = async () => {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 200));
    
    setSystemHealth([
      {
        service: 'Asset Management Service',
        status: 'healthy',
        lastCheck: '2 minutes ago',
        uptime: '99.9%',
        responseTime: 45,
        description: 'All asset operations functioning normally',
      },
      {
        service: 'Search Engine',
        status: 'healthy',
        lastCheck: '1 minute ago',
        uptime: '99.8%',
        responseTime: 120,
        description: 'Search indexing and queries operational',
      },
      {
        service: 'Storage System',
        status: 'warning',
        lastCheck: '3 minutes ago',
        uptime: '98.5%',
        responseTime: 250,
        description: 'High storage utilization detected',
      },
      {
        service: 'Media Processing',
        status: 'healthy',
        lastCheck: '2 minutes ago',
        uptime: '99.7%',
        responseTime: 180,
        description: 'Transcoding and proxy generation active',
      },
      {
        service: 'User Management',
        status: 'healthy',
        lastCheck: '1 minute ago',
        uptime: '99.9%',
        responseTime: 35,
        description: 'Authentication and authorization services',
      },
    ]);
  };


  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const handleRefresh = () => {
    logger.info('Dashboard refresh requested', {
      userId: user?.id,
      actionType: 'dashboard_refresh',
    });
    loadDashboardData();
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Welcome to MAMS
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Hello, {user?.firstName || user?.email}. Here's what's happening with your media assets.
          </Typography>
        </Box>
        <Box>
          <IconButton 
            onClick={handleRefresh} 
            disabled={isLoading}
            title="Refresh dashboard data"
          >
            <RefreshIcon />
          </IconButton>
          <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
            Last updated: {lastRefresh.toLocaleTimeString()}
          </Typography>
        </Box>
      </Box>

      {/* System Status Alert */}
      {systemHealth.some(s => s.status === 'warning' || s.status === 'error') && (
        <Alert 
          severity="warning" 
          sx={{ mb: 3 }}
          action={
            <Button color="inherit" size="small" onClick={() => navigate(ROUTES.SYSTEM_STATUS)}>
              View Details
            </Button>
          }
        >
          Some system services are experiencing issues. Check system status for more details.
        </Alert>
      )}

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {isLoading ? (
          // Loading skeletons
          Array.from({ length: 4 }).map((_, index) => (
            <Grid item xs={12} sm={6} md={3} key={index}>
              <Card>
                <CardContent>
                  <Skeleton variant="rectangular" width="100%" height={100} />
                </CardContent>
              </Card>
            </Grid>
          ))
        ) : (
          stats && [
            {
              title: 'Total Assets',
              value: formatNumber(stats.totalAssets),
              subtitle: `${stats.recentUploads} uploaded today`,
              icon: <VideoLibraryIcon sx={{ fontSize: 32 }} />,
              change: '+8.3%',
              changeType: 'positive' as const,
              color: 'primary' as const,
              onClick: () => navigate(ROUTES.ASSETS),
            },
            {
              title: 'Active Projects',
              value: stats.activeProjects.toString(),
              subtitle: 'In progress',
              icon: <FolderIcon sx={{ fontSize: 32 }} />,
              change: '+12.1%',
              changeType: 'positive' as const,
              color: 'info' as const,
              onClick: () => navigate(ROUTES.PROJECTS),
            },
            {
              title: 'Storage Used',
              value: stats.totalStorage,
              subtitle: 'Of available space',
              icon: <StorageIcon sx={{ fontSize: 32 }} />,
              change: '+5.7%',
              changeType: 'neutral' as const,
              color: 'warning' as const,
              onClick: () => navigate(ROUTES.STORAGE_ANALYTICS),
            },
            {
              title: 'Processing Jobs',
              value: stats.processingJobs.toString(),
              subtitle: 'Currently active',
              icon: <PlayArrowIcon sx={{ fontSize: 32 }} />,
              change: '-2.1%',
              changeType: 'positive' as const,
              color: 'secondary' as const,
              onClick: () => navigate(ROUTES.PROCESSING_QUEUE),
            },
          ].map((stat, index) => (
            <Grid item xs={12} sm={6} md={3} key={index}>
              <StatCard
                title={stat.title}
                value={stat.value}
                subtitle={stat.subtitle}
                icon={stat.icon}
                change={stat.change}
                changeType={stat.changeType}
                color={stat.color}
                onClick={stat.onClick}
              />
            </Grid>
          ))
        )}
      </Grid>

      <Grid container spacing={3}>
        {/* Quick Actions */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Grid container spacing={2}>
              {quickActions.map((action, index) => (
                <Grid item xs={12} sm={6} md={4} key={index}>
                  <Card 
                    sx={{ 
                      cursor: 'pointer',
                      '&:hover': { boxShadow: 2 },
                      transition: 'box-shadow 0.3s',
                      height: '100%',
                    }}
                    onClick={() => navigate(action.route)}
                  >
                    <CardContent sx={{ pb: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        {action.icon}
                        <Typography variant="subtitle2" sx={{ ml: 1 }} fontWeight="medium">
                          {action.title}
                        </Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {action.description}
                      </Typography>
                    </CardContent>
                    <CardActions sx={{ pt: 0 }}>
                      <Button size="small">
                        Open
                      </Button>
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>

          {/* Recent Activity */}
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Recent Activity
              </Typography>
              <Button 
                size="small" 
                onClick={() => navigate(ROUTES.ACTIVITY_LOG)}
                sx={{ textTransform: 'none' }}
              >
                View All
              </Button>
            </Box>
            <ActivityList
              activities={recentActivity}
              isLoading={isLoading}
              maxItems={5}
              showViewAll={true}
              onViewAll={() => navigate(ROUTES.ACTIVITY_LOG)}
              onItemClick={(activity) => {
                // Handle activity item click - navigate to relevant page
                if (activity.assetId) {
                  navigate(ROUTES.ASSET_DETAIL.replace(':id', activity.assetId));
                }
              }}
            />
          </Paper>
        </Grid>

        {/* System Health */}
        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                System Health
              </Typography>
              <Button 
                size="small" 
                onClick={() => navigate(ROUTES.SYSTEM_STATUS)}
                sx={{ textTransform: 'none' }}
              >
                Details
              </Button>
            </Box>
            <SystemHealthList
              services={systemHealth}
              isLoading={isLoading}
              showDetails={true}
            />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;