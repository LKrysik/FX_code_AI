'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useVisibilityAwareInterval } from '@/hooks/useVisibilityAwareInterval';
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
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Storage as StorageIcon,
  Assessment as AssessmentIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  ShowChart as ChartIcon,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import { config } from '@/utils/config';
import { wsService } from '@/services/websocket';
import { useWebSocketStore } from '@/stores/websocketStore';
import { SystemStatusIndicator } from '@/components/common/SystemStatusIndicator';
import { debounce } from 'lodash';
import { useRouter } from 'next/navigation';
import {
  getSessionStatusColor,
  getSessionStatusIcon,
  type SessionStatusType
} from '@/utils/statusUtils';

interface DataCollectionSession {
  session_id: string;
  status: string;
  symbols: string[];
  data_types: string[];
  duration: string;
  start_time?: string;
  end_time?: string;
  records_collected: number;
  storage_path: string;
  created_at: string;
  error_message?: string;

  // WebSocket progress fields
  progress_percentage?: number;
  eta_seconds?: number;
  current_date?: string;
  command_type?: string;
}

const dataTypes = ['price', 'orderbook', 'trades'];

// Helper function to format ETA
const formatETA = (etaSeconds: number): string => {
  if (etaSeconds <= 0) return 'Complete';

  const hours = Math.floor(etaSeconds / 3600);
  const minutes = Math.floor((etaSeconds % 3600) / 60);
  const seconds = etaSeconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  } else {
    return `${seconds}s`;
  }
};

