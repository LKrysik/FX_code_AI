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
  Radio,
  RadioGroup,
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
  Strategy5Section,
  Condition,
  IndicatorVariant,
  StrategyValidationResult,
} from '@/types/strategy';

interface StrategyBuilder5SectionProps {
  strategy?: Strategy5Section;
  availableIndicators: IndicatorVariant[];
  onSave: (strategy: Strategy5Section) => Promise<void>;
  onValidate: (strategy: Strategy5Section) => Promise<StrategyValidationResult>;
  onRunBacktest?: (strategy: Strategy5Section) => void;
}

export const StrategyBuilder5Section: React.FC<StrategyBuilder5SectionProps> = ({
  strategy,
  availableIndicators,
  onSave,
  onValidate,
  onRunBacktest,
}) => {
  const [strategyData, setStrategyData] = useState<Strategy5Section>(
    strategy || {
      name: '',
      direction: 'LONG',  // ⚠️ CRITICAL FIX: Default direction for new strategies
      s1_signal: { conditions: [] },
      z1_entry: {
        conditions: [],
        positionSize: { type: 'percentage', value: 10 },
        timeoutSeconds: 0, // SPRINT_GOAL_04: Z1 timeout
      },
      o1_cancel: {
        timeoutSeconds: 30,
        conditions: [],
        cooldownMinutes: 0, // SPRINT_GOAL_04: O1 cooldown
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
      // SPRINT_GOAL_04: Section 4 (ZE1) is now optional
      ze1_enabled: false,
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

  // Update strategyData when strategy prop changes
  useEffect(() => {
    if (strategy) {
      setStrategyData(prev => ({
        name: strategy.name || '',
        direction: strategy.direction || 'LONG',  // ⚠️ CRITICAL FIX: Include direction field
        s1_signal: strategy.s1_signal || { conditions: [] },
        z1_entry: {
          conditions: strategy.z1_entry?.conditions || [],
          positionSize: strategy.z1_entry?.positionSize || { type: 'percentage', value: 10 },
          timeoutSeconds: strategy.z1_entry?.timeoutSeconds || 0,
          stopLoss: strategy.z1_entry?.stopLoss || prev.z1_entry.stopLoss,
          takeProfit: strategy.z1_entry?.takeProfit || prev.z1_entry.takeProfit,
        },
        o1_cancel: {
          timeoutSeconds: strategy.o1_cancel?.timeoutSeconds || 30,
          conditions: strategy.o1_cancel?.conditions || [],
          cooldownMinutes: strategy.o1_cancel?.cooldownMinutes || 0,
        },
        ze1_close: {
          conditions: strategy.ze1_close?.conditions || [],
          riskAdjustedPricing: strategy.ze1_close?.riskAdjustedPricing || prev.ze1_close.riskAdjustedPricing,
        },
        emergency_exit: {
          conditions: strategy.emergency_exit?.conditions || [],
          cooldownMinutes: strategy.emergency_exit?.cooldownMinutes || 5,
          actions: strategy.emergency_exit?.actions || {
            cancelPending: true,
            closePosition: true,
            logEvent: true,
          },
        },
      }));
    }
  }, [strategy]);

  const handleSectionToggle = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const updateStrategyData = (updates: Partial<Strategy5Section>) => {
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

  const handleZ1OrderConfigChange = (orderConfig: Partial<Strategy5Section['z1_entry']>) => {
    updateStrategyData({
      z1_entry: {
        ...strategyData.z1_entry,
        ...orderConfig,
      },
    });
  };

  const handleO1Change = (updates: Partial<Strategy5Section['o1_cancel']>) => {
    updateStrategyData({
      o1_cancel: {
        ...strategyData.o1_cancel,
        ...updates,
      },
    });
  };

  const handleZE1ConditionsChange = (conditions: Condition[]) => {
    updateStrategyData({
      ze1_close: {
        ...strategyData.ze1_close,
        conditions,
      },
    });
  };

  const handleZE1OrderConfigChange = (closeConfig: Partial<Strategy5Section['ze1_close']>) => {
    updateStrategyData({
      ze1_close: {
        ...strategyData.ze1_close,
        ...closeConfig,
      },
    });
  };

  const handleEmergencyChange = (updates: Partial<Strategy5Section['emergency_exit']>) => {
    updateStrategyData({
      emergency_exit: {
        ...strategyData.emergency_exit,
        ...updates,
      },
    });
  };

  const addCondition = (section: 's1' | 'z1' | 'o1' | 'ze1' | 'emergency') => {
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
      case 'ze1':
        handleZE1ConditionsChange([...strategyData.ze1_close.conditions, newCondition]);
        break;
      case 'emergency':
        handleEmergencyChange({
          conditions: [...strategyData.emergency_exit.conditions, newCondition],
        });
        break;
    }
  };

  const removeCondition = (section: 's1' | 'z1' | 'o1' | 'ze1' | 'emergency', conditionId: string) => {
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
      case 'ze1':
        handleZE1ConditionsChange(strategyData.ze1_close.conditions.filter(c => c.id !== conditionId));
        break;
      case 'emergency':
        handleEmergencyChange({
          conditions: strategyData.emergency_exit.conditions.filter(c => c.id !== conditionId),
        });
        break;
    }
  };

  const updateCondition = (section: 's1' | 'z1' | 'o1' | 'ze1' | 'emergency', condition: Condition) => {
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
      case 'ze1':
        handleZE1ConditionsChange(
          strategyData.ze1_close.conditions.map(c => c.id === condition.id ? condition : c)
        );
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
      // Skip ZE1 validation if disabled
      const strategyToValidate = {
        ...strategyData,
        ze1_close: strategyData.ze1_enabled ? strategyData.ze1_close : { conditions: [] }
      };

      const result = await onValidate(strategyToValidate);
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
    if (!strategyData.name || !strategyData.name.trim()) {
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

  const getIndicatorsForSection = (section: 's1' | 'z1' | 'o1' | 'ze1' | 'emergency'): IndicatorVariant[] => {
    switch (section) {
      case 's1':
      case 'o1':
      case 'emergency':
        return availableIndicators.filter(ind =>
          ind.type === 'general' || ind.type === 'risk'
        );
      case 'z1':
        return availableIndicators.filter(ind =>
          ind.type === 'general' || ind.type === 'risk'
        );
      case 'ze1':
        return availableIndicators.filter(ind =>
          ind.type === 'general' || ind.type === 'risk' ||
          ind.type === 'close_order'
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
          Strategy Builder - 5-Section Form
        </Typography>
        <TextField
          fullWidth
          label="Strategy Name"
          value={strategyData.name}
          onChange={(e) => updateStrategyData({ name: e.target.value })}
          sx={{ mb: 2 }}
        />

        {/* Direction Selector - SHORT Support */}
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Trading Direction</InputLabel>
          <Select
            value={strategyData.direction || 'LONG'}
            label="Trading Direction"
            onChange={(e) => updateStrategyData({ direction: e.target.value as 'LONG' | 'SHORT' | 'BOTH' })}
          >
            <MenuItem value="LONG">
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography>🔼 LONG</Typography>
                <Typography variant="caption" color="text.secondary">
                  - Profit from price increase (Buy low, Sell high)
                </Typography>
              </Box>
            </MenuItem>
            <MenuItem value="SHORT">
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography>🔽 SHORT</Typography>
                <Typography variant="caption" color="text.secondary">
                  - Profit from price drop (Short high, Cover low)
                </Typography>
              </Box>
            </MenuItem>
            <MenuItem value="BOTH" disabled>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography>⚡ BOTH</Typography>
                <Typography variant="caption" color="text.secondary">
                  - (Not yet implemented)
                </Typography>
              </Box>
            </MenuItem>
          </Select>
          {strategyData.direction === 'SHORT' && (
            <Box sx={{ mt: 1, p: 1.5, bgcolor: 'warning.lighter', borderRadius: 1 }}>
              <Typography variant="caption" color="warning.dark">
                ⚠️ SHORT selling strategies profit from price drops. Ideal for pump & dump detection.
                Ensure your indicators detect downward momentum.
              </Typography>
            </Box>
          )}
        </FormControl>
      </Box>

      {/* 5-Section Accordions */}
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
                    .filter(ind => 
                      ind.type === 'general' && 
                      ['TWPA', 'VWAP', 'MAX_PRICE', 'MIN_PRICE', 'FIRST_PRICE', 'LAST_PRICE', 'SMA', 'EMA'].includes(ind.baseType)
                    )
                    .map((indicator) => (
                      <MenuItem key={indicator.id} value={indicator.id}>
                        {indicator.name} ({indicator.baseType})
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>

              {/* Z1 Timeout - SPRINT_GOAL_04 Enhancement */}
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Entry Timeout:
                </Typography>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={strategyData.z1_entry.timeoutSeconds ? strategyData.z1_entry.timeoutSeconds > 0 : false}
                      onChange={(e) => handleZ1OrderConfigChange({
                        timeoutSeconds: e.target.checked ? 300 : 0, // 5 minutes default
                      })}
                    />
                  }
                  label="Enable entry timeout"
                />
                {strategyData.z1_entry.timeoutSeconds && strategyData.z1_entry.timeoutSeconds > 0 && (
                  <TextField
                    label="Cancel entry after (seconds)"
                    type="number"
                    size="small"
                    value={strategyData.z1_entry.timeoutSeconds}
                    onChange={(e) => handleZ1OrderConfigChange({
                      timeoutSeconds: parseInt(e.target.value) || 0,
                    })}
                    sx={{ ml: 4, mt: 1, maxWidth: 200 }}
                  />
                )}
              </Box>

              <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
                <Box sx={{ flex: 1 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={strategyData.z1_entry.stopLoss?.enabled || false}
                        onChange={(e) => handleZ1OrderConfigChange({
                          stopLoss: {
                            ...strategyData.z1_entry.stopLoss,
                            enabled: e.target.checked,
                            offsetPercent: strategyData.z1_entry.stopLoss?.offsetPercent || 1.5,
                          },
                        })}
                      />
                    }
                    label="Enable Stop Loss"
                  />

                  {strategyData.z1_entry.stopLoss?.enabled && (
                    <Box sx={{ ml: 4, mt: 2, p: 2, border: 1, borderColor: 'grey.300', borderRadius: 1 }}>
                      {/* Stop Loss Method Selection */}
                      <FormControl component="fieldset" sx={{ mb: 2 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Stop Loss Method
                        </Typography>
                        <RadioGroup
                          value={strategyData.z1_entry.stopLoss?.indicatorId ? 'indicator' : 'relative'}
                          onChange={(e) => {
                            const isIndicator = e.target.value === 'indicator';
                            handleZ1OrderConfigChange({
                              stopLoss: {
                                ...strategyData.z1_entry.stopLoss!,
                                indicatorId: isIndicator ? '' : undefined,
                                offsetPercent: isIndicator ? 0 : (strategyData.z1_entry.stopLoss?.offsetPercent || 1.5),
                              },
                            });
                          }}
                        >
                          <FormControlLabel 
                            value="indicator" 
                            control={<Radio size="small" />} 
                            label="Use indicator + offset" 
                          />
                          <FormControlLabel 
                            value="relative" 
                            control={<Radio size="small" />} 
                            label="Relative to Entry (Short) - percentage" 
                          />
                        </RadioGroup>
                      </FormControl>

                      {/* Option A: Indicator + Offset */}
                      {strategyData.z1_entry.stopLoss?.indicatorId !== undefined && (
                        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
                          <FormControl size="small" sx={{ minWidth: 180 }}>
                            <InputLabel>Price Indicator</InputLabel>
                            <Select
                              value={strategyData.z1_entry.stopLoss?.indicatorId || ''}
                              label="Price Indicator"
                              onChange={(e) => handleZ1OrderConfigChange({
                                stopLoss: {
                                  ...strategyData.z1_entry.stopLoss!,
                                  indicatorId: e.target.value,
                                },
                              })}
                            >
                              <MenuItem value="">
                                <em>Select indicator</em>
                              </MenuItem>
                              {availableIndicators
                                .filter(ind => 
                                  ind.type === 'general' && 
                                  ['TWPA', 'VWAP', 'MAX_PRICE', 'MIN_PRICE', 'FIRST_PRICE', 'LAST_PRICE', 'SMA', 'EMA'].includes(ind.baseType)
                                )
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
                            helperText="+ increases, - decreases"
                          />
                        </Box>
                      )}

                      {/* Option B: Relative to Entry */}
                      {strategyData.z1_entry.stopLoss?.indicatorId === undefined && (
                        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
                          <TextField
                            label="Stop Loss %"
                            type="number"
                            size="small"
                            value={strategyData.z1_entry.stopLoss?.offsetPercent || 1.5}
                            onChange={(e) => handleZ1OrderConfigChange({
                              stopLoss: {
                                ...strategyData.z1_entry.stopLoss!,
                                offsetPercent: parseFloat(e.target.value) || 1.5,
                              },
                            })}
                            sx={{ width: 120 }}
                            helperText="% below entry price"
                          />
                          <FormControl size="small" sx={{ minWidth: 150 }}>
                            <InputLabel>Calculation Mode</InputLabel>
                            <Select
                              value={strategyData.z1_entry.stopLoss?.calculationMode || 'RELATIVE_TO_ENTRY'}
                              label="Calculation Mode"
                              onChange={(e) => handleZ1OrderConfigChange({
                                stopLoss: {
                                  ...strategyData.z1_entry.stopLoss!,
                                  calculationMode: e.target.value as 'ABSOLUTE' | 'RELATIVE_TO_ENTRY',
                                },
                              })}
                            >
                              <MenuItem value="RELATIVE_TO_ENTRY">Relative to Entry</MenuItem>
                              <MenuItem value="ABSOLUTE">Absolute</MenuItem>
                            </Select>
                          </FormControl>
                        </Box>
                      )}

                      {/* Risk-Adjusted Scaling */}
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={strategyData.z1_entry.stopLoss?.riskScaling?.enabled || false}
                            onChange={(e) => handleZ1OrderConfigChange({
                              stopLoss: {
                                ...strategyData.z1_entry.stopLoss!,
                                riskScaling: {
                                  ...strategyData.z1_entry.stopLoss?.riskScaling,
                                  enabled: e.target.checked,
                                },
                              },
                            })}
                          />
                        }
                        label="Enable risk-adjusted scaling"
                        sx={{ mb: 1 }}
                      />
                      
                      {strategyData.z1_entry.stopLoss?.riskScaling?.enabled && (
                        <Box sx={{ ml: 4, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
                            Scale SL based on risk level (lower risk = tighter SL, higher risk = looser SL)
                          </Typography>
                          
                          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
                            <FormControl size="small" sx={{ minWidth: 150 }}>
                              <InputLabel>Risk Indicator</InputLabel>
                              <Select
                                value={strategyData.z1_entry.stopLoss?.riskScaling?.riskIndicatorId || ''}
                                label="Risk Indicator"
                                onChange={(e) => handleZ1OrderConfigChange({
                                  stopLoss: {
                                    ...strategyData.z1_entry.stopLoss!,
                                    riskScaling: {
                                      ...strategyData.z1_entry.stopLoss?.riskScaling!,
                                      riskIndicatorId: e.target.value,
                                    },
                                  },
                                })}
                              >
                                {availableIndicators
                                  .filter(ind => ind.type === 'risk')
                                  .map((indicator) => (
                                    <MenuItem key={indicator.id} value={indicator.id}>
                                      {indicator.name} ({indicator.baseType})
                                    </MenuItem>
                                  ))}
                              </Select>
                            </FormControl>
                          </Box>
                          
                          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 1 }}>
                            <TextField
                              label="Low Risk Threshold"
                              type="number"
                              size="small"
                              value={strategyData.z1_entry.stopLoss?.riskScaling?.lowRiskThreshold || 30}
                              onChange={(e) => handleZ1OrderConfigChange({
                                stopLoss: {
                                  ...strategyData.z1_entry.stopLoss!,
                                  riskScaling: {
                                    ...strategyData.z1_entry.stopLoss?.riskScaling!,
                                    lowRiskThreshold: parseFloat(e.target.value) || 30,
                                  },
                                },
                              })}
                              sx={{ width: 140 }}
                            />
                            <TextField
                              label="Low Risk Scale %"
                              type="number"
                              size="small"
                              value={strategyData.z1_entry.stopLoss?.riskScaling?.lowRiskScale || 150}
                              onChange={(e) => handleZ1OrderConfigChange({
                                stopLoss: {
                                  ...strategyData.z1_entry.stopLoss!,
                                  riskScaling: {
                                    ...strategyData.z1_entry.stopLoss?.riskScaling!,
                                    lowRiskScale: parseFloat(e.target.value) || 150,
                                  },
                                },
                              })}
                              sx={{ width: 140 }}
                            />
                          </Box>
                          
                          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                            <TextField
                              label="High Risk Threshold"
                              type="number"
                              size="small"
                              value={strategyData.z1_entry.stopLoss?.riskScaling?.highRiskThreshold || 80}
                              onChange={(e) => handleZ1OrderConfigChange({
                                stopLoss: {
                                  ...strategyData.z1_entry.stopLoss!,
                                  riskScaling: {
                                    ...strategyData.z1_entry.stopLoss?.riskScaling!,
                                    highRiskThreshold: parseFloat(e.target.value) || 80,
                                  },
                                },
                              })}
                              sx={{ width: 140 }}
                            />
                            <TextField
                              label="High Risk Scale %"
                              type="number"
                              size="small"
                              value={strategyData.z1_entry.stopLoss?.riskScaling?.highRiskScale || 60}
                              onChange={(e) => handleZ1OrderConfigChange({
                                stopLoss: {
                                  ...strategyData.z1_entry.stopLoss!,
                                  riskScaling: {
                                    ...strategyData.z1_entry.stopLoss?.riskScaling!,
                                    highRiskScale: parseFloat(e.target.value) || 60,
                                  },
                                },
                              })}
                              sx={{ width: 140 }}
                            />
                          </Box>
                        </Box>
                      )}
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
                            ...strategyData.z1_entry.takeProfit,
                            enabled: e.target.checked,
                          },
                        })}
                      />
                    }
                    label="Enable Take Profit (required)"
                  />

                  {strategyData.z1_entry.takeProfit?.enabled && (
                    <Box sx={{ ml: 4, mt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Box sx={{ display: 'flex', gap: 2 }}>
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
                              .filter(ind => ind.type === 'take_profit')
                              .map((indicator) => (
                                <MenuItem key={indicator.id} value={indicator.id}>
                                  {indicator.name} ({indicator.baseType})
                                </MenuItem>
                              ))}
                          </Select>
                        </FormControl>

                        <TextField
                          label="Base Offset %"
                          type="number"
                          size="small"
                          value={strategyData.z1_entry.takeProfit?.offsetPercent || 0}
                          onChange={(e) => handleZ1OrderConfigChange({
                            takeProfit: {
                              ...strategyData.z1_entry.takeProfit!,
                              offsetPercent: parseFloat(e.target.value) || 0,
                            },
                          })}
                          sx={{ width: 120 }}
                        />

                        <FormControl size="small" sx={{ minWidth: 150 }}>
                          <InputLabel>Calculation Mode</InputLabel>
                          <Select
                            value={strategyData.z1_entry.takeProfit?.calculationMode || 'ABSOLUTE'}
                            label="Calculation Mode"
                            onChange={(e) => handleZ1OrderConfigChange({
                              takeProfit: {
                                ...strategyData.z1_entry.takeProfit!,
                                calculationMode: e.target.value as 'ABSOLUTE' | 'RELATIVE_TO_ENTRY',
                              },
                            })}
                          >
                            <MenuItem value="ABSOLUTE">Absolute %</MenuItem>
                            <MenuItem value="RELATIVE_TO_ENTRY">Relative to Entry (SHORT)</MenuItem>
                          </Select>
                        </FormControl>
                      </Box>

                      {/* Risk Scaling for Take Profit - SPRINT_GOAL_04 Enhancement */}
                      <Box sx={{ ml: 2 }}>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={strategyData.z1_entry.takeProfit?.riskScaling?.enabled || false}
                              onChange={(e) => handleZ1OrderConfigChange({
                                takeProfit: {
                                  ...strategyData.z1_entry.takeProfit!,
                                  riskScaling: {
                                    ...strategyData.z1_entry.takeProfit?.riskScaling,
                                    enabled: e.target.checked,
                                  },
                                },
                              })}
                            />
                          }
                          label="Enable risk-adjusted scaling"
                        />

                        {strategyData.z1_entry.takeProfit?.riskScaling?.enabled && (
                          <Box sx={{ ml: 4, mt: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                            <Typography variant="caption" color="text.secondary">
                              Scale TP based on risk level (lower risk = more profit target, higher risk = less profit target)
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                              <FormControl size="small" sx={{ minWidth: 150 }}>
                                <InputLabel>Risk Indicator</InputLabel>
                                <Select
                                  value={strategyData.z1_entry.takeProfit?.riskScaling?.riskIndicatorId || ''}
                                  label="Risk Indicator"
                                  onChange={(e) => handleZ1OrderConfigChange({
                                    takeProfit: {
                                      ...strategyData.z1_entry.takeProfit!,
                                      riskScaling: {
                                        ...strategyData.z1_entry.takeProfit?.riskScaling!,
                                        riskIndicatorId: e.target.value,
                                      },
                                    },
                                  })}
                                >
                                  {availableIndicators
                                    .filter(ind => ind.type === 'risk')
                                    .map((indicator) => (
                                      <MenuItem key={indicator.id} value={indicator.id}>
                                        {indicator.name} ({indicator.baseType})
                                      </MenuItem>
                                    ))}
                                </Select>
                              </FormControl>
                            </Box>

                            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                              <TextField
                                label="Low Risk Threshold"
                                type="number"
                                size="small"
                                value={strategyData.z1_entry.takeProfit?.riskScaling?.lowRiskThreshold || 30}
                                onChange={(e) => handleZ1OrderConfigChange({
                                  takeProfit: {
                                    ...strategyData.z1_entry.takeProfit!,
                                    riskScaling: {
                                      ...strategyData.z1_entry.takeProfit?.riskScaling!,
                                      lowRiskThreshold: parseFloat(e.target.value) || 30,
                                    },
                                  },
                                })}
                                sx={{ width: 140 }}
                              />
                              <TextField
                                label="Low Risk Scale %"
                                type="number"
                                size="small"
                                value={strategyData.z1_entry.takeProfit?.riskScaling?.lowRiskScale || 120}
                                onChange={(e) => handleZ1OrderConfigChange({
                                  takeProfit: {
                                    ...strategyData.z1_entry.takeProfit!,
                                    riskScaling: {
                                      ...strategyData.z1_entry.takeProfit?.riskScaling!,
                                      lowRiskScale: parseFloat(e.target.value) || 120,
                                    },
                                  },
                                })}
                                sx={{ width: 140 }}
                              />
                            </Box>

                            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                              <TextField
                                label="High Risk Threshold"
                                type="number"
                                size="small"
                                value={strategyData.z1_entry.takeProfit?.riskScaling?.highRiskThreshold || 80}
                                onChange={(e) => handleZ1OrderConfigChange({
                                  takeProfit: {
                                    ...strategyData.z1_entry.takeProfit!,
                                    riskScaling: {
                                      ...strategyData.z1_entry.takeProfit?.riskScaling!,
                                      highRiskThreshold: parseFloat(e.target.value) || 80,
                                    },
                                  },
                                })}
                                sx={{ width: 140 }}
                              />
                              <TextField
                                label="High Risk Scale %"
                                type="number"
                                size="small"
                                value={strategyData.z1_entry.takeProfit?.riskScaling?.highRiskScale || 80}
                                onChange={(e) => handleZ1OrderConfigChange({
                                  takeProfit: {
                                    ...strategyData.z1_entry.takeProfit!,
                                    riskScaling: {
                                      ...strategyData.z1_entry.takeProfit?.riskScaling!,
                                      highRiskScale: parseFloat(e.target.value) || 80,
                                    },
                                  },
                                })}
                                sx={{ width: 140 }}
                              />
                            </Box>
                          </Box>
                        )}
                      </Box>
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
                    label={strategyData.z1_entry.positionSize.type === 'percentage' ? 'Base %' : 'Base $'}
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

                {/* Risk Scaling for Position Size - SPRINT_GOAL_04 Enhancement */}
                <Box sx={{ mt: 2, ml: 2 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={strategyData.z1_entry.positionSize.riskScaling?.enabled || false}
                        onChange={(e) => handleZ1OrderConfigChange({
                          positionSize: {
                            ...strategyData.z1_entry.positionSize,
                            riskScaling: {
                              ...strategyData.z1_entry.positionSize.riskScaling,
                              enabled: e.target.checked,
                            },
                          },
                        })}
                      />
                    }
                    label="Enable risk-adjusted position sizing"
                  />

                  {strategyData.z1_entry.positionSize.riskScaling?.enabled && (
                    <Box sx={{ ml: 4, mt: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Scale position size based on risk level (lower risk = larger position, higher risk = smaller position)
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <FormControl size="small" sx={{ minWidth: 150 }}>
                          <InputLabel>Risk Indicator</InputLabel>
                          <Select
                            value={strategyData.z1_entry.positionSize.riskScaling?.riskIndicatorId || ''}
                            label="Risk Indicator"
                            onChange={(e) => handleZ1OrderConfigChange({
                              positionSize: {
                                ...strategyData.z1_entry.positionSize,
                                riskScaling: {
                                  ...strategyData.z1_entry.positionSize.riskScaling!,
                                  riskIndicatorId: e.target.value,
                                },
                              },
                            })}
                          >
                            {availableIndicators
                              .filter(ind => ind.type === 'risk')
                              .map((indicator) => (
                                <MenuItem key={indicator.id} value={indicator.id}>
                                  {indicator.name} ({indicator.baseType})
                                </MenuItem>
                              ))}
                          </Select>
                        </FormControl>
                      </Box>

                      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <TextField
                          label="Low Risk Threshold"
                          type="number"
                          size="small"
                          value={strategyData.z1_entry.positionSize.riskScaling?.lowRiskThreshold || 30}
                          onChange={(e) => handleZ1OrderConfigChange({
                            positionSize: {
                              ...strategyData.z1_entry.positionSize,
                              riskScaling: {
                                ...strategyData.z1_entry.positionSize.riskScaling!,
                                lowRiskThreshold: parseFloat(e.target.value) || 30,
                              },
                            },
                          })}
                          sx={{ width: 140 }}
                        />
                        <TextField
                          label="Low Risk Scale %"
                          type="number"
                          size="small"
                          value={strategyData.z1_entry.positionSize.riskScaling?.lowRiskScale || 120}
                          onChange={(e) => handleZ1OrderConfigChange({
                            positionSize: {
                              ...strategyData.z1_entry.positionSize,
                              riskScaling: {
                                ...strategyData.z1_entry.positionSize.riskScaling!,
                                lowRiskScale: parseFloat(e.target.value) || 120,
                              },
                            },
                          })}
                          sx={{ width: 140 }}
                        />
                      </Box>

                      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <TextField
                          label="High Risk Threshold"
                          type="number"
                          size="small"
                          value={strategyData.z1_entry.positionSize.riskScaling?.highRiskThreshold || 80}
                          onChange={(e) => handleZ1OrderConfigChange({
                            positionSize: {
                              ...strategyData.z1_entry.positionSize,
                              riskScaling: {
                                ...strategyData.z1_entry.positionSize.riskScaling!,
                                highRiskScale: parseFloat(e.target.value) || 80,
                              },
                            },
                          })}
                          sx={{ width: 140 }}
                        />
                        <TextField
                          label="High Risk Scale %"
                          type="number"
                          size="small"
                          value={strategyData.z1_entry.positionSize.riskScaling?.highRiskScale || 80}
                          onChange={(e) => handleZ1OrderConfigChange({
                            positionSize: {
                              ...strategyData.z1_entry.positionSize,
                              riskScaling: {
                                ...strategyData.z1_entry.positionSize.riskScaling!,
                                highRiskScale: parseFloat(e.target.value) || 80,
                              },
                            },
                          })}
                          sx={{ width: 140 }}
                        />
                      </Box>
                    </Box>
                  )}
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
              sx={{ mt: 1, mb: 3 }}
            >
              Add Condition
            </Button>

            <Divider sx={{ my: 3 }} />

            {/* O1 Cooldown - SPRINT_GOAL_04 Enhancement */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Post-Cancellation Cooldown:
              </Typography>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={strategyData.o1_cancel.cooldownMinutes > 0}
                    onChange={(e) => handleO1Change({
                      cooldownMinutes: e.target.checked ? 5 : 0,
                    })}
                  />
                }
                label="Enable cooldown after signal cancellation"
              />
              {strategyData.o1_cancel.cooldownMinutes > 0 && (
                <TextField
                  label="Cooldown duration (minutes)"
                  type="number"
                  size="small"
                  value={strategyData.o1_cancel.cooldownMinutes}
                  onChange={(e) => handleO1Change({
                    cooldownMinutes: parseInt(e.target.value) || 0,
                  })}
                  sx={{ ml: 4, mt: 1, maxWidth: 250 }}
                />
              )}
            </Box>
          </AccordionDetails>
        </Accordion>

        {/* ZE1 - Order Closing Detection (Optional) */}
        <Accordion
          expanded={expandedSections.has('ze1')}
          onChange={() => handleSectionToggle('ze1')}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
              <Typography variant="h6" sx={{ flex: 1 }}>🎯 SECTION 4: ORDER CLOSING DETECTION (ZE1)</Typography>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={strategyData.ze1_enabled || false}
                    onChange={(e) => {
                      e.stopPropagation(); // Prevent accordion toggle
                      updateStrategyData({ ze1_enabled: e.target.checked });
                    }}
                    onClick={(e) => e.stopPropagation()} // Prevent accordion toggle
                  />
                }
                label="Enable"
                sx={{ mr: 2 }}
              />
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              This section defines when to close an open position (after order was filled).
              All conditions must be TRUE simultaneously to trigger position closure.
            </Typography>

            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Close Conditions (AND logic):
            </Typography>

            {strategyData.ze1_close.conditions.map((condition, index) => (
              <ConditionBlock
                key={condition.id}
                condition={condition}
                index={index}
                availableIndicators={getIndicatorsForSection('ze1')}
                onChange={(updated) => updateCondition('ze1', updated)}
                onRemove={() => removeCondition('ze1', condition.id)}
                logicType="AND"
              />
            ))}

            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => addCondition('ze1')}
              sx={{ mt: 1, mb: 3 }}
            >
              Add Condition
            </Button>

            <Divider sx={{ my: 3 }} />

            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Close Order Configuration:
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <FormControl size="small" sx={{ maxWidth: 300 }}>
                <InputLabel>Price Calculation Method</InputLabel>
                <Select
                  value={strategyData.ze1_close.priceIndicatorId ? 'indicator' : 'market'}
                  label="Price Calculation Method"
                  onChange={(e) => handleZE1OrderConfigChange({
                    priceIndicatorId: e.target.value === 'market' ? undefined : strategyData.ze1_close.priceIndicatorId
                  })}
                >
                  <MenuItem value="market">Use market price</MenuItem>
                  <MenuItem value="indicator">Use indicator variant</MenuItem>
                </Select>
              </FormControl>

              {strategyData.ze1_close.priceIndicatorId && (
                <FormControl size="small" sx={{ maxWidth: 300 }}>
                  <InputLabel>Close Order Indicator</InputLabel>
                  <Select
                    value={strategyData.ze1_close.priceIndicatorId || ''}
                    label="Close Order Indicator"
                    onChange={(e) => handleZE1OrderConfigChange({ priceIndicatorId: e.target.value })}
                  >
                    {availableIndicators
                      .filter(ind => ind.type === 'close_order')
                      .map((indicator) => (
                        <MenuItem key={indicator.id} value={indicator.id}>
                          {indicator.name} ({indicator.baseType})
                        </MenuItem>
                      ))}
                  </Select>
                </FormControl>
              )}

              {/* ZE1 Risk-Adjusted Close Pricing - SPRINT_GOAL_04 Enhancement */}
              {strategyData.ze1_close.priceIndicatorId && (
                <Box sx={{ mt: 2 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={strategyData.ze1_close.riskAdjustedPricing?.enabled || false}
                        onChange={(e) => handleZE1OrderConfigChange({
                          riskAdjustedPricing: {
                            ...strategyData.ze1_close.riskAdjustedPricing,
                            enabled: e.target.checked,
                          },
                        })}
                      />
                    }
                    label="Enable risk-adjusted close pricing"
                  />

                  {strategyData.ze1_close.riskAdjustedPricing?.enabled && (
                    <Box sx={{ ml: 4, mt: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Adjust close price based on risk level (lower risk = better price, higher risk = worse price)
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <FormControl size="small" sx={{ minWidth: 150 }}>
                          <InputLabel>Risk Indicator</InputLabel>
                          <Select
                            value={strategyData.ze1_close.riskAdjustedPricing?.riskIndicatorId || ''}
                            label="Risk Indicator"
                            onChange={(e) => handleZE1OrderConfigChange({
                              riskAdjustedPricing: {
                                ...strategyData.ze1_close.riskAdjustedPricing!,
                                riskIndicatorId: e.target.value,
                              },
                            })}
                          >
                            {availableIndicators
                              .filter(ind => ind.type === 'risk')
                              .map((indicator) => (
                                <MenuItem key={indicator.id} value={indicator.id}>
                                  {indicator.name} ({indicator.baseType})
                                </MenuItem>
                              ))}
                          </Select>
                        </FormControl>
                      </Box>

                      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <TextField
                          label="Low Risk Threshold"
                          type="number"
                          size="small"
                          value={strategyData.ze1_close.riskAdjustedPricing?.lowRiskThreshold || 20}
                          onChange={(e) => handleZE1OrderConfigChange({
                            riskAdjustedPricing: {
                              ...strategyData.ze1_close.riskAdjustedPricing!,
                              lowRiskThreshold: parseFloat(e.target.value) || 20,
                            },
                          })}
                          sx={{ width: 140 }}
                        />
                        <TextField
                          label="Low Risk Adjustment %"
                          type="number"
                          size="small"
                          value={strategyData.ze1_close.riskAdjustedPricing?.lowRiskAdjustment || 5}
                          onChange={(e) => handleZE1OrderConfigChange({
                            riskAdjustedPricing: {
                              ...strategyData.ze1_close.riskAdjustedPricing!,
                              lowRiskAdjustment: parseFloat(e.target.value) || 5,
                            },
                          })}
                          sx={{ width: 160 }}
                        />
                      </Box>

                      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <TextField
                          label="High Risk Threshold"
                          type="number"
                          size="small"
                          value={strategyData.ze1_close.riskAdjustedPricing?.highRiskThreshold || 80}
                          onChange={(e) => handleZE1OrderConfigChange({
                            riskAdjustedPricing: {
                              ...strategyData.ze1_close.riskAdjustedPricing!,
                              highRiskThreshold: parseFloat(e.target.value) || 80,
                            },
                          })}
                          sx={{ width: 140 }}
                        />
                        <TextField
                          label="High Risk Adjustment %"
                          type="number"
                          size="small"
                          value={strategyData.ze1_close.riskAdjustedPricing?.highRiskAdjustment || -5}
                          onChange={(e) => handleZE1OrderConfigChange({
                            riskAdjustedPricing: {
                              ...strategyData.ze1_close.riskAdjustedPricing!,
                              highRiskAdjustment: parseFloat(e.target.value) || -5,
                            },
                          })}
                          sx={{ width: 160 }}
                        />
                      </Box>
                    </Box>
                  )}
                </Box>
              )}
            </Box>
          </AccordionDetails>
        </Accordion>

        {/* Emergency Exit */}
        <Accordion
          expanded={expandedSections.has('emergency')}
          onChange={() => handleSectionToggle('emergency')}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">🚨 SECTION 5: EMERGENCY EXIT</Typography>
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