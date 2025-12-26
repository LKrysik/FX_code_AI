/**
 * Cleanup Fixture
 * ================
 *
 * Automatic cleanup tracking for test isolation.
 * Tracks created resources and deletes them after test completion.
 *
 * @see TEA Knowledge Base: fixture-architecture.md, data-factories.md
 */

import { test as base, APIRequestContext } from '@playwright/test';

// ============================================
// TYPE DEFINITIONS
// ============================================

export type ResourceType = 'strategies' | 'indicators' | 'sessions' | 'variants' | string;

export interface TrackedResource {
  type: ResourceType;
  id: string;
  endpoint?: string; // Custom delete endpoint if different from default
}

export interface CleanupManager {
  /**
   * Track a resource for cleanup after test completion
   */
  track: (type: ResourceType, id: string, endpoint?: string) => void;

  /**
   * Get all tracked resources (for debugging)
   */
  getTracked: () => TrackedResource[];

  /**
   * Manually trigger cleanup (usually automatic)
   */
  cleanupAll: () => Promise<void>;

  /**
   * Remove a resource from tracking (if already deleted manually)
   */
  untrack: (type: ResourceType, id: string) => void;
}

export interface CleanupFixtures {
  cleanup: CleanupManager;
}

// ============================================
// CLEANUP MANAGER FACTORY
// ============================================

export function createCleanupManager(request: APIRequestContext, apiUrl: string): CleanupManager {
  const trackedResources: TrackedResource[] = [];

  return {
    track: (type: ResourceType, id: string, endpoint?: string) => {
      trackedResources.push({ type, id, endpoint });
    },

    getTracked: () => [...trackedResources],

    untrack: (type: ResourceType, id: string) => {
      const index = trackedResources.findIndex((r) => r.type === type && r.id === id);
      if (index !== -1) {
        trackedResources.splice(index, 1);
      }
    },

    cleanupAll: async () => {
      // Delete in reverse order (LIFO) to handle dependencies
      const toDelete = [...trackedResources].reverse();

      for (const resource of toDelete) {
        const endpoint = resource.endpoint || `/api/${resource.type}/${resource.id}`;

        try {
          await request.delete(`${apiUrl}${endpoint}`);
        } catch (error) {
          // Log but don't fail - resource may already be deleted
          console.warn(`Cleanup warning: Failed to delete ${resource.type}/${resource.id}`, error);
        }
      }

      // Clear the array
      trackedResources.length = 0;
    },
  };
}

// ============================================
// PLAYWRIGHT FIXTURE
// ============================================

export const test = base.extend<CleanupFixtures>({
  cleanup: async ({ request }, use) => {
    const apiUrl = process.env.TEST_API_URL || process.env.API_URL || 'http://localhost:8080';
    const manager = createCleanupManager(request, apiUrl);

    await use(manager);

    // Auto-cleanup after test completes
    await manager.cleanupAll();
  },
});

export { expect } from '@playwright/test';
