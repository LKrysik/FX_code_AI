'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Paper,
  Avatar,
  Grid,
  Link,
} from '@mui/material';
import { LockOutlined } from '@mui/icons-material';
import { useAuthStore } from '@/stores';

interface LoginFormProps {
  onSuccess?: () => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    login,
    isLoading,
    error,
    clearError,
    isAuthenticated,
  } = useAuthStore();

  // Clear error when component mounts or when inputs change
  useEffect(() => {
    if (error) {
      clearError();
    }
  }, [username, password]);

  // Handle successful login
  useEffect(() => {
    if (isAuthenticated && onSuccess) {
      onSuccess();
    }
  }, [isAuthenticated, onSuccess]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!username.trim() || !password.trim()) {
      return;
    }

    setIsSubmitting(true);
    try {
      const success = await login(username.trim(), password.trim());
      if (success && onSuccess) {
        onSuccess();
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemoLogin = async (userType: 'demo' | 'trader' | 'premium' | 'admin') => {
    const credentials = {
      demo: { username: 'demo', password: 'demo123' },
      trader: { username: 'trader', password: 'trader123' },
      premium: { username: 'premium', password: 'premium123' },
      admin: { username: 'admin', password: 'admin123' },
    };

    const { username: demoUsername, password: demoPassword } = credentials[userType];
    setUsername(demoUsername);
    setPassword(demoPassword);

    setIsSubmitting(true);
    try {
      const success = await login(demoUsername, demoPassword);
      if (success && onSuccess) {
        onSuccess();
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        p: 2,
      }}
    >
      <Card
        sx={{
          maxWidth: 400,
          width: '100%',
          boxShadow: 3,
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              mb: 3,
            }}
          >
            <Avatar sx={{ m: 1, bgcolor: 'primary.main' }}>
              <LockOutlined />
            </Avatar>
            <Typography component="h1" variant="h5" fontWeight="bold">
              Sign In
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Access the Crypto Trading Dashboard
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%' }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="username"
              label="Username"
              name="username"
              autoComplete="username"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isLoading || isSubmitting}
              sx={{ mb: 2 }}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type="password"
              id="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading || isSubmitting}
              sx={{ mb: 3 }}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              disabled={isLoading || isSubmitting || !username.trim() || !password.trim()}
              sx={{
                mt: 1,
                mb: 2,
                height: 48,
                fontSize: '1.1rem',
                fontWeight: 'bold',
              }}
            >
              {isLoading || isSubmitting ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                'Sign In'
              )}
            </Button>
          </Box>

          {/* Demo Login Buttons */}
          <Typography variant="h6" sx={{ mt: 3, mb: 2, textAlign: 'center' }}>
            Demo Accounts
          </Typography>
          <Grid container spacing={1}>
            <Grid item xs={6}>
              <Button
                fullWidth
                variant="outlined"
                size="small"
                onClick={() => handleDemoLogin('demo')}
                disabled={isLoading || isSubmitting}
              >
                Demo User
              </Button>
            </Grid>
            <Grid item xs={6}>
              <Button
                fullWidth
                variant="outlined"
                size="small"
                onClick={() => handleDemoLogin('trader')}
                disabled={isLoading || isSubmitting}
              >
                Trader
              </Button>
            </Grid>
            <Grid item xs={6}>
              <Button
                fullWidth
                variant="outlined"
                size="small"
                onClick={() => handleDemoLogin('premium')}
                disabled={isLoading || isSubmitting}
              >
                Premium
              </Button>
            </Grid>
            <Grid item xs={6}>
              <Button
                fullWidth
                variant="outlined"
                size="small"
                onClick={() => handleDemoLogin('admin')}
                disabled={isLoading || isSubmitting}
              >
                Admin
              </Button>
            </Grid>
          </Grid>

          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Demo credentials are available for testing purposes
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};