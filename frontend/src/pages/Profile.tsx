import React, { useState, useRef } from 'react';
import {
  Box,
  Typography,
  Paper,
  Avatar,
  Grid,
  TextField,
  Button,
  Divider,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Switch,
  FormControlLabel,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Chip,
  Tooltip,
  CircularProgress,
  LinearProgress,
} from '@mui/material';
import {
  AccountCircle as AccountCircleIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Security as SecurityIcon,
  Notifications as NotificationsIcon,
  Language as LanguageIcon,
  Palette as ThemeIcon,
  Storage as StorageIcon,
  History as HistoryIcon,
  CloudUpload as UploadIcon,
  Cancel as CancelIcon,
  VpnKey as PasswordIcon,
  PhoneIphone as PhoneIcon,
  Email as EmailIcon,
  Business as OrganizationIcon,
  CalendarToday as DateIcon,
  Badge as BadgeIcon,
  Group as GroupIcon,
  Assignment as RoleIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { useAppSelector, useAppDispatch } from '../store';
import { updateProfile } from '../store/slices/authSlice';
import { addNotification } from '../store/slices/uiSlice';
import { logger } from '../utils/logger';
import { formatFileSize, formatDate } from '../utils/formatters';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`profile-tabpanel-${index}`}
      aria-labelledby={`profile-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
};

const Profile: React.FC = () => {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector(state => state.auth);
  const [tabValue, setTabValue] = useState(0);
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [formData, setFormData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    display_name: user?.display_name || '',
    email: user?.email || '',
    phone: user?.phone || '',
    organization: user?.organization || '',
    bio: user?.bio || '',
  });

  const [preferences, setPreferences] = useState({
    emailNotifications: true,
    pushNotifications: false,
    smsNotifications: false,
    darkMode: false,
    language: 'en',
    timezone: 'UTC',
    autoPlayVideos: true,
    showThumbnails: true,
  });

  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: '',
  });

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleEditToggle = () => {
    if (editMode) {
      // Cancel edit
      setFormData({
        first_name: user?.first_name || '',
        last_name: user?.last_name || '',
        display_name: user?.display_name || '',
        email: user?.email || '',
        phone: user?.phone || '',
        organization: user?.organization || '',
        bio: user?.bio || '',
      });
    }
    setEditMode(!editMode);
  };

  const handleInputChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [field]: event.target.value,
    }));
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      // API call to update profile would go here
      // await updateProfileApi(formData);
      
      dispatch(updateProfile(formData));
      dispatch(addNotification({
        type: 'success',
        message: 'Profile updated successfully',
      }));
      
      logger.info('Profile updated', {
        userId: user?.id,
        actionType: 'profile_update',
      });
      
      setEditMode(false);
    } catch (error) {
      dispatch(addNotification({
        type: 'error',
        message: 'Failed to update profile',
      }));
      
      logger.error('Profile update failed', {
        userId: user?.id,
        error,
        actionType: 'profile_update_error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      try {
        // Upload avatar logic would go here
        logger.info('Avatar upload started', {
          fileName: file.name,
          fileSize: file.size,
          actionType: 'avatar_upload',
        });
        
        dispatch(addNotification({
          type: 'info',
          message: 'Uploading avatar...',
        }));
      } catch (error) {
        logger.error('Avatar upload failed', {
          error,
          actionType: 'avatar_upload_error',
        });
      }
    }
  };

  const handlePasswordChange = async () => {
    if (passwords.new !== passwords.confirm) {
      dispatch(addNotification({
        type: 'error',
        message: 'New passwords do not match',
      }));
      return;
    }

    try {
      setLoading(true);
      // API call to change password would go here
      // await changePasswordApi(passwords);
      
      dispatch(addNotification({
        type: 'success',
        message: 'Password changed successfully',
      }));
      
      logger.info('Password changed', {
        userId: user?.id,
        actionType: 'password_change',
      });
      
      setChangePasswordOpen(false);
      setPasswords({ current: '', new: '', confirm: '' });
    } catch (error) {
      dispatch(addNotification({
        type: 'error',
        message: 'Failed to change password',
      }));
      
      logger.error('Password change failed', {
        userId: user?.id,
        error,
        actionType: 'password_change_error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handlePreferenceChange = (pref: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setPreferences(prev => ({
      ...prev,
      [pref]: event.target.checked,
    }));
  };

  // Mock data for activity and storage
  const recentActivity = [
    { id: 1, action: 'Uploaded', item: 'Project_Final_v3.mp4', time: new Date(Date.now() - 2 * 60 * 60 * 1000) },
    { id: 2, action: 'Downloaded', item: 'Marketing_Assets.zip', time: new Date(Date.now() - 5 * 60 * 60 * 1000) },
    { id: 3, action: 'Shared', item: 'Q4_Presentation.pptx', time: new Date(Date.now() - 24 * 60 * 60 * 1000) },
    { id: 4, action: 'Edited', item: 'Brand_Guidelines.pdf', time: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000) },
  ];

  const storageUsed = 45.2; // GB
  const storageTotal = 100; // GB
  const storagePercentage = (storageUsed / storageTotal) * 100;

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <AccountCircleIcon sx={{ fontSize: 32, mr: 2, color: 'primary.main' }} />
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
          Profile
        </Typography>
        {!editMode ? (
          <Button variant="contained" startIcon={<EditIcon />} onClick={handleEditToggle}>
            Edit Profile
          </Button>
        ) : (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={<CancelIcon />}
              onClick={handleEditToggle}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSave}
              disabled={loading}
            >
              {loading ? <CircularProgress size={20} /> : 'Save Changes'}
            </Button>
          </Box>
        )}
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Box sx={{ position: 'relative', display: 'inline-block' }}>
              <Avatar
                src={user?.avatar_url}
                sx={{ width: 120, height: 120, mx: 'auto', mb: 2 }}
              >
                {user?.display_name?.[0] || user?.first_name?.[0] || user?.email?.[0]}
              </Avatar>
              {editMode && (
                <Tooltip title="Change Photo">
                  <IconButton
                    sx={{
                      position: 'absolute',
                      bottom: 16,
                      right: -8,
                      backgroundColor: 'background.paper',
                      '&:hover': { backgroundColor: 'action.hover' },
                    }}
                    onClick={handleAvatarClick}
                  >
                    <UploadIcon />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
            <input
              ref={fileInputRef}
              type="file"
              hidden
              accept="image/*"
              onChange={handleAvatarChange}
            />
            <Typography variant="h6" gutterBottom>
              {user?.display_name || `${user?.first_name} ${user?.last_name}`}
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {user?.email}
            </Typography>
            <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Chip
                icon={<RoleIcon />}
                label={user?.is_superuser ? 'Super Admin' : 'User'}
                size="small"
                color={user?.is_superuser ? 'error' : 'default'}
              />
              {user?.groups && user.groups.length > 0 && (
                <Chip
                  icon={<GroupIcon />}
                  label={`${user.groups.length} Groups`}
                  size="small"
                />
              )}
              <Typography variant="caption" color="text.secondary">
                Member since {formatDate(user?.created_at || new Date())}
              </Typography>
            </Box>
          </Paper>

          {/* Storage Usage */}
          <Paper sx={{ p: 3, mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              Storage Usage
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">
                  {formatFileSize(storageUsed * 1024 * 1024 * 1024)} of {formatFileSize(storageTotal * 1024 * 1024 * 1024)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {Math.round(storagePercentage)}%
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={storagePercentage}
                sx={{
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: 'action.hover',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 4,
                    backgroundColor: storagePercentage > 80 ? 'error.main' : 'primary.main',
                  },
                }}
              />
            </Box>
            <Button variant="outlined" size="small" fullWidth>
              Manage Storage
            </Button>
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Tabs value={tabValue} onChange={handleTabChange}>
              <Tab label="Personal Info" icon={<BadgeIcon />} iconPosition="start" />
              <Tab label="Security" icon={<SecurityIcon />} iconPosition="start" />
              <Tab label="Preferences" icon={<NotificationsIcon />} iconPosition="start" />
              <Tab label="Activity" icon={<HistoryIcon />} iconPosition="start" />
            </Tabs>

            <TabPanel value={tabValue} index={0}>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="First Name"
                    value={formData.first_name}
                    onChange={handleInputChange('first_name')}
                    disabled={!editMode}
                    InputProps={{
                      startAdornment: <BadgeIcon sx={{ mr: 1, color: 'action.active' }} />,
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Last Name"
                    value={formData.last_name}
                    onChange={handleInputChange('last_name')}
                    disabled={!editMode}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Display Name"
                    value={formData.display_name}
                    onChange={handleInputChange('display_name')}
                    disabled={!editMode}
                    helperText="This is how your name will appear to others"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Email"
                    value={formData.email}
                    onChange={handleInputChange('email')}
                    disabled={!editMode}
                    InputProps={{
                      startAdornment: <EmailIcon sx={{ mr: 1, color: 'action.active' }} />,
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Phone"
                    value={formData.phone}
                    onChange={handleInputChange('phone')}
                    disabled={!editMode}
                    InputProps={{
                      startAdornment: <PhoneIcon sx={{ mr: 1, color: 'action.active' }} />,
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Organization"
                    value={formData.organization}
                    onChange={handleInputChange('organization')}
                    disabled={!editMode}
                    InputProps={{
                      startAdornment: <OrganizationIcon sx={{ mr: 1, color: 'action.active' }} />,
                    }}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Bio"
                    multiline
                    rows={4}
                    value={formData.bio}
                    onChange={handleInputChange('bio')}
                    disabled={!editMode}
                    helperText="Tell others about yourself"
                  />
                </Grid>
              </Grid>
            </TabPanel>

            <TabPanel value={tabValue} index={1}>
              <List>
                <ListItem>
                  <ListItemIcon>
                    <PasswordIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Password"
                    secondary="Last changed 30 days ago"
                  />
                  <ListItemSecondaryAction>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => setChangePasswordOpen(true)}
                    >
                      Change Password
                    </Button>
                  </ListItemSecondaryAction>
                </ListItem>
                <Divider component="li" />
                <ListItem>
                  <ListItemIcon>
                    <SecurityIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Two-Factor Authentication"
                    secondary={user?.mfa_enabled ? 'Enabled' : 'Not enabled'}
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      edge="end"
                      checked={user?.mfa_enabled || false}
                      onChange={() => {}}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                <Divider component="li" />
                <ListItem>
                  <ListItemIcon>
                    <HistoryIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Login History"
                    secondary="View your recent login activity"
                  />
                  <ListItemSecondaryAction>
                    <Button variant="text" size="small">
                      View History
                    </Button>
                  </ListItemSecondaryAction>
                </ListItem>
              </List>

              {user?.last_login && (
                <Alert severity="info" sx={{ mt: 3 }}>
                  Last login: {formatDistanceToNow(new Date(user.last_login), { addSuffix: true })} from {user.last_login_ip || 'Unknown IP'}
                </Alert>
              )}
            </TabPanel>

            <TabPanel value={tabValue} index={2}>
              <Typography variant="h6" gutterBottom>
                Notifications
              </Typography>
              <List>
                <ListItem>
                  <ListItemIcon>
                    <EmailIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Email Notifications"
                    secondary="Receive updates via email"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      edge="end"
                      checked={preferences.emailNotifications}
                      onChange={handlePreferenceChange('emailNotifications')}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <NotificationsIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Push Notifications"
                    secondary="Receive browser notifications"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      edge="end"
                      checked={preferences.pushNotifications}
                      onChange={handlePreferenceChange('pushNotifications')}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <PhoneIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="SMS Notifications"
                    secondary="Receive important updates via SMS"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      edge="end"
                      checked={preferences.smsNotifications}
                      onChange={handlePreferenceChange('smsNotifications')}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
              </List>

              <Divider sx={{ my: 3 }} />

              <Typography variant="h6" gutterBottom>
                Display Settings
              </Typography>
              <List>
                <ListItem>
                  <ListItemIcon>
                    <ThemeIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Dark Mode"
                    secondary="Use dark theme"
                  />
                  <ListItemSecondaryAction>
                    <Switch
                      edge="end"
                      checked={preferences.darkMode}
                      onChange={handlePreferenceChange('darkMode')}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <LanguageIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Language"
                    secondary="English (US)"
                  />
                  <ListItemSecondaryAction>
                    <Button variant="text" size="small">
                      Change
                    </Button>
                  </ListItemSecondaryAction>
                </ListItem>
              </List>
            </TabPanel>

            <TabPanel value={tabValue} index={3}>
              <Typography variant="h6" gutterBottom>
                Recent Activity
              </Typography>
              <List>
                {recentActivity.map((activity) => (
                  <React.Fragment key={activity.id}>
                    <ListItem>
                      <ListItemText
                        primary={`${activity.action} ${activity.item}`}
                        secondary={formatDistanceToNow(activity.time, { addSuffix: true })}
                      />
                    </ListItem>
                    {activity.id < recentActivity.length && <Divider component="li" />}
                  </React.Fragment>
                ))}
              </List>
              <Button variant="text" fullWidth sx={{ mt: 2 }}>
                View All Activity
              </Button>
            </TabPanel>
          </Paper>
        </Grid>
      </Grid>

      {/* Change Password Dialog */}
      <Dialog open={changePasswordOpen} onClose={() => setChangePasswordOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Change Password</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField
              fullWidth
              type="password"
              label="Current Password"
              value={passwords.current}
              onChange={(e) => setPasswords(prev => ({ ...prev, current: e.target.value }))}
            />
            <TextField
              fullWidth
              type="password"
              label="New Password"
              value={passwords.new}
              onChange={(e) => setPasswords(prev => ({ ...prev, new: e.target.value }))}
            />
            <TextField
              fullWidth
              type="password"
              label="Confirm New Password"
              value={passwords.confirm}
              onChange={(e) => setPasswords(prev => ({ ...prev, confirm: e.target.value }))}
              error={passwords.new !== passwords.confirm && passwords.confirm !== ''}
              helperText={passwords.new !== passwords.confirm && passwords.confirm !== '' ? 'Passwords do not match' : ''}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setChangePasswordOpen(false)}>Cancel</Button>
          <Button
            onClick={handlePasswordChange}
            variant="contained"
            disabled={!passwords.current || !passwords.new || !passwords.confirm || loading}
          >
            {loading ? <CircularProgress size={20} /> : 'Change Password'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Profile;