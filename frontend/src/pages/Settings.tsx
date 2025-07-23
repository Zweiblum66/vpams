import React from 'react';
import { Box, Typography, Paper, Switch, FormControlLabel, Divider, Button } from '@mui/material';
import { Settings as SettingsIcon, Save as SaveIcon } from '@mui/icons-material';

const Settings: React.FC = () => {
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <SettingsIcon sx={{ fontSize: 32, mr: 2, color: 'primary.main' }} />
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
          Settings
        </Typography>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Notification Settings
        </Typography>
        <Divider sx={{ mb: 3 }} />
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <FormControlLabel
            control={<Switch defaultChecked />}
            label="Email notifications"
          />
          <FormControlLabel
            control={<Switch defaultChecked />}
            label="Push notifications"
          />
          <FormControlLabel
            control={<Switch />}
            label="SMS notifications"
          />
        </Box>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h6" gutterBottom>
          Display Settings
        </Typography>
        <Divider sx={{ mb: 3 }} />
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <FormControlLabel
            control={<Switch defaultChecked />}
            label="Dark mode"
          />
          <FormControlLabel
            control={<Switch defaultChecked />}
            label="Compact mode"
          />
          <FormControlLabel
            control={<Switch />}
            label="Show animations"
          />
        </Box>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button variant="contained" startIcon={<SaveIcon />}>
            Save Settings
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

export default Settings;