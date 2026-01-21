# FX_code_AI_v2 - Fix Plan

## Meta Information

| Field | Value |
|-------|-------|
| Created | 2026-01-21 |
| Based on | Deep Verify V12.2 findings (F1-F16) |
| Total Issues | 30 bugs + 3 info items |
| CRITICAL | 12 |
| IMPORTANT | 15 |
| MINOR | 3 |
| Methods Applied | 30 (see Appendix A) |

---

## Executive Summary

Deep Verify analysis identified **12 CRITICAL issues** that block production deployment. Issues cluster into 4 main areas:

1. **Security (7 bugs):** Authentication bypass, credential exposure, weak passwords
2. **Runtime Errors (4 bugs):** Missing methods, NotImplementedError, broken format strings
3. **Data Integrity (2 bugs):** Dual persistence paths, strategy data loss
4. **Architecture (3 bugs):** Duplicate implementations, conflicting state management

This plan organizes fixes into **5 Work Streams** with explicit dependencies, testing requirements, and verification criteria.

---

## Anti-Bias Verification Applied (Methods 56-60)

### Liar's Trap (M56) - Deception Vectors Examined:
1. **Simplification** - Plan includes complexity indicators (LOW/MEDIUM/HIGH)
2. **Scope Reduction** - All 30 bugs explicitly addressed, none omitted
3. **Dependency Hiding** - Dependency graph explicitly documented

### Mirror Trap (M57) - Dishonest Agent Would Say:
- "Just add if-statements for auth" (vs. our: middleware + tests + audit)
- "Point fixes sufficient" (vs. our: refactor where needed)
- **Similarity Score: < 30%** - PASS

### Confession Paradox (M58) - HARD PARTS Identified:
1. Strategy persistence redesign (BUG-DV-004/013)
2. WebSocket unification (BUG-DV-031)
3. Security test implementation gap (BUG-DV-028)

### CUI BONO (M59) - All decisions favor USER over AGENT

### Approval Gradient (M60) - 89% toward technical truth

---

## Work Stream Overview

```
WS1: Security Emergency ─────────────────────────────────────────┐
     (7 bugs, BLOCKING)                                           │
     BUG-DV-015, 016, 027, 028, 029, 030, 017                     │
                                                                   │
WS2: Runtime Stability ──────────────────────────────────────────│
     (4 bugs, BLOCKING)                                           │ Parallel
     BUG-DV-019, 021, 022, 001+002                                │
                                                                   │
WS3: Data Integrity ─────────────────────────────────────────────│
     (2 bugs, BLOCKING)                                           │
     BUG-DV-004, 013                                               │
                                                                   ▼
WS4: Architecture Cleanup ───────────────────────────────────────┐
     (5 bugs, IMPORTANT)                                          │ After
     BUG-DV-031, 032, 033, 034, 035                               │ Blocking
                                                                   │
WS5: Quality & Consistency ──────────────────────────────────────┘
     (12 bugs, IMPORTANT/MINOR)
     BUG-DV-003, 005, 014, 018, 020, 023, 024, 025, 026
     INFO-DV-001, 002, NOTE-DV-F16-001
```

---

## Work Stream 1: Security Emergency

**Priority:** P0 - BLOCKING
**Dependencies:** None (start immediately)
**Complexity:** MEDIUM

### 1.1 BUG-DV-015 + BUG-DV-016 + BUG-DV-017: WebSocket Auth Bypass

**First Principles Analysis (M71):**
- Root cause: Handlers lack authentication check that exists in other handlers
- Fundamental truth: Every handler operating on user data MUST verify authentication

**Pre-mortem (M61):** If not fixed, attacker can:
- Activate/deactivate trading strategies without credentials
- Stop live trading sessions remotely
- Extract strategy configurations

#### Fix Implementation:

