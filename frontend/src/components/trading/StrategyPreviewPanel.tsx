'use client';

/**
 * StrategyPreviewPanel Component (TS-01)
 * ======================================
 *
 * Shows strategy conditions (S1, Z1, ZE1, E1) when a strategy is selected.
 * Helps trader understand what conditions trigger each state transition.
 *
 * Features:
 * - S1 (Signal Detection) conditions display
 * - O1 (Signal Cancellation) conditions display
 * - Z1 (Entry Conditions) display
 * - ZE1 (Close Order) conditions display
 * - E1 (Emergency Exit) conditions display
 * - Color-coded sections matching state machine design
 * - Expandable/collapsible sections
 *
 * Related: docs/UI_BACKLOG.md - TS-01
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Skeleton,
  Alert,
  Tooltip,
  alpha,
  Divider,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  TrendingUp as TrendingUpIcon,
  Block as BlockIcon,
  Login as LoginIcon,
  Logout as LogoutIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';

// ============================================================================
// Types
// ============================================================================

export interface ConditionDefinition {
  condition_type: string;
  operator: string;
  value: number | [number, number];
  enabled: boolean;
  name?: string;
  description?: string;
}

export interface ConditionGroupDefinition {
  require_all: boolean;
  conditions: ConditionDefinition[];
}

export interface StrategyDefinition {
  strategy_name: string;
  description?: string;
  enabled: boolean;
  signal_detection?: ConditionGroupDefinition;
  signal_cancellation?: ConditionGroupDefinition;
  entry_conditions?: ConditionGroupDefinition;
  close_order_detection?: ConditionGroupDefinition;
  emergency_exit?: ConditionGroupDefinition;
}

export interface StrategyPreviewPanelProps {
  strategyName: string | null;
  onClose?: () => void;
}

// ============================================================================
// Section Configuration
// ============================================================================

interface SectionConfig {
  id: string;
  title: string;
  shortTitle: string;
  icon: React.ReactNode;
  color: string;
  description: string;
  field: keyof StrategyDefinition;
}

const SECTIONS: SectionConfig[] = [
  {
    id: 'S1',
    title: 'S1 - Signal Detection (Pump Detection)',
    shortTitle: 'S1',
    icon: <TrendingUpIcon />,
    color: '#ff9800',
    description: 'Conditions that detect a pump event and trigger entry evaluation',
    field: 'signal_detection',
  },
  {
    id: 'O1',
    title: 'O1 - Signal Cancellation',
    shortTitle: 'O1',
    icon: <BlockIcon />,
    color: '#9e9e9e',
    description: 'Conditions that cancel a detected signal (false positive protection)',
    field: 'signal_cancellation',
  },
  {
    id: 'Z1',
    title: 'Z1 - Entry Conditions (Peak Detection)',
    shortTitle: 'Z1',
    icon: <LoginIcon />,
    color: '#4caf50',
    description: 'Conditions that confirm peak and trigger SHORT entry',
    field: 'entry_conditions',
  },
  {
    id: 'ZE1',
    title: 'ZE1 - Close Order (Dump End Detection)',
    shortTitle: 'ZE1',
    icon: <LogoutIcon />,
    color: '#2196f3',
    description: 'Conditions to close position (take profit on dump)',
    field: 'close_order_detection',
  },
  {
    id: 'E1',
    title: 'E1 - Emergency Exit',
    shortTitle: 'E1',
    icon: <WarningIcon />,
    color: '#f44336',
    description: 'Emergency conditions to exit if pump continues',
    field: 'emergency_exit',
  },
];

// ============================================================================
// Helper Functions
// ============================================================================

function formatOperator(operator: string): string {
  const map: Record<string, string> = {
    gte: '>=',
    '>=': '>=',
    lte: '<=',
    '<=': '<=',
    gt: '>',
    '>': '>',
    lt: '<',
    '<': '<',
    eq: '==',
    '==': '==',
    '=': '==',
    neq: '!=',
    '!=': '!=',
    between: 'between',
  };
  return map[operator?.toLowerCase()] || operator;
}

function formatValue(value: number | [number, number]): string {
  if (Array.isArray(value)) {
    return `${value[0]} - ${value[1]}`;
  }
  return value.toString();
}

// ============================================================================
// Condition List Component
// ============================================================================

interface ConditionListProps {
  group: ConditionGroupDefinition | undefined;
  sectionColor: string;
}

const ConditionList: React.FC<ConditionListProps> = ({ group, sectionColor }) => {
  if (!group || !group.conditions || group.conditions.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
        No conditions configured
      </Typography>
    );
  }

  const enabledConditions = group.conditions.filter((c) => c.enabled !== false);

  return (
    <Box>
      <Box sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Chip
          label={group.require_all ? 'ALL must be TRUE (AND)' : 'ANY must be TRUE (OR)'}
          size="small"
          sx={{
            bgcolor: alpha(sectionColor, 0.1),
            color: sectionColor,
            fontWeight: 'bold',
          }}
        />
        <Typography variant="caption" color="text.secondary">
          {enabledConditions.length} condition{enabledConditions.length !== 1 ? 's' : ''}
        </Typography>
      </Box>

      <List dense disablePadding>
        {enabledConditions.map((condition, index) => (
          <ListItem
            key={`${condition.condition_type}-${index}`}
            sx={{
              bgcolor: alpha(sectionColor, 0.05),
              borderRadius: 1,
              mb: 0.5,
              border: '1px solid',
              borderColor: alpha(sectionColor, 0.2),
            }}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>
              <CheckCircleIcon sx={{ fontSize: 18, color: sectionColor }} />
            </ListItemIcon>
            <ListItemText
              primary={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography
                    variant="body2"
                    fontWeight="bold"
                    sx={{ fontFamily: 'monospace', color: sectionColor }}
                  >
                    {condition.name || condition.condition_type}
                  </Typography>
                  <Chip
                    label={`${formatOperator(condition.operator)} ${formatValue(condition.value)}`}
                    size="small"
                    sx={{
                      bgcolor: alpha(sectionColor, 0.15),
                      color: sectionColor,
                      fontFamily: 'monospace',
                      fontSize: '0.75rem',
                    }}
                  />
                </Box>
              }
              secondary={
                condition.description && (
                  <Typography variant="caption" color="text.secondary">
                    {condition.description}
                  </Typography>
                )
              }
            />
          </ListItem>
        ))}

        {/* Show disabled conditions if any */}
        {group.conditions.filter((c) => c.enabled === false).length > 0 && (
          <Typography variant="caption" color="text.secondary" sx={{ ml: 1, mt: 1, display: 'block' }}>
            + {group.conditions.filter((c) => c.enabled === false).length} disabled condition(s)
          </Typography>
        )}
      </List>
    </Box>
  );
};

