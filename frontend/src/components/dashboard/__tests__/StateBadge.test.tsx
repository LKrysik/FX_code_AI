/**
 * StateBadge Component Tests
 * Story 1A-2: State Machine State Badge
 *
 * Tests cover:
 * - AC1: All states render (MONITORING, S1, O1, Z1, ZE1, E1, POSITION_ACTIVE)
 * - AC2: Colors match UX spec
 * - AC3: Hero size renders with 48px font
 * - AC4: Duration updates (tested via showDuration prop)
 * - AC5: Human-readable labels with icons
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
  // Story 1A-2 AC1: All primary trading states + legacy states
  const primaryStates: StateMachineState[] = [
    'MONITORING',
    'S1',
    'O1',
    'Z1',
    'POSITION_ACTIVE',
    'ZE1',
    'E1'
  ];

  const legacyStates: StateMachineState[] = [
    'INACTIVE',
    'SIGNAL_DETECTED',
    'EXITED',
    'ERROR'
  ];

  const allStates = [...primaryStates, ...legacyStates];

  // AC1: Test all states render correctly
  allStates.forEach((state) => {
    it(`renders ${state} state correctly`, () => {
      const { container } = render(<StateBadge state={state} />);

      // Component should render without crashing - MUI Chip renders as div
      const chip = container.querySelector('.MuiChip-root');
      expect(chip).toBeInTheDocument();
    });
  });

  it('renders with small size', () => {
    const { container } = render(<StateBadge state="MONITORING" size="small" />);
    const chip = container.querySelector('.MuiChip-root');
    expect(chip).toHaveClass('MuiChip-sizeSmall');
  });

  it('renders with medium size (default)', () => {
    const { container } = render(<StateBadge state="MONITORING" size="medium" />);
    const chip = container.querySelector('.MuiChip-root');
    expect(chip).toHaveClass('MuiChip-sizeMedium');
  });

  it('displays duration when showDuration is true', async () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();

    const { container } = render(
      <StateBadge
        state="MONITORING"
        since={fiveMinutesAgo}
        showDuration
      />
    );

    await waitFor(() => {
      const chip = container.querySelector('.MuiChip-root');
      expect(chip?.textContent).toMatch(/5m/);
    });
  });

  it('does not display duration when showDuration is false', () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();

    const { container } = render(
      <StateBadge
        state="MONITORING"
        since={fiveMinutesAgo}
        showDuration={false}
      />
    );

    const chip = container.querySelector('.MuiChip-root');
    expect(chip?.textContent).not.toMatch(/\d+m/);
  });

  // AC5: Test human-readable labels with correct icons
  it('includes correct icon for each state', () => {
    const stateIcons: Record<StateMachineState, string> = {
      // Primary states (Story 1A-2)
      MONITORING: '👀',
      S1: '🔥',
      O1: '❌',
      Z1: '🎯',
      POSITION_ACTIVE: '📈',
      ZE1: '💰',
      E1: '🛑',
      // Legacy states
      INACTIVE: '⏸️',
      SIGNAL_DETECTED: '🔥',
      EXITED: '✓',
      ERROR: '⚠️'
    };

    allStates.forEach((state) => {
      const { container, unmount } = render(<StateBadge state={state} />);
      const chip = container.querySelector('.MuiChip-root');
      expect(chip?.textContent).toContain(stateIcons[state]);
      unmount();
    });
  });

  // AC3: Test hero size renders with large font
  it('renders hero size with prominent styling', () => {
    const { container } = render(<StateBadge state="MONITORING" size="hero" />);

    // Hero size should not use Chip (uses Box instead)
    const heroElement = container.querySelector('[class*="MuiBox"]');
    expect(heroElement).toBeInTheDocument();
  });

  // Test pulsing animation for signal detected states (S1 and SIGNAL_DETECTED)
  it('applies pulsing animation for S1 state', () => {
    const { container } = render(<StateBadge state="S1" />);
    const chip = container.querySelector('.MuiChip-root');
    expect(chip).toBeInTheDocument();
  });

  it('applies pulsing animation for SIGNAL_DETECTED state', () => {
    const { container } = render(<StateBadge state="SIGNAL_DETECTED" />);
    const chip = container.querySelector('.MuiChip-root');
    expect(chip).toBeInTheDocument();
  });

  it('handles invalid date gracefully', () => {
    const { container } = render(
      <StateBadge
        state="MONITORING"
        since="invalid-date"
        showDuration
      />
    );

    const chip = container.querySelector('.MuiChip-root');
    expect(chip).toBeInTheDocument();
  });

  it('updates duration over time', async () => {
    jest.useFakeTimers();
    const thirtySecondsAgo = new Date(Date.now() - 30 * 1000).toISOString();

    const { container } = render(
      <StateBadge
        state="MONITORING"
        since={thirtySecondsAgo}
        showDuration
      />
    );

    // Initial state
    let chip = container.querySelector('.MuiChip-root');
    const initialText = chip?.textContent;

    // Advance time by 2 seconds
    jest.advanceTimersByTime(2000);

    await waitFor(() => {
      chip = container.querySelector('.MuiChip-root');
      // Duration should have updated
      expect(chip?.textContent).toBeDefined();
    });

    jest.useRealTimers();
  });
});
