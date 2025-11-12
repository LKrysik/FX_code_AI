# Plan Naprawy Testów - Wieloagentowy Proces

**Data utworzenia**: 2025-11-12
**Status**: PRZYGOTOWANIE
**Cel**: Naprawić 346 niepowodzących się testów (275 errors + 71 failures)

---

## EXECUTIVE SUMMARY - ROOT CAUSES

### Analiza Wyników Testów
- **Total tests**: 493
- **Errors**: 275 (55.8%) - głównie QuestDB connection timeouts
- **Failures**: 71 (14.4%) - błędy logiczne
- **Success rate**: 29.8% (powinno być >95%)
- **Czas wykonania**: ~39 minut (powinno być <2 minuty)

### Główne Przyczyny (Root Causes)

| RC# | Priorytet | Problem | Impact | Tests Affected |
|-----|-----------|---------|--------|----------------|
| RC#1 | CRITICAL | Heavy Fixture Initialization | Każdy test tworzy cały production app | 225 (81.5%) |
| RC#2 | CRITICAL | QuestDB Connection Timeout | 10s timeout × 225 tests = 37.5 min | 225 (81.5%) |
| RC#3 | HIGH | Async/Await Complexity | Race conditions, deadlocks | 10 (3.6%) |
| RC#4 | HIGH | No Mocking/Test Doubles | Tests wymagają działającego QuestDB | 225 (81.5%) |
| RC#5 | MEDIUM | Lock Contention | Nested locks w Container i QuestDB | 6 (2.2%) |
| RC#6 | MEDIUM | Cleanup Fixtures | autouse=True na wszystkich testach | 493 (100%) |

---

## ARCHITECTURE ANALIZY

### Problem: Każdy Test Tworzy Full Production App

```python
# tests_e2e/conftest.py (CURRENT - PROBLEMATIC)
@pytest.fixture(scope="function")
def app():
    return create_unified_app()  # ← FULL PRODUCTION INITIALIZATION!
```

### Co się dzieje podczas każdego testu:

```
Test starts
  → conftest.py app() fixture
    → create_unified_app()
      → lifespan startup (async)
        → Container initialization
          ├── EventBus
          ├── Logger
          ├── Settings
          ├── WebSocketServer → QuestDB connection #1
          ├── UnifiedTradingController
          │   └── StreamingIndicatorEngine
          │       └── IndicatorVariantRepository
          │           └── QuestDBProvider → CONNECTION TIMEOUT ❌ (10s)
          ├── StrategyManager → QuestDB connection #2
          ├── LiveMarketAdapter → QuestDB connection #3
          ├── SessionManager → QuestDB connection #4
          ├── StrategyStorage → QuestDB connection #5
          └── PaperTradingPersistence → QuestDB connection #6
```

**Rezultat**: 225 tests × 10s timeout = **37.5 minutes wasted**

---

## PLAN NAPRAWY - 6 AGENTÓW + KOORDYNATOR

### Organizacja Zespołu

```
KOORDYNATOR (Agent 1)
     │
     ├──→ Agent 2: Fixture Refactoring
     ├──→ Agent 3: Container Mocking
     ├──→ Agent 4: Cleanup Optimization
     ├──→ Agent 5: Test Categorization
     └──→ Agent 6: Code Review & Verification
```

### Workflow

1. **Koordynator** przydziela zadania agentom
2. Agenci pracują **równolegle** (gdzie możliwe)
3. **Koordynator** monitoruje postępy
4. **Agent 6** weryfikuje zmiany przed merge
5. **Koordynator** scala zmiany i uruchamia testy

---

## AGENT 1: KOORDYNATOR

### Rola
- Nadzoruje cały proces naprawy
- Przydziela zadania agentom
- Monitoruje postępy i wykrywa blokery
- Sprawdza spójność zmian między agentami
- Wykrywa problemy architektoniczne
- Scala zmiany i uruchamia testy walidacyjne

