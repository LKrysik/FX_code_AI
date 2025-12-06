'use client';

import React, { useState } from 'react';
import { Box, Button, Container, Typography } from '@mui/material';
import TransitionLog, { Transition } from './TransitionLog';

/**
 * Example usage of TransitionLog component
 */
const TransitionLogExample: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);

  // Mock transition data
  const mockTransitions: Transition[] = [
    {
      timestamp: new Date().toISOString(),
      strategy_id: 'PUMP_DUMP_001',
      symbol: 'BTC/USDT',
      from_state: 'SIGNAL_DETECTED',
      to_state: 'POSITION_ACTIVE',
      trigger: 'O1',
      conditions: {
        volume_surge: {
          indicator_name: 'Volume Surge',
          value: 3.5,
          threshold: 2.0,
          operator: '>',
          met: true
        },
        price_spike: {
          indicator_name: 'Price Spike',
          value: 5.2,
          threshold: 3.0,
          operator: '>',
          met: true
        },
        market_cap: {
          indicator_name: 'Market Cap',
          value: 15000000,
          threshold: 10000000,
          operator: '>',
          met: true
        }
      }
    },
    {
      timestamp: new Date(Date.now() - 60000).toISOString(),
      strategy_id: 'PUMP_DUMP_001',
      symbol: 'BTC/USDT',
      from_state: 'MONITORING',
      to_state: 'SIGNAL_DETECTED',
      trigger: 'S1',
      conditions: {
        volume_change: {
          indicator_name: 'Volume Change',
          value: 2.8,
          threshold: 2.0,
          operator: '>',
          met: true
        },
        price_momentum: {
          indicator_name: 'Price Momentum',
          value: 4.1,
          threshold: 3.5,
          operator: '>',
          met: true
        }
      }
    },
    {
      timestamp: new Date(Date.now() - 120000).toISOString(),
      strategy_id: 'PUMP_DUMP_002',
      symbol: 'ETH/USDT',
      from_state: 'POSITION_ACTIVE',
      to_state: 'EXITED',
      trigger: 'ZE1',
      conditions: {
        profit_target: {
          indicator_name: 'Profit Target',
          value: 5.5,
          threshold: 5.0,
          operator: '>=',
          met: true
        },
        volume_drop: {
          indicator_name: 'Volume Drop',
          value: 0.3,
          threshold: 0.5,
          operator: '<',
          met: true
        }
      }
    },
    {
      timestamp: new Date(Date.now() - 180000).toISOString(),
      strategy_id: 'PUMP_DUMP_003',
      symbol: 'SOL/USDT',
      from_state: 'POSITION_ACTIVE',
      to_state: 'EXITED',
      trigger: 'E1',
      conditions: {
        stop_loss: {
          indicator_name: 'Stop Loss',
          value: -8.2,
          threshold: -5.0,
          operator: '<',
          met: true
        },
        price_crash: {
          indicator_name: 'Price Crash',
          value: -12.5,
          threshold: -10.0,
          operator: '<',
          met: true
        }
      }
    },
    {
      timestamp: new Date(Date.now() - 240000).toISOString(),
      strategy_id: 'PUMP_DUMP_003',
      symbol: 'SOL/USDT',
      from_state: 'MONITORING',
      to_state: 'POSITION_ACTIVE',
      trigger: 'O1',
      conditions: {
        volume_surge: {
          indicator_name: 'Volume Surge',
          value: 4.2,
          threshold: 2.5,
          operator: '>',
          met: true
        }
      }
    },
    {
      timestamp: new Date(Date.now() - 300000).toISOString(),
      strategy_id: 'PUMP_DUMP_001',
      symbol: 'BTC/USDT',
      from_state: 'INACTIVE',
      to_state: 'MONITORING',
      trigger: 'MANUAL',
      conditions: {}
    }
  ];

  const handleTransitionClick = (transition: Transition) => {
    console.log('Transition clicked:', transition);
  };

  const handleToggleLoading = () => {
    setIsLoading(!isLoading);
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          TransitionLog Component Example
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          This component displays the history of state machine transitions with expandable details.
        </Typography>

        <Button
          variant="outlined"
          onClick={handleToggleLoading}
          sx={{ mb: 2 }}
        >
          Toggle Loading State
        </Button>
      </Box>

      <Box sx={{ height: '600px' }}>
        <TransitionLog
          transitions={mockTransitions}
          maxItems={50}
          onTransitionClick={handleTransitionClick}
          isLoading={isLoading}
        />
      </Box>

      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" gutterBottom>
          Features Demonstrated:
        </Typography>
        <ul>
          <li>Newest transitions on top</li>
          <li>Color-coded backgrounds based on transition type</li>
          <li>Expandable rows with condition details</li>
          <li>StateBadge integration for state display</li>
          <li>Trigger badges with appropriate colors</li>
          <li>Loading skeleton state</li>
          <li>Empty state handling</li>
          <li>Auto-scroll to top on new transitions</li>
        </ul>

        <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
          Color Legend:
        </Typography>
        <ul>
          <li><strong>Green background:</strong> Transition to POSITION_ACTIVE (successful entry)</li>
          <li><strong>Red background:</strong> Transition to EXITED with E1 trigger (emergency exit)</li>
          <li><strong>Blue background:</strong> Transition to EXITED with ZE1 trigger (normal close)</li>
        </ul>
      </Box>
    </Container>
  );
};

export default TransitionLogExample;
