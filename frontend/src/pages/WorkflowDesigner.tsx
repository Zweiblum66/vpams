import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Tooltip,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Snackbar,
  Menu,
  MenuItem,
  Divider,
} from '@mui/material';
import {
  Save,
  PlayArrow,
  Pause,
  Stop,
  Undo,
  Redo,
  ZoomIn,
  ZoomOut,
  FitScreen,
  Settings,
  FileDownload,
  FileUpload,
  Share,
  Visibility,
  BugReport,
  Assessment,
} from '@mui/icons-material';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  Connection,
  NodeChange,
  EdgeChange,
  ReactFlowProvider,
  Controls,
  Background,
  MiniMap,
  useReactFlow,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';

import WorkflowNode from '../components/workflow/WorkflowNode';
import NodeLibrary from '../components/workflow/NodeLibrary';
import WorkflowTesting from '../components/workflow/WorkflowTesting';
import WorkflowAnalytics from '../components/workflow/WorkflowAnalytics';
import {
  useGetDesignerWorkflowQuery,
  useUpdateDesignerStateMutation,
  useCreateDesignerWorkflowMutation,
  useValidateWorkflowMutation,
  usePreviewWorkflowMutation,
  useExportWorkflowMutation,
  WorkflowDesignerState,
  WorkflowNode as WorkflowNodeType,
} from '../store/api/workflowApi';
import { useParams, useNavigate } from 'react-router-dom';

const nodeTypes = {
  workflowNode: WorkflowNode,
};

interface WorkflowDesignerContentProps {
  workflowId?: string;
}

