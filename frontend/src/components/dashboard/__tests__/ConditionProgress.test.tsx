/**
 * ConditionProgress Component Tests
 * ==================================
 *
 * Tests for the ConditionProgress component (SM-03)
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ConditionProgress, { ConditionGroup } from '../ConditionProgress';

// ============================================================================
// Mock Data
// ============================================================================

const mockGroups: ConditionGroup[] = [
  {
    section: 'S1',
    label: 'Pump Detection',
    logic: 'AND',
    all_met: true,
    conditions: [
      {
        indicator_name: 'PUMP_MAGNITUDE_PCT',
        operator: '>',
        threshold: 5.0,
        current_value: 7.2,
        met: true,
      },
      {
        indicator_name: 'VOLUME_SPIKE',
        operator: '>',
        threshold: 3.0,
        current_value: 4.5,
        met: true,
      },
    ],
  },
  {
    section: 'Z1',
    label: 'Peak Entry',
    logic: 'AND',
    all_met: false,
    conditions: [
      {
        indicator_name: 'PEAK_CONFIRMED',
        operator: '==',
        threshold: 1.0,
        current_value: 0.0,
        met: false,
      },
      {
        indicator_name: 'RSI',
        operator: '>',
        threshold: 70.0,
        current_value: 65.3,
        met: false,
      },
    ],
  },
];

// ============================================================================
// Tests
// ============================================================================

describe('ConditionProgress', () => {
  it('renders without crashing', () => {
    render(
      <ConditionProgress groups={mockGroups} currentState="MONITORING" isLoading={false} />
    );

    expect(screen.getByText('Condition Progress')).toBeInTheDocument();
  });

  it('displays section headers correctly', () => {
    render(
      <ConditionProgress groups={mockGroups} currentState="MONITORING" isLoading={false} />
    );

    expect(screen.getByText(/S1: Pump Detection/)).toBeInTheDocument();
    expect(screen.getByText(/Z1: Peak Entry/)).toBeInTheDocument();
  });

  it('shows met/total condition counts', () => {
    render(
      <ConditionProgress groups={mockGroups} currentState="MONITORING" isLoading={false} />
    );

    // S1 has 2/2 conditions met
    expect(screen.getByText('2/2')).toBeInTheDocument();

    // Z1 has 0/2 conditions met
    expect(screen.getByText('0/2')).toBeInTheDocument();
  });

  it('displays current state badge', () => {
    render(
      <ConditionProgress groups={mockGroups} currentState="SIGNAL_DETECTED" isLoading={false} />
    );

    expect(screen.getByText('SIGNAL_DETECTED')).toBeInTheDocument();
  });

  it('shows loading skeleton when isLoading is true', () => {
    render(<ConditionProgress groups={[]} currentState="MONITORING" isLoading={true} />);

    // Check for skeleton elements (MUI Skeleton renders with specific classes)
    const skeletons = document.querySelectorAll('.MuiSkeleton-root');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('displays empty state when no groups are provided', () => {
    render(<ConditionProgress groups={[]} currentState="MONITORING" isLoading={false} />);

    expect(screen.getByText('No conditions configured for this session')).toBeInTheDocument();
  });

  it('renders condition names and thresholds', () => {
    render(
      <ConditionProgress groups={mockGroups} currentState="MONITORING" isLoading={false} />
    );

    // Check for condition indicators (after expanding accordion)
    expect(screen.getByText(/PUMP_MAGNITUDE_PCT/)).toBeInTheDocument();
  });

  it('highlights active section based on currentState', () => {
    const { container } = render(
      <ConditionProgress groups={mockGroups} currentState="SIGNAL_DETECTED" isLoading={false} />
    );

    // SIGNAL_DETECTED activates both S1 and Z1 sections (multiple can be active)
    const activeLabels = screen.getAllByText('ACTIVE');
    expect(activeLabels.length).toBeGreaterThan(0);
  });

  it('displays logic type (AND/OR) for each group', () => {
    render(
      <ConditionProgress groups={mockGroups} currentState="MONITORING" isLoading={false} />
    );

    // Check for logic indicators in accordion details
    const logicTexts = screen.getAllByText(/Logic:/);
    expect(logicTexts.length).toBeGreaterThan(0);
  });
});

// ============================================================================
// Edge Cases
// ============================================================================

describe('ConditionProgress - Edge Cases', () => {
  it('handles groups with no conditions', () => {
    const emptyGroup: ConditionGroup = {
      section: 'E1',
      label: 'Emergency Exit',
      logic: 'OR',
      all_met: false,
      conditions: [],
    };

    render(
      <ConditionProgress groups={[emptyGroup]} currentState="MONITORING" isLoading={false} />
    );

    expect(screen.getByText(/E1: Emergency Exit/)).toBeInTheDocument();
  });

  it('renders correctly with all sections', () => {
    const allSections: ConditionGroup[] = [
      {
        section: 'S1',
        label: 'Pump Detection',
        logic: 'AND',
        all_met: false,
        conditions: [],
      },
      {
        section: 'O1',
        label: 'Cancel',
        logic: 'OR',
        all_met: false,
        conditions: [],
      },
      {
        section: 'Z1',
        label: 'Peak Entry',
        logic: 'AND',
        all_met: false,
        conditions: [],
      },
      {
        section: 'ZE1',
        label: 'Dump End Close',
        logic: 'AND',
        all_met: false,
        conditions: [],
      },
      {
        section: 'E1',
        label: 'Emergency Exit',
        logic: 'OR',
        all_met: false,
        conditions: [],
      },
    ];

    render(
      <ConditionProgress groups={allSections} currentState="MONITORING" isLoading={false} />
    );

    expect(screen.getByText(/S1: Pump Detection/)).toBeInTheDocument();
    expect(screen.getByText(/O1: Cancel/)).toBeInTheDocument();
    expect(screen.getByText(/Z1: Peak Entry/)).toBeInTheDocument();
    expect(screen.getByText(/ZE1: Dump End Close/)).toBeInTheDocument();
    expect(screen.getByText(/E1: Emergency Exit/)).toBeInTheDocument();
  });

  it('handles extreme numeric values', () => {
    const extremeGroup: ConditionGroup = {
      section: 'S1',
      label: 'Test',
      logic: 'AND',
      all_met: false,
      conditions: [
        {
          indicator_name: 'LARGE_NUMBER',
          operator: '>',
          threshold: 1000000.0,
          current_value: 1500000.5,
          met: true,
        },
        {
          indicator_name: 'SMALL_NUMBER',
          operator: '<',
          threshold: 0.0001,
          current_value: 0.00005,
          met: true,
        },
      ],
    };

    render(
      <ConditionProgress groups={[extremeGroup]} currentState="MONITORING" isLoading={false} />
    );

    // Component should render without errors
    expect(screen.getByText(/Condition Progress/)).toBeInTheDocument();
  });
});
