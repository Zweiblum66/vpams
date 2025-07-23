import React, { useEffect, useState, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  CircularProgress,
} from '@mui/material';
import { useAuthContext } from './AuthProvider';
import { shouldRefreshToken } from '../utils/tokenInterceptor';

interface SessionTimeoutProps {
  warningTime?: number; // Minutes before expiration to show warning
  sessionTimeout?: number; // Minutes of inactivity before logout
}

const SessionTimeout: React.FC<SessionTimeoutProps> = ({
  warningTime = 5,
  sessionTimeout = 30,
}) => {
  const { token, isAuthenticated, logout, refreshToken } = useAuthContext();
  const [showWarning, setShowWarning] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastActivity, setLastActivity] = useState(Date.now());

  // Activity tracking
  const updateActivity = useCallback(() => {
    setLastActivity(Date.now());
  }, []);

  // Set up activity listeners
  useEffect(() => {
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    
    events.forEach(event => {
      document.addEventListener(event, updateActivity, true);
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, updateActivity, true);
      });
    };
  }, [updateActivity]);

  // Check for session timeout and token expiration
  useEffect(() => {
    if (!isAuthenticated || !token) return;

    const checkSession = () => {
      const now = Date.now();
      const timeSinceActivity = now - lastActivity;
      const sessionTimeoutMs = sessionTimeout * 60 * 1000;

      // Check for inactivity timeout
      if (timeSinceActivity >= sessionTimeoutMs) {
        logout();
        return;
      }

      // Check if token needs refresh
      if (shouldRefreshToken(token, warningTime)) {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const expirationTime = payload.exp * 1000;
        const timeUntilExpiry = expirationTime - now;

        if (timeUntilExpiry > 0) {
          setTimeLeft(Math.ceil(timeUntilExpiry / 1000));
          setShowWarning(true);
        } else {
          // Token already expired, try to refresh
          handleRefreshToken();
        }
      }
    };

    const interval = setInterval(checkSession, 30000); // Check every 30 seconds
    
    return () => clearInterval(interval);
  }, [isAuthenticated, token, lastActivity, sessionTimeout, warningTime, logout]);

  // Update countdown timer
  useEffect(() => {
    if (!showWarning) return;

    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          setShowWarning(false);
          handleRefreshToken();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [showWarning]);

  const handleRefreshToken = async () => {
    setIsRefreshing(true);
    try {
      const success = await refreshToken();
      if (success) {
        setShowWarning(false);
        setLastActivity(Date.now());
      } else {
        logout();
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleStaySignedIn = () => {
    handleRefreshToken();
  };

  const handleSignOut = () => {
    setShowWarning(false);
    logout();
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!isAuthenticated) return null;

  return (
    <Dialog
      open={showWarning}
      onClose={() => {}} // Prevent closing by clicking outside
      disableEscapeKeyDown
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Typography variant="h6">Session Timeout Warning</Typography>
          {isRefreshing && <CircularProgress size={20} />}
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Typography variant="body1" gutterBottom>
          Your session will expire in{' '}
          <Typography component="span" color="error" fontWeight="bold">
            {formatTime(timeLeft)}
          </Typography>
        </Typography>
        
        <Typography variant="body2" color="text.secondary">
          Would you like to extend your session?
        </Typography>
      </DialogContent>
      
      <DialogActions>
        <Button
          onClick={handleSignOut}
          color="secondary"
          disabled={isRefreshing}
        >
          Sign Out
        </Button>
        <Button
          onClick={handleStaySignedIn}
          color="primary"
          variant="contained"
          disabled={isRefreshing}
        >
          {isRefreshing ? 'Refreshing...' : 'Stay Signed In'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SessionTimeout;