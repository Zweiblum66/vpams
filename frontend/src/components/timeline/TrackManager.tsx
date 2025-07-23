import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  ListItemIcon,
  Divider,
  Chip,
  ColorLens,
  Slider,
  Stack,
  Alert,
  Menu,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Card,
  CardContent,
  Grid,
} from '@mui/material';
import {
  Add,
  Delete,
  Edit,
  DragIndicator,
  Visibility,
  VisibilityOff,
  Lock,
  LockOpen,
  VolumeUp,
  VolumeOff,
  Movie,
  AudioFile,
  Image,
  Description,
  Settings,
  ExpandMore,
  ContentCopy,
  Group,
  Layers,
  Timeline,
  Speed,
  Equalizer,
  Brightness6,
  Contrast,
  Palette,
  FilterVintage,
  ColorizeSharp,
  Tune,
  MoreVert,
} from '@mui/icons-material';
import { DragDropContext, Droppable, Draggable, DropResult } from 'react-beautiful-dnd';
import { TimelineTrack, TimelineClip, TrackEffect, TrackGroup } from '../../types';

interface TrackManagerProps {
  tracks: TimelineTrack[];
  trackGroups?: TrackGroup[];
  onTrackAdd: (track: Partial<TimelineTrack>) => void;
  onTrackUpdate: (trackId: string, updates: Partial<TimelineTrack>) => void;
  onTrackDelete: (trackId: string) => void;
  onTrackReorder: (trackId: string, newOrder: number) => void;
  onTrackGroupCreate: (group: Partial<TrackGroup>) => void;
  onTrackGroupUpdate: (groupId: string, updates: Partial<TrackGroup>) => void;
  onTrackGroupDelete: (groupId: string) => void;
  readOnly?: boolean;
}

const TRACK_TYPES = [
  { value: 'video', label: 'Video', icon: Movie, color: '#2196f3' },
  { value: 'audio', label: 'Audio', icon: AudioFile, color: '#ff9800' },
  { value: 'subtitle', label: 'Subtitle', icon: Description, color: '#4caf50' },
  { value: 'graphics', label: 'Graphics', icon: Image, color: '#9c27b0' },
];

const TRACK_COLORS = [
  '#2196f3', '#4caf50', '#ff9800', '#f44336', '#9c27b0',
  '#00bcd4', '#8bc34a', '#ffc107', '#795548', '#607d8b',
  '#e91e63', '#673ab7', '#3f51b5', '#03a9f4', '#009688',
];

