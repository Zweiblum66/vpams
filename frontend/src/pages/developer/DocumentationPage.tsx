import React, { useState } from 'react';
import {
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Box,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Button,
  Stack,
  Divider,
  Paper,
  Alert
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Code as CodeIcon,
  Book as BookIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
  Extension as ExtensionIcon,
  Api as ApiIcon,
  PlayCircle as PlayCircleIcon,
  Download as DownloadIcon,
  Launch as LaunchIcon
} from '@mui/icons-material';
import { useGetDeveloperDocumentationQuery } from '../../store/api/developerApi';
import { PageHeader } from '../../components/PageHeader/PageHeader';
import { Loading } from '../../components/Loading/RTKQueryLoading';

const QUICK_LINKS = [
  {
    title: 'Plugin Templates',
    description: 'Ready-to-use templates for different plugin types',
    icon: <ExtensionIcon />,
    action: 'View Templates',
    href: '/developer/editor'
  },
  {
    title: 'API Reference',
    description: 'Complete API documentation for plugin development',
    icon: <ApiIcon />,
    action: 'View API Docs',
    href: '#api-reference'
  },
  {
    title: 'Example Plugins',
    description: 'Working examples and code samples',
    icon: <CodeIcon />,
    action: 'Browse Examples',
    href: '#examples'
  },
  {
    title: 'Testing Guide',
    description: 'Learn how to test your plugins effectively',
    icon: <PlayCircleIcon />,
    action: 'Testing Guide',
    href: '#testing'
  }
];

const CODE_EXAMPLES = {
  basic_plugin: `from plugin_base import ProcessorPlugin, PluginResult

class MyProcessorPlugin(ProcessorPlugin):
    async def initialize(self) -> bool:
        """Initialize the plugin"""
        self.logger.info("Initializing My Processor Plugin")
        return True
    
    async def process_asset(self, asset_id: str, context) -> PluginResult:
        """Process an asset"""
        try:
            # Your processing logic here
            processed_data = await self.process_logic(asset_id)
            
            return PluginResult(
                success=True,
                data={"processed": True, "result": processed_data}
            )
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            return PluginResult(
                success=False,
                error=str(e)
            )`,
  
  hook_example: `@PluginHook("pre_process")
async def before_processing(self, context, **kwargs):
    """Called before asset processing"""
    asset_id = kwargs.get("asset_id")
    self.logger.info(f"Pre-processing hook for asset {asset_id}")
    
    # Validate asset before processing
    if not await self.validate_asset(asset_id):
        return PluginResult(success=False, error="Asset validation failed")
    
    return PluginResult(success=True)`,

  event_handling: `async def handle_asset_created(self, event_data):
    """Handle asset created event"""
    asset_id = event_data.get("asset_id")
    
    # Automatically process new assets
    if self.config.settings.get("auto_process_new_assets"):
        await self.process_asset(asset_id, {})`,

  configuration: `# config.yaml
enabled: true
settings:
  quality: 85
  format: jpg
  enable_optimization: true
  auto_process_new_assets: false
capabilities:
  - read_assets
  - write_assets
  - execute_workflows
rate_limit: 100  # requests per minute
timeout: 30  # seconds
retry_count: 3
priority: 5`
};

