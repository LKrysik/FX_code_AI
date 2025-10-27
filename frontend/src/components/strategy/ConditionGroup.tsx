import React from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import { Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import { ConditionBlock } from './ConditionBlock';
import { Condition, ConditionGroup as ConditionGroupType, IndicatorVariant, LogicOperator } from '@/types/strategy';
import { v4 as uuidv4 } from 'uuid';

interface ConditionGroupProps {
  group: ConditionGroupType;
  availableIndicators: IndicatorVariant[];
  onChange: (group: ConditionGroupType) => void;
  onRemove?: () => void;
  depth?: number;  // Track nesting depth to prevent infinite recursion
  maxDepth?: number;  // Maximum nesting level allowed
}

/**
 * ConditionGroup Component - Phase 2 Sprint 1
 *
 * Allows grouping conditions with AND/OR logic.
 * Supports nested groups for complex expressions like: (A AND B) OR (C AND D)
 *
 * Example:
 *   Group 1 (OR):
 *     - RSI < 30
 *     - RSI > 70
 *   Group 2 (AND):
 *     - Price > EMA
 *     - Volume > 1000000
 *
 * Result: (RSI < 30 OR RSI > 70) AND (Price > EMA AND Volume > 1000000)
 */
export const ConditionGroup: React.FC<ConditionGroupProps> = ({
  group,
  availableIndicators,
  onChange,
  onRemove,
  depth = 0,
  maxDepth = 3,
}) => {
  const handleConditionChange = (index: number, updatedCondition: Condition) => {
    const newConditions = [...group.conditions];
    newConditions[index] = updatedCondition;
    onChange({
      ...group,
      conditions: newConditions,
    });
  };

  const handleConditionLogicChange = (index: number, newLogic: LogicOperator) => {
    const newConditions = [...group.conditions];
    newConditions[index] = {
      ...newConditions[index],
      logic: newLogic,
    };
    onChange({
      ...group,
      conditions: newConditions,
    });
  };

  const handleAddCondition = () => {
    const newCondition: Condition = {
      id: uuidv4(),
      indicatorId: '',
      operator: '>',
      value: 0,
      logic: 'AND',
    };
    onChange({
      ...group,
      conditions: [...group.conditions, newCondition],
    });
  };

  const handleRemoveCondition = (index: number) => {
    const newConditions = group.conditions.filter((_, i) => i !== index);
    onChange({
      ...group,
      conditions: newConditions,
    });
  };

  const handleAddNestedGroup = () => {
    if (depth >= maxDepth) {
      alert(`Maximum nesting depth (${maxDepth}) reached`);
      return;
    }

    const newGroup: ConditionGroupType = {
      id: uuidv4(),
      logic: 'AND',
      conditions: [
        {
          id: uuidv4(),
          indicatorId: '',
          operator: '>',
          value: 0,
          logic: 'AND',
        },
      ],
    };

    onChange({
      ...group,
      groups: [...(group.groups || []), newGroup],
    });
  };

  const handleNestedGroupChange = (index: number, updatedGroup: ConditionGroupType) => {
    const newGroups = [...(group.groups || [])];
    newGroups[index] = updatedGroup;
    onChange({
      ...group,
      groups: newGroups,
    });
  };

  const handleRemoveNestedGroup = (index: number) => {
    const newGroups = (group.groups || []).filter((_, i) => i !== index);
    onChange({
      ...group,
      groups: newGroups,
    });
  };

  const handleGroupLogicChange = (newLogic: 'AND' | 'OR') => {
    onChange({
      ...group,
      logic: newLogic,
    });
  };

  const getGroupColor = () => {
    const colors = [
      'rgba(25, 118, 210, 0.08)',   // Blue - depth 0
      'rgba(76, 175, 80, 0.08)',    // Green - depth 1
      'rgba(255, 152, 0, 0.08)',    // Orange - depth 2
      'rgba(156, 39, 176, 0.08)',   // Purple - depth 3
    ];
    return colors[depth % colors.length];
  };

  const getBorderColor = () => {
    const colors = [
      'rgba(25, 118, 210, 0.3)',
      'rgba(76, 175, 80, 0.3)',
      'rgba(255, 152, 0, 0.3)',
      'rgba(156, 39, 176, 0.3)',
    ];
    return colors[depth % colors.length];
  };

  return (
    <Paper
      elevation={depth + 1}
      sx={{
        p: 2,
        mb: 2,
        bgcolor: getGroupColor(),
        border: '2px solid',
        borderColor: getBorderColor(),
        borderRadius: 2,
        position: 'relative',
      }}
    >
      {/* Group Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Typography variant="subtitle1" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
          Group {depth === 0 ? '(Root)' : `Level ${depth}`}
        </Typography>

        {/* Group Logic Selector */}
        <Box sx={{ display: 'flex', gap: 1, mr: 1 }}>
          <Chip
            label="AND"
            size="small"
            color={group.logic === 'AND' ? 'primary' : 'default'}
            onClick={() => handleGroupLogicChange('AND')}
            variant={group.logic === 'AND' ? 'filled' : 'outlined'}
            sx={{ cursor: 'pointer' }}
          />
          <Chip
            label="OR"
            size="small"
            color={group.logic === 'OR' ? 'success' : 'default'}
            onClick={() => handleGroupLogicChange('OR')}
            variant={group.logic === 'OR' ? 'filled' : 'outlined'}
            sx={{ cursor: 'pointer' }}
          />
        </Box>

        {/* Remove Group Button (not shown for root group) */}
        {onRemove && (
          <IconButton size="small" onClick={onRemove} color="error">
            <DeleteIcon fontSize="small" />
          </IconButton>
        )}
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
        All conditions below must evaluate to {group.logic === 'AND' ? 'TRUE' : 'at least one TRUE'}
      </Typography>

      <Divider sx={{ mb: 2 }} />

      {/* Conditions in this group */}
      {group.conditions.map((condition, index) => (
        <Box key={condition.id} sx={{ mb: 1 }}>
          <ConditionBlock
            condition={condition}
            index={index}
            availableIndicators={availableIndicators}
            onChange={(updated) => handleConditionChange(index, updated)}
            onRemove={() => handleRemoveCondition(index)}
            logicType={condition.logic || 'AND'}
            onLogicChange={(newLogic) => handleConditionLogicChange(index, newLogic)}
            isLastCondition={index === group.conditions.length - 1 && (!group.groups || group.groups.length === 0)}
          />

          {/* Show logic connector between conditions */}
          {index < group.conditions.length - 1 && (
            <Box sx={{ textAlign: 'center', my: 1 }}>
              <Chip
                label={condition.logic || 'AND'}
                size="small"
                color={condition.logic === 'OR' ? 'success' : condition.logic === 'NOT' ? 'error' : 'primary'}
              />
            </Box>
          )}
        </Box>
      ))}

      {/* Nested Groups */}
      {group.groups && group.groups.length > 0 && (
        <Box sx={{ mt: 2 }}>
          {group.groups.map((nestedGroup, index) => (
            <Box key={nestedGroup.id} sx={{ mb: 2 }}>
              {(group.conditions.length > 0 || index > 0) && (
                <Box sx={{ textAlign: 'center', my: 2 }}>
                  <Chip
                    label={group.logic}
                    size="medium"
                    color={group.logic === 'OR' ? 'success' : 'primary'}
                    sx={{ fontWeight: 'bold' }}
                  />
                </Box>
              )}
              <ConditionGroup
                group={nestedGroup}
                availableIndicators={availableIndicators}
                onChange={(updated) => handleNestedGroupChange(index, updated)}
                onRemove={() => handleRemoveNestedGroup(index)}
                depth={depth + 1}
                maxDepth={maxDepth}
              />
            </Box>
          ))}
        </Box>
      )}

      {/* Action Buttons */}
      <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
        <Button
          size="small"
          startIcon={<AddIcon />}
          onClick={handleAddCondition}
          variant="outlined"
        >
          Add Condition
        </Button>

        {depth < maxDepth && (
          <Button
            size="small"
            startIcon={<AddIcon />}
            onClick={handleAddNestedGroup}
            variant="outlined"
            color="secondary"
          >
            Add Nested Group
          </Button>
        )}
      </Box>

      {/* Depth Indicator */}
      {depth > 0 && (
        <Typography
          variant="caption"
          sx={{
            position: 'absolute',
            top: 8,
            right: onRemove ? 48 : 8,
            opacity: 0.5,
          }}
        >
          Depth: {depth}/{maxDepth}
        </Typography>
      )}
    </Paper>
  );
};
