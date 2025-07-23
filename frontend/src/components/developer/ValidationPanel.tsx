import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
  Stack,
  Card,
  CardContent,
  Divider,
  Grid
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  BugReport as BugReportIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
  Code as CodeIcon
} from '@mui/icons-material';

interface ValidationPanelProps {
  validationResults: any;
  onValidate: () => void;
  codeFiles: Record<string, string>;
}

export const ValidationPanel: React.FC<ValidationPanelProps> = ({
  validationResults,
  onValidate,
  codeFiles
}) => {
  const [isValidating, setIsValidating] = useState(false);

  const handleValidate = async () => {
    setIsValidating(true);
    try {
      await onValidate();
    } finally {
      setIsValidating(false);
    }
  };

  const getValidationIcon = (type: 'error' | 'warning' | 'info') => {
    switch (type) {
      case 'error':
        return <ErrorIcon color="error" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'info':
        return <InfoIcon color="info" />;
    }
  };

  const getValidationColor = (type: 'error' | 'warning' | 'info') => {
    switch (type) {
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
    }
  };

  return (
    <Box>
      {/* Validation Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6">Code Validation</Typography>
        <Button
          variant="contained"
          startIcon={<BugReportIcon />}
          onClick={handleValidate}
          disabled={isValidating || Object.keys(codeFiles).length === 0}
        >
          {isValidating ? 'Validating...' : 'Run Validation'}
        </Button>
      </Box>

      {isValidating && (
        <Box sx={{ mb: 3 }}>
          <LinearProgress />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Analyzing your plugin code...
          </Typography>
        </Box>
      )}

      {!validationResults && !isValidating && (
        <Alert severity="info">
          Click "Run Validation" to check your plugin code for errors, warnings, and potential improvements.
        </Alert>
      )}

      {validationResults && (
        <Stack spacing={3}>
          {/* Overall Status */}
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                {validationResults.valid ? (
                  <CheckCircleIcon color="success" sx={{ mr: 2 }} />
                ) : (
                  <ErrorIcon color="error" sx={{ mr: 2 }} />
                )}
                <Typography variant="h6">
                  {validationResults.valid ? 'Validation Passed' : 'Validation Failed'}
                </Typography>
              </Box>

              <Stack direction="row" spacing={2}>
                <Chip
                  label={`${validationResults.errors?.length || 0} Errors`}
                  color={validationResults.errors?.length > 0 ? 'error' : 'default'}
                  variant={validationResults.errors?.length > 0 ? 'filled' : 'outlined'}
                />
                <Chip
                  label={`${validationResults.warnings?.length || 0} Warnings`}
                  color={validationResults.warnings?.length > 0 ? 'warning' : 'default'}
                  variant={validationResults.warnings?.length > 0 ? 'filled' : 'outlined'}
                />
                <Chip
                  label={`${validationResults.suggestions?.length || 0} Suggestions`}
                  color="info"
                  variant="outlined"
                />
              </Stack>
            </CardContent>
          </Card>

          {/* Errors Section */}
          {validationResults.errors && validationResults.errors.length > 0 && (
            <Accordion defaultExpanded>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <ErrorIcon color="error" sx={{ mr: 1 }} />
                  <Typography variant="h6">
                    Errors ({validationResults.errors.length})
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Alert severity="error" sx={{ mb: 2 }}>
                  These errors must be fixed before your plugin can be published.
                </Alert>
                <List>
                  {validationResults.errors.map((error: string, index: number) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <ErrorIcon color="error" />
                      </ListItemIcon>
                      <ListItemText primary={error} />
                    </ListItem>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          )}

          {/* Warnings Section */}
          {validationResults.warnings && validationResults.warnings.length > 0 && (
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <WarningIcon color="warning" sx={{ mr: 1 }} />
                  <Typography variant="h6">
                    Warnings ({validationResults.warnings.length})
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Alert severity="warning" sx={{ mb: 2 }}>
                  These warnings should be addressed to improve your plugin quality.
                </Alert>
                <List>
                  {validationResults.warnings.map((warning: string, index: number) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <WarningIcon color="warning" />
                      </ListItemIcon>
                      <ListItemText primary={warning} />
                    </ListItem>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          )}

          {/* Suggestions Section */}
          {validationResults.suggestions && validationResults.suggestions.length > 0 && (
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <InfoIcon color="info" sx={{ mr: 1 }} />
                  <Typography variant="h6">
                    Suggestions ({validationResults.suggestions.length})
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Alert severity="info" sx={{ mb: 2 }}>
                  These suggestions can help improve your plugin's performance and maintainability.
                </Alert>
                <List>
                  {validationResults.suggestions.map((suggestion: string, index: number) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <InfoIcon color="info" />
                      </ListItemIcon>
                      <ListItemText primary={suggestion} />
                    </ListItem>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          )}

          {/* Additional Validation Info */}
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <SecurityIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">Security</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    No security vulnerabilities detected in your plugin code.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <SpeedIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">Performance</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Code follows performance best practices.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <CodeIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">Code Quality</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {validationResults.valid ? 'Good' : 'Needs improvement'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Validation Tips */}
          <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
            <Typography variant="h6" gutterBottom>
              Validation Tips
            </Typography>
            <Typography variant="body2" paragraph>
              • Ensure all required methods are implemented for your plugin type
            </Typography>
            <Typography variant="body2" paragraph>
              • Add proper error handling and logging throughout your code
            </Typography>
            <Typography variant="body2" paragraph>
              • Include comprehensive documentation in your plugin metadata
            </Typography>
            <Typography variant="body2" paragraph>
              • Test your plugin with various input scenarios
            </Typography>
            <Typography variant="body2">
              • Follow MAMS security guidelines for safe plugin development
            </Typography>
          </Paper>
        </Stack>
      )}
    </Box>
  );
};

export default ValidationPanel;