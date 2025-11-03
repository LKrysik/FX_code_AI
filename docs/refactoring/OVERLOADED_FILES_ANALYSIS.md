# Analiza Przeładowanych Plików - Plan Refaktoryzacji

**Data analizy:** 2025-11-02
**Analiza:** Identyfikacja 3 najbardziej przeładowanych plików w codebase i plan ich podziału

---

## Executive Summary

Analiza wykazała 3 krytyczne pliki wymagające natychmiastowej refaktoryzacji:

1. **streaming_indicator_engine.py** - 5,730 linii (172 metody w jednej klasie) - **KRYTYCZNE**
2. **websocket_server.py** - 3,126 linii (4 klasy z nadmierną odpowiedzialnością)
3. **mexc_websocket_adapter.py** - 2,968 linii (bardzo długie metody w jednej klasie)

**Szacowany czas refaktoryzacji:** 15-20 godzin dzielone na 3 fazy
**Poziom ryzyka:** WYSOKI - komponenty krytyczne w produkcji
**Priorytet:** P0 (najwyższy)

---

## 1. StreamingIndicatorEngine.py - NAJWYŻSZY PRIORYTET

### 1.1 Aktualna Struktura

**Metryki:**
- **Rozmiar:** 5,730 linii kodu
- **Klasy:** 9 klas (główna: StreamingIndicatorEngine)
- **Metody w głównej klasie:** 172 metody
- **Metody kalkulacyjne:** ~80 metod rozpoczynających się od `_calculate_`
- **Cyklomatyczna złożoność:** Bardzo wysoka (>50 na metodę w niektórych przypadkach)

**Zidentyfikowane odpowiedzialności (Single Responsibility Principle violations):**
1. ✅ Zarządzanie cache'em (12+ metod)
2. ✅ Zarządzanie pamięcią (15+ metod)
3. ✅ Monitoring zdrowia systemu (8+ metod)
4. ✅ Kalkulacje wskaźników (80+ metod)
5. ✅ Zarządzanie wariantami wskaźników (10+ metod)
6. ✅ Integracja z EventBus (5+ metod)
7. ✅ Zarządzanie registry algorytmów (5+ metod)
8. ✅ Incremental calculations (20+ metod)
9. ✅ Circuit breaker i error handling (8+ metod)
10. ✅ TTL cleanup i data expiration (10+ metod)

### 1.2 Proponowany Podział

```
src/domain/services/streaming_indicator_engine/
├── __init__.py                          # Public API exports
├── core/
│   ├── engine.py                        # Main orchestrator (200-300 linii)
│   ├── indicator_registry.py            # Indicator registration & lookup (150 linii)
│   └── types.py                         # Shared types (IndicatorValue, etc.)
├── calculation/
│   ├── calculator_coordinator.py       # Calculation routing (150 linii)
│   ├── incremental_calculator.py       # Incremental algorithms (300 linii)
│   ├── technical_indicators.py         # SMA, EMA, RSI, MACD, BB (400 linii)
│   ├── custom_indicators.py            # TWPA, Velocity, Volume Surge (500 linii)
│   ├── risk_indicators.py              # Risk & volatility metrics (300 linii)
│   └── market_indicators.py            # Liquidity, spread, orderbook (400 linii)
├── caching/
│   ├── cache_manager.py                # Cache operations (300 linii)
│   ├── cache_strategy.py               # TTL, eviction policies (200 linii)
│   └── cache_statistics.py             # Hit rate, metrics (150 linii)
├── memory/
│   ├── memory_monitor.py               # Memory tracking (200 linii)
│   ├── cleanup_coordinator.py          # Cleanup orchestration (250 linii)
│   └── leak_detector.py                # Memory leak detection (200 linii)
├── health/
│   ├── health_monitor.py               # System health tracking (200 linii)
│   ├── circuit_breaker_handler.py      # Circuit breaker logic (150 linii)
│   └── performance_metrics.py          # Performance tracking (150 linii)
└── variants/
    ├── variant_manager.py              # Variant lifecycle (250 linii)
    └── variant_repository_adapter.py   # Persistence integration (100 linii)
```

**Razem:** ~4,900 linii (usuniemy ~830 linii duplikacji i dead code)

### 1.3 Główna Klasa `StreamingIndicatorEngine` (engine.py)

**Odpowiedzialność:** Orkiestracja komponentów, fasada dla zewnętrznych konsumentów

**Publiczne API (zachowane bez zmian):**
```python
class StreamingIndicatorEngine:
    def __init__(self, event_bus, logger, variant_repository=None)
    def add_indicator(self, ...)
    def list_indicators(self) -> List[Dict[str, Any]]
    def get_health_status(self) -> Dict[str, Any]
    def get_system_indicators(self) -> Dict[str, Any]
    def get_system_indicators_by_category(self, category) -> Dict[str, Any]
    def get_available_categories(self) -> List[str]
    def get_memory_stability_report(self) -> Dict[str, Any]
    # ... publiczne metody bez zmian interfejsu
```

**Delegacja do komponentów:**
```python
def __init__(self, event_bus, logger, variant_repository=None):
    self.event_bus = event_bus
    self.logger = logger

    # Dependency Injection - wszystkie komponenty
    self._cache_manager = CacheManager(logger, max_size=10000)
    self._memory_monitor = MemoryMonitor(logger, max_mb=500)
    self._health_monitor = HealthMonitor(logger)
    self._calculator = CalculatorCoordinator(logger, event_bus)
    self._variant_manager = VariantManager(variant_repository, logger)
    self._indicator_registry = IndicatorRegistry()
```

### 1.4 Szczegóły Komponentów

#### A. CacheManager (caching/cache_manager.py)

