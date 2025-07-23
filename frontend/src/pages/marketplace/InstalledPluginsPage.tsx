import React, { useState } from 'react';
import {
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Box,
  Switch,
  FormControlLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Stack,
  Tooltip,
  LinearProgress,
  Avatar
} from '@mui/material';
import {
  Extension as ExtensionIcon,
  Settings as SettingsIcon,
  Delete as DeleteIcon,
  MoreVert as MoreVertIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon,
  Error as ErrorIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  PlayArrow as PlayArrowIcon,
  Pause as PauseIcon,
  GetApp as GetAppIcon,
  Update as UpdateIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { 
  useGetMyInstalledPluginsQuery,
  useUninstallPluginFromMarketplaceMutation
} from '../../store/api/marketplaceApi';
import { Loading } from '../../components/Loading/RTKQueryLoading';

interface PluginMenuProps {
  plugin: any;
  onUninstall: (pluginId: string) => void;
  onConfigure: (pluginId: string) => void;
  onToggleStatus: (pluginId: string, enabled: boolean) => void;
}

const PluginActionMenu: React.FC<PluginMenuProps> = ({
  plugin,
  onUninstall,
  onConfigure,
  onToggleStatus
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <>
      <IconButton onClick={handleClick}>
        <MoreVertIcon />
      </IconButton>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
      >
        <MenuItem onClick={() => { onConfigure(plugin.plugin_id); handleClose(); }}>
          <SettingsIcon sx={{ mr: 1 }} />
          Configure
        </MenuItem>
        <MenuItem 
          onClick={() => { 
            onToggleStatus(plugin.plugin_id, plugin.status !== 'enabled'); 
            handleClose(); 
          }}
        >
          {plugin.status === 'enabled' ? (
            <>
              <PauseIcon sx={{ mr: 1 }} />
              Disable
            </>
          ) : (
            <>
              <PlayArrowIcon sx={{ mr: 1 }} />
              Enable
            </>
          )}
        </MenuItem>
        <MenuItem onClick={() => { onUninstall(plugin.plugin_id); handleClose(); }}>
          <DeleteIcon sx={{ mr: 1 }} />
          Uninstall
        </MenuItem>
      </Menu>
    </>
  );
};

const getStatusColor = (status: string): 'success' | 'error' | 'warning' | 'default' => {
  switch (status) {
    case 'installed':
    case 'enabled':
      return 'success';
    case 'failed':
    case 'error':
      return 'error';
    case 'installing':
    case 'uninstalling':
      return 'warning';
    default:
      return 'default';
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'installed':
    case 'enabled':
      return <CheckCircleIcon color="success" />;
    case 'failed':
    case 'error':
      return <ErrorIcon color="error" />;
    case 'installing':
    case 'uninstalling':
      return <WarningIcon color="warning" />;
    default:
      return <InfoIcon color="info" />;
  }
};

export const InstalledPluginsPage: React.FC = () => {
  const navigate = useNavigate();
  
  // State
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');
  const [uninstallDialogOpen, setUninstallDialogOpen] = useState(false);
  const [selectedPlugin, setSelectedPlugin] = useState<any>(null);

  // API calls
  const { data: installedPlugins, isLoading, error, refetch } = useGetMyInstalledPluginsQuery();
  const [uninstallPlugin, { isLoading: uninstalling }] = useUninstallPluginFromMarketplaceMutation();

  const handleUninstall = (pluginId: string) => {
    const plugin = installedPlugins?.find(p => p.plugin_id === pluginId);
    setSelectedPlugin(plugin);
    setUninstallDialogOpen(true);
  };

  const confirmUninstall = async () => {
    if (selectedPlugin) {
      try {
        await uninstallPlugin({ plugin_id: selectedPlugin.plugin_id }).unwrap();
        setUninstallDialogOpen(false);
        setSelectedPlugin(null);
        refetch();
      } catch (error) {
        console.error('Failed to uninstall plugin:', error);
      }
    }
  };

  const handleConfigure = (pluginId: string) => {
    // Navigate to plugin configuration page
    navigate(`/settings/plugins/${pluginId}`);
  };

  const handleToggleStatus = async (pluginId: string, enabled: boolean) => {
    // TODO: Implement enable/disable plugin functionality
    console.log('Toggle plugin status:', pluginId, enabled);
  };

  if (isLoading) {
    return <Loading />;
  }

  if (error) {
    return (
      <Container maxWidth="lg">
        <Alert severity="error" sx={{ mt: 2 }}>
          Failed to load installed plugins. Please try again.
        </Alert>
      </Container>
    );
  }

  const pluginsByStatus = installedPlugins?.reduce((acc, plugin) => {
    const status = plugin.status;
    if (!acc[status]) acc[status] = 0;
    acc[status]++;
    return acc;
  }, {} as Record<string, number>) || {};

  return (
    <Container maxWidth="xl">
      <PageHeader
        title="Installed Plugins"
        subtitle={`Manage your ${installedPlugins?.length || 0} installed plugins`}
        action={
          <Stack direction="row" spacing={2}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={() => refetch()}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<GetAppIcon />}
              onClick={() => navigate('/marketplace')}
            >
              Browse Marketplace
            </Button>
          </Stack>
        }
      />

      {/* Status Overview */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="primary">
                {installedPlugins?.length || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Installed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="success.main">
                {pluginsByStatus.enabled || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Active
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="warning.main">
                {(pluginsByStatus.installing || 0) + (pluginsByStatus.uninstalling || 0)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                In Progress
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="error.main">
                {pluginsByStatus.failed || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Failed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* View Mode Toggle */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">
          Your Plugins
        </Typography>
        <FormControlLabel
          control={
            <Switch
              checked={viewMode === 'table'}
              onChange={(e) => setViewMode(e.target.checked ? 'table' : 'cards')}
            />
          }
          label="Table View"
        />
      </Box>

      {/* Plugins List */}
      {installedPlugins?.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <ExtensionIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              No Plugins Installed
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Browse the marketplace to discover and install plugins to extend MAMS functionality.
            </Typography>
            <Button
              variant="contained"
              startIcon={<GetAppIcon />}
              onClick={() => navigate('/marketplace')}
            >
              Browse Marketplace
            </Button>
          </CardContent>
        </Card>
      ) : viewMode === 'cards' ? (
        <Grid container spacing={3}>
          {installedPlugins?.map((plugin) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={plugin.installation_id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
                      <ExtensionIcon />
                    </Avatar>
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="h6" noWrap>
                        {plugin.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        v{plugin.version}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      {getStatusIcon(plugin.status)}
                      <PluginActionMenu
                        plugin={plugin}
                        onUninstall={handleUninstall}
                        onConfigure={handleConfigure}
                        onToggleStatus={handleToggleStatus}
                      />
                    </Box>
                  </Box>

                  <Typography variant="body2" color="text.secondary" paragraph>
                    {plugin.description}
                  </Typography>

                  <Stack spacing={1}>
                    <Chip
                      label={plugin.status}
                      color={getStatusColor(plugin.status)}
                      size="small"
                    />
                    <Chip
                      label={plugin.plugin_type}
                      variant="outlined"
                      size="small"
                    />
                  </Stack>

                  {plugin.status === 'installing' && (
                    <Box sx={{ mt: 2 }}>
                      <LinearProgress />
                      <Typography variant="caption" color="text.secondary">
                        Installing...
                      </Typography>
                    </Box>
                  )}

                  {plugin.error_message && (
                    <Alert severity="error" sx={{ mt: 2 }}>
                      {plugin.error_message}
                    </Alert>
                  )}
                </CardContent>

                <CardActions>
                  <Button
                    size="small"
                    startIcon={<SettingsIcon />}
                    onClick={() => handleConfigure(plugin.plugin_id)}
                  >
                    Configure
                  </Button>
                  <Button
                    size="small"
                    startIcon={<InfoIcon />}
                    onClick={() => navigate(`/marketplace/plugins/${plugin.plugin_id}`)}
                  >
                    Details
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Plugin</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Installed</TableCell>
                <TableCell>Last Used</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {installedPlugins?.map((plugin) => (
                <TableRow key={plugin.installation_id}>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
                        <ExtensionIcon />
                      </Avatar>
                      <Box>
                        <Typography variant="subtitle2">
                          {plugin.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          v{plugin.version}
                        </Typography>
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={plugin.plugin_type}
                      variant="outlined"
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      {getStatusIcon(plugin.status)}
                      <Chip
                        label={plugin.status}
                        color={getStatusColor(plugin.status)}
                        size="small"
                        sx={{ ml: 1 }}
                      />
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {plugin.installed_at 
                        ? new Date(plugin.installed_at).toLocaleDateString()
                        : 'N/A'
                      }
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {plugin.last_used 
                        ? new Date(plugin.last_used).toLocaleDateString()
                        : 'Never'
                      }
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <PluginActionMenu
                      plugin={plugin}
                      onUninstall={handleUninstall}
                      onConfigure={handleConfigure}
                      onToggleStatus={handleToggleStatus}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Uninstall Confirmation Dialog */}
      <Dialog
        open={uninstallDialogOpen}
        onClose={() => setUninstallDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Uninstall Plugin</DialogTitle>
        <DialogContent>
          {selectedPlugin && (
            <>
              <Alert severity="warning" sx={{ mb: 2 }}>
                This action cannot be undone. All plugin data and configuration will be removed.
              </Alert>
              <Typography variant="body1">
                Are you sure you want to uninstall "{selectedPlugin.name}"?
              </Typography>
              {selectedPlugin.error_message && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Error: {selectedPlugin.error_message}
                </Typography>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUninstallDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={confirmUninstall}
            disabled={uninstalling}
          >
            {uninstalling ? 'Uninstalling...' : 'Uninstall'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default InstalledPluginsPage;