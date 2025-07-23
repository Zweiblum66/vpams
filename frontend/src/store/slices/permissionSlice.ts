import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Permission, PermissionCreateRequest, PermissionUpdateRequest, PaginatedResponse } from '../../types';
import { permissionService } from '../../services/permissionService';

interface PermissionState {
  permissions: Permission[];
  currentPermission: Permission | null;
  totalPermissions: number;
  isLoading: boolean;
  error?: string;
  selectedPermissions: string[];
  filters: {
    search: string;
    resource: string;
    action: string;
    category: string;
    scope: string;
  };
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
  rolePermissions: Record<string, Permission[]>;
  userPermissions: Record<string, Permission[]>;
  groupPermissions: Record<string, Permission[]>;
}

const initialState: PermissionState = {
  permissions: [],
  currentPermission: null,
  totalPermissions: 0,
  isLoading: false,
  error: undefined,
  selectedPermissions: [],
  filters: {
    search: '',
    resource: '',
    action: '',
    category: '',
    scope: '',
  },
  pagination: {
    page: 1,
    limit: 20,
    total: 0,
    pages: 0,
  },
  rolePermissions: {},
  userPermissions: {},
  groupPermissions: {},
};

// Async thunks
export const fetchPermissions = createAsyncThunk(
  'permissions/fetchPermissions',
  async (params: {
    page?: number;
    limit?: number;
    search?: string;
    resource?: string;
    action?: string;
    category?: string;
    scope?: string;
  } = {}, { rejectWithValue }) => {
    try {
      const response = await permissionService.getPermissions(params);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch permissions');
    }
  }
);

