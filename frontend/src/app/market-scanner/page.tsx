'use client';

import React, { useState, useEffect } from 'react';
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
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
  LinearProgress,
  Switch,
  FormControlLabel,
  Slider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Badge,
  Drawer,
  Divider,
  alpha,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  FlashOn as FlashIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Notifications as NotificationsIcon,
  NotificationsActive as NotificationsActiveIcon,
  FilterList as FilterIcon,
  ExpandMore as ExpandMoreIcon,
  Speed as SpeedIcon,
  ShowChart as ChartIcon,
  Warning as WarningIcon,
  Close as CloseIcon,
  Info as InfoIcon,
  Timeline as TimelineIcon,
  AttachMoney as AttachMoneyIcon,
  BarChart as BarChartIcon,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import MiniSparkline, { generateMockSparklineData } from '@/components/charts/MiniSparkline';
import { SignalHistoryPanel } from '@/components/market-scanner/SignalHistoryPanel';

interface ScannerData {
  symbol: string;
  price: number;
  priceChange24h: number;
  volume24h: number;
  pumpMagnitude: number;
  volumeSurge: number;
  confidenceScore: number;
  lastUpdate: string;
  trend: 'bullish' | 'bearish' | 'neutral';
  volatility: number;
  liquidity: number;
  signalStrength: 'weak' | 'medium' | 'strong' | 'extreme';
  priceHistory?: number[]; // For sparkline chart (MS-01)
}

interface ScannerSettings {
  minPumpMagnitude: number;
  minVolumeSurge: number;
  minConfidence: number;
  maxVolatility: number;
  symbols: string[];
  autoRefresh: boolean;
  refreshInterval: number;
  alertsEnabled: boolean;
}

const commonSymbols = [
  'BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT',
  'LINK_USDT', 'UNI_USDT', 'AAVE_USDT', 'SUSHI_USDT', 'COMP_USDT'
];

