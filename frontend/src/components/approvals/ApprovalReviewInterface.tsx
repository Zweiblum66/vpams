import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Divider,
  Alert,
  AlertTitle,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  CircularProgress,
  LinearProgress,
  IconButton,
  Tooltip,
  Grid,
  Paper,
  Tab,
  Tabs,
  Badge,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
} from '@mui/material';
import {
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
  PersonAdd as DelegateIcon,
  History as HistoryIcon,
  AttachFile as AttachmentIcon,
  Comment as CommentIcon,
  Timer as TimerIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  GetApp as DownloadIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { useSnackbar } from 'notistack';
import { format, formatDistanceToNow } from 'date-fns';

interface ApprovalRequest {
  request_id: string;
  title: string;
  description: string;
  status: string;
  requestor_name: string;
  created_at: string;
  deadline_at?: string;
  context_data: any;
  attachments: any[];
  approval_config: {
    approval_type: string;
    approvers: any[];
    voting_strategy?: string;
    approval_threshold?: number;
  };
  approval_decisions: any[];
  current_level: number;
  escalation_history: any[];
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
      id={`approval-tabpanel-${index}`}
      aria-labelledby={`approval-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const ApprovalReviewInterface: React.FC = () => {
  const { requestId } = useParams<{ requestId: string }>();
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  
  const [approval, setApproval] = useState<ApprovalRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [decision, setDecision] = useState<'approve' | 'reject' | ''>('');
  const [comments, setComments] = useState('');
  const [showDelegateDialog, setShowDelegateDialog] = useState(false);
  const [delegateEmail, setDelegateEmail] = useState('');
  const [delegateReason, setDelegateReason] = useState('');
  const [tabValue, setTabValue] = useState(0);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['details', 'context'])
  );

  useEffect(() => {
    fetchApprovalDetails();
  }, [requestId]);

  const fetchApprovalDetails = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/approvals/${requestId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch approval details');
      }
      
      const data = await response.json();
      setApproval(data);
    } catch (error) {
      enqueueSnackbar('Failed to load approval details', { variant: 'error' });
      navigate('/approvals');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitDecision = async () => {
    if (!decision) {
      enqueueSnackbar('Please select a decision', { variant: 'warning' });
      return;
    }

    try {
      setSubmitting(true);
      const response = await fetch(`/api/v1/approvals/${requestId}/decisions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          decision: decision === 'approve' ? 'approved' : 'rejected',
          comments,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit decision');
      }

      enqueueSnackbar(
        `Approval ${decision === 'approve' ? 'approved' : 'rejected'} successfully`,
        { variant: 'success' }
      );
      navigate('/approvals');
    } catch (error) {
      enqueueSnackbar('Failed to submit decision', { variant: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelegate = async () => {
    if (!delegateEmail || !delegateReason) {
      enqueueSnackbar('Please fill in all delegation fields', { variant: 'warning' });
      return;
    }

    try {
      setSubmitting(true);
      const response = await fetch(`/api/v1/approvals/${requestId}/delegate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          delegate_to: {
            approver_type: 'user',
            identifier: delegateEmail,
            name: delegateEmail,
            email: delegateEmail,
          },
          delegation_reason: delegateReason,
          retain_visibility: true,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to delegate approval');
      }

      enqueueSnackbar('Approval delegated successfully', { variant: 'success' });
      navigate('/approvals');
    } catch (error) {
      enqueueSnackbar('Failed to delegate approval', { variant: 'error' });
    } finally {
      setSubmitting(false);
      setShowDelegateDialog(false);
    }
  };

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'warning';
      case 'approved':
        return 'success';
      case 'rejected':
        return 'error';
      case 'escalated':
        return 'info';
      default:
        return 'default';
    }
  };

  const calculateTimeRemaining = () => {
    if (!approval?.deadline_at) return null;
    
    const deadline = new Date(approval.deadline_at);
    const now = new Date();
    const hoursRemaining = Math.floor((deadline.getTime() - now.getTime()) / (1000 * 60 * 60));
    
    if (hoursRemaining < 0) {
      return { text: 'Overdue', color: 'error' };
    } else if (hoursRemaining < 24) {
      return { text: `${hoursRemaining} hours remaining`, color: 'warning' };
    } else {
      const daysRemaining = Math.floor(hoursRemaining / 24);
      return { text: `${daysRemaining} days remaining`, color: 'info' };
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!approval) {
    return (
      <Alert severity="error">
        <AlertTitle>Approval Not Found</AlertTitle>
        The requested approval could not be found.
      </Alert>
    );
  }

  const timeRemaining = calculateTimeRemaining();
  const hasAlreadyDecided = approval.approval_decisions.some(
    d => d.approver_id === localStorage.getItem('userId')
  );

  return (
    <Box>
      {/* Header */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={3} alignItems="center">
          <Grid item xs={12} md={8}>
            <Typography variant="h4" gutterBottom>
              {approval.title}
            </Typography>
            <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
              <Chip
                label={approval.status.toUpperCase()}
                color={getStatusColor(approval.status) as any}
                size="small"
              />
              <Typography variant="body2" color="text.secondary">
                Requested by {approval.requestor_name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
              </Typography>
              {timeRemaining && (
                <Chip
                  icon={<TimerIcon />}
                  label={timeRemaining.text}
                  color={timeRemaining.color as any}
                  size="small"
                />
              )}
            </Box>
          </Grid>
          <Grid item xs={12} md={4} textAlign={{ xs: 'left', md: 'right' }}>
            <Box display="flex" gap={1} justifyContent={{ xs: 'flex-start', md: 'flex-end' }} flexWrap="wrap">
              <Button
                variant="outlined"
                startIcon={<HistoryIcon />}
                onClick={() => setTabValue(2)}
              >
                History
              </Button>
              <Button
                variant="outlined"
                startIcon={<DelegateIcon />}
                onClick={() => setShowDelegateDialog(true)}
                disabled={hasAlreadyDecided || approval.status !== 'pending'}
              >
                Delegate
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Progress for Sequential/Multi-level Approvals */}
      {approval.approval_config.approval_type === 'sequential' && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Approval Progress
            </Typography>
            <Stepper activeStep={approval.current_level} orientation="vertical">
              {approval.approval_config.approvers.map((approver, index) => {
                const decision = approval.approval_decisions.find(
                  d => d.approver_id === approver.identifier
                );
                return (
                  <Step key={index} completed={!!decision}>
                    <StepLabel
                      optional={
                        decision && (
                          <Typography variant="caption">
                            {decision.decision} - {format(new Date(decision.decided_at), 'PPp')}
                          </Typography>
                        )
                      }
                    >
                      {approver.name}
                    </StepLabel>
                    <StepContent>
                      {decision && decision.comments && (
                        <Typography variant="body2" color="text.secondary">
                          {decision.comments}
                        </Typography>
                      )}
                    </StepContent>
                  </Step>
                );
              })}
            </Stepper>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Card>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="Details" />
          <Tab label="Context & Attachments" />
          <Tab label="History & Activity" />
          {approval.approval_config.approval_type === 'voting' && (
            <Tab label="Voting Status" />
          )}
        </Tabs>

        {/* Details Tab */}
        <TabPanel value={tabValue} index={0}>
          <CardContent>
            <Box mb={3}>
              <Typography variant="h6" gutterBottom>
                Description
              </Typography>
              <Typography variant="body1" paragraph>
                {approval.description}
              </Typography>
            </Box>

            {!hasAlreadyDecided && approval.status === 'pending' && (
              <Box>
                <Divider sx={{ my: 3 }} />
                <Typography variant="h6" gutterBottom>
                  Your Decision
                </Typography>
                
                <FormControl component="fieldset" sx={{ mb: 2 }}>
                  <RadioGroup
                    value={decision}
                    onChange={(e) => setDecision(e.target.value as any)}
                  >
                    <FormControlLabel
                      value="approve"
                      control={<Radio color="success" />}
                      label={
                        <Box display="flex" alignItems="center">
                          <ApproveIcon sx={{ mr: 1, color: 'success.main' }} />
                          Approve
                        </Box>
                      }
                    />
                    <FormControlLabel
                      value="reject"
                      control={<Radio color="error" />}
                      label={
                        <Box display="flex" alignItems="center">
                          <RejectIcon sx={{ mr: 1, color: 'error.main' }} />
                          Reject
                        </Box>
                      }
                    />
                  </RadioGroup>
                </FormControl>

                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="Comments (Optional)"
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="Add any comments or conditions for your decision..."
                  sx={{ mb: 3 }}
                />

                <Box display="flex" gap={2}>
                  <Button
                    variant="contained"
                    color={decision === 'approve' ? 'success' : 'error'}
                    startIcon={decision === 'approve' ? <ApproveIcon /> : <RejectIcon />}
                    onClick={handleSubmitDecision}
                    disabled={!decision || submitting}
                  >
                    {submitting ? 'Submitting...' : `${decision === 'approve' ? 'Approve' : 'Reject'}`}
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => navigate('/approvals')}
                  >
                    Cancel
                  </Button>
                </Box>
              </Box>
            )}

            {hasAlreadyDecided && (
              <Alert severity="info">
                <AlertTitle>You have already made a decision</AlertTitle>
                Check the History tab to see your decision and comments.
              </Alert>
            )}
          </CardContent>
        </TabPanel>

        {/* Context & Attachments Tab */}
        <TabPanel value={tabValue} index={1}>
          <CardContent>
            {/* Context Data */}
            <Box mb={3}>
              <Box display="flex" alignItems="center" mb={2}>
                <Typography variant="h6" sx={{ flexGrow: 1 }}>
                  Context Information
                </Typography>
                <IconButton
                  size="small"
                  onClick={() => toggleSection('context')}
                >
                  {expandedSections.has('context') ? <CollapseIcon /> : <ExpandIcon />}
                </IconButton>
              </Box>
              
              {expandedSections.has('context') && (
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {JSON.stringify(approval.context_data, null, 2)}
                  </pre>
                </Paper>
              )}
            </Box>

            {/* Attachments */}
            <Box>
              <Typography variant="h6" gutterBottom>
                Attachments ({approval.attachments.length})
              </Typography>
              
              {approval.attachments.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No attachments
                </Typography>
              ) : (
                <List>
                  {approval.attachments.map((attachment, index) => (
                    <ListItem
                      key={index}
                      secondaryAction={
                        <Box>
                          <IconButton edge="end" aria-label="view">
                            <ViewIcon />
                          </IconButton>
                          <IconButton edge="end" aria-label="download">
                            <DownloadIcon />
                          </IconButton>
                        </Box>
                      }
                    >
                      <ListItemAvatar>
                        <Avatar>
                          <AttachmentIcon />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={attachment.name || `Attachment ${index + 1}`}
                        secondary={attachment.size || 'Unknown size'}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </Box>
          </CardContent>
        </TabPanel>

        {/* History Tab */}
        <TabPanel value={tabValue} index={2}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Decision History
            </Typography>
            
            {approval.approval_decisions.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No decisions yet
              </Typography>
            ) : (
              <List>
                {approval.approval_decisions.map((decision, index) => (
                  <React.Fragment key={index}>
                    <ListItem alignItems="flex-start">
                      <ListItemAvatar>
                        <Avatar sx={{
                          bgcolor: decision.decision === 'approved' ? 'success.main' : 'error.main'
                        }}>
                          {decision.decision === 'approved' ? <ApproveIcon /> : <RejectIcon />}
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={
                          <Box>
                            <Typography variant="subtitle1">
                              {decision.approver_name} {decision.decision}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {format(new Date(decision.decided_at), 'PPp')}
                            </Typography>
                          </Box>
                        }
                        secondary={
                          decision.comments && (
                            <Box mt={1}>
                              <Typography variant="body2">
                                {decision.comments}
                              </Typography>
                            </Box>
                          )
                        }
                      />
                    </ListItem>
                    {index < approval.approval_decisions.length - 1 && <Divider variant="inset" component="li" />}
                  </React.Fragment>
                ))}
              </List>
            )}

            {approval.escalation_history.length > 0 && (
              <>
                <Divider sx={{ my: 3 }} />
                <Typography variant="h6" gutterBottom>
                  Escalation History
                </Typography>
                <List>
                  {approval.escalation_history.map((escalation, index) => (
                    <ListItem key={index}>
                      <ListItemAvatar>
                        <Avatar sx={{ bgcolor: 'warning.main' }}>
                          <WarningIcon />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={`Escalated to ${escalation.escalated_to}`}
                        secondary={`Level ${escalation.level} - ${escalation.reason}`}
                      />
                    </ListItem>
                  ))}
                </List>
              </>
            )}
          </CardContent>
        </TabPanel>

        {/* Voting Status Tab */}
        {approval.approval_config.approval_type === 'voting' && (
          <TabPanel value={tabValue} index={3}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Voting Progress
              </Typography>
              
              <Box mb={3}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">
                    Votes: {approval.approval_decisions.length} / {approval.approval_config.approvers.length}
                  </Typography>
                  <Typography variant="body2">
                    {Math.round((approval.approval_decisions.length / approval.approval_config.approvers.length) * 100)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={(approval.approval_decisions.length / approval.approval_config.approvers.length) * 100}
                />
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Paper sx={{ p: 2, bgcolor: 'success.light' }}>
                    <Typography variant="h4" align="center">
                      {approval.approval_decisions.filter(d => d.decision === 'approved').length}
                    </Typography>
                    <Typography variant="body2" align="center">
                      Approved
                    </Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6}>
                  <Paper sx={{ p: 2, bgcolor: 'error.light' }}>
                    <Typography variant="h4" align="center">
                      {approval.approval_decisions.filter(d => d.decision === 'rejected').length}
                    </Typography>
                    <Typography variant="body2" align="center">
                      Rejected
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>

              {approval.approval_config.voting_strategy && (
                <Alert severity="info" sx={{ mt: 3 }}>
                  <AlertTitle>Voting Strategy: {approval.approval_config.voting_strategy}</AlertTitle>
                  {approval.approval_config.voting_strategy === 'majority' && 
                    'Requires more than 50% approval votes to pass.'}
                  {approval.approval_config.voting_strategy === 'unanimous' && 
                    'Requires all approvers to approve.'}
                  {approval.approval_config.voting_strategy === 'custom_threshold' && 
                    `Requires ${(approval.approval_config.approval_threshold || 0.5) * 100}% approval votes to pass.`}
                </Alert>
              )}
            </CardContent>
          </TabPanel>
        )}
      </Card>

      {/* Delegate Dialog */}
      <Dialog
        open={showDelegateDialog}
        onClose={() => setShowDelegateDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Delegate Approval</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" paragraph>
            Delegate this approval to another user. You will be notified of the final decision.
          </Typography>
          <TextField
            autoFocus
            margin="dense"
            label="Delegate Email"
            type="email"
            fullWidth
            value={delegateEmail}
            onChange={(e) => setDelegateEmail(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Reason for Delegation"
            multiline
            rows={3}
            fullWidth
            value={delegateReason}
            onChange={(e) => setDelegateReason(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDelegateDialog(false)}>
            Cancel
          </Button>
          <Button onClick={handleDelegate} variant="contained" disabled={submitting}>
            {submitting ? 'Delegating...' : 'Delegate'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ApprovalReviewInterface;