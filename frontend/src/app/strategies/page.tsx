'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Avatar,
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Tabs,
  Tab,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  FlashOn as FlashIcon,
  TrendingUp as TrendingUpIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
  Assessment as AssessmentIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Settings as SettingsIcon,
  Save as SaveIcon,
  List as ListIcon,
  Build as BuildIcon,
} from '@mui/icons-material';
import { StrategyBuilder5Section } from '@/components/strategy/StrategyBuilder5Section';
import { apiService } from '@/services/api';
import { SystemStatusIndicator } from '@/components/common/SystemStatusIndicator';
import { Logger } from '@/services/frontendLogService';
import type { Strategy } from '@/types/api';
import type { Strategy5Section, IndicatorVariant, StrategyValidationResult } from '@/types/strategy';

interface StrategyTemplate {
  id: string;
  name: string;
  description: string;
  category: 'pump_detection' | 'dump_detection' | 'scalping' | 'swing';
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  riskLevel: 'low' | 'medium' | 'high';
  expectedReturn: string;
  winRate: number;
  config: any;
  icon: React.ReactNode;
  color: string;
  isRunning: boolean;
  performance?: {
    totalTrades: number;
    winRate: number;
    totalPnL: number;
    maxDrawdown: number;
  };
}

const strategyTemplates: StrategyTemplate[] = [
  {
    id: 'flash_pump_hunter',
    name: 'Flash Pump Hunter',
    description: 'Aggressive strategy for catching ultra-fast pump movements with high volume surge',
    category: 'pump_detection',
    difficulty: 'advanced',
    riskLevel: 'high',
    expectedReturn: '50-200%',
    winRate: 65,
    icon: <FlashIcon />,
    color: '#ff4444',
    isRunning: false,
    config: {
      pump_magnitude_min: 15,
      volume_surge_min: 5,
      confidence_min: 75,
      max_position_size: 1000,
      stop_loss_pct: 20,
      take_profit_pct: 50
    }
  },
  {
    id: 'steady_pump_rider',
    name: 'Steady Pump Rider',
    description: 'Conservative strategy for riding established pump trends with risk management',
    category: 'pump_detection',
    difficulty: 'intermediate',
    riskLevel: 'medium',
    expectedReturn: '20-80%',
    winRate: 78,
    icon: <TrendingUpIcon />,
    color: '#ff9800',
    isRunning: false,
    config: {
      pump_magnitude_min: 8,
      volume_surge_min: 3,
      confidence_min: 60,
      max_position_size: 500,
      stop_loss_pct: 15,
      take_profit_pct: 30
    }
  },
  {
    id: 'dump_reversal_catcher',
    name: 'Dump Reversal Catcher',
    description: 'Strategy for catching reversals after dump events with momentum analysis',
    category: 'dump_detection',
    difficulty: 'intermediate',
    riskLevel: 'medium',
    expectedReturn: '30-100%',
    winRate: 72,
    icon: <SecurityIcon />,
    color: '#2196f3',
    isRunning: false,
    config: {
      dump_magnitude_min: 12,
      volume_surge_min: 4,
      confidence_min: 65,
      max_position_size: 750,
      stop_loss_pct: 18,
      take_profit_pct: 40
    }
  },
  {
    id: 'quick_scalp_trader',
    name: 'Quick Scalp Trader',
    description: 'Fast scalping strategy for small, frequent profits on pump/dump micro-movements',
    category: 'scalping',
    difficulty: 'advanced',
    riskLevel: 'high',
    expectedReturn: '5-25% per trade',
    winRate: 85,
    icon: <SpeedIcon />,
    color: '#4caf50',
    isRunning: false,
    config: {
      pump_magnitude_min: 3,
      volume_surge_min: 2,
      confidence_min: 50,
      max_position_size: 200,
      stop_loss_pct: 5,
      take_profit_pct: 8,
      max_trade_duration: 300 // 5 minutes
    }
  },
  {
    id: 'swing_pump_trader',
    name: 'Swing Pump Trader',
    description: 'Longer-term strategy for holding through pump cycles with trend following',
    category: 'swing',
    difficulty: 'beginner',
    riskLevel: 'low',
    expectedReturn: '15-60%',
    winRate: 68,
    icon: <AssessmentIcon />,
    color: '#9c27b0',
    isRunning: false,
    config: {
      pump_magnitude_min: 5,
      volume_surge_min: 2.5,
      confidence_min: 55,
      max_position_size: 300,
      stop_loss_pct: 12,
      take_profit_pct: 25,
      min_hold_duration: 1800 // 30 minutes
    }
  }
];

