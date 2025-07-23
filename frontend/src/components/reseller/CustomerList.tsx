import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  Toolbar,
  Typography,
  Checkbox,
  IconButton,
  Tooltip,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Avatar
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Edit as EditIcon,
  Add as AddIcon,
  FilterList as FilterIcon,
  GetApp as ExportIcon,
  Email as EmailIcon,
  Phone as PhoneIcon,
  Business as BusinessIcon
} from '@mui/icons-material';
import { useResellerTools } from '../../hooks/useResellerTools';
import { CustomerForm } from './CustomerForm';

interface Customer {
  id: string;
  company_name: string;
  contact_name: string;
  email: string;
  phone?: string;
  status: 'prospect' | 'trial' | 'active' | 'suspended' | 'cancelled';
  industry?: string;
  contract_value: number;
  monthly_value: number;
  created_at: string;
  updated_at?: string;
}

interface HeadCell {
  id: keyof Customer;
  label: string;
  numeric: boolean;
}

const headCells: HeadCell[] = [
  { id: 'company_name', numeric: false, label: 'Company' },
  { id: 'contact_name', numeric: false, label: 'Contact' },
  { id: 'email', numeric: false, label: 'Email' },
  { id: 'status', numeric: false, label: 'Status' },
  { id: 'industry', numeric: false, label: 'Industry' },
  { id: 'contract_value', numeric: true, label: 'Contract Value' },
  { id: 'monthly_value', numeric: true, label: 'Monthly Value' },
  { id: 'created_at', numeric: false, label: 'Created' },
];

const statusColors = {
  prospect: 'default',
  trial: 'info',
  active: 'success',
  suspended: 'warning',
  cancelled: 'error'
} as const;

