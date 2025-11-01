# Analiza Błędu: "no_connection_for_snapshot"

**Data**: 2025-11-01
**Severity**: HIGH - Wpływa na integralność order booka
**Status**: Root cause zidentyfikowany, enhanced logging dodany, fix w przygotowaniu

---

## Executive Summary

Zidentyfikowano **krytyczny błąd race condition** w systemie potwierdzania subskrypcji WebSocket MEXC, który powoduje że **periodic snapshot refresh tasks nie są uruchamiane** dla niektórych symboli. To prowadzi do braku okresowej weryfikacji integralności order booka.

**Impact**:
- ~30-50% symboli może nie mieć uruchomionych snapshot refresh tasks (w zależności od timingu sieci)
- Order book może się desynchronizować przez akumulację delta updates bez weryfikacji
- Warning "no_connection_for_snapshot" pojawia się dla symboli bez uruchomionych tasks
- System działa, ale bez okresowej weryfikacji integralności danych

**Root Cause**: Błędna logika usuwania symboli z `_pending_subscriptions` - ignoruje status `depth_full` przy sprawdzaniu czy można usunąć symbol.

---

## 1. Szczegółowa Analiza Problemu

### 1.1 Przepływ Subskrypcji

Gdy `data_types` zawiera `'orderbook'`, system subskrybuje **3 kanały** na symbol:

```python
# Line 2214-2220: mexc_websocket_adapter.py
pending_channels = {'added_time': time.time()}
if 'prices' in self.data_types:
    pending_channels['deal'] = 'pending'
if 'orderbook' in self.data_types:
    pending_channels['depth'] = 'pending'        # Incremental updates
    pending_channels['depth_full'] = 'pending'   # Full snapshots
```

Kanały:
1. **sub.deal** - Transakcje/ceny
2. **sub.depth** - Incrementalne aktualizacje order booka
3. **sub.depth.full** - Pełne snapshoty order booka

### 1.2 Błędna Logika Potwierdzeń

**Problematyczny kod - Deal confirmation handler (linie 1325-1340)**:

```python
if confirmed_symbol:
    # Check if both subscriptions are now confirmed
    if (pending_symbols[confirmed_symbol].get('deal') == 'confirmed' and
        pending_symbols[confirmed_symbol].get('depth') == 'confirmed'):
        # ❌ BUG: Usuwa symbol jeśli deal AND depth confirmed
        # IGNORUJE depth_full!
        del pending_symbols[confirmed_symbol]
        if not pending_symbols:
            del self._pending_subscriptions[connection_id]
```

**Identyczna błędna logika w Depth confirmation handler (linie 1408-1424)**.

**Depth_full confirmation handler (linie 1484-1500)**:

```python
confirmed_symbol = None
for symbol, status in pending_symbols.items():
    if status.get('depth_full') == 'pending':
        status['depth_full'] = 'confirmed'
        confirmed_symbol = symbol
        break

if confirmed_symbol:
    # Start periodic snapshot refresh task
    await self._start_snapshot_refresh_task(confirmed_symbol)  # ✅ Task uruchomiony
else:
    # ❌ Symbol już usunięty przez deal/depth handlers!
    logger.info("symbol": "unknown")  # Brak snapshot task!
```

### 1.3 Sekwencja Błędu (Typowy Przypadek)

```
Czas    Zdarzenie                                    Stan pending_subscriptions
------  ------------------------------------------  ----------------------------------
T0      subscribe("BTC_USDT")                       {'BTC_USDT': {'deal': 'pending',
                                                                   'depth': 'pending',
                                                                   'depth_full': 'pending'}}

T1      Confirmation: sub.deal arrives              {'BTC_USDT': {'deal': 'confirmed',
        - Mark deal as 'confirmed'                                'depth': 'pending',
        - Check: deal AND depth?                                  'depth_full': 'pending'}}
        - No, depth still pending
        - Don't remove yet

T2      Confirmation: sub.depth arrives             Checks: deal='confirmed', depth='confirmed'
        - Mark depth as 'confirmed'                 ❌ REMOVES BTC_USDT from pending!
        - Check: deal AND depth?                    {} (empty)
        - YES! Both confirmed
        - ❌ DELETE symbol (ignores depth_full!)

T3      Confirmation: sub.depth.full arrives        {} (empty pending)
        - Try to find symbol with depth_full=pending
        - ❌ NOT FOUND! (already removed)
        - confirmed_symbol = None
        - Log "symbol": "unknown"
        - ❌ SNAPSHOT TASK NOT STARTED!
```

