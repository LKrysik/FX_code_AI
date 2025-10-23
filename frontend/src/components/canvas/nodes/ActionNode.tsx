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
  CheckCircle as CheckCircleIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';

interface ActionNodeData {
  label: string;
  node_type: string;
  position_size?: number;
  max_slippage?: number;
  message?: string;
  priority?: string;
  reason?: string;
  validation_errors?: string[];
}

const ActionNode = React.memo(function ActionNode({ data, selected }: NodeProps<ActionNodeData>) {
  const { label, node_type, position_size, max_slippage, message, priority, reason, validation_errors } = data;

  const getActionColor = (type: string) => {
    switch (type) {
      case 'buy_signal':
        return '#4caf50'; // Green
      case 'sell_signal':
        return '#f44336'; // Red
      case 'alert_action':
        return '#ff9800'; // Orange
      case 'emergency_exit':
        return '#d32f2f'; // Dark red
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
        backgroundColor: '#e8f5e8',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: '#555', width: 8, height: 8 }}
      />

      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <CheckCircleIcon sx={{ mr: 1, color: getActionColor(node_type) }} />
        <Typography variant="subtitle2" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
          {label}
        </Typography>
        <IconButton size="small" sx={{ p: 0.5 }}>
          <SettingsIcon fontSize="small" />
        </IconButton>
      </Box>

      <Box sx={{ mb: 1 }}>
        <Chip
          label={getDisplayType(node_type)}
          size="small"
          sx={{
            backgroundColor: getActionColor(node_type),
            color: 'white',
            fontSize: '0.7rem',
            mb: 0.5
          }}
        />
      </Box>

      <Box sx={{ fontSize: '0.8rem', color: '#666' }}>
        {position_size !== undefined && <div>Position Size: ${position_size}</div>}
        {max_slippage !== undefined && <div>Max Slippage: {max_slippage}</div>}
        {message && <div>Message: {message}</div>}
        {priority && <div>Priority: {priority}</div>}
        {reason && <div>Reason: {reason}</div>}
      </Box>
    </Paper>
  );
});

export default ActionNode;