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
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Checkbox,
  FormControlLabel,
  Switch,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Menu,
  Divider,
  Alert,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  ListItemSecondaryAction,
  ListSubheader,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stack,
  Grid,
  Tooltip,
  Badge,
  AvatarGroup,
  Container,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  ExpandMore,
  Person,
  Group,
  Business,
  Settings,
  Schedule,
  AccountTree,
  Route,
  Timeline,
  SwapVert,
  ArrowForward,
  ArrowDownward,
  PlayArrow,
  Stop,
  Pause,
  MoreVert,
  Copy,
  Visibility,
  VisibilityOff,
  Priority,
  Assignment,
  CheckCircle,
  Cancel,
  Warning,
  Info,
  Save,
  Refresh,
} from '@mui/icons-material';
import { DragDropContext, Droppable, Draggable, DropResult } from 'react-beautiful-dnd';
import {
  WorkflowApprover,
  WorkflowStep,
  WorkflowStepType,
  EscalationRule,
  ApprovalPriority,
  CreateWorkflowTemplateRequest,
  UpdateWorkflowTemplateRequest,
} from '../../types/workflow';
import {
  useGetWorkflowTemplatesQuery,
  useCreateWorkflowTemplateMutation,
  useUpdateWorkflowTemplateMutation,
  useDeleteWorkflowTemplateMutation,
} from '../../store/api/workflowApi';

interface ApprovalRoutingProps {
  workflowId?: string;
  onSave?: (workflow: any) => void;
  embedded?: boolean;
}