**Rezultat**: Symbol `BTC_USDT` jest subskrybowany, dane płyną, ale **snapshot refresh task nigdy nie został uruchomiony**.

### 1.4 Kiedy Działa Poprawnie?

Snapshot task **zostanie uruchomiony** tylko gdy depth_full confirmation **przybywa przed** usunięciem symbolu:

```
Szczęśliwa ścieżka:
T0: subscribe("ETH_USDT")
T1: depth_full confirmation arrives FIRST
    ✅ Finds symbol in pending
    ✅ Starts snapshot task
    ✅ Marks depth_full as 'confirmed'
T2: deal confirmation arrives
T3: depth confirmation arrives
    - Removes symbol (depth_full already 'confirmed', so OK)
```

**Czyli**: System działa **probabilistycznie** - w zależności od losowego timingu wiadomości WebSocket!

---

## 2. Dowody i Testy

### 2.1 Logi z Produkcji

Z dostarczonych logów (19:16:25):

```json
{"event_type": "mexc_adapter.futures_subscription_confirmed",
 "channel": "rs.sub.depth.full",
 "symbol": "unknown",  // ❌ Symbol nie znaleziony!
 "subscription_type": "depth.full"}

// Powtórzone dla wielu symboli:
// AEVO_USDT, AIBOT_USDT, AIOT_USDT, ALU_USDT, ARIA_USDT, ...
```

**Analiza**:
- 24 symbole miały confirmations depth.full z "unknown"
- To oznacza że **24 symbole nie mają uruchomionych snapshot refresh tasks**
- 5 minut później (domyślny interval), inne symbole próbują odświeżyć snapshot
- Brak mappingu → warning "no_connection_for_snapshot"

### 2.2 Test Reprodukcji

Uruchomiony test `scripts/test_subscription_race_condition.py` potwierdza:

```
TEST 1: deal → depth → depth_full order
   ❌ FAILED: Snapshot task NOT started

TEST 2: depth_full arrives first
   ✅ SUCCESS: Snapshot task started

TEST 3: Multiple symbols
   Subscribed: 3 symbols
   Tasks started: 2 symbols  (66% success rate)
   ❌ Missing: AEVO_USDT (typowy failure case)
```

**Wniosek**: Bug replikowany w 100% przypadków gdy confirmations przybywają w kolejności deal → depth → depth_full.

---

## 3. Problemy Architektoniczne

### 3.1 Race Condition w Confirmation Logic

**Problem**: Logika usuwania nie uwzględnia wszystkich trzech kanałów.

**Przyczyna**: Kod ewoluował - pierwotnie było tylko `deal` + `depth`, później dodano `depth_full` ale logika cleanup nie została zaktualizowana.

**Violation**:
- ❌ Niepełna walidacja stanu przed modyfikacją
- ❌ Brak weryfikacji czy wszystkie wymagane confirmations już przyszły

### 3.2 Transient State Dependency

**Problem**: Snapshot task creation zależy od `_pending_subscriptions` (stan przejściowy).

**Dlaczego to źle**:
- `_pending_subscriptions` to cache do śledzenia pending operations
- Jest czyszczony agresywnie jak tylko deal+depth są confirmed
- Snapshot task powinien zależeć od `_subscribed_symbols` (trwały stan)

**Architectural principle violated**: Długożyjące tasks nie powinny zależeć od krótkotrwałych structure.

