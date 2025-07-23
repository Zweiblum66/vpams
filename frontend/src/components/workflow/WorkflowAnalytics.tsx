import React, { useState, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tabs,
  Tab,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Avatar,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
} from '@mui/material';
import {
  Timeline,
  TrendingUp,
  TrendingDown,
  Speed,
  CheckCircle,
  Error,
  Warning,
  PlayArrow,
  Pause,
  Stop,
  Schedule,
  Memory,
  Storage,
  Assessment,
  PieChart,
  BarChart,
  ShowChart,
  Visibility,
  Person,
  Category,
  AccessTime,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  ResponsiveContainer,
  BarChart as RechartsBarChart,
  Bar,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Area,
  AreaChart,
} from 'recharts';

interface WorkflowAnalyticsProps {
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
    id={`analytics-tabpanel-${index}`}
    aria-labelledby={`analytics-tab-${index}`}
  >
    {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
  </div>
);

// Mock data for demonstration
const mockExecutionData = [
  { date: '2024-01-01', executions: 45, success: 42, failed: 3, avgDuration: 120 },
  { date: '2024-01-02', executions: 52, success: 48, failed: 4, avgDuration: 115 },
  { date: '2024-01-03', executions: 38, success: 36, failed: 2, avgDuration: 125 },
  { date: '2024-01-04', executions: 67, success: 61, failed: 6, avgDuration: 110 },
  { date: '2024-01-05', executions: 74, success: 70, failed: 4, avgDuration: 108 },
  { date: '2024-01-06', executions: 83, success: 79, failed: 4, avgDuration: 102 },
  { date: '2024-01-07', executions: 91, success: 88, failed: 3, avgDuration: 98 },
];

const mockNodePerformance = [
  { nodeId: 'video-transcode', name: 'Video Transcode', avgDuration: 45, executions: 234, errorRate: 2.1 },
  { nodeId: 'audio-extract', name: 'Audio Extract', avgDuration: 12, executions: 187, errorRate: 0.5 },
  { nodeId: 'thumbnail-gen', name: 'Thumbnail Generate', avgDuration: 8, executions: 298, errorRate: 1.2 },
  { nodeId: 'metadata-extract', name: 'Metadata Extract', avgDuration: 3, executions: 312, errorRate: 0.8 },
  { nodeId: 'quality-check', name: 'Quality Check', avgDuration: 15, executions: 156, errorRate: 4.5 },
];

const mockResourceUsage = [
  { time: '00:00', cpu: 45, memory: 62, disk: 34 },
  { time: '04:00', cpu: 52, memory: 58, disk: 38 },
  { time: '08:00', cpu: 78, memory: 74, disk: 45 },
  { time: '12:00', cpu: 85, memory: 81, disk: 52 },
  { time: '16:00', cpu: 67, memory: 69, disk: 41 },
  { time: '20:00', cpu: 43, memory: 51, disk: 35 },
];

const mockErrorTypes = [
  { name: 'Network Timeout', count: 12, percentage: 35 },
  { name: 'File Not Found', count: 8, percentage: 24 },
  { name: 'Insufficient Memory', count: 7, percentage: 21 },
  { name: 'Permission Denied', count: 4, percentage: 12 },
  { name: 'Other', count: 3, percentage: 8 },
];

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

const WorkflowAnalytics: React.FC<WorkflowAnalyticsProps> = ({ workflowId }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [timeRange, setTimeRange] = useState('7d');
  const [selectedMetric, setSelectedMetric] = useState('executions');
  const [showNodeDetails, setShowNodeDetails] = useState(false);
  const [selectedNode, setSelectedNode] = useState<any>(null);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const totalExecutions = useMemo(() => 
    mockExecutionData.reduce((sum, day) => sum + day.executions, 0)
  , []);

  const totalSuccess = useMemo(() => 
    mockExecutionData.reduce((sum, day) => sum + day.success, 0)
  , []);

  const totalFailed = useMemo(() => 
    mockExecutionData.reduce((sum, day) => sum + day.failed, 0)
  , []);

  const averageDuration = useMemo(() => 
    mockExecutionData.reduce((sum, day) => sum + day.avgDuration, 0) / mockExecutionData.length
  , []);

  const successRate = useMemo(() => 
    (totalSuccess / totalExecutions * 100).toFixed(1)
  , [totalSuccess, totalExecutions]);

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const renderOverviewTab = () => (
    <Grid container spacing={3}>
      {/* Key Metrics */}
      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <PlayArrow color="primary" />
              <Typography variant="h6" sx={{ ml: 1 }}>
                Total Executions
              </Typography>
            </Box>
            <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
              {totalExecutions}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
              <TrendingUp color="success" fontSize="small" />
              <Typography variant="body2" color="success.main" sx={{ ml: 0.5 }}>
                +12% from last week
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <CheckCircle color="success" />
              <Typography variant="h6" sx={{ ml: 1 }}>
                Success Rate
              </Typography>
            </Box>
            <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
              {successRate}%
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
              <TrendingUp color="success" fontSize="small" />
              <Typography variant="body2" color="success.main" sx={{ ml: 0.5 }}>
                +2.1% from last week
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Speed color="info" />
              <Typography variant="h6" sx={{ ml: 1 }}>
                Avg Duration
              </Typography>
            </Box>
            <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
              {formatDuration(Math.round(averageDuration))}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
              <TrendingDown color="success" fontSize="small" />
              <Typography variant="body2" color="success.main" sx={{ ml: 0.5 }}>
                -8s from last week
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Error color="error" />
              <Typography variant="h6" sx={{ ml: 1 }}>
                Failed Executions
              </Typography>
            </Box>
            <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
              {totalFailed}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
              <TrendingDown color="success" fontSize="small" />
              <Typography variant="body2" color="success.main" sx={{ ml: 0.5 }}>
                -3 from last week
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Execution Trends */}
      <Grid item xs={12} md={8}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Execution Trends</Typography>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Time Range</InputLabel>
                <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)} label="Time Range">
                  <MenuItem value="1d">Last 24 Hours</MenuItem>
                  <MenuItem value="7d">Last 7 Days</MenuItem>
                  <MenuItem value="30d">Last 30 Days</MenuItem>
                  <MenuItem value="90d">Last 90 Days</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={mockExecutionData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <ChartTooltip />
                <Area type="monotone" dataKey="executions" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
                <Area type="monotone" dataKey="success" stroke="#82ca9d" fill="#82ca9d" fillOpacity={0.6} />
                <Area type="monotone" dataKey="failed" stroke="#ffc658" fill="#ffc658" fillOpacity={0.6} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Error Distribution */}
      <Grid item xs={12} md={4}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Error Distribution</Typography>
            <ResponsiveContainer width="100%" height={300}>
              <RechartsPieChart>
                <Pie
                  data={mockErrorTypes}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percentage }) => `${name} ${percentage}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {mockErrorTypes.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <ChartTooltip />
              </RechartsPieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Recent Executions */}
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Recent Executions</Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Execution ID</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Duration</TableCell>
                    <TableCell>Started</TableCell>
                    <TableCell>Triggered By</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Array.from({ length: 5 }).map((_, index) => (
                    <TableRow key={index}>
                      <TableCell>WF-{(Date.now() - index * 30000).toString().slice(-8)}</TableCell>
                      <TableCell>
                        <Chip
                          label={index % 4 === 0 ? 'Failed' : 'Success'}
                          color={index % 4 === 0 ? 'error' : 'success'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{formatDuration(Math.floor(Math.random() * 120) + 30)}</TableCell>
                      <TableCell>{new Date(Date.now() - index * 30000).toLocaleString()}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Avatar sx={{ width: 24, height: 24, mr: 1 }}>
                            <Person fontSize="small" />
                          </Avatar>
                          User {index + 1}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Tooltip title="View Details">
                          <IconButton size="small">
                            <Visibility />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderPerformanceTab = () => (
    <Grid container spacing={3}>
      {/* Node Performance */}
      <Grid item xs={12} md={8}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Node Performance</Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Node</TableCell>
                    <TableCell>Avg Duration</TableCell>
                    <TableCell>Executions</TableCell>
                    <TableCell>Error Rate</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {mockNodePerformance.map((node) => (
                    <TableRow key={node.nodeId}>
                      <TableCell>{node.name}</TableCell>
                      <TableCell>{formatDuration(node.avgDuration)}</TableCell>
                      <TableCell>{node.executions}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <LinearProgress
                            variant="determinate"
                            value={node.errorRate}
                            sx={{ width: 60, mr: 1 }}
                            color={node.errorRate > 3 ? 'error' : node.errorRate > 1 ? 'warning' : 'success'}
                          />
                          <Typography variant="body2">{node.errorRate}%</Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Tooltip title="View Details">
                          <IconButton
                            size="small"
                            onClick={() => {
                              setSelectedNode(node);
                              setShowNodeDetails(true);
                            }}
                          >
                            <Visibility />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Resource Usage */}
      <Grid item xs={12} md={4}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Resource Usage</Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={mockResourceUsage}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <ChartTooltip />
                <Line type="monotone" dataKey="cpu" stroke="#8884d8" name="CPU %" />
                <Line type="monotone" dataKey="memory" stroke="#82ca9d" name="Memory %" />
                <Line type="monotone" dataKey="disk" stroke="#ffc658" name="Disk %" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Duration Trends */}
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Duration Trends</Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={mockExecutionData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <ChartTooltip />
                <Line type="monotone" dataKey="avgDuration" stroke="#8884d8" name="Avg Duration (s)" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderUsageTab = () => (
    <Grid container spacing={3}>
      {/* Usage Statistics */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Usage Statistics</Typography>
            <List>
              <ListItem>
                <ListItemIcon>
                  <Person />
                </ListItemIcon>
                <ListItemText 
                  primary="Total Users" 
                  secondary="23 active users this week"
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <Category />
                </ListItemIcon>
                <ListItemText 
                  primary="Most Used Category" 
                  secondary="Media Processing (67% of executions)"
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <AccessTime />
                </ListItemIcon>
                <ListItemText 
                  primary="Peak Hours" 
                  secondary="2:00 PM - 4:00 PM (UTC)"
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <Assessment />
                </ListItemIcon>
                <ListItemText 
                  primary="Efficiency Score" 
                  secondary="87% (Excellent)"
                />
              </ListItem>
            </List>
          </CardContent>
        </Card>
      </Grid>

      {/* Execution Pattern */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Execution Pattern</Typography>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsBarChart data={mockExecutionData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <ChartTooltip />
                <Bar dataKey="executions" fill="#8884d8" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Top Performing Workflows */}
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Top Performing Workflows</Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Workflow Name</TableCell>
                    <TableCell>Executions</TableCell>
                    <TableCell>Success Rate</TableCell>
                    <TableCell>Avg Duration</TableCell>
                    <TableCell>Last Used</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Array.from({ length: 5 }).map((_, index) => (
                    <TableRow key={index}>
                      <TableCell>Media Processing Workflow {index + 1}</TableCell>
                      <TableCell>{Math.floor(Math.random() * 100) + 50}</TableCell>
                      <TableCell>{(Math.random() * 10 + 90).toFixed(1)}%</TableCell>
                      <TableCell>{formatDuration(Math.floor(Math.random() * 120) + 30)}</TableCell>
                      <TableCell>{new Date(Date.now() - index * 3600000).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  return (
    <Box sx={{ width: '100%' }}>
      <Tabs value={activeTab} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tab label="Overview" />
        <Tab label="Performance" />
        <Tab label="Usage" />
        <Tab label="Alerts" />
      </Tabs>

      <TabPanel value={activeTab} index={0}>
        {renderOverviewTab()}
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        {renderPerformanceTab()}
      </TabPanel>

      <TabPanel value={activeTab} index={2}>
        {renderUsageTab()}
      </TabPanel>

      <TabPanel value={activeTab} index={3}>
        <Alert severity="info" sx={{ mb: 2 }}>
          Configure alerts to be notified when workflows exceed performance thresholds.
        </Alert>
        <Typography variant="body1">
          Alerts functionality will be implemented in a future release.
        </Typography>
      </TabPanel>

      {/* Node Details Dialog */}
      <Dialog
        open={showNodeDetails}
        onClose={() => setShowNodeDetails(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Node Performance Details
          {selectedNode && ` - ${selectedNode.name}`}
        </DialogTitle>
        <DialogContent>
          {selectedNode && (
            <Box>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6">Performance Metrics</Typography>
                  <Typography variant="body2">
                    Average Duration: {formatDuration(selectedNode.avgDuration)}
                  </Typography>
                  <Typography variant="body2">
                    Total Executions: {selectedNode.executions}
                  </Typography>
                  <Typography variant="body2">
                    Error Rate: {selectedNode.errorRate}%
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6">Recommendations</Typography>
                  <Typography variant="body2">
                    {selectedNode.errorRate > 3 
                      ? "Consider optimizing this node as it has a high error rate."
                      : "This node is performing well."}
                  </Typography>
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowNodeDetails(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default WorkflowAnalytics;