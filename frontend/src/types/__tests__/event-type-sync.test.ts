/**
 * EventType Synchronization Tests
 * ================================
 * Validates that EventType in TypeScript matches the shared event-types.json.
 * Ensures frontend/backend type definitions stay synchronized.
 *
 * Part of COH-001-3: Create TypeScript EventType Definitions
 */

import * as fs from 'fs';
import * as path from 'path';
import { EventType, EventTypeValue } from '../events';

interface SharedEventTypesJson {
  eventTypes: string[];
  categories?: Record<string, string[]>;
  version?: string;
  lastUpdated?: string;
}

describe('EventType Synchronization', () => {
  let sharedEventTypes: Set<string>;
  let sharedData: SharedEventTypesJson;

  beforeAll(() => {
    // Load shared event types JSON
    const sharedPath = path.resolve(__dirname, '../../../../shared/event-types.json');

    if (!fs.existsSync(sharedPath)) {
      throw new Error(`Shared event types file not found: ${sharedPath}`);
    }

    const content = fs.readFileSync(sharedPath, 'utf-8');
    sharedData = JSON.parse(content) as SharedEventTypesJson;
    sharedEventTypes = new Set(sharedData.eventTypes);
  });

  it('TypeScript EventType matches shared JSON definition', () => {
    const typescriptTypes = new Set(Object.values(EventType));

    // Find differences
    const inSharedOnly = [...sharedEventTypes].filter((t) => !typescriptTypes.has(t as EventTypeValue));
    const inTypescriptOnly = [...typescriptTypes].filter((t) => !sharedEventTypes.has(t));

    const errors: string[] = [];

    if (inSharedOnly.length > 0) {
      errors.push(
        `Event types in shared/event-types.json but NOT in TypeScript EventType:\n` +
          `  ${inSharedOnly.sort().join(', ')}\n` +
          `  → Add these to frontend/src/types/events.ts EventType object`
      );
    }

    if (inTypescriptOnly.length > 0) {
      errors.push(
        `Event types in TypeScript EventType but NOT in shared/event-types.json:\n` +
          `  ${inTypescriptOnly.sort().join(', ')}\n` +
          `  → Add these to shared/event-types.json OR remove from TypeScript`
      );
    }

    expect(errors).toHaveLength(0);
    if (errors.length > 0) {
      throw new Error(errors.join('\n\n'));
    }
  });

  it('event type count matches between shared JSON and TypeScript', () => {
    const typescriptCount = Object.keys(EventType).length;
    expect(typescriptCount).toBe(sharedEventTypes.size);
  });

  it('shared JSON has required structure', () => {
    expect(sharedData).toHaveProperty('eventTypes');
    expect(Array.isArray(sharedData.eventTypes)).toBe(true);
    expect(sharedData.eventTypes.length).toBeGreaterThan(0);
  });

  it('all event types follow naming convention (category.action)', () => {
    for (const eventType of sharedData.eventTypes) {
      expect(typeof eventType).toBe('string');
      expect(eventType).toMatch(/^[a-z]+\.[a-z_]+$/);
    }
  });

  it('no duplicate event types in shared JSON', () => {
    const unique = new Set(sharedData.eventTypes);
    expect(unique.size).toBe(sharedData.eventTypes.length);
  });

  it('no duplicate values in TypeScript EventType', () => {
    const values = Object.values(EventType);
    const unique = new Set(values);
    expect(unique.size).toBe(values.length);
  });

  it('categories cover all event types (if defined)', () => {
    if (!sharedData.categories) {
      return; // Skip if no categories
    }

    const allTypes = new Set(sharedData.eventTypes);
    const categorizedTypes = new Set<string>();

    for (const types of Object.values(sharedData.categories)) {
      types.forEach((t) => categorizedTypes.add(t));
    }

    const uncategorized = [...allTypes].filter((t) => !categorizedTypes.has(t));

    expect(uncategorized).toHaveLength(0);
    if (uncategorized.length > 0) {
      throw new Error(`Event types not in any category: ${uncategorized.sort().join(', ')}`);
    }
  });

  it('all category entries are valid event types', () => {
    if (!sharedData.categories) {
      return; // Skip if no categories
    }

    const allTypes = new Set(sharedData.eventTypes);
    const invalidCategoryEntries: string[] = [];

    for (const [category, types] of Object.entries(sharedData.categories)) {
      for (const type of types) {
        if (!allTypes.has(type)) {
          invalidCategoryEntries.push(`${category}: ${type}`);
        }
      }
    }

    expect(invalidCategoryEntries).toHaveLength(0);
    if (invalidCategoryEntries.length > 0) {
      throw new Error(`Category entries not in eventTypes: ${invalidCategoryEntries.join(', ')}`);
    }
  });
});