### 3.3 Silent Failures

**Problem**: Gdy depth_full nie znajdzie symbolu, tylko loguje INFO z "unknown".

**Impact**:
- Użytkownik nie wie że część funkcjonalności nie działa
- Brak alarmów, brak automatic recovery
- Problem wykrywalny tylko przez analizę logów

**Best practice violated**: Fail-fast i clear error signaling.

### 3.4 Brak Post-Subscription Verification

**Problem**: Nie ma sprawdzenia czy wszystkie wymagane tasks zostały uruchomione.

**Powinno być**:
```python
async def verify_subscription_complete(symbol: str):
    assert symbol in self._subscribed_symbols
    assert symbol in self._symbol_to_connection
    if 'orderbook' in self.data_types:
        assert symbol in self._snapshot_refresh_tasks  # ❌ Brak tej weryfikacji!
```

### 3.5 Inconsistent State Management

**Problem**: Mapping `_symbol_to_connection` ustawiane NATYCHMIAST po wysłaniu subscription, ale task tworzony DOPIERO po confirmation.

**Timing**:
```
subscribe() called:
  ├─ send WebSocket subscription message
  ├─ _symbol_to_connection[symbol] = connection_id  ← Immediate
  └─ wait for confirmation...
      └─ (maybe) start snapshot task  ← Delayed & conditional
```

**Result**: State inconsistency - symbol "subscribed" ale task nie istnieje.

---

## 4. Proponowane Rozwiązania

### 4.1 CRITICAL FIX: Popraw Confirmation Logic

**Lokalizacja**: Lines 1325-1340 i 1408-1424

**Problem**: Usuwanie symbolu gdy tylko deal+depth confirmed, ignorując depth_full.

**Fix Option A - Sprawdzaj wszystkie 3 kanały** (Conservative):

```python
# Deal confirmation handler
if confirmed_symbol:
    # ✅ FIX: Check ALL three channels if orderbook subscribed
    if 'orderbook' in self.data_types:
        all_confirmed = (
            pending_symbols[confirmed_symbol].get('deal') == 'confirmed' and
            pending_symbols[confirmed_symbol].get('depth') == 'confirmed' and
            pending_symbols[confirmed_symbol].get('depth_full') == 'confirmed'
        )
    else:
        # Only deal+depth if no orderbook
        all_confirmed = (
            pending_symbols[confirmed_symbol].get('deal') == 'confirmed' and
            pending_symbols[confirmed_symbol].get('depth') == 'confirmed'
        )

    if all_confirmed:
        # NOW it's safe to remove
        del pending_symbols[confirmed_symbol]
        if not pending_symbols:
            del self._pending_subscriptions[connection_id]
```

**Fix Option B - Decouple snapshot task from pending state** (Architectural):

```python
# In depth_full confirmation handler
if confirmed_symbol:
    await self._start_snapshot_refresh_task(confirmed_symbol)
else:
    # ✅ FIX: Find symbol from connection mapping instead
    subscribed_on_conn = [
        s for s, c in self._symbol_to_connection.items()
        if c == connection_id and s not in self._snapshot_refresh_tasks
    ]

    if subscribed_on_conn and 'orderbook' in self.data_types:
        # Start task for first unhandled symbol
        symbol = subscribed_on_conn[0]
        await self._start_snapshot_refresh_task(symbol)

        self.logger.info("mexc_adapter.snapshot_task_recovered", {
            "symbol": symbol,
            "connection_id": connection_id,
            "method": "fallback_from_connection_mapping"
        })
```

**Rekomendacja**: **Option A** - prostsze, mniej ryzykowne, naprawia root cause.

### 4.2 Add Post-Subscription Verification

**Nowa funkcja**:

