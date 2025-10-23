'use client';

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
  CircularProgress,
  LinearProgress,
  AppBar,
  Toolbar,
  Breadcrumbs,
  Link,
  ButtonGroup,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  Slider,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  CenterFocusStrong as ResetZoomIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ShowChart as ChartIcon,
  Timeline as TimelineIcon,
  TrendingUp as TrendingUpIcon,
  BarChart as BarChartIcon,
  Palette as PaletteIcon,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  ComposedChart,
  Brush,
  ReferenceLine,
  Area,
  AreaChart,
} from 'recharts';

interface ChartDataPoint {
  timestamp: number;
  price: number;
  volume: number;
  symbol: string;
  bid_prices?: number[];
  ask_prices?: number[];
  bid_quantities?: number[];
  ask_quantities?: number[];
  // Dynamic indicators
  [key: string]: any;
}

interface ChartData {
  session_id: string;
  symbol: string;
  data_points: number;
  data: ChartDataPoint[];
}

interface IndicatorConfig {
  id: string;
  name: string;
  enabled: boolean;
  scale: 'main' | 'secondary';
  color: string;
  field: string;
  indicatorType?: string;
  timeframe?: string;
  period?: number;
  variantId?: string;
  variantType?: string;
  parameters?: Record<string, any>;
}

type IndicatorStatus = 'idle' | 'loading' | 'ready' | 'error';

interface IndicatorStatusState {
  status: IndicatorStatus;
  message?: string;
  filePath?: string;
}

const defaultColors = [
  '#f44336', '#4caf50', '#ff9800', '#2196f3', '#9c27b0',
  '#e91e63', '#00bcd4', '#8bc34a', '#ff5722', '#607d8b',
  '#795548', '#ffc107', '#03a9f4', '#cddc39', '#9e9e9e'
];

const timeIntervals = [
  { label: 'Raw Data', value: 'raw' },
  { label: '10 seconds', value: '10s' },
  { label: '30 seconds', value: '30s' },
  { label: '1 minute', value: '1m' },
  { label: '5 minutes', value: '5m' },
  { label: '15 minutes', value: '15m' },
  { label: '1 hour', value: '1h' },
];

const normalizeTimestampKey = (value: number | string): string => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  // Keep timestamps in consistent format - seconds with decimal precision
  // This matches the format used by both price data and technical indicators
  if (numeric > 1e11) {
    // Already in milliseconds, convert to seconds
    return (numeric / 1000).toFixed(6);
  }
  // Already in seconds format (matches indicators)
  return numeric.toFixed(6);
};

// Helper function to check if indicator exists for given variant
const findExistingIndicatorForVariant = (existingIndicators: Record<string, any>, variantId: string): string | null => {
  for (const [indicatorId, indicator] of Object.entries(existingIndicators)) {
    if (indicator?.variant_id === variantId) {
      return indicatorId;
    }
  }
  return null;
};

