import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
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
  Chip,
  useTheme,
  useMediaQuery,
  Collapse,
} from '@mui/material';
import {
  Menu as MenuIcon,
  ChevronLeft as ChevronLeftIcon,
  Dashboard as DashboardIcon,
  VideoLibrary as VideoLibraryIcon,
  Folder as FolderIcon,
  Search as SearchIcon,
  CloudUpload as CloudUploadIcon,
  People as PeopleIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  AccountCircle as AccountCircleIcon,
  Logout as LogoutIcon,
  Analytics as AnalyticsIcon,
  Security as SecurityIcon,
  ExpandLess,
  ExpandMore,
  Storage as StorageIcon,
  Queue as QueueIcon,
  Assessment as AssessmentIcon,
  AdminPanelSettings as AdminIcon,
} from '@mui/icons-material';

import { useAuth } from '../../hooks/useAuth';
import { useErrorHandler } from '../../hooks/useErrorHandler';
import { logger } from '../../utils/logger';
import { ROUTES } from '../../router/routes';
import { Navigation } from '../../router/navigation';

const drawerWidth = 260;

interface MenuItem {
  text: string;
  icon: React.ReactNode;
  path?: string;
  children?: MenuItem[];
  permission?: string;
  adminOnly?: boolean;
}

const Layout: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, hasPermission } = useAuth();
  const { handleError } = useErrorHandler();

  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(null);
  const [notificationAnchor, setNotificationAnchor] = useState<null | HTMLElement>(null);
  const [expandedSections, setExpandedSections] = useState<string[]>(['media']);

  // Navigation menu items with permissions
  const menuItems: MenuItem[] = [
    {
      text: 'Dashboard',
      icon: <DashboardIcon />,
      path: ROUTES.DASHBOARD,
    },
    {
      text: 'Media Management',
      icon: <VideoLibraryIcon />,
      children: [
        {
          text: 'Browse Assets',
          icon: <VideoLibraryIcon />,
          path: ROUTES.ASSETS,
          permission: 'assets.read',
        },
        {
          text: 'Advanced Asset Browser',
          icon: <VideoLibraryIcon />,
          path: ROUTES.ASSET_ADVANCED,
          permission: 'assets.read',
        },
        {
          text: 'Upload Assets',
          icon: <CloudUploadIcon />,
          path: ROUTES.ASSET_UPLOAD,
          permission: 'assets.create',
        },
        {
          text: 'Projects',
          icon: <FolderIcon />,
          path: ROUTES.PROJECTS,
          permission: 'projects.read',
        },
        {
          text: 'Search',
          icon: <SearchIcon />,
          path: ROUTES.SEARCH,
          permission: 'assets.read',
        },
      ],
    },
    {
      text: 'Analytics',
      icon: <AnalyticsIcon />,
      children: [
        {
          text: 'Usage Analytics',
          icon: <AssessmentIcon />,
          path: ROUTES.ANALYTICS,
          permission: 'analytics.read',
        },
        {
          text: 'Storage Analytics',
          icon: <StorageIcon />,
          path: ROUTES.STORAGE_ANALYTICS,
          permission: 'analytics.read',
        },
        {
          text: 'Processing Queue',
          icon: <QueueIcon />,
          path: ROUTES.PROCESSING_QUEUE,
          permission: 'processing.read',
        },
      ],
    },
    {
      text: 'Administration',
      icon: <AdminIcon />,
      adminOnly: true,
      children: [
        {
          text: 'User Management',
          icon: <PeopleIcon />,
          path: ROUTES.USERS,
          permission: 'users.read',
        },
        {
          text: 'Tenant Management',
          icon: <AdminIcon />,
          path: ROUTES.TENANTS,
          permission: 'system.manage_tenants',
        },
        {
          text: 'Security',
          icon: <SecurityIcon />,
          path: ROUTES.SECURITY_SETTINGS,
          permission: 'security.read',
        },
        {
          text: 'System Status',
          icon: <AssessmentIcon />,
          path: ROUTES.SYSTEM_STATUS,
          permission: 'system.read',
        },
      ],
    },
  ];

  const handleDrawerToggle = () => {
    setSidebarOpen(!sidebarOpen);
    logger.info('Sidebar toggled', {
      open: !sidebarOpen,
      userId: user?.id,
      actionType: 'sidebar_toggle',
    });
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

  const handleLogout = async () => {
    try {
      handleUserMenuClose();
      logger.info('Logout initiated from layout', {
        userId: user?.id,
        actionType: 'logout_initiated',
      });
      
      await logout();
      navigate(ROUTES.LOGIN);
    } catch (error: any) {
      handleError(error, {
        context: 'Layout.handleLogout',
        userMessage: 'Failed to logout. Please try again.',
      });
    }
  };

  const handleNavigate = (path: string) => {
    navigate(path);
    if (isMobile) {
      setSidebarOpen(false);
    }
    
    logger.info('Navigation from sidebar', {
      path,
      userId: user?.id,
      actionType: 'sidebar_navigation',
    });
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => 
      prev.includes(section) 
        ? prev.filter(s => s !== section)
        : [...prev, section]
    );
  };

  const isItemVisible = (item: MenuItem): boolean => {
    // Check admin permission
    if (item.adminOnly && !user?.isSuperuser) {
      return false;
    }
    
    // Check specific permission
    if (item.permission && !hasPermission(item.permission)) {
      return false;
    }
    
    // For parent items with children, show if any child is visible
    if (item.children) {
      return item.children.some(child => isItemVisible(child));
    }
    
    return true;
  };

  const isPathActive = (path: string): boolean => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  const renderMenuItem = (item: MenuItem, depth = 0) => {
    if (!isItemVisible(item)) {
      return null;
    }

    const hasChildren = item.children && item.children.length > 0;
    const sectionKey = item.text.toLowerCase().replace(/\s+/g, '_');
    const isExpanded = expandedSections.includes(sectionKey);
    const isActive = item.path ? isPathActive(item.path) : false;

    return (
      <React.Fragment key={item.text}>
        <ListItem disablePadding sx={{ display: 'block' }}>
          <ListItemButton
            onClick={() => {
              if (hasChildren) {
                toggleSection(sectionKey);
              } else if (item.path) {
                handleNavigate(item.path);
              }
            }}
            selected={isActive}
            sx={{
              minHeight: 48,
              pl: 2 + (depth * 2),
              justifyContent: sidebarOpen ? 'initial' : 'center',
            }}
          >
            <ListItemIcon
              sx={{
                minWidth: 0,
                mr: sidebarOpen ? 2 : 'auto',
                justifyContent: 'center',
                color: isActive ? 'primary.main' : 'inherit',
              }}
            >
              {item.icon}
            </ListItemIcon>
            
            {sidebarOpen && (
              <>
                <ListItemText 
                  primary={item.text}
                  sx={{ 
                    opacity: sidebarOpen ? 1 : 0,
                    color: isActive ? 'primary.main' : 'inherit',
                  }}
                />
                {hasChildren && (
                  isExpanded ? <ExpandLess /> : <ExpandMore />
                )}
              </>
            )}
          </ListItemButton>
        </ListItem>
        
        {hasChildren && sidebarOpen && (
          <Collapse in={isExpanded} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              {item.children!.map(child => renderMenuItem(child, depth + 1))}
            </List>
          </Collapse>
        )}
      </React.Fragment>
    );
  };

  const getPageTitle = (): string => {
    const path = location.pathname;
    if (path === ROUTES.DASHBOARD) return 'Dashboard';
    if (path.startsWith('/assets')) return 'Media Assets';
    if (path.startsWith('/projects')) return 'Projects';
    if (path.startsWith('/search')) return 'Search';
    if (path.startsWith('/users')) return 'User Management';
    if (path.startsWith('/analytics')) return 'Analytics';
    if (path.startsWith('/settings')) return 'Settings';
    return 'MAMS';
  };

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          zIndex: theme.zIndex.drawer + 1,
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          ...(sidebarOpen && !isMobile && {
            marginLeft: drawerWidth,
            width: `calc(100% - ${drawerWidth}px)`,
            transition: theme.transitions.create(['width', 'margin'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
          }),
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="toggle drawer"
            onClick={handleDrawerToggle}
            edge="start"
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {getPageTitle()}
          </Typography>

          {/* System Status Indicator */}
          <Chip
            label="System Online"
            color="success"
            size="small"
            sx={{ mr: 2, display: { xs: 'none', sm: 'flex' } }}
          />
          
          {/* Notifications */}
          <Tooltip title="Notifications">
            <IconButton
              color="inherit"
              onClick={handleNotificationOpen}
              sx={{ mr: 1 }}
            >
              <Badge badgeContent={0} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>
          
          {/* User Menu */}
          <Tooltip title="Account">
            <IconButton
              color="inherit"
              onClick={handleUserMenuOpen}
              sx={{ ml: 1 }}
            >
              <Avatar
                sx={{ width: 32, height: 32 }}
                src={user?.avatar}
                alt={user?.firstName || user?.email}
              >
                {(user?.firstName?.[0] || user?.email?.[0] || 'U').toUpperCase()}
              </Avatar>
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>
      
      {/* Sidebar */}
      <Drawer
        variant={isMobile ? 'temporary' : 'permanent'}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            transition: theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
            ...(!sidebarOpen && !isMobile && {
              width: theme.spacing(9),
              transition: theme.transitions.create('width', {
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
            justifyContent: sidebarOpen ? 'space-between' : 'center',
            px: [1],
          }}
        >
          {sidebarOpen && (
            <Typography variant="h6" component="div" noWrap>
              MAMS
            </Typography>
          )}
          {!isMobile && (
            <IconButton onClick={handleDrawerToggle}>
              <ChevronLeftIcon />
            </IconButton>
          )}
        </Toolbar>
        
        <Divider />
        
        <List sx={{ flexGrow: 1 }}>
          {menuItems.map(item => renderMenuItem(item))}
        </List>
        
        <Divider />
        
        {/* User info at bottom */}
        {sidebarOpen && user && (
          <Box sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Avatar
                sx={{ width: 32, height: 32, mr: 1 }}
                src={user.avatar}
                alt={user.firstName || user.email}
              >
                {(user.firstName?.[0] || user.email?.[0] || 'U').toUpperCase()}
              </Avatar>
              <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                <Typography variant="body2" noWrap>
                  {user.firstName ? `${user.firstName} ${user.lastName}` : user.email}
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap>
                  {user.role || 'User'}
                </Typography>
              </Box>
            </Box>
          </Box>
        )}
      </Drawer>
      
      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { 
            sm: sidebarOpen 
              ? `calc(100% - ${drawerWidth}px)` 
              : `calc(100% - ${theme.spacing(9)})` 
          },
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
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
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <MenuItem onClick={() => navigate(ROUTES.PROFILE)}>
          <ListItemIcon>
            <AccountCircleIcon fontSize="small" />
          </ListItemIcon>
          Profile
        </MenuItem>
        <MenuItem onClick={() => navigate(ROUTES.SETTINGS)}>
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
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        PaperProps={{
          sx: {
            maxWidth: 360,
            maxHeight: 400,
          },
        }}
      >
        <MenuItem>
          <Box sx={{ py: 1 }}>
            <Typography variant="body2" color="text.secondary" align="center">
              No new notifications
            </Typography>
          </Box>
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default Layout;