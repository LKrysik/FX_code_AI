'use client';

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useVisibilityAwareInterval } from '@/hooks/useVisibilityAwareInterval';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
  Alert,
  Button,
  Skeleton,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Badge,
  Avatar,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  AccountBalanceWallet as WalletIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Assessment as AssessmentIcon,
  Refresh as RefreshIcon,
  Error as ErrorIcon,
  CheckCircle as SuccessIcon,
  Warning as WarningIcon,
  Notifications as NotificationsIcon,
  Bolt as FlashIcon,
  ShowChart as ChartIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';
import { wsService } from '@/services/websocket';
import { apiService } from '@/services/api';
import { useWebSocketStore } from '@/stores/websocketStore';
import { useTradingStore, useTradingActions, useDashboardStore, useDashboardActions, useUIActions } from '@/stores';
import { AuthGuard } from '@/components/auth';
import { WalletBalance, TradingPerformance, Strategy } from '@/types/api';
import { SystemStatusIndicator } from '@/components/common/SystemStatusIndicator';
import { useSmartCache } from '@/hooks/useSmartCache';
import { debugLog, errorLog } from '@/utils/config';
import { useRouter } from 'next/navigation';
import { useHealthStore } from '@/stores/healthStore';
import {
  getPerformanceStatusColor,
  getMarketStatusColor,
  getSignalStatusColor,
  getSignalStatusText,
  type SignalType
} from '@/utils/statusUtils';

interface MarketData {
  symbol: string;
  price: number;
  priceChange24h: number;
  volume24h: number;
  pumpMagnitude: number;
  volumeSurge: number;
  confidenceScore: number;
  lastUpdate: string;
}

interface ActiveSignal {
  id: string;
  symbol: string;
  signalType: 'pump' | 'dump';
  magnitude: number;
  confidence: number;
  timestamp: string;
  strategy: string;
}

