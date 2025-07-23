import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Grid,
  Card,
  CardContent,
  Avatar,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  Checkbox,
  ListItemText,
  OutlinedInput,
  Switch,
  FormControlLabel,
  Pagination,
  Skeleton,
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Person as PersonIcon,
  Email as EmailIcon,
  Phone as PhoneIcon,
  Business as BusinessIcon,
  FilterList as FilterListIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '../store';
import { fetchUsers, deleteUser, activateUser, deactivateUser } from '../store/slices/userSlice';
import { openModal, closeModal, addNotification } from '../store/slices/uiSlice';

const UserManagement: React.FC = () => {
  const dispatch = useAppDispatch();
  const { users, isLoading, pagination, filters } = useAppSelector(state => state.users);
  const { modals } = useAppSelector(state => state.ui);

  const [searchTerm, setSearchTerm] = useState('');
  const [filterAnchor, setFilterAnchor] = useState<null | HTMLElement>(null);
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(null);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<string | null>(null);

  useEffect(() => {
    dispatch(fetchUsers({ 
      page: pagination.page, 
      limit: pagination.limit,
      search: searchTerm || undefined,
      ...filters
    }));
  }, [dispatch, pagination.page, pagination.limit, searchTerm, filters]);

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  };

  const handleRefresh = () => {
    dispatch(fetchUsers({ 
      page: pagination.page, 
      limit: pagination.limit,
      search: searchTerm || undefined,
      ...filters
    }));
  };

  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    dispatch(fetchUsers({ 
      page: value, 
      limit: pagination.limit,
      search: searchTerm || undefined,
      ...filters
    }));
  };

  const handleUserMenuClick = (event: React.MouseEvent<HTMLElement>, userId: string) => {
    setUserMenuAnchor(event.currentTarget);
    setSelectedUserId(userId);
  };

  const handleUserMenuClose = () => {
    setUserMenuAnchor(null);
    setSelectedUserId(null);
  };

  const handleEditUser = () => {
    if (selectedUserId) {
      dispatch(openModal('editUser'));
      handleUserMenuClose();
    }
  };

  const handleDeleteUser = () => {
    if (selectedUserId) {
      setUserToDelete(selectedUserId);
      setDeleteDialogOpen(true);
      handleUserMenuClose();
    }
  };

  const handleConfirmDelete = async () => {
    if (userToDelete) {
      try {
        await dispatch(deleteUser(userToDelete)).unwrap();
        dispatch(addNotification({
          type: 'success',
          message: 'User deleted successfully',
        }));
        setDeleteDialogOpen(false);
        setUserToDelete(null);
      } catch (error) {
        dispatch(addNotification({
          type: 'error',
          message: 'Failed to delete user',
        }));
      }
    }
  };

  const handleToggleUserStatus = async (userId: string, isActive: boolean) => {
    try {
      if (isActive) {
        await dispatch(deactivateUser(userId)).unwrap();
        dispatch(addNotification({
          type: 'success',
          message: 'User deactivated successfully',
        }));
      } else {
        await dispatch(activateUser(userId)).unwrap();
        dispatch(addNotification({
          type: 'success',
          message: 'User activated successfully',
        }));
      }
    } catch (error) {
      dispatch(addNotification({
        type: 'error',
        message: 'Failed to update user status',
      }));
    }
  };

  const renderUserCard = (user: any) => (
    <Card key={user.user_id} sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Avatar
            src={user.avatar_url}
            sx={{ width: 56, height: 56, mr: 2 }}
          >
            {user.display_name?.[0] || user.first_name?.[0] || user.email?.[0]}
          </Avatar>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6" component="div">
              {user.display_name || `${user.first_name} ${user.last_name}`}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {user.email}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
              <Chip
                label={user.is_active ? 'Active' : 'Inactive'}
                color={user.is_active ? 'success' : 'error'}
                size="small"
                sx={{ mr: 1 }}
              />
              {user.is_superuser && (
                <Chip
                  label="Superuser"
                  color="warning"
                  size="small"
                  sx={{ mr: 1 }}
                />
              )}
              {user.is_verified && (
                <Chip
                  label="Verified"
                  color="info"
                  size="small"
                />
              )}
            </Box>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <FormControlLabel
              control={
                <Switch
                  checked={user.is_active}
                  onChange={() => handleToggleUserStatus(user.user_id, user.is_active)}
                  size="small"
                />
              }
              label="Active"
              sx={{ mr: 1 }}
            />
            <IconButton
              onClick={(e) => handleUserMenuClick(e, user.user_id)}
              size="small"
            >
              <MoreVertIcon />
            </IconButton>
          </Box>
        </Box>
        
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <EmailIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
              <Typography variant="body2" color="text.secondary">
                {user.email}
              </Typography>
            </Box>
            {user.phone && (
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <PhoneIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
                <Typography variant="body2" color="text.secondary">
                  {user.phone}
                </Typography>
              </Box>
            )}
            {user.organization && (
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <BusinessIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
                <Typography variant="body2" color="text.secondary">
                  {user.organization}
                </Typography>
              </Box>
            )}
          </Grid>
          <Grid item xs={12} sm={6}>
            <Typography variant="body2" color="text.secondary">
              Created: {new Date(user.created_at).toLocaleDateString()}
            </Typography>
            {user.last_login_at && (
              <Typography variant="body2" color="text.secondary">
                Last login: {new Date(user.last_login_at).toLocaleDateString()}
              </Typography>
            )}
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  const renderSkeleton = () => (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Skeleton variant="circular" width={56} height={56} sx={{ mr: 2 }} />
          <Box sx={{ flexGrow: 1 }}>
            <Skeleton variant="text" width="60%" height={28} />
            <Skeleton variant="text" width="80%" height={20} />
            <Skeleton variant="text" width="40%" height={20} />
          </Box>
        </Box>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <Skeleton variant="text" width="90%" />
            <Skeleton variant="text" width="70%" />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Skeleton variant="text" width="80%" />
            <Skeleton variant="text" width="60%" />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <PersonIcon sx={{ fontSize: 32, mr: 2, color: 'primary.main' }} />
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
          User Management
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => dispatch(openModal('createUser'))}
          sx={{ mr: 1 }}
        >
          Add User
        </Button>
        <IconButton onClick={handleRefresh} disabled={isLoading}>
          <RefreshIcon />
        </IconButton>
      </Box>

      {/* Search and Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              placeholder="Search users..."
              value={searchTerm}
              onChange={handleSearch}
              InputProps={{
                startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />,
              }}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                startIcon={<FilterListIcon />}
                onClick={(e) => setFilterAnchor(e.currentTarget)}
              >
                Filters
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* User List */}
      <Box sx={{ mb: 3 }}>
        {isLoading ? (
          // Loading skeleton
          Array.from({ length: 5 }).map((_, index) => (
            <div key={index}>{renderSkeleton()}</div>
          ))
        ) : users.length === 0 ? (
          // Empty state
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <PersonIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary">
              No users found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {searchTerm ? 'Try adjusting your search terms' : 'Start by adding your first user'}
            </Typography>
          </Paper>
        ) : (
          // User list
          users.map(renderUserCard)
        )}
      </Box>

      {/* Pagination */}
      {pagination.pages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
          <Pagination
            count={pagination.pages}
            page={pagination.page}
            onChange={handlePageChange}
            color="primary"
          />
        </Box>
      )}

      {/* User Menu */}
      <Menu
        anchorEl={userMenuAnchor}
        open={Boolean(userMenuAnchor)}
        onClose={handleUserMenuClose}
      >
        <MenuItem onClick={handleEditUser}>
          <EditIcon sx={{ mr: 1 }} />
          Edit User
        </MenuItem>
        <MenuItem onClick={handleDeleteUser}>
          <DeleteIcon sx={{ mr: 1 }} />
          Delete User
        </MenuItem>
      </Menu>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this user? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleConfirmDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default UserManagement;