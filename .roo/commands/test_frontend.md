---
description: "Mandatory frontend verification to prevent AI agent false positives"
---

# /test_frontend - Frontend Reality Check

**Purpose**: Mandatory manual testing for all frontend features to prevent false "working" claims

**Usage**: /test_frontend "[feature_name]"

## MANDATORY Manual Testing Protocol

### 1. Setup Testing Environment
```bash
# Start application
npm run dev
# Open browser to application URL
# Open browser developer tools (F12)
# Clear browser cache and local storage
```

### 2. Step-by-Step User Workflow Testing

#### **For Strategy Builder Features:**
**Required Test Sequence (ALL steps must pass):**

**Tab Navigation:**
- [ ] Navigate to `/strategy-builder` URL
- [ ] Verify page loads without console errors
- [ ] See two tabs: "Strategy List" and "Builder"
- [ ] Click "Strategy List" tab - content loads
- [ ] Click "Builder" tab - content loads
- [ ] Click back to "Strategy List" - previous state preserved

**Strategy List Functionality:**
- [ ] Strategy List displays existing strategies from `config/strategies/`
- [ ] Each strategy shows: name, creation date, valid/invalid status
- [ ] Each strategy has Edit and Delete buttons
- [ ] Click "Edit" on existing strategy:
  - [ ] Switches to Builder tab
  - [ ] Pre-populates form with strategy data
  - [ ] All strategy sections (S1, Z1, O1, ZE1, E1) load correctly
- [ ] Click "Delete" on strategy:
  - [ ] Shows confirmation dialog
  - [ ] Confirm deletion - strategy disappears from list
  - [ ] Verify JSON file removed from `config/strategies/`

**Strategy Builder Functionality:**
- [ ] Strategy name field accepts text input
- [ ] Strategy name validation works (empty, duplicates, special chars)
- [ ] S1 (Signal Detection) section:
  - [ ] Can add conditions
  - [ ] Indicator dropdown shows available indicators
  - [ ] Operator dropdown works (>, <, =, BETWEEN)
  - [ ] Value input accepts numbers
  - [ ] Multiple conditions can be added
  - [ ] Conditions can be removed
- [ ] O1 (Signal Cancellation) section:
  - [ ] Timeout option works
  - [ ] Condition-based cancellation works
  - [ ] Cool down period setting works
- [ ] Z1 (Order Entry) section:
  - [ ] Entry conditions can be set
  - [ ] Stop Loss can be enabled/configured
  - [ ] Take Profit can be enabled/configured
  - [ ] Position Size settings work (Fixed/Percent)
  - [ ] Risk scaling options work
- [ ] ZE1 (Order Closing) section:
  - [ ] Exit conditions can be set
  - [ ] Close price options work
  - [ ] Risk scaling for close price works
- [ ] E1 (Emergency Exit) section:
  - [ ] Emergency conditions can be set
  - [ ] Cool down period works

**Save/Load Functionality:**
- [ ] Click "Save" with valid strategy:
  - [ ] Shows success message
  - [ ] Strategy appears in Strategy List
  - [ ] JSON file created in `config/strategies/`
  - [ ] JSON file contains correct structure
- [ ] Refresh browser:
  - [ ] Saved strategies still appear in list
  - [ ] Can edit saved strategies successfully
- [ ] Create strategy with existing name:
  - [ ] Shows error or auto-renames
  - [ ] Does not overwrite existing strategy

### 3. Error State Testing (MANDATORY)

**Test ALL error scenarios:**
- [ ] Enter empty strategy name - shows validation error
- [ ] Try to save incomplete strategy - prevents save with clear message
- [ ] Enter invalid numeric values - shows validation error
- [ ] Try to add conditions without selecting indicator - shows error
- [ ] Delete all strategies - shows "no strategies" message
- [ ] Network error during save - handles gracefully with error message

### 4. Integration Testing (MANDATORY)

