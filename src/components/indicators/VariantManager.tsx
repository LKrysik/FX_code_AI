import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Card,
  CardContent,
  Chip,
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { IndicatorVariant } from '@/types/strategy';
import { apiService } from '@/services/api';

interface VariantManagerProps {
  onVariantCreated?: (variant: IndicatorVariant) => void;
  onVariantUpdated?: (variant: IndicatorVariant) => void;
  onVariantDeleted?: (variantId: string) => void;
}

interface SystemIndicator {
  id: string;  // Updated to match API response format
  name: string;
  description: string;
  category: 'general' | 'risk' | 'stop_loss_price' | 'take_profit_price' | 'order_price' | 'close_price';  // Updated categories
  is_implemented: boolean;
  parameters: Array<{
    name: string;
    type: 'int' | 'float' | 'string' | 'boolean' | 'json';  // Updated to match API response
    default: any;  // Updated to match API response
    min_value?: number;
    max_value?: number;
    allowed_values?: any[];  // Added for enum parameters
    required: boolean;  // Updated to match API response
    description: string;
  }>;
}

export const VariantManager: React.FC<VariantManagerProps> = ({
  onVariantCreated,
  onVariantUpdated,
  onVariantDeleted,
}) => {
  // Add debugging for page refresh issue
  console.log("[VariantManager] component mounted/re-rendered at:", new Date().toISOString());
  
  const [activeTab, setActiveTab] = useState<'variants' | 'create'>('variants');
  const [variants, setVariants] = useState<IndicatorVariant[]>([]);
  const [systemIndicators, setSystemIndicators] = useState<SystemIndicator[]>([]);
  const [selectedType, setSelectedType] = useState<'all' | 'general' | 'risk' | 'stop_loss_price' | 'take_profit_price' | 'order_price' | 'close_price'>('all');
  const [loading, setLoading] = useState(false);
  const [loadingSystemIndicators, setLoadingSystemIndicators] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingVariant, setEditingVariant] = useState<IndicatorVariant | null>(null);
  const [selectedSystemIndicator, setSelectedSystemIndicator] = useState<SystemIndicator | null>(null);

  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'info'
  });

  // Form state for variant creation/editing
  const [variantForm, setVariantForm] = useState({
    name: '',
    description: '',
    parameters: {} as Record<string, any>,
  });

  const [parameterErrors, setParameterErrors] = useState<Record<string, string>>({});
  const systemIndicatorsRequestRef = useRef<Promise<SystemIndicator[]> | null>(null);
  const hasPrefetchedSystemIndicatorsRef = useRef(false);

  const loadVariants = async () => {

    try {

      const data = await apiService.getVariants();

      // Transform backend data to frontend format
      const transformedVariants: IndicatorVariant[] = data.map((variant: any) => ({
        id: variant.variant_id ?? variant.id,
        name: variant.name,
        baseType: variant.base_indicator_type || variant.baseType,
        type: variant.variant_type || variant.type,
        description: variant.description,
        parameters: variant.parameters || {},
        isActive: true, // API variants are considered active
        lastValue: undefined, // TODO: Get from real-time updates
        lastUpdate: undefined, // TODO: Get from real-time updates
      }));

      setVariants(transformedVariants);

      if (data.length > 0) {
        setSnackbar({
          open: true,
          message: `Loaded ${data.length} variants from API`,
          severity: 'success'
        });
      }
    } catch (error) {
      console.error('Failed to load variants:', error);
      setVariants([]);
      setSnackbar({
        open: true,
        message: 'Failed to load variants',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const loadSystemIndicators = useCallback(
    async (options: { force?: boolean; silent?: boolean } = {}): Promise<SystemIndicator[]> => {
      if (!options.force) {
        if (systemIndicatorsRequestRef.current) {
          return systemIndicatorsRequestRef.current;
        }

        if (systemIndicators.length > 0) {
          return systemIndicators;
        }
      }

      const fetchPromise = (async () => {
        setLoadingSystemIndicators(true);
        try {

          const indicators = await apiService.getSystemIndicators();
          
          // DEBUG: Log raw API response
          console.log("[VariantManager] Raw system indicators from API:", indicators.slice(0, 2));

          // Transform backend data to frontend format
          const transformedIndicators: SystemIndicator[] = indicators.map((indicator: any) => {
            const transformed = {
              id: indicator.id || indicator.indicator_type || indicator.type,
              name: indicator.name,
              description: indicator.description,
              category: indicator.category,
              is_implemented: indicator.is_implemented !== false, // Default to true if missing
              parameters: indicator.parameters.map((param: any) => ({
                name: param.name,
                type: param.type || param.parameter_type,
                default: param.default_value || param.default,
                min_value: param.min_value,
                max_value: param.max_value,
                allowed_values: param.allowed_values,
                required: param.required || param.is_required !== false, // Default to true if missing
                description: param.description,
              })),
            };
            
            // DEBUG: Log transformation
            if (indicator.name?.includes('Time Weighted')) {
              console.log("[VariantManager] TWPA transformation:", {
                original: indicator,
                transformed: transformed
              });
            }
            
            return transformed;
          });

          setSystemIndicators(transformedIndicators);

          if (!options.silent && transformedIndicators.length > 0) {
            setSnackbar({
              open: true,
              message: `Loaded ${transformedIndicators.length} system indicators from backend`,
              severity: 'success'
            });
          }

          return transformedIndicators;
        } catch (error) {
          console.error('Failed to load system indicators:', error);
          setSnackbar({
            open: true,
            message: 'Failed to load system indicators from backend',
            severity: 'error'
          });
          return [];
        } finally {
          setLoadingSystemIndicators(false);
          systemIndicatorsRequestRef.current = null;
        }
      })();

      systemIndicatorsRequestRef.current = fetchPromise;
      return fetchPromise;
    },
    [systemIndicators]
  );
  useEffect(() => {
    if (!hasPrefetchedSystemIndicatorsRef.current) {
      hasPrefetchedSystemIndicatorsRef.current = true;
      loadSystemIndicators({ silent: true });
    }
  }, [loadSystemIndicators]);

  useEffect(() => {
    if (activeTab === 'variants') {
      loadVariants();
    }
  }, [activeTab, selectedType]);

  useEffect(() => {
    if (activeTab === 'create') {
      loadSystemIndicators();
    }
  }, [activeTab, loadSystemIndicators]);

  const handleCreateVariant = (systemIndicator: SystemIndicator, event?: React.MouseEvent) => {
    // Prevent default form submission and event bubbling
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    
    console.log("[VariantManager] Creating variant for:", systemIndicator.name);
    
    setSelectedSystemIndicator(systemIndicator);
    setEditingVariant(null);
    setVariantForm({
      name: `${systemIndicator.name} Custom`,
      description: `Custom variant of ${systemIndicator.name}`,
      parameters: systemIndicator.parameters.reduce((acc, param) => {
        // Dla parametrow typu JSON, konwertuj obiekt na string
        if (param.type === 'json' && typeof param.default === 'object') {
          acc[param.name] = JSON.stringify(param.default, null, 2);
        } else {
          acc[param.name] = param.default;
        }
        return acc;
      }, {} as Record<string, any>),
    });
    setParameterErrors({});
    setDialogOpen(true);
  };

  const handleEditVariant = async (variant: IndicatorVariant) => {
    let availableIndicators = systemIndicators;

    if (!availableIndicators.length) {
      const fetchedIndicators = await loadSystemIndicators({ silent: true });
      if (fetchedIndicators.length) {
        availableIndicators = fetchedIndicators;
      }
    }

    const systemIndicator = availableIndicators.find(si =>
      si.id === variant.baseType ||
      si.id === variant.base_indicator_type
    );

    if (!systemIndicator) {
      setSnackbar({
        open: true,
        message: 'Unable to load base indicator parameters for this variant',
        severity: 'error'
      });
      return;
    }

    setSelectedSystemIndicator(systemIndicator);
    setEditingVariant(variant);

    const processedParameters = { ...variant.parameters };
    systemIndicator.parameters.forEach(param => {
      if (param.type === 'json' && typeof processedParameters[param.name] === 'object') {
        processedParameters[param.name] = JSON.stringify(processedParameters[param.name], null, 2);
      }
    });

    setVariantForm({
      name: variant.name,
      description: variant.description,
      parameters: processedParameters,
    });
    setParameterErrors({});
    setDialogOpen(true);
  };

  const handleDeleteVariant = async (variantId: string) => {
    // Store original variants for rollback
    const originalVariants = [...variants];

    // Optimistically remove from UI
    setVariants(prev => prev.filter(v => v.id !== variantId));

    try {

      await apiService.deleteVariant(variantId);

      setSnackbar({
        open: true,
        message: 'Variant deleted successfully',
        severity: 'success'
      });
      onVariantDeleted?.(variantId);
    } catch (error: any) {
      console.error('Failed to delete variant:', error);

      // Rollback the optimistic update
      setVariants(originalVariants);

      // Check if it's a 404 (variant already deleted)
      const isNotFound = error?.response?.status === 404;
      const message = isNotFound
        ? 'Variant was already removed from server'
        : 'Failed to delete variant from server';

      setSnackbar({
        open: true,
        message: message,
        severity: isNotFound ? 'warning' : 'error'
      });
    }
  };

  const waitForIndicatorReady = async (
    sessionId: string,
    symbol: string,
    indicatorId: string,
    attempts = 6
  ): Promise<string | undefined> => {
    for (let attempt = 1; attempt <= attempts; attempt++) {
      await new Promise(resolve => setTimeout(resolve, attempt * 800));
      try {

        const status = await apiService.getSessionIndicatorValues(sessionId, symbol);
        if (status.indicators && status.indicators[indicatorId]) {
          return status.files?.[indicatorId]?.path;
        }
      } catch (error) {
        console.warn('Failed to poll indicator status:', error);
        throw error;
      }
    }
    throw new Error('Indicator recalculation timed out');
  };

  const handleRecalculateVariant = async (variantId: string) => {
    try {
      setLoading(true);

      const sessionId = localStorage.getItem('currentSessionId') || 'session_exec_20251005_214517_09798f11';
      const symbol = localStorage.getItem('currentSymbol') || 'AEVO_USDT';

      const response = await apiService.addIndicatorToSession(sessionId, symbol, {
        variant_id: variantId,
        parameters: {},
        force_recalculate: true
      });
      const indicatorId = response?.indicator_id;
      if (!indicatorId) {
        throw new Error('Missing indicator identifier from server');
      }

      let filePath = response?.file?.path;
      if (response?.status !== 'added') {
        filePath = await waitForIndicatorReady(sessionId, symbol, indicatorId).catch(() => filePath);
      }

      setSnackbar({
        open: true,
        message: filePath ? `Indicator recalculated. CSV: ${filePath}` : 'Indicator recalculated successfully',
        severity: 'success'
      });
    } catch (error: any) {
      console.error('Failed to recalculate variant:', error);
      setSnackbar({
        open: true,
        message: 'Failed to recalculate indicator',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const validateParameters = (): boolean => {
    if (!selectedSystemIndicator) return false;

    const errors: Record<string, string> = {};
    let isValid = true;

    selectedSystemIndicator.parameters.forEach(param => {
      const value = variantForm.parameters[param.name];

      // Required check
      if (param.required && (value === undefined || value === null || value === '')) {
        errors[param.name] = 'This parameter is required';
        isValid = false;
        return;
      }

      // Type validation
      if (param.type === 'int' && !Number.isInteger(Number(value))) {
        errors[param.name] = 'Must be a whole number';
        isValid = false;
      } else if (param.type === 'float' && isNaN(Number(value))) {
        errors[param.name] = 'Must be a number';
        isValid = false;
      }

      // Range validation
      if ((param.type === 'int' || param.type === 'float') && param.min_value !== undefined && Number(value) < param.min_value) {
        errors[param.name] = `Must be at least ${param.min_value}`;
        isValid = false;
      }
      if ((param.type === 'int' || param.type === 'float') && param.max_value !== undefined && Number(value) > param.max_value) {
        errors[param.name] = `Must be at most ${param.max_value}`;
        isValid = false;
      }
    });

    setParameterErrors(errors);
    return isValid;
  };

  const handleSaveVariant = async () => {
    if (!validateParameters() || !selectedSystemIndicator) return;

    try {

      // Convert JSON string parameters back to objects for API
      const processedParameters = { ...variantForm.parameters };
      selectedSystemIndicator.parameters.forEach(param => {
        if (param.type === 'json' && typeof processedParameters[param.name] === 'string') {
          try {

            processedParameters[param.name] = JSON.parse(processedParameters[param.name]);
          } catch (error) {
            console.error(`Failed to parse JSON parameter ${param.name}:`, error);
          }
        }
      });

      const variantData = {
        system_indicator: selectedSystemIndicator.id,  // Updated field name
        category: selectedSystemIndicator.category,    // Updated field name  
        name: variantForm.name,
        description: variantForm.description,
        parameters: processedParameters,
      };

      if (editingVariant) {
        // DEBUG: Log update attempt
        console.log("[VariantManager] Attempting to update variant:", {
          variantId: editingVariant.id,
          formData: variantForm,
          selectedIndicator: selectedSystemIndicator?.id
        });
        
        const updatePayload = { 
          name: variantForm.name,
          description: variantForm.description,
          parameters: processedParameters 
        };
        
        console.log("[VariantManager] Update payload:", updatePayload);
        
        const result = await apiService.updateVariant(editingVariant.id, updatePayload);
        console.log("[VariantManager] Update result:", result);

        const updatedVariant: IndicatorVariant = {
          ...editingVariant,
          name: variantForm.name,
          description: variantForm.description,
          parameters: variantForm.parameters,
          lastUpdate: new Date().toISOString(),
        };

        setVariants(prev => prev.map(v => v.id === editingVariant.id ? updatedVariant : v));
        setSnackbar({
          open: true,
          message: 'Variant updated successfully',
          severity: 'success'
        });
        onVariantUpdated?.(updatedVariant);
      } else {
        const response = await apiService.createVariant(variantData);

        const newVariant: IndicatorVariant = {
          id: response.data?.variant_id || `variant-${Date.now()}`,
          name: variantForm.name,
          baseType: selectedSystemIndicator.id,
          type: selectedSystemIndicator.category,
          description: variantForm.description,
          parameters: variantForm.parameters,
          isActive: true,
          lastValue: undefined,
          lastUpdate: new Date().toISOString(),
        };

        setVariants(prev => [...prev, newVariant]);
        setSnackbar({
          open: true,
          message: 'Variant created successfully',
          severity: 'success'
        });
        onVariantCreated?.(newVariant);

        // Redirect to variants tab after creation per user_feedback.md
        setActiveTab('variants');
      }

      setDialogOpen(false);
      setSelectedSystemIndicator(null);
      setEditingVariant(null);
    } catch (error: any) {
      console.error('Failed to save variant:', error);
      const errorMessage = error?.response?.data?.error_message ||
                          error?.response?.data?.message ||
                          'Unknown error occurred';
      setSnackbar({
        open: true,
        message: `Failed to ${editingVariant ? 'update' : 'create'} variant: ${errorMessage}`,
        severity: 'error'
      });
    }
  };

  const handleParameterChange = (paramName: string, value: any) => {
    setVariantForm(prev => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        [paramName]: value,
      },
    }));

    // Clear error for this parameter
    if (parameterErrors[paramName]) {
      setParameterErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[paramName];
        return newErrors;
      });
    }

    // Validate JSON parameters
    if (selectedSystemIndicator) {
      const param = selectedSystemIndicator.parameters.find(p => p.name === paramName);
      if (param?.parameter_type === 'json' && value) {
        try {

          JSON.parse(value);
        } catch (error) {
          setParameterErrors(prev => ({
            ...prev,
            [paramName]: 'Invalid JSON format'
          }));
        }
      }
    }
  };

  const filteredSystemIndicators = selectedType === 'all'
    ? systemIndicators
    : systemIndicators.filter(si => si.category === selectedType);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Indicator Variants
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Create and manage custom indicator variants
        </Typography>
      </Box>

      {/* Main Tabs: Indicator Variants vs Create Variant */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_, value) => setActiveTab(value)}
        >
          <Tab value="variants" label="Indicator Variants" />
          <Tab value="create" label="Create Variant" />
        </Tabs>
      </Paper>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Indicator Variants Tab - List only from config/indicators/ */}
      {activeTab === 'variants' && (
        <Paper>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="h6">Indicator Variants</Typography>
            <Typography variant="body2" color="text.secondary">
              Variants loaded from config/indicators/ with validation status
            </Typography>
          </Box>
          <Box sx={{ p: 2 }}>
            {variants.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="body2" color="text.secondary">
                  No variants found in config/indicators/. Create variants using the "Create Variant" tab.
                </Typography>
              </Box>
            ) : (
              <Grid container spacing={2}>
                {variants.map((variant) => (
                  <Grid item xs={12} md={6} lg={4} key={variant.id}>
                    <Card>
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                          <Typography variant="h6" component="h3">
                            {variant.name}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                            <Chip
                              label={variant.type}
                              size="small"
                              color="secondary"
                              variant="outlined"
                            />
                            {variant.isActive ? (
                              <CheckCircleIcon color="success" fontSize="small" titleAccess="Valid variant" />
                            ) : (
                              <ErrorIcon color="error" fontSize="small" titleAccess="Invalid variant" />
                            )}
                          </Box>
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Based on: {variant.baseType}
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 2 }}>
                          {variant.description}
                        </Typography>
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" color="text.secondary">
                            Parameters: {Object.entries(variant.parameters).map(([k, v]) => 
                              `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`
                            ).join(', ')}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Button
                            size="small"
                            startIcon={<RefreshIcon />}
                            color="primary"
                            onClick={() => handleRecalculateVariant(variant.id)}
                          >
                            Recalculate
                          </Button>
                          <Button
                            size="small"
                            startIcon={<EditIcon />}
                            onClick={() => handleEditVariant(variant)}
                          >
                            Edit
                          </Button>
                          <Button
                            size="small"
                            startIcon={<DeleteIcon />}
                            color="error"
                            onClick={() => handleDeleteVariant(variant.id)}
                          >
                            Delete
                          </Button>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </Box>
        </Paper>
      )}

      {/* Create Variant Tab - System indicators by type */}
      {activeTab === 'create' && (
        <>
          {/* Type Filter Tabs */}
          <Paper sx={{ mb: 3 }}>
            <Tabs
              value={selectedType}
              onChange={(_, value) => setSelectedType(value)}
              variant="scrollable"
              scrollButtons="auto"
            >
              <Tab value="all" label="All Types" />
              <Tab value="general" label="General" />
              <Tab value="risk" label="Risk" />
              <Tab value="stop_loss_price" label="Stop Loss Price" />
              <Tab value="take_profit_price" label="Take Profit Price" />
              <Tab value="order_price" label="Order Price" />
              <Tab value="close_price" label="Close Price" />
            </Tabs>
          </Paper>

          {/* System Indicators Section */}
          <Paper>
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
              <Typography variant="h6">System Indicators</Typography>
              <Typography variant="body2" color="text.secondary">
                Create custom variants from these base indicators
              </Typography>
            </Box>
            <Box sx={{ p: 2 }}>
              {loadingSystemIndicators ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                  <LinearProgress sx={{ width: '50%' }} />
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
                    Loading system indicators...
                  </Typography>
                </Box>
              ) : filteredSystemIndicators.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography variant="body2" color="text.secondary">
                    No system indicators available. Check backend connection.
                  </Typography>
                </Box>
              ) : (
                <Grid container spacing={2}>
                  {filteredSystemIndicators.map((indicator) => (
                    <Grid item xs={12} md={6} lg={4} key={indicator.id}>
                      <Card>
                        <CardContent>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                            <Typography variant="h6" component="h3">
                              {indicator.name}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              <Chip
                                label={indicator.category}
                                size="small"
                                color="primary"
                                variant="outlined"
                              />
                              {!indicator.is_implemented && (
                                <Chip
                                  label="Not Implemented"
                                  size="small"
                                  color="warning"
                                  variant="outlined"
                                />
                              )}
                            </Box>
                          </Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {indicator.description}
                          </Typography>
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="caption" color="text.secondary">
                              Parameters: {indicator.parameters.map(p => p.name).join(', ')}
                            </Typography>
                          </Box>
                          <Button
                            size="small"
                            startIcon={<AddIcon />}
                            onClick={(e) => handleCreateVariant(indicator, e)}
                            fullWidth
                            type="button"
                            // Temporarily remove disabled until API provides is_implemented correctly
                            // disabled={!indicator.is_implemented}
                          >
                            Create Variant
                          </Button>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              )}
            </Box>
          </Paper>
        </>
      )}

      {/* Create/Edit Variant Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingVariant ? 'Edit Variant' : 'Create Variant'}
          {selectedSystemIndicator && (
            <Typography variant="subtitle2" component="p" color="text.secondary">
              Based on: {selectedSystemIndicator.name}
            </Typography>
          )}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <TextField
              fullWidth
              label="Variant Name"
              value={variantForm.name}
              onChange={(e) => setVariantForm(prev => ({ ...prev, name: e.target.value }))}
              helperText="Give your variant a descriptive name"
            />

            <TextField
              fullWidth
              label="Description"
              multiline
              rows={2}
              value={variantForm.description}
              onChange={(e) => setVariantForm(prev => ({ ...prev, description: e.target.value }))}
              helperText="Describe what makes this variant special"
            />

            {selectedSystemIndicator && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Parameters
                </Typography>
                <Grid container spacing={2}>
                  {selectedSystemIndicator.parameters.map((param) => (
                    <Grid item xs={12} md={param.parameter_type === 'json' ? 12 : 6} key={param.name}>
                      <TextField
                        fullWidth
                        label={`${param.name}${param.is_required ? ' *' : ''}`}
                        type={param.parameter_type === 'int' || param.parameter_type === 'float' ? 'number' : 'text'}
                        multiline={param.parameter_type === 'json'}
                        rows={param.parameter_type === 'json' ? 4 : 1}
                        value={variantForm.parameters[param.name] || ''}
                        onChange={(e) => handleParameterChange(param.name, e.target.value)}
                        error={!!parameterErrors[param.name]}
                        helperText={parameterErrors[param.name] || param.description || (param.parameter_type === 'json' ? 'JSON format required' : '')}
                        inputProps={{
                          min: param.min_value,
                          max: param.max_value,
                          step: param.parameter_type === 'float' ? '0.01' : '1',
                        }}
                      />
                    </Grid>
                  ))}
                </Grid>
              </Box>
            )}

            <Alert severity="info">
              <Typography variant="body2">
                <strong>Variant Parameters:</strong> These settings customize how the indicator behaves.
                Changes here will affect how the indicator calculates values in your strategies.
              </Typography>
            </Alert>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleSaveVariant}
            variant="contained"
            color="success"
            disabled={!variantForm.name.trim() || Object.keys(parameterErrors).length > 0}
          >
            {editingVariant ? 'Update Variant' : 'Create Variant'}
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
};
