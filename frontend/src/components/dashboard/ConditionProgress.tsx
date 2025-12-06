'use client';

/**
 * ConditionProgress Component (SM-03)
 * ====================================
 *
 * Panel showing which conditions (S1/O1/Z1/ZE1/E1) are met and which are pending.
 *
 * Features:
 * - Accordion/Card view for each section (S1, O1, Z1, ZE1, E1)
 * - Visual indicators: checkmark (met) / X (not met)
 * - Progress bars for numeric conditions (current_value vs threshold)
 * - Section highlighting based on current state machine state
 * - Loading skeleton for async data
 * - Color-coded sections (S1=orange, O1=gray, Z1=green, ZE1=blue, E1=red)
 *
 * Related: docs/frontend/TARGET_STATE_TRADING_INTERFACE.md
 */

import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  LinearProgress,
  Skeleton,
  Alert,
  Tooltip,
  alpha,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface Condition {
  indicator_name: string; // e.g., "PUMP_MAGNITUDE_PCT"
  operator: '>' | '<' | '>=' | '<=' | '==' | '!=';
  threshold: number;
  current_value: number;
  met: boolean;
}

export interface ConditionGroup {
  section: 'S1' | 'O1' | 'Z1' | 'ZE1' | 'E1';
  label: string; // e.g., "Pump Detection", "Peak Entry"
  logic: 'AND' | 'OR';
  conditions: Condition[];
  all_met: boolean;
}

export interface ConditionProgressProps {
  groups: ConditionGroup[];
  currentState: string; // current state machine state
  isLoading?: boolean;
}

// ============================================================================
// Section Configuration (Colors & Mapping)
// ============================================================================

interface SectionConfig {
  color: string;
  bgColor: string;
  borderColor: string;
  associatedStates: string[]; // States where this section is "active"
}

