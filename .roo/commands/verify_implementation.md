---
description: "Streamlined verification with smart deception detection"
---

# /verify_implementation - Smart Task Verification

**Purpose**: Efficient verification that catches false positives without bureaucracy

**Usage**: /verify_implementation "[task_description]"

## Smart Verification Process

### 1. Automated Evidence Check
```bash
# Verify evidence exists and is recent
ls -la docs/evidence/[task_id]/
find docs/evidence/[task_id]/ -name "*.txt" -mtime -1
# Files must exist and be created within last 24 hours
```

### 2. Git Reality Check
```bash
# Cross-verify claimed implementation with actual changes
git log --oneline -5
git diff HEAD~2..HEAD --stat
git show --name-only HEAD

# Verify claimed file changes match git history
```

### 3. Build/Test Consistency Check
```bash
# Verify current state matches claimed test results
npm run build
npm test

# Compare with evidence files - results should be consistent
```

### 4. USER_REC Compliance Check
```markdown
For task: "[task_description]"
Find related USER_REC in docs/MVP.md

Requirements mapping:
- [ ] PRIMARY functionality implemented
- [ ] Core user workflow enabled  
- [ ] Error states handled reasonably
- [ ] Integration with existing features maintained
```

### 5. Spot-Check Manual Testing (10% of tasks)
```bash
# Random verification trigger
task_hash=$(echo "[task_description]" | md5sum | cut -c1-2)
if [ "$task_hash" = "00" ]; then
    echo "DEEP VERIFICATION REQUIRED"
    # Perform comprehensive manual testing
    # Require video evidence
    # Cross-examine all claims
fi
```

### 6. Red Flag Analysis
**Automatic escalation triggers:**
```markdown
❌ Evidence timestamp older than git commits
❌ Generic/template content in evidence files
❌ Perfect test results for complex features
❌ Missing git commits for claimed implementation
❌ Evidence file sizes suspicious (too small/large)
```

## Verification Decision

### VERIFIED (All criteria met)
- [ ] Evidence files exist and are authentic
- [ ] Git changes align with claimed implementation
- [ ] Build/tests pass consistently
- [ ] USER_REC requirements addressed
- [ ] No red flags detected

### NEEDS_WORK (Specific issues found)
```markdown
Issues identified:
1. [ISSUE]: [specific problem]
   - Evidence: [screenshot/log reference]
   - Fix needed: [specific action required]

2. [ISSUE]: [specific problem]
   - Evidence: [screenshot/log reference] 
   - Fix needed: [specific action required]
```

### CANNOT_VERIFY (Blockers present)
- Missing evidence files
- Inconsistent git history
- Build/test failures
- Major red flags detected

## Smart Enforcement

### Standard Verification (90% of tasks)
- Automated checks only
- Evidence file validation
- Git consistency check
- Build/test verification

### Enhanced Verification (10% of tasks - random)
- All standard checks PLUS:
- Manual browser testing required
- Video evidence mandatory
- Cross-agent review
- Detailed requirement analysis

## Output Format

### Verification Status: [VERIFIED/NEEDS_WORK/CANNOT_VERIFY]

### Automated Checks
- **Evidence**: ✅/❌ [files present and recent]
- **Git Changes**: ✅/❌ [commits align with claims]
- **Build/Tests**: ✅/❌ [consistent with evidence]
- **Requirements**: ✅/❌ [USER_REC addressed]

### Red Flag Analysis
- **Suspicious Patterns**: None/[list flags detected]
- **Authenticity Score**: High/Medium/Low
- **Verification Level**: Standard/Enhanced

### Next Actions
- **If VERIFIED**: Task ready for completion
- **If NEEDS_WORK**: Address listed issues
- **If CANNOT_VERIFY**: Resolve blockers and re-verify
- Missing dependencies
- Unclear requirements
- Environment issues
- Need additional information

### 7. COMMON FALSE POSITIVE TRAPS

**❌ Don't Accept These as "Working":**
- Component renders but buttons don't work
- Form submits but data doesn't save
- Page loads but features are broken
- Tests pass but manual testing fails
- API returns data but UI doesn't update
- Error states not handled
- Only works in ideal conditions

**✅ Only Accept as "Working":**
- Real user can complete intended workflow
- All data operations work correctly
- Error cases are handled gracefully
- Feature integrates with existing app
- Works across different scenarios

