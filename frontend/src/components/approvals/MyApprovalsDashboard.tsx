import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemSecondaryAction,
  Avatar,
  Chip,
  IconButton,
  Badge,
  LinearProgress,
  Paper,
  Divider,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  useTheme,
  alpha,
  Menu,
  MenuItem,
  Tooltip,
} from '@mui/material';
import {
  Assignment as TaskIcon,
  CheckCircle as ApprovedIcon,
  Cancel as RejectedIcon,
  Schedule as PendingIcon,
  AccessTime as TimeIcon,
  TrendingUp as StatsIcon,
  Inbox as InboxIcon,
  Send as SentIcon,
  Star as StarIcon,
  MoreVert as MoreIcon,
  FilterList as FilterIcon,
  Sort as SortIcon,
  PlayArrow as ActIcon,
  Visibility as ViewIcon,
  NotificationsActive as UrgentIcon,
  Group as DelegatedIcon,
} from '@mui/icons-material';
import {
  CircularProgressbar,
  buildStyles,
  CircularProgressbarWithChildren,
} from 'react-circular-progressbar';
import 'react-circular-progressbar/dist/styles.css';
import { format, parseISO, formatDistanceToNow } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import { useSnackbar } from 'notistack';

interface MyApprovalStats {
  assigned_to_me: number;
  completed_by_me: number;
  pending_my_action: number;
  created_by_me: number;
  avg_response_time_hours: number;
  completion_rate: number;
  period_days: number;
}

interface ApprovalItem {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  created_at: string;
  deadline?: string;
  type: string;
  requestor: {
    id: string;
    name: string;
    avatar?: string;
  };
  current_approver?: string;
  my_decision?: string;
  decided_at?: string;
}

type ViewMode = 'pending' | 'completed' | 'created' | 'delegated';
type SortBy = 'date' | 'priority' | 'deadline';

