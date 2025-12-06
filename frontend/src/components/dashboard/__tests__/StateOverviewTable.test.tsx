/**
 * StateOverviewTable Component Tests
 * ====================================
 *
 * Unit tests for the State Overview Table component (SM-01)
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import StateOverviewTable, { StateInstance } from '../StateOverviewTable';

// ============================================================================
// MOCK DATA
// ============================================================================

const mockInstances: StateInstance[] = [
  {
    strategy_id: 'pump_dump_v1',
    symbol: 'BTCUSDT',
    state: 'POSITION_ACTIVE',
    since: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
  },
  {
    strategy_id: 'pump_dump_v1',
    symbol: 'ETHUSDT',
    state: 'SIGNAL_DETECTED',
    since: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
  },
  {
    strategy_id: 'trend_follow_v2',
    symbol: 'SOLUSDT',
    state: 'MONITORING',
    since: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
  },
  {
    strategy_id: 'scalping_v1',
    symbol: 'ADAUSDT',
    state: 'INACTIVE',
    since: null,
  },
];

// ============================================================================
// TESTS
// ============================================================================

describe('StateOverviewTable Component', () => {
  // ========================================
  // Basic Rendering
  // ========================================

  it('renders table with column headers', () => {
    render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={mockInstances}
      />
    );

    expect(screen.getByText('Strategy')).toBeInTheDocument();
    expect(screen.getByText('Symbol')).toBeInTheDocument();
    expect(screen.getByText('State')).toBeInTheDocument();
    expect(screen.getByText('Since')).toBeInTheDocument();
    expect(screen.getByText('Action')).toBeInTheDocument();
  });

  it('renders session ID in header', () => {
    render(
      <StateOverviewTable
        sessionId="test-session-123"
        instances={mockInstances}
      />
    );

    expect(screen.getByText(/test-session-123/i)).toBeInTheDocument();
  });

  it('renders all instances', () => {
    render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={mockInstances}
      />
    );

    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    expect(screen.getByText('ETHUSDT')).toBeInTheDocument();
    expect(screen.getByText('SOLUSDT')).toBeInTheDocument();
    expect(screen.getByText('ADAUSDT')).toBeInTheDocument();
  });

  // ========================================
  // Sorting & Priority
  // ========================================

  it('sorts instances by state priority (POSITION_ACTIVE first)', () => {
    const { container } = render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={mockInstances}
      />
    );

    const rows = container.querySelectorAll('tbody tr');

    // First row should be POSITION_ACTIVE (BTCUSDT)
    expect(rows[0]).toHaveTextContent('BTCUSDT');

    // Second row should be SIGNAL_DETECTED (ETHUSDT)
    expect(rows[1]).toHaveTextContent('ETHUSDT');
  });

  // ========================================
  // Empty State
  // ========================================

  it('displays "No active instances" when empty', () => {
    render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={[]}
        isLoading={false}
      />
    );

    expect(screen.getByText('No active instances')).toBeInTheDocument();
  });

  // ========================================
  // Loading State
  // ========================================

  it('displays loading skeleton when isLoading is true and no instances', () => {
    const { container } = render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={[]}
        isLoading={true}
      />
    );

    // Should show skeleton rows (MUI Skeleton)
    const skeletons = container.querySelectorAll('.MuiSkeleton-root');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  // ========================================
  // Click Handlers
  // ========================================

  it('calls onInstanceClick when View button is clicked', () => {
    const handleClick = jest.fn();

    render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={mockInstances}
        onInstanceClick={handleClick}
      />
    );

    const viewButtons = screen.getAllByText('View');
    fireEvent.click(viewButtons[0]);

    expect(handleClick).toHaveBeenCalledTimes(1);
    expect(handleClick).toHaveBeenCalledWith(
      expect.objectContaining({
        strategy_id: expect.any(String),
        symbol: expect.any(String),
        state: expect.any(String),
      })
    );
  });

  it('calls onInstanceClick when row is clicked', () => {
    const handleClick = jest.fn();

    const { container } = render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={mockInstances}
        onInstanceClick={handleClick}
      />
    );

    const firstRow = container.querySelector('tbody tr');
    if (firstRow) {
      fireEvent.click(firstRow);
    }

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  // ========================================
  // Time Display
  // ========================================

  it('displays time elapsed for instances with since timestamp', () => {
    render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={mockInstances}
      />
    );

    // Should show time in format like "5m 0s", "2m 0s", etc.
    // We check for presence of 'm' (minutes) which indicates time display
    const timeElements = screen.getAllByText(/\d+m/);
    expect(timeElements.length).toBeGreaterThan(0);
  });

  it('displays N/A for instances without since timestamp', () => {
    render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={[
          {
            strategy_id: 'test_strategy',
            symbol: 'TESTUSDT',
            state: 'INACTIVE',
            since: null,
          },
        ]}
      />
    );

    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  // ========================================
  // Footer
  // ========================================

  it('displays correct count in footer', () => {
    render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={mockInstances}
      />
    );

    expect(screen.getByText(/Showing 4 instances/i)).toBeInTheDocument();
  });

  it('displays singular form when only 1 instance', () => {
    render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={[mockInstances[0]]}
      />
    );

    expect(screen.getByText(/Showing 1 instance$/i)).toBeInTheDocument();
  });

  // ========================================
  // Background Colors
  // ========================================

  it('applies special background for POSITION_ACTIVE rows', () => {
    const { container } = render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={[
          {
            strategy_id: 'test',
            symbol: 'BTCUSDT',
            state: 'POSITION_ACTIVE',
            since: new Date().toISOString(),
          },
        ]}
      />
    );

    const row = container.querySelector('tbody tr');
    expect(row).toHaveStyle({ backgroundColor: expect.any(String) });
  });

  it('applies special background for SIGNAL_DETECTED rows', () => {
    const { container } = render(
      <StateOverviewTable
        sessionId="test-session-1"
        instances={[
          {
            strategy_id: 'test',
            symbol: 'ETHUSDT',
            state: 'SIGNAL_DETECTED',
            since: new Date().toISOString(),
          },
        ]}
      />
    );

    const row = container.querySelector('tbody tr');
    expect(row).toHaveStyle({ backgroundColor: expect.any(String) });
  });
});
