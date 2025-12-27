/**
 * SignalCard Component Tests
 * ==========================
 * Story 1A-1: Signal Display on Dashboard
 *
 * Tests for AC2: Signal display includes type, symbol, timestamp, indicator value
 * Tests for AC5: Prominent styling
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { SignalCard, SignalCardProps } from '../SignalCard';

// Mock MUI components
jest.mock('@mui/material', () => ({
  Card: ({ children, onClick, sx }: any) => (
    <div data-testid="signal-card" onClick={onClick} style={sx}>
      {children}
    </div>
  ),
  CardContent: ({ children }: any) => <div>{children}</div>,
  Box: ({ children }: any) => <div>{children}</div>,
  Typography: ({ children, variant }: any) => (
    <span data-testid={`typography-${variant}`}>{children}</span>
  ),
  Chip: ({ label }: any) => <span data-testid="chip">{label}</span>,
  LinearProgress: ({ value }: any) => (
    <div data-testid="progress-bar" data-value={value} />
  ),
  // Story 1A-6: Added useTheme mock for signal type color coding
  useTheme: () => ({
    palette: {
      mode: 'light',
    },
  }),
  alpha: (color: string, opacity: number) => `rgba(${color}, ${opacity})`,
}));

jest.mock('@mui/icons-material', () => ({
  TrendingUp: () => <span data-testid="pump-icon">PumpIcon</span>,
  TrendingDown: () => <span data-testid="dump-icon">DumpIcon</span>,
}));

describe('SignalCard', () => {
  const defaultProps: SignalCardProps = {
    id: 'signal_123',
    symbol: 'BTCUSDT',
    signalType: 'pump',
    magnitude: 7.25,
    confidence: 85,
    timestamp: new Date().toISOString(),
    strategy: 'pump_detection_v1',
  };

  describe('AC2: Display includes type, symbol, timestamp, indicator value', () => {
    it('displays the symbol', () => {
      render(<SignalCard {...defaultProps} />);
      expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    });

    it('displays signal type as PUMP for pump signals', () => {
      render(<SignalCard {...defaultProps} signalType="pump" />);
      // Story 1A-6: Uses human-readable label with emoji
      expect(screen.getByTestId('chip')).toHaveTextContent('Pump Detected');
    });

    it('displays signal type as DUMP for dump signals', () => {
      render(<SignalCard {...defaultProps} signalType="dump" />);
      // Story 1A-6: Uses human-readable label with emoji
      expect(screen.getByTestId('chip')).toHaveTextContent('Dump Detected');
    });

    it('displays magnitude with percentage', () => {
      render(<SignalCard {...defaultProps} magnitude={7.25} />);
      expect(screen.getByText('+7.25%')).toBeInTheDocument();
    });

    it('displays negative magnitude correctly', () => {
      render(<SignalCard {...defaultProps} magnitude={-3.5} />);
      expect(screen.getByText('-3.50%')).toBeInTheDocument();
    });

    it('displays confidence percentage', () => {
      render(<SignalCard {...defaultProps} confidence={85} />);
      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('displays strategy when provided', () => {
      render(<SignalCard {...defaultProps} strategy="my_strategy" />);
      expect(screen.getByText(/Strategy: my_strategy/)).toBeInTheDocument();
    });
  });

  describe('AC5: Prominent styling', () => {
    it('renders pump icon for pump signals', () => {
      render(<SignalCard {...defaultProps} signalType="pump" />);
      expect(screen.getByTestId('pump-icon')).toBeInTheDocument();
    });

    it('renders dump icon for dump signals', () => {
      render(<SignalCard {...defaultProps} signalType="dump" />);
      expect(screen.getByTestId('dump-icon')).toBeInTheDocument();
    });

    it('renders confidence progress bar', () => {
      render(<SignalCard {...defaultProps} confidence={75} />);
      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('data-value', '75');
    });
  });

  describe('Interactions', () => {
    it('calls onClick when card is clicked', () => {
      const onClick = jest.fn();
      render(<SignalCard {...defaultProps} onClick={onClick} />);

      fireEvent.click(screen.getByTestId('signal-card'));
      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('does not crash when onClick is not provided', () => {
      render(<SignalCard {...defaultProps} onClick={undefined} />);
      expect(() => fireEvent.click(screen.getByTestId('signal-card'))).not.toThrow();
    });
  });

  describe('Timestamp formatting', () => {
    it('formats recent timestamps as relative time', () => {
      const recentTime = new Date(Date.now() - 30000).toISOString(); // 30 seconds ago
      render(<SignalCard {...defaultProps} timestamp={recentTime} />);
      expect(screen.getByText(/30s ago/)).toBeInTheDocument();
    });
  });

  describe('Edge cases', () => {
    it('handles zero magnitude', () => {
      render(<SignalCard {...defaultProps} magnitude={0} />);
      expect(screen.getByText('+0.00%')).toBeInTheDocument();
    });

    it('handles zero confidence', () => {
      render(<SignalCard {...defaultProps} confidence={0} />);
      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('handles 100% confidence', () => {
      render(<SignalCard {...defaultProps} confidence={100} />);
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('handles missing strategy', () => {
      render(<SignalCard {...defaultProps} strategy={undefined} />);
      expect(screen.queryByText(/Strategy:/)).not.toBeInTheDocument();
    });
  });
});
