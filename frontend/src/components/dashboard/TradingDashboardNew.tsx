/**
 * Trading Dashboard - Refactored with Zustand
 * ===========================================
 * Replaces the original dashboard with proper state management
 * Eliminates 15+ useState hooks and complex useEffect logic
 */

'use client';

import React, { useEffect, useCallback } from 'react';
import { useVisibilityAwareInterval } from '@/hooks/useVisibilityAwareInterval';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Button,
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
  CircularProgress,
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
  CheckCircle,
  Warning as WarningIcon,
  Notifications as NotificationsIcon,
  Bolt as FlashIcon,
  ShowChart as ChartIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';

// Import Zustand stores
import {
  useDashboardStore,
  useWebSocketStore,
  useTradingStore,
  useUIStore,
  useHealthStore,
  useDashboardActions,
  useTradingActions,
} from '@/stores';

// Import services
import { wsService } from '@/services/websocket';

// Import components
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { SystemStatusIndicator } from '@/components/common/SystemStatusIndicator';

export function TradingDashboardNew() {
  // Use Zustand stores instead of useState
  const {
    marketData,
    activeSignals,
    indicators,
    loading: dashboardLoading,
    error: dashboardError,
    setMarketData,
    setActiveSignals,
    setIndicators,
    addSignal,
    addIndicator,
    updateIndicator,
    updateMarketData,
    setLoading,
    setError,
  } = useDashboardStore();

  const {
    isConnected: wsConnected,
    connectionStatus,
    setConnected,
    setConnectionStatus,
    incrementMessagesReceived,
  } = useWebSocketStore();

  const {
    walletBalance,
    performance,
    strategies,
    currentSession,
  } = useTradingStore();

  const {
    fetchWalletBalance,
    fetchTradingPerformance,
    fetchStrategies,
    startSession: startTradingSession,
    stopSession: stopTradingSession,
  } = useTradingActions();

  const {
    fetchMarketData,
    fetchActiveSignals,
  } = useDashboardActions();

  const {
    notifications,
    addNotification,
    setReadOnlyMode,
  } = useUIStore();

  const { addHealthAlert, healthStatus } = useHealthStore();

  // Load dashboard data using stores
  const loadDashboardData = useCallback(async (isRetry = false) => {
    try {
      setLoading(true);
      setError(null);

      if (isRetry) {
        addNotification({
          type: 'info',
          message: 'Retrying to load dashboard data...',
        });
      }

      // Load data from stores (which handle API calls internally)
      await Promise.all([
        fetchWalletBalance(),
        fetchTradingPerformance(),
        fetchStrategies(),
        fetchMarketData(),
        fetchActiveSignals(),
        fetchIndicators(),
      ]);

      if (isRetry) {
        addNotification({
          type: 'success',
          message: 'Dashboard data loaded successfully!',
        });
      }

    } catch (err: any) {
      const errorMessage = err?.response?.data?.error_message ||
                           err?.message ||
                           'Failed to load dashboard data';

      setError(errorMessage);
      addNotification({
        type: 'error',
        message: `Failed to load dashboard: ${errorMessage}`,
      });
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, fetchWalletBalance, fetchTradingPerformance, fetchStrategies, fetchMarketData, fetchActiveSignals, addNotification]);


  // WebSocket status is now managed reactively through the store
  // No need for periodic polling

  useEffect(() => {
    const callbacks = {
      onConnect: () => {
        console.log('WebSocket connected - subscribing to real-time data');
        setConnected(true);
        setConnectionStatus('connected');

        console.log('🎧 [TradingDashboardNew] Subscribing to WebSocket streams:', {
          market_data: { symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT'] },
          indicators: {},
          signals: {},
          session_update: {},
          health_check: {},
          timestamp: new Date().toISOString()
        });

        wsService.subscribe('market_data', { symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT'] });
        wsService.subscribe('indicators', { symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT'] });
        wsService.subscribe('signals', {});
        wsService.subscribe('session_update', {});
        wsService.subscribe('health_check', {});

        console.log('✅ [TradingDashboardNew] All WebSocket subscriptions completed');

        // Log subscription summary after subscribing
        setTimeout(() => wsService.logSubscriptionSummary(), 100);
      },

      onDisconnect: (reason: string) => {
        console.log(`WebSocket disconnected: ${reason}`);
        setConnected(false);
        setConnectionStatus('disconnected');

        addNotification({
          type: 'warning',
          message: 'Connection lost',
        });
      },

      onError: (error: any) => {
        console.error('WebSocket error', error);
        setConnectionStatus('error');

        addNotification({
          type: 'error',
          message: 'WebSocket connection error',
        });
      },

      onMarketData: (data: any) => {
        incrementMessagesReceived();
        updateMarketData(data.symbol, {
          price: data.price,
          volume24h: data.volume24h,
          lastUpdate: new Date().toISOString()
        });
      },

      onSignals: (data: any) => {
        incrementMessagesReceived();
        const signal = {
          id: data.id || `signal_${Date.now()}`,
          symbol: data.symbol || 'UNKNOWN',
          signalType: data.type === 'pump_detection' ? 'pump' : 'dump',
          magnitude: data.magnitude || data.value || 0,
          confidence: data.confidence || 50,
          timestamp: data.timestamp || new Date().toISOString(),
          strategy: data.strategy || 'unknown'
        };
        addSignal(signal);

        addNotification({
          type: 'info',
          message: `New ${signal.signalType} signal: ${signal.symbol}`,
        });
      },

      onIndicators: (data: any) => {
        incrementMessagesReceived();
        // Handle both single indicator and array of indicators
        const indicatorData = data.indicators || [data];
        indicatorData.forEach((indicator: any) => {
          const indicatorObj = {
            name: indicator.name || 'VWAP',
            value: indicator.value || 0,
            symbol: indicator.symbol || 'UNKNOWN',
            timestamp: indicator.timestamp || new Date().toISOString(),
            used_by_strategies: indicator.used_by_strategies || [],
            indicator_type: indicator.indicator_type || 'vwap',
            period: indicator.period,
            metadata: indicator.metadata || {}
          };
          addIndicator(indicatorObj);
        });
      },

      onSessionUpdate: (data: any) => {
        incrementMessagesReceived();
        if (data.session_id) {
          setCurrentSession({
            sessionId: data.session_id,
            type: data.session_type,
            status: data.status,
            symbols: data.symbols || [],
          });
        }
      },

      onHealthCheck: (data: any) => {
        console.log('Health check received via WebSocket:', data);
        incrementMessagesReceived();

        // Process health alert from WebSocket
        if (data && data.alert_id) {
          const healthAlert = {
            alert_id: data.alert_id,
            alert_name: data.alert_name || 'Health Alert',
            level: data.level || 'info',
            message: data.message || 'Health notification received',
            timestamp: data.timestamp || new Date().toISOString(),
            service: data.service,
            details: data.details || {},
          };

          // Add to health store using proper store action
          addHealthAlert(healthAlert);

          // Also add as UI notification for immediate visibility
          const notificationType = healthAlert.level === 'critical' || healthAlert.level === 'error' ? 'error' :
                                   healthAlert.level === 'warning' ? 'warning' : 'info';

          addNotification({
            type: notificationType,
            message: `${healthAlert.alert_name}: ${healthAlert.message}`,
            autoHide: healthAlert.level !== 'critical',
          });
        }

        // Process overall health status updates from WebSocket
        if (data && data.type === 'health_update' && data.data) {
          const healthData = data.data;

          // Update health store with overall status using proper store action
          const overallStatus = healthData.status === 'healthy' ? 'healthy' :
                               healthData.status === 'degraded' ? 'degraded' :
                               healthData.status === 'unhealthy' ? 'unhealthy' : 'unknown';

          // Update service statuses if available
          if (healthData.degradation_info && healthData.degradation_info.services) {
            Object.entries(healthData.degradation_info.services).forEach(([serviceName, serviceData]: [string, any]) => {
              const serviceStatus = serviceData.status === 'healthy' ? 'healthy' :
                                   serviceData.status === 'degraded' ? 'degraded' :
                                   serviceData.status === 'unhealthy' ? 'unhealthy' : 'unknown';
              // Update service status using proper store action
              useHealthStore.getState().updateServiceStatus(serviceName, serviceStatus);
            });
          }

          // Update the overall health status in the store using proper store action
          useHealthStore.getState().setHealthStatus({
            status: overallStatus,
          });

          console.log('Updated health status from WebSocket:', overallStatus);
        }
      }
    };

    wsService.setCallbacks(callbacks);

    // Initial connection status is now managed by the store

    return () => {
      // no-op
    };
  }, [
    setConnected,
    setConnectionStatus,
    setReadOnlyMode,
    updateMarketData,
    addSignal,
    addIndicator,
    incrementMessagesReceived,
    setCurrentSession,
    addNotification,
    addHealthAlert,
  ]);

  // Initial data load
  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Quick actions
  const handleStartPumpScanner = useCallback(async () => {
    try {
      const sessionData = {
        session_type: 'live',
        symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT'],
        strategy_config: {
          pump_dump_detection: {
            symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT'],
            scan_interval: 60,
            min_pump_magnitude: 5.0,
            min_volume_surge: 2.0,
            max_position_size: 100,
            risk_per_trade: 0.02
          }
        },
        config: {
          budget: { global_cap: 1000 },
          data_collection: { duration: 'continuous' }
        },
        idempotent: true
      };

      const response = await startTradingSession(sessionData);
      addNotification({
        type: 'success',
        message: `Live trading session started: ${response.data?.session_id}`,
      });
      loadDashboardData();
    } catch (error) {
      addNotification({
        type: 'error',
        message: 'Failed to start live trading session',
      });
    }
  }, [startTradingSession, addNotification, loadDashboardData]);

  const handleQuickTradeSetup = useCallback(() => {
    // Navigate to trading page (would use Next.js router)
    console.log('Navigate to trading page');
  }, []);

  const handleRiskManagement = useCallback(() => {
    // Navigate to risk management page
    console.log('Navigate to risk management page');
  }, []);

  const handlePerformanceReport = useCallback(async () => {
    try {
      const perf = await fetchTradingPerformance();
      if (perf) {
        addNotification({
          type: 'info',
          message: `Performance Report: Win Rate ${perf.win_rate?.toFixed(1)}%, P&L $${perf.total_pnl?.toFixed(2)}`,
        });
      }
    } catch (error) {
      addNotification({
        type: 'error',
        message: 'Failed to generate performance report',
      });
    }
  }, [fetchTradingPerformance, addNotification]);

  // Emergency stop implementation
  const handleEmergencyStop = useCallback(async () => {
    console.warn('🚨 FINANCIAL SAFETY: Emergency stop activated');

    // Stop active session
    if (currentSession?.sessionId) {
      try {
        await stopTradingSession(currentSession.sessionId);
      } catch (error) {
        console.error('Failed to stop session:', error);
      }
    }

    // Disconnect WebSocket
    wsService.disconnect();

    // Clear store data
    useDashboardStore.getState().reset();
    useTradingStore.getState().reset();

    // Notify user
    addNotification({
      type: 'error',
      message: 'EMERGENCY STOP: All trading operations halted',
      autoHide: false,
    });

    // Block trading buttons
    document.querySelectorAll('[data-trading-action]').forEach(button => {
      (button as HTMLButtonElement).disabled = true;
    });

    // Dispatch emergency event
    const event = new CustomEvent('emergencyStop', {
      detail: { timestamp: Date.now() }
    });
    window.dispatchEvent(event);
  }, [currentSession, stopTradingSession, addNotification]);

  const handleStartBacktest = useCallback(async () => {
    try {
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

      const response = await startTradingSession(sessionData);
      addNotification({
        type: 'success',
        message: `Backtest started: ${response.data?.session_id}`,
      });
      loadDashboardData();
    } catch (error) {
      addNotification({
        type: 'error',
        message: 'Failed to start backtest',
      });
    }
  }, [startTradingSession, addNotification, loadDashboardData]);

  const handleStartDataCollection = useCallback(async () => {
    try {
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

      const response = await startTradingSession(sessionData);
      addNotification({
        type: 'success',
        message: `Data collection started: ${response.data?.session_id}`,
      });
      loadDashboardData();
    } catch (error) {
      addNotification({
        type: 'error',
        message: 'Failed to start data collection',
      });
    }
  }, [startTradingSession, addNotification, loadDashboardData]);

  // Loading state
  if (dashboardLoading) {
    return (
      <Box sx={{ flexGrow: 1, p: 4, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Box sx={{
            width: 80,
            height: 80,
            borderRadius: '50%',
            bgcolor: 'primary.main',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mx: 'auto',
            mb: 3,
            animation: 'pulse 2s infinite ease-in-out'
          }}>
            <ChartIcon sx={{ fontSize: 40, color: 'white' }} />
          </Box>
          <Typography variant="h4" sx={{ mb: 2, fontWeight: 600 }}>
            Loading Trading Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Connecting to backend services and loading market data...
          </Typography>
          <CircularProgress size={40} thickness={4} sx={{ color: 'primary.main' }} />
        </Box>

        {/* Loading steps */}
        <Box sx={{ maxWidth: 400, width: '100%' }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Initializing components:
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {[
              'Connecting to backend API',
              'Loading wallet balance',
              'Fetching trading performance',
              'Initializing market scanner',
              'Setting up real-time updates'
            ].map((step, index) => (
              <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CheckCircle sx={{ fontSize: 16, color: 'success.main' }} />
                <Typography variant="body2" color="text.secondary">{step}</Typography>
              </Box>
            ))}
          </Box>
        </Box>
      </Box>
    );
  }

  // Error state
  if (dashboardError) {
    return (
      <Box sx={{ flexGrow: 1, p: 4, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <Box sx={{ textAlign: 'center', maxWidth: 500 }}>
          <Box sx={{
            width: 80,
            height: 80,
            borderRadius: '50%',
            bgcolor: 'error.main',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mx: 'auto',
            mb: 3
          }}>
            <ErrorIcon sx={{ fontSize: 40, color: 'white' }} />
          </Box>
          <Typography variant="h4" sx={{ mb: 2, fontWeight: 600 }}>
            Dashboard Error
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            {dashboardError}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
            This might be due to backend connectivity issues or API unavailability.
            Please check your connection and try again.
          </Typography>
          <Button
            variant="contained"
            startIcon={<RefreshIcon />}
            onClick={() => loadDashboardData(true)}
            size="large"
            sx={{ borderRadius: 2, px: 4, py: 1.5, fontWeight: 600 }}
          >
            Retry Connection
          </Button>
        </Box>
      </Box>
    );
  }

  return (
    <ErrorBoundary financial={true}>
      <Box sx={{ flexGrow: 1, p: 4 }}>
        {/* Header Section */}
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Box>
              <Typography variant="h3" component="h1" sx={{ fontWeight: 700, mb: 1, background: 'linear-gradient(45deg, #00d4aa 30%, #6366f1 90%)', backgroundClip: 'text', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                🚀 Crypto Trading Dashboard
              </Typography>
              <Typography variant="subtitle1" color="text.secondary">
                Advanced Pump & Dump Detection System
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={() => loadDashboardData()}
                disabled={dashboardLoading}
                sx={{ borderRadius: 2 }}
              >
                Refresh Data
              </Button>
              <Box sx={{ position: 'relative' }}>
                <Badge badgeContent={activeSignals.length} color="error" sx={{ '& .MuiBadge-badge': { fontSize: '0.75rem', height: 20, minWidth: 20 } }}>
                  <IconButton sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
                    <NotificationsIcon />
                  </IconButton>
                </Badge>
              </Box>
            </Box>
          </Box>

          {/* System Status */}
          <SystemStatusIndicator showDetails={false} />
        </Box>

        {/* Quick Actions */}
        <Card sx={{ mb: 4, p: 3 }}>
          <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
            Quick Actions
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={4} lg={2.4}>
              <Button
                variant="contained"
                color="success"
                fullWidth
                startIcon={<FlashIcon />}
                size="large"
                sx={{ py: 2, borderRadius: 2, fontWeight: 600 }}
                onClick={handleStartPumpScanner}
              >
                Start Pump Scanner
              </Button>
            </Grid>
            <Grid item xs={12} sm={6} md={4} lg={2.4}>
              <Button
                variant="contained"
                color="primary"
                fullWidth
                startIcon={<PlayIcon />}
                size="large"
                sx={{ py: 2, borderRadius: 2, fontWeight: 600 }}
                onClick={handleQuickTradeSetup}
              >
                Live Trading
              </Button>
            </Grid>
            <Grid item xs={12} sm={6} md={4} lg={2.4}>
              <Button
                variant="contained"
                color="secondary"
                fullWidth
                startIcon={<TimelineIcon />}
                size="large"
                sx={{ py: 2, borderRadius: 2, fontWeight: 600 }}
                onClick={handleStartBacktest}
              >
                Run Backtest
              </Button>
            </Grid>
            <Grid item xs={12} sm={6} md={4} lg={2.4}>
              <Button
                variant="outlined"
                color="info"
                fullWidth
                startIcon={<ChartIcon />}
                size="large"
                sx={{ py: 2, borderRadius: 2, fontWeight: 600 }}
                onClick={handleStartDataCollection}
              >
                Collect Data
              </Button>
            </Grid>
            <Grid item xs={12} sm={6} md={4} lg={2.4}>
              <Button
                variant="outlined"
                color="warning"
                fullWidth
                startIcon={<SecurityIcon />}
                size="large"
                sx={{ py: 2, borderRadius: 2, fontWeight: 600 }}
                onClick={handleRiskManagement}
              >
                Risk Management
              </Button>
            </Grid>
          </Grid>
        </Card>

        <Grid container spacing={4}>
          {/* Market Scanner */}
          <Grid item xs={12} lg={8}>
            <Card sx={{ p: 0 }}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <ChartIcon color="primary" sx={{ mr: 1.5, fontSize: 28 }} />
                    <Box>
                      <Typography variant="h5" sx={{ fontWeight: 600 }}>
                        Market Scanner
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Real-time Pump & Dump Detection
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <Chip
                      label={`${marketData.length} Symbols Tracked`}
                      size="small"
                      color="info"
                      variant="outlined"
                      sx={{ fontWeight: 500 }}
                    />
                    <Chip
                      label="Live"
                      size="small"
                      color="success"
                      sx={{ fontWeight: 500 }}
                    />
                  </Box>
                </Box>

                <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, overflow: 'hidden' }}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600, fontSize: '0.875rem' }}>Symbol</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.875rem' }}>Price</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.875rem' }}>24h Change</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.875rem' }}>Volume</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.875rem' }}>Pump Magnitude</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.875rem' }}>Volume Surge</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600, fontSize: '0.875rem' }}>Confidence</TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600, fontSize: '0.875rem' }}>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {marketData.map((data) => (
                        <TableRow key={data.symbol} hover sx={{ '&:hover': { bgcolor: 'rgba(0, 212, 170, 0.04)' } }}>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <Avatar sx={{ width: 32, height: 32, mr: 1.5, bgcolor: 'primary.main', fontSize: '0.875rem', fontWeight: 600 }}>
                                {data.symbol.split('_')[0].slice(0, 2).toUpperCase()}
                              </Avatar>
                              <Box>
                                <Typography variant="body1" fontWeight={600}>
                                  {data.symbol.replace('_', '/')}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {data.symbol.split('_')[1]}
                                </Typography>
                              </Box>
                            </Box>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body1" fontWeight={500}>
                              ${data.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography
                              variant="body1"
                              sx={{
                                color: data.priceChange24h >= 0 ? 'success.main' : 'error.main',
                                fontWeight: 500,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'flex-end'
                              }}
                            >
                              {data.priceChange24h >= 0 ? <TrendingUpIcon sx={{ mr: 0.5, fontSize: 16 }} /> : <TrendingDownIcon sx={{ mr: 0.5, fontSize: 16 }} />}
                              {data.priceChange24h >= 0 ? '+' : ''}{data.priceChange24h.toFixed(2)}%
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body1" fontWeight={500}>
                              {(data.volume24h / 1000000).toFixed(1)}M
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Chip
                              label={`${data.pumpMagnitude.toFixed(1)}%`}
                              size="small"
                              color={data.pumpMagnitude > 15 ? 'error' : data.pumpMagnitude > 8 ? 'warning' : 'success'}
                              variant="filled"
                              sx={{ fontWeight: 500, minWidth: 60 }}
                            />
                          </TableCell>
                          <TableCell align="right">
                            <Chip
                              label={`${data.volumeSurge.toFixed(1)}x`}
                              size="small"
                              color={data.volumeSurge > 5 ? 'error' : data.volumeSurge > 3 ? 'warning' : 'info'}
                              variant="filled"
                              sx={{ fontWeight: 500, minWidth: 50 }}
                            />
                          </TableCell>
                          <TableCell align="right">
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                              <Typography variant="body1" sx={{ color: 'primary.main', fontWeight: 600, mr: 1 }}>
                                {data.confidenceScore}%
                              </Typography>
                              <Box sx={{
                                width: 8,
                                height: 8,
                                borderRadius: '50%',
                                bgcolor: data.confidenceScore > 70 ? 'success.main' : data.confidenceScore > 40 ? 'warning.main' : 'error.main'
                              }} />
                            </Box>
                          </TableCell>
                          <TableCell align="center">
                            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                              <Tooltip title="Execute Trade">
                                <IconButton size="small" color="primary" sx={{ bgcolor: 'primary.main', color: 'white', '&:hover': { bgcolor: 'primary.dark' } }}>
                                  <PlayIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="View Details">
                                <IconButton size="small" color="info" sx={{ bgcolor: 'info.main', color: 'white', '&:hover': { bgcolor: 'info.dark' } }}>
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

          {/* Active Signals, Indicators & Risk Panel */}
          <Grid item xs={12} lg={4}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              {/* Active Signals */}
              <Card sx={{ flex: 1 }}>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Badge badgeContent={activeSignals.length} color="error" sx={{ '& .MuiBadge-badge': { fontSize: '0.75rem', height: 20, minWidth: 20 } }}>
                        <NotificationsIcon color="error" sx={{ mr: 1.5, fontSize: 24 }} />
                      </Badge>
                      <Box>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          Active Signals
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Real-time alerts
                        </Typography>
                      </Box>
                    </Box>
                    <Chip
                      label="Live"
                      size="small"
                      color="success"
                      sx={{ fontWeight: 500 }}
                    />
                  </Box>

                  {activeSignals.length > 0 ? (
                    <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                      <List dense sx={{ p: 0 }}>
                        {activeSignals.map((signal) => (
                          <ListItem key={signal.id} sx={{ px: 0, py: 1.5, borderRadius: 1, mb: 1, bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
                            <ListItemIcon sx={{ minWidth: 40 }}>
                              <Box sx={{
                                width: 32,
                                height: 32,
                                borderRadius: '50%',
                                bgcolor: signal.signalType === 'pump' ? 'error.main' : 'warning.main',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                              }}>
                                <FlashIcon sx={{ color: 'white', fontSize: 16 }} />
                              </Box>
                            </ListItemIcon>
                            <ListItemText
                              primary={
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                  <Typography variant="body1" fontWeight={600}>
                                    {signal.symbol.replace('_', '/')}
                                  </Typography>
                                  <Chip
                                    label={signal.signalType.toUpperCase()}
                                    size="small"
                                    color={signal.signalType === 'pump' ? 'error' : 'warning'}
                                    sx={{ fontSize: '0.7rem', height: 20 }}
                                  />
                                </Box>
                              }
                              secondary={
                                <Box>
                                  <Typography variant="caption" color="text.secondary">
                                    Magnitude: <span style={{ color: signal.signalType === 'pump' ? '#ef4444' : '#f59e0b', fontWeight: 500 }}>{signal.magnitude.toFixed(1)}%</span>
                                  </Typography>
                                  <br />
                                  <Typography variant="caption" color="text.secondary">
                                    Confidence: <span style={{ color: '#00d4aa', fontWeight: 500 }}>{signal.confidence}%</span> • {new Date(signal.timestamp).toLocaleTimeString()}
                                  </Typography>
                                </Box>
                              }
                            />
                            <ListItemSecondaryAction>
                              <Button
                                size="small"
                                variant="contained"
                                color="success"
                                sx={{ borderRadius: 1, fontSize: '0.75rem', px: 2 }}
                              >
                                Trade
                              </Button>
                            </ListItemSecondaryAction>
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  ) : (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                      <Box sx={{
                        width: 64,
                        height: 64,
                        borderRadius: '50%',
                        bgcolor: 'rgba(255, 255, 255, 0.05)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        mx: 'auto',
                        mb: 2
                      }}>
                        <NotificationsIcon sx={{ fontSize: 32, color: 'text.disabled' }} />
                      </Box>
                      <Typography variant="body1" color="text.secondary" sx={{ mb: 1 }}>
                        No active signals
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Waiting for market opportunities...
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>

              {/* Live Indicators */}
              <Card>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Badge badgeContent={indicators.length} color="info" sx={{ '& .MuiBadge-badge': { fontSize: '0.75rem', height: 20, minWidth: 20 } }}>
                        <TimelineIcon color="info" sx={{ mr: 1.5, fontSize: 24 }} />
                      </Badge>
                      <Box>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          Live Indicators
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Real-time VWAP values
                        </Typography>
                      </Box>
                    </Box>
                    <Chip
                      label="Live"
                      size="small"
                      color="success"
                      sx={{ fontWeight: 500 }}
                    />
                  </Box>

                  {indicators.length > 0 ? (
                    <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                      <List dense sx={{ p: 0 }}>
                        {indicators.map((indicator) => (
                          <ListItem key={`${indicator.symbol}-${indicator.name}`} sx={{ px: 0, py: 1.5, borderRadius: 1, mb: 1, bgcolor: 'rgba(0, 212, 170, 0.04)' }}>
                            <ListItemIcon sx={{ minWidth: 40 }}>
                              <Box sx={{
                                width: 32,
                                height: 32,
                                borderRadius: '50%',
                                bgcolor: 'info.main',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                              }}>
                                <TimelineIcon sx={{ color: 'white', fontSize: 16 }} />
                              </Box>
                            </ListItemIcon>
                            <ListItemText
                              primary={
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                  <Typography variant="body1" fontWeight={600}>
                                    {indicator.symbol.replace('_', '/')}
                                  </Typography>
                                  <Chip
                                    label={indicator.name}
                                    size="small"
                                    color="info"
                                    sx={{ fontSize: '0.7rem', height: 20 }}
                                  />
                                </Box>
                              }
                              secondary={
                                <Box>
                                  <Typography variant="caption" color="text.secondary">
                                    Value: <span style={{ color: '#00d4aa', fontWeight: 500 }}>${indicator.value.toFixed(4)}</span>
                                  </Typography>
                                  <br />
                                  <Typography variant="caption" color="text.secondary">
                                    Updated: {new Date(indicator.timestamp).toLocaleTimeString()}
                                  </Typography>
                                </Box>
                              }
                            />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  ) : (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                      <Box sx={{
                        width: 64,
                        height: 64,
                        borderRadius: '50%',
                        bgcolor: 'rgba(0, 212, 170, 0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        mx: 'auto',
                        mb: 2
                      }}>
                        <TimelineIcon sx={{ fontSize: 32, color: 'info.main' }} />
                      </Box>
                      <Typography variant="body1" color="text.secondary" sx={{ mb: 1 }}>
                        Waiting for live indicators
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        VWAP values will appear here when trading session starts
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>

              {/* Risk & Performance Summary */}
              <Card>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                    <SecurityIcon color="warning" sx={{ mr: 1.5, fontSize: 24 }} />
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Portfolio & Risk
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Performance metrics
                      </Typography>
                    </Box>
                  </Box>

                  <Box sx={{ mb: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="body2" color="text.secondary">Portfolio Value</Typography>
                      <Typography variant="h6" sx={{ color: 'primary.main', fontWeight: 600 }}>
                        ${walletBalance?.total_usd_estimate?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                      </Typography>
                    </Box>

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="body2" color="text.secondary">Today's P&L</Typography>
                      <Typography
                        variant="body1"
                        sx={{
                          color: performance?.total_pnl && performance.total_pnl >= 0 ? 'success.main' : 'error.main',
                          fontWeight: 600,
                          display: 'flex',
                          alignItems: 'center'
                        }}
                      >
                        {performance?.total_pnl && performance.total_pnl >= 0 ? '+' : ''}${performance?.total_pnl ? performance.total_pnl.toFixed(2) : '0.00'}
                      </Typography>
                    </Box>

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="body2" color="text.secondary">Active Positions</Typography>
                      <Typography variant="body1" fontWeight={500}>
                        {performance?.active_positions || 0}
                      </Typography>
                    </Box>

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="body2" color="text.secondary">Win Rate</Typography>
                      <Typography variant="body1" fontWeight={500}>
                        {performance?.win_rate ? `${performance.win_rate.toFixed(1)}%` : '0%'}
                      </Typography>
                    </Box>
                  </Box>

                  <Divider sx={{ my: 2 }} />

                  <Box sx={{ display: 'flex', gap: 1.5 }}>
                    <Button
                      size="small"
                      variant="outlined"
                      color="warning"
                      fullWidth
                      sx={{ borderRadius: 1, fontWeight: 500 }}
                      onClick={handleEmergencyStop}
                    >
                      Emergency Stop
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      color="info"
                      fullWidth
                      sx={{ borderRadius: 1, fontWeight: 500 }}
                    >
                      Close All
                    </Button>
                  </Box>
                </CardContent>
              </Card>

              {/* System Status */}
              <Card>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <SpeedIcon color="info" sx={{ mr: 1.5, fontSize: 24 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      System Status
                    </Typography>
                  </Box>
                  <SystemStatusIndicator showDetails={true} />
                </CardContent>
              </Card>

              {/* Health Alerts */}
              {healthStatus.alerts.length > 0 && (
                <Card>
                  <CardContent sx={{ p: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <WarningIcon color="warning" sx={{ mr: 1.5, fontSize: 24 }} />
                        <Box>
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            Health Alerts
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Real-time system notifications
                          </Typography>
                        </Box>
                      </Box>
                      <Chip
                        label={`${healthStatus.alerts.length} Active`}
                        size="small"
                        color="warning"
                        sx={{ fontWeight: 500 }}
                      />
                    </Box>

                    <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                      <List dense sx={{ p: 0 }}>
                        {healthStatus.alerts.slice(0, 5).map((alert) => (
                          <ListItem key={alert.alert_id} sx={{ px: 0, py: 1 }}>
                            <ListItemIcon sx={{ minWidth: 40 }}>
                              <Box sx={{
                                width: 24,
                                height: 24,
                                borderRadius: '50%',
                                bgcolor: alert.level === 'critical' ? 'error.main' :
                                        alert.level === 'error' ? 'error.main' :
                                        alert.level === 'warning' ? 'warning.main' : 'info.main',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                              }}>
                                {alert.level === 'critical' || alert.level === 'error' ? (
                                  <ErrorIcon sx={{ color: 'white', fontSize: 14 }} />
                                ) : alert.level === 'warning' ? (
                                  <WarningIcon sx={{ color: 'white', fontSize: 14 }} />
                                ) : (
                                  <CheckCircle sx={{ color: 'white', fontSize: 14 }} />
                                )}
                              </Box>
                            </ListItemIcon>
                            <ListItemText
                              primary={
                                <Typography variant="body2" fontWeight={600}>
                                  {alert.alert_name}
                                </Typography>
                              }
                              secondary={
                                <Box>
                                  <Typography variant="caption" color="text.secondary">
                                    {alert.message}
                                  </Typography>
                                  <br />
                                  <Typography variant="caption" color="text.secondary">
                                    {new Date(alert.timestamp).toLocaleTimeString()}
                                    {alert.service && ` • ${alert.service}`}
                                  </Typography>
                                </Box>
                              }
                            />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  </CardContent>
                </Card>
              )}
            </Box>
          </Grid>
        </Grid>
      </Box>
    </ErrorBoundary>
  );
}
