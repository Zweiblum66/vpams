import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Group, GroupCreateRequest, GroupUpdateRequest, PaginatedResponse } from '../../types';
import { groupService } from '../../services/groupService';

interface GroupState {
  groups: Group[];
  currentGroup: Group | null;
  totalGroups: number;
  isLoading: boolean;
  error?: string;
  selectedGroups: string[];
  filters: {
    search: string;
    groupType: string;
    isActive: boolean | null;
    parentGroupId: string;
  };
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
  groupHierarchy: Group[];
  groupMembers: Record<string, any[]>;
}

const initialState: GroupState = {
  groups: [],
  currentGroup: null,
  totalGroups: 0,
  isLoading: false,
  error: undefined,
  selectedGroups: [],
  filters: {
    search: '',
    groupType: '',
    isActive: null,
    parentGroupId: '',
  },
  pagination: {
    page: 1,
    limit: 20,
    total: 0,
    pages: 0,
  },
  groupHierarchy: [],
  groupMembers: {},
};

// Async thunks
export const fetchGroups = createAsyncThunk(
  'groups/fetchGroups',
  async (params: {
    page?: number;
    limit?: number;
    search?: string;
    groupType?: string;
    isActive?: boolean;
    parentGroupId?: string;
  } = {}, { rejectWithValue }) => {
    try {
      const response = await groupService.getGroups(params);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch groups');
    }
  }
);

export const fetchGroup = createAsyncThunk(
  'groups/fetchGroup',
  async (groupId: string, { rejectWithValue }) => {
    try {
      const response = await groupService.getGroup(groupId);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch group');
    }
  }
);

export const createGroup = createAsyncThunk(
  'groups/createGroup',
  async (groupData: GroupCreateRequest, { rejectWithValue }) => {
    try {
      const response = await groupService.createGroup(groupData);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to create group');
    }
  }
);

export const updateGroup = createAsyncThunk(
  'groups/updateGroup',
  async ({ groupId, groupData }: { groupId: string; groupData: GroupUpdateRequest }, { rejectWithValue }) => {
    try {
      const response = await groupService.updateGroup(groupId, groupData);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to update group');
    }
  }
);

export const deleteGroup = createAsyncThunk(
  'groups/deleteGroup',
  async (groupId: string, { rejectWithValue }) => {
    try {
      await groupService.deleteGroup(groupId);
      return groupId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to delete group');
    }
  }
);

export const fetchGroupHierarchy = createAsyncThunk(
  'groups/fetchGroupHierarchy',
  async (_, { rejectWithValue }) => {
    try {
      const response = await groupService.getGroupHierarchy();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch group hierarchy');
    }
  }
);

