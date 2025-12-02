# Checklist Refaktoryzacji - 3 Przeładowane Pliki

## 📋 FAZA 0: Przygotowanie

### Środowisko
- [ ] Utworzenie feature branch: `refactor/streaming-indicator-engine`
- [ ] Setup test environment z izolowaną bazą danych
- [ ] Backup obecnych danych testowych
- [ ] Przygotowanie narzędzi do profilowania pamięci (memory_profiler, tracemalloc)
- [ ] Setup CI/CD pipeline dla nowej struktury

### Baseline Tests
- [ ] Uruchomienie wszystkich obecnych testów i zapisanie wyników
- [ ] Utworzenie golden master tests dla wskaźników (1000+ próbek)
- [ ] Benchmark performance obecnej implementacji
- [ ] Memory profiling obecnej implementacji (24h run)
- [ ] Zapisanie baseline metrics w `tests/baseline/`

### Dokumentacja
- [ ] Przegląd OVERLOADED_FILES_ANALYSIS.md przez zespół
- [ ] Decyzja GO/NO-GO od stakeholderów
- [ ] Ustalenie timeline i milestones
- [ ] Przypisanie ownership dla każdego ryzyka

---

## 🎯 FAZA 1: StreamingIndicatorEngine - Przygotowanie (2h)

### Struktura Katalogów
- [ ] Utworzenie `src/domain/services/streaming_indicator_engine/`
- [ ] Utworzenie podkatalogów: `core/`, `calculation/`, `caching/`, `memory/`, `health/`, `variants/`
- [ ] Utworzenie wszystkich `__init__.py`
- [ ] Setup import paths w głównym `__init__.py`

### Przeniesienie Typów
- [ ] Utworzenie `core/types.py`
- [ ] Przeniesienie `IndicatorType` enum
- [ ] Przeniesienie `VariantType` enum
- [ ] Przeniesienie `IndicatorValue` dataclass
- [ ] Przeniesienie `TimeDrivenSchedule` dataclass
- [ ] Przeniesienie `StreamingIndicator` dataclass
- [ ] Przeniesienie `IndicatorVariant` dataclass
- [ ] Przeniesienie `SystemIndicatorDefinition` dataclass
- [ ] Test że wszystkie imports działają

### Baseline Integration Tests
- [ ] Test `test_add_indicator_baseline()`
- [ ] Test `test_calculate_sma_baseline()`
- [ ] Test `test_calculate_twpa_baseline()`
- [ ] Test `test_memory_usage_baseline()`
- [ ] Test `test_cache_hit_rate_baseline()`
- [ ] Wszystkie testy przechodzą ✅

**Checkpoint #1:** Commit "refactor: prepare streaming_indicator_engine structure"

---

## 🧩 FAZA 2A: CacheManager Extraction (2h)

### Implementacja
- [ ] Utworzenie `caching/cache_manager.py`
- [ ] Utworzenie klasy `CacheManager`
- [ ] Przeniesienie metody `_get_cache_key()` → `get_cache_key()`
- [ ] Przeniesienie metody `_get_cached_value()` → `get()`
- [ ] Przeniesienie metody `_set_cached_value()` → `set()`
- [ ] Przeniesienie metody `_cleanup_cache()` → `cleanup()`
- [ ] Przeniesienie metody `_calculate_adaptive_ttl()` → `calculate_ttl()`
- [ ] Przeniesienie metody `_enforce_cache_limits()` → `enforce_limits()`
- [ ] Przeniesienie metody `_evict_cache_entries()` → `evict()`
- [ ] Przeniesienie metody `_record_cache_access()` → `record_access()`
- [ ] Przeniesienie metody `_calculate_cache_hit_rate()` → `get_hit_rate()`
- [ ] Przeniesienie wszystkich cache-related fields z __init__

### Unit Tests
- [ ] Test `test_cache_get_set()`
- [ ] Test `test_cache_ttl_expiration()`
- [ ] Test `test_cache_eviction_lru()`
- [ ] Test `test_cache_hit_rate_calculation()`
- [ ] Test `test_cache_cleanup()`
- [ ] Test `test_cache_adaptive_ttl()`
- [ ] Coverage > 90% ✅

### Integration
- [ ] Dodanie `self._cache_manager = CacheManager(...)` do `StreamingIndicatorEngine.__init__()`
- [ ] Aktualizacja wszystkich wywołań cache w engine do `self._cache_manager.get()` etc.
- [ ] Test że cache działa identycznie jak poprzednio
- [ ] Verify cache hit rate nie zmieniła się (±1%)