const WorkflowDesignerContent: React.FC<WorkflowDesignerContentProps> = ({ workflowId }) => {
  const navigate = useNavigate();
  const reactFlowInstance = useReactFlow();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isModified, setIsModified] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(!workflowId);
  const [newWorkflowName, setNewWorkflowName] = useState('');
  const [newWorkflowDescription, setNewWorkflowDescription] = useState('');
  const [showValidation, setShowValidation] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [showTesting, setShowTesting] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'info' }>({
    open: false,
    message: '',
    severity: 'info',
  });
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const dragRef = useRef<HTMLDivElement>(null);

  // API hooks
  const { data: workflowData, isLoading, error } = useGetDesignerWorkflowQuery(workflowId!, {
    skip: !workflowId,
  });
  const [updateDesignerState] = useUpdateDesignerStateMutation();
  const [createDesignerWorkflow] = useCreateDesignerWorkflowMutation();
  const [validateWorkflow] = useValidateWorkflowMutation();
  const [previewWorkflow] = usePreviewWorkflowMutation();
  const [exportWorkflow] = useExportWorkflowMutation();

  // Load workflow data
  useEffect(() => {
    if (workflowData) {
      const flowNodes = workflowData.nodes.map((node: WorkflowNodeType) => ({
        id: node.node_id,
        type: 'workflowNode',
        position: node.position,
        data: {
          ...node,
          onEdit: handleNodeEdit,
          onDelete: handleNodeDelete,
          onSettings: handleNodeSettings,
        },
      }));

      const flowEdges = workflowData.connections.map((conn) => ({
        id: conn.connection_id,
        source: conn.source_node_id,
        target: conn.target_node_id,
        sourceHandle: conn.source_port,
        targetHandle: conn.target_port,
        type: 'smoothstep',
        animated: conn.connection_type === 'running',
        style: {
          stroke: conn.color || '#1976d2',
          strokeWidth: 2,
        },
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
      setIsModified(false);
    }
  }, [workflowData]);

  // Event handlers
  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds));
    setIsModified(true);
  }, []);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => applyEdgeChanges(changes, eds));
    setIsModified(true);
  }, []);

  const onConnect = useCallback((connection: Connection) => {
    setEdges((eds) => addEdge(connection, eds));
    setIsModified(true);
  }, []);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const reactFlowBounds = dragRef.current?.getBoundingClientRect();
      if (!reactFlowBounds) return;

      const type = event.dataTransfer.getData('application/reactflow');
      if (!type) return;

      const { nodeType, nodeData } = JSON.parse(type);
      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const newNode: Node = {
        id: `${nodeType}-${Date.now()}`,
        type: 'workflowNode',
        position,
        data: {
          node_id: `${nodeType}-${Date.now()}`,
          node_type: nodeType,
          task_type: nodeType,
          name: nodeData.name,
          description: nodeData.description,
          position,
          size: { width: 200, height: 80 },
          color: nodeData.color,
          icon: nodeData.icon,
          parameters: {},
          timeout: 300,
          retry_count: 3,
          retry_delay: 60,
          continue_on_error: false,
          input_ports: nodeData.input_ports?.map((p: any) => p.name) || [],
          output_ports: nodeData.output_ports?.map((p: any) => p.name) || [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          onEdit: handleNodeEdit,
          onDelete: handleNodeDelete,
          onSettings: handleNodeSettings,
        },
      };

      setNodes((nds) => nds.concat(newNode));
      setIsModified(true);
    },
    [reactFlowInstance]
  );

  const handleNodeDragStart = useCallback((event: React.DragEvent, nodeType: string, nodeData: any) => {
    // This is handled by the NodeLibrary component
  }, []);

  const handleNodeEdit = useCallback((nodeId: string) => {
    // TODO: Open node edit dialog
    console.log('Edit node:', nodeId);
  }, []);

  const handleNodeDelete = useCallback((nodeId: string) => {
    setNodes((nds) => nds.filter((node) => node.id !== nodeId));
    setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    setIsModified(true);
  }, []);

  const handleNodeSettings = useCallback((nodeId: string) => {
    // TODO: Open node settings dialog
    console.log('Settings for node:', nodeId);
  }, []);

  const handleSave = useCallback(async () => {
    if (!workflowId) return;

    try {
      const workflowState: WorkflowDesignerState = {
        workflow_id: workflowId,
        name: workflowData?.name || 'Untitled Workflow',
        description: workflowData?.description,
        version: workflowData?.version || '1.0.0',
        nodes: nodes.map((node) => ({
          ...node.data,
          position: node.position,
        })),
        connections: edges.map((edge) => ({
          connection_id: edge.id,
          source_node_id: edge.source,
          target_node_id: edge.target,
          source_port: edge.sourceHandle || 'output',
          target_port: edge.targetHandle || 'input',
          connection_type: 'success',
          points: [],
          created_at: new Date().toISOString(),
        })),
        layout: {
          canvas_size: { width: 2000, height: 1500 },
          zoom_level: 1,
          pan_offset: { x: 0, y: 0 },
          grid_size: 20,
          snap_to_grid: true,
          show_grid: true,
          auto_layout: false,
          layout_direction: 'horizontal',
        },
        variables: {},
        created_at: workflowData?.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      await updateDesignerState({ workflowId, state: workflowState });
      setIsModified(false);
      setSnackbar({ open: true, message: 'Workflow saved successfully', severity: 'success' });
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to save workflow', severity: 'error' });
    }
  }, [workflowId, nodes, edges, workflowData, updateDesignerState]);

  const handleCreateWorkflow = useCallback(async () => {
    if (!newWorkflowName.trim()) return;

    try {
      const result = await createDesignerWorkflow({
        name: newWorkflowName,
        description: newWorkflowDescription,
        category: 'custom',
        tags: [],
        created_by: 'user',
      });

      if ('data' in result) {
        navigate(`/workflows/designer/${result.data.workflow_id}`);
        setShowCreateDialog(false);
        setSnackbar({ open: true, message: 'Workflow created successfully', severity: 'success' });
      }
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to create workflow', severity: 'error' });
    }
  }, [newWorkflowName, newWorkflowDescription, createDesignerWorkflow, navigate]);

  const handleValidate = useCallback(async () => {
    if (!workflowId) return;

    try {
      const result = await validateWorkflow(workflowId);
      if ('data' in result) {
        setValidationResult(result.data);
        setShowValidation(true);
      }
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to validate workflow', severity: 'error' });
    }
  }, [workflowId, validateWorkflow]);

  const handlePreview = useCallback(async () => {
    if (!workflowId) return;

    try {
      const result = await previewWorkflow({
        workflowId,
        include_steps: true,
        include_outputs: true,
      });
      if ('data' in result) {
        console.log('Preview result:', result.data);
        setSnackbar({ open: true, message: 'Preview generated successfully', severity: 'success' });
      }
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to generate preview', severity: 'error' });
    }
  }, [workflowId, previewWorkflow]);

  const handleExport = useCallback(async () => {
    if (!workflowId) return;

    try {
      const result = await exportWorkflow({
        workflowId,
        format: 'json',
        include_metadata: true,
        include_layout: true,
      });
      if ('data' in result) {
        const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `workflow-${workflowId}.json`;
        a.click();
        URL.revokeObjectURL(url);
        setSnackbar({ open: true, message: 'Workflow exported successfully', severity: 'success' });
      }
    } catch (error) {
      setSnackbar({ open: true, message: 'Failed to export workflow', severity: 'error' });
    }
  }, [workflowId, exportWorkflow]);

  const handleMenuClick = useCallback((event: React.MouseEvent<HTMLElement>) => {
    setMenuAnchor(event.currentTarget);
  }, []);

  const handleMenuClose = useCallback(() => {
    setMenuAnchor(null);
  }, []);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Typography>Loading workflow...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Alert severity="error">Failed to load workflow</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Toolbar */}
      <AppBar position="static" color="default" elevation={1}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Workflow Designer
            {workflowData?.name && ` - ${workflowData.name}`}
            {isModified && <Chip label="Modified" size="small" sx={{ ml: 1 }} />}
          </Typography>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Save">
              <IconButton onClick={handleSave} disabled={!isModified}>
                <Save />
              </IconButton>
            </Tooltip>
            <Tooltip title="Validate">
              <IconButton onClick={handleValidate}>
                <BugReport />
              </IconButton>
            </Tooltip>
            <Tooltip title="Preview">
              <IconButton onClick={handlePreview}>
                <Visibility />
              </IconButton>
            </Tooltip>
            <Tooltip title="Export">
              <IconButton onClick={handleExport}>
                <FileDownload />
              </IconButton>
            </Tooltip>
            <Tooltip title="Testing">
              <IconButton onClick={() => setShowTesting(true)}>
                <BugReport />
              </IconButton>
            </Tooltip>
            <Tooltip title="Analytics">
              <IconButton onClick={() => setShowAnalytics(true)}>
                <Assessment />
              </IconButton>
            </Tooltip>
            <Tooltip title="More">
              <IconButton onClick={handleMenuClick}>
                <Settings />
              </IconButton>
            </Tooltip>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Box sx={{ display: 'flex', flex: 1 }}>
        {/* Node Library */}
        <NodeLibrary onNodeDragStart={handleNodeDragStart} />

        {/* React Flow */}
        <Box
          ref={dragRef}
          sx={{ flex: 1, height: '100%' }}
          onDragOver={onDragOver}
          onDrop={onDrop}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            snapToGrid
            snapGrid={[20, 20]}
          >
            <Controls />
            <Background color="#f0f0f0" gap={20} />
            <MiniMap
              style={{
                backgroundColor: '#f8f9fa',
                border: '1px solid #e9ecef',
              }}
              nodeColor="#1976d2"
              maskColor="rgba(255, 255, 255, 0.7)"
            />
            <Panel position="top-right">
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Tooltip title="Zoom In">
                  <IconButton size="small" onClick={() => reactFlowInstance.zoomIn()}>
                    <ZoomIn />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Zoom Out">
                  <IconButton size="small" onClick={() => reactFlowInstance.zoomOut()}>
                    <ZoomOut />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Fit View">
                  <IconButton size="small" onClick={() => reactFlowInstance.fitView()}>
                    <FitScreen />
                  </IconButton>
                </Tooltip>
              </Box>
            </Panel>
          </ReactFlow>
        </Box>
      </Box>

      {/* Create Workflow Dialog */}
      <Dialog open={showCreateDialog} onClose={() => setShowCreateDialog(false)}>
        <DialogTitle>Create New Workflow</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Workflow Name"
            value={newWorkflowName}
            onChange={(e) => setNewWorkflowName(e.target.value)}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Description"
            value={newWorkflowDescription}
            onChange={(e) => setNewWorkflowDescription(e.target.value)}
            margin="normal"
            multiline
            rows={3}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreateDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateWorkflow} variant="contained">
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Validation Results Dialog */}
      <Dialog open={showValidation} onClose={() => setShowValidation(false)} maxWidth="md" fullWidth>
        <DialogTitle>Workflow Validation Results</DialogTitle>
        <DialogContent>
          {validationResult && (
            <Box>
              <Typography variant="h6" color={validationResult.is_valid ? 'success.main' : 'error.main'}>
                {validationResult.is_valid ? 'Valid' : 'Invalid'}
              </Typography>
              {validationResult.errors.length > 0 && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  <Typography variant="subtitle2">Errors:</Typography>
                  {validationResult.errors.map((error: any, index: number) => (
                    <Typography key={index} variant="body2">
                      • {error.message}
                    </Typography>
                  ))}
                </Alert>
              )}
              {validationResult.warnings.length > 0 && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  <Typography variant="subtitle2">Warnings:</Typography>
                  {validationResult.warnings.map((warning: any, index: number) => (
                    <Typography key={index} variant="body2">
                      • {warning.message}
                    </Typography>
                  ))}
                </Alert>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowValidation(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Context Menu */}
      <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={handleMenuClose}>
        <MenuItem onClick={handleMenuClose}>
          <FileUpload sx={{ mr: 1 }} />
          Import Workflow
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <Share sx={{ mr: 1 }} />
          Share Workflow
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleMenuClose}>
          <Settings sx={{ mr: 1 }} />
          Settings
        </MenuItem>
      </Menu>

      {/* Testing Dialog */}
      <Dialog open={showTesting} onClose={() => setShowTesting(false)} maxWidth="xl" fullWidth>
        <DialogTitle>
          Workflow Testing
          {workflowData?.name && ` - ${workflowData.name}`}
        </DialogTitle>
        <DialogContent sx={{ height: '80vh' }}>
          {workflowId && <WorkflowTesting workflowId={workflowId} />}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowTesting(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Analytics Dialog */}
      <Dialog open={showAnalytics} onClose={() => setShowAnalytics(false)} maxWidth="xl" fullWidth>
        <DialogTitle>
          Workflow Analytics
          {workflowData?.name && ` - ${workflowData.name}`}
        </DialogTitle>
        <DialogContent sx={{ height: '80vh' }}>
          {workflowId && <WorkflowAnalytics workflowId={workflowId} />}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAnalytics(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

const WorkflowDesigner: React.FC = () => {
  const { workflowId } = useParams<{ workflowId: string }>();

  return (
    <ReactFlowProvider>
      <WorkflowDesignerContent workflowId={workflowId} />
    </ReactFlowProvider>
  );
};

export default WorkflowDesigner;