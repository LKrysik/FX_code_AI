'use client';

import React, { useState, useEffect, useCallback } from 'react';
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
  Tabs,
  Tab,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  ShowChart as ChartIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import { SystemStatusIndicator } from '@/components/common/SystemStatusIndicator';
import { getCategoryStatusColor, type CategoryType } from '@/utils/statusUtils';
import type { Indicator } from '@/types/api';
import { Logger } from '@/services/frontendLogService';

interface IndicatorType {
  name: string;
  category: string;
  description: string;
  parameters: string[];
}

const indicatorTypes: IndicatorType[] = [
  // Fundamental Indicators
  { name: 'PRICE', category: 'Fundamental', description: 'Current price', parameters: [] },
  { name: 'VOLUME', category: 'Fundamental', description: 'Trading volume', parameters: [] },
  { name: 'SPREAD_PCT', category: 'Fundamental', description: 'Bid-ask spread percentage', parameters: [] },

  // Technical Indicators
  { name: 'RSI', category: 'Technical', description: 'Relative Strength Index', parameters: ['period'] },
  { name: 'SMA', category: 'Technical', description: 'Simple Moving Average', parameters: ['period'] },
  { name: 'EMA', category: 'Technical', description: 'Exponential Moving Average', parameters: ['period'] },

  // Pump & Dump Indicators
  { name: 'PUMP_MAGNITUDE_PCT', category: 'Pump & Dump', description: 'Pump magnitude percentage', parameters: ['period'] },
  { name: 'VOLUME_SURGE_RATIO', category: 'Pump & Dump', description: 'Volume surge ratio', parameters: ['period'] },
  { name: 'PRICE_MOMENTUM', category: 'Pump & Dump', description: 'Price momentum', parameters: ['period'] },

  // Risk Indicators
  { name: 'CONFIDENCE_SCORE', category: 'Risk', description: 'Signal confidence score', parameters: [] },
  { name: 'VOLATILITY', category: 'Risk', description: 'Price volatility', parameters: ['period'] },
  { name: 'LIQUIDITY_SCORE', category: 'Risk', description: 'Market liquidity score', parameters: [] },
];

const commonSymbols = ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT'];
const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d'];

