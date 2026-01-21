'use client';

/**
 * JourneyBar Component
 * ====================
 * Story 1B-5: JourneyBar Component
 *
 * Visual representation of the trading flow cycle:
 * Watch -> Found -> Enter -> Monitor -> Exit
 *
 * AC1: Displays trading flow as connected steps
 * AC2: Each step has icon and label
 * AC3: Current step highlighted based on state machine
 * AC4: Completed steps show checkmarks
 * AC5: Future steps are dimmed/grayed
 * AC6: 300ms smooth animation on state change
 * AC7: Exit step shows profit/loss color (green/red)
 */

import React, { useMemo } from 'react';
import {
  Stepper,
  Step,
  StepLabel,
  StepConnector,
  Box,
  Typography,
  stepConnectorClasses,
  styled,
  alpha,
  useTheme,
} from '@mui/material';
import {
  Visibility,
  MyLocation,
  TrendingUp,
  Bolt,
  ExitToApp,
  Check,
} from '@mui/icons-material';
import type { StateMachineState } from '@/utils/stateVocabulary';

// ============================================================================
// TYPES
// ============================================================================

export interface JourneyBarProps {
  /** Current state machine state */
  currentState: StateMachineState;
  /** Profit/Loss amount for coloring exit step (positive = profit, negative = loss) */
  exitPnL?: number;
  /** Compact mode for smaller displays */
  compact?: boolean;
}

/**
 * Journey step definition
 */
interface JourneyStep {
  id: string;
  label: string;
  icon: React.ReactNode;
  emoji: string;
}

/**
 * Journey step status
 */
type StepStatus = 'completed' | 'current' | 'future';

// ============================================================================
// JOURNEY STEPS DEFINITION
// ============================================================================

const JOURNEY_STEPS: JourneyStep[] = [
  {
    id: 'watch',
    label: 'Watch',
    icon: <Visibility />,
    emoji: '\uD83D\uDC41\uFE0F', // Eye emoji
  },
  {
    id: 'found',
    label: 'Found',
    icon: <MyLocation />,
    emoji: '\uD83C\uDFAF', // Target emoji
  },
  {
    id: 'enter',
    label: 'Enter',
    icon: <TrendingUp />,
    emoji: '\uD83D\uDCC8', // Chart emoji
  },
  {
    id: 'monitor',
    label: 'Monitor',
    icon: <Bolt />,
    emoji: '\u26A1', // Lightning emoji
  },
  {
    id: 'exit',
    label: 'Exit',
    icon: <ExitToApp />,
    emoji: '\uD83D\uDEAA', // Door emoji
  },
];

// ============================================================================
// STATE TO STEP MAPPING
// ============================================================================

/**
 * Maps state machine states to journey step index
 * Story 1B-5 Dev Notes: State Machine to Journey Mapping
 *
 * | State Machine State | Journey Step |
 * |---------------------|--------------|
 * | IDLE, MONITORING, INACTIVE | Watch (0) |
 * | SIGNAL_DETECTED, S1 | Found (1) |
 * | ENTERING, POSITION_OPEN, Z1 | Enter (2) |
 * | POSITION_MONITORING, POSITION_ACTIVE | Monitor (3) |
 * | EXITING, EXITED_PROFIT, EXITED_LOSS, ZE1, E1, EXITED, O1 | Exit (4) |
 */
function getStepIndexFromState(state: StateMachineState): number {
  const stateMap: Record<string, number> = {
    // Watch step (0)
    IDLE: 0,
    MONITORING: 0,
    INACTIVE: 0,

    // Found step (1)
    SIGNAL_DETECTED: 1,
    S1: 1,

    // Enter step (2)
    ENTERING: 2,
    POSITION_OPEN: 2,
    Z1: 2,

    // Monitor step (3)
    POSITION_MONITORING: 3,
    POSITION_ACTIVE: 3,

    // Exit step (4)
    EXITING: 4,
    EXITED_PROFIT: 4,
    EXITED_LOSS: 4,
    ZE1: 4,
    E1: 4,
    EXITED: 4,
    O1: 4, // False alarm also ends the journey

    // Error states default to watch
    ERROR: 0,
  };

  return stateMap[state] ?? 0;
}

/**
 * Determine if exit state is profit or loss
 */
function isExitProfit(state: StateMachineState): boolean | null {
  if (state === 'ZE1' || state === 'EXITED_PROFIT' || state === 'EXITED') {
    return true;
  }
  if (state === 'E1' || state === 'EXITED_LOSS') {
    return false;
  }
  // O1 (false alarm) is neutral
  if (state === 'O1') {
    return null;
  }
  return null;
}

