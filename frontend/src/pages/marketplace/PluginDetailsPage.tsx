import React, { useState } from 'react';
import {
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Button,
  Chip,
  Rating,
  Box,
  Tabs,
  Tab,
  Stack,
  Avatar,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Paper,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  LinearProgress,
  IconButton,
  Breadcrumbs,
  Link
} from '@mui/material';
import {
  Download as DownloadIcon,
  Star as StarIcon,
  Verified as VerifiedIcon,
  Extension as ExtensionIcon,
  Code as CodeIcon,
  Description as DescriptionIcon,
  BugReport as BugReportIcon,
  Security as SecurityIcon,
  ArrowBack as ArrowBackIcon,
  Share as ShareIcon,
  Favorite as FavoriteIcon,
  FavoriteBorder as FavoriteBorderIcon,
  Launch as LaunchIcon,
  Close as CloseIcon,
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  useGetPluginDetailsQuery,
  useInstallPluginFromMarketplaceMutation,
  useUninstallPluginFromMarketplaceMutation,
  useAddPluginReviewMutation
} from '../../store/api/marketplaceApi';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Loading } from '../../components/Loading/RTKQueryLoading';

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
      id={`plugin-details-tabpanel-${index}`}
      aria-labelledby={`plugin-details-tab-${index}`}
      {...other}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

