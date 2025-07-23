/**
 * Editing Slice
 * 
 * Redux state management for media editing features
 */

import {createSlice, PayloadAction} from '@reduxjs/toolkit';
import {EditProject, Edit, EditParameters, ExportSettings} from '@/services/editingService';

export interface EditingState {
  activeProject: EditProject | null;
  projects: EditProject[];
  isExporting: boolean;
  exportProgress: number;
  previewUrl: string | null;
  selectedEditId: string | null;
  undoStack: Edit[][];
  redoStack: Edit[][];
}

const initialState: EditingState = {
  activeProject: null,
  projects: [],
  isExporting: false,
  exportProgress: 0,
  previewUrl: null,
  selectedEditId: null,
  undoStack: [],
  redoStack: [],
};

const editingSlice = createSlice({
  name: 'editing',
  initialState,
  reducers: {
    // Project management
    createProject: (state, action: PayloadAction<EditProject>) => {
      state.projects.push(action.payload);
      state.activeProject = action.payload;
      state.undoStack = [];
      state.redoStack = [];
    },
    
    setActiveProject: (state, action: PayloadAction<string>) => {
      const project = state.projects.find(p => p.id === action.payload);
      if (project) {
        state.activeProject = project;
        state.selectedEditId = null;
      }
    },
    
    deleteProject: (state, action: PayloadAction<string>) => {
      state.projects = state.projects.filter(p => p.id !== action.payload);
      if (state.activeProject?.id === action.payload) {
        state.activeProject = null;
      }
    },
    
    // Edit management
    addEdit: (state, action: PayloadAction<Edit>) => {
      if (state.activeProject) {
        // Save current state for undo
        state.undoStack.push([...state.activeProject.edits]);
        state.redoStack = [];
        
        state.activeProject.edits.push(action.payload);
        state.activeProject.updated_at = new Date().toISOString();
        state.selectedEditId = action.payload.id;
      }
    },
    
    updateEdit: (state, action: PayloadAction<{
      editId: string;
      parameters: Partial<EditParameters>;
    }>) => {
      if (state.activeProject) {
        const edit = state.activeProject.edits.find(
          e => e.id === action.payload.editId
        );
        if (edit) {
          // Save current state for undo
          state.undoStack.push([...state.activeProject.edits]);
          state.redoStack = [];
          
          edit.parameters = {...edit.parameters, ...action.payload.parameters};
          state.activeProject.updated_at = new Date().toISOString();
        }
      }
    },
    
    removeEdit: (state, action: PayloadAction<string>) => {
      if (state.activeProject) {
        // Save current state for undo
        state.undoStack.push([...state.activeProject.edits]);
        state.redoStack = [];
        
        state.activeProject.edits = state.activeProject.edits.filter(
          e => e.id !== action.payload
        );
        state.activeProject.updated_at = new Date().toISOString();
        
        if (state.selectedEditId === action.payload) {
          state.selectedEditId = null;
        }
      }
    },
    
    toggleEdit: (state, action: PayloadAction<string>) => {
      if (state.activeProject) {
        const edit = state.activeProject.edits.find(e => e.id === action.payload);
        if (edit) {
          edit.enabled = !edit.enabled;
          state.activeProject.updated_at = new Date().toISOString();
        }
      }
    },
    
    selectEdit: (state, action: PayloadAction<string | null>) => {
      state.selectedEditId = action.payload;
    },
    
    // Undo/Redo
    undo: (state) => {
      if (state.activeProject && state.undoStack.length > 0) {
        state.redoStack.push([...state.activeProject.edits]);
        state.activeProject.edits = state.undoStack.pop() || [];
        state.activeProject.updated_at = new Date().toISOString();
      }
    },
    
    redo: (state) => {
      if (state.activeProject && state.redoStack.length > 0) {
        state.undoStack.push([...state.activeProject.edits]);
        state.activeProject.edits = state.redoStack.pop() || [];
        state.activeProject.updated_at = new Date().toISOString();
      }
    },
    
    // Export settings
    updateExportSettings: (state, action: PayloadAction<Partial<ExportSettings>>) => {
      if (state.activeProject) {
        state.activeProject.exportSettings = {
          ...state.activeProject.exportSettings,
          ...action.payload,
        };
      }
    },
    
    // Export progress
    setExporting: (state, action: PayloadAction<boolean>) => {
      state.isExporting = action.payload;
      if (!action.payload) {
        state.exportProgress = 0;
      }
    },
    
    setExportProgress: (state, action: PayloadAction<number>) => {
      state.exportProgress = action.payload;
    },
    
    // Preview
    setPreviewUrl: (state, action: PayloadAction<string | null>) => {
      state.previewUrl = action.payload;
    },
    
    // Clear state
    clearEditing: (state) => {
      state.activeProject = null;
      state.selectedEditId = null;
      state.previewUrl = null;
      state.undoStack = [];
      state.redoStack = [];
    },
  },
});

export const {
  createProject,
  setActiveProject,
  deleteProject,
  addEdit,
  updateEdit,
  removeEdit,
  toggleEdit,
  selectEdit,
  undo,
  redo,
  updateExportSettings,
  setExporting,
  setExportProgress,
  setPreviewUrl,
  clearEditing,
} = editingSlice.actions;

export default editingSlice.reducer;