const ApprovalRouting: React.FC<ApprovalRoutingProps> = ({
  workflowId,
  onSave,
  embedded = false,
}) => {
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>([]);
  const [selectedStep, setSelectedStep] = useState<WorkflowStep | null>(null);
  const [showStepDialog, setShowStepDialog] = useState(false);
  const [showApproverDialog, setShowApproverDialog] = useState(false);
  const [showEscalationDialog, setShowEscalationDialog] = useState(false);
  const [editingStep, setEditingStep] = useState<WorkflowStep | null>(null);
  const [contextMenu, setContextMenu] = useState<{
    mouseX: number;
    mouseY: number;
    step: WorkflowStep;
  } | null>(null);

  // Step form state
  const [stepForm, setStepForm] = useState({
    name: '',
    type: 'approval' as WorkflowStepType,
    approval_type: 'single' as 'single' | 'multiple' | 'sequential' | 'parallel',
    approvers: [] as WorkflowApprover[],
    min_approvals: 1,
    allow_self_approval: false,
    timeout_minutes: 1440, // 24 hours
    escalation_rules: [] as EscalationRule[],
    is_required: true,
  });

  // Approver form state
  const [approverForm, setApproverForm] = useState({
    type: 'user' as 'user' | 'group' | 'role',
    id: '',
    name: '',
    is_required: true,
    order: 0,
  });

  // Escalation form state
  const [escalationForm, setEscalationForm] = useState({
    after_minutes: 480, // 8 hours
    escalate_to: [] as WorkflowApprover[],
    notification_template: '',
    auto_approve: false,
  });

  // API hooks
  const { data: workflowTemplates, isLoading, refetch } = useGetWorkflowTemplatesQuery({});
  const [createWorkflowTemplate, { isLoading: createLoading }] = useCreateWorkflowTemplateMutation();
  const [updateWorkflowTemplate, { isLoading: updateLoading }] = useUpdateWorkflowTemplateMutation();
  const [deleteWorkflowTemplate, { isLoading: deleteLoading }] = useDeleteWorkflowTemplateMutation();

  const handleAddStep = useCallback(() => {
    setEditingStep(null);
    setStepForm({
      name: '',
      type: 'approval',
      approval_type: 'single',
      approvers: [],
      min_approvals: 1,
      allow_self_approval: false,
      timeout_minutes: 1440,
      escalation_rules: [],
      is_required: true,
    });
    setShowStepDialog(true);
  }, []);

  const handleEditStep = useCallback((step: WorkflowStep) => {
    setEditingStep(step);
    setStepForm({
      name: step.name,
      type: step.type,
      approval_type: step.config.approval_type || 'single',
      approvers: step.config.approvers || [],
      min_approvals: step.config.min_approvals || 1,
      allow_self_approval: step.config.allow_self_approval || false,
      timeout_minutes: step.timeout_minutes || 1440,
      escalation_rules: step.config.escalation_rules || [],
      is_required: step.is_required,
    });
    setShowStepDialog(true);
  }, []);

  const handleSaveStep = useCallback(() => {
    const newStep: WorkflowStep = {
      id: editingStep?.id || `step-${Date.now()}`,
      name: stepForm.name,
      type: stepForm.type,
      order: editingStep?.order || workflowSteps.length,
      config: {
        approval_type: stepForm.approval_type,
        approvers: stepForm.approvers,
        min_approvals: stepForm.min_approvals,
        allow_self_approval: stepForm.allow_self_approval,
        escalation_rules: stepForm.escalation_rules,
      },
      timeout_minutes: stepForm.timeout_minutes,
      is_required: stepForm.is_required,
      retry_count: 0,
      depends_on: editingStep?.depends_on || [],
    };

    if (editingStep) {
      setWorkflowSteps(prev => prev.map(step => 
        step.id === editingStep.id ? newStep : step
      ));
    } else {
      setWorkflowSteps(prev => [...prev, newStep]);
    }

    setShowStepDialog(false);
    setEditingStep(null);
  }, [stepForm, editingStep, workflowSteps]);

  const handleDeleteStep = useCallback((stepId: string) => {
    setWorkflowSteps(prev => prev.filter(step => step.id !== stepId));
  }, []);

  const handleDragEnd = useCallback((result: DropResult) => {
    if (!result.destination) return;

    const items = Array.from(workflowSteps);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);

    // Update order
    const updatedItems = items.map((item, index) => ({
      ...item,
      order: index,
    }));

    setWorkflowSteps(updatedItems);
  }, [workflowSteps]);

  const handleAddApprover = useCallback(() => {
    const newApprover: WorkflowApprover = {
      type: approverForm.type,
      id: approverForm.id,
      name: approverForm.name,
      is_required: approverForm.is_required,
      order: approverForm.order,
    };

    setStepForm(prev => ({
      ...prev,
      approvers: [...prev.approvers, newApprover],
    }));

    setApproverForm({
      type: 'user',
      id: '',
      name: '',
      is_required: true,
      order: 0,
    });

    setShowApproverDialog(false);
  }, [approverForm]);

  const handleRemoveApprover = useCallback((index: number) => {
    setStepForm(prev => ({
      ...prev,
      approvers: prev.approvers.filter((_, i) => i !== index),
    }));
  }, []);

  const handleAddEscalationRule = useCallback(() => {
    const newRule: EscalationRule = {
      after_minutes: escalationForm.after_minutes,
      escalate_to: escalationForm.escalate_to,
      notification_template: escalationForm.notification_template,
      auto_approve: escalationForm.auto_approve,
    };

    setStepForm(prev => ({
      ...prev,
      escalation_rules: [...prev.escalation_rules, newRule],
    }));

    setEscalationForm({
      after_minutes: 480,
      escalate_to: [],
      notification_template: '',
      auto_approve: false,
    });

    setShowEscalationDialog(false);
  }, [escalationForm]);

  const handleSaveWorkflow = useCallback(async () => {
    if (!workflowName.trim()) {
      alert('Please enter a workflow name');
      return;
    }

    if (workflowSteps.length === 0) {
      alert('Please add at least one step');
      return;
    }

    try {
      const workflowData: CreateWorkflowTemplateRequest = {
        name: workflowName,
        description: workflowDescription,
        category: 'approval',
        trigger_type: 'manual',
        trigger_conditions: [],
        steps: workflowSteps.map(step => ({
          name: step.name,
          type: step.type,
          order: step.order,
          config: step.config,
          timeout_minutes: step.timeout_minutes,
          retry_count: step.retry_count,
          is_required: step.is_required,
          depends_on: step.depends_on,
        })),
      };

      if (workflowId) {
        await updateWorkflowTemplate({
          id: workflowId,
          ...workflowData,
        }).unwrap();
      } else {
        await createWorkflowTemplate(workflowData).unwrap();
      }

      onSave?.(workflowData);
      refetch();
    } catch (error) {
      console.error('Failed to save workflow:', error);
      alert('Failed to save workflow');
    }
  }, [workflowName, workflowDescription, workflowSteps, workflowId, createWorkflowTemplate, updateWorkflowTemplate, onSave, refetch]);

  const handleContextMenu = useCallback((event: React.MouseEvent, step: WorkflowStep) => {
    event.preventDefault();
    setContextMenu({
      mouseX: event.clientX - 2,
      mouseY: event.clientY - 4,
      step,
    });
  }, []);

  const handleContextMenuClose = useCallback(() => {
    setContextMenu(null);
  }, []);

  const getStepIcon = (type: WorkflowStepType) => {
    switch (type) {
      case 'approval':
        return <CheckCircle color="primary" />;
      case 'notification':
        return <Info color="info" />;
      case 'automation':
        return <Settings color="secondary" />;
      case 'wait':
        return <Schedule color="warning" />;
      case 'condition':
        return <AccountTree color="success" />;
      default:
        return <Assignment />;
    }
  };

  const getApprovalTypeDescription = (type: string) => {
    switch (type) {
      case 'single':
        return 'Single approver required';
      case 'multiple':
        return 'Multiple approvers required';
      case 'sequential':
        return 'Sequential approval required';
      case 'parallel':
        return 'Parallel approval required';
      default:
        return 'Unknown approval type';
    }
  };

  const renderStepCard = (step: WorkflowStep, index: number) => (
    <Draggable key={step.id} draggableId={step.id} index={index}>
      {(provided, snapshot) => (
        <Card
          ref={provided.innerRef}
          {...provided.draggableProps}
          sx={{
            mb: 2,
            opacity: snapshot.isDragging ? 0.8 : 1,
            border: step.is_required ? '2px solid #2196f3' : '1px solid #e0e0e0',
          }}
          onContextMenu={(e) => handleContextMenu(e, step)}
        >
          <CardHeader
            avatar={getStepIcon(step.type)}
            title={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="h6">{step.name}</Typography>
                {step.is_required && (
                  <Chip label="Required" size="small" color="primary" variant="outlined" />
                )}
              </Box>
            }
            subheader={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  {step.type === 'approval' ? getApprovalTypeDescription(step.config.approval_type || 'single') : step.type}
                </Typography>
                {step.timeout_minutes && (
                  <Typography variant="body2" color="text.secondary">
                    Timeout: {Math.floor(step.timeout_minutes / 60)}h {step.timeout_minutes % 60}m
                  </Typography>
                )}
              </Box>
            }
            action={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box {...provided.dragHandleProps}>
                  <IconButton size="small">
                    <SwapVert />
                  </IconButton>
                </Box>
                <IconButton size="small" onClick={() => handleEditStep(step)}>
                  <Edit />
                </IconButton>
                <IconButton size="small" onClick={() => handleDeleteStep(step.id)}>
                  <Delete />
                </IconButton>
              </Box>
            }
          />
          
          {step.type === 'approval' && step.config.approvers && (
            <CardContent>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Approvers ({step.config.approvers.length})
              </Typography>
              <AvatarGroup max={5} sx={{ '& .MuiAvatar-root': { width: 32, height: 32 } }}>
                {step.config.approvers.map((approver, i) => (
                  <Tooltip key={i} title={`${approver.name} (${approver.type})`}>
                    <Avatar sx={{ bgcolor: approver.type === 'user' ? 'primary.main' : 'secondary.main' }}>
                      {approver.name.charAt(0)}
                    </Avatar>
                  </Tooltip>
                ))}
              </AvatarGroup>
              
              {step.config.escalation_rules && step.config.escalation_rules.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    Escalation Rules
                  </Typography>
                  {step.config.escalation_rules.map((rule, i) => (
                    <Chip
                      key={i}
                      label={`After ${Math.floor(rule.after_minutes / 60)}h ${rule.after_minutes % 60}m`}
                      size="small"
                      variant="outlined"
                      sx={{ mr: 1 }}
                    />
                  ))}
                </Box>
              )}
            </CardContent>
          )}
        </Card>
      )}
    </Draggable>
  );

  const renderWorkflowBuilder = () => (
    <Box>
      {/* Workflow Info */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Workflow Information
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Workflow Name"
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              required
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Description"
              value={workflowDescription}
              onChange={(e) => setWorkflowDescription(e.target.value)}
              multiline
              rows={1}
            />
          </Grid>
        </Grid>
      </Paper>

      {/* Steps */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Workflow Steps ({workflowSteps.length})
          </Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={handleAddStep}
          >
            Add Step
          </Button>
        </Box>

        {workflowSteps.length === 0 ? (
          <Alert severity="info">
            No steps defined. Click "Add Step" to create your first approval step.
          </Alert>
        ) : (
          <DragDropContext onDragEnd={handleDragEnd}>
            <Droppable droppableId="workflow-steps">
              {(provided) => (
                <Box {...provided.droppableProps} ref={provided.innerRef}>
                  {workflowSteps.map((step, index) => renderStepCard(step, index))}
                  {provided.placeholder}
                </Box>
              )}
            </Droppable>
          </DragDropContext>
        )}
      </Paper>

      {/* Actions */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
          <Button variant="outlined" onClick={() => window.history.back()}>
            Cancel
          </Button>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSaveWorkflow}
            disabled={createLoading || updateLoading}
          >
            {workflowId ? 'Update' : 'Create'} Workflow
          </Button>
        </Box>
      </Paper>
    </Box>
  );

  const content = (
    <Box>
      {renderWorkflowBuilder()}

      {/* Step Dialog */}
      <Dialog
        open={showStepDialog}
        onClose={() => setShowStepDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingStep ? 'Edit Step' : 'Add Step'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              fullWidth
              label="Step Name"
              value={stepForm.name}
              onChange={(e) => setStepForm({ ...stepForm, name: e.target.value })}
              required
            />

            <FormControl fullWidth>
              <InputLabel>Step Type</InputLabel>
              <Select
                value={stepForm.type}
                onChange={(e) => setStepForm({ ...stepForm, type: e.target.value as WorkflowStepType })}
                label="Step Type"
              >
                <MenuItem value="approval">Approval</MenuItem>
                <MenuItem value="notification">Notification</MenuItem>
                <MenuItem value="automation">Automation</MenuItem>
                <MenuItem value="wait">Wait</MenuItem>
                <MenuItem value="condition">Condition</MenuItem>
              </Select>
            </FormControl>

            {stepForm.type === 'approval' && (
              <>
                <FormControl fullWidth>
                  <InputLabel>Approval Type</InputLabel>
                  <Select
                    value={stepForm.approval_type}
                    onChange={(e) => setStepForm({ ...stepForm, approval_type: e.target.value as any })}
                    label="Approval Type"
                  >
                    <MenuItem value="single">Single Approver</MenuItem>
                    <MenuItem value="multiple">Multiple Approvers</MenuItem>
                    <MenuItem value="sequential">Sequential Approval</MenuItem>
                    <MenuItem value="parallel">Parallel Approval</MenuItem>
                  </Select>
                </FormControl>

                {stepForm.approval_type === 'multiple' && (
                  <TextField
                    fullWidth
                    label="Minimum Approvals Required"
                    type="number"
                    value={stepForm.min_approvals}
                    onChange={(e) => setStepForm({ ...stepForm, min_approvals: parseInt(e.target.value) || 1 })}
                    InputProps={{ inputProps: { min: 1 } }}
                  />
                )}

                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="subtitle2">
                      Approvers ({stepForm.approvers.length})
                    </Typography>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<Add />}
                      onClick={() => setShowApproverDialog(true)}
                    >
                      Add Approver
                    </Button>
                  </Box>

                  <List dense>
                    {stepForm.approvers.map((approver, index) => (
                      <ListItem key={index}>
                        <ListItemAvatar>
                          <Avatar sx={{ bgcolor: approver.type === 'user' ? 'primary.main' : 'secondary.main' }}>
                            {approver.name.charAt(0)}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={approver.name}
                          secondary={`${approver.type} ${approver.is_required ? '(Required)' : '(Optional)'}`}
                        />
                        <ListItemSecondaryAction>
                          <IconButton size="small" onClick={() => handleRemoveApprover(index)}>
                            <Delete />
                          </IconButton>
                        </ListItemSecondaryAction>
                      </ListItem>
                    ))}
                  </List>
                </Box>

                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="subtitle2">
                      Escalation Rules ({stepForm.escalation_rules.length})
                    </Typography>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<Add />}
                      onClick={() => setShowEscalationDialog(true)}
                    >
                      Add Rule
                    </Button>
                  </Box>

                  {stepForm.escalation_rules.map((rule, index) => (
                    <Chip
                      key={index}
                      label={`After ${Math.floor(rule.after_minutes / 60)}h ${rule.after_minutes % 60}m`}
                      size="small"
                      variant="outlined"
                      sx={{ mr: 1, mb: 1 }}
                    />
                  ))}
                </Box>
              </>
            )}

            <TextField
              fullWidth
              label="Timeout (minutes)"
              type="number"
              value={stepForm.timeout_minutes}
              onChange={(e) => setStepForm({ ...stepForm, timeout_minutes: parseInt(e.target.value) || 0 })}
              InputProps={{ inputProps: { min: 0 } }}
            />

            <FormControlLabel
              control={
                <Switch
                  checked={stepForm.is_required}
                  onChange={(e) => setStepForm({ ...stepForm, is_required: e.target.checked })}
                />
              }
              label="Required Step"
            />

            <FormControlLabel
              control={
                <Switch
                  checked={stepForm.allow_self_approval}
                  onChange={(e) => setStepForm({ ...stepForm, allow_self_approval: e.target.checked })}
                />
              }
              label="Allow Self Approval"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowStepDialog(false)}>Cancel</Button>
          <Button onClick={handleSaveStep} variant="contained" disabled={!stepForm.name}>
            {editingStep ? 'Update' : 'Add'} Step
          </Button>
        </DialogActions>
      </Dialog>

      {/* Approver Dialog */}
      <Dialog
        open={showApproverDialog}
        onClose={() => setShowApproverDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Approver</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Approver Type</InputLabel>
              <Select
                value={approverForm.type}
                onChange={(e) => setApproverForm({ ...approverForm, type: e.target.value as any })}
                label="Approver Type"
              >
                <MenuItem value="user">User</MenuItem>
                <MenuItem value="group">Group</MenuItem>
                <MenuItem value="role">Role</MenuItem>
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="Approver ID"
              value={approverForm.id}
              onChange={(e) => setApproverForm({ ...approverForm, id: e.target.value })}
              required
            />

            <TextField
              fullWidth
              label="Approver Name"
              value={approverForm.name}
              onChange={(e) => setApproverForm({ ...approverForm, name: e.target.value })}
              required
            />

            <TextField
              fullWidth
              label="Order"
              type="number"
              value={approverForm.order}
              onChange={(e) => setApproverForm({ ...approverForm, order: parseInt(e.target.value) || 0 })}
              InputProps={{ inputProps: { min: 0 } }}
            />

            <FormControlLabel
              control={
                <Switch
                  checked={approverForm.is_required}
                  onChange={(e) => setApproverForm({ ...approverForm, is_required: e.target.checked })}
                />
              }
              label="Required Approver"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowApproverDialog(false)}>Cancel</Button>
          <Button onClick={handleAddApprover} variant="contained" disabled={!approverForm.id || !approverForm.name}>
            Add Approver
          </Button>
        </DialogActions>
      </Dialog>

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
        <MenuItem onClick={() => {
          if (contextMenu) handleEditStep(contextMenu.step);
          handleContextMenuClose();
        }}>
          <Edit sx={{ mr: 1 }} />
          Edit Step
        </MenuItem>
        <MenuItem onClick={() => {
          // TODO: Implement copy step
          handleContextMenuClose();
        }}>
          <Copy sx={{ mr: 1 }} />
          Copy Step
        </MenuItem>
        <Divider />
        <MenuItem onClick={() => {
          if (contextMenu) handleDeleteStep(contextMenu.step.id);
          handleContextMenuClose();
        }} sx={{ color: 'error.main' }}>
          <Delete sx={{ mr: 1 }} />
          Delete Step
        </MenuItem>
      </Menu>

      {/* Loading */}
      {(createLoading || updateLoading || deleteLoading) && (
        <LinearProgress sx={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1301 }} />
      )}
    </Box>
  );

  if (embedded) {
    return content;
  }

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      <Typography variant="h4" component="h1" sx={{ mb: 3 }}>
        Approval Routing
      </Typography>
      {content}
    </Container>
  );
};

export default ApprovalRouting;