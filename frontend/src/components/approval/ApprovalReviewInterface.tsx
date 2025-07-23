import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardActions,
  Avatar,
  Chip,
  Divider,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Menu,
  MenuItem,
  Alert,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  ListItemSecondaryAction,
  Badge,
  Tooltip,
  Stack,
  Grid,
  Tab,
  Tabs,
  Container,
  Breadcrumbs,
  Link,
  Skeleton,
} from '@mui/material';
import {
  ThumbUp,
  ThumbDown,
  Comment,
  Edit,
  Share,
  History,
  Escalate,
  Schedule,
  Warning,
  CheckCircle,
  Cancel,
  Person,
  Assignment,
  AttachFile,
  ExpandMore,
  MoreVert,
  Add,
  Send,
  Close,
  Home,
  Visibility,
  VisibilityOff,
  Download,
  Print,
  Email,
  AccessTime,
  PriorityHigh,
  Group,
  Business,
  Movie,
  AudioFile,
  Image,
  Description,
  Timeline,
  Folder,
} from '@mui/icons-material';
import { format, formatDistanceToNow } from 'date-fns';
import { useParams, useNavigate } from 'react-router-dom';
import {
  useGetApprovalRequestQuery,
  useRespondToApprovalRequestMutation,
  useEscalateApprovalRequestMutation,
  useCancelApprovalRequestMutation,
} from '../../store/api/workflowApi';
import { ApprovalRequest, ApprovalResponse, RespondToApprovalRequest } from '../../types/workflow';

interface ApprovalReviewInterfaceProps {
  approvalId?: string;
  onClose?: () => void;
  embedded?: boolean;
}

