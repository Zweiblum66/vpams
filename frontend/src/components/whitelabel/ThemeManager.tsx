import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Chip,
  Divider,
  Alert,
  Tooltip,
  Avatar
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ContentCopy as CopyIcon,
  Star as StarIcon,
  Visibility as PreviewIcon,
  Download as DownloadIcon,
  ColorLens as ColorIcon
} from '@mui/icons-material';
import { ChromePicker } from 'react-color';
import { useWhiteLabel } from '../../hooks/useWhiteLabel';

interface Theme {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  theme_type: string;
  is_default: boolean;
  is_active: boolean;
  primary_color?: string;
  secondary_color?: string;
  accent_color?: string;
  logo_url?: string;
  created_at: string;
}

interface ThemeManagerProps {
  themes: Theme[];
  onThemeChange: () => void;
}

const ThemeManager: React.FC<ThemeManagerProps> = ({ themes, onThemeChange }) => {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [colorPickerOpen, setColorPickerOpen] = useState(false);
  const [selectedTheme, setSelectedTheme] = useState<Theme | null>(null);
  const [selectedColor, setSelectedColor] = useState<string>('primary_color');
  const [newTheme, setNewTheme] = useState({
    name: '',
    display_name: '',
    description: '',
    theme_type: 'basic',
    primary_color: '#1976d2',
    secondary_color: '#dc004e',
    accent_color: '#9c27b0',
    background_color: '#ffffff',
    text_color: '#000000',
    link_color: '#1976d2',
    primary_font: 'Roboto',
    secondary_font: 'Roboto',
    border_radius: '4px',
    spacing_unit: '8px',
    grid_columns: 12,
    supports_dark_mode: false,
    custom_css: ''
  });

  const {
    createTheme,
    updateTheme,
    deleteTheme,
    setDefaultTheme,
    duplicateTheme,
    generateThemeCSS,
    isLoading
  } = useWhiteLabel();

  const handleCreateTheme = async () => {
    try {
      await createTheme(newTheme);
      setCreateDialogOpen(false);
      setNewTheme({
        name: '',
        display_name: '',
        description: '',
        theme_type: 'basic',
        primary_color: '#1976d2',
        secondary_color: '#dc004e',
        accent_color: '#9c27b0',
        background_color: '#ffffff',
        text_color: '#000000',
        link_color: '#1976d2',
        primary_font: 'Roboto',
        secondary_font: 'Roboto',
        border_radius: '4px',
        spacing_unit: '8px',
        grid_columns: 12,
        supports_dark_mode: false,
        custom_css: ''
      });
      onThemeChange();
    } catch (error) {
      console.error('Failed to create theme:', error);
    }
  };

  const handleEditTheme = async () => {
    if (!selectedTheme) return;
    
    try {
      await updateTheme(selectedTheme.id, newTheme);
      setEditDialogOpen(false);
      setSelectedTheme(null);
      onThemeChange();
    } catch (error) {
      console.error('Failed to update theme:', error);
    }
  };

  const handleDeleteTheme = async () => {
    if (!selectedTheme) return;
    
    try {
      await deleteTheme(selectedTheme.id);
      setDeleteDialogOpen(false);
      setSelectedTheme(null);
      onThemeChange();
    } catch (error) {
      console.error('Failed to delete theme:', error);
    }
  };

  const handleSetDefault = async (themeId: string) => {
    try {
      await setDefaultTheme(themeId);
      onThemeChange();
    } catch (error) {
      console.error('Failed to set default theme:', error);
    }
  };

  const handleDuplicate = async (theme: Theme) => {
    try {
      await duplicateTheme(theme.id, `${theme.name}_copy`);
      onThemeChange();
    } catch (error) {
      console.error('Failed to duplicate theme:', error);
    }
  };

  const handleDownloadCSS = async (theme: Theme) => {
    try {
      const css = await generateThemeCSS(theme.id);
      const blob = new Blob([css], { type: 'text/css' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${theme.name}.css`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download CSS:', error);
    }
  };

  const openEditDialog = (theme: Theme) => {
    setSelectedTheme(theme);
    setNewTheme({
      name: theme.name,
      display_name: theme.display_name,
      description: theme.description || '',
      theme_type: theme.theme_type,
      primary_color: theme.primary_color || '#1976d2',
      secondary_color: theme.secondary_color || '#dc004e',
      accent_color: theme.accent_color || '#9c27b0',
      background_color: '#ffffff',
      text_color: '#000000',
      link_color: theme.primary_color || '#1976d2',
      primary_font: 'Roboto',
      secondary_font: 'Roboto',
      border_radius: '4px',
      spacing_unit: '8px',
      grid_columns: 12,
      supports_dark_mode: false,
      custom_css: ''
    });
    setEditDialogOpen(true);
  };

  const renderThemeCard = (theme: Theme) => (
    <Grid item xs={12} sm={6} md={4} key={theme.id}>
      <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <CardContent sx={{ flexGrow: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Avatar
              sx={{ 
                width: 40, 
                height: 40, 
                mr: 2,
                bgcolor: theme.primary_color || '#1976d2' 
              }}
            >
              <ColorIcon />
            </Avatar>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h6" component="h3">
                {theme.display_name || theme.name}
                {theme.is_default && (
                  <Chip 
                    label="Default" 
                    size="small" 
                    color="primary" 
                    sx={{ ml: 1 }}
                  />
                )}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {theme.theme_type.toUpperCase()}
              </Typography>
            </Box>
          </Box>

          {theme.description && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {theme.description}
            </Typography>
          )}

          <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
            {theme.primary_color && (
              <Box
                sx={{
                  width: 20,
                  height: 20,
                  bgcolor: theme.primary_color,
                  borderRadius: '50%',
                  border: '1px solid',
                  borderColor: 'divider'
                }}
              />
            )}
            {theme.secondary_color && (
              <Box
                sx={{
                  width: 20,
                  height: 20,
                  bgcolor: theme.secondary_color,
                  borderRadius: '50%',
                  border: '1px solid',
                  borderColor: 'divider'
                }}
              />
            )}
            {theme.accent_color && (
              <Box
                sx={{
                  width: 20,
                  height: 20,
                  bgcolor: theme.accent_color,
                  borderRadius: '50%',
                  border: '1px solid',
                  borderColor: 'divider'
                }}
              />
            )}
          </Box>

          <Typography variant="caption" color="text.secondary">
            Created: {new Date(theme.created_at).toLocaleDateString()}
          </Typography>
        </CardContent>

        <CardActions>
          <Tooltip title="Edit Theme">
            <IconButton 
              size="small" 
              onClick={() => openEditDialog(theme)}
              disabled={isLoading}
            >
              <EditIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Duplicate Theme">
            <IconButton 
              size="small" 
              onClick={() => handleDuplicate(theme)}
              disabled={isLoading}
            >
              <CopyIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Download CSS">
            <IconButton 
              size="small" 
              onClick={() => handleDownloadCSS(theme)}
              disabled={isLoading}
            >
              <DownloadIcon />
            </IconButton>
          </Tooltip>
          
          {!theme.is_default && (
            <Tooltip title="Set as Default">
              <IconButton 
                size="small" 
                onClick={() => handleSetDefault(theme.id)}
                disabled={isLoading}
              >
                <StarIcon />
              </IconButton>
            </Tooltip>
          )}
          
          {!theme.is_default && (
            <Tooltip title="Delete Theme">
              <IconButton 
                size="small" 
                color="error"
                onClick={() => {
                  setSelectedTheme(theme);
                  setDeleteDialogOpen(true);
                }}
                disabled={isLoading}
              >
                <DeleteIcon />
              </IconButton>
            </Tooltip>
          )}
        </CardActions>
      </Card>
    </Grid>
  );

  const renderColorPicker = (colorKey: string, label: string) => (
    <Box key={colorKey} sx={{ mb: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        {label}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box
          sx={{
            width: 40,
            height: 40,
            bgcolor: newTheme[colorKey as keyof typeof newTheme] as string,
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
            cursor: 'pointer'
          }}
          onClick={() => {
            setSelectedColor(colorKey);
            setColorPickerOpen(true);
          }}
        />
        <TextField
          size="small"
          value={newTheme[colorKey as keyof typeof newTheme] as string}
          onChange={(e) => setNewTheme({
            ...newTheme,
            [colorKey]: e.target.value
          })}
          sx={{ width: 100 }}
        />
      </Box>
    </Box>
  );

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">
          Theme Management
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
          disabled={isLoading}
        >
          Create Theme
        </Button>
      </Box>

      {themes.length === 0 ? (
        <Alert severity="info">
          No themes found. Create your first theme to get started.
        </Alert>
      ) : (
        <Grid container spacing={3}>
          {themes.map(renderThemeCard)}
        </Grid>
      )}

      {/* Create Theme Dialog */}
      <Dialog 
        open={createDialogOpen} 
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Create New Theme</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Theme Name"
                fullWidth
                value={newTheme.name}
                onChange={(e) => setNewTheme({ ...newTheme, name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Display Name"
                fullWidth
                value={newTheme.display_name}
                onChange={(e) => setNewTheme({ ...newTheme, display_name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Description"
                fullWidth
                multiline
                rows={2}
                value={newTheme.description}
                onChange={(e) => setNewTheme({ ...newTheme, description: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Theme Type</InputLabel>
                <Select
                  value={newTheme.theme_type}
                  onChange={(e) => setNewTheme({ ...newTheme, theme_type: e.target.value })}
                  label="Theme Type"
                >
                  <MenuItem value="basic">Basic</MenuItem>
                  <MenuItem value="advanced">Advanced</MenuItem>
                  <MenuItem value="custom">Custom</MenuItem>
                  <MenuItem value="premium">Premium</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" gutterBottom>Colors</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={4}>
                  {renderColorPicker('primary_color', 'Primary Color')}
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  {renderColorPicker('secondary_color', 'Secondary Color')}
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  {renderColorPicker('accent_color', 'Accent Color')}
                </Grid>
              </Grid>
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={newTheme.supports_dark_mode}
                    onChange={(e) => setNewTheme({ ...newTheme, supports_dark_mode: e.target.checked })}
                  />
                }
                label="Support Dark Mode"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            onClick={handleCreateTheme}
            disabled={!newTheme.name || isLoading}
          >
            Create Theme
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Theme Dialog */}
      <Dialog 
        open={editDialogOpen} 
        onClose={() => setEditDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Edit Theme</DialogTitle>
        <DialogContent>
          {/* Similar content to create dialog */}
          <Typography>Edit theme functionality will be implemented here</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            onClick={handleEditTheme}
            disabled={isLoading}
          >
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Theme</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete the theme "{selectedTheme?.display_name || selectedTheme?.name}"?
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            color="error" 
            onClick={handleDeleteTheme}
            disabled={isLoading}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Color Picker Dialog */}
      <Dialog open={colorPickerOpen} onClose={() => setColorPickerOpen(false)}>
        <DialogTitle>Choose Color</DialogTitle>
        <DialogContent>
          <ChromePicker
            color={newTheme[selectedColor as keyof typeof newTheme] as string}
            onChange={(color) => setNewTheme({
              ...newTheme,
              [selectedColor]: color.hex
            })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setColorPickerOpen(false)}>Done</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ThemeManager;