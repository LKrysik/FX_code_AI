import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import {
  Paper,
  Typography,
  Box,
  Chip,
  IconButton,
} from '@mui/material';
import {
  Storage as StorageIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';

interface DataSourceNodeData {
  label: string;
  node_type: string;
  symbol?: string;
  update_frequency?: number;
  aggregation?: string;
  validation_errors?: string[];
}

const DataSourceNode = React.memo(function DataSourceNode({ data, selected }: NodeProps<DataSourceNodeData>) {
  const { label, node_type, symbol, update_frequency, aggregation, validation_errors } = data;

  const getDataSourceColor = (type: string) => {
    switch (type) {
      case 'price_source':
        return '#2196f3'; // Blue
      case 'volume_source':
        return '#ff9800'; // Orange
      case 'orderbook_source':
        return '#4caf50'; // Green
      default:
        return '#9c27b0'; // Purple
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
        backgroundColor: '#f3e5f5',
        position: 'relative',
      }}
    >
      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: getDataSourceColor(node_type),
          width: 8,
          height: 8,
        }}
      />

      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <StorageIcon sx={{ mr: 1, color: getDataSourceColor(node_type) }} />
        <Typography variant="subtitle2" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
          {label}
        </Typography>
        <IconButton size="small" sx={{ p: 0.5 }}>
          <SettingsIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* Data Source Type */}
      <Box sx={{ mb: 1 }}>
        <Chip
          label={getDisplayType(node_type)}
          size="small"
          sx={{
            backgroundColor: getDataSourceColor(node_type),
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
      </Box>

      {/* Validation Errors */}
      {validation_errors && validation_errors.length > 0 && (
        <Box sx={{ mt: 1 }}>
          <Typography variant="caption" sx={{ color: '#d32f2f', display: 'block' }}>
            {validation_errors.length} error(s)
          </Typography>
        </Box>
      )}
    </Paper>
  );
});

export default DataSourceNode;