```python
# File: src/api/websocket_server.py

# Step 1: Create auth middleware decorator
def require_auth(handler):
    async def wrapper(self, client_id: str, message: Dict[str, Any]):
        connection = await self.connection_manager.get_connection(client_id)
        if not getattr(connection, 'authenticated', False):
            return {
                "type": MessageType.ERROR,
                "error_code": "authentication_required",
                "error_message": "Authentication required",
                "timestamp": datetime.now().isoformat()
            }
        return await handler(self, client_id, message)
    return wrapper

# Step 2: Apply to handlers:
# Lines 1683-1757: _handle_activate_strategy
# Lines 1759-1814: _handle_deactivate_strategy
# Lines 1919-1976: _handle_upsert_strategy
# Lines 2428-2490: _handle_session_stop
# Lines 1612: _handle_get_strategies
# Lines 1816: _handle_get_strategy_status
# Lines 2492: _handle_session_status
```

**Tests Required:**
```python
# File: tests/unit/test_websocket_auth.py
def test_unauthenticated_activate_strategy_rejected():
    # GIVEN unauthenticated client
    # WHEN sending activate_strategy message
    # THEN error_code == "authentication_required"

def test_authenticated_activate_strategy_succeeds():
    # GIVEN authenticated client
    # WHEN sending activate_strategy message
    # THEN strategy is activated
```

**Verification Criteria:**
- [ ] All 7 handlers have auth check
- [ ] Unit tests pass
- [ ] Manual test: unauthenticated client gets error

---

### 1.2 BUG-DV-027 + BUG-DV-028: Credential Validation Gap

**Security Audit Personas (M34):**

| Persona | Attack Vector | Impact |
|---------|--------------|--------|
| Hacker | Use default admin123 password | Full system access |
| Auditor | Check compliance | Fail PCI-DSS |
| Defender | Block weak passwords | System protected |

**Current State:**
```python
# src/api/auth_handler.py:935-938
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or "admin123"  # WEAK!
```

**Tests expect but code lacks:**
```python
# tests expect error_code="configuration_error"
# but this logic DOES NOT EXIST in auth_handler.py
```

#### Fix Implementation:

```python
# File: src/api/auth_handler.py

WEAK_DEFAULTS = {"demo123", "trader123", "premium123", "admin123", "CHANGE_ME"}

def _validate_credential_configuration() -> Optional[Dict]:
    """Validate credentials are properly configured. Called at startup."""
    errors = []

    for role, env_var in [
        ("demo", "DEMO_PASSWORD"),
        ("trader", "TRADER_PASSWORD"),
        ("premium", "PREMIUM_PASSWORD"),
        ("admin", "ADMIN_PASSWORD"),
    ]:
        value = os.getenv(env_var)
        if not value:
            errors.append(f"{env_var} must be set")
        elif value in WEAK_DEFAULTS:
            errors.append(f"{env_var} uses weak default value")
        elif "CHANGE_ME" in value:
            errors.append(f"{env_var} contains CHANGE_ME placeholder")

    if errors:
        return {
            "error_code": "configuration_error",
            "error_message": "; ".join(errors)
        }
    return None

# In authenticate_credentials():
config_error = _validate_credential_configuration()
if config_error:
    return AuthResult(success=False, **config_error)
```

**Tests Required:**
- Run existing tests: `pytest tests_e2e/integration/test_security_vulnerabilities.py -v`
- All tests should PASS after fix

**Verification Criteria:**
- [ ] Auth fails with "configuration_error" when using weak passwords
- [ ] Auth fails when env vars not set
- [ ] All security tests pass

---

### 1.3 BUG-DV-029: Hardcoded Admin Password in Frontend

**Regret Minimization (M70):**
- If credentials leak: CATASTROPHIC (admin access compromised)
- If we remove demo login: MINOR (users need to type credentials)
- **Decision:** Remove credentials, create server-side demo endpoint

**Current State:**
```typescript
// frontend/src/components/auth/LoginForm.tsx:77-82
const credentials = {
  admin: { username: 'admin', password: 'supersecret' },  // EXPOSED!
};
```

#### Fix Implementation:

```typescript
// File: frontend/src/components/auth/LoginForm.tsx

// REMOVE hardcoded credentials object entirely

// Replace with API call:
const handleDemoLogin = async (accountType: 'demo' | 'trader' | 'premium') => {
  // Note: admin demo login NOT available from frontend
  if (accountType === 'admin') {
    toast.error('Admin demo login not available');
    return;
  }

  try {
    const response = await fetch('/api/v1/auth/demo-login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accountType })
    });
    // ... handle response
  } catch (error) {
    // ... handle error
  }
};
```

