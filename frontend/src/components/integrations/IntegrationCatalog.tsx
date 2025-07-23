import React, { useState, useMemo } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Typography,
  Chip,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Autocomplete,
  Rating,
  Avatar,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Paper,
  Divider,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Star as StarIcon,
  Download as InstallIcon,
  Visibility as ViewIcon,
  Category as CategoryIcon,
  Code as CodeIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
  Support as SupportIcon,
  Close as CloseIcon,
  Launch as LaunchIcon
} from '@mui/icons-material';
import { useIntegrationCatalog } from '../../hooks/useIntegrationCatalog';

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
      id={`integration-tabpanel-${index}`}
      aria-labelledby={`integration-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const IntegrationCatalog: React.FC = () => {
  const [currentTab, setCurrentTab] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [showOnlyFree, setShowOnlyFree] = useState(false);
  const [showOnlyFeatured, setShowOnlyFeatured] = useState(false);
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');
  const [selectedIntegration, setSelectedIntegration] = useState<any>(null);
  const [installDialogOpen, setInstallDialogOpen] = useState(false);
  const [selectedEnvironment, setSelectedEnvironment] = useState('production');

  const {
    integrations,
    categories,
    featuredIntegrations,
    popularIntegrations,
    stats,
    isLoading,
    error,
    searchSuggestions,
    refetchIntegrations,
    installIntegration,
    getIntegrationDetails
  } = useIntegrationCatalog({
    search: searchTerm,
    category: selectedCategory,
    integration_type: selectedType,
    provider: selectedProvider,
    is_free: showOnlyFree || undefined,
    is_featured: showOnlyFeatured || undefined,
    sort_by: sortBy,
    sort_order: sortOrder as 'asc' | 'desc'
  });

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleIntegrationClick = async (integration: any) => {
    try {
      const details = await getIntegrationDetails(integration.id);
      setSelectedIntegration(details);
    } catch (error) {
      console.error('Failed to load integration details:', error);
    }
  };

  const handleInstallClick = (integration: any) => {
    setSelectedIntegration(integration);
    setInstallDialogOpen(true);
  };

  const handleInstallSubmit = async () => {
    if (!selectedIntegration) return;

    try {
      await installIntegration({
        integration_id: selectedIntegration.id,
        environment: selectedEnvironment,
        config: {}
      });
      setInstallDialogOpen(false);
      // TODO: Show success notification
    } catch (error) {
      console.error('Installation failed:', error);
      // TODO: Show error notification
    }
  };

  const renderIntegrationCard = (integration: any) => (
    <Grid item xs={12} sm={6} md={4} lg={3} key={integration.id}>
      <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <CardMedia
          sx={{
            height: 60,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: 'grey.100'
          }}
        >
          {integration.logo_url ? (
            <img
              src={integration.logo_url}
              alt={integration.display_name}
              style={{ maxHeight: 40, maxWidth: '100%' }}
            />
          ) : (
            <Avatar sx={{ width: 40, height: 40 }}>
              {integration.display_name?.charAt(0)}
            </Avatar>
          )}
        </CardMedia>
        
        <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Typography variant="h6" component="h3" sx={{ flexGrow: 1 }}>
              {integration.display_name || integration.name}
            </Typography>
            {integration.is_verified && (
              <Tooltip title="Verified Integration">
                <SecurityIcon color="primary" fontSize="small" />
              </Tooltip>
            )}
          </Box>
          
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, flexGrow: 1 }}>
            {integration.description}
          </Typography>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Rating
              value={integration.rating}
              readOnly
              size="small"
              precision={0.1}
            />
            <Typography variant="caption">
              ({integration.review_count})
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {integration.install_count} installs
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
            <Chip
              label={integration.category}
              size="small"
              color="primary"
              variant="outlined"
            />
            {integration.is_free && (
              <Chip label="Free" size="small" color="success" />
            )}
            {integration.is_featured && (
              <Chip label="Featured" size="small" color="secondary" />
            )}
          </Box>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              size="small"
              startIcon={<ViewIcon />}
              onClick={() => handleIntegrationClick(integration)}
              sx={{ flex: 1 }}
            >
              View
            </Button>
            <Button
              variant="contained"
              size="small"
              startIcon={<InstallIcon />}
              onClick={() => handleInstallClick(integration)}
              sx={{ flex: 1 }}
            >
              Install
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Grid>
  );

  const renderFilters = () => (
    <Paper sx={{ p: 2, mb: 3 }}>
      <Grid container spacing={2} alignItems="center">
        <Grid item xs={12} md={4}>
          <Autocomplete
            freeSolo
            options={searchSuggestions || []}
            value={searchTerm}
            onInputChange={(_, newValue) => setSearchTerm(newValue)}
            renderInput={(params) => (
              <TextField
                {...params}
                placeholder="Search integrations..."
                InputProps={{
                  ...params.InputProps,
                  startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
                }}
              />
            )}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
            <InputLabel>Category</InputLabel>
            <Select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              label="Category"
            >
              <MenuItem value="">All Categories</MenuItem>
              {categories?.map((category) => (
                <MenuItem key={category.id} value={category.slug}>
                  {category.display_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>

        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
            <InputLabel>Type</InputLabel>
            <Select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              label="Type"
            >
              <MenuItem value="">All Types</MenuItem>
              <MenuItem value="rest_api">REST API</MenuItem>
              <MenuItem value="graphql">GraphQL</MenuItem>
              <MenuItem value="webhook">Webhook</MenuItem>
              <MenuItem value="sdk">SDK</MenuItem>
              <MenuItem value="plugin">Plugin</MenuItem>
              <MenuItem value="connector">Connector</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        <Grid item xs={12} sm={6} md={2}>
          <FormControl fullWidth size="small">
            <InputLabel>Sort By</InputLabel>
            <Select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              label="Sort By"
            >
              <MenuItem value="name">Name</MenuItem>
              <MenuItem value="rating">Rating</MenuItem>
              <MenuItem value="install_count">Popularity</MenuItem>
              <MenuItem value="created_at">Date Added</MenuItem>
              <MenuItem value="updated_at">Last Updated</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        <Grid item xs={12} sm={6} md={2}>
          <Button
            variant="outlined"
            startIcon={<FilterIcon />}
            onClick={() => {
              setShowOnlyFree(!showOnlyFree);
              setShowOnlyFeatured(false);
            }}
            color={showOnlyFree ? 'primary' : 'inherit'}
          >
            Free Only
          </Button>
        </Grid>
      </Grid>
    </Paper>
  );

  const renderStats = () => (
    <Grid container spacing={3} sx={{ mb: 3 }}>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Total Integrations
            </Typography>
            <Typography variant="h4">
              {stats?.total_integrations || 0}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Categories
            </Typography>
            <Typography variant="h4">
              {Object.keys(stats?.by_category || {}).length}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Free Integrations
            </Typography>
            <Typography variant="h4">
              {stats?.by_pricing?.free || 0}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Top Providers
            </Typography>
            <Typography variant="h4">
              {stats?.top_providers?.length || 0}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        Failed to load integration catalog: {error.message}
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Integration Catalog
      </Typography>

      <Tabs value={currentTab} onChange={handleTabChange} sx={{ mb: 3 }}>
        <Tab label="All Integrations" />
        <Tab label="Featured" />
        <Tab label="Popular" />
        <Tab label="Browse by Category" />
      </Tabs>

      <TabPanel value={currentTab} index={0}>
        {renderStats()}
        {renderFilters()}
        
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Grid container spacing={3}>
            {integrations?.integrations?.map(renderIntegrationCard)}
          </Grid>
        )}
      </TabPanel>

      <TabPanel value={currentTab} index={1}>
        <Typography variant="h5" gutterBottom>
          Featured Integrations
        </Typography>
        <Grid container spacing={3}>
          {featuredIntegrations?.map(renderIntegrationCard)}
        </Grid>
      </TabPanel>

      <TabPanel value={currentTab} index={2}>
        <Typography variant="h5" gutterBottom>
          Popular Integrations
        </Typography>
        <Grid container spacing={3}>
          {popularIntegrations?.map(renderIntegrationCard)}
        </Grid>
      </TabPanel>

      <TabPanel value={currentTab} index={3}>
        <Typography variant="h5" gutterBottom>
          Browse by Category
        </Typography>
        <Grid container spacing={2}>
          {categories?.map((category) => (
            <Grid item xs={12} sm={6} md={4} key={category.id}>
              <Card
                sx={{ cursor: 'pointer' }}
                onClick={() => {
                  setSelectedCategory(category.slug);
                  setCurrentTab(0);
                }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <CategoryIcon sx={{ mr: 1, color: category.color }} />
                    <Typography variant="h6">
                      {category.display_name}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {category.description}
                  </Typography>
                  <Typography variant="caption" color="primary">
                    {category.integration_count} integrations
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </TabPanel>

      {/* Integration Details Dialog */}
      <Dialog
        open={!!selectedIntegration && !installDialogOpen}
        onClose={() => setSelectedIntegration(null)}
        maxWidth="md"
        fullWidth
      >
        {selectedIntegration && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="h6">
                  {selectedIntegration.display_name || selectedIntegration.name}
                </Typography>
                <IconButton onClick={() => setSelectedIntegration(null)}>
                  <CloseIcon />
                </IconButton>
              </Box>
            </DialogTitle>
            <DialogContent>
              <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                {selectedIntegration.logo_url && (
                  <img
                    src={selectedIntegration.logo_url}
                    alt={selectedIntegration.display_name}
                    style={{ width: 64, height: 64 }}
                  />
                )}
                <Box sx={{ flex: 1 }}>
                  <Typography variant="h6">
                    {selectedIntegration.provider_name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Version {selectedIntegration.version}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                    <Rating value={selectedIntegration.rating} readOnly size="small" />
                    <Typography variant="caption">
                      ({selectedIntegration.review_count} reviews)
                    </Typography>
                  </Box>
                </Box>
              </Box>

              <Typography variant="body1" paragraph>
                {selectedIntegration.description}
              </Typography>

              <Divider sx={{ my: 2 }} />

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Category
                  </Typography>
                  <Typography variant="body2">
                    {selectedIntegration.category}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Type
                  </Typography>
                  <Typography variant="body2">
                    {selectedIntegration.integration_type}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Setup Complexity
                  </Typography>
                  <Typography variant="body2">
                    {selectedIntegration.setup_complexity}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Pricing
                  </Typography>
                  <Typography variant="body2">
                    {selectedIntegration.pricing_model}
                  </Typography>
                </Grid>
              </Grid>

              {selectedIntegration.documentation_url && (
                <Box sx={{ mt: 2 }}>
                  <Button
                    variant="outlined"
                    startIcon={<LaunchIcon />}
                    href={selectedIntegration.documentation_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View Documentation
                  </Button>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedIntegration(null)}>
                Close
              </Button>
              <Button
                variant="contained"
                onClick={() => handleInstallClick(selectedIntegration)}
              >
                Install
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Installation Dialog */}
      <Dialog open={installDialogOpen} onClose={() => setInstallDialogOpen(false)}>
        <DialogTitle>
          Install {selectedIntegration?.display_name || selectedIntegration?.name}
        </DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Environment</InputLabel>
            <Select
              value={selectedEnvironment}
              onChange={(e) => setSelectedEnvironment(e.target.value)}
              label="Environment"
            >
              <MenuItem value="development">Development</MenuItem>
              <MenuItem value="staging">Staging</MenuItem>
              <MenuItem value="production">Production</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInstallDialogOpen(false)}>
            Cancel
          </Button>
          <Button variant="contained" onClick={handleInstallSubmit}>
            Install
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default IntegrationCatalog;