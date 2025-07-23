import React, { Suspense } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Chip,
  Paper,
  Stack,
  Avatar,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  ListItemSecondaryAction,
  IconButton,
  LinearProgress,
  Alert
} from '@mui/material';
import {
  Code as CodeIcon,
  Analytics as AnalyticsIcon,
  Book as BookIcon,
  CloudUpload as CloudUploadIcon,
  Settings as SettingsIcon,
  Extension as ExtensionIcon,
  Star as StarIcon,
  Download as DownloadIcon,
  TrendingUp as TrendingUpIcon,
  BugReport as BugReportIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useGetDeveloperDashboardQuery } from '../../store/api/developerApi';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { StatCard } from '../../components/common/StatCard';
import { Loading } from '../../components/Loading/RTKQueryLoading';

interface DeveloperPortalPageProps {}

export const DeveloperPortalPage: React.FC<DeveloperPortalPageProps> = () => {
  const navigate = useNavigate();
  const { data: dashboardData, isLoading, error } = useGetDeveloperDashboardQuery();

  if (isLoading) {
    return <Loading />;
  }

  if (error) {
    return (
      <Container maxWidth="lg">
        <Alert severity="error" sx={{ mt: 2 }}>
          Failed to load developer dashboard. Please try again.
        </Alert>
      </Container>
    );
  }

  if (!dashboardData) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="h4" gutterBottom>
            Welcome to the Developer Portal
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph>
            Register as a developer to start creating plugins for the MAMS platform.
          </Typography>
          <Button
            variant="contained"
            size="large"
            startIcon={<ExtensionIcon />}
            onClick={() => navigate('/developer/register')}
          >
            Register as Developer
          </Button>
        </Box>
      </Container>
    );
  }

  const { developer_info, plugin_stats, recent_reviews, plugins } = dashboardData;

  return (
    <Container maxWidth="lg">
      <PageHeader
        title="Developer Portal"
        subtitle="Manage your plugins and track performance"
        action={
          <Button
            variant="contained"
            startIcon={<CodeIcon />}
            onClick={() => navigate('/developer/editor')}
          >
            Create Plugin
          </Button>
        }
      />

      {/* Developer Info Card */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
              {developer_info.company_name?.[0] || 'D'}
            </Avatar>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h6">
                {developer_info.company_name || 'Developer Account'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Member since {new Date(developer_info.created_at).toLocaleDateString()}
              </Typography>
            </Box>
            <Stack direction="row" spacing={1}>
              {developer_info.verified && (
                <Chip 
                  label="Verified" 
                  color="success" 
                  size="small" 
                  icon={<StarIcon />} 
                />
              )}
              <IconButton onClick={() => navigate('/developer/settings')}>
                <SettingsIcon />
              </IconButton>
            </Stack>
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Total Plugins"
                value={plugin_stats.total_plugins}
                icon={<ExtensionIcon />}
                color="primary"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Total Downloads"
                value={plugin_stats.total_downloads.toLocaleString()}
                icon={<DownloadIcon />}
                color="success"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Success Rate"
                value={`${plugin_stats.success_rate.toFixed(1)}%`}
                icon={<TrendingUpIcon />}
                color="info"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="Avg. Execution"
                value={`${plugin_stats.avg_execution_time.toFixed(2)}ms`}
                icon={<AnalyticsIcon />}
                color="warning"
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        {/* Quick Actions */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>
              <Stack spacing={2}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<CodeIcon />}
                  onClick={() => navigate('/developer/editor')}
                >
                  Create New Plugin
                </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<AnalyticsIcon />}
                  onClick={() => navigate('/developer/analytics')}
                >
                  View Analytics
                </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<BookIcon />}
                  onClick={() => navigate('/developer/documentation')}
                >
                  Documentation
                </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<CloudUploadIcon />}
                  onClick={() => navigate('/developer/plugins')}
                >
                  Manage Plugins
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Plugins */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Your Plugins ({plugins.length})
                </Typography>
                <Button
                  size="small"
                  onClick={() => navigate('/developer/plugins')}
                >
                  View All
                </Button>
              </Box>

              {plugins.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <ExtensionIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="body1" color="text.secondary">
                    No plugins yet. Create your first plugin to get started!
                  </Typography>
                </Box>
              ) : (
                <List>
                  {plugins.slice(0, 5).map((plugin, index) => (
                    <React.Fragment key={plugin.id}>
                      {index > 0 && <Divider />}
                      <ListItem>
                        <ListItemAvatar>
                          <Avatar sx={{ bgcolor: getStatusColor(plugin.status) }}>
                            <ExtensionIcon />
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={plugin.name}
                          secondary={
                            <Box>
                              <Typography variant="body2" color="text.secondary">
                                v{plugin.version} • {plugin.downloads} downloads
                              </Typography>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                                <Chip 
                                  label={plugin.status} 
                                  size="small" 
                                  color={getStatusChipColor(plugin.status)}
                                />
                                {plugin.rating > 0 && (
                                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                    <StarIcon sx={{ fontSize: 16, color: 'warning.main' }} />
                                    <Typography variant="body2" sx={{ ml: 0.5 }}>
                                      {plugin.rating.toFixed(1)}
                                    </Typography>
                                  </Box>
                                )}
                              </Box>
                            </Box>
                          }
                        />
                        <ListItemSecondaryAction>
                          <Stack direction="row" spacing={1}>
                            <IconButton 
                              size="small"
                              onClick={() => navigate(`/developer/editor/${plugin.id}`)}
                            >
                              <EditIcon />
                            </IconButton>
                            <IconButton 
                              size="small"
                              onClick={() => navigate(`/developer/plugins/${plugin.id}`)}
                            >
                              <VisibilityIcon />
                            </IconButton>
                          </Stack>
                        </ListItemSecondaryAction>
                      </ListItem>
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Reviews */}
        {recent_reviews.length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Recent Reviews
                </Typography>
                <List>
                  {recent_reviews.slice(0, 3).map((review, index) => (
                    <React.Fragment key={index}>
                      {index > 0 && <Divider />}
                      <ListItem>
                        <ListItemAvatar>
                          <Avatar sx={{ bgcolor: getRatingColor(review.rating) }}>
                            <StarIcon />
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography variant="body1">
                                {review.rating}/5 stars
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                on {plugins.find(p => p.id === review.plugin_id)?.name || 'Unknown Plugin'}
                              </Typography>
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="body2" sx={{ mt: 0.5 }}>
                                "{review.comment}"
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {new Date(review.created_at).toLocaleDateString()}
                              </Typography>
                            </Box>
                          }
                        />
                      </ListItem>
                    </React.Fragment>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Container>
  );
};

// Helper functions
function getStatusColor(status: string): string {
  switch (status) {
    case 'enabled':
    case 'published':
      return 'success.main';
    case 'disabled':
    case 'draft':
      return 'grey.500';
    case 'error':
    case 'rejected':
      return 'error.main';
    case 'pending_approval':
    case 'under_review':
      return 'warning.main';
    default:
      return 'primary.main';
  }
}

function getStatusChipColor(status: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' {
  switch (status) {
    case 'enabled':
    case 'published':
      return 'success';
    case 'disabled':
    case 'draft':
      return 'default';
    case 'error':
    case 'rejected':
      return 'error';
    case 'pending_approval':
    case 'under_review':
      return 'warning';
    default:
      return 'primary';
  }
}

function getRatingColor(rating: number): string {
  if (rating >= 4) return 'success.main';
  if (rating >= 3) return 'warning.main';
  return 'error.main';
}

export default DeveloperPortalPage;