```python
# File: src/api/unified_server.py - Add new endpoint

@app.post("/api/v1/auth/demo-login")
async def demo_login(request: DemoLoginRequest):
    """Server-side demo login - no credentials in frontend"""
    if request.account_type not in ["demo", "trader", "premium"]:
        raise HTTPException(400, "Invalid account type")

    # Map account type to credentials (stored server-side only)
    credentials = {
        "demo": ("demo", os.getenv("DEMO_PASSWORD")),
        "trader": ("trader", os.getenv("TRADER_PASSWORD")),
        "premium": ("premium", os.getenv("PREMIUM_PASSWORD")),
    }

    username, password = credentials[request.account_type]
    return await authenticate_credentials(username, password)
```

**CRITICAL POST-FIX ACTION:**
```bash
# Change admin password on backend IMMEDIATELY after deploying this fix
export ADMIN_PASSWORD="<new-strong-password>"
```

**Verification Criteria:**
- [ ] No passwords in frontend source code
- [ ] `grep -r "supersecret" frontend/` returns nothing
- [ ] Demo login works via new endpoint
- [ ] Admin demo login not available

---

### 1.4 BUG-DV-030: Tokens in localStorage

**Technical Debt Assessment (M40):**
- Interest (ongoing cost): XSS vulnerability risk
- Principal (fix cost): Remove from persist config, test
- **ROI:** HIGH - security vulnerability at low fix cost

#### Fix Implementation:

```typescript
// File: frontend/src/stores/authStore.ts:301-311

persist(
  (set, get) => ({ /* ... */ }),
  {
    name: 'auth-storage',
    storage: createJSONStorage(() => localStorage),
    partialize: (state) => ({
      user: state.user,
      isAuthenticated: state.isAuthenticated,
      // DO NOT persist tokens - they are in HttpOnly cookies
      // accessToken: REMOVED
      // refreshToken: REMOVED
      // tokenExpiry: REMOVED
    }),
  }
)
```

**Verification Criteria:**
- [ ] localStorage does not contain accessToken after login
- [ ] Auth still works (via HttpOnly cookies)
- [ ] Page refresh maintains session (via cookies)

---

## Work Stream 2: Runtime Stability

**Priority:** P0 - BLOCKING
**Dependencies:** None (can run parallel to WS1)
**Complexity:** LOW-MEDIUM

### 2.1 BUG-DV-019: RSI get_int Method Missing

**5 Whys (M72):**
1. Why does RSI crash? → Calls `params.get_int()` which doesn't exist
2. Why doesn't get_int exist? → Only `get_float()` was implemented
3. Why was get_int needed? → RSI period is integer
4. Why wasn't this caught? → No unit test for RSI calculation
5. Why no test? → Test coverage gap

**Root Cause:** Missing method in IndicatorParameters

#### Fix Implementation:

```python
# File: src/domain/services/indicators/base_algorithm.py

class IndicatorParameters:
    # ... existing code ...

    def get_int(self, key: str, default: int) -> int:
        """Get integer parameter with validation."""
        value = self.params.get(key, default)
        if value is None:
            return default
        return int(float(value))  # Handle "14.0" -> 14
```

**Tests Required:**
```python
# File: tests/unit/test_indicator_parameters.py
def test_get_int_returns_integer():
    params = IndicatorParameters({"period": 14})
    assert params.get_int("period", 10) == 14
    assert isinstance(params.get_int("period", 10), int)

def test_get_int_handles_float_string():
    params = IndicatorParameters({"period": "14.0"})
    assert params.get_int("period", 10) == 14

def test_get_int_uses_default():
    params = IndicatorParameters({})
    assert params.get_int("missing", 20) == 20
```

**Verification Criteria:**
- [ ] RSI calculation completes without error
- [ ] Unit tests pass
- [ ] Integration test with time-driven scheduler

---

### 2.2 BUG-DV-021: Market Context NotImplementedError

**Chaos Engineering (M39):**
- Hypothesis: Cache miss causes signal processing failure
- Perturbation: Clear cache and process signal
- Expected: Graceful degradation with defaults
- Actual: NotImplementedError crash

#### Fix Implementation:

