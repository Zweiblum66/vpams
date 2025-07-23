import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  IconButton,
  Tooltip,
  Chip,
  Avatar,
  AvatarGroup,
  LinearProgress,
  Alert,
  Paper,
  Divider,
  Stack,
  Badge,
  CardHeader,
  CardActions,
  Menu,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  SelectChangeEvent,
  Tabs,
  Tab,
  Container,
} from '@mui/material';
import {
  PendingActions,
  CheckCircle,
  Cancel,
  Schedule,
  TrendingUp,
  Timeline,
  Assessment,
  Refresh,
  FilterList,
  Sort,
  MoreVert,
  NotificationsActive,
  Person,
  Business,
  Priority,
  CalendarToday,
  Speed,
  ThumbUp,
  ThumbDown,
  AccessTime,
  Group,
  Assignment,
  AttachFile,
  Comment,
  Escalate,
  Warning,
} from '@mui/icons-material';
import { format, formatDistanceToNow } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import {
  useGetApprovalDashboardStatsQuery,
  useGetApprovalMetricsQuery,
  useGetMyApprovalsToReviewQuery,
  useGetMyApprovalRequestsQuery,
  useRespondToApprovalRequestMutation,
} from '../../store/api/workflowApi';
import { ApprovalRequest, ApprovalPriority, ApprovalStatus } from '../../types/workflow';

interface ApprovalDashboardProps {
  refreshInterval?: number;
}

const priorityColors: Record<ApprovalPriority, 'error' | 'warning' | 'info' | 'success'> = {
  urgent: 'error',
  high: 'warning',
  medium: 'info',
  low: 'success',
};

const statusColors: Record<ApprovalStatus, 'warning' | 'success' | 'error' | 'info' | 'secondary' | 'primary'> = {
  pending: 'warning',
  in_review: 'info',
  approved: 'success',
  rejected: 'error',
  cancelled: 'secondary',
  escalated: 'primary',
};

