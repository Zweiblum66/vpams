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
  Typography,
  Button,
  IconButton,
  Tooltip,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Alert,
  Snackbar,
  Grid,
  Card,
  CardContent
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  ContentCopy as CopyIcon,
  Security as SecurityIcon,
  Analytics as AnalyticsIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { usePartnerAPIs } from '../../hooks/usePartnerAPIs';
import { APIKeyForm } from './APIKeyForm';
import { APIKeyAnalytics } from './APIKeyAnalytics';

interface APIKey {
  id: string;
  key_id: string;
  name: string;
  description?: string;
  status: 'active' | 'inactive' | 'revoked' | 'expired';
  tier: 'basic' | 'standard' | 'premium' | 'enterprise';
  scopes: string[];
  allowed_features: string[];
  allowed_api_versions: string[];
  rate_limit: string;
  burst_limit: number;
  current_usage: number;
  last_used_at?: string;
  created_at: string;
  updated_at?: string;
}

const statusColors = {
  active: 'success',
  inactive: 'default',
  revoked: 'error',
  expired: 'warning'
} as const;

const tierColors = {
  basic: 'default',
  standard: 'primary',
  premium: 'secondary',
  enterprise: 'warning'
} as const;

export const APIKeyManager: React.FC = () => {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [total, setTotal] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [editingKey, setEditingKey] = useState<APIKey | null>(null);
  const [selectedKeyId, setSelectedKeyId] = useState<string | null>(null);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'info'
  });

  const {
    getAPIKeys,
    createAPIKey,
    updateAPIKey,
    deleteAPIKey,
    regenerateAPIKey
  } = usePartnerAPIs();

  useEffect(() => {
    loadAPIKeys();
  }, [page, rowsPerPage]);

  const loadAPIKeys = async () => {
    setLoading(true);
    try {
      const response = await getAPIKeys({
        page: page + 1,
        limit: rowsPerPage
      });
      setApiKeys(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to load API keys:', error);
      setSnackbar({
        open: true,
        message: 'Failed to load API keys',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingKey(null);
    setShowForm(true);
  };

  const handleEdit = (apiKey: APIKey) => {
    setEditingKey(apiKey);
    setShowForm(true);
  };

  const handleDelete = async (apiKeyId: string) => {
    if (window.confirm('Are you sure you want to delete this API key? This action cannot be undone.')) {
      try {
        await deleteAPIKey(apiKeyId);
        await loadAPIKeys();
        setSnackbar({
          open: true,
          message: 'API key deleted successfully',
          severity: 'success'
        });
      } catch (error) {
        console.error('Failed to delete API key:', error);
        setSnackbar({
          open: true,
          message: 'Failed to delete API key',
          severity: 'error'
        });
      }
    }
  };

  const handleFormSubmit = async (apiKeyData: any) => {
    try {
      if (editingKey) {
        await updateAPIKey(editingKey.id, apiKeyData);
        setSnackbar({
          open: true,
          message: 'API key updated successfully',
          severity: 'success'
        });
      } else {
        const response = await createAPIKey(apiKeyData);
        setNewApiKey(response.api_key);
        setSnackbar({
          open: true,
          message: 'API key created successfully',
          severity: 'success'
        });
      }
      setShowForm(false);
      setEditingKey(null);
      await loadAPIKeys();
    } catch (error) {
      console.error('Failed to save API key:', error);
      setSnackbar({
        open: true,
        message: 'Failed to save API key',
        severity: 'error'
      });
    }
  };

  const handleRegenerate = async (apiKeyId: string) => {
    if (window.confirm('Are you sure you want to regenerate this API key? The old key will stop working immediately.')) {
      try {
        const response = await regenerateAPIKey(apiKeyId);
        setNewApiKey(response.api_key);
        await loadAPIKeys();
        setSnackbar({
          open: true,
          message: 'API key regenerated successfully',
          severity: 'success'
        });
      } catch (error) {
        console.error('Failed to regenerate API key:', error);
        setSnackbar({
          open: true,
          message: 'Failed to regenerate API key',
          severity: 'error'
        });
      }
    }
  };

  const handleCopyApiKey = (apiKey: string) => {
    navigator.clipboard.writeText(apiKey);
    setSnackbar({
      open: true,
      message: 'API key copied to clipboard',
      severity: 'success'
    });
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleViewAnalytics = (apiKeyId: string) => {
    setSelectedKeyId(apiKeyId);
    setShowAnalytics(true);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const formatUsage = (usage: number, limit: number) => {
    const percentage = limit > 0 ? (usage / limit) * 100 : 0;
    return `${usage.toLocaleString()} / ${limit.toLocaleString()} (${percentage.toFixed(1)}%)`;
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box display="flex" justifyContent="between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          API Key Management
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadAPIKeys}
            sx={{ mr: 2 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreate}
          >
            Create API Key
          </Button>
        </Box>
      </Box>

      {/* Usage Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom variant="body2">
                Total API Keys
              </Typography>
              <Typography variant="h4" component="div">
                {total}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom variant="body2">
                Active Keys
              </Typography>
              <Typography variant="h4" component="div" color="success.main">
                {apiKeys.filter(key => key.status === 'active').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom variant="body2">
                This Month Usage
              </Typography>
              <Typography variant="h4" component="div">
                {apiKeys.reduce((sum, key) => sum + key.current_usage, 0).toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom variant="body2">
                Enterprise Keys
              </Typography>
              <Typography variant="h4" component="div" color="warning.main">
                {apiKeys.filter(key => key.tier === 'enterprise').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* API Keys Table */}
      <Paper sx={{ width: '100%', mb: 2 }}>
        <TableContainer>
          <Table sx={{ minWidth: 750 }} aria-labelledby="tableTitle">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Key ID</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Tier</TableCell>
                <TableCell>Usage</TableCell>
                <TableCell>Features</TableCell>
                <TableCell>Last Used</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {apiKeys.map((apiKey) => (
                <TableRow hover key={apiKey.id}>
                  <TableCell>
                    <Box>
                      <Typography variant="body2" fontWeight="medium">
                        {apiKey.name}
                      </Typography>
                      {apiKey.description && (
                        <Typography variant="caption" color="textSecondary">
                          {apiKey.description}
                        </Typography>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace">
                      {apiKey.key_id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={apiKey.status}
                      color={statusColors[apiKey.status]}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={apiKey.tier}
                      color={tierColors[apiKey.tier]}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {formatUsage(apiKey.current_usage, apiKey.burst_limit)}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {apiKey.rate_limit}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {apiKey.allowed_features.slice(0, 3).map((feature) => (
                        <Chip
                          key={feature}
                          label={feature}
                          size="small"
                          variant="outlined"
                        />
                      ))}
                      {apiKey.allowed_features.length > 3 && (
                        <Chip
                          label={`+${apiKey.allowed_features.length - 3}`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    {apiKey.last_used_at ? formatDate(apiKey.last_used_at) : 'Never'}
                  </TableCell>
                  <TableCell>{formatDate(apiKey.created_at)}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="View Analytics">
                      <IconButton
                        size="small"
                        onClick={() => handleViewAnalytics(apiKey.id)}
                      >
                        <AnalyticsIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Edit">
                      <IconButton
                        size="small"
                        onClick={() => handleEdit(apiKey)}
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Regenerate">
                      <IconButton
                        size="small"
                        onClick={() => handleRegenerate(apiKey.id)}
                      >
                        <SecurityIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(apiKey.id)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
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

      {/* Create/Edit Form Dialog */}
      <Dialog
        open={showForm}
        onClose={() => {
          setShowForm(false);
          setEditingKey(null);
        }}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingKey ? 'Edit API Key' : 'Create New API Key'}
        </DialogTitle>
        <DialogContent>
          <APIKeyForm
            apiKey={editingKey}
            onSubmit={handleFormSubmit}
            onCancel={() => {
              setShowForm(false);
              setEditingKey(null);
            }}
          />
        </DialogContent>
      </Dialog>

      {/* Analytics Dialog */}
      <Dialog
        open={showAnalytics}
        onClose={() => {
          setShowAnalytics(false);
          setSelectedKeyId(null);
        }}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>API Key Analytics</DialogTitle>
        <DialogContent>
          {selectedKeyId && (
            <APIKeyAnalytics
              apiKeyId={selectedKeyId}
              onClose={() => {
                setShowAnalytics(false);
                setSelectedKeyId(null);
              }}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* New API Key Display Dialog */}
      <Dialog
        open={!!newApiKey}
        onClose={() => setNewApiKey(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={1}>
            <SecurityIcon color="primary" />
            New API Key Created
          </Box>
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This is the only time you will see this API key. Please copy it and store it securely.
          </Alert>
          <TextField
            fullWidth
            label="API Key"
            value={newApiKey || ''}
            InputProps={{
              readOnly: true,
              endAdornment: (
                <IconButton
                  onClick={() => handleCopyApiKey(newApiKey!)}
                  edge="end"
                >
                  <CopyIcon />
                </IconButton>
              )
            }}
            sx={{ fontFamily: 'monospace' }}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => handleCopyApiKey(newApiKey!)}
            startIcon={<CopyIcon />}
            variant="outlined"
          >
            Copy to Clipboard
          </Button>
          <Button onClick={() => setNewApiKey(null)} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};