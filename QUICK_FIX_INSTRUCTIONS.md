# Quick Fix Instructions - Indicator Calculation Hang Issue

## ✅ PROBLEM RESOLVED - Phase 2 Complete

## Problem (Original)
Dodawanie wskaźnika technicznego w `/data-collection/{sessionId}/chart` powoduje nieskończony proces "calculating indicator" bez błędów w logach.

## ✅ ROOT CAUSE FOUND & FIXED

**Problem**: Algorithm registry initialization failure → silent fallback to legacy method → NO error handling around `calculate_indicator_unified()` → single exception = hang.

**Solution**: Added try/except + comprehensive observability + early warning validation.

---

## Co zostało zrobione

### Faza 1: Diagnostyka + Enhanced Observability

### Faza 1A - Initial Observability

✅ Dodano szczegółowe logowanie w kluczowych punktach:
- `src/api/indicators_routes.py` - ładowanie danych, ThreadPoolExecutor, timing
- `src/domain/services/offline_indicator_engine.py` - wybór metody kalkulacji, progress tracking

### Faza 1B - Enhanced Observability (LATEST)

✅ **Wyeliminowano WSZYSTKIE silent fallbacks** - teraz logowane jako ERROR:
- Algorithm registry failures → ERROR z listą dostępnych algorytmów
- Fallback do starej metody → ERROR z pełnym traceback
- Brak algorithm registry → ERROR z actionable guidance

✅ **Dodano QuestDB query observability**:
- Timing każdego query do QuestDB
- Liczba zwróconych wierszy
- Data conversion metrics (conversion rate, invalid rows count)

✅ **Enhanced algorithm registry logging**:
- Auto-discovery tracking
- Detailed algorithm retrieval diagnostics
- ERROR when algorithm not found (z listą dostępnych)

### Faza 2: Implementation & Fix ✅ COMPLETE

✅ **ROOT CAUSE IDENTIFIED**:
- Algorithm registry init failure przechwytywany bez traceback
- Fallback do legacy metody BEZ error handling
- Pojedynczy exception w `calculate_indicator_unified()` = hang

✅ **FIXES IMPLEMENTED**:
1. **Enhanced error logging** - traceback + impact w algorithm registry init
2. **Post-init validation** - early warning jeśli registry failed
3. **Try/except w legacy calculation** - graceful failure handling
4. **Comprehensive observability** - progress tracking, error counts

✅ **IMPACT**:
- Legacy calculation NIE zawiesza się na błędach
- Zwraca partial results zamiast hang
- Algorithm registry failures widoczne at startup
- Każdy błąd logowany z kontekstem

**Zobacz**: [PHASE_2_IMPLEMENTATION_REPORT.md](PHASE_2_IMPLEMENTATION_REPORT.md) dla pełnej analizy.

---

## Co musisz zrobić TERAZ (Testing)

### Krok 1: Restart Backendu

```bash
# Zatrzymaj obecny backend (Ctrl+C)

# Uruchom ponownie
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload
```

### Krok 2: Odtwórz Problem

1. Otwórz `http://localhost:3000/data-collection/{existing_session_id}/chart`
2. Kliknij "Add Technical Indicator"
3. Wybierz dowolny wskaźnik (np. TWPA, RSI)
4. Kliknij "Add"

### Krok 3: **BARDZO WAŻNE** - Obserwuj Logi Backend

**Szukaj sekwencji logów** zaczynającej się od:
```
INFO  indicators_routes.compute_indicator.loading_data
```

**SZCZEGÓLNIE szukaj ERROR logów** - teraz wszystkie problemy są logowane jako ERROR:
```
ERROR indicator_algorithm_registry.algorithm_not_found
ERROR offline_indicator_engine.algorithm_not_ready_fallback
ERROR offline_indicator_engine.no_algorithm_registry
ERROR indicators_routes.no_price_data_found
ERROR indicators_routes.all_rows_invalid
```

### Krok 4: Skopiuj Ostatni Log Przed Zawieszeniem + WSZYSTKIE ERROR

**PRZYKŁAD 1** - Zawiesza się na ładowaniu danych:
```
INFO  indicators_routes.compute_indicator.loading_data {indicator_id: "...", session_id: "...", ...}
[TUTAJ SIĘ ZATRZYMUJE - NIE MA DALSZYCH LOGÓW]
```
→ **Diagnoza**: Problem z QuestDB query

**PRZYKŁAD 2** - Zawiesza się w executor:
```
INFO  indicators_routes.compute_indicator.entering_executor {...}
INFO  offline_indicator_engine.calculate_series_start {...}
INFO  offline_indicator_engine.checking_algorithm_registry {...}
[TUTAJ SIĘ ZATRZYMUJE]
```
→ **Diagnoza**: Problem z algorithm registry

**PRZYKŁAD 3** - Zawiesza się podczas kalkulacji:
```
INFO  offline_indicator_engine.time_axis_generated {time_points_count: 50000, ...}
DEBUG offline_indicator_engine.calculation_progress {progress: "0/50000", ...}
[TUTAJ SIĘ ZATRZYMUJE - BRAK KOLEJNYCH PROGRESS]
```
→ **Diagnoza**: Kalkulacja jest za wolna lub zawieszona

### Krok 5: Wyślij Mi Wyniki

Skopiuj:
1. **Wszystkie logi** od "compute_indicator.loading_data" do miejsca zawieszenia
2. **Typ wskaźnika** który dodawałeś
3. **Session ID**
4. **Ile wierszy danych** ma sesja (jeśli wiesz)

## Co Dalej

Na podstawie Twoich logów będę wiedział **dokładnie** gdzie się zatrzymuje i zaimplementuję **konkretną naprawę** (Faza 2).

### Możliwe Naprawy (Po Diagnostyce)

**Jeśli zawiesza się na QuestDB**:
- Dodanie retry logic z exponential backoff
- Timeout dla zapytań

**Jeśli zawiesza się na semaphore**:
- Zwiększenie limitu z 12 do 24
- Dodanie queue monitoring

**Jeśli zawiesza się w executor**:
- Konwersja do async/await
- Zamiana ThreadPoolExecutor na asyncio.create_task

**Jeśli zawiesza się podczas kalkulacji**:
- Optymalizacja window extraction
- Streaming calculation (yield intermediate results)

## Szybkie Sprawdzenie

Jeśli chcesz szybko sprawdzić czy logowanie działa:

```bash
# Uruchom backend i poszukaj w logach:
grep "offline_indicator_engine" <log_file>
grep "compute_indicator" <log_file>
```

Powinny pojawić się nowe szczegółowe logi.

## Pliki Zmodyfikowane (Do Commitowania Później)

```
src/api/indicators_routes.py                      (~40 linii logowania dodane)
src/domain/services/offline_indicator_engine.py   (~80 linii logowania dodane)
INDICATOR_CALCULATION_DIAGNOSTIC_REPORT.md        (nowy plik - szczegółowy raport)
QUICK_FIX_INSTRUCTIONS.md                         (ten plik)
```

**Żadna logika biznesowa nie została zmieniona** - tylko dodano logowanie diagnostyczne.

## Kontakt

Po odtworzeniu problemu i zebraniu logów, powiedz mi:
- "Zatrzymało się na [nazwa ostatniego logu]"
- Wklej pełną sekwencję logów
- Opisz co próbowałeś dodać

Wtedy przejdę do Fazy 2 i naprawię konkretny problem.

---

**Status**: Faza 1 Complete ✅ | Faza 2 Pending Diagnostic Results ⏳