// ============================================================================
// Main Component
// ============================================================================

const StrategyPreviewPanel: React.FC<StrategyPreviewPanelProps> = ({
  strategyName,
}) => {
  // ========================================
  // State
  // ========================================

  const [strategy, setStrategy] = useState<StrategyDefinition | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | false>('S1');

  // ========================================
  // API Fetch
  // ========================================

  const fetchStrategy = useCallback(async () => {
    if (!strategyName) {
      setStrategy(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const response = await fetch(`${apiUrl}/api/strategies/${encodeURIComponent(strategyName)}`);

      if (!response.ok) {
        // Try the 4-section strategies endpoint as fallback
        const fallbackResponse = await fetch(`${apiUrl}/api/4section-strategies`);
        if (fallbackResponse.ok) {
          const result = await fallbackResponse.json();
          const strategies = result.data?.strategies || result.strategies || [];
          const found = strategies.find((s: StrategyDefinition) => s.strategy_name === strategyName);
          if (found) {
            setStrategy(found);
            return;
          }
        }
        throw new Error(`Strategy not found: ${strategyName}`);
      }

      const result = await response.json();
      const data = result.data || result;
      setStrategy(data);
    } catch (err) {
      console.error('[StrategyPreviewPanel] Fetch error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load strategy');
    } finally {
      setIsLoading(false);
    }
  }, [strategyName]);

  // ========================================
  // Effects
  // ========================================

  useEffect(() => {
    fetchStrategy();
  }, [fetchStrategy]);

  // ========================================
  // Handlers
  // ========================================

  const handleAccordionChange = (panel: string) => (_event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedSection(isExpanded ? panel : false);
  };

  // ========================================
  // Render
  // ========================================

  if (!strategyName) {
    return (
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <SettingsIcon color="primary" />
          <Typography variant="h6" fontWeight="bold">
            Strategy Preview
          </Typography>
        </Box>
        <Alert severity="info">
          Select a strategy to see its S1, Z1, ZE1, E1 conditions
        </Alert>
      </Paper>
    );
  }

  if (isLoading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <SettingsIcon color="primary" />
          <Typography variant="h6" fontWeight="bold">
            Strategy Preview
          </Typography>
        </Box>
        <Skeleton variant="text" width="60%" height={30} />
        <Skeleton variant="rectangular" height={100} sx={{ mt: 2, borderRadius: 1 }} />
        <Skeleton variant="rectangular" height={100} sx={{ mt: 1, borderRadius: 1 }} />
        <Skeleton variant="rectangular" height={100} sx={{ mt: 1, borderRadius: 1 }} />
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <SettingsIcon color="primary" />
          <Typography variant="h6" fontWeight="bold">
            Strategy Preview
          </Typography>
        </Box>
        <Alert severity="error">{error}</Alert>
      </Paper>
    );
  }

  if (!strategy) {
    return null;
  }

  return (
    <Paper sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SettingsIcon color="primary" />
          <Typography variant="h6" fontWeight="bold">
            Strategy Preview
          </Typography>
        </Box>
        <Chip
          label={strategy.enabled ? 'ENABLED' : 'DISABLED'}
          color={strategy.enabled ? 'success' : 'default'}
          size="small"
        />
      </Box>

      {/* Strategy Name & Description */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" fontWeight="bold" color="primary">
          {strategy.strategy_name}
        </Typography>
        {strategy.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {strategy.description}
          </Typography>
        )}
      </Box>

      <Divider sx={{ mb: 2 }} />

      {/* Condition Sections */}
      {SECTIONS.map((section) => {
        const group = strategy[section.field] as ConditionGroupDefinition | undefined;
        const conditionCount = group?.conditions?.filter((c) => c.enabled !== false).length || 0;

        return (
          <Accordion
            key={section.id}
            expanded={expandedSection === section.id}
            onChange={handleAccordionChange(section.id)}
            sx={{
              mb: 1,
              border: '2px solid',
              borderColor: expandedSection === section.id ? section.color : alpha(section.color, 0.3),
              borderRadius: '8px !important',
              bgcolor: alpha(section.color, 0.03),
              '&:before': { display: 'none' },
              '&.Mui-expanded': {
                boxShadow: `0 0 10px ${alpha(section.color, 0.2)}`,
              },
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon sx={{ color: section.color }} />}
              sx={{
                bgcolor: alpha(section.color, 0.05),
                '&:hover': {
                  bgcolor: alpha(section.color, 0.1),
                },
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                <Box sx={{ color: section.color }}>{section.icon}</Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle1" fontWeight="bold" sx={{ color: section.color }}>
                    {section.title}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {section.description}
                  </Typography>
                </Box>
                <Chip
                  label={`${conditionCount} condition${conditionCount !== 1 ? 's' : ''}`}
                  size="small"
                  sx={{
                    bgcolor: alpha(section.color, 0.15),
                    color: section.color,
                    fontWeight: 'bold',
                  }}
                />
              </Box>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 2 }}>
              <ConditionList group={group} sectionColor={section.color} />
            </AccordionDetails>
          </Accordion>
        );
      })}

      {/* State Machine Flow Summary */}
      <Box sx={{ mt: 3, p: 2, bgcolor: alpha('#9e9e9e', 0.1), borderRadius: 2 }}>
        <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
          State Machine Flow:
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
          <Chip label="MONITORING" size="small" sx={{ bgcolor: '#9e9e9e', color: 'white' }} />
          <Typography color="text.secondary">--S1--&gt;</Typography>
          <Chip label="SIGNAL_DETECTED" size="small" sx={{ bgcolor: '#ff9800', color: 'white' }} />
          <Typography color="text.secondary">--Z1--&gt;</Typography>
          <Chip label="POSITION_ACTIVE" size="small" sx={{ bgcolor: '#4caf50', color: 'white' }} />
          <Typography color="text.secondary">--ZE1/E1--&gt;</Typography>
          <Chip label="EXITED" size="small" sx={{ bgcolor: '#2196f3', color: 'white' }} />
        </Box>
      </Box>
    </Paper>
  );
};

export default StrategyPreviewPanel;
