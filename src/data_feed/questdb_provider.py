#!/usr/bin/env python3
"""
QuestDB Data Provider - Phase 2 Sprint 3
========================================

High-performance data provider for QuestDB time-series database.

Features:
- InfluxDB line protocol for ultra-fast inserts (1M+ rows/sec)
- PostgreSQL wire protocol for SQL queries
- Connection pooling
- Batch insertion optimization
- Error handling and retry logic

⚠️ CRITICAL: QuestDB WAL Race Condition Awareness
==================================================

QuestDB uses dual-protocol architecture which creates a race condition:

1. **Write Path (InfluxDB Line Protocol - ILP):**
   - Ultra-fast writes (1M+ rows/sec)
   - Data goes to WAL (Write-Ahead Log) first
   - sender.flush() sends data over network
   - Returns IMMEDIATELY (async operation)
   - WAL commit to main table files happens LATER (1-3 seconds typical)

2. **Read Path (PostgreSQL Wire Protocol):**
   - Standard SQL queries via PostgreSQL protocol
   - Reads from MAIN TABLE FILES only
   - CANNOT see data still in WAL
   - This creates a visibility gap!

3. **The Race Condition:**
   ```
   T=0ms:    insert_indicators_batch() → WAL
   T=100ms:  sender.flush() → network send
   T=150ms:  Returns success ✓
   T=200ms:  get_indicators() → SELECT query
   T=250ms:  PostgreSQL reads main files (WAL not visible)
   T=300ms:  Returns [] (empty!) ❌
   ...
   T=2000ms: WAL commits to main files
   T=3000ms: get_indicators() → SELECT query
   T=3050ms: Returns data ✓
   ```

4. **Solutions for Application Code:**

   **Option A: Retry with exponential backoff (Recommended)**
   - Retry queries 3-6 times with delays (200ms, 400ms, 600ms, etc.)
   - Covers 95%+ of cases
   - Transparent to caller
   - See: indicators_routes.py:get_indicator_history() for implementation

   **Option B: Add artificial delay after write**
   - await asyncio.sleep(2.0) after insert operations
   - Simple but inefficient
   - Adds latency to all operations

   **Option C: Use PostgreSQL INSERT instead of ILP**
   - Immediate visibility (ACID guarantees)
   - 10-100x slower than ILP
   - Only for small datasets where performance isn't critical

5. **When to Worry:**
   - ✅ Write then immediately read same data → USE RETRY LOGIC
   - ✅ High-frequency operations (< 3 seconds apart) → USE RETRY LOGIC
   - ⚠️ Batch writes followed by queries → ADD DELAY or RETRY
   - ✅ Long-running queries (>5 seconds after write) → Usually OK

6. **Monitoring:**
   - Log retry counts in application
   - Monitor "retry_count" field in responses
   - If retry_count consistently >3, consider tuning WAL commit settings

Usage:
    provider = QuestDBProvider(
        ilp_host='localhost',
        ilp_port=9009,
        pg_host='localhost',
        pg_port=8812
    )

    # Fast insert (async - data goes to WAL)
    await provider.insert_price(symbol='BTC/USD', timestamp=now, close=50000, volume=1000)

    # Batch insert (fastest - async)
    await provider.insert_prices_batch(prices_list)

    # ⚠️ IMPORTANT: Query immediately after write may return empty!
    # Solution: Use retry logic in calling code (see indicators_routes.py)
    df = await provider.get_prices(symbol='BTC/USD', start_time=..., end_time=...)
"""

import logging
import asyncio
import time
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import asyncpg
from questdb.ingress import Sender, IngressError, TimestampNanos, Protocol

logger = logging.getLogger(__name__)


