export const ROUTES = {
  // Public routes
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  
  // Main routes
  HOME: '/',
  DASHBOARD: '/dashboard',
  
  // Asset Management
  ASSETS: '/assets',
  ASSET_DETAIL: '/assets/:id',
  ASSET_UPLOAD: '/assets/upload',
  ASSET_EDIT: '/assets/:id/edit',
  ASSET_ADVANCED: '/assets/advanced',
  
  // Project Management
  PROJECTS: '/projects',
  PROJECT_DETAIL: '/projects/:id',
  PROJECT_CREATE: '/projects/create',
  PROJECT_EDIT: '/projects/:id/edit',
  SHOTLIST: '/projects/:projectId/shotlists/:shotlistId',
  
  // Search
  SEARCH: '/search',
  SEARCH_RESULTS: '/search/results',
  SAVED_SEARCHES: '/search/saved',
  
  // User Management
  USERS: '/users',
  USER_DETAIL: '/users/:id',
  USER_CREATE: '/users/create',
  USER_EDIT: '/users/:id/edit',
  PROFILE: '/profile',
  
  // Analytics
  ANALYTICS: '/analytics',
  STORAGE_ANALYTICS: '/analytics/storage',
  PROCESSING_QUEUE: '/processing/queue',
  ACTIVITY_LOG: '/activity',
  
  // System
  SYSTEM_STATUS: '/system/status',
  SECURITY_SETTINGS: '/security',
  SETTINGS: '/settings',
  
  // Tenant Management
  TENANTS: '/tenants',
  TENANT_DETAIL: '/tenants/:tenantId',
  
  // Role Management
  ROLES: '/roles',
  ROLE_DETAIL: '/roles/:id',
  ROLE_CREATE: '/roles/create',
  ROLE_EDIT: '/roles/:id/edit',
  
  // Group Management
  GROUPS: '/groups',
  GROUP_DETAIL: '/groups/:id',
  GROUP_CREATE: '/groups/create',
  GROUP_EDIT: '/groups/:id/edit',
  
  // Permission Management
  PERMISSIONS: '/permissions',
  PERMISSION_DETAIL: '/permissions/:id',
  PERMISSION_CREATE: '/permissions/create',
  PERMISSION_EDIT: '/permissions/:id/edit',

  // Workflow Management
  WORKFLOWS: '/workflows',
  WORKFLOW_DESIGNER: '/workflows/designer',
  WORKFLOW_DESIGNER_EDIT: '/workflows/designer/:workflowId',
  WORKFLOW_TEMPLATES: '/workflows/templates',
  WORKFLOW_HISTORY: '/workflows/history',
  
  // System
  INHERITANCE: '/inheritance',
  SETTINGS: '/settings',
  PROFILE: '/profile',
  
  // Error pages
  NOT_FOUND: '/404',
  UNAUTHORIZED: '/unauthorized',
  SERVER_ERROR: '/500',
} as const;

export type RouteKey = keyof typeof ROUTES;
export type RoutePath = typeof ROUTES[RouteKey];

