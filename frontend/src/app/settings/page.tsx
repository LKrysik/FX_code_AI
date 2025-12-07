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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
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
  Keyboard as KeyboardIcon,
  Warning as WarningIcon,
  Edit as EditIcon,
  Restore as RestoreIcon,
  Person as PersonIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  Upload as UploadIcon,
  Backup as BackupIcon,
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
    // ST-01: Default SL/TP settings
    defaultStopLoss: number;
    defaultTakeProfit: number;
    defaultLeverage: number;
    slTpMode: 'percentage' | 'fixed';
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
  // ST-02: Keyboard shortcuts
  shortcuts: {
    emergencyStop: string;
    closePosition: string;
    goToDashboard: string;
    goToTrading: string;
    goToHistory: string;
    zoomIn: string;
    zoomOut: string;
    fullscreen: string;
    shortcutsEnabled: boolean;
  };
}

// ST-03: Trading Profiles
interface TradingProfile {
  id: string;
  name: string;
  description: string;
  style: 'aggressive' | 'moderate' | 'conservative' | 'scalping' | 'custom';
  settings: {
    defaultStopLoss: number;
    defaultTakeProfit: number;
    defaultLeverage: number;
    maxConcurrentPositions: number;
    defaultBudget: number;
  };
  createdAt: string;
  isDefault: boolean;
}

