import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  AlertTitle,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Grid,
  Tooltip,
  LinearProgress,
  FormHelperText,
  ToggleButton,
  ToggleButtonGroup,
  Divider,
  Stack,
} from '@mui/material';
import {
  TrendingUp as EscalateIcon,
  Timer as TimeIcon,
  Block as RejectIcon,
  Rule as RuleIcon,
  Warning as WarningIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Visibility as ViewIcon,
  Timeline as MetricsIcon,
  Person as PersonIcon,
  Group as GroupIcon,
  AccountTree as RoleIcon,
  Notifications as NotifyIcon,
  AutoMode as AutoIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import { format } from 'date-fns';

interface SLAViolation {
  task_id: string;
  title: string;
  created_at: string;
  deadline: string;
  hours_overdue: number;
  status: string;
  approvers: string[];
}

interface EscalationRule {
  rule_id: string;
  escalation_type: string;
  trigger_after_hours?: number;
  rejection_count?: number;
  escalation_action: string;
  escalate_to?: {
    approver_type: string;
    identifier: string;
    name: string;
  };
  escalation_message?: string;
}

interface EscalationMetrics {
  total_escalations: number;
  trigger_breakdown: Record<string, number>;
  type_breakdown: Record<string, number>;
  auto_approvals: number;
  period: {
    start: string;
    end: string;
  };
}

interface EscalationManagerProps {
  approvalTaskId?: string;
  onEscalate?: () => void;
}

const EscalationManager: React.FC<EscalationManagerProps> = ({
  approvalTaskId,
  onEscalate,
}) => {
  const { enqueueSnackbar } = useSnackbar();
  const [loading, setLoading] = useState(false);
  const [violations, setViolations] = useState<SLAViolation[]>([]);
  const [metrics, setMetrics] = useState<EscalationMetrics | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState(30);
  const [showEscalateDialog, setShowEscalateDialog] = useState(false);
  const [showAddRuleDialog, setShowAddRuleDialog] = useState(false);
  const [escalationHistory, setEscalationHistory] = useState<any[]>([]);
  
  // Manual escalation form
  const [escalationForm, setEscalationForm] = useState({
    reason: '',
    approverType: 'role',
    identifier: '',
    name: '',
    notifyMessage: '',
  });
  
  // New rule form
  const [newRule, setNewRule] = useState<Partial<EscalationRule>>({
    escalation_type: 'time_based',
    trigger_after_hours: 24,
    escalation_action: 'add_approver',
    escalate_to: {
      approver_type: 'role',
      identifier: '',
      name: '',
    },
    escalation_message: '',
  });

  useEffect(() => {
    fetchViolations();
    fetchMetrics();
  }, []);

  useEffect(() => {
    if (approvalTaskId) {
      fetchEscalationHistory();
    }
  }, [approvalTaskId]);

  const fetchViolations = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/escalations/sla-violations', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setViolations(data);
      }
    } catch (error) {
      enqueueSnackbar('Failed to fetch SLA violations', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const fetchMetrics = async () => {
    try {
      const response = await fetch(`/api/v1/escalations/metrics?days=${selectedPeriod}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setMetrics(data);
      }
    } catch (error) {
      enqueueSnackbar('Failed to fetch escalation metrics', { variant: 'error' });
    }
  };

  const fetchEscalationHistory = async () => {
    if (!approvalTaskId) return;
    
    try {
      const response = await fetch(`/api/v1/escalations/history/${approvalTaskId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setEscalationHistory(data.history || []);
      }
    } catch (error) {
      console.error('Failed to fetch escalation history:', error);
    }
  };

  const handleManualEscalation = async () => {
    if (!approvalTaskId) return;
    
    try {
      const response = await fetch('/api/v1/escalations/manual', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          approval_task_id: approvalTaskId,
          reason: escalationForm.reason,
          escalate_to: {
            approver_type: escalationForm.approverType,
            identifier: escalationForm.identifier,
            name: escalationForm.name,
          },
          notify_message: escalationForm.notifyMessage,
        }),
      });
      
      if (response.ok) {
        enqueueSnackbar('Approval escalated successfully', { variant: 'success' });
        setShowEscalateDialog(false);
        if (onEscalate) onEscalate();
        fetchEscalationHistory();
      } else {
        const error = await response.json();
        enqueueSnackbar(error.detail || 'Failed to escalate approval', { variant: 'error' });
      }
    } catch (error) {
      enqueueSnackbar('Failed to escalate approval', { variant: 'error' });
    }
  };

  const handleAddRule = async () => {
    if (!approvalTaskId || !newRule.escalate_to?.identifier) return;
    
    try {
      const response = await fetch('/api/v1/escalations/rules', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          approval_task_id: approvalTaskId,
          rule: newRule,
        }),
      });
      
      if (response.ok) {
        enqueueSnackbar('Escalation rule added successfully', { variant: 'success' });
        setShowAddRuleDialog(false);
      } else {
        const error = await response.json();
        enqueueSnackbar(error.detail || 'Failed to add escalation rule', { variant: 'error' });
      }
    } catch (error) {
      enqueueSnackbar('Failed to add escalation rule', { variant: 'error' });
    }
  };

  const getEscalationTypeIcon = (type: string) => {
    switch (type) {
      case 'time_based':
        return <TimeIcon />;
      case 'rejection_based':
        return <RejectIcon />;
      case 'manual':
        return <PersonIcon />;
      default:
        return <RuleIcon />;
    }
  };

  const getEscalationActionIcon = (action: string) => {
    switch (action) {
      case 'add_approver':
        return <AddIcon />;
      case 'replace_approver':
        return <EditIcon />;
      case 'notify':
        return <NotifyIcon />;
      case 'auto_approve':
        return <AutoIcon />;
      case 'cancel':
        return <CancelIcon />;
      default:
        return <RuleIcon />;
    }
  };

  const getSeverityColor = (hoursOverdue: number): 'error' | 'warning' | 'info' => {
    if (hoursOverdue > 48) return 'error';
    if (hoursOverdue > 24) return 'warning';
    return 'info';
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Escalation Management
      </Typography>

      {/* SLA Violations */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              <WarningIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
              SLA Violations
            </Typography>
            <Button
              startIcon={<ViewIcon />}
              onClick={fetchViolations}
              disabled={loading}
            >
              Refresh
            </Button>
          </Box>

          {loading && <LinearProgress />}

          {violations.length === 0 ? (
            <Alert severity="success">
              <AlertTitle>No SLA Violations</AlertTitle>
              All approvals are within their SLA deadlines.
            </Alert>
          ) : (
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Title</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Deadline</TableCell>
                    <TableCell>Overdue</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {violations.map((violation) => (
                    <TableRow key={violation.task_id}>
                      <TableCell>{violation.title}</TableCell>
                      <TableCell>
                        {format(new Date(violation.created_at), 'MMM d, HH:mm')}
                      </TableCell>
                      <TableCell>
                        {format(new Date(violation.deadline), 'MMM d, HH:mm')}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={`${violation.hours_overdue.toFixed(1)}h`}
                          color={getSeverityColor(violation.hours_overdue)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={violation.status}
                          variant="outlined"
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Tooltip title="View details">
                          <IconButton size="small">
                            <ViewIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Escalation Metrics */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              <MetricsIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
              Escalation Metrics
            </Typography>
            <ToggleButtonGroup
              value={selectedPeriod}
              exclusive
              onChange={(e, value) => {
                if (value) {
                  setSelectedPeriod(value);
                  fetchMetrics();
                }
              }}
              size="small"
            >
              <ToggleButton value={7}>7 Days</ToggleButton>
              <ToggleButton value={30}>30 Days</ToggleButton>
              <ToggleButton value={90}>90 Days</ToggleButton>
            </ToggleButtonGroup>
          </Box>

          {metrics && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={3}>
                <Paper sx={{ p: 2, textAlign: 'center' }}>
                  <Typography variant="h4">{metrics.total_escalations}</Typography>
                  <Typography color="text.secondary">Total Escalations</Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={3}>
                <Paper sx={{ p: 2, textAlign: 'center' }}>
                  <Typography variant="h4">{metrics.auto_approvals}</Typography>
                  <Typography color="text.secondary">Auto-Approvals</Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={3}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    By Trigger
                  </Typography>
                  {Object.entries(metrics.trigger_breakdown).map(([trigger, count]) => (
                    <Box key={trigger} display="flex" justifyContent="space-between">
                      <Typography variant="body2">{trigger}:</Typography>
                      <Typography variant="body2" fontWeight="bold">{count}</Typography>
                    </Box>
                  ))}
                </Paper>
              </Grid>
              <Grid item xs={12} md={3}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    By Type
                  </Typography>
                  {Object.entries(metrics.type_breakdown).map(([type, count]) => (
                    <Box key={type} display="flex" justifyContent="space-between">
                      <Typography variant="body2">{type}:</Typography>
                      <Typography variant="body2" fontWeight="bold">{count}</Typography>
                    </Box>
                  ))}
                </Paper>
              </Grid>
            </Grid>
          )}
        </CardContent>
      </Card>

      {/* Task-specific actions */}
      {approvalTaskId && (
        <>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">
                  Escalation Actions
                </Typography>
              </Box>
              
              <Stack direction="row" spacing={2}>
                <Button
                  variant="contained"
                  startIcon={<EscalateIcon />}
                  onClick={() => setShowEscalateDialog(true)}
                >
                  Manual Escalation
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={() => setShowAddRuleDialog(true)}
                >
                  Add Escalation Rule
                </Button>
              </Stack>
            </CardContent>
          </Card>

          {/* Escalation History */}
          {escalationHistory.length > 0 && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Escalation History
                </Typography>
                <List>
                  {escalationHistory.map((event) => (
                    <ListItem key={event.id}>
                      <ListItemIcon>
                        {getEscalationTypeIcon(event.details?.trigger || 'manual')}
                      </ListItemIcon>
                      <ListItemText
                        primary={event.action}
                        secondary={
                          <>
                            <Typography variant="caption" component="span">
                              {format(new Date(event.created_at), 'MMM d, yyyy HH:mm')}
                            </Typography>
                            {event.details?.escalated_to && (
                              <Typography variant="caption" component="span">
                                {' • Escalated to: '}{event.details.escalated_to}
                              </Typography>
                            )}
                          </>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Manual Escalation Dialog */}
      <Dialog
        open={showEscalateDialog}
        onClose={() => setShowEscalateDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Manual Escalation</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Reason for Escalation"
                multiline
                rows={3}
                value={escalationForm.reason}
                onChange={(e) => setEscalationForm({ ...escalationForm, reason: e.target.value })}
                required
              />
            </Grid>
            
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Approver Type</InputLabel>
                <Select
                  value={escalationForm.approverType}
                  onChange={(e) => setEscalationForm({ ...escalationForm, approverType: e.target.value })}
                >
                  <MenuItem value="user">User</MenuItem>
                  <MenuItem value="role">Role</MenuItem>
                  <MenuItem value="group">Group</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Identifier"
                value={escalationForm.identifier}
                onChange={(e) => setEscalationForm({ ...escalationForm, identifier: e.target.value })}
                helperText="User ID, role name, or group ID"
                required
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Name"
                value={escalationForm.name}
                onChange={(e) => setEscalationForm({ ...escalationForm, name: e.target.value })}
                required
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Notification Message"
                multiline
                rows={2}
                value={escalationForm.notifyMessage}
                onChange={(e) => setEscalationForm({ ...escalationForm, notifyMessage: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowEscalateDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleManualEscalation}
            disabled={!escalationForm.reason || !escalationForm.identifier || !escalationForm.name}
          >
            Escalate
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add Rule Dialog */}
      <Dialog
        open={showAddRuleDialog}
        onClose={() => setShowAddRuleDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Escalation Rule</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Escalation Type</InputLabel>
                <Select
                  value={newRule.escalation_type}
                  onChange={(e) => setNewRule({ ...newRule, escalation_type: e.target.value })}
                >
                  <MenuItem value="time_based">Time Based</MenuItem>
                  <MenuItem value="rejection_based">Rejection Based</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            {newRule.escalation_type === 'time_based' && (
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  type="number"
                  label="Trigger After Hours"
                  value={newRule.trigger_after_hours}
                  onChange={(e) => setNewRule({ ...newRule, trigger_after_hours: parseInt(e.target.value) })}
                />
              </Grid>
            )}
            
            {newRule.escalation_type === 'rejection_based' && (
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  type="number"
                  label="Rejection Count"
                  value={newRule.rejection_count || 1}
                  onChange={(e) => setNewRule({ ...newRule, rejection_count: parseInt(e.target.value) })}
                />
              </Grid>
            )}
            
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Escalation Action</InputLabel>
                <Select
                  value={newRule.escalation_action}
                  onChange={(e) => setNewRule({ ...newRule, escalation_action: e.target.value })}
                >
                  <MenuItem value="add_approver">Add Approver</MenuItem>
                  <MenuItem value="replace_approver">Replace Approver</MenuItem>
                  <MenuItem value="notify">Notify Only</MenuItem>
                  <MenuItem value="auto_approve">Auto Approve</MenuItem>
                  <MenuItem value="cancel">Cancel</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            {(newRule.escalation_action === 'add_approver' || 
              newRule.escalation_action === 'replace_approver') && (
              <>
                <Grid item xs={12}>
                  <Typography variant="subtitle2" gutterBottom>
                    Escalate To
                  </Typography>
                </Grid>
                
                <Grid item xs={12}>
                  <FormControl fullWidth>
                    <InputLabel>Approver Type</InputLabel>
                    <Select
                      value={newRule.escalate_to?.approver_type || 'role'}
                      onChange={(e) => setNewRule({
                        ...newRule,
                        escalate_to: {
                          ...newRule.escalate_to!,
                          approver_type: e.target.value,
                        },
                      })}
                    >
                      <MenuItem value="user">User</MenuItem>
                      <MenuItem value="role">Role</MenuItem>
                      <MenuItem value="group">Group</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Identifier"
                    value={newRule.escalate_to?.identifier || ''}
                    onChange={(e) => setNewRule({
                      ...newRule,
                      escalate_to: {
                        ...newRule.escalate_to!,
                        identifier: e.target.value,
                      },
                    })}
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Name"
                    value={newRule.escalate_to?.name || ''}
                    onChange={(e) => setNewRule({
                      ...newRule,
                      escalate_to: {
                        ...newRule.escalate_to!,
                        name: e.target.value,
                      },
                    })}
                  />
                </Grid>
              </>
            )}
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Escalation Message"
                multiline
                rows={2}
                value={newRule.escalation_message}
                onChange={(e) => setNewRule({ ...newRule, escalation_message: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAddRuleDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleAddRule}
          >
            Add Rule
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EscalationManager;