import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  IconButton,
  Chip,
  Avatar,
  LinearProgress,
  Paper,
  Tab,
  Tabs,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Badge,
  Tooltip,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Assignment as TaskIcon,
  CheckCircle as ApprovedIcon,
  Cancel as RejectedIcon,
  Schedule as PendingIcon,
  TrendingUp as TrendingIcon,
  AccessTime as TimeIcon,
  Person as PersonIcon,
  Group as GroupIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  PlayArrow as ActIcon,
  MoreVert as MoreIcon,
  Warning as WarningIcon,
  ArrowUpward as UpIcon,
  ArrowDownward as DownIcon,
} from '@mui/icons-material';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { format, parseISO, startOfWeek, endOfWeek, eachDayOfInterval } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import { useSnackbar } from 'notistack';

interface ApprovalSummary {
  pending_count: number;
  approved_count: number;
  rejected_count: number;
  escalated_count: number;
  total_count: number;
  average_response_time_hours: number;
  sla_compliance_rate: number;
  pending_urgent: number;
}

interface ApprovalRequest {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  created_at: string;
  deadline?: string;
  approvers: Array<{
    id: string;
    name: string;
    status: string;
    decided_at?: string;
  }>;
  requestor: {
    id: string;
    name: string;
    avatar?: string;
  };
}