**Checkpoint #2:** Commit "refactor: extract CacheManager from StreamingIndicatorEngine"

---

## 🧩 FAZA 2B: MemoryMonitor Extraction (1.5h)

### Implementacja
- [ ] Utworzenie `memory/memory_monitor.py`
- [ ] Utworzenie klasy `MemoryMonitor`
- [ ] Przeniesienie metody `_check_memory_limits()` → `check_limits()`
- [ ] Przeniesienie metody `_detect_memory_leaks()` → `detect_leaks()`
- [ ] Przeniesienie metody `get_memory_stability_report()` → `get_stability_report()`
- [ ] Przeniesienie metody `_record_memory_sample()` → `record_sample()`
- [ ] Przeniesienie wszystkich memory-related fields

### Unit Tests
- [ ] Test `test_memory_check_limits()`
- [ ] Test `test_memory_leak_detection()`
- [ ] Test `test_memory_stability_report()`
- [ ] Test `test_memory_sample_recording()`
- [ ] Coverage > 90% ✅

### Integration
- [ ] Dodanie `self._memory_monitor = MemoryMonitor(...)` do engine
- [ ] Aktualizacja wywołań memory checks
- [ ] Test że memory monitoring działa poprawnie

**Checkpoint #3:** Commit "refactor: extract MemoryMonitor from StreamingIndicatorEngine"

---

## 🧩 FAZA 2C: HealthMonitor Extraction (1.5h)

### Implementacja
- [ ] Utworzenie `health/health_monitor.py`
- [ ] Utworzenie `health/circuit_breaker_handler.py`
- [ ] Utworzenie `health/performance_metrics.py`
- [ ] Przeniesienie metody `get_health_status()` → `HealthMonitor.get_status()`
- [ ] Przeniesienie metody `_update_health_status()` → `update_status()`
- [ ] Przeniesienie metody `_is_circuit_breaker_open()` → `CircuitBreakerHandler`
- [ ] Przeniesienie metody `_record_calculation_success()` → `CircuitBreakerHandler`
- [ ] Przeniesienie metody `_record_calculation_failure()` → `CircuitBreakerHandler`

### Unit Tests
- [ ] Test `test_health_status_reporting()`
- [ ] Test `test_circuit_breaker_open_close()`
- [ ] Test `test_performance_metrics_tracking()`
- [ ] Coverage > 85% ✅

### Integration
- [ ] Dodanie health monitors do engine
- [ ] Test że health reporting działa poprawnie

**Checkpoint #4:** Commit "refactor: extract HealthMonitor from StreamingIndicatorEngine"

---

## 🧩 FAZA 2D: CleanupCoordinator Extraction (2h)

### Implementacja
- [ ] Utworzenie `memory/cleanup_coordinator.py`
- [ ] Utworzenie klasy `CleanupCoordinator`
- [ ] Przeniesienie metody `_cleanup_expired_data()` → `cleanup_expired()`
- [ ] Przeniesienie metody `_force_cleanup()` → `force_cleanup()`
- [ ] Przeniesienie metody `_emergency_cleanup()` → `emergency_cleanup()`
- [ ] Przeniesienie metody `_cleanup_all_data_structures()` → `cleanup_all()`
- [ ] Przeniesienie metody `_should_cleanup_data()` → `should_cleanup()`

### Unit Tests
- [ ] Test `test_cleanup_expired_data()`
- [ ] Test `test_force_cleanup()`
- [ ] Test `test_emergency_cleanup()`
- [ ] Test `test_cleanup_decision_logic()`
- [ ] Coverage > 90% ✅

### Integration
- [ ] Dodanie cleanup coordinator do engine
- [ ] Test że cleanup działa poprawnie
- [ ] Verify że nie ma memory leaks

**Checkpoint #5:** Commit "refactor: extract CleanupCoordinator"

---

## ✅ MAJOR CHECKPOINT: Faza 2 Complete

### Weryfikacja
- [ ] Uruchomienie wszystkich testów unit
- [ ] Uruchomienie wszystkich testów integration
- [ ] Backtest na 3 sesjach historycznych
- [ ] Porównanie wyników z baseline (różnice < 0.01%)
- [ ] Memory profiling (24h run) - wzrost pamięci < 10MB/h
- [ ] Performance benchmark - degradacja < 5%