## Output Format

### Verification Status: [VERIFIED/NEEDS_WORK/CANNOT_VERIFY]

### Manual Testing Evidence
**Browser Testing:**
- URL tested: [specific URL]
- User workflow completed: [detailed steps]
- Screenshots: [attach evidence]
- Issues found: [specific problems or "none"]

**Integration Testing:**
- Data persistence: [verified/failed]
- API integration: [working/broken] 
- Error handling: [adequate/inadequate]

### Red Team Results
**Break Testing:**
- [List what was tested to try to break it]
- [Document any breaking scenarios found]

### Final Recommendation
- **If VERIFIED**: Task can be marked DONE
- **If NEEDS_WORK**: Specific fixes required before DONE
- **If CANNOT_VERIFY**: Blockers that prevent verification

### Evidence Files
- Screenshots saved to: `docs/evidence/[task]/`
- Test logs saved to: `docs/evidence/[task]/`

## Verification Rules

1. **No manual testing = No VERIFIED status**
2. **Any broken workflow = NEEDS_WORK status**
3. **AI agent must provide evidence screenshots**
4. **Red team testing is mandatory for UI features**
5. **Integration testing required for all features**
  - Check route definition in FastAPI/Express
  - Verify request/response schemas
  - Check authentication/authorization
  - Verify error responses defined

---

### 4. **🔍 Cross-Layer Integration Verification** ⭐ NEW

This step identifies gaps and inconsistencies between backend and frontend implementations.

#### 4.1 Backend → Frontend Gap Analysis

**Purpose**: Find backend features NOT consumed by frontend

**Check for Orphaned Backend Features**:

```python
# Backend API Inventory
backend_endpoints = []
# From: src/routes/*.py or src/api/*.py
# Extract: all @app.route(), @router.get/post/put/delete()

backend_models = []
# From: src/models/*.py or src/schemas/*.py
# Extract: all Pydantic models, SQLAlchemy models

backend_services = []
# From: src/services/*.py
# Extract: all business logic functions
```

**Frontend API Usage Inventory**:

```typescript
// Frontend API Calls
frontend_api_calls = []
// From: frontend/src/**/*.{ts,tsx}
// Extract: all fetch(), axios.get/post/put/delete()
// Extract: all API endpoint strings

frontend_types = []
// From: frontend/src/types/*.ts
// Extract: all interface/type definitions

frontend_stores = []
// From: frontend/src/stores/*.ts
// Extract: all state management, data fetching
```

**Gap Detection**:

```
For each backend_endpoint:
  If endpoint NOT in frontend_api_calls:
    → Mark as "Backend feature not integrated in frontend"
    
For each backend_model:
  If model has no corresponding frontend_type:
    → Mark as "Backend data structure not typed in frontend"
    
For each backend_service:
  If service has no API endpoint OR endpoint not called by frontend:
    → Mark as "Backend business logic not exposed/used"
```

#### 4.2 Frontend → Backend Gap Analysis

**Purpose**: Find frontend features NOT supported by backend

**Check for Missing Backend Support**:

```
For each frontend_api_call:
  If endpoint NOT in backend_endpoints:
    → Mark as "Frontend calling non-existent backend endpoint"
    
For each frontend_type:
  If type has no corresponding backend_model:
    → Mark as "Frontend expects data structure not provided by backend"
    
For each frontend_store/state:
  If data source has no backend endpoint:
    → Mark as "Frontend state management with no backend support"
```

#### 4.3 Contract Mismatch Analysis

**Purpose**: Find inconsistencies in shared contracts

**Check Request/Response Schemas**:

```
For each matching endpoint (exists in both layers):
  
  Backend Schema:
    - Extract: request body parameters
    - Extract: response body structure
    - Extract: query parameters
    - Extract: path parameters
    
  Frontend Usage:
    - Extract: data sent in request
    - Extract: expected response structure (TypeScript types)
    - Extract: query params used
    - Extract: path params used
    
  Compare:
    - Request fields: backend expects vs frontend sends
    - Response fields: backend returns vs frontend expects
    - Data types: backend types vs frontend types
    - Required vs optional fields
    - Field naming (camelCase vs snake_case)
    
  If mismatch found:
    → Mark as "Schema mismatch between layers"
```

#### 4.4 Authentication/Authorization Gaps