**Odpowiedzialność:** Zarządzanie cache'em wartości wskaźników

**Metody przeniesione:**
- `_get_cache_key()` → `get_cache_key()`
- `_get_cached_value()` → `get()`
- `_set_cached_value()` → `set()`
- `_cleanup_cache()` → `cleanup()`
- `_calculate_adaptive_ttl()` → `calculate_ttl()`
- `_enforce_cache_limits()` → `enforce_limits()`
- `_evict_cache_entries()` → `evict()`
- `_record_cache_access()` → `record_access()`
- `_calculate_cache_hit_rate()` → `get_hit_rate()`

**Interfejs:**
```python
class CacheManager:
    def get(self, cache_key: str) -> Optional[float]
    def set(self, cache_key: str, value: float, ttl: Optional[int] = None) -> None
    def cleanup(self) -> int
    def get_statistics(self) -> Dict[str, Any]
```

**Ryzyko:** NISKIE - czysta logika cache, brak zależności od kalkulacji

#### B. CalculatorCoordinator (calculation/calculator_coordinator.py)

**Odpowiedzialność:** Routing do odpowiednich kalkulatorów, orchestracja

**Metody przeniesione:**
- `_calculate_indicator_value_incremental()` → `calculate()`
- `_calculate_incremental_indicator()` → delegacja do IncrementalCalculator
- Wszystkie metody `_calculate_*_registered()` → delegacja do specjalistycznych kalkulatorów

**Struktura:**
```python
class CalculatorCoordinator:
    def __init__(self, logger, event_bus):
        self._technical = TechnicalIndicatorsCalculator()
        self._custom = CustomIndicatorsCalculator()
        self._risk = RiskIndicatorsCalculator()
        self._market = MarketIndicatorsCalculator()
        self._incremental = IncrementalCalculator()

    def calculate(self, indicator: StreamingIndicator, params: Dict) -> Optional[float]:
        # Route to appropriate calculator based on indicator type
        calculator = self._get_calculator(indicator.indicator)
        return calculator.calculate(indicator, params)
```

**Ryzyko:** ŚREDNIE - kluczowa logika biznesowa, wymaga dokładnych testów

#### C. MemoryMonitor (memory/memory_monitor.py)

**Odpowiedzialność:** Monitoring pamięci, wykrywanie wycieków

**Metody przeniesione:**
- `_check_memory_limits()` → `check_limits()`
- `_detect_memory_leaks()` → `detect_leaks()`
- `_update_health_status()` → przeniesione do HealthMonitor
- `get_memory_stability_report()` → `get_stability_report()`

**Interfejs:**
```python
class MemoryMonitor:
    def check_limits(self) -> bool
    def detect_leaks(self) -> Optional[Dict[str, Any]]
    def get_stability_report(self) -> Dict[str, Any]
    def record_sample(self) -> None
```

**Ryzyko:** NISKIE - izolowana logika monitoringu

#### D. CleanupCoordinator (memory/cleanup_coordinator.py)

**Odpowiedzialność:** Koordynacja czyszczenia danych

**Metody przeniesione:**
- `_cleanup_expired_data()` → `cleanup_expired()`
- `_force_cleanup()` → `force_cleanup()`
- `_emergency_cleanup()` → `emergency_cleanup()`
- `_cleanup_all_data_structures()` → `cleanup_all()`
- `_should_cleanup_data()` → `should_cleanup()`

**Interfejs:**
```python
class CleanupCoordinator:
    def cleanup_expired(self) -> int
    def force_cleanup(self) -> int
    def emergency_cleanup(self) -> int
    def should_cleanup(self) -> bool
```

**Ryzyko:** ŚREDNIE - krytyczne dla stabilności pamięci

#### E. TechnicalIndicatorsCalculator (calculation/technical_indicators.py)

**Odpowiedzialność:** Kalkulacje klasycznych wskaźników technicznych

**Metody przeniesione:**
- `_calculate_sma_registered()` → `calculate_sma()`
- `_calculate_ema_registered()` → `calculate_ema()`
- `_calculate_rsi_registered()` → `calculate_rsi()`
- `_calculate_macd_registered()` → `calculate_macd()`
- `_calculate_bollinger_bands_registered()` → `calculate_bollinger_bands()`
- Pomocnicze metody kalkulacji (np. `_calculate_ema()`, `_calculate_rsi()`)

**Interfejs:**
```python
class TechnicalIndicatorsCalculator:
    def calculate_sma(self, indicator: StreamingIndicator, params: Dict) -> Optional[float]
    def calculate_ema(self, indicator: StreamingIndicator, params: Dict) -> Optional[float]
    def calculate_rsi(self, indicator: StreamingIndicator, params: Dict) -> Optional[float]
    # ...
```

**Ryzyko:** NISKIE - dobrze zdefiniowane algorytmy, łatwe do testowania

#### F. CustomIndicatorsCalculator (calculation/custom_indicators.py)

**Odpowiedzialność:** Kalkulacje niestandardowych wskaźników (TWPA, Velocity, etc.)

**Metody przeniesione:**
- `_calculate_pump_magnitude_pct_registered()` → `calculate_pump_magnitude()`
- `_calculate_volume_surge_ratio_registered()` → `calculate_volume_surge()`
- `_calculate_price_velocity_registered()` → `calculate_velocity()`
- `_calculate_velocity_cascade()` → `calculate_velocity_cascade()`
- `_calculate_velocity_acceleration()` → `calculate_velocity_acceleration()`
- `_calculate_max_twpa()` → `calculate_max_twpa()`
- `_calculate_min_twpa()` → `calculate_min_twpa()`
- `_calculate_vtwpa()` → `calculate_vtwpa()`
- Wszystkie metody TWPA-related