// ============================================================================
// STYLED COMPONENTS
// ============================================================================

/**
 * Custom connector with animation (AC6)
 */
const JourneyConnector = styled(StepConnector)(({ theme }) => ({
  [`&.${stepConnectorClasses.alternativeLabel}`]: {
    top: 22,
  },
  [`&.${stepConnectorClasses.active}`]: {
    [`& .${stepConnectorClasses.line}`]: {
      backgroundImage: `linear-gradient(95deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.light} 100%)`,
    },
  },
  [`&.${stepConnectorClasses.completed}`]: {
    [`& .${stepConnectorClasses.line}`]: {
      backgroundImage: `linear-gradient(95deg, ${theme.palette.success.main} 0%, ${theme.palette.success.light} 100%)`,
    },
  },
  [`& .${stepConnectorClasses.line}`]: {
    height: 3,
    border: 0,
    backgroundColor: theme.palette.mode === 'dark' ? theme.palette.grey[800] : theme.palette.grey[300],
    borderRadius: 1,
    transition: 'all 300ms ease-in-out', // AC6
  },
}));

/**
 * Step icon container with status-based styling
 */
interface StepIconContainerProps {
  status: StepStatus;
  isExitStep: boolean;
  exitProfit: boolean | null;
}

const StepIconContainer = styled(Box, {
  shouldForwardProp: (prop) =>
    prop !== 'status' && prop !== 'isExitStep' && prop !== 'exitProfit',
})<StepIconContainerProps>(({ theme, status, isExitStep, exitProfit }) => {
  // Determine color based on status and exit state
  let backgroundColor: string;
  let borderColor: string;
  let boxShadow: string;

  if (status === 'completed') {
    backgroundColor = theme.palette.success.main;
    borderColor = theme.palette.success.main;
    boxShadow = `0 4px 10px ${alpha(theme.palette.success.main, 0.3)}`;
  } else if (status === 'current') {
    // AC7: Exit step shows profit/loss color
    if (isExitStep && exitProfit !== null) {
      const color = exitProfit ? theme.palette.success.main : theme.palette.error.main;
      backgroundColor = color;
      borderColor = color;
      boxShadow = `0 4px 20px ${alpha(color, 0.5)}`;
    } else {
      backgroundColor = theme.palette.primary.main;
      borderColor = theme.palette.primary.main;
      boxShadow = `0 4px 20px ${alpha(theme.palette.primary.main, 0.5)}`;
    }
  } else {
    // Future step (AC5)
    backgroundColor = theme.palette.mode === 'dark' ? theme.palette.grey[800] : theme.palette.grey[200];
    borderColor = theme.palette.mode === 'dark' ? theme.palette.grey[700] : theme.palette.grey[400];
    boxShadow = 'none';
  }

  return {
    width: 44,
    height: 44,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '50%',
    backgroundColor,
    border: `2px solid ${borderColor}`,
    boxShadow,
    color: status === 'future'
      ? theme.palette.mode === 'dark' ? theme.palette.grey[500] : theme.palette.grey[600]
      : theme.palette.common.white,
    transition: 'all 300ms ease-in-out', // AC6
    '& svg': {
      fontSize: 22,
      transition: 'transform 300ms ease-in-out', // AC6
    },
    // Current step glow effect (AC3)
    ...(status === 'current' && {
      animation: 'pulse 2s ease-in-out infinite',
      '@keyframes pulse': {
        '0%, 100%': {
          boxShadow: boxShadow,
          transform: 'scale(1)',
        },
        '50%': {
          boxShadow: isExitStep && exitProfit !== null
            ? `0 4px 30px ${alpha(exitProfit ? theme.palette.success.main : theme.palette.error.main, 0.7)}`
            : `0 4px 30px ${alpha(theme.palette.primary.main, 0.7)}`,
          transform: 'scale(1.05)',
        },
      },
    }),
  };
});

/**
 * Step label with status-based styling
 */
interface StepLabelTextProps {
  status: StepStatus;
  isExitStep: boolean;
  exitProfit: boolean | null;
}

