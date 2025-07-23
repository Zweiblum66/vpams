import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Role, RoleCreateRequest, RoleUpdateRequest, PaginatedResponse } from '../../types';
import { roleService } from '../../services/roleService';

interface RoleState {
  roles: Role[];
  currentRole: Role | null;
  totalRoles: number;
  isLoading: boolean;
  error?: string;
  selectedRoles: string[];
  filters: {
    search: string;
    roleType: string;
    isActive: boolean | null;
  };
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

const initialState: RoleState = {
  roles: [],
  currentRole: null,
  totalRoles: 0,
  isLoading: false,
  error: undefined,
  selectedRoles: [],
  filters: {
    search: '',
    roleType: '',
    isActive: null,
  },
  pagination: {
    page: 1,
    limit: 20,
    total: 0,
    pages: 0,
  },
};

// Async thunks
export const fetchRoles = createAsyncThunk(
  'roles/fetchRoles',
  async (params: {
    page?: number;
    limit?: number;
    search?: string;
    roleType?: string;
    isActive?: boolean;
  } = {}, { rejectWithValue }) => {
    try {
      const response = await roleService.getRoles(params);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch roles');
    }
  }
);

export const fetchRole = createAsyncThunk(
  'roles/fetchRole',
  async (roleId: string, { rejectWithValue }) => {
    try {
      const response = await roleService.getRole(roleId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch role');
    }
  }
);

export const createRole = createAsyncThunk(
  'roles/createRole',
  async (roleData: RoleCreateRequest, { rejectWithValue }) => {
    try {
      const response = await roleService.createRole(roleData);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to create role');
    }
  }
);

export const updateRole = createAsyncThunk(
  'roles/updateRole',
  async ({ roleId, roleData }: { roleId: string; roleData: RoleUpdateRequest }, { rejectWithValue }) => {
    try {
      const response = await roleService.updateRole(roleId, roleData);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to update role');
    }
  }
);

export const deleteRole = createAsyncThunk(
  'roles/deleteRole',
  async (roleId: string, { rejectWithValue }) => {
    try {
      await roleService.deleteRole(roleId);
      return roleId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to delete role');
    }
  }
);

export const assignPermissionToRole = createAsyncThunk(
  'roles/assignPermissionToRole',
  async ({ roleId, permissionId }: { roleId: string; permissionId: string }, { rejectWithValue }) => {
    try {
      const response = await roleService.assignPermission(roleId, permissionId);
      return { roleId, permissionId, response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to assign permission');
    }
  }
);

export const revokePermissionFromRole = createAsyncThunk(
  'roles/revokePermissionFromRole',
  async ({ roleId, permissionId }: { roleId: string; permissionId: string }, { rejectWithValue }) => {
    try {
      await roleService.revokePermission(roleId, permissionId);
      return { roleId, permissionId };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to revoke permission');
    }
  }
);

export const getRolePermissions = createAsyncThunk(
  'roles/getRolePermissions',
  async (roleId: string, { rejectWithValue }) => {
    try {
      const response = await roleService.getRolePermissions(roleId);
      return { roleId, permissions: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch role permissions');
    }
  }
);

export const getRoleHierarchy = createAsyncThunk(
  'roles/getRoleHierarchy',
  async (_, { rejectWithValue }) => {
    try {
      const response = await roleService.getRoleHierarchy();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch role hierarchy');
    }
  }
);

const roleSlice = createSlice({
  name: 'roles',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = undefined;
    },
    setSelectedRoles: (state, action: PayloadAction<string[]>) => {
      state.selectedRoles = action.payload;
    },
    addSelectedRole: (state, action: PayloadAction<string>) => {
      if (!state.selectedRoles.includes(action.payload)) {
        state.selectedRoles.push(action.payload);
      }
    },
    removeSelectedRole: (state, action: PayloadAction<string>) => {
      state.selectedRoles = state.selectedRoles.filter(id => id !== action.payload);
    },
    clearSelectedRoles: (state) => {
      state.selectedRoles = [];
    },
    setFilters: (state, action: PayloadAction<Partial<RoleState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = initialState.filters;
    },
    setPagination: (state, action: PayloadAction<Partial<RoleState['pagination']>>) => {
      state.pagination = { ...state.pagination, ...action.payload };
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch roles
      .addCase(fetchRoles.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(fetchRoles.fulfilled, (state, action) => {
        state.isLoading = false;
        state.roles = action.payload.data;
        state.pagination = action.payload.meta;
        state.totalRoles = action.payload.meta.total;
        state.error = undefined;
      })
      .addCase(fetchRoles.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Fetch role
      .addCase(fetchRole.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(fetchRole.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentRole = action.payload;
        state.error = undefined;
      })
      .addCase(fetchRole.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Create role
      .addCase(createRole.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(createRole.fulfilled, (state, action) => {
        state.isLoading = false;
        state.roles.unshift(action.payload);
        state.totalRoles += 1;
        state.error = undefined;
      })
      .addCase(createRole.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Update role
      .addCase(updateRole.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(updateRole.fulfilled, (state, action) => {
        state.isLoading = false;
        const index = state.roles.findIndex(role => role.role_id === action.payload.role_id);
        if (index !== -1) {
          state.roles[index] = action.payload;
        }
        if (state.currentRole?.role_id === action.payload.role_id) {
          state.currentRole = action.payload;
        }
        state.error = undefined;
      })
      .addCase(updateRole.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Delete role
      .addCase(deleteRole.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(deleteRole.fulfilled, (state, action) => {
        state.isLoading = false;
        state.roles = state.roles.filter(role => role.role_id !== action.payload);
        state.selectedRoles = state.selectedRoles.filter(id => id !== action.payload);
        state.totalRoles -= 1;
        state.error = undefined;
      })
      .addCase(deleteRole.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Assign permission to role
      .addCase(assignPermissionToRole.fulfilled, (state, action) => {
        // Permission assignment handled by separate permissions state
        state.error = undefined;
      })
      .addCase(assignPermissionToRole.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Revoke permission from role
      .addCase(revokePermissionFromRole.fulfilled, (state, action) => {
        // Permission revocation handled by separate permissions state
        state.error = undefined;
      })
      .addCase(revokePermissionFromRole.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const {
  clearError,
  setSelectedRoles,
  addSelectedRole,
  removeSelectedRole,
  clearSelectedRoles,
  setFilters,
  clearFilters,
  setPagination,
} = roleSlice.actions;

export default roleSlice.reducer;