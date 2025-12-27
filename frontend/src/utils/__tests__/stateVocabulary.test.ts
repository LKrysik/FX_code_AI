/**
 * Tests for State Vocabulary Utility
 * ===================================
 * Story 1A-4: Human Vocabulary Labels
 *
 * Verifies centralized vocabulary mapping works correctly.
 */

import {
  STATE_VOCABULARY,
  SIGNAL_TYPE_VOCABULARY,
  getHumanLabel,
  getStateIcon,
  getStateDescription,
  getStateColor,
  getStateVocabulary,
  getSignalLabel,
  getSignalIcon,
  getSignalColor,
  getSignalVocabulary,
  StateMachineState,
  SignalType,
} from '../stateVocabulary';

// ============================================================================
// STATE_VOCABULARY Tests
// ============================================================================

describe('STATE_VOCABULARY', () => {
  it('should have all required state machine states', () => {
    const requiredStates: StateMachineState[] = [
      'INACTIVE',
      'MONITORING',
      'S1',
      'O1',
      'Z1',
      'POSITION_ACTIVE',
      'ZE1',
      'E1',
      'SIGNAL_DETECTED',
      'EXITED',
      'ERROR',
    ];

    requiredStates.forEach((state) => {
      expect(STATE_VOCABULARY[state]).toBeDefined();
      expect(STATE_VOCABULARY[state].label).toBeTruthy();
      expect(STATE_VOCABULARY[state].icon).toBeTruthy();
      expect(STATE_VOCABULARY[state].description).toBeTruthy();
      expect(STATE_VOCABULARY[state].color).toMatch(/^#[0-9A-Fa-f]{6}$/);
    });
  });

  it('should have human-readable labels from UX spec', () => {
    expect(STATE_VOCABULARY.MONITORING.label).toBe('Watching');
    expect(STATE_VOCABULARY.S1.label).toBe('Found!');
    expect(STATE_VOCABULARY.O1.label).toBe('False Alarm');
    expect(STATE_VOCABULARY.Z1.label).toBe('Entering');
    expect(STATE_VOCABULARY.POSITION_ACTIVE.label).toBe('In Position');
    expect(STATE_VOCABULARY.ZE1.label).toBe('Taking Profit');
    expect(STATE_VOCABULARY.E1.label).toBe('Stopping Loss');
  });

  it('should have colors from UX spec', () => {
    expect(STATE_VOCABULARY.MONITORING.color).toBe('#64748B'); // Slate
    expect(STATE_VOCABULARY.S1.color).toBe('#F59E0B'); // Amber
    expect(STATE_VOCABULARY.O1.color).toBe('#6B7280'); // Gray
    expect(STATE_VOCABULARY.Z1.color).toBe('#F59E0B'); // Amber
    expect(STATE_VOCABULARY.POSITION_ACTIVE.color).toBe('#3B82F6'); // Blue
    expect(STATE_VOCABULARY.ZE1.color).toBe('#10B981'); // Green
    expect(STATE_VOCABULARY.E1.color).toBe('#EF4444'); // Red
  });
});

// ============================================================================
// SIGNAL_TYPE_VOCABULARY Tests
// ============================================================================

describe('SIGNAL_TYPE_VOCABULARY', () => {
  it('should have all required signal types', () => {
    const requiredTypes: SignalType[] = ['S1', 'O1', 'Z1', 'ZE1', 'E1', 'pump', 'dump'];

    requiredTypes.forEach((type) => {
      expect(SIGNAL_TYPE_VOCABULARY[type]).toBeDefined();
      expect(SIGNAL_TYPE_VOCABULARY[type].label).toBeTruthy();
      expect(SIGNAL_TYPE_VOCABULARY[type].icon).toBeTruthy();
      expect(SIGNAL_TYPE_VOCABULARY[type].description).toBeTruthy();
      expect(SIGNAL_TYPE_VOCABULARY[type].color).toMatch(/^#[0-9A-Fa-f]{6}$/);
    });
  });

  it('should have human-readable labels for pump/dump', () => {
    expect(SIGNAL_TYPE_VOCABULARY.pump.label).toBe('Pump Detected');
    expect(SIGNAL_TYPE_VOCABULARY.dump.label).toBe('Dump Detected');
  });
});

// ============================================================================
// getHumanLabel Tests
// ============================================================================

describe('getHumanLabel', () => {
  it('should return human label for known states', () => {
    expect(getHumanLabel('MONITORING')).toBe('Watching');
    expect(getHumanLabel('S1')).toBe('Found!');
    expect(getHumanLabel('POSITION_ACTIVE')).toBe('In Position');
  });

  it('should return original code for unknown states', () => {
    expect(getHumanLabel('UNKNOWN_STATE')).toBe('UNKNOWN_STATE');
    expect(getHumanLabel('random')).toBe('random');
  });
});

// ============================================================================
// getStateIcon Tests
// ============================================================================

describe('getStateIcon', () => {
  it('should return icon for known states', () => {
    expect(getStateIcon('MONITORING')).toBe('👀');
    expect(getStateIcon('S1')).toBe('🔥');
    expect(getStateIcon('ZE1')).toBe('💰');
    expect(getStateIcon('E1')).toBe('🛑');
  });

  it('should return fallback icon for unknown states', () => {
    expect(getStateIcon('UNKNOWN')).toBe('❓');
  });
});

// ============================================================================
// getStateDescription Tests
// ============================================================================

describe('getStateDescription', () => {
  it('should return description for known states', () => {
    expect(getStateDescription('MONITORING')).toContain('scanning');
    expect(getStateDescription('S1')).toContain('detected');
    expect(getStateDescription('ZE1')).toContain('profit');
  });

  it('should return fallback description for unknown states', () => {
    expect(getStateDescription('UNKNOWN')).toBe('Unknown state');
  });
});

// ============================================================================
// getStateColor Tests
// ============================================================================

describe('getStateColor', () => {
  it('should return color for known states', () => {
    expect(getStateColor('MONITORING')).toBe('#64748B');
    expect(getStateColor('E1')).toBe('#EF4444');
    expect(getStateColor('ZE1')).toBe('#10B981');
  });

  it('should return fallback color for unknown states', () => {
    expect(getStateColor('UNKNOWN')).toBe('#6B7280');
  });
});

// ============================================================================
// getStateVocabulary Tests
// ============================================================================

describe('getStateVocabulary', () => {
  it('should return complete vocabulary object for known states', () => {
    const vocab = getStateVocabulary('S1');
    expect(vocab.label).toBe('Found!');
    expect(vocab.icon).toBe('🔥');
    expect(vocab.color).toBe('#F59E0B');
    expect(vocab.description).toBeTruthy();
  });

  it('should return fallback object for unknown states', () => {
    const vocab = getStateVocabulary('UNKNOWN');
    expect(vocab.label).toBe('UNKNOWN');
    expect(vocab.icon).toBe('❓');
    expect(vocab.color).toBe('#6B7280');
    expect(vocab.description).toBe('Unknown state');
  });
});

// ============================================================================
// Signal Type Helper Functions Tests
// ============================================================================

describe('getSignalLabel', () => {
  it('should return human label for signal types', () => {
    expect(getSignalLabel('pump')).toBe('Pump Detected');
    expect(getSignalLabel('dump')).toBe('Dump Detected');
    expect(getSignalLabel('S1')).toBe('Entry Signal');
  });

  it('should return original code for unknown signal types', () => {
    expect(getSignalLabel('unknown')).toBe('unknown');
  });
});

describe('getSignalIcon', () => {
  it('should return icon for signal types', () => {
    expect(getSignalIcon('pump')).toBe('📈');
    expect(getSignalIcon('dump')).toBe('📉');
  });

  it('should return fallback icon for unknown types', () => {
    expect(getSignalIcon('unknown')).toBe('❓');
  });
});

describe('getSignalColor', () => {
  it('should return color for signal types', () => {
    expect(getSignalColor('pump')).toBe('#10B981'); // Green
    expect(getSignalColor('dump')).toBe('#EF4444'); // Red
    expect(getSignalColor('S1')).toBe('#F59E0B'); // Amber
  });

  it('should return fallback color for unknown types', () => {
    expect(getSignalColor('unknown')).toBe('#6B7280');
  });
});

describe('getSignalVocabulary', () => {
  it('should return complete vocabulary for signal types', () => {
    const vocab = getSignalVocabulary('pump');
    expect(vocab.label).toBe('Pump Detected');
    expect(vocab.icon).toBe('📈');
    expect(vocab.color).toBe('#10B981');
    expect(vocab.description).toBeTruthy();
  });

  it('should return fallback for unknown signal types', () => {
    const vocab = getSignalVocabulary('unknown');
    expect(vocab.label).toBe('unknown');
    expect(vocab.icon).toBe('❓');
  });
});

// ============================================================================
// Consistency Tests (AC4 - Single source of truth)
// ============================================================================

describe('Vocabulary Consistency', () => {
  it('S1 state and signal vocabulary should match', () => {
    // S1 as state and S1 as signal type should have consistent vocabulary
    expect(STATE_VOCABULARY.S1.label).toBe('Found!');
    expect(SIGNAL_TYPE_VOCABULARY.S1.label).toBe('Entry Signal');
    // Different labels but consistent colors
    expect(STATE_VOCABULARY.S1.color).toBe(SIGNAL_TYPE_VOCABULARY.S1.color);
  });

  it('SIGNAL_DETECTED should map to S1 vocabulary', () => {
    // SIGNAL_DETECTED is legacy - should match S1
    expect(STATE_VOCABULARY.SIGNAL_DETECTED.label).toBe(STATE_VOCABULARY.S1.label);
    expect(STATE_VOCABULARY.SIGNAL_DETECTED.icon).toBe(STATE_VOCABULARY.S1.icon);
    expect(STATE_VOCABULARY.SIGNAL_DETECTED.color).toBe(STATE_VOCABULARY.S1.color);
  });
});