**Check Security Implementation**:

```
For each protected backend_endpoint:
  - Check: authentication required (JWT, session, etc.)
  - Check: authorization/permissions required
  
For each frontend_api_call to protected endpoint:
  - Check: auth token included in request
  - Check: auth state management exists
  - Check: unauthorized handling (401/403)
  
If mismatch:
  → Mark as "Auth/authz implementation gap"
```

#### 4.5 Error Handling Consistency

**Check Error Propagation**:

```
For each backend_endpoint:
  - Extract: all error responses (400, 404, 500, etc.)
  - Extract: error response format (code, message, details)
  
For each frontend_api_call:
  - Check: error handling exists (try/catch, .catch())
  - Check: error types handled match backend errors
  - Check: user feedback for errors (toasts, messages)
  
If mismatch:
  → Mark as "Error handling gap"
```

#### 4.6 Generate Integration Gap Report

Create detailed report in verification document:

```markdown
## 🔍 Backend-Frontend Integration Analysis

### Backend Features Not Used by Frontend ⚠️

| Backend Feature | Type | Location | Severity | Action Required |
|----------------|------|----------|----------|-----------------|
| GET /api/users/{id}/stats | Endpoint | src/routes/users.py:45 | HIGH | Implement in frontend or remove |
| UserStatsSchema | Model | src/schemas/user.py:12 | HIGH | Create TypeScript interface |
| calculate_user_score() | Service | src/services/analytics.py:78 | MEDIUM | Expose via API and integrate |

**Total Orphaned Backend Features**: 3

### Frontend Features Not Supported by Backend ⚠️

| Frontend Feature | Type | Location | Severity | Action Required |
|-----------------|------|----------|----------|-----------------|
| fetch('/api/notifications') | API Call | frontend/src/hooks/useNotifications.ts:23 | CRITICAL | Implement backend endpoint |
| NotificationPreferences | Interface | frontend/src/types/notifications.ts:8 | HIGH | Create backend model |
| notificationsStore | Store | frontend/src/stores/notifications.ts:15 | HIGH | Implement backend support |

**Total Missing Backend Support**: 3

### Schema/Contract Mismatches 🔴

| Endpoint | Issue | Backend | Frontend | Action Required |
|----------|-------|---------|----------|-----------------|
| POST /api/users | Field mismatch | Expects `email` (required) | Sends `userEmail` (optional) | Align field names |
| GET /api/projects/{id} | Type mismatch | Returns `created_at` (string) | Expects `createdAt` (Date) | Fix serialization |
| PUT /api/tasks/{id} | Missing field | Returns `updated_by` | Not in TaskInterface | Add to frontend type |

**Total Contract Mismatches**: 3

### Authentication/Authorization Gaps 🔒

| Issue | Backend | Frontend | Action Required |
|-------|---------|----------|-----------------|
| Protected endpoint | /api/admin/* requires role='admin' | No role check in frontend | Add role-based guards |
| Auth token | Expires in 1h | No refresh logic | Implement token refresh |
| Unauthorized handling | Returns 401 with reason | Generic error toast | Show specific message |

**Total Auth Gaps**: 3

### Error Handling Gaps ❌

| Endpoint | Backend Errors | Frontend Handling | Action Required |
|----------|---------------|-------------------|-----------------|
| POST /api/login | 401, 429, 500 | Only handles 401 | Handle rate limit, server errors |
| GET /api/data | 404 with details | Generic "Not found" | Show specific error details |

**Total Error Handling Gaps**: 2

### Summary Statistics

- **Backend Orphaned Features**: 3 (2 HIGH, 1 MEDIUM)
- **Frontend Missing Backend**: 3 (1 CRITICAL, 2 HIGH)
- **Contract Mismatches**: 3 (ALL HIGH)
- **Auth/Authz Gaps**: 3 (2 HIGH, 1 MEDIUM)
- **Error Handling Gaps**: 2 (1 HIGH, 1 MEDIUM)

**Total Integration Issues**: 14

### Priority Actions

1. **CRITICAL** - Implement missing backend endpoint: /api/notifications
2. **HIGH** - Fix schema mismatch: POST /api/users field names
3. **HIGH** - Remove orphaned backend: GET /api/users/{id}/stats or integrate
4. **HIGH** - Add frontend auth role guards for admin routes
5. **MEDIUM** - Implement token refresh logic
```

