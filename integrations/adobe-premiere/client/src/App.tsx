import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  TextField,
  InputAdornment,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Search,
  Refresh,
  Settings,
  CloudDownload,
  Folder,
} from '@mui/icons-material';
import AssetBrowser from './components/AssetBrowser';
import AssetDetails from './components/AssetDetails';
import ProjectSync from './components/ProjectSync';
import Settings from './components/Settings';
import { MAMSClient } from './services/mamsClient';
import { CSInterface } from './utils/CSInterface';
import { useAuth } from './hooks/useAuth';
import { useAssets } from './hooks/useAssets';
import { Asset } from './types';

// Create CSInterface instance
const csInterface = new CSInterface();

// Theme configuration
const theme = createTheme({
  palette: {
    mode: csInterface.getHostEnvironment().appSkinInfo.panelBackgroundColor.color.red > 128 ? 'light' : 'dark',
  },
});

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
      id={`tabpanel-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 2 }}>{children}</Box>}
    </div>
  );
}

function App() {
  const [tabValue, setTabValue] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { isAuthenticated, user, login, logout } = useAuth();
  const { assets, loading: assetsLoading, error: assetsError, searchAssets, refreshAssets } = useAssets();

  useEffect(() => {
    // Initialize panel
    csInterface.addEventListener('com.mams.refresh', () => {
      refreshAssets();
    });

    // Auto-login if credentials are saved
    const savedCredentials = localStorage.getItem('mams_credentials');
    if (savedCredentials && !isAuthenticated) {
      const { username, password } = JSON.parse(savedCredentials);
      login(username, password);
    }
  }, []);

  const handleSearch = (event: React.FormEvent) => {
    event.preventDefault();
    searchAssets(searchQuery);
  };

  const handleAssetSelect = (asset: Asset) => {
    setSelectedAsset(asset);
  };

  const handleImportAsset = async (asset: Asset) => {
    try {
      setLoading(true);
      
      // Download asset to local cache
      const localPath = await MAMSClient.getInstance().downloadAsset(asset.id);
      
      // Import to Premiere Pro project
      csInterface.evalScript(`importAsset("${localPath}", "${asset.name}")`, (result: string) => {
        if (result === 'success') {
          console.log('Asset imported successfully');
        } else {
          throw new Error('Import failed');
        }
      });
    } catch (err) {
      setError('Failed to import asset');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (!isAuthenticated) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box sx={{ p: 3 }}>
          <LoginForm onLogin={login} />
        </Box>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1, height: '100vh', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <AppBar position="static" color="default" elevation={0}>
          <Toolbar variant="dense">
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              MAMS
            </Typography>
            <IconButton size="small" onClick={refreshAssets}>
              <Refresh />
            </IconButton>
            <IconButton size="small" onClick={() => setTabValue(3)}>
              <Settings />
            </IconButton>
          </Toolbar>
        </AppBar>

        {/* Search Bar */}
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <form onSubmit={handleSearch}>
            <TextField
              fullWidth
              size="small"
              placeholder="Search assets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
            />
          </form>
        </Box>

        {/* Tabs */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Browse" />
            <Tab label="Details" disabled={!selectedAsset} />
            <Tab label="Project" />
            <Tab label="Settings" />
          </Tabs>
        </Box>

        {/* Tab Panels */}
        <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
          <TabPanel value={tabValue} index={0}>
            <AssetBrowser
              assets={assets}
              loading={assetsLoading}
              error={assetsError}
              onAssetSelect={handleAssetSelect}
              onAssetImport={handleImportAsset}
            />
          </TabPanel>
          
          <TabPanel value={tabValue} index={1}>
            {selectedAsset && (
              <AssetDetails
                asset={selectedAsset}
                onImport={handleImportAsset}
                onClose={() => setSelectedAsset(null)}
              />
            )}
          </TabPanel>
          
          <TabPanel value={tabValue} index={2}>
            <ProjectSync />
          </TabPanel>
          
          <TabPanel value={tabValue} index={3}>
            <Settings onLogout={logout} />
          </TabPanel>
        </Box>

        {/* Loading Overlay */}
        {loading && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              zIndex: 9999,
            }}
          >
            <CircularProgress />
          </Box>
        )}

        {/* Error Snackbar */}
        {error && (
          <Alert severity="error" onClose={() => setError(null)} sx={{ m: 2 }}>
            {error}
          </Alert>
        )}
      </Box>
    </ThemeProvider>
  );
}

// Login Component
interface LoginFormProps {
  onLogin: (username: string, password: string) => Promise<void>;
}

function LoginForm({ onLogin }: LoginFormProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      await onLogin(username, password);
    } catch (err) {
      setError('Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <Typography variant="h5" gutterBottom>
        Login to MAMS
      </Typography>
      <TextField
        fullWidth
        label="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        margin="normal"
        required
      />
      <TextField
        fullWidth
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        margin="normal"
        required
      />
      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      <Box sx={{ mt: 3 }}>
        <button type="submit" disabled={loading}>
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </Box>
    </form>
  );
}

export default App;