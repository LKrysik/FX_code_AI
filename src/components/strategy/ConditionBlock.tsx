import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Chip from '@mui/material/Chip';
import Tooltip from '@mui/material/Tooltip';
import { Delete as DeleteIcon, ExpandMore as ExpandMoreIcon, Info as InfoIcon } from '@mui/icons-material';
import { Condition, IndicatorVariant } from '@/types/strategy';

interface ConditionBlockProps {
  condition: Condition;
  index: number;
  availableIndicators: IndicatorVariant[];
  onChange: (condition: Condition) => void;
  onRemove: () => void;
  logicType?: 'AND';
}

export const ConditionBlock = ({
  condition,
  index,
  availableIndicators,
  onChange,
  onRemove,
  logicType = 'AND',
}: ConditionBlockProps) => {
  const [showDetails, setShowDetails] = useState(false);
  const selectedIndicator = availableIndicators.find(ind => ind.id === condition.indicatorId);

  const getFilteredIndicators = () => {
    return availableIndicators;
  };

  const filteredIndicators = getFilteredIndicators();

  const handleIndicatorChange = (indicatorId: string) => {
    const indicator = availableIndicators.find(ind => ind.id === indicatorId);
    if (indicator) {
      onChange({
        ...condition,
        indicatorId,
      });
    }
  };

  const handleOperatorChange = (operator: string) => {
    onChange({
      ...condition,
      operator: operator as Condition['operator'],
    });
  };

  const handleValueChange = (value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      onChange({
        ...condition,
        value: numValue,
      });
    }
  };

  const generateDescription = () => {
    if (!selectedIndicator) return 'Select an indicator';

    const indicatorName = selectedIndicator.name;
    const operatorText = {
      '>': 'greater than',
      '<': 'less than',
      '>=': 'greater than or equal to',
      '<=': 'less than or equal to',
      '==': 'equal to',
    }[condition.operator] || condition.operator;

    return `${indicatorName} must be ${operatorText} ${condition.value}`;
  };

  return (
    <Paper
      elevation={1}
      sx={{
        p: 2,
        mb: 2,
        border: '1px solid',
        borderColor: 'divider',
        position: 'relative',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
          Condition {index + 1}
        </Typography>
        <Chip
          label={logicType}
          size="small"
          color={logicType === 'AND' ? 'primary' : 'secondary'}
          variant="outlined"
        />
        <IconButton
          size="small"
          onClick={onRemove}
          sx={{ ml: 1 }}
          color="error"
        >
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Box>

      <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Select Indicator</InputLabel>
          <Select
            value={condition.indicatorId || ''}
            label="Select Indicator"
            onChange={(e) => handleIndicatorChange(e.target.value)}
          >
            {filteredIndicators.map((indicator) => (
              <MenuItem key={indicator.id} value={indicator.id}>
                <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="body2">{indicator.name}</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        {indicator.baseType} • {indicator.type}
                      </Typography>
                      {Object.keys(indicator.parameters).length > 0 && (
                        <Tooltip title={`Parameters: ${Object.entries(indicator.parameters).map(([k, v]) => `${k}=${v}`).join(', ')}`}>
                          <InfoIcon fontSize="small" color="action" sx={{ fontSize: 14 }} />
                        </Tooltip>
                      )}
                    </Box>
                  </Box>
                  <Chip
                    label={indicator.type}
                    size="small"
                    color={
                      indicator.type === 'risk' ? 'error' :
                      indicator.type === 'price' ? 'success' :
                      indicator.type === 'stop_loss' ? 'warning' :
                      indicator.type === 'take_profit' ? 'info' :
                      'default'
                    }
                    variant="outlined"
                    sx={{ ml: 1, fontSize: '0.7rem', height: 20 }}
                  />
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Operator</InputLabel>
          <Select
            value={condition.operator || ''}
            label="Operator"
            onChange={(e) => handleOperatorChange(e.target.value)}
            disabled={!condition.indicatorId}
          >
            <MenuItem value=">">{'>'}</MenuItem>
            <MenuItem value="<">{'<'}</MenuItem>
            <MenuItem value=">=">{'>='}</MenuItem>
            <MenuItem value="<=">{'<='}</MenuItem>
          </Select>
        </FormControl>

        <TextField
          label="Value"
          type="number"
          size="small"
          value={condition.value || ''}
          onChange={(e) => handleValueChange(e.target.value)}
          disabled={!condition.indicatorId}
          sx={{ minWidth: 100 }}
        />
      </Box>

      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ mt: 1, fontStyle: 'italic' }}
      >
        {generateDescription()}
      </Typography>

      {selectedIndicator && (
        <Box sx={{ mt: 1 }}>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Current: {selectedIndicator.lastValue ?? 'N/A'}
            </Typography>
            {selectedIndicator.lastUpdate && (
              <Typography variant="caption" color="text.secondary">
                • Updated: {new Date(selectedIndicator.lastUpdate).toLocaleTimeString()}
              </Typography>
            )}
            <IconButton
              size="small"
              onClick={() => setShowDetails(!showDetails)}
              sx={{ ml: 'auto', p: 0.5 }}
            >
              <ExpandMoreIcon
                sx={{
                  transform: showDetails ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s'
                }}
              />
            </IconButton>
          </Box>

          {showDetails && (
            <Box sx={{ mt: 1, p: 1, bgcolor: 'grey.50', borderRadius: 1 }}>
              <Typography variant="caption" fontWeight="bold" color="text.secondary">
                Variant Details
              </Typography>
              <Box sx={{ mt: 0.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Base Indicator: {selectedIndicator.baseType}
                </Typography>
              </Box>
              {Object.keys(selectedIndicator.parameters).length > 0 && (
                <Box sx={{ mt: 0.5 }}>
                  <Typography variant="caption" color="text.secondary">
                    Parameters:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                    {Object.entries(selectedIndicator.parameters).map(([key, value]) => (
                      <Chip
                        key={key}
                        label={`${key}=${value}`}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: '0.7rem', height: 20 }}
                      />
                    ))}
                  </Box>
                </Box>
              )}
              {selectedIndicator.description && (
                <Box sx={{ mt: 0.5 }}>
                  <Typography variant="caption" color="text.secondary">
                    {selectedIndicator.description}
                  </Typography>
                </Box>
              )}
            </Box>
          )}
        </Box>
      )}
    </Paper>
  );
};