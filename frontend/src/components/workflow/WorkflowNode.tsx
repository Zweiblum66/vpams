import React, { memo, useCallback } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import {
  Card,
  CardContent,
  Typography,
  Box,
  IconButton,
  Tooltip,
  Chip,
  CircularProgress,
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  Stop,
  Edit,
  Delete,
  Settings,
  Error,
  CheckCircle,
  Warning,
} from '@mui/icons-material';
import { WorkflowNode as WorkflowNodeType } from '../../store/api/workflowApi';

interface WorkflowNodeData extends WorkflowNodeType {
  status?: 'idle' | 'running' | 'completed' | 'failed' | 'paused';
  onEdit?: (nodeId: string) => void;
  onDelete?: (nodeId: string) => void;
  onSettings?: (nodeId: string) => void;
}

const WorkflowNode: React.FC<NodeProps<WorkflowNodeData>> = memo(({ data, selected }) => {
  const {
    node_id,
    node_type,
    name,
    description,
    color,
    icon,
    status = 'idle',
    input_ports,
    output_ports,
    onEdit,
    onDelete,
    onSettings,
  } = data;

  const getStatusColor = useCallback((status: string) => {
    switch (status) {
      case 'running':
        return '#2196F3';
      case 'completed':
        return '#4CAF50';
      case 'failed':
        return '#F44336';
      case 'paused':
        return '#FF9800';
      default:
        return '#9E9E9E';
    }
  }, []);

  const getStatusIcon = useCallback((status: string) => {
    switch (status) {
      case 'running':
        return <CircularProgress size={16} />;
      case 'completed':
        return <CheckCircle fontSize="small" />;
      case 'failed':
        return <Error fontSize="small" />;
      case 'paused':
        return <Pause fontSize="small" />;
      default:
        return null;
    }
  }, []);

  const getNodeIcon = useCallback((nodeType: string, icon?: string) => {
    if (icon) {
      return icon;
    }
    
    switch (nodeType) {
      case 'start':
        return '🚀';
      case 'end':
        return '🏁';
      case 'task':
        return '⚙️';
      case 'condition':
        return '🔀';
      case 'parallel':
        return '🔄';
      case 'timer':
        return '⏰';
      case 'notification':
        return '📢';
      default:
        return '📦';
    }
  }, []);

  const handleEdit = useCallback(() => {
    if (onEdit) {
      onEdit(node_id);
    }
  }, [node_id, onEdit]);

  const handleDelete = useCallback(() => {
    if (onDelete) {
      onDelete(node_id);
    }
  }, [node_id, onDelete]);

  const handleSettings = useCallback(() => {
    if (onSettings) {
      onSettings(node_id);
    }
  }, [node_id, onSettings]);

  return (
    <Card
      sx={{
        minWidth: 200,
        maxWidth: 300,
        border: selected ? '2px solid #1976d2' : '1px solid #e0e0e0',
        borderRadius: 2,
        position: 'relative',
        backgroundColor: color || '#ffffff',
        boxShadow: selected ? 3 : 1,
        transition: 'all 0.2s ease-in-out',
        '&:hover': {
          boxShadow: 3,
        },
      }}
    >
      {/* Input Handles */}
      {input_ports.map((port, index) => (
        <Handle
          key={`input-${port}`}
          type="target"
          position={Position.Left}
          id={port}
          style={{
            top: `${20 + (index * 20)}px`,
            left: -8,
            width: 16,
            height: 16,
            backgroundColor: '#1976d2',
            border: '2px solid #ffffff',
          }}
        />
      ))}

      {/* Output Handles */}
      {output_ports.map((port, index) => (
        <Handle
          key={`output-${port}`}
          type="source"
          position={Position.Right}
          id={port}
          style={{
            top: `${20 + (index * 20)}px`,
            right: -8,
            width: 16,
            height: 16,
            backgroundColor: '#1976d2',
            border: '2px solid #ffffff',
          }}
        />
      ))}

      <CardContent sx={{ p: 2 }}>
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: 1,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h6" component="span">
              {getNodeIcon(node_type, icon)}
            </Typography>
            <Typography
              variant="subtitle1"
              sx={{
                fontWeight: 'bold',
                fontSize: '0.9rem',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                maxWidth: '120px',
              }}
            >
              {name}
            </Typography>
          </Box>

          {/* Status Indicator */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              color: getStatusColor(status),
            }}
          >
            {getStatusIcon(status)}
            <Chip
              label={status}
              size="small"
              variant="outlined"
              sx={{
                height: 20,
                fontSize: '0.7rem',
                borderColor: getStatusColor(status),
                color: getStatusColor(status),
              }}
            />
          </Box>
        </Box>

        {/* Description */}
        {description && (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              mb: 1,
              fontSize: '0.75rem',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
            }}
          >
            {description}
          </Typography>
        )}

        {/* Node Type */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Chip
            label={node_type}
            size="small"
            variant="filled"
            sx={{
              height: 20,
              fontSize: '0.7rem',
              backgroundColor: color || '#e3f2fd',
              color: '#1976d2',
            }}
          />
        </Box>

        {/* Action Buttons */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mt: 1,
          }}
        >
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <Tooltip title="Edit">
              <IconButton
                size="small"
                onClick={handleEdit}
                sx={{
                  width: 24,
                  height: 24,
                  '&:hover': { backgroundColor: 'rgba(25, 118, 210, 0.1)' },
                }}
              >
                <Edit fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Settings">
              <IconButton
                size="small"
                onClick={handleSettings}
                sx={{
                  width: 24,
                  height: 24,
                  '&:hover': { backgroundColor: 'rgba(25, 118, 210, 0.1)' },
                }}
              >
                <Settings fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete">
              <IconButton
                size="small"
                onClick={handleDelete}
                sx={{
                  width: 24,
                  height: 24,
                  '&:hover': { backgroundColor: 'rgba(244, 67, 54, 0.1)' },
                }}
              >
                <Delete fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>

          {/* Port Indicators */}
          <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
            {input_ports.length > 0 && (
              <Tooltip title={`${input_ports.length} input port(s)`}>
                <Chip
                  label={`← ${input_ports.length}`}
                  size="small"
                  variant="outlined"
                  sx={{
                    height: 16,
                    fontSize: '0.6rem',
                    borderColor: '#4caf50',
                    color: '#4caf50',
                  }}
                />
              </Tooltip>
            )}
            {output_ports.length > 0 && (
              <Tooltip title={`${output_ports.length} output port(s)`}>
                <Chip
                  label={`${output_ports.length} →`}
                  size="small"
                  variant="outlined"
                  sx={{
                    height: 16,
                    fontSize: '0.6rem',
                    borderColor: '#ff9800',
                    color: '#ff9800',
                  }}
                />
              </Tooltip>
            )}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
});

WorkflowNode.displayName = 'WorkflowNode';

export default WorkflowNode;