# Circuit Breaker Integration in MEXC Futures Adapter - TIER 2.2

## Overview

The MEXC Futures Adapter (`src/infrastructure/adapters/mexc_futures_adapter.py`) inherits circuit breaker protection from its parent class `MexcRealAdapter`. This document explains the integration, usage patterns, and best practices.

## How It Works

### Automatic Protection

All API calls through `_make_request()` are automatically protected by:

1. **Circuit Breaker** - Opens after 5 consecutive failures, prevents cascading failures
2. **Retry Logic** - 3 attempts with exponential backoff (1s → 2s → 4s)
3. **Timeout Protection** - 30s timeout per request
4. **Rate Limiting** - 100 requests/second for futures API

### States

- **CLOSED** (Normal): All requests pass through
- **OPEN** (Failing): Requests rejected immediately, service recovering
- **HALF_OPEN** (Testing): Limited requests allowed to test recovery

## Usage Examples

### Basic Usage (Automatic Protection)

```python
async with MexcFuturesAdapter(api_key, api_secret, logger) as adapter:
    # All calls are automatically protected
    order = await adapter.place_futures_order(
        symbol="BTC_USDT",
        side="SELL",
        position_side="SHORT",
        order_type="MARKET",
        quantity=0.001
    )
    # Automatic retry on failure (3 attempts)
    # Circuit breaker opens after 5 consecutive failures
```

### Monitoring Circuit Breaker

```python
# Get detailed metrics
metrics = adapter.get_circuit_breaker_metrics()
print(f"State: {metrics['circuit_breaker']['state']}")
print(f"Success rate: {metrics['circuit_breaker']['metrics']['success_rate_percent']}%")
print(f"Failed requests: {metrics['circuit_breaker']['metrics']['failed_requests']}")
print(f"Rejected requests: {metrics['circuit_breaker']['metrics']['rejected_requests']}")

# Check health
if adapter.is_circuit_breaker_healthy():
    print("Circuit breaker is healthy (CLOSED or HALF_OPEN)")
else:
    print("Circuit breaker is OPEN - API calls will be rejected")

# Get current state
state = adapter.get_circuit_breaker_state()  # 'closed', 'open', 'half_open', or 'unknown'
```

### Using Fallback Methods

For non-critical operations, use `_with_fallback` methods to gracefully degrade:

```python
# Get leverage with fallback (never throws exception)
leverage = await adapter.get_leverage_with_fallback("BTC_USDT", default_leverage=3)
# Returns: API value → cached value → default value (3)

# Get funding rate with fallback (returns zero on failure)
funding = await adapter.get_funding_rate_with_fallback("BTC_USDT")
# Returns: API data → fallback data (funding_rate=0.0)
```

### Logging Circuit Breaker Status

```python
# Log detailed status for debugging
adapter.log_circuit_breaker_status()

# Output example:
# INFO: mexc_futures_adapter.circuit_breaker_status {
#   "state": "closed",
#   "success_rate_percent": 98.5,
#   "total_requests": 1234,
#   "failed_requests": 18,
#   "rejected_requests": 0,
#   "consecutive_failures": 0,
#   "state_changes": 2
# }
```

## Best Practices

### 1. Check Circuit Breaker Before Non-Essential Operations

```python
if adapter.is_circuit_breaker_healthy():
    # Proceed with operation
    funding = await adapter.get_funding_rate("BTC_USDT")
else:
    # Skip or use fallback
    logger.warning("Circuit breaker is OPEN - skipping funding rate query")
    funding = {"funding_rate": 0.0}  # Use default
```

### 2. Use Fallback Methods for Non-Critical Data

```python
# GOOD: Always returns a value
leverage = await adapter.get_leverage_with_fallback("BTC_USDT", default_leverage=1)

# AVOID: Throws exception when circuit breaker is open
try:
    leverage = await adapter.get_leverage("BTC_USDT")
except Exception:
    leverage = 1  # Manual fallback
```

### 3. Monitor Circuit Breaker in Production