**Jeśli wszystko ✅:** Kontynuuj do Fazy 3
**Jeśli problemy ❌:** Fix i re-test przed kontynuacją

---

## 🧮 FAZA 3A: TechnicalIndicatorsCalculator (3h)

### Implementacja
- [ ] Utworzenie `calculation/technical_indicators.py`
- [ ] Utworzenie klasy `TechnicalIndicatorsCalculator`
- [ ] Przeniesienie metody `_calculate_sma_registered()` → `calculate_sma()`
- [ ] Przeniesienie metody `_calculate_ema_registered()` → `calculate_ema()`
- [ ] Przeniesienie metody `_calculate_rsi_registered()` → `calculate_rsi()`
- [ ] Przeniesienie metody `_calculate_macd_registered()` → `calculate_macd()`
- [ ] Przeniesienie metody `_calculate_bollinger_bands_registered()` → `calculate_bollinger_bands()`
- [ ] Przeniesienie pomocniczych metod (np. `_calculate_ema()`, `_calculate_rsi()`)

### Unit Tests (Golden Master)
- [ ] Test `test_sma_golden_master()` - 100 przypadków testowych
- [ ] Test `test_ema_golden_master()` - 100 przypadków testowych
- [ ] Test `test_rsi_golden_master()` - 100 przypadków testowych
- [ ] Test `test_macd_golden_master()` - 100 przypadków testowych
- [ ] Test `test_bollinger_bands_golden_master()` - 100 przypadków testowych
- [ ] Wszystkie wartości dopasowane do 4 miejsc po przecinku ✅
- [ ] Coverage > 95% ✅

### Integration
- [ ] Integration z CalculatorCoordinator
- [ ] Test pełnego flow kalkulacji
- [ ] Verify że wyniki są identyczne z baseline

**Checkpoint #6:** Commit "refactor: extract TechnicalIndicatorsCalculator"

---

## 🧮 FAZA 3B: CustomIndicatorsCalculator (4h)

### Implementacja
- [ ] Utworzenie `calculation/custom_indicators.py`
- [ ] Utworzenie klasy `CustomIndicatorsCalculator`
- [ ] Przeniesienie wszystkich metod TWPA-related
  - [ ] `_calculate_pump_magnitude_pct_registered()`
  - [ ] `_calculate_volume_surge_ratio_registered()`
  - [ ] `_calculate_price_velocity_registered()`
  - [ ] `_calculate_velocity_cascade()`
  - [ ] `_calculate_velocity_acceleration()`
  - [ ] `_calculate_max_twpa()`
  - [ ] `_calculate_min_twpa()`
  - [ ] `_calculate_vtwpa()`
  - [ ] `_get_twpa_series_for_window()`
  - [ ] `_calculate_single_velocity()`
  - [ ] `_calculate_momentum_streak()`
  - [ ] `_calculate_direction_consistency()`

### Unit Tests (Golden Master)
- [ ] Test `test_twpa_golden_master()` - 200 przypadków
- [ ] Test `test_velocity_golden_master()` - 200 przypadków
- [ ] Test `test_volume_surge_golden_master()` - 100 przypadków
- [ ] Test `test_velocity_cascade_golden_master()` - 100 przypadków
- [ ] Test `test_velocity_acceleration_golden_master()` - 100 przypadków
- [ ] Test edge cases (empty windows, single data point, etc.)
- [ ] Wszystkie wartości dokładne do 4 miejsc po przecinku ✅
- [ ] Coverage > 95% ✅

### Integration
- [ ] Integration z CalculatorCoordinator
- [ ] Test z danymi historycznymi (10 sesji)
- [ ] Porównanie wszystkich wartości z baseline (< 0.01% różnicy)

**Checkpoint #7:** Commit "refactor: extract CustomIndicatorsCalculator"

---

## 🧮 FAZA 3C: RiskIndicatorsCalculator (2h)

### Implementacja
- [ ] Utworzenie `calculation/risk_indicators.py`
- [ ] Utworzenie klasy `RiskIndicatorsCalculator`
- [ ] Przeniesienie metod:
  - [ ] `_calculate_volatility_registered()`
  - [ ] `_calculate_risk_level_registered()`
  - [ ] `_calculate_price_volatility()`
  - [ ] `_calculate_deal_size_volatility()`

