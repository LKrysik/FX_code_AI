# Story SEC-0-2: Strategy JSON Validation

Status: ready-for-dev

## Story

As a **trader**,
I want **strategy configurations to be validated against a strict schema**,
so that **malicious or malformed JSON cannot crash the system or execute unauthorized code**.

## Background

**SEC-P0: Strategy JSON Injection**
- **Severity:** CRITICAL
- **Vector:** Malformed strategy JSON from visual builder with malicious indicator names
- **Risk:** Code execution, system crash, data corruption
- **Impact:** System security compromised

## Acceptance Criteria

1. **AC1:** All indicator names validated against allowlist
2. **AC2:** All action names validated against allowlist
3. **AC3:** Malformed JSON rejected with clear error message
4. **AC4:** Validation happens server-side (not just client-side)
5. **AC5:** Validation logs rejected payloads for security audit

## Tasks / Subtasks

- [ ] **Task 1: Define Allowlists**
  - [ ] 1.1 Create `ALLOWED_INDICATOR_TYPES` from IndicatorType enum
  - [ ] 1.2 Create `ALLOWED_ACTION_TYPES` from ActionType enum
  - [ ] 1.3 Create `ALLOWED_CONDITION_OPERATORS` list
  - [ ] 1.4 Document allowlists in security docs

- [ ] **Task 2: Implement Schema Validation**
  - [ ] 2.1 Create `StrategyValidator` class
  - [ ] 2.2 Validate structure against JSON schema
  - [ ] 2.3 Validate all names against allowlists
  - [ ] 2.4 Validate numeric thresholds are within bounds

- [ ] **Task 3: Add Server-Side Validation**
  - [ ] 3.1 Add validation to POST /api/strategies endpoint
  - [ ] 3.2 Add validation to PUT /api/strategies/{id} endpoint
  - [ ] 3.3 Return 400 with details on validation failure
  - [ ] 3.4 Log all rejected payloads with timestamp and source IP

- [ ] **Task 4: Add Security Tests**
  - [ ] 4.1 Test with valid strategy JSON
  - [ ] 4.2 Test with unknown indicator names
  - [ ] 4.3 Test with SQL injection attempts
  - [ ] 4.4 Test with script injection attempts
  - [ ] 4.5 Test with deeply nested payloads

## Dev Notes

### Key Files

| File | Purpose |
|------|---------|
| `src/api/unified_server.py` | API endpoints |
| `src/core/domain/strategy.py` | Strategy domain model |
| `src/core/strategy_storage.py` | Strategy persistence |

### Allowlist Pattern

```python
from enum import Enum
from src.core.domain.indicator import IndicatorType

ALLOWED_INDICATOR_TYPES = {t.value for t in IndicatorType}
# e.g., {'twpa', 'pump_magnitude_pct', 'volume_surge_ratio', ...}

ALLOWED_CONDITION_OPERATORS = {
    'greater_than', 'less_than', 'equal_to',
    'greater_than_or_equal', 'less_than_or_equal'
}

def validate_indicator_name(name: str) -> bool:
    normalized = name.lower().strip()
    return normalized in ALLOWED_INDICATOR_TYPES
```

### Validation Error Response

```python
class StrategyValidationError(Exception):
    def __init__(self, field: str, value: str, reason: str):
        self.field = field
        self.value = value
        self.reason = reason

# Response format
{
    "error": "validation_failed",
    "details": [
        {"field": "sections[0].conditions[0].indicator_type",
         "value": "evil_indicator",
         "reason": "Unknown indicator type"}
    ]
}
```

### Security Logging

```python
logger.warning(
    f"SECURITY: Rejected strategy JSON from {request.client.host}",
    extra={
        "event": "strategy_validation_failed",
        "client_ip": request.client.host,
        "validation_errors": errors,
        "payload_hash": hashlib.sha256(payload).hexdigest()[:16]
    }
)
```

## References

- [Source: docs/KNOWN_ISSUES.md#SEC-P0: Strategy JSON Injection]
- [Source: src/core/domain/indicator.py#IndicatorType]
- [Source: src/api/unified_server.py]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