const DEFAULT_PROFILES: TradingProfile[] = [
  {
    id: 'aggressive',
    name: 'Aggressive Trader',
    description: 'High risk, high reward. Suitable for experienced traders.',
    style: 'aggressive',
    settings: {
      defaultStopLoss: 5.0,
      defaultTakeProfit: 15.0,
      defaultLeverage: 20,
      maxConcurrentPositions: 10,
      defaultBudget: 5000,
    },
    createdAt: new Date().toISOString(),
    isDefault: false,
  },
  {
    id: 'moderate',
    name: 'Moderate Trader',
    description: 'Balanced risk/reward. Good for most traders.',
    style: 'moderate',
    settings: {
      defaultStopLoss: 2.0,
      defaultTakeProfit: 6.0,
      defaultLeverage: 5,
      maxConcurrentPositions: 5,
      defaultBudget: 1000,
    },
    createdAt: new Date().toISOString(),
    isDefault: true,
  },
  {
    id: 'conservative',
    name: 'Conservative Trader',
    description: 'Low risk, steady gains. Best for beginners.',
    style: 'conservative',
    settings: {
      defaultStopLoss: 1.0,
      defaultTakeProfit: 3.0,
      defaultLeverage: 2,
      maxConcurrentPositions: 3,
      defaultBudget: 500,
    },
    createdAt: new Date().toISOString(),
    isDefault: false,
  },
  {
    id: 'scalping',
    name: 'Scalper',
    description: 'Quick trades, small profits. Requires active monitoring.',
    style: 'scalping',
    settings: {
      defaultStopLoss: 0.5,
      defaultTakeProfit: 1.0,
      defaultLeverage: 10,
      maxConcurrentPositions: 1,
      defaultBudget: 2000,
    },
    createdAt: new Date().toISOString(),
    isDefault: false,
  },
];

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
      riskManagement: true,
      // ST-01: Default SL/TP settings
      defaultStopLoss: 2.0,
      defaultTakeProfit: 4.0,
      defaultLeverage: 5,
      slTpMode: 'percentage',
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
    },
    // ST-02: Keyboard shortcuts with defaults
    shortcuts: {
      emergencyStop: 'Escape',
      closePosition: 'c',
      goToDashboard: 'd',
      goToTrading: 't',
      goToHistory: 's',
      zoomIn: '+',
      zoomOut: '-',
      fullscreen: 'f',
      shortcutsEnabled: true,
    }
  });

  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info' | 'warning'}>({
    open: false,
    message: '',
    severity: 'info'
  });
  const [activeTab, setActiveTab] = useState(0);

  // ST-03: Trading Profiles state
  const [profiles, setProfiles] = useState<TradingProfile[]>(DEFAULT_PROFILES);
  const [activeProfile, setActiveProfile] = useState<string>('moderate');

  useEffect(() => {
    loadSettings();
  }, []);

  // ST-03: Apply profile to settings
  const applyProfile = (profileId: string) => {
    const profile = profiles.find(p => p.id === profileId);
    if (!profile) return;

    setSettings(prev => ({
      ...prev,
      trading: {
        ...prev.trading,
        defaultStopLoss: profile.settings.defaultStopLoss,
        defaultTakeProfit: profile.settings.defaultTakeProfit,
        defaultLeverage: profile.settings.defaultLeverage,
        maxConcurrentPositions: profile.settings.maxConcurrentPositions,
        defaultBudget: profile.settings.defaultBudget,
      }
    }));
    setActiveProfile(profileId);
    setSnackbar({
      open: true,
      message: `Profile "${profile.name}" applied successfully`,
      severity: 'success'
    });
  };

  // ST-03: Get style color
  const getStyleColor = (style: TradingProfile['style']): 'error' | 'warning' | 'success' | 'info' | 'default' => {
    switch (style) {
      case 'aggressive': return 'error';
      case 'moderate': return 'warning';
      case 'conservative': return 'success';
      case 'scalping': return 'info';
      default: return 'default';
    }
  };

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

  // SY-02: Export all settings to JSON file
  const exportSettings = () => {
    const exportData = {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      settings,
      profiles,
      activeProfile,
    };

    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `fxcrypto-settings-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setSnackbar({
      open: true,
      message: 'Settings exported successfully',
      severity: 'success'
    });
  };

  // SY-02: Import settings from JSON file
  const importSettings = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const importData = JSON.parse(e.target?.result as string);

        // Validate structure
        if (!importData.version || !importData.settings) {
          throw new Error('Invalid settings file format');
        }

        // Import settings
        if (importData.settings) {
          setSettings(prev => ({
            ...prev,
            ...importData.settings,
          }));
        }

        // Import profiles if present
        if (importData.profiles) {
          setProfiles(importData.profiles);
        }

        // Import active profile if present
        if (importData.activeProfile) {
          setActiveProfile(importData.activeProfile);
        }

        setSnackbar({
          open: true,
          message: 'Settings imported successfully',
          severity: 'success'
        });
      } catch (error) {
        setSnackbar({
          open: true,
          message: 'Failed to import settings: Invalid file format',
          severity: 'error'
        });
      }
    };

    reader.readAsText(file);
    // Reset input so same file can be selected again
    event.target.value = '';
  };

  // SY-02: Reset to default settings
  const resetToDefaults = () => {
    setSettings({
      api: {
        baseUrl: 'http://localhost:8000',
        timeout: 30,
        retryAttempts: 3
      },
      trading: {
        defaultSymbols: ['BTC_USDT', 'ETH_USDT'],
        maxConcurrentPositions: 5,
        defaultBudget: 1000,
        riskManagement: true,
        defaultStopLoss: 2.0,
        defaultTakeProfit: 4.0,
        defaultLeverage: 5,
        slTpMode: 'percentage',
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
      },
      shortcuts: {
        emergencyStop: 'Escape',
        closePosition: 'c',
        goToDashboard: 'd',
        goToTrading: 't',
        goToHistory: 's',
        zoomIn: '+',
        zoomOut: '-',
        fullscreen: 'f',
        shortcutsEnabled: true,
      }
    });
    setProfiles(DEFAULT_PROFILES);
    setActiveProfile('moderate');

    setSnackbar({
      open: true,
      message: 'Settings reset to defaults',
      severity: 'info'
    });
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
          <Tab label="Keyboard Shortcuts" />
          <Tab label="Profiles" />
          <Tab label="Backup / Restore" />
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
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <SecurityIcon color="warning" sx={{ mr: 1 }} />
                  <Typography variant="h6">Default SL/TP Settings (ST-01)</Typography>
                </Box>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <FormControl fullWidth>
                    <InputLabel>SL/TP Mode</InputLabel>
                    <Select
                      value={settings.trading.slTpMode}
                      label="SL/TP Mode"
                      onChange={(e) => updateSetting('trading', 'slTpMode', e.target.value)}
                    >
                      <MenuItem value="percentage">Percentage (%)</MenuItem>
                      <MenuItem value="fixed">Fixed (USD)</MenuItem>
                    </Select>
                  </FormControl>

                  <TextField
                    fullWidth
                    label={`Default Stop Loss (${settings.trading.slTpMode === 'percentage' ? '%' : 'USD'})`}
                    type="number"
                    value={settings.trading.defaultStopLoss}
                    onChange={(e) => updateSetting('trading', 'defaultStopLoss', parseFloat(e.target.value))}
                    helperText={settings.trading.slTpMode === 'percentage'
                      ? "Percentage below entry price to trigger stop loss"
                      : "Fixed USD amount for stop loss"}
                    InputProps={{
                      inputProps: { min: 0.1, max: settings.trading.slTpMode === 'percentage' ? 50 : 10000, step: 0.1 }
                    }}
                  />

                  <TextField
                    fullWidth
                    label={`Default Take Profit (${settings.trading.slTpMode === 'percentage' ? '%' : 'USD'})`}
                    type="number"
                    value={settings.trading.defaultTakeProfit}
                    onChange={(e) => updateSetting('trading', 'defaultTakeProfit', parseFloat(e.target.value))}
                    helperText={settings.trading.slTpMode === 'percentage'
                      ? "Percentage above entry price to trigger take profit"
                      : "Fixed USD amount for take profit"}
                    InputProps={{
                      inputProps: { min: 0.1, max: settings.trading.slTpMode === 'percentage' ? 100 : 50000, step: 0.1 }
                    }}
                  />

                  <TextField
                    fullWidth
                    label="Default Leverage"
                    type="number"
                    value={settings.trading.defaultLeverage}
                    onChange={(e) => updateSetting('trading', 'defaultLeverage', parseInt(e.target.value))}
                    helperText="Default leverage multiplier (1-125x)"
                    InputProps={{
                      inputProps: { min: 1, max: 125, step: 1 }
                    }}
                  />

                  <Alert severity="warning" sx={{ mt: 1 }}>
                    <Typography variant="body2">
                      <strong>Risk Warning:</strong> Higher leverage amplifies both gains and losses.
                      A 5x leverage with 2% SL means a ~10% loss per trade.
                    </Typography>
                  </Alert>
                </Box>
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
                  <Alert severity="success" variant="outlined">
                    <Typography variant="body2">✅ Trade executions</Typography>
                  </Alert>
                  <Alert severity="error" variant="outlined">
                    <Typography variant="body2">❌ System errors</Typography>
                  </Alert>
                  <Alert severity="warning" variant="outlined">
                    <Typography variant="body2">⚠️ Risk warnings</Typography>
                  </Alert>
                  <Alert severity="info" variant="outlined">
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

      {/* ST-02: Keyboard Shortcuts Tab */}
      {activeTab === 5 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <KeyboardIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">Keyboard Shortcuts Configuration</Typography>
                  </Box>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.shortcuts.shortcutsEnabled}
                        onChange={(e) => updateSetting('shortcuts', 'shortcutsEnabled', e.target.checked)}
                      />
                    }
                    label="Enable Shortcuts"
                  />
                </Box>

                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Action</TableCell>
                        <TableCell>Description</TableCell>
                        <TableCell>Shortcut</TableCell>
                        <TableCell>Priority</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {/* Emergency Actions - HIGH priority */}
                      <TableRow sx={{ bgcolor: 'error.lighter' }}>
                        <TableCell>
                          <Typography variant="body2" fontWeight="bold">Emergency Stop All</Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            Stop all active trading sessions immediately
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            value={settings.shortcuts.emergencyStop}
                            onChange={(e) => updateSetting('shortcuts', 'emergencyStop', e.target.value)}
                            disabled={!settings.shortcuts.shortcutsEnabled}
                            sx={{ width: 100 }}
                            inputProps={{ style: { textAlign: 'center', fontFamily: 'monospace' } }}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip label="HIGH" size="small" color="error" />
                        </TableCell>
                      </TableRow>

                      <TableRow sx={{ bgcolor: 'error.lighter' }}>
                        <TableCell>
                          <Typography variant="body2" fontWeight="bold">Close Position</Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            Close current/selected position
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            value={settings.shortcuts.closePosition}
                            onChange={(e) => updateSetting('shortcuts', 'closePosition', e.target.value)}
                            disabled={!settings.shortcuts.shortcutsEnabled}
                            sx={{ width: 100 }}
                            inputProps={{ style: { textAlign: 'center', fontFamily: 'monospace' } }}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip label="HIGH" size="small" color="error" />
                        </TableCell>
                      </TableRow>

                      {/* Navigation - MEDIUM priority */}
                      <TableRow>
                        <TableCell>
                          <Typography variant="body2" fontWeight="bold">Go to Dashboard</Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            Navigate to Dashboard page
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            value={settings.shortcuts.goToDashboard}
                            onChange={(e) => updateSetting('shortcuts', 'goToDashboard', e.target.value)}
                            disabled={!settings.shortcuts.shortcutsEnabled}
                            sx={{ width: 100 }}
                            inputProps={{ style: { textAlign: 'center', fontFamily: 'monospace' } }}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip label="MEDIUM" size="small" color="warning" />
                        </TableCell>
                      </TableRow>

                      <TableRow>
                        <TableCell>
                          <Typography variant="body2" fontWeight="bold">Go to Trading Session</Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            Navigate to Trading Session page
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            value={settings.shortcuts.goToTrading}
                            onChange={(e) => updateSetting('shortcuts', 'goToTrading', e.target.value)}
                            disabled={!settings.shortcuts.shortcutsEnabled}
                            sx={{ width: 100 }}
                            inputProps={{ style: { textAlign: 'center', fontFamily: 'monospace' } }}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip label="MEDIUM" size="small" color="warning" />
                        </TableCell>
                      </TableRow>

                      <TableRow>
                        <TableCell>
                          <Typography variant="body2" fontWeight="bold">Go to Session History</Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            Navigate to Session History page
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            value={settings.shortcuts.goToHistory}
                            onChange={(e) => updateSetting('shortcuts', 'goToHistory', e.target.value)}
                            disabled={!settings.shortcuts.shortcutsEnabled}
                            sx={{ width: 100 }}
                            inputProps={{ style: { textAlign: 'center', fontFamily: 'monospace' } }}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip label="MEDIUM" size="small" color="warning" />
                        </TableCell>
                      </TableRow>

                      {/* Chart Controls - MEDIUM priority */}
                      <TableRow>
                        <TableCell>
                          <Typography variant="body2" fontWeight="bold">Zoom In</Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            Zoom in on chart
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            value={settings.shortcuts.zoomIn}
                            onChange={(e) => updateSetting('shortcuts', 'zoomIn', e.target.value)}
                            disabled={!settings.shortcuts.shortcutsEnabled}
                            sx={{ width: 100 }}
                            inputProps={{ style: { textAlign: 'center', fontFamily: 'monospace' } }}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip label="MEDIUM" size="small" color="warning" />
                        </TableCell>
                      </TableRow>

                      <TableRow>
                        <TableCell>
                          <Typography variant="body2" fontWeight="bold">Zoom Out</Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            Zoom out on chart
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            value={settings.shortcuts.zoomOut}
                            onChange={(e) => updateSetting('shortcuts', 'zoomOut', e.target.value)}
                            disabled={!settings.shortcuts.shortcutsEnabled}
                            sx={{ width: 100 }}
                            inputProps={{ style: { textAlign: 'center', fontFamily: 'monospace' } }}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip label="MEDIUM" size="small" color="warning" />
                        </TableCell>
                      </TableRow>

                      {/* Display - LOW priority */}
                      <TableRow sx={{ bgcolor: 'action.hover' }}>
                        <TableCell>
                          <Typography variant="body2" fontWeight="bold">Full Screen</Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            Toggle fullscreen chart view
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            value={settings.shortcuts.fullscreen}
                            onChange={(e) => updateSetting('shortcuts', 'fullscreen', e.target.value)}
                            disabled={!settings.shortcuts.shortcutsEnabled}
                            sx={{ width: 100 }}
                            inputProps={{ style: { textAlign: 'center', fontFamily: 'monospace' } }}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip label="LOW" size="small" color="default" />
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>

                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                  <Button
                    variant="outlined"
                    startIcon={<RestoreIcon />}
                    onClick={() => {
                      setSettings(prev => ({
                        ...prev,
                        shortcuts: {
                          emergencyStop: 'Escape',
                          closePosition: 'c',
                          goToDashboard: 'd',
                          goToTrading: 't',
                          goToHistory: 's',
                          zoomIn: '+',
                          zoomOut: '-',
                          fullscreen: 'f',
                          shortcutsEnabled: true,
                        }
                      }));
                      setSnackbar({ open: true, message: 'Shortcuts reset to defaults', severity: 'info' });
                    }}
                  >
                    Reset to Defaults
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Shortcut Guide
                </Typography>

                <Alert severity="info" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    <strong>How to set shortcuts:</strong>
                    <br />• Single key: a, b, c, etc.
                    <br />• Special keys: Escape, Enter, Space
                    <br />• Combinations: Ctrl+S, Alt+D (coming soon)
                  </Typography>
                </Alert>

                <Alert severity="warning" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    <strong>Emergency shortcuts</strong> (ESC, C) are always active when a trading session is running.
                  </Typography>
                </Alert>

                <Divider sx={{ my: 2 }} />

                <Typography variant="subtitle2" gutterBottom>
                  Priority Legend
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Chip label="HIGH" size="small" color="error" />
                    <Typography variant="body2">Critical trading actions</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Chip label="MEDIUM" size="small" color="warning" />
                    <Typography variant="body2">Navigation & chart controls</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Chip label="LOW" size="small" color="default" />
                    <Typography variant="body2">Nice to have features</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>

            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Status
                </Typography>
                {settings.shortcuts.shortcutsEnabled ? (
                  <Alert severity="success">
                    <Typography variant="body2">
                      Keyboard shortcuts are <strong>enabled</strong>.
                      <br />
                      Shortcuts work on Dashboard, Trading Session, and Chart pages.
                    </Typography>
                  </Alert>
                ) : (
                  <Alert severity="warning">
                    <Typography variant="body2">
                      Keyboard shortcuts are <strong>disabled</strong>.
                      <br />
                      Enable them using the toggle above.
                    </Typography>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* ST-03: Profiles Tab */}
      {activeTab === 6 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <PersonIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">Trading Profiles</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Active: <Chip label={profiles.find(p => p.id === activeProfile)?.name || 'None'} size="small" color="primary" />
                  </Typography>
                </Box>

                <Alert severity="info" sx={{ mb: 3 }}>
                  <Typography variant="body2">
                    Trading profiles let you quickly switch between different trading styles.
                    Each profile contains pre-configured SL/TP, leverage, and position settings.
                  </Typography>
                </Alert>

                <Grid container spacing={2}>
                  {profiles.map((profile) => (
                    <Grid item xs={12} md={6} lg={3} key={profile.id}>
                      <Card
                        variant="outlined"
                        sx={{
                          height: '100%',
                          border: activeProfile === profile.id ? 2 : 1,
                          borderColor: activeProfile === profile.id ? 'primary.main' : 'divider',
                          bgcolor: activeProfile === profile.id ? 'action.selected' : 'background.paper',
                        }}
                      >
                        <CardContent>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                            <Typography variant="h6" component="div">
                              {profile.name}
                            </Typography>
                            <Chip
                              label={profile.style.toUpperCase()}
                              size="small"
                              color={getStyleColor(profile.style)}
                            />
                          </Box>

                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, minHeight: 40 }}>
                            {profile.description}
                          </Typography>

                          <Divider sx={{ my: 1.5 }} />

                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                              <Typography variant="caption" color="text.secondary">Stop Loss:</Typography>
                              <Typography variant="caption" fontWeight="bold">{profile.settings.defaultStopLoss}%</Typography>
                            </Box>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                              <Typography variant="caption" color="text.secondary">Take Profit:</Typography>
                              <Typography variant="caption" fontWeight="bold">{profile.settings.defaultTakeProfit}%</Typography>
                            </Box>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                              <Typography variant="caption" color="text.secondary">Leverage:</Typography>
                              <Typography variant="caption" fontWeight="bold">{profile.settings.defaultLeverage}x</Typography>
                            </Box>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                              <Typography variant="caption" color="text.secondary">Max Positions:</Typography>
                              <Typography variant="caption" fontWeight="bold">{profile.settings.maxConcurrentPositions}</Typography>
                            </Box>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                              <Typography variant="caption" color="text.secondary">Budget:</Typography>
                              <Typography variant="caption" fontWeight="bold">${profile.settings.defaultBudget}</Typography>
                            </Box>
                          </Box>

                          <Button
                            variant={activeProfile === profile.id ? "contained" : "outlined"}
                            fullWidth
                            sx={{ mt: 2 }}
                            onClick={() => applyProfile(profile.id)}
                            disabled={activeProfile === profile.id}
                          >
                            {activeProfile === profile.id ? 'Active' : 'Apply Profile'}
                          </Button>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>

                <Divider sx={{ my: 3 }} />

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Risk Level Summary
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Chip label="Aggressive" size="small" color="error" variant="outlined" />
                      <Typography variant="body2" sx={{ mx: 0.5 }}>=</Typography>
                      <Typography variant="body2">High risk, high reward</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                      <Chip label="Moderate" size="small" color="warning" variant="outlined" />
                      <Typography variant="body2" sx={{ mx: 0.5 }}>=</Typography>
                      <Typography variant="body2">Balanced approach</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                      <Chip label="Conservative" size="small" color="success" variant="outlined" />
                      <Typography variant="body2" sx={{ mx: 0.5 }}>=</Typography>
                      <Typography variant="body2">Low risk, steady gains</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                      <Chip label="Scalping" size="small" color="info" variant="outlined" />
                      <Typography variant="body2" sx={{ mx: 0.5 }}>=</Typography>
                      <Typography variant="body2">Quick trades, active monitoring</Typography>
                    </Box>
                  </Box>

                  <Alert severity="warning" sx={{ maxWidth: 400 }}>
                    <Typography variant="body2">
                      <strong>Note:</strong> Applying a profile will overwrite your current Trading Settings.
                      Your other settings (API, Display, etc.) remain unchanged.
                    </Typography>
                  </Alert>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* SY-02: Backup / Restore Tab */}
      {activeTab === 7 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <BackupIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Export Settings</Typography>
                </Box>

                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Export all your settings to a JSON file for backup or transfer to another machine.
                </Typography>

                <Alert severity="info" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    The export includes:
                  </Typography>
                  <Box component="ul" sx={{ m: 0, pl: 2 }}>
                    <li>API configuration</li>
                    <li>Trading settings</li>
                    <li>Notification preferences</li>
                    <li>Display settings</li>
                    <li>Performance settings</li>
                    <li>Keyboard shortcuts</li>
                    <li>Trading profiles</li>
                  </Box>
                </Alert>

                <Button
                  variant="contained"
                  fullWidth
                  startIcon={<DownloadIcon />}
                  onClick={exportSettings}
                >
                  Export All Settings
                </Button>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <UploadIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Import Settings</Typography>
                </Box>

                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Import settings from a previously exported JSON file.
                </Typography>

                <Alert severity="warning" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    <strong>Warning:</strong> Importing settings will overwrite your current configuration.
                    Consider exporting your current settings first.
                  </Typography>
                </Alert>

                <Button
                  variant="outlined"
                  fullWidth
                  component="label"
                  startIcon={<UploadIcon />}
                >
                  Import Settings
                  <input
                    type="file"
                    accept=".json"
                    hidden
                    onChange={importSettings}
                  />
                </Button>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <RestoreIcon color="error" sx={{ mr: 1 }} />
                  <Typography variant="h6">Reset to Defaults</Typography>
                </Box>

                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Reset all settings to their default values. This cannot be undone.
                </Typography>

                <Alert severity="error" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    <strong>Danger Zone:</strong> This will reset ALL settings including API configuration,
                    trading preferences, and profiles.
                  </Typography>
                </Alert>

                <Button
                  variant="outlined"
                  color="error"
                  fullWidth
                  startIcon={<RestoreIcon />}
                  onClick={resetToDefaults}
                >
                  Reset All to Defaults
                </Button>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <StorageIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Current Configuration</Typography>
                </Box>

                <TableContainer>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell><strong>API URL</strong></TableCell>
                        <TableCell>{settings.api.baseUrl}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Active Profile</strong></TableCell>
                        <TableCell>
                          <Chip
                            label={profiles.find(p => p.id === activeProfile)?.name || 'Custom'}
                            size="small"
                            color={getStyleColor(profiles.find(p => p.id === activeProfile)?.style || 'custom')}
                          />
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Theme</strong></TableCell>
                        <TableCell>{settings.display.theme}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Default Budget</strong></TableCell>
                        <TableCell>${settings.trading.defaultBudget}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Max Positions</strong></TableCell>
                        <TableCell>{settings.trading.maxConcurrentPositions}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Shortcuts Enabled</strong></TableCell>
                        <TableCell>
                          <Chip
                            label={settings.shortcuts.shortcutsEnabled ? 'Yes' : 'No'}
                            size="small"
                            color={settings.shortcuts.shortcutsEnabled ? 'success' : 'default'}
                          />
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
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
