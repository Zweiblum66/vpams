import React, { useEffect } from 'react';
import { Snackbar, Alert, AlertColor } from '@mui/material';
import { useAppDispatch, useAppSelector } from '../store';
import { removeNotification } from '../store/slices/uiSlice';

const NotificationContainer: React.FC = () => {
  const dispatch = useAppDispatch();
  const { notifications } = useAppSelector(state => state.ui);

  useEffect(() => {
    // Auto-remove notifications after their duration
    notifications.forEach(notification => {
      if (notification.duration && notification.duration > 0) {
        setTimeout(() => {
          dispatch(removeNotification(notification.id));
        }, notification.duration);
      }
    });
  }, [notifications, dispatch]);

  const handleClose = (notificationId: string) => {
    dispatch(removeNotification(notificationId));
  };

  return (
    <>
      {notifications.map((notification, index) => (
        <Snackbar
          key={notification.id}
          open={true}
          autoHideDuration={notification.duration || 5000}
          onClose={() => handleClose(notification.id)}
          anchorOrigin={{
            vertical: 'top',
            horizontal: 'right',
          }}
          sx={{
            marginTop: `${index * 60}px`, // Stack notifications
          }}
        >
          <Alert
            onClose={() => handleClose(notification.id)}
            severity={notification.type as AlertColor}
            variant="filled"
            sx={{ width: '100%' }}
          >
            {notification.message}
          </Alert>
        </Snackbar>
      ))}
    </>
  );
};

export default NotificationContainer;