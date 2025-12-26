# Testing Guide

**Last Updated:** 2025-12-25

Comprehensive guide to running and writing tests for FX Agent AI.

---

## Quick Start

```bash
# Backend unit tests (fast, no database required)
pytest tests_e2e -m "unit" -v

# Backend integration tests (requires QuestDB)
pytest tests_e2e -m "integration" -v

# Frontend unit tests
cd frontend && npm test

# Frontend E2E tests (requires backend running)
cd frontend && npx playwright test
```

---

## Test Architecture Overview

```
FX_code_AI_v2/
├── tests_e2e/              # Backend tests (pytest)
│   ├── unit/               # Unit tests (no external deps)
│   ├── integration/        # Integration tests (requires QuestDB)
│   ├── e2e/                # End-to-end tests
│   ├── api/                # API route tests
│   ├── performance/        # Load/performance tests
│   └── mocks/              # Mock implementations
│
├── frontend/tests/         # Frontend tests
│   └── e2e/               # Playwright E2E tests
│       ├── components/    # Component tests
│       ├── flows/         # User flow tests
│       ├── pages/         # Page objects
│       ├── api/           # API tests
│       └── support/       # Fixtures, factories, helpers
│
└── src/__tests__/          # Co-located unit tests
```

---

## Backend Tests (Python/Pytest)

### Configuration Files

| File | Purpose |
|------|---------|
| `tests_e2e/pytest.ini` | Pytest configuration |
| `tests_e2e/conftest.py` | Shared fixtures |
| `pyproject.toml` | Coverage, linting settings |

### Test Markers

Use markers to run specific test categories:

| Marker | Description | Requires |
|--------|-------------|----------|
| `@pytest.mark.unit` | Unit tests | Nothing |
| `@pytest.mark.fast` | Fast tests | Nothing |
| `@pytest.mark.integration` | Integration tests | QuestDB |
| `@pytest.mark.database` | Database tests | QuestDB |
| `@pytest.mark.e2e` | End-to-end tests | Full stack |
| `@pytest.mark.performance` | Performance tests | Full stack |
| `@pytest.mark.auth` | Authentication tests | - |
| `@pytest.mark.strategies` | Strategy CRUD tests | - |
| `@pytest.mark.sessions` | Session management | QuestDB |
| `@pytest.mark.slow` | Slow tests (skippable) | - |

### Running Backend Tests

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# All tests
pytest tests_e2e -v

# Unit tests only (fast, no database)
pytest tests_e2e -m "unit" -v

# Integration tests (requires QuestDB)
pytest tests_e2e -m "integration" -v

# Specific test file
pytest tests_e2e/unit/test_auth_unit.py -v

# Specific test function
pytest tests_e2e/unit/test_auth_unit.py::test_login_success -v

# With coverage
pytest tests_e2e -m "unit" --cov=src --cov-report=html

# Skip slow tests
pytest tests_e2e -m "not slow" -v

# Run tests matching pattern
pytest tests_e2e -k "auth" -v
```

### Test Output

```bash
# HTML coverage report
open htmlcov/index.html

# Test results (if configured)
cat test-results/results.json
```

### Writing Backend Tests

```python
# tests_e2e/unit/test_example.py
import pytest
from src.domain.services.example_service import ExampleService