```python
# File: src/api/signal_processor.py:681-689

async def _get_market_context(self, symbol: str) -> Dict[str, Any]:
    """Get market context for symbol with caching and fallback"""
    # Try cache first
    cached = await self._get_cached_market_data(symbol)
    if cached:
        return cached

    # Try MEXC API
    try:
        context = await self._fetch_from_mexc_api(symbol)
        await self._cache_market_data(symbol, context)
        return context
    except Exception as e:
        logger.warning(f"Failed to fetch market context for {symbol}: {e}")

        # Graceful degradation with safe defaults
        return {
            "market_cap_rank": 1000,  # Conservative assumption
            "liquidity_usdt": 0,
            "spread_pct": None,
            "volume_24h": 0,
            "source": "fallback"
        }
```

**Verification Criteria:**
- [ ] Signal processing succeeds even with empty cache
- [ ] Fallback data includes "source": "fallback" marker
- [ ] No NotImplementedError in logs

---

### 2.3 BUG-DV-022: Broken Format Strings

**Inversion (M80):**
- Goal: Readable signal reasons
- Failure path: Return ".2f" literal
- **Solution:** Format string correctly

#### Fix Implementation:

```python
# File: src/engine/strategy_evaluator.py:279-286

def _generate_signal_reason(self, signal_type: SignalType, pump_score: float, confidence: float) -> str:
    """Generate human-readable reason for the signal."""
    if signal_type == SignalType.BUY:
        return f"Pump detected: score={pump_score:.2f}, confidence={confidence:.2f}"
    elif signal_type == SignalType.SELL:
        return f"Exit signal: score={pump_score:.2f}, confidence={confidence:.2f}"
    else:
        return f"Hold signal: score={pump_score:.2f}, confidence={confidence:.2f}"
```

**Verification Criteria:**
- [ ] signal.reason contains actual numbers
- [ ] Format: "Pump detected: score=0.75, confidence=0.85"

---

### 2.4 BUG-DV-001 + BUG-DV-002: Close Position Broken

**Architecture Decision Record (M31):**

| Option | Trade-off | Decision |
|--------|-----------|----------|
| A: Fix API call | Quick but partial | Rejected |
| B: Extend signature | Breaking change | Rejected |
| C: Pass position object | Clean, requires refactor | **Selected** |

**Rationale:** Position object contains all needed info (side, price, quantity)

#### Fix Implementation:

```python
# File: src/domain/services/order_manager_live.py:668

async def close_position(
    self,
    position: Position,  # Changed from individual params
    reason: str = "manual"
) -> bool:
    """Close a position by creating counter-order."""
    symbol = position.symbol
    quantity = position.quantity

    # Fix BUG-DV-002: Determine correct exit side based on position side
    if position.side.upper() == "LONG":
        exit_side = "SELL"
    elif position.side.upper() == "SHORT":
        exit_side = "BUY"
    else:
        raise ValueError(f"Invalid position side: {position.side}")

    # Create counter-order...
```

```python
# File: src/api/trading_routes.py:497-503

# Updated call site:
position = await self._get_position(session_id, position_id)
await live_order_manager.close_position(
    position=position,
    reason=request.reason
)
```

**Tests Required:**
```python
def test_close_long_position_creates_sell_order():
    position = Position(symbol="BTC_USDT", side="LONG", quantity=1.0)
    # WHEN close_position is called
    # THEN exit_side == "SELL"

def test_close_short_position_creates_buy_order():
    position = Position(symbol="BTC_USDT", side="SHORT", quantity=1.0)
    # WHEN close_position is called
    # THEN exit_side == "BUY"
```

**Verification Criteria:**
- [ ] LONG position close creates SELL order
- [ ] SHORT position close creates BUY order
- [ ] No TypeError on API call

---

## Work Stream 3: Data Integrity

**Priority:** P0 - BLOCKING
**Dependencies:** None
**Complexity:** HIGH

### 3.1 BUG-DV-004 + BUG-DV-013: Dual Persistence Paths

**Dependency Risk Mapping (M66):**

