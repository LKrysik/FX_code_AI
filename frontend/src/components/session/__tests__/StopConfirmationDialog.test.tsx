/**
 * StopConfirmationDialog Component Tests
 * =======================================
 * Story: 1b-8-emergency-stop-button
 *
 * Tests for:
 * - AC3: Dialog shows warning about irreversibility
 * - AC4: Confirm with Enter or cancel with Esc
 * - Focus management
 * - Loading state
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StopConfirmationDialog } from '../StopConfirmationDialog';

// Mock the logger
jest.mock('@/services/frontendLogService', () => ({
  Logger: {
    info: jest.fn(),
    debug: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  },
}));

describe('StopConfirmationDialog', () => {
  const defaultProps = {
    open: true,
    onConfirm: jest.fn(),
    onCancel: jest.fn(),
    isLoading: false,
    sessionId: 'test-session-123',
    sessionType: 'paper',
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders when open is true', () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      expect(screen.getByTestId('stop-confirmation-dialog')).toBeInTheDocument();
    });

    it('does not render when open is false', () => {
      render(<StopConfirmationDialog {...defaultProps} open={false} />);

      expect(screen.queryByTestId('stop-confirmation-dialog')).not.toBeInTheDocument();
    });

    it('displays session type in title', () => {
      render(<StopConfirmationDialog {...defaultProps} sessionType="paper" />);

      expect(screen.getByText(/Stop Paper Trading Session\?/)).toBeInTheDocument();
    });

    it('displays session ID', () => {
      render(<StopConfirmationDialog {...defaultProps} sessionId="test-session-123" />);

      expect(screen.getByText(/test-session-123/)).toBeInTheDocument();
    });
  });

  describe('AC3: Warning Content', () => {
    it('shows warning about irreversibility', () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      expect(screen.getByText(/This action cannot be undone/)).toBeInTheDocument();
    });

    it('lists what will happen on stop', () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      expect(screen.getByText(/All open positions will be closed/)).toBeInTheDocument();
      expect(screen.getByText(/Final P&L will be calculated/)).toBeInTheDocument();
      expect(screen.getByText(/Partial results will be preserved/)).toBeInTheDocument();
      expect(screen.getByText(/Session status will show/)).toBeInTheDocument();
    });
  });

  describe('Button Labels', () => {
    it('shows keyboard shortcut hints on buttons', () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      expect(screen.getByText(/Cancel \(Esc\)/)).toBeInTheDocument();
      expect(screen.getByText(/Stop Session \(Enter\)/)).toBeInTheDocument();
    });
  });

  describe('AC4: Keyboard Shortcuts', () => {
    it('calls onConfirm when Enter is pressed', async () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      fireEvent.keyDown(window, { key: 'Enter' });

      expect(defaultProps.onConfirm).toHaveBeenCalled();
    });

    it('calls onCancel when Escape is pressed', async () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      fireEvent.keyDown(window, { key: 'Escape' });

      expect(defaultProps.onCancel).toHaveBeenCalled();
    });

    it('does not trigger shortcuts when loading', async () => {
      render(<StopConfirmationDialog {...defaultProps} isLoading={true} />);

      fireEvent.keyDown(window, { key: 'Enter' });
      fireEvent.keyDown(window, { key: 'Escape' });

      expect(defaultProps.onConfirm).not.toHaveBeenCalled();
      expect(defaultProps.onCancel).not.toHaveBeenCalled();
    });

    it('does not trigger shortcuts when dialog is closed', async () => {
      render(<StopConfirmationDialog {...defaultProps} open={false} />);

      fireEvent.keyDown(window, { key: 'Enter' });

      expect(defaultProps.onConfirm).not.toHaveBeenCalled();
    });
  });

  describe('Button Clicks', () => {
    it('calls onConfirm when confirm button is clicked', async () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      const confirmButton = screen.getByTestId('stop-dialog-confirm-button');
      await userEvent.click(confirmButton);

      expect(defaultProps.onConfirm).toHaveBeenCalled();
    });

    it('calls onCancel when cancel button is clicked', async () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      const cancelButton = screen.getByTestId('stop-dialog-cancel-button');
      await userEvent.click(cancelButton);

      expect(defaultProps.onCancel).toHaveBeenCalled();
    });
  });

  describe('Loading State', () => {
    it('disables buttons when loading', () => {
      render(<StopConfirmationDialog {...defaultProps} isLoading={true} />);

      expect(screen.getByTestId('stop-dialog-confirm-button')).toBeDisabled();
      expect(screen.getByTestId('stop-dialog-cancel-button')).toBeDisabled();
    });

    it('shows "Stopping..." text when loading', () => {
      render(<StopConfirmationDialog {...defaultProps} isLoading={true} />);

      expect(screen.getByText('Stopping...')).toBeInTheDocument();
    });

    it('shows loading spinner when loading', () => {
      render(<StopConfirmationDialog {...defaultProps} isLoading={true} />);

      // MUI CircularProgress renders with role="progressbar"
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  describe('Focus Management', () => {
    it('focuses confirm button when dialog opens', async () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      await waitFor(() => {
        const confirmButton = screen.getByTestId('stop-dialog-confirm-button');
        expect(document.activeElement).toBe(confirmButton);
      }, { timeout: 100 });
    });
  });

  describe('Session Type Display', () => {
    it('displays "Backtest" for backtest session type', () => {
      render(<StopConfirmationDialog {...defaultProps} sessionType="backtest" />);

      expect(screen.getByText(/Stop Backtest Session\?/)).toBeInTheDocument();
    });

    it('displays "Live Trading" for live session type', () => {
      render(<StopConfirmationDialog {...defaultProps} sessionType="live" />);

      expect(screen.getByText(/Stop Live Trading Session\?/)).toBeInTheDocument();
    });

    it('displays "Trading" for unknown session type', () => {
      render(<StopConfirmationDialog {...defaultProps} sessionType={undefined} />);

      expect(screen.getByText(/Stop Trading Session\?/)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper dialog role', () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('has aria-labelledby', () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-labelledby', 'stop-confirmation-dialog-title');
    });

    it('has aria-describedby', () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-describedby', 'stop-confirmation-dialog-description');
    });
  });

  describe('Event Prevention', () => {
    it('prevents default on Enter key', () => {
      render(<StopConfirmationDialog {...defaultProps} />);

      const event = new KeyboardEvent('keydown', {
        key: 'Enter',
        bubbles: true,
        cancelable: true,
      });
      const preventDefaultSpy = jest.spyOn(event, 'preventDefault');

      window.dispatchEvent(event);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });
});