const SECTION_CONFIG: Record<ConditionGroup['section'], SectionConfig> = {
  S1: {
    color: '#ff9800', // orange
    bgColor: alpha('#ff9800', 0.1),
    borderColor: alpha('#ff9800', 0.3),
    associatedStates: ['MONITORING', 'SIGNAL_DETECTED'],
  },
  O1: {
    color: '#9e9e9e', // gray
    bgColor: alpha('#9e9e9e', 0.1),
    borderColor: alpha('#9e9e9e', 0.3),
    associatedStates: ['SIGNAL_DETECTED'], // Cancel conditions
  },
  Z1: {
    color: '#4caf50', // green
    bgColor: alpha('#4caf50', 0.1),
    borderColor: alpha('#4caf50', 0.3),
    associatedStates: ['SIGNAL_DETECTED', 'POSITION_ACTIVE'],
  },
  ZE1: {
    color: '#2196f3', // blue
    bgColor: alpha('#2196f3', 0.1),
    borderColor: alpha('#2196f3', 0.3),
    associatedStates: ['POSITION_ACTIVE', 'EXITED'],
  },
  E1: {
    color: '#f44336', // red
    bgColor: alpha('#f44336', 0.1),
    borderColor: alpha('#f44336', 0.3),
    associatedStates: ['POSITION_ACTIVE', 'ERROR'],
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format operator symbol for display
 */
function formatOperator(operator: Condition['operator']): string {
  const map: Record<Condition['operator'], string> = {
    '>': '>',
    '<': '<',
    '>=': '≥',
    '<=': '≤',
    '==': '=',
    '!=': '≠',
  };
  return map[operator] || operator;
}

/**
 * Format numeric value with appropriate decimals
 */
function formatValue(value: number): string {
  if (Math.abs(value) >= 1000) {
    return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
  }
  if (Math.abs(value) >= 1) {
    return value.toFixed(2);
  }
  return value.toFixed(4);
}

/**
 * Calculate progress percentage for visual bar
 * Returns percentage (0-100) of current_value relative to threshold
 */
function calculateProgress(condition: Condition): number {
  const { current_value, threshold, operator } = condition;

  if (threshold === 0) return 0;

  // For > or >=, show progress toward threshold
  if (operator === '>' || operator === '>=') {
    const progress = (current_value / threshold) * 100;
    return Math.min(progress, 200); // Cap at 200% for visual purposes
  }

  // For < or <=, show progress toward threshold (inverse)
  if (operator === '<' || operator === '<=') {
    const progress = ((threshold - current_value) / threshold) * 100;
    return Math.max(progress, 0);
  }

  // For == or !=, show binary result
  return condition.met ? 100 : 0;
}

// ============================================================================
// Sub-Components
// ============================================================================

/**
 * Render a single condition row with progress bar
 */
const ConditionRow: React.FC<{ condition: Condition; sectionColor: string }> = ({
  condition,
  sectionColor,
}) => {
  const progress = calculateProgress(condition);
  const isMetColor = condition.met ? '#4caf50' : '#f44336';

  return (
    <Box sx={{ mb: 2, pb: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        {/* Left: Condition description */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
          {condition.met ? (
            <CheckCircleIcon fontSize="small" sx={{ color: '#4caf50' }} />
          ) : (
            <CancelIcon fontSize="small" sx={{ color: '#f44336' }} />
          )}

          <Tooltip
            title={`Current: ${formatValue(condition.current_value)} | Threshold: ${formatValue(
              condition.threshold
            )}`}
            arrow
          >
            <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
              {condition.indicator_name} {formatOperator(condition.operator)}{' '}
              {formatValue(condition.threshold)}%
            </Typography>
          </Tooltip>
        </Box>

        {/* Right: Current value badge */}
        <Chip
          label={`${formatValue(condition.current_value)}%`}
          size="small"
          sx={{
            bgcolor: alpha(isMetColor, 0.15),
            color: isMetColor,
            fontWeight: 'bold',
            border: '1px solid',
            borderColor: isMetColor,
          }}
        />
      </Box>

      {/* Progress bar for numeric thresholds */}
      {(condition.operator === '>' ||
        condition.operator === '>=' ||
        condition.operator === '<' ||
        condition.operator === '<=') && (
        <LinearProgress
          variant="determinate"
          value={Math.min(progress, 100)}
          sx={{
            height: 6,
            borderRadius: 3,
            bgcolor: alpha(sectionColor, 0.1),
            '& .MuiLinearProgress-bar': {
              bgcolor: condition.met ? '#4caf50' : sectionColor,
            },
          }}
        />
      )}
    </Box>
  );
};

/**
 * Loading skeleton for condition group
 */
const ConditionGroupSkeleton: React.FC = () => (
  <Box sx={{ p: 2 }}>
    <Skeleton variant="text" width="60%" height={24} sx={{ mb: 2 }} />
    <Skeleton variant="rectangular" width="100%" height={50} sx={{ mb: 1, borderRadius: 1 }} />
    <Skeleton variant="rectangular" width="100%" height={50} sx={{ mb: 1, borderRadius: 1 }} />
    <Skeleton variant="rectangular" width="100%" height={50} sx={{ borderRadius: 1 }} />
  </Box>
);

// ============================================================================
// Main Component
// ============================================================================

const ConditionProgress: React.FC<ConditionProgressProps> = ({
  groups,
  currentState,
  isLoading = false,
}) => {
  // ========================================
  // Render Helpers
  // ========================================

  const isActiveSection = (section: ConditionGroup['section']): boolean => {
    const config = SECTION_CONFIG[section];
    return config.associatedStates.includes(currentState);
  };

  const renderGroupHeader = (group: ConditionGroup) => {
    const config = SECTION_CONFIG[group.section];
    const metCount = group.conditions.filter((c) => c.met).length;
    const totalCount = group.conditions.length;
    const isActive = isActiveSection(group.section);

    return (
      <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', gap: 2 }}>
        {/* Section Icon + Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
          <TrendingUpIcon sx={{ color: config.color }} />
          <Typography variant="subtitle1" fontWeight="bold" sx={{ color: config.color }}>
            {group.section}: {group.label}
          </Typography>
        </Box>

        {/* Badge: Met count */}
        <Chip
          label={`${metCount}/${totalCount}`}
          size="small"
          sx={{
            bgcolor: group.all_met ? alpha('#4caf50', 0.15) : alpha('#f44336', 0.15),
            color: group.all_met ? '#4caf50' : '#f44336',
            fontWeight: 'bold',
            border: '1px solid',
            borderColor: group.all_met ? '#4caf50' : '#f44336',
          }}
        />

        {/* Status Icon */}
        {group.all_met ? (
          <CheckCircleIcon fontSize="medium" sx={{ color: '#4caf50' }} />
        ) : (
          <CancelIcon fontSize="medium" sx={{ color: '#f44336' }} />
        )}

        {/* Active Indicator */}
        {isActive && (
          <Chip
            label="ACTIVE"
            size="small"
            sx={{
              bgcolor: alpha(config.color, 0.2),
              color: config.color,
              fontWeight: 'bold',
              animation: 'pulse 2s ease-in-out infinite',
              '@keyframes pulse': {
                '0%, 100%': { opacity: 1 },
                '50%': { opacity: 0.6 },
              },
            }}
          />
        )}
      </Box>
    );
  };

  const renderGroup = (group: ConditionGroup) => {
    const config = SECTION_CONFIG[group.section];
    const isActive = isActiveSection(group.section);

    return (
      <Accordion
        key={group.section}
        defaultExpanded={isActive}
        sx={{
          mb: 2,
          border: '2px solid',
          borderColor: isActive ? config.color : config.borderColor,
          borderRadius: 2,
          bgcolor: config.bgColor,
          boxShadow: isActive ? `0 0 12px ${alpha(config.color, 0.3)}` : 'none',
          '&:before': {
            display: 'none', // Remove default MUI divider
          },
        }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon sx={{ color: config.color }} />}
          sx={{
            bgcolor: alpha(config.color, 0.05),
            '&:hover': {
              bgcolor: alpha(config.color, 0.1),
            },
          }}
        >
          {renderGroupHeader(group)}
        </AccordionSummary>

        <AccordionDetails sx={{ pt: 2 }}>
          {/* Logic Info */}
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="caption">
              Logic: <strong>{group.logic}</strong> - All conditions must{' '}
              {group.logic === 'AND' ? 'be TRUE' : 'have at least one TRUE'}
            </Typography>
          </Alert>

          {/* Conditions List */}
          {group.conditions.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No conditions defined
            </Typography>
          ) : (
            group.conditions.map((condition, idx) => (
              <ConditionRow
                key={`${group.section}-${idx}`}
                condition={condition}
                sectionColor={config.color}
              />
            ))
          )}
        </AccordionDetails>
      </Accordion>
    );
  };

  // ========================================
  // Render
  // ========================================

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight="bold">
          Condition Progress
        </Typography>

        <Chip
          label={currentState}
          size="small"
          color="primary"
          variant="outlined"
          sx={{ fontWeight: 'bold' }}
        />
      </Box>

      {isLoading ? (
        <>
          <ConditionGroupSkeleton />
          <ConditionGroupSkeleton />
          <ConditionGroupSkeleton />
        </>
      ) : groups.length === 0 ? (
        <Alert severity="info">
          <Typography variant="body2">No conditions configured for this session</Typography>
        </Alert>
      ) : (
        <Box sx={{ maxHeight: '700px', overflowY: 'auto', pr: 1 }}>
          {groups.map((group) => renderGroup(group))}
        </Box>
      )}
    </Paper>
  );
};

export default ConditionProgress;
