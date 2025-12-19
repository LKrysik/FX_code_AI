/**
 * Global Setup for Playwright Tests
 * ==================================
 *
 * Runs once before all tests. Used for:
 * - Environment validation
 * - Test data seeding
 * - Authentication state caching
 */

import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('\n🧪 FX Agent AI - Test Suite Starting...\n');

  const baseURL = config.projects[0].use?.baseURL || 'http://localhost:3000';
  const apiURL = process.env.API_URL || 'http://localhost:8080';

  console.log(`📍 Frontend URL: ${baseURL}`);
  console.log(`📍 API URL: ${apiURL}`);

  // Validate environment
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Check frontend availability
    const frontendResponse = await page.goto(baseURL, { timeout: 30000 });
    if (frontendResponse?.ok()) {
      console.log('✅ Frontend is accessible');
    } else {
      console.warn(`⚠️ Frontend returned status: ${frontendResponse?.status()}`);
    }

    // Check API availability
    const apiResponse = await page.request.get(`${apiURL}/api/health`);
    if (apiResponse.ok()) {
      console.log('✅ API is accessible');
    } else {
      console.warn(`⚠️ API health check failed: ${apiResponse.status()}`);
    }

    // Store environment info for tests
    process.env.TEST_BASE_URL = baseURL;
    process.env.TEST_API_URL = apiURL;
    process.env.TEST_START_TIME = new Date().toISOString();

  } catch (error) {
    console.error('❌ Environment check failed:', error);
    // Don't fail setup - let tests handle unavailable services
  } finally {
    await browser.close();
  }

  console.log('\n🚀 Global setup complete\n');
}

export default globalSetup;