### Odpowiedzialności

1. **Pre-Flight Check**
   - Sprawdź czy QuestDB jest uruchomiony
   - Sprawdź historię git dla kluczowych plików
   - Zidentyfikuj potencjalne konflikty między zadaniami agentów

2. **Task Assignment**
   - Priorytetyzuj zadania (CRITICAL → HIGH → MEDIUM)
   - Zidentyfikuj zależności między zadaniami
   - Przydziel zadania agentom z jasnym scope

3. **Progress Monitoring**
   - Sprawdzaj co 5 minut status każdego agenta
   - Wykryj blokery i realokuj zasoby
   - Eskaluj problemy wymagające decyzji użytkownika

4. **Quality Assurance**
   - Weryfikuj czy zmiany są zgodne z architekturą
   - Sprawdź czy nie powstał dead code
   - Sprawdź czy nie powstały backward compatibility hacks
   - Zweryfikuj spójność zmian

5. **Integration & Testing**
   - Scala zmiany od agentów
   - Rozwiąż konflikty merge
   - Uruchom testy: `python run_tests.py --api --fast`
   - Raportuj wyniki

### Metryki Sukcesu
- Wszyscy agenci zakończyli pracę bez blockerów
- Zmiany są spójne i zgodne z architekturą
- Test success rate: >95%
- Test execution time: <2 minuty

---

## AGENT 2: FIXTURE REFACTORING (RC#1, RC#4)

### Zadania

#### 1. Create Lightweight App Fixture
**Cel**: FastAPI app bez heavy initialization

**Pliki do modyfikacji**:
- `tests_e2e/conftest.py`

**Zmiany**:

```python
# tests_e2e/conftest.py

@pytest.fixture(scope="session")
def mock_questdb_provider():
    """Lightweight QuestDB mock - no real database"""
    from unittest.mock import AsyncMock, MagicMock
    from src.data_feed.questdb_provider import QuestDBProvider

    mock = MagicMock(spec=QuestDBProvider)
    mock.initialize = AsyncMock()
    mock.is_healthy = AsyncMock(return_value=True)
    mock.execute_query = AsyncMock(return_value=[])
    mock.fetch_tick_prices = AsyncMock(return_value=[])
    mock.pg_pool = MagicMock()

    return mock


@pytest.fixture(scope="session")
def test_settings():
    """Minimal settings for testing"""
    from src.infrastructure.config.settings import AppSettings

    settings = AppSettings()
    settings.trading.mode = "mock"  # Don't connect to real exchange
    settings.questdb.pg_host = "127.0.0.1"  # Localhost for CI
    settings.questdb.pg_port = 8812

    return settings


@pytest.fixture(scope="function")
def lightweight_container(mock_questdb_provider, test_settings):
    """Container with mocked QuestDB - no database required"""
    from src.infrastructure.container import Container
    from src.core.event_bus import EventBus
    from src.infrastructure.logger import StructuredLogger

    event_bus = EventBus()
    logger = StructuredLogger("Test", test_settings.logging)
    container = Container(test_settings, event_bus, logger)

    # Replace QuestDB provider with mock
    container._singleton_services["questdb_provider"] = mock_questdb_provider

    return container


@pytest.fixture(scope="function")
def lightweight_app(lightweight_container):
    """FastAPI app with mocked dependencies - FAST"""
    from fastapi import FastAPI
    from contextlib import asynccontextmanager

    # Create app WITHOUT lifespan (skip heavy initialization)
    app = FastAPI()
    app.state.container = lightweight_container

    # Register routes (but skip lifespan startup)
    # ... TODO: import and register route handlers ...

    return app


# DEPRECATED: Old heavy fixture
@pytest.fixture(scope="function")
def app():
    """
    DEPRECATED: Use lightweight_app instead.

    This fixture creates a FULL production app with QuestDB connections.
    Only use for integration tests that REQUIRE real database.
    """
    from src.api.unified_server import create_unified_app
    return create_unified_app()
```

