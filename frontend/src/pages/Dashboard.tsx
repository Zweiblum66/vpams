import React from 'react';
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
} from '@mui/material';
import {
  People as PeopleIcon,
  Security as SecurityIcon,
  Group as GroupIcon,
  VpnKey as VpnKeyIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
  VideoLibrary as VideoLibraryIcon,
  Folder as FolderIcon,
  Storage as StorageIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAppSelector } from '../store';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAppSelector(state => state.auth);

  const stats = [
    {
      title: 'Total Assets',
      value: '12,847',
      icon: <VideoLibraryIcon sx={{ fontSize: 40, color: 'primary.main' }} />,
      change: '+8.3%',
      color: 'success',
      action: () => navigate('/assets'),
    },
    {
      title: 'Active Projects',
      value: '156',
      icon: <FolderIcon sx={{ fontSize: 40, color: 'info.main' }} />,
      change: '+12.1%',
      color: 'info',
      action: () => navigate('/projects'),
    },
    {
      title: 'Storage Used',
      value: '2.4 TB',
      icon: <StorageIcon sx={{ fontSize: 40, color: 'warning.main' }} />,
      change: '+5.7%',
      color: 'warning',
      action: () => navigate('/assets'),
    },
    {
      title: 'Total Users',
      value: '234',
      icon: <PeopleIcon sx={{ fontSize: 40, color: 'secondary.main' }} />,
      change: '+2.1%',
      color: 'secondary',
      action: () => navigate('/users'),
    },
  ];

  const recentActivity = [
    {
      type: 'asset_uploaded',
      message: 'New video asset "Interview_Final.mp4" uploaded',
      timestamp: '5 minutes ago',
      icon: <VideoLibraryIcon color="primary" />,
    },
    {
      type: 'project_created',
      message: 'Project "Summer Campaign 2024" created',
      timestamp: '20 minutes ago',
      icon: <FolderIcon color="info" />,
    },
    {
      type: 'search_performed',
      message: 'Advanced search performed: "outdoor scenes"',
      timestamp: '45 minutes ago',
      icon: <SearchIcon color="warning" />,
    },
    {
      type: 'user_created',
      message: 'New user Sarah Johnson added',
      timestamp: '1 hour ago',
      icon: <PeopleIcon color="secondary" />,
    },
  ];

  const systemHealth = [
    {
      service: 'Asset Management',
      status: 'healthy',
      icon: <CheckCircleIcon color="success" />,
    },
    {
      service: 'Search Engine',
      status: 'healthy',
      icon: <CheckCircleIcon color="success" />,
    },
    {
      service: 'Storage System',
      status: 'warning',
      icon: <WarningIcon color="warning" />,
    },
    {
      service: 'Media Processing',
      status: 'healthy',
      icon: <CheckCircleIcon color="success" />,
    },
  ];

  const quickActions = [
    {
      title: 'Upload Assets',
      description: 'Add new media assets to the system',
      action: () => navigate('/assets/upload'),
      icon: <VideoLibraryIcon />,
    },
    {
      title: 'Create Project',
      description: 'Start a new media project',
      action: () => navigate('/projects'),
      icon: <FolderIcon />,
    },
    {
      title: 'Search Assets',
      description: 'Find media assets quickly',
      action: () => navigate('/search'),
      icon: <SearchIcon />,
    },
    {
      title: 'Manage Users',
      description: 'Add and manage system users',
      action: () => navigate('/users'),
      icon: <PeopleIcon />,
    },
  ];

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          MAMS Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Welcome back, {user?.display_name || user?.first_name || user?.email}. Manage your media assets and projects here.
        </Typography>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {stats.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card 
              sx={{ 
                cursor: 'pointer',
                '&:hover': { boxShadow: 4 },
                transition: 'box-shadow 0.3s'
              }}
              onClick={stat.action}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  {stat.icon}
                  <Box sx={{ ml: 2 }}>
                    <Typography variant="h4" component="div" fontWeight="bold">
                      {stat.value}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {stat.title}
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Chip
                    label={stat.change}
                    color={stat.color as any}
                    size="small"
                    icon={<TrendingUpIcon sx={{ fontSize: 16 }} />}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                    vs last month
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* Recent Activity */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recent Activity
            </Typography>
            <List>
              {recentActivity.map((activity, index) => (
                <React.Fragment key={index}>
                  <ListItem alignItems="flex-start">
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      {activity.icon}
                    </ListItemIcon>
                    <ListItemText
                      primary={activity.message}
                      secondary={
                        <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                          <ScheduleIcon sx={{ fontSize: 14, mr: 0.5 }} />
                          {activity.timestamp}
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < recentActivity.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </Paper>
        </Grid>

        {/* Quick Actions */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Grid container spacing={2}>
              {quickActions.map((action, index) => (
                <Grid item xs={12} sm={6} key={index}>
                  <Card 
                    sx={{ 
                      cursor: 'pointer',
                      '&:hover': { boxShadow: 2 },
                      transition: 'box-shadow 0.3s'
                    }}
                  >
                    <CardContent sx={{ pb: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        {action.icon}
                        <Typography variant="subtitle2" sx={{ ml: 1 }}>
                          {action.title}
                        </Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {action.description}
                      </Typography>
                    </CardContent>
                    <CardActions>
                      <Button size="small" onClick={action.action}>
                        Open
                      </Button>
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>

          {/* System Health */}
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              System Health
            </Typography>
            <List>
              {systemHealth.map((service, index) => (
                <React.Fragment key={index}>
                  <ListItem>
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      {service.icon}
                    </ListItemIcon>
                    <ListItemText
                      primary={service.service}
                      secondary={
                        <Chip
                          label={service.status}
                          color={service.status === 'healthy' ? 'success' : 'warning'}
                          size="small"
                        />
                      }
                    />
                  </ListItem>
                  {index < systemHealth.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;