---

### 5. Test Verification

**Mandatory Testing Checklist (as per `docs/TESTING_STANDARDS.md`)**:
- [ ] **Backend Tests (`pytest`)**: `pytest tests/backend/ -v --cov=src`
- [ ] **Frontend Tests (`pytest-playwright`)**: `pytest --playwright tests/frontend/`
- [ ] **Integration tests**: `pytest tests/integration -v`

**Frontend Actions Coverage (100% Required)**:
- ✅ Button clicks (add, delete, edit, save, cancel)
- ✅ Form submissions
- ✅ Tab switching
- ✅ Modal open/close
- ✅ Dropdown selections
- ✅ Checkbox/radio toggles
- ✅ File uploads
- ✅ Drag & drop
- ✅ Keyboard navigation
- ✅ Hover interactions

**Test Requirements**:
- All tests must PASS (0 failures)
- Coverage ≥80% backend, 100% critical UI actions
- No skipped tests without justification
- Frontend actions 100% covered for UI features
- Performance: Unit <5s, Integration <30s, Frontend <2min

**Evidence Required**:
- Test execution logs with timestamps
- Screenshots of failed tests
- Coverage report showing 100% action coverage

### 6. Evidence Verification

**Required Evidence Files**:
- `docs/evidence/[feature]/PHASE_[N]_EVIDENCE.md` must exist
- Must contain:
  - Test execution logs with timestamps
  - Coverage reports
  - API testing results (Postman/curl)
  - Screenshots (for UI features)
  - Performance benchmarks (if applicable)

**Evidence Validation**:
- Timestamps must be recent (within last 7 days)
- Test results must show PASS status
- Coverage must meet acceptance criteria targets
- All acceptance criteria must have corresponding evidence

### 7. Documentation Verification

**Updated Files Check**:
- If task modifies API: verify `docs/api/` updated
- If task adds feature: verify `docs/MVP.md` updated
- If task changes architecture: verify `KNOWLEDGE_BANK.md` updated
- If task completes goal: verify `BUSINESS_GOALS.md` updated

---

### 8. Generate Verification Report

Create `docs/verification/[task_id]_verification_report.md`:

```markdown
# Task Verification Report

**Task**: [Task description]
**Task ID**: [task_id from backlog]
**Verification Date**: [timestamp]
**Verified By**: /verify_implementation command

## Specification
- Design Reference: [path to design doc]
- Acceptance Criteria: [list from backlog]
- Testing Requirements: [list from backlog]

## Code Verification Results

### Backend Components
- [✓/✗] File: src/[path]/[file].py
  - Expected: [description]
  - Found: [yes/no]
  - Status: [complete/incomplete/missing]
  - Issues: [list any problems]

### Frontend Components  
- [✓/✗] Component: frontend/src/[path]/[Component].tsx
  - Expected: [description]
  - Found: [yes/no]
  - Status: [complete/incomplete/missing]
  - Issues: [list any problems]

### API Endpoints
- [✓/✗] Endpoint: [method] /api/[path]
  - Defined: [yes/no]
  - Tested: [yes/no]
  - Issues: [list any problems]

## 🔍 Backend-Frontend Integration Analysis

[Include full integration gap report from step 4.6]

## Test Verification Results

### Unit Tests
- File: tests/[path]/test_[module].py
- Status: [✓ PASS / ✗ FAIL]
- Tests Run: [count]
- Passed: [count]
- Failed: [count]
- Coverage: [percentage]
- Log: [path to test output]

### Integration Tests
[Similar structure]

### Evidence Files
- [✓/✗] docs/evidence/[feature]/PHASE_[N]_EVIDENCE.md
  - Exists: [yes/no]
  - Complete: [yes/no]
  - Timestamp: [date]
  - Issues: [list any problems]

## Documentation Verification
- [✓/✗] API docs updated
- [✓/✗] MVP.md updated
- [✓/✗] KNOWLEDGE_BANK.md updated
- [✓/✗] BUSINESS_GOALS.md updated (if applicable)

## Overall Assessment

**Status**: [✓ VERIFIED / ⚠️ PARTIAL / ✗ FAILED]

**Summary**:
[Brief description of verification outcome]

**Issues Found**: [count]
- Code Issues: [count]
- Test Issues: [count]
- Integration Issues: [count] ⭐ NEW
- Documentation Issues: [count]

**Integration Health Score**: [X/10] ⭐ NEW
- Backend completeness: [percentage]
- Frontend completeness: [percentage]
- Contract consistency: [percentage]
- Auth/Error handling: [percentage]

**Recommendation**:
- [✓] Task can be marked DONE
- [⚠️] Task needs minor fixes before DONE
- [✗] Task is NOT complete - return to IN_PROGRESS

## Required Actions

[If not verified, list specific actions needed]

### Code Fixes
- [ ] Action 1
- [ ] Action 2

### Integration Fixes ⭐ NEW
- [ ] Implement missing backend endpoint: /api/[path]
- [ ] Add frontend integration for: [backend feature]
- [ ] Fix schema mismatch in: [endpoint]
- [ ] Remove orphaned feature: [feature]

### Test Fixes
- [ ] Action 1

### Documentation Fixes
- [ ] Action 1
```

