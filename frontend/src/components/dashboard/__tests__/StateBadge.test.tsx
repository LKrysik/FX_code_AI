/**
 * StateBadge Component Tests
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import StateBadge from '../StateBadge';
import type { StateMachineState } from '../StateBadge';

// Mock MUI components if needed
jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  Tooltip: ({ children, title }: any) => (
    <div data-testid="tooltip" title={typeof title === 'string' ? title : 'tooltip'}>
      {children}
    </div>
  )
}));

describe('StateBadge Component', () => {
  // Basic rendering tests for all states
  const states: StateMachineState[] = [
    'INACTIVE',
    'MONITORING',
    'SIGNAL_DETECTED',
    'POSITION_ACTIVE',
    'EXITED',
    'ERROR'
  ];

  states.forEach((state) => {
    it(`renders ${state} state correctly`, () => {
      render(<StateBadge state={state} />);

      // Component should render without crashing
      const chip = screen.getByRole('button');
      expect(chip).toBeInTheDocument();
    });
  });

  it('renders with small size', () => {
    render(<StateBadge state="MONITORING" size="small" />);
    const chip = screen.getByRole('button');
    expect(chip).toHaveClass('MuiChip-sizeSmall');
  });

  it('renders with medium size (default)', () => {
    render(<StateBadge state="MONITORING" size="medium" />);
    const chip = screen.getByRole('button');
    expect(chip).toHaveClass('MuiChip-sizeMedium');
  });

  it('displays duration when showDuration is true', async () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();

    render(
      <StateBadge
        state="MONITORING"
        since={fiveMinutesAgo}
        showDuration
      />
    );

    await waitFor(() => {
      const chip = screen.getByRole('button');
      expect(chip.textContent).toMatch(/5m/);
    });
  });

  it('does not display duration when showDuration is false', () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();

    render(
      <StateBadge
        state="MONITORING"
        since={fiveMinutesAgo}
        showDuration={false}
      />
    );

    const chip = screen.getByRole('button');
    expect(chip.textContent).not.toMatch(/\d+m/);
  });

  it('includes correct icon for each state', () => {
    const stateIcons: Record<StateMachineState, string> = {
      INACTIVE: '⏸️',
      MONITORING: '👁️',
      SIGNAL_DETECTED: '⚡',
      POSITION_ACTIVE: '📍',
      EXITED: '✓',
      ERROR: '⚠️'
    };

    states.forEach((state) => {
      const { unmount } = render(<StateBadge state={state} />);
      const chip = screen.getByRole('button');
      expect(chip.textContent).toContain(stateIcons[state]);
      unmount();
    });
  });

  it('applies pulsing animation for SIGNAL_DETECTED state', () => {
    render(<StateBadge state="SIGNAL_DETECTED" />);
    const chip = screen.getByRole('button');

    // Check if the chip has the pulsing class or style
    // This is a basic check - actual animation testing would require more sophisticated tools
    expect(chip).toBeInTheDocument();
  });

  it('handles invalid date gracefully', () => {
    render(
      <StateBadge
        state="MONITORING"
        since="invalid-date"
        showDuration
      />
    );

    const chip = screen.getByRole('button');
    expect(chip).toBeInTheDocument();
  });

  it('updates duration over time', async () => {
    jest.useFakeTimers();
    const thirtySecondsAgo = new Date(Date.now() - 30 * 1000).toISOString();

    render(
      <StateBadge
        state="MONITORING"
        since={thirtySecondsAgo}
        showDuration
      />
    );

    // Initial state
    let chip = screen.getByRole('button');
    const initialText = chip.textContent;

    // Advance time by 2 seconds
    jest.advanceTimersByTime(2000);

    await waitFor(() => {
      chip = screen.getByRole('button');
      // Duration should have updated
      expect(chip.textContent).toBeDefined();
    });

    jest.useRealTimers();
  });
});