export const fetchGroupMembers = createAsyncThunk(
  'groups/fetchGroupMembers',
  async (groupId: string, { rejectWithValue }) => {
    try {
      const response = await groupService.getGroupMembers(groupId);
      return { groupId, members: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch group members');
    }
  }
);

export const addUserToGroup = createAsyncThunk(
  'groups/addUserToGroup',
  async ({ groupId, userId }: { groupId: string; userId: string }, { rejectWithValue }) => {
    try {
      const response = await groupService.addUserToGroup(groupId, userId);
      return { groupId, userId, response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to add user to group');
    }
  }
);

export const removeUserFromGroup = createAsyncThunk(
  'groups/removeUserFromGroup',
  async ({ groupId, userId }: { groupId: string; userId: string }, { rejectWithValue }) => {
    try {
      await groupService.removeUserFromGroup(groupId, userId);
      return { groupId, userId };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to remove user from group');
    }
  }
);

export const assignRoleToGroup = createAsyncThunk(
  'groups/assignRoleToGroup',
  async ({ groupId, roleId }: { groupId: string; roleId: string }, { rejectWithValue }) => {
    try {
      const response = await groupService.assignRoleToGroup(groupId, roleId);
      return { groupId, roleId, response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to assign role to group');
    }
  }
);

export const revokeRoleFromGroup = createAsyncThunk(
  'groups/revokeRoleFromGroup',
  async ({ groupId, roleId }: { groupId: string; roleId: string }, { rejectWithValue }) => {
    try {
      await groupService.revokeRoleFromGroup(groupId, roleId);
      return { groupId, roleId };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to revoke role from group');
    }
  }
);

export const bulkAddUsersToGroup = createAsyncThunk(
  'groups/bulkAddUsersToGroup',
  async ({ groupId, userIds }: { groupId: string; userIds: string[] }, { rejectWithValue }) => {
    try {
      const response = await groupService.bulkAddUsersToGroup(groupId, userIds);
      return { groupId, userIds, response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to add users to group');
    }
  }
);

export const bulkRemoveUsersFromGroup = createAsyncThunk(
  'groups/bulkRemoveUsersFromGroup',
  async ({ groupId, userIds }: { groupId: string; userIds: string[] }, { rejectWithValue }) => {
    try {
      await groupService.bulkRemoveUsersFromGroup(groupId, userIds);
      return { groupId, userIds };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to remove users from group');
    }
  }
);

const groupSlice = createSlice({
  name: 'groups',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = undefined;
    },
    setSelectedGroups: (state, action: PayloadAction<string[]>) => {
      state.selectedGroups = action.payload;
    },
    addSelectedGroup: (state, action: PayloadAction<string>) => {
      if (!state.selectedGroups.includes(action.payload)) {
        state.selectedGroups.push(action.payload);
      }
    },
    removeSelectedGroup: (state, action: PayloadAction<string>) => {
      state.selectedGroups = state.selectedGroups.filter(id => id !== action.payload);
    },
    clearSelectedGroups: (state) => {
      state.selectedGroups = [];
    },
    setFilters: (state, action: PayloadAction<Partial<GroupState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = initialState.filters;
    },
    setPagination: (state, action: PayloadAction<Partial<GroupState['pagination']>>) => {
      state.pagination = { ...state.pagination, ...action.payload };
    },
    clearGroupMembers: (state, action: PayloadAction<string>) => {
      delete state.groupMembers[action.payload];
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch groups
      .addCase(fetchGroups.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(fetchGroups.fulfilled, (state, action) => {
        state.isLoading = false;
        state.groups = action.payload.data;
        state.pagination = action.payload.meta;
        state.totalGroups = action.payload.meta.total;
        state.error = undefined;
      })
      .addCase(fetchGroups.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Fetch group
      .addCase(fetchGroup.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(fetchGroup.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentGroup = action.payload;
        state.error = undefined;
      })
      .addCase(fetchGroup.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Create group
      .addCase(createGroup.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(createGroup.fulfilled, (state, action) => {
        state.isLoading = false;
        state.groups.unshift(action.payload);
        state.totalGroups += 1;
        state.error = undefined;
      })
      .addCase(createGroup.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Update group
      .addCase(updateGroup.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(updateGroup.fulfilled, (state, action) => {
        state.isLoading = false;
        const index = state.groups.findIndex(group => group.group_id === action.payload.group_id);
        if (index !== -1) {
          state.groups[index] = action.payload;
        }
        if (state.currentGroup?.group_id === action.payload.group_id) {
          state.currentGroup = action.payload;
        }
        state.error = undefined;
      })
      .addCase(updateGroup.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Delete group
      .addCase(deleteGroup.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(deleteGroup.fulfilled, (state, action) => {
        state.isLoading = false;
        state.groups = state.groups.filter(group => group.group_id !== action.payload);
        state.selectedGroups = state.selectedGroups.filter(id => id !== action.payload);
        state.totalGroups -= 1;
        // Remove from hierarchy
        state.groupHierarchy = state.groupHierarchy.filter(group => group.group_id !== action.payload);
        state.error = undefined;
      })
      .addCase(deleteGroup.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Fetch group hierarchy
      .addCase(fetchGroupHierarchy.fulfilled, (state, action) => {
        state.groupHierarchy = action.payload;
      })
      // Fetch group members
      .addCase(fetchGroupMembers.fulfilled, (state, action) => {
        state.groupMembers[action.payload.groupId] = action.payload.members;
      })
      // Add user to group
      .addCase(addUserToGroup.fulfilled, (state, action) => {
        const { groupId, userId, response } = action.payload;
        if (state.groupMembers[groupId]) {
          state.groupMembers[groupId].push(response);
        }
        // Update member count
        const groupIndex = state.groups.findIndex(g => g.group_id === groupId);
        if (groupIndex !== -1 && state.groups[groupIndex].member_count !== undefined) {
          state.groups[groupIndex].member_count! += 1;
        }
      })
      // Remove user from group
      .addCase(removeUserFromGroup.fulfilled, (state, action) => {
        const { groupId, userId } = action.payload;
        if (state.groupMembers[groupId]) {
          state.groupMembers[groupId] = state.groupMembers[groupId].filter((member: any) => member.user_id !== userId);
        }
        // Update member count
        const groupIndex = state.groups.findIndex(g => g.group_id === groupId);
        if (groupIndex !== -1 && state.groups[groupIndex].member_count !== undefined) {
          state.groups[groupIndex].member_count! -= 1;
        }
      })
      // Bulk add users to group
      .addCase(bulkAddUsersToGroup.fulfilled, (state, action) => {
        const { groupId, userIds, response } = action.payload;
        if (state.groupMembers[groupId]) {
          state.groupMembers[groupId].push(...response);
        }
        // Update member count
        const groupIndex = state.groups.findIndex(g => g.group_id === groupId);
        if (groupIndex !== -1 && state.groups[groupIndex].member_count !== undefined) {
          state.groups[groupIndex].member_count! += userIds.length;
        }
      })
      // Bulk remove users from group
      .addCase(bulkRemoveUsersFromGroup.fulfilled, (state, action) => {
        const { groupId, userIds } = action.payload;
        if (state.groupMembers[groupId]) {
          state.groupMembers[groupId] = state.groupMembers[groupId].filter((member: any) => !userIds.includes(member.user_id));
        }
        // Update member count
        const groupIndex = state.groups.findIndex(g => g.group_id === groupId);
        if (groupIndex !== -1 && state.groups[groupIndex].member_count !== undefined) {
          state.groups[groupIndex].member_count! -= userIds.length;
        }
      });
  },
});

export const {
  clearError,
  setSelectedGroups,
  addSelectedGroup,
  removeSelectedGroup,
  clearSelectedGroups,
  setFilters,
  clearFilters,
  setPagination,
  clearGroupMembers,
} = groupSlice.actions;

export default groupSlice.reducer;