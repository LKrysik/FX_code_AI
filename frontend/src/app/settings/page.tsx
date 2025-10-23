'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  Snackbar,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Security as SecurityIcon,
  Notifications as NotificationsIcon,
  Storage as StorageIcon,
  Api as ApiIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';

interface Settings {
  api: {
    baseUrl: string;
    timeout: number;
    retryAttempts: number;
  };
  trading: {
    defaultSymbols: string[];
    maxConcurrentPositions: number;
    defaultBudget: number;
    riskManagement: boolean;
  };
  notifications: {
    emailEnabled: boolean;
    emailAddress: string;
    telegramEnabled: boolean;
    telegramToken: string;
    alertOnTrades: boolean;
    alertOnErrors: boolean;
  };
  display: {
    theme: 'light' | 'dark' | 'auto';
    language: string;
    timezone: string;
    dateFormat: string;
  };
  performance: {
    enableCaching: boolean;
    cacheTimeout: number;
    enableCompression: boolean;
    maxConnections: number;
  };
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({
    api: {
      baseUrl: 'http://localhost:8000',
      timeout: 30,
      retryAttempts: 3
    },
    trading: {
      defaultSymbols: ['BTC_USDT', 'ETH_USDT'],
      maxConcurrentPositions: 5,
      defaultBudget: 1000,
      riskManagement: true
    },
    notifications: {
      emailEnabled: false,
      emailAddress: '',
      telegramEnabled: false,
      telegramToken: '',
      alertOnTrades: true,
      alertOnErrors: true
    },
    display: {
      theme: 'light',
      language: 'en',
      timezone: 'UTC',
      dateFormat: 'YYYY-MM-DD'
    },
    performance: {
      enableCaching: true,
      cacheTimeout: 300,
      enableCompression: true,
      maxConnections: 10
    }
  });

  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info'}>({
    open: false,
    message: '',
    severity: 'info'
  });
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      // In a real implementation, this would load from API
      // For now, we use the default settings
      setSnackbar({
        open: true,
        message: 'Settings loaded successfully',
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to load settings',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    setLoading(true);
    try {
      // In a real implementation, this would save to API
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      setSnackbar({
        open: true,
        message: 'Settings saved successfully',
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to save settings',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = (category: keyof Settings, field: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [field]: value
      }
    }));
  };

  const handleSnackbarClose = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Settings
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadSettings}
            disabled={loading}
          >
            Reload
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={saveSettings}
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Settings'}
          </Button>
        </Box>
      </Box>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
          <Tab label="API Configuration" />
          <Tab label="Trading Settings" />
          <Tab label="Notifications" />
          <Tab label="Display" />
          <Tab label="Performance" />
        </Tabs>
      </Paper>

      {/* API Configuration Tab */}
      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <ApiIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Backend API</Typography>
                </Box>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField
                    fullWidth
                    label="API Base URL"
                    value={settings.api.baseUrl}
                    onChange={(e) => updateSetting('api', 'baseUrl', e.target.value)}
                    helperText="Backend API endpoint URL"
                  />

                  <TextField
                    fullWidth
                    label="Request Timeout (seconds)"
                    type="number"
                    value={settings.api.timeout}
                    onChange={(e) => updateSetting('api', 'timeout', parseInt(e.target.value))}
                    helperText="Maximum time to wait for API responses"
                  />

                  <TextField
                    fullWidth
                    label="Retry Attempts"
                    type="number"
                    value={settings.api.retryAttempts}
                    onChange={(e) => updateSetting('api', 'retryAttempts', parseInt(e.target.value))}
                    helperText="Number of retry attempts for failed requests"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Connection Status
                </Typography>

                <Alert severity="success" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    <strong>Backend:</strong> Connected
                    <br />
                    <strong>WebSocket:</strong> Connected
                    <br />
                    <strong>MEXC API:</strong> Ready
                  </Typography>
                </Alert>

                <Button variant="outlined" fullWidth>
                  Test Connection
                </Button>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Trading Settings Tab */}
      {activeTab === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <SecurityIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Trading Parameters</Typography>
                </Box>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField
                    fullWidth
                    label="Default Symbols"
                    value={settings.trading.defaultSymbols.join(', ')}
                    onChange={(e) => updateSetting('trading', 'defaultSymbols', e.target.value.split(', '))}
                    helperText="Comma-separated list of default trading symbols"
                  />

                  <TextField
                    fullWidth
                    label="Max Concurrent Positions"
                    type="number"
                    value={settings.trading.maxConcurrentPositions}
                    onChange={(e) => updateSetting('trading', 'maxConcurrentPositions', parseInt(e.target.value))}
                    helperText="Maximum number of simultaneous positions"
                  />

                  <TextField
                    fullWidth
                    label="Default Budget (USD)"
                    type="number"
                    value={settings.trading.defaultBudget}
                    onChange={(e) => updateSetting('trading', 'defaultBudget', parseFloat(e.target.value))}
                    helperText="Default trading budget per session"
                  />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.trading.riskManagement}
                        onChange={(e) => updateSetting('trading', 'riskManagement', e.target.checked)}
                      />
                    }
                    label="Enable Risk Management"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Risk Management
                </Typography>

                <Alert severity="info">
                  <Typography variant="body2">
                    Risk management features include:
                    <br />• Position size limits
                    <br />• Stop-loss orders
                    <br />• Maximum drawdown protection
                    <br />• Portfolio diversification
                  </Typography>
                </Alert>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Notifications Tab */}
      {activeTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <NotificationsIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Notification Settings</Typography>
                </Box>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.notifications.emailEnabled}
                        onChange={(e) => updateSetting('notifications', 'emailEnabled', e.target.checked)}
                      />
                    }
                    label="Enable Email Notifications"
                  />

                  {settings.notifications.emailEnabled && (
                    <TextField
                      fullWidth
                      label="Email Address"
                      type="email"
                      value={settings.notifications.emailAddress}
                      onChange={(e) => updateSetting('notifications', 'emailAddress', e.target.value)}
                      helperText="Email address for notifications"
                    />
                  )}

                  <Divider sx={{ my: 1 }} />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.notifications.telegramEnabled}
                        onChange={(e) => updateSetting('notifications', 'telegramEnabled', e.target.checked)}
                      />
                    }
                    label="Enable Telegram Notifications"
                  />

                  {settings.notifications.telegramEnabled && (
                    <TextField
                      fullWidth
                      label="Telegram Bot Token"
                      value={settings.notifications.telegramToken}
                      onChange={(e) => updateSetting('notifications', 'telegramToken', e.target.value)}
                      helperText="Telegram bot token for notifications"
                      type="password"
                    />
                  )}

                  <Divider sx={{ my: 1 }} />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.notifications.alertOnTrades}
                        onChange={(e) => updateSetting('notifications', 'alertOnTrades', e.target.checked)}
                      />
                    }
                    label="Alert on Trade Executions"
                  />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.notifications.alertOnErrors}
                        onChange={(e) => updateSetting('notifications', 'alertOnErrors', e.target.checked)}
                      />
                    }
                    label="Alert on System Errors"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Notification Types
                </Typography>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Alert severity="success" variant="outlined" size="small">
                    <Typography variant="body2">✅ Trade executions</Typography>
                  </Alert>
                  <Alert severity="error" variant="outlined" size="small">
                    <Typography variant="body2">❌ System errors</Typography>
                  </Alert>
                  <Alert severity="warning" variant="outlined" size="small">
                    <Typography variant="body2">⚠️ Risk warnings</Typography>
                  </Alert>
                  <Alert severity="info" variant="outlined" size="small">
                    <Typography variant="body2">ℹ️ Session status changes</Typography>
                  </Alert>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Display Tab */}
      {activeTab === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Display Preferences
                </Typography>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <FormControl fullWidth>
                    <InputLabel>Theme</InputLabel>
                    <Select
                      value={settings.display.theme}
                      label="Theme"
                      onChange={(e) => updateSetting('display', 'theme', e.target.value)}
                    >
                      <MenuItem value="light">Light</MenuItem>
                      <MenuItem value="dark">Dark</MenuItem>
                      <MenuItem value="auto">Auto (System)</MenuItem>
                    </Select>
                  </FormControl>

                  <FormControl fullWidth>
                    <InputLabel>Language</InputLabel>
                    <Select
                      value={settings.display.language}
                      label="Language"
                      onChange={(e) => updateSetting('display', 'language', e.target.value)}
                    >
                      <MenuItem value="en">English</MenuItem>
                      <MenuItem value="pl">Polski</MenuItem>
                      <MenuItem value="es">Español</MenuItem>
                    </Select>
                  </FormControl>

                  <FormControl fullWidth>
                    <InputLabel>Timezone</InputLabel>
                    <Select
                      value={settings.display.timezone}
                      label="Timezone"
                      onChange={(e) => updateSetting('display', 'timezone', e.target.value)}
                    >
                      <MenuItem value="UTC">UTC</MenuItem>
                      <MenuItem value="America/New_York">Eastern Time</MenuItem>
                      <MenuItem value="Europe/London">London</MenuItem>
                      <MenuItem value="Asia/Tokyo">Tokyo</MenuItem>
                    </Select>
                  </FormControl>

                  <FormControl fullWidth>
                    <InputLabel>Date Format</InputLabel>
                    <Select
                      value={settings.display.dateFormat}
                      label="Date Format"
                      onChange={(e) => updateSetting('display', 'dateFormat', e.target.value)}
                    >
                      <MenuItem value="YYYY-MM-DD">2024-01-15</MenuItem>
                      <MenuItem value="MM/DD/YYYY">01/15/2024</MenuItem>
                      <MenuItem value="DD/MM/YYYY">15/01/2024</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Interface Customization
                </Typography>

                <Alert severity="info">
                  <Typography variant="body2">
                    Display settings affect:
                    <br />• Chart colors and themes
                    <br />• Date/time formatting
                    <br />• Number formatting
                    <br />• Language of UI elements
                  </Typography>
                </Alert>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Performance Tab */}
      {activeTab === 4 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <StorageIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Performance Settings</Typography>
                </Box>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.performance.enableCaching}
                        onChange={(e) => updateSetting('performance', 'enableCaching', e.target.checked)}
                      />
                    }
                    label="Enable API Response Caching"
                  />

                  {settings.performance.enableCaching && (
                    <TextField
                      fullWidth
                      label="Cache Timeout (seconds)"
                      type="number"
                      value={settings.performance.cacheTimeout}
                      onChange={(e) => updateSetting('performance', 'cacheTimeout', parseInt(e.target.value))}
                      helperText="How long to cache API responses"
                    />
                  )}

                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.performance.enableCompression}
                        onChange={(e) => updateSetting('performance', 'enableCompression', e.target.checked)}
                      />
                    }
                    label="Enable Data Compression"
                  />

                  <TextField
                    fullWidth
                    label="Max Concurrent Connections"
                    type="number"
                    value={settings.performance.maxConnections}
                    onChange={(e) => updateSetting('performance', 'maxConnections', parseInt(e.target.value))}
                    helperText="Maximum concurrent API connections"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  System Performance
                </Typography>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">CPU Usage</Typography>
                    <Typography variant="body2" color="success.main">23%</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Memory Usage</Typography>
                    <Typography variant="body2" color="info.main">156 MB</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Active Connections</Typography>
                    <Typography variant="body2" color="primary.main">3</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Cache Hit Rate</Typography>
                    <Typography variant="body2" color="success.main">87%</Typography>
                  </Box>
                </Box>

                <Divider sx={{ my: 2 }} />

                <Button variant="outlined" fullWidth>
                  Clear Cache
                </Button>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleSnackbarClose}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}