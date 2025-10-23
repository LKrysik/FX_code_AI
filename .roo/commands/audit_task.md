---
description: "Multi-layer verification to prevent AI agent deception and false positives"
---

# /audit_task - Independent Task Verification

**Purpose**: Provide independent verification of task completion to prevent AI agent self-reporting bias and deception

**Usage**: /audit_task "[task_description]"

## ANTI-DECEPTION Audit Process

### 1. Evidence Authenticity Verification

#### **Timestamp and Context Validation:**
- [ ] Check all evidence has consistent timestamps
- [ ] Verify browser URLs match claimed functionality
- [ ] Validate git commit history matches claimed implementation
- [ ] Check file system timestamps align with implementation claims
- [ ] Verify console logs are from actual testing session

#### **Evidence Completeness Check:**
```markdown
Required Evidence Files:
- docs/evidence/[task]/workflow_demo.mp4 (video proof)
- docs/evidence/[task]/before_files.txt (baseline)
- docs/evidence/[task]/after_files.txt (changes)
- docs/evidence/[task]/api_testing.log (backend proof)
- docs/evidence/[task]/integration_results.md (integration proof)

Validation:
- [ ] ALL required files present
- [ ] File sizes reasonable (videos >500KB, logs >100 lines)
- [ ] Timestamps within reasonable implementation timeframe
- [ ] Content matches claimed functionality
```

### 2. Independent Functional Testing

#### **Fresh Environment Testing:**
```bash
# Start from clean state
rm -rf node_modules
npm install
npm run dev

# Test claimed functionality independently
# Open browser in incognito mode
# Navigate to feature URL
# Attempt to reproduce claimed workflows
```

#### **Black Box User Testing:**
- [ ] Attempt to use feature without reading implementation
- [ ] Follow USER_REC requirements exactly as written
- [ ] Try to break feature with unexpected inputs
- [ ] Verify error handling works as claimed
- [ ] Test integration with existing features

### 3. Code Quality Audit

#### **Implementation Completeness Check:**
```bash
# Search for TODO, FIXME, HACK comments
grep -r "TODO\|FIXME\|HACK" src/
# Should return minimal results for production code

# Check for placeholder/mock implementations
grep -r "placeholder\|mock\|fake" src/
# Should return no results in business logic

# Verify test coverage
npm test -- --coverage
# Should meet minimum coverage requirements
```

#### **Integration Point Validation:**
- [ ] Verify all API endpoints actually exist and work
- [ ] Check database/file operations actually persist data
- [ ] Validate UI updates reflect backend state changes
- [ ] Confirm error handling covers realistic scenarios

### 4. Requirement Compliance Audit

#### **USER_REC Mapping Verification:**
```markdown
For each sentence in relevant USER_REC:
1. "Strategy Builder ma dwie zakładki"
   ✅/❌ Two tabs present in implementation
   ✅/❌ Tab switching functional
   ✅/❌ Content preserved between switches

2. "można edytować, albo kopiować/klonować oraz usuwać"
   ✅/❌ Edit functionality works
   ✅/❌ Copy/clone functionality works  
   ✅/❌ Delete functionality works
   ✅/❌ Error handling for each operation

3. [Continue for all USER_REC sentences]
```

#### **Business Logic Verification:**
- [ ] Core business rules implemented correctly
- [ ] Data validation matches specifications
- [ ] Workflows match intended user experience
- [ ] Performance meets stated requirements

### 5. Regression Testing Audit

#### **Existing Feature Impact Check:**
```bash
# Run full regression test suite
npm run test:regression

# Check performance benchmarks
npm run benchmark

# Verify no new errors in logs
npm run dev 2>&1 | grep -i error
# Should show minimal/no errors
```

#### **Integration Stability Verification:**
- [ ] Existing user workflows still work
- [ ] Data consistency maintained across features
- [ ] No performance degradation detected
- [ ] Memory usage within acceptable limits

### 6. Red Team Attack Testing

#### **Malicious User Simulation:**
- [ ] Rapid button clicking/form submission
- [ ] Invalid/malicious data injection attempts
- [ ] Concurrent access from multiple sessions
- [ ] Browser back/forward navigation stress testing
- [ ] Network interruption simulation