export default function DataCollectionPage() {
  // Use reactive WebSocket store instead of polling
  const { isConnected } = useWebSocketStore();
  const router = useRouter();

  const [sessions, setSessions] = useState<DataCollectionSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<DataCollectionSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [symbolsError, setSymbolsError] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info' | 'warning'}>({
    open: false,
    message: '',
    severity: 'info'
  });

  // Backend health check - only as backup (WebSocket provides real-time status)
  const checkBackendConnection = useCallback(async () => {
    try {
      await apiService.healthCheck();
    } catch (error) {
      // Silently handle health check failures
      console.warn('Health check failed:', error);
    }
  }, []);

  // Reduced polling frequency - only backup every 5 minutes when WebSocket unavailable
  useVisibilityAwareInterval(checkBackendConnection, 300000); // 5 minutes

  // Form state for new data collection
  const [collectionForm, setCollectionForm] = useState({
    symbols: ['BTC_USDT'],
    duration_value: 1,
    duration_unit: 'hours' as 'seconds' | 'minutes' | 'hours' | 'days',
    storage_path: 'data',
    config: {
      max_file_size_mb: 100,
      compression_enabled: true
    }
  });

  useEffect(() => {
    loadDataCollectionSessions();
    loadAvailableSymbols();
  }, []);

  // When symbols are loaded, initialize form selection from config
  useEffect(() => {
    // If available symbols are loaded and no symbols are selected in the form (or only the default one),
    // pre-select all available symbols for user convenience.
    if (availableSymbols.length > 0 && collectionForm.symbols.length <= 1) { // More robust condition
      setCollectionForm(prev => ({
        ...prev,
        symbols: availableSymbols
      }));
    }
  }, [availableSymbols]);
  // Debounced session update function for performance (reduced delay for snappier UI)
  const debouncedUpdateSession = useMemo(
    () => debounce((message: any) => {
      console.log('[debouncedUpdateSession] Processing message:', message);

      // Extract data from WebSocket message format
      const sessionData = message.data || message;
      console.log('[debouncedUpdateSession] Extracted sessionData:', sessionData);

      setSessions(prev => prev.map(session => {
        if (session.session_id === sessionData.session_id) {
          // Enhanced progress parsing with multiple fallbacks
          let progress_percentage = session.progress_percentage;
          let eta_seconds = session.eta_seconds;
          let current_date = session.current_date;
          let records_collected = session.records_collected;

          // Handle progress data from backend ExecutionProgress.to_dict() format
          if (typeof sessionData.progress === 'number') {
            progress_percentage = sessionData.progress;
          } else if (sessionData.progress && typeof sessionData.progress === 'object') {
            // Backend sends: {percentage, eta_seconds, current_date}
            progress_percentage = sessionData.progress.percentage;
            eta_seconds = sessionData.progress.eta_seconds;
            current_date = sessionData.progress.current_date;
          }

          // Handle records_collected with multiple fallbacks - backend sends at top level
          if (sessionData.records_collected !== undefined) {
            records_collected = sessionData.records_collected;
          } else if (sessionData.trading_stats?.records_collected !== undefined) {
            records_collected = sessionData.trading_stats.records_collected;
          } else if (sessionData.progress?.current_step !== undefined) {
            records_collected = sessionData.progress.current_step;
          }

          console.log('[debouncedUpdateSession] Progress parsing:', {
            sessionData_progress: sessionData.progress,
            sessionData_records: sessionData.records_collected,
            sessionData_trading_stats: sessionData.trading_stats,
            parsed_percentage: progress_percentage,
            parsed_records: records_collected,
            parsed_eta: eta_seconds
          });

          console.log('[UI UPDATE] 🎯 Updating progress bar and records count:');
          console.log('[UI UPDATE] 🎯 Progress:', progress_percentage + '%');
          console.log('[UI UPDATE] 🎯 Records:', records_collected.toLocaleString());
          console.log('[UI UPDATE] 🎯 ETA:', eta_seconds ? formatETA(eta_seconds) : 'N/A');

          const updatedSession = {
            ...session,
            ...sessionData,
            progress_percentage,
            eta_seconds,
            current_date,
            records_collected,
            status: sessionData.status || session.status,
            error_message: sessionData.error_message || session.error_message
          };

          console.log('[debouncedUpdateSession] Updated session:', updatedSession);
          console.log('[STATE UPDATE] 💾 React state will be updated with new progress data');
          return updatedSession;
        }
        return session;
      }));
    }, 200), // Reduced from 500ms to 200ms for snappier real-time updates
    []
  );

  // WebSocket integration for real-time updates with connection state awareness
  useEffect(() => {
    let subscribed = false;

    const setupWebSocketSubscription = () => {
      if (subscribed) return;

      console.log('[WebSocket] Setting up subscription');

      // Add debug logging to see what messages are received
      const unsubscribe = wsService.addSessionUpdateListener((message) => {
        console.log('[WebSocket] 📨 RECEIVED MESSAGE:', {
          type: message?.type,
          stream: message?.stream,
          hasData: !!message?.data,
          dataKeys: message?.data ? Object.keys(message.data) : [],
          session_id: message?.data?.session_id,
          timestamp: message?.timestamp
        });

        // Special logging for ALL data messages
        if (message?.type === 'data') {
          console.log('[WebSocket] 📊 DATA MESSAGE RECEIVED:', {
            stream: message.stream,
            session_id: message.data?.session_id,
            progress_percentage: message.data?.progress?.percentage,
            records_collected: message.data?.records_collected,
            command_type: message.data?.command_type,
            status: message.data?.status
          });
        }

        // Special logging for progress messages
        if (message?.type === 'data' && message?.stream === 'execution_status') {
          console.log('[WebSocket] 🎯 PROGRESS MESSAGE RECEIVED:', {
            session_id: message.data?.session_id,
            progress_percentage: message.data?.progress?.percentage,
            records_collected: message.data?.records_collected,
            command_type: message.data?.command_type
          });
        }

        if (!message) return;

        // Extract data from WebSocket message format
        const payload = message.data || message;
        console.log('[WebSocket] Extracted payload:', payload);

        // Check if this is a data collection message
        const isDataCollectionMessage = (
          payload?.command_type === 'collect' ||
          payload?.mode === 'collect' ||
          message.type === 'execution_result' ||
          message.type === 'data' && message.stream === 'execution_status'
        );

        console.log('[WebSocket] Is data collection message:', isDataCollectionMessage, {
          command_type: payload?.command_type,
          mode: payload?.mode,
          message_type: message.type,
          stream: message.stream,
          payload_keys: Object.keys(payload || {})
        });

        if (isDataCollectionMessage) {
          console.log('[WebSocket] Processing data collection message');

          // Handle execution_result messages (completion/failure)
          if (message.type === 'execution_result') {
            console.log('[WebSocket] Handling execution_result message');
            const progressData = payload.final_results?.progress;
            const resultPayload = {
              session_id: payload.session_id,
              status: payload.status,
              error_message: payload.error_message,
              command_type: payload.command_type || 'collect',
              // Extract records_collected from correct location
              records_collected: progressData?.trading_stats?.records_collected ||
                                progressData?.records_collected ||
                                payload.records_collected || 0,
              // Provide progress structure that debouncedUpdateSession expects
              progress: {
                percentage: payload.status === 'completed' ? 100 :
                           (progressData?.progress?.percentage || progressData?.percentage || 0),
                eta_seconds: progressData?.progress?.eta_seconds || progressData?.eta_seconds,
                current_date: progressData?.progress?.current_date || progressData?.current_date
              }
            };
            console.log('[WebSocket] Calling debouncedUpdateSession with result payload:', resultPayload);
            debouncedUpdateSession({
              type: 'execution_result',
              data: resultPayload
            });
          } else if (message.type === 'data' && message.stream === 'execution_status') {
            // Handle regular execution_status progress messages
            console.log('[WebSocket] Handling execution_status progress message');

            // Ensure the payload has the expected structure for debouncedUpdateSession
            const progressPayload = {
              session_id: payload.session_id,
              status: payload.status || 'running',
              command_type: payload.command_type || 'collect',
              records_collected: payload.records_collected || payload.trading_stats?.records_collected || 0,
              progress: payload.progress || {
                percentage: payload.progress_percentage || 0,
                eta_seconds: payload.eta_seconds,
                current_date: payload.current_date
              },
              trading_stats: payload.trading_stats || {},
              error_message: payload.error_message
            };

            console.log('[WebSocket] 📊 PROGRESS UPDATE - Session:', progressPayload.session_id);
            console.log('[WebSocket] 📊 Records collected:', progressPayload.records_collected);
            console.log('[WebSocket] 📊 Progress percentage:', progressPayload.progress?.percentage || 0);
            console.log('[WebSocket] 📊 ETA seconds:', progressPayload.progress?.eta_seconds);

            debouncedUpdateSession({
              type: 'data',
              data: progressPayload
            });
          } else {
            // Handle other execution_status messages
            console.log('[WebSocket] Handling other execution_status message, calling debouncedUpdateSession with message:', message);
            debouncedUpdateSession(message);
          }
        } else {
          console.log('[WebSocket] Ignoring non-data-collection message');
        }

        if (payload?.status === 'failed' || payload?.error_message) {
          console.log('[WebSocket] Handling error status');
          setSessions(prev => prev.map(session => {
            if (session.session_id === payload.session_id) {
              return {
                ...session,
                status: 'error',
                error_message: payload.error_message || session.error_message
              };
            }
            return session;
          }));

          setSnackbar({
            open: true,
            message: `Data collection error: ${payload.error_message || 'Unknown error'}`,
            severity: 'error'
          });
        }
      });

      // Subscribe to execution_status with retry logic
      const subscribeWithRetry = () => {
        try {
          console.log('[WebSocket] 🔄 Subscribing to execution_status');
          wsService.subscribe('execution_status');
          console.log('[WebSocket] ✅ Successfully subscribed to execution_status');

          // Log subscription summary to verify
          setTimeout(() => {
            wsService.logSubscriptionSummary();
          }, 1000);

          subscribed = true;
        } catch (error) {
          console.error('[WebSocket] ❌ Subscription failed, retrying in 2s:', error);
          setTimeout(subscribeWithRetry, 2000);
        }
      };

      // Also subscribe immediately when WebSocket connects
      const handleWebSocketConnect = () => {
        console.log('[WebSocket] 🔗 Connection established, subscribing to execution_status');
        if (!subscribed) {
          subscribeWithRetry();
        }
      };

      // Set up connection callback
      wsService.setCallbacks({
        onConnect: handleWebSocketConnect,
        onDisconnect: (reason) => {
          console.log('[WebSocket] 🔌 Disconnected:', reason);
          subscribed = false;
        },
        onError: (error) => {
          console.error('[WebSocket] ❌ Connection error:', error);
        }
      });

      // Check if WebSocket is connected using reactive store
      if (isConnected) {
        console.log('[WebSocket] Already connected, subscribing immediately');
        subscribeWithRetry();
      } else {
        console.log('[WebSocket] Waiting for connection before subscribing');


        // Also try to subscribe after a short delay as fallback
        setTimeout(() => {
          if (!subscribed && isConnected) {
            console.log('[WebSocket] Fallback: trying subscription after delay');
            subscribeWithRetry();
          }
        }, 2000);
      }

      return unsubscribe;
    };

    const unsubscribe = setupWebSocketSubscription();

    return () => {
      console.log('[WebSocket] Cleaning up WebSocket listener');
      if (unsubscribe) unsubscribe();
      if (typeof (debouncedUpdateSession as any).cancel === 'function') {
        (debouncedUpdateSession as any).cancel();
      }
      subscribed = false;
    };
  }, [debouncedUpdateSession, isConnected]);

  const loadAvailableSymbols = async () => {
    try {
      const symbols = await apiService.getSymbols();
      setAvailableSymbols(symbols);
      setSymbolsError(null);
    } catch (error) {
      console.error('Failed to load available symbols from', config.apiUrl, error);
      setSymbolsError(`Failed to load symbols from ${config.apiUrl}. Check backend and NEXT_PUBLIC_API_URL.`);
      // Do not silently fallback; surface the error
      setAvailableSymbols([]);
    }
  };

  const loadDataCollectionSessions = async () => {
    setLoading(true);
    try {
      // Get both current session and historical sessions
      const [sessionStatus, historicalSessions] = await Promise.all([
        apiService.getExecutionStatus().catch(() => null),
        apiService.getDataCollectionSessions(50, true).catch(() => ({ sessions: [] }))
      ]);

      const allSessions: DataCollectionSession[] = [];

      // Add current active session if exists
      if (sessionStatus && sessionStatus.session_id && sessionStatus.mode === 'collect') {
        const currentSession: DataCollectionSession = {
          session_id: sessionStatus.session_id,
          status: sessionStatus.status || 'unknown',
          symbols: sessionStatus.symbols || [],
          data_types: sessionStatus.data_types || ['price', 'orderbook'],
          duration: sessionStatus.duration || 'continuous',
          start_time: sessionStatus.start_time,
          records_collected: sessionStatus.records_collected || 0,
          storage_path: sessionStatus.storage_path || 'data/historical',
          created_at: sessionStatus.start_time || new Date().toISOString(),
          error_message: sessionStatus.error_message || undefined,
          progress_percentage: typeof sessionStatus.progress === 'object'
            ? sessionStatus.progress?.percentage
            : (typeof sessionStatus.progress === 'number' ? sessionStatus.progress : undefined),
          eta_seconds: typeof sessionStatus.progress === 'object'
            ? sessionStatus.progress?.eta_seconds
            : undefined,
          current_date: typeof sessionStatus.progress === 'object'
            ? sessionStatus.progress?.current_date
            : undefined,
          command_type: sessionStatus.command_type || 'collect'
        };
        allSessions.push(currentSession);
      }

      // Add historical sessions
      if (historicalSessions.sessions) {
        const historicalSessionsFormatted = historicalSessions.sessions.map((session: any) => ({
          session_id: session.session_id || session.id,
          status: session.status || 'completed',
          symbols: session.symbols || [],
          data_types: session.data_types || ['price', 'orderbook'],
          duration: session.duration || 'unknown',
          start_time: session.start_time || session.created_at,
          end_time: session.end_time,
          records_collected: session.records_collected || session.total_records || 0,
          storage_path: session.storage_path || session.path || 'data/historical',
          created_at: session.created_at || session.start_time || new Date().toISOString(),
          error_message: session.error_message || undefined,
          command_type: 'collect'
        }));
        allSessions.push(...historicalSessionsFormatted);
      }

      // Sort by start_time/created_at, most recent first
      allSessions.sort((a, b) => {
        const timeA = new Date(a.start_time || a.created_at).getTime();
        const timeB = new Date(b.start_time || b.created_at).getTime();
        return timeB - timeA;
      });

      setSessions(allSessions);
    } catch (error) {
      console.error('Failed to load data collection sessions:', error);
      setSessions([]);
      setSnackbar({
        open: true,
        message: 'Failed to load data collection sessions',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStartDataCollection = () => {
    setDialogOpen(true);
  };

  const handleStopDataCollection = async (sessionId: string) => {
    try {
      await apiService.stopSession(sessionId);
      setSnackbar({
        open: true,
        message: 'Data collection stopped successfully',
        severity: 'success'
      });
      loadDataCollectionSessions();
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to stop data collection',
        severity: 'error'
      });
    }
  };

  const handleViewResults = async (session: DataCollectionSession) => {
    // For data collection, we can show collection statistics
    setSelectedSession(session);
  };

  const handleCreateDataCollection = async () => {
    try {
      // Basic validation
      if (!collectionForm.symbols || collectionForm.symbols.length === 0) {
        setSnackbar({ open: true, message: 'Please select at least one symbol', severity: 'error' });
        return;
      }
      const unitMap: Record<string, string> = { seconds: 's', minutes: 'm', hours: 'h', days: 'd' };
      const dv = Number((collectionForm as any).duration_value) || 0;
      const durationStr = dv <= 0 ? 'continuous' : `${dv}${unitMap[(collectionForm as any).duration_unit]}`;

      const collectionData = {
        session_type: 'collect',
        strategy_config: { symbols: collectionForm.symbols },
        config: {
          ...collectionForm.config,
          data_path: collectionForm.storage_path,
          duration: durationStr
        },
        idempotent: true
      };

      const response = await apiService.startSession(collectionData);
      const sessionId = (response && (response.data?.session_id || response.session_id)) || 'unknown';

      // Immediately create a running session to show progress bar
      const newSession: DataCollectionSession = {
        session_id: sessionId,
        status: 'running',
        symbols: collectionForm.symbols,
        data_types: ['price', 'orderbook', 'trades'],
        duration: durationStr,
        start_time: new Date().toISOString(),
        records_collected: 0,
        storage_path: collectionForm.storage_path,
        created_at: new Date().toISOString(),
        command_type: 'collect'
      };

      setSessions([newSession]);

      setSnackbar({
        open: true,
        message: `Data collection started: ${sessionId}`,
        severity: 'success'
      });
      setDialogOpen(false);

    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to start data collection',
        severity: 'error'
      });
    }
  };

  const handleDownloadData = (sessionId: string) => {
    // In a real implementation, this would trigger a download
    setSnackbar({
      open: true,
      message: `Downloading data for session ${sessionId}`,
      severity: 'info'
    });
  };

  const handleViewCharts = (session: DataCollectionSession) => {
    // Navigate to chart page with session ID
    router.push(`/data-collection/${session.session_id}/chart`);
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      const result = await apiService.deleteDataCollectionSession(sessionId);
      if (result.success) {
        setSnackbar({
          open: true,
          message: `Session ${sessionId} deleted successfully`,
          severity: 'success'
        });
        // Refresh the sessions list
        await loadDataCollectionSessions();
      } else {
        throw new Error(result.message || 'Failed to delete session');
      }
    } catch (error: any) {
      console.error('Failed to delete session:', error);
      setSnackbar({
        open: true,
        message: `Failed to delete session: ${error.message}`,
        severity: 'error'
      });
    }
  };


  return (
    <Box>
            {symbolsError && (
        <Alert severity="error" sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={loadAvailableSymbols}>
              Retry
            </Button>
          }
        >
          {symbolsError} (API: {config.apiUrl})
        </Alert>
      
      )}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1">
            Data Collection
          </Typography>
          {/* Add System Status */}
          <SystemStatusIndicator showDetails={false} compact={true} />
          {/* WebSocket Status Indicator */}
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              WebSocket:
            </Typography>
            <Chip
              label={isConnected ? "Connected" : "Disconnected"}
              color={isConnected ? "success" : "error"}
              size="small"
              sx={{ ml: 1 }}
            />
            <Button
              size="small"
              variant="outlined"
              onClick={() => wsService.logSubscriptionSummary()}
              sx={{ ml: 1 }}
            >
              Check Status
            </Button>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadDataCollectionSessions}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<PlayIcon />}
            onClick={handleStartDataCollection}
          >
            Start Collection
          </Button>
        </Box>
      </Box>


      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <StorageIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Active Collections</Typography>
              </Box>
              <Typography variant="h4" color="primary">
                {sessions.filter(s => s.status === 'running').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="h6">Completed</Typography>
              </Box>
              <Typography variant="h4" color="success">
                {sessions.filter(s => s.status === 'completed').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <AssessmentIcon color="info" sx={{ mr: 1 }} />
                <Typography variant="h6">Total Records</Typography>
              </Box>
              <Typography variant="h4" color="info">
                {sessions.reduce((sum, s) => sum + s.records_collected, 0).toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <StorageIcon color="secondary" sx={{ mr: 1 }} />
                <Typography variant="h6">Storage Used</Typography>
              </Box>
              <Typography variant="h4" color="secondary">
                ~{(sessions.reduce((sum, s) => sum + s.records_collected, 0) * 0.1).toFixed(1)}MB
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Data Collection Sessions Table */}
      <Paper sx={{ mb: 3 }}>
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6">Data Collection Sessions</Typography>
        </Box>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Session ID</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Symbols</TableCell>
                <TableCell>Data Types</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell align="right">Records</TableCell>
                <TableCell>Storage Path</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sessions.map((session) => (
                <TableRow key={session.session_id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {session.session_id}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(session.created_at).toLocaleDateString()}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={session.status}
                      color={getSessionStatusColor(session.status as SessionStatusType)}
                      size="small"
                      icon={getSessionStatusIcon(session.status as SessionStatusType)}
                    />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {session.symbols.map(symbol => (
                        <Chip key={symbol} label={symbol} size="small" variant="outlined" />
                      ))}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {session.data_types.map(type => (
                        <Chip key={type} label={type} size="small" color="primary" variant="outlined" />
                      ))}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip label={session.duration} size="small" variant="outlined" />
                      {session.status.toLowerCase() === 'error' && (
                        <Tooltip title={session.error_message || 'Unknown error'}>
                          <Chip label="error" color="error" size="small" />
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell align="right">
                    <Box>
                      <Typography variant="body2">
                        {session.records_collected.toLocaleString()}
                      </Typography>
                      {session.status === 'running' && (
                        <Box sx={{ mt: 1, minWidth: 120 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">
                              {session.progress_percentage !== undefined && session.progress_percentage >= 0
                                ? `${session.progress_percentage.toFixed(1)}%`
                                : 'Collecting data...'}
                            </Typography>
                            {session.eta_seconds && session.eta_seconds > 0 && (
                              <Typography variant="caption" color="text.secondary">
                                ETA: {formatETA(session.eta_seconds)}
                              </Typography>
                            )}
                          </Box>
                          <LinearProgress
                            variant={session.progress_percentage !== undefined && session.progress_percentage >= 0 ? "determinate" : "indeterminate"}
                            value={session.progress_percentage !== undefined && session.progress_percentage >= 0
                              ? Math.min(session.progress_percentage, 100)
                              : undefined}
                            color="primary"
                            sx={{ height: 6, borderRadius: 3 }}
                          />
                        </Box>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                      {session.storage_path}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Tooltip title="View Details">
                      <IconButton
                        size="small"
                        onClick={() => handleViewResults(session)}
                      >
                        <AssessmentIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {session.status === 'running' && (
                      <Tooltip title="Stop Collection">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleStopDataCollection(session.session_id)}
                        >
                          <StopIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    <Tooltip title="Download Data">
                      <span>
                        <IconButton
                          size="small"
                          onClick={() => handleDownloadData(session.session_id)}
                          disabled={session.status !== 'completed'}
                        >
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                    {session.status !== 'running' && session.symbols.length > 0 && (
                      <Tooltip title="View Charts">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => handleViewCharts(session)}
                        >
                          <ChartIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    {session.status !== 'running' && (
                      <Tooltip title="Delete Session">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteSession(session.session_id)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {sessions.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      No data collection sessions found. Start your first collection to see results here.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Detailed Results Accordion */}
      {selectedSession && (
        <Accordion key={selectedSession.session_id} expanded={true}> {/* Added key for proper re-rendering */}
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              Collection Details: {selectedSession.session_id}
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Collection Summary
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2">Session ID</Typography>
                      <Typography variant="body2" fontWeight="bold" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {selectedSession.session_id}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2">Status</Typography>
                      <Chip
                        label={selectedSession.status}
                        color={getSessionStatusColor(selectedSession.status as SessionStatusType)}
                        size="small"
                      />
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2">Records Collected</Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {selectedSession.records_collected.toLocaleString()}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2">Storage Path</Typography>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {selectedSession.storage_path}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2">Start Time</Typography>
                      <Typography variant="body2">
                        {selectedSession.start_time ? new Date(selectedSession.start_time).toLocaleString() : 'N/A'}
                      </Typography>
                    </Box>
                  </Box>
                </Paper>
              </Grid>

              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Data Types & Symbols
                  </Typography>
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Data Types Collected:
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 2 }}>
                      {selectedSession.data_types.map(type => (
                        <Chip key={type} label={type} size="small" color="primary" />
                      ))}
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Symbols Monitored:
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {selectedSession.symbols.map(symbol => (
                        <Chip key={symbol} label={symbol} size="small" variant="outlined" />
                      ))}
                    </Box>
                  </Box>
                </Paper>
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Start Data Collection Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Start Data Collection</DialogTitle>
        <DialogContent>
          <Box component="form" sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}> {/* Increased gap for better spacing */}
            <FormControl fullWidth>
              <InputLabel id="symbols-label">Symbols</InputLabel>
              <Select
                multiple
                value={collectionForm.symbols}
                label="Symbols"
                labelId="symbols-label"
                id="symbols-select"
                onChange={(e) => setCollectionForm(prev => ({
                  ...prev,
                  symbols: typeof e.target.value === 'string' ? [e.target.value] : e.target.value
                }))}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} size="small" />
                    ))}
                  </Box>
                )}
              >
                {availableSymbols.map(symbol => (
                  <MenuItem key={symbol} value={symbol}>{symbol}</MenuItem>
                ))}
              </Select>
            </FormControl>


            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField
                fullWidth
                label="Duration Value"
                type="number"
                id="duration-value-input"
                value={(collectionForm as any).duration_value}
                onChange={(e) => setCollectionForm(prev => ({
                  ...prev,
                  duration_value: Math.max(0, parseInt(e.target.value) || 0)
                }))}
                helperText="Enter 0 for continuous"
              />
              <FormControl fullWidth>
                <InputLabel id="duration-unit-label">Unit</InputLabel>
                <Select
                  value={(collectionForm as any).duration_unit}
                  label="Unit"
                  labelId="duration-unit-label"
                  id="duration-unit-select"
                  onChange={(e) => setCollectionForm(prev => ({
                    ...prev,
                    duration_unit: (e.target.value as any)
                  }))}
                >
                  <MenuItem value="seconds">Seconds</MenuItem>
                  <MenuItem value="minutes">Minutes</MenuItem>
                  <MenuItem value="hours">Hours</MenuItem>
                  <MenuItem value="days">Days</MenuItem>
                </Select>
              </FormControl>
            </Box>

            <TextField
              fullWidth
              label="Storage Path"
              id="storage-path-input"
              value={collectionForm.storage_path}
              onChange={(e) => setCollectionForm(prev => ({ ...prev, storage_path: e.target.value }))}
              // Atrybut autoFocus został usunięty, aby zapobiec problemom z renderowaniem etykiety w komponencie Select powyżej
              helperText="Directory where collected data will be stored"
            />

            {/* Collection Interval removed — backend controls cadence */}

            <Alert severity="info">
              <Typography variant="body2">
                <strong>Data Collection:</strong> Continuously gather market data for analysis
                <br />
                Data will be stored as CSV files organized by symbol and date
              </Typography>
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateDataCollection} variant="contained" color="success">
            Start Collection
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
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
