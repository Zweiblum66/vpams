import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Notification, ThemeState, TableState } from '../../types';

interface UIState {
  theme: ThemeState;
  notifications: Notification[];
  loading: {
    global: boolean;
    components: Record<string, boolean>;
  };
  modals: {
    createUser: boolean;
    editUser: boolean;
    deleteUser: boolean;
    createRole: boolean;
    editRole: boolean;
    deleteRole: boolean;
    createGroup: boolean;
    editGroup: boolean;
    deleteGroup: boolean;
    createPermission: boolean;
    editPermission: boolean;
    deletePermission: boolean;
    assignPermissions: boolean;
    manageGroupMembers: boolean;
    inheritanceAnalysis: boolean;
    permissionTrace: boolean;
    bulkActions: boolean;
    importUsers: boolean;
    exportData: boolean;
  };
  selectedItems: {
    users: string[];
    roles: string[];
    groups: string[];
    permissions: string[];
  };
  tableStates: Record<string, TableState>;
  breadcrumbs: Array<{
    label: string;
    path: string;
    icon?: string;
  }>;
  activeTab: string;
  expandedItems: Record<string, boolean>;
  preferences: {
    itemsPerPage: number;
    defaultView: 'table' | 'card' | 'hierarchy';
    enableTooltips: boolean;
    enableAnimations: boolean;
    autoRefreshInterval: number;
    compactMode: boolean;
  };
}

const initialState: UIState = {
  theme: {
    mode: 'light',
    primaryColor: '#1976d2',
    sidebarOpen: true,
  },
  notifications: [],
  loading: {
    global: false,
    components: {},
  },
  modals: {
    createUser: false,
    editUser: false,
    deleteUser: false,
    createRole: false,
    editRole: false,
    deleteRole: false,
    createGroup: false,
    editGroup: false,
    deleteGroup: false,
    createPermission: false,
    editPermission: false,
    deletePermission: false,
    assignPermissions: false,
    manageGroupMembers: false,
    inheritanceAnalysis: false,
    permissionTrace: false,
    bulkActions: false,
    importUsers: false,
    exportData: false,
  },
  selectedItems: {
    users: [],
    roles: [],
    groups: [],
    permissions: [],
  },
  tableStates: {},
  breadcrumbs: [],
  activeTab: 'users',
  expandedItems: {},
  preferences: {
    itemsPerPage: 20,
    defaultView: 'table',
    enableTooltips: true,
    enableAnimations: true,
    autoRefreshInterval: 30000,
    compactMode: false,
  },
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    // Theme actions
    setThemeMode: (state, action: PayloadAction<'light' | 'dark'>) => {
      state.theme.mode = action.payload;
      localStorage.setItem('theme_mode', action.payload);
    },
    setPrimaryColor: (state, action: PayloadAction<string>) => {
      state.theme.primaryColor = action.payload;
      localStorage.setItem('primary_color', action.payload);
    },
    toggleSidebar: (state) => {
      state.theme.sidebarOpen = !state.theme.sidebarOpen;
      localStorage.setItem('sidebar_open', String(state.theme.sidebarOpen));
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.theme.sidebarOpen = action.payload;
      localStorage.setItem('sidebar_open', String(action.payload));
    },

    // Notification actions
    addNotification: (state, action: PayloadAction<Omit<Notification, 'id'>>) => {
      const notification: Notification = {
        id: Date.now().toString(),
        duration: 5000,
        ...action.payload,
      };
      state.notifications.push(notification);
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(n => n.id !== action.payload);
    },
    clearNotifications: (state) => {
      state.notifications = [];
    },

    // Loading actions
    setGlobalLoading: (state, action: PayloadAction<boolean>) => {
      state.loading.global = action.payload;
    },
    setComponentLoading: (state, action: PayloadAction<{ component: string; loading: boolean }>) => {
      state.loading.components[action.payload.component] = action.payload.loading;
    },
    clearComponentLoading: (state, action: PayloadAction<string>) => {
      delete state.loading.components[action.payload];
    },

    // Modal actions
    openModal: (state, action: PayloadAction<keyof UIState['modals']>) => {
      state.modals[action.payload] = true;
    },
    closeModal: (state, action: PayloadAction<keyof UIState['modals']>) => {
      state.modals[action.payload] = false;
    },
    closeAllModals: (state) => {
      Object.keys(state.modals).forEach(key => {
        state.modals[key as keyof UIState['modals']] = false;
      });
    },

    // Selection actions
    setSelectedItems: (state, action: PayloadAction<{ type: keyof UIState['selectedItems']; items: string[] }>) => {
      state.selectedItems[action.payload.type] = action.payload.items;
    },
    addSelectedItem: (state, action: PayloadAction<{ type: keyof UIState['selectedItems']; item: string }>) => {
      const { type, item } = action.payload;
      if (!state.selectedItems[type].includes(item)) {
        state.selectedItems[type].push(item);
      }
    },
    removeSelectedItem: (state, action: PayloadAction<{ type: keyof UIState['selectedItems']; item: string }>) => {
      const { type, item } = action.payload;
      state.selectedItems[type] = state.selectedItems[type].filter(i => i !== item);
    },
    clearSelectedItems: (state, action: PayloadAction<keyof UIState['selectedItems']>) => {
      state.selectedItems[action.payload] = [];
    },
    clearAllSelectedItems: (state) => {
      state.selectedItems = {
        users: [],
        roles: [],
        groups: [],
        permissions: [],
      };
    },

    // Table state actions
    setTableState: (state, action: PayloadAction<{ tableId: string; tableState: TableState }>) => {
      state.tableStates[action.payload.tableId] = action.payload.tableState;
    },
    updateTableState: (state, action: PayloadAction<{ tableId: string; updates: Partial<TableState> }>) => {
      const { tableId, updates } = action.payload;
      if (state.tableStates[tableId]) {
        state.tableStates[tableId] = { ...state.tableStates[tableId], ...updates };
      } else {
        state.tableStates[tableId] = {
          page: 1,
          pageSize: 20,
          sortModel: [],
          filterModel: {},
          ...updates,
        };
      }
    },
    resetTableState: (state, action: PayloadAction<string>) => {
      delete state.tableStates[action.payload];
    },

    // Breadcrumb actions
    setBreadcrumbs: (state, action: PayloadAction<UIState['breadcrumbs']>) => {
      state.breadcrumbs = action.payload;
    },
    addBreadcrumb: (state, action: PayloadAction<{ label: string; path: string; icon?: string }>) => {
      state.breadcrumbs.push(action.payload);
    },
    removeBreadcrumb: (state, action: PayloadAction<number>) => {
      state.breadcrumbs = state.breadcrumbs.slice(0, action.payload);
    },
    clearBreadcrumbs: (state) => {
      state.breadcrumbs = [];
    },

    // Tab actions
    setActiveTab: (state, action: PayloadAction<string>) => {
      state.activeTab = action.payload;
    },

    // Expanded items actions
    setExpandedItem: (state, action: PayloadAction<{ key: string; expanded: boolean }>) => {
      state.expandedItems[action.payload.key] = action.payload.expanded;
    },
    toggleExpandedItem: (state, action: PayloadAction<string>) => {
      state.expandedItems[action.payload] = !state.expandedItems[action.payload];
    },
    clearExpandedItems: (state) => {
      state.expandedItems = {};
    },

    // Preferences actions
    setPreferences: (state, action: PayloadAction<Partial<UIState['preferences']>>) => {
      state.preferences = { ...state.preferences, ...action.payload };
      localStorage.setItem('ui_preferences', JSON.stringify(state.preferences));
    },
    resetPreferences: (state) => {
      state.preferences = initialState.preferences;
      localStorage.removeItem('ui_preferences');
    },

    // Utility actions
    resetUIState: (state) => {
      return { ...initialState, theme: state.theme, preferences: state.preferences };
    },
  },
});

