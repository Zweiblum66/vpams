import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  MenuItem,
  Button,
  Chip,
  Alert,
  CircularProgress,
  Tabs,
  Tab
} from '@mui/material';
import {
  TrendingUp,
  Assessment,
  FileDownload,
  DateRange
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { useRevenue } from '../../hooks/useRevenue';

interface SalesAnalyticsProps {
  developerId?: string;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

const SalesAnalytics: React.FC<SalesAnalyticsProps> = ({ developerId }) => {
  const { analytics, salesHistory, loading, error, generateTaxReport } = useRevenue();
  const [activeTab, setActiveTab] = useState(0);
  const [dateRange, setDateRange] = useState(30);
  const [pluginFilter, setPluginFilter] = useState('all');
  const [taxYear, setTaxYear] = useState(new Date().getFullYear());

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleDownloadTaxReport = async () => {
    try {
      await generateTaxReport(taxYear);
    } catch (error) {
      console.error('Failed to generate tax report:', error);
    }
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

  const TabPanel = ({ children, value, index }: { children: React.ReactNode; value: number; index: number }) => (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Sales Analytics
      </Typography>

      {/* Controls */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                select
                fullWidth
                label="Date Range"
                value={dateRange}
                onChange={(e) => setDateRange(Number(e.target.value))}
                size="small"
              >
                <MenuItem value={7}>Last 7 days</MenuItem>
                <MenuItem value={30}>Last 30 days</MenuItem>
                <MenuItem value={90}>Last 90 days</MenuItem>
                <MenuItem value={365}>Last year</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                select
                fullWidth
                label="Plugin Filter"
                value={pluginFilter}
                onChange={(e) => setPluginFilter(e.target.value)}
                size="small"
              >
                <MenuItem value="all">All Plugins</MenuItem>
                {analytics?.plugin_revenue?.map((plugin) => (
                  <MenuItem key={plugin.plugin_id} value={plugin.plugin_id}>
                    {plugin.plugin_name}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                select
                fullWidth
                label="Tax Year"
                value={taxYear}
                onChange={(e) => setTaxYear(Number(e.target.value))}
                size="small"
              >
                {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i).map(year => (
                  <MenuItem key={year} value={year}>{year}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Button
                variant="outlined"
                startIcon={<FileDownload />}
                onClick={handleDownloadTaxReport}
                fullWidth
              >
                Tax Report
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Analytics Summary */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <TrendingUp color="primary" />
                <Box ml={2}>
                  <Typography variant="h6">
                    {analytics?.summary?.total_plugins || 0}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Total Plugins
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
                <Assessment color="success" />
                <Box ml={2}>
                  <Typography variant="h6">
                    ${analytics?.summary?.total_revenue?.toFixed(2) || '0.00'}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Total Revenue
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
                <DateRange color="info" />
                <Box ml={2}>
                  <Typography variant="h6">
                    {analytics?.summary?.total_sales || 0}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Total Sales
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
                <TrendingUp color="warning" />
                <Box ml={2}>
                  <Typography variant="h6">
                    ${analytics?.summary?.avg_revenue_per_plugin?.toFixed(2) || '0.00'}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Avg per Plugin
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs for different analytics views */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={handleTabChange}>
            <Tab label="Revenue Trends" />
            <Tab label="Plugin Performance" />
            <Tab label="Payment Methods" />
            <Tab label="Sales History" />
          </Tabs>
        </Box>

        <TabPanel value={activeTab} index={0}>
          {/* Revenue Trends */}
          <Typography variant="h6" gutterBottom>
            Weekly Revenue Trend
          </Typography>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={analytics?.weekly_revenue || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" />
              <YAxis />
              <Tooltip formatter={(value: number) => [`$${value.toFixed(2)}`, 'Revenue']} />
              <Line type="monotone" dataKey="revenue" stroke="#1976d2" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          {/* Plugin Performance */}
          <Typography variant="h6" gutterBottom>
            Plugin Revenue Performance
          </Typography>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={analytics?.plugin_revenue || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="plugin_name" />
              <YAxis />
              <Tooltip formatter={(value: number) => [`$${value.toFixed(2)}`, 'Revenue']} />
              <Bar dataKey="total_revenue" fill="#1976d2" />
            </BarChart>
          </ResponsiveContainer>

          <TableContainer sx={{ mt: 3 }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Plugin Name</TableCell>
                  <TableCell align="right">Price</TableCell>
                  <TableCell align="right">Total Revenue</TableCell>
                  <TableCell align="right">Sales Count</TableCell>
                  <TableCell align="right">Avg Sale Price</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {analytics?.plugin_revenue?.map((plugin) => (
                  <TableRow key={plugin.plugin_id}>
                    <TableCell>{plugin.plugin_name}</TableCell>
                    <TableCell align="right">${plugin.plugin_price.toFixed(2)}</TableCell>
                    <TableCell align="right">${plugin.total_revenue.toFixed(2)}</TableCell>
                    <TableCell align="right">{plugin.sales_count}</TableCell>
                    <TableCell align="right">${plugin.avg_sale_price.toFixed(2)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          {/* Payment Methods */}
          <Typography variant="h6" gutterBottom>
            Revenue by Payment Method
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={analytics?.payment_methods || []}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ payment_method, percent }) => `${payment_method} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="total_revenue"
                  >
                    {analytics?.payment_methods?.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => [`$${value.toFixed(2)}`, 'Revenue']} />
                </PieChart>
              </ResponsiveContainer>
            </Grid>
            <Grid item xs={12} md={6}>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Payment Method</TableCell>
                      <TableCell align="right">Revenue</TableCell>
                      <TableCell align="right">Sales</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {analytics?.payment_methods?.map((method) => (
                      <TableRow key={method.payment_method}>
                        <TableCell>{method.payment_method}</TableCell>
                        <TableCell align="right">${method.total_revenue.toFixed(2)}</TableCell>
                        <TableCell align="right">{method.sales_count}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={activeTab} index={3}>
          {/* Sales History */}
          <Typography variant="h6" gutterBottom>
            Recent Sales History
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Sale ID</TableCell>
                  <TableCell>Plugin</TableCell>
                  <TableCell align="right">Sale Price</TableCell>
                  <TableCell align="right">Your Share</TableCell>
                  <TableCell>Payment Method</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {salesHistory?.slice(0, 20).map((sale) => (
                  <TableRow key={sale.sale_id}>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">
                        {sale.sale_id.slice(0, 8)}...
                      </Typography>
                    </TableCell>
                    <TableCell>{sale.plugin_name}</TableCell>
                    <TableCell align="right">${sale.sale_price.toFixed(2)}</TableCell>
                    <TableCell align="right">
                      <Typography color="success.main" fontWeight="bold">
                        ${sale.revenue_share_amount.toFixed(2)}
                      </Typography>
                    </TableCell>
                    <TableCell>{sale.payment_method}</TableCell>
                    <TableCell>{new Date(sale.sale_date).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Chip
                        label={sale.status}
                        color={sale.status === 'completed' ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>
      </Card>
    </Box>
  );
};

export default SalesAnalytics;