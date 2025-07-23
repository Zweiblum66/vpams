import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Alert,
  CircularProgress,
  Pagination
} from '@mui/material';
import {
  Payment,
  Add,
  Edit,
  Verified,
  Warning
} from '@mui/icons-material';
import { useRevenue } from '../../hooks/useRevenue';

interface PayoutManagementProps {
  developerId?: string;
}

const PayoutManagement: React.FC<PayoutManagementProps> = ({ developerId }) => {
  const { payouts, paymentMethods, loading, error, addPaymentMethod, requestPayout } = useRevenue();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('all');
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [newPaymentMethod, setNewPaymentMethod] = useState({
    method_type: 'paypal',
    payment_details: {},
    is_primary: false
  });

  const handleAddPaymentMethod = async () => {
    try {
      await addPaymentMethod(newPaymentMethod);
      setPaymentDialogOpen(false);
      setNewPaymentMethod({
        method_type: 'paypal',
        payment_details: {},
        is_primary: false
      });
    } catch (error) {
      console.error('Failed to add payment method:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'pending': return 'warning';
      case 'processing': return 'info';
      case 'failed': return 'error';
      case 'cancelled': return 'default';
      default: return 'default';
    }
  };

  const filteredPayouts = payouts?.filter(payout => 
    statusFilter === 'all' || payout.status === statusFilter
  ) || [];

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

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Payout Management
      </Typography>

      {/* Payment Methods Section */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Payment Methods</Typography>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setPaymentDialogOpen(true)}
            >
              Add Payment Method
            </Button>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Method Type</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Primary</TableCell>
                  <TableCell>Added</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {paymentMethods?.map((method) => (
                  <TableRow key={method.id}>
                    <TableCell>
                      <Box display="flex" alignItems="center">
                        <Payment sx={{ mr: 1 }} />
                        {method.method_type.charAt(0).toUpperCase() + method.method_type.slice(1)}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        icon={method.is_verified ? <Verified /> : <Warning />}
                        label={method.verification_status}
                        color={method.is_verified ? 'success' : 'warning'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {method.is_primary && (
                        <Chip label="Primary" color="primary" size="small" />
                      )}
                    </TableCell>
                    <TableCell>
                      {new Date(method.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Button size="small" startIcon={<Edit />}>
                        Edit
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {(!paymentMethods || paymentMethods.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography variant="body2" color="textSecondary">
                        No payment methods configured. Add one to receive payouts.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Payout History Section */}
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Payout History</Typography>
            <Box display="flex" gap={2}>
              <TextField
                select
                label="Status Filter"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                size="small"
                sx={{ minWidth: 120 }}
              >
                <MenuItem value="all">All</MenuItem>
                <MenuItem value="pending">Pending</MenuItem>
                <MenuItem value="processing">Processing</MenuItem>
                <MenuItem value="completed">Completed</MenuItem>
                <MenuItem value="failed">Failed</MenuItem>
                <MenuItem value="cancelled">Cancelled</MenuItem>
              </TextField>
            </Box>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Payout ID</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell>Method</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Requested</TableCell>
                  <TableCell>Processed</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredPayouts.map((payout) => (
                  <TableRow key={payout.id}>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">
                        {payout.id.slice(0, 8)}...
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" fontWeight="bold">
                        ${payout.amount.toFixed(2)} {payout.currency}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {payout.payout_method.charAt(0).toUpperCase() + payout.payout_method.slice(1)}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={payout.status}
                        color={getStatusColor(payout.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {new Date(payout.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {payout.processed_at ? 
                        new Date(payout.processed_at).toLocaleDateString() : 
                        '-'
                      }
                    </TableCell>
                  </TableRow>
                ))}
                {filteredPayouts.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="textSecondary">
                        No payouts found.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {filteredPayouts.length > 0 && (
            <Box display="flex" justifyContent="center" mt={2}>
              <Pagination
                count={Math.ceil(filteredPayouts.length / 10)}
                page={page}
                onChange={(e, value) => setPage(value)}
              />
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Add Payment Method Dialog */}
      <Dialog open={paymentDialogOpen} onClose={() => setPaymentDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Payment Method</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <TextField
              select
              fullWidth
              label="Payment Method Type"
              value={newPaymentMethod.method_type}
              onChange={(e) => setNewPaymentMethod(prev => ({ ...prev, method_type: e.target.value }))}
              sx={{ mb: 2 }}
            >
              <MenuItem value="paypal">PayPal</MenuItem>
              <MenuItem value="bank_transfer">Bank Transfer</MenuItem>
              <MenuItem value="stripe">Stripe</MenuItem>
            </TextField>

            {newPaymentMethod.method_type === 'paypal' && (
              <TextField
                fullWidth
                label="PayPal Email"
                type="email"
                value={newPaymentMethod.payment_details.email || ''}
                onChange={(e) => setNewPaymentMethod(prev => ({
                  ...prev,
                  payment_details: { ...prev.payment_details, email: e.target.value }
                }))}
                sx={{ mb: 2 }}
              />
            )}

            {newPaymentMethod.method_type === 'bank_transfer' && (
              <>
                <TextField
                  fullWidth
                  label="Account Number"
                  value={newPaymentMethod.payment_details.account_number || ''}
                  onChange={(e) => setNewPaymentMethod(prev => ({
                    ...prev,
                    payment_details: { ...prev.payment_details, account_number: e.target.value }
                  }))}
                  sx={{ mb: 2 }}
                />
                <TextField
                  fullWidth
                  label="Routing Number"
                  value={newPaymentMethod.payment_details.routing_number || ''}
                  onChange={(e) => setNewPaymentMethod(prev => ({
                    ...prev,
                    payment_details: { ...prev.payment_details, routing_number: e.target.value }
                  }))}
                  sx={{ mb: 2 }}
                />
              </>
            )}

            {newPaymentMethod.method_type === 'stripe' && (
              <TextField
                fullWidth
                label="Stripe Account ID"
                value={newPaymentMethod.payment_details.account_id || ''}
                onChange={(e) => setNewPaymentMethod(prev => ({
                  ...prev,
                  payment_details: { ...prev.payment_details, account_id: e.target.value }
                }))}
                sx={{ mb: 2 }}
              />
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPaymentDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddPaymentMethod}>
            Add Payment Method
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PayoutManagement;