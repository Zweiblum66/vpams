import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  CircularProgress,
  Stepper,
  Step,
  StepLabel
} from '@mui/material';
import {
  Security,
  Verified,
  Assessment,
  TrendingUp,
  Warning,
  CheckCircle,
  Error,
  Info,
  Star,
  Badge
} from '@mui/icons-material';
import { useCertification } from '../../hooks/useCertification';

interface CertificationDashboardProps {
  developerId?: string;
}

const CertificationDashboard: React.FC<CertificationDashboardProps> = ({ developerId }) => {
  const { 
    certificationStats, 
    certificationLevels, 
    loading, 
    error, 
    submitForCertification,
    validatePlugin 
  } = useCertification();
  const [selectedPlugin, setSelectedPlugin] = useState<string | null>(null);
  const [levelsDialogOpen, setLevelsDialogOpen] = useState(false);
  const [validationDialogOpen, setValidationDialogOpen] = useState(false);
  const [validationResults, setValidationResults] = useState<any>(null);
  const [validating, setValidating] = useState(false);

  const handleValidatePlugin = async (pluginId: string) => {
    setValidating(true);
    try {
      const results = await validatePlugin(pluginId);
      setValidationResults(results);
      setValidationDialogOpen(true);
    } catch (error) {
      console.error('Validation failed:', error);
    } finally {
      setValidating(false);
    }
  };

  const handleSubmitForCertification = async (pluginId: string) => {
    try {
      await submitForCertification(pluginId);
      // Refresh stats after submission
    } catch (error) {
      console.error('Certification submission failed:', error);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'success';
    if (score >= 75) return 'info';
    if (score >= 60) return 'warning';
    return 'error';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'certified': return <Verified color="success" />;
      case 'pending': return <Info color="info" />;
      case 'in_review': return <Assessment color="primary" />;
      case 'rejected': return <Error color="error" />;
      case 'failed': return <Warning color="warning" />;
      default: return <Info />;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Plugin Certification
      </Typography>

      {/* Overview Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Badge color="primary" />
                <Box ml={2}>
                  <Typography variant="h6">
                    {certificationStats?.certified_plugins || 0}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Certified Plugins
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Assessment color="info" />
                <Box ml={2}>
                  <Typography variant="h6">
                    {certificationStats?.pending_reviews || 0}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Pending Reviews
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <TrendingUp color="success" />
                <Box ml={2}>
                  <Typography variant="h6">
                    {certificationStats?.average_score?.toFixed(1) || '0.0'}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Average Score
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Star color="warning" />
                <Box ml={2}>
                  <Typography variant="h6">
                    {certificationStats?.certification_rate?.toFixed(1) || '0.0'}%
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Certification Rate
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Certification Levels */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Certification Levels</Typography>
            <Button 
              variant="outlined" 
              onClick={() => setLevelsDialogOpen(true)}
            >
              View All Levels
            </Button>
          </Box>

          <Grid container spacing={2}>
            {certificationLevels?.slice(0, 3).map((level) => (
              <Grid item xs={12} md={4} key={level.level}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" color="primary" gutterBottom>
                      {level.title}
                    </Typography>
                    <Typography variant="body2" color="textSecondary" paragraph>
                      {level.description}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Min Score:</strong> {level.min_score}%
                    </Typography>
                    <Typography variant="body2">
                      <strong>Review Time:</strong> {level.review_time}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

      {/* Plugin Actions */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Plugin Actions
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item>
              <Button
                variant="contained"
                startIcon={<Security />}
                onClick={() => handleValidatePlugin('your-plugin-id')}
                disabled={validating}
              >
                {validating ? <CircularProgress size={20} /> : 'Validate Plugin'}
              </Button>
            </Grid>
            <Grid item>
              <Button
                variant="contained"
                color="success"
                startIcon={<Verified />}
                onClick={() => handleSubmitForCertification('your-plugin-id')}
              >
                Submit for Certification
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Certification Process */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Certification Process
          </Typography>
          
          <Stepper activeStep={2} alternativeLabel>
            <Step>
              <StepLabel>Plugin Development</StepLabel>
            </Step>
            <Step>
              <StepLabel>Validation Testing</StepLabel>
            </Step>
            <Step>
              <StepLabel>Certification Submission</StepLabel>
            </Step>
            <Step>
              <StepLabel>Automated Review</StepLabel>
            </Step>
            <Step>
              <StepLabel>Manual Review</StepLabel>
            </Step>
            <Step>
              <StepLabel>Certification Issued</StepLabel>
            </Step>
          </Stepper>
        </CardContent>
      </Card>

      {/* Certification Levels Dialog */}
      <Dialog 
        open={levelsDialogOpen} 
        onClose={() => setLevelsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Certification Levels</DialogTitle>
        <DialogContent>
          <Grid container spacing={3}>
            {certificationLevels?.map((level) => (
              <Grid item xs={12} key={level.level}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" color="primary" gutterBottom>
                      {level.title}
                    </Typography>
                    <Typography variant="body2" paragraph>
                      {level.description}
                    </Typography>
                    
                    <Typography variant="subtitle2" gutterBottom>
                      Requirements:
                    </Typography>
                    <List dense>
                      {level.requirements.map((req, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <CheckCircle color="success" fontSize="small" />
                          </ListItemIcon>
                          <ListItemText primary={req} />
                        </ListItem>
                      ))}
                    </List>
                    
                    <Typography variant="subtitle2" gutterBottom>
                      Benefits:
                    </Typography>
                    <List dense>
                      {level.benefits.map((benefit, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <Star color="warning" fontSize="small" />
                          </ListItemIcon>
                          <ListItemText primary={benefit} />
                        </ListItem>
                      ))}
                    </List>

                    <Box mt={2}>
                      <Typography variant="body2">
                        <strong>Minimum Score:</strong> {level.min_score}%
                      </Typography>
                      <Typography variant="body2">
                        <strong>Review Time:</strong> {level.review_time}
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLevelsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Validation Results Dialog */}
      <Dialog 
        open={validationDialogOpen} 
        onClose={() => setValidationDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Plugin Validation Results
          {validationResults?.valid ? (
            <Chip icon={<CheckCircle />} label="Valid" color="success" sx={{ ml: 2 }} />
          ) : (
            <Chip icon={<Error />} label="Issues Found" color="error" sx={{ ml: 2 }} />
          )}
        </DialogTitle>
        <DialogContent>
          {validationResults && (
            <Box>
              {validationResults.errors.length > 0 && (
                <Box mb={2}>
                  <Typography variant="h6" color="error" gutterBottom>
                    Errors ({validationResults.errors.length})
                  </Typography>
                  <List>
                    {validationResults.errors.map((error: string, index: number) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          <Error color="error" />
                        </ListItemIcon>
                        <ListItemText primary={error} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              {validationResults.warnings.length > 0 && (
                <Box mb={2}>
                  <Typography variant="h6" color="warning.main" gutterBottom>
                    Warnings ({validationResults.warnings.length})
                  </Typography>
                  <List>
                    {validationResults.warnings.map((warning: string, index: number) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          <Warning color="warning" />
                        </ListItemIcon>
                        <ListItemText primary={warning} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              {validationResults.suggestions.length > 0 && (
                <Box mb={2}>
                  <Typography variant="h6" color="info.main" gutterBottom>
                    Suggestions ({validationResults.suggestions.length})
                  </Typography>
                  <List>
                    {validationResults.suggestions.map((suggestion: string, index: number) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          <Info color="info" />
                        </ListItemIcon>
                        <ListItemText primary={suggestion} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setValidationDialogOpen(false)}>Close</Button>
          {validationResults?.valid && (
            <Button 
              variant="contained" 
              color="success"
              onClick={() => {
                setValidationDialogOpen(false);
                handleSubmitForCertification('your-plugin-id');
              }}
            >
              Submit for Certification
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CertificationDashboard;