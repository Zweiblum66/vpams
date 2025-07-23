import React, { useState } from 'react';
import {
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Stack,
  Box,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Download as DownloadIcon,
  Star as StarIcon,
  Speed as SpeedIcon,
  DateRange as DateRangeIcon
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { useGetPluginAnalyticsQuery, useGetDeveloperPluginsQuery } from '../../store/api/developerApi';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { StatCard } from '../../components/common/StatCard';
import { Loading } from '../../components/Loading/RTKQueryLoading';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export const PluginAnalyticsPage: React.FC = () => {
  const [selectedPlugin, setSelectedPlugin] = useState<string>('');
  const [dateRange, setDateRange] = useState<number>(30);

  const { data: plugins } = useGetDeveloperPluginsQuery();
  const { data: analytics, isLoading, error } = useGetPluginAnalyticsQuery({
    plugin_id: selectedPlugin || undefined,
    days: dateRange
  });

  if (isLoading) {
    return <Loading />;
  }

  if (error) {
    return (
      <Container maxWidth="lg">
        <Alert severity="error" sx={{ mt: 2 }}>
          Failed to load analytics data. Please try again.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl">
      <PageHeader
        title="Plugin Analytics"
        subtitle="Track performance and usage metrics for your plugins"
      />

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center">
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>Plugin</InputLabel>
              <Select
                value={selectedPlugin}
                onChange={(e) => setSelectedPlugin(e.target.value)}
                label="Plugin"
              >
                <MenuItem value="">All Plugins</MenuItem>
                {plugins?.map((plugin) => (
                  <MenuItem key={plugin.id} value={plugin.id}>
                    {plugin.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl sx={{ minWidth: 150 }}>
              <InputLabel>Date Range</InputLabel>
              <Select
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value as number)}
                label="Date Range"
              >
                <MenuItem value={7}>Last 7 days</MenuItem>
                <MenuItem value={30}>Last 30 days</MenuItem>
                <MenuItem value={90}>Last 90 days</MenuItem>
                <MenuItem value={365}>Last year</MenuItem>
              </Select>
            </FormControl>

            <Button
              variant="outlined"
              startIcon={<DateRangeIcon />}
              sx={{ minWidth: 120 }}
            >
              Export Data
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {analytics && (
        <Grid container spacing={3}>
          {/* Overview Stats */}
          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>
              Overview ({analytics.period.start_date} - {analytics.period.end_date})
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <StatCard
                  title="Total Downloads"
                  value={analytics.overview.total_downloads.toLocaleString()}
                  icon={<DownloadIcon />}
                  color="primary"
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <StatCard
                  title="Average Rating"
                  value={analytics.overview.avg_rating.toFixed(1)}
                  icon={<StarIcon />}
                  color="warning"
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <StatCard
                  title="Total Reviews"
                  value={analytics.overview.total_reviews.toString()}
                  icon={<TrendingUpIcon />}
                  color="success"
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <StatCard
                  title="Positive Rate"
                  value={`${analytics.overview.positive_review_rate.toFixed(1)}%`}
                  icon={<SpeedIcon />}
                  color="info"
                />
              </Grid>
            </Grid>
          </Grid>

          {/* Daily Analytics Chart */}
          <Grid item xs={12} lg={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Daily Executions
                </Typography>
                <Box sx={{ width: '100%', height: 300 }}>
                  <ResponsiveContainer>
                    <LineChart data={analytics.daily_analytics}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="executions"
                        stroke="#8884d8"
                        strokeWidth={2}
                        name="Executions"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Success Rate Chart */}
          <Grid item xs={12} lg={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Success Rate Trend
                </Typography>
                <Box sx={{ width: '100%', height: 300 }}>
                  <ResponsiveContainer>
                    <LineChart data={analytics.daily_analytics}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis domain={[0, 100]} />
                      <Tooltip formatter={(value) => [`${value}%`, 'Success Rate']} />
                      <Line
                        type="monotone"
                        dataKey="success_rate"
                        stroke="#00C49F"
                        strokeWidth={2}
                        name="Success Rate (%)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Plugin Breakdown */}
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Plugin Performance
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Plugin</TableCell>
                        <TableCell align="right">Downloads</TableCell>
                        <TableCell align="right">Rating</TableCell>
                        <TableCell>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {analytics.plugin_breakdown.map((plugin) => (
                        <TableRow key={plugin.id}>
                          <TableCell>{plugin.name}</TableCell>
                          <TableCell align="right">{plugin.downloads.toLocaleString()}</TableCell>
                          <TableCell align="right">
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                              <StarIcon sx={{ fontSize: 16, color: 'warning.main', mr: 0.5 }} />
                              {plugin.rating.toFixed(1)}
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={plugin.status}
                              size="small"
                              color={getStatusColor(plugin.status)}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>

          {/* Execution Time Chart */}
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Average Execution Time
                </Typography>
                <Box sx={{ width: '100%', height: 300 }}>
                  <ResponsiveContainer>
                    <BarChart data={analytics.daily_analytics}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip formatter={(value) => [`${value}ms`, 'Avg. Execution Time']} />
                      <Bar dataKey="avg_execution_time" fill="#FFBB28" />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Performance Insights */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Performance Insights
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ p: 2, bgcolor: 'success.light', borderRadius: 1 }}>
                      <Typography variant="h6" color="success.contrastText">
                        Best Performing Plugin
                      </Typography>
                      <Typography variant="body2" color="success.contrastText">
                        {analytics.plugin_breakdown.length > 0 
                          ? analytics.plugin_breakdown.reduce((best, current) => 
                              current.rating > best.rating ? current : best
                            ).name
                          : 'N/A'
                        }
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ p: 2, bgcolor: 'info.light', borderRadius: 1 }}>
                      <Typography variant="h6" color="info.contrastText">
                        Most Downloaded
                      </Typography>
                      <Typography variant="body2" color="info.contrastText">
                        {analytics.plugin_breakdown.length > 0
                          ? analytics.plugin_breakdown.reduce((most, current) =>
                              current.downloads > most.downloads ? current : most
                            ).name
                          : 'N/A'
                        }
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ p: 2, bgcolor: 'warning.light', borderRadius: 1 }}>
                      <Typography variant="h6" color="warning.contrastText">
                        Improvement Needed
                      </Typography>
                      <Typography variant="body2" color="warning.contrastText">
                        {analytics.plugin_breakdown.find(p => p.rating < 3)?.name || 'All plugins performing well'}
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Container>
  );
};

function getStatusColor(status: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' {
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

export default PluginAnalyticsPage;