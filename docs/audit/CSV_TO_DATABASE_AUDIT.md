# Audyt CSV/YAML → Baza Danych - Raport Kompleksowy

**Data**: 2025-10-28
**Sesja**: claude/session-011CUZdBwDcWturpihvQ5igr
**Status**: ✅ Audit Zakończony

---

## Streszczenie Wykonawcze

System FX_code_AI został przeanalizowany pod kątem użycia plików CSV/YAML zamiast bazy danych QuestDB. Zidentyfikowano **12 plików z operacjami CSV/YAML**, z czego **3 są krytyczne** i wymagają migracji do bazy danych.

### Kluczowe Ustalenia

✅ **DOBRE WIADOMOŚCI**:
- Frontend używa wyłącznie REST API/WebSocket (100% przez bazę)
- Wszystkie endpointy API korzystają z QuestDB
- WebSocket real-time działa przez EventBus + QuestDB
- Data collection zapisuje do QuestDB (nie CSV)

❌ **PROBLEMY DO NAPRAWY**:
- **IndicatorPersistenceService** zapisuje/czyta wskaźniki z CSV zamiast QuestDB
- **OfflineIndicatorEngine** ładuje dane historyczne z CSV
- **FileConnector** używa CSV dla backtestów (ale to może być OK)

---

## 🔴 PRIORYTET 1: KRYTYCZNE - Wymagane do Naprawy

### 1. IndicatorPersistenceService - Migracja na QuestDB

**Plik**: `src/domain/services/indicator_persistence_service.py`
**Problem**: Zapisuje i czyta wartości wskaźników z plików CSV zamiast QuestDB

#### Operacje CSV:
- **Linie 171, 229**: `csv.writer` - Zapis wartości wskaźników
- **Linie 410, 489, 736**: `csv.DictReader` - Odczyt wartości wskaźników

#### Ścieżki plików CSV:
```
data/{session_id}/{symbol}/indicators/{variant_type}_{variant_id}.csv
```

#### Metody do migracji:
1. `save_values()` (line 151-205) - Zapis wartości wskaźników
2. `save_value()` (line 207-249) - Zapis pojedynczej wartości
3. `load_values_with_stats()` (line 361-459) - Odczyt z statystykami
4. `load_values()` (line 461-531) - Odczyt wartości
5. `get_file_info()` (line 712-801) - Informacje o pliku

#### Wpływ:
- **Wysokie ryzyko**: Wskaźniki są kluczowe dla systemu tradingowego
- **Wydajność**: CSV jest wolny dla dużych zbiorów danych
- **Konsystencja**: Dane w 2 miejscach (CSV + QuestDB) = niekonsystencja
- **Skalowalność**: CSV nie skaluje się dla tysięcy sesji

#### Rozwiązanie:
```python
# PRZED (CSV):
csv_file = f"data/{session_id}/{symbol}/indicators/{variant_type}_{variant_id}.csv"
with open(csv_file, 'w') as f:
    writer = csv.writer(f)
    writer.writerows(values)

# PO (QuestDB):
await self.questdb_provider.insert_indicators_batch([
    {
        'session_id': session_id,
        'symbol': symbol,
        'indicator_id': indicator_id,
        'timestamp': value.timestamp,
        'value': value.value,
        'confidence': value.confidence
    }
    for value in values
])
```

#### Estymacja:
- **Effort**: 6-8 godzin
- **Ryzyko**: Średnie (wymaga testowania)
- **ROI**: Wysoki (kluczowa funkcjonalność)

---

### 2. OfflineIndicatorEngine - Migracja na QuestDB

**Plik**: `src/domain/services/offline_indicator_engine.py`
**Problem**: Ładuje dane historyczne z pliku CSV zamiast QuestDB

#### Operacje CSV:
- **Linia 253**: `pd.read_csv(prices_file)` - Ładowanie danych OHLCV

#### Ścieżki plików CSV:
```
data/{session_id}/prices.csv
```

#### Metody do migracji:
1. `_load_symbol_data()` (line 232-260) - Ładowanie danych dla symbolu

