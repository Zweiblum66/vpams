import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Card,
  CardContent,
  CardActions,
  Grid,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
} from '@mui/material';
import {
  Add,
  PlayArrow,
  Stop,
  Delete,
  Edit,
  Visibility,
  ExpandMore,
  CheckCircle,
  Error,
  Warning,
  Code,
  Timeline,
  Assessment,
  DataObject,
  BugReport,
  Speed,
} from '@mui/icons-material';
import { useParams } from 'react-router-dom';
import {
  useGetTestCasesQuery,
  useCreateTestCaseMutation,
  useUpdateTestCaseMutation,
  useDeleteTestCaseMutation,
  useRunTestCaseMutation,
  useRunAllTestCasesMutation,
  useGetTestResultsQuery,
  useGetTestResultQuery,
  useGetTestDataTemplatesQuery,
  useCreateTestDataTemplateMutation,
  useGetTestCoverageQuery,
  WorkflowTestCase,
  WorkflowTestResult,
  WorkflowTestDataTemplate,
  WorkflowTestCoverage,
  WorkflowTestSuiteResult,
} from '../../store/api/workflowApi';

interface WorkflowTestingProps {
  workflowId: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`testing-tabpanel-${index}`}
    aria-labelledby={`testing-tab-${index}`}
  >
    {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
  </div>
);

