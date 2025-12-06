'use client';

/**
 * ConditionProgress Example Usage
 * ================================
 *
 * Demonstrates how to integrate ConditionProgress component
 * with live data from backend API.
 */

import React, { useState, useEffect } from 'react';
import { Box, Container, Typography, Button } from '@mui/material';
import ConditionProgress, { ConditionGroup } from './ConditionProgress';

// ============================================================================
// Mock Data (Replace with actual API call)
// ============================================================================

const MOCK_CONDITION_GROUPS: ConditionGroup[] = [
  {
    section: 'S1',
    label: 'Pump Detection',
    logic: 'AND',
    all_met: true,
    conditions: [
      {
        indicator_name: 'PUMP_MAGNITUDE_PCT',
        operator: '>',
        threshold: 5.0,
        current_value: 7.2,
        met: true,
      },
      {
        indicator_name: 'VOLUME_SPIKE',
        operator: '>',
        threshold: 3.0,
        current_value: 4.5,
        met: true,
      },
      {
        indicator_name: 'PRICE_ACCELERATION',
        operator: '>=',
        threshold: 2.0,
        current_value: 2.8,
        met: true,
      },
    ],
  },
  {
    section: 'O1',
    label: 'Cancel Signal',
    logic: 'OR',
    all_met: false,
    conditions: [
      {
        indicator_name: 'DUMP_DETECTED',
        operator: '==',
        threshold: 1.0,
        current_value: 0.0,
        met: false,
      },
      {
        indicator_name: 'VOLATILITY_TOO_HIGH',
        operator: '>',
        threshold: 10.0,
        current_value: 6.2,
        met: false,
      },
    ],
  },
  {
    section: 'Z1',
    label: 'Peak Entry',
    logic: 'AND',
    all_met: false,
    conditions: [
      {
        indicator_name: 'PEAK_CONFIRMED',
        operator: '==',
        threshold: 1.0,
        current_value: 0.0,
        met: false,
      },
      {
        indicator_name: 'RSI',
        operator: '>',
        threshold: 70.0,
        current_value: 65.3,
        met: false,
      },
      {
        indicator_name: 'PRICE_ABOVE_MA',
        operator: '>=',
        threshold: 1.0,
        current_value: 1.2,
        met: true,
      },
    ],
  },
  {
    section: 'ZE1',
    label: 'Dump End Close',
    logic: 'AND',
    all_met: false,
    conditions: [
      {
        indicator_name: 'DUMP_MAGNITUDE_PCT',
        operator: '<',
        threshold: -8.0,
        current_value: -5.2,
        met: false,
      },
      {
        indicator_name: 'DUMP_DURATION_MIN',
        operator: '>=',
        threshold: 15.0,
        current_value: 8.0,
        met: false,
      },
    ],
  },
  {
    section: 'E1',
    label: 'Emergency Exit',
    logic: 'OR',
    all_met: false,
    conditions: [
      {
        indicator_name: 'LOSS_PCT',
        operator: '<',
        threshold: -10.0,
        current_value: -2.5,
        met: false,
      },
      {
        indicator_name: 'LIQUIDATION_RISK',
        operator: '>',
        threshold: 0.9,
        current_value: 0.15,
        met: false,
      },
      {
        indicator_name: 'TIME_IN_POSITION_MIN',
        operator: '>',
        threshold: 60.0,
        current_value: 12.0,
        met: false,
      },
    ],
  },
];

// ============================================================================
// Example Component
// ============================================================================

const ConditionProgressExample: React.FC = () => {
  const [groups, setGroups] = useState<ConditionGroup[]>([]);
  const [currentState, setCurrentState] = useState<string>('SIGNAL_DETECTED');
  const [isLoading, setIsLoading] = useState(false);

  // Simulate API call
  const loadConditions = async () => {
    setIsLoading(true);
    setTimeout(() => {
      setGroups(MOCK_CONDITION_GROUPS);
      setIsLoading(false);
    }, 1000);
  };

  useEffect(() => {
    loadConditions();
  }, []);

  // Simulate state transitions
  const handleStateChange = (newState: string) => {
    setCurrentState(newState);
  };

  // Simulate condition value updates (e.g., from WebSocket)
  const handleSimulateUpdate = () => {
    setGroups((prev) =>
      prev.map((group) => ({
        ...group,
        conditions: group.conditions.map((cond) => ({
          ...cond,
          current_value: cond.current_value + (Math.random() - 0.5) * 2,
          met: Math.random() > 0.5,
        })),
        all_met: Math.random() > 0.7,
      }))
    );
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        ConditionProgress Example
      </Typography>

      <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Button variant="outlined" onClick={() => handleStateChange('INACTIVE')}>
          INACTIVE
        </Button>
        <Button variant="outlined" onClick={() => handleStateChange('MONITORING')}>
          MONITORING
        </Button>
        <Button variant="outlined" onClick={() => handleStateChange('SIGNAL_DETECTED')}>
          SIGNAL_DETECTED
        </Button>
        <Button variant="outlined" onClick={() => handleStateChange('POSITION_ACTIVE')}>
          POSITION_ACTIVE
        </Button>
        <Button variant="outlined" onClick={() => handleStateChange('EXITED')}>
          EXITED
        </Button>
        <Button variant="contained" color="primary" onClick={handleSimulateUpdate}>
          Simulate Update
        </Button>
      </Box>

      <ConditionProgress groups={groups} currentState={currentState} isLoading={isLoading} />
    </Container>
  );
};

export default ConditionProgressExample;
