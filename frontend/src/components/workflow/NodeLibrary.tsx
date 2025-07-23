import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Typography,
  TextField,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Card,
  CardContent,
  Chip,
  Tooltip,
  InputAdornment,
  IconButton,
  Skeleton,
  Alert,
} from '@mui/material';
import {
  ExpandMore,
  Search,
  Clear,
  DragIndicator,
  Info,
} from '@mui/icons-material';
import { useGetAvailableNodesQuery } from '../../store/api/workflowApi';

interface NodeLibraryProps {
  onNodeDragStart: (event: React.DragEvent, nodeType: string, nodeData: any) => void;
  className?: string;
}

const NodeLibrary: React.FC<NodeLibraryProps> = ({ onNodeDragStart, className }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<string[]>([]);

  const {
    data: nodesData,
    isLoading,
    error,
    refetch,
  } = useGetAvailableNodesQuery({
    search: searchTerm || undefined,
    category: selectedCategory || undefined,
  });

  const categories = useMemo(() => {
    if (!nodesData?.categories) return [];
    return Object.keys(nodesData.categories).sort();
  }, [nodesData]);

  const handleSearchChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  }, []);

  const handleClearSearch = useCallback(() => {
    setSearchTerm('');
  }, []);

  const handleCategoryToggle = useCallback((category: string) => {
    setExpandedCategories(prev => 
      prev.includes(category) 
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  }, []);

  const handleNodeDragStart = useCallback((event: React.DragEvent, nodeType: string, nodeData: any) => {
    // Set drag data
    event.dataTransfer.setData('application/reactflow', JSON.stringify({
      nodeType,
      nodeData,
    }));
    event.dataTransfer.effectAllowed = 'move';

    // Call parent handler
    onNodeDragStart(event, nodeType, nodeData);
  }, [onNodeDragStart]);

  const getNodeIcon = useCallback((nodeType: string, icon?: string) => {
    if (icon) return icon;
    
    switch (nodeType) {
      case 'transcode':
        return '🎬';
      case 'generate_proxy':
        return '📹';
      case 'generate_thumbnail':
        return '🖼️';
      case 'copy_file':
        return '📋';
      case 'move_file':
        return '📁';
      case 'create_asset':
        return '➕';
      case 'send_email':
        return '📧';
      case 'condition':
        return '🔀';
      case 'auto_tag':
        return '🏷️';
      default:
        return '📦';
    }
  }, []);

  const getCategoryColor = useCallback((category: string) => {
    const colors = {
      'media_processing': '#FF6B6B',
      'file_operations': '#4ECDC4',
      'asset_operations': '#45B7D1',
      'notifications': '#96CEB4',
      'control_flow': '#FFEAA7',
      'ai_ml': '#DDA0DD',
    };
    return colors[category as keyof typeof colors] || '#E0E0E0';
  }, []);

  if (isLoading) {
    return (
      <Box className={className} sx={{ width: 300, p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Node Library
        </Typography>
        <Skeleton variant="rectangular" height={40} sx={{ mb: 2 }} />
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} variant="rectangular" height={60} sx={{ mb: 1 }} />
        ))}
      </Box>
    );
  }

  if (error) {
    return (
      <Box className={className} sx={{ width: 300, p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Node Library
        </Typography>
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load nodes. 
          <IconButton size="small" onClick={() => refetch()}>
            <Clear />
          </IconButton>
        </Alert>
      </Box>
    );
  }

  return (
    <Box 
      className={className} 
      sx={{ 
        width: 300, 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column',
        borderRight: '1px solid #e0e0e0',
        backgroundColor: '#fafafa',
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0' }}>
        <Typography variant="h6" gutterBottom>
          Node Library
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Drag and drop nodes to create your workflow
        </Typography>
        
        {/* Search */}
        <TextField
          fullWidth
          size="small"
          placeholder="Search nodes..."
          value={searchTerm}
          onChange={handleSearchChange}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: searchTerm && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={handleClearSearch}>
                  <Clear fontSize="small" />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
      </Box>

      {/* Categories */}
      <Box sx={{ flex: 1, overflow: 'auto', p: 1 }}>
        {categories.map((category) => {
          const categoryNodes = nodesData?.categories[category] || [];
          const isExpanded = expandedCategories.includes(category);

          return (
            <Accordion
              key={category}
              expanded={isExpanded}
              onChange={() => handleCategoryToggle(category)}
              sx={{
                mb: 1,
                boxShadow: 1,
                '&:before': { display: 'none' },
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMore />}
                sx={{
                  backgroundColor: getCategoryColor(category),
                  color: 'white',
                  '& .MuiAccordionSummary-content': {
                    alignItems: 'center',
                  },
                }}
              >
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                  {category.replace('_', ' ').toUpperCase()}
                </Typography>
                <Chip
                  label={categoryNodes.length}
                  size="small"
                  sx={{
                    ml: 1,
                    backgroundColor: 'rgba(255, 255, 255, 0.3)',
                    color: 'white',
                  }}
                />
              </AccordionSummary>
              <AccordionDetails sx={{ p: 1 }}>
                {categoryNodes.map((node) => (
                  <Card
                    key={node.node_type}
                    sx={{
                      mb: 1,
                      cursor: 'grab',
                      transition: 'all 0.2s ease-in-out',
                      '&:hover': {
                        boxShadow: 2,
                        transform: 'translateY(-1px)',
                      },
                      '&:active': {
                        cursor: 'grabbing',
                        transform: 'translateY(0)',
                      },
                    }}
                    draggable
                    onDragStart={(e) => handleNodeDragStart(e, node.node_type, node)}
                  >
                    <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <DragIndicator fontSize="small" color="action" />
                        <Typography variant="body2" sx={{ fontSize: '1.2rem' }}>
                          {getNodeIcon(node.node_type, node.icon)}
                        </Typography>
                        <Box sx={{ flex: 1 }}>
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: 'bold',
                              fontSize: '0.8rem',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {node.name}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{
                              fontSize: '0.7rem',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              display: 'block',
                            }}
                          >
                            {node.description}
                          </Typography>
                        </Box>
                        <Tooltip title={node.description}>
                          <IconButton size="small">
                            <Info fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      
                      {/* Port indicators */}
                      <Box sx={{ display: 'flex', gap: 0.5, mt: 1 }}>
                        {node.input_ports.length > 0 && (
                          <Chip
                            label={`← ${node.input_ports.length}`}
                            size="small"
                            variant="outlined"
                            sx={{
                              height: 16,
                              fontSize: '0.6rem',
                              borderColor: '#4caf50',
                              color: '#4caf50',
                            }}
                          />
                        )}
                        {node.output_ports.length > 0 && (
                          <Chip
                            label={`${node.output_ports.length} →`}
                            size="small"
                            variant="outlined"
                            sx={{
                              height: 16,
                              fontSize: '0.6rem',
                              borderColor: '#ff9800',
                              color: '#ff9800',
                            }}
                          />
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                ))}
              </AccordionDetails>
            </Accordion>
          );
        })}
      </Box>

      {/* Footer */}
      <Box sx={{ p: 2, borderTop: '1px solid #e0e0e0', backgroundColor: 'white' }}>
        <Typography variant="caption" color="text.secondary">
          Total: {nodesData?.total_nodes || 0} nodes
        </Typography>
      </Box>
    </Box>
  );
};

export default NodeLibrary;