**Walidacja**:
- [ ] `lightweight_app` nie wymaga QuestDB
- [ ] Test z `lightweight_app` wykonuje się <100ms
- [ ] Sprawdź git history `conftest.py` - czy były niedawne zmiany?
- [ ] Uzasadnij czemu ta zmiana nie cofnie poprzednich fix'ów

#### 2. Create Test-Specific Mocks

**Pliki do modyfikacji**:
- `tests_e2e/mocks/__init__.py` (nowy plik)
- `tests_e2e/mocks/indicator_engine.py` (nowy plik)
- `tests_e2e/mocks/strategy_manager.py` (nowy plik)

**Zmiany**:

```python
# tests_e2e/mocks/indicator_engine.py

from unittest.mock import AsyncMock, MagicMock
from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine


def create_mock_indicator_engine():
    """Mock StreamingIndicatorEngine - no database"""
    mock = MagicMock(spec=StreamingIndicatorEngine)

    # Mock async methods
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.create_variant = AsyncMock(return_value="variant_id_123")
    mock.get_indicators = AsyncMock(return_value={
        "BTC_USDT": {
            "TWPA_5min": {"value": 50000.0, "timestamp": "2025-11-12T10:00:00Z"}
        }
    })

    return mock
```

**Walidacja**:
- [ ] Mocks mają wszystkie metody używane przez testy
- [ ] Mocks zwracają realistyczne dane
- [ ] Sprawdź czy nie duplikujesz istniejących mocków

#### 3. Update Test Files to Use Lightweight Fixtures

**Pliki do modyfikacji**:
- `tests_e2e/api/test_indicators.py`
- `tests_e2e/api/test_auth.py`
- `tests_e2e/api/test_misc.py`
- ... (wszystkie test_*.py files)

**Przykład**:

```python
# tests_e2e/api/test_indicators.py (BEFORE)
def test_get_indicators_for_symbol(self, api_client):
    """Test GET /api/v1/indicators/{symbol}"""
    response = api_client.get("/api/v1/indicators/BTC_USDT")
    assert response.status_code == 200


# tests_e2e/api/test_indicators.py (AFTER)
@pytest.mark.fast  # New marker
def test_get_indicators_for_symbol(self, lightweight_api_client):
    """Test GET /api/v1/indicators/{symbol}"""
    response = lightweight_api_client.get("/api/v1/indicators/BTC_USDT")
    assert response.status_code == 200
```

**Walidacja**:
- [ ] Testy używają `lightweight_api_client` zamiast `api_client`
- [ ] Testy z markerem `@pytest.mark.fast` wykonują się <100ms
- [ ] Sprawdź git log dla każdego modyfikowanego pliku
- [ ] Uzasadnij czemu zmiana nie złamie innych testów

### Metryki Sukcesu
- [ ] 225 testów nie wymaga już QuestDB
- [ ] Test execution time: <100ms per test (fast tests)
- [ ] Wszystkie testy z `@pytest.mark.fast` przechodzą

### Ryzyka i Mitigacje

| Ryzyko | Prawdopodobieństwo | Mitigacja |
|--------|-------------------|-----------|
| Mocks nie pokrywają wszystkich use cases | Medium | Code review by Agent 6 |
| Testy tracą wartość (testują mocks, nie kod) | High | Agent 5 segreguje unit vs integration |
| Breaking changes w API | Low | Agent 1 sprawdza git history |

---

## AGENT 3: CONTAINER MOCKING (RC#2, RC#3)

### Zadania

#### 1. Create TestContainer Class

**Cel**: Container dla testów bez QuestDB connections

**Pliki do modyfikacji**:
- `tests_e2e/test_container.py` (nowy plik)

**Zmiany**:

