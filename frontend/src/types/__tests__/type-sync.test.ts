/**
 * Test Type Synchronization
 * ==========================
 * Validates that WSMessageType in TypeScript matches the shared message-types.json.
 * Ensures frontend/backend type definitions stay synchronized.
 *
 * Part of COH-001-1: Synchronize MessageType Definitions
 */

import * as fs from 'fs';
import * as path from 'path';
import type { WSMessageType } from '../api';

// Extract all WSMessageType values from the type definition
// Note: Since TypeScript types are erased at runtime, we need to maintain this list
// in sync with the type definition. The test will catch any drift.
const TYPESCRIPT_MESSAGE_TYPES: WSMessageType[] = [
  'subscribe',
  'unsubscribe',
  'command',
  'query',
  'heartbeat',
  'auth',
  'data',
  'signal',
  'alert',
  'response',
  'error',
  'status',
  'session_start',
  'session_stop',
  'session_status',
  'collection_start',
  'collection_stop',
  'collection_status',
  'results_request',
  'get_strategies',
  'activate_strategy',
  'deactivate_strategy',
  'get_strategy_status',
  'validate_strategy_config',
  'upsert_strategy',
  'handshake',
];

interface SharedMessageTypesJson {
  messageTypes: string[];
  categories?: Record<string, string[]>;
  version?: string;
  lastUpdated?: string;
}

describe('MessageType Synchronization', () => {
  let sharedMessageTypes: Set<string>;
  let sharedData: SharedMessageTypesJson;

  beforeAll(() => {
    // Load shared message types JSON
    const sharedPath = path.resolve(__dirname, '../../../../shared/message-types.json');

    if (!fs.existsSync(sharedPath)) {
      throw new Error(`Shared message types file not found: ${sharedPath}`);
    }

    const content = fs.readFileSync(sharedPath, 'utf-8');
    sharedData = JSON.parse(content) as SharedMessageTypesJson;
    sharedMessageTypes = new Set(sharedData.messageTypes);
  });

  it('TypeScript WSMessageType matches shared JSON definition', () => {
    const typescriptTypes = new Set(TYPESCRIPT_MESSAGE_TYPES);

    // Find differences
    const inSharedOnly = [...sharedMessageTypes].filter((t) => !typescriptTypes.has(t as WSMessageType));
    const inTypescriptOnly = [...typescriptTypes].filter((t) => !sharedMessageTypes.has(t));

    const errors: string[] = [];

    if (inSharedOnly.length > 0) {
      errors.push(
        `Message types in shared/message-types.json but NOT in TypeScript WSMessageType:\n` +
          `  ${inSharedOnly.sort().join(', ')}\n` +
          `  → Add these to frontend/src/types/api.ts WSMessageType and this test's TYPESCRIPT_MESSAGE_TYPES array`
      );
    }

    if (inTypescriptOnly.length > 0) {
      errors.push(
        `Message types in TypeScript WSMessageType but NOT in shared/message-types.json:\n` +
          `  ${inTypescriptOnly.sort().join(', ')}\n` +
          `  → Add these to shared/message-types.json OR remove from TypeScript`
      );
    }

    expect(errors).toHaveLength(0);
    if (errors.length > 0) {
      throw new Error(errors.join('\n\n'));
    }
  });

  it('message type count matches between shared JSON and TypeScript', () => {
    expect(TYPESCRIPT_MESSAGE_TYPES.length).toBe(sharedMessageTypes.size);
  });

  it('shared JSON has required structure', () => {
    expect(sharedData).toHaveProperty('messageTypes');
    expect(Array.isArray(sharedData.messageTypes)).toBe(true);
    expect(sharedData.messageTypes.length).toBeGreaterThan(0);
  });

  it('all message types are lowercase strings', () => {
    for (const msgType of sharedData.messageTypes) {
      expect(typeof msgType).toBe('string');
      expect(msgType).toBe(msgType.toLowerCase());
    }
  });

  it('no duplicate message types in shared JSON', () => {
    const unique = new Set(sharedData.messageTypes);
    expect(unique.size).toBe(sharedData.messageTypes.length);
  });

  it('TYPESCRIPT_MESSAGE_TYPES array has no duplicates', () => {
    const unique = new Set(TYPESCRIPT_MESSAGE_TYPES);
    expect(unique.size).toBe(TYPESCRIPT_MESSAGE_TYPES.length);
  });

  it('categories cover all message types (if defined)', () => {
    if (!sharedData.categories) {
      return; // Skip if no categories
    }

    const allTypes = new Set(sharedData.messageTypes);
    const categorizedTypes = new Set<string>();

    for (const types of Object.values(sharedData.categories)) {
      types.forEach((t) => categorizedTypes.add(t));
    }

    const uncategorized = [...allTypes].filter((t) => !categorizedTypes.has(t));

    expect(uncategorized).toHaveLength(0);
    if (uncategorized.length > 0) {
      throw new Error(`Message types not in any category: ${uncategorized.sort().join(', ')}`);
    }
  });
});