export const fetchPermission = createAsyncThunk(
  'permissions/fetchPermission',
  async (permissionId: string, { rejectWithValue }) => {
    try {
      const response = await permissionService.getPermission(permissionId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch permission');
    }
  }
);

export const createPermission = createAsyncThunk(
  'permissions/createPermission',
  async (permissionData: PermissionCreateRequest, { rejectWithValue }) => {
    try {
      const response = await permissionService.createPermission(permissionData);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to create permission');
    }
  }
);

export const updatePermission = createAsyncThunk(
  'permissions/updatePermission',
  async ({ permissionId, permissionData }: { permissionId: string; permissionData: PermissionUpdateRequest }, { rejectWithValue }) => {
    try {
      const response = await permissionService.updatePermission(permissionId, permissionData);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to update permission');
    }
  }
);

export const deletePermission = createAsyncThunk(
  'permissions/deletePermission',
  async (permissionId: string, { rejectWithValue }) => {
    try {
      await permissionService.deletePermission(permissionId);
      return permissionId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to delete permission');
    }
  }
);

export const fetchUserPermissions = createAsyncThunk(
  'permissions/fetchUserPermissions',
  async (userId: string, { rejectWithValue }) => {
    try {
      const response = await permissionService.getUserPermissions(userId);
      return { userId, permissions: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch user permissions');
    }
  }
);

export const fetchRolePermissions = createAsyncThunk(
  'permissions/fetchRolePermissions',
  async (roleId: string, { rejectWithValue }) => {
    try {
      const response = await permissionService.getRolePermissions(roleId);
      return { roleId, permissions: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch role permissions');
    }
  }
);

export const fetchGroupPermissions = createAsyncThunk(
  'permissions/fetchGroupPermissions',
  async (groupId: string, { rejectWithValue }) => {
    try {
      const response = await permissionService.getGroupPermissions(groupId);
      return { groupId, permissions: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch group permissions');
    }
  }
);

export const assignPermissionToUser = createAsyncThunk(
  'permissions/assignPermissionToUser',
  async ({ userId, permissionId }: { userId: string; permissionId: string }, { rejectWithValue }) => {
    try {
      const response = await permissionService.assignPermissionToUser(userId, permissionId);
      return { userId, permissionId, response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to assign permission to user');
    }
  }
);

export const revokePermissionFromUser = createAsyncThunk(
  'permissions/revokePermissionFromUser',
  async ({ userId, permissionId }: { userId: string; permissionId: string }, { rejectWithValue }) => {
    try {
      await permissionService.revokePermissionFromUser(userId, permissionId);
      return { userId, permissionId };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to revoke permission from user');
    }
  }
);

export const getPermissionCategories = createAsyncThunk(
  'permissions/getPermissionCategories',
  async (_, { rejectWithValue }) => {
    try {
      const response = await permissionService.getPermissionCategories();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch permission categories');
    }
  }
);

export const getPermissionResources = createAsyncThunk(
  'permissions/getPermissionResources',
  async (_, { rejectWithValue }) => {
    try {
      const response = await permissionService.getPermissionResources();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch permission resources');
    }
  }
);

const permissionSlice = createSlice({
  name: 'permissions',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = undefined;
    },
    setSelectedPermissions: (state, action: PayloadAction<string[]>) => {
      state.selectedPermissions = action.payload;
    },
    addSelectedPermission: (state, action: PayloadAction<string>) => {
      if (!state.selectedPermissions.includes(action.payload)) {
        state.selectedPermissions.push(action.payload);
      }
    },
    removeSelectedPermission: (state, action: PayloadAction<string>) => {
      state.selectedPermissions = state.selectedPermissions.filter(id => id !== action.payload);
    },
    clearSelectedPermissions: (state) => {
      state.selectedPermissions = [];
    },
    setFilters: (state, action: PayloadAction<Partial<PermissionState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = initialState.filters;
    },
    setPagination: (state, action: PayloadAction<Partial<PermissionState['pagination']>>) => {
      state.pagination = { ...state.pagination, ...action.payload };
    },
    clearRolePermissions: (state, action: PayloadAction<string>) => {
      delete state.rolePermissions[action.payload];
    },
    clearUserPermissions: (state, action: PayloadAction<string>) => {
      delete state.userPermissions[action.payload];
    },
    clearGroupPermissions: (state, action: PayloadAction<string>) => {
      delete state.groupPermissions[action.payload];
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch permissions
      .addCase(fetchPermissions.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(fetchPermissions.fulfilled, (state, action) => {
        state.isLoading = false;
        state.permissions = action.payload.data;
        state.pagination = action.payload.meta;
        state.totalPermissions = action.payload.meta.total;
        state.error = undefined;
      })
      .addCase(fetchPermissions.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Fetch permission
      .addCase(fetchPermission.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(fetchPermission.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentPermission = action.payload;
        state.error = undefined;
      })
      .addCase(fetchPermission.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Create permission
      .addCase(createPermission.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(createPermission.fulfilled, (state, action) => {
        state.isLoading = false;
        state.permissions.unshift(action.payload);
        state.totalPermissions += 1;
        state.error = undefined;
      })
      .addCase(createPermission.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Update permission
      .addCase(updatePermission.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(updatePermission.fulfilled, (state, action) => {
        state.isLoading = false;
        const index = state.permissions.findIndex(permission => permission.permission_id === action.payload.permission_id);
        if (index !== -1) {
          state.permissions[index] = action.payload;
        }
        if (state.currentPermission?.permission_id === action.payload.permission_id) {
          state.currentPermission = action.payload;
        }
        state.error = undefined;
      })
      .addCase(updatePermission.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Delete permission
      .addCase(deletePermission.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(deletePermission.fulfilled, (state, action) => {
        state.isLoading = false;
        state.permissions = state.permissions.filter(permission => permission.permission_id !== action.payload);
        state.selectedPermissions = state.selectedPermissions.filter(id => id !== action.payload);
        state.totalPermissions -= 1;
        state.error = undefined;
      })
      .addCase(deletePermission.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Fetch user permissions
      .addCase(fetchUserPermissions.fulfilled, (state, action) => {
        state.userPermissions[action.payload.userId] = action.payload.permissions;
      })
      // Fetch role permissions
      .addCase(fetchRolePermissions.fulfilled, (state, action) => {
        state.rolePermissions[action.payload.roleId] = action.payload.permissions;
      })
      // Fetch group permissions
      .addCase(fetchGroupPermissions.fulfilled, (state, action) => {
        state.groupPermissions[action.payload.groupId] = action.payload.permissions;
      })
      // Assign permission to user
      .addCase(assignPermissionToUser.fulfilled, (state, action) => {
        const { userId, permissionId } = action.payload;
        if (state.userPermissions[userId]) {
          const permission = state.permissions.find(p => p.permission_id === permissionId);
          if (permission && !state.userPermissions[userId].some(p => p.permission_id === permissionId)) {
            state.userPermissions[userId].push(permission);
          }
        }
      })
      // Revoke permission from user
      .addCase(revokePermissionFromUser.fulfilled, (state, action) => {
        const { userId, permissionId } = action.payload;
        if (state.userPermissions[userId]) {
          state.userPermissions[userId] = state.userPermissions[userId].filter(p => p.permission_id !== permissionId);
        }
      });
  },
});

export const {
  clearError,
  setSelectedPermissions,
  addSelectedPermission,
  removeSelectedPermission,
  clearSelectedPermissions,
  setFilters,
  clearFilters,
  setPagination,
  clearRolePermissions,
  clearUserPermissions,
  clearGroupPermissions,
} = permissionSlice.actions;

export default permissionSlice.reducer;