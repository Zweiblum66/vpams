/**
 * API Marketplace Component
 * Browse and install API integrations from the marketplace
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Rating,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Avatar,
  Divider,
  CircularProgress,
  Alert,
  Link
} from '@mui/material';
import {
  Search,
  FilterList,
  Star,
  GetApp,
  Visibility,
  Code,
  TestTube,
  Launch,
  Category,
  TrendingUp,
  NewReleases,
  Verified
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';

import { integrationApi } from '../../api/integrations';
import { APIListing, MarketplaceStats, APICategory } from '../../types/integration';
import { ConfigurationDialog } from './ConfigurationDialog';
import { ReviewDialog } from './ReviewDialog';
import { TestDialog } from './TestDialog';


interface APIMarketplaceProps {
  onInstall?: (integration: any) => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index, ...other }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`marketplace-tabpanel-${index}`}
      aria-labelledby={`marketplace-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export const APIMarketplace: React.FC<APIMarketplaceProps> = ({ onInstall }) => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [sortBy, setSortBy] = useState('popularity');
  const [selectedListing, setSelectedListing] = useState<APIListing | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [showConfiguration, setShowConfiguration] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [showTest, setShowTest] = useState(false);

  const queryClient = useQueryClient();

  // Fetch marketplace listings
  const { data: listings, isLoading: loadingListings, refetch } = useQuery({
    queryKey: ['marketplace-listings', searchQuery, selectedCategory, sortBy],
    queryFn: () => integrationApi.getMarketplaceListings({
      search: searchQuery || undefined,
      category: selectedCategory || undefined,
      sort: sortBy,
      limit: 50
    })
  });

  // Fetch marketplace categories
  const { data: categories } = useQuery({
    queryKey: ['marketplace-categories'],
    queryFn: integrationApi.getMarketplaceCategories
  });

  // Fetch marketplace stats
  const { data: stats } = useQuery({
    queryKey: ['marketplace-stats'],
    queryFn: integrationApi.getMarketplaceStats
  });

  // Fetch featured listings
  const { data: featuredListings } = useQuery({
    queryKey: ['marketplace-featured'],
    queryFn: () => integrationApi.getMarketplaceListings({ featured: true, limit: 6 })
  });

  // Install integration mutation
  const installMutation = useMutation({
    mutationFn: ({ listingId, config }: { listingId: string; config: any }) =>
      integrationApi.installMarketplaceIntegration(listingId, config),
    onSuccess: (data) => {
      toast.success('Integration installed successfully');
      queryClient.invalidateQueries({ queryKey: ['integrations'] });
      setShowConfiguration(false);
      onInstall?.(data);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to install integration');
    }
  });

  // Rate listing mutation
  const rateMutation = useMutation({
    mutationFn: ({ listingId, rating, review }: { listingId: string; rating: number; review?: string }) =>
      integrationApi.rateMarketplaceListing(listingId, rating, review),
    onSuccess: () => {
      toast.success('Rating submitted successfully');
      queryClient.invalidateQueries({ queryKey: ['marketplace-listings'] });
      setShowReview(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to submit rating');
    }
  });

  const handleInstall = (listing: APIListing) => {
    setSelectedListing(listing);
    setShowConfiguration(true);
  };

  const handleConfirmInstall = (config: any) => {
    if (selectedListing) {
      installMutation.mutate({
        listingId: selectedListing.id,
        config
      });
    }
  };

  const handleRate = (listing: APIListing) => {
    setSelectedListing(listing);
    setShowReview(true);
  };

  const handleSubmitRating = (rating: number, review?: string) => {
    if (selectedListing) {
      rateMutation.mutate({
        listingId: selectedListing.id,
        rating,
        review
      });
    }
  };

  const handleTest = (listing: APIListing) => {
    setSelectedListing(listing);
    setShowTest(true);
  };

  const handleViewDetails = (listing: APIListing) => {
    setSelectedListing(listing);
    setShowDetails(true);
  };

  const renderListingCard = (listing: APIListing) => (
    <Card key={listing.id} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <Avatar
            src={listing.provider_icon}
            sx={{ bgcolor: 'primary.main' }}
          >
            {listing.provider_name.charAt(0)}
          </Avatar>
          <Box flexGrow={1}>
            <Typography variant="h6" component="h3" noWrap>
              {listing.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              by {listing.provider_name}
            </Typography>
          </Box>
          {listing.featured && (
            <Chip
              icon={<Star />}
              label="Featured"
              color="primary"
              size="small"
            />
          )}
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {listing.short_description}
        </Typography>

        <Box display="flex" alignItems="center" gap={1} mb={2}>
          <Rating value={listing.rating_average} precision={0.1} readOnly size="small" />
          <Typography variant="body2" color="text.secondary">
            ({listing.rating_count})
          </Typography>
          <Chip label={listing.category} size="small" variant="outlined" />
        </Box>

        <Box display="flex" gap={1} mb={2} flexWrap="wrap">
          {listing.tags?.slice(0, 3).map((tag) => (
            <Chip key={tag} label={tag} size="small" variant="outlined" />
          ))}
        </Box>

        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="body2" color="text.secondary">
            {listing.install_count} installs
          </Typography>
          <Chip
            label={listing.pricing_model}
            color={listing.pricing_model === 'free' ? 'success' : 'default'}
            size="small"
          />
        </Box>
      </CardContent>

      <CardActions>
        <Button
          size="small"
          onClick={() => handleViewDetails(listing)}
          startIcon={<Visibility />}
        >
          Details
        </Button>
        <Button
          size="small"
          onClick={() => handleTest(listing)}
          startIcon={<TestTube />}
        >
          Test
        </Button>
        <Button
          variant="contained"
          size="small"
          onClick={() => handleInstall(listing)}
          startIcon={<GetApp />}
          disabled={installMutation.isPending}
        >
          Install
        </Button>
      </CardActions>
    </Card>
  );

  const renderStatsCard = (title: string, value: number, icon: React.ReactNode, color: string) => (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" gap={2}>
          <Box sx={{ color: color }}>{icon}</Box>
          <Box>
            <Typography variant="h4">{value.toLocaleString()}</Typography>
            <Typography variant="body2" color="text.secondary">
              {title}
            </Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );

  return (
    <Box>
      {/* Header */}
      <Box mb={4}>
        <Typography variant="h4" gutterBottom>
          API Marketplace
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Discover and install API integrations to extend your MAMS capabilities
        </Typography>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={selectedTab} onChange={(_, newValue) => setSelectedTab(newValue)}>
          <Tab label="Browse" icon={<Search />} />
          <Tab label="Featured" icon={<Star />} />
          <Tab label="Categories" icon={<Category />} />
          <Tab label="Stats" icon={<TrendingUp />} />
        </Tabs>
      </Box>

      {/* Browse Tab */}
      <TabPanel value={selectedTab} index={0}>
        {/* Search and Filters */}
        <Box display="flex" gap={2} mb={3} flexWrap="wrap">
          <TextField
            placeholder="Search integrations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
            }}
            sx={{ minWidth: 300 }}
          />
          <FormControl sx={{ minWidth: 150 }}>
            <InputLabel>Category</InputLabel>
            <Select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              label="Category"
            >
              <MenuItem value="">All Categories</MenuItem>
              {categories?.map((category: APICategory) => (
                <MenuItem key={category.id} value={category.name}>
                  {category.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl sx={{ minWidth: 150 }}>
            <InputLabel>Sort By</InputLabel>
            <Select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              label="Sort By"
            >
              <MenuItem value="popularity">Popularity</MenuItem>
              <MenuItem value="rating">Rating</MenuItem>
              <MenuItem value="created_at">Newest</MenuItem>
              <MenuItem value="name">Name</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {/* Listings Grid */}
        {loadingListings ? (
          <Box display="flex" justifyContent="center" p={4}>
            <CircularProgress />
          </Box>
        ) : (
          <Grid container spacing={3}>
            {listings?.data?.map((listing: APIListing) => (
              <Grid item xs={12} sm={6} md={4} key={listing.id}>
                {renderListingCard(listing)}
              </Grid>
            ))}
          </Grid>
        )}

        {listings?.data?.length === 0 && (
          <Alert severity="info" sx={{ mt: 2 }}>
            No integrations found. Try adjusting your search criteria.
          </Alert>
        )}
      </TabPanel>

      {/* Featured Tab */}
      <TabPanel value={selectedTab} index={1}>
        <Typography variant="h5" gutterBottom>
          Featured Integrations
        </Typography>
        <Grid container spacing={3}>
          {featuredListings?.data?.map((listing: APIListing) => (
            <Grid item xs={12} sm={6} md={4} key={listing.id}>
              {renderListingCard(listing)}
            </Grid>
          ))}
        </Grid>
      </TabPanel>

      {/* Categories Tab */}
      <TabPanel value={selectedTab} index={2}>
        <Typography variant="h5" gutterBottom>
          Browse by Category
        </Typography>
        <Grid container spacing={3}>
          {categories?.map((category: APICategory) => (
            <Grid item xs={12} sm={6} md={4} key={category.id}>
              <Card 
                sx={{ cursor: 'pointer' }}
                onClick={() => {
                  setSelectedCategory(category.name);
                  setSelectedTab(0);
                }}
              >
                <CardContent>
                  <Box display="flex" alignItems="center" gap={2} mb={2}>
                    {category.icon && (
                      <Box sx={{ color: category.color || 'primary.main' }}>
                        <Category />
                      </Box>
                    )}
                    <Typography variant="h6">{category.name}</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" mb={2}>
                    {category.description}
                  </Typography>
                  <Typography variant="body2">
                    {category.listing_count} integrations
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </TabPanel>

      {/* Stats Tab */}
      <TabPanel value={selectedTab} index={3}>
        <Typography variant="h5" gutterBottom>
          Marketplace Statistics
        </Typography>
        <Grid container spacing={3}>
          {stats && (
            <>
              <Grid item xs={12} sm={6} md={3}>
                {renderStatsCard(
                  'Total Integrations',
                  stats.total_listings,
                  <Code />,
                  'primary.main'
                )}
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                {renderStatsCard(
                  'Total Installs',
                  stats.total_installs,
                  <GetApp />,
                  'success.main'
                )}
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                {renderStatsCard(
                  'Categories',
                  stats.categories?.length || 0,
                  <Category />,
                  'info.main'
                )}
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                {renderStatsCard(
                  'Featured',
                  stats.featured_count || 0,
                  <Star />,
                  'warning.main'
                )}
              </Grid>
            </>
          )}
        </Grid>
      </TabPanel>

      {/* Listing Details Dialog */}
      <Dialog
        open={showDetails}
        onClose={() => setShowDetails(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={2}>
            <Avatar src={selectedListing?.provider_icon}>
              {selectedListing?.provider_name.charAt(0)}
            </Avatar>
            <Box>
              <Typography variant="h6">{selectedListing?.name}</Typography>
              <Typography variant="body2" color="text.secondary">
                by {selectedListing?.provider_name}
              </Typography>
            </Box>
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedListing && (
            <>
              <Typography variant="body1" paragraph>
                {selectedListing.description}
              </Typography>
              
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <Rating value={selectedListing.rating_average} precision={0.1} readOnly />
                <Typography variant="body2">
                  {selectedListing.rating_average}/5 ({selectedListing.rating_count} reviews)
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" gutterBottom>
                Details
              </Typography>
              <Box mb={2}>
                <Typography variant="body2" color="text.secondary">
                  Version: {selectedListing.version}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  API Type: {selectedListing.api_type.toUpperCase()}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Authentication: {selectedListing.authentication_type}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Installs: {selectedListing.install_count}
                </Typography>
              </Box>

              {selectedListing.documentation_url && (
                <Box mb={2}>
                  <Link
                    href={selectedListing.documentation_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View Documentation <Launch sx={{ fontSize: 16, ml: 0.5 }} />
                  </Link>
                </Box>
              )}

              <Box display="flex" gap={1} flexWrap="wrap">
                {selectedListing.tags?.map((tag) => (
                  <Chip key={tag} label={tag} size="small" variant="outlined" />
                ))}
              </Box>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDetails(false)}>Close</Button>
          <Button onClick={() => selectedListing && handleRate(selectedListing)}>
            Rate & Review
          </Button>
          <Button
            variant="contained"
            onClick={() => selectedListing && handleInstall(selectedListing)}
            startIcon={<GetApp />}
          >
            Install
          </Button>
        </DialogActions>
      </Dialog>

      {/* Configuration Dialog */}
      {selectedListing && (
        <ConfigurationDialog
          open={showConfiguration}
          onClose={() => setShowConfiguration(false)}
          listing={selectedListing}
          onConfirm={handleConfirmInstall}
          isInstalling={installMutation.isPending}
        />
      )}

      {/* Review Dialog */}
      {selectedListing && (
        <ReviewDialog
          open={showReview}
          onClose={() => setShowReview(false)}
          listing={selectedListing}
          onSubmit={handleSubmitRating}
          isSubmitting={rateMutation.isPending}
        />
      )}

      {/* Test Dialog */}
      {selectedListing && (
        <TestDialog
          open={showTest}
          onClose={() => setShowTest(false)}
          listing={selectedListing}
        />
      )}
    </Box>
  );
};