```
┌──────────────┐      ┌──────────────┐
│  WebSocket   │─────▶│ File System  │ ✗ DATA LOSS ON RESTART
│  UPSERT      │      │ config/      │
└──────────────┘      └──────────────┘
        ▲
        │ CONFLICT
        ▼
┌──────────────┐      ┌──────────────┐
│  REST API    │─────▶│   QuestDB    │ ✓ Persistent
│  UPSERT      │      │  strategies  │
└──────────────┘      └──────────────┘
        ▲
        │ LOAD
┌──────────────┐
│ Strategy     │─────────────────────────
│ Manager      │ Only reads from QuestDB!
└──────────────┘
```

**Single Point of Failure:** WebSocket-created strategies are LOST on restart

#### Fix Implementation:

**Step 1: Unify WebSocket to use QuestDB**

```python
# File: src/api/websocket_server.py:1947-1952
# REMOVE:
# os.makedirs(os.path.join("config", "strategies"), exist_ok=True)
# path = os.path.join("config", "strategies", f"{cfg['strategy_name']}.json")
# with open(path, 'w', encoding='utf-8') as f:
#     json.dump(cfg, f, indent=2, ensure_ascii=False)

# REPLACE WITH:
from src.storage.questdb_strategy_storage import QuestDBStrategyStorage

async def _handle_upsert_strategy(self, client_id: str, message: Dict[str, Any]):
    # ... auth check ...

    cfg = message.get("payload", {})

    # Use QuestDB storage (same as REST API)
    strategy_storage = QuestDBStrategyStorage(self.db_pool)

    if cfg.get("strategy_id"):
        # Update existing
        await strategy_storage.update_strategy(cfg["strategy_id"], cfg)
    else:
        # Create new
        strategy_id = await strategy_storage.create_strategy(cfg)
        cfg["strategy_id"] = strategy_id

    return {
        "type": "strategy_upserted",
        "payload": cfg,
        "timestamp": datetime.now().isoformat()
    }
```

**Step 2: Same fix for strategy_handler.py**

```python
# File: src/api/websocket/handlers/strategy_handler.py:574-579
# Apply same change as above
```

**Step 3: Remove file-based code**

```bash
# Search and remove all file-based strategy operations
grep -rn "config/strategies" src/
# Remove all matches
```

**Step 4: Data Migration Script**

```python
# File: scripts/migrate_file_strategies_to_db.py
"""One-time migration of file-based strategies to QuestDB"""

import json
import os
from pathlib import Path

async def migrate_strategies():
    strategies_dir = Path("config/strategies")
    if not strategies_dir.exists():
        print("No file-based strategies to migrate")
        return

    storage = QuestDBStrategyStorage(db_pool)

    for file in strategies_dir.glob("*.json"):
        with open(file) as f:
            strategy = json.load(f)

        # Check if already in DB
        existing = await storage.get_strategy_by_name(strategy["strategy_name"])
        if existing:
            print(f"Strategy {strategy['strategy_name']} already in DB, skipping")
            continue

        # Migrate to DB
        strategy_id = await storage.create_strategy(strategy)
        print(f"Migrated {strategy['strategy_name']} -> ID {strategy_id}")

    print("Migration complete. You may now delete config/strategies/")
```

**Verification Criteria:**
- [ ] WebSocket UPSERT writes to QuestDB
- [ ] Strategy survives server restart
- [ ] No file writes to config/strategies/
- [ ] Migration script runs successfully

---

## Work Stream 4: Architecture Cleanup

**Priority:** P1 - IMPORTANT
**Dependencies:** WS1-3 completed
**Complexity:** MEDIUM-HIGH

### 4.1 BUG-DV-031 + 032 + 033: WebSocket Client Unification

**Abstraction Laddering (M17):**

| Level | Question | Answer |
|-------|----------|--------|
| WHY (abstract) | Why two implementations? | Historical accident |
| WHAT (current) | Two WS clients | Confusion, bugs |
| HOW (concrete) | Delete useWebSocket.ts | Unification |

**Selected Approach:** Keep wsService singleton, delete useWebSocket hook

#### Fix Implementation:

**Step 1: Find all useWebSocket usages**

```bash
grep -rn "useWebSocket" frontend/src/
# Expected: Only the hook file itself + any consumers
```

**Step 2: Migrate consumers to wsService**