```python
# tests_e2e/test_container.py

from src.infrastructure.container import Container
from unittest.mock import AsyncMock, MagicMock


class TestContainer(Container):
    """
    Lightweight Container for testing.

    Overrides expensive factories to return mocks.
    Use for unit tests that don't need real database.
    """

    async def create_questdb_provider(self):
        """Mock QuestDBProvider - no database"""
        from src.data_feed.questdb_provider import QuestDBProvider

        mock = MagicMock(spec=QuestDBProvider)
        mock.initialize = AsyncMock()
        mock.is_healthy = AsyncMock(return_value=True)
        mock.execute_query = AsyncMock(return_value=[])
        mock.fetch_tick_prices = AsyncMock(return_value=[])
        mock.pg_pool = MagicMock()

        return mock

    async def create_streaming_indicator_engine(self):
        """Mock StreamingIndicatorEngine - no database"""
        from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine

        mock = MagicMock(spec=StreamingIndicatorEngine)
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.create_variant = AsyncMock(return_value="variant_123")
        mock.get_indicators = AsyncMock(return_value={})

        return mock

    async def create_strategy_manager(self):
        """Mock StrategyManager - no database"""
        from src.domain.services.strategy_manager import StrategyManager

        mock = MagicMock(spec=StrategyManager)
        mock.initialize_strategies = AsyncMock()
        mock.start = AsyncMock()
        mock.stop = AsyncMock()

        return mock

    # TODO: Override other expensive factories:
    # - create_live_market_adapter
    # - create_session_manager
    # - create_strategy_storage
    # - create_paper_trading_persistence
```

**Walidacja**:
- [ ] TestContainer nie łączy się z QuestDB
- [ ] Wszystkie mock'i mają spec= (type checking)
- [ ] Sprawdź git history `src/infrastructure/container.py`
- [ ] Uzasadnij czy ta zmiana nie koliduje z poprzednimi fix'ami

#### 2. Add QuestDB Health Check

**Cel**: Fail fast jeśli QuestDB nie działa

**Pliki do modyfikacji**:
- `tests_e2e/conftest.py`

**Zmiany**:

```python
# tests_e2e/conftest.py

import pytest
import asyncio


def pytest_configure(config):
    """
    Run BEFORE any tests - check if QuestDB is available.

    For integration tests that require database.
    """
    # Skip health check if only running unit tests
    markers = config.option.markexpr or ""
    if "integration" not in markers and "database" not in markers:
        return  # Unit tests don't need QuestDB

    print("\n🔍 Checking QuestDB availability...")

    try:
        import asyncpg

        async def check_questdb():
            try:
                pool = await asyncpg.create_pool(
                    host='127.0.0.1',
                    port=8812,
                    user='admin',
                    password='quest',
                    database='qdb',
                    min_size=1,
                    max_size=2,
                    timeout=2.0  # Fast check
                )
                await pool.close()
                return True
            except Exception as e:
                return False, str(e)

        result = asyncio.run(check_questdb())

        if result is True:
            print("✅ QuestDB is running on port 8812")
        else:
            error_msg = result[1] if isinstance(result, tuple) else "Unknown error"
            pytest.exit(
                f"\n❌ QuestDB is NOT running on port 8812.\n"
                f"Error: {error_msg}\n\n"
                f"Integration tests require QuestDB.\n"
                f"Start QuestDB:\n"
                f"  1. python database/questdb/install_questdb.py\n"
                f"  2. .\\start_all.ps1\n\n"
                f"Or run only unit tests:\n"
                f"  pytest -m 'not database'\n",
                returncode=1
            )
    except Exception as e:
        pytest.exit(f"QuestDB health check failed: {e}", returncode=1)
```

**Walidacja**:
- [ ] Health check wykonuje się <2s
- [ ] Health check wykrywa brak QuestDB
- [ ] Health check nie blokuje unit testów
- [ ] Sprawdź git history - czy był podobny health check?

#### 3. Optimize Container Initialization Order

**Cel**: Zmniejsz liczbę QuestDB connections w production

**Pliki do modyfikacji**:
- `src/infrastructure/container.py`

