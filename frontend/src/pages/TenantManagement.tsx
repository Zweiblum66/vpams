"""
Tenant Management Page - Main UI for managing tenants.

Provides comprehensive tenant management interface including:
- Tenant list with filtering and sorting
- Create/Edit/Delete tenants
- Domain management
- Configuration management
- Usage monitoring
"""

import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tab,
  Tabs,
  Grid,
  Card,
  CardContent,
  Tooltip,
  Alert,
  Skeleton,
  LinearProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Settings as SettingsIcon,
  Domain as DomainIcon,
  BarChart as UsageIcon,
  Refresh as RefreshIcon,
  Download as ExportIcon,
  Upload as ImportIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/PageHeader/PageHeader';
import {
  useGetTenantsQuery,
  useCreateTenantMutation,
  useUpdateTenantMutation,
  useDeleteTenantMutation,
  Tenant,
  TenantCreate,
} from '../store/api/tenantApi';

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
      id={`tenant-tabpanel-${index}`}
      aria-labelledby={`tenant-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function TenantManagement() {
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');

  // API hooks
  const { data: tenants, isLoading, refetch } = useGetTenantsQuery({
    status: statusFilter || undefined,
  });
  const [createTenant, { isLoading: isCreating }] = useCreateTenantMutation();
  const [updateTenant, { isLoading: isUpdating }] = useUpdateTenantMutation();
  const [deleteTenant, { isLoading: isDeleting }] = useDeleteTenantMutation();

  // Form state for create/edit
  const [formData, setFormData] = useState<TenantCreate>({
    name: '',
    subdomain: '',
    admin_email: '',
    plan: 'starter',
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleCreateTenant = async () => {
    try {
      await createTenant(formData).unwrap();
      setCreateDialogOpen(false);
      setFormData({ name: '', subdomain: '', admin_email: '', plan: 'starter' });
      refetch();
    } catch (error) {
      console.error('Failed to create tenant:', error);
    }
  };

  const handleDeleteTenant = async () => {
    if (!selectedTenant) return;
    
    try {
      await deleteTenant(selectedTenant.tenant_id).unwrap();
      setDeleteDialogOpen(false);
      setSelectedTenant(null);
      refetch();
    } catch (error) {
      console.error('Failed to delete tenant:', error);
    }
  };

  const navigateToTenantDetail = (tenantId: string, section?: string) => {
    navigate(`/tenants/${tenantId}${section ? `?section=${section}` : ''}`);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'suspended':
        return 'warning';
      case 'pending':
        return 'info';
      case 'deleted':
        return 'error';
      default:
        return 'default';
    }
  };

  const getPlanColor = (plan: string) => {
    switch (plan) {
      case 'enterprise':
        return 'error';
      case 'professional':
        return 'warning';
      case 'standard':
        return 'primary';
      case 'starter':
        return 'info';
      case 'free':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <PageHeader
        title="Tenant Management"
        subtitle="Manage multi-tenant instances and configurations"
        action={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create Tenant
          </Button>
        }
      />

      <Paper sx={{ width: '100%', mb: 2 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          aria-label="tenant management tabs"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="All Tenants" />
          <Tab label="Active" />
          <Tab label="Suspended" />
          <Tab label="Pending" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          {/* All Tenants View */}
          <TenantList
            tenants={tenants}
            isLoading={isLoading}
            onEdit={(tenant) => navigateToTenantDetail(tenant.tenant_id)}
            onDelete={(tenant) => {
              setSelectedTenant(tenant);
              setDeleteDialogOpen(true);
            }}
            onViewConfig={(tenant) => navigateToTenantDetail(tenant.tenant_id, 'config')}
            onViewDomains={(tenant) => navigateToTenantDetail(tenant.tenant_id, 'domains')}
            onViewUsage={(tenant) => navigateToTenantDetail(tenant.tenant_id, 'usage')}
            onRefresh={refetch}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {/* Active Tenants */}
          <TenantList
            tenants={tenants?.filter(t => t.status === 'active')}
            isLoading={isLoading}
            onEdit={(tenant) => navigateToTenantDetail(tenant.tenant_id)}
            onDelete={(tenant) => {
              setSelectedTenant(tenant);
              setDeleteDialogOpen(true);
            }}
            onViewConfig={(tenant) => navigateToTenantDetail(tenant.tenant_id, 'config')}
            onViewDomains={(tenant) => navigateToTenantDetail(tenant.tenant_id, 'domains')}
            onViewUsage={(tenant) => navigateToTenantDetail(tenant.tenant_id, 'usage')}
            onRefresh={refetch}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {/* Suspended Tenants */}
          <TenantList
            tenants={tenants?.filter(t => t.status === 'suspended')}
            isLoading={isLoading}
            onEdit={(tenant) => navigateToTenantDetail(tenant.tenant_id)}
            onDelete={(tenant) => {
              setSelectedTenant(tenant);
              setDeleteDialogOpen(true);
            }}
            onViewConfig={(tenant) => navigateToTenantDetail(tenant.tenant_id, 'config')}
            onViewDomains={(tenant) => navigateToTenantDetail(tenant.tenant_id, 'domains')}
            onViewUsage={(tenant) => navigateToTenantDetail(tenant.tenant_id, 'usage')}
            onRefresh={refetch}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          {/* Pending Tenants */}
          <TenantList
            tenants={tenants?.filter(t => t.status === 'pending')}
            isLoading={isLoading}
            onEdit={(tenant) => navigateToTenantDetail(tenant.tenant_id)}
            onDelete={(tenant) => {
              setSelectedTenant(tenant);
              setDeleteDialogOpen(true);
            }}
            onViewConfig={(tenant) => navigateToTenantDetail(tenant.tenant_id, 'config')}
            onViewDomains={(tenant) => navigateToTenantDetail(tenant.tenant_id, 'domains')}
            onViewUsage={(tenant) => navigateToTenantDetail(tenant.tenant_id, 'usage')}
            onRefresh={refetch}
          />
        </TabPanel>
      </Paper>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Tenants
              </Typography>
              <Typography variant="h4">
                {tenants?.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Tenants
              </Typography>
              <Typography variant="h4" color="success.main">
                {tenants?.filter(t => t.status === 'active').length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Enterprise Plans
              </Typography>
              <Typography variant="h4" color="error.main">
                {tenants?.filter(t => t.plan === 'enterprise').length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Suspended
              </Typography>
              <Typography variant="h4" color="warning.main">
                {tenants?.filter(t => t.status === 'suspended').length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Create Tenant Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Tenant</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Tenant Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Subdomain"
              value={formData.subdomain}
              onChange={(e) => setFormData({ ...formData, subdomain: e.target.value })}
              fullWidth
              required
              helperText="Will be accessible at subdomain.mams.app"
            />
            <TextField
              label="Admin Email"
              type="email"
              value={formData.admin_email}
              onChange={(e) => setFormData({ ...formData, admin_email: e.target.value })}
              fullWidth
              required
            />
            <FormControl fullWidth>
              <InputLabel>Plan</InputLabel>
              <Select
                value={formData.plan}
                onChange={(e) => setFormData({ ...formData, plan: e.target.value })}
                label="Plan"
              >
                <MenuItem value="free">Free</MenuItem>
                <MenuItem value="starter">Starter</MenuItem>
                <MenuItem value="standard">Standard</MenuItem>
                <MenuItem value="professional">Professional</MenuItem>
                <MenuItem value="enterprise">Enterprise</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateTenant}
            variant="contained"
            disabled={isCreating || !formData.name || !formData.subdomain || !formData.admin_email}
          >
            Create
          </Button>
        </DialogActions>
        {isCreating && <LinearProgress />}
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Delete Tenant</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mt: 2 }}>
            Are you sure you want to delete tenant "{selectedTenant?.name}"? This action cannot be undone.
            All data associated with this tenant will be permanently deleted.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleDeleteTenant}
            variant="contained"
            color="error"
            disabled={isDeleting}
          >
            Delete
          </Button>
        </DialogActions>
        {isDeleting && <LinearProgress />}
      </Dialog>
    </Box>
  );
}

// Tenant List Component
interface TenantListProps {
  tenants?: Tenant[];
  isLoading: boolean;
  onEdit: (tenant: Tenant) => void;
  onDelete: (tenant: Tenant) => void;
  onViewConfig: (tenant: Tenant) => void;
  onViewDomains: (tenant: Tenant) => void;
  onViewUsage: (tenant: Tenant) => void;
  onRefresh: () => void;
}

function TenantList({
  tenants,
  isLoading,
  onEdit,
  onDelete,
  onViewConfig,
  onViewDomains,
  onViewUsage,
  onRefresh,
}: TenantListProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'suspended':
        return 'warning';
      case 'pending':
        return 'info';
      case 'deleted':
        return 'error';
      default:
        return 'default';
    }
  };

  const getPlanColor = (plan: string) => {
    switch (plan) {
      case 'enterprise':
        return 'error';
      case 'professional':
        return 'warning';
      case 'standard':
        return 'primary';
      case 'starter':
        return 'info';
      case 'free':
        return 'default';
      default:
        return 'default';
    }
  };

  if (isLoading) {
    return (
      <Box>
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} height={60} sx={{ mb: 1 }} />
        ))}
      </Box>
    );
  }

  if (!tenants || tenants.length === 0) {
    return (
      <Box textAlign="center" py={4}>
        <Typography color="textSecondary">No tenants found</Typography>
      </Box>
    );
  }

  return (
    <>
      <Box display="flex" justifyContent="flex-end" mb={2}>
        <IconButton onClick={onRefresh} size="small">
          <RefreshIcon />
        </IconButton>
      </Box>

      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Tenant ID</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Subdomain</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Plan</TableCell>
              <TableCell>Admin Email</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tenants.map((tenant) => (
              <TableRow key={tenant.tenant_id} hover>
                <TableCell>
                  <Typography variant="body2" fontFamily="monospace">
                    {tenant.tenant_id}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography fontWeight="medium">{tenant.name}</Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {tenant.subdomain}.mams.app
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={tenant.status}
                    color={getStatusColor(tenant.status) as any}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Chip
                    label={tenant.plan}
                    color={getPlanColor(tenant.plan) as any}
                    size="small"
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>{tenant.admin_email}</TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {new Date(tenant.created_at).toLocaleDateString()}
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="Edit">
                    <IconButton
                      size="small"
                      onClick={() => onEdit(tenant)}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Configuration">
                    <IconButton
                      size="small"
                      onClick={() => onViewConfig(tenant)}
                    >
                      <SettingsIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Domains">
                    <IconButton
                      size="small"
                      onClick={() => onViewDomains(tenant)}
                    >
                      <DomainIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Usage">
                    <IconButton
                      size="small"
                      onClick={() => onViewUsage(tenant)}
                    >
                      <UsageIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <IconButton
                      size="small"
                      onClick={() => onDelete(tenant)}
                      disabled={tenant.status === 'deleted'}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
}