'use client';

import React from 'react';
import { Snackbar, Alert } from '@mui/material';
import { useNotifications, useUIActions } from '@/stores/uiStore';

export default function NotificationProvider() {
  const notifications = useNotifications();
  const { removeNotification } = useUIActions();

  return (
    <>
      {notifications.map((notification) => (
        <Snackbar
          key={notification.id}
          open={true}
          autoHideDuration={notification.autoHide ? 5000 : null}
          onClose={() => removeNotification(notification.id)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <Alert
            onClose={() => removeNotification(notification.id)}
            severity={notification.type}
            variant="filled"
            sx={{ width: '100%' }}
          >
            {notification.message}
          </Alert>
        </Snackbar>
      ))}
    </>
  );
}