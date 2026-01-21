# Verification Todos for src/api

This document tracks findings from the `deep-verify` workflow process.

## `src/api/auth_handler.py`

**Verdict: REJECT**

| ID | Severity | Description | Location | Recommendation |
|----|----------|-------------|----------|----------------|
| F1 | CRITICAL | **Incorrect use of cryptographic primitive:** `hmac.compare_digest` is used for plaintext password comparison, which is incorrect. The entire plaintext fallback is a vulnerability. | line 772 | Remove the plaintext password verification path. Use `secrets.compare_digest` if a constant-time comparison is ever needed for secrets. |
| F2 | IMPORTANT| **Blocking async event loop:** Synchronous `_verify_password` (CPU-bound) is called directly from an async function, blocking the server. | line 1007 | Run the blocking `bcrypt` call in a `ThreadPoolExecutor` using `loop.run_in_executor`. |
| F3 | IMPORTANT| **Lack of session persistence:** "Production-ready" component uses in-memory dictionaries for all session data, which are lost on restart. | line 220 | Replace in-memory storage with a persistent backend like Redis or a database. Document the single-process limitation if persistence is not added. |
| F4 | IMPORTANT| **Potential race condition:** Background cleanup task iterates over a shared dictionary without a lock, which can cause a `RuntimeError`. | line 851 | Use a lock when modifying session dictionaries or iterate over a copy of the keys (e.g., `list(self.active_sessions)`). |
| F5 | MINOR | **Redundant logic in config check:** The check for environment variables can produce duplicate error messages. | lines 963-967 | Refactor the credential validation logic to be clearer and avoid redundant error messages. |

---

## `src/api/backtest_routes.py`

**Verdict: UNCERTAIN**

| ID | Severity | Description | Location | Recommendation |
|----|----------|-------------|----------|----------------|
| F1 | IMPORTANT | **Incompatible with Multi-Process Deployment:** Global in-memory dictionary (`_running_backtests`) makes the service stateful and incompatible with multiple worker processes. | line 33 | Use a distributed state store like Redis or document the single-process limitation. |
| F2 | IMPORTANT | **Database State Not Updated on Task Failure:** The background task catches exceptions but doesn't update the session's status in the database to "failed", leaving it as "started". | lines 112-117 | In the `except` block of `_run_backtest_task`, update the session status in the DB to "failed". |
| F3 | IMPORTANT | **Orphan Backtests Created on Database Failure:** The `/start` endpoint starts a backtest task even if writing the initial session record to the database fails, creating an untrackable task. | lines 480-486 | Do not start the backtest task if the DB write fails. Return an error to the client. |
| F4 | MINOR | **Task Cancellation Not Awaited:** Task is cancelled via `task.cancel()` but not `await`ed, which can delay cleanup. | line 629 | After calling `task.cancel()`, `await` the task in a `try...except asyncio.CancelledError` block. |

---

## `src/api/broadcast_provider.py`

**Verdict: REJECT**

| ID | Severity | Description | Location | Recommendation |
|----|----------|-------------|----------|----------------|
| F1 | CRITICAL | **Deadlock in `get_stats` method:** The method acquires a non-re-entrant `asyncio.Lock` and then calls other methods that attempt to acquire the same lock, causing a deadlock. | lines 627-639 | Refactor `get_stats` to access statistic values directly within the single lock acquisition block. |
| F2 | IMPORTANT | **Improper Exception Handling Prevents Shutdown:** The main processing loop's `except Exception` block catches `asyncio.CancelledError`, preventing the task from terminating on cancellation. | line 614 | Explicitly catch and re-raise `asyncio.CancelledError` before the general `except Exception` block. |
| F3 | MINOR | **Unused Lock Initialized:** A lock named `_queue_lock` is initialized but never used. | line 85 | Remove the unused `self._queue_lock` attribute. |

---

## `src/api/chart_routes.py`

**Verdict: UNCERTAIN**

