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
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
  LinearProgress,
  Slider,
  Switch,
  FormControlLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
} from '@mui/material';
import {
  Security as SecurityIcon,
  Warning as WarningIcon,
  Shield as ShieldIcon,
  TrendingDown as TrendingDownIcon,
  Stop as StopIcon,
  PlayArrow as PlayIcon,
  Settings as SettingsIcon,
  Assessment as AssessmentIcon,
  ExpandMore as ExpandMoreIcon,
  Error as ErrorIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { apiService } from '@/services/api';

interface Position {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPct: number;
  stopLoss: number;
  takeProfit: number;
  riskPct: number;
  strategy: string;
  timestamp: string;
}

interface RiskSettings {
  maxPortfolioRisk: number; // Max % of portfolio at risk
  maxPositionRisk: number; // Max % risk per position
  maxDrawdown: number; // Max drawdown before emergency stop
  dailyLossLimit: number; // Daily loss limit
  maxConcurrentPositions: number;
  emergencyStopEnabled: boolean;
  autoReduceEnabled: boolean;
  alertThresholds: {
    highRisk: number;
    criticalRisk: number;
  };
}

interface RiskMetrics {
  totalPortfolioValue: number;
  currentRisk: number;
  dailyPnL: number;
  maxDrawdown: number;
  activePositions: number;
  atRiskAmount: number;
  availableCapital: number;
}

export default function RiskManagementPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [riskSettings, setRiskSettings] = useState<RiskSettings>({
    maxPortfolioRisk: 20,
    maxPositionRisk: 5,
    maxDrawdown: 10,
    dailyLossLimit: 500,
    maxConcurrentPositions: 5,
    emergencyStopEnabled: true,
    autoReduceEnabled: false,
    alertThresholds: {
      highRisk: 15,
      criticalRisk: 25
    }
  });
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics>({
    totalPortfolioValue: 10000,
    currentRisk: 8.5,
    dailyPnL: -125.50,
    maxDrawdown: 3.2,
    activePositions: 3,
    atRiskAmount: 850,
    availableCapital: 9150
  });
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info' | 'warning'}>({
    open: false,
    message: '',
    severity: 'info'
  });

  useEffect(() => {
    loadRiskData();
  }, []);

  const loadRiskData = async () => {
    setLoading(true);
    try {
      // Mock data - in real app, this would come from API
      const mockPositions: Position[] = [
        {
          id: '1',
          symbol: 'ADA_USDT',
          side: 'long',
          size: 50000,
          entryPrice: 0.42,
          currentPrice: 0.48,
          pnl: 300,
          pnlPct: 14.3,
          stopLoss: 0.38,
          takeProfit: 0.55,
          riskPct: 3.2,
          strategy: 'flash_pump_hunter',
          timestamp: new Date(Date.now() - 1800000).toISOString()
        },
        {
          id: '2',
          symbol: 'DOT_USDT',
          side: 'long',
          size: 1000,
          entryPrice: 7.25,
          currentPrice: 7.85,
          pnl: 600,
          pnlPct: 8.3,
          stopLoss: 6.80,
          takeProfit: 8.50,
          riskPct: 2.1,
          strategy: 'steady_pump_rider',
          timestamp: new Date(Date.now() - 900000).toISOString()
        },
        {
          id: '3',
          symbol: 'SOL_USDT',
          side: 'short',
          size: 50,
          entryPrice: 105,
          currentPrice: 98,
          pnl: 350,
          pnlPct: 6.7,
          stopLoss: 110,
          takeProfit: 90,
          riskPct: 4.8,
          strategy: 'dump_reversal_catcher',
          timestamp: new Date(Date.now() - 600000).toISOString()
        }
      ];
      setPositions(mockPositions);
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to load risk data',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleEmergencyStop = async () => {
    try {
      await apiService.stopSession();
      setSnackbar({
        open: true,
        message: 'Emergency stop executed - all positions closed',
        severity: 'warning'
      });
      loadRiskData();
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to execute emergency stop',
        severity: 'error'
      });
    }
  };

  const handleClosePosition = async (positionId: string) => {
    try {
      // In real app, this would close specific position
      setPositions(prev => prev.filter(p => p.id !== positionId));
      setSnackbar({
        open: true,
        message: 'Position closed successfully',
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to close position',
        severity: 'error'
      });
    }
  };

  const handleUpdateStopLoss = async (positionId: string, newStopLoss: number) => {
    try {
      setPositions(prev => prev.map(p =>
        p.id === positionId ? { ...p, stopLoss: newStopLoss } : p
      ));
      setSnackbar({
        open: true,
        message: 'Stop loss updated successfully',
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to update stop loss',
        severity: 'error'
      });
    }
  };

  const getRiskLevel = (riskPct: number) => {
    if (riskPct >= riskSettings.alertThresholds.criticalRisk) return 'critical';
    if (riskPct >= riskSettings.alertThresholds.highRisk) return 'high';
    return 'normal';
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      default: return 'success';
    }
  };

  const getTotalRisk = () => {
    return positions.reduce((sum, pos) => sum + pos.riskPct, 0);
  };

  const getRiskStatus = () => {
    const totalRisk = getTotalRisk();
    if (totalRisk >= riskSettings.alertThresholds.criticalRisk) return 'critical';
    if (totalRisk >= riskSettings.alertThresholds.highRisk) return 'high';
    if (totalRisk >= riskSettings.maxPortfolioRisk) return 'warning';
    return 'normal';
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          🛡️ Risk Management Control Panel
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            color="warning"
            startIcon={<WarningIcon />}
            onClick={handleEmergencyStop}
          >
            Emergency Stop
          </Button>
          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
          >
            Risk Settings
          </Button>
        </Box>
      </Box>

      {/* Risk Status Alert */}
      {getRiskStatus() !== 'normal' && (
        <Alert
          severity={getRiskStatus() === 'critical' ? 'error' : 'warning'}
          sx={{ mb: 3 }}
          action={
            <Button color="inherit" size="small" onClick={handleEmergencyStop}>
              Emergency Stop
            </Button>
          }
        >
          <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
            ⚠️ Risk Alert: {getRiskStatus().toUpperCase()} Risk Level
          </Typography>
          <Typography variant="body2">
            Total portfolio risk: {getTotalRisk().toFixed(1)}% |
            Threshold: {riskSettings.maxPortfolioRisk}% |
            {positions.length} active positions
          </Typography>
        </Alert>
      )}

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Risk Overview Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <SecurityIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Portfolio Risk</Typography>
              </Box>
              <Typography variant="h4" color="primary" sx={{ mb: 1 }}>
                {getTotalRisk().toFixed(1)}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                of {riskSettings.maxPortfolioRisk}% limit
              </Typography>
              <LinearProgress
                variant="determinate"
                value={(getTotalRisk() / riskSettings.maxPortfolioRisk) * 100}
                color={getRiskColor(getRiskStatus())}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <ShieldIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="h6">Daily P&L</Typography>
              </Box>
              <Typography
                variant="h4"
                color={riskMetrics.dailyPnL >= 0 ? 'success.main' : 'error.main'}
                sx={{ mb: 1 }}
              >
                ${riskMetrics.dailyPnL.toFixed(2)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Limit: -${riskSettings.dailyLossLimit}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <TrendingDownIcon color="warning" sx={{ mr: 1 }} />
                <Typography variant="h6">Max Drawdown</Typography>
              </Box>
              <Typography variant="h4" color="warning.main" sx={{ mb: 1 }}>
                {riskMetrics.maxDrawdown.toFixed(1)}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                of {riskSettings.maxDrawdown}% limit
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <AssessmentIcon color="info" sx={{ mr: 1 }} />
                <Typography variant="h6">Active Positions</Typography>
              </Box>
              <Typography variant="h4" color="info.main" sx={{ mb: 1 }}>
                {positions.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                of {riskSettings.maxConcurrentPositions} max
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Positions Table */}
      <Paper sx={{ mb: 3 }}>
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6">Active Positions & Risk Management</Typography>
        </Box>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Symbol</TableCell>
                <TableCell>Side</TableCell>
                <TableCell align="right">Size</TableCell>
                <TableCell align="right">Entry Price</TableCell>
                <TableCell align="right">Current Price</TableCell>
                <TableCell align="right">P&L</TableCell>
                <TableCell align="right">Risk %</TableCell>
                <TableCell align="right">Stop Loss</TableCell>
                <TableCell align="right">Take Profit</TableCell>
                <TableCell>Strategy</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {positions.map((position) => (
                <TableRow key={position.id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {position.symbol.replace('_', '/')}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={position.side.toUpperCase()}
                      color={position.side === 'long' ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">
                    {position.size.toLocaleString()}
                  </TableCell>
                  <TableCell align="right">
                    ${position.entryPrice.toFixed(4)}
                  </TableCell>
                  <TableCell align="right">
                    ${position.currentPrice.toFixed(4)}
                  </TableCell>
                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      color={position.pnl >= 0 ? 'success.main' : 'error.main'}
                      fontWeight="bold"
                    >
                      ${position.pnl.toFixed(2)} ({position.pnlPct.toFixed(1)}%)
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Chip
                      label={`${position.riskPct.toFixed(1)}%`}
                      size="small"
                      color={getRiskColor(getRiskLevel(position.riskPct))}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" color="error.main">
                      ${position.stopLoss.toFixed(4)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" color="success.main">
                      ${position.takeProfit.toFixed(4)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={position.strategy} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      <Tooltip title="Update Stop Loss">
                        <IconButton size="small" color="warning">
                          <StopIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Close Position">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleClosePosition(position.id)}
                        >
                          <ErrorIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
              {positions.length === 0 && (
                <TableRow>
                  <TableCell colSpan={11} align="center" sx={{ py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      No active positions
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Risk Settings Accordion */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Risk Management Settings</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                Portfolio Limits
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box>
                  <Typography variant="body2" gutterBottom>
                    Max Portfolio Risk: {riskSettings.maxPortfolioRisk}%
                  </Typography>
                  <Slider
                    value={riskSettings.maxPortfolioRisk}
                    onChange={(e, value) => setRiskSettings(prev => ({ ...prev, maxPortfolioRisk: value as number }))}
                    min={5}
                    max={50}
                    step={1}
                    marks
                    valueLabelDisplay="auto"
                  />
                </Box>

                <Box>
                  <Typography variant="body2" gutterBottom>
                    Max Position Risk: {riskSettings.maxPositionRisk}%
                  </Typography>
                  <Slider
                    value={riskSettings.maxPositionRisk}
                    onChange={(e, value) => setRiskSettings(prev => ({ ...prev, maxPositionRisk: value as number }))}
                    min={1}
                    max={10}
                    step={0.5}
                    marks
                    valueLabelDisplay="auto"
                  />
                </Box>

                <Box>
                  <Typography variant="body2" gutterBottom>
                    Max Drawdown: {riskSettings.maxDrawdown}%
                  </Typography>
                  <Slider
                    value={riskSettings.maxDrawdown}
                    onChange={(e, value) => setRiskSettings(prev => ({ ...prev, maxDrawdown: value as number }))}
                    min={5}
                    max={30}
                    step={1}
                    marks
                    valueLabelDisplay="auto"
                  />
                </Box>
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                Safety Controls
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={riskSettings.emergencyStopEnabled}
                      onChange={(e) => setRiskSettings(prev => ({ ...prev, emergencyStopEnabled: e.target.checked }))}
                    />
                  }
                  label="Enable Emergency Stop"
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={riskSettings.autoReduceEnabled}
                      onChange={(e) => setRiskSettings(prev => ({ ...prev, autoReduceEnabled: e.target.checked }))}
                    />
                  }
                  label="Auto-reduce position sizes on high risk"
                />

                <TextField
                  fullWidth
                  label="Daily Loss Limit ($)"
                  type="number"
                  value={riskSettings.dailyLossLimit}
                  onChange={(e) => setRiskSettings(prev => ({ ...prev, dailyLossLimit: parseFloat(e.target.value) || 0 }))}
                />

                <TextField
                  fullWidth
                  label="Max Concurrent Positions"
                  type="number"
                  value={riskSettings.maxConcurrentPositions}
                  onChange={(e) => setRiskSettings(prev => ({ ...prev, maxConcurrentPositions: parseInt(e.target.value) || 1 }))}
                />
              </Box>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

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