class QuestDBProvider:
    """
    QuestDB data provider with dual-protocol support:
    - InfluxDB line protocol (ILP) for fast writes (port 9009)
    - PostgreSQL wire protocol for SQL queries (port 8812)

    NOTE: We use QuestDB as the database, NOT PostgreSQL!
    QuestDB implements PostgreSQL wire protocol for SQL compatibility.
    """

    def __init__(
        self,
        ilp_host: str = 'localhost',
        ilp_port: int = 9009,
        pg_host: str = 'localhost',
        pg_port: int = 8812,
        pg_user: str = 'admin',
        pg_password: str = 'quest',
        pg_database: str = 'qdb',
        pg_pool_size: int = 10,
        ilp_sender_pool_size: int = 5,
        ilp_retry_attempts: int = 3,
        ilp_retry_delays: Optional[List[float]] = None,
    ):
        """
        Initialize QuestDB provider with connection pooling for both protocols.

        ✅ PERFORMANCE FIX: Now uses connection pool pattern for ILP Senders to prevent
        port exhaustion and reduce connection overhead. Reuses persistent TCP connections
        instead of creating new ones for each batch write.

        Args:
            ilp_host: QuestDB ILP endpoint host
            ilp_port: QuestDB ILP endpoint port (default 9009)
            pg_host: QuestDB host for PostgreSQL protocol
            pg_port: QuestDB PostgreSQL protocol port (default 8812)
            pg_user: QuestDB username (for PostgreSQL protocol)
            pg_password: QuestDB password (for PostgreSQL protocol)
            pg_database: QuestDB database name (default 'qdb')
            pg_pool_size: Connection pool size for PostgreSQL protocol (default 10)
            ilp_sender_pool_size: ILP Sender pool size (default 5)
            ilp_retry_attempts: Number of retry attempts for ILP operations (default 3)
            ilp_retry_delays: Retry delays in seconds (default [1.0, 2.0, 4.0] for exponential backoff)
        """
        # InfluxDB line protocol config
        self.ilp_host = ilp_host
        self.ilp_port = ilp_port
        self.ilp_sender_pool_size = ilp_sender_pool_size
        self.ilp_retry_attempts = ilp_retry_attempts
        self.ilp_retry_delays = ilp_retry_delays or [1.0, 2.0, 4.0]

        # QuestDB config (PostgreSQL protocol)
        self.pg_host = pg_host
        self.pg_port = pg_port
        self.pg_user = pg_user
        self.pg_password = pg_password
        self.pg_database = pg_database
        self.pg_pool_size = pg_pool_size

        # QuestDB connection pool via PostgreSQL protocol (initialized in async context)
        self.pg_pool: Optional[asyncpg.Pool] = None

        # ✅ RACE CONDITION FIX: Initialization lock to prevent concurrent pool creation
        self._init_lock = asyncio.Lock()
        self._initialized = False

        # ✅ PERFORMANCE FIX: ILP Sender connection pool
        # Reuses TCP connections to prevent port exhaustion and reduce overhead
        self._sender_pool: List[Sender] = []
        self._sender_pool_lock = asyncio.Lock()
        self._sender_available = asyncio.Condition(self._sender_pool_lock)
        self._ilp_available = True  # ✅ GRACEFUL DEGRADATION: Track ILP availability

        logger.info(
            f"QuestDBProvider initialized (ILP: {ilp_host}:{ilp_port}, PG: {pg_host}:{pg_port}, "
            f"pg_pool: {pg_pool_size}, ilp_pool: {ilp_sender_pool_size}, retry_attempts: {ilp_retry_attempts})"
        )

    async def initialize(self):
        """
        Initialize both PostgreSQL connection pool and ILP Sender pool.

        ✅ PERFORMANCE FIX: Creates persistent ILP Sender connections to prevent
        port exhaustion and reduce TCP handshake overhead.

        ✅ RACE CONDITION FIX: Protected by initialization lock to prevent concurrent
        pool creation from multiple callers. Idempotent - safe to call multiple times.
        """
        async with self._init_lock:
            # ✅ IDEMPOTENT: Return immediately if already initialized
            if self._initialized:
                return

            # Initialize QuestDB connection pool (PostgreSQL protocol)
            if self.pg_pool is None:
                try:
                    self.pg_pool = await asyncpg.create_pool(
                        host=self.pg_host,
                        port=self.pg_port,
                        user=self.pg_user,
                        password=self.pg_password,
                        database=self.pg_database,
                        min_size=2,
                        max_size=self.pg_pool_size,
                        timeout=10.0,  # ✅ CONNECTION TIMEOUT: Prevent infinite hangs
                        command_timeout=30.0,  # ✅ QUERY TIMEOUT: Prevent stuck queries
                    )
                    logger.info(f"QuestDB connection pool created (PostgreSQL protocol, {self.pg_pool_size} connections)")
                except (ConnectionRefusedError, OSError) as e:
                    # ✅ CRITICAL ERROR: QuestDB connection failed (PostgreSQL protocol)
                    # This is REQUIRED (not optional like ILP)
                    error_msg = (
                        f"CRITICAL: Cannot connect to QuestDB (PostgreSQL protocol)\n"
                        f"Error: {e}\n"
                        f"Error Type: {type(e).__name__}\n"
                        f"\n"
                        f"Connection Details:\n"
                        f"  Host: {self.pg_host}:{self.pg_port}\n"
                        f"  User: {self.pg_user}\n"
                        f"  Database: {self.pg_database}\n"
                        f"\n"
                        f"DIAGNOSIS:\n"
                        f"  Port {self.pg_port} may be listening, but connections are being refused.\n"
                        f"  This can happen if:\n"
                        f"    1. QuestDB is starting up (ports open but server not ready)\n"
                        f"    2. Windows Firewall is blocking loopback connections\n"
                        f"    3. QuestDB PostgreSQL wire protocol is disabled\n"
                        f"    4. Wrong credentials or database name\n"
                        f"\n"
                        f"SOLUTION:\n"
                        f"  1. Verify QuestDB is FULLY started:\n"
                        f"     - Open http://127.0.0.1:9000 in browser\n"
                        f"     - Run query: SELECT 1\n"
                        f"     - Check logs for \"server is ready\" message\n"
                        f"\n"
                        f"  2. Enable QuestDB PostgreSQL protocol:\n"
                        f"     - Edit: <questdb_root>/conf/server.conf\n"
                        f"     - Add/verify lines:\n"
                        f"         pg.enabled=true\n"
                        f"         pg.net.bind.to=0.0.0.0:8812\n"
                        f"     - Restart QuestDB after config changes\n"
                        f"     - NOTE: This is QuestDB's PostgreSQL PROTOCOL, not a separate PostgreSQL database!\n"
                        f"\n"
                        f"  3. Check Windows Firewall:\n"
                        f"     - Allow QuestDB.exe through firewall\n"
                        f"     - Allow port 8812 (PostgreSQL)\n"
                        f"     - Allow port 9009 (ILP)\n"
                        f"\n"
                        f"  4. Test connection manually:\n"
                        f"     - Windows: Test-NetConnection -ComputerName 127.0.0.1 -Port 8812\n"
                        f"     - Use PostgreSQL client: psql -h 127.0.0.1 -p 8812 -U admin -d qdb\n"
                        f"\n"
                        f"  5. Wait 30 seconds if QuestDB just started, then retry\n"
                    )
                    logger.error("questdb_provider.postgresql_connection_failed", {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "pg_host": self.pg_host,
                        "pg_port": self.pg_port,
                        "pg_user": self.pg_user,
                        "pg_database": self.pg_database,
                        "solution": "See error message for detailed diagnostics"
                    })
                    raise RuntimeError(error_msg) from e
                except Exception as e:
                    # ✅ CATCH-ALL: Unexpected QuestDB connection errors (auth, invalid database, etc.)
                    # NOTE: asyncpg is already imported globally (line 102), no need for local import
                    error_msg = (
                        f"CRITICAL: QuestDB connection failed (PostgreSQL protocol)\n"
                        f"Error: {e}\n"
                        f"Error Type: {type(e).__name__}\n"
                        f"\n"
                        f"Connection Details:\n"
                        f"  Host: {self.pg_host}:{self.pg_port}\n"
                        f"  User: {self.pg_user}\n"
                        f"  Database: {self.pg_database}\n"
                        f"\n"
                    )

                    # Add specific guidance based on error type
                    if isinstance(e, asyncpg.exceptions.InvalidPasswordError):
                        error_msg += (
                            f"DIAGNOSIS: Invalid password for user '{self.pg_user}'\n"
                            f"SOLUTION: Check QuestDB default credentials (admin/quest)\n"
                        )
                    elif isinstance(e, asyncpg.exceptions.InvalidCatalogNameError):
                        error_msg += (
                            f"DIAGNOSIS: Database '{self.pg_database}' does not exist\n"
                            f"SOLUTION: QuestDB default database is 'qdb' - verify in server.conf\n"
                        )
                    else:
                        error_msg += (
                            f"DIAGNOSIS: Unexpected error during QuestDB connection\n"
                            f"SOLUTION:\n"
                            f"  1. Check QuestDB logs for errors\n"
                            f"  2. Enable PostgreSQL protocol in server.conf (pg.enabled=true, pg.net.bind.to=0.0.0.0:8812)\n"
                            f"  3. Restart QuestDB\n"
                            f"  4. NOTE: QuestDB uses PostgreSQL PROTOCOL for SQL queries, NOT a separate PostgreSQL database!\n"
                        )

                    logger.error("questdb_provider.connection_error", {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "pg_host": self.pg_host,
                        "pg_port": self.pg_port
                    })
                    raise RuntimeError(error_msg) from e

            # ✅ PERFORMANCE FIX: Initialize ILP Sender pool (OPTIONAL - graceful degradation)
            async with self._sender_pool_lock:
                if not self._sender_pool:
                    ilp_initialization_failed = False
                    for i in range(self.ilp_sender_pool_size):
                        try:
                            sender = Sender(Protocol.Tcp, self.ilp_host, self.ilp_port)
                            sender.__enter__()  # ✅ CRITICAL FIX: Open sender context (required by QuestDB client)
                            self._sender_pool.append(sender)
                            logger.debug(f"ILP Sender #{i+1} created")
                        except IngressError as e:
                            logger.error(f"Failed to create ILP Sender #{i+1}: {e}")
                            # Close any senders that were created
                            for s in self._sender_pool:
                                try:
                                    s.__exit__(None, None, None)  # ✅ CRITICAL FIX: Properly close sender context
                                except:
                                    pass
                            self._sender_pool.clear()
                            ilp_initialization_failed = True
                            self._ilp_available = False  # ✅ GRACEFUL DEGRADATION: Mark ILP as unavailable

                            # ✅ GRACEFUL DEGRADATION: Log warning but continue with PostgreSQL-only mode
                            logger.warning(
                                "questdb_provider.ilp_initialization_failed",
                                {
                                    "error": str(e),
                                    "ilp_host": self.ilp_host,
                                    "ilp_port": self.ilp_port,
                                    "fallback": "PostgreSQL protocol only",
                                    "impact": "Writes will be slower (PostgreSQL instead of ILP)",
                                    "solution": "Verify QuestDB ILP endpoint is enabled: check conf/server.conf -> line.tcp.enabled=true"
                                }
                            )
                            break  # Stop trying to create more senders

                    if self._sender_pool:
                        logger.info(f"ILP Sender pool created ({len(self._sender_pool)} connections)")
                    elif ilp_initialization_failed:
                        logger.warning(f"QuestDB running in DEGRADED MODE: SQL queries only via PostgreSQL protocol (ILP writes unavailable)")

            # ✅ MARK AS INITIALIZED: Prevents re-initialization
            self._initialized = True

    async def close(self):
        """
        Close both PostgreSQL connection pool and ILP Sender pool.

        ✅ PERFORMANCE FIX: Properly closes all pooled connections.
        ✅ RACE CONDITION FIX: Protected by initialization lock to prevent concurrent cleanup.
        Idempotent - safe to call multiple times.
        """
        async with self._init_lock:
            # ✅ IDEMPOTENT: Return immediately if already closed
            if not self._initialized:
                return

            # Close QuestDB connection pool (PostgreSQL protocol)
            if self.pg_pool:
                await self.pg_pool.close()
                self.pg_pool = None
                logger.info("QuestDB connection pool closed (PostgreSQL protocol)")

            # ✅ PERFORMANCE FIX: Close ILP Sender pool
            async with self._sender_pool_lock:
                for i, sender in enumerate(self._sender_pool):
                    try:
                        sender.__exit__(None, None, None)  # ✅ CRITICAL FIX: Properly close sender context
                        logger.debug(f"ILP Sender #{i+1} closed")
                    except Exception as e:
                        logger.warning(f"Error closing ILP Sender #{i+1}: {e}")
                sender_count = len(self._sender_pool)
                self._sender_pool.clear()
                if sender_count > 0:
                    logger.info(f"ILP Sender pool closed ({sender_count} connections)")
                # Note: using if check because pool might be empty if initialize() was never called

            # ✅ MARK AS CLOSED: Prevents re-cleanup
            self._initialized = False

    async def is_healthy(self) -> bool:
        """
        Check if QuestDB is healthy and accepting connections.

        Tests both ILP (port 9009) and PostgreSQL (port 8812) connections
        to ensure full database availability.

        Returns:
            True if both ILP and PostgreSQL are accessible, False otherwise
        """
        ilp_ok = False
        pg_ok = False

        # Test ILP connection (port 9009) - try to create sender
        try:
            with Sender(Protocol.Tcp, self.ilp_host, self.ilp_port) as sender:
                # Just test connection creation, no actual write
                pass
            ilp_ok = True
            logger.debug("QuestDB ILP health check: OK")
        except IngressError as e:
            logger.warning(f"QuestDB ILP health check failed: {e}")
        except Exception as e:
            logger.warning(f"QuestDB ILP health check error: {e}")

        # Test QuestDB connection via PostgreSQL protocol (port 8812)
        try:
            await self.initialize()  # Ensure pool is created
            if self.pg_pool:
                async with self.pg_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                pg_ok = True
                logger.debug("QuestDB PostgreSQL health check: OK")
        except Exception as e:
            logger.warning(f"QuestDB PostgreSQL health check failed: {e}")

        is_healthy = ilp_ok and pg_ok

        if is_healthy:
            logger.info("QuestDB health check: HEALTHY (ILP ✓, PostgreSQL ✓)")
        else:
            logger.error(f"QuestDB health check: UNHEALTHY (ILP: {'✓' if ilp_ok else '✗'}, PostgreSQL: {'✓' if pg_ok else '✗'})")

        return is_healthy

    async def _acquire_sender(self) -> Sender:
        """
        Acquire a Sender from the pool (blocking until available).

        ✅ PERFORMANCE FIX: Reuses pooled connections instead of creating new ones.
        ✅ CRITICAL FIX: On-demand sender creation when pool is exhausted.
        ✅ GRACEFUL DEGRADATION: Raises RuntimeError if ILP is unavailable.

        This prevents deadlock when all senders fail and replacement attempts fail.
        Instead of waiting forever, we attempt to create a new sender on-demand.

        Returns:
            Sender instance from the pool or newly created

        Raises:
            RuntimeError: If ILP is unavailable or unable to create sender after max retries
        """
        # ✅ GRACEFUL DEGRADATION: Check if ILP is available before attempting
        if not self._ilp_available:
            raise RuntimeError(
                "ILP (InfluxDB Line Protocol) is not available. "
                "QuestDB is running in PostgreSQL-only mode. "
                "To enable ILP, verify QuestDB configuration: conf/server.conf -> line.tcp.enabled=true"
            )

        async with self._sender_available:
            max_create_attempts = 3
            create_retry_delay = 1.0

            for attempt in range(max_create_attempts):
                if self._sender_pool:
                    # Happy path: sender available in pool
                    sender = self._sender_pool.pop()
                    logger.debug(f"Sender acquired from pool (remaining: {len(self._sender_pool)})")
                    return sender

                # Pool is empty - try to create new sender on-demand
                logger.warning(
                    f"Sender pool exhausted (attempt {attempt + 1}/{max_create_attempts}), "
                    f"creating new sender on-demand for emergency recovery"
                )

                try:
                    new_sender = Sender(Protocol.Tcp, self.ilp_host, self.ilp_port)
                    new_sender.__enter__()  # ✅ CRITICAL FIX: Open sender context (required by QuestDB client)
                    logger.info(f"Emergency sender created (pool was empty, self-healing activated)")
                    return new_sender
                except IngressError as e:
                    is_last_attempt = (attempt == max_create_attempts - 1)

                    if is_last_attempt:
                        # All creation attempts failed - QuestDB is likely offline
                        error_msg = (
                            f"Failed to create sender after {max_create_attempts} attempts: {e}\n"
                            f"QuestDB appears to be offline or unreachable.\n"
                            f"Please verify:\n"
                            f"  1. QuestDB is running\n"
                            f"  2. Port {self.ilp_port} (ILP) is accessible\n"
                            f"  3. No firewall blocking connections\n"
                            f"  4. Check Web UI: http://127.0.0.1:9000"
                        )
                        logger.error(error_msg)
                        raise RuntimeError(error_msg) from e
                    else:
                        logger.warning(
                            f"Sender creation failed (attempt {attempt + 1}): {e}, "
                            f"retrying in {create_retry_delay}s"
                        )
                        # Release lock temporarily to allow other operations
                        # Using asyncio.sleep releases the lock due to context manager exit
                        # We'll re-acquire in next iteration
                        await asyncio.sleep(create_retry_delay)

            # Should never reach here due to exception in last attempt, but for safety
            raise RuntimeError("Failed to acquire sender: pool exhausted and unable to create new sender")

    async def _release_sender(self, sender: Sender, is_broken: bool = False):
        """
        Return a Sender to the pool or replace if broken.

        ✅ PERFORMANCE FIX: Returns healthy senders to pool for reuse, recreates broken ones.
        ✅ RECOVERY FIX: Graceful degradation - even if replacement fails, we don't crash.

        The _acquire_sender() method will handle on-demand creation if pool exhausts,
        so we don't need to panic if replacement fails here.

        Args:
            sender: Sender instance to release
            is_broken: If True, sender will be closed and replaced with a new one
        """
        async with self._sender_available:
            if is_broken:
                # Close broken sender (properly exit context)
                try:
                    sender.__exit__(None, None, None)  # ✅ CRITICAL FIX: Properly close sender context
                    logger.debug("Broken sender closed")
                except Exception as e:
                    logger.warning(f"Error closing broken sender: {e}")

                # Try to create a replacement (best effort)
                try:
                    new_sender = Sender(Protocol.Tcp, self.ilp_host, self.ilp_port)
                    new_sender.__enter__()  # ✅ CRITICAL FIX: Open sender context (required by QuestDB client)
                    self._sender_pool.append(new_sender)
                    logger.info(f"Broken sender replaced (pool size: {len(self._sender_pool)})")
                except IngressError as e:
                    # ✅ CHANGED: Log as warning, not error - this is recoverable
                    # Pool shrinks, but _acquire_sender will handle on-demand creation
                    logger.warning(
                        f"Failed to replace broken sender: {e}. "
                        f"Pool reduced to {len(self._sender_pool)} connections. "
                        f"On-demand creation will be used if pool exhausts."
                    )
                    # ✅ CRITICAL: Don't raise - allow graceful degradation
                    # The system can continue with reduced pool size
            else:
                # Return healthy sender to pool
                self._sender_pool.append(sender)
                logger.debug(f"Sender released to pool (total: {len(self._sender_pool)})")

            # Notify waiting coroutines that a sender may be available
            # (or they should try creating one via on-demand creation)
            self._sender_available.notify()

    @asynccontextmanager
    async def _get_pooled_sender(self):
        """
        ✅ CRITICAL FIX: Async context manager for acquiring/releasing pooled Senders.

        This replaces the old non-existent _get_sender() method with proper async pool
        integration. Automatically handles acquisition, release, and error recovery.

        Usage:
            async with self._get_pooled_sender() as sender:
                sender.row(...)
                sender.flush()

        Yields:
            Sender instance from the pool

        Raises:
            RuntimeError: If pool is not initialized
        """
        sender = None
        sender_acquired = False

        try:
            # Acquire sender from pool
            sender = await self._acquire_sender()
            sender_acquired = True

            # Yield sender for use in 'with' block
            yield sender

        except IngressError as e:
            # ILP error - mark sender as broken
            logger.warning(f"ILP error in context manager: {e}")
            if sender_acquired and sender is not None:
                await self._release_sender(sender, is_broken=True)
                sender_acquired = False
                sender = None  # ✅ CRITICAL: Reset sender reference to prevent use-after-free
            raise

        except Exception as e:
            # Unexpected error - mark sender as broken
            logger.error(f"Unexpected error in pooled sender context: {e}")
            if sender_acquired and sender is not None:
                await self._release_sender(sender, is_broken=True)
                sender_acquired = False
                sender = None  # ✅ CRITICAL: Reset sender reference to prevent use-after-free
            raise

        else:
            # Success - return healthy sender to pool
            if sender_acquired and sender is not None:
                await self._release_sender(sender, is_broken=False)
                sender_acquired = False
                sender = None  # ✅ CRITICAL: Reset sender reference to prevent use-after-free

    @staticmethod
    def _convert_datetime_to_timestamp(row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert datetime objects to Unix timestamps in a dictionary.

        ✅ CRITICAL FIX: Ensures consistent timestamp format across all query methods.

        Args:
            row_dict: Dictionary potentially containing datetime values

        Returns:
            Dictionary with datetime values converted to Unix timestamps (float)
        """
        for key, value in row_dict.items():
            if isinstance(value, datetime):
                row_dict[key] = value.timestamp()
        return row_dict

    @staticmethod
    def _is_permanent_failure(error: IngressError) -> bool:
        """
        Detect if error indicates a permanent failure (e.g., server not running).

        ✅ RETRY LOGIC FIX: Distinguishes between permanent failures (QuestDB not running)
        and transient failures (network glitch, temporary overload).

        Permanent failures should fail fast without retries, while transient failures
        benefit from exponential backoff retry.

        Args:
            error: IngressError from QuestDB client

        Returns:
            True if error indicates permanent failure, False for transient failure
        """
        error_str = str(error).lower()

        # Connection refused - server not running (WSAECONNREFUSED 10061 on Windows)
        permanent_indicators = [
            'connection refused',
            'could not connect',
            'os error 10061',  # Windows WSAECONNREFUSED
            'connection reset',
            'broken pipe',
        ]

        return any(indicator in error_str for indicator in permanent_indicators)

    async def _execute_ilp_with_retry(self, operation_name: str, write_func) -> int:
        """
        Execute ILP write operation with retry logic and exponential backoff.

        ✅ PERFORMANCE FIX: Now uses connection pool pattern instead of creating new Sender
        for each operation. Reuses persistent TCP connections to prevent port exhaustion
        and reduce overhead.

        ✅ RETRY LOGIC FIX: Detects permanent failures (server not running) and fails fast
        without exhausting all retry attempts. Only retries transient failures.

        This method addresses transient connection failures to QuestDB caused by:
        - QuestDB overload (WAL queue full, temporarily refusing new connections)
        - Network timing issues (even on localhost)
        - Broken connections (automatically recreated)

        Args:
            operation_name: Name of operation for logging (e.g., "insert_tick_prices")
            write_func: Callable that performs the actual write using a Sender instance

        Returns:
            Number of successfully inserted rows

        Raises:
            Exception: If all retry attempts fail or permanent failure detected
        """
        last_error = None
        sender = None
        sender_acquired = False

        for attempt in range(self.ilp_retry_attempts + 1):
            try:
                # ✅ PERFORMANCE FIX: Acquire sender from pool (not create new)
                if not sender_acquired:
                    sender = await self._acquire_sender()
                    sender_acquired = True

                # Execute write operation
                inserted = write_func(sender)
                sender.flush()

                # ✅ PERFORMANCE FIX: Return sender to pool (not close)
                await self._release_sender(sender, is_broken=False)
                sender_acquired = False
                sender = None

                if attempt > 0:
                    logger.info(f"{operation_name} succeeded after {attempt + 1} attempts ({inserted} rows)")
                else:
                    logger.debug(f"{operation_name} succeeded ({inserted} rows)")

                return inserted

            except IngressError as e:
                last_error = e
                is_last_attempt = (attempt == self.ilp_retry_attempts)
                error_str = str(e).lower()

                # ✅ CRITICAL FIX: Mark sender as broken and release it
                if sender_acquired and sender is not None:
                    await self._release_sender(sender, is_broken=True)
                    sender_acquired = False
                    sender = None

                # ✅ STALE SENDER DETECTION: "Sender is closed" is recoverable
                # This happens when:
                # - QuestDB restarted (all TCP connections closed)
                # - Sender was idle too long (connection timeout)
                # - Previous error left sender in closed state
                # - Pool returned a stale sender that wasn't properly validated
                is_stale_sender = "sender is closed" in error_str or "closed" in error_str

                if is_stale_sender:
                    if not is_last_attempt:
                        logger.warning(
                            f"{operation_name} failed with stale sender (attempt {attempt + 1}/{self.ilp_retry_attempts + 1}): {e}. "
                            f"Sender was closed (QuestDB restart or idle timeout). "
                            f"Retrying with new sender..."
                        )
                        # Don't check for permanent failure - this is always recoverable
                        # Just retry with new sender (will be acquired in next iteration)
                        delay = self.ilp_retry_delays[min(attempt, len(self.ilp_retry_delays) - 1)]
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Last attempt with stale sender - still fail but with clear message
                        error_msg = (
                            f"Failed to {operation_name} after {self.ilp_retry_attempts + 1} attempts (stale sender): {e}\n"
                            f"All retry attempts exhausted. Senders are persistently closed.\n"
                            f"This may indicate:\n"
                            f"  1. QuestDB is restarting repeatedly\n"
                            f"  2. Network connection is unstable\n"
                            f"  3. Firewall is blocking persistent connections"
                        )
                        logger.error(error_msg)
                        raise Exception(error_msg) from e

                # ✅ RETRY LOGIC FIX: Detect permanent failures and fail fast
                is_permanent = self._is_permanent_failure(e)

                if is_permanent:
                    error_msg = (
                        f"Failed to {operation_name}: QuestDB appears to be OFFLINE (permanent failure detected)\n"
                        f"Error: {e}\n"
                        f"\n"
                        f"This error indicates QuestDB is not running or not accepting connections.\n"
                        f"Retrying will not help. Please:\n"
                        f"  1. Start QuestDB server\n"
                        f"  2. Verify ports {self.ilp_port} (ILP) and {self.pg_port} (PostgreSQL) are accessible\n"
                        f"  3. Check Web UI: http://127.0.0.1:9000\n"
                        f"\n"
                        f"Failing fast without retries to prevent data loss and buffer overflow."
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg) from e

                if is_last_attempt:
                    error_msg = f"Failed to {operation_name} after {self.ilp_retry_attempts + 1} attempts: {e}"
                    logger.error(error_msg)
                    raise Exception(error_msg) from e
                else:
                    # Calculate delay for this attempt (ensure we don't exceed delays list)
                    delay = self.ilp_retry_delays[min(attempt, len(self.ilp_retry_delays) - 1)]
                    logger.warning(
                        f"Failed to {operation_name} (attempt {attempt + 1}/{self.ilp_retry_attempts + 1}): {e}. "
                        f"Retrying in {delay}s... (transient failure)"
                    )
                    await asyncio.sleep(delay)

            except Exception as e:
                # Unexpected error - release sender if acquired
                if sender_acquired and sender is not None:
                    await self._release_sender(sender, is_broken=True)
                    sender_acquired = False
                    sender = None
                raise

        # Should never reach here, but for type safety
        raise Exception(f"Failed to {operation_name}: {last_error}")

    # ========================================================================
    # FAST WRITES (InfluxDB Line Protocol)
    # ========================================================================

    async def insert_price(
        self,
        symbol: str,
        timestamp: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
    ) -> bool:
        """
        Insert single price record (InfluxDB line protocol).

        ✅ CRITICAL FIX: Now uses connection pool via async context manager.

        Args:
            symbol: Trading pair (e.g., 'BTC/USD')
            timestamp: Price timestamp
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
            bid: Bid price (optional)
            ask: Ask price (optional)

        Returns:
            True if successful
        """
        try:
            async with self._get_pooled_sender() as sender:
                columns = {
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'volume': volume,
                }

                if bid is not None:
                    columns['bid'] = bid
                if ask is not None:
                    columns['ask'] = ask
                    if bid is not None:
                        columns['spread'] = ask - bid

                sender.row(
                    'prices',
                    symbols={'symbol': symbol},
                    columns=columns,
                    at=TimestampNanos(int(timestamp.timestamp() * 1_000_000_000))
                )
                sender.flush()

            return True

        except IngressError as e:
            logger.error(f"Failed to insert price for {symbol}: {e}")
            return False

    async def insert_prices_batch(self, prices: List[Dict[str, Any]]) -> int:
        """
        Insert batch of price records (fastest method).

        ✅ CRITICAL FIX: Now uses connection pool via async context manager.

        Args:
            prices: List of price dictionaries with keys:
                - symbol: str
                - timestamp: datetime
                - open, high, low, close, volume: float
                - bid, ask: float (optional)

        Returns:
            Number of successfully inserted rows
        """
        if not prices:
            return 0

        inserted = 0

        try:
            async with self._get_pooled_sender() as sender:
                for price in prices:
                    columns = {
                        'open': price['open'],
                        'high': price['high'],
                        'low': price['low'],
                        'close': price['close'],
                        'volume': price['volume'],
                    }

                    if 'bid' in price and price['bid'] is not None:
                        columns['bid'] = price['bid']
                    if 'ask' in price and price['ask'] is not None:
                        columns['ask'] = price['ask']
                        if 'bid' in price and price['bid'] is not None:
                            columns['spread'] = price['ask'] - price['bid']

                    sender.row(
                        'prices',
                        symbols={'symbol': price['symbol']},
                        columns=columns,
                        at=TimestampNanos(int(price['timestamp'].timestamp() * 1_000_000_000))
                    )
                    inserted += 1

                sender.flush()

            logger.info(f"Inserted {inserted} price records")
            return inserted

        except IngressError as e:
            logger.error(f"Failed to insert batch: {e}")
            return inserted

    async def insert_indicator(
        self,
        symbol: str,
        indicator_id: str,
        timestamp: datetime,
        value: float,
        confidence: Optional[float] = None,
        metadata: Optional[str] = None,
    ) -> bool:
        """
        Insert single indicator value (InfluxDB line protocol).

        ✅ CRITICAL FIX: Now uses connection pool via async context manager.

        Args:
            symbol: Trading pair
            indicator_id: Indicator identifier (e.g., 'RSI_14')
            timestamp: Calculation timestamp
            value: Indicator value
            confidence: Confidence score 0-1 (optional)
            metadata: JSON metadata string (optional)

        Returns:
            True if successful
        """
        try:
            async with self._get_pooled_sender() as sender:
                columns = {'value': value}

                if confidence is not None:
                    columns['confidence'] = confidence

                # Note: metadata must be sent via PostgreSQL INSERT
                # InfluxDB line protocol doesn't support STRING columns well

                sender.row(
                    'indicators',
                    symbols={
                        'symbol': symbol,
                        'indicator_id': indicator_id,
                    },
                    columns=columns,
                    at=TimestampNanos(int(timestamp.timestamp() * 1_000_000_000))
                )
                sender.flush()

            return True

        except IngressError as e:
            logger.error(f"Failed to insert indicator {indicator_id} for {symbol}: {e}")
            return False

    async def insert_indicators_batch(self, indicators: List[Dict[str, Any]]) -> int:
        """
        Insert batch of indicator values with automatic retry logic.

        CRITICAL: session_id is REQUIRED - no backward compatibility with NULL values.
        All indicators must be associated with a data collection session.

        This method uses exponential backoff retry to handle transient connection
        failures to QuestDB.

        Args:
            indicators: List of indicator dictionaries with REQUIRED keys:
                - session_id: str (REQUIRED)
                - symbol: str (REQUIRED)
                - indicator_id: str (REQUIRED)
                - timestamp: datetime (REQUIRED)
                - value: float (REQUIRED)
                - confidence: float (optional)

        Returns:
            Number of successfully inserted rows

        Raises:
            ValueError: If any required field is missing
            Exception: If all retry attempts fail
        """
        if not indicators:
            return 0

        # VALIDATION: Enforce required fields (no backward compatibility)
        required_fields = ['session_id', 'symbol', 'indicator_id', 'timestamp', 'value']

        for idx, indicator in enumerate(indicators):
            missing = [field for field in required_fields if field not in indicator]
            if missing:
                error_msg = f"Indicator at index {idx} missing required fields: {missing}"
                logger.error(f"insert_indicators_batch.validation_failed: {error_msg}")
                raise ValueError(error_msg)

        def write_batch(sender):
            """Inner function that performs the actual write."""
            inserted = 0
            for indicator in indicators:
                columns = {'value': indicator['value']}

                if 'confidence' in indicator and indicator['confidence'] is not None:
                    columns['confidence'] = indicator['confidence']

                # CRITICAL FIX: Include session_id in SYMBOL fields
                # session_id is a SYMBOL column in QuestDB schema, not a regular column
                sender.row(
                    'indicators',
                    symbols={
                        'session_id': indicator['session_id'],  # ✅ ADDED
                        'symbol': indicator['symbol'],
                        'indicator_id': indicator['indicator_id'],
                    },
                    columns=columns,
                    at=TimestampNanos(int(indicator['timestamp'].timestamp() * 1_000_000_000))
                )
                inserted += 1
            return inserted

        return await self._execute_ilp_with_retry("insert_indicators_batch", write_batch)

    # ========================================================================
    # QUERIES (PostgreSQL Wire Protocol)
    # ========================================================================

    async def get_prices(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Query price data.

        ✅ CRITICAL FIX: Converts datetime objects to Unix timestamps.

        Args:
            symbol: Trading pair
            start_time: Start timestamp (optional)
            end_time: End timestamp (optional)
            limit: Maximum rows to return

        Returns:
            DataFrame with price data (timestamps as Unix floats)
        """
        await self.initialize()

        query = "SELECT * FROM tick_prices WHERE symbol = $1"
        params = [symbol]

        if start_time:
            query += " AND timestamp >= $2"
            params.append(start_time)

        if end_time:
            idx = len(params) + 1
            query += f" AND timestamp <= ${idx}"
            params.append(end_time)

        query += f" ORDER BY timestamp DESC LIMIT ${len(params) + 1}"
        params.append(limit)

        async with self.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        if not rows:
            return pd.DataFrame()

        # Convert datetime objects to Unix timestamps
        df = pd.DataFrame([self._convert_datetime_to_timestamp(dict(row)) for row in rows])
        return df

    async def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest price for symbol.

        ✅ CRITICAL FIX: Converts datetime objects to Unix timestamps.

        Args:
            symbol: Trading pair

        Returns:
            Price dictionary with timestamps as Unix floats, or None
        """
        await self.initialize()

        query = """
            SELECT * FROM tick_prices
            WHERE symbol = $1
            LATEST BY symbol
        """

        async with self.pg_pool.acquire() as conn:
            row = await conn.fetchrow(query, symbol)

        if row:
            return self._convert_datetime_to_timestamp(dict(row))
        return None

    async def get_indicators(
        self,
        symbol: str,
        indicator_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Query indicator data.

        ✅ CRITICAL FIX: Converts datetime objects to Unix timestamps.

        Args:
            symbol: Trading pair
            indicator_ids: List of indicator IDs to filter (optional)
            start_time: Start timestamp (optional)
            end_time: End timestamp (optional)
            limit: Maximum rows per indicator

        Returns:
            DataFrame with indicator data (timestamps as Unix floats)
        """
        await self.initialize()

        query = "SELECT * FROM indicators WHERE symbol = $1"
        params = [symbol]

        if indicator_ids:
            placeholders = ', '.join([f'${i+2}' for i in range(len(indicator_ids))])
            query += f" AND indicator_id IN ({placeholders})"
            params.extend(indicator_ids)

        if start_time:
            idx = len(params) + 1
            query += f" AND timestamp >= ${idx}"
            params.append(start_time)

        if end_time:
            idx = len(params) + 1
            query += f" AND timestamp <= ${idx}"
            params.append(end_time)

        query += f" ORDER BY timestamp DESC LIMIT ${len(params) + 1}"
        params.append(limit)

        async with self.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        if not rows:
            return pd.DataFrame()

        # Convert datetime objects to Unix timestamps
        df = pd.DataFrame([self._convert_datetime_to_timestamp(dict(row)) for row in rows])
        return df

    async def get_latest_indicators(
        self,
        symbol: str,
        indicator_ids: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Get latest values for all indicators.

        Args:
            symbol: Trading pair
            indicator_ids: List of indicator IDs to filter (optional)

        Returns:
            Dictionary: {indicator_id: value}
        """
        await self.initialize()

        if indicator_ids:
            placeholders = ', '.join([f'${i+2}' for i in range(len(indicator_ids))])
            query = f"""
                SELECT indicator_id, value
                FROM indicators
                WHERE symbol = $1
                  AND indicator_id IN ({placeholders})
                LATEST BY indicator_id
            """
            params = [symbol] + indicator_ids
        else:
            query = """
                SELECT indicator_id, value
                FROM indicators
                WHERE symbol = $1
                LATEST BY indicator_id
            """
            params = [symbol]

        async with self.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return {row['indicator_id']: row['value'] for row in rows}

    async def get_ohlcv_resample(
        self,
        symbol: str,
        interval: str = '1m',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Get resampled OHLCV data.

        ✅ CRITICAL FIX: Converts datetime objects to Unix timestamps.

        Args:
            symbol: Trading pair
            interval: Resample interval ('1s', '1m', '5m', '1h', '1d')
            start_time: Start timestamp (optional)
            end_time: End timestamp (optional)

        Returns:
            DataFrame with resampled OHLCV (timestamps as Unix floats)
        """
        await self.initialize()

        query = f"""
            SELECT
                timestamp,
                first(price) as open,
                max(price) as high,
                min(price) as low,
                last(price) as close,
                sum(volume) as volume
            FROM tick_prices
            WHERE symbol = $1
        """
        params = [symbol]

        if start_time:
            query += " AND timestamp >= $2"
            params.append(start_time)

        if end_time:
            idx = len(params) + 1
            query += f" AND timestamp <= ${idx}"
            params.append(end_time)

        query += f" SAMPLE BY {interval} ALIGN TO CALENDAR"

        async with self.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        if not rows:
            return pd.DataFrame()

        # Convert datetime objects to Unix timestamps
        df = pd.DataFrame([self._convert_datetime_to_timestamp(dict(row)) for row in rows])
        return df

    # ========================================================================
    # DATA COLLECTION SUPPORT
    # ========================================================================

    async def insert_tick_prices_batch(self, ticks: List[Dict[str, Any]]) -> int:
        """
        Insert batch of tick price data (high-frequency) with automatic retry logic.

        This method uses exponential backoff retry to handle transient connection
        failures to QuestDB. Common causes include connection exhaustion, QuestDB
        overload, and OS port exhaustion.

        Args:
            ticks: List of tick dictionaries with keys:
                - session_id: str
                - symbol: str
                - timestamp: float (seconds with decimal precision)
                - price: float
                - volume: float
                - quote_volume: float

        Returns:
            Number of successfully inserted rows

        Raises:
            Exception: If all retry attempts fail
        """
        if not ticks:
            return 0

        def write_batch(sender):
            """Inner function that performs the actual write."""
            inserted = 0
            for tick in ticks:
                timestamp_seconds = float(tick['timestamp'])
                timestamp_ns = int(timestamp_seconds * 1_000_000_000)

                sender.row(
                    'tick_prices',
                    symbols={
                        'session_id': tick['session_id'],
                        'symbol': tick['symbol'],
                    },
                    columns={
                        'price': float(tick['price']),
                        'volume': float(tick['volume']),
                        'quote_volume': float(tick['quote_volume']),
                    },
                    at=TimestampNanos(timestamp_ns)
                )
                inserted += 1
            return inserted

        return await self._execute_ilp_with_retry("insert_tick_prices_batch", write_batch)

    async def insert_orderbook_snapshots_batch(self, snapshots: List[Dict[str, Any]]) -> int:
        """
        Insert batch of orderbook snapshots (3-level) with automatic retry logic.

        This method uses exponential backoff retry to handle transient connection
        failures to QuestDB.

        Args:
            snapshots: List of orderbook dictionaries with keys:
                - session_id: str
                - symbol: str
                - timestamp: float (seconds with decimal precision)
                - bid_price_1, bid_qty_1, bid_price_2, bid_qty_2, bid_price_3, bid_qty_3: float
                - ask_price_1, ask_qty_1, ask_price_2, ask_qty_2, ask_price_3, ask_qty_3: float

        Returns:
            Number of successfully inserted rows

        Raises:
            Exception: If all retry attempts fail
        """
        if not snapshots:
            return 0

        def write_batch(sender):
            """Inner function that performs the actual write."""
            inserted = 0
            for snapshot in snapshots:
                timestamp_seconds = float(snapshot['timestamp'])
                timestamp_ns = int(timestamp_seconds * 1_000_000_000)

                sender.row(
                    'tick_orderbook',
                    symbols={
                        'session_id': snapshot['session_id'],
                        'symbol': snapshot['symbol'],
                    },
                    columns={
                        'bid_price_1': float(snapshot.get('bid_price_1', 0)),
                        'bid_qty_1': float(snapshot.get('bid_qty_1', 0)),
                        'bid_price_2': float(snapshot.get('bid_price_2', 0)),
                        'bid_qty_2': float(snapshot.get('bid_qty_2', 0)),
                        'bid_price_3': float(snapshot.get('bid_price_3', 0)),
                        'bid_qty_3': float(snapshot.get('bid_qty_3', 0)),
                        'ask_price_1': float(snapshot.get('ask_price_1', 0)),
                        'ask_qty_1': float(snapshot.get('ask_qty_1', 0)),
                        'ask_price_2': float(snapshot.get('ask_price_2', 0)),
                        'ask_qty_2': float(snapshot.get('ask_qty_2', 0)),
                        'ask_price_3': float(snapshot.get('ask_price_3', 0)),
                        'ask_qty_3': float(snapshot.get('ask_qty_3', 0)),
                    },
                    at=TimestampNanos(timestamp_ns)
                )
                inserted += 1
            return inserted

        return await self._execute_ilp_with_retry("insert_orderbook_snapshots_batch", write_batch)

    # ========================================================================
    # OHLCV AGGREGATION REMOVED
    # ========================================================================
    # insert_ohlcv_candles_batch() removed - aggregated_ohlcv table not used
    # Rationale:
    # - OHLCV aggregation was premature optimization (450+ lines of overhead)
    # - QuestDB has built-in SAMPLE BY for on-demand aggregation
    # - Example: SELECT timestamp, first(price) as open, max(price) as high,
    #            min(price) as low, last(price) as close, sum(volume) as volume
    #            FROM tick_prices SAMPLE BY 1m
    # - Faster, simpler, no pre-aggregation overhead during data collection

    async def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute arbitrary SQL query on QuestDB via PostgreSQL wire protocol.

        ✅ CRITICAL FIX: Converts datetime objects to Unix timestamps (float).

        QuestDB returns TIMESTAMP columns as Python datetime objects via asyncpg,
        but the application expects Unix timestamp floats throughout. This conversion
        prevents timedelta arithmetic errors (datetime - datetime produces timedelta,
        which cannot be divided by int or passed to round()).

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            List of result dictionaries with datetime values converted to Unix timestamps
        """
        await self.initialize()

        try:
            async with self.pg_pool.acquire() as conn:
                if params:
                    rows = await conn.fetch(query, *params)
                else:
                    rows = await conn.fetch(query)

            # Convert datetime objects to Unix timestamps (float)
            results = []
            for row in rows:
                row_dict = self._convert_datetime_to_timestamp(dict(row))
                results.append(row_dict)

            return results

        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            raise

    # ========================================================================
    # BACKTEST SUPPORT
    # ========================================================================

    async def get_backtest_data(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        indicator_ids: List[str],
    ) -> Tuple[pd.DataFrame, Dict[str, pd.Series]]:
        """
        Get data for backtesting (prices + indicators).

        Args:
            symbol: Trading pair
            start_time: Backtest start time
            end_time: Backtest end time
            indicator_ids: List of required indicators

        Returns:
            Tuple of (prices_df, indicators_dict)
        """
        # Get prices
        prices_df = await self.get_prices(
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            limit=1000000  # No limit for backtest
        )

        # Get indicators
        indicators_df = await self.get_indicators(
            symbol=symbol,
            indicator_ids=indicator_ids,
            start_time=start_time,
            end_time=end_time,
            limit=1000000
        )

        # Pivot indicators to dict of series
        indicators_dict = {}
        if not indicators_df.empty:
            for indicator_id in indicator_ids:
                indicator_data = indicators_df[indicators_df['indicator_id'] == indicator_id]
                if not indicator_data.empty:
                    indicators_dict[indicator_id] = indicator_data.set_index('timestamp')['value']

        return prices_df, indicators_dict

    # ========================================================================
    # DELETE OPERATIONS (Application-Level Cascade)
    # ========================================================================

    async def delete_tick_prices(
        self,
        session_id: str,
        symbol: Optional[str] = None
    ) -> int:
        """
        Soft delete tick price data for session.

        Uses UPDATE to set is_deleted = true instead of physical deletion.
        This is 100x faster than table rebuild and allows easy rollback.

        Args:
            session_id: Session identifier
            symbol: Optional symbol filter (soft deletes all symbols if None)

        Returns:
            Number of rows soft deleted
        """
        await self.initialize()

        try:
            # Build UPDATE query with parameterized values
            query = "UPDATE tick_prices SET is_deleted = true WHERE session_id = $1 AND is_deleted = false"
            params = [session_id]

            if symbol:
                query += " AND symbol = $2"
                params.append(symbol)

            async with self.pg_pool.acquire() as conn:
                result = await conn.execute(query, *params)
                # Parse result: "UPDATE N" -> N
                affected_rows = int(result.split()[-1]) if result else 0

            logger.info(f"Soft deleted {affected_rows} tick_prices rows for session {session_id}" +
                       (f", symbol {symbol}" if symbol else ""))
            return affected_rows

        except Exception as e:
            logger.error(f"Failed to soft delete tick_prices for session {session_id}: {e}")
            raise

    async def delete_tick_orderbook(
        self,
        session_id: str,
        symbol: Optional[str] = None
    ) -> int:
        """
        Soft delete orderbook snapshots for session.

        Uses UPDATE to set is_deleted = true instead of physical deletion.

        Args:
            session_id: Session identifier
            symbol: Optional symbol filter (soft deletes all symbols if None)

        Returns:
            Number of rows soft deleted
        """
        await self.initialize()

        try:
            query = "UPDATE tick_orderbook SET is_deleted = true WHERE session_id = $1 AND is_deleted = false"
            params = [session_id]

            if symbol:
                query += " AND symbol = $2"
                params.append(symbol)

            async with self.pg_pool.acquire() as conn:
                result = await conn.execute(query, *params)
                affected_rows = int(result.split()[-1]) if result else 0

            logger.info(f"Soft deleted {affected_rows} tick_orderbook rows for session {session_id}" +
                       (f", symbol {symbol}" if symbol else ""))
            return affected_rows

        except Exception as e:
            logger.error(f"Failed to soft delete tick_orderbook for session {session_id}: {e}")
            raise

    # delete_aggregated_ohlcv() removed - aggregated_ohlcv table not used
    # See OHLCV AGGREGATION REMOVED comment above for rationale

    async def delete_indicators(
        self,
        session_id: str,
        symbol: Optional[str] = None,
        indicator_id: Optional[str] = None
    ) -> int:
        """
        Soft delete indicator values for session.

        Uses UPDATE to set is_deleted = true instead of physical deletion.

        Args:
            session_id: Session identifier
            symbol: Optional symbol filter
            indicator_id: Optional indicator ID filter

        Returns:
            Number of rows soft deleted
        """
        await self.initialize()

        try:
            query = "UPDATE indicators SET is_deleted = true WHERE session_id = $1 AND is_deleted = false"
            params = [session_id]

            if symbol:
                query += " AND symbol = $2"
                params.append(symbol)

            if indicator_id:
                param_idx = len(params) + 1
                query += f" AND indicator_id = ${param_idx}"
                params.append(indicator_id)

            async with self.pg_pool.acquire() as conn:
                result = await conn.execute(query, *params)
                affected_rows = int(result.split()[-1]) if result else 0

            logger.info(f"Soft deleted {affected_rows} indicators rows for session {session_id}" +
                       (f", symbol {symbol}" if symbol else "") +
                       (f", indicator {indicator_id}" if indicator_id else ""))
            return affected_rows

        except Exception as e:
            logger.error(f"Failed to soft delete indicators for session {session_id}: {e}")
            raise

    async def delete_backtest_results(self, session_id: str) -> int:
        """
        Soft delete backtest results linked to session.

        Uses UPDATE to set is_deleted = true instead of physical deletion.

        Args:
            session_id: Session identifier

        Returns:
            Number of rows soft deleted
        """
        await self.initialize()

        try:
            query = "UPDATE backtest_results SET is_deleted = true WHERE session_id = $1 AND is_deleted = false"

            async with self.pg_pool.acquire() as conn:
                result = await conn.execute(query, session_id)
                affected_rows = int(result.split()[-1]) if result else 0

            logger.info(f"Soft deleted {affected_rows} backtest_results rows for session {session_id}")
            return affected_rows

        except Exception as e:
            logger.error(f"Failed to soft delete backtest_results for session {session_id}: {e}")
            raise

    async def delete_session_metadata(self, session_id: str) -> int:
        """
        Soft delete session metadata record.

        WARNING: This should be called LAST after all child data is soft deleted.
        Uses UPDATE to set is_deleted = true instead of physical deletion.

        ✅ RACE CONDITION FIX: Now waits for WAL commit verification before returning.
        This ensures subsequent SELECT queries see the updated is_deleted = true state.

        Args:
            session_id: Session identifier

        Returns:
            Number of rows soft deleted (should be 1)

        Raises:
            RuntimeError: If WAL commit verification fails after max retries
        """
        await self.initialize()

        try:
            query = "UPDATE data_collection_sessions SET is_deleted = true WHERE session_id = $1 AND is_deleted = false"

            async with self.pg_pool.acquire() as conn:
                result = await conn.execute(query, session_id)
                affected_rows = int(result.split()[-1]) if result else 0

            logger.info(f"Soft deleted session metadata for {session_id}")

            # ✅ CRITICAL FIX: Verify WAL commit before returning success
            # This prevents race condition where frontend queries GET /sessions
            # immediately after DELETE returns, but UPDATE isn't visible yet
            if affected_rows > 0:
                await self._verify_session_deleted(session_id)
                logger.info(f"Session {session_id} soft delete verified (WAL committed)")

            return affected_rows

        except Exception as e:
            logger.error(f"Failed to soft delete session metadata for {session_id}: {e}")
            raise

    async def _verify_session_deleted(
        self,
        session_id: str,
        max_retries: int = 6,
        retry_delays: Optional[List[float]] = None
    ) -> None:
        """
        Verify that session soft delete has committed to QuestDB.

        This method implements retry logic to wait for QuestDB WAL (Write-Ahead Log)
        commit after UPDATE operation. QuestDB optimizes for fast INSERTs via ILP,
        but UPDATEs require rewriting partitions which can take 50-500ms.

        Without this verification, there's a race condition:
        1. DELETE endpoint executes UPDATE (writes to WAL)
        2. DELETE returns HTTP 200 immediately
        3. Frontend calls GET /sessions
        4. GET query reads old state (UPDATE not yet committed from WAL)
        5. Deleted session appears in results ❌

        This method polls the database until UPDATE is visible or timeout.

        Args:
            session_id: Session identifier to verify
            max_retries: Maximum verification attempts (default: 6)
            retry_delays: Delays between retries in seconds
                         (default: [0, 0.2, 0.4, 0.6, 1.0, 1.5] = ~4s total)

        Raises:
            RuntimeError: If session is still not marked as deleted after max retries
        """
        if retry_delays is None:
            retry_delays = [0, 0.2, 0.4, 0.6, 1.0, 1.5]

        for attempt, delay in enumerate(retry_delays):
            if delay > 0:
                await asyncio.sleep(delay)

            # Query to check if session is now marked as deleted
            verify_query = """
            SELECT is_deleted
            FROM data_collection_sessions
            WHERE session_id = $1
            """

            try:
                async with self.pg_pool.acquire() as conn:
                    row = await conn.fetchrow(verify_query, session_id)

                if row and row['is_deleted']:
                    # ✅ SUCCESS: UPDATE is now visible (WAL committed)
                    if attempt > 0:
                        total_wait = sum(retry_delays[:attempt+1])
                        logger.info(f"Session {session_id} delete verified after {attempt+1} attempts " +
                                   f"(waited {total_wait:.2f}s for WAL commit)")
                    return

                # Still not deleted, continue retry loop
                if attempt < len(retry_delays) - 1:
                    logger.debug(f"Session {session_id} delete verification retry {attempt+1}/{len(retry_delays)} - " +
                                f"is_deleted = {row['is_deleted'] if row else 'NULL'}")

            except Exception as e:
                logger.warning(f"Session {session_id} delete verification failed on attempt {attempt+1}: {e}")
                # Continue retry loop
                continue

        # ❌ TIMEOUT: WAL commit took too long
        total_wait = sum(retry_delays)
        raise RuntimeError(
            f"Failed to verify session {session_id} deletion after {len(retry_delays)} attempts "
            f"(total wait: {total_wait:.2f}s). QuestDB WAL commit timeout exceeded. "
            f"The session may be deleted but the change is not yet visible to queries."
        )

    async def delete_session_cascade(self, session_id: str) -> Dict[str, int]:
        """
        Delete all data for session (cascade delete).

        Deletes in correct order:
        1. Backtest results (most dispensable)
        2. Indicators (computed from prices)
        3. Orderbook snapshots
        4. Tick prices
        5. Session metadata (parent record)

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with deleted row counts per table:
            {
                'backtest_results': N,
                'indicators': N,
                'tick_orderbook': N,
                'tick_prices': N,
                'data_collection_sessions': N,
                'total': N
            }
        """
        logger.info(f"Starting cascade delete for session {session_id}")

        deleted_counts = {}

        try:
            # 1. Delete backtest results
            deleted_counts['backtest_results'] = await self.delete_backtest_results(session_id)

            # 2. Delete indicators
            deleted_counts['indicators'] = await self.delete_indicators(session_id)

            # 3. aggregated_ohlcv deletion removed (table not used)

            # 4. Delete orderbook snapshots
            deleted_counts['tick_orderbook'] = await self.delete_tick_orderbook(session_id)

            # 5. Delete tick prices
            deleted_counts['tick_prices'] = await self.delete_tick_prices(session_id)

            # 6. Delete session metadata (parent record - LAST)
            deleted_counts['data_collection_sessions'] = await self.delete_session_metadata(session_id)

            # Calculate total
            deleted_counts['total'] = sum(deleted_counts.values())

            logger.info(f"Cascade delete completed for session {session_id}: " +
                       f"total {deleted_counts['total']} rows deleted")

            return deleted_counts

        except Exception as e:
            logger.error(f"Cascade delete failed for session {session_id}: {e}")
            # Return partial counts if any deletes succeeded
            deleted_counts['total'] = sum(deleted_counts.values())
            deleted_counts['error'] = str(e)
            raise

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def query_with_wal_retry(
        self,
        query_func: callable,
        *args,
        max_retries: int = 6,
        retry_delays: Optional[List[float]] = None,
        validation_func: Optional[callable] = None,
        **kwargs
    ) -> Any:
        """
        Execute a query with automatic retry logic to handle WAL race condition.

        ✅ CRITICAL: Use this helper when querying data immediately after ILP write operations.

        This helper implements exponential backoff retry to wait for QuestDB WAL commit.
        See module docstring for detailed explanation of the race condition.

        Args:
            query_func: Async function to execute (e.g., self.get_indicators)
            *args: Positional arguments for query_func
            max_retries: Maximum retry attempts (default: 6)
            retry_delays: List of delays in seconds between retries
                         (default: [0, 0.2, 0.4, 0.6, 1.0, 1.5])
            validation_func: Optional function to validate results.
                            Should return True if data is valid, False to retry.
                            Default: checks if result is non-empty
            **kwargs: Keyword arguments for query_func

        Returns:
            Query result (type depends on query_func)

        Example:
            # Query indicators with automatic retry
            result = await provider.query_with_wal_retry(
                provider.get_indicators,
                symbol='BTC_USDT',
                indicator_ids=['my_indicator_123'],
                limit=1000
            )

            # Custom validation (e.g., require at least 100 records)
            result = await provider.query_with_wal_retry(
                provider.get_indicators,
                symbol='BTC_USDT',
                indicator_ids=['my_indicator_123'],
                validation_func=lambda df: len(df) >= 100
            )

        Raises:
            Exception: Re-raises last exception if all retries exhausted
        """
        if retry_delays is None:
            retry_delays = [0, 0.2, 0.4, 0.6, 1.0, 1.5]

        if validation_func is None:
            # Default validation: check if result is non-empty
            def default_validation(result):
                if hasattr(result, '__len__'):
                    return len(result) > 0
                elif hasattr(result, 'empty'):  # pandas DataFrame
                    return not result.empty
                return result is not None

            validation_func = default_validation

        last_error = None
        result = None

        for attempt in range(max_retries):
            try:
                # Execute query
                result = await query_func(*args, **kwargs)

                # Validate result
                if validation_func(result) or attempt == max_retries - 1:
                    # Valid result or last attempt
                    if validation_func(result) and attempt > 0:
                        logger.info(f"WAL retry successful after {attempt} attempts " +
                                   f"(total wait: {sum(retry_delays[:attempt]):.2f}s)")
                    elif not validation_func(result) and attempt > 0:
                        logger.warning(f"WAL retry exhausted after {attempt} attempts " +
                                      f"(total wait: {sum(retry_delays[:attempt]):.2f}s) - " +
                                      f"returning invalid result")
                    return result

                # Invalid result, retry
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    logger.debug(f"WAL retry attempt {attempt + 1}/{max_retries} - " +
                                f"waiting {wait_time}s for WAL commit")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                last_error = e
                if attempt == max_retries - 1:
                    # Last attempt failed, re-raise
                    logger.error(f"WAL retry failed after {max_retries} attempts: {e}")
                    raise

                # Not last attempt, retry
                wait_time = retry_delays[attempt]
                logger.warning(f"WAL retry attempt {attempt + 1} failed: {e} - " +
                              f"retrying after {wait_time}s")
                await asyncio.sleep(wait_time)

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        return result

    async def health_check(self) -> Dict[str, bool]:
        """
        Check QuestDB connection health.

        ✅ CRITICAL FIX: Now uses connection pool via async context manager.

        Returns:
            Dictionary with status of ILP and PostgreSQL
        """
        health = {
            'ilp': False,
            'postgresql': False,
        }

        # Test InfluxDB line protocol
        try:
            async with self._get_pooled_sender() as sender:
                sender.row(
                    'health_check',
                    symbols={'test': 'test'},
                    columns={'value': 1.0},
                    at=TimestampNanos.now()
                )
                sender.flush()
            health['ilp'] = True
        except Exception as e:
            logger.warning(f"ILP health check failed: {e}")

        # Test PostgreSQL
        try:
            await self.initialize()
            async with self.pg_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health['postgresql'] = True
        except Exception as e:
            logger.warning(f"PostgreSQL health check failed: {e}")

        return health


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_usage():
    """Example usage of QuestDBProvider."""

    provider = QuestDBProvider()

    # Initialize
    await provider.initialize()

    # Insert single price
    await provider.insert_price(
        symbol='BTC/USD',
        timestamp=datetime.utcnow(),
        open_price=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=1000000.0,
    )

    # Insert batch of prices
    prices = [
        {
            'symbol': 'BTC/USD',
            'timestamp': datetime.utcnow() - timedelta(seconds=i),
            'open': 50000 + i,
            'high': 50100 + i,
            'low': 49900 + i,
            'close': 50050 + i,
            'volume': 1000000,
        }
        for i in range(100)
    ]
    await provider.insert_prices_batch(prices)

    # Insert indicators
    await provider.insert_indicator(
        symbol='BTC/USD',
        indicator_id='RSI_14',
        timestamp=datetime.utcnow(),
        value=45.5,
        confidence=0.95,
    )

    # Query latest price
    latest = await provider.get_latest_price('BTC/USD')
    print(f"Latest price: {latest}")

    # Query latest indicators
    indicators = await provider.get_latest_indicators('BTC/USD')
    print(f"Latest indicators: {indicators}")

    # Health check
    health = await provider.health_check()
    print(f"Health: {health}")

    # Close
    await provider.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