**Ryzyko:** ŚREDNIE/WYSOKI - najbardziej skomplikowane algorytmy, wymaga dokładnej walidacji

### 1.5 Strategia Migracji (Phased Approach)

**FAZA 1: Przygotowanie (2 godziny)**
1. Utworzenie nowej struktury katalogów
2. Utworzenie plików `__init__.py` z pustymi klasami
3. Przeniesienie typów danych (IndicatorType, VariantType, etc.) do `core/types.py`
4. Stworzenie testów integracyjnych baseline (snapshot obecnego zachowania)

**FAZA 2: Ekstrakcja komponentów niskoryzylownych (4 godziny)**
1. **CacheManager** - przeniesienie logiki cache'owania
   - Test każdej metody osobno
   - Integracja z główną klasą przez delegację
   - Veryfikacja że wszystkie przypadki użycia działają
2. **MemoryMonitor** - przeniesienie monitoringu pamięci
   - Test monitoringu
   - Integracja z główną klasą
3. **HealthMonitor** - przeniesienie health checks
   - Test health reporting
   - Integracja z główną klasą

**Checkpoint:** Uruchomienie pełnego zestawu testów + manualne testy backtestingu

**FAZA 3: Ekstrakcja kalkulatorów (6 godzin)**
1. **TechnicalIndicatorsCalculator** - najprostsze algorytmy
   - Przeniesienie SMA, EMA, RSI, MACD, BB
   - Unit testy dla każdego wskaźnika
   - Veryfikacja przeciwko znanym wartościom
2. **CustomIndicatorsCalculator** - złożone algorytmy
   - Przeniesienie TWPA, Velocity, Volume Surge
   - Dokładne testy z danymi historycznymi
   - Porównanie wartości przed/po refaktoryzacji
3. **CalculatorCoordinator** - routing
   - Implementacja routingu do kalkulatorów
   - Test wszystkich ścieżek kalkulacji

**Checkpoint:** Uruchomienie backtestów z porównaniem wyników przed/po

**FAZA 4: Ekstrakcja pozostałych komponentów (3 godziny)**
1. **CleanupCoordinator** - logika czyszczenia
2. **VariantManager** - zarządzanie wariantami
3. **IndicatorRegistry** - rejestracja wskaźników

**Checkpoint:** Pełna weryfikacja systemu

**FAZA 5: Finalizacja (2 godziny)**
1. Aktualizacja dokumentacji
2. Cleanup starego kodu
3. Finalne testy integracyjne
4. Testy obciążeniowe (memory leaks, performance)

### 1.6 Strategia Minimalizacji Ryzyka

#### Ryzyko #1: Zmiana zachowania kalkulacji wskaźników

**Prawdopodobieństwo:** WYSOKIE
**Wpływ:** KRYTYCZNY (błędne sygnały tradingowe)

**Mitigacje:**
1. **Golden Master Testing**
   - Zapisanie 1000+ wartości wskaźników z obecnej implementacji
   - Porównanie wartości po refaktoryzacji (dokładność do 0.0001%)
   - Automatyczne alerty przy rozbieżnościach

2. **Historical Data Validation**
   - Uruchomienie backtestów na 10 różnych sesjach historycznych
   - Porównanie wyników (PnL, signals, entries/exits) przed/po
   - Akceptacja tylko jeśli różnice < 0.01%

3. **Parallel Run Strategy (jeśli możliwe)**
   - Tymczasowe uruchomienie obu implementacji równolegle
   - Logowanie rozbieżności w real-time
   - Rollback jeśli rozbieżności przekraczają threshold

**Veryfikacja:**
```python
# Przykładowy test Golden Master
def test_golden_master_sma():
    # Load golden data
    golden_data = load_golden_data("sma_test_cases.json")

    for test_case in golden_data:
        result = calculator.calculate_sma(test_case.indicator, test_case.params)
        expected = test_case.expected_value

        assert abs(result - expected) < 0.0001, f"SMA mismatch: {result} != {expected}"
```

#### Ryzyko #2: Broken dependencies i import cycles

**Prawdopodobieństwo:** ŚREDNIE
**Wpływ:** WYSOKI (brak możliwości uruchomienia)

**Mitigacje:**
1. **Clear Dependency Hierarchy**
   ```
   core/types.py (no dependencies)
   ↓
   calculation/calculators.py (depends on types)
   ↓
   core/engine.py (depends on all)
   ```

2. **Explicit Interface Definitions**
   - Każdy komponent definiuje swój interface na początku pliku
   - Użycie Protocol/ABC dla wszystkich komponentów
   - Dependency Injection przez konstruktor

3. **Import Validation Tests**
   ```python
   def test_no_circular_imports():
       # Automatic detection of circular imports
       import_graph = analyze_imports("src/domain/services/streaming_indicator_engine/")
       cycles = find_cycles(import_graph)
       assert len(cycles) == 0, f"Circular imports detected: {cycles}"
   ```

#### Ryzyko #3: Memory leaks w nowej strukturze

**Prawdopodobieństwo:** ŚREDNIE
**Wpływ:** WYSOKI (crash po kilku godzinach)

**Mitigacje:**
1. **Memory Profiling Before/After**
   - Profil pamięci przed refaktoryzacją (baseline)
   - Profil pamięci po refaktoryzacji
   - Porównanie wzrostu pamięci w czasie

2. **Long-Running Tests**
   - Test 24-godzinny z symulowanymi danymi
   - Monitoring pamięci co 1 minutę
   - Alert jeśli pamięć rośnie > 10MB/godzinę

3. **Explicit Cleanup in All Components**
   - Każdy komponent implementuje metodę `cleanup()`
   - Orchestrator wywołuje cleanup wszystkich komponentów
   - WeakReferences gdzie to możliwe

