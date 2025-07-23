import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Box,
  Typography,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  IconButton,
  Divider,
  List,
  ListItem,
  ListItemText,
  Switch,
  FormControlLabel,
  TextField,
  Tab,
  Tabs,
  Alert,
} from '@mui/material';
import {
  ExpandMore,
  Close,
  DeleteOutline,
  DownloadOutlined,
  Memory,
  Speed,
  BugReport,
  Settings,
} from '@mui/icons-material';
import { logger, LogLevel } from '../utils/logger';
import { performanceMonitor } from '../utils/performance';
import { useAppSelector } from '../store';

interface DebugPanelProps {
  open: boolean;
  onClose: () => void;
}

const DebugPanel: React.FC<DebugPanelProps> = ({ open, onClose }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [logs, setLogs] = useState<any[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<any[]>([]);
  const [memoryUsage, setMemoryUsage] = useState<any>(null);
  const [logLevel, setLogLevel] = useState<LogLevel>(LogLevel.INFO);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  
  const authState = useAppSelector(state => state.auth);
  const uiState = useAppSelector(state => state.ui);

  // Refresh data periodically
  useEffect(() => {
    const refreshData = () => {
      setLogs(logger.getAllStoredLogs());
      setPerformanceMetrics(performanceMonitor.getMetrics());
      setMemoryUsage(performanceMonitor.getMemoryUsage());
    };

    refreshData();

    if (autoRefresh) {
      const interval = setInterval(refreshData, 2000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleLogLevelChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const level = parseInt(event.target.value) as LogLevel;
    setLogLevel(level);
    logger.setLevel(level);
  };

  const handleClearLogs = () => {
    logger.clearLogs();
    setLogs([]);
  };

  const handleDownloadLogs = () => {
    const logData = logger.exportLogs();
    const blob = new Blob([logData], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mams-logs-${new Date().toISOString()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleClearMetrics = () => {
    performanceMonitor.clearMetrics();
    setPerformanceMetrics([]);
  };

  const filteredLogs = logs.filter(log => 
    log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
    JSON.stringify(log.context).toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getLogLevelColor = (level: LogLevel) => {
    switch (level) {
      case LogLevel.DEBUG: return 'default';
      case LogLevel.INFO: return 'primary';
      case LogLevel.WARN: return 'warning';
      case LogLevel.ERROR: return 'error';
      case LogLevel.FATAL: return 'error';
      default: return 'default';
    }
  };

  const getLogLevelName = (level: LogLevel) => {
    return LogLevel[level];
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: { width: 500, maxWidth: '90vw' }
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 2 }}>
        <Typography variant="h6">Debug Panel</Typography>
        <IconButton onClick={onClose}>
          <Close />
        </IconButton>
      </Box>
      
      <Divider />

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={handleTabChange} variant="scrollable">
          <Tab label="Logs" icon={<BugReport />} />
          <Tab label="Performance" icon={<Speed />} />
          <Tab label="Memory" icon={<Memory />} />
          <Tab label="State" icon={<Settings />} />
        </Tabs>
      </Box>

      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        {/* Logs Tab */}
        {activeTab === 0 && (
          <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ mb: 2 }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                sx={{ mb: 2 }}
              />
              
              <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                <Button size="small" onClick={handleClearLogs} startIcon={<DeleteOutline />}>
                  Clear
                </Button>
                <Button size="small" onClick={handleDownloadLogs} startIcon={<DownloadOutlined />}>
                  Download
                </Button>
                <FormControlLabel
                  control={
                    <Switch
                      checked={autoRefresh}
                      onChange={(e) => setAutoRefresh(e.target.checked)}
                      size="small"
                    />
                  }
                  label="Auto Refresh"
                />
              </Box>

              <TextField
                select
                size="small"
                label="Log Level"
                value={logLevel}
                onChange={handleLogLevelChange}
                SelectProps={{ native: true }}
              >
                <option value={LogLevel.DEBUG}>Debug</option>
                <option value={LogLevel.INFO}>Info</option>
                <option value={LogLevel.WARN}>Warn</option>
                <option value={LogLevel.ERROR}>Error</option>
                <option value={LogLevel.FATAL}>Fatal</option>
              </TextField>
            </Box>

            <Box sx={{ flex: 1, overflow: 'auto' }}>
              <List dense>
                {filteredLogs.length === 0 ? (
                  <ListItem>
                    <ListItemText primary="No logs found" />
                  </ListItem>
                ) : (
                  filteredLogs.map((log, index) => (
                    <ListItem key={index} divider>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Chip
                              label={getLogLevelName(log.level)}
                              color={getLogLevelColor(log.level)}
                              size="small"
                            />
                            <Typography variant="body2">{log.message}</Typography>
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography variant="caption" color="text.secondary">
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </Typography>
                            {log.context && (
                              <Typography variant="caption" component="pre" sx={{ fontSize: '0.7rem' }}>
                                {JSON.stringify(log.context, null, 2)}
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    </ListItem>
                  ))
                )}
              </List>
            </Box>
          </Box>
        )}

        {/* Performance Tab */}
        {activeTab === 1 && (
          <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ mb: 2, display: 'flex', gap: 1 }}>
              <Button size="small" onClick={handleClearMetrics} startIcon={<DeleteOutline />}>
                Clear Metrics
              </Button>
            </Box>

            <Box sx={{ flex: 1, overflow: 'auto' }}>
              {performanceMetrics.length === 0 ? (
                <Typography>No performance metrics available</Typography>
              ) : (
                performanceMetrics.map((metric, index) => (
                  <Accordion key={index}>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Typography variant="subtitle2">{metric.name}</Typography>
                      {metric.duration && (
                        <Chip
                          label={`${metric.duration.toFixed(2)}ms`}
                          size="small"
                          color={metric.duration > 100 ? 'warning' : 'default'}
                          sx={{ ml: 1 }}
                        />
                      )}
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body2" component="pre">
                        {JSON.stringify(metric, null, 2)}
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                ))
              )}
            </Box>
          </Box>
        )}

        {/* Memory Tab */}
        {activeTab === 2 && (
          <Box sx={{ p: 2 }}>
            {memoryUsage ? (
              <Box>
                <Typography variant="h6" gutterBottom>Memory Usage</Typography>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    Used: {(memoryUsage.usedJSHeapSize / 1024 / 1024).toFixed(2)} MB
                  </Typography>
                  <Typography variant="body2">
                    Total: {(memoryUsage.totalJSHeapSize / 1024 / 1024).toFixed(2)} MB
                  </Typography>
                  <Typography variant="body2">
                    Limit: {(memoryUsage.jsHeapSizeLimit / 1024 / 1024).toFixed(2)} MB
                  </Typography>
                  <Typography variant="body2">
                    Usage: {memoryUsage.usedPercentage.toFixed(2)}%
                  </Typography>
                </Box>
                
                {memoryUsage.usedPercentage > 80 && (
                  <Alert severity="warning">
                    Memory usage is high. Consider optimizing your application.
                  </Alert>
                )}
              </Box>
            ) : (
              <Typography>Memory information not available</Typography>
            )}
          </Box>
        )}

        {/* State Tab */}
        {activeTab === 3 && (
          <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle2">Auth State</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="body2" component="pre">
                  {JSON.stringify(authState, null, 2)}
                </Typography>
              </AccordionDetails>
            </Accordion>

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle2">UI State</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="body2" component="pre">
                  {JSON.stringify(uiState, null, 2)}
                </Typography>
              </AccordionDetails>
            </Accordion>
          </Box>
        )}
      </Box>
    </Drawer>
  );
};

export default DebugPanel;