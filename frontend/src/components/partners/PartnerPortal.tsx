import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Tabs,
  Tab,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  CircularProgress,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  LinearProgress
} from '@mui/material';
import {
  Dashboard,
  Business,
  People,
  Assignment,
  TrendingUp,
  School,
  Description,
  Handshake,
  Star,
  CheckCircle,
  Schedule,
  AttachMoney
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { usePartnerPortal } from '../../hooks/usePartnerPortal';

interface PartnerPortalProps {
  partnerId?: string;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

const PartnerPortal: React.FC<PartnerPortalProps> = ({ partnerId }) => {
  const { 
    dashboard, 
    partnerInfo, 
    analytics, 
    loading, 
    error, 
    fetchDashboard,
    fetchAnalytics
  } = usePartnerPortal();
  
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    if (partnerId) {
      fetchDashboard(partnerId);
      fetchAnalytics(partnerId);
    }
  }, [partnerId, fetchDashboard, fetchAnalytics]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'pending': return 'warning';
      case 'suspended': return 'error';
      default: return 'default';
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'platinum': return '#E5E4E2';
      case 'gold': return '#FFD700';
      case 'silver': return '#C0C0C0';
      case 'bronze': return '#CD7F32';
      default: return '#Gray';
    }
  };

  const TabPanel = ({ children, value, index }: { children: React.ReactNode; value: number; index: number }) => (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={8}>
          <Typography variant="h4" gutterBottom>
            Partner Portal
          </Typography>
          {partnerInfo && (
            <Box display="flex" alignItems="center" gap={2}>
              <Avatar sx={{ bgcolor: getTierColor(partnerInfo.partner_tier) }}>
                <Business />
              </Avatar>
              <Box>
                <Typography variant="h6">{partnerInfo.company_name}</Typography>
                <Box display="flex" gap={1}>
                  <Chip 
                    label={partnerInfo.status} 
                    color={getStatusColor(partnerInfo.status)}
                    size="small"
                  />
                  <Chip 
                    label={`${partnerInfo.partner_tier} Partner`}
                    style={{ backgroundColor: getTierColor(partnerInfo.partner_tier), color: 'white' }}
                    size="small"
                  />
                  <Chip 
                    label={partnerInfo.partner_type}
                    variant="outlined"
                    size="small"
                  />
                </Box>
              </Box>
            </Box>
          )}
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>
              <Box display="flex" flexDirection="column" gap={1}>
                <Button variant="outlined" startIcon={<Assignment />} fullWidth>
                  Submit Application
                </Button>
                <Button variant="outlined" startIcon={<Description />} fullWidth>
                  Access Resources
                </Button>
                <Button variant="outlined" startIcon={<School />} fullWidth>
                  View Training
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Statistics Cards */}
      {dashboard && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <Handshake color="primary" />
                  <Box ml={2}>
                    <Typography variant="h6">
                      {dashboard.statistics.deals.total}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Total Deals
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <AttachMoney color="success" />
                  <Box ml={2}>
                    <Typography variant="h6">
                      ${dashboard.statistics.deals.total_value.toLocaleString()}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Pipeline Value
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <TrendingUp color="info" />
                  <Box ml={2}>
                    <Typography variant="h6">
                      {dashboard.statistics.deals.win_rate.toFixed(1)}%
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Win Rate
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <School color="warning" />
                  <Box ml={2}>
                    <Typography variant="h6">
                      {dashboard.statistics.certifications.active}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Certifications
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Main Content Tabs */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={handleTabChange}>
            <Tab icon={<Dashboard />} label="Dashboard" />
            <Tab icon={<Handshake />} label="Deals" />
            <Tab icon={<People />} label="Contacts" />
            <Tab icon={<School />} label="Certifications" />
            <Tab icon={<TrendingUp />} label="Analytics" />
          </Tabs>
        </Box>

        <TabPanel value={activeTab} index={0}>
          {/* Dashboard Tab */}
          <Grid container spacing={3}>
            {/* Recent Activities */}
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                Recent Activities
              </Typography>
              <List>
                {dashboard?.recent_activities?.slice(0, 5).map((activity, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      <CheckCircle color="success" />
                    </ListItemIcon>
                    <ListItemText
                      primary={activity.title || activity.activity_type}
                      secondary={activity.description}
                    />
                  </ListItem>
                ))}
              </List>
            </Grid>

            {/* Performance Chart */}
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                Deal Pipeline
              </Typography>
              {analytics?.deal_trends && (
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={analytics.deal_trends}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip formatter={(value: number) => [`$${value.toLocaleString()}`, 'Value']} />
                    <Line type="monotone" dataKey="total_value" stroke="#1976d2" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          {/* Deals Tab */}
          <Typography variant="h6" gutterBottom>
            Active Deals
          </Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Deal Name</TableCell>
                  <TableCell>Customer</TableCell>
                  <TableCell align="right">Value</TableCell>
                  <TableCell>Stage</TableCell>
                  <TableCell align="right">Probability</TableCell>
                  <TableCell>Expected Close</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {dashboard?.active_deals?.map((deal) => (
                  <TableRow key={deal.id}>
                    <TableCell>{deal.deal_name}</TableCell>
                    <TableCell>{deal.customer_name}</TableCell>
                    <TableCell align="right">
                      ${deal.deal_value.toLocaleString()} {deal.currency}
                    </TableCell>
                    <TableCell>
                      <Chip label={deal.stage} size="small" />
                    </TableCell>
                    <TableCell align="right">
                      <Box display="flex" alignItems="center">
                        <LinearProgress 
                          variant="determinate" 
                          value={deal.probability} 
                          sx={{ width: 60, mr: 1 }} 
                        />
                        {deal.probability}%
                      </Box>
                    </TableCell>
                    <TableCell>
                      {deal.expected_close_date ? 
                        new Date(deal.expected_close_date).toLocaleDateString() : 
                        'TBD'
                      }
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          {/* Contacts Tab */}
          <Typography variant="h6" gutterBottom>
            Partner Contacts
          </Typography>
          <Typography color="textSecondary">
            Total Contacts: {dashboard?.contacts_count || 0}
          </Typography>
          <Typography variant="body2" sx={{ mt: 2 }}>
            Contact management functionality will be displayed here.
          </Typography>
        </TabPanel>

        <TabPanel value={activeTab} index={3}>
          {/* Certifications Tab */}
          <Typography variant="h6" gutterBottom>
            Certifications & Training
          </Typography>
          <Grid container spacing={2}>
            {dashboard?.certifications?.map((cert, index) => (
              <Grid item xs={12} md={6} key={index}>
                <Card>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="start">
                      <Box>
                        <Typography variant="h6">{cert.name}</Typography>
                        <Typography variant="body2" color="textSecondary">
                          {cert.type}
                        </Typography>
                      </Box>
                      <Chip
                        label={cert.status}
                        color={cert.status === 'completed' ? 'success' : 'warning'}
                        size="small"
                      />
                    </Box>
                    {cert.completion_date && (
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        Completed: {new Date(cert.completion_date).toLocaleDateString()}
                      </Typography>
                    )}
                    {cert.expiry_date && (
                      <Typography variant="body2" color="warning.main">
                        Expires: {new Date(cert.expiry_date).toLocaleDateString()}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </TabPanel>

        <TabPanel value={activeTab} index={4}>
          {/* Analytics Tab */}
          <Typography variant="h6" gutterBottom>
            Partner Analytics
          </Typography>
          <Grid container spacing={3}>
            {/* Performance Overview */}
            <Grid item xs={12} md={8}>
              <Typography variant="subtitle1" gutterBottom>
                Deal Performance Trends
              </Typography>
              {analytics?.deal_trends && (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={analytics.deal_trends}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="total_value" stroke="#1976d2" name="Deal Value" />
                    <Line type="monotone" dataKey="deal_count" stroke="#ff7300" name="Deal Count" />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </Grid>

            {/* Activity Distribution */}
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle1" gutterBottom>
                Activity Distribution
              </Typography>
              {analytics?.activity_trends && (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={Object.entries(analytics.activity_performance || {}).map(([key, value]) => ({
                        name: key,
                        value: value
                      }))}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {Object.entries(analytics.activity_performance || {}).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </Grid>

            {/* Key Metrics */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                Key Performance Indicators
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6">
                        {analytics?.deal_performance?.total_deals || 0}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Total Deals
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6">
                        ${(analytics?.deal_performance?.avg_deal_value || 0).toLocaleString()}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Avg Deal Size
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6">
                        ${(analytics?.deal_performance?.total_commission || 0).toLocaleString()}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Total Commission
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6">
                        {analytics?.resource_engagement?.total_downloads || 0}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Resource Downloads
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </TabPanel>
      </Card>
    </Box>
  );
};

export default PartnerPortal;