**Analiza wymagana**:
1. Sprawdź git log `src/infrastructure/container.py` - ostatnie 20 commitów
2. Zidentyfikuj które serwisy MUSZĄ mieć QuestDB przy starcie
3. Zidentyfikuj które serwisy mogą być lazy-loaded

**Zmiany**:

```python
# src/infrastructure/container.py

# BEFORE: Wszystkie serwisy tworzone przy starcie
async def create_streaming_indicator_engine(self):
    variant_repository = await self.create_indicator_variant_repository()  # ← QuestDB
    engine = StreamingIndicatorEngine(...)
    await engine.start()  # ← Loads from DB
    return engine


# AFTER: Lazy loading dla testów
async def create_streaming_indicator_engine(self, lazy_init: bool = False):
    """
    Create StreamingIndicatorEngine.

    Args:
        lazy_init: If True, skip database loading (for tests)
    """
    variant_repository = await self.create_indicator_variant_repository()
    engine = StreamingIndicatorEngine(...)

    if not lazy_init:
        await engine.start()  # Load variants from DB

    return engine
```

**Walidacja**:
- [ ] Production behavior nie zmienia się
- [ ] Tests mogą używać `lazy_init=True`
- [ ] Sprawdź czy nie złamiesz istniejących callsites
- [ ] Uzasadnij czemu to nie jest backward compatibility hack

### Metryki Sukcesu
- [ ] TestContainer dostępny dla wszystkich testów
- [ ] Health check wykrywa brak QuestDB
- [ ] Container initialization time: <100ms (w testach)

### Ryzyka i Mitigacje

| Ryzyko | Prawdopodobieństwo | Mitigacja |
|--------|-------------------|-----------|
| Mocks nie pokrywają real Container behavior | High | Agent 5 segreguje unit vs integration |
| lazy_init flag proliferuje przez codebase | Medium | Code review by Agent 6 |
| Health check ma false positives | Low | Test on CI |

---

## AGENT 4: CLEANUP OPTIMIZATION (RC#6)

### Zadania

#### 1. Remove autouse from Cleanup Fixtures

**Cel**: Cleanup tylko dla testów które tego potrzebują

**Pliki do modyfikacji**:
- `tests_e2e/conftest.py`

**Zmiany**:

```python
# tests_e2e/conftest.py

# BEFORE
@pytest.fixture(autouse=True)  # ← Runs for EVERY test
def cleanup_strategies(api_client):
    yield
    # Cleanup logic...


# AFTER
@pytest.fixture  # ← Removed autouse=True
def cleanup_strategies(api_client):
    """
    Manual cleanup for strategy tests.

    Usage:
        def test_create_strategy(api_client, cleanup_strategies):
            # Test creates strategies
            # cleanup_strategies will delete them after test
    """
    yield
    # Cleanup logic...


# Add explicit fixture for tests that need it
@pytest.fixture
def strategy_test(api_client, cleanup_strategies):
    """
    Convenience fixture for strategy tests.

    Automatically includes cleanup_strategies.
    """
    return api_client
```

**Walidacja**:
- [ ] Cleanup nie uruchamia się dla testów które nie tworzą strategies
- [ ] Tests które POTRZEBUJĄ cleanup nadal działają
- [ ] Sprawdź git log - czy cleanup był dodany z powodu?

#### 2. Improve Cleanup Error Handling

**Cel**: Zrozum dlaczego cleanup fail'uje

**Pliki do modyfikacji**:
- `tests_e2e/conftest.py`

**Zmiany**:

```python
# tests_e2e/conftest.py

# BEFORE
except Exception:
    pass  # ← Silent failures hide real problems


# AFTER
except Exception as e:
    # Log cleanup failures for debugging
    import logging
    logging.warning(f"Test cleanup failed: {type(e).__name__}: {e}")
    # Don't fail test due to cleanup failure, but report it
```