### Unit Tests
- [ ] Test `test_volatility_calculation()`
- [ ] Test `test_risk_level_calculation()`
- [ ] Test edge cases
- [ ] Coverage > 90% ✅

**Checkpoint #8:** Commit "refactor: extract RiskIndicatorsCalculator"

---

## 🧮 FAZA 3D: MarketIndicatorsCalculator (2h)

### Implementacja
- [ ] Utworzenie `calculation/market_indicators.py`
- [ ] Utworzenie klasy `MarketIndicatorsCalculator`
- [ ] Przeniesienie metod:
  - [ ] `_calculate_trade_size_momentum()`
  - [ ] `_calculate_mid_price_velocity()`
  - [ ] `_calculate_total_liquidity()`
  - [ ] `_calculate_liquidity_ratio()`
  - [ ] `_calculate_liquidity_drain_index()`
  - [ ] `_calculate_deal_vs_mid_deviation()`
  - [ ] `_calculate_inter_deal_intervals()`
  - [ ] `_calculate_decision_density_acceleration()`
  - [ ] `_calculate_trade_clustering_coefficient()`

### Unit Tests
- [ ] Test każdej metody osobno
- [ ] Test z rzeczywistymi danymi orderbook
- [ ] Coverage > 90% ✅

**Checkpoint #9:** Commit "refactor: extract MarketIndicatorsCalculator"

---

## 🧮 FAZA 3E: CalculatorCoordinator (2h)

### Implementacja
- [ ] Utworzenie `calculation/calculator_coordinator.py`
- [ ] Utworzenie klasy `CalculatorCoordinator`
- [ ] Implementacja metody `calculate()` z routing logic
- [ ] Integration wszystkich specjalistycznych kalkulatorów
- [ ] Przeniesienie metody `_calculate_indicator_value_incremental()`

### Unit Tests
- [ ] Test routing do właściwego kalkulatora
- [ ] Test dla wszystkich typów wskaźników
- [ ] Test error handling
- [ ] Coverage > 90% ✅

### Integration
- [ ] Dodanie `self._calculator = CalculatorCoordinator(...)` do engine
- [ ] Aktualizacja wszystkich wywołań kalkulacji
- [ ] Test że wszystkie wskaźniki działają poprawnie

**Checkpoint #10:** Commit "refactor: extract CalculatorCoordinator"

---

## ✅ MAJOR CHECKPOINT: Faza 3 Complete

### Weryfikacja
- [ ] Uruchomienie wszystkich testów unit (>90% coverage)
- [ ] Uruchomienie wszystkich golden master tests (100% pass)
- [ ] Backtest na 10 sesjach historycznych
- [ ] Porównanie WSZYSTKICH wartości wskaźników z baseline
  - [ ] Różnice < 0.01% dla TWPA
  - [ ] Różnice < 0.01% dla Velocity
  - [ ] Różnice < 0.01% dla Volume Surge
  - [ ] Różnice < 0.01% dla SMA/EMA/RSI/MACD
- [ ] Performance benchmark - degradacja < 5%
- [ ] Memory profiling - brak memory leaks

**Jeśli wszystko ✅:** Kontynuuj do Fazy 4
**Jeśli problemy ❌:** STOP, fix critical issues przed kontynuacją

---

## 🔧 FAZA 4: Pozostałe Komponenty (3h)

### VariantManager
- [ ] Utworzenie `variants/variant_manager.py`
- [ ] Przeniesienie logiki zarządzania wariantami
- [ ] Unit tests (>90% coverage)
- [ ] Integration test

### IncrementalCalculator
- [ ] Utworzenie `calculation/incremental_calculator.py`
- [ ] Przeniesienie incremental calculation logic
- [ ] Unit tests (>90% coverage)
- [ ] Verify performance (musi być O(1))

### IndicatorRegistry
- [ ] Utworzenie `core/indicator_registry.py`
- [ ] Przeniesienie registration logic
- [ ] Unit tests (>85% coverage)

**Checkpoint #11:** Commit "refactor: extract remaining components"

---

## 🏗️ FAZA 5: Finalna Integracja (2h)

### Główna Klasa Engine
- [ ] Aktualizacja `core/engine.py` - tylko orchestration
- [ ] Usunięcie wszystkich przeniesionychmetod
- [ ] Zachowanie publicznego API bez zmian
- [ ] Dodanie wszystkich komponentów do __init__
- [ ] Delegacja do komponentów

