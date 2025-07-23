import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Grid,
  TextField,
  InputAdornment,
  Chip,
  Avatar,
  Rating,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  Alert,
  Skeleton,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Badge,
} from '@mui/material';
import {
  Search,
  FilterList,
  Star,
  Download,
  Visibility,
  Share,
  Favorite,
  FavoriteBorder,
  Category,
  TrendingUp,
  AccessTime,
  Person,
  Code,
  PlayArrow,
  GetApp,
  ExpandMore,
  Verified,
  Public,
  Lock,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import {
  useGetDesignerTemplatesQuery,
  useCreateDesignerTemplateMutation,
  useGetDesignerWorkflowQuery,
  WorkflowTemplate,
  WorkflowDesignerState,
} from '../store/api/workflowApi';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`marketplace-tabpanel-${index}`}
    aria-labelledby={`marketplace-tab-${index}`}
  >
    {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
  </div>
);

const WorkflowMarketplace: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate | null>(null);
  const [showTemplateDetails, setShowTemplateDetails] = useState(false);
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());

  // Publish form state
  const [publishForm, setPublishForm] = useState({
    workflowId: '',
    name: '',
    description: '',
    category: '',
    tags: [] as string[],
    is_public: true,
    is_featured: false,
  });

  // API hooks
  const { data: templatesData, isLoading: templatesLoading } = useGetDesignerTemplatesQuery({
    category: selectedCategory === 'all' ? undefined : selectedCategory,
    search: searchTerm || undefined,
    page: 1,
    page_size: 50,
  });

  const [createDesignerTemplate] = useCreateDesignerTemplateMutation();

  // Computed values
  const templates = templatesData?.templates || [];
  const categories = useMemo(() => {
    const categorySet = new Set(templates.map(t => t.category));
    return Array.from(categorySet).sort();
  }, [templates]);

  const filteredTemplates = useMemo(() => {
    let filtered = templates;

    if (searchTerm) {
      filtered = filtered.filter(template =>
        template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        template.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        template.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    return filtered;
  }, [templates, searchTerm]);

  const featuredTemplates = useMemo(() => 
    filteredTemplates.filter(t => t.is_featured),
    [filteredTemplates]
  );

  const popularTemplates = useMemo(() => 
    filteredTemplates.sort((a, b) => b.usage_count - a.usage_count).slice(0, 10),
    [filteredTemplates]
  );

  const recentTemplates = useMemo(() => 
    filteredTemplates.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 10),
    [filteredTemplates]
  );

  // Event handlers
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleTemplateClick = (template: WorkflowTemplate) => {
    setSelectedTemplate(template);
    setShowTemplateDetails(true);
  };

  const handleUseTemplate = useCallback(async (template: WorkflowTemplate) => {
    try {
      // Navigate to workflow designer with the template
      navigate(`/workflows/designer?template=${template.template_id}`);
    } catch (error) {
      console.error('Failed to use template:', error);
    }
  }, [navigate]);

  const handleDownloadTemplate = useCallback(async (template: WorkflowTemplate) => {
    try {
      const blob = new Blob([JSON.stringify(template.workflow_state, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${template.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_template.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download template:', error);
    }
  }, []);

  const handleToggleFavorite = (templateId: string) => {
    setFavorites(prev => {
      const newFavorites = new Set(prev);
      if (newFavorites.has(templateId)) {
        newFavorites.delete(templateId);
      } else {
        newFavorites.add(templateId);
      }
      return newFavorites;
    });
  };

  const handlePublishTemplate = useCallback(async () => {
    try {
      await createDesignerTemplate({
        template_id: '',
        name: publishForm.name,
        description: publishForm.description,
        category: publishForm.category,
        tags: publishForm.tags,
        workflow_state: {} as WorkflowDesignerState, // This should be populated with actual workflow data
        is_public: publishForm.is_public,
        is_featured: publishForm.is_featured,
        usage_count: 0,
        rating: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      setShowPublishDialog(false);
      setPublishForm({
        workflowId: '',
        name: '',
        description: '',
        category: '',
        tags: [],
        is_public: true,
        is_featured: false,
      });
    } catch (error) {
      console.error('Failed to publish template:', error);
    }
  }, [publishForm, createDesignerTemplate]);

  const renderTemplateCard = (template: WorkflowTemplate) => (
    <Card
      key={template.template_id}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        cursor: 'pointer',
        transition: 'transform 0.2s, box-shadow 0.2s',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: 3,
        },
      }}
      onClick={() => handleTemplateClick(template)}
    >
      <CardContent sx={{ flex: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
          <Typography variant="h6" component="h2" sx={{ fontWeight: 'bold' }}>
            {template.name}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {template.is_featured && (
              <Tooltip title="Featured">
                <Verified color="primary" fontSize="small" />
              </Tooltip>
            )}
            {template.is_public ? (
              <Tooltip title="Public">
                <Public fontSize="small" color="action" />
              </Tooltip>
            ) : (
              <Tooltip title="Private">
                <Lock fontSize="small" color="action" />
              </Tooltip>
            )}
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                handleToggleFavorite(template.template_id);
              }}
            >
              {favorites.has(template.template_id) ? (
                <Favorite color="error" fontSize="small" />
              ) : (
                <FavoriteBorder fontSize="small" />
              )}
            </IconButton>
          </Box>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {template.description}
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Rating value={template.rating} precision={0.5} size="small" readOnly />
          <Typography variant="caption" color="text.secondary">
            ({template.usage_count} uses)
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
          <Chip label={template.category} size="small" color="primary" />
          {template.tags.slice(0, 3).map((tag) => (
            <Chip key={tag} label={tag} size="small" variant="outlined" />
          ))}
          {template.tags.length > 3 && (
            <Chip label={`+${template.tags.length - 3} more`} size="small" variant="outlined" />
          )}
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Avatar sx={{ width: 24, height: 24 }}>
            <Person fontSize="small" />
          </Avatar>
          <Typography variant="caption" color="text.secondary">
            {template.created_by || 'Anonymous'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            • {new Date(template.created_at).toLocaleDateString()}
          </Typography>
        </Box>
      </CardContent>

      <CardActions sx={{ p: 2, pt: 0 }}>
        <Button
          size="small"
          startIcon={<PlayArrow />}
          onClick={(e) => {
            e.stopPropagation();
            handleUseTemplate(template);
          }}
        >
          Use Template
        </Button>
        <Button
          size="small"
          startIcon={<Download />}
          onClick={(e) => {
            e.stopPropagation();
            handleDownloadTemplate(template);
          }}
        >
          Download
        </Button>
      </CardActions>
    </Card>
  );

  const renderTemplateGrid = (templates: WorkflowTemplate[]) => (
    <Grid container spacing={3}>
      {templatesLoading ? (
        Array.from({ length: 8 }).map((_, index) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={index}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Skeleton variant="text" width="80%" height={32} />
                <Skeleton variant="text" width="100%" height={20} />
                <Skeleton variant="text" width="60%" height={20} />
                <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                  <Skeleton variant="rounded" width={60} height={24} />
                  <Skeleton variant="rounded" width={60} height={24} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))
      ) : templates.length === 0 ? (
        <Grid item xs={12}>
          <Alert severity="info">
            No templates found matching your criteria. Try adjusting your search or filters.
          </Alert>
        </Grid>
      ) : (
        templates.map((template) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={template.template_id}>
            {renderTemplateCard(template)}
          </Grid>
        ))
      )}
    </Grid>
  );

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Workflow Marketplace
        </Typography>
        <Button
          variant="contained"
          onClick={() => setShowPublishDialog(true)}
          startIcon={<Share />}
        >
          Publish Template
        </Button>
      </Box>

      {/* Search and Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <TextField
            placeholder="Search templates..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
            sx={{ flex: 1 }}
          />
          <FormControl sx={{ minWidth: 120 }}>
            <InputLabel>Category</InputLabel>
            <Select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              label="Category"
            >
              <MenuItem value="all">All Categories</MenuItem>
              {categories.map((category) => (
                <MenuItem key={category} value={category}>
                  {category}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Paper>

      {/* Tabs */}
      <Tabs value={activeTab} onChange={handleTabChange} sx={{ mb: 3 }}>
        <Tab label="Browse All" />
        <Tab label="Featured" />
        <Tab label="Popular" />
        <Tab label="Recent" />
      </Tabs>

      {/* Content */}
      <TabPanel value={activeTab} index={0}>
        {renderTemplateGrid(filteredTemplates)}
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        {renderTemplateGrid(featuredTemplates)}
      </TabPanel>

      <TabPanel value={activeTab} index={2}>
        {renderTemplateGrid(popularTemplates)}
      </TabPanel>

      <TabPanel value={activeTab} index={3}>
        {renderTemplateGrid(recentTemplates)}
      </TabPanel>

      {/* Template Details Dialog */}
      <Dialog
        open={showTemplateDetails}
        onClose={() => setShowTemplateDetails(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {selectedTemplate?.name}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
            <Rating value={selectedTemplate?.rating} precision={0.5} size="small" readOnly />
            <Typography variant="body2" color="text.secondary">
              ({selectedTemplate?.usage_count} uses)
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedTemplate && (
            <Box>
              <Typography variant="body1" paragraph>
                {selectedTemplate.description}
              </Typography>

              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                <Chip label={selectedTemplate.category} color="primary" />
                {selectedTemplate.tags.map((tag) => (
                  <Chip key={tag} label={tag} variant="outlined" />
                ))}
              </Box>

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" gutterBottom>
                Workflow Details
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Nodes: {selectedTemplate.workflow_state.nodes?.length || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Connections: {selectedTemplate.workflow_state.connections?.length || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Version: {selectedTemplate.workflow_state.version}
              </Typography>

              <Divider sx={{ my: 2 }} />

              <Typography variant="body2" color="text.secondary">
                Created by: {selectedTemplate.created_by || 'Anonymous'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Created: {new Date(selectedTemplate.created_at).toLocaleDateString()}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Updated: {new Date(selectedTemplate.updated_at).toLocaleDateString()}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowTemplateDetails(false)}>Close</Button>
          <Button
            onClick={() => selectedTemplate && handleDownloadTemplate(selectedTemplate)}
            startIcon={<Download />}
          >
            Download
          </Button>
          <Button
            variant="contained"
            onClick={() => selectedTemplate && handleUseTemplate(selectedTemplate)}
            startIcon={<PlayArrow />}
          >
            Use Template
          </Button>
        </DialogActions>
      </Dialog>

      {/* Publish Template Dialog */}
      <Dialog
        open={showPublishDialog}
        onClose={() => setShowPublishDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Publish Workflow Template</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Template Name"
            value={publishForm.name}
            onChange={(e) => setPublishForm({ ...publishForm, name: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Description"
            value={publishForm.description}
            onChange={(e) => setPublishForm({ ...publishForm, description: e.target.value })}
            margin="normal"
            multiline
            rows={3}
          />
          <TextField
            fullWidth
            label="Category"
            value={publishForm.category}
            onChange={(e) => setPublishForm({ ...publishForm, category: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Tags (comma separated)"
            value={publishForm.tags.join(', ')}
            onChange={(e) => setPublishForm({ 
              ...publishForm, 
              tags: e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag) 
            })}
            margin="normal"
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Visibility</InputLabel>
            <Select
              value={publishForm.is_public ? 'public' : 'private'}
              onChange={(e) => setPublishForm({ ...publishForm, is_public: e.target.value === 'public' })}
              label="Visibility"
            >
              <MenuItem value="public">Public</MenuItem>
              <MenuItem value="private">Private</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowPublishDialog(false)}>Cancel</Button>
          <Button onClick={handlePublishTemplate} variant="contained">
            Publish
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default WorkflowMarketplace;