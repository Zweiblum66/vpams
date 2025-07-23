import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Checkbox,
  IconButton,
  Paper,
  Divider,
  Alert,
  CircularProgress,
  Chip,
  FormControlLabel,
  Switch,
  LinearProgress,
  Collapse,
} from '@mui/material';
import {
  Sync,
  CloudUpload,
  Folder,
  VideoLibrary,
  CheckCircle,
  Error,
  Warning,
  ExpandMore,
  ExpandLess,
  FilterList,
  Delete,
} from '@mui/icons-material';
import { CSInterface } from '../utils/CSInterface';
import { MAMSClient } from '../services/mamsClient';

const csInterface = new CSInterface();

interface ProjectItem {
  id: string;
  name: string;
  type: string;
  path: string;
  synced: boolean;
  mamsId?: string;
  status?: 'synced' | 'modified' | 'new' | 'missing';
}

interface SyncResult {
  success: boolean;
  itemId: string;
  mamsId?: string;
  error?: string;
}

const ProjectSync: React.FC = () => {
  const [projectData, setProjectData] = useState<any>(null);
  const [projectItems, setProjectItems] = useState<ProjectItem[]>([]);
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState(0);
  const [autoSync, setAutoSync] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedBins, setExpandedBins] = useState<string[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>('all');

  useEffect(() => {
    loadProjectData();
    
    // Listen for project changes
    csInterface.addEventListener('com.mams.projectChanged', loadProjectData);
    
    return () => {
      csInterface.removeEventListener('com.mams.projectChanged', loadProjectData);
    };
  }, []);

  useEffect(() => {
    if (autoSync) {
      const interval = setInterval(syncProject, 60000); // Sync every minute
      return () => clearInterval(interval);
    }
  }, [autoSync]);

  const loadProjectData = () => {
    setLoading(true);
    csInterface.evalScript('getProjectInfo()', (result: string) => {
      try {
        if (result === 'null' || !result) {
          setError('No active project');
          setLoading(false);
          return;
        }
        
        const data = JSON.parse(result);
        setProjectData(data);
        
        // Load project items
        csInterface.evalScript('syncProject()', (syncResult: string) => {
          if (syncResult && syncResult !== 'null') {
            const syncData = JSON.parse(syncResult);
            processProjectItems(syncData.items);
          }
          setLoading(false);
        });
      } catch (err) {
        setError('Failed to load project data');
        setLoading(false);
      }
    });
  };

  const processProjectItems = async (items: any[]) => {
    const processed: ProjectItem[] = [];
    
    for (const item of items) {
      // Check if item exists in MAMS
      let synced = false;
      let mamsId: string | undefined;
      let status: 'synced' | 'modified' | 'new' | 'missing' = 'new';
      
      try {
        // Check by path or metadata
        const searchResult = await MAMSClient.getInstance().searchAssets({
          query: item.path,
          limit: 1,
        });
        
        if (searchResult.total > 0) {
          synced = true;
          mamsId = searchResult.assets[0].id;
          status = 'synced';
          
          // Check if modified
          if (item.metadata?.lastModified > searchResult.assets[0].updatedAt) {
            status = 'modified';
          }
        }
      } catch (err) {
        // Ignore search errors
      }
      
      processed.push({
        id: item.id,
        name: item.name,
        type: item.type,
        path: item.path,
        synced,
        mamsId,
        status,
      });
    }
    
    setProjectItems(processed);
  };

  const handleSelectAll = () => {
    if (selectedItems.length === projectItems.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(projectItems.map(item => item.id));
    }
  };

  const handleSelectItem = (itemId: string) => {
    if (selectedItems.includes(itemId)) {
      setSelectedItems(selectedItems.filter(id => id !== itemId));
    } else {
      setSelectedItems([...selectedItems, itemId]);
    }
  };

  const syncSelectedItems = async () => {
    setSyncing(true);
    setSyncProgress(0);
    const results: SyncResult[] = [];
    
    const itemsToSync = projectItems.filter(item => selectedItems.includes(item.id));
    
    for (let i = 0; i < itemsToSync.length; i++) {
      const item = itemsToSync[i];
      setSyncProgress((i / itemsToSync.length) * 100);
      
      try {
        // Upload to MAMS
        const file = await getFileFromPath(item.path);
        const asset = await MAMSClient.getInstance().uploadAsset(
          file,
          {
            name: item.name,
            projectId: projectData.name,
            premiereItemId: item.id,
          }
        );
        
        results.push({
          success: true,
          itemId: item.id,
          mamsId: asset.id,
        });
        
        // Update item status
        setProjectItems(prev => prev.map(p => 
          p.id === item.id ? { ...p, synced: true, mamsId: asset.id, status: 'synced' } : p
        ));
      } catch (err) {
        results.push({
          success: false,
          itemId: item.id,
          error: err.message,
        });
      }
    }
    
    setSyncProgress(100);
    setSyncing(false);
    setSelectedItems([]);
    
    // Show results
    const successCount = results.filter(r => r.success).length;
    if (successCount === results.length) {
      // All succeeded
    } else {
      setError(`${successCount} of ${results.length} items synced successfully`);
    }
  };

  const syncProject = async () => {
    // Sync entire project
    const allItems = projectItems.filter(item => !item.synced || item.status === 'modified');
    setSelectedItems(allItems.map(item => item.id));
    await syncSelectedItems();
  };

  const getFileFromPath = async (path: string): Promise<File> => {
    // This is a simplified version - in reality, you'd need to handle this differently
    // as browser security prevents direct file system access
    const response = await fetch(path);
    const blob = await response.blob();
    const filename = path.split('/').pop() || 'file';
    return new File([blob], filename);
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'synced':
        return <CheckCircle color="success" />;
      case 'modified':
        return <Warning color="warning" />;
      case 'missing':
        return <Error color="error" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'synced':
        return 'success';
      case 'modified':
        return 'warning';
      case 'missing':
        return 'error';
      default:
        return 'default';
    }
  };

  const filteredItems = projectItems.filter(item => {
    if (filterStatus === 'all') return true;
    return item.status === filterStatus;
  });

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!projectData) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">
          No active project. Open a project in Premiere Pro to enable sync.
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      {/* Project Info */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          {projectData.name}
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <Chip
            label={`${projectData.sequences.length} Sequences`}
            size="small"
          />
          <Chip
            label={`${projectItems.length} Items`}
            size="small"
          />
          <Chip
            label={`${projectItems.filter(i => i.synced).length} Synced`}
            size="small"
            color="success"
          />
        </Box>
        
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <FormControlLabel
            control={
              <Switch
                checked={autoSync}
                onChange={(e) => setAutoSync(e.target.checked)}
              />
            }
            label="Auto-sync"
          />
          
          <Box>
            <Button
              startIcon={<Sync />}
              onClick={loadProjectData}
              disabled={syncing}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<CloudUpload />}
              onClick={syncProject}
              disabled={syncing || projectItems.length === 0}
              sx={{ ml: 1 }}
            >
              Sync All
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* Sync Progress */}
      {syncing && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" gutterBottom>
            Syncing items...
          </Typography>
          <LinearProgress variant="determinate" value={syncProgress} />
        </Box>
      )}

      {/* Filter */}
      <Box sx={{ mb: 2, display: 'flex', gap: 1 }}>
        <Chip
          label="All"
          onClick={() => setFilterStatus('all')}
          color={filterStatus === 'all' ? 'primary' : 'default'}
        />
        <Chip
          label="New"
          onClick={() => setFilterStatus('new')}
          color={filterStatus === 'new' ? 'primary' : 'default'}
        />
        <Chip
          label="Modified"
          onClick={() => setFilterStatus('modified')}
          color={filterStatus === 'modified' ? 'primary' : 'default'}
        />
        <Chip
          label="Synced"
          onClick={() => setFilterStatus('synced')}
          color={filterStatus === 'synced' ? 'primary' : 'default'}
        />
      </Box>

      {/* Items List */}
      <Paper>
        <List>
          <ListItem>
            <ListItemIcon>
              <Checkbox
                checked={selectedItems.length === projectItems.length && projectItems.length > 0}
                indeterminate={selectedItems.length > 0 && selectedItems.length < projectItems.length}
                onChange={handleSelectAll}
              />
            </ListItemIcon>
            <ListItemText
              primary="Select All"
              secondary={`${selectedItems.length} selected`}
            />
            {selectedItems.length > 0 && (
              <Button
                size="small"
                variant="contained"
                startIcon={<CloudUpload />}
                onClick={syncSelectedItems}
                disabled={syncing}
              >
                Sync Selected
              </Button>
            )}
          </ListItem>
          
          <Divider />
          
          {filteredItems.map((item) => (
            <ListItem key={item.id} button onClick={() => handleSelectItem(item.id)}>
              <ListItemIcon>
                <Checkbox
                  checked={selectedItems.includes(item.id)}
                  onChange={() => handleSelectItem(item.id)}
                />
              </ListItemIcon>
              <ListItemIcon>
                <VideoLibrary />
              </ListItemIcon>
              <ListItemText
                primary={item.name}
                secondary={item.path}
              />
              <ListItemSecondaryAction>
                {getStatusIcon(item.status)}
                <Chip
                  label={item.status || 'new'}
                  size="small"
                  color={getStatusColor(item.status) as any}
                  sx={{ ml: 1 }}
                />
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      </Paper>

      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Box>
  );
};

export default ProjectSync;