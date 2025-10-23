# Error Handling - Robust Patterns

## 🎯 PRINCIPLES

Implement consistent error handling to ensure graceful degradation and detailed logging without crashing the application.

## 🛡️ PATTERNS

- **Custom Exceptions**: Define hierarchy like ExchangeError, ConfigError.
- **Try-Except Blocks**: Catch specific exceptions, log with context.
- **Retries**: Use exponential backoff for transient errors (e.g., network).
- **Fallbacks**: Implement MexcRestFallback for WebSocket failures.
- **Logging**: Use structured JSON logs with error details.

## 📜 EXAMPLE

```python
class ExchangeError(Exception):
    pass

async def fetch_data():
    try:
        # Operation
        pass
    except ExchangeError as e:
        logger.error("exchange.fetch_failed", {"error": str(e)})
        # Fallback or retry
```

## 🚫 AVOID

- Bare except clauses.
- Silent failures.

This ensures reliable operation.