**Veryfikacja:**
```python
def test_memory_stability_24h():
    engine = StreamingIndicatorEngine(...)
    memory_samples = []

    for hour in range(24):
        # Simulate 1 hour of trading data
        simulate_trading_hour(engine)

        # Record memory
        memory_mb = get_memory_usage_mb()
        memory_samples.append(memory_mb)

    # Check memory growth
    growth_rate = calculate_growth_rate(memory_samples)
    assert growth_rate < 10  # MB per hour
```

#### Ryzyko #4: Performance degradation

**Prawdopodobieństwo:** NISKIE
**Wpływ:** ŚREDNI (wolniejsze kalkulacje)

**Mitigacje:**
1. **Benchmark Tests**
   - Benchmark kalkulacji wskaźników przed refaktoryzacją
   - Benchmark po refaktoryzacji
   - Akceptacja tylko jeśli performance różni się < 5%

2. **Profiling Hot Paths**
   - Identyfikacja najczęściej wywoływanych metod
   - Optymalizacja tych ścieżek
   - Unikanie zbędnych kopiowań danych

**Veryfikacja:**
```python
def test_performance_baseline():
    data = generate_test_data(100000)  # 100k data points

    # Old implementation
    start = time.time()
    old_engine.calculate_all_indicators(data)
    old_time = time.time() - start

    # New implementation
    start = time.time()
    new_engine.calculate_all_indicators(data)
    new_time = time.time() - start

    # Allow 5% degradation
    assert new_time <= old_time * 1.05
```

#### Ryzyko #5: Breaking existing API contracts

**Prawdopodobieństwo:** ŚREDNIE
**Wpływ:** KRYTYCZNY (wszystkie konsumenci przestają działać)

**Mitigacje:**
1. **API Compatibility Layer**
   - Wszystkie publiczne metody zachowane bez zmian sygnatur
   - Backward compatibility na poziomie API
   - Deprecation warnings dla metod które się zmienią w przyszłości

2. **Contract Tests**
   ```python
   def test_api_contracts():
       """Verify all public methods maintain their signatures"""
       engine = StreamingIndicatorEngine(event_bus, logger)

       # Test all public methods exist
       assert hasattr(engine, 'add_indicator')
       assert hasattr(engine, 'list_indicators')
       assert hasattr(engine, 'get_health_status')
       # ...

       # Test method signatures
       sig = inspect.signature(engine.add_indicator)
       expected_params = ['symbol', 'indicator', 'timeframe', ...]
       assert list(sig.parameters.keys()) == expected_params
   ```

3. **Consumer Integration Tests**
   - Testy z perspektywy głównych konsumentów:
     - ExecutionController
     - StrategyManager
     - WebSocket API
   - Veryfikacja że wszystkie use cases działają

### 1.7 Strategia Weryfikacji

**Poziom 1: Unit Tests**
- Każdy komponent ma osobne unit testy
- Coverage > 90% dla nowego kodu
- Testy dla edge cases i error handling

**Poziom 2: Integration Tests**
- Testy integracji między komponentami
- Testy pełnego flow'u kalkulacji wskaźników
- Testy event-driven communication

**Poziom 3: System Tests**
- Testy backtestingu z danymi historycznymi
- Testy data collection flow
- Testy live trading simulation (paper trading)

**Poziom 4: Performance Tests**
- Benchmark kalkulacji wskaźników
- Memory leak tests (24h run)
- Load tests (1000+ indicators, 100+ symbols)

**Poziom 5: Manual Verification**
- Przegląd kodu przez drugą osobę
- Manualne testy UI (frontend dashboard)
- Veryfikacja logów w czasie rzeczywistym

---

## 2. WebSocket Server (websocket_server.py) - ŚREDNI PRIORYTET

### 2.1 Aktualna Struktura

**Metryki:**
- **Rozmiar:** 3,126 linii kodu
- **Klasy:** 4 klasy (RateLimitEntry, LRUCache, RateLimiter, WebSocketAPIServer)
- **Metody async:** 42 metody async w WebSocketAPIServer
- **Odpowiedzialności:** 6+ głównych odpowiedzialności w jednej klasie

**Problem:** WebSocketAPIServer jest god object który zarządza:
1. Connection management
2. Authentication & authorization
3. Message routing
4. Subscription management
5. Event broadcasting
6. Rate limiting coordination
7. Health monitoring
8. Error handling

### 2.2 Proponowany Podział

```
src/api/websocket/
├── __init__.py                      # Public API
├── server.py                        # Main WebSocketAPIServer (300-400 linii)
├── connection/
│   ├── connection_manager.py       # Already separate (keep as is)
│   ├── connection_lifecycle.py     # Connection lifecycle mgmt (200 linii)
│   └── connection_tracker.py       # Active connections tracking (150 linii)
├── auth/
│   ├── auth_handler.py             # Already separate (keep as is)
│   ├── session_manager.py          # Session lifecycle (150 linii)
│   └── permission_validator.py     # Permission checks (100 linii)
├── messaging/
│   ├── message_router.py           # Already separate (keep as is)
│   ├── message_validator.py        # Input validation (150 linii)
│   └── message_serializer.py       # JSON encoding/decoding (100 linii)
├── subscription/
│   ├── subscription_manager.py     # Already separate (keep as is)
│   ├── topic_coordinator.py        # Topic management (150 linii)
│   └── subscription_persistence.py # Subscription state (100 linii)
├── broadcast/
│   ├── broadcast_provider.py       # Already separate (keep as is)
│   ├── event_bridge.py             # Already separate (keep as is)
│   └── broadcast_throttler.py      # Rate limiting broadcasts (150 linii)
├── ratelimit/
│   ├── rate_limiter.py             # Core rate limiting (keep current)
│   ├── ip_tracker.py               # IP-based tracking (150 linii)
│   └── quota_manager.py            # Quota enforcement (100 linii)
└── monitoring/
    ├── health_checker.py           # WebSocket health (150 linii)
    └── metrics_collector.py        # WS metrics (150 linii)
```