#### **Edge Case Exploitation:**
- [ ] Boundary value testing (max/min inputs)
- [ ] Unicode/special character handling
- [ ] Large data volume handling
- [ ] Slow network condition testing
- [ ] Mobile/tablet compatibility testing

### 7. Verification Decision Matrix

#### **AUDIT_PASSED** - Only if ALL criteria met:
- [ ] All evidence files present and authentic
- [ ] Independent testing confirms functionality
- [ ] Code quality meets standards
- [ ] All USER_REC requirements implemented
- [ ] Regression tests pass
- [ ] Red team testing reveals no critical issues
- [ ] Integration with existing features verified
- [ ] Performance benchmarks met

#### **AUDIT_FAILED** - If ANY critical issue found:
- List specific failures with evidence
- Provide exact reproduction steps
- Categorize issues: Critical/Major/Minor
- Recommend specific fixes
- Estimate time required for resolution

#### **AUDIT_INCOMPLETE** - If verification blocked:
- Missing evidence files
- Environment setup issues
- Dependency problems
- Unclear requirements

### 8. Common Deception Patterns Detection

#### **Pattern 1: Facade Implementation**
```markdown
DETECTION SIGNS:
- UI components render but don't function
- API endpoints return mock data
- File operations simulate but don't persist
- Error handling shows generic messages
- Performance testing skipped

VERIFICATION:
- Test all interactive elements manually
- Verify data persistence after browser refresh
- Check file system for actual changes
- Test error scenarios with invalid data
```

#### **Pattern 2: Happy Path Only**
```markdown
DETECTION SIGNS:
- Only ideal scenarios tested
- Error cases not implemented
- Edge cases ignored
- Integration testing superficial

VERIFICATION:
- Intentionally provide invalid inputs
- Test boundary conditions
- Simulate network failures
- Test concurrent usage scenarios
```

#### **Pattern 3: Evidence Fabrication**
```markdown
DETECTION SIGNS:
- Screenshots from different sessions
- Inconsistent timestamps
- Generic/template evidence
- Missing specific details

VERIFICATION:
- Cross-reference timestamps
- Verify file system states
- Check browser history
- Validate git commit correlation
```

## Audit Output

### Audit Status: [AUDIT_PASSED/AUDIT_FAILED/AUDIT_INCOMPLETE]

### Evidence Validation Results
- **Authenticity**: [VERIFIED/SUSPICIOUS/INVALID]
- **Completeness**: [COMPLETE/MISSING_ITEMS/INSUFFICIENT]
- **Quality**: [HIGH/ADEQUATE/POOR]

### Independent Testing Results
- **Functionality**: [WORKS_AS_CLAIMED/PARTIAL/BROKEN]
- **Integration**: [SEAMLESS/ISSUES_FOUND/BROKEN]
- **Performance**: [MEETS_REQUIREMENTS/DEGRADED/UNACCEPTABLE]

### Requirement Compliance
- **USER_REC Coverage**: [X]% of requirements implemented
- **Business Logic**: [CORRECT/ISSUES_FOUND/INCORRECT]
- **Edge Cases**: [HANDLED/PARTIAL/IGNORED]

### Critical Issues Found
[List any critical problems that block production deployment]

### Minor Issues Found  
[List minor issues that should be addressed but don't block deployment]

### Recommendations
- **If AUDIT_PASSED**: Safe to deploy to production
- **If AUDIT_FAILED**: Return to development with specific fix list
- **If AUDIT_INCOMPLETE**: Resolve blockers and re-audit

### Evidence Archive
- Audit evidence saved to: `docs/audit/[task]/[timestamp]/`
- Independent test results: `docs/audit/[task]/independent_testing.md`
- Issue tracking: `docs/audit/[task]/issues_found.md`

## Integration with Workflow

**This command should be run AFTER `/verify_implementation` and BEFORE marking task as DONE**

**Workflow Integration:**
1. AI agent completes task with `/work`
2. AI agent self-verifies with `/verify_implementation`
3. **Independent audit with `/audit_task`** (NEW STEP)
4. Only if audit passes → task can be marked DONE
5. Sprint closure proceeds with `/end_sprint`

**Protection Level**: **90%+ reduction in false positives through independent verification**