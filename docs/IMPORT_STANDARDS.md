# Import Standards - FX_code_AI Project

**Version**: 1.0
**Date**: 2025-10-28
**Status**: Official Standard

---

## Executive Summary

This document establishes official import standards for the FX_code_AI codebase to ensure consistency, maintainability, and avoid common pitfalls.

**Key Principles**:
1. **Prefer absolute imports** for cross-package imports
2. **Use relative imports** only within the same package
3. **Never mask import errors** with try-except (unless solving circular imports)
4. **Import from types/models** modules to avoid circular dependencies

---

## 1. Absolute vs Relative Imports

### When to Use Absolute Imports

**Use absolute imports for**:
- Cross-package imports (importing from different top-level packages)
- Importing from `src.core.*` modules (shared utilities)
- Importing from `src.domain.types.*` (shared types)
- Any import that crosses architectural boundaries

**Example** (✅ CORRECT):
```python
# File: src/domain/services/indicators/algorithm_registry.py
from src.core.logger import get_logger
from src.domain.types.indicator_types import IndicatorValue
```

**Why**: Absolute imports are:
- More readable (clear where import comes from)
- More maintainable (moving files doesn't break imports)
- Less error-prone (no need to count directory levels)
- PEP 8 recommended for cross-package imports

---

### When to Use Relative Imports

**Use relative imports for**:
- Importing from sibling modules in the same package
- Importing from parent package (only 1-2 levels up)

**Example** (✅ CORRECT):
```python
# File: src/domain/services/indicators/momentum_reversal_index.py
from .base_algorithm import MultiWindowIndicatorAlgorithm  # Sibling module
from .window_calculations import compute_time_weighted_average  # Sibling module
```

**Why**: Relative imports are:
- Concise for same-package imports
- Make package structure clear
- Easier to refactor entire packages

---

### Calculating Relative Import Levels

**Rule**: Number of dots = Directory levels to go up to reach the target

**Example**:
```
src/infrastructure/factories/position_management_factory.py (3 levels deep)
│
├─ from ...core.logger import ...
   └─ ... = 3 levels up (factories/ → infrastructure/ → src/)
   └─ Then down to core/logger
   └─ Result: src/core/logger ✅ CORRECT
```

**Common Mistakes**:
```python
# ❌ WRONG: Not enough dots
# File at src/domain/services/indicators/file.py (4 levels)
from ...core.logger import ...  # Only goes up 3 levels → src/domain/core (doesn't exist!)

# ✅ CORRECT: Use absolute import instead
from src.core.logger import ...
```

---

## 2. Import Style by Module Type

### Core Modules (`src/core/*`)

**Core modules should be imported with absolute imports from everywhere**:

```python
# ✅ CORRECT - Absolute import (preferred)
from src.core.logger import get_logger, StructuredLogger
from src.core.event_bus import EventBus
from src.core.config import ConfigLoader

# ⚠️ ACCEPTABLE - Relative import (only from nearby modules)
# File: src/infrastructure/container.py (2 levels deep)
from ..core.logger import StructuredLogger

# ❌ WRONG - Inconsistent style
from src.core.logger import get_logger
from ..core.event_bus import EventBus  # Mix of absolute and relative
```

**Recommendation**: Standardize on absolute imports for `src.core.*` throughout the project.

---

### Domain Types (`src/domain/types/*`)

**Type modules should always be imported absolutely**:

```python
# ✅ CORRECT
from src.domain.types.indicator_types import IndicatorValue, MarketDataPoint
from src.domain.types.order_types import OrderType, OrderStatus

# ❌ WRONG - Relative import for shared types
from ...types.indicator_types import IndicatorValue  # Hard to read, error-prone
```

**Why**: Types are shared across many modules. Absolute imports make dependencies explicit.

---

### API Routes (`src/api/*`)

**API modules should use absolute imports** for everything except response models:

```python
# File: src/api/indicators_routes.py

# ✅ CORRECT - Absolute imports for services
from src.core.logger import get_logger
from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine
from src.data.questdb_data_provider import QuestDBDataProvider

# ✅ ACCEPTABLE - Relative import for same package
from .response_envelope import ensure_envelope
```

---

### Algorithm Modules (`src/domain/services/indicators/*`)

**Algorithm modules should**:
- Use relative imports for base classes (same package)
- Use absolute imports for types and utilities

```python
# File: src/domain/services/indicators/momentum_reversal_index.py

# ✅ CORRECT - Relative for sibling modules
from .base_algorithm import MultiWindowIndicatorAlgorithm
from .window_calculations import compute_time_weighted_average

# ✅ CORRECT - Absolute for shared types
from src.domain.types.indicator_types import IndicatorValue

# ❌ WRONG - Try-except to hide import errors (unless circular import)
try:
    from ..streaming_indicator_engine import VariantParameter
except ImportError:
    pass  # Don't mask errors!
```

---

## 3. Anti-Patterns to Avoid

### Anti-Pattern #1: Masking Import Errors

**❌ WRONG**:
```python
try:
    from ...core.logger import StructuredLogger
except ImportError:
    import logging
    StructuredLogger = logging.getLogger  # Masks the real problem!
```

**Why this is bad**:
- Hides broken imports
- Makes debugging difficult
- Creates inconsistent behavior
- Violates "errors should never pass silently"

**✅ CORRECT - Fix the import**:
```python
from src.core.logger import StructuredLogger  # Explicit import, will fail fast if broken
```

**✅ ACCEPTABLE - Only for circular imports**:
```python
# Only use try-except when solving circular import problems
# AND document why it's needed
try:
    from ..streaming_indicator_engine import VariantParameter
except ImportError:
    # Circular import: engine imports algorithms, algorithms import engine types
    # TODO: Move VariantParameter to src/domain/types/indicator_types.py
    from typing import NamedTuple
    class VariantParameter(NamedTuple):
        ...  # Fallback definition
```

---

### Anti-Pattern #2: Mixing Import Styles

**❌ WRONG**:
```python
from src.core.logger import get_logger
from ..core.event_bus import EventBus  # Mixed absolute/relative
from ...core.config import ConfigLoader
```

**✅ CORRECT**:
```python
# Choose one style per file (prefer absolute for core modules)
from src.core.logger import get_logger
from src.core.event_bus import EventBus
from src.core.config import ConfigLoader
```

---

### Anti-Pattern #3: Deep Relative Imports

**❌ WRONG**:
```python
# File at src/domain/services/indicators/algorithms/file.py (5 levels deep)
from .....core.logger import get_logger  # Too many dots, hard to read
```

**✅ CORRECT**:
```python
from src.core.logger import get_logger  # Clear and explicit
```

**Rule**: If you need more than 3 dots (`...`), use absolute import instead.

---

## 4. Solving Circular Import Problems

### Strategy 1: Move Shared Types to `types/` Module

**Problem**:
```
module_a.py imports from module_b.py
module_b.py imports from module_a.py
→ Circular import!
```

**Solution**: Extract shared types to a separate module

**Before**:
```
src/domain/services/
├─ streaming_indicator_engine.py  (defines VariantParameter, imports algorithms)
└─ indicators/
   └─ algorithm.py  (needs VariantParameter, creates circular import)
```

**After**:
```
src/domain/types/
└─ indicator_types.py  (defines VariantParameter)

src/domain/services/
├─ streaming_indicator_engine.py  (imports VariantParameter from types)
└─ indicators/
   └─ algorithm.py  (imports VariantParameter from types)
```

---

### Strategy 2: Lazy Imports (Last Resort)

**Only use if Strategy 1 is not feasible**:

```python
def get_indicator_metadata():
    # Import inside function to break circular dependency
    from src.domain.services.streaming_indicator_engine import VariantParameter
    return VariantParameter(...)
```

**When to use**: Only when refactoring module structure is too risky.

---

## 5. Import Order Standards

**Follow PEP 8 import order**:

```python
# 1. Standard library imports
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 2. Third-party library imports
import pandas as pd
from fastapi import APIRouter

# 3. Local application imports (absolute)
from src.core.logger import get_logger
from src.domain.types.indicator_types import IndicatorValue

# 4. Local application imports (relative) - same package only
from .base_algorithm import IndicatorAlgorithm
from .utils import compute_average
```

**Tools**: Use `isort` to automatically sort imports:
```bash
isort src/
```

---

## 6. Migration Guide

### Migrating from Relative to Absolute Imports

**Step 1**: Identify current import
```python
from ...core.logger import get_logger
```

**Step 2**: Calculate absolute path
- File location: `src/domain/services/indicators/file.py`
- Current import: `...core.logger` (3 levels up → `src/`, then `core/logger`)
- Absolute path: `src.core.logger`

**Step 3**: Replace
```python
from src.core.logger import get_logger
```

**Step 4**: Test
```bash
python -m pytest tests/
```

---

### Fixing "No module named" Errors

**Error Example**:
```
ModuleNotFoundError: No module named 'src.domain.core'
```

**Diagnosis**:
1. Check file location: `src/domain/services/indicators/file.py` (4 levels deep)
2. Check import: `from ...core.logger import ...` (only 3 dots)
3. Problem: Need 4 dots to reach `src/`, or use absolute import

**Solution**:
```python
# Option A: Use absolute import (recommended)
from src.core.logger import get_logger

# Option B: Add correct number of dots (not recommended, harder to maintain)
from ....core.logger import get_logger
```

---

## 7. Linting Configuration

### pylint Configuration

**File**: `.pylintrc`

```ini
[MASTER]
# Add src to Python path for absolute imports
init-hook='import sys; sys.path.append("src")'

[IMPORTS]
# Prefer absolute imports
preferred-modules=src.core:core,src.domain:domain

# Warn on relative imports that go up more than 2 levels
max-relative-import-depth=2

# Report mixed import styles in same file
analyse-fallback-blocks=yes
```

### flake8 Configuration

**File**: `.flake8`

```ini
[flake8]
# Allow absolute imports from src
import-order-style = google
application-import-names = src
```

### isort Configuration

**File**: `.isort.cfg` or `pyproject.toml`

```ini
[tool.isort]
profile = "black"
src_paths = ["src"]
known_first_party = ["src"]
sections = ["FUTURE", "STDLIB", "THIRDPARTY", "FIRSTPARTY", "LOCALFOLDER"]
```

---

## 8. Quick Reference

### Import Decision Tree

```
Need to import something?
│
├─ From same package (sibling module)?
│  └─ Use relative import: from .module import X
│
├─ From src.core.* or src.domain.types.*?
│  └─ Use absolute import: from src.core.module import X
│
├─ From different package?
│  └─ Use absolute import: from src.package.module import X
│
└─ Getting ImportError?
   ├─ Circular import?
   │  └─ Refactor: Move shared types to types/ module
   └─ Wrong path?
      └─ Use absolute import: from src.core.module import X
```

---

### Common Imports Cheat Sheet

```python
# Logging
from src.core.logger import get_logger, StructuredLogger

# Configuration
from src.infrastructure.config.config_loader import get_settings_from_working_directory

# Event Bus
from src.core.event_bus import EventBus, EventPriority

# Indicator Types
from src.domain.types.indicator_types import (
    IndicatorValue,
    MarketDataPoint,
    IndicatorConfig
)

# QuestDB
from src.data_feed.questdb_provider import QuestDBProvider
from src.data.questdb_data_provider import QuestDBDataProvider
```

---

## 9. Code Review Checklist

When reviewing imports in pull requests, check:

- [ ] All imports from `src.core.*` use consistent style (prefer absolute)
- [ ] No try-except around imports (unless documented circular import)
- [ ] No relative imports with more than 3 dots (`...`)
- [ ] Import order follows PEP 8 (stdlib → third-party → local)
- [ ] No unused imports
- [ ] No `import *` (except in `__init__.py` for re-exports)
- [ ] Types imported from `src.domain.types.*` not from implementation modules

---

## 10. FAQ

### Q: Why prefer absolute imports over relative?

**A**: Absolute imports are:
- More readable (clear where the import comes from)
- More maintainable (moving files doesn't break imports)
- Less error-prone (no need to count directory levels)
- PEP 8 recommended for cross-package imports

### Q: When should I use relative imports?

**A**: Only for importing from sibling modules in the same package. Example:
```python
# File: src/domain/services/indicators/momentum.py
from .base_algorithm import IndicatorAlgorithm  # Same package, OK
from .utils import helper_function  # Same package, OK
```

### Q: What if I get a circular import error?

**A**:
1. **Best solution**: Move shared types to `src/domain/types/`
2. **Alternative**: Use lazy imports (import inside function)
3. **Last resort**: Use try-except with clear documentation of why

### Q: Can I use `from module import *`?

**A**: Only in `__init__.py` files for package re-exports. Never in regular modules.

### Q: How do I run import checks automatically?

**A**:
```bash
# Check import order
isort --check-only src/

# Check import style
pylint --disable=all --enable=import-error,relative-import src/

# Check for unused imports
flake8 --select=F401 src/
```

---

## 11. Examples from Codebase

### Example 1: API Route (Good)

```python
# File: src/api/indicators_routes.py

# Standard library
import json
import math
from typing import List, Dict, Any, Optional

# Third-party
from fastapi import APIRouter, HTTPException

# Absolute imports for services (✅ GOOD)
from src.core.logger import get_logger
from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine
from src.data_feed.questdb_provider import QuestDBProvider

# Relative import for same package (✅ GOOD)
from .response_envelope import ensure_envelope
```

### Example 2: Algorithm (Before Fix)

```python
# File: src/domain/services/indicators/momentum_reversal_index.py

# ❌ BAD: Try-except masking import error
try:
    from ..streaming_indicator_engine import VariantParameter
except ImportError:
    from typing import NamedTuple
    class VariantParameter(NamedTuple):
        ...  # Duplicate definition
```

### Example 3: Algorithm (After Fix)

```python
# File: src/domain/services/indicators/momentum_reversal_index.py

# ✅ GOOD: Import from types module (breaks circular dependency)
from src.domain.types.indicator_types import VariantParameter

# ✅ GOOD: Relative import for sibling modules
from .base_algorithm import MultiWindowIndicatorAlgorithm
```

---

## 12. Future Improvements

### Short-term (Next Sprint)
- [ ] Add pre-commit hook to check import style
- [ ] Run `isort` on entire codebase
- [ ] Add import checks to CI/CD pipeline

### Medium-term (Next Quarter)
- [ ] Refactor `VariantParameter` to `src/domain/types/indicator_types.py`
- [ ] Remove all try-except import anti-patterns
- [ ] Standardize all `src.core.*` imports to absolute style

### Long-term (Next Year)
- [ ] Reduce maximum directory nesting to 3 levels
- [ ] Create import style guide training for new developers
- [ ] Automate import style fixes in IDE settings

---

## 13. Related Documentation

- [PEP 8 - Import Guidelines](https://pep8.org/#imports)
- [Python Import System](https://docs.python.org/3/reference/import.html)
- [Google Python Style Guide - Imports](https://google.github.io/styleguide/pyguide.html#22-imports)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-28
**Maintained By**: Development Team
**Review Cycle**: Quarterly