export const {
  // Theme actions
  setThemeMode,
  setPrimaryColor,
  toggleSidebar,
  setSidebarOpen,
  
  // Notification actions
  addNotification,
  removeNotification,
  clearNotifications,
  
  // Loading actions
  setGlobalLoading,
  setComponentLoading,
  clearComponentLoading,
  
  // Modal actions
  openModal,
  closeModal,
  closeAllModals,
  
  // Selection actions
  setSelectedItems,
  addSelectedItem,
  removeSelectedItem,
  clearSelectedItems,
  clearAllSelectedItems,
  
  // Table state actions
  setTableState,
  updateTableState,
  resetTableState,
  
  // Breadcrumb actions
  setBreadcrumbs,
  addBreadcrumb,
  removeBreadcrumb,
  clearBreadcrumbs,
  
  // Tab actions
  setActiveTab,
  
  // Expanded items actions
  setExpandedItem,
  toggleExpandedItem,
  clearExpandedItems,
  
  // Preferences actions
  setPreferences,
  resetPreferences,
  
  // Utility actions
  resetUIState,
} = uiSlice.actions;

export default uiSlice.reducer;

// Initialize theme and preferences from localStorage
export const initializeUIFromStorage = () => {
  const savedThemeMode = localStorage.getItem('theme_mode') as 'light' | 'dark' | null;
  const savedPrimaryColor = localStorage.getItem('primary_color');
  const savedSidebarOpen = localStorage.getItem('sidebar_open');
  const savedPreferences = localStorage.getItem('ui_preferences');

  return {
    theme: {
      mode: savedThemeMode || initialState.theme.mode,
      primaryColor: savedPrimaryColor || initialState.theme.primaryColor,
      sidebarOpen: savedSidebarOpen ? JSON.parse(savedSidebarOpen) : initialState.theme.sidebarOpen,
    },
    preferences: savedPreferences ? JSON.parse(savedPreferences) : initialState.preferences,
  };
};