```python
# Periodic health check (e.g., every 60 seconds)
async def monitor_circuit_breaker():
    while True:
        metrics = adapter.get_circuit_breaker_metrics()
        state = metrics['circuit_breaker']['state']

        if state == 'open':
            logger.error("Circuit breaker is OPEN - MEXC API degraded")
            # Alert operations team
        elif state == 'half_open':
            logger.warning("Circuit breaker is HALF_OPEN - testing recovery")

        await asyncio.sleep(60)
```

### 4. Handle Circuit Breaker Exceptions

```python
from src.core.circuit_breaker import CircuitBreakerOpenException

try:
    order = await adapter.place_futures_order(...)
except CircuitBreakerOpenException:
    logger.error("Circuit breaker is OPEN - order rejected without API call")
    # Don't retry - circuit breaker prevents cascading failures
    # Wait for automatic recovery (60s) or use fallback strategy
except Exception as e:
    logger.error(f"Order placement failed: {e}")
    # Other exceptions can be retried
```

## Configuration

Circuit breaker configuration is set in `MexcRealAdapter`:

```python
circuit_config = CircuitBreakerConfig(
    name="mexc_api",
    failure_threshold=5,        # Open after 5 failures
    recovery_timeout=60.0,      # Try recovery after 60s
    timeout=30.0,               # 30s request timeout
    success_threshold=3,        # 3 successes to close in half-open
)

retry_config = RetryConfig(
    name="mexc_api",
    max_attempts=3,             # Retry 3 times
    initial_delay=1.0,          # Start with 1s delay
    backoff_factor=2.0,         # Double delay each retry (1s → 2s → 4s)
    jitter=True,                # Add random jitter to prevent thundering herd
)
```

## Metrics Explained

### State Metrics
- `total_requests`: Total API calls attempted
- `successful_requests`: Calls that succeeded
- `failed_requests`: Calls that failed and counted toward threshold
- `rejected_requests`: Calls rejected when circuit breaker was OPEN

### Health Indicators
- `success_rate_percent`: % of successful requests (healthy > 95%)
- `consecutive_failures`: Current failure streak (opens at 5)
- `consecutive_successes`: Current success streak in HALF_OPEN (closes at 3)
- `state_changes`: Number of state transitions (frequent changes = unstable API)

### Timestamps
- `last_failure_time`: Unix timestamp of last failure
- `last_success_time`: Unix timestamp of last success
- `time_since_last_failure`: Seconds since last failure
- `time_since_last_success`: Seconds since last success

## Troubleshooting

### Circuit Breaker Stuck OPEN

**Symptoms**: All API calls rejected, state remains 'open'

**Causes**:
- MEXC API is down or rate-limited
- Network connectivity issues
- Invalid API credentials

**Solutions**:
1. Check MEXC API status: https://www.mexc.com/support/articles/360051845953
2. Verify network connectivity
3. Wait for automatic recovery (60s timeout)
4. Check API key permissions and validity

### High Rejection Rate

**Symptoms**: `rejected_requests` increasing rapidly

**Causes**:
- Circuit breaker opening frequently due to unstable API
- Application making too many requests during degradation

**Solutions**:
1. Increase `recovery_timeout` (default 60s)
2. Implement backoff at application level
3. Use fallback methods (`_with_fallback`) for non-critical operations
4. Reduce request frequency when circuit breaker opens

### Frequent State Changes

**Symptoms**: `state_changes` > 10 within short period

**Causes**:
- Intermittent API issues (flapping)
- Threshold too sensitive for workload

**Solutions**:
1. Increase `failure_threshold` (default 5)
2. Increase `success_threshold` (default 3)
3. Implement exponential backoff at application level

## Related Files

- `src/core/circuit_breaker.py` - Circuit breaker implementation
- `src/infrastructure/adapters/mexc_adapter.py` - Parent class with circuit breaker integration
- `src/infrastructure/adapters/mexc_futures_adapter.py` - Futures adapter with fallback methods

## Performance Impact

- **Overhead**: < 1ms per request (negligible)
- **Memory**: ~1KB per circuit breaker instance
- **Benefits**:
  - Prevents cascading failures
  - Reduces load during API degradation
  - Automatic recovery without manual intervention
  - Graceful degradation with fallback strategies
