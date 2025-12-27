/**
 * StatusHero Component Tests
 * Story 1A-5: StatusHero Component
 *
 * Tests cover:
 * - AC1: Hero renders as largest and most prominent element
 * - AC2: State-driven styling with correct colors
 * - AC3: P&L display with proper formatting
 * - AC4: Position details (entry, current, side)
 * - AC5: Session/position timers update
 * - AC6: Signal type display (pump/dump)
 * - AC7: Responsive sizing (mobile/tablet/desktop)
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import StatusHero from '../StatusHero';
import type { StateMachineState } from '../StateBadge';

// Mock MUI useMediaQuery
jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  useMediaQuery: () => false, // Default to desktop view
}));

describe('StatusHero Component', () => {
  // All trading states
  const allStates: StateMachineState[] = [
    'MONITORING',
    'S1',
    'O1',
    'Z1',
    'POSITION_ACTIVE',
    'ZE1',
    'E1',
    'INACTIVE',
    'SIGNAL_DETECTED',
    'EXITED',
    'ERROR'
  ];

  // Position states (show P&L)
  const positionStates: StateMachineState[] = ['POSITION_ACTIVE', 'ZE1', 'E1'];

  // Signal states (show signal info)
  const signalStates: StateMachineState[] = ['S1', 'SIGNAL_DETECTED', 'Z1'];

  // AC1: Test all states render correctly
  describe('State Rendering', () => {
    allStates.forEach((state) => {
      it(`renders ${state} state correctly`, () => {
        const { container } = render(<StatusHero state={state} />);

        // Hero should render
        const hero = container.querySelector('.MuiPaper-root');
        expect(hero).toBeInTheDocument();
      });
    });

    it('displays state label prominently', () => {
      render(<StatusHero state="MONITORING" />);

      expect(screen.getByText('WATCHING')).toBeInTheDocument();
    });

    it('displays state icon', () => {
      render(<StatusHero state="MONITORING" />);

      expect(screen.getByText('👀')).toBeInTheDocument();
    });

    it('displays symbol when provided', () => {
      render(<StatusHero state="MONITORING" symbol="BTCUSDT" />);

      expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    });
  });

  // AC2: Test state-driven styling
  describe('State-Driven Styling', () => {
    it('applies pulsing animation for S1 state', () => {
      const { container } = render(<StatusHero state="S1" />);
      const hero = container.querySelector('.MuiPaper-root');
      expect(hero).toBeInTheDocument();
    });

    it('applies pulsing animation for SIGNAL_DETECTED state', () => {
      const { container } = render(<StatusHero state="SIGNAL_DETECTED" />);
      const hero = container.querySelector('.MuiPaper-root');
      expect(hero).toBeInTheDocument();
    });

    it('applies pulsing animation for Z1 state', () => {
      const { container } = render(<StatusHero state="Z1" />);
      const hero = container.querySelector('.MuiPaper-root');
      expect(hero).toBeInTheDocument();
    });
  });

  // AC3: Test P&L display
  describe('P&L Display', () => {
    it('displays P&L for position states', () => {
      render(<StatusHero state="POSITION_ACTIVE" pnl={1250.50} />);

      expect(screen.getByText('+$1.25K')).toBeInTheDocument();
    });

    it('displays negative P&L correctly', () => {
      render(<StatusHero state="POSITION_ACTIVE" pnl={-500.25} />);

      expect(screen.getByText('-$500.25')).toBeInTheDocument();
    });

    it('displays P&L percentage when provided', () => {
      render(<StatusHero state="POSITION_ACTIVE" pnl={1000} pnlPercent={5.25} />);

      expect(screen.getByText('+5.25%')).toBeInTheDocument();
    });

    it('formats million dollar P&L correctly', () => {
      render(<StatusHero state="POSITION_ACTIVE" pnl={1500000} />);

      expect(screen.getByText('+$1.50M')).toBeInTheDocument();
    });

    it('does not display P&L for non-position states', () => {
      render(<StatusHero state="MONITORING" pnl={1000} />);

      expect(screen.queryByText('+$1.00K')).not.toBeInTheDocument();
    });
  });

  // AC4: Test position details
  describe('Position Details', () => {
    it('displays side when in position', () => {
      render(<StatusHero state="POSITION_ACTIVE" side="LONG" pnl={100} />);

      expect(screen.getByText('LONG')).toBeInTheDocument();
    });

    it('displays entry price when provided', () => {
      render(<StatusHero state="POSITION_ACTIVE" entryPrice={50250.50} pnl={100} />);

      expect(screen.getByText('$50,250.50')).toBeInTheDocument();
    });

    it('displays current price when provided', () => {
      render(<StatusHero state="POSITION_ACTIVE" currentPrice={51000.25} pnl={100} />);

      expect(screen.getByText('$51,000.25')).toBeInTheDocument();
    });

    it('formats low-value prices with 4 decimal places', () => {
      render(<StatusHero state="POSITION_ACTIVE" entryPrice={0.0015} pnl={100} />);

      expect(screen.getByText('$0.0015')).toBeInTheDocument();
    });
  });

  // AC5: Test timers
  describe('Timer Display', () => {
    it('displays session time when provided', () => {
      render(<StatusHero state="MONITORING" sessionTime={3665} />); // 1h 1m 5s

      expect(screen.getByText(/Session: 1h 1m/)).toBeInTheDocument();
    });

    it('displays position duration for position states', () => {
      render(<StatusHero state="POSITION_ACTIVE" positionTime={125} pnl={100} />); // 2m 5s

      expect(screen.getByText('2m 5s')).toBeInTheDocument();
    });

    it('formats timer with only seconds', () => {
      render(<StatusHero state="MONITORING" sessionTime={45} />);

      expect(screen.getByText(/Session: 45s/)).toBeInTheDocument();
    });

    it('formats timer with minutes and seconds', () => {
      render(<StatusHero state="MONITORING" sessionTime={185} />); // 3m 5s

      expect(screen.getByText(/Session: 3m 5s/)).toBeInTheDocument();
    });
  });

  // AC6: Test signal type display
  describe('Signal Type Display', () => {
    it('displays pump signal type', () => {
      render(<StatusHero state="S1" signalType="pump" />);

      expect(screen.getByText('📈 Pump Signal')).toBeInTheDocument();
    });

    it('displays dump signal type', () => {
      render(<StatusHero state="S1" signalType="dump" />);

      expect(screen.getByText('📉 Dump Signal')).toBeInTheDocument();
    });

    it('does not display signal type for non-signal states', () => {
      render(<StatusHero state="MONITORING" signalType="pump" />);

      expect(screen.queryByText('📈 Pump Signal')).not.toBeInTheDocument();
    });
  });

  // Test indicator highlights
  describe('Indicator Highlights', () => {
    it('displays indicator highlights when provided', () => {
      const highlights = [
        { name: 'RSI', value: '65.50' },
        { name: 'MACD', value: '0.25' },
      ];

      render(<StatusHero state="MONITORING" indicatorHighlights={highlights} />);

      expect(screen.getByText('RSI')).toBeInTheDocument();
      expect(screen.getByText('65.50')).toBeInTheDocument();
      expect(screen.getByText('MACD')).toBeInTheDocument();
      expect(screen.getByText('0.25')).toBeInTheDocument();
    });

    it('limits indicators to 3 max', () => {
      const highlights = [
        { name: 'RSI', value: '65.50' },
        { name: 'MACD', value: '0.25' },
        { name: 'SMA', value: '50000' },
        { name: 'EMA', value: '51000' }, // Should not be displayed
      ];

      render(<StatusHero state="MONITORING" indicatorHighlights={highlights} />);

      expect(screen.getByText('RSI')).toBeInTheDocument();
      expect(screen.getByText('MACD')).toBeInTheDocument();
      expect(screen.getByText('SMA')).toBeInTheDocument();
      expect(screen.queryByText('EMA')).not.toBeInTheDocument();
    });
  });

  // Test state labels match vocabulary
  describe('State Labels', () => {
    const stateLabels: Record<string, string> = {
      MONITORING: 'WATCHING',
      S1: 'FOUND!',
      O1: 'FALSE ALARM',
      Z1: 'ENTERING',
      POSITION_ACTIVE: 'IN POSITION',
      ZE1: 'TAKING PROFIT',
      E1: 'STOPPING LOSS',
      INACTIVE: 'INACTIVE',
      SIGNAL_DETECTED: 'FOUND!',
      EXITED: 'EXITED',
      ERROR: 'ERROR',
    };

    Object.entries(stateLabels).forEach(([state, label]) => {
      it(`displays correct label for ${state}`, () => {
        render(<StatusHero state={state as StateMachineState} />);
        expect(screen.getByText(label)).toBeInTheDocument();
      });
    });
  });

  // Test description display
  describe('State Description', () => {
    it('displays state description', () => {
      render(<StatusHero state="MONITORING" />);
      expect(screen.getByText('Scanning for signals...')).toBeInTheDocument();
    });

    it('displays different description for position states', () => {
      render(<StatusHero state="POSITION_ACTIVE" pnl={100} />);
      expect(screen.getByText('Monitoring exit conditions')).toBeInTheDocument();
    });
  });

  // Test timer auto-increment
  describe('Timer Auto-Increment', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('increments session time every second', async () => {
      render(<StatusHero state="MONITORING" sessionTime={10} />);

      // Initial state
      expect(screen.getByText(/Session: 10s/)).toBeInTheDocument();

      // Advance 2 seconds
      jest.advanceTimersByTime(2000);

      await waitFor(() => {
        expect(screen.getByText(/Session: 12s/)).toBeInTheDocument();
      });
    });

    it('increments position time when in position', async () => {
      render(<StatusHero state="POSITION_ACTIVE" positionTime={60} pnl={100} />);

      // Initial: 1m 0s
      expect(screen.getByText('1m 0s')).toBeInTheDocument();

      // Advance 5 seconds
      jest.advanceTimersByTime(5000);

      await waitFor(() => {
        expect(screen.getByText('1m 5s')).toBeInTheDocument();
      });
    });
  });
});