---

### 9. Update Task Status

**If VERIFIED (✓)**:
- Keep task status as DONE in `SPRINT_BACKLOG.md`
- Add verification reference:

```markdown
- **Status**: DONE
- **Verification**: docs/verification/[task_id]_verification_report.md (✓ VERIFIED)
- **Evidence**: docs/evidence/[feature]/PHASE_[N]_EVIDENCE.md
- **Integration Score**: 9/10 ✓
```

**If PARTIAL (⚠️)**:
- Change status to IN_PROGRESS in `SPRINT_BACKLOG.md`
- Add blockers:

```markdown
- **Status**: IN_PROGRESS (verification issues found)
- **Blockers**: See docs/verification/[task_id]_verification_report.md
- **Integration Issues**: 5 gaps found between backend/frontend
- **Required Actions**: [list from report]
```

**If FAILED (✗)**:
- Change status to NOT_STARTED or IN_PROGRESS
- Add to `STATUS.md` → BLOCKER
- Create remediation tasks

---

## Output Summary

```
Verification Complete: [task_description]

Status: [✓ VERIFIED / ⚠️ PARTIAL / ✗ FAILED]

Code Checks: [X/Y passed]
Test Checks: [X/Y passed]
Integration Checks: [X/Y passed] ⭐ NEW
  - Backend orphaned features: [count]
  - Frontend missing backend: [count]
  - Contract mismatches: [count]
  - Auth/error gaps: [count]
Evidence: [complete/incomplete]
Documentation: [updated/outdated]

Integration Health Score: [X/10] ⭐ NEW

Report: docs/verification/[task_id]_verification_report.md

[If verified]
✓ Task legitimately complete - DONE status confirmed
✓ Backend and frontend fully synchronized

[If partial/failed]
✗ Task requires work - status changed to IN_PROGRESS
✗ Integration gaps found - see report for details
Required actions documented in verification report
```

---

## When to Use

- Before marking any task as DONE
- During sprint reviews to validate completed work
- Before `/end_sprint` to ensure sprint scope actually delivered
- When suspicious that documentation doesn't match code reality
- **When backend and frontend development are out of sync** ⭐ NEW
- **After major API changes to verify frontend compatibility** ⭐ NEW

## Integration with Other Commands

- `/work`: Should call `/verify_implementation` before moving task to DONE
- `/end_sprint`: Must call `/verify_implementation` for all DONE tasks
- `/sync_docs`: Should flag tasks marked DONE without verification reports
- **`/sync_layers`**: NEW command to auto-fix integration gaps ⭐ NEW

---

## Example Verification Output

```
🔍 Verifying Task: "User Authentication System"

✓ Backend Code: 5/5 files verified
✓ Frontend Code: 4/4 components verified
⚠️ Integration Check: 3 issues found
  - Missing endpoint: POST /api/auth/refresh
  - Schema mismatch: GET /api/user (field naming)
  - Orphaned backend: DELETE /api/sessions/all
✓ Tests: 45/45 passed (94% coverage)
✓ Evidence: Complete with timestamps
✓ Documentation: All files updated

Integration Health Score: 7/10

Status: ⚠️ PARTIAL - Integration fixes required

Required Actions:
1. Implement token refresh endpoint
2. Align user schema field names (snake_case → camelCase)
3. Either integrate or remove bulk session delete feature

Report: docs/verification/AUTH_001_verification_report.md
```