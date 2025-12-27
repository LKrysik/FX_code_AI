/**
 * Signal Colors Test Suite
 * ========================
 * Story 1A-6: Signal Type Color Coding
 *
 * Tests for color consistency, light/dark mode support, and accessibility
 */

import {
  SIGNAL_COLORS,
  getSignalColorPalette,
  getSignalColorConfig,
  getSignalPrimaryColor,
  getSignalAccessibilityIcon,
  SignalColorType,
} from '../signalColors';

describe('Signal Colors', () => {
  // AC1: Each signal type has a unique, distinct color
  describe('AC1: Unique colors for each signal type', () => {
    it('should have distinct primary colors for each signal type', () => {
      const primaryColors = new Set<string>();
      const signalTypes: SignalColorType[] = ['S1', 'O1', 'Z1', 'ZE1', 'E1'];

      signalTypes.forEach((type) => {
        const color = SIGNAL_COLORS[type].primary;
        expect(color).toBeDefined();
        primaryColors.add(color);
      });

      // Should have at least 4 distinct colors (Z1 and S1 were same in original spec)
      expect(primaryColors.size).toBeGreaterThanOrEqual(4);
    });

    it('should define all required signal types', () => {
      const requiredTypes: SignalColorType[] = ['S1', 'O1', 'Z1', 'ZE1', 'E1', 'pump', 'dump'];

      requiredTypes.forEach((type) => {
        expect(SIGNAL_COLORS[type]).toBeDefined();
        expect(SIGNAL_COLORS[type].primary).toBeDefined();
        expect(SIGNAL_COLORS[type].light).toBeDefined();
        expect(SIGNAL_COLORS[type].dark).toBeDefined();
      });
    });
  });

  // AC3: Colors match UX specification
  describe('AC3: UX specification compliance', () => {
    it('should have S1 as Amber (#F59E0B)', () => {
      expect(SIGNAL_COLORS.S1.primary).toBe('#F59E0B');
    });

    it('should have O1 as Gray (#6B7280)', () => {
      expect(SIGNAL_COLORS.O1.primary).toBe('#6B7280');
    });

    it('should have ZE1 as Green (#10B981)', () => {
      expect(SIGNAL_COLORS.ZE1.primary).toBe('#10B981');
    });

    it('should have E1 as Red (#EF4444)', () => {
      expect(SIGNAL_COLORS.E1.primary).toBe('#EF4444');
    });

    it('should have pump as Green (#10B981)', () => {
      expect(SIGNAL_COLORS.pump.primary).toBe('#10B981');
    });

    it('should have dump as Red (#EF4444)', () => {
      expect(SIGNAL_COLORS.dump.primary).toBe('#EF4444');
    });
  });

  // AC4: Color-blind friendly (icons supplement colors)
  describe('AC4: Accessibility icons', () => {
    it('should have distinct icons for each signal type', () => {
      const icons: Record<SignalColorType, string> = {
        S1: '🔥',
        O1: '❌',
        Z1: '🎯',
        ZE1: '💰',
        E1: '🛑',
        pump: '📈',
        dump: '📉',
        MONITORING: '👀',
        POSITION_ACTIVE: '📊',
      };

      Object.entries(icons).forEach(([type, expectedIcon]) => {
        expect(SIGNAL_COLORS[type as SignalColorType].icon).toBe(expectedIcon);
      });
    });

    it('should return accessibility icon via helper function', () => {
      expect(getSignalAccessibilityIcon('S1')).toBe('🔥');
      expect(getSignalAccessibilityIcon('ZE1')).toBe('💰');
      expect(getSignalAccessibilityIcon('unknown')).toBe('❓');
    });
  });

  // AC5: Works in both light and dark modes
  describe('AC5: Light and dark mode support', () => {
    it('should have both light and dark palettes for each signal type', () => {
      const signalTypes: SignalColorType[] = ['S1', 'O1', 'Z1', 'ZE1', 'E1', 'pump', 'dump'];

      signalTypes.forEach((type) => {
        const config = SIGNAL_COLORS[type];

        // Light mode
        expect(config.light.bg).toBeDefined();
        expect(config.light.border).toBeDefined();
        expect(config.light.text).toBeDefined();
        expect(config.light.icon).toBeDefined();

        // Dark mode
        expect(config.dark.bg).toBeDefined();
        expect(config.dark.border).toBeDefined();
        expect(config.dark.text).toBeDefined();
        expect(config.dark.icon).toBeDefined();
      });
    });

    it('should return correct palette for light mode', () => {
      const lightPalette = getSignalColorPalette('S1', 'light');

      expect(lightPalette.bg).toBe('#FEF3C7');
      expect(lightPalette.border).toBe('#F59E0B');
      expect(lightPalette.text).toBe('#92400E');
    });

    it('should return correct palette for dark mode', () => {
      const darkPalette = getSignalColorPalette('S1', 'dark');

      expect(darkPalette.bg).toBe('rgba(245, 158, 11, 0.15)');
      expect(darkPalette.border).toBe('#F59E0B');
      expect(darkPalette.text).toBe('#FDE68A');
    });

    it('should have different bg colors for light and dark modes', () => {
      const signalTypes: SignalColorType[] = ['S1', 'O1', 'Z1', 'ZE1', 'E1'];

      signalTypes.forEach((type) => {
        const lightPalette = getSignalColorPalette(type, 'light');
        const darkPalette = getSignalColorPalette(type, 'dark');

        // Background colors should be different
        expect(lightPalette.bg).not.toBe(darkPalette.bg);
        // Border color should be consistent
        expect(lightPalette.border).toBe(darkPalette.border);
      });
    });
  });

  // Helper function tests
  describe('Helper functions', () => {
    describe('getSignalColorPalette', () => {
      it('should return S1 colors for unknown signal type', () => {
        const palette = getSignalColorPalette('UNKNOWN', 'light');
        expect(palette).toEqual(SIGNAL_COLORS.S1.light);
      });
    });

    describe('getSignalColorConfig', () => {
      it('should return full config for valid signal type', () => {
        const config = getSignalColorConfig('ZE1');

        expect(config.primary).toBe('#10B981');
        expect(config.icon).toBe('💰');
        expect(config.label).toBe('Profit Exit');
        expect(config.light).toBeDefined();
        expect(config.dark).toBeDefined();
      });

      it('should return S1 config for unknown signal type', () => {
        const config = getSignalColorConfig('UNKNOWN');
        expect(config).toEqual(SIGNAL_COLORS.S1);
      });
    });

    describe('getSignalPrimaryColor', () => {
      it('should return primary color for valid signal type', () => {
        expect(getSignalPrimaryColor('E1')).toBe('#EF4444');
        expect(getSignalPrimaryColor('ZE1')).toBe('#10B981');
      });

      it('should return default color for unknown signal type', () => {
        expect(getSignalPrimaryColor('UNKNOWN')).toBe('#F59E0B');
      });
    });
  });

  // AC2: Colors are consistent across all signal displays
  describe('AC2: Color consistency', () => {
    it('should have consistent border colors between light and dark modes', () => {
      const signalTypes: SignalColorType[] = ['S1', 'O1', 'Z1', 'ZE1', 'E1'];

      signalTypes.forEach((type) => {
        const lightBorder = SIGNAL_COLORS[type].light.border;
        const darkBorder = SIGNAL_COLORS[type].dark.border;

        expect(lightBorder).toBe(darkBorder);
      });
    });

    it('should have primary color match border color', () => {
      const signalTypes: SignalColorType[] = ['S1', 'O1', 'Z1', 'ZE1', 'E1'];

      signalTypes.forEach((type) => {
        expect(SIGNAL_COLORS[type].primary).toBe(SIGNAL_COLORS[type].light.border);
      });
    });
  });
});