const TrackManager: React.FC<TrackManagerProps> = ({
  tracks,
  trackGroups = [],
  onTrackAdd,
  onTrackUpdate,
  onTrackDelete,
  onTrackReorder,
  onTrackGroupCreate,
  onTrackGroupUpdate,
  onTrackGroupDelete,
  readOnly = false,
}) => {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showGroupDialog, setShowGroupDialog] = useState(false);
  const [editingTrack, setEditingTrack] = useState<TimelineTrack | null>(null);
  const [editingGroup, setEditingGroup] = useState<TrackGroup | null>(null);
  const [contextMenu, setContextMenu] = useState<{
    mouseX: number;
    mouseY: number;
    trackId?: string;
    groupId?: string;
  } | null>(null);

  const [newTrack, setNewTrack] = useState({
    name: '',
    type: 'video' as const,
    color: TRACK_COLORS[0],
    height: 80,
    visible: true,
    locked: false,
    muted: false,
    solo: false,
    groupId: '',
  });

  const [newGroup, setNewGroup] = useState({
    name: '',
    color: TRACK_COLORS[0],
    collapsed: false,
    muted: false,
    solo: false,
  });

  // Group tracks by their group assignment
  const groupedTracks = useMemo(() => {
    const ungroupedTracks = tracks.filter(track => !track.groupId);
    const grouped = trackGroups.map(group => ({
      ...group,
      tracks: tracks.filter(track => track.groupId === group.id),
    }));
    
    return { ungroupedTracks, grouped };
  }, [tracks, trackGroups]);

  const handleAddTrack = useCallback(() => {
    const trackTypeConfig = TRACK_TYPES.find(t => t.value === newTrack.type);
    const maxOrder = Math.max(...tracks.map(t => t.order), 0);
    
    onTrackAdd({
      ...newTrack,
      order: maxOrder + 1,
      clips: [],
      height: trackTypeConfig ? 
        (trackTypeConfig.value === 'video' ? 80 : 
         trackTypeConfig.value === 'audio' ? 40 : 
         trackTypeConfig.value === 'subtitle' ? 30 : 60) : 80,
    });
    
    setShowAddDialog(false);
    setNewTrack({
      name: '',
      type: 'video',
      color: TRACK_COLORS[0],
      height: 80,
      visible: true,
      locked: false,
      muted: false,
      solo: false,
      groupId: '',
    });
  }, [newTrack, tracks, onTrackAdd]);

  const handleUpdateTrack = useCallback(() => {
    if (!editingTrack) return;
    
    onTrackUpdate(editingTrack.id, {
      name: editingTrack.name,
      color: editingTrack.color,
      height: editingTrack.height,
      visible: editingTrack.visible,
      locked: editingTrack.locked,
      muted: editingTrack.muted,
      solo: editingTrack.solo,
      groupId: editingTrack.groupId,
    });
    
    setShowEditDialog(false);
    setEditingTrack(null);
  }, [editingTrack, onTrackUpdate]);

  const handleDeleteTrack = useCallback((trackId: string) => {
    onTrackDelete(trackId);
    setContextMenu(null);
  }, [onTrackDelete]);

  const handleDuplicateTrack = useCallback((track: TimelineTrack) => {
    const maxOrder = Math.max(...tracks.map(t => t.order), 0);
    
    onTrackAdd({
      ...track,
      id: undefined,
      name: `${track.name} Copy`,
      order: maxOrder + 1,
      clips: [], // Don't duplicate clips
    });
    
    setContextMenu(null);
  }, [tracks, onTrackAdd]);

  const handleDragEnd = useCallback((result: DropResult) => {
    if (!result.destination) return;
    
    const sourceIndex = result.source.index;
    const destinationIndex = result.destination.index;
    
    if (sourceIndex === destinationIndex) return;
    
    const trackId = result.draggableId;
    onTrackReorder(trackId, destinationIndex);
  }, [onTrackReorder]);

  const handleContextMenu = useCallback((
    event: React.MouseEvent, 
    trackId?: string, 
    groupId?: string
  ) => {
    event.preventDefault();
    setContextMenu({
      mouseX: event.clientX - 2,
      mouseY: event.clientY - 4,
      trackId,
      groupId,
    });
  }, []);

  const handleContextMenuClose = useCallback(() => {
    setContextMenu(null);
  }, []);

  const handleCreateGroup = useCallback(() => {
    onTrackGroupCreate({
      ...newGroup,
      tracks: [],
    });
    
    setShowGroupDialog(false);
    setNewGroup({
      name: '',
      color: TRACK_COLORS[0],
      collapsed: false,
      muted: false,
      solo: false,
    });
  }, [newGroup, onTrackGroupCreate]);

  const getTrackIcon = (type: string) => {
    const trackType = TRACK_TYPES.find(t => t.value === type);
    return trackType ? trackType.icon : Movie;
  };

  const renderTrackItem = (track: TimelineTrack, index: number) => (
    <Draggable key={track.id} draggableId={track.id} index={index} isDragDisabled={readOnly}>
      {(provided, snapshot) => (
        <Card
          ref={provided.innerRef}
          {...provided.draggableProps}
          sx={{
            mb: 1,
            opacity: snapshot.isDragging ? 0.8 : 1,
            border: `2px solid ${track.color}`,
            borderLeft: `8px solid ${track.color}`,
          }}
        >
          <CardContent sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {!readOnly && (
                <Box {...provided.dragHandleProps}>
                  <DragIndicator sx={{ color: 'text.secondary' }} />
                </Box>
              )}
              
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {React.createElement(getTrackIcon(track.type), {
                  sx: { color: track.color }
                })}
                <Typography variant="subtitle1" sx={{ fontWeight: 'medium' }}>
                  {track.name}
                </Typography>
                <Chip
                  label={track.type}
                  size="small"
                  variant="outlined"
                  sx={{ textTransform: 'capitalize' }}
                />
              </Box>
              
              <Box sx={{ flex: 1 }} />
              
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  {track.clips.length} clips
                </Typography>
                
                <Tooltip title={track.visible ? 'Hide' : 'Show'}>
                  <IconButton
                    size="small"
                    onClick={() => onTrackUpdate(track.id, { visible: !track.visible })}
                    disabled={readOnly}
                  >
                    {track.visible ? <Visibility /> : <VisibilityOff />}
                  </IconButton>
                </Tooltip>
                
                <Tooltip title={track.locked ? 'Unlock' : 'Lock'}>
                  <IconButton
                    size="small"
                    onClick={() => onTrackUpdate(track.id, { locked: !track.locked })}
                    disabled={readOnly}
                  >
                    {track.locked ? <Lock /> : <LockOpen />}
                  </IconButton>
                </Tooltip>
                
                {track.type === 'audio' && (
                  <Tooltip title={track.muted ? 'Unmute' : 'Mute'}>
                    <IconButton
                      size="small"
                      onClick={() => onTrackUpdate(track.id, { muted: !track.muted })}
                      disabled={readOnly}
                    >
                      {track.muted ? <VolumeOff /> : <VolumeUp />}
                    </IconButton>
                  </Tooltip>
                )}
                
                {!readOnly && (
                  <IconButton
                    size="small"
                    onClick={(e) => handleContextMenu(e, track.id)}
                  >
                    <MoreVert />
                  </IconButton>
                )}
              </Box>
            </Box>
            
            {/* Track details */}
            <Box sx={{ mt: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Chip
                label={`Height: ${track.height}px`}
                size="small"
                variant="outlined"
              />
              <Chip
                label={`Order: ${track.order}`}
                size="small"
                variant="outlined"
              />
              {track.groupId && (
                <Chip
                  label={`Group: ${trackGroups.find(g => g.id === track.groupId)?.name || 'Unknown'}`}
                  size="small"
                  variant="outlined"
                  color="secondary"
                />
              )}
            </Box>
          </CardContent>
        </Card>
      )}
    </Draggable>
  );

  const renderGroupItem = (group: TrackGroup & { tracks: TimelineTrack[] }) => (
    <Accordion key={group.id} defaultExpanded={!group.collapsed}>
      <AccordionSummary
        expandIcon={<ExpandMore />}
        sx={{
          backgroundColor: group.color,
          color: 'white',
          '&:hover': { backgroundColor: `${group.color}dd` },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1 }}>
          <Group />
          <Typography variant="subtitle1" sx={{ fontWeight: 'medium' }}>
            {group.name}
          </Typography>
          <Chip
            label={`${group.tracks.length} tracks`}
            size="small"
            sx={{ backgroundColor: 'rgba(255, 255, 255, 0.2)' }}
          />
          
          <Box sx={{ flex: 1 }} />
          
          {!readOnly && (
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                handleContextMenu(e, undefined, group.id);
              }}
              sx={{ color: 'white' }}
            >
              <MoreVert />
            </IconButton>
          )}
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        <DragDropContext onDragEnd={handleDragEnd}>
          <Droppable droppableId={`group-${group.id}`}>
            {(provided) => (
              <Box {...provided.droppableProps} ref={provided.innerRef}>
                {group.tracks.map((track, index) => renderTrackItem(track, index))}
                {provided.placeholder}
              </Box>
            )}
          </Droppable>
        </DragDropContext>
      </AccordionDetails>
    </Accordion>
  );

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Track Manager</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {!readOnly && (
              <>
                <Button
                  variant="outlined"
                  startIcon={<Group />}
                  onClick={() => setShowGroupDialog(true)}
                >
                  Create Group
                </Button>
                <Button
                  variant="contained"
                  startIcon={<Add />}
                  onClick={() => setShowAddDialog(true)}
                >
                  Add Track
                </Button>
              </>
            )}
          </Box>
        </Box>
      </Paper>

      {/* Track List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {/* Track Groups */}
        {groupedTracks.grouped.map(group => renderGroupItem(group))}
        
        {/* Ungrouped Tracks */}
        {groupedTracks.ungroupedTracks.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
              Ungrouped Tracks
            </Typography>
            <DragDropContext onDragEnd={handleDragEnd}>
              <Droppable droppableId="ungrouped">
                {(provided) => (
                  <Box {...provided.droppableProps} ref={provided.innerRef}>
                    {groupedTracks.ungroupedTracks.map((track, index) => 
                      renderTrackItem(track, index)
                    )}
                    {provided.placeholder}
                  </Box>
                )}
              </Droppable>
            </DragDropContext>
          </Box>
        )}
      </Box>

      {/* Add Track Dialog */}
      <Dialog open={showAddDialog} onClose={() => setShowAddDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add New Track</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Track Name"
                value={newTrack.name}
                onChange={(e) => setNewTrack({ ...newTrack, name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Track Type</InputLabel>
                <Select
                  value={newTrack.type}
                  onChange={(e) => setNewTrack({ ...newTrack, type: e.target.value as any })}
                  label="Track Type"
                >
                  {TRACK_TYPES.map(type => (
                    <MenuItem key={type.value} value={type.value}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <type.icon sx={{ color: type.color }} />
                        {type.label}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Group</InputLabel>
                <Select
                  value={newTrack.groupId}
                  onChange={(e) => setNewTrack({ ...newTrack, groupId: e.target.value })}
                  label="Group"
                >
                  <MenuItem value="">None</MenuItem>
                  {trackGroups.map(group => (
                    <MenuItem key={group.id} value={group.id}>
                      {group.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>Track Color</Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {TRACK_COLORS.map(color => (
                  <Box
                    key={color}
                    sx={{
                      width: 24,
                      height: 24,
                      backgroundColor: color,
                      border: newTrack.color === color ? '2px solid #000' : '1px solid #ccc',
                      cursor: 'pointer',
                      borderRadius: '50%',
                    }}
                    onClick={() => setNewTrack({ ...newTrack, color })}
                  />
                ))}
              </Box>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAddDialog(false)}>Cancel</Button>
          <Button onClick={handleAddTrack} variant="contained" disabled={!newTrack.name}>
            Add Track
          </Button>
        </DialogActions>
      </Dialog>

      {/* Create Group Dialog */}
      <Dialog open={showGroupDialog} onClose={() => setShowGroupDialog(false)}>
        <DialogTitle>Create Track Group</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              fullWidth
              label="Group Name"
              value={newGroup.name}
              onChange={(e) => setNewGroup({ ...newGroup, name: e.target.value })}
            />
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>Group Color</Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {TRACK_COLORS.map(color => (
                  <Box
                    key={color}
                    sx={{
                      width: 24,
                      height: 24,
                      backgroundColor: color,
                      border: newGroup.color === color ? '2px solid #000' : '1px solid #ccc',
                      cursor: 'pointer',
                      borderRadius: '50%',
                    }}
                    onClick={() => setNewGroup({ ...newGroup, color })}
                  />
                ))}
              </Box>
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowGroupDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateGroup} variant="contained" disabled={!newGroup.name}>
            Create Group
          </Button>
        </DialogActions>
      </Dialog>

      {/* Context Menu */}
      <Menu
        open={contextMenu !== null}
        onClose={handleContextMenuClose}
        anchorReference="anchorPosition"
        anchorPosition={
          contextMenu !== null
            ? { top: contextMenu.mouseY, left: contextMenu.mouseX }
            : undefined
        }
      >
        {contextMenu?.trackId && [
          <MenuItem key="edit" onClick={() => {
            const track = tracks.find(t => t.id === contextMenu.trackId);
            if (track) {
              setEditingTrack(track);
              setShowEditDialog(true);
            }
            handleContextMenuClose();
          }}>
            <Edit sx={{ mr: 1 }} />
            Edit Track
          </MenuItem>,
          <MenuItem key="duplicate" onClick={() => {
            const track = tracks.find(t => t.id === contextMenu.trackId);
            if (track) handleDuplicateTrack(track);
          }}>
            <ContentCopy sx={{ mr: 1 }} />
            Duplicate Track
          </MenuItem>,
          <Divider key="divider" />,
          <MenuItem key="delete" onClick={() => {
            if (contextMenu.trackId) handleDeleteTrack(contextMenu.trackId);
          }} sx={{ color: 'error.main' }}>
            <Delete sx={{ mr: 1 }} />
            Delete Track
          </MenuItem>,
        ]}
      </Menu>
    </Box>
  );
};

export default TrackManager;