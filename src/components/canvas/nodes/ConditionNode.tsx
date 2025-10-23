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
  CompareArrows as CompareArrowsIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';

interface ConditionNodeData {
  label: string;
  node_type: string;
  operator?: string;
  threshold?: number;
  duration_seconds?: number;
  reset_on_false?: boolean;
  sequence_length?: number;
  max_gap_seconds?: number;
  validation_errors?: string[];
}

const ConditionNode = React.memo(function ConditionNode({ data, selected }: NodeProps<ConditionNodeData>) {
  const { label, node_type, operator, threshold, duration_seconds, reset_on_false, sequence_length, max_gap_seconds, validation_errors } = data;

  const getConditionColor = (type: string) => {
    switch (type) {
      case 'threshold_condition':
        return '#ff9800'; // Orange
      case 'duration_condition':
        return '#2196f3'; // Blue
      case 'sequence_condition':
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
        backgroundColor: '#fff3e0',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: '#555', width: 8, height: 8 }}
      />

      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <CompareArrowsIcon sx={{ mr: 1, color: getConditionColor(node_type) }} />
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
            backgroundColor: getConditionColor(node_type),
            color: 'white',
            fontSize: '0.7rem',
            mb: 0.5
          }}
        />
      </Box>

      <Box sx={{ fontSize: '0.8rem', color: '#666', mb: 1 }}>
        {operator && <div>Operator: {operator}</div>}
        {threshold !== undefined && <div>Threshold: {threshold}</div>}
        {duration_seconds && <div>Duration: {duration_seconds}s</div>}
        {reset_on_false !== undefined && <div>Reset on False: {reset_on_false ? 'Yes' : 'No'}</div>}
        {sequence_length && <div>Sequence Length: {sequence_length}</div>}
        {max_gap_seconds && <div>Max Gap: {max_gap_seconds}s</div>}
      </Box>

      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: getConditionColor(node_type),
          width: 8,
          height: 8
        }}
      />
    </Paper>
  );
});

export default ConditionNode;