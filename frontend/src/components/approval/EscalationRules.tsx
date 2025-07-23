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
  Switch,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  ListItemSecondaryAction,
  Alert,
  Divider,
  Stack,
  Grid,
  Tooltip,
  Badge,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Container,
  LinearProgress,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  ExpandMore,
  Schedule,
  Person,
  Group,
  Business,
  Warning,
  CheckCircle,
  Cancel,
  PlayArrow,
  Pause,
  Stop,
  Timeline,
  Notifications,
  Email,
  Phone,
  Settings,
  Priority,
  AccessTime,
  TrendingUp,
  Assignment,
  Save,
  Refresh,
  Visibility,
  VisibilityOff,
  Info,
} from '@mui/icons-material';
import { format, addMinutes } from 'date-fns';
import {
  WorkflowApprover,
  EscalationRule,
  EscalationAction,
  EscalationTrigger,
  EscalationNotification,
  ApprovalPriority,
} from '../../types/workflow';
import {
  useGetEscalationRulesQuery,
  useCreateEscalationRuleMutation,
  useUpdateEscalationRuleMutation,
  useDeleteEscalationRuleMutation,
  useTestEscalationRuleMutation,
} from '../../store/api/workflowApi';

interface EscalationRulesProps {
  workflowId?: string;
  stepId?: string;
  onSave?: (rules: EscalationRule[]) => void;
  embedded?: boolean;
}