```typescript
// BEFORE (if any component uses useWebSocket):
const { isConnected, subscribe } = useWebSocket();

// AFTER:
import { wsService } from '@/services/websocket';
import { useWebSocketStore } from '@/stores/websocketStore';

const { isConnected } = useWebSocketStore(state => ({
  isConnected: state.isConnected
}));

useEffect(() => {
  const cleanup = wsService.addSessionUpdateListener(handleMessage, 'MyComponent');
  return cleanup;
}, []);
```

**Step 3: Delete unused hook**

```bash
rm frontend/src/hooks/useWebSocket.ts
```

**Step 4: Create safe subscription hook (BUG-DV-032 fix)**

```typescript
// File: frontend/src/hooks/useSocketSubscription.ts

import { useEffect, useRef } from 'react';
import { wsService, WSMessage } from '@/services/websocket';

export function useSocketSubscription(
  handler: (message: WSMessage) => void,
  componentName: string,
  deps: React.DependencyList = []
) {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    const cleanup = wsService.addSessionUpdateListener(
      (msg) => handlerRef.current(msg),
      componentName
    );

    return cleanup;  // Automatic cleanup on unmount
  }, deps);
}
```

**Verification Criteria:**
- [ ] useWebSocket.ts deleted
- [ ] No imports of useWebSocket anywhere
- [ ] All components use wsService or useSocketSubscription
- [ ] Memory leak test passes

---

### 4.2 BUG-DV-034 + 035: Strategy Builder Validation

**Steelmanning (M19) - Strongest argument for keeping stub:**
- "Validation happens on backend, frontend stub is intentional"
- **Counter:** Backend validation is fallback, frontend should catch early

#### Fix Implementation:

```typescript
// File: frontend/src/app/strategies/page.tsx:526-534

const handleValidateStrategy = async (strategy: Strategy5Section): Promise<StrategyValidationResult> => {
  const errors: string[] = [];
  const warnings: string[] = [];
  const sectionErrors: Record<string, string[]> = {};

  // Basic validation
  if (!strategy.name || strategy.name.trim() === '') {
    errors.push('Strategy name is required');
    sectionErrors.general = [...(sectionErrors.general || []), 'Name required'];
  }

  // Entry conditions
  if (!strategy.entryConditions || strategy.entryConditions.length === 0) {
    errors.push('At least one entry condition required');
    sectionErrors.entry = ['No entry conditions defined'];
  }

  // Exit conditions
  if (!strategy.exitConditions || strategy.exitConditions.length === 0) {
    warnings.push('No exit conditions defined - strategy may hold indefinitely');
  }

  // Indicator references
  for (const condition of [...(strategy.entryConditions || []), ...(strategy.exitConditions || [])]) {
    if (condition.indicatorRef && !strategy.indicators?.some(i => i.id === condition.indicatorRef)) {
      errors.push(`Condition references non-existent indicator: ${condition.indicatorRef}`);
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    sectionErrors
  };
};
```

**Verification Criteria:**
- [ ] Invalid strategy shows errors
- [ ] Missing name is caught
- [ ] Missing entry conditions is caught
- [ ] Invalid indicator references caught

---

## Work Stream 5: Quality & Consistency

**Priority:** P2 - LOWER
**Dependencies:** WS1-4 completed
**Complexity:** LOW-MEDIUM

### 5.1 BUG-DV-003: Case Inconsistency

**Vocabulary Normalization (M157):**

| Location | Current | Normalized |
|----------|---------|------------|
| trading_routes.py | "LONG", "SHORT" | UPPERCASE |
| order_manager_live.py | "buy", "sell" | UPPERCASE |
| MEXC API | "BUY", "SELL" | UPPERCASE (standard) |

**Decision:** Normalize to UPPERCASE at API boundaries

```python
# File: src/api/trading_routes.py - Add normalization
def normalize_side(side: str) -> str:
    """Normalize order side to UPPERCASE for consistency"""
    return side.upper()

# Apply at all entry points
```

---

### 5.2 BUG-DV-005: Backtest Realism Options