| ID | Severity | Description | Location | Recommendation |
|----|----------|-------------|----------|----------------|
| F1 | IMPORTANT | **Potential SQL Injection Vector:** The `sample_interval` is formatted directly into the SQL query string, a dangerous practice even if the input is currently controlled. | lines 105-115 | Use an `if/elif` structure to build the query with hardcoded, validated `SAMPLE BY` clauses. |
| F2 | IMPORTANT | **Incorrect Handling of Null Data:** Missing OHLCV data is converted to `0.0` instead of `null`, which will cause misleading chart visualizations. | lines 122-127 | Return `None` for missing database values so they are serialized as `null` in the JSON response. |
| F3 | MINOR | **Fragile Dependency Injection Pattern:** Relies on global variables and a manual initializer function, which is less robust than using FastAPI's `Depends` system. | lines 44-48 | Refactor to use FastAPI's dependency injection system for providing the `QuestDBProvider`. |

---

## `src/api/command_handler.py`

**Verdict: ACCEPT**

| ID | Severity | Description | Location | Recommendation |
|----|----------|-------------|----------|----------------|
| F1 | MINOR | **Inefficient Polling Pattern:** The `_execute_live_trading` method uses an `await asyncio.sleep(1)` loop instead of a more efficient event-based wait. | line 621 | (Optional) Refactor to `await` an `asyncio.Event` that is set by the stop handler. |
| F2 | MINOR | **Code Duplication:** The `_stop_execution_session` and `_stop_live_trading_session` methods contain nearly identical logic. | lines 646, 661 | (Recommended) Create a single private `_terminate_session` method to be called by both stop handlers. |
| F3 | MINOR | **Fragile Manual State Counting:** The `active_session_count` is manually incremented/decremented, which is more error-prone than deriving it from `len(self.active_sessions)`. | line 641 | (Recommended) Remove the manual counter and calculate the value from the session dictionary when needed. |
| F4 | MINOR | **Inconsistent Deprecation:** A deprecated command is still listed in the `supported_commands` dictionary. | lines 112, 410 | (Optional) Remove the command from the dictionary for a cleaner design. |

---

## `src/api/connection_manager.py`

**Verdict: REJECT**

| ID | Severity | Description | Location | Recommendation |
|----|----------|-------------|----------|----------------|
| F1 | CRITICAL | **Deadlock in Cleanup Loop:** The `_perform_cleanup` method acquires a lock and then calls `remove_connection`, which tries to acquire the same lock, causing a deadlock. | lines 627, 639 | Create private, non-locking helper methods for core logic that can be safely called from methods that have already acquired the lock. |
| F2 | CRITICAL | **Deadlock in Disconnect Logic:** A second deadlock path exists: `remove_connection` -> `unsubscribe_client` -> `get_connection`, all of which try to acquire the same lock. | lines 355, 496, 423 | Use the same private, non-locking helper method pattern as for F1. |
| F3 | IMPORTANT | **Misleading Documentation (No Weak References):** Docstring claims use of weak references for memory safety, but the code uses a standard dictionary. | lines 166, 205 | Remove the misleading documentation or implement `weakref.WeakValueDictionary`. |
| F4 | IMPORTANT | **Unsafe Public Method:** The `get_connection_stats_snapshot` method is documented as not thread-safe and accesses shared state without a lock, risking crashes. | lines 664-693 | Refactor this to be an `async` method that properly acquires the lock before accessing data. |

---

## `src/api/dashboard_routes.py`

**Verdict: UNCERTAIN**

| ID | Severity | Description | Location | Recommendation |
|----|----------|-------------|----------|----------------|
| F1 | IMPORTANT | **Silent Data Truncation:** The `/summary` endpoint silently limits the watchlist to 20 symbols due to a hardcoded `LIMIT 20` in its helper function. | line 427 | Remove the hardcoded `LIMIT 20`. If a limit is needed, it should be documented and consistent. |
| F2 | IMPORTANT | **Inconsistent API Schema:** The `/summary` and `/watchlist` endpoints return different key names for the same data (`price` vs `latest_price`), which will break UI components. | lines 434, 250 | Standardize on a single key name for the price field across both endpoints. |
| F3 | MINOR | **Potential for Client-Induced Performance Issues:** The `/watchlist` endpoint does not limit the number of symbols that can be requested in a single call. | line 214 | Add validation to limit the number of symbols per request (e.g., max 50). |
| F4 | MINOR | **Overly Broad Exception Handling:** Helper functions silently return default/empty values on any exception, which can hide underlying data source problems from users. | line 451 | Consider propagating critical errors or returning a specific error status for the failed data component. |

---
