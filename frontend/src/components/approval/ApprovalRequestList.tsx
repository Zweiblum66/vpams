import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Chip,
  Stack,
  Pagination,
  LinearProgress,
  Alert,
  Checkbox,
  Menu,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Badge,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
  Container,
} from '@mui/material';
import {
  FilterList,
  Sort,
  Search,
  Refresh,
  MoreVert,
  ViewList,
  ViewModule,
  SelectAll,
  ThumbUp,
  ThumbDown,
  Delete,
  FileDownload,
  Add,
  Clear,
  TrendingUp,
  TrendingDown,
  Schedule,
  Person,
  Business,
  Priority,
  CheckCircle,
  Cancel,
  Warning,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { format } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import {
  useGetApprovalRequestsQuery,
  useBulkApproveRequestsMutation,
  useBulkRejectRequestsMutation,
} from '../../store/api/workflowApi';
import {
  ApprovalRequest,
  ApprovalRequestFilter,
  ApprovalPriority,
  ApprovalStatus,
  ApprovalType,
} from '../../types/workflow';
import ApprovalRequestCard from './ApprovalRequestCard';

interface ApprovalRequestListProps {
  title?: string;
  showFilters?: boolean;
  showBulkActions?: boolean;
  defaultFilters?: ApprovalRequestFilter;
  variant?: 'default' | 'compact' | 'detailed';
  pageSize?: number;
}

const priorityOrder: ApprovalPriority[] = ['urgent', 'high', 'medium', 'low'];
const statusOrder: ApprovalStatus[] = ['pending', 'in_review', 'approved', 'rejected', 'cancelled', 'escalated'];

const ApprovalRequestList: React.FC<ApprovalRequestListProps> = ({
  title = 'Approval Requests',
  showFilters = true,
  showBulkActions = true,
  defaultFilters = {},
  variant = 'default',
  pageSize = 20,
}) => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'created_at' | 'due_date' | 'priority' | 'status'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [selectedRequests, setSelectedRequests] = useState<string[]>([]);
  const [showFiltersDialog, setShowFiltersDialog] = useState(false);
  const [bulkActionMenu, setBulkActionMenu] = useState<null | HTMLElement>(null);
  const [bulkComment, setBulkComment] = useState('');
  const [showBulkDialog, setShowBulkDialog] = useState(false);
  const [bulkAction, setBulkAction] = useState<'approve' | 'reject'>('approve');

  // Filters
  const [filters, setFilters] = useState<ApprovalRequestFilter>({
    ...defaultFilters,
    status: defaultFilters.status || [],
    priority: defaultFilters.priority || [],
    type: defaultFilters.type || [],
  });

  // API hooks
  const { data: approvalRequests, isLoading, error, refetch } = useGetApprovalRequestsQuery({
    page,
    limit: pageSize,
    filters: {
      ...filters,
      // Add search term to filters if needed
    },
  });

  const [bulkApprove, { isLoading: bulkApproveLoading }] = useBulkApproveRequestsMutation();
  const [bulkReject, { isLoading: bulkRejectLoading }] = useBulkRejectRequestsMutation();

  const handlePageChange = useCallback((event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  }, []);

  const handleSearchChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
    setPage(1); // Reset to first page when searching
  }, []);

  const handleSortChange = useCallback((event: SelectChangeEvent<string>) => {
    setSortBy(event.target.value as typeof sortBy);
    setPage(1);
  }, []);

  const handleSortOrderChange = useCallback(() => {
    setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    setPage(1);
  }, []);

  const handleViewModeChange = useCallback((event: React.MouseEvent<HTMLElement>, newViewMode: 'list' | 'grid') => {
    if (newViewMode !== null) {
      setViewMode(newViewMode);
    }
  }, []);

  const handleFilterChange = useCallback((filterKey: keyof ApprovalRequestFilter, value: any) => {
    setFilters(prev => ({
      ...prev,
      [filterKey]: value,
    }));
    setPage(1);
  }, []);

  const handleClearFilters = useCallback(() => {
    setFilters({
      status: [],
      priority: [],
      type: [],
    });
    setSearchTerm('');
    setPage(1);
  }, []);

  const handleSelectRequest = useCallback((requestId: string) => {
    setSelectedRequests(prev => 
      prev.includes(requestId) 
        ? prev.filter(id => id !== requestId)
        : [...prev, requestId]
    );
  }, []);

  const handleSelectAll = useCallback(() => {
    if (selectedRequests.length === approvalRequests?.data.length) {
      setSelectedRequests([]);
    } else {
      setSelectedRequests(approvalRequests?.data.map(req => req.id) || []);
    }
  }, [selectedRequests, approvalRequests]);

  const handleBulkActionClick = useCallback((event: React.MouseEvent<HTMLElement>) => {
    setBulkActionMenu(event.currentTarget);
  }, []);

  const handleBulkActionClose = useCallback(() => {
    setBulkActionMenu(null);
  }, []);

  const handleBulkAction = useCallback(async (action: 'approve' | 'reject') => {
    setBulkAction(action);
    setShowBulkDialog(true);
    handleBulkActionClose();
  }, []);

  const handleConfirmBulkAction = useCallback(async () => {
    try {
      if (bulkAction === 'approve') {
        await bulkApprove({
          request_ids: selectedRequests,
          comment: bulkComment,
        }).unwrap();
      } else {
        await bulkReject({
          request_ids: selectedRequests,
          comment: bulkComment,
        }).unwrap();
      }
      setSelectedRequests([]);
      setBulkComment('');
      setShowBulkDialog(false);
      refetch();
    } catch (error) {
      console.error('Bulk action failed:', error);
    }
  }, [bulkAction, selectedRequests, bulkComment, bulkApprove, bulkReject, refetch]);

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  const handleCreateRequest = useCallback(() => {
    navigate('/approvals/new');
  }, [navigate]);

  // Filter and sort the requests
  const filteredAndSortedRequests = useMemo(() => {
    if (!approvalRequests?.data) return [];

    let filtered = [...approvalRequests.data];

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(req => 
        req.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        req.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        req.requester.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply status filter
    if (filters.status && filters.status.length > 0) {
      filtered = filtered.filter(req => filters.status!.includes(req.status));
    }

    // Apply priority filter
    if (filters.priority && filters.priority.length > 0) {
      filtered = filtered.filter(req => filters.priority!.includes(req.priority));
    }

    // Apply type filter
    if (filters.type && filters.type.length > 0) {
      filtered = filtered.filter(req => filters.type!.includes(req.type));
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue: any, bValue: any;

      switch (sortBy) {
        case 'created_at':
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        case 'due_date':
          aValue = a.due_date ? new Date(a.due_date).getTime() : 0;
          bValue = b.due_date ? new Date(b.due_date).getTime() : 0;
          break;
        case 'priority':
          aValue = priorityOrder.indexOf(a.priority);
          bValue = priorityOrder.indexOf(b.priority);
          break;
        case 'status':
          aValue = statusOrder.indexOf(a.status);
          bValue = statusOrder.indexOf(b.status);
          break;
        default:
          return 0;
      }

      return sortOrder === 'asc' ? aValue - bValue : bValue - aValue;
    });

    return filtered;
  }, [approvalRequests?.data, searchTerm, filters, sortBy, sortOrder]);

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (filters.status && filters.status.length > 0) count++;
    if (filters.priority && filters.priority.length > 0) count++;
    if (filters.type && filters.type.length > 0) count++;
    if (filters.date_range) count++;
    if (searchTerm) count++;
    return count;
  }, [filters, searchTerm]);

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Alert severity="error">
          Failed to load approval requests. Please try again.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          {title}
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleRefresh}
            disabled={isLoading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={handleCreateRequest}
          >
            New Request
          </Button>
        </Box>
      </Box>

      {/* Filters and Controls */}
      {showFilters && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <TextField
              size="small"
              placeholder="Search requests..."
              value={searchTerm}
              onChange={handleSearchChange}
              InputProps={{
                startAdornment: <Search sx={{ mr: 1 }} />,
              }}
              sx={{ minWidth: 200 }}
            />

            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Sort by</InputLabel>
              <Select
                value={sortBy}
                onChange={handleSortChange}
                label="Sort by"
              >
                <MenuItem value="created_at">Created</MenuItem>
                <MenuItem value="due_date">Due Date</MenuItem>
                <MenuItem value="priority">Priority</MenuItem>
                <MenuItem value="status">Status</MenuItem>
              </Select>
            </FormControl>

            <IconButton onClick={handleSortOrderChange}>
              {sortOrder === 'asc' ? <TrendingUp /> : <TrendingDown />}
            </IconButton>

            <Badge badgeContent={activeFiltersCount} color="primary">
              <Button
                variant="outlined"
                startIcon={<FilterList />}
                onClick={() => setShowFiltersDialog(true)}
              >
                Filters
              </Button>
            </Badge>

            {activeFiltersCount > 0 && (
              <Button
                variant="outlined"
                startIcon={<Clear />}
                onClick={handleClearFilters}
              >
                Clear
              </Button>
            )}

            <Box sx={{ flex: 1 }} />

            <ToggleButtonGroup
              value={viewMode}
              exclusive
              onChange={handleViewModeChange}
              size="small"
            >
              <ToggleButton value="list">
                <ViewList />
              </ToggleButton>
              <ToggleButton value="grid">
                <ViewModule />
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>

          {/* Active Filters */}
          {activeFiltersCount > 0 && (
            <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {filters.status?.map(status => (
                <Chip
                  key={status}
                  label={`Status: ${status}`}
                  size="small"
                  onDelete={() => handleFilterChange('status', filters.status?.filter(s => s !== status))}
                />
              ))}
              {filters.priority?.map(priority => (
                <Chip
                  key={priority}
                  label={`Priority: ${priority}`}
                  size="small"
                  onDelete={() => handleFilterChange('priority', filters.priority?.filter(p => p !== priority))}
                />
              ))}
              {filters.type?.map(type => (
                <Chip
                  key={type}
                  label={`Type: ${type}`}
                  size="small"
                  onDelete={() => handleFilterChange('type', filters.type?.filter(t => t !== type))}
                />
              ))}
            </Box>
          )}
        </Paper>
      )}

      {/* Bulk Actions */}
      {showBulkActions && selectedRequests.length > 0 && (
        <Paper sx={{ p: 2, mb: 3, bgcolor: 'action.selected' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body1">
              {selectedRequests.length} item{selectedRequests.length > 1 ? 's' : ''} selected
            </Typography>
            <Button
              variant="outlined"
              startIcon={<ThumbUp />}
              onClick={() => handleBulkAction('approve')}
              disabled={bulkApproveLoading || bulkRejectLoading}
            >
              Bulk Approve
            </Button>
            <Button
              variant="outlined"
              startIcon={<ThumbDown />}
              onClick={() => handleBulkAction('reject')}
              disabled={bulkApproveLoading || bulkRejectLoading}
            >
              Bulk Reject
            </Button>
            <Button
              variant="outlined"
              onClick={() => setSelectedRequests([])}
            >
              Clear Selection
            </Button>
          </Box>
        </Paper>
      )}

      {/* Content */}
      <Paper sx={{ p: 2 }}>
        {/* Selection Header */}
        {showBulkActions && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Checkbox
              checked={selectedRequests.length === approvalRequests?.data.length && approvalRequests?.data.length > 0}
              indeterminate={selectedRequests.length > 0 && selectedRequests.length < (approvalRequests?.data.length || 0)}
              onChange={handleSelectAll}
            />
            <Typography variant="body2">
              Select all
            </Typography>
          </Box>
        )}

        {/* Loading */}
        {isLoading && <LinearProgress sx={{ mb: 2 }} />}

        {/* Results */}
        {filteredAndSortedRequests.length === 0 ? (
          <Alert severity="info">
            No approval requests found matching your criteria.
          </Alert>
        ) : (
          <Box>
            {filteredAndSortedRequests.map((request) => (
              <Box key={request.id} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                {showBulkActions && (
                  <Checkbox
                    checked={selectedRequests.includes(request.id)}
                    onChange={() => handleSelectRequest(request.id)}
                    sx={{ mt: 1 }}
                  />
                )}
                <Box sx={{ flex: 1 }}>
                  <ApprovalRequestCard
                    approval={request}
                    variant={variant}
                    onUpdate={refetch}
                  />
                </Box>
              </Box>
            ))}
          </Box>
        )}

        {/* Pagination */}
        {approvalRequests && approvalRequests.total > pageSize && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
            <Pagination
              count={Math.ceil(approvalRequests.total / pageSize)}
              page={page}
              onChange={handlePageChange}
              color="primary"
            />
          </Box>
        )}
      </Paper>

      {/* Bulk Action Dialog */}
      <Dialog
        open={showBulkDialog}
        onClose={() => setShowBulkDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Bulk {bulkAction === 'approve' ? 'Approve' : 'Reject'} Requests
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Are you sure you want to {bulkAction} {selectedRequests.length} approval request{selectedRequests.length > 1 ? 's' : ''}?
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Comment (optional)"
            value={bulkComment}
            onChange={(e) => setBulkComment(e.target.value)}
            placeholder={`Add a comment for this bulk ${bulkAction}...`}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowBulkDialog(false)}>Cancel</Button>
          <Button
            onClick={handleConfirmBulkAction}
            variant="contained"
            color={bulkAction === 'approve' ? 'success' : 'error'}
            disabled={bulkApproveLoading || bulkRejectLoading}
          >
            {bulkAction === 'approve' ? 'Approve All' : 'Reject All'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Filters Dialog */}
      <Dialog
        open={showFiltersDialog}
        onClose={() => setShowFiltersDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Filter Approval Requests</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 2 }}>
            {/* Status Filter */}
            <FormControl fullWidth>
              <InputLabel>Status</InputLabel>
              <Select
                multiple
                value={filters.status || []}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                label="Status"
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} size="small" />
                    ))}
                  </Box>
                )}
              >
                {statusOrder.map(status => (
                  <MenuItem key={status} value={status}>
                    {status}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Priority Filter */}
            <FormControl fullWidth>
              <InputLabel>Priority</InputLabel>
              <Select
                multiple
                value={filters.priority || []}
                onChange={(e) => handleFilterChange('priority', e.target.value)}
                label="Priority"
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} size="small" />
                    ))}
                  </Box>
                )}
              >
                {priorityOrder.map(priority => (
                  <MenuItem key={priority} value={priority}>
                    {priority}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Type Filter */}
            <FormControl fullWidth>
              <InputLabel>Type</InputLabel>
              <Select
                multiple
                value={filters.type || []}
                onChange={(e) => handleFilterChange('type', e.target.value)}
                label="Type"
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} size="small" />
                    ))}
                  </Box>
                )}
              >
                <MenuItem value="asset_approval">Asset Approval</MenuItem>
                <MenuItem value="project_approval">Project Approval</MenuItem>
                <MenuItem value="timeline_approval">Timeline Approval</MenuItem>
                <MenuItem value="metadata_approval">Metadata Approval</MenuItem>
                <MenuItem value="custom">Custom</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowFiltersDialog(false)}>Cancel</Button>
          <Button onClick={handleClearFilters} variant="outlined">
            Clear All
          </Button>
          <Button onClick={() => setShowFiltersDialog(false)} variant="contained">
            Apply Filters
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ApprovalRequestList;