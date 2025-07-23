import React from 'react';
import { Outlet } from 'react-router-dom';
import {
  Box,
  CssBaseline,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Menu,
  MenuItem,
  Badge,
  Tooltip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  ChevronLeft as ChevronLeftIcon,
  Dashboard as DashboardIcon,
  People as PeopleIcon,
  Security as SecurityIcon,
  Group as GroupIcon,
  VpnKey as VpnKeyIcon,
  AccountTree as AccountTreeIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  AccountCircle as AccountCircleIcon,
  Logout as LogoutIcon,
  VideoLibrary as VideoLibraryIcon,
  Search as SearchIcon,
  Folder as FolderIcon,
  Upload as UploadIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../store';
import { clearAuth } from '../store/slices/authSlice';
import { toggleSidebar } from '../store/slices/uiSlice';
import { Navigation } from '../router/navigation';

const drawerWidth = 240;

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: Navigation.dashboard() },
  { text: 'Assets', icon: <VideoLibraryIcon />, path: Navigation.assets() },
  { text: 'Projects', icon: <FolderIcon />, path: Navigation.projects() },
  { text: 'Search', icon: <SearchIcon />, path: Navigation.search() },
  { text: 'Upload', icon: <UploadIcon />, path: Navigation.assetUpload() },
  { text: 'Users', icon: <PeopleIcon />, path: Navigation.users() },
  { text: 'Roles', icon: <SecurityIcon />, path: Navigation.roles() },
  { text: 'Groups', icon: <GroupIcon />, path: Navigation.groups() },
  { text: 'Permissions', icon: <VpnKeyIcon />, path: Navigation.permissions() },
  { text: 'Inheritance', icon: <AccountTreeIcon />, path: Navigation.inheritance() },
  { text: 'Settings', icon: <SettingsIcon />, path: Navigation.settings() },
];

const Layout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const { user } = useAppSelector(state => state.auth);
  const { sidebarOpen } = useAppSelector(state => state.ui.theme);
  const { notifications } = useAppSelector(state => state.ui);

  const [userMenuAnchor, setUserMenuAnchor] = React.useState<null | HTMLElement>(null);
  const [notificationAnchor, setNotificationAnchor] = React.useState<null | HTMLElement>(null);

  const handleDrawerToggle = () => {
    dispatch(toggleSidebar());
  };

  const handleUserMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setUserMenuAnchor(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setUserMenuAnchor(null);
  };

  const handleNotificationOpen = (event: React.MouseEvent<HTMLElement>) => {
    setNotificationAnchor(event.currentTarget);
  };

  const handleNotificationClose = () => {
    setNotificationAnchor(null);
  };

  const handleLogout = () => {
    dispatch(clearAuth());
    handleUserMenuClose();
    navigate(Navigation.login());
  };

  const handleNavigate = (path: string) => {
    navigate(path);
  };

  const unreadNotifications = notifications.filter(n => n.type === 'info').length;

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          transition: (theme) =>
            theme.transitions.create(['width', 'margin'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.leavingScreen,
            }),
          ...(sidebarOpen && {
            marginLeft: drawerWidth,
            width: `calc(100% - ${drawerWidth}px)`,
            transition: (theme) =>
              theme.transitions.create(['width', 'margin'], {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.enteringScreen,
              }),
          }),
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            onClick={handleDrawerToggle}
            edge="start"
            sx={{
              marginRight: 5,
              ...(sidebarOpen && { display: 'none' }),
            }}
          >
            <MenuIcon />
          </IconButton>
          
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            MAMS - Media Asset Management System
          </Typography>
          
          {/* Notifications */}
          <Tooltip title="Notifications">
            <IconButton
              color="inherit"
              onClick={handleNotificationOpen}
              sx={{ mr: 2 }}
            >
              <Badge badgeContent={unreadNotifications} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>
          
          {/* User Menu */}
          <Tooltip title="Account">
            <IconButton
              color="inherit"
              onClick={handleUserMenuOpen}
            >
              <Avatar
                sx={{ width: 32, height: 32 }}
                src={user?.avatar_url}
                alt={user?.display_name || user?.email}
              >
                {user?.display_name?.[0] || user?.email?.[0]}
              </Avatar>
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>
      
      {/* Sidebar */}
      <Drawer
        variant="permanent"
        open={sidebarOpen}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            transition: (theme) =>
              theme.transitions.create('width', {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.enteringScreen,
              }),
            ...(!sidebarOpen && {
              width: (theme) => theme.spacing(9),
              transition: (theme) =>
                theme.transitions.create('width', {
                  easing: theme.transitions.easing.sharp,
                  duration: theme.transitions.duration.leavingScreen,
                }),
            }),
          },
        }}
      >
        <Toolbar
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            px: [1],
          }}
        >
          <IconButton onClick={handleDrawerToggle}>
            <ChevronLeftIcon />
          </IconButton>
        </Toolbar>
        
        <Divider />
        
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding sx={{ display: 'block' }}>
              <ListItemButton
                onClick={() => handleNavigate(item.path)}
                selected={location.pathname === item.path}
                sx={{
                  minHeight: 48,
                  justifyContent: sidebarOpen ? 'initial' : 'center',
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: sidebarOpen ? 3 : 'auto',
                    justifyContent: 'center',
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText 
                  primary={item.text} 
                  sx={{ opacity: sidebarOpen ? 1 : 0 }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Drawer>
      
      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
      
      {/* User Menu */}
      <Menu
        anchorEl={userMenuAnchor}
        open={Boolean(userMenuAnchor)}
        onClose={handleUserMenuClose}
        onClick={handleUserMenuClose}
      >
        <MenuItem onClick={() => navigate(Navigation.profile())}>
          <ListItemIcon>
            <AccountCircleIcon fontSize="small" />
          </ListItemIcon>
          Profile
        </MenuItem>
        <MenuItem onClick={() => navigate(Navigation.settings())}>
          <ListItemIcon>
            <SettingsIcon fontSize="small" />
          </ListItemIcon>
          Settings
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          Logout
        </MenuItem>
      </Menu>
      
      {/* Notification Menu */}
      <Menu
        anchorEl={notificationAnchor}
        open={Boolean(notificationAnchor)}
        onClose={handleNotificationClose}
        PaperProps={{
          sx: {
            maxWidth: 320,
            maxHeight: 400,
          },
        }}
      >
        {notifications.length === 0 ? (
          <MenuItem>
            <Typography variant="body2" color="text.secondary">
              No notifications
            </Typography>
          </MenuItem>
        ) : (
          notifications.slice(0, 10).map((notification) => (
            <MenuItem key={notification.id} onClick={handleNotificationClose}>
              <Box>
                <Typography variant="body2" noWrap>
                  {notification.message}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {notification.type}
                </Typography>
              </Box>
            </MenuItem>
          ))
        )}
      </Menu>
    </Box>
  );
};

export default Layout;