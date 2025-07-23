/**
 * Projects Redux Slice
 * 
 * Manages project state including project list,
 * current project, and project-related operations.
 */

import {createSlice, PayloadAction} from '@reduxjs/toolkit';
import {ProjectState, Project} from '@/types';

const initialState: ProjectState = {
  projects: {},
  currentProject: null,
  isLoading: false,
  error: null,
};

const projectsSlice = createSlice({
  name: 'projects',
  initialState,
  reducers: {
    setProjects: (state, action: PayloadAction<Record<string, Project>>) => {
      state.projects = action.payload;
    },
    
    setCurrentProject: (state, action: PayloadAction<Project | null>) => {
      state.currentProject = action.payload;
    },
    
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

export const {
  setProjects,
  setCurrentProject,
  setLoading,
  setError,
} = projectsSlice.actions;

export default projectsSlice.reducer;