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
  const [indicatorVariants] = useState<IndicatorVariant[]>([]);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info' | 'warning'}>({
    open: false,
    message: '',
    severity: 'info'
  });

  // Intentionally run only on mount to load initial data
  useEffect(() => {
    loadStrategies();
    loadUserStrategies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadStrategies = async () => {
    try {
      setLoading(true);

      // Load strategies from backend
      const backendStrategies = await apiService.getStrategies();

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
        console.warn('Failed to load strategy statuses:', statusError);
      }

    } catch (error) {
      console.error('Failed to load strategies:', error);
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
      // Load user-created strategies from backend
      const userStrategiesData = await apiService.getStrategies();
      setUserStrategies(userStrategiesData);
    } catch (error) {
      console.error('Failed to load user strategies:', error);
      setUserStrategies([]);
    }
  };

  const mapStrategyToTemplate = (strategy: any): StrategyTemplate => {
    // Map backend strategy to frontend template format
    const config = strategy.config || {};

    return {
      id: strategy.strategy_name || strategy.name,
      name: strategy.strategy_name || strategy.name,
      description: config.description || 'Trading strategy',
      category: config.category || 'pump_detection',
      difficulty: config.difficulty || 'intermediate',
      riskLevel: config.risk_level || 'medium',
      expectedReturn: config.expected_return || '10-50%',
      winRate: config.win_rate || 70,
      config: config,
      icon: getCategoryIcon(config.category || 'pump_detection'),
      color: getCategoryColor(config.category || 'pump_detection'),
      isRunning: strategy.current_state === 'ACTIVE',
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
      console.error('Failed to save custom configuration:', error);
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
        message: `Strategy "${strategy.strategy_name}" deleted successfully`,
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
        message: 'Strategy saved successfully',
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
    // TODO: Implement validation logic
    return {
      isValid: true,
      errors: [],
      warnings: [],
      sectionErrors: {}
    };
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
                        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                          <Chip
                            label={strategy.enabled ? "Enabled" : "Disabled"}
                            color={strategy.enabled ? "primary" : "default"}
                            size="small"
                          />
                          <Chip
                            label={strategy.current_state || "Unknown"}
                            size="small"
                            variant="outlined"
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
