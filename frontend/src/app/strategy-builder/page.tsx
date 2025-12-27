'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';

import { StrategyBuilder5Section } from '@/components/strategy/StrategyBuilder5Section';
import { QuickBacktestPreview } from '@/components/strategy/QuickBacktestPreview';
import { SignalPreviewChart } from '@/components/strategy/SignalPreviewChart';
import { apiService } from '@/services/api';
import { Strategy5Section, IndicatorVariant, StrategyValidationResult } from '@/types/strategy';
import { Logger } from '@/services/frontendLogService';

interface StrategyListItem {
  id: string;
  strategy_name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index } = props;
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function StrategyBuilderPage() {
  const [currentTab, setCurrentTab] = useState(0);
  
  // Core state
  const [availableIndicators, setAvailableIndicators] = useState<IndicatorVariant[]>([]);
  const [loading, setLoading] = useState(true);

  // Strategy list state
  const [strategiesList, setStrategiesList] = useState<StrategyListItem[]>([]);
  const [strategiesLoading, setStrategiesLoading] = useState(false);

  // Strategy editor state
  const [editingStrategy, setEditingStrategy] = useState<Strategy5Section | null>(null);
  const [isNewStrategy, setIsNewStrategy] = useState(false);

  // UI state
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });

  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean;
    strategyId: string | null;
    strategyName: string;
  }>({
    open: false,
    strategyId: null,
    strategyName: '',
  });

  // Load initial data
  // Intentionally run only on mount to load initial data
  useEffect(() => {
    Logger.info('StrategyBuilderPage.mount', { message: 'Starting to load initial data' });
    loadInitialData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Helper function to convert API variant to frontend IndicatorVariant
  const mapApiVariantToIndicatorVariant = (apiVariant: any): IndicatorVariant => ({
    id: apiVariant.id,
    name: apiVariant.name,
    baseType: apiVariant.base_indicator_type,  // API: base_indicator_type -> Frontend: baseType
    type: apiVariant.variant_type,             // API: variant_type -> Frontend: type
    description: apiVariant.description || '',
    parameters: apiVariant.parameters || {},
    isActive: true, // Default to active
    lastValue: undefined,
    lastUpdate: undefined
  });

  const loadInitialData = async () => {
    try {
      setLoading(true);

      // ✅ ARCHITECTURE FIX: Check authentication state instead of auto-login
      // Previously: Automatic login with hardcoded credentials ('admin', 'admin123')
      // Problem: Password mismatch with backend (.env has 'supersecret'), caused 4x failed login attempts
      // Solution: Check if user is already authenticated, let them login explicitly via LoginForm
      // Related: docs/bugfixes/STRATEGY_BUILDER_AUTH_ISSUE.md

      // Load indicators from API (works without authentication)
      try {
        Logger.info('StrategyBuilderPage.loadInitialData', { message: 'Loading indicator variants' });
        const apiVariants = await apiService.getVariants();
        const mappedVariants = (apiVariants || []).map(mapApiVariantToIndicatorVariant);
        Logger.info('StrategyBuilderPage.loadInitialData', { message: 'Loaded variants', count: mappedVariants.length });
        setAvailableIndicators(mappedVariants);
      } catch (indicatorError) {
        Logger.warn('StrategyBuilderPage.loadInitialData', { message: 'Failed to load indicators', error: indicatorError });
        showNotification('Failed to load indicators - using empty list', 'warning');
        setAvailableIndicators([]);
      }

      // Load strategies list (requires authentication)
      await loadStrategiesList();
    } catch (error) {
      Logger.error('StrategyBuilderPage.loadInitialData', { message: 'Failed to load initial data', error });
      showNotification('Failed to load data - check if you are logged in', 'warning');
      // Set empty strategies list as fallback
      setStrategiesList([]);
    } finally {
      setLoading(false);
    }
  };

  const loadStrategiesList = async () => {
    try {
      setStrategiesLoading(true);
      const strategies = await apiService.get4SectionStrategies();
      setStrategiesList(strategies || []);
    } catch (error) {
      Logger.error('StrategyBuilderPage.loadStrategiesList', { message: 'Failed to load strategies', error });
      showNotification('Cannot connect to API server - working offline', 'warning');
      // Set empty array as fallback so UI can still work
      setStrategiesList([]);
    } finally {
      setStrategiesLoading(false);
    }
  };

  const showNotification = (message: string, severity: 'success' | 'error' | 'warning' | 'info') => {
    setNotification({
      open: true,
      message,
      severity,
    });
  };

  const handleCloseNotification = () => {
    setNotification(prev => ({ ...prev, open: false }));
  };

  const handleCreateStrategy = () => {
    setEditingStrategy({
      name: '',
      s1_signal: {
        conditions: [],
      },
      z1_entry: {
        conditions: [],
        positionSize: { type: 'percentage', value: 1 },
      },
      o1_cancel: {
        timeoutSeconds: 300,
        conditions: [],
        cooldownMinutes: 5,
      },
      ze1_close: { 
        conditions: [] 
      },
      emergency_exit: {
        conditions: [],
        cooldownMinutes: 60,
        actions: {
          cancelPending: true,
          closePosition: true,
          logEvent: true,
        },
      },
    });
    setIsNewStrategy(true);
    setCurrentTab(1);
  };

  const handleEditStrategy = async (strategyId: string) => {
    try {
      const strategy = await apiService.get4SectionStrategy(strategyId);
      if (strategy) {
        setEditingStrategy(strategy);
        setIsNewStrategy(false);
        setCurrentTab(1);
      }
    } catch (error) {
      Logger.error('StrategyBuilderPage.handleEditStrategy', { message: 'Failed to load strategy', error, strategyId });
      showNotification('Failed to load strategy', 'error');
    }
  };

  const handleDeleteStrategy = (strategyId: string, strategyName: string) => {
    setDeleteDialog({
      open: true,
      strategyId,
      strategyName,
    });
  };

  const confirmDeleteStrategy = async () => {
    if (deleteDialog.strategyId) {
      try {
        await apiService.delete4SectionStrategy(deleteDialog.strategyId);
        showNotification('Strategy deleted successfully', 'success');
        await loadStrategiesList();
      } catch (error) {
        Logger.error('StrategyBuilderPage.confirmDeleteStrategy', { message: 'Failed to delete strategy', error, strategyId: deleteDialog.strategyId });
        showNotification('Failed to delete strategy', 'error');
      }
    }
    setDeleteDialog({ open: false, strategyId: null, strategyName: '' });
  };

  const convertStrategy5SectionToAPIFormat = (strategy5: Strategy5Section) => {
    // Backend actually expects 5-section format based on strategy_schema.py!
    // Don't remove ze1_close - send it as-is
    return {
      strategy_name: strategy5.name,
      s1_signal: strategy5.s1_signal,
      z1_entry: strategy5.z1_entry,
      o1_cancel: strategy5.o1_cancel,
      ze1_close: strategy5.ze1_close, // Keep ze1_close - backend expects it!
      emergency_exit: strategy5.emergency_exit,
      description: `5-section strategy: ${strategy5.name}`
    };
  };

  const handleSaveStrategy = async (strategy: Strategy5Section) => {
    try {
      // Convert 5-section to API format
      const strategyAPIFormat = convertStrategy5SectionToAPIFormat(strategy);

      // Debug: Log what we're sending to API
      Logger.debug('StrategyBuilderPage.handleSaveStrategy', { message: 'Saving strategy to API', strategy: strategyAPIFormat });

      if (isNewStrategy) {
        await apiService.saveStrategy(strategyAPIFormat);
        // ✅ UX FIX (2025-12-26): Updated message to reflect that strategy is now active
        showNotification('Strategy created and activated for trading', 'success');
      } else if (editingStrategy?.id) {
        await apiService.update4SectionStrategy(editingStrategy.id, strategyAPIFormat);
        // ✅ UX FIX (2025-12-26): Updated message to reflect that changes are now active
        showNotification('Strategy updated - changes are now active', 'success');
      }
      
      // Return to strategies list
      setCurrentTab(0);
      setEditingStrategy(null);
      setIsNewStrategy(false);
      await loadStrategiesList();
    } catch (error) {
      Logger.error('StrategyBuilderPage.handleSaveStrategy', { message: 'Failed to save strategy', error });
      showNotification('Failed to save strategy', 'error');
    }
  };

  const handleValidateStrategy = async (strategy: Strategy5Section): Promise<StrategyValidationResult> => {
    try {
      // Convert 5-section to API format for validation
      const strategyAPIFormat = convertStrategy5SectionToAPIFormat(strategy);
      const response = await apiService.validateStrategy(strategyAPIFormat);
      return {
        isValid: response.data.isValid,
        errors: response.data.errors || [],
        warnings: response.data.warnings || [],
        sectionErrors: {},
      };
    } catch (error: any) {
      // Fallback to basic validation if server validation fails
      Logger.warn('StrategyBuilderPage.handleValidateStrategy', { message: 'Server validation failed, falling back to local validation', error });

      const errors: string[] = [];
      const warnings: string[] = [];

      if (!strategy.name.trim()) {
        errors.push('Strategy name is required');
      }

      if (strategy.s1_signal.conditions.length === 0) {
        errors.push('S1 section must have at least one condition');
      }

      if (strategy.z1_entry.conditions.length === 0) {
        errors.push('Z1 section must have at least one condition');
      }

      if (strategy.ze1_close.conditions.length === 0) {
        errors.push('ZE1 section must have at least one condition');
      }

      return {
        isValid: errors.length === 0,
        errors,
        warnings,
        sectionErrors: {},
      };
    }
  };

  const handleBackToList = () => {
    setCurrentTab(0);
    setEditingStrategy(null);
    setIsNewStrategy(false);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h4" sx={{ mb: 2 }}>Strategy Builder</Typography>
      
      <Tabs value={currentTab} onChange={(e, v) => setCurrentTab(v)}>
        <Tab label="Strategies List" />
        <Tab 
          label={isNewStrategy ? "Create Strategy" : "Edit Strategy"} 
          disabled={!editingStrategy && !isNewStrategy}
        />
      </Tabs>

      <TabPanel value={currentTab} index={0}>
        <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h5">Strategies</Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreateStrategy}
          >
            Create New Strategy
          </Button>
        </Box>

        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Updated</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {strategiesLoading ? (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    Loading strategies...
                  </TableCell>
                </TableRow>
              ) : strategiesList.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    No strategies found. Create your first strategy!
                  </TableCell>
                </TableRow>
              ) : (
                strategiesList.map((strategy) => (
                  <TableRow key={strategy.id}>
                    <TableCell component="th" scope="row">
                      <Typography variant="subtitle2">{strategy.strategy_name}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {strategy.description || 'No description'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {new Date(strategy.created_at).toLocaleDateString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {new Date(strategy.updated_at).toLocaleDateString()}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => handleEditStrategy(strategy.id)}
                        title="Edit Strategy"
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteStrategy(strategy.id, strategy.strategy_name)}
                        title="Delete Strategy"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </TabPanel>

      <TabPanel value={currentTab} index={1}>
        {editingStrategy ? (
          <Box>
            <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
              <IconButton onClick={handleBackToList}>
                <ArrowBackIcon />
              </IconButton>
              <Typography variant="h5">
                {isNewStrategy ? 'Create New Strategy' : `Edit: ${editingStrategy.name}`}
              </Typography>
            </Box>
            
            <StrategyBuilder5Section
              strategy={editingStrategy}
              onSave={handleSaveStrategy}
              onValidate={handleValidateStrategy}
              availableIndicators={availableIndicators}
            />

            {/* SB-02: Quick Backtest Preview */}
            <QuickBacktestPreview
              strategy={editingStrategy}
              onRunFullBacktest={() => {
                showNotification('Full backtest requires backend integration', 'info');
              }}
            />

            {/* SB-03: Signal Preview Chart */}
            <SignalPreviewChart
              strategy={editingStrategy}
            />
          </Box>
        ) : (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
            <Typography color="text.secondary">
              No strategy selected. Please select a strategy from the list or create a new one.
            </Typography>
          </Box>
        )}
      </TabPanel>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, strategyId: null, strategyName: '' })}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete the strategy "{deleteDialog.strategyName}"?
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setDeleteDialog({ open: false, strategyId: null, strategyName: '' })}
          >
            Cancel
          </Button>
          <Button onClick={confirmDeleteStrategy} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Notification Snackbar */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={handleCloseNotification}
      >
        <Alert 
          onClose={handleCloseNotification} 
          severity={notification.severity}
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