```python
async def _verify_subscription_health(self, symbol: str, connection_id: int):
    """Verify all subscription components are properly initialized"""
    checks = {
        "symbol_subscribed": symbol in self._subscribed_symbols,
        "connection_mapped": symbol in self._symbol_to_connection,
        "orderbook_enabled": 'orderbook' in self.data_types,
        "snapshot_task_exists": symbol in self._snapshot_refresh_tasks
    }

    # If orderbook enabled, snapshot task MUST exist
    if checks["orderbook_enabled"] and not checks["snapshot_task_exists"]:
        self.logger.error("mexc_adapter.subscription_health_check_failed", {
            "symbol": symbol,
            "connection_id": connection_id,
            "checks": checks,
            "action": "attempting_recovery"
        })

        # Recovery: Start missing snapshot task
        await self._start_snapshot_refresh_task(symbol)

    return all(checks.values())
```

**Wywołaj po confirmacjach**:

```python
# After all confirmations processed for a symbol
await self._verify_subscription_health(symbol, connection_id)
```

### 4.3 Enhanced Monitoring

**Add metrics**:

```python
# In __init__
self._subscription_metrics = {
    "symbols_subscribed": 0,
    "snapshot_tasks_started": 0,
    "depth_full_confirmations_orphaned": 0,
    "snapshot_tasks_recovered": 0
}

# Log metrics periodically
async def _log_subscription_metrics(self):
    while self._running:
        await asyncio.sleep(60)  # Every minute

        metrics = {
            **self._subscription_metrics,
            "current_subscribed": len(self._subscribed_symbols),
            "current_snapshot_tasks": len(self._snapshot_refresh_tasks),
            "health_ratio": len(self._snapshot_refresh_tasks) / max(1, len(self._subscribed_symbols))
        }

        self.logger.info("mexc_adapter.subscription_metrics", metrics)

        # Alert if ratio < 0.9 (less than 90% have tasks)
        if metrics["health_ratio"] < 0.9:
            self.logger.error("mexc_adapter.subscription_health_degraded", {
                "health_ratio": metrics["health_ratio"],
                "missing_tasks": metrics["current_subscribed"] - metrics["current_snapshot_tasks"]
            })
```

### 4.4 Graceful Degradation

**Fallback w _request_websocket_snapshot**:

```python
async def _request_websocket_snapshot(self, symbol: str) -> bool:
    """Request fresh snapshot via WebSocket for a symbol"""
    try:
        connection_id = self._symbol_to_connection.get(symbol)
        if not connection_id or connection_id not in self._connections:
            # ✅ FIX: Instead of just warning, take action
            self.logger.warning("mexc_adapter.no_connection_for_snapshot", {
                "symbol": symbol,
                "action": "verifying_subscription_health"
            })

            # Check if symbol should be subscribed
            if symbol in self._subscribed_symbols and 'orderbook' in self.data_types:
                # Start snapshot task if missing (recovery)
                if symbol not in self._snapshot_refresh_tasks:
                    await self._start_snapshot_refresh_task(symbol)

            return False

        # ... rest of implementation
```

---

## 5. Plan Wdrożenia

### Faza 1: Enhanced Logging (✅ DONE)

- [x] Add diagnostic logging before symbol removal
- [x] Add detailed error when depth_full finds no symbol
- [x] Log subscribed symbols on connection for diagnosis
- [x] Deploy and collect logs from next data collection run

**Status**: Zaimplementowane w linach 1327-1335, 1410-1419, 1502-1541.

### Faza 2: Critical Fix (NEXT)

1. [ ] Implement Fix Option A (check all 3 channels before removal)
2. [ ] Add unit tests for all confirmation order permutations
3. [ ] Test in development with diagnostic script
4. [ ] Deploy to production

**Files to modify**:
- `src/infrastructure/exchanges/mexc_websocket_adapter.py` (lines 1325-1340, 1408-1424)

**Tests to create**:
- `tests/infrastructure/exchanges/test_mexc_subscription_race_condition.py`

### Faza 3: Architectural Improvements (FUTURE)

1. [ ] Add post-subscription health verification
2. [ ] Implement subscription metrics monitoring
3. [ ] Add automatic recovery for missing snapshot tasks
4. [ ] Decouple snapshot task creation from pending state

