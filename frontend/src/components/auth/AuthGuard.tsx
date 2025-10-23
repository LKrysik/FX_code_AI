'use client';

import React, { useEffect, useState } from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';
import { useAuthStore } from '@/stores';
import { LoginForm } from './LoginForm';

interface AuthGuardProps {
  children: React.ReactNode;
  requireAuth?: boolean;
  fallback?: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({
  children,
  requireAuth = true,
  fallback,
}) => {
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const initializeAuth = async () => {
      await checkAuth();
      setIsChecking(false);
    };

    initializeAuth();
  }, [checkAuth]);

  // Show loading spinner while checking authentication
  if (isChecking || isLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
      >
        <CircularProgress size={60} sx={{ mb: 2 }} />
        <Typography variant="h6" color="white">
          Checking authentication...
        </Typography>
      </Box>
    );
  }

  // If authentication is required and user is not authenticated, show login form
  if (requireAuth && !isAuthenticated) {
    return fallback || <LoginForm />;
  }

  // If authentication is not required or user is authenticated, show children
  return <>{children}</>;
};