export default function ChartPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [loading, setLoading] = useState(true);
  const [isUpdatingIndicators, setIsUpdatingIndicators] = useState(false);
  const [isCreatingIndicator, setIsCreatingIndicator] = useState(false); // Flag to prevent multiple processChartData calls
  const [error, setError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [processedData, setProcessedData] = useState<any[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [indicators, setIndicators] = useState<IndicatorConfig[]>([]);
  const [availableFields, setAvailableFields] = useState<string[]>([]);
  const [maxPoints, setMaxPoints] = useState(1000);
  const [timeInterval, setTimeInterval] = useState('raw');
  const [zoomDomain, setZoomDomain] = useState<[number, number] | null>(null);
  const [brushDomain, setBrushDomain] = useState<[number, number] | null>(null);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info'}>({
    open: false,
    message: '',
    severity: 'info'
  });
  const [indicatorStatuses, setIndicatorStatuses] = useState<Record<string, IndicatorStatusState>>({});

  useEffect(() => {
    loadSessionData();
  }, [sessionId]);

  useEffect(() => {
    if (selectedSymbol) {
      loadChartData();
    }
  }, [selectedSymbol, maxPoints]);

  useEffect(() => {
    const processData = async () => {
      if (chartData && !isCreatingIndicator) {
        console.log(`[DEBUG] Processing chart data with ${indicators.length} indicators, ${indicators.filter(i => i.enabled).length} enabled`);
        await processChartData();
      } else if (isCreatingIndicator) {
        console.log(`[DEBUG] Skipping processChartData during indicator creation`);
      }
    };
    processData();
  }, [chartData, timeInterval, indicators, isCreatingIndicator]); // Added isCreatingIndicator to dependency

  const loadSessionData = async () => {
    try {
      setLoading(true);
      const sessionsResponse = await apiService.getDataCollectionSessions();
      const session = sessionsResponse.sessions.find((s: any) => s.session_id === sessionId);
      
      if (session && session.symbols.length > 0) {
        setAvailableSymbols(session.symbols);
        setSelectedSymbol(session.symbols[0]);
      } else {
        setError('No symbols found in this session');
      }
    } catch (error: any) {
      console.error('Failed to load session data:', error);
      setError(`Failed to load session data: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const updateIndicatorStatus = (indicatorId: string, status: IndicatorStatus, message?: string, filePath?: string) => {
    setIndicatorStatuses(prev => ({
      ...prev,
      [indicatorId]: { status, message, filePath }
    }));
  };

  const loadChartData = async (isIndicatorUpdate: boolean = false) => {
    if (!selectedSymbol) return;

    try {
      // Only set main loading state for initial load, not indicator updates
      if (!isIndicatorUpdate) {
        setLoading(true);
      } else {
        setIsUpdatingIndicators(true);
      }
      setError(null);
      
      // Load chart data
      const data = await apiService.getChartData(sessionId, selectedSymbol, maxPoints);
      setChartData(data);
      
      // Load available indicators for this symbol only on initial load, not updates
      if (!isIndicatorUpdate) {
        await loadAvailableIndicators();
      }
      
      setSnackbar({
        open: true,
        message: `Loaded ${data.data_points} data points for ${selectedSymbol}`,
        severity: 'success'
      });
    } catch (error: any) {
      console.error('Failed to load chart data:', error);
      setError(`Failed to load chart data: ${error.message}`);
      setSnackbar({
        open: true,
        message: `Failed to load chart data: ${error.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
      setIsUpdatingIndicators(false);
    }
  };

  const loadAvailableIndicators = async () => {
    try {
      // Load available variants from the new unified API
      const variantsResponse = await apiService.get('/api/indicators/variants');
      const variants = variantsResponse.data?.variants || [];
      console.log('Available indicator variants:', variants);
      
      // Load existing indicators from backend to check what's already created
      const existingIndicatorsResponse = await apiService.getSessionIndicatorValues(sessionId, selectedSymbol);
      const existingIndicators = existingIndicatorsResponse.indicators || {};
      console.log('Existing indicators in backend:', existingIndicators);
      
      // Load user preferences for this session/symbol
      const preferencesResponse = await apiService.get(`/api/indicators/sessions/${sessionId}/symbols/${selectedSymbol}/preferences`);
      const preferences = preferencesResponse.data?.preferences || {};
      console.log('User preferences:', preferences);
      
      // Create indicator configs from variants
      const indicatorConfigs: IndicatorConfig[] = variants.map((variant: any, index: number) => {
        const variantId = variant.id || variant.variant_id;
        const baseIndicatorType = variant.base_indicator_type || variant.system_indicator;
        const variantType = variant.variant_type || variant.category || 'general';
        
        // Check if indicator already exists in backend for this variant
        const existingIndicatorId = findExistingIndicatorForVariant(existingIndicators, variantId);
        
        // Use existing ID if found, otherwise use a temporary ID that will be replaced when created
        const indicatorId = existingIndicatorId || `temp_${variantId}`;
        
        // Check if this indicator is enabled in preferences
        const isEnabled = preferences.enabled_indicators?.includes(indicatorId) || !!existingIndicatorId;
        const displayScale = preferences.indicator_scales?.[indicatorId] || determineIndicatorScale(variantType);
        const color = preferences.indicator_colors?.[indicatorId] || defaultColors[index % defaultColors.length];
        
        return {
          id: indicatorId,
          name: `${variant.name}`,
          enabled: isEnabled,
          scale: displayScale,
          color: color,
          field: indicatorId,
          indicatorType: baseIndicatorType,
          timeframe: '1m', // default timeframe
          period: variant.parameters?.period || 14,
          variantId,
          variantType,
          parameters: variant.parameters,
          category: variantType,
          description: variant.description || `${baseIndicatorType} indicator`
        };
      });
      
      setIndicators(indicatorConfigs);
      setIndicatorStatuses(() => {
        const next: Record<string, IndicatorStatusState> = {};
        indicatorConfigs.forEach((indicator) => {
          // Set status based on whether indicator already exists in backend
          const hasBackendData = !indicator.id.startsWith('temp_');
          next[indicator.id] = { 
            status: hasBackendData ? 'ready' : (indicator.enabled ? 'idle' : 'idle') 
          };
        });
        return next;
      });
      
      // NOTE: Removed automatic creation of enabled indicators here
      // This was causing duplicates. Now indicators are only created when explicitly toggled.
      
      console.log(`[DEBUG] Loaded ${indicatorConfigs.length} indicator configs without auto-creation`);
      
    } catch (error: any) {
      console.error('Failed to load indicator variants:', error);
      setIndicators([]);
    }
  };

  const loadCurrentIndicatorValues = async () => {
    try {
      const status = await apiService.getSessionIndicatorValues(sessionId, selectedSymbol);
      const indicatorValues = status.indicators || {};
      console.log('Current indicator values:', indicatorValues);

      setAvailableFields(Object.keys(indicatorValues));

      setIndicatorStatuses(prev => {
        const next = { ...prev };
        Object.keys(indicatorValues).forEach((indicatorId) => {
          const fileInfo = status.files?.[indicatorId];
          next[indicatorId] = {
            status: 'ready',
            message: fileInfo?.path ? `CSV ready: ${fileInfo.path}` : prev[indicatorId]?.message,
            filePath: fileInfo?.path || prev[indicatorId]?.filePath
          };
        });
        return next;
      });

      const indicatorValueKeys = new Set(Object.keys(indicatorValues));
      if (indicatorValueKeys.size > 0) {
        setIndicators(prevIndicators =>
          prevIndicators.map(indicator =>
            indicatorValueKeys.has(indicator.id)
              ? { ...indicator, enabled: true }
              : indicator
          )
        );
      }
    } catch (error: any) {
      console.warn('Failed to load current indicator values:', error);
    }
  };

  const determineIndicatorScale = (variantType: string): 'main' | 'secondary' => {
    // Price-related indicators go on main chart (same scale as price)
    const mainChartTypes = ['price', 'stop_loss', 'take_profit', 'close_order'];
    
    // Risk and general indicators go on secondary chart (different scales)
    const secondaryChartTypes = ['risk', 'general'];
    
    if (mainChartTypes.includes(variantType)) {
      return 'main';
    } else if (secondaryChartTypes.includes(variantType)) {
      return 'secondary';
    }
    
    // Default to secondary for unknown types
    return 'secondary';
  };

  const loadMockIndicators = () => {
    // Fallback to mock indicators when API fails
    const mockFields = [
      // Price-based indicators (main chart)
      'sma_20', 'sma_50', 'sma_200', 'ema_12', 'ema_26', 
      'bollinger_upper', 'bollinger_lower', 'support', 'resistance',
      // Momentum indicators (secondary chart)
      'rsi', 'macd', 'macd_signal', 'stoch_k', 'stoch_d',
      // Volume indicators (secondary chart)
      'volume_sma', 'volume_rsi', 'on_balance_volume',
      // Volatility indicators (secondary chart)
      'atr', 'volatility', 'williams_r'
    ];
    
    setAvailableFields(mockFields);
    
    // Create indicators from available fields with better categorization
    const newIndicators: IndicatorConfig[] = mockFields.map((field, index) => {
      const mainChartIndicators = [
        'sma_', 'ema_', 'bollinger_', 'support', 'resistance', 
        'pivot', 'vwap', 'twap'
      ];
      const isMainChart = mainChartIndicators.some(prefix => field.includes(prefix));
      
      return {
        id: field,
        name: field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        enabled: false,
        scale: isMainChart ? 'main' : 'secondary',
        color: defaultColors[index % defaultColors.length],
        field: field
      };
    });
    
    setIndicators(newIndicators);
    setIndicatorStatuses(() => {
      const next: Record<string, IndicatorStatusState> = {};
      newIndicators.forEach(ind => {
        next[ind.id] = { status: ind.enabled ? 'ready' : 'idle' };
      });
      return next;
    });
  };

  const pollIndicatorUntilReady = async (indicatorId: string, attempts = 6): Promise<boolean> => {
    for (let attempt = 1; attempt <= attempts; attempt++) {
      await new Promise(resolve => setTimeout(resolve, attempt * 800));
      try {
        const status = await apiService.getSessionIndicatorValues(sessionId, selectedSymbol);
        if (status.indicators && status.indicators[indicatorId]) {
          const fileInfo = status.files?.[indicatorId];
          updateIndicatorStatus(
            indicatorId,
            'ready',
            fileInfo?.path ? `CSV ready: ${fileInfo.path}` : undefined,
            fileInfo?.path
          );
          await loadChartData(true);
          return true;
        }
        updateIndicatorStatus(indicatorId, 'loading', `Processing (${attempt}/${attempts})...`);
      } catch (pollError) {
        console.error('Failed to poll indicator status:', pollError);
        updateIndicatorStatus(indicatorId, 'error', 'Failed to poll indicator status');
        return false;
      }
    }
    updateIndicatorStatus(indicatorId, 'error', 'Indicator calculation timeout');
    return false;
  };

  const processChartData = async () => {
    if (!chartData) return;

    let data = [...chartData.data];

    // Apply time interval aggregation
    if (timeInterval !== 'raw') {
      data = aggregateData(data, timeInterval);
      console.log(`Aggregated data for ${timeInterval}:`, data.length, 'points');
      if (data.length > 0) console.log('Sample aggregated point:', data[0]);
    }

    // Load real indicator values for enabled indicators
    let indicatorValues: any = {};
        const enabledIndicators = indicators.filter(ind => ind.enabled);
        // Filter out indicators with temporary IDs to prevent duplicate requests
        const validEnabledIndicators = enabledIndicators.filter(ind => 
          ind.field && !ind.field.startsWith('temp_') && !ind.id.startsWith('temp_')
        );
        
        if (validEnabledIndicators.length > 0) {
          try {
            // Use new unified API
            const valuesResponse = await apiService.getSessionIndicatorValues(sessionId, selectedSymbol);
            indicatorValues = valuesResponse.indicators || {};
            console.log('Loaded indicator values for valid enabled indicators:', indicatorValues);
            console.log('Valid enabled indicators:', validEnabledIndicators.map(ind => ({ field: ind.field, key: ind.id })));
          } catch (error) {
            console.warn('Failed to load indicator values, will use mock data for enabled indicators:', error);
            // Try legacy API as fallback
            try {
              indicatorValues = await apiService.getIndicatorValuesLegacy(selectedSymbol);
            } catch (legacyError) {
              console.warn('Legacy API also failed:', legacyError);
            }
          }
        }
    
        // Load histories for each indicator in parallel for better performance
        const indicatorHistories: { [field: string]: Record<string, any> } = {};
        
        const historyPromises = validEnabledIndicators.map(async (indicator) => {
          try {
            // Use indicator.field (session indicator ID) for API call - backend requires full session ID
            const apiEndpoint = `/api/indicators/sessions/${sessionId}/symbols/${selectedSymbol}/indicators/${indicator.field}/history`;
            console.log(`[DEBUG] Loading history from endpoint: ${apiEndpoint}`);
            const historyResponse = await apiService.get(apiEndpoint);
            const history = historyResponse.data?.history || [];
            
            console.log(`[DEBUG] Loaded history for ${indicator.field} (variant: ${indicator.variantId}):`, history.length, 'points');
            console.log(`[DEBUG] Sample history points for ${indicator.field}:`, history.slice(0, 3));
            
            if (history.length === 0) {
              console.warn(`[WARNING] No history data received for indicator ${indicator.field}`);
            }
            
            const historyMap: Record<string, any> = {};
            for (const hist of history) {
              const key = normalizeTimestampKey(hist.timestamp);
              historyMap[key] = hist.value;
              
              // DEBUG: Log first few timestamp conversions
              if (Object.keys(historyMap).length <= 5) {
                console.log(`[DEBUG] API timestamp conversion: ${hist.timestamp} -> normalized: ${key} (value: ${hist.value})`);
              }
            }
            
            console.log(`[DEBUG] History map keys for ${indicator.field}:`, Object.keys(historyMap).slice(0, 5));
            return { field: indicator.field, historyMap };
          } catch (error) {
            console.error(`Failed to load history for indicator ${indicator.field} (variant: ${indicator.variantId}) from endpoint:`, 
              `/api/indicators/sessions/${sessionId}/symbols/${selectedSymbol}/indicators/${indicator.field}/history`, 
              'Error:', error);
            return { field: indicator.field, historyMap: {} };
          }
        });
        
        // Wait for all history requests to complete
        const historyResults = await Promise.all(historyPromises);
        
        // Populate indicatorHistories object
        historyResults.forEach(({ field, historyMap }) => {
          indicatorHistories[field] = historyMap;
        });
    
        // Format data for Recharts
        const formattedData = data.map((point, index) => {
          // Convert Unix timestamp (seconds) to JavaScript timestamp (milliseconds)
          const timestampMs = point.timestamp * 1000;

          const formattedPoint: any = {
            index,
            timestamp: timestampMs,
            timeStr: new Date(timestampMs).toLocaleTimeString(),
            dateTimeStr: new Date(timestampMs).toLocaleString(),
            price: point.price,
            volume: point.volume || 0,
            highestBid: point.bid_prices ? Math.max(...point.bid_prices) : null,
            lowestAsk: point.ask_prices ? Math.min(...point.ask_prices) : null,
            // Add OHLC data for intervals
            open: point.open || point.price,
            high: point.high || point.price,
            low: point.low || point.price,
            close: point.close || point.price,
          };
    
          // Add only enabled indicators with valid IDs
          const enabledIndicators = indicators.filter(ind => ind.enabled);
          const validEnabledIndicators = enabledIndicators.filter(ind => 
            ind.field && !ind.field.startsWith('temp_') && !ind.id.startsWith('temp_')
          );
          validEnabledIndicators.forEach(indicator => {
            const field = indicator.field;
            
            // ALWAYS prefer historical data from backend over chart point data
            const historyMap = indicatorHistories[field] || {};
            const historyKey = normalizeTimestampKey(point.timestamp);
            
            // DEBUG: Show timestamp mapping for first few points
            if (index < 3) {
              console.log(`[DEBUG] Point ${index} timestamp mapping for ${field}:`);
              console.log(`  - Chart timestamp (original): ${point.timestamp} seconds`);
              console.log(`  - Chart timestamp (converted): ${timestampMs} ms (${new Date(timestampMs).toISOString()})`);
              console.log(`  - Normalized key: ${historyKey}`);
              console.log(`  - Available history keys sample:`, Object.keys(historyMap).slice(0, 10));
              console.log(`  - History value for key ${historyKey}:`, historyMap[historyKey]);
            }
            
            // Try exact match first
            if (historyMap[historyKey] !== undefined) {
              formattedPoint[field] = historyMap[historyKey];
              if (index < 3) console.log(`[DEBUG] Using exact match for ${field}:`, historyMap[historyKey]);
            } 
            // Try alternative key format
            else if (historyMap[String(point.timestamp)] !== undefined) {
              formattedPoint[field] = historyMap[String(point.timestamp)];
              if (index < 3) console.log(`[DEBUG] Using alt format for ${field}:`, historyMap[String(point.timestamp)]);
            } 
            // Try approximate matching with tolerance (±1000ms for timestamp precision differences)
            else {
              let foundValue = null;
              const tolerance = 1000; // 1 second tolerance
              const chartTime = Number(historyKey);
              
              for (const [timeKey, value] of Object.entries(historyMap)) {
                const histTime = Number(timeKey);
                if (Math.abs(chartTime - histTime) <= tolerance) {
                  foundValue = value;
                  if (index < 3) console.log(`[DEBUG] Found approximate match for ${field}: chart=${chartTime}, hist=${histTime}, diff=${Math.abs(chartTime - histTime)}ms, value=${value}`);
                  break;
                }
              }
              
              if (foundValue !== null) {
                formattedPoint[field] = foundValue;
              }
              // Fallback to chart data if available
              else if (point[field] !== undefined && point[field] !== null) {
                formattedPoint[field] = point[field];
                if (index < 3) console.log(`[DEBUG] Using chart data fallback for ${field}:`, point[field]);
              } 
              // Last resort: null
              else {
                formattedPoint[field] = null;
                if (index < 3) console.log(`[DEBUG] No data found for ${field}, setting null. Chart time: ${chartTime}`);
              }
            }
          });

          return formattedPoint;
        });
    
        console.log('Processed data:', formattedData.length, 'points');
        if (formattedData.length > 0) {
          console.log('Sample processed point:', formattedData[0]);
          console.log('[DEBUG] Chart data timestamps (first 3):', data.slice(0, 3).map(p => ({
            original_seconds: p.timestamp,
            converted_ms: p.timestamp * 1000,
            normalized: normalizeTimestampKey(p.timestamp),
            date: new Date(p.timestamp * 1000).toISOString()
          })));
        }
        
        setProcessedData(formattedData);
        
        // Reset zoom when data changes
        setZoomDomain(null);
        setBrushDomain(null);
  };

  const generateMockIndicatorValue = (field: string, point: any, index: number): number => {
    switch (field) {
      // Price-based indicators (main chart)
      case 'sma_20':
        return point.price * (0.99 + Math.random() * 0.02);
      case 'sma_50':
        return point.price * (0.98 + Math.random() * 0.04);
      case 'sma_200':
        return point.price * (0.95 + Math.random() * 0.1);
      case 'ema_12':
        return point.price * (0.995 + Math.random() * 0.01);
      case 'ema_26':
        return point.price * (0.99 + Math.random() * 0.02);
      case 'bollinger_upper':
        return point.price * 1.025;
      case 'bollinger_lower':
        return point.price * 0.975;
      case 'support':
        return point.price * 0.98;
      case 'resistance':
        return point.price * 1.02;
      
      // Momentum indicators (secondary chart)
      case 'rsi':
        return 30 + Math.random() * 40; // RSI 30-70 range
      case 'macd':
        return (Math.random() - 0.5) * 2; // MACD around 0
      case 'macd_signal':
        return (Math.random() - 0.5) * 1.5; // MACD Signal
      case 'stoch_k':
        return Math.random() * 100; // Stochastic %K
      case 'stoch_d':
        return Math.random() * 100; // Stochastic %D
      case 'williams_r':
        return -Math.random() * 100; // Williams %R (-100 to 0)
      
      // Volume indicators (secondary chart)
      case 'volume_sma':
        return point.volume * (0.8 + Math.random() * 0.4);
      case 'volume_rsi':
        return 40 + Math.random() * 20; // Volume RSI
      case 'on_balance_volume':
        return index * 1000 + Math.random() * 10000; // OBV
      
      // Volatility indicators (secondary chart)
      case 'atr':
        return point.price * 0.01 * (0.5 + Math.random()); // ATR
      case 'volatility':
        return Math.random() * 0.05; // Volatility %
      
      default:
        return point[field] || Math.random() * 100;
    }
  };

  // Helper function to find actual indicator IDs for a variant from given indicators object
  const findIndicatorIdsForVariant = (indicators: Record<string, any>, variantId: string): string[] => {
    return Object.keys(indicators).filter(indicatorId => {
      const indicator = indicators[indicatorId];
      return indicator?.variant_id === variantId;
    });
  };

  // Helper function to find existing indicator ID for a variant (returns first match)
  const findExistingIndicatorForVariant = (indicators: Record<string, any>, variantId: string): string | null => {
    const ids = findIndicatorIdsForVariant(indicators, variantId);
    return ids.length > 0 ? ids[0] : null;
  };

  // Helper function to disable other indicators with the same variant_id in local state
  const disableOtherIndicatorsWithSameVariant = (currentIndicators: any[], variantId: string, excludeIndex: number): any[] => {
    return currentIndicators.map((ind, i) => {
      if (i !== excludeIndex && (ind.variantId === variantId || ind.id === variantId)) {
        console.log(`[DEBUG] Disabling duplicate indicator: ${ind.name} (ID: ${ind.id})`);
        return { ...ind, enabled: false };
      }
      return ind;
    });
  };

  // Handler functions for indicator management
  const handleIndicatorToggle = async (index: number) => {
    const originalIndicators = indicators;
    const indicator = originalIndicators[index];
    const newEnabledState = !indicator.enabled;
    const previousId = indicator.id;

    let updatedIndicators = originalIndicators.map((ind, i) =>
      i === index ? { ...ind, enabled: newEnabledState } : ind
    );

    // If enabling indicator, disable any other indicators with the same variant_id first
    if (newEnabledState) {
      const variantId = indicator.variantId || indicator.id;
      updatedIndicators = disableOtherIndicatorsWithSameVariant(updatedIndicators, variantId, index);
      
      // Set flag to prevent useEffect from triggering processChartData during creation
      setIsCreatingIndicator(true);
    }

    setIndicators(updatedIndicators);

    if (newEnabledState) {
      updateIndicatorStatus(previousId, 'loading', 'Calculating indicator...');
    } else {
      updateIndicatorStatus(previousId, 'idle');
    }

    try {
      if (newEnabledState) {
        const variantId = indicator.variantId || indicator.id;
        
        // Validate variant_id exists
        if (!variantId) {
          throw new Error('Missing variant_id for indicator');
        }

        // POPRAWKA: Sprawdź czy wskaźnik już istnieje dla tego variant_id
        const existingIndicatorsResponse = await apiService.getSessionIndicatorValues(sessionId, selectedSymbol);
        const existingIndicators = existingIndicatorsResponse.indicators || {};
        const existingIndicatorId = findExistingIndicatorForVariant(existingIndicators, variantId);
        
        if (existingIndicatorId) {
          // Wskaźnik już istnieje - użyj istniejącego ID zamiast tworzyć nowy
          console.log(`[DEBUG] Reusing existing indicator: ${existingIndicatorId} for variant: ${variantId}`);
          
          updatedIndicators = updatedIndicators.map((ind, i) =>
            i === index ? { ...ind, field: existingIndicatorId, id: existingIndicatorId } : ind
          );
          setIndicators(updatedIndicators);
          
          // Reset flag to allow useEffect to process chart data
          setIsCreatingIndicator(false);
          
          updateIndicatorStatus(existingIndicatorId, 'ready', 'Using existing indicator');
          
          setSnackbar({
            open: true,
            message: `${indicator.name} enabled (using existing data)`,
            severity: 'success'
          });
          
          await saveUserPreferences(updatedIndicators);
          return; // Nie twórz nowego wskaźnika
        }

        // Jeśli wskaźnik nie istnieje, utwórz nowy
        const payload = {
          variant_id: variantId as string,
          parameters: indicator.parameters || {},
          force_recalculate: false
        };

        const response = await apiService.addIndicatorToSession(sessionId, selectedSymbol, payload);
        const indicatorId = response?.indicator_id;
        console.log(`[DEBUG] Backend response for ${indicator.name}:`, response);
        console.log(`[DEBUG] Received indicator ID:`, indicatorId);
        if (!indicatorId) {
          throw new Error('Missing indicator identifier from server');
        }

        updatedIndicators = updatedIndicators.map((ind, i) =>
          i === index ? { ...ind, field: indicatorId, id: indicatorId } : ind
        );
        setIndicators(updatedIndicators);
        
        // Reset flag to allow useEffect to process chart data with the new indicator
        setIsCreatingIndicator(false);

        setIndicatorStatuses(prev => {
          const next = { ...prev };
          const status = response?.status === 'added' ? 'ready' : 'loading';
          const statusMessage = response?.status === 'calculating'
            ? 'Processing indicator...'
            : response?.file?.path
              ? `CSV ready: ${response.file.path}`
              : prev[previousId]?.message;
          const filePath = response?.file?.path || prev[previousId]?.filePath;
          delete next[previousId];
          next[indicatorId] = { status, message: statusMessage, filePath };
          return next;
        });

        if (response?.status === 'added' && (response?.recent_values?.length ?? 0) > 0) {
          if (response?.file?.path) {
            updateIndicatorStatus(indicatorId, 'ready', `CSV ready: ${response.file.path}`, response.file.path);
          } else {
            updateIndicatorStatus(indicatorId, 'ready');
          }
          setSnackbar({
            open: true,
            message: `${indicator.name} enabled`,
            severity: 'success'
          });
        } else {
          const ready = await pollIndicatorUntilReady(indicatorId);
          if (ready) {
            setSnackbar({
              open: true,
              message: `${indicator.name} ready`,
              severity: 'success'
            });
          } else {
            setSnackbar({
              open: true,
              message: `${indicator.name} is still processing in the background`,
              severity: 'info'
            });
          }
        }

        await saveUserPreferences(updatedIndicators);
        
        // Chart data will update automatically via useEffect when indicators state changes
      } else {
        // Wyłączanie wskaźnika - pobierz aktualne wskaźniki z backend
        const currentIndicatorsResponse = await apiService.getSessionIndicatorValues(sessionId, selectedSymbol);
        const currentIndicators = currentIndicatorsResponse.indicators || {};
        
        if (indicator.variantId) {
          const existingIndicatorIds = findIndicatorIdsForVariant(currentIndicators, indicator.variantId);
          
          // Usuń wszystkie znalezione instancje
          for (const indicatorId of existingIndicatorIds) {
            try {
              await apiService.delete(
                `/api/indicators/sessions/${sessionId}/symbols/${selectedSymbol}/indicators/${indicatorId}`
              );
              console.log(`Removed duplicate indicator: ${indicatorId}`);
            } catch (error) {
              console.warn(`Failed to remove indicator ${indicatorId}:`, error);
            }
          }
          
          console.log(`Removed ${existingIndicatorIds.length} instances of variant ${indicator.variantId}`);
        } else if (indicator.field) {
          // Fallback dla starszych wskaźników bez variantId
          await apiService.delete(
            `/api/indicators/sessions/${sessionId}/symbols/${selectedSymbol}/indicators/${indicator.field}`
          );
        }

        updateIndicatorStatus(previousId, 'idle');
        await saveUserPreferences(updatedIndicators);
        
        // Don't call processChartData() after disabling indicator
        // The indicator was just deleted from backend, so processChartData() would get 500 error
        // Chart will update automatically via useEffect when indicators state changes
        
        setSnackbar({
          open: true,
          message: `${indicator.name} disabled`,
          severity: 'info'
        });
      }
    } catch (error: any) {
      console.error('Failed to toggle indicator:', error);
      setIndicators(originalIndicators);
      setIsCreatingIndicator(false); // Reset flag on error
      updateIndicatorStatus(previousId, 'error', error?.message || 'Failed to toggle indicator');
      setSnackbar({
        open: true,
        message: `Failed to toggle indicator: ${error?.message || 'Unexpected error'}`,
        severity: 'error'
      });
    }
  };

  const handleIndicatorColorChange = (index: number, color: string) => {
    const updated = indicators.map((indicator, i) =>
      i === index ? { ...indicator, color } : indicator
    );
    setIndicators(updated);
    // Auto-save preferences when color changes
    saveUserPreferences(updated);
  };

  const handleIndicatorScaleChange = (index: number, scale: 'main' | 'secondary') => {
    const updated = indicators.map((indicator, i) =>
      i === index ? { ...indicator, scale } : indicator
    );
    setIndicators(updated);
    // Auto-save preferences when scale changes
    saveUserPreferences(updated);
  };

  const saveUserPreferences = async (nextIndicators: IndicatorConfig[] = indicators) => {
    try {
      const preferences = {
        enabled_indicators: nextIndicators.filter(ind => ind.enabled).map(ind => ind.id),
        indicator_scales: Object.fromEntries(
          nextIndicators.map(ind => [ind.id, ind.scale])
        ),
        indicator_colors: Object.fromEntries(
          nextIndicators.map(ind => [ind.id, ind.color])
        ),
        timestamp: Date.now()
      };
      
      await apiService.post(
        `/api/indicators/sessions/${sessionId}/symbols/${selectedSymbol}/preferences`,
        preferences
      );
      
      console.log('Saved user preferences');
      
    } catch (error: any) {
      console.warn('Failed to save user preferences:', error);
    }
  };

  // Computed values for enabled indicators
  const enabledMainIndicators = indicators.filter(i => i.enabled && i.scale === 'main');
  const enabledSecondaryIndicators = indicators.filter(i => i.enabled && i.scale === 'secondary');

  // Calculate price domain for better scaling
  const priceDomain = useMemo(() => {
    if (processedData.length === 0) {
      console.log('No processed data for price domain calculation');
      return [0, 100]; // fallback
    }
    
    const prices: number[] = [];
    processedData.forEach(point => {
      if (point.price != null && !isNaN(point.price)) prices.push(point.price);
      if (point.high != null && !isNaN(point.high)) prices.push(point.high);
      if (point.low != null && !isNaN(point.low)) prices.push(point.low);
      if (point.open != null && !isNaN(point.open)) prices.push(point.open);
      if (point.close != null && !isNaN(point.close)) prices.push(point.close);
      if (point.highestBid != null && !isNaN(point.highestBid)) prices.push(point.highestBid);
      if (point.lowestAsk != null && !isNaN(point.lowestAsk)) prices.push(point.lowestAsk);
      
      // Include main indicators in price domain
      enabledMainIndicators.forEach(indicator => {
        if (point[indicator.field] != null && typeof point[indicator.field] === 'number' && !isNaN(point[indicator.field])) {
          prices.push(point[indicator.field]);
        }
      });
    });
    
    if (prices.length === 0) {
      console.log('No valid prices found for domain calculation');
      return [0, 100]; // fallback
    }
    
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const margin = (maxPrice - minPrice) * 0.05; // 5% margin
    
    const domain = [minPrice - margin, maxPrice + margin];
    console.log(`Price domain calculated: [${domain[0].toFixed(6)}, ${domain[1].toFixed(6)}] from ${prices.length} prices`);
    console.log(`Min price: ${minPrice.toFixed(6)}, Max price: ${maxPrice.toFixed(6)}`);
    
    return domain;
  }, [processedData, enabledMainIndicators]);

  // Debug priceDomain
  useEffect(() => {
    console.log('Current priceDomain:', priceDomain);
  }, [priceDomain]);

  // Formatting functions
  const formatXAxisTick = (timestamp: number) => {
    const date = new Date(timestamp);
    if (timeInterval === 'raw' || timeInterval === '10s' || timeInterval === '30s') {
      return date.toLocaleTimeString();
    } else {
      return date.toLocaleString().split(',')[1]?.trim() || date.toLocaleTimeString();
    }
  };

  const formatTooltipLabel = (timestamp: number) => {
    return new Date(timestamp).toLocaleString();
  };

  const resetZoom = () => {
    setZoomDomain(null);
    setBrushDomain(null);
  };

  const handleBrushChange = (domain: any) => {
    if (domain && domain.startIndex !== undefined && domain.endIndex !== undefined) {
      const start = processedData[domain.startIndex]?.timestamp;
      const end = processedData[domain.endIndex]?.timestamp;
      if (start && end) {
        setZoomDomain([start, end]);
      }
    }
  };

  const aggregateData = (data: ChartDataPoint[], interval: string): ChartDataPoint[] => {
    if (interval === 'raw') return data;

    const intervalMs = getIntervalMs(interval);
    const aggregated: ChartDataPoint[] = [];
    
    let currentBucket: ChartDataPoint[] = [];
    let bucketStart = Math.floor(data[0]?.timestamp / intervalMs) * intervalMs;

    data.forEach(point => {
      const pointBucket = Math.floor(point.timestamp / intervalMs) * intervalMs;
      
      if (pointBucket === bucketStart) {
        currentBucket.push(point);
      } else {
        if (currentBucket.length > 0) {
          aggregated.push(aggregatePoints(currentBucket, bucketStart));
        }
        currentBucket = [point];
        bucketStart = pointBucket;
      }
    });

    if (currentBucket.length > 0) {
      aggregated.push(aggregatePoints(currentBucket, bucketStart));
    }

    return aggregated;
  };

  const getIntervalMs = (interval: string): number => {
    switch (interval) {
      case '10s': return 10000;
      case '30s': return 30000;
      case '1m': return 60000;
      case '5m': return 300000;
      case '15m': return 900000;
      case '1h': return 3600000;
      default: return 1000;
    }
  };

  const aggregatePoints = (points: ChartDataPoint[], timestamp: number): ChartDataPoint => {
    // OHLC calculation for candle charts
    const prices = points.map(p => p.price);
    const open = points[0].price;
    const high = Math.max(...prices);
    const low = Math.min(...prices);
    const close = points[points.length - 1].price;
    
    const aggregated: ChartDataPoint = {
      timestamp,
      symbol: points[0].symbol,
      price: close, // Close price for line representation
      open: open,   // Open price for candles
      high: high,   // High price for candles
      low: low,     // Low price for candles
      close: close, // Close price for candles
      volume: points.reduce((sum, p) => sum + p.volume, 0), // Sum volume
    };

    // Aggregate bid/ask prices
    const bidPrices: number[] = [];
    const askPrices: number[] = [];
    
    points.forEach(point => {
      if (point.bid_prices) bidPrices.push(...point.bid_prices);
      if (point.ask_prices) askPrices.push(...point.ask_prices);
    });

    if (bidPrices.length > 0) aggregated.bid_prices = [Math.max(...bidPrices)];
    if (askPrices.length > 0) aggregated.ask_prices = [Math.min(...askPrices)];

    // Aggregate other fields (average)
    availableFields.forEach(field => {
      const values = points.map(p => p[field]).filter(v => v !== null && v !== undefined);
      if (values.length > 0) {
        aggregated[field] = values.reduce((sum, val) => sum + val, 0) / values.length;
      }
    });

    return aggregated;
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading data...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
        <Button
          variant="contained"
          onClick={() => router.back()}
          sx={{ mt: 2 }}
          startIcon={<ArrowBackIcon />}
        >
          Go Back
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <AppBar position="static" color="transparent" elevation={0} sx={{ mb: 3 }}>
        <Toolbar sx={{ px: 0 }}>
          <IconButton
            edge="start"
            onClick={() => router.back()}
            sx={{ mr: 2 }}
          >
            <ArrowBackIcon />
          </IconButton>
          
          <Box sx={{ flexGrow: 1 }}>
            <Breadcrumbs>
              <Link
                color="inherit"
                href="/data-collection"
                sx={{ textDecoration: 'none' }}
              >
                Data Collection
              </Link>
              <Typography color="textPrimary">
                Charts - {sessionId}
              </Typography>
            </Breadcrumbs>
            <Typography variant="h4" sx={{ mt: 1 }}>
              <ChartIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              Interactive Chart Analysis
            </Typography>
          </Box>

          <ButtonGroup variant="outlined" size="small">
            <Tooltip title="Reset Zoom">
              <Button onClick={resetZoom} startIcon={<ResetZoomIcon />}>
                Reset Zoom
              </Button>
            </Tooltip>
            <Tooltip title="Refresh Data">
              <Button onClick={() => loadChartData()} startIcon={<RefreshIcon />}>
                Refresh
              </Button>
            </Tooltip>
          </ButtonGroup>
        </Toolbar>
      </AppBar>

      {/* Controls */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <FormControl fullWidth>
            <InputLabel>Symbol</InputLabel>
            <Select
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              label="Symbol"
            >
              {availableSymbols.map(symbol => (
                <MenuItem key={symbol} value={symbol}>
                  {symbol}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <FormControl fullWidth>
            <InputLabel>Time Interval</InputLabel>
            <Select
              value={timeInterval}
              onChange={(e) => setTimeInterval(e.target.value)}
              label="Time Interval"
            >
              {timeIntervals.map(interval => (
                <MenuItem key={interval.value} value={interval.value}>
                  {interval.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <FormControl fullWidth>
            <InputLabel>Max Data Points</InputLabel>
            <Select
              value={maxPoints}
              onChange={(e) => setMaxPoints(e.target.value as number)}
              label="Max Data Points"
            >
              <MenuItem value={500}>500 points</MenuItem>
              <MenuItem value={1000}>1,000 points</MenuItem>
              <MenuItem value={2500}>2,500 points</MenuItem>
              <MenuItem value={5000}>5,000 points</MenuItem>
              <MenuItem value={10000}>10,000 points</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ py: 1.5 }}>
              <Typography variant="body2" color="text.secondary">
                Data Points: {processedData.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Interval: {timeIntervals.find(i => i.value === timeInterval)?.label}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Indicators Panel */}
      <Accordion sx={{ mb: 3 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">
            <TimelineIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Technical Indicators ({indicators.filter(i => i.enabled).length} enabled of {indicators.length} available)
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          {/* Quick Enable/Disable All */}
          <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
            <Button 
              variant="outlined" 
              size="small"
              onClick={() => setIndicators(prev => prev.map(ind => ({ ...ind, enabled: true })))}
            >
              Enable All
            </Button>
            <Button 
              variant="outlined" 
              size="small"
              onClick={() => setIndicators(prev => prev.map(ind => ({ ...ind, enabled: false })))}
            >
              Disable All
            </Button>
            <Button 
              variant="outlined" 
              size="small"
              onClick={() => setIndicators(prev => prev.map(ind => ({ ...ind, enabled: ind.scale === 'main' })))}
            >
              Main Chart Only
            </Button>
            <Button 
              variant="outlined" 
              size="small"
              onClick={() => setIndicators(prev => prev.map(ind => ({ ...ind, enabled: ind.scale === 'secondary' })))}
            >
              Secondary Chart Only
            </Button>
          </Box>

          {/* Categorized Indicators */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" color="primary" sx={{ mb: 1, fontWeight: 'bold' }}>
              📈 Main Chart Indicators (overlays on price chart)
            </Typography>
            <Grid container spacing={2}>
              {indicators.filter(ind => ind.scale === 'main').map((indicator, index) => (
                <Grid item xs={12} md={6} lg={4} key={indicator.id}>
                  <Paper sx={{ p: 2, border: indicator.enabled ? '2px solid' : '1px solid', borderColor: indicator.enabled ? indicator.color : 'divider' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={indicator.enabled}
                            onChange={() => handleIndicatorToggle(indicators.indexOf(indicator))}
                            sx={{ '&.Mui-checked': { color: indicator.color } }}
                          />
                        }
                        label={indicator.name}
                        sx={{ flexGrow: 1 }}
                      />
                      <TextField
                        type="color"
                        value={indicator.color}
                        onChange={(e) => handleIndicatorColorChange(indicators.indexOf(indicator), e.target.value)}
                        sx={{ width: 50, height: 35 }}
                        size="small"
                      />
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => handleIndicatorScaleChange(indicators.indexOf(indicator), 'secondary')}
                        sx={{ fontSize: '0.7rem', minWidth: 'auto', px: 1 }}
                      >
                        Move to Secondary
                      </Button>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {indicator.indicatorType ? (
                        <>
                          Type: {indicator.indicatorType} • Period: {indicator.period || 'default'} • Timeframe: {indicator.timeframe || '1m'}
                          <br />
                          Field: {indicator.field} • Overlays on price chart
                        </>
                      ) : (
                        `Field: ${indicator.field} • Overlays on price chart`
                      )}
                    </Typography>
                    {indicatorStatuses[indicator.id]?.status === 'loading' && (
                      <LinearProgress sx={{ mt: 1 }} />
                    )}
                    {indicatorStatuses[indicator.id]?.status === 'ready' && indicatorStatuses[indicator.id]?.filePath && (
                      <Typography variant="caption" color="success.main" sx={{ mt: 1, display: 'block' }}>
                        CSV: {indicatorStatuses[indicator.id]?.filePath}
                      </Typography>
                    )}
                    {indicatorStatuses[indicator.id]?.status === 'loading' && indicatorStatuses[indicator.id]?.message && (
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                        {indicatorStatuses[indicator.id]?.message}
                      </Typography>
                    )}
                    {indicatorStatuses[indicator.id]?.status === 'error' && (
                      <Alert severity="warning" sx={{ mt: 1 }}>
                        {indicatorStatuses[indicator.id]?.message || 'Indicator calculation failed'}
                      </Alert>
                    )}
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </Box>

          <Box>
            <Typography variant="subtitle1" color="secondary" sx={{ mb: 1, fontWeight: 'bold' }}>
              📊 Secondary Chart Indicators (separate chart below)
            </Typography>
            <Grid container spacing={2}>
              {indicators.filter(ind => ind.scale === 'secondary').map((indicator, index) => (
                <Grid item xs={12} md={6} lg={4} key={indicator.id}>
                  <Paper sx={{ p: 2, border: indicator.enabled ? '2px solid' : '1px solid', borderColor: indicator.enabled ? indicator.color : 'divider' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={indicator.enabled}
                            onChange={() => handleIndicatorToggle(indicators.indexOf(indicator))}
                            sx={{ '&.Mui-checked': { color: indicator.color } }}
                          />
                        }
                        label={indicator.name}
                        sx={{ flexGrow: 1 }}
                      />
                      <TextField
                        type="color"
                        value={indicator.color}
                        onChange={(e) => handleIndicatorColorChange(indicators.indexOf(indicator), e.target.value)}
                        sx={{ width: 50, height: 35 }}
                        size="small"
                      />
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => handleIndicatorScaleChange(indicators.indexOf(indicator), 'main')}
                        sx={{ fontSize: '0.7rem', minWidth: 'auto', px: 1 }}
                      >
                        Move to Main
                      </Button>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {indicator.indicatorType ? (
                        <>
                          Type: {indicator.indicatorType} • Period: {indicator.period || 'default'} • Timeframe: {indicator.timeframe || '1m'}
                          <br />
                          Field: {indicator.field} • Shows in secondary chart
                        </>
                      ) : (
                        `Field: ${indicator.field} • Shows in secondary chart`
                      )}
                    </Typography>
                    {indicatorStatuses[indicator.id]?.status === 'loading' && (
                      <LinearProgress sx={{ mt: 1 }} />
                    )}
                    {indicatorStatuses[indicator.id]?.status === 'ready' && indicatorStatuses[indicator.id]?.filePath && (
                      <Typography variant="caption" color="success.main" sx={{ mt: 1, display: 'block' }}>
                        CSV: {indicatorStatuses[indicator.id]?.filePath}
                      </Typography>
                    )}
                    {indicatorStatuses[indicator.id]?.status === 'loading' && indicatorStatuses[indicator.id]?.message && (
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                        {indicatorStatuses[indicator.id]?.message}
                      </Typography>
                    )}
                    {indicatorStatuses[indicator.id]?.status === 'error' && (
                      <Alert severity="warning" sx={{ mt: 1 }}>
                        {indicatorStatuses[indicator.id]?.message || 'Indicator calculation failed'}
                      </Alert>
                    )}
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </Box>
          
          {indicators.length === 0 && (
            <Alert severity="info">
              No indicators available for this symbol. Load data to see available indicators.
            </Alert>
          )}
        </AccordionDetails>
      </Accordion>

      {/* Charts */}
      {processedData.length > 0 && (
        <Grid container spacing={3}>
          {/* Loading indicator for indicator updates */}
          {isUpdatingIndicators && (
            <Grid item xs={12}>
              <Alert severity="info" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CircularProgress size={20} />
                <Typography>Updating indicators... Chart data is being refreshed.</Typography>
              </Alert>
            </Grid>
          )}
          
          {/* Main Price Chart with Volume and Brush */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2, height: 700 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                <TrendingUpIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Price Chart with Volume {enabledMainIndicators.length > 0 && `and ${enabledMainIndicators.map(i => i.name).join(', ')}`}
              </Typography>
              <Box sx={{ height: 'calc(100% - 60px)' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={processedData}
                    margin={{ top: 5, right: 80, left: 20, bottom: 100 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp"
                      type="number"
                      scale="time"
                      domain={zoomDomain || ['dataMin', 'dataMax']}
                      tickFormatter={formatXAxisTick}
                    />
                    {/* Left Y-axis for Price */}
                    <YAxis 
                      yAxisId="price" 
                      orientation="left"
                      domain={[(dataMin: number) => {
                        console.log('YAxis dataMin callback:', dataMin);
                        return priceDomain[0];
                      }, (dataMax: number) => {
                        console.log('YAxis dataMax callback:', dataMax);
                        return priceDomain[1];
                      }]}
                      allowDataOverflow={false}
                      includeHidden={false}
                      scale="linear"
                      type="number"
                      tickCount={8}
                      tickFormatter={(value) => value.toFixed(6)}
                      label={{ value: 'Price', angle: -90, position: 'insideLeft' }}
                    />
                    {/* Right Y-axis for Volume */}
                    <YAxis 
                      yAxisId="volume" 
                      orientation="right"
                      domain={['dataMin', 'dataMax']}
                      label={{ value: 'Volume', angle: 90, position: 'insideRight' }}
                    />
                    <RechartsTooltip 
                      labelFormatter={formatTooltipLabel}
                      formatter={(value: any, name: string) => [
                        typeof value === 'number' ? 
                          (name === 'Volume' ? value.toFixed(2) : value.toFixed(6)) : value,
                        name
                      ]}
                    />
                    <Legend />
                    
                    {/* Price representation - line for raw data, OHLC lines for intervals */}
                    {timeInterval === 'raw' ? (
                      <Line 
                        yAxisId="price"
                        type="monotone" 
                        dataKey="price" 
                        stroke="#1976d2" 
                        strokeWidth={2} 
                        dot={false} 
                        name="Price"
                        connectNulls={false}
                      />
                    ) : (
                      // For intervals, show OHLC as multiple lines
                      <>
                        {/* High price line */}
                        <Line 
                          yAxisId="price"
                          type="monotone" 
                          dataKey="high" 
                          stroke="#4caf50" 
                          strokeWidth={1} 
                          dot={false} 
                          name="High"
                          connectNulls={false}
                        />
                        {/* Low price line */}
                        <Line 
                          yAxisId="price"
                          type="monotone" 
                          dataKey="low" 
                          stroke="#f44336" 
                          strokeWidth={1} 
                          dot={false} 
                          name="Low"
                          connectNulls={false}
                        />
                        {/* Close price line (main) */}
                        <Line 
                          yAxisId="price"
                          type="monotone" 
                          dataKey="close" 
                          stroke="#1976d2" 
                          strokeWidth={3} 
                          dot={false} 
                          name="Close"
                          connectNulls={false}
                        />
                        {/* Open price line (dashed) */}
                        <Line 
                          yAxisId="price"
                          type="monotone" 
                          dataKey="open" 
                          stroke="#ff9800" 
                          strokeWidth={2} 
                          strokeDasharray="5 5"
                          dot={false} 
                          name="Open"
                          connectNulls={false}
                        />
                      </>
                    )}
                    
                    {/* Volume - line for raw data, bars for intervals */}
                    {timeInterval === 'raw' ? (
                      <Line 
                        yAxisId="volume"
                        type="monotone" 
                        dataKey="volume" 
                        stroke="#9c27b0" 
                        strokeWidth={1}
                        strokeOpacity={0.7}
                        dot={false} 
                        name="Volume"
                        connectNulls={false}
                      />
                    ) : (
                      <Bar 
                        yAxisId="volume"
                        dataKey="volume" 
                        fill="#9c27b0" 
                        fillOpacity={0.3}
                        name="Volume"
                      />
                    )}
                    
                    {/* Bid/Ask Lines */}
                    {processedData.some(d => d.highestBid !== null) && (
                      <Line 
                        yAxisId="price"
                        type="monotone" 
                        dataKey="highestBid" 
                        stroke="#4caf50" 
                        strokeWidth={1} 
                        dot={false} 
                        name="Highest Bid"
                        connectNulls={false}
                      />
                    )}
                    
                    {processedData.some(d => d.lowestAsk !== null) && (
                      <Line 
                        yAxisId="price"
                        type="monotone" 
                        dataKey="lowestAsk" 
                        stroke="#f44336" 
                        strokeWidth={1} 
                        dot={false} 
                        name="Lowest Ask"
                        connectNulls={false}
                      />
                    )}
                    
                    {/* Main Scale Indicators */}
                    {enabledMainIndicators.map(indicator => (
                      <Line
                        key={indicator.field}
                        yAxisId="price"
                        type="monotone"
                        dataKey={indicator.field}
                        stroke={indicator.color}
                        strokeWidth={1}
                        strokeDasharray="5 5"
                        dot={false}
                        name={indicator.name}
                        connectNulls
                      />
                    ))}
                    
                    {/* Brush for zoom/pan */}
                    <Brush
                      dataKey="timestamp"
                      height={60}
                      stroke="#8884d8"
                      onChange={handleBrushChange}
                      tickFormatter={formatXAxisTick}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                💡 Use the brush at the bottom to zoom and pan. Volume shows as {timeInterval === 'raw' ? 'line' : 'bars'} for {timeInterval === 'raw' ? 'raw data' : 'time intervals'}.
              </Typography>
            </Paper>
          </Grid>

          {/* Secondary Indicators Chart - Always visible */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2, height: 400 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                <TimelineIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Secondary Indicators Chart
                {enabledSecondaryIndicators.length > 0 && (
                  <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                    ({enabledSecondaryIndicators.map(i => i.name).join(', ')})
                  </Typography>
                )}
              </Typography>
              <Box sx={{ height: 'calc(100% - 60px)' }}>
                {enabledSecondaryIndicators.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart 
                      data={processedData}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="timestamp"
                        type="number"
                        scale="time"
                        domain={zoomDomain || ['dataMin', 'dataMax']}
                        tickFormatter={formatXAxisTick}
                      />
                      <YAxis 
                        domain={['dataMin', 'dataMax']}
                        allowDataOverflow={false}
                        scale="linear"
                        type="number"
                        label={{ value: 'Indicator Values', angle: -90, position: 'insideLeft' }}
                      />
                      <RechartsTooltip 
                        labelFormatter={formatTooltipLabel}
                        formatter={(value: any, name: string) => [
                          typeof value === 'number' ? value.toFixed(4) : value,
                          name
                        ]}
                      />
                      <Legend />
                      {enabledSecondaryIndicators.map(indicator => (
                      <Line
                        key={indicator.field}
                        type="monotone"
                        dataKey={indicator.field}
                        stroke={indicator.color}
                        strokeWidth={2}
                        dot={false}
                        name={indicator.name}
                        connectNulls
                      />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <Box 
                    sx={{ 
                      height: '100%', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      border: '2px dashed #ccc',
                      borderRadius: 1,
                      backgroundColor: '#f9f9f9'
                    }}
                  >
                    <Typography variant="h6" color="text.secondary" textAlign="center">
                      📊 Select indicators from the panel above<br />
                      <Typography variant="body2" color="text.secondary">
                        Choose from RSI, MACD, Volume indicators and more
                      </Typography>
                    </Typography>
                  </Box>
                )}
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                📊 Secondary indicators chart - Enable indicators from the panel above. Chart is synchronized with main chart zoom/pan.
              </Typography>
            </Paper>
          </Grid>

          {/* Chart Controls Info */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Chart Controls & Features
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6} lg={3}>
                  <Typography variant="subtitle2" color="primary">Synchronized Zoom & Pan</Typography>
                  <Typography variant="body2">Use the brush at the bottom of price chart. All charts (main and secondary indicators) are synchronized</Typography>
                </Grid>
                <Grid item xs={12} md={6} lg={3}>
                  <Typography variant="subtitle2" color="primary">Volume Integration</Typography>
                  <Typography variant="body2">Volume is now on main chart - {timeInterval === 'raw' ? 'line for raw data' : 'bars for intervals'} on right axis</Typography>
                </Grid>
                <Grid item xs={12} md={6} lg={3}>
                  <Typography variant="subtitle2" color="primary">Price Display</Typography>
                  <Typography variant="body2">{timeInterval === 'raw' ? 'Line chart for raw data' : 'OHLC representation for intervals with Open, High, Low, Close prices'}</Typography>
                </Grid>
                <Grid item xs={12} md={6} lg={3}>
                  <Typography variant="subtitle2" color="primary">Indicators System</Typography>
                  <Typography variant="body2">Main indicators overlay on price chart, secondary indicators in separate synchronized chart below</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Alert severity="success">
                    ✅ <strong>New Features:</strong> Volume integrated into main chart, OHLC candles for time intervals, perfect synchronization between main and secondary indicator charts
                  </Alert>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      )}

      {processedData.length === 0 && chartData && (
        <Alert severity="warning">
          No data available for the selected time interval. Try selecting "Raw Data" or a different interval.
        </Alert>
      )}

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
      >
        <Alert
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
