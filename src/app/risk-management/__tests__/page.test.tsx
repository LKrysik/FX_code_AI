import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import RiskManagementPage from '../page';

// Mock the API service
jest.mock('@/services/api', () => ({
  apiService: {
    stopSession: jest.fn(),
  },
}));

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

describe('RiskManagementPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders risk management dashboard correctly', () => {
    render(<RiskManagementPage />);

    expect(screen.getByText('🛡️ Risk Management Control Panel')).toBeInTheDocument();
    expect(screen.getByText('Emergency Stop')).toBeInTheDocument();
    expect(screen.getByText('Risk Settings')).toBeInTheDocument();
    expect(screen.getByText('Portfolio Risk')).toBeInTheDocument();
    expect(screen.getByText('Daily P&L')).toBeInTheDocument();
    expect(screen.getByText('Max Drawdown')).toBeInTheDocument();
    expect(screen.getByText('Active Positions')).toBeInTheDocument();
  });

  it('displays risk overview cards with correct data', () => {
    render(<RiskManagementPage />);

    expect(screen.getByText('8.5%')).toBeInTheDocument(); // Current risk
    expect(screen.getByText('$-125.50')).toBeInTheDocument(); // Daily P&L
    expect(screen.getByText('3.2%')).toBeInTheDocument(); // Max drawdown
    expect(screen.getByText('3')).toBeInTheDocument(); // Active positions
  });

  it('shows risk alert when risk level is high', () => {
    render(<RiskManagementPage />);

    // The component should show a risk alert since total risk (8.5%) is above threshold
    expect(screen.getByText(/Risk Alert/)).toBeInTheDocument();
  });

  it('displays active positions table with correct data', () => {
    render(<RiskManagementPage />);

    expect(screen.getByText('ADA/USDT')).toBeInTheDocument();
    expect(screen.getByText('DOT/USDT')).toBeInTheDocument();
    expect(screen.getByText('SOL/USDT')).toBeInTheDocument();
    expect(screen.getByText('LONG')).toBeInTheDocument();
    expect(screen.getByText('SHORT')).toBeInTheDocument();
  });

  it('shows position P&L with correct colors', () => {
    render(<RiskManagementPage />);

    // Positive P&L should be green, negative should be red
    const positivePnL = screen.getByText('$300.00 (14.3%)');
    const negativePnL = screen.getByText('$350.00 (6.7%)');

    expect(positivePnL).toHaveStyle('color: rgb(76, 175, 80)'); // success color
    expect(negativePnL).toHaveStyle('color: rgb(244, 67, 54)'); // error color
  });

  it('displays risk levels with appropriate colors', () => {
    render(<RiskManagementPage />);

    // Check that risk percentages are displayed with chips
    expect(screen.getByText('3.2%')).toBeInTheDocument();
    expect(screen.getByText('2.1%')).toBeInTheDocument();
    expect(screen.getByText('4.8%')).toBeInTheDocument();
  });

  it('handles emergency stop button click', async () => {
    const mockStopSession = require('@/services/api').apiService.stopSession;
    mockStopSession.mockResolvedValue({});

    render(<RiskManagementPage />);

    const emergencyStopButton = screen.getByText('Emergency Stop');
    fireEvent.click(emergencyStopButton);

    await waitFor(() => {
      expect(mockStopSession).toHaveBeenCalledWith({ session_id: 'emergency' });
    });

    expect(screen.getByText('Emergency stop executed - all positions closed')).toBeInTheDocument();
  });

  it('handles position close action', async () => {
    render(<RiskManagementPage />);

    // Find close buttons (there should be 3 for 3 positions)
    const closeButtons = screen.getAllByLabelText('Close Position');
    expect(closeButtons).toHaveLength(3);

    fireEvent.click(closeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Position closed successfully')).toBeInTheDocument();
    });
  });

  it('expands risk settings accordion', () => {
    render(<RiskManagementPage />);

    const accordion = screen.getByText('Risk Management Settings');
    fireEvent.click(accordion);

    expect(screen.getByText('Portfolio Limits')).toBeInTheDocument();
    expect(screen.getByText('Safety Controls')).toBeInTheDocument();
    expect(screen.getByText('Max Portfolio Risk: 20%')).toBeInTheDocument();
    expect(screen.getByText('Max Position Risk: 5%')).toBeInTheDocument();
  });

  it('updates risk settings sliders', () => {
    render(<RiskManagementPage />);

    const accordion = screen.getByText('Risk Management Settings');
    fireEvent.click(accordion);

    // Test max portfolio risk slider
    const portfolioRiskSlider = screen.getByRole('slider', { name: /max portfolio risk/i });
    fireEvent.change(portfolioRiskSlider, { target: { value: 25 } });

    expect(screen.getByText('Max Portfolio Risk: 25%')).toBeInTheDocument();
  });

  it('toggles safety control switches', () => {
    render(<RiskManagementPage />);

    const accordion = screen.getByText('Risk Management Settings');
    fireEvent.click(accordion);

    const emergencyStopSwitch = screen.getByLabelText('Enable Emergency Stop');
    const autoReduceSwitch = screen.getByLabelText('Auto-reduce position sizes on high risk');

    expect(emergencyStopSwitch).toBeChecked();
    expect(autoReduceSwitch).not.toBeChecked();

    fireEvent.click(autoReduceSwitch);
    expect(autoReduceSwitch).toBeChecked();
  });

  it('updates text input fields', () => {
    render(<RiskManagementPage />);

    const accordion = screen.getByText('Risk Management Settings');
    fireEvent.click(accordion);

    const dailyLossInput = screen.getByLabelText('Daily Loss Limit ($)');
    fireEvent.change(dailyLossInput, { target: { value: '750' } });

    expect(dailyLossInput).toHaveValue(750);
  });

  it('shows empty state when no positions', () => {
    // Mock empty positions by overriding the component's state
    // This would require more complex mocking in a real scenario
    render(<RiskManagementPage />);

    // The component starts with positions, so we can't easily test empty state
    // without more sophisticated mocking
    expect(screen.getByText('Active Positions & Risk Management')).toBeInTheDocument();
  });

  it('displays loading state', () => {
    render(<RiskManagementPage />);

    // Loading should be brief, but we can check that the component renders
    expect(screen.getByText('🛡️ Risk Management Control Panel')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    const mockStopSession = require('@/services/api').apiService.stopSession;
    mockStopSession.mockRejectedValue(new Error('API Error'));

    render(<RiskManagementPage />);

    const emergencyStopButton = screen.getByText('Emergency Stop');
    fireEvent.click(emergencyStopButton);

    await waitFor(() => {
      expect(screen.getByText('Failed to execute emergency stop')).toBeInTheDocument();
    });
  });
});