const MyApprovalsDashboard: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<MyApprovalStats | null>(null);
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('pending');
  const [sortBy, setSortBy] = useState<SortBy>('date');
  const [filterMenuEl, setFilterMenuEl] = useState<null | HTMLElement>(null);
  const [sortMenuEl, setSortMenuEl] = useState<null | HTMLElement>(null);
  const [selectedPriority, setSelectedPriority] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [viewMode, sortBy, selectedPriority]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Fetch stats
      const statsResponse = await fetch('/api/v1/approvals/dashboard/my-stats', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const statsData = await statsResponse.json();
      setStats(statsData);
      
      // Fetch approvals based on view mode
      let endpoint = '/api/v1/approvals';
      const params = new URLSearchParams();
      
      switch (viewMode) {
        case 'pending':
          params.append('status', 'pending');
          params.append('assigned_to_me', 'true');
          break;
        case 'completed':
          params.append('decided_by_me', 'true');
          break;
        case 'created':
          params.append('created_by_me', 'true');
          break;
        case 'delegated':
          params.append('delegated_by_me', 'true');
          break;
      }
      
      if (selectedPriority) {
        params.append('priority', selectedPriority);
      }
      
      params.append('sort', sortBy);
      params.append('limit', '20');
      
      const approvalsResponse = await fetch(`${endpoint}?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const approvalsData = await approvalsResponse.json();
      setApprovals(approvalsData.data || []);
      
    } catch (error) {
      enqueueSnackbar('Failed to load approvals data', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleQuickAction = async (approvalId: string, action: 'approve' | 'reject') => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/v1/approvals/${approvalId}/decide`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          decision: action === 'approve' ? 'approved' : 'rejected',
          comments: `Quick ${action} from dashboard`,
        }),
      });
      
      if (response.ok) {
        enqueueSnackbar(`Approval ${action}d successfully`, { variant: 'success' });
        fetchData();
      } else {
        throw new Error('Failed to process decision');
      }
    } catch (error) {
      enqueueSnackbar('Failed to process decision', { variant: 'error' });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <ApprovedIcon sx={{ color: theme.palette.success.main }} />;
      case 'rejected':
        return <RejectedIcon sx={{ color: theme.palette.error.main }} />;
      case 'pending':
        return <PendingIcon sx={{ color: theme.palette.warning.main }} />;
      default:
        return <TaskIcon />;
    }
  };

  const getPriorityColor = (priority: string): any => {
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

  const getTimeRemaining = (deadline: string) => {
    const now = new Date();
    const due = parseISO(deadline);
    const hoursRemaining = (due.getTime() - now.getTime()) / (1000 * 60 * 60);
    
    if (hoursRemaining < 0) {
      return { text: 'Overdue', color: 'error' };
    } else if (hoursRemaining < 24) {
      return { text: `${Math.round(hoursRemaining)}h remaining`, color: 'warning' };
    } else {
      return { text: `${Math.round(hoursRemaining / 24)}d remaining`, color: 'info' };
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <LinearProgress sx={{ width: '50%' }} />
      </Box>
    );
  }

  const completionPercentage = stats ? Math.round(stats.completion_rate * 100) : 0;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        My Approvals
      </Typography>

      {/* Stats Overview */}
      {stats && (
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="text.secondary" variant="caption">
                      PENDING MY ACTION
                    </Typography>
                    <Typography variant="h3" color="warning.main">
                      {stats.pending_my_action}
                    </Typography>
                    <Button
                      size="small"
                      startIcon={<InboxIcon />}
                      onClick={() => setViewMode('pending')}
                      sx={{ mt: 1 }}
                    >
                      View Pending
                    </Button>
                  </Box>
                  <Badge
                    badgeContent={stats.pending_my_action}
                    color="warning"
                    max={99}
                  >
                    <Avatar sx={{ bgcolor: alpha(theme.palette.warning.main, 0.1) }}>
                      <InboxIcon sx={{ color: theme.palette.warning.main }} />
                    </Avatar>
                  </Badge>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="text.secondary" variant="caption">
                      COMPLETION RATE
                    </Typography>
                    <Box width={100} height={100} mt={1}>
                      <CircularProgressbar
                        value={completionPercentage}
                        text={`${completionPercentage}%`}
                        styles={buildStyles({
                          textSize: '24px',
                          pathColor: theme.palette.success.main,
                          textColor: theme.palette.text.primary,
                          trailColor: theme.palette.action.disabled,
                        })}
                      />
                    </Box>
                  </Box>
                  <Box textAlign="right">
                    <Typography variant="h6">
                      {stats.completed_by_me}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      of {stats.assigned_to_me}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      completed
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box>
                  <Typography color="text.secondary" variant="caption">
                    AVG RESPONSE TIME
                  </Typography>
                  <Typography variant="h4">
                    {stats.avg_response_time_hours < 1
                      ? `${Math.round(stats.avg_response_time_hours * 60)}m`
                      : stats.avg_response_time_hours < 24
                      ? `${stats.avg_response_time_hours.toFixed(1)}h`
                      : `${(stats.avg_response_time_hours / 24).toFixed(1)}d`}
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(100, (24 / stats.avg_response_time_hours) * 100)}
                    sx={{ mt: 2 }}
                    color={stats.avg_response_time_hours <= 24 ? 'success' : 'warning'}
                  />
                  <Typography variant="caption" color="text.secondary">
                    Target: 24h
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box>
                  <Typography color="text.secondary" variant="caption">
                    REQUESTS CREATED
                  </Typography>
                  <Typography variant="h4">
                    {stats.created_by_me}
                  </Typography>
                  <Stack direction="row" spacing={1} mt={2}>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => navigate('/approvals/new')}
                    >
                      New Request
                    </Button>
                    <Button
                      size="small"
                      onClick={() => setViewMode('created')}
                    >
                      View All
                    </Button>
                  </Stack>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Main Content */}
      <Card>
        <CardContent>
          {/* View Mode Selector */}
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <ToggleButtonGroup
              value={viewMode}
              exclusive
              onChange={(e, value) => value && setViewMode(value)}
              size="small"
            >
              <ToggleButton value="pending">
                <Badge badgeContent={stats?.pending_my_action} color="warning">
                  <InboxIcon sx={{ mr: 1 }} />
                  Pending
                </Badge>
              </ToggleButton>
              <ToggleButton value="completed">
                <CheckCircle sx={{ mr: 1 }} />
                Completed
              </ToggleButton>
              <ToggleButton value="created">
                <SentIcon sx={{ mr: 1 }} />
                Created by Me
              </ToggleButton>
              <ToggleButton value="delegated">
                <DelegatedIcon sx={{ mr: 1 }} />
                Delegated
              </ToggleButton>
            </ToggleButtonGroup>

            <Stack direction="row" spacing={1}>
              <Tooltip title="Filter">
                <IconButton onClick={(e) => setFilterMenuEl(e.currentTarget)}>
                  <FilterIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Sort">
                <IconButton onClick={(e) => setSortMenuEl(e.currentTarget)}>
                  <SortIcon />
                </IconButton>
              </Tooltip>
            </Stack>
          </Box>

          {/* Approvals List */}
          <List>
            {approvals.length === 0 ? (
              <Box textAlign="center" py={4}>
                <Typography variant="h6" color="text.secondary">
                  No approvals found
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {viewMode === 'pending'
                    ? "You don't have any pending approvals"
                    : `No ${viewMode} approvals to display`}
                </Typography>
              </Box>
            ) : (
              approvals.map((approval, index) => (
                <React.Fragment key={approval.id}>
                  {index > 0 && <Divider />}
                  <ListItem sx={{ py: 2 }}>
                    <ListItemAvatar>
                      <Avatar>
                        {approval.priority === 'critical' || approval.priority === 'high' ? (
                          <UrgentIcon color="error" />
                        ) : (
                          getStatusIcon(approval.status)
                        )}
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="subtitle1">
                            {approval.title}
                          </Typography>
                          <Chip
                            label={approval.priority}
                            size="small"
                            color={getPriorityColor(approval.priority)}
                          />
                          <Chip
                            label={approval.type}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            {approval.description}
                          </Typography>
                          <Box display="flex" alignItems="center" gap={2} mt={0.5}>
                            <Typography variant="caption" color="text.secondary">
                              From {approval.requestor.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {formatDistanceToNow(parseISO(approval.created_at), { addSuffix: true })}
                            </Typography>
                            {approval.deadline && (
                              <Chip
                                label={getTimeRemaining(approval.deadline).text}
                                size="small"
                                color={getTimeRemaining(approval.deadline).color as any}
                              />
                            )}
                            {approval.my_decision && (
                              <Chip
                                label={`You ${approval.my_decision}`}
                                size="small"
                                color={approval.my_decision === 'approved' ? 'success' : 'error'}
                              />
                            )}
                          </Box>
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      {viewMode === 'pending' ? (
                        <Stack direction="row" spacing={1}>
                          <Tooltip title="Quick Approve">
                            <IconButton
                              color="success"
                              onClick={() => handleQuickAction(approval.id, 'approve')}
                            >
                              <ApprovedIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Quick Reject">
                            <IconButton
                              color="error"
                              onClick={() => handleQuickAction(approval.id, 'reject')}
                            >
                              <RejectedIcon />
                            </IconButton>
                          </Tooltip>
                          <Button
                            variant="contained"
                            size="small"
                            startIcon={<ViewIcon />}
                            onClick={() => navigate(`/approvals/${approval.id}`)}
                          >
                            Review
                          </Button>
                        </Stack>
                      ) : (
                        <Button
                          variant="outlined"
                          size="small"
                          startIcon={<ViewIcon />}
                          onClick={() => navigate(`/approvals/${approval.id}`)}
                        >
                          View Details
                        </Button>
                      )}
                    </ListItemSecondaryAction>
                  </ListItem>
                </React.Fragment>
              ))
            )}
          </List>
        </CardContent>
      </Card>

      {/* Filter Menu */}
      <Menu
        anchorEl={filterMenuEl}
        open={Boolean(filterMenuEl)}
        onClose={() => setFilterMenuEl(null)}
      >
        <MenuItem onClick={() => { setSelectedPriority(null); setFilterMenuEl(null); }}>
          All Priorities
        </MenuItem>
        <MenuItem onClick={() => { setSelectedPriority('critical'); setFilterMenuEl(null); }}>
          Critical
        </MenuItem>
        <MenuItem onClick={() => { setSelectedPriority('high'); setFilterMenuEl(null); }}>
          High
        </MenuItem>
        <MenuItem onClick={() => { setSelectedPriority('normal'); setFilterMenuEl(null); }}>
          Normal
        </MenuItem>
        <MenuItem onClick={() => { setSelectedPriority('low'); setFilterMenuEl(null); }}>
          Low
        </MenuItem>
      </Menu>

      {/* Sort Menu */}
      <Menu
        anchorEl={sortMenuEl}
        open={Boolean(sortMenuEl)}
        onClose={() => setSortMenuEl(null)}
      >
        <MenuItem onClick={() => { setSortBy('date'); setSortMenuEl(null); }}>
          Sort by Date
        </MenuItem>
        <MenuItem onClick={() => { setSortBy('priority'); setSortMenuEl(null); }}>
          Sort by Priority
        </MenuItem>
        <MenuItem onClick={() => { setSortBy('deadline'); setSortMenuEl(null); }}>
          Sort by Deadline
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default MyApprovalsDashboard;