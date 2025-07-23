import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Project, ProjectContainer, CreateProjectRequest, UpdateProjectRequest } from '../../types';
import { projectService } from '../../services/projectService';

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  containers: ProjectContainer[];
  loading: boolean;
  error: string | null;
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

const initialState: ProjectState = {
  projects: [],
  currentProject: null,
  containers: [],
  loading: false,
  error: null,
  pagination: {
    page: 1,
    limit: 20,
    total: 0,
    pages: 0,
  },
};

// Async thunks
export const fetchProjects = createAsyncThunk(
  'projects/fetchProjects',
  async (params: {
    page?: number;
    limit?: number;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
    filters?: Record<string, any>;
  } = {}) => {
    const response = await projectService.getProjects(params);
    return response;
  }
);

export const fetchProjectById = createAsyncThunk(
  'projects/fetchProjectById',
  async (id: string) => {
    const response = await projectService.getProjectById(id);
    return response;
  }
);

export const createProject = createAsyncThunk(
  'projects/createProject',
  async (data: CreateProjectRequest) => {
    const response = await projectService.createProject(data);
    return response;
  }
);

export const updateProject = createAsyncThunk(
  'projects/updateProject',
  async ({ id, data }: { id: string; data: UpdateProjectRequest }) => {
    const response = await projectService.updateProject(id, data);
    return response;
  }
);

export const deleteProject = createAsyncThunk(
  'projects/deleteProject',
  async (id: string) => {
    await projectService.deleteProject(id);
    return id;
  }
);

export const fetchProjectContainers = createAsyncThunk(
  'projects/fetchProjectContainers',
  async (projectId: string) => {
    const response = await projectService.getProjectContainers(projectId);
    return response;
  }
);

export const createContainer = createAsyncThunk(
  'projects/createContainer',
  async (data: {
    projectId: string;
    name: string;
    type: 'folder' | 'bin' | 'shotlist' | 'sequence';
    parentId?: string;
  }) => {
    const response = await projectService.createContainer(data);
    return response;
  }
);

export const updateContainer = createAsyncThunk(
  'projects/updateContainer',
  async ({ id, data }: { id: string; data: { name?: string; parentId?: string } }) => {
    const response = await projectService.updateContainer(id, data);
    return response;
  }
);

export const deleteContainer = createAsyncThunk(
  'projects/deleteContainer',
  async (id: string) => {
    await projectService.deleteContainer(id);
    return id;
  }
);

export const moveContainer = createAsyncThunk(
  'projects/moveContainer',
  async ({ id, parentId }: { id: string; parentId?: string }) => {
    const response = await projectService.moveContainer(id, parentId);
    return response;
  }
);

const projectSlice = createSlice({
  name: 'projects',
  initialState,
  reducers: {
    setCurrentProject: (state, action: PayloadAction<Project | null>) => {
      state.currentProject = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch projects
      .addCase(fetchProjects.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchProjects.fulfilled, (state, action) => {
        state.loading = false;
        state.projects = action.payload.data;
        state.pagination = action.payload.meta;
      })
      .addCase(fetchProjects.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch projects';
      })
      
      // Fetch project by ID
      .addCase(fetchProjectById.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchProjectById.fulfilled, (state, action) => {
        state.loading = false;
        state.currentProject = action.payload;
      })
      .addCase(fetchProjectById.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch project';
      })
      
      // Create project
      .addCase(createProject.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createProject.fulfilled, (state, action) => {
        state.loading = false;
        state.projects.unshift(action.payload);
        state.pagination.total += 1;
      })
      .addCase(createProject.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to create project';
      })
      
      // Update project
      .addCase(updateProject.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateProject.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.projects.findIndex(project => project.id === action.payload.id);
        if (index !== -1) {
          state.projects[index] = action.payload;
        }
        if (state.currentProject?.id === action.payload.id) {
          state.currentProject = action.payload;
        }
      })
      .addCase(updateProject.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to update project';
      })
      
      // Delete project
      .addCase(deleteProject.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteProject.fulfilled, (state, action) => {
        state.loading = false;
        state.projects = state.projects.filter(project => project.id !== action.payload);
        state.pagination.total -= 1;
        if (state.currentProject?.id === action.payload) {
          state.currentProject = null;
        }
      })
      .addCase(deleteProject.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to delete project';
      })
      
      // Fetch project containers
      .addCase(fetchProjectContainers.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchProjectContainers.fulfilled, (state, action) => {
        state.loading = false;
        state.containers = action.payload;
      })
      .addCase(fetchProjectContainers.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch containers';
      })
      
      // Create container
      .addCase(createContainer.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createContainer.fulfilled, (state, action) => {
        state.loading = false;
        state.containers.push(action.payload);
      })
      .addCase(createContainer.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to create container';
      })
      
      // Update container
      .addCase(updateContainer.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateContainer.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.containers.findIndex(container => container.id === action.payload.id);
        if (index !== -1) {
          state.containers[index] = action.payload;
        }
      })
      .addCase(updateContainer.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to update container';
      })
      
      // Delete container
      .addCase(deleteContainer.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteContainer.fulfilled, (state, action) => {
        state.loading = false;
        state.containers = state.containers.filter(container => container.id !== action.payload);
      })
      .addCase(deleteContainer.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to delete container';
      })
      
      // Move container
      .addCase(moveContainer.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(moveContainer.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.containers.findIndex(container => container.id === action.payload.id);
        if (index !== -1) {
          state.containers[index] = action.payload;
        }
      })
      .addCase(moveContainer.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to move container';
      });
  },
});

export const {
  setCurrentProject,
  clearError,
} = projectSlice.actions;

export default projectSlice.reducer;