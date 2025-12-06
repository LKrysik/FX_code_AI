/**
 * TransitionLog Component Tests
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import TransitionLog from '../TransitionLog';
import type { Transition } from '../TransitionLog';

// Mock StateBadge component
jest.mock('../StateBadge', () => ({
  __esModule: true,
  default: ({ state }: { state: string }) => (
    <div data-testid="state-badge">{state}</div>
  )
}));

// Mock MUI components if needed
jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  Collapse: ({ children, in: isOpen }: any) => (
    <div style={{ display: isOpen ? 'block' : 'none' }}>{children}</div>
  )
}));

describe('TransitionLog Component', () => {
  const mockTransitions: Transition[] = [
    {
      timestamp: '2024-01-15T10:30:00Z',
      strategy_id: 'PUMP_DUMP_001',
      symbol: 'BTC/USDT',
      from_state: 'MONITORING',
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
        }
      }
    },
    {
      timestamp: '2024-01-15T10:25:00Z',
      strategy_id: 'PUMP_DUMP_001',
      symbol: 'ETH/USDT',
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
        }
      }
    }
  ];

  it('renders without crashing', () => {
    render(<TransitionLog transitions={[]} />);
    expect(screen.getByText(/Transition Log/i)).toBeInTheDocument();
  });

  it('displays empty state when no transitions', () => {
    render(<TransitionLog transitions={[]} />);
    expect(screen.getByText(/No transitions yet/i)).toBeInTheDocument();
  });

  it('displays loading skeletons when isLoading is true', () => {
    render(<TransitionLog transitions={[]} isLoading />);
    const skeletons = screen.getAllByTestId(/skeleton/i);
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders transition rows correctly', () => {
    render(<TransitionLog transitions={mockTransitions} />);

    // Check if symbols are displayed
    expect(screen.getByText('BTC/USDT')).toBeInTheDocument();
    expect(screen.getByText('ETH/USDT')).toBeInTheDocument();
  });

  it('displays trigger badges', () => {
    render(<TransitionLog transitions={mockTransitions} />);

    expect(screen.getByText('O1')).toBeInTheDocument();
    expect(screen.getByText('E1')).toBeInTheDocument();
  });

  it('expands row details on click', () => {
    render(<TransitionLog transitions={mockTransitions} />);

    // Initially details should not be visible
    expect(screen.queryByText('Full Timestamp:')).not.toBeInTheDocument();

    // Click first row
    const rows = screen.getAllByRole('row');
    const firstDataRow = rows[1]; // Index 0 is header
    fireEvent.click(firstDataRow);

    // Details should now be visible
    expect(screen.getByText(/Full Timestamp:/i)).toBeInTheDocument();
    expect(screen.getByText(/Strategy ID:/i)).toBeInTheDocument();
  });

  it('displays condition details when expanded', () => {
    render(<TransitionLog transitions={mockTransitions} />);

    // Click first row to expand
    const rows = screen.getAllByRole('row');
    const firstDataRow = rows[1];
    fireEvent.click(firstDataRow);

    // Check if conditions are displayed
    expect(screen.getByText(/Volume Surge/i)).toBeInTheDocument();
    expect(screen.getByText(/Price Spike/i)).toBeInTheDocument();
  });

  it('calls onTransitionClick callback when row is clicked', () => {
    const mockCallback = jest.fn();
    render(
      <TransitionLog
        transitions={mockTransitions}
        onTransitionClick={mockCallback}
      />
    );

    // Click first row
    const rows = screen.getAllByRole('row');
    const firstDataRow = rows[1];
    fireEvent.click(firstDataRow);

    expect(mockCallback).toHaveBeenCalledWith(mockTransitions[0]);
  });

  it('limits displayed transitions to maxItems', () => {
    const manyTransitions: Transition[] = Array.from({ length: 100 }, (_, i) => ({
      timestamp: `2024-01-15T10:${i}:00Z`,
      strategy_id: `STRATEGY_${i}`,
      symbol: `SYMBOL${i}`,
      from_state: 'MONITORING',
      to_state: 'SIGNAL_DETECTED',
      trigger: 'S1' as const,
      conditions: {}
    }));

    render(<TransitionLog transitions={manyTransitions} maxItems={10} />);

    // Should show "Showing 10 of 100"
    expect(screen.getByText(/Showing 10 of 100/i)).toBeInTheDocument();
  });

  it('displays state badges for from_state and to_state', () => {
    render(<TransitionLog transitions={mockTransitions} />);

    // Should render multiple StateBadge components
    const stateBadges = screen.getAllByTestId('state-badge');
    expect(stateBadges.length).toBeGreaterThan(0);
  });

  it('formats time correctly', () => {
    render(<TransitionLog transitions={mockTransitions} />);

    // Time should be displayed in HH:MM:SS format
    // The exact format depends on locale, but it should be present
    const timeElements = screen.getAllByText(/\d{2}:\d{2}:\d{2}/);
    expect(timeElements.length).toBeGreaterThan(0);
  });

  it('toggles row expansion', () => {
    render(<TransitionLog transitions={mockTransitions} />);

    const rows = screen.getAllByRole('row');
    const firstDataRow = rows[1];

    // Click to expand
    fireEvent.click(firstDataRow);
    expect(screen.getByText(/Full Timestamp:/i)).toBeInTheDocument();

    // Click again to collapse
    fireEvent.click(firstDataRow);
    expect(screen.queryByText(/Full Timestamp:/i)).not.toBeInTheDocument();
  });

  it('shows correct transition count in header', () => {
    render(<TransitionLog transitions={mockTransitions} />);
    expect(screen.getByText(/Showing 2 of 2 transitions/i)).toBeInTheDocument();
  });

  it('handles empty conditions gracefully', () => {
    const transitionsWithEmptyConditions: Transition[] = [
      {
        timestamp: '2024-01-15T10:30:00Z',
        strategy_id: 'TEST_001',
        symbol: 'BTC/USDT',
        from_state: 'INACTIVE',
        to_state: 'MONITORING',
        trigger: 'MANUAL',
        conditions: {}
      }
    ];

    render(<TransitionLog transitions={transitionsWithEmptyConditions} />);

    // Click to expand
    const rows = screen.getAllByRole('row');
    const firstDataRow = rows[1];
    fireEvent.click(firstDataRow);

    // Should show "No conditions data available"
    expect(screen.getByText(/No conditions data available/i)).toBeInTheDocument();
  });
});
