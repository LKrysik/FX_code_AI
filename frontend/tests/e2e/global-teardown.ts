/**
 * Global Teardown for Playwright Tests
 * =====================================
 *
 * Runs once after all tests. Used for:
 * - Test data cleanup
 * - Report generation
 * - Resource release
 */

import { FullConfig } from '@playwright/test';

async function globalTeardown(config: FullConfig) {
  console.log('\n🧹 FX Agent AI - Test Suite Cleanup...\n');

  const startTime = process.env.TEST_START_TIME;
  if (startTime) {
    const duration = Date.now() - new Date(startTime).getTime();
    console.log(`⏱️ Total test duration: ${(duration / 1000).toFixed(2)}s`);
  }

  console.log('✅ Global teardown complete\n');
}

export default globalTeardown;