const DashboardContent = React.memo(function DashboardContent() {
  const router = useRouter();

  // Use Zustand stores instead of local state
  const {
    walletBalance,
    performance,
    strategies,
  } = useTradingStore();

  const {
    marketData,
    activeSignals,
    loading: dashboardLoading,
    error: dashboardError,
  } = useDashboardStore();

  const {
    fetchWalletBalance,
    fetchTradingPerformance,
    fetchStrategies,
    startSession,
  } = useTradingActions();

  const {
    fetchMarketData,
    fetchActiveSignals,
  } = useDashboardActions();

  const { addNotification } = useUIActions();

  // Local state for UI-specific data
  const [dataTimestamps, setDataTimestamps] = useState({
    wallet: null as string | null,
    performance: null as string | null,
    strategies: null as string | null,
    marketData: null as string | null,
    signals: null as string | null
  });
  const [loadingStates, setLoadingStates] = useState({
    dashboard: false,
    marketData: false,
    signals: false
  });
  const [backendConnected, setBackendConnected] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  // Use reactive WebSocket store
  const { isConnected: wsConnected } = useWebSocketStore();

  // Backend health check - only as backup (WebSocket provides real-time status)
  const checkBackendConnection = async () => {
    try {
      await apiService.healthCheck();
      setBackendConnected(true);
    } catch (error) {
      setBackendConnected(false);
    }
  };

  // Reduced polling frequency - only backup every 5 minutes when WebSocket unavailable
  useVisibilityAwareInterval(checkBackendConnection, 300000); // 5 minutes

  // ✅ PERFORMANCE FIX: Separate WebSocket setup from data loading
  useEffect(() => {
    // Set up WebSocket callbacks for real-time updates - only once
    wsService.setCallbacks({
      onConnect: () => {
        debugLog('WebSocket connected - subscribing to real-time data');
        // Status is now managed reactively by the store
        // Subscribe to real-time data streams
        wsService.subscribe('market_data', { symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT'] });
        wsService.subscribe('signals', {});
        wsService.subscribe('session_update', {});
        wsService.subscribe('health_check', {});
      },
      onDisconnect: (reason) => {
        debugLog(`WebSocket disconnected: ${reason}`);
        // Status is now managed reactively by the store
      },
      onError: (error) => {
        errorLog('WebSocket error', error);
        // Status is now managed reactively by the store
      },
      onMarketData: (data) => {
        // Update market data in real-time using store
        useDashboardStore.getState().updateMarketData(data.symbol, {
          price: data.price,
          priceChange24h: data.priceChange24h,
          volume24h: data.volume24h,
        });
      },
      onSignals: (data) => {
        // Update active signals in real-time using store
        const signalType: ActiveSignal['signalType'] =
          data.type === 'pump_detection' ? 'pump' : 'dump';
        const newSignal: ActiveSignal = {
          id: data.id || `signal_${Date.now()}`,
          symbol: data.symbol || 'UNKNOWN',
          signalType,
          magnitude: data.magnitude || data.value || 0,
          confidence: data.confidence || 50,
          timestamp: data.timestamp || new Date().toISOString(),
          strategy: data.strategy || 'unknown'
        };
        useDashboardStore.getState().addSignal(newSignal);
      },
      onSessionUpdate: (data) => {
        // Update session data in real-time
        if (data.session_id) {
          // Refresh dashboard data when session updates
          loadDashboardData();
        }
      },
      onHealthCheck: (data) => {
        // Update health status in real-time using health store
        if (data.alert_id) {
          // This is a health alert from backend
          useHealthStore.getState().addHealthAlert({
            alert_id: data.alert_id,
            alert_name: data.alert_name,
            level: data.level,
            message: data.message,
            timestamp: data.timestamp,
            service: data.check_name,
            details: data.details
          });
        }
      }
    });

    // Initial backend connection check (WebSocket status is reactive)
    checkBackendConnection();
  }, []); // Empty dependency array - only run once

  // ✅ PERFORMANCE FIX: Separate data loading with proper dependencies
  useEffect(() => {
    loadDashboardData();
  }, []); // Only run once on mount

  // Load dashboard data using stores
  const loadDashboardData = useCallback(async (isRetry = false) => {
    try {
      // Set loading state in dashboard store
      useDashboardStore.getState().setLoading(true);
      useDashboardStore.getState().setError(null);

      if (isRetry) {
        setRetryCount(prev => prev + 1);
        addNotification({
          type: 'info',
          message: `Retrying to load dashboard data (attempt ${retryCount + 1})...`,
        });
      }

      // Load data from stores (which handle API calls internally)
      await Promise.all([
        fetchWalletBalance(),
        fetchTradingPerformance(),
        fetchStrategies(),
        fetchMarketData(),
        fetchActiveSignals(),
      ]);

      // Update timestamps for successfully loaded data
      const now = new Date().toISOString();
      setDataTimestamps(prev => ({
        ...prev,
        wallet: walletBalance ? now : prev.wallet,
        performance: performance ? now : prev.performance,
        strategies: strategies.length > 0 ? now : prev.strategies,
        marketData: marketData.length > 0 ? now : prev.marketData,
        signals: activeSignals.length > 0 ? now : prev.signals
      }));

      setBackendConnected(true);

      if (isRetry) {
        addNotification({
          type: 'success',
          message: 'Dashboard data loaded successfully!',
        });
        setRetryCount(0);
      }

    } catch (err: any) {
      const errorMessage = err?.response?.data?.error_message ||
                           err?.message ||
                           'Failed to load dashboard data';

      // Set error in dashboard store
      useDashboardStore.getState().setError(errorMessage);

      console.error('Dashboard error:', err);

      addNotification({
        type: 'error',
        message: `Failed to load dashboard: ${errorMessage}`,
      });
    } finally {
      useDashboardStore.getState().setLoading(false);
    }
  }, [fetchWalletBalance, fetchTradingPerformance, fetchStrategies, fetchMarketData, fetchActiveSignals, retryCount, walletBalance, performance, strategies.length, marketData.length, activeSignals.length]);


  const handleRetry = useCallback(() => {
    loadDashboardData(true);
  }, [loadDashboardData]);

  // ✅ PERFORMANCE FIX: Memoize expensive data transformations
  const processedMarketData = useMemo(() => {
    return marketData.map((data) => ({
      ...data,
      displayPrice: `$${data.price.toLocaleString()}`,
      displayChange: `${data.priceChange24h >= 0 ? '+' : ''}${data.priceChange24h.toFixed(1)}%`,
      displayVolume: `$${(data.volume24h / 1000000).toFixed(1)}M`,
      displayMagnitude: `${data.pumpMagnitude.toFixed(1)}%`,
      displaySurge: `${data.volumeSurge.toFixed(1)}x`
    }));
  }, [marketData]);

  const processedSignals = useMemo(() => {
    return activeSignals.map((signal) => ({
      ...signal,
      displaySymbol: signal.symbol.replace('_', '/'),
      displayMagnitude: `${signal.magnitude.toFixed(1)}%`,
      displayTimestamp: new Date(signal.timestamp).toLocaleTimeString()
    }));
  }, [activeSignals]);


  // Helper function to format timestamps
  const formatLastUpdated = (timestamp: string | null): string => {
    if (!timestamp) return 'Never';

    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  };

  // Quick action handlers
  const handleStartPumpScanner = async () => {
    try {
      // Start a data collection session for pump scanning
      const sessionData = {
        session_type: 'live',
        symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT'],
        strategy_config: {
          pump_scanner: {
            scan_interval: 60,
            min_pump_magnitude: 5.0,
            min_volume_surge: 2.0
          }
        },
        config: {
          budget: { global_cap: 1000 },
          data_collection: { duration: 'continuous' }
        },
        idempotent: true
      };

      const response = await startSession(sessionData);

      // Validate response before showing success
      if (response?.data?.session_id) {
        addNotification({
          type: 'success',
          message: `Pump scanner started successfully: ${response.data.session_id}`,
        });
      } else {
        // Response missing expected data - show warning instead
        addNotification({
          type: 'warning',
          message: 'Pump scanner may have started but session ID is unavailable',
        });
      }
      // Refresh data to show new session
      loadDashboardData();
    } catch (error) {
      addNotification({
        type: 'error',
        message: 'Failed to start pump scanner',
      });
    }
  };

  const handleQuickTradeSetup = () => {
    // Navigate to trading page
    router.push('/trading');
  };

  const handleRiskManagement = () => {
    // Navigate to risk management page
    router.push('/risk-management');
  };

  const handlePerformanceReport = async () => {
    try {
      // Generate and show performance report
      const performance = await fetchTradingPerformance();
      if (performance) {
        addNotification({
          type: 'info',
          message: `Performance Report: Win Rate ${performance.win_rate?.toFixed(1)}%, P&L $${performance.total_pnl?.toFixed(2)}`,
        });
      }
    } catch (error) {
      addNotification({
        type: 'error',
        message: 'Failed to generate performance report',
      });
    }
  };

  const handleStartBacktest = async () => {
    try {
      // Start a backtest session
      const sessionData = {
        session_type: 'backtest',
        symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT'],
        strategy_config: {
          pump_dump_detector: {
            scan_interval: 60,
            min_pump_magnitude: 5.0,
            min_volume_surge: 2.0
          }
        },
        config: {
          budget: { global_cap: 10000 },
          data_collection: { duration: 'continuous' }
        },
        idempotent: true
      };

      const response = await startSession(sessionData);

      // Validate response before showing success
      if (response?.data?.session_id) {
        addNotification({
          type: 'success',
          message: `Backtest started successfully: ${response.data.session_id}`,
        });
      } else {
        // Response missing expected data - show warning instead
        addNotification({
          type: 'warning',
          message: 'Backtest may have started but session ID is unavailable',
        });
      }
      // Refresh data to show new session
      loadDashboardData();
    } catch (error) {
      addNotification({
        type: 'error',
        message: 'Failed to start backtest',
      });
    }
  };

  const handleStartDataCollection = async () => {
    try {
      // Start a data collection session
      const sessionData = {
        session_type: 'collect',
        symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT'],
        strategy_config: {
          data_collector: {
            scan_interval: 30,
            collect_orderbook: true,
            collect_trades: true
          }
        },
        config: {
          data_path: 'data/historical',
          duration: 'continuous'
        },
        idempotent: true
      };

      const response = await startSession(sessionData);

      // Validate response before showing success
      if (response?.data?.session_id) {
        addNotification({
          type: 'success',
          message: `Data collection started successfully: ${response.data.session_id}`,
        });
      } else {
        // Response missing expected data - show warning instead
        addNotification({
          type: 'warning',
          message: 'Data collection may have started but session ID is unavailable',
        });
      }
      // Refresh data to show new session
      loadDashboardData();
    } catch (error) {
      addNotification({
        type: 'error',
        message: 'Failed to start data collection',
      });
    }
  };

  const handleQuickTrade = async (symbol: string) => {
    try {
      // Navigate to trading page with pre-selected symbol
      router.push(`/trading?symbol=${symbol}`);
    } catch (error) {
      addNotification({
        type: 'error',
        message: 'Failed to initiate trade',
      });
    }
  };

  const handleMonitorSymbol = async (symbol: string) => {
    try {
      // Add symbol to monitoring (could subscribe to WebSocket updates)
      wsService.subscribe('market_data', { symbols: [symbol] });
      addNotification({
        type: 'success',
        message: `Now monitoring ${symbol}`,
      });
    } catch (error) {
      addNotification({
        type: 'error',
        message: 'Failed to start monitoring',
      });
    }
  };

  if (dashboardLoading) {
    return (
      <Box sx={{ flexGrow: 1, p: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Trading Dashboard
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <CircularProgress size={20} sx={{ mr: 2 }} />
          <Typography variant="body1">
            Loading dashboard data...
          </Typography>
        </Box>

        <Grid container spacing={3}>
          {/* Wallet Balance Card Skeleton */}
          <Grid item xs={12} md={6} lg={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Skeleton variant="circular" width={24} height={24} sx={{ mr: 1 }} />
                  <Skeleton variant="text" width={120} height={24} />
                </Box>
                <Skeleton variant="text" width={100} height={36} sx={{ mb: 2 }} />
                <Skeleton variant="rectangular" width="100%" height={60} sx={{ mb: 2 }} />
                <Skeleton variant="rectangular" width={80} height={24} />
              </CardContent>
            </Card>
          </Grid>

          {/* Trading Performance Card Skeleton */}
          <Grid item xs={12} md={6} lg={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Skeleton variant="circular" width={24} height={24} sx={{ mr: 1 }} />
                  <Skeleton variant="text" width={140} height={24} />
                </Box>
                <Skeleton variant="text" width={80} height={36} sx={{ mb: 2 }} />
                <Grid container spacing={1} sx={{ mb: 2 }}>
                  {[...Array(4)].map((_, i) => (
                    <Grid item xs={6} key={i}>
                      <Skeleton variant="text" width="100%" height={16} sx={{ mb: 1 }} />
                      <Skeleton variant="text" width="60%" height={20} />
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {/* Active Strategies Card Skeleton */}
          <Grid item xs={12} md={12} lg={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Skeleton variant="circular" width={24} height={24} sx={{ mr: 1 }} />
                  <Skeleton variant="text" width={130} height={24} />
                </Box>
                <Box>
                  {[...Array(3)].map((_, i) => (
                    <Box key={i} sx={{ mb: 2 }}>
                      <Skeleton variant="text" width="70%" height={20} sx={{ mb: 1 }} />
                      <Skeleton variant="text" width="50%" height={16} />
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* System Status Skeleton */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Skeleton variant="text" width={120} height={24} sx={{ mb: 2 }} />
                <Grid container spacing={2}>
                  {[...Array(4)].map((_, i) => (
                    <Grid item xs={12} md={3} key={i}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Skeleton variant="text" width={60} height={16} sx={{ mb: 1 }} />
                        <Skeleton variant="rectangular" width={80} height={24} sx={{ mx: 'auto' }} />
                      </Box>
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    );
  }


  if (dashboardError) {
    return (
      <Box sx={{ mt: 2 }}>
        <Alert
          severity="error"
          action={
            <Button
              color="inherit"
              size="small"
              startIcon={<RefreshIcon />}
              onClick={handleRetry}
              disabled={dashboardLoading}
            >
              Retry
            </Button>
          }
          sx={{ mb: 2 }}
        >
          <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
            Dashboard Loading Failed
          </Typography>
          <Typography variant="body2">
            {dashboardError}
          </Typography>
        </Alert>

        <Box sx={{ textAlign: 'center', mt: 3 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Having trouble connecting? Check your backend connection and try again.
          </Typography>
          <Button
            variant="outlined"
            startIcon={<ErrorIcon />}
            onClick={() => window.location.reload()}
          >
            Reload Page
          </Button>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          🚀 Pump & Dump Trading Dashboard
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => loadDashboardData()}
            disabled={dashboardLoading}
          >
            Refresh
          </Button>
          <Badge badgeContent={activeSignals.length} color="error">
            <NotificationsIcon color="action" />
          </Badge>
        </Box>
      </Box>

      {/* System Status */}
      <SystemStatusIndicator showDetails={false} />

      {/* Quick Actions Bar */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={2.4}>
          <Button
            variant="contained"
            color="success"
            fullWidth
            startIcon={<FlashIcon />}
            size="large"
            sx={{ py: 1.5 }}
            onClick={handleStartPumpScanner}
          >
            Start Pump Scanner
          </Button>
        </Grid>
        <Grid item xs={12} md={2.4}>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            startIcon={<PlayIcon />}
            size="large"
            sx={{ py: 1.5 }}
            onClick={handleQuickTradeSetup}
          >
            Live Trading
          </Button>
        </Grid>
        <Grid item xs={12} md={2.4}>
          <Button
            variant="contained"
            color="secondary"
            fullWidth
            startIcon={<TimelineIcon />}
            size="large"
            sx={{ py: 1.5 }}
            onClick={handleStartBacktest}
          >
            Run Backtest
          </Button>
        </Grid>
        <Grid item xs={12} md={2.4}>
          <Button
            variant="outlined"
            color="info"
            fullWidth
            startIcon={<ChartIcon />}
            size="large"
            sx={{ py: 1.5 }}
            onClick={handleStartDataCollection}
          >
            Collect Data
          </Button>
        </Grid>
        <Grid item xs={12} md={2.4}>
          <Button
            variant="outlined"
            color="warning"
            fullWidth
            startIcon={<SecurityIcon />}
            size="large"
            sx={{ py: 1.5 }}
            onClick={handleRiskManagement}
          >
            Risk Management
          </Button>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Market Scanner */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <ChartIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Market Scanner - Pump & Dump Detection</Typography>
                <Chip
                  label={`${marketData.length} Symbols`}
                  size="small"
                  color="info"
                  sx={{ ml: 1 }}
                />
              </Box>

              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Symbol</TableCell>
                      <TableCell align="right">Price</TableCell>
                      <TableCell align="right">24h %</TableCell>
                      <TableCell align="right">Volume</TableCell>
                      <TableCell align="right">
                        <Tooltip title="Pump Magnitude">
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <FlashIcon fontSize="small" sx={{ mr: 0.5 }} />
                            Magnitude
                          </Box>
                        </Tooltip>
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Volume Surge Ratio">
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <TrendingUpIcon fontSize="small" sx={{ mr: 0.5 }} />
                            Surge
                          </Box>
                        </Tooltip>
                      </TableCell>
                      <TableCell align="right">Confidence</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {processedMarketData.map((data) => (
                      <TableRow key={data.symbol} hover>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Avatar sx={{ width: 24, height: 24, mr: 1, bgcolor: 'primary.main', fontSize: '0.75rem' }}>
                              {data.symbol.split('_')[0].slice(0, 2)}
                            </Avatar>
                            <Typography variant="body2" fontWeight="bold">
                              {data.symbol.replace('_', '/')}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            {data.displayPrice}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography
                            variant="body2"
                            color={data.priceChange24h >= 0 ? 'success.main' : 'error.main'}
                          >
                            {data.displayChange}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            {data.displayVolume}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={data.displayMagnitude}
                            size="small"
                            color={getMarketStatusColor(data.pumpMagnitude, 'magnitude')}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={data.displaySurge}
                            size="small"
                            color={getMarketStatusColor(data.volumeSurge, 'surge')}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" color="primary">
                            {data.confidenceScore}%
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 0.5 }}>
                            <Tooltip title="Trade">
                              <IconButton
                                size="small"
                                color="primary"
                                onClick={() => handleQuickTrade(data.symbol)}
                              >
                                <PlayIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Monitor">
                              <IconButton
                                size="small"
                                color="info"
                                onClick={() => handleMonitorSymbol(data.symbol)}
                              >
                                <TimelineIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Active Signals & Risk Panel */}
        <Grid item xs={12} lg={4}>
          <Grid container spacing={2}>
            {/* Active Signals */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Badge badgeContent={activeSignals.length} color="error">
                      <NotificationsIcon color="error" sx={{ mr: 1 }} />
                    </Badge>
                    <Typography variant="h6">Active Signals</Typography>
                  </Box>

                  {processedSignals.length > 0 ? (
                    <List dense>
                      {processedSignals.map((signal) => (
                        <ListItem key={signal.id} divider>
                          <ListItemIcon>
                            <FlashIcon color={signal.signalType === 'pump' ? 'error' : 'warning'} />
                          </ListItemIcon>
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="body2" fontWeight="bold">
                                  {signal.displaySymbol}
                                </Typography>
                                <Chip
                                  label={getSignalStatusText(signal.signalType as SignalType)}
                                  size="small"
                                  color={getSignalStatusColor(signal.signalType as SignalType)}
                                />
                              </Box>
                            }
                            secondary={
                              <Typography variant="caption">
                                Magnitude: {signal.displayMagnitude} |
                                Confidence: {signal.confidence}% |
                                {signal.displayTimestamp}
                              </Typography>
                            }
                          />
                          <ListItemSecondaryAction>
                            <Button size="small" variant="outlined" color="success">
                              Trade
                            </Button>
                          </ListItemSecondaryAction>
                        </ListItem>
                      ))}
                    </List>
                  ) : (
                    <Box sx={{ textAlign: 'center', py: 3 }}>
                      <NotificationsIcon color="disabled" sx={{ fontSize: 48, mb: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        No active signals detected
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Risk & Performance Summary */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Risk & Performance
                  </Typography>

                  <Box sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2">Portfolio Value</Typography>
                      <Typography variant="body2" fontWeight="bold">
                        ${walletBalance?.total_usd_estimate?.toFixed(2) || '0.00'}
                      </Typography>
                    </Box>
                    {dataTimestamps.wallet && (
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Last updated: {formatLastUpdated(dataTimestamps.wallet)}
                        </Typography>
                      </Box>
                    )}

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2">Today's P&L</Typography>
                      <Typography
                        variant="body2"
                        color={getPerformanceStatusColor(performance?.total_pnl || 0) + '.main'}
                        fontWeight="bold"
                      >
                        ${performance?.total_pnl ? performance.total_pnl.toFixed(2) : '0.00'}
                      </Typography>
                    </Box>

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2">Active Positions</Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {performance?.active_positions || 0}
                      </Typography>
                    </Box>

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2">Win Rate</Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {performance?.win_rate ? `${performance.win_rate.toFixed(1)}%` : '0%'}
                      </Typography>
                    </Box>
                  </Box>

                  <Divider sx={{ my: 2 }} />

                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button size="small" variant="outlined" color="warning" fullWidth>
                      Emergency Stop
                    </Button>
                    <Button size="small" variant="outlined" color="info" fullWidth>
                      Close All
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* System Status */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    System Status
                  </Typography>
                  <SystemStatusIndicator showDetails={true} />
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

    </Box>
  );
});

const PumpDumpDashboard = React.memo(function PumpDumpDashboard() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
});

export default PumpDumpDashboard;
