import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  CardMedia,
  CardActions,
  Button,
  Chip,
  Rating,
  Box,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab,
  Stack,
  Avatar,
  IconButton,
  Tooltip,
  Badge,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Skeleton
} from '@mui/material';
import {
  Search as SearchIcon,
  Star as StarIcon,
  Download as DownloadIcon,
  Category as CategoryIcon,
  Extension as ExtensionIcon,
  Verified as VerifiedIcon,
  Info as InfoIcon,
  Close as CloseIcon,
  TrendingUp as TrendingUpIcon,
  FilterList as FilterListIcon,
  Sort as SortIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { 
  useGetFeaturedPluginsQuery,
  useSearchMarketplacePluginsQuery,
  useGetPluginCategoriesQuery,
  useGetPopularPluginsQuery,
  useGetMarketplaceStatsQuery,
  useInstallPluginFromMarketplaceMutation
} from '../../store/api/marketplaceApi';

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
      id={`marketplace-tabpanel-${index}`}
      aria-labelledby={`marketplace-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const PLUGIN_TYPE_LABELS: Record<string, string> = {
  processor: 'Processor',
  storage: 'Storage',
  metadata: 'Metadata',
  workflow: 'Workflow',
  search: 'Search',
  export: 'Export',
  analytics: 'Analytics',
  notification: 'Notification',
  authentication: 'Authentication',
  ingest: 'Ingest',
  ui_component: 'UI Component',
  api_extension: 'API Extension'
};

export const MarketplacePage: React.FC = () => {
  const navigate = useNavigate();
  
  // State
  const [currentTab, setCurrentTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedPluginType, setSelectedPluginType] = useState('');
  const [minRating, setMinRating] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState('relevance');
  const [selectedPlugin, setSelectedPlugin] = useState<any>(null);
  const [installDialogOpen, setInstallDialogOpen] = useState(false);

  // API calls
  const { data: featuredPlugins, isLoading: featuredLoading } = useGetFeaturedPluginsQuery();
  const { data: popularPlugins, isLoading: popularLoading } = useGetPopularPluginsQuery({ limit: 8 });
  const { data: categories } = useGetPluginCategoriesQuery();
  const { data: marketplaceStats } = useGetMarketplaceStatsQuery();
  
  const { data: searchResults, isLoading: searchLoading } = useSearchMarketplacePluginsQuery({
    query: searchQuery || undefined,
    category: selectedCategory || undefined,
    plugin_type: selectedPluginType || undefined,
    min_rating: minRating || undefined,
    sort_by: sortBy,
    page: 1,
    limit: 20
  });

  const [installPlugin] = useInstallPluginFromMarketplaceMutation();

  const handleInstallPlugin = async (pluginId: string) => {
    try {
      await installPlugin({ plugin_id: pluginId }).unwrap();
      setInstallDialogOpen(false);
      // Show success message or refresh data
    } catch (error) {
      console.error('Failed to install plugin:', error);
    }
  };

  const handlePluginClick = (plugin: any) => {
    navigate(`/marketplace/plugins/${plugin.id}`);
  };

  const PluginCard = ({ plugin, featured = false }: { plugin: any; featured?: boolean }) => (
    <Card 
      sx={{ 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column',
        cursor: 'pointer',
        '&:hover': { boxShadow: 4 }
      }}
      onClick={() => handlePluginClick(plugin)}
    >
      {featured && (
        <Box sx={{ position: 'relative' }}>
          <Chip
            label="Featured"
            color="primary"
            size="small"
            sx={{ position: 'absolute', top: 8, right: 8, zIndex: 1 }}
          />
        </Box>
      )}
      
      <CardMedia
        sx={{ 
          height: featured ? 200 : 140, 
          bgcolor: 'grey.100',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        <ExtensionIcon sx={{ fontSize: 48, color: 'grey.400' }} />
      </CardMedia>
      
      <CardContent sx={{ flexGrow: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <Typography variant="h6" component="h3" noWrap sx={{ flexGrow: 1 }}>
            {plugin.name}
          </Typography>
          {plugin.author === 'Verified Developer' && (
            <Tooltip title="Verified Developer">
              <VerifiedIcon color="primary" sx={{ ml: 1 }} />
            </Tooltip>
          )}
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {plugin.description}
        </Typography>
        
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <Rating value={plugin.rating} precision={0.1} size="small" readOnly />
          <Typography variant="body2" color="text.secondary">
            ({plugin.download_count.toLocaleString()})
          </Typography>
        </Stack>
        
        <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
          <Chip 
            label={plugin.category} 
            size="small" 
            variant="outlined"
            color="primary"
          />
          <Chip 
            label={PLUGIN_TYPE_LABELS[plugin.plugin_type] || plugin.plugin_type} 
            size="small" 
            variant="outlined"
          />
        </Stack>
        
        <Typography variant="caption" color="text.secondary">
          by {plugin.author}
        </Typography>
      </CardContent>
      
      <CardActions>
        <Button
          size="small"
          startIcon={<DownloadIcon />}
          onClick={(e) => {
            e.stopPropagation();
            setSelectedPlugin(plugin);
            setInstallDialogOpen(true);
          }}
        >
          Install
        </Button>
        <Button size="small" onClick={(e) => e.stopPropagation()}>
          Details
        </Button>
      </CardActions>
    </Card>
  );

  return (
    <Container maxWidth="xl">
      <PageHeader
        title="Plugin Marketplace"
        subtitle="Discover and install plugins to extend MAMS functionality"
      />

      {/* Marketplace Stats */}
      {marketplaceStats && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="primary">
                    {marketplaceStats.total_plugins}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Plugins
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="success.main">
                    {marketplaceStats.total_downloads.toLocaleString()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Downloads
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="warning.main">
                    {marketplaceStats.average_rating}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Average Rating
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="info.main">
                    {marketplaceStats.total_categories}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Categories
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Search and Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                placeholder="Search plugins..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <InputLabel>Category</InputLabel>
                <Select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  label="Category"
                >
                  <MenuItem value="">All Categories</MenuItem>
                  {categories?.map((category) => (
                    <MenuItem key={category.id} value={category.name}>
                      {category.name} ({category.plugin_count})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <InputLabel>Plugin Type</InputLabel>
                <Select
                  value={selectedPluginType}
                  onChange={(e) => setSelectedPluginType(e.target.value)}
                  label="Plugin Type"
                >
                  <MenuItem value="">All Types</MenuItem>
                  {Object.entries(PLUGIN_TYPE_LABELS).map(([key, label]) => (
                    <MenuItem key={key} value={key}>
                      {label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <InputLabel>Min Rating</InputLabel>
                <Select
                  value={minRating || ''}
                  onChange={(e) => setMinRating(e.target.value ? Number(e.target.value) : null)}
                  label="Min Rating"
                >
                  <MenuItem value="">Any Rating</MenuItem>
                  <MenuItem value={4}>4+ Stars</MenuItem>
                  <MenuItem value={3}>3+ Stars</MenuItem>
                  <MenuItem value={2}>2+ Stars</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <InputLabel>Sort By</InputLabel>
                <Select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  label="Sort By"
                >
                  <MenuItem value="relevance">Relevance</MenuItem>
                  <MenuItem value="rating">Rating</MenuItem>
                  <MenuItem value="downloads">Downloads</MenuItem>
                  <MenuItem value="newest">Newest</MenuItem>
                  <MenuItem value="oldest">Oldest</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={currentTab} onChange={(_, newValue) => setCurrentTab(newValue)}>
          <Tab label="Featured" icon={<StarIcon />} />
          <Tab label="Popular" icon={<TrendingUpIcon />} />
          <Tab label="All Plugins" icon={<ExtensionIcon />} />
          <Tab label="Categories" icon={<CategoryIcon />} />
        </Tabs>
      </Box>

      {/* Featured Plugins Tab */}
      <TabPanel value={currentTab} index={0}>
        {featuredLoading ? (
          <Grid container spacing={3}>
            {[...Array(6)].map((_, index) => (
              <Grid item xs={12} sm={6} md={4} key={index}>
                <Skeleton variant="rectangular" height={300} />
              </Grid>
            ))}
          </Grid>
        ) : (
          <Grid container spacing={3}>
            {featuredPlugins?.map((plugin) => (
              <Grid item xs={12} sm={6} md={4} key={plugin.id}>
                <PluginCard plugin={plugin} featured />
              </Grid>
            ))}
          </Grid>
        )}
      </TabPanel>

      {/* Popular Plugins Tab */}
      <TabPanel value={currentTab} index={1}>
        {popularLoading ? (
          <Grid container spacing={3}>
            {[...Array(8)].map((_, index) => (
              <Grid item xs={12} sm={6} md={3} key={index}>
                <Skeleton variant="rectangular" height={250} />
              </Grid>
            ))}
          </Grid>
        ) : (
          <Grid container spacing={3}>
            {popularPlugins?.map((plugin) => (
              <Grid item xs={12} sm={6} md={3} key={plugin.id}>
                <PluginCard plugin={plugin} />
              </Grid>
            ))}
          </Grid>
        )}
      </TabPanel>

      {/* All Plugins Tab */}
      <TabPanel value={currentTab} index={2}>
        {searchLoading ? (
          <Grid container spacing={3}>
            {[...Array(12)].map((_, index) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={index}>
                <Skeleton variant="rectangular" height={250} />
              </Grid>
            ))}
          </Grid>
        ) : (
          <Grid container spacing={3}>
            {searchResults?.map((plugin) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={plugin.id}>
                <PluginCard plugin={plugin} />
              </Grid>
            ))}
          </Grid>
        )}
      </TabPanel>

      {/* Categories Tab */}
      <TabPanel value={currentTab} index={3}>
        <Grid container spacing={3}>
          {categories?.map((category) => (
            <Grid item xs={12} sm={6} md={4} key={category.id}>
              <Card sx={{ cursor: 'pointer', '&:hover': { boxShadow: 4 } }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
                      <CategoryIcon />
                    </Avatar>
                    <Box>
                      <Typography variant="h6">{category.name}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {category.plugin_count} plugins
                      </Typography>
                    </Box>
                  </Box>
                  <Typography variant="body2">
                    {category.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </TabPanel>

      {/* Install Plugin Dialog */}
      <Dialog
        open={installDialogOpen}
        onClose={() => setInstallDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Install Plugin
          <IconButton
            onClick={() => setInstallDialogOpen(false)}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selectedPlugin && (
            <Box>
              <Typography variant="h6" gutterBottom>
                {selectedPlugin.name}
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                {selectedPlugin.description}
              </Typography>
              <Typography variant="body2" paragraph>
                <strong>Author:</strong> {selectedPlugin.author}
              </Typography>
              <Typography variant="body2" paragraph>
                <strong>Version:</strong> {selectedPlugin.version}
              </Typography>
              <Typography variant="body2" paragraph>
                <strong>Category:</strong> {selectedPlugin.category}
              </Typography>
              
              <Alert severity="info" sx={{ mt: 2 }}>
                This plugin will be installed for your organization and will be available
                to all users with appropriate permissions.
              </Alert>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInstallDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={() => selectedPlugin && handleInstallPlugin(selectedPlugin.id)}
            startIcon={<DownloadIcon />}
          >
            Install Plugin
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default MarketplacePage;