const ApprovalReviewInterface: React.FC<ApprovalReviewInterfaceProps> = ({
  approvalId: propApprovalId,
  onClose,
  embedded = false,
}) => {
  const { approvalId: paramApprovalId } = useParams<{ approvalId: string }>();
  const navigate = useNavigate();
  const approvalId = propApprovalId || paramApprovalId;

  const [activeTab, setActiveTab] = useState(0);
  const [showResponseDialog, setShowResponseDialog] = useState(false);
  const [responseType, setResponseType] = useState<'approve' | 'reject' | 'request_changes'>('approve');
  const [responseComment, setResponseComment] = useState('');
  const [responseAttachments, setResponseAttachments] = useState<string[]>([]);
  const [showEscalateDialog, setShowEscalateDialog] = useState(false);
  const [escalateComment, setEscalateComment] = useState('');
  const [escalateToUsers, setEscalateToUsers] = useState<string[]>([]);
  const [showShareDialog, setShowShareDialog] = useState(false);
  const [contextMenu, setContextMenu] = useState<null | HTMLElement>(null);

  // API hooks
  const { data: approval, isLoading, error, refetch } = useGetApprovalRequestQuery(approvalId!, {
    skip: !approvalId,
  });

  const [respondToApproval, { isLoading: respondLoading }] = useRespondToApprovalRequestMutation();
  const [escalateApproval, { isLoading: escalateLoading }] = useEscalateApprovalRequestMutation();
  const [cancelApproval, { isLoading: cancelLoading }] = useCancelApprovalRequestMutation();

  const handleTabChange = useCallback((event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  }, []);

  const handleResponseClick = useCallback((response: 'approve' | 'reject' | 'request_changes') => {
    setResponseType(response);
    setShowResponseDialog(true);
  }, []);

  const handleSubmitResponse = useCallback(async () => {
    if (!approval) return;

    try {
      const responseData: RespondToApprovalRequest = {
        response: responseType,
        comment: responseComment,
        attachments: responseAttachments,
      };

      await respondToApproval({
        id: approval.id,
        ...responseData,
      }).unwrap();

      setShowResponseDialog(false);
      setResponseComment('');
      setResponseAttachments([]);
      refetch();
    } catch (error) {
      console.error('Failed to submit response:', error);
    }
  }, [approval, responseType, responseComment, responseAttachments, respondToApproval, refetch]);

  const handleEscalate = useCallback(async () => {
    if (!approval) return;

    try {
      await escalateApproval({
        id: approval.id,
        escalate_to: escalateToUsers,
        comment: escalateComment,
      }).unwrap();

      setShowEscalateDialog(false);
      setEscalateComment('');
      setEscalateToUsers([]);
      refetch();
    } catch (error) {
      console.error('Failed to escalate approval:', error);
    }
  }, [approval, escalateToUsers, escalateComment, escalateApproval, refetch]);

  const handleCancel = useCallback(async () => {
    if (!approval) return;

    try {
      await cancelApproval(approval.id).unwrap();
      refetch();
    } catch (error) {
      console.error('Failed to cancel approval:', error);
    }
  }, [approval, cancelApproval, refetch]);

  const handleContextMenuClick = useCallback((event: React.MouseEvent<HTMLElement>) => {
    setContextMenu(event.currentTarget);
  }, []);

  const handleContextMenuClose = useCallback(() => {
    setContextMenu(null);
  }, []);

  const canRespond = useMemo(() => {
    if (!approval) return false;
    return approval.status === 'pending' || approval.status === 'in_review';
  }, [approval]);

  const isRequester = useMemo(() => {
    // TODO: Check if current user is the requester
    return true;
  }, []);

  const isApprover = useMemo(() => {
    // TODO: Check if current user is one of the approvers
    return true;
  }, []);

  const getAssetTypeIcon = (type: string) => {
    switch (type) {
      case 'video': return <Movie />;
      case 'audio': return <AudioFile />;
      case 'image': return <Image />;
      case 'document': return <Description />;
      default: return <Assignment />;
    }
  };

  const getContextIcon = (approval: ApprovalRequest) => {
    if (approval.context.asset) return getAssetTypeIcon(approval.context.asset.asset_type);
    if (approval.context.project) return <Folder />;
    if (approval.context.timeline) return <Timeline />;
    return <Assignment />;
  };

  const renderApprovalHeader = () => {
    if (!approval) return null;

    const isOverdue = approval.due_date && new Date(approval.due_date) < new Date();

    return (
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
          <Avatar src={approval.requester.avatar_url} sx={{ width: 56, height: 56 }}>
            {approval.requester.name.charAt(0)}
          </Avatar>
          
          <Box sx={{ flex: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              <Typography variant="h5" component="h1">
                {approval.title}
              </Typography>
              {isOverdue && (
                <Badge badgeContent="OVERDUE" color="error">
                  <Box />
                </Badge>
              )}
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <Chip
                label={approval.priority}
                size="small"
                color={approval.priority === 'urgent' ? 'error' : 
                       approval.priority === 'high' ? 'warning' : 
                       approval.priority === 'medium' ? 'info' : 'success'}
                variant="outlined"
              />
              <Chip
                label={approval.status}
                size="small"
                color={approval.status === 'approved' ? 'success' : 
                       approval.status === 'rejected' ? 'error' : 
                       approval.status === 'cancelled' ? 'secondary' : 'warning'}
                variant="filled"
              />
              <Chip
                label={approval.type}
                size="small"
                variant="outlined"
              />
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Person fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  Requested by {approval.requester.name}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <AccessTime fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
                </Typography>
              </Box>
              {approval.due_date && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Schedule fontSize="small" />
                  <Typography 
                    variant="body2" 
                    color={isOverdue ? 'error' : 'text.secondary'}
                    sx={{ fontWeight: isOverdue ? 'bold' : 'normal' }}
                  >
                    Due {format(new Date(approval.due_date), 'MMM d, yyyy')}
                  </Typography>
                </Box>
              )}
            </Box>
            
            {approval.description && (
              <Typography variant="body1" sx={{ mb: 2 }}>
                {approval.description}
              </Typography>
            )}
          </Box>
          
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton onClick={handleContextMenuClick}>
              <MoreVert />
            </IconButton>
          </Box>
        </Box>
      </Paper>
    );
  };

  const renderContextInfo = () => {
    if (!approval) return null;

    return (
      <Card sx={{ mb: 3 }}>
        <CardHeader
          avatar={getContextIcon(approval)}
          title="Context Information"
          subheader="Related items and changes"
        />
        <CardContent>
          <Stack spacing={2}>
            {approval.context.asset && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <getAssetTypeIcon />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2">Asset</Typography>
                  <Typography 
                    variant="body2" 
                    color="primary" 
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/assets/${approval.context.asset_id}`)}
                  >
                    {approval.context.asset.name}
                  </Typography>
                </Box>
              </Box>
            )}
            
            {approval.context.project && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Folder />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2">Project</Typography>
                  <Typography 
                    variant="body2" 
                    color="primary" 
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/projects/${approval.context.project_id}`)}
                  >
                    {approval.context.project.name}
                  </Typography>
                </Box>
              </Box>
            )}
            
            {approval.context.timeline && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Timeline />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2">Timeline</Typography>
                  <Typography 
                    variant="body2" 
                    color="primary" 
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/timelines/${approval.context.timeline_id}`)}
                  >
                    {approval.context.timeline.name}
                  </Typography>
                </Box>
              </Box>
            )}
            
            {approval.context.changes && approval.context.changes.length > 0 && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>Changes</Typography>
                <List dense>
                  {approval.context.changes.map((change, index) => (
                    <ListItem key={index}>
                      <ListItemText
                        primary={change.field}
                        secondary={
                          <Box>
                            <Typography variant="body2" color="text.secondary">
                              {change.change_type === 'create' ? 'Created' : 
                               change.change_type === 'update' ? 'Updated' : 'Deleted'}
                            </Typography>
                            {change.old_value && (
                              <Typography variant="body2" color="text.secondary">
                                From: {JSON.stringify(change.old_value)}
                              </Typography>
                            )}
                            {change.new_value && (
                              <Typography variant="body2" color="text.secondary">
                                To: {JSON.stringify(change.new_value)}
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
          </Stack>
        </CardContent>
      </Card>
    );
  };

  const renderApprovers = () => {
    if (!approval) return null;

    return (
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title="Approvers"
          subheader={`${approval.approvers.length} approver${approval.approvers.length > 1 ? 's' : ''}`}
        />
        <CardContent>
          <List>
            {approval.approvers.map((approver) => (
              <ListItem key={approver.user_id}>
                <ListItemAvatar>
                  <Avatar
                    src={approver.user.avatar_url}
                    sx={{
                      border: approver.status === 'approved' ? '2px solid #4caf50' : 
                             approver.status === 'rejected' ? '2px solid #f44336' : 
                             '2px solid #e0e0e0',
                    }}
                  >
                    {approver.user.name.charAt(0)}
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={approver.user.name}
                  secondary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={approver.status}
                        size="small"
                        color={approver.status === 'approved' ? 'success' : 
                               approver.status === 'rejected' ? 'error' : 'default'}
                        variant="outlined"
                      />
                      {approver.is_required && (
                        <Chip label="Required" size="small" color="warning" variant="outlined" />
                      )}
                      {approver.responded_at && (
                        <Typography variant="caption" color="text.secondary">
                          {formatDistanceToNow(new Date(approver.responded_at), { addSuffix: true })}
                        </Typography>
                      )}
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>
    );
  };

  const renderResponses = () => {
    if (!approval || approval.responses.length === 0) return null;

    return (
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title="Responses & Comments"
          subheader={`${approval.responses.length} response${approval.responses.length > 1 ? 's' : ''}`}
        />
        <CardContent>
          <List>
            {approval.responses.map((response) => (
              <ListItem key={response.id} alignItems="flex-start">
                <ListItemAvatar>
                  <Avatar src={response.user.avatar_url}>
                    {response.user.name.charAt(0)}
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle2">
                        {response.user.name}
                      </Typography>
                      <Chip
                        label={response.response}
                        size="small"
                        color={response.response === 'approve' ? 'success' : 
                               response.response === 'reject' ? 'error' : 'warning'}
                        variant="outlined"
                      />
                      <Typography variant="caption" color="text.secondary">
                        {formatDistanceToNow(new Date(response.created_at), { addSuffix: true })}
                      </Typography>
                    </Box>
                  }
                  secondary={
                    response.comment && (
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        {response.comment}
                      </Typography>
                    )
                  }
                />
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>
    );
  };

  const renderActions = () => {
    if (!approval || !canRespond) return null;

    return (
      <Paper sx={{ p: 3, position: 'sticky', bottom: 0, zIndex: 100 }}>
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
          <Button
            variant="outlined"
            color="error"
            startIcon={<ThumbDown />}
            onClick={() => handleResponseClick('reject')}
            disabled={respondLoading}
          >
            Reject
          </Button>
          <Button
            variant="outlined"
            color="warning"
            startIcon={<Comment />}
            onClick={() => handleResponseClick('request_changes')}
            disabled={respondLoading}
          >
            Request Changes
          </Button>
          <Button
            variant="contained"
            color="success"
            startIcon={<ThumbUp />}
            onClick={() => handleResponseClick('approve')}
            disabled={respondLoading}
          >
            Approve
          </Button>
        </Box>
      </Paper>
    );
  };

  if (!approvalId) {
    return (
      <Alert severity="error">
        No approval ID provided.
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Stack spacing={2}>
          <Skeleton variant="rectangular" height={200} />
          <Skeleton variant="rectangular" height={300} />
          <Skeleton variant="rectangular" height={200} />
        </Stack>
      </Container>
    );
  }

  if (error || !approval) {
    return (
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Alert severity="error">
          Failed to load approval request. Please try again.
        </Alert>
      </Container>
    );
  }

  const content = (
    <Box sx={{ pb: 10 }}>
      {renderApprovalHeader()}
      
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={handleTabChange}>
          <Tab label="Overview" />
          <Tab label="Context" />
          <Tab label="Approvers" />
          <Tab label="Activity" />
        </Tabs>
      </Box>

      {activeTab === 0 && (
        <Box>
          {renderContextInfo()}
          {renderApprovers()}
        </Box>
      )}

      {activeTab === 1 && renderContextInfo()}
      {activeTab === 2 && renderApprovers()}
      {activeTab === 3 && renderResponses()}

      {renderActions()}
    </Box>
  );

  if (embedded) {
    return content;
  }

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 3 }}>
        <Link
          component="button"
          variant="body2"
          onClick={() => navigate('/')}
          sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
        >
          <Home fontSize="small" />
          Home
        </Link>
        <Link
          component="button"
          variant="body2"
          onClick={() => navigate('/approvals')}
        >
          Approvals
        </Link>
        <Typography variant="body2" color="text.primary">
          {approval.title}
        </Typography>
      </Breadcrumbs>

      {content}

      {/* Context Menu */}
      <Menu
        anchorEl={contextMenu}
        open={Boolean(contextMenu)}
        onClose={handleContextMenuClose}
      >
        <MenuItem onClick={() => setShowShareDialog(true)}>
          <Share sx={{ mr: 1 }} />
          Share
        </MenuItem>
        <MenuItem onClick={() => setShowEscalateDialog(true)}>
          <Escalate sx={{ mr: 1 }} />
          Escalate
        </MenuItem>
        <MenuItem onClick={() => window.print()}>
          <Print sx={{ mr: 1 }} />
          Print
        </MenuItem>
        <Divider />
        {isRequester && approval.status === 'pending' && (
          <MenuItem onClick={handleCancel} sx={{ color: 'error.main' }}>
            <Cancel sx={{ mr: 1 }} />
            Cancel Request
          </MenuItem>
        )}
      </Menu>

      {/* Response Dialog */}
      <Dialog
        open={showResponseDialog}
        onClose={() => setShowResponseDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {responseType === 'approve' ? 'Approve Request' : 
           responseType === 'reject' ? 'Reject Request' : 
           'Request Changes'}
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Comment"
            value={responseComment}
            onChange={(e) => setResponseComment(e.target.value)}
            placeholder={`Add a comment for your ${responseType}...`}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowResponseDialog(false)}>Cancel</Button>
          <Button
            onClick={handleSubmitResponse}
            variant="contained"
            color={responseType === 'approve' ? 'success' : 
                   responseType === 'reject' ? 'error' : 'warning'}
            disabled={respondLoading}
          >
            {responseType === 'approve' ? 'Approve' : 
             responseType === 'reject' ? 'Reject' : 
             'Request Changes'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Loading overlay */}
      {(respondLoading || escalateLoading || cancelLoading) && (
        <LinearProgress sx={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1301 }} />
      )}
    </Container>
  );
};

export default ApprovalReviewInterface;