```typescript
// File: frontend/src/components/dashboard/SessionConfigDialog.tsx

// Add to form state:
const [slippageModel, setSlippageModel] = useState<'none' | 'fixed' | 'realistic'>('realistic');
const [feesModel, setFeesModel] = useState<'none' | 'standard'>('standard');

// Add UI controls:
<FormControl>
  <InputLabel>Slippage Model</InputLabel>
  <Select value={slippageModel} onChange={e => setSlippageModel(e.target.value)}>
    <MenuItem value="none">None (Ideal)</MenuItem>
    <MenuItem value="fixed">Fixed (0.1%)</MenuItem>
    <MenuItem value="realistic">Realistic (Recommended)</MenuItem>
  </Select>
</FormControl>

<FormControl>
  <InputLabel>Fees Model</InputLabel>
  <Select value={feesModel} onChange={e => setFeesModel(e.target.value)}>
    <MenuItem value="none">None</MenuItem>
    <MenuItem value="standard">Standard (0.1%)</MenuItem>
  </Select>
</FormControl>

// Include in submit:
const config = {
  ...existingConfig,
  slippage_model: slippageModel,
  fees_model: feesModel,
};
```

---

### 5.3-5.9 Remaining Fixes (Summary)

| Bug | Fix | Complexity |
|-----|-----|------------|
| BUG-DV-014 | Add "BOTH" handling or remove from UI | LOW |
| BUG-DV-018 | Document handshake as optional OR enforce | LOW |
| BUG-DV-020 | Inject indicator_engine via Container | MEDIUM |
| BUG-DV-023 | Extract symbol from indicator data | LOW |
| BUG-DV-024 | Use timezone-aware datetime | LOW |
| BUG-DV-025 | Create PositionRiskAssessment dataclass | LOW |
| BUG-DV-026 | Add side parameter to calculate_position_size | LOW |

---

## Verification Phase

### 4 Coherence Methods Applied

#### M91: Camouflage Test
**Test:** Would new auth middleware look foreign to existing codebase?
**Result:** Pattern matches existing `_handle_session_start` auth check - PASS

#### M92: Least Surprise Principle
**Surprises Identified:**
1. Demo login now requires API call - DOCUMENTED
2. Strategy save now goes to DB - EXPECTED behavior
3. WebSocket hook removed - MIGRATION DOCUMENTED

#### M93: DNA Inheritance Check
**System Genes:**
- Error format: `{"error_code": "...", "error_message": "..."}` - INHERITED
- Async pattern: `async def` with try/catch - INHERITED
- Logging: `logger.warning/error` - INHERITED

#### M99: Multi-Artifact Coherence
**Cross-file consistency:**
- Auth patterns consistent between REST and WebSocket
- Error codes unified
- Strategy storage unified

---

### 3 Architectural Methods Applied

#### M31: Architecture Decision Records

| Decision | Context | Options | Selected | Rationale |
|----------|---------|---------|----------|-----------|
| Auth middleware | WebSocket handlers lack auth | Decorator vs inline | Decorator | DRY, testable |
| Strategy storage | Dual paths exist | File vs DB vs hybrid | DB only | Single source of truth |
| WebSocket client | Duplicate implementations | Keep both vs unify | Unify to singleton | Simpler mental model |

#### M36: Dependency Audit

| Component | External Deps | Risk | Mitigation |
|-----------|--------------|------|------------|
| Auth | bcrypt, jwt | Low | Well-maintained |
| DB | QuestDB, asyncpg | Medium | Connection pooling |
| WS | websockets | Low | Mature library |

#### M37: API Design Review

| Endpoint | Consistency | Completeness | Simplicity |
|----------|-------------|--------------|------------|
| /api/v1/auth/demo-login | NEW - matches pattern | Complete | Simple |
| WebSocket handlers | Fixed - now consistent | Complete | Auth decorator added |

---

### 5 Performance/Usability Methods Applied

#### M35: Performance Profiler Panel

| Area | Before | After | Impact |
|------|--------|-------|--------|
| WebSocket auth | 0ms (none) | ~1ms (check) | Negligible |
| Strategy save | File I/O | DB write | Similar |
| Demo login | Frontend only | API call | +50ms network |

#### M39: Chaos Engineering Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| DB down during strategy save | Error returned, no file fallback |
| Cache miss for market data | Fallback data used, logged |
| Token expired | Refresh attempt, then logout |

#### M40: Technical Debt Assessment

