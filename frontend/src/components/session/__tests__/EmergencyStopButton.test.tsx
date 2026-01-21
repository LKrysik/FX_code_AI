/**
 * EmergencyStopButton Component Tests
 * ====================================
 * Story: 1b-8-emergency-stop-button
 *
 * Tests for:
 * - AC1: Prominent red "STOP" button is always visible when session is active
 * - AC2: Button is labeled clearly (text, not just icon)
 * - Button click opens confirmation dialog
 * - Button disabled when no session active
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EmergencyStopButton } from '../EmergencyStopButton';

// Mock the stores
jest.mock('@/stores/tradingStore', () => ({
  useCurrentSession: jest.fn(),
  useTradingActions: jest.fn(() => ({
    stopSession: jest.fn(),
  })),
}));

jest.mock('@/stores/uiStore', () => ({
  useUIActions: jest.fn(() => ({
    addNotification: jest.fn(),
  })),
}));

// Mock the logger
jest.mock('@/services/frontendLogService', () => ({
  Logger: {
    info: jest.fn(),
    debug: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  },
}));

import { useCurrentSession, useTradingActions } from '@/stores/tradingStore';
import { useUIActions } from '@/stores/uiStore';

const mockUseCurrentSession = useCurrentSession as jest.Mock;
const mockUseTradingActions = useTradingActions as jest.Mock;
const mockUseUIActions = useUIActions as jest.Mock;

describe('EmergencyStopButton', () => {
  const mockStopSession = jest.fn();
  const mockAddNotification = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockStopSession.mockResolvedValue(undefined);
    mockUseTradingActions.mockReturnValue({
      stopSession: mockStopSession,
    });
    mockUseUIActions.mockReturnValue({
      addNotification: mockAddNotification,
    });
  });

  describe('Visibility and Rendering', () => {
    it('AC1: renders when session is active', () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton />);

      expect(screen.getByTestId('emergency-stop-button')).toBeInTheDocument();
    });

    it('AC1: does not render when no session is active', () => {
      mockUseCurrentSession.mockReturnValue(null);

      render(<EmergencyStopButton />);

      expect(screen.queryByTestId('emergency-stop-button')).not.toBeInTheDocument();
    });

    it('AC1: does not render when session status is not active', () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'idle',
        type: 'paper',
        symbols: [],
      });

      render(<EmergencyStopButton />);

      expect(screen.queryByTestId('emergency-stop-button')).not.toBeInTheDocument();
    });

    it('renders even when session inactive if showOnlyWhenActive is false', () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'idle',
        type: 'paper',
        symbols: [],
      });

      render(<EmergencyStopButton showOnlyWhenActive={false} />);

      const button = screen.getByTestId('emergency-stop-button');
      expect(button).toBeInTheDocument();
      expect(button).toBeDisabled();
    });
  });

  describe('Button Label and Appearance', () => {
    it('AC2: displays "STOP" text label', () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton />);

      expect(screen.getByText('STOP')).toBeInTheDocument();
    });

    it('AC2: has error/red color variant', () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton />);

      const button = screen.getByTestId('emergency-stop-button');
      expect(button).toHaveClass('MuiButton-containedError');
    });

    it('includes stop icon', () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton />);

      // Check for MUI icon (SVG with data-testid)
      const button = screen.getByTestId('emergency-stop-button');
      const svg = button.querySelector('svg');
      expect(svg).toBeInTheDocument();
    });
  });

  describe('Dialog Interaction', () => {
    it('opens confirmation dialog when clicked', async () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton />);

      const button = screen.getByTestId('emergency-stop-button');
      await userEvent.click(button);

      expect(screen.getByTestId('stop-confirmation-dialog')).toBeInTheDocument();
    });

    it('closes dialog when cancelled', async () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton />);

      // Open dialog
      const button = screen.getByTestId('emergency-stop-button');
      await userEvent.click(button);

      expect(screen.getByTestId('stop-confirmation-dialog')).toBeInTheDocument();

      // Cancel dialog
      const cancelButton = screen.getByTestId('stop-dialog-cancel-button');
      await userEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByTestId('stop-confirmation-dialog')).not.toBeInTheDocument();
      });
    });

    it('calls stopSession when confirmed', async () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton />);

      // Open dialog
      const button = screen.getByTestId('emergency-stop-button');
      await userEvent.click(button);

      // Confirm stop
      const confirmButton = screen.getByTestId('stop-dialog-confirm-button');
      await userEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockStopSession).toHaveBeenCalledWith('test-session-123');
      });
    });

    it('shows notification on successful stop', async () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton />);

      // Open and confirm
      await userEvent.click(screen.getByTestId('emergency-stop-button'));
      await userEvent.click(screen.getByTestId('stop-dialog-confirm-button'));

      await waitFor(() => {
        expect(mockAddNotification).toHaveBeenCalledWith({
          type: 'warning',
          message: 'Trading session stopped by user',
          autoHide: true,
        });
      });
    });
  });

  describe('Custom Props', () => {
    it('uses custom onStop callback when provided', async () => {
      const customOnStop = jest.fn().mockResolvedValue(undefined);

      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton onStop={customOnStop} />);

      // Open and confirm
      await userEvent.click(screen.getByTestId('emergency-stop-button'));
      await userEvent.click(screen.getByTestId('stop-dialog-confirm-button'));

      await waitFor(() => {
        expect(customOnStop).toHaveBeenCalled();
        expect(mockStopSession).not.toHaveBeenCalled();
      });
    });

    it('uses prop sessionId over store sessionId', async () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'store-session',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton sessionId="prop-session" />);

      await userEvent.click(screen.getByTestId('emergency-stop-button'));
      await userEvent.click(screen.getByTestId('stop-dialog-confirm-button'));

      await waitFor(() => {
        expect(mockStopSession).toHaveBeenCalledWith('prop-session');
      });
    });

    it('respects disabled prop', () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton disabled={true} />);

      const button = screen.getByTestId('emergency-stop-button');
      expect(button).toBeDisabled();
    });
  });

  describe('Loading State', () => {
    it('shows loading state during stop operation', async () => {
      // Make stop take some time
      mockStopSession.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton />);

      await userEvent.click(screen.getByTestId('emergency-stop-button'));
      await userEvent.click(screen.getByTestId('stop-dialog-confirm-button'));

      // Should show "STOPPING..." during operation
      await waitFor(() => {
        expect(screen.getByText('Stopping...')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper aria-label', () => {
      mockUseCurrentSession.mockReturnValue({
        sessionId: 'test-session-123',
        status: 'running',
        type: 'paper',
        symbols: ['BTC_USDT'],
      });

      render(<EmergencyStopButton />);

      const button = screen.getByTestId('emergency-stop-button');
      expect(button).toHaveAttribute('aria-label', 'Emergency Stop - Stop trading session');
    });
  });
});