**Razem:** ~2,800 linii (redukcja ~300 linii przez eliminację duplikacji)

### 2.3 Główna Klasa WebSocketAPIServer (server.py)

**Odpowiedzialność:** Orchestration i lifecycle management WebSocket serwera

**Struktura:**
```python
class WebSocketAPIServer:
    def __init__(self, event_bus, logger, ...):
        self.event_bus = event_bus
        self.logger = logger

        # Dependency Injection
        self._connection_lifecycle = ConnectionLifecycle(logger)
        self._session_manager = SessionManager(logger)
        self._message_validator = MessageValidator(logger)
        self._topic_coordinator = TopicCoordinator(event_bus, logger)
        self._health_checker = HealthChecker(logger)

        # Keep existing components
        self.connection_manager = ConnectionManager()
        self.auth_handler = AuthHandler(...)
        self.message_router = MessageRouter(...)
        self.subscription_manager = SubscriptionManager(...)
        self.event_bridge = EventBridge(...)
        self.broadcast_provider = BroadcastProvider(...)
        self.rate_limiter = RateLimiter(...)

    async def handle_connection(self, websocket: WebSocket):
        """Main connection handler - orchestrates all components"""
        # Delegate to components
        if not await self._connection_lifecycle.accept_connection(websocket):
            return

        session = await self._session_manager.create_session(websocket)
        try:
            await self._message_loop(session)
        finally:
            await self._connection_lifecycle.cleanup_connection(session)
```

### 2.4 Kluczowe Zmiany

#### A. ConnectionLifecycle (connection/connection_lifecycle.py)

**Odpowiedzialność:** Zarządzanie cyklem życia połączenia

**Metody przeniesione z WebSocketAPIServer:**
- Connection acceptance logic
- Connection initialization
- Connection cleanup
- Connection state transitions

**Interfejs:**
```python
class ConnectionLifecycle:
    async def accept_connection(self, websocket: WebSocket) -> bool
    async def initialize_connection(self, client_id: str) -> None
    async def cleanup_connection(self, client_id: str) -> None
    async def handle_disconnect(self, client_id: str, reason: str) -> None
```

**Ryzyko:** NISKIE - jasno zdefiniowana odpowiedzialność

#### B. SessionManager (auth/session_manager.py)

**Odpowiedzialność:** Zarządzanie sesjami użytkowników

**Metody przeniesione:**
- Session creation
- Session refresh
- Session expiration
- Token management

**Ryzyko:** ŚREDNIE - krytyczne dla bezpieczeństwa

#### C. TopicCoordinator (subscription/topic_coordinator.py)

**Odpowiedzialność:** Koordynacja subskrypcji i topicsmów

**Metody przeniesione:**
- Topic subscription logic
- Topic filtering
- Topic-based routing

**Ryzyko:** ŚREDNIE - krytyczne dla event delivery

### 2.5 Strategia Migracji

**FAZA 1: Ekstrakcja connection lifecycle (2 godziny)**
1. Utworzenie ConnectionLifecycle class
2. Przeniesienie logiki lifecycle
3. Integracja z WebSocketAPIServer
4. Test connection flow

**FAZA 2: Ekstrakcja session management (2 godziny)**
1. Utworzenie SessionManager
2. Przeniesienie logiki sesji
3. Test authentication flow

**FAZA 3: Ekstrakcja topic coordination (2 godziny)**
1. Utworzenie TopicCoordinator
2. Przeniesienie logiki subskrypcji
3. Test subscription flow

**FAZA 4: Weryfikacja i cleanup (1 godzina)**
1. Integracja wszystkich komponentów
2. Pełne testy WebSocket protocol
3. Load testing

### 2.6 Strategia Minimalizacji Ryzyka

#### Ryzyko #1: WebSocket connection drops

**Prawdopodobieństwo:** ŚREDNIE
**Wpływ:** WYSOKI (utrata real-time data)

**Mitigacje:**
1. **Connection Stability Tests**
   - Test 1000 simultaneous connections
   - Test connection handling under load
   - Test reconnection scenarios

2. **Message Delivery Verification**
   - Test że wszystkie wiadomości są dostarczane
   - Test ordering messages
   - Test że nie ma message loss

**Veryfikacja:**
```python
async def test_websocket_stability():
    # Create 1000 WebSocket connections
    connections = []
    for i in range(1000):
        ws = await connect_websocket()
        connections.append(ws)

    # Send messages to all
    for i in range(100):
        await server.broadcast({"msg": i})
        await asyncio.sleep(0.1)

    # Verify all received all messages
    for ws in connections:
        messages = await ws.receive_all()
        assert len(messages) == 100
```

#### Ryzyko #2: Authentication bypass

**Prawdopodobieństwo:** NISKIE
**Wpływ:** KRYTYCZNY (security breach)

**Mitigacje:**
1. **Security Audit**
   - Przegląd kodu authentication flow
   - Test wszystkich edge cases
   - Penetration testing

2. **Auth Flow Tests**
   ```python
   async def test_authentication_required():
       ws = await connect_websocket()

       # Try to send command without auth
       response = await ws.send_command({"type": "subscribe", ...})
       assert response.status == "error"
       assert response.code == "UNAUTHORIZED"
   ```

### 2.7 Strategia Weryfikacji