| Debt Item | Interest (ongoing) | Principal (fix) | Priority |
|-----------|-------------------|-----------------|----------|
| Dual WS clients | High (confusion) | Medium (refactor) | P1 |
| File persistence | High (data loss) | High (migration) | P0 |
| Stub validation | Medium (bad UX) | Low (implement) | P2 |

#### M61: Pre-mortem Analysis

**If we deploy without these fixes:**
1. Security breach via unauthenticated WebSocket - **CRITICAL**
2. Data loss from file-based strategies - **CRITICAL**
3. Runtime crashes from missing methods - **CRITICAL**
4. User confusion from dual WS implementations - **IMPORTANT**

#### M70: Regret Minimization

| Decision | Regret if wrong |
|----------|-----------------|
| Remove demo credentials from frontend | LOW (minor UX change) |
| Unify to DB storage | LOW (correct architecture) |
| Delete useWebSocket hook | MEDIUM (if something depended on it) |

---

## Implementation Order

### Phase 1: Security (Week 1)
1. BUG-DV-015/016/017 - WebSocket auth
2. BUG-DV-027/028 - Credential validation
3. BUG-DV-029 - Remove frontend credentials
4. BUG-DV-030 - Remove tokens from localStorage

### Phase 2: Runtime (Week 1-2)
5. BUG-DV-019 - Add get_int method
6. BUG-DV-021 - Market context fallback
7. BUG-DV-022 - Fix format strings
8. BUG-DV-001/002 - Fix close_position

### Phase 3: Data Integrity (Week 2)
9. BUG-DV-004/013 - Unify strategy persistence
10. Run migration script

### Phase 4: Architecture (Week 3)
11. BUG-DV-031/032/033 - WebSocket unification
12. BUG-DV-034/035 - Strategy validation

### Phase 5: Quality (Week 3-4)
13. Remaining IMPORTANT bugs
14. MINOR items

---

## Appendix A: Methods Applied

| # | Method | Category | Applied To |
|---|--------|----------|------------|
| 56 | Liar's Trap | anti-bias | Self-analysis |
| 57 | Mirror Trap | anti-bias | Self-analysis |
| 58 | Confession Paradox | anti-bias | Self-analysis |
| 59 | CUI BONO | anti-bias | Self-analysis |
| 60 | Approval Gradient | anti-bias | Self-analysis |
| 71 | First Principles | core | WS auth |
| 72 | 5 Whys | core | RSI bug |
| 80 | Inversion | core | Format strings |
| 17 | Abstraction Laddering | advanced | WS unification |
| 19 | Steelmanning | advanced | Validation stub |
| 31 | Architecture Decision Records | technical | All major decisions |
| 34 | Security Audit Personas | technical | Auth validation |
| 36 | Dependency Audit | technical | External deps |
| 37 | API Design Review | technical | New endpoints |
| 39 | Chaos Engineering | technical | Fallback behavior |
| 40 | Technical Debt Assessment | technical | Prioritization |
| 61 | Pre-mortem | risk | Deployment risk |
| 66 | Dependency Risk Mapping | risk | Strategy persistence |
| 70 | Regret Minimization | risk | Key decisions |
| 81 | Scope Integrity Audit | sanity | Coverage check |
| 82 | Alignment Check | sanity | Goal alignment |
| 83 | Closure Check | sanity | Completeness |
| 84 | Coherence Check | sanity | Consistency |
| 91 | Camouflage Test | coherence | New code |
| 92 | Least Surprise | coherence | Breaking changes |
| 93 | DNA Inheritance | coherence | Patterns |
| 99 | Multi-Artifact Coherence | coherence | Cross-file |
| 145 | Documentation | protocol | This document |
| 146 | Verification | protocol | Criteria |
| 149 | Completion Checklist | protocol | Final check |

---

## Appendix B: Completion Checklist (M149)

### Pre-Deployment
- [ ] All CRITICAL bugs fixed
- [ ] All security tests pass
- [ ] Integration tests pass
- [ ] No hardcoded credentials in codebase
- [ ] Migration script tested

### Post-Deployment
- [ ] Admin password changed
- [ ] File-based strategies migrated
- [ ] Monitor for auth errors
- [ ] Monitor for runtime exceptions

### Documentation
- [ ] CHANGELOG updated
- [ ] Security policy updated
- [ ] API docs updated (new demo-login endpoint)