@pytest.mark.unit
class TestExampleService:
    """Unit tests for ExampleService"""

    def test_basic_operation(self):
        """Test that basic operation works correctly."""
        service = ExampleService()
        result = service.do_something("input")
        assert result == "expected_output"

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async operation."""
        service = ExampleService()
        result = await service.async_operation()
        assert result is not None

@pytest.mark.integration
@pytest.mark.database
class TestExampleIntegration:
    """Integration tests requiring database."""

    def test_database_operation(self, db_connection):
        """Test database operation."""
        # Uses db_connection fixture from conftest.py
        pass
```

---

## Frontend Tests

### Test Types

| Type | Tool | Location | Purpose |
|------|------|----------|---------|
| Unit | Jest | `src/**/__tests__/` | Component logic |
| E2E | Playwright | `frontend/tests/e2e/` | User flows |

### Configuration Files

| File | Purpose |
|------|---------|
| `frontend/jest.config.js` | Jest configuration |
| `frontend/playwright.config.ts` | Playwright configuration |
| `frontend/tests/e2e/fixtures/` | Test fixtures |

### Running Frontend Tests

```bash
cd frontend

# Unit tests (Jest)
npm test                    # Run once
npm run test:watch          # Watch mode
npm run test:coverage       # With coverage

# E2E tests (Playwright)
npx playwright test                      # All E2E tests
npx playwright test --ui                 # Interactive mode
npx playwright test tests/e2e/flows/     # Specific folder
npx playwright test -g "trading"         # Tests matching pattern

# Generate test report
npx playwright show-report
```

### Page Object Pattern

Frontend E2E tests use the Page Object Model:

```typescript
// frontend/tests/e2e/pages/DashboardPage.ts
import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class DashboardPage extends BasePage {
  readonly tradingButton: Locator;
  readonly strategyList: Locator;

  constructor(page: Page) {
    super(page);
    this.tradingButton = page.locator('[data-testid="start-trading"]');
    this.strategyList = page.locator('.strategy-list');
  }

  async startTrading(): Promise<void> {
    await this.tradingButton.click();
  }
}
```

### Writing E2E Tests

```typescript
// frontend/tests/e2e/flows/trading.e2e.spec.ts
import { test, expect } from '@playwright/test';
import { DashboardPage } from '../pages/DashboardPage';

test.describe('Trading Flow', () => {
  test('user can start a paper trading session', async ({ page }) => {
    const dashboard = new DashboardPage(page);

    await dashboard.goto('/dashboard');
    await dashboard.startTrading();

    await expect(page.locator('.session-active')).toBeVisible();
  });
});
```

---

## Known Failing Tests

> **Important:** The following tests are known to fail due to incomplete features. Do not spend time debugging these until the underlying features are fixed.

### Backend

| Test | Reason | Ticket |
|------|--------|--------|
| `test_backtest_session_flow.py` | Trading engine not working | CORE-01 |
| `test_full_trading_flow.py` | Trading engine not working | CORE-01 |
| `test_live_trading_flow.py` | MEXC integration incomplete | CORE-01 |
| `test_pump_and_dump_strategy.py` | Strategy evaluation broken | CORE-02 |

### Frontend

| Test | Reason | Ticket |
|------|--------|--------|
| `trading-session.e2e.spec.ts` | Backend trading broken | CORE-01 |
| `legacy-trading-flow.e2e.spec.ts` | Deprecated flow | - |

### Test Results Directory

The `frontend/test-results/` directory contains failure artifacts:
- Screenshots on failure
- Video recordings (if enabled)
- Trace files for debugging

**Note:** These directories are auto-generated and should not be committed to git.

---

## Fixtures and Mocks

### Backend Fixtures (conftest.py)

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `test_client` | function | FastAPI TestClient |
| `db_connection` | session | QuestDB connection |
| `auth_token` | function | Valid JWT token |
| `mock_mexc` | function | Mocked MEXC adapter |

### Frontend Fixtures

| Fixture | Location | Purpose |
|---------|----------|---------|
| `api.fixture.ts` | support/fixtures/ | API mocking |
| `network.fixture.ts` | support/fixtures/ | Network interception |
| `cleanup.fixture.ts` | support/fixtures/ | Test cleanup |

### Using Mocks

```python
# Backend: Using mock indicator engine
from tests_e2e.mocks.indicator_engine import MockIndicatorEngine

def test_with_mock_indicators(mocker):
    mock_engine = MockIndicatorEngine()
    mocker.patch('src.domain.services.streaming_indicator_engine', mock_engine)
    # Test code here
```

```typescript
// Frontend: Intercepting API calls
test('handles API error gracefully', async ({ page }) => {
  await page.route('**/api/strategies', route => {
    route.fulfill({ status: 500, body: 'Server Error' });
  });

  await page.goto('/strategies');
  await expect(page.locator('.error-message')).toBeVisible();
});
```

---

## CI/CD Integration

### GitHub Actions (Expected)

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run unit tests
        run: pytest tests_e2e -m "unit" -v

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: cd frontend && npm ci
      - name: Run tests
        run: cd frontend && npm test
```

### Quality Gates

Before merging, ensure:
- [ ] All unit tests pass (`pytest tests_e2e -m "unit"`)
- [ ] No new lint errors (`ruff check src/`)
- [ ] Type checks pass (`mypy src/`)
- [ ] Frontend tests pass (`npm test`)

---

## Coverage Expectations

### Current State (Estimated)

| Area | Coverage | Target |
|------|----------|--------|
| Backend Unit | ~40% | 70% |
| Backend Integration | ~20% | 50% |
| Frontend Unit | ~30% | 60% |
| Frontend E2E | ~15% | 40% |

### Viewing Coverage

```bash
# Backend
pytest tests_e2e -m "unit" --cov=src --cov-report=html
open htmlcov/index.html

# Frontend
cd frontend && npm run test:coverage
open coverage/lcov-report/index.html
```

---

## Troubleshooting Tests

### "QuestDB not available"

```bash
# Start QuestDB
docker run -p 9000:9000 -p 8812:8812 questdb/questdb

# Or run only unit tests
pytest tests_e2e -m "unit" -v
```

### "Event loop is closed" (Windows)

Add to test file:
```python
import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

### Playwright browser not installed

```bash
cd frontend
npx playwright install
```

### Tests hang indefinitely

Check for:
- Unawaited async operations
- Missing timeouts
- Database connection leaks

Add timeout:
```python
@pytest.mark.timeout(30)
def test_potentially_slow():
    pass
```

---

## Best Practices

### DO

- Use descriptive test names: `test_login_with_invalid_password_returns_401`
- One assertion per test when possible
- Use fixtures for shared setup
- Mark tests appropriately (`@pytest.mark.unit`, etc.)
- Clean up test data after tests

### DON'T

- Don't depend on test execution order
- Don't use `time.sleep()` - use proper waits
- Don't hardcode test data that changes
- Don't skip tests without documenting why
- Don't commit `.env` files or secrets

---

## Adding New Tests

### Checklist

1. [ ] Choose correct test type (unit/integration/e2e)
2. [ ] Place in appropriate directory
3. [ ] Add appropriate markers
4. [ ] Use existing fixtures where possible
5. [ ] Add to this README if it's a new pattern
6. [ ] Verify test passes in isolation
7. [ ] Verify test passes with full suite

---

## Signal Flow E2E Verification (Story 0-2)

### Quick Verification Script

```bash
# Run backend signal flow verification
python scripts/verify_signal_flow_e2e.py
```

This script verifies:
- EventBus -> EventBridge -> WebSocket broadcast flow
- Latency < 500ms (AC1)
- All signal types (S1, O1, Z1, ZE1, E1) are forwarded

### Manual Frontend Verification

1. Start backend: `python -m src.api.unified_server`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser DevTools Console (F12)
4. Filter by: `[SIGNAL-FLOW]`
5. Trigger a backtest or strategy evaluation via UI
6. Verify logs appear:
   - `[SIGNAL-FLOW] Signal received: {...}` (websocket.ts)
   - `[SIGNAL-FLOW] Signal added to store: {...}` (dashboardStore.ts)

### Integration Tests

```bash
# Run signal flow integration tests
pytest tests_e2e/integration/test_signal_flow.py -v -m unit
```

---

*For questions about testing, see the architecture documentation or ask the team.*
