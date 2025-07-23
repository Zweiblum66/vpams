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
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  AlertTitle,
  Stepper,
  Step,
  StepLabel,
  FormControlLabel,
  Switch,
  Slider,
  Grid,
  Collapse,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  PlayArrow as TestIcon,
  AccountTree as RoutingIcon,
  Group as GroupIcon,
  Person as PersonIcon,
  Business as DepartmentIcon,
  AttachMoney as ExpenseIcon,
  Article as ContentIcon,
  Lock as AccessIcon,
  Folder as ProjectIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Info as InfoIcon,
  CheckCircle as SuccessIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';

interface RoutingRule {
  id: string;
  type: string;
  name: string;
  condition: string;
  routing: string;
  deadline: string;
}

interface ApproverSuggestion {
  approver_type: string;
  identifier: string;
  name: string;
  email?: string;
  reason?: string;
}

interface RoutingExample {
  name: string;
  description: string;
  context: any;
  expected_routing: string;
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
      id={`routing-tabpanel-${index}`}
      aria-labelledby={`routing-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const ApprovalRoutingConfig: React.FC = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [rules, setRules] = useState<RoutingRule[]>([]);
  const [examples, setExamples] = useState<RoutingExample[]>([]);
  const [departments, setDepartments] = useState<Record<string, string[]>>({});
  const [approverPools, setApproverPools] = useState<Record<string, any[]>>({});
  
  // Test routing state
  const [testContext, setTestContext] = useState({
    approval_type: 'expense',
    amount: 0,
    department: '',
    urgency: 'normal',
    title: 'Test Approval',
    description: 'Test routing logic',
  });
  const [testResult, setTestResult] = useState<any>(null);
  const [showTestDialog, setShowTestDialog] = useState(false);
  
  // Suggestions state
  const [showSuggestionsDialog, setShowSuggestionsDialog] = useState(false);
  const [suggestions, setSuggestions] = useState<ApproverSuggestion[]>([]);
  const [expandedExample, setExpandedExample] = useState<string | null>(null);

  useEffect(() => {
    fetchRoutingData();
  }, []);

  const fetchRoutingData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Fetch routing rules
      const rulesResponse = await fetch('/api/v1/approval-routing/rules', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const rulesData = await rulesResponse.json();
      setRules(rulesData);
      
      // Fetch examples
      const examplesResponse = await fetch('/api/v1/approval-routing/examples', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const examplesData = await examplesResponse.json();
      setExamples(examplesData);
      
      // Fetch departments
      const deptResponse = await fetch('/api/v1/approval-routing/departments', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const deptData = await deptResponse.json();
      setDepartments(deptData);
      
      // Fetch approver pools
      const poolsResponse = await fetch('/api/v1/approval-routing/approver-pools', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const poolsData = await poolsResponse.json();
      setApproverPools(poolsData);
      
    } catch (error) {
      enqueueSnackbar('Failed to load routing configuration', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleTestRouting = async () => {
    try {
      const response = await fetch('/api/v1/approval-routing/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ context: testContext }),
      });
      
      const result = await response.json();
      setTestResult(result);
      
      if (result.success) {
        enqueueSnackbar('Routing test completed successfully', { variant: 'success' });
      } else {
        enqueueSnackbar(`Routing test failed: ${result.error}`, { variant: 'error' });
      }
    } catch (error) {
      enqueueSnackbar('Failed to test routing', { variant: 'error' });
    }
  };

  const handleSuggestApprovers = async () => {
    try {
      const response = await fetch('/api/v1/approval-routing/suggest-approvers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(testContext),
      });
      
      const data = await response.json();
      setSuggestions(data);
      setShowSuggestionsDialog(true);
    } catch (error) {
      enqueueSnackbar('Failed to get approver suggestions', { variant: 'error' });
    }
  };

  const handleTestExample = async (example: RoutingExample) => {
    setTestContext(example.context);
    setShowTestDialog(true);
    
    // Auto-run test for the example
    try {
      const response = await fetch('/api/v1/approval-routing/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ context: example.context }),
      });
      
      const result = await response.json();
      setTestResult(result);
    } catch (error) {
      enqueueSnackbar('Failed to test example', { variant: 'error' });
    }
  };

  const getApprovalTypeIcon = (type: string) => {
    switch (type) {
      case 'expense':
        return <ExpenseIcon />;
      case 'content':
        return <ContentIcon />;
      case 'access':
        return <AccessIcon />;
      case 'project':
        return <ProjectIcon />;
      default:
        return <RoutingIcon />;
    }
  };

  const getApproverTypeIcon = (type: string) => {
    switch (type) {
      case 'user':
        return <PersonIcon />;
      case 'role':
        return <AccountTree />;
      case 'group':
        return <GroupIcon />;
      default:
        return <PersonIcon />;
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Approval Routing Configuration
      </Typography>
      
      <Card sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="Routing Rules" />
          <Tab label="Test Routing" />
          <Tab label="Examples" />
          <Tab label="Department Hierarchy" />
          <Tab label="Approver Pools" />
        </Tabs>

        {/* Routing Rules Tab */}
        <TabPanel value={tabValue} index={0}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">Configured Routing Rules</Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                disabled
              >
                Add Rule
              </Button>
            </Box>

            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell>Name</TableCell>
                    <TableCell>Condition</TableCell>
                    <TableCell>Routing</TableCell>
                    <TableCell>Deadline</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rules.map((rule) => (
                    <TableRow key={rule.id}>
                      <TableCell>
                        <Chip
                          icon={getApprovalTypeIcon(rule.type)}
                          label={rule.type}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{rule.name}</TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {rule.condition}
                        </Typography>
                      </TableCell>
                      <TableCell>{rule.routing}</TableCell>
                      <TableCell>{rule.deadline}</TableCell>
                      <TableCell>
                        <IconButton size="small" disabled>
                          <EditIcon />
                        </IconButton>
                        <IconButton size="small" disabled>
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </TabPanel>

        {/* Test Routing Tab */}
        <TabPanel value={tabValue} index={1}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Test Approval Routing
            </Typography>
            
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 3 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    Test Context
                  </Typography>
                  
                  <FormControl fullWidth margin="normal">
                    <InputLabel>Approval Type</InputLabel>
                    <Select
                      value={testContext.approval_type}
                      onChange={(e) => setTestContext({ ...testContext, approval_type: e.target.value })}
                    >
                      <MenuItem value="expense">Expense</MenuItem>
                      <MenuItem value="content">Content</MenuItem>
                      <MenuItem value="access">Access</MenuItem>
                      <MenuItem value="project">Project</MenuItem>
                      <MenuItem value="general">General</MenuItem>
                    </Select>
                  </FormControl>

                  {testContext.approval_type === 'expense' && (
                    <TextField
                      fullWidth
                      margin="normal"
                      label="Amount"
                      type="number"
                      value={testContext.amount}
                      onChange={(e) => setTestContext({ ...testContext, amount: parseFloat(e.target.value) })}
                    />
                  )}

                  <FormControl fullWidth margin="normal">
                    <InputLabel>Department</InputLabel>
                    <Select
                      value={testContext.department}
                      onChange={(e) => setTestContext({ ...testContext, department: e.target.value })}
                    >
                      <MenuItem value="">None</MenuItem>
                      {Object.keys(departments).map((dept) => (
                        <MenuItem key={dept} value={dept}>{dept}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <FormControl fullWidth margin="normal">
                    <InputLabel>Urgency</InputLabel>
                    <Select
                      value={testContext.urgency}
                      onChange={(e) => setTestContext({ ...testContext, urgency: e.target.value })}
                    >
                      <MenuItem value="low">Low</MenuItem>
                      <MenuItem value="normal">Normal</MenuItem>
                      <MenuItem value="high">High</MenuItem>
                      <MenuItem value="critical">Critical</MenuItem>
                    </Select>
                  </FormControl>

                  <TextField
                    fullWidth
                    margin="normal"
                    label="Title"
                    value={testContext.title}
                    onChange={(e) => setTestContext({ ...testContext, title: e.target.value })}
                  />

                  <TextField
                    fullWidth
                    margin="normal"
                    label="Description"
                    multiline
                    rows={2}
                    value={testContext.description}
                    onChange={(e) => setTestContext({ ...testContext, description: e.target.value })}
                  />

                  <Box mt={2} display="flex" gap={2}>
                    <Button
                      variant="contained"
                      startIcon={<TestIcon />}
                      onClick={handleTestRouting}
                    >
                      Test Routing
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<GroupIcon />}
                      onClick={handleSuggestApprovers}
                    >
                      Suggest Approvers
                    </Button>
                  </Box>
                </Paper>
              </Grid>

              <Grid item xs={12} md={6}>
                {testResult && (
                  <Paper sx={{ p: 3 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Test Result
                    </Typography>
                    
                    {testResult.success ? (
                      <>
                        <Alert severity="success" sx={{ mb: 2 }}>
                          <AlertTitle>Routing Successful</AlertTitle>
                          {testResult.approver_count} approver(s) assigned
                        </Alert>
                        
                        <Box mb={2}>
                          <Typography variant="body2" color="text.secondary">
                            Approval Type
                          </Typography>
                          <Typography variant="body1">
                            {testResult.approval_type}
                          </Typography>
                        </Box>

                        <Box mb={2}>
                          <Typography variant="body2" color="text.secondary">
                            Deadline
                          </Typography>
                          <Typography variant="body1">
                            {testResult.deadline_hours} hours
                          </Typography>
                        </Box>

                        {testResult.voting_strategy && (
                          <Box mb={2}>
                            <Typography variant="body2" color="text.secondary">
                              Voting Strategy
                            </Typography>
                            <Typography variant="body1">
                              {testResult.voting_strategy}
                            </Typography>
                          </Box>
                        )}

                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          Approvers
                        </Typography>
                        <List dense>
                          {testResult.approvers?.map((approver: any, index: number) => (
                            <ListItem key={index}>
                              <ListItemAvatar>
                                <Avatar>
                                  {getApproverTypeIcon(approver.type)}
                                </Avatar>
                              </ListItemAvatar>
                              <ListItemText
                                primary={approver.name}
                                secondary={`${approver.type} - ${approver.identifier}`}
                              />
                            </ListItem>
                          ))}
                        </List>
                      </>
                    ) : (
                      <Alert severity="error">
                        <AlertTitle>Routing Failed</AlertTitle>
                        {testResult.error}
                      </Alert>
                    )}
                  </Paper>
                )}
              </Grid>
            </Grid>
          </CardContent>
        </TabPanel>

        {/* Examples Tab */}
        <TabPanel value={tabValue} index={2}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Routing Examples
            </Typography>
            
            <Grid container spacing={2}>
              {examples.map((example) => (
                <Grid item xs={12} md={6} key={example.name}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box display="flex" justifyContent="space-between" alignItems="start">
                        <Box flex={1}>
                          <Typography variant="subtitle1" gutterBottom>
                            {example.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" paragraph>
                            {example.description}
                          </Typography>
                          <Chip
                            label={example.expected_routing}
                            size="small"
                            color="primary"
                            variant="outlined"
                          />
                        </Box>
                        <IconButton
                          onClick={() => setExpandedExample(
                            expandedExample === example.name ? null : example.name
                          )}
                        >
                          {expandedExample === example.name ? <CollapseIcon /> : <ExpandIcon />}
                        </IconButton>
                      </Box>
                      
                      <Collapse in={expandedExample === example.name}>
                        <Box mt={2} p={2} bgcolor="grey.50" borderRadius={1}>
                          <Typography variant="body2" sx={{ fontFamily: 'monospace', whiteSpace: 'pre' }}>
                            {JSON.stringify(example.context, null, 2)}
                          </Typography>
                        </Box>
                        <Box mt={2}>
                          <Button
                            size="small"
                            variant="contained"
                            startIcon={<TestIcon />}
                            onClick={() => handleTestExample(example)}
                          >
                            Test This Example
                          </Button>
                        </Box>
                      </Collapse>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </TabPanel>

        {/* Department Hierarchy Tab */}
        <TabPanel value={tabValue} index={3}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Department Approval Hierarchies
            </Typography>
            
            <Grid container spacing={3}>
              {Object.entries(departments).map(([dept, hierarchy]) => (
                <Grid item xs={12} md={6} key={dept}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box display="flex" alignItems="center" mb={2}>
                        <DepartmentIcon sx={{ mr: 1 }} />
                        <Typography variant="subtitle1">
                          {dept.charAt(0).toUpperCase() + dept.slice(1)}
                        </Typography>
                      </Box>
                      
                      <Stepper orientation="vertical" activeStep={-1}>
                        {hierarchy.map((role, index) => (
                          <Step key={index} expanded>
                            <StepLabel>
                              {role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </StepLabel>
                          </Step>
                        ))}
                      </Stepper>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </TabPanel>

        {/* Approver Pools Tab */}
        <TabPanel value={tabValue} index={4}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Approver Pools
            </Typography>
            
            <Grid container spacing={3}>
              {Object.entries(approverPools).map(([poolName, approvers]) => (
                <Grid item xs={12} md={6} key={poolName}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle1" gutterBottom>
                        {poolName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </Typography>
                      
                      <List dense>
                        {approvers.map((approver: any, index: number) => (
                          <ListItem key={index}>
                            <ListItemAvatar>
                              <Avatar>
                                {getApproverTypeIcon(approver.approver_type)}
                              </Avatar>
                            </ListItemAvatar>
                            <ListItemText
                              primary={approver.name}
                              secondary={
                                <>
                                  <Chip label={approver.approver_type} size="small" sx={{ mr: 1 }} />
                                  {approver.email}
                                </>
                              }
                            />
                          </ListItem>
                        ))}
                      </List>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </TabPanel>
      </Card>

      {/* Test Dialog */}
      <Dialog
        open={showTestDialog}
        onClose={() => setShowTestDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Routing Test Results</DialogTitle>
        <DialogContent>
          {testResult && testResult.success && (
            <Box>
              <Alert severity="info" sx={{ mb: 2 }}>
                Based on the provided context, the system would route this approval as follows:
              </Alert>
              
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Approval Type
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    {testResult.approval_type}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Deadline
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    {testResult.deadline_hours} hours
                  </Typography>
                </Grid>
              </Grid>

              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                Assigned Approvers ({testResult.approver_count})
              </Typography>
              <List>
                {testResult.approvers?.map((approver: any, index: number) => (
                  <ListItem key={index}>
                    <ListItemAvatar>
                      <Avatar>{getApproverTypeIcon(approver.type)}</Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={approver.name}
                      secondary={`${approver.type} - ${approver.identifier}`}
                    />
                  </ListItem>
                ))}
              </List>

              {testResult.escalation_rules > 0 && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  {testResult.escalation_rules} escalation rule(s) will be applied
                </Alert>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowTestDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Suggestions Dialog */}
      <Dialog
        open={showSuggestionsDialog}
        onClose={() => setShowSuggestionsDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Suggested Approvers</DialogTitle>
        <DialogContent>
          <List>
            {suggestions.map((suggestion, index) => (
              <ListItem key={index}>
                <ListItemAvatar>
                  <Avatar>{getApproverTypeIcon(suggestion.approver_type)}</Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={suggestion.name}
                  secondary={
                    <>
                      {suggestion.identifier}
                      {suggestion.reason && (
                        <Typography variant="caption" display="block">
                          {suggestion.reason}
                        </Typography>
                      )}
                    </>
                  }
                />
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSuggestionsDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ApprovalRoutingConfig;