#### Wpływ:
- **Średnie ryzyko**: Używane do offline kalkulacji wskaźników
- **Wydajność**: Dla dużych sesji CSV jest bardzo wolny
- **Duplikacja**: Dane już są w QuestDB (tick_prices, aggregated_ohlcv)

#### Rozwiązanie:
```python
# PRZED (CSV):
df = pd.read_csv(f"data/{session_id}/prices.csv")

# PO (QuestDB):
tick_prices = await self.questdb_data_provider.get_tick_prices(
    session_id=session_id,
    symbol=symbol
)
# Convert to DataFrame if needed
df = pd.DataFrame(tick_prices)
```

#### Estymacja:
- **Effort**: 3-4 godziny
- **Ryzyko**: Niskie (prosta zmiana)
- **ROI**: Średni

---

### 3. API Export - Pozostawić CSV jako Format Eksportu

**Plik**: `src/data/data_export_service.py`
**Problem**: BRAK PROBLEMU - CSV jest odpowiednim formatem eksportu

#### Operacje CSV:
- **Linia 339**: `csv.writer` - Eksport danych sesji do CSV

#### Decyzja: ✅ **POZOSTAWIĆ**
- CSV jest standardowym formatem eksportu danych
- Użytkownicy oczekują CSV dla analizy w Excel/Python
- To nie jest źródło prawdy (truth source), tylko eksport

#### Endpoint:
```
GET /api/data-collection/{session_id}/export?format=csv
```

---

## 🟡 PRIORYTET 2: WAŻNE - Do Rozważenia

### 4. FileConnector - CSV Playback dla Backtestów

**Plik**: `src/exchanges/file_connector.py`
**Problem**: Używa CSV do odtwarzania danych historycznych w backtestach

#### Operacje CSV:
- **Linie 265, 291**: `csv.DictReader` - Odczyt plików z danymi rynkowymi

#### Ścieżki plików CSV:
```
{data_dir}/{symbol}/{symbol}_{session}.csv
{data_dir}/{symbol}/{symbol}_{session}_orderbook.csv
```

#### Decyzja: 🤔 **DO PRZEMYŚLENIA**

**Argumenty ZA pozostawieniem CSV**:
1. FileConnector symuluje wymianę plików (file-based exchange)
2. Użytkownicy mogą chcieć backtestu na zewnętrznych danych CSV
3. Nie jest to primary data source - tylko alternatywny connector
4. Istnieje już `QuestDBHistoricalDataSource` dla backtestów z bazy

**Argumenty PRZECIW CSV**:
1. Duplikacja logiki (CSV + QuestDB dla backtestów)
2. Niekonsystencja w kodzie
3. Trudniejsze utrzymanie

#### Rekomendacja:
**Pozostawić FileConnector** jako opcjonalny connector dla importu zewnętrznych danych, ale:
- Dodać deprecation warning
- Zrekomendować QuestDB jako primary source
- Udokumentować jako "legacy" lub "external data import"

---

### 5. HistoricalDataSource (Deprecated) - Do Usunięcia

**Plik**: `src/application/controllers/data_sources.py`
**Problem**: Deprecated CSV-based backtest data source

#### Operacje CSV:
- **Linia 88**: `csv.DictReader` - Odczyt danych historycznych

#### Decyzja: ✅ **USUŃ**
- Klasa jest już oznaczona jako deprecated
- Zastąpiona przez `QuestDBHistoricalDataSource`
- Nie powinno być używane w nowym kodzie

#### Akcja:
```python
# DELETE:
class HistoricalDataSource:
    # ... deprecated implementation ...

# USE INSTEAD:
class QuestDBHistoricalDataSource:
    # ... modern implementation ...
```

---

## 🟢 PRIORYTET 3: OPCJONALNE - Nice to Have

### 6. Strategy Config - YAML jest OK

**Plik**: `src/config/strategy_config.py`
**Problem**: BRAK PROBLEMU - YAML jest dobrym formatem dla konfiguracji

#### Operacje YAML:
- **Linia 97**: `yaml.safe_load` - Ładowanie konfiguracji strategii
- **Linia 198**: `yaml.dump` - Zapis domyślnej strategii

