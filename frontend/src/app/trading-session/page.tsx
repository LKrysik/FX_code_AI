'use client';

/**
 * Trading Session Configuration Page
 * ===================================
 * Complete interface for configuring and starting trading sessions.
 * Works for: Live Trading, Paper Trading, Backtesting
 *
 * Uses real API calls to backend:
 * - GET /api/strategies - fetch available strategies
 * - GET /api/data-collection/sessions - fetch data sessions for backtest
 * - POST /sessions/start - start trading session
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Button,
  ToggleButton,
  ToggleButtonGroup,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  Chip,
  Alert,
  AlertTitle,
  Divider,
  Grid,
  Card,
  CardContent,
  CardHeader,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Slider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  CircularProgress,
  Skeleton,
} from '@mui/material';
import {
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Settings as SettingsIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as AttachMoneyIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { apiService } from '@/services/api';
import StrategyPreviewPanel from '@/components/trading/StrategyPreviewPanel';
import SessionMatrix from '@/components/trading/SessionMatrix';
import SymbolRecommendation from '@/components/trading/SymbolRecommendation';

// ============================================================================
// Types
// ============================================================================

interface StrategyData {
  strategy_name: string;
  enabled: boolean;
  description?: string;
  signal_detection?: any;
  entry_conditions?: any;
}

interface DataSession {
  session_id: string;
  status: string;
  symbols: string[];
  prices_count: number;
  duration_seconds: number;
  created_at: number;
  exchange: string;
}

type TradingMode = 'live' | 'paper' | 'backtest';

// ============================================================================
// Main Component
// ============================================================================

export default function TradingSessionPage() {
  const router = useRouter();

  // Data from API
  const [strategies, setStrategies] = useState<StrategyData[]>([]);
  const [dataSessions, setDataSessions] = useState<DataSession[]>([]);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);

  // Loading states
  const [loadingStrategies, setLoadingStrategies] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [startingSession, setStartingSession] = useState(false);

  // Error states
  const [strategiesError, setStrategiesError] = useState<string | null>(null);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);

  // Form state
  const [mode, setMode] = useState<TradingMode>('paper');
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [globalBudget, setGlobalBudget] = useState(1000);
  const [maxPositionSize, setMaxPositionSize] = useState(100);
  const [stopLoss, setStopLoss] = useState(5);
  const [takeProfit, setTakeProfit] = useState(10);
  const [backtestSessionId, setBacktestSessionId] = useState('');
  const [accelerationFactor, setAccelerationFactor] = useState(10);

  // Session status
  const [isSessionRunning, setIsSessionRunning] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // ========================================
  // Data Fetching
  // ========================================

  const fetchStrategies = useCallback(async () => {
    setLoadingStrategies(true);
    setStrategiesError(null);
    try {
      const data = await apiService.get4SectionStrategies();
      setStrategies(data || []);
      // Auto-select first enabled strategy if none selected
      if (selectedStrategies.length === 0 && data?.length > 0) {
        const enabledStrategy = data.find((s: StrategyData) => s.enabled);
        if (enabledStrategy) {
          setSelectedStrategies([enabledStrategy.strategy_name]);
        }
      }
    } catch (error: any) {
      console.error('Failed to fetch strategies:', error);
      setStrategiesError(error.message || 'Failed to load strategies');
    } finally {
      setLoadingStrategies(false);
    }
  }, [selectedStrategies.length]);

  const fetchDataSessions = useCallback(async () => {
    setLoadingSessions(true);
    setSessionsError(null);
    try {
      const response = await apiService.getDataCollectionSessions(50, false);
      const sessions = response.sessions || [];
      // Filter to only completed sessions with data
      const validSessions = sessions.filter(
        (s: DataSession) => s.prices_count > 0 || s.status === 'completed'
      );
      setDataSessions(validSessions);

      // Build unique symbols list from all sessions
      const symbolSet = new Set<string>();
      validSessions.forEach((s: DataSession) => {
        s.symbols?.forEach((sym: string) => symbolSet.add(sym));
      });
      setAvailableSymbols(Array.from(symbolSet).sort());

      // Auto-select first session if none selected and in backtest mode
      if (!backtestSessionId && validSessions.length > 0) {
        setBacktestSessionId(validSessions[0].session_id);
      }
    } catch (error: any) {
      console.error('Failed to fetch data sessions:', error);
      setSessionsError(error.message || 'Failed to load data sessions');
    } finally {
      setLoadingSessions(false);
    }
  }, [backtestSessionId]);

  useEffect(() => {
    fetchStrategies();
    fetchDataSessions();
  }, []);

  // Update available symbols when backtest session changes
  useEffect(() => {
    if (mode === 'backtest' && backtestSessionId) {
      const session = dataSessions.find(s => s.session_id === backtestSessionId);
      if (session?.symbols) {
        // Auto-select all symbols from the selected session
        setSelectedSymbols(session.symbols);
      }
    }
  }, [backtestSessionId, mode, dataSessions]);

  // ========================================
  // Event Handlers
  // ========================================

  const handleStrategyToggle = (strategyName: string) => {
    setSelectedStrategies(prev =>
      prev.includes(strategyName)
        ? prev.filter(name => name !== strategyName)
        : [...prev, strategyName]
    );
  };

  const handleSymbolToggle = (symbol: string) => {
    setSelectedSymbols(prev =>
      prev.includes(symbol)
        ? prev.filter(s => s !== symbol)
        : [...prev, symbol]
    );
  };

  const handleStartSession = async () => {
    setStartingSession(true);
    setStartError(null);

    try {
      // Build strategy_config: map each strategy to selected symbols
      const strategyConfig: Record<string, string[]> = {};
      selectedStrategies.forEach(stratName => {
        strategyConfig[stratName] = selectedSymbols;
      });

      const sessionData = {
        session_type: mode,
        name: `${mode}_${Date.now()}`,
        symbols: selectedSymbols,
        strategy_config: strategyConfig,
        config: {
          global_budget: globalBudget,
          max_position_size: maxPositionSize,
          stop_loss_percent: stopLoss,
          take_profit_percent: takeProfit,
          ...(mode === 'backtest' && {
            session_id: backtestSessionId,
            replay_speed: accelerationFactor,
          }),
        },
      };

      console.log('Starting session with config:', sessionData);

      const response = await apiService.startSession(sessionData);
      const newSessionId = response?.data?.session_id || response?.session_id;

      if (newSessionId) {
        setIsSessionRunning(true);
        setCurrentSessionId(newSessionId);
        // Redirect to dashboard after successful start
        router.push('/dashboard');
      } else {
        throw new Error('No session_id returned from API');
      }
    } catch (error: any) {
      console.error('Failed to start session:', error);
      setStartError(error.message || 'Failed to start session');
    } finally {
      setStartingSession(false);
    }
  };

  const handleStopSession = async () => {
    try {
      await apiService.stopSession(currentSessionId || undefined);
      setIsSessionRunning(false);
      setCurrentSessionId(null);
    } catch (error: any) {
      console.error('Failed to stop session:', error);
      setStartError(error.message || 'Failed to stop session');
    }
  };

  // Validation
  const canStart = selectedStrategies.length > 0 &&
                   selectedSymbols.length > 0 &&
                   (mode !== 'backtest' || backtestSessionId !== '');

  // Helper to format session for display
  const formatSessionOption = (session: DataSession) => {
    const date = new Date(session.created_at * 1000).toLocaleString();
    const symbols = session.symbols?.join(', ') || 'No symbols';
    const records = session.prices_count?.toLocaleString() || '0';
    return `${date} - ${symbols} (${records} records)`;
  };

  // ========================================
  // Render
  // ========================================

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
          Configure Trading Session
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Complete configuration interface for Live Trading, Paper Trading, and Backtesting
        </Typography>
      </Box>

      {/* Error alerts */}
      {startError && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setStartError(null)}>
          <AlertTitle>Session Start Failed</AlertTitle>
          {startError}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* LEFT COLUMN: Configuration */}
        <Grid item xs={12} lg={8}>
          {/* Mode Selection */}
          <Card sx={{ mb: 3 }}>
            <CardHeader
              title="1. Select Trading Mode"
              avatar={<SettingsIcon color="primary" />}
            />
            <CardContent>
              <ToggleButtonGroup
                value={mode}
                exclusive
                onChange={(_, newMode) => newMode && setMode(newMode)}
                fullWidth
                disabled={isSessionRunning}
              >
                <ToggleButton value="live" color="error">
                  Live Trading<br/>
                  <Typography variant="caption">(Real Money)</Typography>
                </ToggleButton>
                <ToggleButton value="paper" color="primary">
                  Paper Trading<br/>
                  <Typography variant="caption">(Simulated)</Typography>
                </ToggleButton>
                <ToggleButton value="backtest">
                  Backtest<br/>
                  <Typography variant="caption">(Historical)</Typography>
                </ToggleButton>
              </ToggleButtonGroup>

              {mode === 'live' && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  <strong>WARNING: Real Money Trading</strong><br/>
                  Live mode uses real funds. Test strategies in paper mode first!
                </Alert>
              )}

              {mode === 'paper' && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Paper trading simulates real trading with virtual funds. Perfect for testing!
                </Alert>
              )}

              {mode === 'backtest' && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Backtest mode replays historical data to evaluate strategy performance.
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Backtest Session Selection */}
          {mode === 'backtest' && (
            <Card sx={{ mb: 3 }}>
              <CardHeader
                title="Historical Data Session"
                avatar={<StorageIcon color="primary" />}
                action={
                  <Button
                    size="small"
                    startIcon={<RefreshIcon />}
                    onClick={fetchDataSessions}
                    disabled={loadingSessions}
                  >
                    Refresh
                  </Button>
                }
              />
              <CardContent>
                {loadingSessions ? (
                  <Skeleton variant="rectangular" height={56} />
                ) : sessionsError ? (
                  <Alert severity="error" action={
                    <Button color="inherit" size="small" onClick={fetchDataSessions}>
                      Retry
                    </Button>
                  }>
                    {sessionsError}
                  </Alert>
                ) : dataSessions.length === 0 ? (
                  <Alert severity="warning">
                    No data collection sessions found. Please collect some data first.
                  </Alert>
                ) : (
                  <>
                    <FormControl fullWidth sx={{ mb: 2 }}>
                      <InputLabel>Data Collection Session</InputLabel>
                      <Select
                        value={backtestSessionId}
                        label="Data Collection Session"
                        onChange={(e) => setBacktestSessionId(e.target.value)}
                        disabled={isSessionRunning}
                      >
                        {dataSessions.map(session => (
                          <MenuItem key={session.session_id} value={session.session_id}>
                            {formatSessionOption(session)}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    <Typography variant="body2" gutterBottom>
                      Acceleration Factor: {accelerationFactor}x
                    </Typography>
                    <Slider
                      value={accelerationFactor}
                      onChange={(_, val) => setAccelerationFactor(val as number)}
                      min={1}
                      max={100}
                      marks={[
                        { value: 1, label: '1x' },
                        { value: 10, label: '10x' },
                        { value: 50, label: '50x' },
                        { value: 100, label: '100x' },
                      ]}
                      disabled={isSessionRunning}
                    />
                    <Typography variant="caption" color="text.secondary">
                      Higher acceleration = faster backtest, but may consume more resources
                    </Typography>
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* Strategy Selection */}
          <Card sx={{ mb: 3 }}>
            <CardHeader
              title={`2. Select Strategies (${selectedStrategies.length} selected)`}
              avatar={<TrendingUpIcon color="primary" />}
              action={
                <Button
                  size="small"
                  startIcon={<RefreshIcon />}
                  onClick={fetchStrategies}
                  disabled={loadingStrategies}
                >
                  Refresh
                </Button>
              }
            />
            <CardContent>
              {loadingStrategies ? (
                <Box>
                  {[1, 2, 3].map(i => (
                    <Skeleton key={i} variant="rectangular" height={60} sx={{ mb: 1 }} />
                  ))}
                </Box>
              ) : strategiesError ? (
                <Alert severity="error" action={
                  <Button color="inherit" size="small" onClick={fetchStrategies}>
                    Retry
                  </Button>
                }>
                  {strategiesError}
                </Alert>
              ) : strategies.length === 0 ? (
                <Alert severity="warning">
                  No strategies found. Please create a strategy first.
                </Alert>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell padding="checkbox"></TableCell>
                      <TableCell>Strategy</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {strategies.map(strategy => (
                      <TableRow
                        key={strategy.strategy_name}
                        sx={{
                          backgroundColor: selectedStrategies.includes(strategy.strategy_name) ? 'action.selected' : 'inherit',
                          cursor: 'pointer',
                        }}
                        onClick={() => !isSessionRunning && handleStrategyToggle(strategy.strategy_name)}
                      >
                        <TableCell padding="checkbox">
                          <Checkbox
                            checked={selectedStrategies.includes(strategy.strategy_name)}
                            disabled={isSessionRunning}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight="bold">
                            {strategy.strategy_name}
                          </Typography>
                          {strategy.description && (
                            <Typography variant="caption" color="text.secondary">
                              {strategy.description}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          {strategy.enabled ? (
                            <Chip label="Enabled" size="small" color="success" />
                          ) : (
                            <Chip label="Disabled" size="small" />
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Strategy Preview Panel (TS-01) - Shows S1, Z1, ZE1, E1 conditions */}
          {selectedStrategies.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <StrategyPreviewPanel
                strategyName={selectedStrategies[selectedStrategies.length - 1]}
              />
            </Box>
          )}

          {/* Session Matrix (TS-02) - Strategy x Symbol grid */}
          {(selectedStrategies.length > 0 || selectedSymbols.length > 0) && (
            <Box sx={{ mb: 3 }}>
              <SessionMatrix
                strategies={strategies.map(s => s.strategy_name)}
                symbols={availableSymbols}
                selectedStrategies={selectedStrategies}
                selectedSymbols={selectedSymbols}
                mode={(selectedStrategies.length > 0 && selectedSymbols.length > 0) ? 'full' : 'compact'}
                showTotals={true}
              />
            </Box>
          )}

          {/* Symbol Selection */}
          <Card sx={{ mb: 3 }}>
            <CardHeader
              title={`3. Select Symbols (${selectedSymbols.length} selected)`}
              avatar={<AttachMoneyIcon color="primary" />}
            />
            <CardContent>
              {mode === 'backtest' && backtestSessionId ? (
                // For backtest, show symbols from selected data session
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Symbols available in selected data session:
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                    {dataSessions.find(s => s.session_id === backtestSessionId)?.symbols?.map(symbol => (
                      <Chip
                        key={symbol}
                        label={symbol}
                        color={selectedSymbols.includes(symbol) ? 'primary' : 'default'}
                        onClick={() => !isSessionRunning && handleSymbolToggle(symbol)}
                        onDelete={selectedSymbols.includes(symbol) ? () => handleSymbolToggle(symbol) : undefined}
                        deleteIcon={<DeleteIcon />}
                        disabled={isSessionRunning}
                      />
                    )) || (
                      <Typography color="text.secondary">No symbols in this session</Typography>
                    )}
                  </Box>
                </Box>
              ) : (
                // For live/paper, show all available symbols
                <Box>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                    {availableSymbols.length > 0 ? (
                      availableSymbols.map(symbol => (
                        <Chip
                          key={symbol}
                          label={symbol}
                          color={selectedSymbols.includes(symbol) ? 'primary' : 'default'}
                          onClick={() => !isSessionRunning && handleSymbolToggle(symbol)}
                          onDelete={selectedSymbols.includes(symbol) ? () => handleSymbolToggle(symbol) : undefined}
                          deleteIcon={<DeleteIcon />}
                          disabled={isSessionRunning}
                        />
                      ))
                    ) : (
                      <Alert severity="info" sx={{ width: '100%' }}>
                        No symbols available. Run data collection first or enter symbols manually.
                      </Alert>
                    )}
                  </Box>

                  <Stack direction="row" spacing={1}>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => setSelectedSymbols(availableSymbols.slice(0, 3))}
                      disabled={isSessionRunning || availableSymbols.length === 0}
                    >
                      Top 3
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => setSelectedSymbols([])}
                      disabled={isSessionRunning}
                    >
                      Clear All
                    </Button>
                  </Stack>
                </Box>
              )}
            </CardContent>
          </Card>

          {/* TS-03: Symbol Recommendations (only for live/paper mode) */}
          {mode !== 'backtest' && (
            <Box sx={{ mb: 3 }}>
              <SymbolRecommendation
                selectedSymbols={selectedSymbols}
                onAddSymbol={(symbol) => {
                  if (!selectedSymbols.includes(symbol)) {
                    setSelectedSymbols([...selectedSymbols, symbol]);
                  }
                }}
                onRemoveSymbol={(symbol) => {
                  setSelectedSymbols(selectedSymbols.filter(s => s !== symbol));
                }}
                maxRecommendations={5}
              />
            </Box>
          )}

          {/* Budget & Risk Management */}
          <Card sx={{ mb: 3 }}>
            <CardHeader
              title="4. Budget & Risk Management"
              avatar={<AttachMoneyIcon color="primary" />}
            />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Global Budget (USDT)"
                    type="number"
                    value={globalBudget}
                    onChange={(e) => setGlobalBudget(Number(e.target.value))}
                    disabled={isSessionRunning}
                    helperText="Total capital available"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Max Position Size (USDT)"
                    type="number"
                    value={maxPositionSize}
                    onChange={(e) => setMaxPositionSize(Number(e.target.value))}
                    disabled={isSessionRunning}
                    helperText="Per position limit"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Stop Loss (%)"
                    type="number"
                    value={stopLoss}
                    onChange={(e) => setStopLoss(Number(e.target.value))}
                    disabled={isSessionRunning}
                    helperText="Auto stop loss"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Take Profit (%)"
                    type="number"
                    value={takeProfit}
                    onChange={(e) => setTakeProfit(Number(e.target.value))}
                    disabled={isSessionRunning}
                    helperText="Auto take profit"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* RIGHT COLUMN: Summary & Actions */}
        <Grid item xs={12} lg={4}>
          <Card sx={{ position: 'sticky', top: 80 }}>
            <CardHeader
              title="Session Summary"
              avatar={<CheckCircleIcon color="success" />}
            />
            <CardContent>
              <List dense>
                <ListItem>
                  <ListItemText
                    primary="Mode"
                    secondary={mode.toUpperCase()}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Strategies"
                    secondary={selectedStrategies.length > 0
                      ? selectedStrategies.join(', ')
                      : 'None selected'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Symbols"
                    secondary={selectedSymbols.length > 0
                      ? selectedSymbols.join(', ')
                      : 'None selected'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Budget"
                    secondary={`$${globalBudget} USDT`}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Max Position"
                    secondary={`$${maxPositionSize} USDT`}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Risk Controls"
                    secondary={`SL: ${stopLoss}% / TP: ${takeProfit}%`}
                  />
                </ListItem>
                {mode === 'backtest' && backtestSessionId && (
                  <ListItem>
                    <ListItemText
                      primary="Data Session"
                      secondary={backtestSessionId}
                    />
                  </ListItem>
                )}
              </List>

              <Divider sx={{ my: 2 }} />

              {/* Validation Messages */}
              {!canStart && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  {selectedStrategies.length === 0 && <div>Select at least 1 strategy</div>}
                  {selectedSymbols.length === 0 && <div>Select at least 1 symbol</div>}
                  {mode === 'backtest' && !backtestSessionId && <div>Select data session</div>}
                </Alert>
              )}

              {/* Action Buttons */}
              <Stack spacing={2}>
                {!isSessionRunning ? (
                  <Button
                    variant="contained"
                    color="primary"
                    size="large"
                    fullWidth
                    startIcon={startingSession ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
                    onClick={handleStartSession}
                    disabled={!canStart || startingSession}
                  >
                    {startingSession ? 'Starting...' : `Start ${mode.toUpperCase()} Session`}
                  </Button>
                ) : (
                  <Button
                    variant="contained"
                    color="error"
                    size="large"
                    fullWidth
                    startIcon={<StopIcon />}
                    onClick={handleStopSession}
                  >
                    Stop Session
                  </Button>
                )}

                <Button
                  variant="outlined"
                  size="large"
                  fullWidth
                  onClick={() => router.push('/dashboard')}
                >
                  Go to Dashboard
                </Button>
              </Stack>

              {isSessionRunning && currentSessionId && (
                <Alert severity="success" sx={{ mt: 2 }}>
                  <Typography variant="body2" fontWeight="bold">
                    Session Running
                  </Typography>
                  <Typography variant="caption">
                    ID: {currentSessionId}
                  </Typography>
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
}
