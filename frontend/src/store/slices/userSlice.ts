import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { User, UserCreateRequest, UserUpdateRequest, PaginatedResponse } from '../../types';
import { userService } from '../../services/userService';

interface UserState {
  users: User[];
  currentUser: User | null;
  totalUsers: number;
  isLoading: boolean;
  error?: string;
  selectedUsers: string[];
  filters: {
    search: string;
    isActive: boolean | null;
    department: string;
    role: string;
  };
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

const initialState: UserState = {
  users: [],
  currentUser: null,
  totalUsers: 0,
  isLoading: false,
  error: undefined,
  selectedUsers: [],
  filters: {
    search: '',
    isActive: null,
    department: '',
    role: '',
  },
  pagination: {
    page: 1,
    limit: 20,
    total: 0,
    pages: 0,
  },
};

// Async thunks
export const fetchUsers = createAsyncThunk(
  'users/fetchUsers',
  async (params: {
    page?: number;
    limit?: number;
    search?: string;
    isActive?: boolean;
    department?: string;
    role?: string;
  } = {}, { rejectWithValue }) => {
    try {
      const response = await userService.getUsers(params);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch users');
    }
  }
);

export const fetchUser = createAsyncThunk(
  'users/fetchUser',
  async (userId: string, { rejectWithValue }) => {
    try {
      const response = await userService.getUser(userId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch user');
    }
  }
);

export const createUser = createAsyncThunk(
  'users/createUser',
  async (userData: UserCreateRequest, { rejectWithValue }) => {
    try {
      const response = await userService.createUser(userData);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to create user');
    }
  }
);

export const updateUser = createAsyncThunk(
  'users/updateUser',
  async ({ userId, userData }: { userId: string; userData: UserUpdateRequest }, { rejectWithValue }) => {
    try {
      const response = await userService.updateUser(userId, userData);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to update user');
    }
  }
);

export const deleteUser = createAsyncThunk(
  'users/deleteUser',
  async (userId: string, { rejectWithValue }) => {
    try {
      await userService.deleteUser(userId);
      return userId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to delete user');
    }
  }
);

export const bulkDeleteUsers = createAsyncThunk(
  'users/bulkDeleteUsers',
  async (userIds: string[], { rejectWithValue }) => {
    try {
      await userService.bulkDeleteUsers(userIds);
      return userIds;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to delete users');
    }
  }
);

export const activateUser = createAsyncThunk(
  'users/activateUser',
  async (userId: string, { rejectWithValue }) => {
    try {
      const response = await userService.activateUser(userId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to activate user');
    }
  }
);

export const deactivateUser = createAsyncThunk(
  'users/deactivateUser',
  async (userId: string, { rejectWithValue }) => {
    try {
      const response = await userService.deactivateUser(userId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to deactivate user');
    }
  }
);

const userSlice = createSlice({
  name: 'users',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = undefined;
    },
    setSelectedUsers: (state, action: PayloadAction<string[]>) => {
      state.selectedUsers = action.payload;
    },
    addSelectedUser: (state, action: PayloadAction<string>) => {
      if (!state.selectedUsers.includes(action.payload)) {
        state.selectedUsers.push(action.payload);
      }
    },
    removeSelectedUser: (state, action: PayloadAction<string>) => {
      state.selectedUsers = state.selectedUsers.filter(id => id !== action.payload);
    },
    clearSelectedUsers: (state) => {
      state.selectedUsers = [];
    },
    setFilters: (state, action: PayloadAction<Partial<UserState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = initialState.filters;
    },
    setPagination: (state, action: PayloadAction<Partial<UserState['pagination']>>) => {
      state.pagination = { ...state.pagination, ...action.payload };
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch users
      .addCase(fetchUsers.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(fetchUsers.fulfilled, (state, action) => {
        state.isLoading = false;
        state.users = action.payload.data;
        state.pagination = action.payload.meta;
        state.totalUsers = action.payload.meta.total;
        state.error = undefined;
      })
      .addCase(fetchUsers.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Fetch user
      .addCase(fetchUser.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(fetchUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentUser = action.payload;
        state.error = undefined;
      })
      .addCase(fetchUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Create user
      .addCase(createUser.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(createUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.users.unshift(action.payload);
        state.totalUsers += 1;
        state.error = undefined;
      })
      .addCase(createUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Update user
      .addCase(updateUser.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(updateUser.fulfilled, (state, action) => {
        state.isLoading = false;
        const index = state.users.findIndex(user => user.user_id === action.payload.user_id);
        if (index !== -1) {
          state.users[index] = action.payload;
        }
        if (state.currentUser?.user_id === action.payload.user_id) {
          state.currentUser = action.payload;
        }
        state.error = undefined;
      })
      .addCase(updateUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Delete user
      .addCase(deleteUser.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(deleteUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.users = state.users.filter(user => user.user_id !== action.payload);
        state.selectedUsers = state.selectedUsers.filter(id => id !== action.payload);
        state.totalUsers -= 1;
        state.error = undefined;
      })
      .addCase(deleteUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Bulk delete users
      .addCase(bulkDeleteUsers.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(bulkDeleteUsers.fulfilled, (state, action) => {
        state.isLoading = false;
        state.users = state.users.filter(user => !action.payload.includes(user.user_id));
        state.selectedUsers = [];
        state.totalUsers -= action.payload.length;
        state.error = undefined;
      })
      .addCase(bulkDeleteUsers.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Activate user
      .addCase(activateUser.fulfilled, (state, action) => {
        const index = state.users.findIndex(user => user.user_id === action.payload.user_id);
        if (index !== -1) {
          state.users[index] = action.payload;
        }
        if (state.currentUser?.user_id === action.payload.user_id) {
          state.currentUser = action.payload;
        }
      })
      // Deactivate user
      .addCase(deactivateUser.fulfilled, (state, action) => {
        const index = state.users.findIndex(user => user.user_id === action.payload.user_id);
        if (index !== -1) {
          state.users[index] = action.payload;
        }
        if (state.currentUser?.user_id === action.payload.user_id) {
          state.currentUser = action.payload;
        }
      });
  },
});

export const {
  clearError,
  setSelectedUsers,
  addSelectedUser,
  removeSelectedUser,
  clearSelectedUsers,
  setFilters,
  clearFilters,
  setPagination,
} = userSlice.actions;

export default userSlice.reducer;