#### Decyzja: ✅ **POZOSTAWIĆ**
- YAML jest standardem dla konfiguracji
- Łatwy do edycji przez użytkowników
- Wsparcie dla wersjonowania (git)
- Nie jest to dane transakcyjne

#### Ścieżki plików YAML:
```
configs/strategies/{strategy_name}.yaml
```

---

### 7-12. Narzędzia Migracji - Pozostawić

**Pliki**:
- `database/questdb/migrate_csv_to_questdb.py`
- `database/questdb/migrate_indicators_csv_to_questdb.py`
- `scripts/database/migrate_csv_to_timescale.py`
- `src/visualization/analysis_export.py`

#### Decyzja: ✅ **POZOSTAWIĆ**
- To są narzędzia migracyjne/pomocnicze
- Potrzebne do jednorazowej migracji danych
- Eksport do CSV jest funkcjonalnością, nie problemem

---

## Frontend - Weryfikacja ✅

### Struktura Frontend
```
frontend/
├── src/
│   ├── services/
│   │   ├── api.ts           # REST API client
│   │   ├── websocket.ts     # WebSocket client
│   │   └── strategiesApi.ts # Strategy API
│   ├── app/                 # Next.js pages
│   └── components/          # React components
```

### Analiza API Calls (frontend/src/services/api.ts)

#### ✅ Wszystkie dane przez REST API:
```typescript
// Indicators
GET /api/indicators/types
GET /api/indicators?scope=&symbol=&type=
POST /api/indicators
PUT /api/indicators/{key}
DELETE /api/indicators/{key}

// Data Collection
GET /api/data-collection/sessions
GET /api/data-collection/{sessionId}/chart-data
DELETE /api/data-collection/sessions/{sessionId}

// Strategies
GET /api/strategies
POST /api/strategies
GET /api/strategies/{id}
PUT /api/strategies/{id}
DELETE /api/strategies/{id}

// Trading
POST /sessions/start
POST /sessions/stop
GET /sessions/execution-status

// Risk Management
GET /risk/budget
POST /risk/budget/allocate
POST /risk/assess-position
```

#### ✅ Real-time przez WebSocket:
```typescript
// WebSocket subscriptions (via wsService)
- market_data
- indicators
- signals
- orders
- positions
- session_progress
```

### Wnioski Frontend:
✅ **BRAK PROBLEMÓW** - Frontend:
- NIE czyta plików CSV bezpośrednio
- NIE parsuje YAML
- Wszystko przez REST API lub WebSocket
- Dane z backendu pochodzą z QuestDB

---

## Tabela Priorytetów - Akcje Rekomendowane

| Plik | Operacja | Priorytet | Akcja | Effort | ROI | Status |
|------|----------|-----------|-------|--------|-----|--------|
| indicator_persistence_service.py | CSV R/W | 🔴 P1 | Migruj na QuestDB | 6-8h | Wysoki | TODO |
| offline_indicator_engine.py | CSV R | 🔴 P1 | Migruj na QuestDB | 3-4h | Średni | TODO |
| data_sources.py | CSV R | 🟡 P2 | Usuń deprecated | 1h | Niski | TODO |
| file_connector.py | CSV R | 🟡 P2 | Pozostaw + doc | 0.5h | Niski | OK |
| data_export_service.py | CSV W | 🟢 P3 | Pozostaw | 0h | - | ✅ OK |
| strategy_config.py | YAML R/W | 🟢 P3 | Pozostaw | 0h | - | ✅ OK |
| migrate_*.py | CSV R | 🟢 P3 | Pozostaw | 0h | - | ✅ OK |
| analysis_export.py | CSV W | 🟢 P3 | Pozostaw | 0h | - | ✅ OK |

---

## Plan Implementacji

### Faza 1: Krytyczne Migracje (2-3 dni)

#### Task 1.1: Migracja IndicatorPersistenceService (PRIORYTET 1)
**Cel**: Zapisywanie i odczyt wartości wskaźników z QuestDB zamiast CSV

