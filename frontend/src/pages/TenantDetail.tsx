"""
Tenant Detail Page - Detailed management interface for a single tenant.

Provides comprehensive tenant management including:
- Tenant information and status
- Domain management
- Configuration management with templates
- Usage monitoring and analytics
"""

import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Button,
  Tabs,
  Tab,
  Grid,
  Card,
  CardContent,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Divider,
  LinearProgress,
  Skeleton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Switch,
  FormControlLabel,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Domain as DomainIcon,
  VerifiedUser as VerifiedIcon,
  Warning as WarningIcon,
  ExpandMore as ExpandMoreIcon,
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  Upload as UploadIcon,
  History as HistoryIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { PageHeader } from '../components/PageHeader/PageHeader';
import {
  useGetTenantQuery,
  useUpdateTenantMutation,
  useGetTenantDomainsQuery,
  useAddDomainMutation,
  useVerifyDomainMutation,
  useRemoveDomainMutation,
  useGetTenantConfigQuery,
  useUpdateTenantConfigMutation,
  useGetConfigTemplatesQuery,
  useApplyConfigTemplateMutation,
  useRollbackConfigMutation,
  useExportConfigMutation,
  useImportConfigMutation,
  useGetTenantUsageQuery,
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
      id={`tenant-detail-tabpanel-${index}`}
      aria-labelledby={`tenant-detail-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function TenantDetail() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [tabValue, setTabValue] = useState(0);
  const [isEditing, setIsEditing] = useState(false);
  const [addDomainOpen, setAddDomainOpen] = useState(false);
  const [applyTemplateOpen, setApplyTemplateOpen] = useState(false);
  const [importConfigOpen, setImportConfigOpen] = useState(false);
  
  // Form states
  const [editData, setEditData] = useState<any>({});
  const [newDomain, setNewDomain] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [configEditData, setConfigEditData] = useState<any>({});

  // API hooks
  const { data: tenant, isLoading: tenantLoading } = useGetTenantQuery(tenantId!);
  const { data: domains, isLoading: domainsLoading, refetch: refetchDomains } = useGetTenantDomainsQuery(tenantId!);
  const { data: config, isLoading: configLoading, refetch: refetchConfig } = useGetTenantConfigQuery(tenantId!);
  const { data: templates } = useGetConfigTemplatesQuery(undefined);
  const { data: usage, isLoading: usageLoading } = useGetTenantUsageQuery({ tenantId: tenantId! });

  const [updateTenant] = useUpdateTenantMutation();
  const [addDomain] = useAddDomainMutation();
  const [verifyDomain] = useVerifyDomainMutation();
  const [removeDomain] = useRemoveDomainMutation();
  const [updateConfig] = useUpdateTenantConfigMutation();
  const [applyTemplate] = useApplyConfigTemplateMutation();
  const [rollbackConfig] = useRollbackConfigMutation();
  const [exportConfig] = useExportConfigMutation();
  const [importConfig] = useImportConfigMutation();

  // Set initial tab based on URL param
  useEffect(() => {
    const section = searchParams.get('section');
    switch (section) {
      case 'config':
        setTabValue(1);
        break;
      case 'domains':
        setTabValue(2);
        break;
      case 'usage':
        setTabValue(3);
        break;
      default:
        setTabValue(0);
    }
  }, [searchParams]);

  // Initialize edit data when tenant loads
  useEffect(() => {
    if (tenant) {
      setEditData({
        name: tenant.name,
        metadata: tenant.metadata || {},
      });
    }
  }, [tenant]);

  // Initialize config edit data when config loads
  useEffect(() => {
    if (config) {
      setConfigEditData(config);
    }
  }, [config]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSaveTenant = async () => {
    try {
      await updateTenant({ tenantId: tenantId!, update: editData }).unwrap();
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update tenant:', error);
    }
  };

  const handleAddDomain = async () => {
    try {
      await addDomain({
        tenantId: tenantId!,
        domain: newDomain,
        auto_verify: true,
        auto_ssl: true,
      }).unwrap();
      setAddDomainOpen(false);
      setNewDomain('');
      refetchDomains();
    } catch (error) {
      console.error('Failed to add domain:', error);
    }
  };

  const handleVerifyDomain = async (domain: string) => {
    try {
      await verifyDomain({
        tenantId: tenantId!,
        domain,
        method: 'dns',
      }).unwrap();
      refetchDomains();
    } catch (error) {
      console.error('Failed to verify domain:', error);
    }
  };

  const handleRemoveDomain = async (domain: string) => {
    try {
      await removeDomain({
        tenantId: tenantId!,
        domain,
      }).unwrap();
      refetchDomains();
    } catch (error) {
      console.error('Failed to remove domain:', error);
    }
  };

  const handleUpdateConfig = async () => {
    try {
      await updateConfig({
        tenantId: tenantId!,
        config: configEditData,
      }).unwrap();
      refetchConfig();
    } catch (error) {
      console.error('Failed to update config:', error);
    }
  };

  const handleApplyTemplate = async () => {
    try {
      await applyTemplate({
        tenantId: tenantId!,
        templateName: selectedTemplate,
        merge: true,
      }).unwrap();
      setApplyTemplateOpen(false);
      setSelectedTemplate('');
      refetchConfig();
    } catch (error) {
      console.error('Failed to apply template:', error);
    }
  };

  const handleExportConfig = async () => {
    try {
      const data = await exportConfig(tenantId!).unwrap();
      // Download as JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tenant-${tenantId}-config.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export config:', error);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (tenantLoading) {
    return <LinearProgress />;
  }

  if (!tenant) {
    return (
      <Box p={3}>
        <Alert severity="error">Tenant not found</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title={tenant.name}
        subtitle={`Tenant ID: ${tenant.tenant_id}`}
        breadcrumbs={[
          { label: 'Tenant Management', path: '/tenants' },
          { label: tenant.name },
        ]}
        action={
          <Button
            startIcon={<BackIcon />}
            onClick={() => navigate('/tenants')}
          >
            Back to Tenants
          </Button>
        }
      />

      <Paper sx={{ width: '100%', mb: 2 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          aria-label="tenant detail tabs"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Overview" />
          <Tab label="Configuration" />
          <Tab label="Domains" />
          <Tab label="Usage & Analytics" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          {/* Overview Tab */}
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6">Tenant Information</Typography>
                    {!isEditing ? (
                      <IconButton onClick={() => setIsEditing(true)}>
                        <EditIcon />
                      </IconButton>
                    ) : (
                      <Box>
                        <IconButton onClick={handleSaveTenant} color="primary">
                          <SaveIcon />
                        </IconButton>
                        <IconButton onClick={() => setIsEditing(false)}>
                          <CancelIcon />
                        </IconButton>
                      </Box>
                    )}
                  </Box>

                  <Table>
                    <TableBody>
                      <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>
                          {isEditing ? (
                            <TextField
                              value={editData.name}
                              onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                              fullWidth
                              size="small"
                            />
                          ) : (
                            tenant.name
                          )}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Subdomain</TableCell>
                        <TableCell>{tenant.subdomain}.mams.app</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Status</TableCell>
                        <TableCell>
                          <Chip
                            label={tenant.status}
                            color={tenant.status === 'active' ? 'success' : 'warning'}
                            size="small"
                          />
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Plan</TableCell>
                        <TableCell>
                          <Chip
                            label={tenant.plan}
                            color={tenant.plan === 'enterprise' ? 'error' : 'primary'}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Admin Email</TableCell>
                        <TableCell>{tenant.admin_email}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Created</TableCell>
                        <TableCell>{new Date(tenant.created_at).toLocaleString()}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" mb={2}>Quick Stats</Typography>
                  {usageLoading ? (
                    <Skeleton height={200} />
                  ) : usage ? (
                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Typography color="textSecondary">Storage Used</Typography>
                        <Typography variant="h5">{usage.storage_gb.toFixed(2)} GB</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography color="textSecondary">Active Users</Typography>
                        <Typography variant="h5">{usage.active_users}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography color="textSecondary">Total Assets</Typography>
                        <Typography variant="h5">{usage.asset_count}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography color="textSecondary">API Calls</Typography>
                        <Typography variant="h5">{usage.api_calls.toLocaleString()}</Typography>
                      </Grid>
                    </Grid>
                  ) : (
                    <Alert severity="info">No usage data available</Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {/* Configuration Tab */}
          <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
              <Typography variant="h6">Configuration</Typography>
              <Box>
                <Button
                  startIcon={<DownloadIcon />}
                  onClick={handleExportConfig}
                  sx={{ mr: 1 }}
                >
                  Export
                </Button>
                <Button
                  startIcon={<UploadIcon />}
                  onClick={() => setImportConfigOpen(true)}
                  sx={{ mr: 1 }}
                >
                  Import
                </Button>
                <Button
                  variant="contained"
                  onClick={() => setApplyTemplateOpen(true)}
                >
                  Apply Template
                </Button>
              </Box>
            </Box>

            {configLoading ? (
              <Skeleton height={400} />
            ) : config ? (
              <Box>
                {/* Branding Configuration */}
                <Accordion defaultExpanded>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Branding</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="Primary Color"
                          value={configEditData.branding?.primary_color || ''}
                          onChange={(e) => setConfigEditData({
                            ...configEditData,
                            branding: { ...configEditData.branding, primary_color: e.target.value }
                          })}
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          label="Secondary Color"
                          value={configEditData.branding?.secondary_color || ''}
                          onChange={(e) => setConfigEditData({
                            ...configEditData,
                            branding: { ...configEditData.branding, secondary_color: e.target.value }
                          })}
                          fullWidth
                          size="small"
                        />
                      </Grid>
                      <Grid item xs={12}>
                        <TextField
                          label="Logo URL"
                          value={configEditData.branding?.logo_url || ''}
                          onChange={(e) => setConfigEditData({
                            ...configEditData,
                            branding: { ...configEditData.branding, logo_url: e.target.value }
                          })}
                          fullWidth
                          size="small"
                        />
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>

                {/* Feature Flags */}
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Features</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      {Object.entries(config.features).map(([key, value]) => (
                        <Grid item xs={12} sm={6} key={key}>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={configEditData.features?.[key] || false}
                                onChange={(e) => setConfigEditData({
                                  ...configEditData,
                                  features: { ...configEditData.features, [key]: e.target.checked }
                                })}
                              />
                            }
                            label={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          />
                        </Grid>
                      ))}
                    </Grid>
                  </AccordionDetails>
                </Accordion>

                {/* Security Settings */}
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Security</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={configEditData.security?.mfa_required || false}
                              onChange={(e) => setConfigEditData({
                                ...configEditData,
                                security: { ...configEditData.security, mfa_required: e.target.checked }
                              })}
                            />
                          }
                          label="MFA Required"
                        />
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <TextField
                          label="Session Timeout (minutes)"
                          type="number"
                          value={configEditData.security?.session_timeout_minutes || 30}
                          onChange={(e) => setConfigEditData({
                            ...configEditData,
                            security: { ...configEditData.security, session_timeout_minutes: parseInt(e.target.value) }
                          })}
                          fullWidth
                          size="small"
                        />
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>

                <Box mt={3} display="flex" justifyContent="flex-end">
                  <Button
                    variant="contained"
                    onClick={handleUpdateConfig}
                    startIcon={<SaveIcon />}
                  >
                    Save Configuration
                  </Button>
                </Box>
              </Box>
            ) : (
              <Alert severity="error">Failed to load configuration</Alert>
            )}
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {/* Domains Tab */}
          <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
              <Typography variant="h6">Custom Domains</Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => setAddDomainOpen(true)}
              >
                Add Domain
              </Button>
            </Box>

            {domainsLoading ? (
              <Skeleton height={200} />
            ) : domains && domains.length > 0 ? (
              <List>
                {domains.map((domain) => (
                  <React.Fragment key={domain.domain}>
                    <ListItem>
                      <ListItemText
                        primary={
                          <Box display="flex" alignItems="center" gap={1}>
                            <Typography>{domain.domain}</Typography>
                            {domain.is_verified ? (
                              <Chip
                                label="Verified"
                                color="success"
                                size="small"
                                icon={<VerifiedIcon />}
                              />
                            ) : (
                              <Chip
                                label="Pending Verification"
                                color="warning"
                                size="small"
                                icon={<WarningIcon />}
                              />
                            )}
                            {domain.ssl_enabled && (
                              <Chip label="SSL" color="primary" size="small" />
                            )}
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography variant="body2" color="textSecondary">
                              Created: {new Date(domain.created_at).toLocaleString()}
                            </Typography>
                            {!domain.is_verified && domain.verification_token && (
                              <Box mt={1}>
                                <Typography variant="body2" color="error">
                                  Add this TXT record to your DNS:
                                </Typography>
                                <Box display="flex" alignItems="center" gap={1} mt={0.5}>
                                  <Typography variant="body2" fontFamily="monospace" sx={{ bgcolor: 'grey.100', p: 1, borderRadius: 1 }}>
                                    {domain.verification_token}
                                  </Typography>
                                  <IconButton size="small" onClick={() => copyToClipboard(domain.verification_token!)}>
                                    <CopyIcon fontSize="small" />
                                  </IconButton>
                                </Box>
                              </Box>
                            )}
                          </Box>
                        }
                      />
                      <ListItemSecondaryAction>
                        {!domain.is_verified && (
                          <Button
                            size="small"
                            onClick={() => handleVerifyDomain(domain.domain)}
                            sx={{ mr: 1 }}
                          >
                            Verify
                          </Button>
                        )}
                        <IconButton
                          edge="end"
                          onClick={() => handleRemoveDomain(domain.domain)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                    <Divider />
                  </React.Fragment>
                ))}
              </List>
            ) : (
              <Alert severity="info">No custom domains configured</Alert>
            )}
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          {/* Usage Tab */}
          <Box>
            <Typography variant="h6" mb={3}>Usage & Analytics</Typography>
            
            {usageLoading ? (
              <Skeleton height={300} />
            ) : usage ? (
              <Grid container spacing={3}>
                <Grid item xs={12} md={4}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" gutterBottom>
                        Storage Usage
                      </Typography>
                      <Typography variant="h4">
                        {usage.storage_gb.toFixed(2)} GB
                      </Typography>
                      <LinearProgress
                        variant="determinate"
                        value={(usage.storage_gb / 1000) * 100}
                        sx={{ mt: 2 }}
                      />
                      <Typography variant="body2" color="textSecondary" mt={1}>
                        {((usage.storage_gb / 1000) * 100).toFixed(1)}% of 1TB limit
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" gutterBottom>
                        Bandwidth Usage
                      </Typography>
                      <Typography variant="h4">
                        {usage.bandwidth_gb.toFixed(2)} GB
                      </Typography>
                      <Typography variant="body2" color="textSecondary" mt={2}>
                        This billing period
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" gutterBottom>
                        Estimated Cost
                      </Typography>
                      <Typography variant="h4">
                        ${usage.cost_estimate?.toFixed(2) || '0.00'}
                      </Typography>
                      <Typography variant="body2" color="textSecondary" mt={2}>
                        Current billing period
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" mb={2}>Detailed Metrics</Typography>
                      <Table>
                        <TableBody>
                          <TableRow>
                            <TableCell>Active Users</TableCell>
                            <TableCell align="right">{usage.active_users}</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Total Assets</TableCell>
                            <TableCell align="right">{usage.asset_count.toLocaleString()}</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>API Calls (This Period)</TableCell>
                            <TableCell align="right">{usage.api_calls.toLocaleString()}</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Period</TableCell>
                            <TableCell align="right">
                              {new Date(usage.period_start).toLocaleDateString()} - {new Date(usage.period_end).toLocaleDateString()}
                            </TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            ) : (
              <Alert severity="info">No usage data available</Alert>
            )}
          </Box>
        </TabPanel>
      </Paper>

      {/* Add Domain Dialog */}
      <Dialog
        open={addDomainOpen}
        onClose={() => setAddDomainOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Custom Domain</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <TextField
              label="Domain"
              value={newDomain}
              onChange={(e) => setNewDomain(e.target.value)}
              fullWidth
              placeholder="example.com"
              helperText="Enter your custom domain without protocol (https://)"
            />
            <Alert severity="info" sx={{ mt: 2 }}>
              After adding the domain, you'll need to add a TXT record to your DNS to verify ownership.
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDomainOpen(false)}>Cancel</Button>
          <Button
            onClick={handleAddDomain}
            variant="contained"
            disabled={!newDomain}
          >
            Add Domain
          </Button>
        </DialogActions>
      </Dialog>

      {/* Apply Template Dialog */}
      <Dialog
        open={applyTemplateOpen}
        onClose={() => setApplyTemplateOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Apply Configuration Template</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Template</InputLabel>
              <Select
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                label="Template"
              >
                {templates?.map((template) => (
                  <MenuItem key={template.name} value={template.name}>
                    <Box>
                      <Typography>{template.name}</Typography>
                      <Typography variant="body2" color="textSecondary">
                        {template.description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Alert severity="warning" sx={{ mt: 2 }}>
              This will merge the template settings with your current configuration.
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApplyTemplateOpen(false)}>Cancel</Button>
          <Button
            onClick={handleApplyTemplate}
            variant="contained"
            disabled={!selectedTemplate}
          >
            Apply Template
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}