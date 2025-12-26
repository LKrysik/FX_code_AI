# Story 0.3: Strategy Builder Audit

Status: ready-for-dev

## Story

As a **trader**,
I want **to verify that the Strategy Builder can save and load strategies correctly**,
so that **my strategy configurations persist and I can use them for backtesting and trading**.

## Acceptance Criteria

1. **AC1:** At least one existing strategy can be loaded from the backend and displayed in Strategy Builder
2. **AC2:** A new strategy can be created, saved, and then reloaded successfully
3. **AC3:** Strategy configuration includes all 5 sections (S1, O1, Z1, ZE1, E1) with indicators
4. **AC4:** Saved strategy matches loaded strategy (no data loss or corruption)
5. **AC5:** Errors during save/load are displayed to user (no silent failures)

## Tasks / Subtasks

- [ ] **Task 1: Audit Existing Strategy API** (AC: 1)
  - [ ] 1.1 Test `GET /strategies` endpoint returns list of strategies
  - [ ] 1.2 Test `GET /strategies/{name}` returns full strategy config
  - [ ] 1.3 Verify response envelope format matches frontend expectations
  - [ ] 1.4 Document any API response issues

- [ ] **Task 2: Audit Save Flow** (AC: 2, 4)
  - [ ] 2.1 Trace `apiService.saveStrategy()` call in `strategy-builder/page.tsx:271`
  - [ ] 2.2 Verify `POST /api/strategies` endpoint works
  - [ ] 2.3 Confirm saved data matches input (no field loss)
  - [ ] 2.4 Test validation endpoint `POST /api/strategies/validate`

- [ ] **Task 3: Audit Load Flow** (AC: 1, 3)
  - [ ] 3.1 Trace `apiService.getStrategies()` call in `strategies/page.tsx:219`
  - [ ] 3.2 Verify strategy list populates correctly
  - [ ] 3.3 Verify individual strategy loads with all 5 sections
  - [ ] 3.4 Confirm indicators are preserved after reload

- [ ] **Task 4: Test Round-Trip Integrity** (AC: 4)
  - [ ] 4.1 Create test strategy with known values
  - [ ] 4.2 Save strategy
  - [ ] 4.3 Reload strategy
  - [ ] 4.4 Compare: saved config === loaded config
  - [ ] 4.5 Document any discrepancies

- [ ] **Task 5: Verify Error Handling** (AC: 5)
  - [ ] 5.1 Test save with invalid config (expect user-visible error)
  - [ ] 5.2 Test load of non-existent strategy (expect user-visible error)
  - [ ] 5.3 Test save when backend is down (expect graceful failure)
  - [ ] 5.4 Confirm no silent failures (check console for unhandled errors)

## Dev Notes

### FR8 Requirement

From PRD: "FR8: Trader can save and load strategy configurations"

This story AUDITS existing functionality rather than implementing new features. The Strategy Builder exists but has never been verified end-to-end.

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `frontend/src/app/strategy-builder/page.tsx` | Save strategy | 271 |
| `frontend/src/app/strategies/page.tsx` | Load strategies | 219, 264 |
| `frontend/src/services/api.ts` | API methods | 279-330, 737-763 |
| `frontend/src/services/strategiesApi.ts` | Strategy API | 146-282 |
| `src/api/routers/strategies_router.py` | Backend routes | - |

### API Endpoints

**Strategy CRUD:**
```
GET  /strategies           → List all strategies
GET  /strategies/{name}    → Get single strategy
POST /strategies           → Create strategy
PUT  /strategies/{name}    → Update strategy
DELETE /strategies/{name}  → Delete strategy
```

**4-Section API (newer):**
```
GET  /api/strategies           → List 4-section strategies
POST /api/strategies           → Save 4-section strategy
POST /api/strategies/validate  → Validate without saving
GET  /api/strategies/{id}      → Get by ID
PUT  /api/strategies/{id}      → Update by ID
```

### Strategy Config Schema

**Expected structure (5 sections):**
```typescript
interface StrategyConfig {
  strategy_name: string;
  version: string;
  sections: {
    S1: SectionConfig;   // Signal Detection
    O1: SectionConfig;   // Cancellation
    Z1: SectionConfig;   // Entry Confirmation
    ZE1: SectionConfig;  // Exit with Profit
    E1: SectionConfig;   // Emergency Exit
  };
  indicators: IndicatorConfig[];
  metadata: {
    created_at: string;
    updated_at: string;
  };
}
```

### Testing Approach

**Manual Test Script:**
1. Open `/strategies` page
2. Create new strategy via Strategy Builder
3. Configure S1 with pump_magnitude > 7%
4. Save strategy
5. Refresh page
6. Load saved strategy
7. Verify S1 shows pump_magnitude > 7%

**Automated Test:**
```typescript
// frontend/tests/e2e/strategy-save-load.spec.ts
test('strategy round-trip', async ({ page }) => {
  // Create
  await page.goto('/strategy-builder');
  await page.fill('[data-testid="strategy-name"]', 'test-strategy');
  // ... configure S1
  await page.click('[data-testid="save-strategy"]');

  // Reload
  await page.goto('/strategies');
  await page.click('text=test-strategy');

  // Verify
  expect(await page.inputValue('[data-testid="s1-threshold"]')).toBe('7');
});
```

### Known Issues to Check

1. **Dual API confusion** - There's both `/strategies` and `/api/strategies` - which is correct?
2. **4-section vs 5-section** - Files mention both, verify which is current
3. **Response envelope** - Does `response.data.data?.strategies` work consistently?

### Pattern Requirements

- Use existing `apiService` methods, don't create new ones
- Follow error handling pattern from `api.ts` (try/catch with user notification)
- Use existing toast/snackbar for user feedback

### References

- [Source: _bmad-output/prd.md#FR8: Save and load strategy configurations]
- [Source: _bmad-output/epics.md#Epic 0 Story 5]
- [Source: frontend/src/app/strategy-builder/page.tsx:271]
- [Source: frontend/src/services/api.ts:279-330]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