export default function MarketDataPage() {
  const [indicators, setIndicators] = useState<Indicator[]>([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingIndicator, setEditingIndicator] = useState<Indicator | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info' | 'warning'}>({
    open: false,
    message: '',
    severity: 'info'
  });

  // Backend health check (consistent with Dashboard)
  const checkBackendConnection = useCallback(async () => {
    try {
      await apiService.healthCheck();
    } catch (error) {
      // Silently handle health check failures
      Logger.warn('MarketDataPage.checkBackendConnection', 'Health check failed', { error });
    }
  }, []);

  useVisibilityAwareInterval(checkBackendConnection, 15000);

  // Form state
  const [formData, setFormData] = useState({
    symbol: 'BTC_USDT',
    indicator: 'PRICE',
    period: 20,
    timeframe: '1m',
    scope: 'default'
  });

  useEffect(() => {
    loadIndicators();
  }, []);

  const loadIndicators = async () => {
    setLoading(true);
    try {
      const indicatorsData = await apiService.getIndicators();
      setIndicators(indicatorsData);
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to load indicators',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleAddIndicator = () => {
    setEditingIndicator(null);
    setFormData({
      symbol: 'BTC_USDT',
      indicator: 'PRICE',
      period: 20,
      timeframe: '1m',
      scope: 'default'
    });
    setDialogOpen(true);
  };

  const handleEditIndicator = (indicator: Indicator) => {
    setEditingIndicator(indicator);
    setFormData({
      symbol: indicator.symbol,
      indicator: indicator.indicator,
      period: indicator.period ?? 20,
      timeframe: indicator.timeframe || '1m',
      scope: indicator.scope || 'default'
    });
    setDialogOpen(true);
  };

  const handleDeleteIndicator = async (key: string) => {
    try {
      await apiService.deleteIndicator(key);
      setIndicators(prev => prev.filter(ind => ind.key !== key));
      setSnackbar({
        open: true,
        message: 'Indicator deleted successfully',
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to delete indicator',
        severity: 'error'
      });
    }
  };

  const handleSaveIndicator = async () => {
    try {
      const indicatorData = {
        symbol: formData.symbol,
        indicator_type: formData.indicator,
        period: formData.period,
        timeframe: formData.timeframe,
        scope: formData.scope
      };

      if (editingIndicator) {
        // Update existing
        await apiService.updateIndicator(editingIndicator.key, indicatorData);
        setSnackbar({
          open: true,
          message: 'Indicator updated successfully',
          severity: 'success'
        });
      } else {
        // Add new
        const response = await apiService.addIndicator(indicatorData);
        setSnackbar({
          open: true,
          message: 'Indicator added successfully',
          severity: 'success'
        });
      }

      setDialogOpen(false);
      loadIndicators();
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to save indicator',
        severity: 'error'
      });
    }
  };

  const getIndicatorCategory = (indicatorName: string) => {
    const type = indicatorTypes.find(t => t.name === indicatorName);
    return type?.category || 'Unknown';
  };

  const getIndicatorDescription = (indicatorName: string) => {
    const type = indicatorTypes.find(t => t.name === indicatorName);
    return type?.description || '';
  };

  const filteredIndicators = indicators.filter(indicator => {
    if (activeTab === 0) return true; // All
    if (activeTab === 1) return getIndicatorCategory(indicator.indicator) === 'Fundamental';
    if (activeTab === 2) return getIndicatorCategory(indicator.indicator) === 'Technical';
    if (activeTab === 3) return getIndicatorCategory(indicator.indicator) === 'Pump & Dump';
    if (activeTab === 4) return getIndicatorCategory(indicator.indicator) === 'Risk';
    return false;
  });

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Market Data & Indicators
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadIndicators}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleAddIndicator}
          >
            Add Indicator
          </Button>
        </Box>
      </Box>

      {/* System Status */}
      <SystemStatusIndicator showDetails={false} />

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <TrendingUpIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Total Indicators</Typography>
              </Box>
              <Typography variant="h4" color="primary">
                {indicators.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <ChartIcon color="secondary" sx={{ mr: 1 }} />
                <Typography variant="h6">Active Symbols</Typography>
              </Box>
              <Typography variant="h4" color="secondary">
                {new Set(indicators.map(i => i.symbol)).size}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <AssessmentIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="h6">Categories</Typography>
              </Box>
              <Typography variant="h4" color="success">
                {new Set(indicators.map(i => getIndicatorCategory(i.indicator))).size}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <RefreshIcon color="info" sx={{ mr: 1 }} />
                <Typography variant="h6">Real-time</Typography>
              </Box>
              <Typography variant="h4" color="info">
                {indicators.filter(i => i.timestamp).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Category Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
          <Tab label="All Indicators" />
          <Tab label="Fundamental" />
          <Tab label="Technical" />
          <Tab label="Pump & Dump" />
          <Tab label="Risk" />
        </Tabs>
      </Paper>

      {/* Indicators Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Symbol</TableCell>
              <TableCell>Indicator</TableCell>
              <TableCell>Category</TableCell>
              <TableCell>Period</TableCell>
              <TableCell>Timeframe</TableCell>
              <TableCell>Current Value</TableCell>
              <TableCell>Last Update</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredIndicators.map((indicator) => (
              <TableRow key={indicator.key} hover>
                <TableCell>
                  <Chip label={indicator.symbol} size="small" />
                </TableCell>
                <TableCell>
                  <Box>
                    <Typography variant="body2" fontWeight="bold">
                      {indicator.indicator.replace(/_/g, ' ')}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {getIndicatorDescription(indicator.indicator)}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip
                    label={getIndicatorCategory(indicator.indicator)}
                    size="small"
                    color={getCategoryStatusColor(getIndicatorCategory(indicator.indicator) as CategoryType)}
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>{indicator.period}</TableCell>
                <TableCell>{indicator.timeframe || 'N/A'}</TableCell>
                <TableCell>
                  {indicator.value !== undefined ? (
                    <Typography variant="body2" fontWeight="bold" color="primary">
                      {indicator.value.toFixed(4)}
                    </Typography>
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      No data
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  {indicator.timestamp ? (
                    <Typography variant="caption">
                      {new Date(indicator.timestamp).toLocaleTimeString()}
                    </Typography>
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      Never
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Tooltip title="Edit">
                    <IconButton size="small" onClick={() => handleEditIndicator(indicator)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <IconButton size="small" color="error" onClick={() => handleDeleteIndicator(indicator.key)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {filteredIndicators.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                  <Typography variant="body2" color="text.secondary">
                    No indicators found in this category
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit Indicator Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingIndicator ? 'Edit Indicator' : 'Add New Indicator'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Symbol</InputLabel>
              <Select
                value={formData.symbol}
                label="Symbol"
                onChange={(e) => setFormData(prev => ({ ...prev, symbol: e.target.value }))}
              >
                {commonSymbols.map(symbol => (
                  <MenuItem key={symbol} value={symbol}>{symbol}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Indicator Type</InputLabel>
              <Select
                value={formData.indicator}
                label="Indicator Type"
                onChange={(e) => setFormData(prev => ({ ...prev, indicator: e.target.value }))}
              >
                {indicatorTypes.map(type => (
                  <MenuItem key={type.name} value={type.name}>
                    <Box>
                      <Typography variant="body2">{type.name.replace(/_/g, ' ')}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {type.category} - {type.description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="Period"
              type="number"
              value={formData.period}
              onChange={(e) => setFormData(prev => ({ ...prev, period: parseInt(e.target.value) || 20 }))}
              helperText="Period for moving averages, RSI, etc."
            />

            <FormControl fullWidth>
              <InputLabel>Timeframe</InputLabel>
              <Select
                value={formData.timeframe}
                label="Timeframe"
                onChange={(e) => setFormData(prev => ({ ...prev, timeframe: e.target.value }))}
              >
                {timeframes.map(tf => (
                  <MenuItem key={tf} value={tf}>{tf}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="Scope"
              value={formData.scope}
              onChange={(e) => setFormData(prev => ({ ...prev, scope: e.target.value }))}
              helperText="Multi-tenant scope for indicator isolation"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveIndicator} variant="contained">
            {editingIndicator ? 'Update' : 'Add'} Indicator
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