**Walidacja**:
- [ ] Cleanup failures są logowane
- [ ] Cleanup failures nie psują testów
- [ ] Sprawdź czy cleanup failures wskazują na real bugs

#### 3. Add Cleanup Performance Metrics

**Cel**: Zmierz czas cleanup

**Pliki do modyfikacji**:
- `tests_e2e/conftest.py`

**Zmiany**:

```python
# tests_e2e/conftest.py

import time

@pytest.fixture
def cleanup_strategies(api_client):
    yield

    # Measure cleanup time
    start = time.time()
    try:
        # Cleanup logic...
        pass
    finally:
        duration = time.time() - start
        if duration > 1.0:  # Slow cleanup
            import logging
            logging.warning(f"Slow cleanup: {duration:.2f}s")
```

**Walidacja**:
- [ ] Cleanup time < 100ms per fixture
- [ ] Slow cleanups są identyfikowane

### Metryki Sukcesu
- [ ] Cleanup fixtures: autouse=False
- [ ] Cleanup time per test: <100ms
- [ ] Cleanup failures są logowane (nie silent)

---

## AGENT 5: TEST CATEGORIZATION (RC#4)

### Zadania

#### 1. Add Test Markers

**Cel**: Segreguj unit vs integration tests

**Pliki do modyfikacji**:
- `pytest.ini`
- Wszystkie test files

**Zmiany**:

```ini
# pytest.ini

[pytest]
markers =
    fast: Fast unit tests (<100ms, no database)
    slow: Slow tests (>1s)
    database: Tests that require QuestDB
    integration: Integration tests (multiple components)
    e2e: End-to-end tests (full system)
    frontend: Frontend tests (Playwright)
    api: API endpoint tests
    unit: Unit tests (single component, mocked dependencies)
```

```python
# Example: tests_e2e/api/test_indicators.py

@pytest.mark.fast
@pytest.mark.unit
def test_get_indicators_for_symbol(lightweight_api_client):
    """Unit test - mocked dependencies"""
    ...


@pytest.mark.slow
@pytest.mark.database
@pytest.mark.integration
def test_indicators_with_real_database(api_client):
    """Integration test - requires QuestDB"""
    ...
```

**Walidacja**:
- [ ] Wszystkie testy mają marker (fast/slow)
- [ ] Wszystkie testy mają marker (unit/integration/e2e)
- [ ] Testy z `@pytest.mark.fast` nie używają QuestDB

#### 2. Split Test Files

**Cel**: Oddziel unit tests od integration tests

**Struktura**:

```
tests_e2e/
  unit/           # Fast tests, mocked dependencies
    test_indicators_unit.py
    test_auth_unit.py
  integration/    # Require QuestDB
    test_indicators_integration.py
    test_auth_integration.py
  e2e/            # Full system tests
    test_trading_flow.py
```

**Walidacja**:
- [ ] Unit tests nie wymagają QuestDB
- [ ] Integration tests sprawdzają real DB interactions
- [ ] Nie ma duplikacji testów

#### 3. Update run_tests.py

**Cel**: Support dla nowych markerów

**Pliki do modyfikacji**:
- `run_tests.py`

**Zmiany**:

```python
# run_tests.py

parser.add_argument('--unit', action='store_true',
                    help='Run only unit tests (fast, no database)')
parser.add_argument('--database', action='store_true',
                    help='Run tests that require database')

# Build pytest command
if args.unit:
    pytest_args.extend(['-m', 'unit'])
elif args.database:
    pytest_args.extend(['-m', 'database'])
```

**Walidacja**:
- [ ] `python run_tests.py --unit` działa
- [ ] `python run_tests.py --database` wymaga QuestDB

### Metryki Sukcesu
- [ ] 100% testów ma marker fast/slow
- [ ] 100% testów ma marker unit/integration/e2e
- [ ] `pytest -m unit` wykonuje się <10s

---

## AGENT 6: CODE REVIEW & VERIFICATION

### Zadania

