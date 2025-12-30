/**
 * WelcomeTooltip Component Tests
 * ==============================
 * Story 1A-7: First-Visit Onboarding Tooltip
 *
 * AC2: Tooltip explains dashboard purpose
 * AC3: Tooltip points to key areas
 * AC5: Non-blocking (user can interact)
 */

import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { WelcomeTooltip, WelcomeTooltipProps } from '../WelcomeTooltip';

// Mock MUI components
jest.mock('@mui/material', () => ({
  Paper: ({ children, elevation, sx }: any) => (
    <div data-testid="tooltip-paper" data-elevation={elevation} style={sx}>
      {children}
    </div>
  ),
  Box: ({ children, sx }: any) => <div style={sx}>{children}</div>,
  Typography: ({ children, variant, component, sx, color }: any) => (
    <span data-testid={`typography-${variant || 'default'}`} data-color={color}>
      {children}
    </span>
  ),
  Button: ({ children, onClick, variant, color, size, fullWidth, sx }: any) => (
    <button
      data-testid="dismiss-button"
      onClick={onClick}
      data-variant={variant}
      data-color={color}
      data-size={size}
      data-fullwidth={fullWidth}
    >
      {children}
    </button>
  ),
  List: ({ children }: any) => <ul data-testid="feature-list">{children}</ul>,
  ListItem: ({ children }: any) => <li>{children}</li>,
  ListItemIcon: ({ children }: any) => <span data-testid="list-icon">{children}</span>,
  ListItemText: ({ primary }: any) => <span>{primary}</span>,
  Fade: ({ children, in: fadeIn }: any) => (
    <div data-testid="fade-wrapper" data-visible={fadeIn}>
      {children}
    </div>
  ),
  Popper: ({ children, open, anchorEl, placement }: any) => (
    open ? (
      <div data-testid="popper" data-placement={placement}>
        {children}
      </div>
    ) : null
  ),
  ClickAwayListener: ({ children, onClickAway }: any) => (
    <div data-testid="click-away-listener" onClick={onClickAway}>
      {children}
    </div>
  ),
  useTheme: () => ({
    palette: {
      mode: 'light',
      primary: { main: '#1976d2' },
      background: { paper: '#fff' },
      divider: '#e0e0e0',
    },
    shadows: Array(25).fill('none'),
    zIndex: {
      tooltip: 1500,
    },
  }),
  alpha: (color: string, opacity: number) => `rgba(${color}, ${opacity})`,
  styled: (component: any) => (styles: any) => component,
}));

jest.mock('@mui/icons-material', () => ({
  TrendingUp: () => <span data-testid="icon-signals">SignalsIcon</span>,
  Visibility: () => <span data-testid="icon-state">StateIcon</span>,
  ShowChart: () => <span data-testid="icon-indicators">IndicatorsIcon</span>,
  Close: () => <span data-testid="icon-close">CloseIcon</span>,
  Celebration: () => <span data-testid="icon-celebration">CelebrationIcon</span>,
}));

describe('WelcomeTooltip', () => {
  const defaultProps: WelcomeTooltipProps = {
    onDismiss: jest.fn(),
    open: true,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('AC2: Tooltip explains dashboard purpose', () => {
    it('displays welcome heading', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      expect(screen.getByText(/Welcome to FX Agent AI/i)).toBeInTheDocument();
    });

    it('explains that this is the trading dashboard', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      expect(screen.getByText(/trading dashboard/i)).toBeInTheDocument();
    });

    it('mentions signals will appear here', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      expect(screen.getByText(/Signals when the system detects/i)).toBeInTheDocument();
    });
  });

  describe('AC3: Tooltip points to key areas', () => {
    it('highlights signals area', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      expect(screen.getByText(/Signals when the system detects opportunities/i)).toBeInTheDocument();
    });

    it('highlights strategy state area', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      expect(screen.getByText(/Current state of your trading strategy/i)).toBeInTheDocument();
    });

    it('highlights indicators area', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      expect(screen.getByText(/Real-time indicator values/i)).toBeInTheDocument();
    });

    it('renders feature list with icons', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      expect(screen.getByTestId('feature-list')).toBeInTheDocument();
    });
  });

  describe('AC5: Non-blocking', () => {
    it('renders as a floating tooltip (not modal)', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      // Popper/floating component, not a dialog/modal
      expect(screen.getByTestId('tooltip-paper')).toBeInTheDocument();
    });

    it('does not have backdrop overlay', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      expect(screen.queryByTestId('backdrop')).not.toBeInTheDocument();
    });
  });

  describe('Dismiss functionality', () => {
    it('shows "Got it!" dismiss button', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      expect(screen.getByTestId('dismiss-button')).toHaveTextContent(/Got it/i);
    });

    it('calls onDismiss when dismiss button is clicked', () => {
      const onDismiss = jest.fn();
      render(<WelcomeTooltip {...defaultProps} onDismiss={onDismiss} />);

      fireEvent.click(screen.getByTestId('dismiss-button'));
      expect(onDismiss).toHaveBeenCalledTimes(1);
    });
  });

  describe('Visibility control', () => {
    it('renders when open is true', () => {
      render(<WelcomeTooltip {...defaultProps} open={true} />);
      expect(screen.getByTestId('tooltip-paper')).toBeInTheDocument();
    });

    it('does not render when open is false', () => {
      render(<WelcomeTooltip {...defaultProps} open={false} />);
      expect(screen.queryByTestId('tooltip-paper')).not.toBeInTheDocument();
    });
  });

  describe('Quick Start CTA', () => {
    it('mentions Quick Start option', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      expect(screen.getByText(/Quick Start/i)).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('uses elevated paper for prominence', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      const paper = screen.getByTestId('tooltip-paper');
      expect(paper).toHaveAttribute('data-elevation', '8');
    });
  });

  describe('Accessibility', () => {
    it('dismiss button is keyboard accessible', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      const button = screen.getByTestId('dismiss-button');
      expect(button).toBeInTheDocument();
      expect(button.tagName.toLowerCase()).toBe('button');
    });
  });

  describe('Animation', () => {
    it('uses fade animation wrapper', () => {
      render(<WelcomeTooltip {...defaultProps} />);
      expect(screen.getByTestId('fade-wrapper')).toBeInTheDocument();
    });
  });
});