const WorkflowTesting: React.FC<WorkflowTestingProps> = ({ workflowId }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [showCreateTestCase, setShowCreateTestCase] = useState(false);
  const [showTestResult, setShowTestResult] = useState(false);
  const [selectedTestCase, setSelectedTestCase] = useState<WorkflowTestCase | null>(null);
  const [selectedTestResult, setSelectedTestResult] = useState<WorkflowTestResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [runningTests, setRunningTests] = useState<Set<string>>(new Set());

  // Form state
  const [testCaseForm, setTestCaseForm] = useState({
    name: '',
    description: '',
    test_data: '{}',
    expected_outputs: '{}',
    timeout: 300,
    tags: [] as string[],
  });

  // API hooks
  const { data: testCases, isLoading: testCasesLoading } = useGetTestCasesQuery({ 
    workflowId,
    page: 1,
    page_size: 50,
  });
  
  const { data: testResults, isLoading: testResultsLoading } = useGetTestResultsQuery({ 
    workflowId,
    page: 1,
    page_size: 50,
  });

  const { data: testDataTemplates } = useGetTestDataTemplatesQuery({ workflowId });
  const { data: testCoverage } = useGetTestCoverageQuery({ workflowId });

  const [createTestCase] = useCreateTestCaseMutation();
  const [updateTestCase] = useUpdateTestCaseMutation();
  const [deleteTestCase] = useDeleteTestCaseMutation();
  const [runTestCase] = useRunTestCaseMutation();
  const [runAllTestCases] = useRunAllTestCasesMutation();
  const [createTestDataTemplate] = useCreateTestDataTemplateMutation();

  // Event handlers
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleCreateTestCase = useCallback(async () => {
    try {
      const testData = JSON.parse(testCaseForm.test_data);
      const expectedOutputs = testCaseForm.expected_outputs ? JSON.parse(testCaseForm.expected_outputs) : undefined;

      await createTestCase({
        workflowId,
        name: testCaseForm.name,
        description: testCaseForm.description,
        test_data: testData,
        expected_outputs: expectedOutputs,
        timeout: testCaseForm.timeout,
        tags: testCaseForm.tags,
      });

      setShowCreateTestCase(false);
      setTestCaseForm({
        name: '',
        description: '',
        test_data: '{}',
        expected_outputs: '{}',
        timeout: 300,
        tags: [],
      });
    } catch (error) {
      console.error('Failed to create test case:', error);
    }
  }, [workflowId, testCaseForm, createTestCase]);

  const handleRunTestCase = useCallback(async (testCaseId: string) => {
    try {
      setRunningTests(prev => new Set(prev).add(testCaseId));
      await runTestCase({ workflowId, testCaseId });
    } catch (error) {
      console.error('Failed to run test case:', error);
    } finally {
      setRunningTests(prev => {
        const newSet = new Set(prev);
        newSet.delete(testCaseId);
        return newSet;
      });
    }
  }, [workflowId, runTestCase]);

  const handleRunAllTestCases = useCallback(async () => {
    try {
      setIsRunning(true);
      await runAllTestCases({ workflowId, parallel: true });
    } catch (error) {
      console.error('Failed to run all test cases:', error);
    } finally {
      setIsRunning(false);
    }
  }, [workflowId, runAllTestCases]);

  const handleDeleteTestCase = useCallback(async (testCaseId: string) => {
    try {
      await deleteTestCase({ workflowId, testCaseId });
    } catch (error) {
      console.error('Failed to delete test case:', error);
    }
  }, [workflowId, deleteTestCase]);

  const getStatusColor = (status: 'passed' | 'failed' | 'error') => {
    switch (status) {
      case 'passed': return 'success';
      case 'failed': return 'error';
      case 'error': return 'warning';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: 'passed' | 'failed' | 'error') => {
    switch (status) {
      case 'passed': return <CheckCircle color="success" />;
      case 'failed': return <Error color="error" />;
      case 'error': return <Warning color="warning" />;
      default: return null;
    }
  };

  const formatExecutionTime = (timeMs: number) => {
    if (timeMs < 1000) return `${timeMs}ms`;
    if (timeMs < 60000) return `${(timeMs / 1000).toFixed(1)}s`;
    return `${(timeMs / 60000).toFixed(1)}m`;
  };

  const renderTestCasesTab = () => (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">Test Cases</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            onClick={handleRunAllTestCases}
            disabled={isRunning || !testCases?.test_cases.length}
            startIcon={isRunning ? <CircularProgress size={20} /> : <PlayArrow />}
          >
            {isRunning ? 'Running...' : 'Run All'}
          </Button>
          <Button
            variant="contained"
            onClick={() => setShowCreateTestCase(true)}
            startIcon={<Add />}
          >
            Create Test Case
          </Button>
        </Box>
      </Box>

      {testCasesLoading ? (
        <CircularProgress />
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Tags</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Last Run</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {testCases?.test_cases.map((testCase) => {
                const lastResult = testResults?.results.find(r => r.test_case_id === testCase.test_case_id);
                const isRunningTest = runningTests.has(testCase.test_case_id);
                
                return (
                  <TableRow key={testCase.test_case_id}>
                    <TableCell>{testCase.name}</TableCell>
                    <TableCell>{testCase.description}</TableCell>
                    <TableCell>
                      {testCase.tags.map(tag => (
                        <Chip key={tag} label={tag} size="small" sx={{ mr: 0.5 }} />
                      ))}
                    </TableCell>
                    <TableCell>
                      {lastResult ? (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getStatusIcon(lastResult.status)}
                          <Chip 
                            label={lastResult.status} 
                            color={getStatusColor(lastResult.status)}
                            size="small"
                          />
                        </Box>
                      ) : (
                        <Chip label="Not run" color="default" size="small" />
                      )}
                    </TableCell>
                    <TableCell>
                      {lastResult ? (
                        <Box>
                          <Typography variant="caption">
                            {formatExecutionTime(lastResult.execution_time)}
                          </Typography>
                          <Typography variant="caption" display="block" color="text.secondary">
                            {new Date(lastResult.created_at).toLocaleString()}
                          </Typography>
                        </Box>
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          Never
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Tooltip title="Run Test">
                          <IconButton
                            size="small"
                            onClick={() => handleRunTestCase(testCase.test_case_id)}
                            disabled={isRunningTest}
                          >
                            {isRunningTest ? <CircularProgress size={20} /> : <PlayArrow />}
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="View Results">
                          <IconButton
                            size="small"
                            onClick={() => {
                              setSelectedTestCase(testCase);
                              setSelectedTestResult(lastResult || null);
                              setShowTestResult(true);
                            }}
                          >
                            <Visibility />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Edit">
                          <IconButton size="small">
                            <Edit />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteTestCase(testCase.test_case_id)}
                          >
                            <Delete />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );

  const renderTestResultsTab = () => (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>Test Results</Typography>
      
      {testResultsLoading ? (
        <CircularProgress />
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Test Case</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Execution Time</TableCell>
                <TableCell>Started</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {testResults?.results.map((result) => {
                const testCase = testCases?.test_cases.find(tc => tc.test_case_id === result.test_case_id);
                
                return (
                  <TableRow key={result.result_id}>
                    <TableCell>{testCase?.name || 'Unknown'}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {getStatusIcon(result.status)}
                        <Chip 
                          label={result.status} 
                          color={getStatusColor(result.status)}
                          size="small"
                        />
                      </Box>
                    </TableCell>
                    <TableCell>{formatExecutionTime(result.execution_time)}</TableCell>
                    <TableCell>{new Date(result.start_time).toLocaleString()}</TableCell>
                    <TableCell>
                      <Tooltip title="View Details">
                        <IconButton
                          size="small"
                          onClick={() => {
                            setSelectedTestResult(result);
                            setSelectedTestCase(testCase || null);
                            setShowTestResult(true);
                          }}
                        >
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );

  const renderTestCoverageTab = () => (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>Test Coverage</Typography>
      
      {testCoverage ? (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <Assessment sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Coverage Summary
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Node Coverage</Typography>
                    <Typography variant="body2">
                      {testCoverage.tested_nodes}/{testCoverage.total_nodes} ({testCoverage.coverage_percentage.toFixed(1)}%)
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={testCoverage.coverage_percentage}
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                </Box>
                <Typography variant="caption" color="text.secondary">
                  Generated: {new Date(testCoverage.generated_at).toLocaleString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <BugReport sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Untested Paths
                </Typography>
                {testCoverage.untested_paths.length > 0 ? (
                  testCoverage.untested_paths.map((path, index) => (
                    <Alert key={index} severity="warning" sx={{ mb: 1 }}>
                      <Typography variant="body2">{path.reason}</Typography>
                    </Alert>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    All paths are covered by tests
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Node Coverage Details
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Node ID</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Test Cases</TableCell>
                        <TableCell>Execution Count</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.values(testCoverage.node_coverage).map((nodeCoverage) => (
                        <TableRow key={nodeCoverage.node_id}>
                          <TableCell>{nodeCoverage.node_id}</TableCell>
                          <TableCell>
                            <Chip
                              label={nodeCoverage.is_covered ? 'Covered' : 'Not Covered'}
                              color={nodeCoverage.is_covered ? 'success' : 'error'}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>{nodeCoverage.test_cases.length}</TableCell>
                          <TableCell>{nodeCoverage.execution_count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      ) : (
        <Alert severity="info">
          No coverage data available. Run some tests to generate coverage information.
        </Alert>
      )}
    </Box>
  );

  return (
    <Box sx={{ width: '100%' }}>
      <Tabs value={activeTab} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tab label="Test Cases" />
        <Tab label="Test Results" />
        <Tab label="Coverage" />
        <Tab label="Data Templates" />
      </Tabs>

      <TabPanel value={activeTab} index={0}>
        {renderTestCasesTab()}
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        {renderTestResultsTab()}
      </TabPanel>

      <TabPanel value={activeTab} index={2}>
        {renderTestCoverageTab()}
      </TabPanel>

      <TabPanel value={activeTab} index={3}>
        <Typography variant="h6" sx={{ mb: 2 }}>Test Data Templates</Typography>
        <Alert severity="info">
          Test data templates functionality will be implemented here.
        </Alert>
      </TabPanel>

      {/* Create Test Case Dialog */}
      <Dialog open={showCreateTestCase} onClose={() => setShowCreateTestCase(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create Test Case</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Name"
            value={testCaseForm.name}
            onChange={(e) => setTestCaseForm({ ...testCaseForm, name: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Description"
            value={testCaseForm.description}
            onChange={(e) => setTestCaseForm({ ...testCaseForm, description: e.target.value })}
            margin="normal"
            multiline
            rows={2}
          />
          <TextField
            fullWidth
            label="Test Data (JSON)"
            value={testCaseForm.test_data}
            onChange={(e) => setTestCaseForm({ ...testCaseForm, test_data: e.target.value })}
            margin="normal"
            multiline
            rows={4}
          />
          <TextField
            fullWidth
            label="Expected Outputs (JSON)"
            value={testCaseForm.expected_outputs}
            onChange={(e) => setTestCaseForm({ ...testCaseForm, expected_outputs: e.target.value })}
            margin="normal"
            multiline
            rows={4}
          />
          <TextField
            fullWidth
            label="Timeout (seconds)"
            type="number"
            value={testCaseForm.timeout}
            onChange={(e) => setTestCaseForm({ ...testCaseForm, timeout: Number(e.target.value) })}
            margin="normal"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreateTestCase(false)}>Cancel</Button>
          <Button onClick={handleCreateTestCase} variant="contained">Create</Button>
        </DialogActions>
      </Dialog>

      {/* Test Result Details Dialog */}
      <Dialog open={showTestResult} onClose={() => setShowTestResult(false)} maxWidth="lg" fullWidth>
        <DialogTitle>
          Test Result Details
          {selectedTestCase && ` - ${selectedTestCase.name}`}
        </DialogTitle>
        <DialogContent>
          {selectedTestResult && (
            <Box>
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6">Status</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getStatusIcon(selectedTestResult.status)}
                    <Chip 
                      label={selectedTestResult.status} 
                      color={getStatusColor(selectedTestResult.status)}
                    />
                  </Box>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6">Execution Time</Typography>
                  <Typography>{formatExecutionTime(selectedTestResult.execution_time)}</Typography>
                </Grid>
              </Grid>

              {selectedTestResult.error_message && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  <Typography variant="body2">{selectedTestResult.error_message}</Typography>
                </Alert>
              )}

              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography>Step Results</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Step</TableCell>
                          <TableCell>Status</TableCell>
                          <TableCell>Execution Time</TableCell>
                          <TableCell>Error</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {selectedTestResult.step_results.map((step, index) => (
                          <TableRow key={index}>
                            <TableCell>{step.step_name}</TableCell>
                            <TableCell>
                              <Chip 
                                label={step.status} 
                                color={getStatusColor(step.status)}
                                size="small"
                              />
                            </TableCell>
                            <TableCell>{formatExecutionTime(step.execution_time)}</TableCell>
                            <TableCell>{step.error_message || '-'}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </AccordionDetails>
              </Accordion>

              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography>Input Data</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ bgcolor: 'grey.100', p: 2, borderRadius: 1 }}>
                    <pre>{JSON.stringify(selectedTestResult.input_data, null, 2)}</pre>
                  </Box>
                </AccordionDetails>
              </Accordion>

              {selectedTestResult.output_data && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography>Output Data</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box sx={{ bgcolor: 'grey.100', p: 2, borderRadius: 1 }}>
                      <pre>{JSON.stringify(selectedTestResult.output_data, null, 2)}</pre>
                    </Box>
                  </AccordionDetails>
                </Accordion>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowTestResult(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default WorkflowTesting;