#### 1. Review Changes from Other Agents

**Cel**: Sprawdź spójność i jakość zmian

**Checklist**:
- [ ] Zmiany Agent 2: Fixtures są lightweight, nie łamią istniejących testów
- [ ] Zmiany Agent 3: TestContainer pokrywa wszystkie use cases
- [ ] Zmiany Agent 4: Cleanup fixtures są optymalne
- [ ] Zmiany Agent 5: Markers są poprawnie zastosowane

**Pliki do sprawdzenia**:
- Wszystkie pliki zmodyfikowane przez Agentów 2-5

**Metoda**:
1. Przeczytaj każdą zmianę
2. Sprawdź git history dla kontekstu
3. Zidentyfikuj potencjalne problemy:
   - Dead code
   - Backward compatibility hacks
   - Race conditions
   - Memory leaks
   - Inconsistent naming

#### 2. Run Static Analysis

**Cel**: Wykryj problemy przed uruchomieniem testów

**Komendy**:
```bash
# Type checking
mypy src/ tests_e2e/

# Code quality
pylint src/infrastructure/container.py
pylint tests_e2e/conftest.py

# Security
bandit -r src/
```

**Walidacja**:
- [ ] Brak nowych type errors
- [ ] Brak nowych pylint errors
- [ ] Brak nowych security issues

#### 3. Verify Git History Compatibility

**Cel**: Upewnij się że zmiany nie cofają poprzednich fix'ów

**Dla każdego zmodyfikowanego pliku**:
```bash
git log --oneline -20 -- <filepath>
git diff <last_commit> -- <filepath>
```

**Analiza**:
- [ ] Czy były niedawne fix'y w tym obszarze?
- [ ] Czy nasze zmiany nie cofają tych fix'ów?
- [ ] Czy commit messages wskazują na problemy?

**Przykład**:
```bash
# tests_e2e/conftest.py history
git log --oneline -10 -- tests_e2e/conftest.py

# Output:
# e2a3f5d Fix CRITICAL: UnboundLocalError in QuestDB error handling
# 16c229f Fix CRITICAL: Add comprehensive error handling for QuestDB
# ...

# QUESTION: Czy nasze zmiany w conftest.py kolidują z tymi fix'ami?
# ANSWER: Nie, fix'y były w src/data_feed/questdb_provider.py, nie conftest.py
```

#### 4. Architecture Compliance Check

**Cel**: Sprawdź zgodność z architekturą

**Checklist**:
- [ ] Dependency Injection: Czy konstruktory używają DI?
- [ ] EventBus: Czy wszystkie handlery są async?
- [ ] Logging: Czy używamy StructuredLogger (nie print)?
- [ ] Error Handling: Czy RuntimeError ma sensowny message?
- [ ] Single Source of Truth: Czy nie ma duplikacji?

**Pliki do sprawdzenia**:
- `src/infrastructure/container.py`
- `tests_e2e/conftest.py`
- `tests_e2e/test_container.py`