export const DocumentationPage: React.FC = () => {
  const [selectedExample, setSelectedExample] = useState<string>('basic_plugin');
  
  const { data: documentation, isLoading, error } = useGetDeveloperDocumentationQuery();

  if (isLoading) {
    return <Loading />;
  }

  if (error) {
    return (
      <Container maxWidth="lg">
        <Alert severity="error" sx={{ mt: 2 }}>
          Failed to load documentation. Please try again.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl">
      <PageHeader
        title="Developer Documentation"
        subtitle="Complete guide to building plugins for the MAMS platform"
      />

      {/* Quick Links */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {QUICK_LINKS.map((link, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card 
              sx={{ 
                height: '100%', 
                cursor: 'pointer',
                '&:hover': { boxShadow: 4 }
              }}
            >
              <CardContent sx={{ textAlign: 'center' }}>
                <Box sx={{ color: 'primary.main', mb: 2 }}>
                  {link.icon}
                </Box>
                <Typography variant="h6" gutterBottom>
                  {link.title}
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  {link.description}
                </Typography>
                <Button 
                  variant="outlined" 
                  size="small"
                  endIcon={<LaunchIcon />}
                >
                  {link.action}
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* Documentation Content */}
        <Grid item xs={12} lg={8}>
          {documentation && (
            <Stack spacing={3}>
              {/* Getting Started */}
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <BookIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h5">
                      {documentation.getting_started.title}
                    </Typography>
                  </Box>
                  
                  {documentation.getting_started.sections.map((section: any, index: number) => (
                    <Accordion key={index}>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="h6">{section.title}</Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="body1">{section.content}</Typography>
                      </AccordionDetails>
                    </Accordion>
                  ))}
                </CardContent>
              </Card>

              {/* API Reference */}
              <Card id="api-reference">
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <ApiIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h5">
                      {documentation.api_reference.title}
                    </Typography>
                  </Box>
                  
                  {documentation.api_reference.sections.map((section: any, index: number) => (
                    <Accordion key={index}>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="h6">{section.title}</Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="body1" paragraph>{section.content}</Typography>
                        
                        {section.title === 'Plugin Base Classes' && (
                          <List>
                            <ListItem>
                              <ListItemIcon><ExtensionIcon /></ListItemIcon>
                              <ListItemText 
                                primary="ProcessorPlugin" 
                                secondary="For asset processing and transformation"
                              />
                            </ListItem>
                            <ListItem>
                              <ListItemIcon><ExtensionIcon /></ListItemIcon>
                              <ListItemText 
                                primary="StoragePlugin" 
                                secondary="For storage backend integrations"
                              />
                            </ListItem>
                            <ListItem>
                              <ListItemIcon><ExtensionIcon /></ListItemIcon>
                              <ListItemText 
                                primary="MetadataPlugin" 
                                secondary="For metadata extraction and enrichment"
                              />
                            </ListItem>
                            <ListItem>
                              <ListItemIcon><ExtensionIcon /></ListItemIcon>
                              <ListItemText 
                                primary="WorkflowPlugin" 
                                secondary="For workflow automation"
                              />
                            </ListItem>
                          </List>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  ))}
                </CardContent>
              </Card>

              {/* Examples */}
              <Card id="examples">
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <CodeIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h5">
                      {documentation.examples.title}
                    </Typography>
                  </Box>
                  
                  {documentation.examples.sections.map((section: any, index: number) => (
                    <Accordion key={index}>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="h6">{section.title}</Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="body1">{section.content}</Typography>
                      </AccordionDetails>
                    </Accordion>
                  ))}
                </CardContent>
              </Card>

              {/* Best Practices */}
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <SecurityIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h5">
                      {documentation.best_practices.title}
                    </Typography>
                  </Box>
                  
                  {documentation.best_practices.sections.map((section: any, index: number) => (
                    <Accordion key={index}>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="h6">{section.title}</Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="body1">{section.content}</Typography>
                        
                        {section.title === 'Security Guidelines' && (
                          <Alert severity="warning" sx={{ mt: 2 }}>
                            Always validate input data and sanitize user inputs to prevent security vulnerabilities.
                          </Alert>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  ))}
                </CardContent>
              </Card>
            </Stack>
          )}
        </Grid>

        {/* Code Examples Sidebar */}
        <Grid item xs={12} lg={4}>
          <Card sx={{ position: 'sticky', top: 24 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Code Examples
              </Typography>
              
              <Stack spacing={2}>
                {Object.entries(CODE_EXAMPLES).map(([key, code]) => (
                  <Button
                    key={key}
                    variant={selectedExample === key ? 'contained' : 'outlined'}
                    onClick={() => setSelectedExample(key)}
                    fullWidth
                    sx={{ justifyContent: 'flex-start' }}
                  >
                    {key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </Button>
                ))}
              </Stack>

              <Divider sx={{ my: 2 }} />

              <Paper 
                sx={{ 
                  p: 2, 
                  bgcolor: 'grey.900', 
                  color: 'white',
                  maxHeight: 400,
                  overflow: 'auto'
                }}
              >
                <pre style={{ margin: 0, fontSize: '0.75rem', whiteSpace: 'pre-wrap' }}>
                  <code>{CODE_EXAMPLES[selectedExample as keyof typeof CODE_EXAMPLES]}</code>
                </pre>
              </Paper>

              <Button
                fullWidth
                variant="outlined"
                startIcon={<DownloadIcon />}
                sx={{ mt: 2 }}
                onClick={() => {
                  const blob = new Blob([CODE_EXAMPLES[selectedExample as keyof typeof CODE_EXAMPLES]], { type: 'text/plain' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `${selectedExample}.py`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                Download Example
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default DocumentationPage;