**Poziom 1: Unit Tests**
- Test każdego komponentu osobno
- Mock dependencies
- Coverage > 85%

**Poziom 2: Integration Tests**
- Test WebSocket protocol end-to-end
- Test authentication flow
- Test subscription flow

**Poziom 3: Load Tests**
- 1000+ simultaneous connections
- 10,000+ messages per second
- Memory stability test

**Poziom 4: Security Tests**
- Authentication bypass attempts
- Rate limiting tests
- SQL injection / XSS tests

---

## 3. MEXC WebSocket Adapter (mexc_websocket_adapter.py) - NIŻSZY PRIORYTET

### 3.1 Aktualna Struktura

**Metryki:**
- **Rozmiar:** 2,968 linii kodu
- **Klasy:** 1 główna klasa (MexcWebSocketAdapter)
- **Metody:** 13+ metod (wiele bardzo długich - 200+ linii każda)
- **Złożoność:** Bardzo długie metody z zagnieżdżoną logiką

**Problem:** MexcWebSocketAdapter jest bardzo długą klasą z:
1. Multi-connection management (5+ długich metod)
2. Subscription management (3+ długich metod)
3. Message handling (4+ długich metod - BARDZO długie)
4. Circuit breaker coordination
5. Rate limiting
6. Reconnection logic
7. Memory management

**Główny problem:** Metody są za długie (200-400 linii), nie tyle że jest za dużo metod

### 3.2 Proponowany Podział

```
src/infrastructure/exchanges/mexc/
├── __init__.py                           # Public API
├── adapter.py                            # Main adapter (300-400 linii)
├── connection/
│   ├── connection_pool.py               # Multi-connection management (300 linii)
│   ├── connection_handler.py            # Single connection handler (250 linii)
│   └── reconnection_manager.py          # Reconnection logic (200 linii)
├── subscription/
│   ├── subscription_coordinator.py      # Subscription routing (200 linii)
│   ├── subscription_tracker.py          # Subscription state (150 linii)
│   └── subscription_confirmer.py        # Confirmation handling (150 linii)
├── messaging/
│   ├── message_handler.py               # Message routing (200 linii)
│   ├── deal_message_processor.py        # Deal messages (200 linii)
│   ├── depth_message_processor.py       # Depth messages (200 linii)
│   └── subscription_message_processor.py # Subscription confirmations (150 linii)
├── protection/
│   ├── circuit_breaker.py               # Already separate (keep as is)
│   └── rate_limiter.py                  # Already separate (keep as is)
└── monitoring/
    ├── health_tracker.py                # Connection health (150 linii)
    └── metrics_reporter.py              # MEXC-specific metrics (100 linii)
```

**Razem:** ~2,600 linii (redukcja ~368 linii)

### 3.3 Główna Klasa MexcWebSocketAdapter (adapter.py)

**Odpowiedzialność:** Orchestration i public interface dla MEXC integration

**Struktura:**
```python
class MexcWebSocketAdapter(IMarketDataProvider):
    def __init__(self, settings, event_bus, logger, data_types=None):
        self.settings = settings
        self.event_bus = event_bus
        self.logger = logger

        # Dependency Injection
        self._connection_pool = ConnectionPool(settings, logger)
        self._subscription_coordinator = SubscriptionCoordinator(event_bus, logger)
        self._message_handler = MessageHandler(event_bus, logger)
        self._reconnection_manager = ReconnectionManager(logger)
        self._health_tracker = HealthTracker(logger)

        # Keep existing components
        self.circuit_breaker = CircuitBreaker(...)
        self.subscription_rate_limiter = TokenBucketRateLimiter(...)

    async def start(self, symbols: List[str]) -> None:
        """Start adapter - delegates to components"""
        await self._connection_pool.initialize(symbols)
        await self._subscription_coordinator.subscribe_all(symbols)

    async def stop(self) -> None:
        """Stop adapter - delegates cleanup"""
        await self._subscription_coordinator.unsubscribe_all()
        await self._connection_pool.shutdown()
```

### 3.4 Kluczowe Zmiany

#### A. ConnectionPool (connection/connection_pool.py)

**Odpowiedzialność:** Zarządzanie wieloma połączeniami WebSocket

**Metody przeniesione:**
- Multi-connection initialization
- Connection assignment logic
- Load balancing across connections
- Connection monitoring

**Najważniejsza zmiana:** Ekstrakcja bardzo długiej metody `_manage_connection()` (400+ linii) do mniejszych metod w ConnectionHandler

**Interfejs:**
```python
class ConnectionPool:
    async def initialize(self, symbols: List[str]) -> None
    async def get_connection_for_symbol(self, symbol: str) -> ConnectionHandler
    async def shutdown(self) -> None
    def get_connection_stats(self) -> Dict[str, Any]
```

**Ryzyko:** ŚREDNIE - krytyczne dla niezawodności połączeń

#### B. DealMessageProcessor (messaging/deal_message_processor.py)

**Odpowiedzialność:** Przetwarzanie wiadomości deal z MEXC

**Metody przeniesione:**
- Część bardzo długiej metody `_handle_message()` dotycząca deal messages
- Parsing deal data
- Validation deal messages
- Publishing deal events

**Interfejs:**
```python
class DealMessageProcessor:
    async def process(self, message: Dict[str, Any]) -> None
    def validate_deal_message(self, message: Dict) -> bool
    async def publish_deal_event(self, deal_data: Dict) -> None
```

**Ryzyko:** ŚREDNIE - krytyczne dla jakości danych price

#### C. DepthMessageProcessor (messaging/depth_message_processor.py)

**Odpowiedzialność:** Przetwarzanie wiadomości orderbook depth z MEXC