const StepLabelText = styled(Typography, {
  shouldForwardProp: (prop) =>
    prop !== 'status' && prop !== 'isExitStep' && prop !== 'exitProfit',
})<StepLabelTextProps>(({ theme, status, isExitStep, exitProfit }) => {
  let color: string;
  let fontWeight: number;

  if (status === 'completed') {
    color = theme.palette.success.main;
    fontWeight = 600;
  } else if (status === 'current') {
    // AC7: Exit step shows profit/loss color
    if (isExitStep && exitProfit !== null) {
      color = exitProfit ? theme.palette.success.main : theme.palette.error.main;
    } else {
      color = theme.palette.primary.main;
    }
    fontWeight = 700;
  } else {
    // Future step (AC5)
    color = theme.palette.mode === 'dark' ? theme.palette.grey[500] : theme.palette.grey[600];
    fontWeight = 400;
  }

  return {
    marginTop: theme.spacing(1),
    fontSize: '0.75rem',
    color,
    fontWeight,
    textAlign: 'center',
    transition: 'all 300ms ease-in-out', // AC6
  };
});

// ============================================================================
// STEP ICON COMPONENT
// ============================================================================

interface JourneyStepIconProps {
  step: JourneyStep;
  stepIndex: number;
  currentStepIndex: number;
  exitProfit: boolean | null;
}

const JourneyStepIcon: React.FC<JourneyStepIconProps> = ({
  step,
  stepIndex,
  currentStepIndex,
  exitProfit,
}) => {
  const status: StepStatus = useMemo(() => {
    if (stepIndex < currentStepIndex) return 'completed';
    if (stepIndex === currentStepIndex) return 'current';
    return 'future';
  }, [stepIndex, currentStepIndex]);

  const isExitStep = step.id === 'exit';

  return (
    <StepIconContainer
      status={status}
      isExitStep={isExitStep}
      exitProfit={exitProfit}
      data-testid={`journey-step-icon-${step.id}`}
      data-status={status}
    >
      {status === 'completed' ? <Check /> : step.icon}
    </StepIconContainer>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

/**
 * JourneyBar Component
 *
 * Displays a visual progress indicator for the trading flow cycle.
 * Uses MUI Stepper as base with custom styling for journey visualization.
 *
 * @example
 * ```tsx
 * <JourneyBar currentState="POSITION_ACTIVE" />
 *
 * // With exit P&L coloring
 * <JourneyBar currentState="ZE1" exitPnL={150.50} />
 *
 * // Compact mode
 * <JourneyBar currentState="S1" compact />
 * ```
 */
const JourneyBar: React.FC<JourneyBarProps> = ({
  currentState,
  exitPnL,
  compact = false,
}) => {
  const theme = useTheme();

  // Get current step index from state machine state
  const currentStepIndex = useMemo(
    () => getStepIndexFromState(currentState),
    [currentState]
  );

  // Determine exit profit/loss status
  const exitProfit = useMemo(() => {
    // If exitPnL is provided, use it for coloring
    if (exitPnL !== undefined) {
      return exitPnL >= 0;
    }
    // Otherwise, determine from state
    return isExitProfit(currentState);
  }, [currentState, exitPnL]);

  // Get step status for label styling
  const getStepStatus = (stepIndex: number): StepStatus => {
    if (stepIndex < currentStepIndex) return 'completed';
    if (stepIndex === currentStepIndex) return 'current';
    return 'future';
  };

  return (
    <Box
      sx={{
        width: '100%',
        py: compact ? 1 : 2,
        px: compact ? 1 : 2,
      }}
      data-testid="journey-bar"
      data-current-step={currentStepIndex}
      data-current-state={currentState}
    >
      <Stepper
        alternativeLabel
        activeStep={currentStepIndex}
        connector={<JourneyConnector />}
        sx={{
          '& .MuiStep-root': {
            transition: 'all 300ms ease-in-out', // AC6
          },
        }}
      >
        {JOURNEY_STEPS.map((step, index) => {
          const status = getStepStatus(index);
          const isExitStep = step.id === 'exit';

          return (
            <Step key={step.id} data-testid={`journey-step-${step.id}`}>
              <StepLabel
                StepIconComponent={() => (
                  <JourneyStepIcon
                    step={step}
                    stepIndex={index}
                    currentStepIndex={currentStepIndex}
                    exitProfit={exitProfit}
                  />
                )}
              >
                <StepLabelText
                  status={status}
                  isExitStep={isExitStep}
                  exitProfit={exitProfit}
                  data-testid={`journey-step-label-${step.id}`}
                >
                  {step.label}
                </StepLabelText>
              </StepLabel>
            </Step>
          );
        })}
      </Stepper>
    </Box>
  );
};

// Export utility functions for testing
export { getStepIndexFromState, isExitProfit, JOURNEY_STEPS };

export default JourneyBar;