// Route permissions mapping
export const ROUTE_PERMISSIONS = {
  [ROUTES.DASHBOARD]: [],
  [ROUTES.ASSETS]: ['asset.read'],
  [ROUTES.ASSET_DETAIL]: ['asset.read'],
  [ROUTES.ASSET_UPLOAD]: ['asset.create'],
  [ROUTES.ASSET_EDIT]: ['asset.update'],
  [ROUTES.ASSET_ADVANCED]: ['asset.read'],
  [ROUTES.PROJECTS]: ['project.read'],
  [ROUTES.PROJECT_DETAIL]: ['project.read'],
  [ROUTES.PROJECT_CREATE]: ['project.create'],
  [ROUTES.PROJECT_EDIT]: ['project.update'],
  [ROUTES.SEARCH]: ['asset.read'],
  [ROUTES.SEARCH_RESULTS]: ['asset.read'],
  [ROUTES.SAVED_SEARCHES]: ['asset.read'],
  [ROUTES.USERS]: ['user.read'],
  [ROUTES.USER_DETAIL]: ['user.read'],
  [ROUTES.USER_CREATE]: ['user.create'],
  [ROUTES.USER_EDIT]: ['user.update'],
  [ROUTES.ROLES]: ['role.read'],
  [ROUTES.ROLE_DETAIL]: ['role.read'],
  [ROUTES.ROLE_CREATE]: ['role.create'],
  [ROUTES.ROLE_EDIT]: ['role.update'],
  [ROUTES.GROUPS]: ['group.read'],
  [ROUTES.GROUP_DETAIL]: ['group.read'],
  [ROUTES.GROUP_CREATE]: ['group.create'],
  [ROUTES.GROUP_EDIT]: ['group.update'],
  [ROUTES.PERMISSIONS]: ['permission.read'],
  [ROUTES.PERMISSION_DETAIL]: ['permission.read'],
  [ROUTES.PERMISSION_CREATE]: ['permission.create'],
  [ROUTES.PERMISSION_EDIT]: ['permission.update'],
  [ROUTES.WORKFLOWS]: ['workflow.read'],
  [ROUTES.WORKFLOW_DESIGNER]: ['workflow.create'],
  [ROUTES.WORKFLOW_DESIGNER_EDIT]: ['workflow.update'],
  [ROUTES.WORKFLOW_TEMPLATES]: ['workflow.read'],
  [ROUTES.WORKFLOW_HISTORY]: ['workflow.read'],
  [ROUTES.INHERITANCE]: ['permission.read'],
  [ROUTES.SETTINGS]: ['system.manage'],
  [ROUTES.PROFILE]: [],
} as const;