### Public API
- [ ] Verify że wszystkie publiczne metody działają
  - [ ] `add_indicator()`
  - [ ] `list_indicators()`
  - [ ] `get_health_status()`
  - [ ] `get_system_indicators()`
  - [ ] `get_memory_stability_report()`
- [ ] Test backward compatibility

### Cleanup
- [ ] Usunięcie starego pliku `streaming_indicator_engine.py`
- [ ] Aktualizacja wszystkich importów w codebase
- [ ] Usunięcie dead code
- [ ] Usunięcie duplikacji

**Checkpoint #12:** Commit "refactor: finalize StreamingIndicatorEngine refactoring"

---

## ✅ FINAL CHECKPOINT: StreamingIndicatorEngine Complete

### Full System Verification
- [ ] Wszystkie testy unit przechodzą (>90% coverage)
- [ ] Wszystkie testy integration przechodzą
- [ ] Wszystkie testy system przechodzą
- [ ] Backtest na 20 sesjach historycznych - wyniki identyczne z baseline
- [ ] Live simulation (paper trading) - 4 godziny bez błędów
- [ ] Performance benchmark - nie gorszy niż baseline ±5%
- [ ] Memory profiling 24h - wzrost < 10MB/h
- [ ] Load test - 1000 indicators, 100 symbols - stabilny

### Dokumentacja
- [ ] Aktualizacja `docs/architecture/STREAMING_INDICATOR_ENGINE.md`
- [ ] Dokumentacja nowej struktury katalogów
- [ ] Diagramy architektury (przed/po)
- [ ] Migration guide dla innych developerów
- [ ] Aktualizacja CLAUDE.md

**Jeśli wszystko ✅:** Merge do main branch
**Jeśli problemy ❌:** Rollback i analiza root cause

---

## 🌐 FAZA 6: WebSocketServer (Opcjonalne - 7 dni)

_Checklist szczegółowy dla WebSocketServer będzie utworzony po zakończeniu Fazy 5_

### High-Level Tasks
- [ ] Ekstrakcja ConnectionLifecycle (2h)
- [ ] Ekstrakcja SessionManager (2h)
- [ ] Ekstrakcja TopicCoordinator (2h)
- [ ] Integracja i weryfikacja (1h)
- [ ] Full system tests

---

## 🔌 FAZA 7: MexcWebSocketAdapter (Opcjonalne - 10 dni)

_Checklist szczegółowy dla MexcWebSocketAdapter będzie utworzony po zakończeniu Fazy 6_

### High-Level Tasks
- [ ] Ekstrakcja MessageProcessors (3h)
- [ ] Ekstrakcja ConnectionPool (3h)
- [ ] Ekstrakcja SubscriptionCoordinator (2h)
- [ ] Ekstrakcja ReconnectionManager (1h)
- [ ] Integracja i weryfikacja (1h)
- [ ] Live tests z MEXC

---

## 📊 KPIs Tracking

### Maintainability Index
- Baseline: ~15-20
- Current: _____
- Target: >60

### Average File Length
- Baseline: 3,941 linii (top 3)
- Current: _____
- Target: <500 linii

### Test Coverage
- Baseline: ~70%
- Current: _____
- Target: >90%

### Bugs Found
- P0 bugs: _____
- P1 bugs: _____
- P2 bugs: _____
- Target: <3 P0/P1 bugs

### Performance
- Calculation time baseline: _____ ms
- Calculation time current: _____ ms
- Target: ±5% of baseline

### Memory Usage
- Memory baseline (1h): _____ MB
- Memory current (1h): _____ MB
- Memory growth rate: _____ MB/h
- Target: <10 MB/h growth

---

## 🚨 Emergency Rollback Procedure

Jeśli napotkasz krytyczne problemy:

1. **STOP** - nie kontynuuj refaktoryzacji
2. **Assess** - określ severity (P0 = production broken, P1 = major feature broken, P2 = minor issues)
3. **Rollback** jeśli P0:
   ```bash
   git checkout main
   git branch -D refactor/streaming-indicator-engine
   ```
4. **Fix Forward** jeśli P1/P2:
   - Stwórz hotfix branch
   - Fix issue
   - Re-run wszystkie testy
   - Kontynuuj refaktoryzację

5. **Document** - dodaj do lessons learned

---

**Last Updated:** 2025-11-02
**Owner:** Development Team
**Reviewer:** Tech Lead
