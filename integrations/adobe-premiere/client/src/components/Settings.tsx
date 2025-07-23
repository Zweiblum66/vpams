import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Switch,
  Divider,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Checkbox,
} from '@mui/material';
import {
  Link,
  Person,
  Folder,
  CloudQueue,
  Delete,
  Cached,
  Security,
  Notifications,
  Palette,
  Storage,
  Info,
  ExitToApp,
} from '@mui/icons-material';
import { MAMSClient } from '../services/mamsClient';
import { CSInterface } from '../utils/CSInterface';

const csInterface = new CSInterface();

interface SettingsProps {
  onLogout: () => void;
}

const Settings: React.FC<SettingsProps> = ({ onLogout }) => {
  const [config, setConfig] = useState({
    endpoint: '',
    apiKey: '',
    proxyQuality: 'medium',
    autoSync: false,
    syncInterval: 60,
    cacheSize: 1000,
    enableNotifications: true,
    theme: 'auto',
    rememberCredentials: false,
  });
  
  const [user, setUser] = useState<any>(null);
  const [cacheInfo, setCacheInfo] = useState({ size: 0, items: 0 });
  const [clearCacheDialog, setClearCacheDialog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    loadSettings();
    loadUserInfo();
    loadCacheInfo();
  }, []);

  const loadSettings = () => {
    const savedConfig = localStorage.getItem('mams_settings');
    if (savedConfig) {
      setConfig({ ...config, ...JSON.parse(savedConfig) });
    }
    
    // Load MAMS endpoint from client
    const mamsConfig = JSON.parse(localStorage.getItem('mams_config') || '{}');
    if (mamsConfig.endpoint) {
      setConfig(prev => ({ ...prev, endpoint: mamsConfig.endpoint }));
    }
  };

  const loadUserInfo = async () => {
    try {
      const currentUser = await MAMSClient.getInstance().getCurrentUser();
      setUser(currentUser);
    } catch (err) {
      // Not logged in
    }
  };

  const loadCacheInfo = async () => {
    try {
      const size = await MAMSClient.getInstance().getCacheSize();
      const downloads = JSON.parse(localStorage.getItem('mams_downloads') || '[]');
      setCacheInfo({ size, items: downloads.length });
    } catch (err) {
      // Ignore
    }
  };

  const handleSave = () => {
    setSaving(true);
    
    // Save settings
    localStorage.setItem('mams_settings', JSON.stringify(config));
    
    // Update MAMS client config
    MAMSClient.getInstance().saveConfig({
      endpoint: config.endpoint,
      apiKey: config.apiKey,
    });
    
    // Apply theme
    applyTheme(config.theme);
    
    // Show success message
    setMessage({ type: 'success', text: 'Settings saved successfully' });
    setSaving(false);
    
    setTimeout(() => setMessage(null), 3000);
  };

  const handleClearCache = async () => {
    try {
      await MAMSClient.getInstance().clearCache();
      setCacheInfo({ size: 0, items: 0 });
      setClearCacheDialog(false);
      setMessage({ type: 'success', text: 'Cache cleared successfully' });
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to clear cache' });
    }
  };

  const applyTheme = (theme: string) => {
    if (theme === 'auto') {
      // Use Premiere Pro's theme
      const hostEnv = csInterface.getHostEnvironment();
      const isDark = hostEnv.appSkinInfo.panelBackgroundColor.color.red < 128;
      document.body.className = isDark ? 'theme-dark' : 'theme-light';
    } else {
      document.body.className = `theme-${theme}`;
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Box sx={{ p: 2 }}>
      {/* User Info */}
      {user && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Person sx={{ mr: 2, fontSize: 40 }} />
              <Box>
                <Typography variant="h6">{user.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {user.email}
                </Typography>
              </Box>
            </Box>
            <Button
              variant="outlined"
              startIcon={<ExitToApp />}
              onClick={onLogout}
            >
              Logout
            </Button>
          </Box>
        </Paper>
      )}

      {/* Connection Settings */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Connection Settings
        </Typography>
        <TextField
          fullWidth
          label="MAMS Server URL"
          value={config.endpoint}
          onChange={(e) => setConfig({ ...config, endpoint: e.target.value })}
          margin="normal"
          placeholder="https://mams.example.com"
        />
        <TextField
          fullWidth
          label="API Key (optional)"
          value={config.apiKey}
          onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
          margin="normal"
          type="password"
          helperText="Use API key for authentication instead of username/password"
        />
      </Paper>

      {/* Sync Settings */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Sync Settings
        </Typography>
        <List>
          <ListItem>
            <ListItemIcon>
              <Cached />
            </ListItemIcon>
            <ListItemText
              primary="Auto-sync project"
              secondary="Automatically sync project changes to MAMS"
            />
            <ListItemSecondaryAction>
              <Switch
                checked={config.autoSync}
                onChange={(e) => setConfig({ ...config, autoSync: e.target.checked })}
              />
            </ListItemSecondaryAction>
          </ListItem>
          
          {config.autoSync && (
            <ListItem>
              <ListItemText
                inset
                primary="Sync interval"
              />
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <Select
                  value={config.syncInterval}
                  onChange={(e) => setConfig({ ...config, syncInterval: Number(e.target.value) })}
                >
                  <MenuItem value={30}>30 seconds</MenuItem>
                  <MenuItem value={60}>1 minute</MenuItem>
                  <MenuItem value={300}>5 minutes</MenuItem>
                  <MenuItem value={600}>10 minutes</MenuItem>
                </Select>
              </FormControl>
            </ListItem>
          )}
        </List>
      </Paper>

      {/* Cache Settings */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Cache Settings
        </Typography>
        <List>
          <ListItem>
            <ListItemIcon>
              <Storage />
            </ListItemIcon>
            <ListItemText
              primary="Cache size"
              secondary={`${cacheInfo.items} items using ${formatBytes(cacheInfo.size)}`}
            />
            <ListItemSecondaryAction>
              <Button
                size="small"
                startIcon={<Delete />}
                onClick={() => setClearCacheDialog(true)}
              >
                Clear
              </Button>
            </ListItemSecondaryAction>
          </ListItem>
          
          <ListItem>
            <ListItemText
              inset
              primary="Maximum cache size"
            />
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <Select
                value={config.cacheSize}
                onChange={(e) => setConfig({ ...config, cacheSize: Number(e.target.value) })}
              >
                <MenuItem value={500}>500 MB</MenuItem>
                <MenuItem value={1000}>1 GB</MenuItem>
                <MenuItem value={2000}>2 GB</MenuItem>
                <MenuItem value={5000}>5 GB</MenuItem>
              </Select>
            </FormControl>
          </ListItem>
        </List>
      </Paper>

      {/* Preferences */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Preferences
        </Typography>
        <List>
          <ListItem>
            <ListItemIcon>
              <CloudQueue />
            </ListItemIcon>
            <ListItemText
              primary="Proxy quality"
              secondary="Quality of proxy files for preview"
            />
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <Select
                value={config.proxyQuality}
                onChange={(e) => setConfig({ ...config, proxyQuality: e.target.value })}
              >
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="high">High</MenuItem>
              </Select>
            </FormControl>
          </ListItem>
          
          <ListItem>
            <ListItemIcon>
              <Notifications />
            </ListItemIcon>
            <ListItemText
              primary="Enable notifications"
              secondary="Show notifications for sync and import events"
            />
            <ListItemSecondaryAction>
              <Switch
                checked={config.enableNotifications}
                onChange={(e) => setConfig({ ...config, enableNotifications: e.target.checked })}
              />
            </ListItemSecondaryAction>
          </ListItem>
          
          <ListItem>
            <ListItemIcon>
              <Palette />
            </ListItemIcon>
            <ListItemText
              primary="Theme"
              secondary="Panel appearance"
            />
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <Select
                value={config.theme}
                onChange={(e) => setConfig({ ...config, theme: e.target.value })}
              >
                <MenuItem value="auto">Auto</MenuItem>
                <MenuItem value="light">Light</MenuItem>
                <MenuItem value="dark">Dark</MenuItem>
              </Select>
            </FormControl>
          </ListItem>
          
          <ListItem>
            <ListItemIcon>
              <Security />
            </ListItemIcon>
            <ListItemText
              primary="Remember credentials"
              secondary="Stay logged in between sessions"
            />
            <ListItemSecondaryAction>
              <Switch
                checked={config.rememberCredentials}
                onChange={(e) => setConfig({ ...config, rememberCredentials: e.target.checked })}
              />
            </ListItemSecondaryAction>
          </ListItem>
        </List>
      </Paper>

      {/* About */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          About
        </Typography>
        <List>
          <ListItem>
            <ListItemIcon>
              <Info />
            </ListItemIcon>
            <ListItemText
              primary="MAMS Panel for Premiere Pro"
              secondary="Version 1.0.0"
            />
          </ListItem>
          <ListItem>
            <ListItemIcon>
              <Link />
            </ListItemIcon>
            <ListItemText
              primary="Documentation"
              secondary="View online help"
            />
            <ListItemSecondaryAction>
              <IconButton
                size="small"
                onClick={() => window.open('https://docs.mams.io/premiere', '_blank')}
              >
                <Link />
              </IconButton>
            </ListItemSecondaryAction>
          </ListItem>
        </List>
      </Paper>

      {/* Save Button */}
      <Box sx={{ textAlign: 'center' }}>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={saving}
          size="large"
        >
          Save Settings
        </Button>
      </Box>

      {/* Messages */}
      {message && (
        <Alert severity={message.type} sx={{ mt: 3 }} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}

      {/* Clear Cache Dialog */}
      <Dialog open={clearCacheDialog} onClose={() => setClearCacheDialog(false)}>
        <DialogTitle>Clear Cache</DialogTitle>
        <DialogContent>
          <Typography>
            This will remove all cached proxy files and thumbnails. 
            Files will be re-downloaded when needed.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Current cache: {cacheInfo.items} items, {formatBytes(cacheInfo.size)}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClearCacheDialog(false)}>Cancel</Button>
          <Button onClick={handleClearCache} color="error">Clear Cache</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Settings;