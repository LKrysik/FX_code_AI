# E2E Testing Framework

## Overview

This framework provides comprehensive end-to-end testing for the FX Agent Trading Application using Playwright. It follows the Page Object Model (POM) pattern and includes specialized fixtures for common testing scenarios.

## Directory Structure

```
tests/e2e/
├── fixtures/           # Playwright fixtures and test setup
│   ├── base.fixture.ts # Extended test with API client, mocks, error tracking
│   ├── global-setup.ts # Pre-test environment setup
│   └── global-teardown.ts # Post-test cleanup
├── pages/              # Page Object Models
│   ├── BasePage.ts     # Abstract base class with common methods
│   ├── DashboardPage.ts
│   ├── TradingSessionPage.ts
│   ├── StrategyBuilderPage.ts
│   ├── IndicatorsPage.ts
│   └── index.ts        # Exports all page objects
├── flows/              # End-to-end user journey tests
│   ├── trading-session.smoke.spec.ts
│   ├── trading-session.e2e.spec.ts
│   └── legacy-trading-flow.e2e.spec.ts
├── components/         # Component-specific tests (edge cases)
│   ├── dashboard.component.spec.ts
│   ├── trading-session.component.spec.ts
│   ├── strategy-builder.component.spec.ts
│   └── indicators.component.spec.ts
└── api/                # Backend API tests
    └── backend.api.spec.ts
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

## Fixtures

### apiClient
HTTP client for direct API calls:
```typescript
test('my test', async ({ apiClient }) => {
  const response = await apiClient.get('/api/strategies');
});
```

### consoleErrors
Collects JavaScript console errors:
```typescript
test('my test', async ({ consoleErrors }) => {
  expect(consoleErrors).toHaveLength(0);
});
```

### testConfig
Environment configuration:
```typescript
test('my test', async ({ testConfig }) => {
  console.log(testConfig.apiUrl);
});
```

### mockedWebSocket
Mock WebSocket for testing real-time updates:
```typescript
test('my test', async ({ mockedWebSocket }) => {
  mockedWebSocket.send({ type: 'price_update', data: {...} });
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