// Route metadata for breadcrumbs and page titles
export const ROUTE_METADATA = {
  [ROUTES.DASHBOARD]: {
    title: 'Dashboard',
    breadcrumb: 'Dashboard',
    description: 'MAMS system overview and analytics',
  },
  [ROUTES.ASSETS]: {
    title: 'Assets',
    breadcrumb: 'Assets',
    description: 'Browse and manage media assets',
  },
  [ROUTES.ASSET_DETAIL]: {
    title: 'Asset Details',
    breadcrumb: 'Asset Details',
    description: 'View and edit asset information',
  },
  [ROUTES.ASSET_UPLOAD]: {
    title: 'Upload Assets',
    breadcrumb: 'Upload',
    description: 'Upload new media assets',
  },
  [ROUTES.ASSET_EDIT]: {
    title: 'Edit Asset',
    breadcrumb: 'Edit',
    description: 'Edit asset information',
  },
  [ROUTES.ASSET_ADVANCED]: {
    title: 'Advanced Asset Browser',
    breadcrumb: 'Advanced Browser',
    description: 'Advanced asset browsing with drag and drop capabilities',
  },
  [ROUTES.PROJECTS]: {
    title: 'Projects',
    breadcrumb: 'Projects',
    description: 'Manage media projects',
  },
  [ROUTES.PROJECT_DETAIL]: {
    title: 'Project Details',
    breadcrumb: 'Project Details',
    description: 'View and edit project information',
  },
  [ROUTES.PROJECT_CREATE]: {
    title: 'Create Project',
    breadcrumb: 'Create',
    description: 'Create a new media project',
  },
  [ROUTES.PROJECT_EDIT]: {
    title: 'Edit Project',
    breadcrumb: 'Edit',
    description: 'Edit project information',
  },
  [ROUTES.SHOTLIST]: {
    title: 'Shotlist',
    breadcrumb: 'Shotlist',
    description: 'Edit and manage shotlist',
  },
  [ROUTES.SEARCH]: {
    title: 'Search',
    breadcrumb: 'Search',
    description: 'Search across all media assets',
  },
  [ROUTES.SEARCH_RESULTS]: {
    title: 'Search Results',
    breadcrumb: 'Results',
    description: 'Search results',
  },
  [ROUTES.SAVED_SEARCHES]: {
    title: 'Saved Searches',
    breadcrumb: 'Saved Searches',
    description: 'Manage your saved searches',
  },
  [ROUTES.USERS]: {
    title: 'User Management',
    breadcrumb: 'Users',
    description: 'Manage system users',
  },
  [ROUTES.USER_DETAIL]: {
    title: 'User Details',
    breadcrumb: 'User Details',
    description: 'View and edit user information',
  },
  [ROUTES.USER_CREATE]: {
    title: 'Create User',
    breadcrumb: 'Create',
    description: 'Create a new user',
  },
  [ROUTES.USER_EDIT]: {
    title: 'Edit User',
    breadcrumb: 'Edit',
    description: 'Edit user information',
  },
  [ROUTES.ROLES]: {
    title: 'Role Management',
    breadcrumb: 'Roles',
    description: 'Manage system roles',
  },
  [ROUTES.ROLE_DETAIL]: {
    title: 'Role Details',
    breadcrumb: 'Role Details',
    description: 'View and edit role information',
  },
  [ROUTES.ROLE_CREATE]: {
    title: 'Create Role',
    breadcrumb: 'Create',
    description: 'Create a new role',
  },
  [ROUTES.ROLE_EDIT]: {
    title: 'Edit Role',
    breadcrumb: 'Edit',
    description: 'Edit role information',
  },
  [ROUTES.GROUPS]: {
    title: 'Group Management',
    breadcrumb: 'Groups',
    description: 'Manage user groups',
  },
  [ROUTES.GROUP_DETAIL]: {
    title: 'Group Details',
    breadcrumb: 'Group Details',
    description: 'View and edit group information',
  },
  [ROUTES.GROUP_CREATE]: {
    title: 'Create Group',
    breadcrumb: 'Create',
    description: 'Create a new group',
  },
  [ROUTES.GROUP_EDIT]: {
    title: 'Edit Group',
    breadcrumb: 'Edit',
    description: 'Edit group information',
  },
  [ROUTES.PERMISSIONS]: {
    title: 'Permission Management',
    breadcrumb: 'Permissions',
    description: 'Manage system permissions',
  },
  [ROUTES.PERMISSION_DETAIL]: {
    title: 'Permission Details',
    breadcrumb: 'Permission Details',
    description: 'View and edit permission information',
  },
  [ROUTES.PERMISSION_CREATE]: {
    title: 'Create Permission',
    breadcrumb: 'Create',
    description: 'Create a new permission',
  },
  [ROUTES.PERMISSION_EDIT]: {
    title: 'Edit Permission',
    breadcrumb: 'Edit',
    description: 'Edit permission information',
  },
  [ROUTES.WORKFLOWS]: {
    title: 'Workflow Management',
    breadcrumb: 'Workflows',
    description: 'Manage automated workflows',
  },
  [ROUTES.WORKFLOW_DESIGNER]: {
    title: 'Workflow Designer',
    breadcrumb: 'Designer',
    description: 'Create and edit workflows visually',
  },
  [ROUTES.WORKFLOW_DESIGNER_EDIT]: {
    title: 'Edit Workflow',
    breadcrumb: 'Edit Workflow',
    description: 'Edit workflow design',
  },
  [ROUTES.WORKFLOW_TEMPLATES]: {
    title: 'Workflow Templates',
    breadcrumb: 'Templates',
    description: 'Browse and manage workflow templates',
  },
  [ROUTES.WORKFLOW_HISTORY]: {
    title: 'Workflow History',
    breadcrumb: 'History',
    description: 'View workflow execution history',
  },
  [ROUTES.INHERITANCE]: {
    title: 'Permission Inheritance',
    breadcrumb: 'Inheritance',
    description: 'Analyze permission inheritance',
  },
  [ROUTES.SETTINGS]: {
    title: 'Settings',
    breadcrumb: 'Settings',
    description: 'System settings and configuration',
  },
  [ROUTES.PROFILE]: {
    title: 'Profile',
    breadcrumb: 'Profile',
    description: 'Your user profile',
  },
} as const;