export const PluginDetailsPage: React.FC = () => {
  const { pluginId } = useParams<{ pluginId: string }>();
  const navigate = useNavigate();
  
  // State
  const [currentTab, setCurrentTab] = useState(0);
  const [installDialogOpen, setInstallDialogOpen] = useState(false);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [reviewRating, setReviewRating] = useState<number>(5);
  const [reviewTitle, setReviewTitle] = useState('');
  const [reviewComment, setReviewComment] = useState('');

  // API calls
  const { data: plugin, isLoading, error } = useGetPluginDetailsQuery(pluginId!);
  const [installPlugin, { isLoading: installing }] = useInstallPluginFromMarketplaceMutation();
  const [uninstallPlugin, { isLoading: uninstalling }] = useUninstallPluginFromMarketplaceMutation();
  const [addReview] = useAddPluginReviewMutation();

  if (isLoading) {
    return <Loading />;
  }

  if (error || !plugin) {
    return (
      <Container maxWidth="lg">
        <Alert severity="error" sx={{ mt: 2 }}>
          Plugin not found or failed to load.
        </Alert>
      </Container>
    );
  }

  const handleInstall = async () => {
    try {
      await installPlugin({ plugin_id: plugin.id }).unwrap();
      setInstallDialogOpen(false);
    } catch (error) {
      console.error('Installation failed:', error);
    }
  };

  const handleUninstall = async () => {
    try {
      await uninstallPlugin({ plugin_id: plugin.id }).unwrap();
    } catch (error) {
      console.error('Uninstallation failed:', error);
    }
  };

  const handleSubmitReview = async () => {
    try {
      await addReview({
        plugin_id: plugin.id,
        review: {
          rating: reviewRating,
          title: reviewTitle,
          comment: reviewComment
        }
      }).unwrap();
      
      setReviewDialogOpen(false);
      setReviewTitle('');
      setReviewComment('');
      setReviewRating(5);
    } catch (error) {
      console.error('Failed to submit review:', error);
    }
  };

  const getRatingDistributionPercentage = (rating: string): number => {
    const total = Object.values(plugin.rating_distribution).reduce((sum, count) => sum + count, 0);
    return total > 0 ? (plugin.rating_distribution[rating] / total) * 100 : 0;
  };

  return (
    <Container maxWidth="xl">
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link
          color="inherit"
          href="/marketplace"
          onClick={(e) => {
            e.preventDefault();
            navigate('/marketplace');
          }}
          sx={{ cursor: 'pointer' }}
        >
          Marketplace
        </Link>
        <Typography color="textPrimary">{plugin.name}</Typography>
      </Breadcrumbs>

      <Grid container spacing={3}>
        {/* Main Content */}
        <Grid item xs={12} lg={8}>
          {/* Plugin Header */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={3}>
                  <CardMedia
                    sx={{
                      height: 150,
                      bgcolor: 'grey.100',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: 1
                    }}
                  >
                    <ExtensionIcon sx={{ fontSize: 64, color: 'grey.400' }} />
                  </CardMedia>
                </Grid>
                <Grid item xs={12} sm={9}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <Typography variant="h4" component="h1">
                          {plugin.name}
                        </Typography>
                        {plugin.author_verified && (
                          <VerifiedIcon color="primary" sx={{ ml: 1 }} />
                        )}
                      </Box>
                      <Typography variant="h6" color="text.secondary" gutterBottom>
                        by {plugin.author}
                      </Typography>
                    </Box>
                    <Stack direction="row" spacing={1}>
                      <IconButton>
                        <ShareIcon />
                      </IconButton>
                      <IconButton>
                        <FavoriteBorderIcon />
                      </IconButton>
                    </Stack>
                  </Box>

                  <Typography variant="body1" paragraph>
                    {plugin.description}
                  </Typography>

                  <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
                    <Rating value={plugin.rating} precision={0.1} readOnly />
                    <Typography variant="body2">
                      {plugin.rating.toFixed(1)} ({plugin.total_reviews} reviews)
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {plugin.download_count.toLocaleString()} downloads
                    </Typography>
                  </Stack>

                  <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                    <Chip label={plugin.category} color="primary" variant="outlined" />
                    <Chip label={`v${plugin.version}`} variant="outlined" />
                    <Chip label={plugin.license} variant="outlined" />
                    {plugin.price === 0 && <Chip label="Free" color="success" />}
                  </Stack>

                  <Stack direction="row" spacing={2}>
                    {plugin.is_installed ? (
                      <>
                        <Button
                          variant="outlined"
                          color="error"
                          onClick={handleUninstall}
                          disabled={uninstalling}
                        >
                          {uninstalling ? 'Uninstalling...' : 'Uninstall'}
                        </Button>
                        <Chip 
                          label={`Installed (${plugin.installation_status})`} 
                          color="success"
                        />
                      </>
                    ) : (
                      <Button
                        variant="contained"
                        size="large"
                        startIcon={<DownloadIcon />}
                        onClick={() => setInstallDialogOpen(true)}
                        disabled={installing}
                      >
                        {installing ? 'Installing...' : 'Install Plugin'}
                      </Button>
                    )}
                    <Button
                      variant="outlined"
                      onClick={() => setReviewDialogOpen(true)}
                      disabled={!plugin.is_installed}
                    >
                      Write Review
                    </Button>
                  </Stack>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Plugin Details Tabs */}
          <Card>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={currentTab} onChange={(_, newValue) => setCurrentTab(newValue)}>
                <Tab label="Overview" icon={<DescriptionIcon />} />
                <Tab label="Reviews" icon={<StarIcon />} />
                <Tab label="Changelog" icon={<CodeIcon />} />
                <Tab label="Support" icon={<BugReportIcon />} />
              </Tabs>
            </Box>

            {/* Overview Tab */}
            <TabPanel value={currentTab} index={0}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Description
                </Typography>
                <Typography variant="body1" paragraph>
                  {plugin.long_description}
                </Typography>

                {plugin.screenshots.length > 0 && (
                  <>
                    <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                      Screenshots
                    </Typography>
                    <Grid container spacing={2}>
                      {plugin.screenshots.map((screenshot, index) => (
                        <Grid item xs={12} sm={6} md={4} key={index}>
                          <CardMedia
                            component="img"
                            height={200}
                            image={screenshot}
                            alt={`Screenshot ${index + 1}`}
                            sx={{ borderRadius: 1 }}
                          />
                        </Grid>
                      ))}
                    </Grid>
                  </>
                )}

                {plugin.tags.length > 0 && (
                  <>
                    <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                      Tags
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                      {plugin.tags.map((tag) => (
                        <Chip key={tag} label={tag} size="small" />
                      ))}
                    </Stack>
                  </>
                )}

                <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                  Requirements
                </Typography>
                {Object.keys(plugin.requirements).length > 0 ? (
                  <Box component="pre" sx={{ bgcolor: 'grey.100', p: 2, borderRadius: 1, overflow: 'auto' }}>
                    {JSON.stringify(plugin.requirements, null, 2)}
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No specific requirements
                  </Typography>
                )}
              </CardContent>
            </TabPanel>

            {/* Reviews Tab */}
            <TabPanel value={currentTab} index={1}>
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 3, textAlign: 'center' }}>
                      <Typography variant="h2" color="primary">
                        {plugin.rating.toFixed(1)}
                      </Typography>
                      <Rating value={plugin.rating} precision={0.1} readOnly />
                      <Typography variant="body2" color="text.secondary">
                        Based on {plugin.total_reviews} reviews
                      </Typography>
                    </Paper>

                    <Box sx={{ mt: 2 }}>
                      {[5, 4, 3, 2, 1].map((rating) => (
                        <Box key={rating} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                          <Typography variant="body2" sx={{ minWidth: '3ch' }}>
                            {rating}★
                          </Typography>
                          <LinearProgress
                            variant="determinate"
                            value={getRatingDistributionPercentage(rating.toString())}
                            sx={{ flexGrow: 1, mx: 1 }}
                          />
                          <Typography variant="body2" sx={{ minWidth: '4ch' }}>
                            {plugin.rating_distribution[rating.toString()] || 0}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  </Grid>

                  <Grid item xs={12} md={8}>
                    <List>
                      {plugin.reviews.map((review) => (
                        <React.Fragment key={review.id}>
                          <ListItem alignItems="flex-start">
                            <ListItemAvatar>
                              <Avatar>{review.author[0]}</Avatar>
                            </ListItemAvatar>
                            <ListItemText
                              primary={
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  <Typography variant="subtitle2">
                                    {review.title}
                                  </Typography>
                                  <Rating value={review.rating} size="small" readOnly />
                                </Box>
                              }
                              secondary={
                                <Box>
                                  <Typography variant="body2" paragraph>
                                    {review.comment}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    by {review.author} • {new Date(review.created_at).toLocaleDateString()}
                                  </Typography>
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                                    <IconButton size="small">
                                      <ThumbUpIcon fontSize="small" />
                                    </IconButton>
                                    <Typography variant="caption">
                                      {review.helpful_count}
                                    </Typography>
                                    <IconButton size="small">
                                      <ThumbDownIcon fontSize="small" />
                                    </IconButton>
                                  </Box>
                                </Box>
                              }
                            />
                          </ListItem>
                          <Divider variant="inset" component="li" />
                        </React.Fragment>
                      ))}
                    </List>
                  </Grid>
                </Grid>
              </CardContent>
            </TabPanel>

            {/* Changelog Tab */}
            <TabPanel value={currentTab} index={2}>
              <CardContent>
                {plugin.changelog.length > 0 ? (
                  <List>
                    {plugin.changelog.map((entry, index) => (
                      <ListItem key={index} alignItems="flex-start">
                        <ListItemText
                          primary={`Version ${entry.version}`}
                          secondary={
                            <Box>
                              <Typography variant="body2" color="text.secondary">
                                {new Date(entry.date).toLocaleDateString()}
                              </Typography>
                              <List dense sx={{ ml: 2 }}>
                                {entry.changes.map((change, changeIndex) => (
                                  <ListItem key={changeIndex}>
                                    <Typography variant="body2">• {change}</Typography>
                                  </ListItem>
                                ))}
                              </List>
                            </Box>
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No changelog available
                  </Typography>
                )}
              </CardContent>
            </TabPanel>

            {/* Support Tab */}
            <TabPanel value={currentTab} index={3}>
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="h6" gutterBottom>
                      Links
                    </Typography>
                    <List>
                      {plugin.documentation_url && (
                        <ListItem>
                          <Button
                            startIcon={<LaunchIcon />}
                            href={plugin.documentation_url}
                            target="_blank"
                            rel="noopener"
                          >
                            Documentation
                          </Button>
                        </ListItem>
                      )}
                      {plugin.support_url && (
                        <ListItem>
                          <Button
                            startIcon={<BugReportIcon />}
                            href={plugin.support_url}
                            target="_blank"
                            rel="noopener"
                          >
                            Support
                          </Button>
                        </ListItem>
                      )}
                      {plugin.source_url && (
                        <ListItem>
                          <Button
                            startIcon={<CodeIcon />}
                            href={plugin.source_url}
                            target="_blank"
                            rel="noopener"
                          >
                            Source Code
                          </Button>
                        </ListItem>
                      )}
                    </List>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="h6" gutterBottom>
                      Developer Information
                    </Typography>
                    <Typography variant="body2" paragraph>
                      <strong>Author:</strong> {plugin.author}
                    </Typography>
                    <Typography variant="body2" paragraph>
                      <strong>License:</strong> {plugin.license}
                    </Typography>
                    <Typography variant="body2" paragraph>
                      <strong>Version:</strong> {plugin.version}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Last Updated:</strong> {new Date(plugin.updated_at).toLocaleDateString()}
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </TabPanel>
          </Card>
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} lg={4}>
          <Stack spacing={2}>
            {/* Quick Stats */}
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Plugin Statistics
                </Typography>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">Downloads</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {plugin.download_count.toLocaleString()}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">Rating</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {plugin.rating.toFixed(1)}/5
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">Reviews</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {plugin.total_reviews}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2">Price</Typography>
                  <Typography variant="body2" fontWeight="bold" color="success.main">
                    {plugin.price === 0 ? 'Free' : `$${plugin.price}`}
                  </Typography>
                </Box>
              </CardContent>
            </Card>

            {/* Security Info */}
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <SecurityIcon color="success" sx={{ mr: 1 }} />
                  <Typography variant="h6">
                    Security
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  This plugin has been reviewed and verified for security compliance.
                </Typography>
              </CardContent>
            </Card>
          </Stack>
        </Grid>
      </Grid>

      {/* Install Dialog */}
      <Dialog open={installDialogOpen} onClose={() => setInstallDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Install Plugin</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            This plugin will be installed for your organization and available to all users.
          </Alert>
          <Typography variant="body2">
            Are you sure you want to install "{plugin.name}" version {plugin.version}?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInstallDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleInstall} disabled={installing}>
            {installing ? 'Installing...' : 'Install'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Review Dialog */}
      <Dialog open={reviewDialogOpen} onClose={() => setReviewDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Write a Review</DialogTitle>
        <DialogContent>
          <Box sx={{ py: 2 }}>
            <Typography variant="body2" gutterBottom>
              Rating
            </Typography>
            <Rating
              value={reviewRating}
              onChange={(_, newValue) => setReviewRating(newValue || 1)}
              size="large"
            />
            
            <TextField
              fullWidth
              label="Review Title"
              value={reviewTitle}
              onChange={(e) => setReviewTitle(e.target.value)}
              margin="normal"
            />
            
            <TextField
              fullWidth
              label="Review Comment"
              value={reviewComment}
              onChange={(e) => setReviewComment(e.target.value)}
              multiline
              rows={4}
              margin="normal"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReviewDialogOpen(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            onClick={handleSubmitReview}
            disabled={!reviewTitle || !reviewComment}
          >
            Submit Review
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default PluginDetailsPage;