export default function MarketScannerPage() {
  const [scannerData, setScannerData] = useState<ScannerData[]>([]);
  const [filteredData, setFilteredData] = useState<ScannerData[]>([]);
  // Price history for sparklines (MS-01) - keeps last 20 values per symbol
  const [priceHistoryMap, setPriceHistoryMap] = useState<Record<string, number[]>>({});
  const [loading, setLoading] = useState(false);
  const [settings, setSettings] = useState<ScannerSettings>({
    minPumpMagnitude: 5,
    minVolumeSurge: 2,
    minConfidence: 50,
    maxVolatility: 20,
    symbols: commonSymbols.slice(0, 5),
    autoRefresh: true,
    refreshInterval: 30,
    alertsEnabled: true
  });
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info' | 'warning'}>({
    open: false,
    message: '',
    severity: 'info'
  });
  const [alerts, setAlerts] = useState<any[]>([]);
  // MS-03: Selected symbol for details panel
  const [selectedSymbol, setSelectedSymbol] = useState<ScannerData | null>(null);
  const [detailsDrawerOpen, setDetailsDrawerOpen] = useState(false);

  useEffect(() => {
    loadScannerData();
  }, []);

  // Auto-refresh with current settings; pause when tab hidden
  useVisibilityAwareInterval(
    () => { if (settings.autoRefresh) loadScannerData(); },
    Math.max(1000, (settings.refreshInterval || 30) * 1000)
  );

  useEffect(() => {
    applyFilters();
  }, [scannerData, settings]);

  const loadScannerData = async () => {
    setLoading(true);
    try {
      // Fetch real market data from /api/exchange/symbols endpoint
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const response = await fetch(`${apiUrl}/api/exchange/symbols`);

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const result = await response.json();
      const symbolsData = result.data?.symbols || result.symbols || [];

      // Filter by selected symbols and transform to ScannerData format
      const scannerResults: ScannerData[] = symbolsData
        .filter((s: any) => settings.symbols.includes(s.symbol))
        .map((symbolInfo: any) => {
          // Calculate derived scanner metrics based on real data
          const price = symbolInfo.price || 0;
          const volume24h = symbolInfo.volume24h || 0;
          const priceChange24h = symbolInfo.change24h || 0;

          // Derive pump magnitude from price change (real metric)
          const pumpMagnitude = Math.abs(priceChange24h);

          // Volume surge estimate (compare to average - simplified)
          // In production, this would compare against historical average volume
          const volumeSurge = volume24h > 0 ? Math.min(volume24h / 100000, 10) : 0;

          // Confidence score based on volume and price movement correlation
          const confidenceScore = Math.min(100, (pumpMagnitude * 5) + (volumeSurge * 10));

          // Determine trend from price change
          const trend = priceChange24h > 2 ? 'bullish' : priceChange24h < -2 ? 'bearish' : 'neutral';

          // Volatility estimate from price change magnitude
          const volatility = Math.abs(priceChange24h);

          // Liquidity score from volume
          const liquidity = Math.min(100, volume24h / 10000);

          // Signal strength based on pump magnitude
          const signalStrength = pumpMagnitude > 15 ? 'extreme' :
                                pumpMagnitude > 10 ? 'strong' :
                                pumpMagnitude > 5 ? 'medium' : 'weak';

          return {
            symbol: symbolInfo.symbol,
            price,
            priceChange24h,
            volume24h,
            pumpMagnitude,
            volumeSurge,
            confidenceScore,
            lastUpdate: symbolInfo.timestamp || new Date().toISOString(),
            trend,
            volatility,
            liquidity,
            signalStrength
          } as ScannerData;
        });

      // Update price history for sparklines (MS-01)
      setPriceHistoryMap(prev => {
        const newHistory = { ...prev };
        scannerResults.forEach(result => {
          const currentHistory = newHistory[result.symbol] || [];
          // Add new price, keep last 20 values
          newHistory[result.symbol] = [...currentHistory.slice(-19), result.price];

          // If first load (no history), generate initial mock data based on trend
          if (currentHistory.length === 0 && result.price > 0) {
            // Generate 15 previous points with slight variation to show trend
            const trendDirection = result.trend === 'bullish' ? 'up' : result.trend === 'bearish' ? 'down' : 'random';
            newHistory[result.symbol] = generateMockSparklineData(16, trendDirection, 0.02)
              .map((v, i, arr) => {
                // Scale to match current price
                const scaleFactor = result.price / arr[arr.length - 1];
                return v * scaleFactor;
              });
          }
        });
        return newHistory;
      });

      // Add priceHistory to scanner results
      const resultsWithHistory = scannerResults.map(result => ({
        ...result,
        priceHistory: priceHistoryMap[result.symbol] || []
      }));

      setScannerData(resultsWithHistory);

      // Check for alerts
      checkForAlerts(scannerResults);
    } catch (error) {
      console.error('Failed to load scanner data:', error);
      setSnackbar({
        open: true,
        message: `Failed to load scanner data: ${error instanceof Error ? error.message : 'Unknown error'}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    const filtered = scannerData.filter(data =>
      data.pumpMagnitude >= settings.minPumpMagnitude &&
      data.volumeSurge >= settings.minVolumeSurge &&
      data.confidenceScore >= settings.minConfidence &&
      data.volatility <= settings.maxVolatility
    );
    setFilteredData(filtered);
  };

  const checkForAlerts = (data: ScannerData[]) => {
    if (!settings.alertsEnabled) return;

    const newAlerts = data.filter(item =>
      item.pumpMagnitude >= 15 ||
      item.volumeSurge >= 5 ||
      item.confidenceScore >= 80
    );

    if (newAlerts.length > 0) {
      setAlerts(prev => [...prev, ...newAlerts.map(item => ({
        id: Date.now(),
        symbol: item.symbol,
        type: 'pump_signal',
        magnitude: item.pumpMagnitude,
        timestamp: new Date().toISOString()
      }))]);
    }
  };

  const getSignalColor = (strength: string) => {
    switch (strength) {
      case 'extreme': return 'error';
      case 'strong': return 'warning';
      case 'medium': return 'info';
      default: return 'default';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'bullish': return <TrendingUpIcon color="success" />;
      case 'bearish': return <TrendingDownIcon color="error" />;
      default: return <TrendingUpIcon color="disabled" />;
    }
  };

  const handleQuickTrade = (symbol: string) => {
    setSnackbar({
      open: true,
      message: `Quick trade initiated for ${symbol}`,
      severity: 'success'
    });
  };

  /**
   * MS-03: Handle row click to open details panel
   */
  const handleRowClick = (data: ScannerData) => {
    setSelectedSymbol(data);
    setDetailsDrawerOpen(true);
  };

  /**
   * MS-03: Close details panel
   */
  const handleCloseDetails = () => {
    setDetailsDrawerOpen(false);
  };

  const clearAlerts = () => {
    setAlerts([]);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          🔍 Real-Time Market Scanner
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Badge badgeContent={alerts.length} color="error">
            <NotificationsIcon />
          </Badge>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadScannerData}
            disabled={loading}
          >
            Refresh
          </Button>
          <FormControlLabel
            control={
              <Switch
                checked={settings.autoRefresh}
                onChange={(e) => setSettings(prev => ({ ...prev, autoRefresh: e.target.checked }))}
              />
            }
            label="Auto Refresh"
          />
        </Box>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Alerts Panel */}
      {alerts.length > 0 && (
        <Alert
          severity="warning"
          sx={{ mb: 3 }}
          action={
            <Button color="inherit" size="small" onClick={clearAlerts}>
              Clear
            </Button>
          }
        >
          <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
            🚨 {alerts.length} New Signal{alerts.length > 1 ? 's' : ''} Detected!
          </Typography>
          <Typography variant="body2">
            {alerts.slice(0, 3).map(alert => `${alert.symbol} (${alert.magnitude.toFixed(1)}%)`).join(', ')}
            {alerts.length > 3 && ` and ${alerts.length - 3} more...`}
          </Typography>
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Scanner Settings */}
        <Grid item xs={12} lg={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Scanner Settings
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Typography variant="body2" gutterBottom>
                  Min Pump Magnitude: {settings.minPumpMagnitude}%
                </Typography>
                <Slider
                  value={settings.minPumpMagnitude}
                  onChange={(e, value) => setSettings(prev => ({ ...prev, minPumpMagnitude: value as number }))}
                  min={0}
                  max={50}
                  step={1}
                  marks
                  valueLabelDisplay="auto"
                />

                <Typography variant="body2" gutterBottom>
                  Min Volume Surge: {settings.minVolumeSurge}x
                </Typography>
                <Slider
                  value={settings.minVolumeSurge}
                  onChange={(e, value) => setSettings(prev => ({ ...prev, minVolumeSurge: value as number }))}
                  min={1}
                  max={10}
                  step={0.5}
                  marks
                  valueLabelDisplay="auto"
                />

                <Typography variant="body2" gutterBottom>
                  Min Confidence: {settings.minConfidence}%
                </Typography>
                <Slider
                  value={settings.minConfidence}
                  onChange={(e, value) => setSettings(prev => ({ ...prev, minConfidence: value as number }))}
                  min={0}
                  max={100}
                  step={5}
                  marks
                  valueLabelDisplay="auto"
                />

                <Typography variant="body2" gutterBottom>
                  Max Volatility: {settings.maxVolatility}%
                </Typography>
                <Slider
                  value={settings.maxVolatility}
                  onChange={(e, value) => setSettings(prev => ({ ...prev, maxVolatility: value as number }))}
                  min={0}
                  max={50}
                  step={1}
                  marks
                  valueLabelDisplay="auto"
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.alertsEnabled}
                      onChange={(e) => setSettings(prev => ({ ...prev, alertsEnabled: e.target.checked }))}
                    />
                  }
                  label="Enable Alerts"
                />

                <FormControl fullWidth>
                  <InputLabel>Refresh Interval</InputLabel>
                  <Select
                    value={settings.refreshInterval}
                    label="Refresh Interval"
                    onChange={(e) => setSettings(prev => ({ ...prev, refreshInterval: parseInt(String(e.target.value), 10) }))}
                  >
                    <MenuItem value={10}>10 seconds</MenuItem>
                    <MenuItem value={30}>30 seconds</MenuItem>
                    <MenuItem value={60}>1 minute</MenuItem>
                    <MenuItem value={300}>5 minutes</MenuItem>
                  </Select>
                </FormControl>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Market Scanner Table */}
        <Grid item xs={12} lg={9}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <SpeedIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">
                    Market Scanner Results
                  </Typography>
                  <Chip
                    label={`${filteredData.length} matches`}
                    size="small"
                    color="info"
                    sx={{ ml: 1 }}
                  />
                </Box>
                <Typography variant="caption" color="text.secondary">
                  Last update: {new Date().toLocaleTimeString()}
                </Typography>
              </Box>

              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Symbol</TableCell>
                      <TableCell align="center">
                        <Tooltip title="Price trend (last 20 values)">
                          <ChartIcon fontSize="small" />
                        </Tooltip>
                      </TableCell>
                      <TableCell align="right">Price</TableCell>
                      <TableCell align="right">24h %</TableCell>
                      <TableCell align="right">Volume</TableCell>
                      <TableCell align="center">Trend</TableCell>
                      <TableCell align="right">
                        <Tooltip title="Pump Magnitude">
                          <FlashIcon fontSize="small" />
                        </Tooltip>
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Volume Surge">
                          <TrendingUpIcon fontSize="small" />
                        </Tooltip>
                      </TableCell>
                      <TableCell align="right">Confidence</TableCell>
                      <TableCell align="center">Signal</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredData.map((data) => (
                      <TableRow
                        key={data.symbol}
                        hover
                        onClick={() => handleRowClick(data)}
                        sx={{
                          cursor: 'pointer',
                          bgcolor: selectedSymbol?.symbol === data.symbol ? alpha('#2196f3', 0.1) : 'transparent',
                        }}
                      >
                        <TableCell>
                          <Typography variant="body2" fontWeight="bold">
                            {data.symbol.replace('_', '/')}
                          </Typography>
                        </TableCell>
                        {/* Mini Sparkline Chart (MS-01) */}
                        <TableCell align="center" sx={{ py: 0.5 }}>
                          <MiniSparkline
                            data={priceHistoryMap[data.symbol] || data.priceHistory || []}
                            width={70}
                            height={22}
                            color="auto"
                            showMarker={true}
                            strokeWidth={1.5}
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            ${data.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography
                            variant="body2"
                            color={data.priceChange24h >= 0 ? 'success.main' : 'error.main'}
                          >
                            {data.priceChange24h >= 0 ? '+' : ''}{data.priceChange24h.toFixed(1)}%
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            ${(data.volume24h / 1000000).toFixed(1)}M
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          {getTrendIcon(data.trend)}
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={`${data.pumpMagnitude.toFixed(1)}%`}
                            size="small"
                            color={data.pumpMagnitude > 15 ? 'error' : data.pumpMagnitude > 8 ? 'warning' : 'default'}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={`${data.volumeSurge.toFixed(1)}x`}
                            size="small"
                            color={data.volumeSurge > 5 ? 'error' : data.volumeSurge > 3 ? 'warning' : 'default'}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" color="primary" fontWeight="bold">
                            {data.confidenceScore.toFixed(0)}%
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={data.signalStrength.toUpperCase()}
                            size="small"
                            color={getSignalColor(data.signalStrength)}
                            variant="filled"
                          />
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 0.5 }}>
                            <Tooltip title="Quick Trade">
                              <IconButton
                                size="small"
                                color="success"
                                onClick={() => handleQuickTrade(data.symbol)}
                              >
                                <PlayIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Monitor">
                              <IconButton size="small" color="info">
                                <ChartIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Alert">
                              <IconButton size="small" color="warning">
                                <NotificationsActiveIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                    {filteredData.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={10} align="center" sx={{ py: 4 }}>
                          <Typography variant="body2" color="text.secondary">
                            No symbols match current filter criteria
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Advanced Filters Accordion */}
      <Accordion sx={{ mt: 3 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Advanced Filters & Settings</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Monitored Symbols</InputLabel>
                <Select
                  multiple
                  value={settings.symbols}
                  label="Monitored Symbols"
                  onChange={(e) => setSettings(prev => ({
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
                  {commonSymbols.map(symbol => (
                    <MenuItem key={symbol} value={symbol}>{symbol}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button variant="outlined" fullWidth>
                  Save Filter Preset
                </Button>
                <Button variant="outlined" fullWidth>
                  Load Preset
                </Button>
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

      {/* MS-03: Symbol Details Drawer */}
      <Drawer
        anchor="right"
        open={detailsDrawerOpen}
        onClose={handleCloseDetails}
        PaperProps={{
          sx: { width: { xs: '100%', sm: 400 } }
        }}
      >
        {selectedSymbol && (
          <Box sx={{ p: 2 }}>
            {/* Header */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h5" fontWeight="bold">
                {selectedSymbol.symbol.replace('_', '/')}
              </Typography>
              <IconButton onClick={handleCloseDetails}>
                <CloseIcon />
              </IconButton>
            </Box>

            <Divider sx={{ mb: 2 }} />

            {/* Large Price Display */}
            <Box sx={{ textAlign: 'center', mb: 3, p: 2, bgcolor: 'background.default', borderRadius: 2 }}>
              <Typography variant="h3" fontWeight="bold">
                ${selectedSymbol.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
              </Typography>
              <Chip
                label={`${selectedSymbol.priceChange24h >= 0 ? '+' : ''}${selectedSymbol.priceChange24h.toFixed(2)}%`}
                color={selectedSymbol.priceChange24h >= 0 ? 'success' : 'error'}
                size="medium"
                sx={{ mt: 1 }}
              />
            </Box>

            {/* Sparkline Chart (larger) */}
            <Box sx={{ mb: 3, p: 2, bgcolor: 'background.default', borderRadius: 2 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                <TimelineIcon fontSize="small" sx={{ mr: 0.5, verticalAlign: 'middle' }} />
                Price History (Last 20 ticks)
              </Typography>
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
                <MiniSparkline
                  data={priceHistoryMap[selectedSymbol.symbol] || selectedSymbol.priceHistory || []}
                  width={340}
                  height={80}
                  color="auto"
                  showMarker={true}
                  showFill={true}
                  strokeWidth={2}
                />
              </Box>
            </Box>

            {/* Key Metrics Grid */}
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              <BarChartIcon fontSize="small" sx={{ mr: 0.5, verticalAlign: 'middle' }} />
              Key Metrics
            </Typography>
            <Grid container spacing={1} sx={{ mb: 3 }}>
              <Grid item xs={6}>
                <Paper sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="caption" color="text.secondary">Volume 24h</Typography>
                  <Typography variant="body1" fontWeight="bold">
                    ${(selectedSymbol.volume24h / 1000000).toFixed(2)}M
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={6}>
                <Paper sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="caption" color="text.secondary">Trend</Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 0.5 }}>
                    {getTrendIcon(selectedSymbol.trend)}
                    <Typography variant="body1" fontWeight="bold" sx={{ textTransform: 'capitalize' }}>
                      {selectedSymbol.trend}
                    </Typography>
                  </Box>
                </Paper>
              </Grid>
              <Grid item xs={6}>
                <Paper sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="caption" color="text.secondary">Volatility</Typography>
                  <Typography
                    variant="body1"
                    fontWeight="bold"
                    color={selectedSymbol.volatility > 15 ? 'error.main' : selectedSymbol.volatility > 8 ? 'warning.main' : 'success.main'}
                  >
                    {selectedSymbol.volatility.toFixed(1)}%
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={6}>
                <Paper sx={{ p: 1.5, textAlign: 'center' }}>
                  <Typography variant="caption" color="text.secondary">Liquidity</Typography>
                  <Typography variant="body1" fontWeight="bold">
                    {selectedSymbol.liquidity.toFixed(0)}%
                  </Typography>
                </Paper>
              </Grid>
            </Grid>

            {/* Pump/Dump Indicators */}
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              <FlashIcon fontSize="small" sx={{ mr: 0.5, verticalAlign: 'middle' }} />
              Pump/Dump Detection
            </Typography>
            <Paper sx={{ p: 2, mb: 3 }}>
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2">Pump Magnitude</Typography>
                  <Typography
                    variant="body2"
                    fontWeight="bold"
                    color={selectedSymbol.pumpMagnitude > 15 ? 'error.main' : selectedSymbol.pumpMagnitude > 8 ? 'warning.main' : 'text.primary'}
                  >
                    {selectedSymbol.pumpMagnitude.toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(selectedSymbol.pumpMagnitude / 20 * 100, 100)}
                  color={selectedSymbol.pumpMagnitude > 15 ? 'error' : selectedSymbol.pumpMagnitude > 8 ? 'warning' : 'primary'}
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </Box>
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2">Volume Surge</Typography>
                  <Typography
                    variant="body2"
                    fontWeight="bold"
                    color={selectedSymbol.volumeSurge > 5 ? 'error.main' : selectedSymbol.volumeSurge > 3 ? 'warning.main' : 'text.primary'}
                  >
                    {selectedSymbol.volumeSurge.toFixed(1)}x
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(selectedSymbol.volumeSurge / 10 * 100, 100)}
                  color={selectedSymbol.volumeSurge > 5 ? 'error' : selectedSymbol.volumeSurge > 3 ? 'warning' : 'primary'}
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2">Confidence Score</Typography>
                  <Typography variant="body2" fontWeight="bold" color="primary">
                    {selectedSymbol.confidenceScore.toFixed(0)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={selectedSymbol.confidenceScore}
                  color="primary"
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </Box>
            </Paper>

            {/* Signal Strength */}
            <Box sx={{ textAlign: 'center', mb: 3 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Signal Strength
              </Typography>
              <Chip
                label={selectedSymbol.signalStrength.toUpperCase()}
                color={getSignalColor(selectedSymbol.signalStrength)}
                size="medium"
                sx={{ fontSize: '1.1rem', fontWeight: 'bold', px: 3, py: 2, height: 'auto' }}
              />
            </Box>

            {/* MS-02: Signal History */}
            <Paper sx={{ p: 2, mb: 3 }}>
              <SignalHistoryPanel
                symbol={selectedSymbol.symbol}
                maxSignals={7}
                showOutcomes={true}
              />
            </Paper>

            {/* Action Buttons */}
            <Divider sx={{ mb: 2 }} />
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="contained"
                color="success"
                fullWidth
                startIcon={<PlayIcon />}
                onClick={() => {
                  handleQuickTrade(selectedSymbol.symbol);
                  handleCloseDetails();
                }}
              >
                Quick Trade
              </Button>
              <Button
                variant="outlined"
                color="primary"
                fullWidth
                startIcon={<ChartIcon />}
              >
                View Chart
              </Button>
            </Box>
            <Button
              variant="outlined"
              color="warning"
              fullWidth
              startIcon={<NotificationsActiveIcon />}
              sx={{ mt: 1 }}
            >
              Set Alert
            </Button>

            {/* Last Update */}
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 2 }}>
              Last update: {selectedSymbol.lastUpdate}
            </Typography>
          </Box>
        )}
      </Drawer>
    </Box>
  );
}