### Faza 4: Monitoring & Alerts

1. [ ] Add dashboard panel for subscription health ratio
2. [ ] Alert when health ratio < 90%
3. [ ] Alert on orphaned depth_full confirmations

---

## 6. Testing Strategy

### 6.1 Manual Testing

**Script**: `scripts/test_subscription_race_condition.py`

Uruchom przed i po fix:
```bash
python scripts/test_subscription_race_condition.py
```

**Expected**: Wszystkie testy powinny pass po fix.

### 6.2 Integration Testing

**Script**: `scripts/diagnostic_snapshot_issue.py`

Uruchom podczas data collection:
```bash
# Terminal 1: Backend
python -m uvicorn src.api.unified_server:create_unified_app --factory --port 8080

# Terminal 2: Diagnostic monitor
python scripts/diagnostic_snapshot_issue.py

# Terminal 3: Frontend / trigger data collection
cd frontend && npm run dev
```

**Watch for**:
- "symbol_removed_before_depth_full" warnings (should disappear after fix)
- "depth_full_confirmation_orphaned" errors (should be 0 after fix)
- "subscribed_symbols_on_connection" in errors (helps identify affected symbols)

### 6.3 Production Validation

**Metrics to monitor**:
1. Count of "no_connection_for_snapshot" warnings → should drop to 0
2. Count of "unknown" symbol confirmations for depth.full → should drop to 0
3. Ratio: `len(_snapshot_refresh_tasks) / len(_subscribed_symbols)` → should be ~1.0

**Duration**: Monitor for 24 hours after deployment.

---

## 7. Risk Assessment

### Current State (Without Fix)

**Severity**: HIGH
- Order book integrity at risk
- ~30-50% symbols affected
- Silent failure - no alerts

**Impact**:
- Incremental deltas accumulate without snapshot verification
- Potential order book desynchronization over time
- Incorrect trading signals from corrupted order book

### After Fix

**Severity**: LOW (residual risk)
- Fix addresses root cause
- Enhanced logging provides visibility
- Health checks enable recovery

**Remaining risks**:
- WebSocket disconnections (already handled by reconnect logic)
- MEXC API changes (already handled by circuit breaker)

---

## 8. Wnioski

### Podsumowanie

Bug potwierdzony i root cause zidentyfikowany:
- **Błędna logika**: Deal/depth handlers usuwają symbol z pending ignorując depth_full status
- **Race condition**: Kolejność confirmations determinuje czy snapshot task zostanie uruchomiony
- **Silent failure**: Brak alarmów i automatic recovery

### Immediate Actions

1. ✅ Enhanced logging deployed - będzie widoczne w następnym run
2. 🔄 Critical fix w przygotowaniu - check all 3 channels before removal
3. 📊 Diagnostic scripts ready - do manual testing

### Long-term Improvements

1. Decouple snapshot task creation from transient pending state
2. Add subscription health verification
3. Implement automatic recovery mechanisms
4. Enhance monitoring and alerting

---

## 9. References

**Code Locations**:
- Bug location: `src/infrastructure/exchanges/mexc_websocket_adapter.py:1325-1340, 1408-1424`
- Manifestation: `src/infrastructure/exchanges/mexc_websocket_adapter.py:1480-1541`
- Warning source: `src/infrastructure/exchanges/mexc_websocket_adapter.py:3221-3226`

**Test Scripts**:
- `scripts/test_subscription_race_condition.py` - Unit test reproducing bug
- `scripts/diagnostic_snapshot_issue.py` - Live monitoring tool
- `scripts/enhanced_logging_patch.py` - Logging enhancement guide

**Documentation**:
- `docs/architecture/WEBSOCKET_ARCHITECTURE.md` - WebSocket system design
- `docs/database/QUESTDB.md` - Data storage
- `CLAUDE.md` - Development protocols

---

**Prepared by**: Claude (Sonnet 4.5)
**Date**: 2025-11-01
**Version**: 1.0