const EscalationRules: React.FC<EscalationRulesProps> = ({
  workflowId,
  stepId,
  onSave,
  embedded = false,
}) => {
  const [showRuleDialog, setShowRuleDialog] = useState(false);
  const [editingRule, setEditingRule] = useState<EscalationRule | null>(null);
  const [showTestDialog, setShowTestDialog] = useState(false);
  const [testingRule, setTestingRule] = useState<EscalationRule | null>(null);
  const [expandedRule, setExpandedRule] = useState<string | null>(null);

  // Rule form state
  const [ruleForm, setRuleForm] = useState({
    name: '',
    description: '',
    trigger: {
      type: 'timeout' as EscalationTrigger,
      after_minutes: 480, // 8 hours
      conditions: [],
    },
    actions: [] as EscalationAction[],
    notifications: [] as EscalationNotification[],
    escalate_to: [] as WorkflowApprover[],
    auto_approve: false,
    priority: 'medium' as ApprovalPriority,
    is_active: true,
    max_escalations: 3,
    escalation_interval: 240, // 4 hours
  });

  // Action form state
  const [actionForm, setActionForm] = useState({
    type: 'escalate' as EscalationAction['type'],
    target_type: 'user' as 'user' | 'group' | 'role',
    target_id: '',
    target_name: '',
    parameters: {},
  });

  // Notification form state
  const [notificationForm, setNotificationForm] = useState({
    type: 'email' as EscalationNotification['type'],
    template: '',
    recipients: [] as string[],
    delay_minutes: 0,
  });

  // API hooks
  const { data: escalationRules, isLoading, refetch } = useGetEscalationRulesQuery({
    workflow_id: workflowId,
    step_id: stepId,
  });

  const [createEscalationRule, { isLoading: createLoading }] = useCreateEscalationRuleMutation();
  const [updateEscalationRule, { isLoading: updateLoading }] = useUpdateEscalationRuleMutation();
  const [deleteEscalationRule, { isLoading: deleteLoading }] = useDeleteEscalationRuleMutation();
  const [testEscalationRule, { isLoading: testLoading }] = useTestEscalationRuleMutation();

  const handleAddRule = useCallback(() => {
    setEditingRule(null);
    setRuleForm({
      name: '',
      description: '',
      trigger: {
        type: 'timeout',
        after_minutes: 480,
        conditions: [],
      },
      actions: [],
      notifications: [],
      escalate_to: [],
      auto_approve: false,
      priority: 'medium',
      is_active: true,
      max_escalations: 3,
      escalation_interval: 240,
    });
    setShowRuleDialog(true);
  }, []);

  const handleEditRule = useCallback((rule: EscalationRule) => {
    setEditingRule(rule);
    setRuleForm({
      name: rule.name || '',
      description: rule.description || '',
      trigger: rule.trigger || {
        type: 'timeout',
        after_minutes: 480,
        conditions: [],
      },
      actions: rule.actions || [],
      notifications: rule.notifications || [],
      escalate_to: rule.escalate_to || [],
      auto_approve: rule.auto_approve || false,
      priority: rule.priority || 'medium',
      is_active: rule.is_active !== false,
      max_escalations: rule.max_escalations || 3,
      escalation_interval: rule.escalation_interval || 240,
    });
    setShowRuleDialog(true);
  }, []);

  const handleSaveRule = useCallback(async () => {
    if (!ruleForm.name.trim()) {
      alert('Please enter a rule name');
      return;
    }

    try {
      const ruleData = {
        ...ruleForm,
        workflow_id: workflowId,
        step_id: stepId,
      };

      if (editingRule) {
        await updateEscalationRule({
          id: editingRule.id!,
          ...ruleData,
        }).unwrap();
      } else {
        await createEscalationRule(ruleData).unwrap();
      }

      setShowRuleDialog(false);
      setEditingRule(null);
      refetch();
      onSave?.(escalationRules?.data || []);
    } catch (error) {
      console.error('Failed to save escalation rule:', error);
      alert('Failed to save escalation rule');
    }
  }, [ruleForm, editingRule, workflowId, stepId, createEscalationRule, updateEscalationRule, refetch, onSave, escalationRules?.data]);

  const handleDeleteRule = useCallback(async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this escalation rule?')) return;

    try {
      await deleteEscalationRule(ruleId).unwrap();
      refetch();
      onSave?.(escalationRules?.data || []);
    } catch (error) {
      console.error('Failed to delete escalation rule:', error);
      alert('Failed to delete escalation rule');
    }
  }, [deleteEscalationRule, refetch, onSave, escalationRules?.data]);

  const handleTestRule = useCallback(async (rule: EscalationRule) => {
    setTestingRule(rule);
    setShowTestDialog(true);
  }, []);

  const handleRunTest = useCallback(async () => {
    if (!testingRule) return;

    try {
      await testEscalationRule({
        id: testingRule.id!,
        test_scenario: 'manual',
      }).unwrap();
      
      setShowTestDialog(false);
      setTestingRule(null);
      alert('Test completed successfully');
    } catch (error) {
      console.error('Failed to test escalation rule:', error);
      alert('Failed to test escalation rule');
    }
  }, [testingRule, testEscalationRule]);

  const handleAddAction = useCallback(() => {
    const newAction: EscalationAction = {
      type: actionForm.type,
      target_type: actionForm.target_type,
      target_id: actionForm.target_id,
      target_name: actionForm.target_name,
      parameters: actionForm.parameters,
    };

    setRuleForm(prev => ({
      ...prev,
      actions: [...prev.actions, newAction],
    }));

    setActionForm({
      type: 'escalate',
      target_type: 'user',
      target_id: '',
      target_name: '',
      parameters: {},
    });
  }, [actionForm]);

  const handleRemoveAction = useCallback((index: number) => {
    setRuleForm(prev => ({
      ...prev,
      actions: prev.actions.filter((_, i) => i !== index),
    }));
  }, []);

  const handleAddNotification = useCallback(() => {
    const newNotification: EscalationNotification = {
      type: notificationForm.type,
      template: notificationForm.template,
      recipients: notificationForm.recipients,
      delay_minutes: notificationForm.delay_minutes,
    };

    setRuleForm(prev => ({
      ...prev,
      notifications: [...prev.notifications, newNotification],
    }));

    setNotificationForm({
      type: 'email',
      template: '',
      recipients: [],
      delay_minutes: 0,
    });
  }, [notificationForm]);

  const handleRemoveNotification = useCallback((index: number) => {
    setRuleForm(prev => ({
      ...prev,
      notifications: prev.notifications.filter((_, i) => i !== index),
    }));
  }, []);

  const getTriggerDescription = (trigger: EscalationTrigger) => {
    switch (trigger) {
      case 'timeout':
        return 'After timeout period';
      case 'overdue':
        return 'When overdue';
      case 'no_response':
        return 'No response received';
      case 'rejected':
        return 'After rejection';
      case 'manual':
        return 'Manual trigger';
      default:
        return 'Unknown trigger';
    }
  };

  const getActionIcon = (type: EscalationAction['type']) => {
    switch (type) {
      case 'escalate':
        return <TrendingUp />;
      case 'notify':
        return <Notifications />;
      case 'approve':
        return <CheckCircle />;
      case 'cancel':
        return <Cancel />;
      case 'reassign':
        return <Assignment />;
      default:
        return <Settings />;
    }
  };

  const renderRuleCard = (rule: EscalationRule) => (
    <Card key={rule.id} sx={{ mb: 2 }}>
      <CardHeader
        avatar={
          <Avatar sx={{ bgcolor: rule.is_active ? 'success.main' : 'grey.500' }}>
            {rule.is_active ? <CheckCircle /> : <Pause />}
          </Avatar>
        }
        title={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h6">{rule.name}</Typography>
            <Chip
              label={rule.priority}
              size="small"
              color={rule.priority === 'urgent' ? 'error' : 
                     rule.priority === 'high' ? 'warning' : 
                     rule.priority === 'medium' ? 'info' : 'success'}
              variant="outlined"
            />
            {!rule.is_active && (
              <Chip label="Inactive" size="small" color="secondary" variant="outlined" />
            )}
          </Box>
        }
        subheader={rule.description}
        action={
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton size="small" onClick={() => handleTestRule(rule)}>
              <PlayArrow />
            </IconButton>
            <IconButton size="small" onClick={() => handleEditRule(rule)}>
              <Edit />
            </IconButton>
            <IconButton size="small" onClick={() => handleDeleteRule(rule.id!)}>
              <Delete />
            </IconButton>
          </Box>
        }
      />
      
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <AccessTime fontSize="small" />
              <Typography variant="body2">
                Trigger: {getTriggerDescription(rule.trigger?.type || 'timeout')}
              </Typography>
            </Box>
            {rule.trigger?.after_minutes && (
              <Typography variant="body2" color="text.secondary">
                After {Math.floor(rule.trigger.after_minutes / 60)}h {rule.trigger.after_minutes % 60}m
              </Typography>
            )}
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Settings fontSize="small" />
              <Typography variant="body2">
                Actions: {rule.actions?.length || 0}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {rule.actions?.map((action, index) => (
                <Tooltip key={index} title={action.type}>
                  <Chip
                    icon={getActionIcon(action.type)}
                    label={action.type}
                    size="small"
                    variant="outlined"
                  />
                </Tooltip>
              ))}
            </Box>
          </Grid>
          
          {rule.escalate_to && rule.escalate_to.length > 0 && (
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Person fontSize="small" />
                <Typography variant="body2">
                  Escalate to: {rule.escalate_to.length} approver{rule.escalate_to.length > 1 ? 's' : ''}
                </Typography>
              </Box>
            </Grid>
          )}
          
          {rule.auto_approve && (
            <Grid item xs={12}>
              <Alert severity="warning" sx={{ mt: 1 }}>
                Auto-approve is enabled for this rule
              </Alert>
            </Grid>
          )}
        </Grid>
      </CardContent>
    </Card>
  );

  const renderRuleDialog = () => (
    <Dialog
      open={showRuleDialog}
      onClose={() => setShowRuleDialog(false)}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        {editingRule ? 'Edit Escalation Rule' : 'Add Escalation Rule'}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
          <TextField
            fullWidth
            label="Rule Name"
            value={ruleForm.name}
            onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
            required
          />
          
          <TextField
            fullWidth
            label="Description"
            value={ruleForm.description}
            onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })}
            multiline
            rows={2}
          />
          
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Trigger Type</InputLabel>
                <Select
                  value={ruleForm.trigger.type}
                  onChange={(e) => setRuleForm({
                    ...ruleForm,
                    trigger: { ...ruleForm.trigger, type: e.target.value as EscalationTrigger }
                  })}
                  label="Trigger Type"
                >
                  <MenuItem value="timeout">Timeout</MenuItem>
                  <MenuItem value="overdue">Overdue</MenuItem>
                  <MenuItem value="no_response">No Response</MenuItem>
                  <MenuItem value="rejected">Rejected</MenuItem>
                  <MenuItem value="manual">Manual</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="After Minutes"
                type="number"
                value={ruleForm.trigger.after_minutes}
                onChange={(e) => setRuleForm({
                  ...ruleForm,
                  trigger: { ...ruleForm.trigger, after_minutes: parseInt(e.target.value) || 0 }
                })}
                InputProps={{ inputProps: { min: 0 } }}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Priority</InputLabel>
                <Select
                  value={ruleForm.priority}
                  onChange={(e) => setRuleForm({ ...ruleForm, priority: e.target.value as ApprovalPriority })}
                  label="Priority"
                >
                  <MenuItem value="low">Low</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="urgent">Urgent</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Max Escalations"
                type="number"
                value={ruleForm.max_escalations}
                onChange={(e) => setRuleForm({ ...ruleForm, max_escalations: parseInt(e.target.value) || 1 })}
                InputProps={{ inputProps: { min: 1, max: 10 } }}
              />
            </Grid>
          </Grid>
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={ruleForm.is_active}
                  onChange={(e) => setRuleForm({ ...ruleForm, is_active: e.target.checked })}
                />
              }
              label="Active"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={ruleForm.auto_approve}
                  onChange={(e) => setRuleForm({ ...ruleForm, auto_approve: e.target.checked })}
                />
              }
              label="Auto Approve"
            />
          </Box>
          
          <Divider />
          
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Actions</Typography>
              <Button
                variant="outlined"
                size="small"
                startIcon={<Add />}
                onClick={() => {
                  // Show action form inline
                }}
              >
                Add Action
              </Button>
            </Box>
            
            {ruleForm.actions.length === 0 ? (
              <Alert severity="info">No actions defined</Alert>
            ) : (
              <List dense>
                {ruleForm.actions.map((action, index) => (
                  <ListItem key={index}>
                    <ListItemAvatar>
                      <Avatar sx={{ bgcolor: 'primary.main' }}>
                        {getActionIcon(action.type)}
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={action.type}
                      secondary={action.target_name}
                    />
                    <ListItemSecondaryAction>
                      <IconButton size="small" onClick={() => handleRemoveAction(index)}>
                        <Delete />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            )}
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setShowRuleDialog(false)}>Cancel</Button>
        <Button onClick={handleSaveRule} variant="contained" disabled={!ruleForm.name || createLoading || updateLoading}>
          {editingRule ? 'Update' : 'Create'} Rule
        </Button>
      </DialogActions>
    </Dialog>
  );

  const renderTestDialog = () => (
    <Dialog
      open={showTestDialog}
      onClose={() => setShowTestDialog(false)}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>Test Escalation Rule</DialogTitle>
      <DialogContent>
        <Alert severity="info" sx={{ mb: 2 }}>
          This will simulate the escalation rule execution without affecting actual approvals.
        </Alert>
        {testingRule && (
          <Box>
            <Typography variant="h6" sx={{ mb: 1 }}>
              {testingRule.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {testingRule.description}
            </Typography>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setShowTestDialog(false)}>Cancel</Button>
        <Button onClick={handleRunTest} variant="contained" disabled={testLoading}>
          Run Test
        </Button>
      </DialogActions>
    </Dialog>
  );

  if (isLoading) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress sx={{ mb: 2 }} />
        <Typography>Loading escalation rules...</Typography>
      </Box>
    );
  }

  const content = (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">
          Escalation Rules ({escalationRules?.data?.length || 0})
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleAddRule}
        >
          Add Rule
        </Button>
      </Box>

      {!escalationRules?.data || escalationRules.data.length === 0 ? (
        <Alert severity="info">
          No escalation rules defined. Click "Add Rule" to create your first escalation rule.
        </Alert>
      ) : (
        <Box>
          {escalationRules.data.map(rule => renderRuleCard(rule))}
        </Box>
      )}

      {renderRuleDialog()}
      {renderTestDialog()}

      {(createLoading || updateLoading || deleteLoading || testLoading) && (
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
        Escalation Rules
      </Typography>
      {content}
    </Container>
  );
};

export default EscalationRules;