### Metryki Sukcesu
- [ ] Brak architecture violations
- [ ] Brak regressions (cofnięć poprzednich fix'ów)
- [ ] Brak dead code
- [ ] Consistent naming i style

---

## DEPENDENCIES & EXECUTION ORDER

### Phase 1: Preparation (Parallel)
```
Agent 1 (Koordynator) → Pre-Flight Check
  ├→ Agent 6 → Git History Analysis (parallel)
  └→ Agent 6 → Architecture Review (parallel)
```

### Phase 2: Core Changes (Parallel where possible)
```
Agent 2 → Fixture Refactoring
  ├→ Create lightweight_app fixture
  ├→ Create mocks
  └→ [BLOCKER for Agent 5]

Agent 3 → Container Mocking
  ├→ Create TestContainer
  ├→ Add health check
  └→ [PARALLEL with Agent 2]

Agent 4 → Cleanup Optimization
  ├→ Remove autouse
  └→ [PARALLEL with Agents 2, 3]
```

### Phase 3: Integration (Sequential)
```
Agent 5 → Test Categorization
  ├→ [REQUIRES Agent 2 completion]
  ├→ Add markers
  └→ Split test files

Agent 6 → Code Review
  ├→ [REQUIRES Agents 2-5 completion]
  ├→ Review all changes
  └→ Run static analysis
```

### Phase 4: Validation (Sequential)
```
Agent 1 (Koordynator) → Integration & Testing
  ├→ Merge all changes
  ├→ Run: pytest -m unit
  ├→ Run: pytest -m fast
  ├→ Run: python run_tests.py --api --fast
  └→ Report results
```

---

## SUCCESS CRITERIA

### Performance Metrics
- [ ] Test execution time: <2 minutes (was: 39 minutes)
- [ ] Test success rate: >95% (was: 29.8%)
- [ ] Unit test speed: <100ms per test
- [ ] Integration test speed: <5s per test

### Quality Metrics
- [ ] Test coverage: >80% (unchanged)
- [ ] No new type errors
- [ ] No new security issues
- [ ] No dead code introduced

### Architecture Metrics
- [ ] No backward compatibility hacks
- [ ] No code duplication
- [ ] Consistent naming and style
- [ ] All fixtures documented

---

## ROLLBACK PLAN

Jeśli naprawy fail'ują:

1. **Identify failure point**
   ```bash
   git log --oneline -10
   git diff HEAD~5..HEAD
   ```

2. **Rollback changes**
   ```bash
   git reset --hard <commit_before_changes>
   ```

3. **Analyze failure**
   - Sprawdź logi testów
   - Zidentyfikuj root cause
   - Update plan naprawy

4. **Retry with updated plan**

---

## COMMUNICATION PROTOCOL

### Agent → Koordynator
- Raportuj co 5 minut status
- Eskaluj blokery natychmiast
- Raportuj completion z evidence

### Koordynator → Agent
- Przydziel task z jasnym scope
- Podaj expected deliverables
- Wskaż dependencies

### Koordynator → User
- Raportuj progress co 10 minut
- Eskaluj decyzje wymagające input
- Raportuj completion z metrics

---

## APPENDIX: ERROR CATEGORIES

### Full Error Breakdown
```
QuestDB Connection (StreamingIndicatorEngine): 225 (81.5%)
  ↳ Root Cause: RC#1, RC#2, RC#4
  ↳ Fix: Agent 2, Agent 3

Status Code Mismatch: 10 (3.6%)
  ↳ Root Cause: RC#4 (tests expect 404, get 500)
  ↳ Fix: Agent 2 (proper mocking)

QuestDB Timeout: 6 (2.2%)
  ↳ Root Cause: RC#2
  ↳ Fix: Agent 3 (health check)

KeyError: 3 (1.1%)
  ↳ Root Cause: RC#3 (async init order)
  ↳ Fix: Code fixes (not in this plan)

Playwright Timeout: 3 (1.1%)
  ↳ Root Cause: RC#1 (frontend waits for backend)
  ↳ Fix: Agent 2 (lightweight backend)

Strategy Storage Init: 2 (0.7%)
  ↳ Root Cause: RC#2
  ↳ Fix: Agent 3

TypeError: 2 (0.7%)
  ↳ Root Cause: Code bugs (not test infrastructure)
  ↳ Fix: Separate fix (not in this plan)

AttributeError: 1 (0.4%)
  ↳ Root Cause: Code bug (RiskManager API change)
  ↳ Fix: Separate fix (not in this plan)
```

---

## NEXT STEPS

1. **Koordynator (Agent 1)**: Review plan, assign tasks
2. **All Agents**: Acknowledge task assignment
3. **Execute**: Phase 1 → Phase 2 → Phase 3 → Phase 4
4. **Validate**: Run full test suite
5. **Report**: Deliver results to user

**Estimated Time**: 2-3 hours (with 6 parallel agents)
