import React, { useState, useCallback } from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  CardActions,
  Avatar,
  Typography,
  Button,
  IconButton,
  Chip,
  Box,
  Menu,
  MenuItem,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  AvatarGroup,
  LinearProgress,
  Alert,
  Stack,
  Tooltip,
  Badge,
} from '@mui/material';
import {
  MoreVert,
  ThumbUp,
  ThumbDown,
  Comment,
  Schedule,
  Priority,
  Warning,
  AccessTime,
  CheckCircle,
  Cancel,
  Escalate,
  Assignment,
  AttachFile,
  Visibility,
  Edit,
  Delete,
  Share,
  History,
  Person,
  Group,
  Business,
} from '@mui/icons-material';
import { format, formatDistanceToNow, isAfter } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import {
  useRespondToApprovalRequestMutation,
  useCancelApprovalRequestMutation,
} from '../../store/api/workflowApi';
import { ApprovalRequest, ApprovalPriority, ApprovalStatus } from '../../types/workflow';

interface ApprovalRequestCardProps {
  approval: ApprovalRequest;
  showActions?: boolean;
  onUpdate?: () => void;
  variant?: 'default' | 'compact' | 'detailed';
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

const ApprovalRequestCard: React.FC<ApprovalRequestCardProps> = ({
  approval,
  showActions = true,
  onUpdate,
  variant = 'default',
}) => {
  const navigate = useNavigate();
  const [contextMenu, setContextMenu] = useState<null | HTMLElement>(null);
  const [showResponseDialog, setShowResponseDialog] = useState(false);
  const [responseType, setResponseType] = useState<'approve' | 'reject' | 'request_changes'>('approve');
  const [responseComment, setResponseComment] = useState('');

  const [respondToApproval, { isLoading: respondLoading }] = useRespondToApprovalRequestMutation();
  const [cancelApproval, { isLoading: cancelLoading }] = useCancelApprovalRequestMutation();

  const handleContextMenuClick = useCallback((event: React.MouseEvent<HTMLElement>) => {
    setContextMenu(event.currentTarget);
  }, []);

  const handleContextMenuClose = useCallback(() => {
    setContextMenu(null);
  }, []);

  const handleViewDetails = useCallback(() => {
    navigate(`/approvals/${approval.id}`);
    handleContextMenuClose();
  }, [approval.id, navigate]);

  const handleQuickResponse = useCallback((response: 'approve' | 'reject' | 'request_changes') => {
    setResponseType(response);
    setShowResponseDialog(true);
    handleContextMenuClose();
  }, []);

  const handleSubmitResponse = useCallback(async () => {
    try {
      await respondToApproval({
        id: approval.id,
        response: responseType,
        comment: responseComment,
      }).unwrap();
      setShowResponseDialog(false);
      setResponseComment('');
      onUpdate?.();
    } catch (error) {
      console.error('Failed to respond to approval:', error);
    }
  }, [approval.id, responseType, responseComment, respondToApproval, onUpdate]);

  const handleCancelRequest = useCallback(async () => {
    try {
      await cancelApproval(approval.id).unwrap();
      onUpdate?.();
    } catch (error) {
      console.error('Failed to cancel approval:', error);
    }
    handleContextMenuClose();
  }, [approval.id, cancelApproval, onUpdate]);

  const handleEscalate = useCallback(() => {
    navigate(`/approvals/${approval.id}/escalate`);
    handleContextMenuClose();
  }, [approval.id, navigate]);

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

  const getStatusIcon = (status: ApprovalStatus) => {
    switch (status) {
      case 'approved':
        return <CheckCircle color="success" />;
      case 'rejected':
        return <Cancel color="error" />;
      case 'cancelled':
        return <Cancel color="disabled" />;
      case 'escalated':
        return <Escalate color="primary" />;
      case 'in_review':
        return <Visibility color="info" />;
      default:
        return <Schedule color="warning" />;
    }
  };

  const isOverdue = approval.due_date && isAfter(new Date(), new Date(approval.due_date));
  const canRespond = approval.status === 'pending' || approval.status === 'in_review';
  const isRequester = true; // TODO: Check if current user is the requester

  const renderCompactCard = () => (
    <Card
      sx={{
        mb: 1,
        cursor: 'pointer',
        '&:hover': { bgcolor: 'action.hover' },
        border: approval.priority === 'urgent' ? '2px solid #f44336' : undefined,
      }}
      onClick={() => handleViewDetails()}
    >
      <CardContent sx={{ py: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1 }}>
            <Avatar src={approval.requester.avatar_url} sx={{ width: 32, height: 32 }}>
              {approval.requester.name.charAt(0)}
            </Avatar>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle2" noWrap>
                {approval.title}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {approval.requester.name} • {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
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
            {getPriorityIcon(approval.priority)}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );

  const renderDetailedCard = () => (
    <Card
      sx={{
        mb: 2,
        border: approval.priority === 'urgent' ? '2px solid #f44336' : undefined,
      }}
    >
      <CardHeader
        avatar={
          <Avatar src={approval.requester.avatar_url}>
            {approval.requester.name.charAt(0)}
          </Avatar>
        }
        title={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h6">{approval.title}</Typography>
            {isOverdue && (
              <Badge badgeContent="OVERDUE" color="error">
                <Box />
              </Badge>
            )}
          </Box>
        }
        subheader={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Requested by {approval.requester.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
            </Typography>
            {approval.due_date && (
              <Typography
                variant="body2"
                color={isOverdue ? 'error' : 'text.secondary'}
                sx={{ fontWeight: isOverdue ? 'bold' : 'normal' }}
              >
                Due {format(new Date(approval.due_date), 'MMM d, yyyy')}
              </Typography>
            )}
          </Box>
        }
        action={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Stack direction="row" spacing={1}>
              <Chip
                label={approval.priority}
                size="small"
                color={priorityColors[approval.priority]}
                variant="outlined"
                icon={getPriorityIcon(approval.priority)}
              />
              <Chip
                label={approval.status}
                size="small"
                color={statusColors[approval.status]}
                variant="filled"
                icon={getStatusIcon(approval.status)}
              />
            </Stack>
            <IconButton onClick={handleContextMenuClick}>
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

      {/* Approvers */}
      <CardContent sx={{ pt: 0 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <Typography variant="subtitle2">Approvers:</Typography>
          <AvatarGroup max={4} sx={{ '& .MuiAvatar-root': { width: 32, height: 32 } }}>
            {approval.approvers.map((approver) => (
              <Tooltip key={approver.user_id} title={`${approver.user.name} - ${approver.status}`}>
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
              </Tooltip>
            ))}
          </AvatarGroup>
        </Box>

        {/* Context Information */}
        {approval.context.asset && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Asset:
            </Typography>
            <Chip
              label={approval.context.asset.name}
              size="small"
              variant="outlined"
              onClick={() => navigate(`/assets/${approval.context.asset_id}`)}
              clickable
            />
          </Box>
        )}

        {approval.context.project && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Project:
            </Typography>
            <Chip
              label={approval.context.project.name}
              size="small"
              variant="outlined"
              onClick={() => navigate(`/projects/${approval.context.project_id}`)}
              clickable
            />
          </Box>
        )}

        {/* Recent Responses */}
        {approval.responses.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Recent Activity:
            </Typography>
            {approval.responses.slice(-2).map((response) => (
              <Box key={response.id} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Avatar src={response.user.avatar_url} sx={{ width: 24, height: 24 }}>
                  {response.user.name.charAt(0)}
                </Avatar>
                <Typography variant="body2">
                  {response.user.name} {response.response_type}d
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {formatDistanceToNow(new Date(response.created_at), { addSuffix: true })}
                </Typography>
              </Box>
            ))}
          </Box>
        )}
      </CardContent>

      {/* Actions */}
      {showActions && canRespond && (
        <CardActions sx={{ justifyContent: 'flex-end', gap: 1 }}>
          <Button
            variant="outlined"
            color="error"
            startIcon={<ThumbDown />}
            onClick={() => handleQuickResponse('reject')}
            disabled={respondLoading}
          >
            Reject
          </Button>
          <Button
            variant="outlined"
            color="warning"
            startIcon={<Comment />}
            onClick={() => handleQuickResponse('request_changes')}
            disabled={respondLoading}
          >
            Request Changes
          </Button>
          <Button
            variant="contained"
            color="success"
            startIcon={<ThumbUp />}
            onClick={() => handleQuickResponse('approve')}
            disabled={respondLoading}
          >
            Approve
          </Button>
        </CardActions>
      )}

      {/* Loading indicator */}
      {(respondLoading || cancelLoading) && (
        <LinearProgress />
      )}
    </Card>
  );

  const renderDefaultCard = () => (
    <Card
      sx={{
        mb: 2,
        cursor: 'pointer',
        '&:hover': { bgcolor: 'action.hover' },
        border: approval.priority === 'urgent' ? '2px solid #f44336' : undefined,
      }}
      onClick={() => handleViewDetails()}
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
              {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
            </Typography>
            {approval.due_date && (
              <Typography
                variant="body2"
                color={isOverdue ? 'error' : 'text.secondary'}
              >
                Due {format(new Date(approval.due_date), 'MMM d, yyyy')}
              </Typography>
            )}
          </Box>
        }
        action={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {getPriorityIcon(approval.priority)}
            <IconButton onClick={handleContextMenuClick}>
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

  const renderCard = () => {
    switch (variant) {
      case 'compact':
        return renderCompactCard();
      case 'detailed':
        return renderDetailedCard();
      default:
        return renderDefaultCard();
    }
  };

  return (
    <>
      {renderCard()}

      {/* Context Menu */}
      <Menu
        anchorEl={contextMenu}
        open={Boolean(contextMenu)}
        onClose={handleContextMenuClose}
      >
        <MenuItem onClick={handleViewDetails}>
          <Assignment sx={{ mr: 1 }} />
          View Details
        </MenuItem>
        <Divider />
        {canRespond && (
          <>
            <MenuItem onClick={() => handleQuickResponse('approve')} sx={{ color: 'success.main' }}>
              <ThumbUp sx={{ mr: 1 }} />
              Approve
            </MenuItem>
            <MenuItem onClick={() => handleQuickResponse('reject')} sx={{ color: 'error.main' }}>
              <ThumbDown sx={{ mr: 1 }} />
              Reject
            </MenuItem>
            <MenuItem onClick={() => handleQuickResponse('request_changes')} sx={{ color: 'warning.main' }}>
              <Comment sx={{ mr: 1 }} />
              Request Changes
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleEscalate}>
              <Escalate sx={{ mr: 1 }} />
              Escalate
            </MenuItem>
          </>
        )}
        {isRequester && approval.status === 'pending' && (
          <>
            <Divider />
            <MenuItem onClick={handleCancelRequest} sx={{ color: 'error.main' }}>
              <Cancel sx={{ mr: 1 }} />
              Cancel Request
            </MenuItem>
          </>
        )}
        <Divider />
        <MenuItem onClick={() => navigate(`/approvals/${approval.id}/history`)}>
          <History sx={{ mr: 1 }} />
          View History
        </MenuItem>
        <MenuItem onClick={() => {/* TODO: Implement sharing */}}>
          <Share sx={{ mr: 1 }} />
          Share
        </MenuItem>
      </Menu>

      {/* Response Dialog */}
      <Dialog
        open={showResponseDialog}
        onClose={() => setShowResponseDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {responseType === 'approve' ? 'Approve Request' : 
           responseType === 'reject' ? 'Reject Request' : 
           'Request Changes'}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {approval.title}
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Comment (optional)"
            value={responseComment}
            onChange={(e) => setResponseComment(e.target.value)}
            placeholder={`Add a comment for your ${responseType === 'approve' ? 'approval' : responseType === 'reject' ? 'rejection' : 'change request'}...`}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowResponseDialog(false)}>Cancel</Button>
          <Button
            onClick={handleSubmitResponse}
            variant="contained"
            color={responseType === 'approve' ? 'success' : responseType === 'reject' ? 'error' : 'warning'}
            disabled={respondLoading}
          >
            {responseType === 'approve' ? 'Approve' : 
             responseType === 'reject' ? 'Reject' : 
             'Request Changes'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default ApprovalRequestCard;