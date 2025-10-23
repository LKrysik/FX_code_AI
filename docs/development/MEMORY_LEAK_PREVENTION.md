# Memory Leak Prevention - Patterns and Monitoring

## 🎯 OBJECTIVE

Prevent memory leaks in long-running app with simple patterns.

## 🛡️ PATTERNS

- **No defaultdict**: Use dict with checks.
- **Weak References**: For handlers.
- **Bounded Structures**: Add max sizes/TTLs to all dicts and queues.
- **Deque for Windows**: Fixed-size.
- **Cleanup**: Use context managers.

## 📊 MONITORING

- Log usage regularly.
- Alert on high usage.

## 🚀 EXAMPLE

```python
from collections import deque

class BoundedCache:
    def __init__(self, max_size: int):
        self.cache = {}
        self.max_size = max_size

    def add(self, key, value):
        if len(self.cache) >= self.max_size:
            # Evict oldest
            del self.cache[next(iter(self.cache))]
        self.cache[key] = value
```

Always bound collections.