**Metody przeniesione:**
- Część metody `_handle_message()` dotycząca depth messages
- Orderbook reconstruction logic
- Depth validation
- Publishing orderbook events

**Interfejs:**
```python
class DepthMessageProcessor:
    async def process(self, message: Dict[str, Any]) -> None
    def validate_depth_message(self, message: Dict) -> bool
    async def publish_depth_event(self, depth_data: Dict) -> None
    def reconstruct_orderbook(self, depth_data: Dict) -> Dict
```

**Ryzyko:** ŚREDNIE - krytyczne dla jakości danych orderbook

#### D. ReconnectionManager (connection/reconnection_manager.py)

**Odpowiedzialność:** Zarządzanie reconnection logic

**Metody przeniesione:**
- Reconnection attempt logic
- Backoff calculation
- Reconnection failure handling
- State restoration after reconnect

**Interfejs:**
```python
class ReconnectionManager:
    async def attempt_reconnect(self, connection_id: int) -> bool
    def calculate_backoff(self, attempt: int) -> float
    async def restore_subscriptions(self, connection_id: int) -> None
```

**Ryzyko:** NISKIE - jasna odpowiedzialność

### 3.5 Strategia Migracji

**FAZA 1: Ekstrakcja message processors (3 godziny)**
1. Utworzenie DealMessageProcessor
2. Utworzenie DepthMessageProcessor
3. Utworzenie SubscriptionMessageProcessor
4. Utworzenie MessageHandler jako coordinator
5. Refaktoryzacja bardzo długiej metody `_handle_message()`
6. Test message processing flow

**FAZA 2: Ekstrakcja connection management (3 godziny)**
1. Utworzenie ConnectionHandler
2. Utworzenie ConnectionPool
3. Refaktoryzacja metody `_manage_connection()`
4. Test multi-connection management

**FAZA 3: Ekstrakcja subscription management (2 godziny)**
1. Utworzenie SubscriptionCoordinator
2. Utworzenie SubscriptionTracker
3. Test subscription flow

**FAZA 4: Ekstrakcja reconnection logic (1 godzina)**
1. Utworzenie ReconnectionManager
2. Test reconnection scenarios

**FAZA 5: Weryfikacja (1 godzina)**
1. Integracja wszystkich komponentów
2. Test z live MEXC connection
3. Load testing

### 3.6 Strategia Minimalizacji Ryzyka

#### Ryzyko #1: Data loss podczas reconnection

**Prawdopodobieństwo:** ŚREDNIE
**Wpływ:** WYSOKI (missing price data)

**Mitigacje:**
1. **Reconnection Flow Tests**
   - Test że subscriptions są przywracane po reconnect
   - Test że nie ma data gaps
   - Test sequential reconnects

2. **Data Continuity Verification**
   ```python
   async def test_no_data_loss_on_reconnect():
       adapter = MexcWebSocketAdapter(...)
       await adapter.start(["BTC_USDT"])

       received_prices = []
       event_bus.subscribe("market_data", lambda data: received_prices.append(data))

       # Simulate connection drop
       await adapter._connection_pool.force_disconnect(connection_id=0)

       # Wait for reconnect
       await asyncio.sleep(5)

       # Verify continuous price stream
       assert len(received_prices) > 0
       assert all(p.timestamp for p in received_prices)  # No gaps
   ```

#### Ryzyko #2: Incorrect orderbook reconstruction

**Prawdopodobieństwo:** NISKIE/ŚREDNIE
**Wpływ:** WYSOKI (wrong trading decisions)

**Mitigacje:**
1. **Orderbook Validation**
   - Compare reconstructed orderbook z MEXC REST API
   - Verify orderbook consistency
   - Test edge cases (empty orderbook, huge orderbook)

2. **Golden Master Tests**
   ```python
   def test_orderbook_reconstruction():
       processor = DepthMessageProcessor(...)

       # Load known good orderbook data
       test_data = load_test_data("mexc_depth_messages.json")

       for msg in test_data.messages:
           result = processor.reconstruct_orderbook(msg)
           expected = test_data.expected_orderbooks[msg.id]

           assert result.bids == expected.bids
           assert result.asks == expected.asks
   ```

#### Ryzyko #3: Rate limiting violations

**Prawdopodobieństwo:** NISKIE
**Wpływ:** ŚREDNI (connection bans)

**Mitigacje:**
1. **Rate Limit Tests**
   - Test że nie przekraczamy 30 subscriptions per connection
   - Test subscription rate limiting
   - Test backoff on rate limit errors

2. **MEXC Protocol Compliance**
   - Verify zgodność z MEXC WebSocket protocol spec
   - Test error handling dla wszystkich MEXC error codes
   - Monitor MEXC-specific rate limit headers

### 3.7 Strategia Weryfikacji

**Poziom 1: Unit Tests**
- Test każdego message processora osobno
- Mock WebSocket connections
- Coverage > 85%

**Poziom 2: Integration Tests**
- Test z mock MEXC server
- Test full message flow
- Test reconnection scenarios

**Poziom 3: Live Tests**
- Test z real MEXC connection (testnet)
- Verify data accuracy
- Test long-running stability (4+ hours)

**Poziom 4: Load Tests**
- 100+ symbols subscription
- High-frequency message handling
- Memory stability

---

## Podsumowanie i Rekomendacje

### Priorytetyzacja

**P0 - NAJWYŻSZY PRIORYTET:**
1. **StreamingIndicatorEngine.py** (15 dni pracy)
   - Największy wpływ na maintainability
   - Krytyczny dla wszystkich strategii tradingowych
   - Największe ryzyko jeśli nie zostanie naprawiony (niemożliwe dalsze rozwijanie)