export const CustomerList: React.FC = () => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [orderBy, setOrderBy] = useState<keyof Customer>('created_at');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [selected, setSelected] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showForm, setShowForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [total, setTotal] = useState(0);

  const {
    getCustomers,
    createCustomer,
    updateCustomer,
    deleteCustomer,
    exportCustomers
  } = useResellerTools();

  useEffect(() => {
    loadCustomers();
  }, [page, rowsPerPage, orderBy, order, searchTerm, statusFilter]);

  const loadCustomers = async () => {
    setLoading(true);
    try {
      const params = {
        page: page + 1,
        limit: rowsPerPage,
        sort_by: orderBy,
        sort_order: order,
        search: searchTerm || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined
      };

      const response = await getCustomers(params);
      setCustomers(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to load customers:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRequestSort = (property: keyof Customer) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const handleSelectAllClick = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      const newSelected = customers.map((n) => n.id);
      setSelected(newSelected);
      return;
    }
    setSelected([]);
  };

  const handleClick = (id: string) => {
    const selectedIndex = selected.indexOf(id);
    let newSelected: string[] = [];

    if (selectedIndex === -1) {
      newSelected = newSelected.concat(selected, id);
    } else if (selectedIndex === 0) {
      newSelected = newSelected.concat(selected.slice(1));
    } else if (selectedIndex === selected.length - 1) {
      newSelected = newSelected.concat(selected.slice(0, -1));
    } else if (selectedIndex > 0) {
      newSelected = newSelected.concat(
        selected.slice(0, selectedIndex),
        selected.slice(selectedIndex + 1),
      );
    }

    setSelected(newSelected);
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleEdit = (customer: Customer) => {
    setEditingCustomer(customer);
    setShowForm(true);
  };

  const handleDelete = async (customerId: string) => {
    if (window.confirm('Are you sure you want to delete this customer?')) {
      try {
        await deleteCustomer(customerId);
        loadCustomers();
      } catch (error) {
        console.error('Failed to delete customer:', error);
      }
    }
  };

  const handleFormSubmit = async (customerData: any) => {
    try {
      if (editingCustomer) {
        await updateCustomer(editingCustomer.id, customerData);
      } else {
        await createCustomer(customerData);
      }
      setShowForm(false);
      setEditingCustomer(null);
      loadCustomers();
    } catch (error) {
      console.error('Failed to save customer:', error);
    }
  };

  const handleExport = async () => {
    try {
      await exportCustomers();
    } catch (error) {
      console.error('Failed to export customers:', error);
    }
  };

  const isSelected = (id: string) => selected.indexOf(id) !== -1;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ width: '100%', mb: 2 }}>
        <Toolbar
          sx={{
            pl: { sm: 2 },
            pr: { xs: 1, sm: 1 },
            ...(selected.length > 0 && {
              bgcolor: (theme) => theme.palette.action.selected,
            }),
          }}
        >
          {selected.length > 0 ? (
            <Typography
              sx={{ flex: '1 1 100%' }}
              color="inherit"
              variant="subtitle1"
              component="div"
            >
              {selected.length} selected
            </Typography>
          ) : (
            <Typography
              sx={{ flex: '1 1 100%' }}
              variant="h6"
              id="tableTitle"
              component="div"
            >
              Customers
            </Typography>
          )}

          {selected.length > 0 ? (
            <Tooltip title="Delete">
              <IconButton>
                <DeleteIcon />
              </IconButton>
            </Tooltip>
          ) : (
            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField
                size="small"
                placeholder="Search customers..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                sx={{ minWidth: 200 }}
              />
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Status</InputLabel>
                <Select
                  value={statusFilter}
                  label="Status"
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="prospect">Prospect</MenuItem>
                  <MenuItem value="trial">Trial</MenuItem>
                  <MenuItem value="active">Active</MenuItem>
                  <MenuItem value="suspended">Suspended</MenuItem>
                  <MenuItem value="cancelled">Cancelled</MenuItem>
                </Select>
              </FormControl>
              <Tooltip title="Export">
                <IconButton onClick={handleExport}>
                  <ExportIcon />
                </IconButton>
              </Tooltip>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => setShowForm(true)}
              >
                Add Customer
              </Button>
            </Box>
          )}
        </Toolbar>

        <TableContainer>
          <Table sx={{ minWidth: 750 }} aria-labelledby="tableTitle">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">
                  <Checkbox
                    color="primary"
                    indeterminate={selected.length > 0 && selected.length < customers.length}
                    checked={customers.length > 0 && selected.length === customers.length}
                    onChange={handleSelectAllClick}
                  />
                </TableCell>
                {headCells.map((headCell) => (
                  <TableCell
                    key={headCell.id}
                    align={headCell.numeric ? 'right' : 'left'}
                    sortDirection={orderBy === headCell.id ? order : false}
                  >
                    <TableSortLabel
                      active={orderBy === headCell.id}
                      direction={orderBy === headCell.id ? order : 'asc'}
                      onClick={() => handleRequestSort(headCell.id)}
                    >
                      {headCell.label}
                    </TableSortLabel>
                  </TableCell>
                ))}
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {customers.map((customer) => {
                const isItemSelected = isSelected(customer.id);
                return (
                  <TableRow
                    hover
                    onClick={() => handleClick(customer.id)}
                    role="checkbox"
                    aria-checked={isItemSelected}
                    tabIndex={-1}
                    key={customer.id}
                    selected={isItemSelected}
                  >
                    <TableCell padding="checkbox">
                      <Checkbox
                        color="primary"
                        checked={isItemSelected}
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Avatar sx={{ width: 32, height: 32 }}>
                          <BusinessIcon />
                        </Avatar>
                        <Box>
                          <Typography variant="body2" fontWeight="medium">
                            {customer.company_name}
                          </Typography>
                          {customer.industry && (
                            <Typography variant="caption" color="textSecondary">
                              {customer.industry}
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell>{customer.contact_name}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <EmailIcon fontSize="small" color="action" />
                        {customer.email}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={customer.status}
                        color={statusColors[customer.status]}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{customer.industry || '-'}</TableCell>
                    <TableCell align="right">
                      {formatCurrency(customer.contract_value)}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(customer.monthly_value)}
                    </TableCell>
                    <TableCell>{formatDate(customer.created_at)}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEdit(customer);
                        }}
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(customer.id);
                        }}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          rowsPerPageOptions={[10, 25, 50]}
          component="div"
          count={total}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>

      {/* Customer Form Dialog */}
      <Dialog
        open={showForm}
        onClose={() => {
          setShowForm(false);
          setEditingCustomer(null);
        }}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingCustomer ? 'Edit Customer' : 'Add New Customer'}
        </DialogTitle>
        <DialogContent>
          <CustomerForm
            customer={editingCustomer}
            onSubmit={handleFormSubmit}
            onCancel={() => {
              setShowForm(false);
              setEditingCustomer(null);
            }}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
};