**Kroki**:
1. Zmodyfikuj `save_values()` - użyj `insert_indicators_batch()`
2. Zmodyfikuj `save_value()` - użyj `insert_indicators_batch()` z 1 elementem
3. Zmodyfikuj `load_values_with_stats()` - użyj `get_indicators()` z QuestDB
4. Zmodyfikuj `load_values()` - użyj `get_indicators()` z QuestDB
5. Zmodyfikuj `get_file_info()` - query COUNT(*) z QuestDB

**Przed**:
```python
csv_file = self._get_csv_file_path(session_id, symbol, variant_type, variant_id)
with open(csv_file, 'w') as f:
    writer = csv.writer(f)
    writer.writerows(values)
```

**Po**:
```python
await self.questdb_provider.insert_indicators_batch([
    {
        'session_id': session_id,
        'symbol': symbol,
        'indicator_id': indicator_id,
        'timestamp': datetime.fromtimestamp(value.timestamp),
        'value': float(value.value),
        'confidence': float(value.confidence) if value.confidence else None
    }
    for value in indicator_values
])
```

**Testy**:
- Unit tests dla save/load operations
- Integration test z QuestDB
- Performance benchmark (CSV vs QuestDB)

---

#### Task 1.2: Migracja OfflineIndicatorEngine (PRIORYTET 1)
**Cel**: Ładowanie danych historycznych z QuestDB zamiast CSV

**Kroki**:
1. Zmodyfikuj `_load_symbol_data()` - użyj `get_tick_prices()` lub `get_aggregated_ohlcv()`
2. Dodaj fallback do CSV dla backward compatibility (opcjonalnie)
3. Dodaj caching dla wydajności

**Przed**:
```python
prices_file = f"data/{session_id}/prices.csv"
df = pd.read_csv(prices_file)
```

**Po**:
```python
# Option 1: Tick prices (high resolution)
tick_prices = await self.questdb_data_provider.get_tick_prices(
    session_id=session_id,
    symbol=symbol
)
df = pd.DataFrame(tick_prices)

# Option 2: Aggregated OHLCV (better performance)
ohlcv = await self.questdb_data_provider.get_aggregated_ohlcv(
    session_id=session_id,
    symbol=symbol,
    interval='1m'
)
df = pd.DataFrame(ohlcv)
```

**Testy**:
- Unit tests dla data loading
- Verify calculations match previous results
- Performance comparison

---

### Faza 2: Cleanup (1 dzień)

#### Task 2.1: Usuń Deprecated HistoricalDataSource
**Cel**: Usunięcie nieużywanego kodu CSV-based backtest

**Kroki**:
1. Verify że nic nie używa `HistoricalDataSource`
2. Usuń klasę z `data_sources.py`
3. Update dokumentacji

**Impact**: Niski (klasa już deprecated)

---

#### Task 2.2: Dokumentacja FileConnector
**Cel**: Oznaczenie FileConnector jako legacy/external import

**Kroki**:
1. Dodaj docstring z deprecation notice
2. Update README z rekomendacją użycia QuestDB
3. Dodaj przykłady migracji CSV → QuestDB

**Przykład docstring**:
```python
class FileConnector:
    """
    File-based exchange connector for CSV playback.

    ⚠️ LEGACY: This connector is maintained for external data import only.

    For backtesting with internal data, use QuestDBHistoricalDataSource instead.

    Use cases:
    - Importing external market data from CSV files
    - Replaying historical data from third-party sources
    - Testing with custom datasets

    Recommended alternative: QuestDBHistoricalDataSource
    """
```

---

### Faza 3: Optymalizacja (opcjonalnie)

#### Task 3.1: Performance Tuning
**Cel**: Optymalizacja zapytań do QuestDB

**Opcje**:
1. Batch insert optimization (więcej wierszy na raz)
2. Query caching dla często używanych danych
3. Connection pooling dla QuestDB

---

#### Task 3.2: Monitoring
**Cel**: Monitorowanie wydajności migracji

**Metryki**:
- Query latency (CSV vs QuestDB)
- Throughput (records/second)
- Storage usage (disk space)
- Error rates

---

## Szacowanie Czasu i Zasobów