**API Integration:**
- [ ] Monitor Network tab during strategy operations
- [ ] Verify correct API calls are made:
  - `GET /api/strategies` for loading
  - `POST /api/strategies` for creating
  - `PUT /api/strategies/{id}` for updating
  - `DELETE /api/strategies/{id}` for deleting
- [ ] Verify API responses update UI correctly
- [ ] Test API error responses (500, 404) show proper error messages

**File System Integration:**
- [ ] Check `config/strategies/` directory after operations
- [ ] Verify JSON files have correct structure:
```json
{
  "id": "uuid",
  "name": "Strategy Name",
  "sections": {
    "S1": { "conditions": [...] },
    "Z1": { "entry": {...} },
    "O1": { "cancellation": {...} },
    "ZE1": { "exit": {...} },
    "E1": { "emergency": {...} }
  },
  "created": "timestamp",
  "updated": "timestamp"
}
```

### 5. Stress Testing (MANDATORY)

**Try to break the feature:**
- [ ] Rapid button clicking (save/delete/edit)
- [ ] Multiple browser tabs with same feature
- [ ] Very long strategy names (500+ characters)
- [ ] Create 50+ strategies - performance acceptable
- [ ] Browser back/forward buttons don't break state
- [ ] Mobile/tablet screen sizes work
- [ ] Slow network simulation (throttle to 3G)

### 6. Evidence Collection (REQUIRED)

**Document in `docs/evidence/frontend_testing/`:**

**Screenshots Required:**
- Strategy List with sample data
- Strategy Builder form with all sections
- Successful save confirmation
- Error message examples
- Mobile view (if responsive)

**Test Logs Required:**
```markdown
## Manual Testing Results - [Date/Time]

### Browser Environment
- Browser: Chrome/Firefox/Safari [version]
- Screen Size: [width x height]
- Network: Normal/Throttled

### Test Results
- Tab Navigation: ✅/❌
- Strategy List: ✅/❌ [specific issues if any]
- Strategy Builder: ✅/❌ [specific issues if any]
- Save/Load: ✅/❌ [specific issues if any]
- Error Handling: ✅/❌ [specific issues if any]
- API Integration: ✅/❌ [specific issues if any]
- Stress Testing: ✅/❌ [specific issues if any]

### Issues Found
[List any bugs, usability issues, or unexpected behavior]

### Console Errors
[Copy any JavaScript errors from browser console]

### Performance Notes
[Loading times, responsiveness issues]
```

## Verification Status

**FRONTEND_VERIFIED** - Only if ALL conditions met:
- [ ] All manual test steps completed successfully
- [ ] All error scenarios handled properly
- [ ] API integration working correctly
- [ ] File system operations verified
- [ ] Stress testing passed
- [ ] Evidence documented with screenshots
- [ ] No critical console errors
- [ ] Feature works on multiple browsers/screen sizes

**FRONTEND_FAILED** - If ANY critical issue found:
- List specific failures
- Provide exact steps to reproduce
- Include screenshots of problems
- Mark feature as not ready for production

## Common Frontend False Positives

**❌ These are NOT sufficient for VERIFIED status:**
- Component renders without errors
- Form accepts input
- Button click triggers function
- API call returns data
- Tests pass in isolation

**✅ These ARE required for VERIFIED status:**
- User can complete intended workflow
- All interactions work as expected
- Data persists correctly
- Error states are handled
- Integration works end-to-end
- Feature is actually usable by real users

## Output

### Frontend Testing Status: [FRONTEND_VERIFIED/FRONTEND_FAILED]

### Evidence Location
- Screenshots: `docs/evidence/frontend_testing/[feature]/screenshots/`
- Test logs: `docs/evidence/frontend_testing/[feature]/test_log.md`
- Console logs: `docs/evidence/frontend_testing/[feature]/console.log`

### Issues Summary
[List of any issues found during testing]

### Recommendation
- **If FRONTEND_VERIFIED**: Feature ready for production use
- **If FRONTEND_FAILED**: Return to development with specific fix list