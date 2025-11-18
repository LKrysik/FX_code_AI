import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  Divider,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Save as SaveIcon,
  CheckCircle as CheckCircleIcon,
  Add as AddIcon,
  PlayArrow as PlayIcon,
} from '@mui/icons-material';
import { ConditionBlock } from './ConditionBlock';
import {
  Strategy4Section,
  Condition,
  IndicatorVariant,
  StrategyValidationResult,
} from '@/types/strategy';

interface StrategyBuilder4SectionProps {
  strategy?: Strategy4Section;
  availableIndicators: IndicatorVariant[];
  onSave: (strategy: Strategy4Section) => Promise<void>;
  onValidate: (strategy: Strategy4Section) => Promise<StrategyValidationResult>;
  onRunBacktest?: (strategy: Strategy4Section) => void;
}

export const StrategyBuilder4Section: React.FC<StrategyBuilder4SectionProps> = ({
  strategy,
  availableIndicators,
  onSave,
  onValidate,
  onRunBacktest,
}) => {
  const [strategyData, setStrategyData] = useState<Strategy4Section>(
    strategy || {
      name: '',
      s1_signal: { conditions: [] },
      z1_entry: {
        conditions: [],
        positionSize: { type: 'percentage', value: 10 },
      },
      o1_cancel: {
        timeoutSeconds: 30,
        conditions: [],
        cooldownMinutes: 5,
      },
      ze1_close: {
        conditions: [],
      },
      emergency_exit: {
        conditions: [],
        cooldownMinutes: 5,
        actions: {
          cancelPending: true,
          closePosition: true,
          logEvent: true,
        },
      },
    }
  );

  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['s1'])
  );
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<StrategyValidationResult | null>(null);
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({ open: false, message: '', severity: 'info' });
  const [validationDialogOpen, setValidationDialogOpen] = useState(false);

  const handleSectionToggle = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const updateStrategyData = (updates: Partial<Strategy4Section>) => {
    setStrategyData(prev => ({ ...prev, ...updates }));
  };

  const handleS1Change = (conditions: Condition[]) => {
    updateStrategyData({
      s1_signal: { conditions },
    });
  };

  const handleZ1ConditionsChange = (conditions: Condition[]) => {
    updateStrategyData({
      z1_entry: {
        ...strategyData.z1_entry,
        conditions,
      },
    });
  };

  const handleZ1OrderConfigChange = (orderConfig: Partial<Strategy4Section['z1_entry']>) => {
    updateStrategyData({
      z1_entry: {
        ...strategyData.z1_entry,
        ...orderConfig,
      },
    });
  };

  const handleO1Change = (updates: Partial<Strategy4Section['o1_cancel']>) => {
    updateStrategyData({
      o1_cancel: {
        ...strategyData.o1_cancel,
        ...updates,
      },
    });
  };

  const handleEmergencyChange = (updates: Partial<Strategy4Section['emergency_exit']>) => {
    updateStrategyData({
      emergency_exit: {
        ...strategyData.emergency_exit,
        ...updates,
      },
    });
  };

  const addCondition = (section: 's1' | 'z1' | 'o1' | 'emergency') => {
    const newCondition: Condition = {
      id: `${section}_${Date.now()}`,
      indicatorId: '',
      operator: '>',
      value: 0,
    };

    switch (section) {
      case 's1':
        handleS1Change([...strategyData.s1_signal.conditions, newCondition]);
        break;
      case 'z1':
        handleZ1ConditionsChange([...strategyData.z1_entry.conditions, newCondition]);
        break;
      case 'o1':
        handleO1Change({
          conditions: [...strategyData.o1_cancel.conditions, newCondition],
        });
        break;
      case 'emergency':
        handleEmergencyChange({
          conditions: [...strategyData.emergency_exit.conditions, newCondition],
        });
        break;
    }
  };

  const removeCondition = (section: 's1' | 'z1' | 'o1' | 'emergency', conditionId: string) => {
    switch (section) {
      case 's1':
        handleS1Change(strategyData.s1_signal.conditions.filter(c => c.id !== conditionId));
        break;
      case 'z1':
        handleZ1ConditionsChange(strategyData.z1_entry.conditions.filter(c => c.id !== conditionId));
        break;
      case 'o1':
        handleO1Change({
          conditions: strategyData.o1_cancel.conditions.filter(c => c.id !== conditionId),
        });
        break;
      case 'emergency':
        handleEmergencyChange({
          conditions: strategyData.emergency_exit.conditions.filter(c => c.id !== conditionId),
        });
        break;
    }
  };

  const updateCondition = (section: 's1' | 'z1' | 'o1' | 'emergency', condition: Condition) => {
    switch (section) {
      case 's1':
        handleS1Change(
          strategyData.s1_signal.conditions.map(c => c.id === condition.id ? condition : c)
        );
        break;
      case 'z1':
        handleZ1ConditionsChange(
          strategyData.z1_entry.conditions.map(c => c.id === condition.id ? condition : c)
        );
        break;
      case 'o1':
        handleO1Change({
          conditions: strategyData.o1_cancel.conditions.map(c => c.id === condition.id ? condition : c),
        });
        break;
      case 'emergency':
        handleEmergencyChange({
          conditions: strategyData.emergency_exit.conditions.map(c => c.id === condition.id ? condition : c),
        });
        break;
    }
  };

  const handleValidate = async () => {
    if (!strategyData.name.trim()) {
      setNotification({
        open: true,
        message: 'Please enter a strategy name',
        severity: 'error',
      });
      return;
    }

    setValidating(true);
    try {
      const result = await onValidate(strategyData);
      setValidationResult(result);
      setValidationDialogOpen(true);

      if (result.isValid) {
        setNotification({
          open: true,
          message: 'Strategy validation completed successfully',
          severity: 'success',
        });
      } else {
        setNotification({
          open: true,
          message: `Validation failed: ${result.errors.length} error(s)`,
          severity: 'error',
        });
      }
    } catch (error: any) {
      setNotification({
        open: true,
        message: error.message || 'Validation failed',
        severity: 'error',
      });
    } finally {
      setValidating(false);
    }
  };

  const handleSave = async () => {
    if (!strategyData.name.trim()) {
      setNotification({
        open: true,
        message: 'Please enter a strategy name',
        severity: 'error',
      });
      return;
    }

    setSaving(true);
    try {
      await onSave(strategyData);
      setNotification({
        open: true,
        message: 'Strategy saved successfully!',
        severity: 'success',
      });
    } catch (error: any) {
      setNotification({
        open: true,
        message: error.message || 'Failed to save strategy',
        severity: 'error',
      });
    } finally {
      setSaving(false);
    }
  };

  const getIndicatorsForSection = (section: 's1' | 'z1' | 'o1' | 'emergency'): IndicatorVariant[] => {
    switch (section) {
      case 's1':
      case 'o1':
      case 'emergency':
        return availableIndicators.filter(ind =>
          ind.type === 'general' || ind.type === 'risk'
        );
      case 'z1':
        return availableIndicators.filter(ind =>
          ind.type === 'general' ||
          ind.type === 'stop_loss_price' || ind.type === 'take_profit_price' ||
          ind.type === 'order_price' || ind.type === 'close_price'
        );
      default:
        return availableIndicators;
    }
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Strategy Builder - 4-Section Form
        </Typography>
        <TextField
          fullWidth
          label="Strategy Name"
          value={strategyData.name}
          onChange={(e) => updateStrategyData({ name: e.target.value })}
          sx={{ mb: 2 }}
        />
      </Box>

      {/* 4-Section Accordions */}
      <Box sx={{ mb: 4 }}>
        {/* S1 - Signal Detection */}
        <Accordion
          expanded={expandedSections.has('s1')}
          onChange={() => handleSectionToggle('s1')}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">🎯 SECTION 1: SIGNAL DETECTION (S1)</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              This section defines when to open a signal (lock symbol for further analysis).
              All conditions must be TRUE simultaneously.
            </Typography>

            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Conditions (AND logic):
            </Typography>

            {strategyData.s1_signal.conditions.map((condition, index) => (
              <ConditionBlock
                key={condition.id}
                condition={condition}
                index={index}
                availableIndicators={getIndicatorsForSection('s1')}
                onChange={(updated) => updateCondition('s1', updated)}
                onRemove={() => removeCondition('s1', condition.id)}
                logicType="AND"
              />
            ))}

            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => addCondition('s1')}
              sx={{ mt: 1 }}
            >
              Add Condition
            </Button>
          </AccordionDetails>
        </Accordion>

        {/* Z1 - Order Entry */}
        <Accordion
          expanded={expandedSections.has('z1')}
          onChange={() => handleSectionToggle('z1')}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">💰 SECTION 2: ORDER ENTRY (Z1)</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              This section defines when to actually place an order (after S1 is triggered).
              Symbol is locked until order is placed or signal cancelled.
            </Typography>

            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Entry Conditions (AND logic):
            </Typography>

            {strategyData.z1_entry.conditions.map((condition, index) => (
              <ConditionBlock
                key={condition.id}
                condition={condition}
                index={index}
                availableIndicators={getIndicatorsForSection('z1')}
                onChange={(updated) => updateCondition('z1', updated)}
                onRemove={() => removeCondition('z1', condition.id)}
                logicType="AND"
              />
            ))}

            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => addCondition('z1')}
              sx={{ mt: 1, mb: 3 }}
            >
              Add Condition
            </Button>

            <Divider sx={{ my: 3 }} />

            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Order Configuration:
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <FormControl size="small" sx={{ maxWidth: 300 }}>
                <InputLabel>Price Calculation</InputLabel>
                <Select
                  value={strategyData.z1_entry.priceIndicatorId || ''}
                  label="Price Calculation"
                  onChange={(e) => handleZ1OrderConfigChange({ priceIndicatorId: e.target.value })}
                >
                  <MenuItem value="">
                    <em>Use market price</em>
                  </MenuItem>
                  {availableIndicators
                    .filter(ind => ind.type === 'order_price')
                    .map((indicator) => (
                      <MenuItem key={indicator.id} value={indicator.id}>
                        {indicator.name} ({indicator.baseType})
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>

              <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
                <Box sx={{ flex: 1 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={strategyData.z1_entry.stopLoss?.enabled || false}
                        onChange={(e) => handleZ1OrderConfigChange({
                          stopLoss: {
                            enabled: e.target.checked,
                            offsetPercent: strategyData.z1_entry.stopLoss?.offsetPercent || 1,
                            ...strategyData.z1_entry.stopLoss,
                          },
                        })}
                      />
                    }
                    label="Enable Stop Loss"
                  />

                  {strategyData.z1_entry.stopLoss?.enabled && (
                    <Box sx={{ ml: 4, mt: 1, display: 'flex', gap: 2 }}>
                      <FormControl size="small" sx={{ minWidth: 200 }}>
                        <InputLabel>SL Indicator</InputLabel>
                        <Select
                          value={strategyData.z1_entry.stopLoss?.indicatorId || ''}
                          label="SL Indicator"
                          onChange={(e) => handleZ1OrderConfigChange({
                            stopLoss: {
                              ...strategyData.z1_entry.stopLoss!,
                              indicatorId: e.target.value,
                            },
                          })}
                        >
                          {availableIndicators
                            .filter(ind => ind.type === 'stop_loss_price')
                            .map((indicator) => (
                              <MenuItem key={indicator.id} value={indicator.id}>
                                {indicator.name} ({indicator.baseType})
                              </MenuItem>
                            ))}
                        </Select>
                      </FormControl>

                      <TextField
                        label="Offset %"
                        type="number"
                        size="small"
                        value={strategyData.z1_entry.stopLoss?.offsetPercent || 0}
                        onChange={(e) => handleZ1OrderConfigChange({
                          stopLoss: {
                            ...strategyData.z1_entry.stopLoss!,
                            offsetPercent: parseFloat(e.target.value) || 0,
                          },
                        })}
                        sx={{ width: 100 }}
                      />
                    </Box>
                  )}
                </Box>

                <Box sx={{ flex: 1 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={strategyData.z1_entry.takeProfit?.enabled || false}
                        onChange={(e) => handleZ1OrderConfigChange({
                          takeProfit: {
                            enabled: e.target.checked,
                            offsetPercent: strategyData.z1_entry.takeProfit?.offsetPercent || 2,
                            ...strategyData.z1_entry.takeProfit,
                          },
                        })}
                      />
                    }
                    label="Enable Take Profit (required)"
                  />

                  {strategyData.z1_entry.takeProfit?.enabled && (
                    <Box sx={{ ml: 4, mt: 1, display: 'flex', gap: 2 }}>
                      <FormControl size="small" sx={{ minWidth: 200 }}>
                        <InputLabel>TP Indicator</InputLabel>
                        <Select
                          value={strategyData.z1_entry.takeProfit?.indicatorId || ''}
                          label="TP Indicator"
                          onChange={(e) => handleZ1OrderConfigChange({
                            takeProfit: {
                              ...strategyData.z1_entry.takeProfit!,
                              indicatorId: e.target.value,
                            },
                          })}
                        >
                          {availableIndicators
                            .filter(ind => ind.type === 'take_profit_price')
                            .map((indicator) => (
                              <MenuItem key={indicator.id} value={indicator.id}>
                                {indicator.name} ({indicator.baseType})
                              </MenuItem>
                            ))}
                        </Select>
                      </FormControl>

                      <TextField
                        label="Offset %"
                        type="number"
                        size="small"
                        value={strategyData.z1_entry.takeProfit?.offsetPercent || 0}
                        onChange={(e) => handleZ1OrderConfigChange({
                          takeProfit: {
                            ...strategyData.z1_entry.takeProfit!,
                            offsetPercent: parseFloat(e.target.value) || 0,
                          },
                        })}
                        sx={{ width: 100 }}
                      />
                    </Box>
                  )}
                </Box>
              </Box>

              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Position Size:
                </Typography>

                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                  <FormControl size="small" sx={{ minWidth: 150 }}>
                    <InputLabel>Type</InputLabel>
                    <Select
                      value={strategyData.z1_entry.positionSize.type}
                      label="Type"
                      onChange={(e) => handleZ1OrderConfigChange({
                        positionSize: {
                          ...strategyData.z1_entry.positionSize,
                          type: e.target.value as 'fixed' | 'percentage',
                        },
                      })}
                    >
                      <MenuItem value="percentage">Percentage of balance</MenuItem>
                      <MenuItem value="fixed">Fixed amount</MenuItem>
                    </Select>
                  </FormControl>

                  <TextField
                    label={strategyData.z1_entry.positionSize.type === 'percentage' ? '%' : '$'}
                    type="number"
                    size="small"
                    value={strategyData.z1_entry.positionSize.value}
                    onChange={(e) => handleZ1OrderConfigChange({
                      positionSize: {
                        ...strategyData.z1_entry.positionSize,
                        value: parseFloat(e.target.value) || 0,
                      },
                    })}
                    sx={{ width: 100 }}
                  />
                </Box>
              </Box>
            </Box>
          </AccordionDetails>
        </Accordion>

        {/* O1 - Signal Cancellation */}
        <Accordion
          expanded={expandedSections.has('o1')}
          onChange={() => handleSectionToggle('o1')}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">❌ SECTION 3: SIGNAL CANCELLATION (O1)</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              This section defines when to cancel a signal (unlock symbol) if order was NOT yet placed.
              Either timeout OR conditions trigger.
            </Typography>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Timeout:
              </Typography>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={strategyData.o1_cancel.timeoutSeconds > 0}
                    onChange={(e) => handleO1Change({
                      timeoutSeconds: e.target.checked ? 30 : 0,
                    })}
                  />
                }
                label="Enable timeout"
              />
              {strategyData.o1_cancel.timeoutSeconds > 0 && (
                <TextField
                  label="Cancel after (seconds)"
                  type="number"
                  size="small"
                  value={strategyData.o1_cancel.timeoutSeconds}
                  onChange={(e) => handleO1Change({
                    timeoutSeconds: parseInt(e.target.value) || 0,
                  })}
                  sx={{ ml: 4, mt: 1 }}
                />
              )}
            </Box>

            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              AND Custom Conditions (all conditions = cancel):
            </Typography>

            {strategyData.o1_cancel.conditions.map((condition, index) => (
              <ConditionBlock
                key={condition.id}
                condition={condition}
                index={index}
                availableIndicators={getIndicatorsForSection('o1')}
                onChange={(updated) => updateCondition('o1', updated)}
                onRemove={() => removeCondition('o1', condition.id)}
                logicType="AND"
              />
            ))}

            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => addCondition('o1')}
              sx={{ mt: 1 }}
            >
              Add Condition
            </Button>
          </AccordionDetails>
        </Accordion>

        {/* Emergency Exit */}
        <Accordion
          expanded={expandedSections.has('emergency')}
          onChange={() => handleSectionToggle('emergency')}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">🚨 SECTION 4: EMERGENCY EXIT</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              This section defines when to immediately exit position or cancel pending orders.
              Highest priority - overrides everything.
            </Typography>

            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Emergency Conditions (all conditions = emergency exit):
            </Typography>

            {strategyData.emergency_exit.conditions.map((condition, index) => (
              <ConditionBlock
                key={condition.id}
                condition={condition}
                index={index}
                availableIndicators={getIndicatorsForSection('emergency')}
                onChange={(updated) => updateCondition('emergency', updated)}
                onRemove={() => removeCondition('emergency', condition.id)}
                logicType="AND"
              />
            ))}

            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => addCondition('emergency')}
              sx={{ mt: 1, mb: 3 }}
            >
              Add Condition
            </Button>

            <Divider sx={{ my: 3 }} />

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Post-Emergency Cooldown:
              </Typography>
              <TextField
                label="Prevent trading for (minutes)"
                type="number"
                size="small"
                value={strategyData.emergency_exit.cooldownMinutes}
                onChange={(e) => handleEmergencyChange({
                  cooldownMinutes: parseInt(e.target.value) || 0,
                })}
                sx={{ maxWidth: 250 }}
              />
            </Box>

            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Emergency Actions:
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={strategyData.emergency_exit.actions.cancelPending}
                    onChange={(e) => handleEmergencyChange({
                      actions: {
                        ...strategyData.emergency_exit.actions,
                        cancelPending: e.target.checked,
                      },
                    })}
                  />
                }
                label="Cancel pending order (if not yet filled)"
              />

              <FormControlLabel
                control={
                  <Checkbox
                    checked={strategyData.emergency_exit.actions.closePosition}
                    onChange={(e) => handleEmergencyChange({
                      actions: {
                        ...strategyData.emergency_exit.actions,
                        closePosition: e.target.checked,
                      },
                    })}
                  />
                }
                label="Close position at market (if order filled)"
              />

              <FormControlLabel
                control={
                  <Checkbox
                    checked={strategyData.emergency_exit.actions.logEvent}
                    onChange={(e) => handleEmergencyChange({
                      actions: {
                        ...strategyData.emergency_exit.actions,
                        logEvent: e.target.checked,
                      },
                    })}
                  />
                }
                label="Log emergency event for analysis"
              />
            </Box>
          </AccordionDetails>
        </Accordion>
      </Box>

      {/* Action Buttons */}
      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', mt: 4 }}>
        <Button
          variant="outlined"
          onClick={handleValidate}
          disabled={validating}
        >
          {validating ? 'Validating...' : 'Validate Strategy'}
        </Button>

        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Strategy'}
        </Button>

        {onRunBacktest && (
          <Button
            variant="contained"
            color="success"
            startIcon={<PlayIcon />}
            onClick={() => onRunBacktest(strategyData)}
          >
            Save & Run Backtest
          </Button>
        )}
      </Box>

      {/* Validation Dialog */}
      <Dialog
        open={validationDialogOpen}
        onClose={() => setValidationDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Strategy Validation Results</DialogTitle>
        <DialogContent>
          {validationResult && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Checking strategy "{strategyData.name}"...
              </Typography>

              {validationResult.isValid ? (
                <Alert severity="success" sx={{ mb: 2 }}>
                  ✓ Strategy is valid and ready to use!
                </Alert>
              ) : (
                <Alert severity="error" sx={{ mb: 2 }}>
                  ✗ Validation failed: {validationResult.errors.length} error(s)
                </Alert>
              )}

              {validationResult.errors.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="error">
                    Errors:
                  </Typography>
                  <List dense>
                    {validationResult.errors.map((error, index) => (
                      <ListItem key={index}>
                        <ListItemText primary={error} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              {validationResult.warnings.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="warning.main">
                    Warnings (strategy will work, but consider):
                  </Typography>
                  <List dense>
                    {validationResult.warnings.map((warning, index) => (
                      <ListItem key={index}>
                        <ListItemText primary={warning} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setValidationDialogOpen(false)}>
            {validationResult?.isValid ? 'Continue Editing' : 'Close'}
          </Button>
          {validationResult?.isValid && (
            <Button onClick={() => {
              setValidationDialogOpen(false);
              handleSave();
            }}>
              Save Strategy
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Notification Snackbar */}
      <Snackbar
        open={notification.open}
        autoHideDuration={4000}
        onClose={() => setNotification({ ...notification, open: false })}
      >
        <Alert
          onClose={() => setNotification({ ...notification, open: false })}
          severity={notification.severity}
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};