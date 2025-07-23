import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { PermissionSource, InheritanceStatistics } from '../../types';
import { inheritanceService } from '../../services/inheritanceService';

interface InheritanceState {
  userEffectivePermissions: Record<string, {
    permissions: Record<string, PermissionSource[]>;
    statistics: InheritanceStatistics;
  }>;
  roleHierarchy: any[];
  groupHierarchy: any[];
  inheritanceConflicts: any[];
  isLoading: boolean;
  error?: string;
  analysisResults: Record<string, any>;
}

const initialState: InheritanceState = {
  userEffectivePermissions: {},
  roleHierarchy: [],
  groupHierarchy: [],
  inheritanceConflicts: [],
  isLoading: false,
  error: undefined,
  analysisResults: {},
};

// Async thunks
export const fetchUserEffectivePermissions = createAsyncThunk(
  'inheritance/fetchUserEffectivePermissions',
  async (params: { userId: string; includeSources?: boolean }, { rejectWithValue }) => {
    try {
      const response = await inheritanceService.getUserEffectivePermissions(params.userId, params.includeSources);
      return { userId: params.userId, data: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch user effective permissions');
    }
  }
);

export const fetchRoleHierarchy = createAsyncThunk(
  'inheritance/fetchRoleHierarchy',
  async (_, { rejectWithValue }) => {
    try {
      const response = await inheritanceService.getRoleHierarchy();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch role hierarchy');
    }
  }
);

export const fetchGroupHierarchy = createAsyncThunk(
  'inheritance/fetchGroupHierarchy',
  async (_, { rejectWithValue }) => {
    try {
      const response = await inheritanceService.getGroupHierarchy();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch group hierarchy');
    }
  }
);

export const analyzeInheritanceConflicts = createAsyncThunk(
  'inheritance/analyzeInheritanceConflicts',
  async (userId: string, { rejectWithValue }) => {
    try {
      const response = await inheritanceService.analyzeInheritanceConflicts(userId);
      return { userId, conflicts: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to analyze inheritance conflicts');
    }
  }
);

export const analyzePermissionComplexity = createAsyncThunk(
  'inheritance/analyzePermissionComplexity',
  async (userId: string, { rejectWithValue }) => {
    try {
      const response = await inheritanceService.analyzePermissionComplexity(userId);
      return { userId, complexity: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to analyze permission complexity');
    }
  }
);

export const optimizeUserPermissions = createAsyncThunk(
  'inheritance/optimizeUserPermissions',
  async (userId: string, { rejectWithValue }) => {
    try {
      const response = await inheritanceService.optimizeUserPermissions(userId);
      return { userId, optimization: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to optimize user permissions');
    }
  }
);

export const previewPermissionChanges = createAsyncThunk(
  'inheritance/previewPermissionChanges',
  async (params: {
    userId: string;
    changes: {
      addRoles?: string[];
      removeRoles?: string[];
      addGroups?: string[];
      removeGroups?: string[];
      addDirectPermissions?: string[];
      removeDirectPermissions?: string[];
    };
  }, { rejectWithValue }) => {
    try {
      const response = await inheritanceService.previewPermissionChanges(params.userId, params.changes);
      return { userId: params.userId, preview: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to preview permission changes');
    }
  }
);

export const getInheritanceStatistics = createAsyncThunk(
  'inheritance/getInheritanceStatistics',
  async (userId: string, { rejectWithValue }) => {
    try {
      const response = await inheritanceService.getInheritanceStatistics(userId);
      return { userId, statistics: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch inheritance statistics');
    }
  }
);

export const validateInheritanceIntegrity = createAsyncThunk(
  'inheritance/validateInheritanceIntegrity',
  async (_, { rejectWithValue }) => {
    try {
      const response = await inheritanceService.validateInheritanceIntegrity();
      return response;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to validate inheritance integrity');
    }
  }
);

export const getPermissionTrace = createAsyncThunk(
  'inheritance/getPermissionTrace',
  async (params: { userId: string; permissionName: string }, { rejectWithValue }) => {
    try {
      const response = await inheritanceService.getPermissionTrace(params.userId, params.permissionName);
      return { userId: params.userId, permissionName: params.permissionName, trace: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to get permission trace');
    }
  }
);

export const simulatePermissionRemoval = createAsyncThunk(
  'inheritance/simulatePermissionRemoval',
  async (params: { userId: string; sourceType: string; sourceId: string }, { rejectWithValue }) => {
    try {
      const response = await inheritanceService.simulatePermissionRemoval(params.userId, params.sourceType, params.sourceId);
      return { userId: params.userId, simulation: response };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to simulate permission removal');
    }
  }
);

const inheritanceSlice = createSlice({
  name: 'inheritance',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = undefined;
    },
    clearUserEffectivePermissions: (state, action: PayloadAction<string>) => {
      delete state.userEffectivePermissions[action.payload];
    },
    clearAnalysisResults: (state, action: PayloadAction<string>) => {
      delete state.analysisResults[action.payload];
    },
    clearAllAnalysisResults: (state) => {
      state.analysisResults = {};
    },
    setInheritanceConflicts: (state, action: PayloadAction<any[]>) => {
      state.inheritanceConflicts = action.payload;
    },
    clearInheritanceConflicts: (state) => {
      state.inheritanceConflicts = [];
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch user effective permissions
      .addCase(fetchUserEffectivePermissions.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(fetchUserEffectivePermissions.fulfilled, (state, action) => {
        state.isLoading = false;
        state.userEffectivePermissions[action.payload.userId] = action.payload.data;
        state.error = undefined;
      })
      .addCase(fetchUserEffectivePermissions.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Fetch role hierarchy
      .addCase(fetchRoleHierarchy.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(fetchRoleHierarchy.fulfilled, (state, action) => {
        state.isLoading = false;
        state.roleHierarchy = action.payload;
        state.error = undefined;
      })
      .addCase(fetchRoleHierarchy.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Fetch group hierarchy
      .addCase(fetchGroupHierarchy.pending, (state) => {
        state.isLoading = true;
        state.error = undefined;
      })
      .addCase(fetchGroupHierarchy.fulfilled, (state, action) => {
        state.isLoading = false;
        state.groupHierarchy = action.payload;
        state.error = undefined;
      })
      .addCase(fetchGroupHierarchy.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Analyze inheritance conflicts
      .addCase(analyzeInheritanceConflicts.fulfilled, (state, action) => {
        state.analysisResults[`conflicts_${action.payload.userId}`] = action.payload.conflicts;
        state.inheritanceConflicts = action.payload.conflicts;
      })
      .addCase(analyzeInheritanceConflicts.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Analyze permission complexity
      .addCase(analyzePermissionComplexity.fulfilled, (state, action) => {
        state.analysisResults[`complexity_${action.payload.userId}`] = action.payload.complexity;
      })
      .addCase(analyzePermissionComplexity.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Optimize user permissions
      .addCase(optimizeUserPermissions.fulfilled, (state, action) => {
        state.analysisResults[`optimization_${action.payload.userId}`] = action.payload.optimization;
      })
      .addCase(optimizeUserPermissions.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Preview permission changes
      .addCase(previewPermissionChanges.fulfilled, (state, action) => {
        state.analysisResults[`preview_${action.payload.userId}`] = action.payload.preview;
      })
      .addCase(previewPermissionChanges.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Get inheritance statistics
      .addCase(getInheritanceStatistics.fulfilled, (state, action) => {
        if (state.userEffectivePermissions[action.payload.userId]) {
          state.userEffectivePermissions[action.payload.userId].statistics = action.payload.statistics;
        }
      })
      .addCase(getInheritanceStatistics.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Validate inheritance integrity
      .addCase(validateInheritanceIntegrity.fulfilled, (state, action) => {
        state.analysisResults.integrity_validation = action.payload;
      })
      .addCase(validateInheritanceIntegrity.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Get permission trace
      .addCase(getPermissionTrace.fulfilled, (state, action) => {
        const key = `trace_${action.payload.userId}_${action.payload.permissionName}`;
        state.analysisResults[key] = action.payload.trace;
      })
      .addCase(getPermissionTrace.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Simulate permission removal
      .addCase(simulatePermissionRemoval.fulfilled, (state, action) => {
        const key = `simulation_${action.payload.userId}`;
        state.analysisResults[key] = action.payload.simulation;
      })
      .addCase(simulatePermissionRemoval.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const {
  clearError,
  clearUserEffectivePermissions,
  clearAnalysisResults,
  clearAllAnalysisResults,
  setInheritanceConflicts,
  clearInheritanceConflicts,
} = inheritanceSlice.actions;

export default inheritanceSlice.reducer;