const ApprovalDashboard: React.FC<ApprovalDashboardProps> = ({ refreshInterval = 30000 }) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0);
  const [selectedPeriod, setSelectedPeriod] = useState<'day' | 'week' | 'month'>('week');
  const [contextMenu, setContextMenu] = useState<{
    mouseX: number;
    mouseY: number;
    approval: ApprovalRequest;
  } | null>(null);

  // API hooks
  const { data: dashboardStats, isLoading: statsLoading, refetch: refetchStats } = useGetApprovalDashboardStatsQuery();
  const { data: metrics, isLoading: metricsLoading } = useGetApprovalMetricsQuery({
    period: selectedPeriod,
  });
  const { data: myApprovals, isLoading: myApprovalsLoading } = useGetMyApprovalsToReviewQuery({
    page: 1,
    limit: 10,
  });
  const { data: myRequests, isLoading: myRequestsLoading } = useGetMyApprovalRequestsQuery({
    page: 1,
    limit: 10,
    status: ['pending', 'in_review'],
  });

  const [respondToApproval] = useRespondToApprovalRequestMutation();

  const handleTabChange = useCallback((event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  }, []);

  const handlePeriodChange = useCallback((event: SelectChangeEvent<string>) => {
    setSelectedPeriod(event.target.value as 'day' | 'week' | 'month');
  }, []);

  const handleContextMenu = useCallback((event: React.MouseEvent, approval: ApprovalRequest) => {
    event.preventDefault();
    setContextMenu({
      mouseX: event.clientX - 2,
      mouseY: event.clientY - 4,
      approval,
    });
  }, []);

  const handleContextMenuClose = useCallback(() => {
    setContextMenu(null);
  }, []);

  const handleQuickApprove = useCallback(async (approvalId: string) => {
    try {
      await respondToApproval({
        id: approvalId,
        response: 'approve',
        comment: 'Quick approval from dashboard',
      }).unwrap();
      refetchStats();
    } catch (error) {
      console.error('Failed to approve request:', error);
    }
    handleContextMenuClose();
  }, [respondToApproval, refetchStats]);

  const handleQuickReject = useCallback(async (approvalId: string) => {
    try {
      await respondToApproval({
        id: approvalId,
        response: 'reject',
        comment: 'Quick rejection from dashboard',
      }).unwrap();
      refetchStats();
    } catch (error) {
      console.error('Failed to reject request:', error);
    }
    handleContextMenuClose();
  }, [respondToApproval, refetchStats]);

  const handleViewDetails = useCallback((approvalId: string) => {
    navigate(`/approvals/${approvalId}`);
    handleContextMenuClose();
  }, [navigate]);

  const formatApprovalTime = (createdAt: string) => {
    return formatDistanceToNow(new Date(createdAt), { addSuffix: true });
  };

  const getPriorityIcon = (priority: ApprovalPriority) => {
    switch (priority) {
      case 'urgent':
        return <Warning color="error" />;
      case 'high':
        return <Priority color="warning" />;
      case 'medium':
        return <Schedule color="info" />;
      case 'low':
        return <AccessTime color="success" />;
      default:
        return <Schedule />;
    }
  };

  const urgentApprovals = useMemo(() => {
    return myApprovals?.data.filter(approval => approval.priority === 'urgent') || [];
  }, [myApprovals]);

  const overdueApprovals = useMemo(() => {
    return myApprovals?.data.filter(approval => {
      if (!approval.due_date) return false;
      return new Date(approval.due_date) < new Date();
    }) || [];
  }, [myApprovals]);

  const renderStatsCard = (title: string, value: number, icon: React.ReactNode, color: string, subtitle?: string) => (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="h4" component="div" sx={{ fontWeight: 'bold', color }}>
              {value}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {title}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box sx={{ color }}>{icon}</Box>
        </Box>
      </CardContent>
    </Card>
  );

  const renderApprovalCard = (approval: ApprovalRequest) => (
    <Card
      key={approval.id}
      sx={{
        mb: 2,
        cursor: 'pointer',
        '&:hover': { bgcolor: 'action.hover' },
        border: approval.priority === 'urgent' ? '2px solid #f44336' : undefined,
      }}
      onClick={() => handleViewDetails(approval.id)}
      onContextMenu={(e) => handleContextMenu(e, approval)}
    >
      <CardHeader
        avatar={
          <Avatar src={approval.requester.avatar_url}>
            {approval.requester.name.charAt(0)}
          </Avatar>
        }
        title={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 'medium' }}>
              {approval.title}
            </Typography>
            <Chip
              label={approval.priority}
              size="small"
              color={priorityColors[approval.priority]}
              variant="outlined"
            />
            <Chip
              label={approval.status}
              size="small"
              color={statusColors[approval.status]}
              variant="filled"
            />
          </Box>
        }
        subheader={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              By {approval.requester.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {formatApprovalTime(approval.created_at)}
            </Typography>
            {approval.due_date && (
              <Typography
                variant="body2"
                color={new Date(approval.due_date) < new Date() ? 'error' : 'text.secondary'}
              >
                Due {format(new Date(approval.due_date), 'MMM d, yyyy')}
              </Typography>
            )}
          </Box>
        }
        action={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {getPriorityIcon(approval.priority)}
            <IconButton onClick={(e) => handleContextMenu(e, approval)}>
              <MoreVert />
            </IconButton>
          </Box>
        }
      />
      {approval.description && (
        <CardContent sx={{ pt: 0 }}>
          <Typography variant="body2" color="text.secondary">
            {approval.description}
          </Typography>
        </CardContent>
      )}
    </Card>
  );

  if (statsLoading || metricsLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
          <LinearProgress sx={{ width: '50%' }} />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          Approval Dashboard
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Period</InputLabel>
            <Select
              value={selectedPeriod}
              onChange={handlePeriodChange}
              label="Period"
            >
              <MenuItem value="day">Today</MenuItem>
              <MenuItem value="week">This Week</MenuItem>
              <MenuItem value="month">This Month</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => refetchStats()}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Urgent Alerts */}
      {urgentApprovals.length > 0 && (
        <Alert severity="error" sx={{ mb: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
            {urgentApprovals.length} urgent approval{urgentApprovals.length > 1 ? 's' : ''} require immediate attention
          </Typography>
        </Alert>
      )}

      {overdueApprovals.length > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
            {overdueApprovals.length} overdue approval{overdueApprovals.length > 1 ? 's' : ''}
          </Typography>
        </Alert>
      )}

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          {renderStatsCard(
            'Pending Approvals',
            dashboardStats?.my_pending || 0,
            <PendingActions fontSize="large" />,
            '#ff9800',
            'Assigned to you'
          )}
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          {renderStatsCard(
            'Approved Today',
            dashboardStats?.my_approved || 0,
            <CheckCircle fontSize="large" />,
            '#4caf50',
            'Your approvals'
          )}
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          {renderStatsCard(
            'Avg Response Time',
            Math.round(dashboardStats?.avg_approval_time || 0),
            <Speed fontSize="large" />,
            '#2196f3',
            'Hours'
          )}
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          {renderStatsCard(
            'Approval Rate',
            Math.round((dashboardStats?.approval_rate || 0) * 100),
            <TrendingUp fontSize="large" />,
            '#9c27b0',
            'Percentage'
          )}
        </Grid>
      </Grid>

      {/* Main Content */}
      <Paper sx={{ mb: 3 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={handleTabChange}>
            <Tab 
              label={
                <Badge badgeContent={myApprovals?.data.length || 0} color="primary">
                  My Approvals
                </Badge>
              }
              icon={<Assignment />}
            />
            <Tab 
              label={
                <Badge badgeContent={myRequests?.data.length || 0} color="secondary">
                  My Requests
                </Badge>
              }
              icon={<Person />}
            />
            <Tab label="Analytics" icon={<Assessment />} />
          </Tabs>
        </Box>

        <Box sx={{ p: 3 }}>
          {activeTab === 0 && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Approvals Waiting for Your Review
              </Typography>
              {myApprovalsLoading ? (
                <LinearProgress />
              ) : myApprovals?.data.length === 0 ? (
                <Alert severity="info">No approvals waiting for your review.</Alert>
              ) : (
                <Box>
                  {myApprovals?.data.map(renderApprovalCard)}
                  {myApprovals && myApprovals.total > 10 && (
                    <Button
                      variant="outlined"
                      onClick={() => navigate('/approvals/my-approvals')}
                      sx={{ mt: 2 }}
                    >
                      View All ({myApprovals.total})
                    </Button>
                  )}
                </Box>
              )}
            </Box>
          )}

          {activeTab === 1 && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Your Approval Requests
              </Typography>
              {myRequestsLoading ? (
                <LinearProgress />
              ) : myRequests?.data.length === 0 ? (
                <Alert severity="info">You have no pending approval requests.</Alert>
              ) : (
                <Box>
                  {myRequests?.data.map(renderApprovalCard)}
                  {myRequests && myRequests.total > 10 && (
                    <Button
                      variant="outlined"
                      onClick={() => navigate('/approvals/my-requests')}
                      sx={{ mt: 2 }}
                    >
                      View All ({myRequests.total})
                    </Button>
                  )}
                </Box>
              )}
            </Box>
          )}

          {activeTab === 2 && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Approval Analytics
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography variant="subtitle1" sx={{ mb: 2 }}>
                        Approval Summary
                      </Typography>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">Total Requests</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                          {metrics?.metrics.total_requests || 0}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">Approved</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'success.main' }}>
                          {metrics?.metrics.approved_requests || 0}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">Rejected</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'error.main' }}>
                          {metrics?.metrics.rejected_requests || 0}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">Pending</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'warning.main' }}>
                          {metrics?.metrics.pending_requests || 0}
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography variant="subtitle1" sx={{ mb: 2 }}>
                        Performance Metrics
                      </Typography>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">Avg Response Time</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                          {Math.round(metrics?.metrics.avg_approval_time_hours || 0)}h
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">Approval Rate</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                          {Math.round(metrics?.metrics.approval_rate_percentage || 0)}%
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">Escalated</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                          {metrics?.metrics.escalated_requests || 0}
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Box>
          )}
        </Box>
      </Paper>

      {/* Context Menu */}
      <Menu
        open={contextMenu !== null}
        onClose={handleContextMenuClose}
        anchorReference="anchorPosition"
        anchorPosition={
          contextMenu !== null
            ? { top: contextMenu.mouseY, left: contextMenu.mouseX }
            : undefined
        }
      >
        <MenuItem onClick={() => handleViewDetails(contextMenu?.approval.id!)}>
          <Assignment sx={{ mr: 1 }} />
          View Details
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={() => handleQuickApprove(contextMenu?.approval.id!)}
          sx={{ color: 'success.main' }}
        >
          <ThumbUp sx={{ mr: 1 }} />
          Quick Approve
        </MenuItem>
        <MenuItem
          onClick={() => handleQuickReject(contextMenu?.approval.id!)}
          sx={{ color: 'error.main' }}
        >
          <ThumbDown sx={{ mr: 1 }} />
          Quick Reject
        </MenuItem>
        <Divider />
        <MenuItem onClick={() => navigate(`/approvals/${contextMenu?.approval.id}/escalate`)}>
          <Escalate sx={{ mr: 1 }} />
          Escalate
        </MenuItem>
      </Menu>
    </Container>
  );
};

export default ApprovalDashboard;