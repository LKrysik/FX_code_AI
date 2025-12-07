'use client';

import React, { useState } from 'react';
import {
  Box,
  Typography,
  ToggleButtonGroup,
  ToggleButton,
  Paper,
} from '@mui/material';
import StateMachineDiagram, { StateMachineState } from './StateMachineDiagram';

/**
 * Example/Demo component for StateMachineDiagram
 *
 * This shows how to use the StateMachineDiagram component with different states
 * and interactions.
 */
export default function StateMachineDiagramExample() {
  const [currentState, setCurrentState] = useState<StateMachineState>('MONITORING');
  const [showLabels, setShowLabels] = useState(true);

  const handleStateChange = (
    event: React.MouseEvent<HTMLElement>,
    newState: StateMachineState | null,
  ) => {
    if (newState !== null) {
      setCurrentState(newState);
    }
  };

  const handleStateClick = (state: StateMachineState) => {
    console.log('State clicked:', state);
    setCurrentState(state);
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom>
        State Machine Diagram - Interactive Demo
      </Typography>

      <Typography variant="body1" color="text.secondary" paragraph>
        This diagram visualizes the pump/dump detection state machine flow.
        Click on states or use the buttons below to highlight different states.
      </Typography>

      {/* Controls */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Current State:
        </Typography>
        <ToggleButtonGroup
          value={currentState}
          exclusive
          onChange={handleStateChange}
          aria-label="state selector"
          sx={{ mb: 2, flexWrap: 'wrap' }}
        >
          <ToggleButton value="MONITORING" aria-label="monitoring">
            MONITORING
          </ToggleButton>
          <ToggleButton value="SIGNAL_DETECTED" aria-label="signal detected">
            SIGNAL_DETECTED
          </ToggleButton>
          <ToggleButton value="POSITION_ACTIVE" aria-label="position active">
            POSITION_ACTIVE
          </ToggleButton>
          <ToggleButton value="EXITED" aria-label="exited">
            EXITED
          </ToggleButton>
          <ToggleButton value="ERROR" aria-label="error">
            ERROR
          </ToggleButton>
        </ToggleButtonGroup>

        <Box sx={{ mt: 2 }}>
          <ToggleButtonGroup
            value={showLabels}
            exclusive
            onChange={(e, val) => val !== null && setShowLabels(val)}
            aria-label="show labels"
          >
            <ToggleButton value={true} aria-label="show labels">
              Show Labels
            </ToggleButton>
            <ToggleButton value={false} aria-label="hide labels">
              Hide Labels
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Paper>

      {/* Diagram */}
      <StateMachineDiagram
        currentState={currentState}
        onStateClick={handleStateClick}
        showLabels={showLabels}
      />

      {/* State Descriptions */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          State Descriptions
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Box>
            <Typography variant="subtitle2" color="success.main">
              MONITORING (Idle)
            </Typography>
            <Typography variant="body2" color="text.secondary">
              System is actively scanning markets for pump/dump signals. Waiting for S1 condition (velocity spike + volume surge).
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2" color="warning.main">
              SIGNAL_DETECTED (Pump Found)
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Pump signal detected. System is evaluating entry conditions (Z1) to determine if peak is reached.
              If Z1 not met within timeout, transitions to EXITED via O1.
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2" color="error.main">
              POSITION_ACTIVE (In Trade)
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Active SHORT position opened at pump peak. Monitoring for dump completion (ZE1) or emergency conditions (E1).
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2" color="info.main">
              EXITED (Done)
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Position closed successfully or signal cancelled. System returns to MONITORING state after cooldown.
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2" color="error.dark">
              ERROR
            </Typography>
            <Typography variant="body2" color="text.secondary">
              System error detected (e.g., exchange connection lost, risk limit breached). Requires attention before resuming.
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* Transition Conditions */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Transition Conditions
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Box>
            <Typography variant="subtitle2">
              S1: MONITORING → SIGNAL_DETECTED
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Trigger: Pump detected via velocity spike + volume surge indicators
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2">
              Z1: SIGNAL_DETECTED → POSITION_ACTIVE
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Trigger: Peak detection conditions met, SHORT entry confirmed
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2">
              O1: SIGNAL_DETECTED → EXITED
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Trigger: Timeout - signal expired without entry conditions being met
            </Typography>
          </Box>

          <Box>
            <Typography variant="subtitle2">
              ZE1 / E1: POSITION_ACTIVE → EXITED
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Trigger: Dump completed (ZE1) OR emergency stop conditions (E1)
            </Typography>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
}
