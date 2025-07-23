import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
  Paper,
  Chip,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  TrendingUp,
  People,
  AttachMoney,
  Assessment,
  Add as AddIcon,
  Refresh as RefreshIcon,
  FileDownload as ExportIcon
} from '@mui/icons-material';
import { useResellerTools } from '../../hooks/useResellerTools';
import { CustomerList } from './CustomerList';
import { LeadList } from './LeadList';
import { CommissionTracker } from './CommissionTracker';
import { PricingManager } from './PricingManager';
import { ResellerAnalytics } from './ResellerAnalytics';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index, ...other }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`reseller-tabpanel-${index}`}
      aria-labelledby={`reseller-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const ResellerDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  
  const {
    dashboard,
    loading,
    error,
    refreshDashboard,
    exportData
  } = useResellerTools();

  useEffect(() => {
    refreshDashboard();
  }, [refreshKey]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  const handleExport = async () => {
    try {
      await exportData('dashboard');
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  if (loading && !dashboard) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  const MetricCard = ({ 
    title, 
    value, 
    icon, 
    color = 'primary',
    subtitle 
  }: {
    title: string;
    value: string | number;
    icon: React.ReactNode;
    color?: 'primary' | 'secondary' | 'success' | 'warning';
    subtitle?: string;
  }) => (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography color="textSecondary" gutterBottom variant="body2">
              {title}
            </Typography>
            <Typography variant="h4" component="div" color={`${color}.main`}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="body2" color="textSecondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box color={`${color}.main`}>
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box display="flex" justifyContent="between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Reseller Dashboard
        </Typography>
        <Box>
          <Tooltip title="Refresh Data">
            <IconButton onClick={handleRefresh} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Export Data">
            <IconButton onClick={handleExport}>
              <ExportIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Metrics Cards */}
      {dashboard && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Total Leads"
              value={dashboard.total_leads}
              icon={<People fontSize="large" />}
              color="primary"
              subtitle={`${dashboard.qualified_leads} qualified`}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Active Customers"
              value={dashboard.active_customers}
              icon={<People fontSize="large" />}
              color="success"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Total Revenue"
              value={`$${dashboard.total_revenue?.toLocaleString() || '0'}`}
              icon={<AttachMoney fontSize="large" />}
              color="success"
              subtitle="All time"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              title="Pending Commissions"
              value={`$${dashboard.pending_commissions?.toLocaleString() || '0'}`}
              icon={<TrendingUp fontSize="large" />}
              color="warning"
            />
          </Grid>
        </Grid>
      )}

      {/* Performance Metrics */}
      {dashboard && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                Conversion Rate
              </Typography>
              <Typography variant="h3" color="primary.main">
                {dashboard.conversion_rate}%
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                Average Deal Size
              </Typography>
              <Typography variant="h3" color="success.main">
                ${dashboard.average_deal_size?.toLocaleString() || '0'}
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                Pipeline Value
              </Typography>
              <Typography variant="h3" color="warning.main">
                ${dashboard.pipeline_value?.toLocaleString() || '0'}
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Tabs */}
      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="Customers" />
          <Tab label="Leads" />
          <Tab label="Commissions" />
          <Tab label="Pricing" />
          <Tab label="Analytics" />
        </Tabs>

        <TabPanel value={activeTab} index={0}>
          <CustomerList />
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <LeadList />
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <CommissionTracker />
        </TabPanel>

        <TabPanel value={activeTab} index={3}>
          <PricingManager />
        </TabPanel>

        <TabPanel value={activeTab} index={4}>
          <ResellerAnalytics />
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default ResellerDashboard;