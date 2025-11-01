"""
Analysis: Memory Leak in Fix Implementation
============================================

## Problem Discovered

After implementing fix for snapshot task race condition, new error appeared:
"mexc_adapter.depth_full_confirmation_no_pending"

## Root Cause

The fix successfully prevented premature symbol removal in deal/depth handlers,
BUT forgot to add cleanup logic to depth_full handler.

### Current Behavior (BROKEN)

```python
# depth_full handler (lines 1509-1519)
if confirmed_symbol:
    status['depth_full'] = 'confirmed'  # Mark as confirmed
    await self._start_snapshot_refresh_task(confirmed_symbol)  # Start task
    # ❌ NO CLEANUP! Symbol stays in pending forever!
```

### Flow with Memory Leak

```
T0: subscribe(symbol) → added to pending {'deal': 'pending', 'depth': 'pending', 'depth_full': 'pending'}

T1: deal confirmation → marked as 'confirmed', symbol STAYS (fix working)

T2: depth confirmation → marked as 'confirmed', symbol STAYS (fix working)

T3: depth_full confirmation → marked as 'confirmed', starts snapshot task
    ❌ Symbol STAYS in pending_subscriptions!
    All 3 channels confirmed but symbol NOT removed!

T4: Symbol sits in pending subscriptions forever
    - Memory leak accumulates for every symbol
    - Cleanup task will eventually remove (TTL > 60s)

T5: If depth_full confirmation comes again (duplicate/late):
    - pending_subscriptions[connection_id] already cleaned up
    - ERROR: "No pending subscriptions found for connection"
    - Snapshot task NOT started for duplicate confirmation
```

### Evidence from Logs

```json
{
  "event_type": "mexc_adapter.depth_full_confirmation_no_pending",
  "problem": "No pending subscriptions found for connection",
  "subscribed_symbols_on_connection": [
    "DUPE_USDT", "PLAY_USDT", "RWA_USDT", ... (13 symbols)
  ],
  "impact": "Snapshot refresh task NOT started"
}
```

**Analysis**:
- 13 symbols on connection_id=1
- All were subscribed successfully
- pending_subscriptions[1] is EMPTY when depth_full confirmation arrives
- This happens because:
  1. Symbols stayed in pending after depth_full confirmation (no cleanup)
  2. Cleanup task removed them after TTL (60s)
  3. Late/duplicate depth_full confirmations found empty pending

### Cleanup Task Behavior

```python
# Lines 2715-2758: _cleanup_pending_subscriptions
async def _cleanup_pending_subscriptions(self) -> None:
    while self._running:
        await asyncio.sleep(300)  # Every 5 minutes

        for conn_id, symbols in list(self._pending_subscriptions.items()):
            for symbol, status in list(symbols.items()):
                added_time = status.get('added_time', current_time)
                if current_time - added_time > 60:  # ❌ 60 second TTL
                    del self._pending_subscriptions[conn_id][symbol]
                    if not self._pending_subscriptions[conn_id]:
                        del self._pending_subscriptions[conn_id]
```

Symbols left in pending after confirmation will be cleaned up after 60s.

## Impact Assessment

### Immediate Impact
1. **Memory leak**: Every subscribed symbol stays in pending_subscriptions forever
2. **Cleanup task load**: Has to remove ALL symbols after TTL
3. **Duplicate confirmations fail**: If depth_full comes again → ERROR
4. **Inconsistent state**: pending_subscriptions contains fully confirmed symbols

### Production Impact
- 13 symbols affected in this case
- Over time, pending_subscriptions grows unbounded (until cleanup)
- If depth_full confirmations are slow/duplicated → snapshot tasks NOT started

## Solution Required

Add cleanup logic to depth_full handler:

```python
# After starting snapshot task
await self._start_snapshot_refresh_task(confirmed_symbol)

# ✅ ADD: Check if all 3 channels confirmed, remove from pending
if (pending_symbols[confirmed_symbol].get('deal') == 'confirmed' and
    pending_symbols[confirmed_symbol].get('depth') == 'confirmed' and
    pending_symbols[confirmed_symbol].get('depth_full') == 'confirmed'):

    self.logger.debug("mexc_adapter.symbol_confirmed_removing_from_pending", {
        "symbol": confirmed_symbol,
        "connection_id": connection_id,
        "has_orderbook": 'orderbook' in self.data_types,
        "all_channels_confirmed": True,
        "handler": "depth_full"
    })

    del pending_symbols[confirmed_symbol]
    if not pending_symbols:
        del self._pending_subscriptions[connection_id]
```

This ensures:
1. Symbol removed as soon as ALL 3 channels confirmed
2. No memory leak
3. Consistent with deal/depth handlers
4. Duplicate confirmations handled gracefully (symbol already gone)

## Test Cases to Add

1. **Normal flow**: All 3 confirmations arrive → symbol removed after last one
2. **Duplicate depth_full**: Second depth_full arrives → no error, gracefully handled
3. **Late depth_full**: depth_full arrives >60s → should still work if not cleaned up
4. **Memory leak verification**: pending_subscriptions should be empty after all confirmations

## Architectural Issue Identified

**Problem**: Inconsistent cleanup logic across confirmation handlers
- Deal handler: checks all 3 channels, removes if all confirmed
- Depth handler: checks all 3 channels, removes if all confirmed
- Depth_full handler: ONLY starts task, NO cleanup ❌

**Should be**: All 3 handlers use IDENTICAL cleanup logic:
```python
# Generic cleanup logic (DRY principle)
async def _remove_from_pending_if_all_confirmed(
    self, connection_id: int, symbol: str, pending_symbols: Dict
):
    if 'orderbook' in self.data_types:
        all_confirmed = (
            pending_symbols[symbol].get('deal') == 'confirmed' and
            pending_symbols[symbol].get('depth') == 'confirmed' and
            pending_symbols[symbol].get('depth_full') == 'confirmed'
        )
    else:
        all_confirmed = (
            pending_symbols[symbol].get('deal') == 'confirmed' and
            pending_symbols[symbol].get('depth') == 'confirmed'
        )

    if all_confirmed:
        del pending_symbols[symbol]
        if not pending_symbols:
            del self._pending_subscriptions[connection_id]
```

This would be called by all 3 handlers, ensuring consistent behavior.

## Priority: CRITICAL

This must be fixed immediately as it:
1. Causes memory leak
2. Causes snapshot tasks to not start for duplicate/late confirmations
3. Violates architectural consistency
4. Contradicts the original fix intent
"""