**P1 - WYSOKI PRIORYTET:**
2. **WebSocketServer.py** (7 dni pracy)
   - Ważny dla real-time communication
   - Wpływa na user experience
   - Mniejsze ryzyko niż #1

**P2 - ŚREDNI PRIORYTET:**
3. **MexcWebSocketAdapter.py** (10 dni pracy)
   - Specyficzny dla jednej giełdy
   - Można dodać inne giełdy bez refaktoryzacji
   - Najmniejszy wpływ na całość systemu

### Całkowity Szacunek Czasu

**Optymistyczny:** 25 dni roboczych
**Realistyczny:** 32 dni roboczych (6.5 tygodni)
**Pesymistyczny:** 40 dni roboczych (8 tygodni)

### Kluczowe Wskaźniki Sukcesu (KPIs)

1. **Maintainability Index:**
   - Przed: ~15-20 (bardzo trudne do utrzymania)
   - Cel: >60 (łatwe do utrzymania)

2. **Average File Length:**
   - Przed: 3,941 linii (top 3 files)
   - Cel: <500 linii per file

3. **Cyclomatic Complexity:**
   - Przed: >50 w niektórych metodach
   - Cel: <10 per method

4. **Test Coverage:**
   - Przed: ~70% (głównie integration tests)
   - Cel: >90% (z unit tests)

5. **Bug Rate:**
   - Monitorowanie przez 30 dni po refaktoryzacji
   - Cel: <3 bugs P0/P1 related do refaktoryzacji

### Decyzja Go/No-Go

**GO jeśli:**
- ✅ Zespół ma 8+ tygodni na refaktoryzację
- ✅ Jest możliwość code freeze dla affektowanych komponentów
- ✅ Jest kompletny zestaw testów integracyjnych jako baseline
- ✅ Jest możliwość rollback w przypadku problemów

**NO-GO jeśli:**
- ❌ Nadchodzą critical features w ciągu 2 miesięcy
- ❌ Brak czasu na dokładne testowanie
- ❌ Brak testów integracyjnych jako baseline
- ❌ Zespół < 2 osoby

### Następne Kroki

1. **Decyzja stakeholderów** (1 dzień)
   - Prezentacja tego dokumentu
   - Decyzja go/no-go
   - Ustalenie timeline

2. **Przygotowanie środowiska** (2 dni)
   - Setup test environment
   - Utworzenie baseline testów
   - Przygotowanie narzędzi monitoringu

3. **Start Fazy 1** (jeśli GO)
   - StreamingIndicatorEngine refactoring
   - Daily standups
   - Progress tracking

---

## Appendix A: Detailed Risk Register

| # | Ryzyko | Prawdop. | Wpływ | Severity | Mitigacja | Owner |
|---|--------|----------|-------|----------|-----------|--------|
| R1 | Zmiana zachowania kalkulacji wskaźników | WYSOKIE | KRYTYCZNY | P0 | Golden Master Testing, Historical Data Validation | Tech Lead |
| R2 | Broken dependencies i import cycles | ŚREDNIE | WYSOKI | P1 | Clear Dependency Hierarchy, Import Validation Tests | Developer |
| R3 | Memory leaks w nowej strukturze | ŚREDNIE | WYSOKI | P1 | Memory Profiling, Long-Running Tests | Developer |
| R4 | Performance degradation | NISKIE | ŚREDNI | P2 | Benchmark Tests, Profiling Hot Paths | Developer |
| R5 | Breaking existing API contracts | ŚREDNIE | KRYTYCZNY | P0 | API Compatibility Layer, Contract Tests | Tech Lead |
| R6 | WebSocket connection drops | ŚREDNIE | WYSOKI | P1 | Connection Stability Tests | Developer |
| R7 | Authentication bypass | NISKIE | KRYTYCZNY | P0 | Security Audit, Auth Flow Tests | Security Lead |
| R8 | Data loss podczas reconnection | ŚREDNIE | WYSOKI | P1 | Reconnection Flow Tests | Developer |
| R9 | Incorrect orderbook reconstruction | NISKIE/ŚREDNIE | WYSOKI | P1 | Orderbook Validation, Golden Master | Developer |
| R10 | Rate limiting violations | NISKIE | ŚREDNI | P2 | Rate Limit Tests | Developer |

**Całkowity Severity Score:** 24 (WYSOKI)
**Wymaga:** Szczegółowe planowanie i monitoring

---

## Appendix B: Testing Strategy Matrix

| Komponent | Unit Tests | Integration Tests | System Tests | Performance Tests | Security Tests |
|-----------|------------|-------------------|--------------|-------------------|----------------|
| StreamingIndicatorEngine | ✅ (>90%) | ✅ | ✅ Backtest | ✅ 24h Memory | ❌ |
| CacheManager | ✅ | ✅ | ❌ | ✅ Benchmark | ❌ |
| CalculatorCoordinator | ✅ (>95%) | ✅ | ✅ Golden Master | ✅ Hot Path | ❌ |
| MemoryMonitor | ✅ | ✅ | ✅ 24h Run | ✅ | ❌ |
| WebSocketAPIServer | ✅ (>85%) | ✅ | ✅ | ✅ Load Test | ✅ |
| SessionManager | ✅ | ✅ | ❌ | ❌ | ✅ Auth Tests |
| MexcWebSocketAdapter | ✅ (>85%) | ✅ Mock | ✅ Live Test | ✅ Load Test | ❌ |
| MessageProcessors | ✅ | ✅ | ✅ Golden Master | ✅ | ❌ |

**Całkowity Coverage Target:** >88% (weighted average)

---

**Dokument przygotowany przez:** Claude (AI Code Assistant)
**Data:** 2025-11-02
**Wersja:** 1.0
**Status:** DRAFT - Awaiting Stakeholder Review
