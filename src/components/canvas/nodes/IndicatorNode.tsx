import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import {
  Paper,
  Typography,
  Box,
  Chip,
  IconButton,
  Alert,
  Collapse,
  Button,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Settings as SettingsIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';

interface IndicatorNodeData {
  label: string;
  node_type: string;
  // Data source parameters
  symbol?: string;
  update_frequency?: number;
  aggregation?: string;
  // Indicator parameters
  window?: number;
  baseline_window?: number;
  surge_threshold?: number;
  period?: number;
  depth_levels?: number;
  // Live data
  currentValue?: number;
  lastUpdate?: string;
  // Common
  validation_errors?: string[];
}

const IndicatorNode = React.memo(function IndicatorNode({ data, selected }: NodeProps<IndicatorNodeData>) {
  const { label, node_type, symbol, update_frequency, aggregation, window, baseline_window, surge_threshold, period, depth_levels, currentValue, lastUpdate, validation_errors } = data;

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'price_source':
      case 'volume_source':
        return '#2196f3'; // Blue for data sources
      case 'vwap':
        return '#4caf50'; // Green for VWAP
      case 'volume_surge_ratio':
      case 'price_velocity':
        return '#ff9800'; // Orange for pump indicators
      case 'bid_ask_imbalance':
        return '#9c27b0'; // Purple for order book
      default:
        return '#757575'; // Grey for unknown
    }
  };

  const getDisplayType = (type: string) => {
    return type.replace(/_/g, ' ').toUpperCase();
  };

  return (
    <Paper
      elevation={selected ? 8 : 2}
      sx={{
        p: 2,
        minWidth: 180,
        border: selected ? '2px solid #2196f3' : '1px solid #e0e0e0',
        borderRadius: 2,
        backgroundColor: '#f8f9fa',
        position: 'relative',
      }}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: '#555',
          width: 8,
          height: 8,
        }}
      />

      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <TrendingUpIcon sx={{ mr: 1, color: getNodeColor(node_type) }} />
        <Typography variant="subtitle2" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
          {label}
        </Typography>
        <IconButton size="small" sx={{ p: 0.5 }}>
          <SettingsIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* Node Type */}
      <Box sx={{ mb: 1 }}>
        <Chip
          label={getDisplayType(node_type)}
          size="small"
          sx={{
            backgroundColor: getNodeColor(node_type),
            color: 'white',
            fontSize: '0.7rem',
            mb: 0.5
          }}
        />
      </Box>

      {/* Parameters */}
      <Box sx={{ fontSize: '0.8rem', color: '#666', mb: 1 }}>
        {symbol && <div>Symbol: {symbol}</div>}
        {update_frequency && <div>Update Freq: {update_frequency}ms</div>}
        {aggregation && <div>Aggregation: {aggregation}</div>}
        {window && <div>Window: {window}s</div>}
        {baseline_window && <div>Baseline: {baseline_window}s</div>}
        {surge_threshold && <div>Threshold: {surge_threshold}</div>}
        {period && <div>Period: {period}</div>}
        {depth_levels && <div>Depth Levels: {depth_levels}</div>}
      </Box>

      {/* Current Value */}
      {currentValue !== undefined && (
        <Box sx={{
          p: 1,
          backgroundColor: '#e3f2fd',
          borderRadius: 1,
          textAlign: 'center'
        }}>
          <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#1976d2' }}>
            {node_type.includes('ratio') || node_type.includes('pct') ?
              `${currentValue.toFixed(2)}%` :
              currentValue.toFixed(4)
            }
          </Typography>
          {lastUpdate && (
            <Typography variant="caption" sx={{ color: '#666', display: 'block', mt: 0.5 }}>
              Updated: {new Date(lastUpdate).toLocaleTimeString()}
            </Typography>
          )}
        </Box>
      )}

      {/* Connection Status */}
      {currentValue === undefined && (
        <Box sx={{
          p: 1,
          backgroundColor: '#fff3e0',
          borderRadius: 1,
          textAlign: 'center'
        }}>
          <Typography variant="caption" sx={{ color: '#f57c00' }}>
            Waiting for live data...
          </Typography>
        </Box>
      )}

      {/* Validation Errors */}
      {validation_errors && validation_errors.length > 0 && (
        <Box sx={{ mt: 1 }}>
          <Collapse in={true}>
            <Alert
              severity="error"
              variant="outlined"
              size="small"
              icon={<ErrorIcon fontSize="small" />}
              action={
                <Button
                  size="small"
                  startIcon={<RefreshIcon />}
                  onClick={() => {
                    // Trigger validation refresh
                    console.log('Retrying validation for', label);
                  }}
                  sx={{ fontSize: '0.7rem' }}
                >
                  Retry
                </Button>
              }
              sx={{
                fontSize: '0.7rem',
                '& .MuiAlert-message': { p: 0.5 },
                '& .MuiAlert-action': { p: 0 }
              }}
            >
              <Box>
                {validation_errors.map((error, index) => (
                  <Typography
                    key={index}
                    variant="caption"
                    sx={{
                      display: 'block',
                      fontSize: '0.7rem',
                      lineHeight: 1.2,
                      mb: index < validation_errors.length - 1 ? 0.5 : 0
                    }}
                  >
                    • {error}
                  </Typography>
                ))}
              </Box>
            </Alert>
          </Collapse>
        </Box>
      )}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: getNodeColor(node_type),
          width: 8,
          height: 8,
        }}
      />
    </Paper>
  );
});

export default IndicatorNode;