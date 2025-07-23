import React from 'react';
import {
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Box,
  Typography,
  Avatar,
  Skeleton,
  Paper,
  Button,
} from '@mui/material';
import {
  Schedule as ScheduleIcon,
  CloudUpload as CloudUploadIcon,
  Folder as FolderIcon,
  Search as SearchIcon,
  People as PeopleIcon,
  PlayArrow as PlayArrowIcon,
  VideoLibrary as VideoLibraryIcon,
} from '@mui/icons-material';

export interface ActivityItem {
  id: string;
  type: 'upload' | 'project' | 'search' | 'user' | 'processing' | 'asset';
  message: string;
  timestamp: string;
  user?: string;
  userId?: string;
  assetId?: string;
  avatar?: string;
}

interface ActivityListProps {
  activities: ActivityItem[];
  isLoading?: boolean;
  maxItems?: number;
  showViewAll?: boolean;
  onViewAll?: () => void;
  onItemClick?: (activity: ActivityItem) => void;
}

const ActivityList: React.FC<ActivityListProps> = ({
  activities,
  isLoading = false,
  maxItems = 5,
  showViewAll = false,
  onViewAll,
  onItemClick,
}) => {
  const getActivityIcon = (type: ActivityItem['type']) => {
    const iconProps = { fontSize: 20 };
    
    switch (type) {
      case 'upload':
        return <CloudUploadIcon color="primary" sx={iconProps} />;
      case 'project':
        return <FolderIcon color="info" sx={iconProps} />;
      case 'search':
        return <SearchIcon color="warning" sx={iconProps} />;
      case 'user':
        return <PeopleIcon color="secondary" sx={iconProps} />;
      case 'processing':
        return <PlayArrowIcon color="success" sx={iconProps} />;
      case 'asset':
        return <VideoLibraryIcon color="primary" sx={iconProps} />;
      default:
        return <VideoLibraryIcon color="primary" sx={iconProps} />;
    }
  };

  const getActivityColor = (type: ActivityItem['type']): string => {
    switch (type) {
      case 'upload':
        return 'primary.main';
      case 'project':
        return 'info.main';
      case 'search':
        return 'warning.main';
      case 'user':
        return 'secondary.main';
      case 'processing':
        return 'success.main';
      case 'asset':
        return 'primary.main';
      default:
        return 'primary.main';
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    // Simple timestamp formatting - in a real app, use a proper date library
    return timestamp;
  };

  const displayedActivities = activities.slice(0, maxItems);

  if (isLoading) {
    return (
      <Box>
        {Array.from({ length: 3 }).map((_, index) => (
          <Box key={index} sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
              <Skeleton variant="circular" width={40} height={40} sx={{ mr: 2 }} />
              <Box sx={{ flex: 1 }}>
                <Skeleton variant="text" width="80%" height={24} />
                <Skeleton variant="text" width="40%" height={20} />
              </Box>
            </Box>
            {index < 2 && <Divider sx={{ mt: 2 }} />}
          </Box>
        ))}
      </Box>
    );
  }

  if (activities.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body2" color="text.secondary">
          No recent activity
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <List sx={{ py: 0 }}>
        {displayedActivities.map((activity, index) => (
          <React.Fragment key={activity.id}>
            <ListItem 
              alignItems="flex-start" 
              sx={{ 
                px: 0,
                cursor: onItemClick ? 'pointer' : 'default',
                '&:hover': onItemClick ? {
                  backgroundColor: 'action.hover',
                  borderRadius: 1,
                } : {},
                borderRadius: 1,
                mb: 0.5,
              }}
              onClick={() => onItemClick?.(activity)}
            >
              <ListItemIcon sx={{ minWidth: 48, mt: 0.5 }}>
                {activity.avatar ? (
                  <Avatar
                    src={activity.avatar}
                    alt={activity.user}
                    sx={{ width: 32, height: 32 }}
                  >
                    {activity.user?.[0]?.toUpperCase()}
                  </Avatar>
                ) : (
                  <Box
                    sx={{
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                      backgroundColor: getActivityColor(activity.type),
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'white',
                    }}
                  >
                    {getActivityIcon(activity.type)}
                  </Box>
                )}
              </ListItemIcon>
              
              <ListItemText
                primary={
                  <Typography variant="body2" sx={{ fontWeight: 500, mb: 0.5 }}>
                    {activity.message}
                  </Typography>
                }
                secondary={
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                    <ScheduleIcon sx={{ fontSize: 14, mr: 0.5, color: 'text.secondary' }} />
                    <Typography variant="caption" color="text.secondary">
                      {formatTimestamp(activity.timestamp)}
                      {activity.user && (
                        <>
                          {' • by '}
                          <Typography 
                            component="span" 
                            variant="caption" 
                            sx={{ fontWeight: 500 }}
                          >
                            {activity.user}
                          </Typography>
                        </>
                      )}
                    </Typography>
                  </Box>
                }
              />
            </ListItem>
            {index < displayedActivities.length - 1 && (
              <Divider sx={{ my: 1 }} />
            )}
          </React.Fragment>
        ))}
      </List>
      
      {showViewAll && onViewAll && activities.length > maxItems && (
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Button 
            size="small" 
            onClick={onViewAll}
            sx={{ textTransform: 'none' }}
          >
            View All Activities
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default ActivityList;