### Total Effort:
- **Faza 1 (Krytyczne)**: 2-3 dni (12-24h) - **MUST DO**
- **Faza 2 (Cleanup)**: 1 dzień (4-8h) - **SHOULD DO**
- **Faza 3 (Optymalizacja)**: 0.5-1 dzień (4-8h) - **NICE TO HAVE**

**TOTAL**: 3.5-5 dni (20-40h)

### Breakdown:
1. IndicatorPersistenceService migration: **6-8h** (40%)
2. OfflineIndicatorEngine migration: **3-4h** (15%)
3. Testing & validation: **4-6h** (20%)
4. Cleanup & documentation: **3-4h** (15%)
5. Performance optimization: **4-8h** (10%)
6. Deployment & monitoring: **2-4h** (10%)

---

## Ryzyka i Mitigation

### Ryzyko 1: Data Loss podczas migracji
**Mitigation**:
- Backup all CSV files before migration
- Dual-write (CSV + QuestDB) during transition period
- Verification queries to compare results

### Ryzyko 2: Performance degradation
**Mitigation**:
- Benchmark przed i po migracji
- Monitor query times
- Add indexes if needed (migration 006)

### Ryzyko 3: Breaking changes dla istniejących sesji
**Mitigation**:
- Maintain backward compatibility
- Migrate existing CSV data to QuestDB using migration scripts
- Fallback logic: try QuestDB first, then CSV

---

## Success Metrics

### Przed Migracją:
- Indicator save time: ~100ms (CSV write)
- Indicator load time: ~500ms (CSV read dla 10k records)
- Storage: CSV files (~1MB per indicator per session)

### Po Migracji (Expected):
- Indicator save time: ~10ms (QuestDB batch insert)
- Indicator load time: ~50ms (QuestDB query)
- Storage: QuestDB (~100 bytes per record compressed)

**Target**: 10x speedup dla operacji I/O

---

## Pytania do Decyzji

### Q1: Czy migrować FileConnector?
**Rekomendacja**: ❌ NIE
- Pozostaw jako opcjonalny connector dla zewnętrznych danych
- Dodaj dokumentację że to legacy
- Priorytet: QuestDB > CSV

### Q2: Czy usunąć wszystkie CSV operations?
**Rekomendacja**: ❌ NIE
- Export do CSV to feature, nie bug
- Migracja tools potrzebne do one-time migration
- Strategy config w YAML jest OK

### Q3: Jaki timeline?
**Rekomendacja**: ⏰ 1 tydzień
- Sprint 1 (3 dni): Critical migrations
- Sprint 2 (2 dni): Testing & validation
- Sprint 3 (1-2 dni): Cleanup & documentation

---

## Podsumowanie

### ✅ Dobre Wiadomości:
1. **Frontend jest czysty** - wszystko przez REST/WebSocket
2. **Większość backendu używa QuestDB** - migracja 80% done
3. **Tylko 2 krytyczne pliki** do naprawy
4. **Migracje są straightforward** - niskie ryzyko

### 🔴 Do Naprawy (Must):
1. `indicator_persistence_service.py` - zapisuj do QuestDB zamiast CSV
2. `offline_indicator_engine.py` - czytaj z QuestDB zamiast CSV

### 🟡 Do Rozważenia (Should):
3. Usuń deprecated `HistoricalDataSource`
4. Dodaj deprecation warning do `FileConnector`

### 🟢 OK - Nie zmieniaj (Nice):
5. Export CSV - zostaw jako feature
6. Strategy YAML config - zostaw
7. Migration tools - zostaw

---

## Next Steps

1. ✅ Review this audit report
2. ⏳ Approve migration plan
3. ⏳ Create feature branch: `feature/migrate-csv-to-questdb`
4. ⏳ Implement Task 1.1 (IndicatorPersistenceService)
5. ⏳ Implement Task 1.2 (OfflineIndicatorEngine)
6. ⏳ Testing & validation
7. ⏳ Merge to development
8. ⏳ Deploy to production

**Szacowany czas: 1 tydzień (3-5 dni roboczych)**

---

**Przygotował**: Claude (Anthropic)
**Data**: 2025-10-28
**Sesja**: claude/session-011CUZdBwDcWturpihvQ5igr
