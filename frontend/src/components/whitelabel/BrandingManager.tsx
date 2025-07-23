import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Divider,
  Switch,
  FormControlLabel,
  Chip
} from '@mui/material';
import {
  Save as SaveIcon,
  CheckCircle as ActiveIcon,
  Settings as ConfigIcon
} from '@mui/icons-material';

interface BrandingManagerProps {
  branding: any;
  themes: any[];
  onBrandingChange: () => void;
}

const BrandingManager: React.FC<BrandingManagerProps> = ({ 
  branding, 
  themes, 
  onBrandingChange 
}) => {
  const [formData, setFormData] = useState({
    company_name: '',
    company_tagline: '',
    company_description: '',
    company_website: '',
    contact_email: '',
    support_email: '',
    phone_number: '',
    platform_name: '',
    welcome_message: '',
    login_message: '',
    footer_text: '',
    theme_id: ''
  });

  useEffect(() => {
    if (branding) {
      setFormData({
        company_name: branding.company_name || '',
        company_tagline: branding.company_tagline || '',
        company_description: branding.company_description || '',
        company_website: branding.company_website || '',
        contact_email: branding.contact_email || '',
        support_email: branding.support_email || '',
        phone_number: branding.phone_number || '',
        platform_name: branding.platform_name || '',
        welcome_message: branding.welcome_message || '',
        login_message: branding.login_message || '',
        footer_text: branding.footer_text || '',
        theme_id: branding.theme_id || ''
      });
    }
  }, [branding]);

  const handleSave = () => {
    // TODO: Implement save functionality
    console.log('Saving branding configuration:', formData);
    onBrandingChange();
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">
          Branding Configuration
        </Typography>
        {branding?.status && (
          <Chip
            icon={branding.status === 'active' ? <ActiveIcon /> : <ConfigIcon />}
            label={branding.status.toUpperCase()}
            color={branding.status === 'active' ? 'success' : 'default'}
          />
        )}
      </Box>

      <Grid container spacing={3}>
        {/* Company Information */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Company Information
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Company Name"
                    fullWidth
                    required
                    value={formData.company_name}
                    onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Company Tagline"
                    fullWidth
                    value={formData.company_tagline}
                    onChange={(e) => setFormData({ ...formData, company_tagline: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    label="Company Description"
                    fullWidth
                    multiline
                    rows={3}
                    value={formData.company_description}
                    onChange={(e) => setFormData({ ...formData, company_description: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Website URL"
                    fullWidth
                    type="url"
                    value={formData.company_website}
                    onChange={(e) => setFormData({ ...formData, company_website: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Theme</InputLabel>
                    <Select
                      value={formData.theme_id}
                      onChange={(e) => setFormData({ ...formData, theme_id: e.target.value })}
                      label="Theme"
                    >
                      <MenuItem value="">No Theme</MenuItem>
                      {themes.map((theme) => (
                        <MenuItem key={theme.id} value={theme.id}>
                          {theme.display_name || theme.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Contact Information */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Contact Information
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Contact Email"
                    fullWidth
                    type="email"
                    required
                    value={formData.contact_email}
                    onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Support Email"
                    fullWidth
                    type="email"
                    value={formData.support_email}
                    onChange={(e) => setFormData({ ...formData, support_email: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Phone Number"
                    fullWidth
                    value={formData.phone_number}
                    onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Platform Customization */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Platform Customization
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Platform Name"
                    fullWidth
                    value={formData.platform_name}
                    onChange={(e) => setFormData({ ...formData, platform_name: e.target.value })}
                    helperText="Custom name for your platform instance"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    label="Welcome Message"
                    fullWidth
                    multiline
                    rows={2}
                    value={formData.welcome_message}
                    onChange={(e) => setFormData({ ...formData, welcome_message: e.target.value })}
                    helperText="Message shown to users when they first visit"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    label="Login Message"
                    fullWidth
                    multiline
                    rows={2}
                    value={formData.login_message}
                    onChange={(e) => setFormData({ ...formData, login_message: e.target.value })}
                    helperText="Message shown on the login page"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    label="Footer Text"
                    fullWidth
                    value={formData.footer_text}
                    onChange={(e) => setFormData({ ...formData, footer_text: e.target.value })}
                    helperText="Text displayed in the footer"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Actions */}
        <Grid item xs={12}>
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSave}
              disabled={!formData.company_name || !formData.contact_email}
            >
              Save Configuration
            </Button>
          </Box>
        </Grid>
      </Grid>

      {!branding && (
        <Alert severity="info" sx={{ mt: 3 }}>
          No branding configuration found. Fill out the form above to create your first branding configuration.
        </Alert>
      )}
    </Box>
  );
};

export default BrandingManager;