export default function StrategiesPage() {
  const [activeTab, setActiveTab] = useState(0);
  const [userStrategies, setUserStrategies] = useState<Strategy[]>([]);
  const [strategies, setStrategies] = useState<StrategyTemplate[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyTemplate | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [customConfig, setCustomConfig] = useState<any>({});
  const [loading, setLoading] = useState(true);
  // BUG-DV-035 FIX: Add setter to load indicator variants
  const [indicatorVariants, setIndicatorVariants] = useState<IndicatorVariant[]>([]);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info' | 'warning'}>({
    open: false,
    message: '',
    severity: 'info'
  });

  // Intentionally run only on mount to load initial data
  useEffect(() => {
    loadStrategies();
    loadUserStrategies();
    loadIndicatorVariants(); // BUG-DV-035 FIX: Load indicator variants
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // BUG-DV-035 FIX: Load indicator variants for embedded builder
  const loadIndicatorVariants = async () => {
    try {
      const apiVariants = await apiService.getVariants();
      const mappedVariants: IndicatorVariant[] = (apiVariants || []).map((variant: any) => ({
        id: variant.variant_id || variant.id || '',
        name: variant.name || variant.variant_id || '',
        baseType: variant.base_type || variant.baseType || variant.category || 'custom',
        parameters: variant.parameters || {},
        type: (variant.type || 'general') as IndicatorVariant['type'],
        description: variant.description || '',
        isActive: variant.is_active ?? variant.isActive ?? true,
        lastValue: variant.last_value ?? variant.lastValue,
        lastUpdate: variant.last_update ?? variant.lastUpdate,
      }));
      setIndicatorVariants(mappedVariants);
    } catch (error) {
      console.warn('Failed to load indicator variants:', error);
      setIndicatorVariants([]);
    }
  };

  const loadStrategies = async () => {
    try {
      setLoading(true);

      // Load strategies from backend (using 4-section API for consistency with Strategy Builder)
      // FIX: Changed from getStrategies() to get4SectionStrategies() to match save flow
      const backendStrategies = await apiService.get4SectionStrategies();

      // Transform backend data to frontend format
      const transformedStrategies: StrategyTemplate[] = backendStrategies.map(strategy => {
        // Map backend strategy data to frontend template format
        const template = mapStrategyToTemplate(strategy);
        return template;
      });

      // If no strategies from backend, use templates as fallback
      if (transformedStrategies.length === 0) {
        setStrategies(strategyTemplates);
      } else {
        setStrategies(transformedStrategies);
      }

      // Load strategy statuses to update running state
      try {
        const statuses = await apiService.getStrategyStatus();
        // Update running status based on backend response
        setStrategies(prev => prev.map(strategy => ({
          ...strategy,
          isRunning: statuses.some((s: any) => s.strategy_name === strategy.id && s.current_state === 'ACTIVE')
        })));
      } catch (statusError) {
        Logger.warn('StrategiesPage.loadStrategies', { message: 'Failed to load strategy statuses', error: statusError });
      }

    } catch (error) {
      Logger.error('StrategiesPage.loadStrategies', { message: 'Failed to load strategies', error });
      // Fallback to template data
      setStrategies(strategyTemplates);
      setSnackbar({
        open: true,
        message: 'Failed to load strategies from backend, showing templates',
        severity: 'warning'
      });
    } finally {
      setLoading(false);
    }
  };

  const loadUserStrategies = async () => {
    try {
      // Load user-created strategies from backend (using 4-section API)
      // FIX: Changed from getStrategies() to get4SectionStrategies() for consistency
      const userStrategiesData = await apiService.get4SectionStrategies();
      setUserStrategies(userStrategiesData);
    } catch (error) {
      Logger.error('StrategiesPage.loadUserStrategies', { message: 'Failed to load user strategies', error });
      setUserStrategies([]);
    }
  };

  const mapStrategyToTemplate = (strategy: any): StrategyTemplate => {
    // Map backend strategy to frontend template format
    // Supports both old format (config object) and new 4-section format (s1_signal, z1_entry, etc.)
    const config = strategy.config || {};

    // Extract description from either config or 4-section format
    const description = strategy.description || config.description || 'Trading strategy';

    // Determine category from s1_signal section or config
    const category = config.category ||
                     (strategy.s1_signal?.conditions?.some((c: any) => c.indicator_type === 'pump') ? 'pump_detection' : 'pump_detection');

    return {
      id: strategy.id || strategy.strategy_name || strategy.name,
      name: strategy.strategy_name || strategy.name || 'Unnamed Strategy',
      description: description,
      category: category,
      difficulty: config.difficulty || 'intermediate',
      riskLevel: config.risk_level || 'medium',
      expectedReturn: config.expected_return || '10-50%',
      winRate: config.win_rate || 70,
      config: {
        // Merge old config with 4-section data
        ...config,
        s1_signal: strategy.s1_signal,
        z1_entry: strategy.z1_entry,
        o1_cancel: strategy.o1_cancel,
        emergency_exit: strategy.emergency_exit,
      },
      icon: getCategoryIcon(category),
      color: getCategoryColor(category),
      isRunning: strategy.current_state === 'ACTIVE' || strategy.enabled === true,
      performance: strategy.performance
    };
  };

  const getCategoryColor = (category: string): string => {
    switch (category) {
      case 'pump_detection': return '#ff4444';
      case 'dump_detection': return '#2196f3';
      case 'scalping': return '#4caf50';
      case 'swing': return '#9c27b0';
      default: return '#ff9800';
    }
  };

  const handleQuickStart = async (strategy: StrategyTemplate) => {
    try {
      const sessionData = {
        session_type: 'live',
        symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT'], // Default symbols
        strategy_config: {
          [strategy.id]: strategy.config
        },
        config: {
          budget: {
            global_cap: 1000,
            allocations: {}
          }
        },
        idempotent: true
      };

      const response = await apiService.startSession(sessionData);

      // Update strategy status
      setStrategies(prev => prev.map(s =>
        s.id === strategy.id ? { ...s, isRunning: true } : s
      ));

      setSnackbar({
        open: true,
        message: `${strategy.name} started successfully!`,
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: `Failed to start ${strategy.name}`,
        severity: 'error'
      });
    }
  };

  const handleStop = async (strategy: StrategyTemplate) => {
    try {
      // In real app, this would stop the specific strategy
      await apiService.stopSession();

      setStrategies(prev => prev.map(s =>
        s.id === strategy.id ? { ...s, isRunning: false } : s
      ));

      setSnackbar({
        open: true,
        message: `${strategy.name} stopped successfully`,
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: `Failed to stop ${strategy.name}`,
        severity: 'error'
      });
    }
  };

  const handleCustomize = (strategy: StrategyTemplate) => {
    setSelectedStrategy(strategy);
    setCustomConfig({ ...strategy.config });
    setDialogOpen(true);
  };

  const handleSaveCustom = async () => {
    if (!selectedStrategy) return;

    try {
      // Create strategy configuration for backend
      const strategyConfig = {
        strategy_name: selectedStrategy.id,
        config: customConfig,
        enabled: true
      };

      // Save to backend
      await apiService.saveStrategy(strategyConfig);

      // Update local state
      setStrategies(prev => prev.map(strategy =>
        strategy.id === selectedStrategy.id
          ? { ...strategy, config: customConfig }
          : strategy
      ));

      setSnackbar({
        open: true,
        message: `Custom configuration saved for ${selectedStrategy.name}`,
        severity: 'success'
      });
      setDialogOpen(false);
    } catch (error) {
      Logger.error('StrategiesPage.handleSaveCustom', { message: 'Failed to save custom configuration', error });
      setSnackbar({
        open: true,
        message: 'Failed to save custom configuration',
        severity: 'error'
      });
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner': return 'success';
      case 'intermediate': return 'warning';
      case 'advanced': return 'error';
      default: return 'default';
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'success';
      case 'medium': return 'warning';
      case 'high': return 'error';
      default: return 'default';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'pump_detection': return <FlashIcon />;
      case 'dump_detection': return <TrendingUpIcon />;
      case 'scalping': return <SpeedIcon />;
      case 'swing': return <AssessmentIcon />;
      default: return <SettingsIcon />;
    }
  };

  const handleEditStrategy = (strategy: Strategy) => {
    // TODO: Open strategy in builder tab with pre-filled data
    setActiveTab(1); // Switch to builder tab
  };

  const handleCopyStrategy = async (strategy: Strategy) => {
    // TODO: Implement copyStrategy in apiService
    setSnackbar({
      open: true,
      message: 'Copy strategy feature not yet implemented',
      severity: 'info'
    });
    // try {
    //   await apiService.copyStrategy(strategy.strategy_name);
    //   await loadUserStrategies();
    //   setSnackbar({
    //     open: true,
    //     message: `Strategy "${strategy.strategy_name}" copied successfully`,
    //     severity: 'success'
    //   });
    // } catch (error) {
    //   setSnackbar({
    //     open: true,
    //     message: 'Failed to copy strategy',
    //     severity: 'error'
    //   });
    // }
  };

  const handleDeleteStrategy = async (strategy: Strategy) => {
    if (!confirm(`Are you sure you want to delete "${strategy.strategy_name}"?`)) return;

    try {
      await apiService.deleteStrategy(strategy.strategy_name);
      await loadUserStrategies();
      setSnackbar({
        open: true,
        // ✅ UX FIX (2025-12-26): Updated message to reflect that strategy is removed from trading engine
        message: `Strategy "${strategy.strategy_name}" deleted and removed from trading engine`,
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to delete strategy',
        severity: 'error'
      });
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleSaveStrategy = async (strategy: Strategy5Section) => {
    try {
      await apiService.saveStrategy(strategy);
      await loadUserStrategies();
      setSnackbar({
        open: true,
        // ✅ UX FIX (2025-12-26): Updated message to reflect that strategy is now active
        message: 'Strategy saved and activated for trading',
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to save strategy',
        severity: 'error'
      });
    }
  };

  const handleValidateStrategy = async (strategy: Strategy5Section): Promise<StrategyValidationResult> => {
    // BUG-DV-034 FIX: Implement real validation instead of always returning true
    try {
      // Convert 5-section to API format for validation
      const strategyAPIFormat = {
        strategy_name: strategy.name,
        s1_signal: strategy.s1_signal,
        z1_entry: strategy.z1_entry,
        o1_cancel: strategy.o1_cancel,
        ze1_close: strategy.ze1_close,
        emergency_exit: strategy.emergency_exit,
        description: `5-section strategy: ${strategy.name}`
      };
      const response = await apiService.validateStrategy(strategyAPIFormat);
      return {
        isValid: response.data.isValid,
        errors: response.data.errors || [],
        warnings: response.data.warnings || [],
        sectionErrors: {},
      };
    } catch (error: any) {
      // Fallback to basic local validation if server validation fails
      Logger.warn('StrategiesPage.handleValidateStrategy', { message: 'Server validation failed, falling back to local validation', error });

      const errors: string[] = [];
      const warnings: string[] = [];

      // Required field validation
      if (!strategy.name.trim()) {
        errors.push('Strategy name is required');
      }

      // Section validation
      if (strategy.s1_signal.conditions.length === 0) {
        errors.push('S1 Signal section must have at least one condition');
      }

      if (strategy.z1_entry.conditions.length === 0) {
        errors.push('Z1 Entry section must have at least one condition');
      }

      if (strategy.ze1_close.conditions.length === 0) {
        errors.push('ZE1 Close section must have at least one condition');
      }

      // Optional warnings
      if (strategy.o1_cancel.conditions.length === 0) {
        warnings.push('O1 Cancel section has no conditions - orders may never be cancelled');
      }

      if (strategy.emergency_exit.conditions.length === 0) {
        warnings.push('Emergency exit has no conditions - consider adding for risk management');
      }

      return {
        isValid: errors.length === 0,
        errors,
        warnings,
        sectionErrors: {},
      };
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1">
            Strategies & Builder
          </Typography>
          <SystemStatusIndicator showDetails={false} compact={true} />
        </Box>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={handleTabChange} aria-label="strategy tabs">
          <Tab
            icon={<ListIcon />}
            label="Strategies"
            iconPosition="start"
            sx={{ minHeight: 48 }}
          />
          <Tab
            icon={<BuildIcon />}
            label="Builder"
            iconPosition="start"
            sx={{ minHeight: 48 }}
          />
        </Tabs>
      </Box>

      <Box sx={{ mt: 3 }}>
        {activeTab === 0 && (
          // Strategies List Tab
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h5">Your Strategies</Typography>
              <Button variant="contained" startIcon={<BuildIcon />} onClick={() => setActiveTab(1)}>
                Create New Strategy
              </Button>
            </Box>

            {userStrategies.length === 0 ? (
              <Alert severity="info">
                <Typography variant="body2">
                  No strategies created yet. Switch to the Builder tab to create your first strategy.
                </Typography>
              </Alert>
            ) : (
              <Grid container spacing={2}>
                {userStrategies.map((strategy, index) => (
                  <Grid item xs={12} md={6} lg={4} key={`${strategy.strategy_name}-${index}`}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6">{strategy.strategy_name}</Typography>
                        <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                          {/* ✅ UX FIX (2025-12-26): Show activation status */}
                          <Chip
                            label={strategy.enabled ? "Active" : "Inactive"}
                            color={strategy.enabled ? "success" : "default"}
                            size="small"
                            title={strategy.enabled
                              ? "Strategy is loaded and will generate signals"
                              : "Strategy is saved but not generating signals"}
                          />
                          <Chip
                            label={strategy.current_state || "Ready"}
                            size="small"
                            variant="outlined"
                            color={strategy.current_state === 'MONITORING' ? 'info' : 'default'}
                          />
                        </Box>
                        {strategy.symbol && (
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            Symbol: {strategy.symbol}
                          </Typography>
                        )}
                      </CardContent>
                      <CardActions>
                        <IconButton size="small" onClick={() => handleEditStrategy(strategy)}>
                          <EditIcon />
                        </IconButton>
                        <IconButton size="small" onClick={() => handleCopyStrategy(strategy)}>
                          <SaveIcon />
                        </IconButton>
                        <IconButton size="small" color="error" onClick={() => handleDeleteStrategy(strategy)}>
                          <DeleteIcon />
                        </IconButton>
                      </CardActions>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </Box>
        )}

        {activeTab === 1 && (
          // Builder Tab
          <Box>
            <StrategyBuilder5Section
              availableIndicators={indicatorVariants}
              onSave={handleSaveStrategy}
              onValidate={handleValidateStrategy}
            />
          </Box>
        )}
      </Box>

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
