# E2E Testing Framework

## Overview

This framework provides comprehensive end-to-end testing for the FX Agent Trading Application using Playwright. It follows the Page Object Model (POM) pattern and includes specialized fixtures for common testing scenarios.

## Directory Structure

```
tests/e2e/
├── support/                    # NEW: Shared test infrastructure
│   ├── fixtures/               # Composable fixtures (mergeTests pattern)
│   │   ├── index.ts            # Merged fixtures export
│   │   ├── api.fixture.ts      # Typed HTTP client
│   │   ├── cleanup.fixture.ts  # Auto-cleanup tracking
│   │   ├── network.fixture.ts  # Network mocking
│   │   └── console.fixture.ts  # Console error tracking
│   ├── factories/              # Faker-based test data factories
│   │   ├── index.ts            # Factory exports
│   │   ├── strategy.factory.ts # Strategy + conditions
│   │   ├── indicator.factory.ts # Indicators + variants
│   │   └── trading-session.factory.ts # Session config
│   └── helpers/                # Pure utility functions
│       ├── wait-helpers.ts     # Deterministic waiting
│       └── seed-helpers.ts     # API-first data seeding
├── fixtures/                   # LEGACY: Old fixture location
│   └── base.fixture.ts         # Extended test (being replaced)
├── pages/                      # Page Object Models
│   ├── BasePage.ts
│   ├── DashboardPage.ts
│   ├── TradingSessionPage.ts
│   ├── StrategyBuilderPage.ts
│   ├── IndicatorsPage.ts
│   └── index.ts
├── flows/                      # E2E user journey tests
├── components/                 # Component edge case tests
├── api/                        # Backend API tests
├── examples/                   # NEW: Example tests showing patterns
│   └── new-patterns.example.spec.ts
├── global-setup.ts
└── global-teardown.ts
```

## Test Categories

### Smoke Tests (*.smoke.spec.ts)
Critical path tests that MUST pass before any deployment:
- Dashboard loads without errors
- Trading session page loads
- API connectivity
- Core navigation works
- Charts render without crashing

### E2E Tests (*.e2e.spec.ts)
Full user journey tests for the trading session workflow:
- Complete paper trading session lifecycle
- Strategy selection flow
- Mode switching
- Dashboard session display
- Signal monitoring
- Session history access
- Position monitoring
- WebSocket connection

### Component Tests (*.component.spec.ts)
Edge case tests for individual UI components:
- Each component has 3+ edge case tests
- Tests for error states, boundary conditions, rapid interactions
- Validates graceful degradation and error handling

### API Tests (*.api.spec.ts)
Backend API endpoint tests:
- CRUD operations validation
- Input validation (SQL injection, XSS)
- Error handling
- Rate limiting
- WebSocket connection tests

## Running Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run smoke tests only (fast)
npx playwright test --project=smoke

# Run component tests
npx playwright test --project=components

# Run API tests
npx playwright test --project=api

# Run with specific browser
npx playwright test --project=firefox
npx playwright test --project=mobile

# Run with UI mode (debugging)
npx playwright test --ui