interface DashboardMetrics {
  weekly_trend: Array<{
    date: string;
    pending: number;
    approved: number;
    rejected: number;
  }>;
  by_department: Array<{
    department: string;
    count: number;
  }>;
  by_type: Array<{
    type: string;
    count: number;
  }>;
  response_time_distribution: Array<{
    range: string;
    count: number;
  }>;
  top_requestors: Array<{
    name: string;
    count: number;
  }>;
  top_approvers: Array<{
    name: string;
    count: number;
    avg_response_time: number;
  }>;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`dashboard-tabpanel-${index}`}
      aria-labelledby={`dashboard-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const ApprovalDashboard: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  
  const [loading, setLoading] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  const [summary, setSummary] = useState<ApprovalSummary | null>(null);
  const [recentRequests, setRecentRequests] = useState<ApprovalRequest[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchDashboardData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      setRefreshing(true);
      const token = localStorage.getItem('token');
      
      // Fetch summary
      const summaryResponse = await fetch('/api/v1/approvals/dashboard/summary', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const summaryData = await summaryResponse.json();
      setSummary(summaryData);
      
      // Fetch recent requests
      const requestsResponse = await fetch('/api/v1/approvals/dashboard/recent', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const requestsData = await requestsResponse.json();
      setRecentRequests(requestsData);
      
      // Fetch metrics
      const metricsResponse = await fetch('/api/v1/approvals/dashboard/metrics', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const metricsData = await metricsResponse.json();
      setMetrics(metricsData);
      
      setLoading(false);
    } catch (error) {
      enqueueSnackbar('Failed to load dashboard data', { variant: 'error' });
    } finally {
      setRefreshing(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return theme.palette.success.main;
      case 'rejected':
        return theme.palette.error.main;
      case 'pending':
        return theme.palette.warning.main;
      case 'escalated':
        return theme.palette.info.main;
      default:
        return theme.palette.grey[500];
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <ApprovedIcon />;
      case 'rejected':
        return <RejectedIcon />;
      case 'pending':
        return <PendingIcon />;
      default:
        return <TaskIcon />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      case 'normal':
        return 'info';
      case 'low':
        return 'default';
      default:
        return 'default';
    }
  };

  const formatResponseTime = (hours: number) => {
    if (hours < 1) {
      return `${Math.round(hours * 60)}m`;
    } else if (hours < 24) {
      return `${hours.toFixed(1)}h`;
    } else {
      return `${(hours / 24).toFixed(1)}d`;
    }
  };

  if (loading && !refreshing) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <LinearProgress sx={{ width: '50%' }} />
      </Box>
    );
  }

  const pieChartData = summary ? [
    { name: 'Approved', value: summary.approved_count, color: theme.palette.success.main },
    { name: 'Rejected', value: summary.rejected_count, color: theme.palette.error.main },
    { name: 'Pending', value: summary.pending_count, color: theme.palette.warning.main },
    { name: 'Escalated', value: summary.escalated_count, color: theme.palette.info.main },
  ].filter(item => item.value > 0) : [];

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Approval Dashboard</Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={fetchDashboardData}
          disabled={refreshing}
        >
          Refresh
        </Button>
      </Box>

      {/* Summary Cards */}
      {summary && (
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Box>
                    <Typography color="text.secondary" variant="subtitle2">
                      Pending Approvals
                    </Typography>
                    <Typography variant="h4">
                      {summary.pending_count}
                    </Typography>
                    {summary.pending_urgent > 0 && (
                      <Chip
                        label={`${summary.pending_urgent} urgent`}
                        color="error"
                        size="small"
                        sx={{ mt: 1 }}
                      />
                    )}
                  </Box>
                  <Avatar sx={{ bgcolor: alpha(theme.palette.warning.main, 0.1) }}>
                    <PendingIcon sx={{ color: theme.palette.warning.main }} />
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Box>
                    <Typography color="text.secondary" variant="subtitle2">
                      Approved Today
                    </Typography>
                    <Typography variant="h4">
                      {summary.approved_count}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      <UpIcon sx={{ fontSize: 16, verticalAlign: 'middle' }} />
                      12% from yesterday
                    </Typography>
                  </Box>
                  <Avatar sx={{ bgcolor: alpha(theme.palette.success.main, 0.1) }}>
                    <ApprovedIcon sx={{ color: theme.palette.success.main }} />
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Box>
                    <Typography color="text.secondary" variant="subtitle2">
                      Avg Response Time
                    </Typography>
                    <Typography variant="h4">
                      {formatResponseTime(summary.average_response_time_hours)}
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={Math.min(100, (24 / summary.average_response_time_hours) * 100)}
                      sx={{ mt: 1 }}
                      color={summary.average_response_time_hours <= 24 ? 'success' : 'warning'}
                    />
                  </Box>
                  <Avatar sx={{ bgcolor: alpha(theme.palette.info.main, 0.1) }}>
                    <TimeIcon sx={{ color: theme.palette.info.main }} />
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Box>
                    <Typography color="text.secondary" variant="subtitle2">
                      SLA Compliance
                    </Typography>
                    <Typography variant="h4">
                      {(summary.sla_compliance_rate * 100).toFixed(1)}%
                    </Typography>
                    <Chip
                      label={summary.sla_compliance_rate >= 0.95 ? 'Excellent' : 'Needs Attention'}
                      color={summary.sla_compliance_rate >= 0.95 ? 'success' : 'warning'}
                      size="small"
                      sx={{ mt: 1 }}
                    />
                  </Box>
                  <Avatar sx={{ bgcolor: alpha(theme.palette.primary.main, 0.1) }}>
                    <TrendingIcon sx={{ color: theme.palette.primary.main }} />
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Main Content Tabs */}
      <Card>
        <Tabs
          value={tabValue}
          onChange={(e, v) => setTabValue(v)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Overview" />
          <Tab label="My Approvals" />
          <Tab label="Analytics" />
          <Tab label="Team Performance" />
        </Tabs>

        {/* Overview Tab */}
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            {/* Status Distribution */}
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Status Distribution
                </Typography>
                <Box height={300}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieChartData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {pieChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <ChartTooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              </Paper>
            </Grid>

            {/* Weekly Trend */}
            <Grid item xs={12} md={8}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Weekly Trend
                </Typography>
                <Box height={300}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={metrics?.weekly_trend || []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="date"
                        tickFormatter={(date) => format(parseISO(date), 'MMM d')}
                      />
                      <YAxis />
                      <ChartTooltip
                        labelFormatter={(date) => format(parseISO(date), 'MMM d, yyyy')}
                      />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="approved"
                        stackId="1"
                        stroke={theme.palette.success.main}
                        fill={theme.palette.success.main}
                      />
                      <Area
                        type="monotone"
                        dataKey="rejected"
                        stackId="1"
                        stroke={theme.palette.error.main}
                        fill={theme.palette.error.main}
                      />
                      <Area
                        type="monotone"
                        dataKey="pending"
                        stackId="1"
                        stroke={theme.palette.warning.main}
                        fill={theme.palette.warning.main}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>
              </Paper>
            </Grid>

            {/* Recent Requests */}
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">Recent Approval Requests</Typography>
                  <Button
                    size="small"
                    onClick={() => navigate('/approvals')}
                  >
                    View All
                  </Button>
                </Box>
                <List>
                  {recentRequests.map((request, index) => (
                    <React.Fragment key={request.id}>
                      {index > 0 && <Divider />}
                      <ListItem>
                        <ListItemAvatar>
                          <Avatar>
                            {getStatusIcon(request.status)}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Typography variant="subtitle1">
                                {request.title}
                              </Typography>
                              <Chip
                                label={request.priority}
                                size="small"
                                color={getPriorityColor(request.priority) as any}
                              />
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="body2" color="text.secondary">
                                Requested by {request.requestor.name} • {' '}
                                {format(parseISO(request.created_at), 'MMM d, HH:mm')}
                              </Typography>
                              {request.deadline && (
                                <Typography variant="caption" color="warning.main">
                                  <WarningIcon sx={{ fontSize: 14, verticalAlign: 'middle' }} />
                                  Due {format(parseISO(request.deadline), 'MMM d, HH:mm')}
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                        <ListItemSecondaryAction>
                          <Tooltip title="View Details">
                            <IconButton
                              edge="end"
                              onClick={() => navigate(`/approvals/${request.id}`)}
                            >
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                        </ListItemSecondaryAction>
                      </ListItem>
                    </React.Fragment>
                  ))}
                </List>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>

        {/* My Approvals Tab */}
        <TabPanel value={tabValue} index={1}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Pending My Action
                </Typography>
                <List>
                  {recentRequests
                    .filter(req => req.status === 'pending')
                    .map((request) => (
                      <ListItem key={request.id}>
                        <ListItemAvatar>
                          <Badge
                            color="error"
                            variant="dot"
                            invisible={request.priority !== 'high' && request.priority !== 'critical'}
                          >
                            <Avatar>
                              <TaskIcon />
                            </Avatar>
                          </Badge>
                        </ListItemAvatar>
                        <ListItemText
                          primary={request.title}
                          secondary={
                            <Box>
                              <Typography variant="body2">
                                {request.description}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                From {request.requestor.name} • {' '}
                                {format(parseISO(request.created_at), 'MMM d, HH:mm')}
                              </Typography>
                            </Box>
                          }
                        />
                        <ListItemSecondaryAction>
                          <Button
                            variant="contained"
                            size="small"
                            startIcon={<ActIcon />}
                            onClick={() => navigate(`/approvals/${request.id}`)}
                          >
                            Take Action
                          </Button>
                        </ListItemSecondaryAction>
                      </ListItem>
                    ))}
                </List>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Analytics Tab */}
        <TabPanel value={tabValue} index={2}>
          <Grid container spacing={3}>
            {/* By Department */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Approvals by Department
                </Typography>
                <Box height={300}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={metrics?.by_department || []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="department" />
                      <YAxis />
                      <ChartTooltip />
                      <Bar dataKey="count" fill={theme.palette.primary.main} />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Paper>
            </Grid>

            {/* Response Time Distribution */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Response Time Distribution
                </Typography>
                <Box height={300}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={metrics?.response_time_distribution || []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="range" />
                      <YAxis />
                      <ChartTooltip />
                      <Bar dataKey="count" fill={theme.palette.secondary.main} />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Paper>
            </Grid>

            {/* By Type */}
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Approvals by Type
                </Typography>
                <Box height={300}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={metrics?.by_type || []}
                      layout="horizontal"
                      margin={{ left: 80 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis type="category" dataKey="type" />
                      <ChartTooltip />
                      <Bar dataKey="count" fill={theme.palette.info.main} />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Team Performance Tab */}
        <TabPanel value={tabValue} index={3}>
          <Grid container spacing={3}>
            {/* Top Approvers */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Top Approvers
                </Typography>
                <List>
                  {metrics?.top_approvers.map((approver, index) => (
                    <ListItem key={index}>
                      <ListItemAvatar>
                        <Avatar>
                          <PersonIcon />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={approver.name}
                        secondary={
                          <Box>
                            <Typography variant="body2">
                              {approver.count} approvals
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Avg response: {formatResponseTime(approver.avg_response_time)}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Grid>

            {/* Top Requestors */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Top Requestors
                </Typography>
                <List>
                  {metrics?.top_requestors.map((requestor, index) => (
                    <ListItem key={index}>
                      <ListItemAvatar>
                        <Avatar>
                          <PersonIcon />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={requestor.name}
                        secondary={`${requestor.count} requests`}
                      />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>
      </Card>
    </Box>
  );
};

export default ApprovalDashboard;