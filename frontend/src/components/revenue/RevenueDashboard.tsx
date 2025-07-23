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
  Button,
  Chip,
  LinearProgress,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  TrendingUp,
  AttachMoney,
  Payment,
  DateRange
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { useRevenue } from '../../hooks/useRevenue';

interface RevenueDashboardProps {
  developerId?: string;
}

const RevenueDashboard: React.FC<RevenueDashboardProps> = ({ developerId }) => {
  const { dashboard, loading, error, requestPayout } = useRevenue();
  const [payoutLoading, setPayoutLoading] = useState(false);

  const handleRequestPayout = async () => {
    setPayoutLoading(true);
    try {
      await requestPayout();
    } catch (error) {
      console.error('Failed to request payout:', error);
    } finally {
      setPayoutLoading(false);
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

  const canRequestPayout = dashboard?.developer_info?.pending_payout >= 50;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Revenue Dashboard
      </Typography>

      {/* Overview Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <AttachMoney color="primary" />
                <Box ml={2}>
                  <Typography variant="h6">
                    ${dashboard?.overview?.total_revenue?.toFixed(2) || '0.00'}
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
                <TrendingUp color="success" />
                <Box ml={2}>
                  <Typography variant="h6">
                    ${dashboard?.overview?.current_month_revenue?.toFixed(2) || '0.00'}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    This Month
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
                <Payment color="warning" />
                <Box ml={2}>
                  <Typography variant="h6">
                    ${dashboard?.overview?.pending_payout?.toFixed(2) || '0.00'}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Pending Payout
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
                    {dashboard?.overview?.total_sales || 0}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Total Sales
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Payout Information */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Payout Information
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="body2" color="textSecondary">
                Revenue Share Rate: {dashboard?.overview?.revenue_share_rate || 70}%
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Next Payout Date: {dashboard?.payment_info?.next_payout_date ? new Date(dashboard.payment_info.next_payout_date).toLocaleDateString() : 'TBD'}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Minimum Payout: ${dashboard?.payment_info?.minimum_payout || 50}
              </Typography>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box display="flex" alignItems="center" gap={2}>
                <Button
                  variant="contained"
                  color="primary"
                  disabled={!canRequestPayout || payoutLoading}
                  onClick={handleRequestPayout}
                  startIcon={payoutLoading ? <CircularProgress size={20} /> : <Payment />}
                >
                  Request Payout
                </Button>
                {!canRequestPayout && (
                  <Typography variant="body2" color="textSecondary">
                    Minimum ${dashboard?.payment_info?.minimum_payout || 50} required
                  </Typography>
                )}
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Daily Sales Chart */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Daily Sales (Last 30 Days)
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={dashboard?.daily_sales || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip formatter={(value: number) => [`$${value.toFixed(2)}`, 'Revenue']} />
              <Line type="monotone" dataKey="revenue" stroke="#1976d2" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Top Performing Plugins */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Top Performing Plugins
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Plugin Name</TableCell>
                  <TableCell align="right">Total Revenue</TableCell>
                  <TableCell align="right">Sales Count</TableCell>
                  <TableCell align="right">Performance</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {dashboard?.top_plugins?.map((plugin, index) => (
                  <TableRow key={plugin.plugin_id}>
                    <TableCell>{plugin.name}</TableCell>
                    <TableCell align="right">${plugin.total_revenue.toFixed(2)}</TableCell>
                    <TableCell align="right">{plugin.sales_count}</TableCell>
                    <TableCell align="right">
                      <Chip
                        label={index === 0 ? 'Best' : index === 1 ? 'Good' : 'Average'}
                        color={index === 0 ? 'success' : index === 1 ? 'primary' : 'default'}
                        size="small"
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

export default RevenueDashboard;