# Generate test report
npx playwright show-report
```

## Page Object Model

Each page object extends `BasePage` and provides:

### Locators
```typescript
readonly strategyTable: Locator;
readonly createStrategyButton: Locator;
```

### Actions
```typescript
async selectStrategy(name: string): Promise<void> {}
async saveStrategy(): Promise<void> {}
```

### Assertions
```typescript
async expectStrategyVisible(name: string): Promise<void> {}
```

### Data Extraction
```typescript
async getStrategyNames(): Promise<string[]> {}
```

## Fixtures (NEW Architecture)

Import from `support/fixtures` for the new composable fixture system:

```typescript
import { test, expect } from '../support/fixtures';
```

### apiClient
Typed HTTP client for backend API calls:
```typescript
test('my test', async ({ apiClient }) => {
  const strategies = await apiClient.get<Strategy[]>('/api/strategies');
  await apiClient.post('/api/strategies', { name: 'New Strategy' });
});
```

### cleanup
Automatic resource cleanup after test completion:
```typescript
test('my test', async ({ apiClient, cleanup }) => {
  const strategy = createStrategy();
  await apiClient.post('/api/strategies', strategy);
  cleanup.track('strategies', strategy.id); // Auto-deleted after test
});
```

### network
Network interception and mocking:
```typescript
test('my test', async ({ page, network }) => {
  // Mock API before navigation (network-first!)
  await network.mock({
    method: 'GET',
    urlPattern: '**/api/strategies',
    response: [{ id: '1', name: 'Mocked' }],
  });
  await page.goto('/strategies');
});
```

### console
Console error tracking and assertions:
```typescript
test('my test', async ({ page, console: consoleManager }) => {
  await page.goto('/dashboard');
  expect(consoleManager.hasNoCriticalErrors()).toBe(true);
});
```

### consoleErrors (Legacy)
String array of errors for backward compatibility:
```typescript
test('my test', async ({ consoleErrors }) => {
  expect(consoleErrors).toHaveLength(0);
});
```

## Data Factories

Import from `support/factories` for test data generation:

```typescript
import { createStrategy, createPaperSession, createSymbols } from '../support/factories';
```

### Strategy Factory
```typescript
// Default strategy with random values
const strategy = createStrategy();

// Override specific fields
const customStrategy = createStrategy({
  name: 'My Strategy',
  isActive: false,
});

// Specialized factories
const rsiStrategy = createRsiStrategy();
const pumpStrategy = createPumpStrategy();
```

### Trading Session Factory
```typescript
// Paper trading session
const session = createPaperSession();

// With custom config
const session = createPaperSession({
  config: { symbols: ['BTCUSDT'], leverage: 5 },
});
```

### Indicator Factory
```typescript
const indicator = createIndicator();
const rsi = createRsiIndicator();
const variant = createIndicatorVariant(indicator.id);
```

## Seed Helpers

Import from `support/helpers` for API-first data setup:

```typescript
import { seedStrategy, seedTradingSetup } from '../support/helpers';
```

### API-First Pattern
```typescript
test('my test', async ({ apiClient, cleanup, page }) => {
  // Seed via API (fast!)
  const strategy = await seedStrategy(apiClient, cleanup, { name: 'Test' });

  // Then test UI
  await page.goto('/strategies');
  await expect(page.getByText(strategy.name)).toBeVisible();

  // Cleanup is automatic!
});
```

### Complete Setup
```typescript
const { strategies, session } = await seedTradingSetup(apiClient, cleanup, {
  strategyCount: 2,
  symbols: ['BTCUSDT', 'ETHUSDT'],
  mode: 'Paper',
});
```

## Naming Conventions

- Smoke tests: `SMOKE-XX: Description`
- E2E tests: `E2E-XX: Description`
- Component tests: `EDGE-XX: Description`
- API tests: `API-XX: Description`
- Legacy tests: `LEGACY-XX: Description`

## Test Tags

Tests are tagged for filtering:
- `@tags smoke, critical` - Critical smoke tests
- `@tags e2e, trading` - Trading flow E2E tests
- `@tags components, edge-cases` - Component edge cases
- `@tags api, backend` - Backend API tests

## Best Practices

1. **Use Page Objects**: Never use raw selectors in tests
2. **Prefer data-testid**: Add `data-testid` attributes to UI components
3. **Independent tests**: Each test should be runnable in isolation
4. **Avoid waitForTimeout**: Use proper waiting strategies (waitForSelector, expect with timeout)
5. **Log for debugging**: Use console.log for debugging complex flows
6. **Handle missing elements**: Use conditional checks for optional UI elements

## Adding New Tests

### New Page Object
1. Create `pages/NewPage.ts` extending `BasePage`
2. Add locators, actions, assertions
3. Export from `pages/index.ts`

### New Test File
1. Create in appropriate directory (flows/, components/, api/)
2. Import from fixtures and pages
3. Follow naming conventions
4. Tag appropriately

## Configuration

See `playwright.config.ts` for:
- Test timeout settings
- Browser projects configuration
- Reporter settings
- Web server configuration
- Parallel execution settings
