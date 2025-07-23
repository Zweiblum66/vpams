import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  Tab,
  Tabs,
  TabPanel,
  Paper,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  Save as SaveIcon,
  PlayArrow as PlayIcon,
  Publish as PublishIcon,
  Code as CodeIcon,
  Settings as SettingsIcon,
  BugReport as BugReportIcon,
  Help as HelpIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { CodeEditor } from '../../components/developer/CodeEditor';
import { ValidationPanel } from '../../components/developer/ValidationPanel';
import { 
  useGetPluginTemplatesQuery,
  useCreatePluginDraftMutation,
  useUpdatePluginDraftMutation,
  useValidatePluginCodeMutation,
  usePublishPluginMutation
} from '../../store/api/developerApi';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function CustomTabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`plugin-editor-tabpanel-${index}`}
      aria-labelledby={`plugin-editor-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const PLUGIN_TYPES = [
  { value: 'processor', label: 'Processor Plugin' },
  { value: 'storage', label: 'Storage Plugin' },
  { value: 'metadata', label: 'Metadata Plugin' },
  { value: 'workflow', label: 'Workflow Plugin' },
  { value: 'search', label: 'Search Plugin' },
  { value: 'export', label: 'Export Plugin' },
  { value: 'analytics', label: 'Analytics Plugin' },
  { value: 'notification', label: 'Notification Plugin' },
  { value: 'authentication', label: 'Authentication Plugin' },
  { value: 'ingest', label: 'Ingest Plugin' },
  { value: 'ui_component', label: 'UI Component Plugin' },
  { value: 'api_extension', label: 'API Extension Plugin' }
];

const DEVELOPMENT_STEPS = [
  'Project Setup',
  'Code Implementation',
  'Configuration',
  'Testing & Validation',
  'Documentation',
  'Publishing'
];

export const PluginEditorPage: React.FC = () => {
  const { pluginId } = useParams();
  const navigate = useNavigate();
  const isEditing = Boolean(pluginId);

  // State
  const [currentTab, setCurrentTab] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [pluginData, setPluginData] = useState({
    name: '',
    description: '',
    plugin_type: '',
    version: '1.0.0',
    author: '',
    author_email: '',
    metadata: {}
  });

  const [codeFiles, setCodeFiles] = useState({
    'main.py': '',
    'plugin.json': '',
    'config.yaml': '',
    'requirements.txt': ''
  });

  const [validationResults, setValidationResults] = useState<any>(null);
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<any>(null);

  // API calls
  const { data: templates } = useGetPluginTemplatesQuery();
  const [createPlugin] = useCreatePluginDraftMutation();
  const [updatePlugin] = useUpdatePluginDraftMutation();
  const [validateCode] = useValidatePluginCodeMutation();
  const [publishPlugin] = usePublishPluginMutation();

  // Load template when plugin type changes
  useEffect(() => {
    if (pluginData.plugin_type && templates && !isEditing) {
      const template = templates.find(t => t.plugin_type === pluginData.plugin_type);
      if (template) {
        setSelectedTemplate(template);
        setCodeFiles(template.files);
        
        // Update plugin.json with current metadata
        const pluginJsonTemplate = JSON.parse(template.files['plugin.json'] || '{}');
        pluginJsonTemplate.metadata = {
          ...pluginJsonTemplate.metadata,
          id: pluginData.name.toLowerCase().replace(/\s+/g, '-'),
          name: pluginData.name,
          description: pluginData.description,
          author: pluginData.author
        };
        
        setCodeFiles(prev => ({
          ...prev,
          'plugin.json': JSON.stringify(pluginJsonTemplate, null, 2)
        }));
      }
    }
  }, [pluginData.plugin_type, templates, isEditing, pluginData.name, pluginData.description, pluginData.author]);

  const handleSave = async () => {
    try {
      if (isEditing) {
        await updatePlugin({ 
          pluginId: pluginId!, 
          plugin_data: pluginData 
        }).unwrap();
      } else {
        const result = await createPlugin({ plugin_data: pluginData }).unwrap();
        navigate(`/developer/editor/${result.plugin_id}`);
      }
    } catch (error) {
      console.error('Failed to save plugin:', error);
    }
  };

  const handleValidate = async () => {
    try {
      const result = await validateCode({ plugin_code: codeFiles }).unwrap();
      setValidationResults(result);
      setCurrentTab(2); // Switch to validation tab
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const handlePublish = async () => {
    if (pluginId) {
      try {
        await publishPlugin({ plugin_id: pluginId }).unwrap();
        setPublishDialogOpen(false);
        navigate('/developer/plugins');
      } catch (error) {
        console.error('Failed to publish plugin:', error);
      }
    }
  };

  const handleFileChange = (filename: string, content: string) => {
    setCodeFiles(prev => ({
      ...prev,
      [filename]: content
    }));
  };

  return (
    <Container maxWidth="xl">
      <PageHeader
        title={isEditing ? `Edit Plugin: ${pluginData.name}` : 'Create New Plugin'}
        subtitle="Build and publish plugins for the MAMS platform"
        action={
          <Stack direction="row" spacing={2}>
            <Button
              variant="outlined"
              startIcon={<BugReportIcon />}
              onClick={handleValidate}
            >
              Validate
            </Button>
            <Button
              variant="outlined"
              startIcon={<SaveIcon />}
              onClick={handleSave}
            >
              Save Draft
            </Button>
            {isEditing && (
              <Button
                variant="contained"
                startIcon={<PublishIcon />}
                onClick={() => setPublishDialogOpen(true)}
              >
                Publish
              </Button>
            )}
          </Stack>
        }
      />

      <Grid container spacing={3}>
        {/* Development Steps Sidebar */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Development Progress
              </Typography>
              <Stepper activeStep={currentStep} orientation="vertical">
                {DEVELOPMENT_STEPS.map((label, index) => (
                  <Step key={label}>
                    <StepLabel
                      onClick={() => setCurrentStep(index)}
                      sx={{ cursor: 'pointer' }}
                    >
                      {label}
                    </StepLabel>
                    <StepContent>
                      <Typography variant="body2" color="text.secondary">
                        {getStepDescription(index)}
                      </Typography>
                    </StepContent>
                  </Step>
                ))}
              </Stepper>
            </CardContent>
          </Card>
        </Grid>

        {/* Main Editor Area */}
        <Grid item xs={12} md={9}>
          <Card>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={currentTab} onChange={(_, newValue) => setCurrentTab(newValue)}>
                <Tab label="Project Setup" icon={<SettingsIcon />} />
                <Tab label="Code Editor" icon={<CodeIcon />} />
                <Tab label="Validation" icon={<BugReportIcon />} />
                <Tab label="Help" icon={<HelpIcon />} />
              </Tabs>
            </Box>

            {/* Project Setup Tab */}
            <CustomTabPanel value={currentTab} index={0}>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Plugin Name"
                    value={pluginData.name}
                    onChange={(e) => setPluginData(prev => ({ ...prev, name: e.target.value }))}
                    margin="normal"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth margin="normal">
                    <InputLabel>Plugin Type</InputLabel>
                    <Select
                      value={pluginData.plugin_type}
                      onChange={(e) => setPluginData(prev => ({ ...prev, plugin_type: e.target.value }))}
                    >
                      {PLUGIN_TYPES.map((type) => (
                        <MenuItem key={type.value} value={type.value}>
                          {type.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Description"
                    value={pluginData.description}
                    onChange={(e) => setPluginData(prev => ({ ...prev, description: e.target.value }))}
                    multiline
                    rows={3}
                    margin="normal"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Author"
                    value={pluginData.author}
                    onChange={(e) => setPluginData(prev => ({ ...prev, author: e.target.value }))}
                    margin="normal"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Author Email"
                    value={pluginData.author_email}
                    onChange={(e) => setPluginData(prev => ({ ...prev, author_email: e.target.value }))}
                    margin="normal"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Version"
                    value={pluginData.version}
                    onChange={(e) => setPluginData(prev => ({ ...prev, version: e.target.value }))}
                    margin="normal"
                  />
                </Grid>
              </Grid>

              {selectedTemplate && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Using template: {selectedTemplate.name}. The code editor has been populated with the template files.
                </Alert>
              )}
            </CustomTabPanel>

            {/* Code Editor Tab */}
            <CustomTabPanel value={currentTab} index={1}>
              <CodeEditor
                files={codeFiles}
                onFileChange={handleFileChange}
                pluginType={pluginData.plugin_type}
              />
            </CustomTabPanel>

            {/* Validation Tab */}
            <CustomTabPanel value={currentTab} index={2}>
              <ValidationPanel
                validationResults={validationResults}
                onValidate={handleValidate}
                codeFiles={codeFiles}
              />
            </CustomTabPanel>

            {/* Help Tab */}
            <CustomTabPanel value={currentTab} index={3}>
              <Stack spacing={3}>
                <Typography variant="h6">Plugin Development Guide</Typography>
                
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Getting Started</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2">
                      Learn the basics of MAMS plugin development, including architecture overview
                      and supported plugin types.
                    </Typography>
                  </AccordionDetails>
                </Accordion>

                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Plugin Types</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Stack spacing={2}>
                      {PLUGIN_TYPES.map((type) => (
                        <Box key={type.value}>
                          <Typography variant="subtitle2">{type.label}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            {getPluginTypeDescription(type.value)}
                          </Typography>
                        </Box>
                      ))}
                    </Stack>
                  </AccordionDetails>
                </Accordion>

                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>API Reference</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2">
                      Detailed documentation for plugin base classes, hook system, and event handling.
                    </Typography>
                  </AccordionDetails>
                </Accordion>

                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Best Practices</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2">
                      Security guidelines, performance optimization tips, and proper error handling.
                    </Typography>
                  </AccordionDetails>
                </Accordion>
              </Stack>
            </CustomTabPanel>
          </Card>
        </Grid>
      </Grid>

      {/* Publish Dialog */}
      <Dialog open={publishDialogOpen} onClose={() => setPublishDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Publish Plugin to Marketplace</DialogTitle>
        <DialogContent>
          <Typography variant="body1" paragraph>
            Are you ready to publish this plugin to the MAMS marketplace? Once published, it will be
            available for other users to install and use.
          </Typography>
          
          <Alert severity="info">
            Your plugin will be reviewed by our team before being made publicly available.
            This process typically takes 1-3 business days.
          </Alert>

          {validationResults && !validationResults.valid && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Your plugin has validation errors. Please fix them before publishing.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPublishDialogOpen(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            onClick={handlePublish}
            disabled={validationResults && !validationResults.valid}
          >
            Publish Plugin
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

// Helper functions
function getStepDescription(step: number): string {
  const descriptions = [
    'Configure plugin metadata and basic settings',
    'Write your plugin code using our templates and examples',
    'Set up plugin configuration and requirements',
    'Validate your code and test functionality',
    'Add documentation and usage examples',
    'Publish to the marketplace for review'
  ];
  return descriptions[step] || '';
}

function getPluginTypeDescription(type: string): string {
  const descriptions: Record<string, string> = {
    processor: 'Process and transform media assets',
    storage: 'Integrate with external storage systems',
    metadata: 'Extract and enrich asset metadata',
    workflow: 'Create custom workflow automation',
    search: 'Extend search capabilities',
    export: 'Support additional export formats',
    analytics: 'Generate custom analytics and reports',
    notification: 'Send notifications through various channels',
    authentication: 'Integrate with external auth providers',
    ingest: 'Import assets from external sources',
    ui_component: 'Add custom UI components',
    api_extension: 'Extend the API with custom endpoints'
  };
  return descriptions[type] || 'Custom plugin functionality';
}

export default PluginEditorPage;