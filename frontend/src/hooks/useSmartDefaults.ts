/**
 * useSmartDefaults Hook
 *
 * Auto-remembers user's last used values and provides smart defaults.
 * Stores preferences in localStorage and validates before using.
 *
 * @example
 * const [mode, setMode] = useSmartDefaults({
 *   key: 'sessionMode',
 *   defaultValue: 'paper',
 *   validator: (v) => ['paper', 'live'].includes(v)
 * });
 */

import { useState, useEffect, useCallback } from 'react';

interface SmartDefaultsOptions<T> {
  key: string;
  defaultValue: T;
  validator?: (value: T) => boolean;
  onChange?: (value: T) => void;
}

export function useSmartDefaults<T>({
  key,
  defaultValue,
  validator,
  onChange
}: SmartDefaultsOptions<T>): [T, (value: T) => void] {
  const storageKey = `smartDefaults_${key}`;

  // Initialize with stored value or default
  const [value, setValueInternal] = useState<T>(() => {
    if (typeof window === 'undefined') {
      return defaultValue;
    }

    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const parsed = JSON.parse(stored) as T;

        // Validate before using
        if (!validator || validator(parsed)) {
          return parsed;
        } else {
          console.warn(`Stored value for "${key}" failed validation, using default`);
        }
      }
    } catch (error) {
      console.warn(`Failed to load smart default for "${key}":`, error);
    }

    return defaultValue;
  });

  // Auto-save to localStorage when value changes
  useEffect(() => {
    if (typeof window === 'undefined') return;

    try {
      localStorage.setItem(storageKey, JSON.stringify(value));
    } catch (error) {
      console.warn(`Failed to save smart default for "${key}":`, error);
    }
  }, [storageKey, value, key]);

  // Wrapped setValue with onChange callback
  const setValue = useCallback((newValue: T) => {
    setValueInternal(newValue);
    onChange?.(newValue);
  }, [onChange]);

  return [value, setValue];
}

/**
 * Batch clear smart defaults (useful for logout/reset)
 */
export function clearSmartDefaults(keys?: string[]) {
  if (typeof window === 'undefined') return;

  if (keys) {
    // Clear specific keys
    keys.forEach(key => {
      localStorage.removeItem(`smartDefaults_${key}`);
    });
  } else {
    // Clear all smart defaults
    Object.keys(localStorage)
      .filter(key => key.startsWith('smartDefaults_'))
      .forEach(key => localStorage.removeItem(key));
  }
}

/**
 * Export current smart defaults (for debugging/analytics)
 */
export function exportSmartDefaults(): Record<string, any> {
  if (typeof window === 'undefined') return {};

  const defaults: Record<string, any> = {};

  Object.keys(localStorage)
    .filter(key => key.startsWith('smartDefaults_'))
    .forEach(key => {
      try {
        const cleanKey = key.replace('smartDefaults_', '');
        defaults[cleanKey] = JSON.parse(localStorage.getItem(key) || 'null');
      } catch (error) {
        console.warn(`Failed to export default for ${key}:`, error);
      }
    });

  return defaults;
}
