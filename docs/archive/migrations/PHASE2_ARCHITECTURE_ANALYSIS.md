# Analiza Architektury - Usunięcie CSV, Przejście na QuestDB-Only

## Streszczenie Decyzji

**DECYZJA UŻYTKOWNIKA:** CSV jest zbędne. QuestDB musi działać. System bez QuestDB nie powinien uruchamiać data collection.

## Identyfikacja Wszystkich Użyć CSV

### 1. **Zapis CSV (CSV Write Operations)**

#### execution_controller.py - USUNĄĆ CAŁKOWICIE
**Lokalizacja:** `src/application/controllers/execution_controller.py`

**Funkcja start_data_collection() - Linie 538-556:**
```python
# ZBĘDNE - DO USUNIĘCIA
price_file = symbol_dir / "prices.csv"
if not price_file.exists():
    with price_file.open('w') as f:
        f.write("timestamp,price,volume,quote_volume\n")

orderbook_file = symbol_dir / "orderbook.csv"
if not orderbook_file.exists():
    with orderbook_file.open('w') as f:
        header_parts = ["timestamp", ...]
        f.write(",".join(header_parts) + "\n")
```

**Problem:** Tworzy katalogi `data/session_{id}/{symbol}/` i pliki CSV.
**Akcja:** USUNĄĆ tworzenie katalogów i plików CSV. Session istnieje tylko w QuestDB.

**Funkcja _write_data_batch() - Linie 1256-1337:**
```python
# ZBĘDNE - DO USUNIĘCIA
if price_batch:
    price_file = session_dir / symbol / "prices.csv"
    async with aiofiles.open(price_file, 'a') as f:
        await f.write(''.join(price_lines))

if orderbook_batch:
    orderbook_file = session_dir / symbol / "orderbook.csv"
    async with aiofiles.open(orderbook_file, 'a') as f:
        await f.write(''.join(orderbook_lines))
```

**Problem:** Dual write - zapisuje dane zarówno do CSV jak i QuestDB.
**Akcja:** USUNĄĆ całkowicie zapisy CSV, zostawić tylko QuestDB writes.

**Zależności:**
- Moduł `aiofiles` - może być zbędny (sprawdzić czy używany gdzie indziej)
- Katalogi `data/session_*` - nie będą tworzone

---

### 2. **Odczyt CSV (CSV Read Operations)**

#### A. data_analysis_service.py - ZASTĄPIĆ QuestDB
**Lokalizacja:** `src/data/data_analysis_service.py`

**Funkcja _load_symbol_data() - Linie 347-356:**
```python
# ZASTĄPIĆ ZAPYTANIEM DO QuestDB
price_csv = session_dir / symbol / "prices.csv"
if not price_csv.exists():
    return None
data = await asyncio.to_thread(self._parse_price_csv, price_csv)
```

**Problem:** Czyta prices.csv dla sesji.
**Akcja:** Zastąpić SELECT z tick_prices WHERE session_id = X AND symbol = Y.

**Funkcja _build_metadata_from_session() - Linie 436-444:**
```python
# ZASTĄPIĆ ZAPYTANIEM DO QuestDB
for symbol in symbols:
    price_csv = session_dir / symbol / "prices.csv"
    if not price_csv.exists():
        continue
    summary = self._summarize_price_csv(price_csv)
```

**Problem:** Buduje metadata skanując CSV files.
**Akcja:** Zastąpić zapytaniem do data_collection_sessions.

**Funkcja _summarize_price_csv() - Linie 472-489:**
```python
# ZASTĄPIĆ ZAPYTANIEM DO QuestDB
with price_csv.open("r", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        count += 1
        # ... calculate min/max timestamp
```

**Problem:** Parsuje CSV żeby policzyć rekordy i znaleźć min/max timestamp.
**Akcja:** Zastąpić `SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM tick_prices WHERE session_id = X`.

**Funkcja _parse_price_csv() - Linie 491-513:**
```python
# ZASTĄPIĆ ZAPYTANIEM DO QuestDB
with price_csv.open("r", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        points.append({
            "timestamp": timestamp,
            "price": price,
            "volume": volume
        })
```

**Problem:** Parsuje cały CSV do listy dict.
**Akcja:** Zastąpić `SELECT timestamp, price, volume, quote_volume FROM tick_prices WHERE session_id = X AND symbol = Y ORDER BY timestamp`.

**Zależności:**
- REST API endpoints w `data_analysis_routes.py` - używają DataAnalysisService
- Frontend - wywołuje te endpointy
- Moduł `csv` - może być zbędny w tym pliku

---

#### B. data_sources.py - HistoricalDataSource - ZASTĄPIĆ CAŁKOWICIE
**Lokalizacja:** `src/application/controllers/data_sources.py`

**Klasa HistoricalDataSource - Linie 19-196:**
```python
# ZASTĄPIĆ NOWĄ KLASĄ: QuestDBHistoricalDataSource
class HistoricalDataSource(IExecutionDataSource):
    """Replays CSV files with time acceleration."""

    async def start_stream(self) -> None:
        # Find data files: symbol_dir.glob("*/*_prices.csv")
        # Open CSV readers

    async def get_next_batch(self) -> List[Dict]:
        # Read next rows from CSV
        # Return batch of market data
```

**Problem:** Backtest używa CSV files jako źródła danych.
**Akcja:** Stworzyć nową klasę `QuestDBHistoricalDataSource` która:
- W `start_stream()`: Nie otwiera plików, tylko przygotowuje query do QuestDB
- W `get_next_batch()`: Pobiera następną partię danych z QuestDB

**KRYTYCZNE:** Backtest jest całkowicie zależny od tego źródła danych.

**Zależności:**
- `command_processor.py` - tworzy HistoricalDataSource w `_handle_start_backtest()`
- `execution_controller.py` - używa IExecutionDataSource interface

---

#### C. offline_indicator_engine.py - SPRAWDZIĆ I ZASTĄPIĆ
**Lokalizacja:** `src/domain/services/offline_indicator_engine.py`

**Komentarze w pliku:**
```python
# Linia 4: "Calculates indicators for historical data from CSV files."
# Linia 26: "Loads data from CSV files and calculates indicators for complete datasets."
# Linia 234: "_load_symbol_data() -> Load historical data for a symbol from CSV files."
```

**Problem:** Offline indicator engine używa CSV.
**Akcja:** SPRAWDZIĆ dokładnie jak używa CSV i czy jest to ten sam flow co data collection.
**Możliwość:** Może używać tego samego DataAnalysisService, więc refactor tam automatycznie naprawi to.

---

### 3. **Potencjalne Duplikacje i Dead Code**

#### Duplikacje w session metadata
**Problem:** Session metadata obecnie w 2 miejscach:
1. `data_collection_sessions` (QuestDB) - pełne dane
2. Katalogi `data/session_*` (filesystem) - tylko struktura

**Akcja:** Po usunięciu CSV, metadata tylko w QuestDB.

#### Dead code po usunięciu CSV
- `_write_data_batch()` - cały blok CSV write (linie 1254-1337)
- `_parse_price_csv()` - cała funkcja
- `_summarize_price_csv()` - cała funkcja
- `_find_session_directory()` - może być zbędna (sprawdzić)
- `_initialize_data_directories()` - może być zbędna (sprawdzić)
- Import `aiofiles` - może być zbędny (sprawdzić inne użycia)
- Import `csv` w data_analysis_service.py - będzie zbędny

---

## Architektura Problemy Zidentyfikowane

### Problem 1: Dual Write bez Synchronizacji
**Gdzie:** `execution_controller._write_data_batch()`

**Obecna implementacja:**
```python
# 1. Write to CSV
async with aiofiles.open(price_file, 'a') as f:
    await f.write(''.join(price_lines))

# 2. Write to DB
if self.db_persistence_service:
    await self.db_persistence_service.persist_tick_prices(...)
```

**Problem:**
- CSV write może się udać, DB write może się nie udać → brak spójności
- DB write failure jest tylko logowany, nie propagowany
- Nie ma mechanizmu rollback
- Nie ma weryfikacji czy oba zapisy się powiodły

**Rozwiązanie:**
- USUNĄĆ CSV write całkowicie
- DB write failure = critical error, stop collection
- Pojedyncze źródło prawdy (QuestDB)

### Problem 2: Brak Session Selection w Backtest
**Gdzie:** `command_processor._handle_start_backtest()` + `data_sources.HistoricalDataSource`

**Obecna implementacja:**
```python
# Find latest data file
price_files = list(symbol_dir.glob("*/*_prices.csv"))
latest_file = max(price_files, key=lambda f: f.stat().st_mtime)
```

**Problem:**
- Backtest zawsze używa "najnowszego" pliku na podstawie modification time
- Nie ma możliwości wyboru konkretnej sesji
- Użytkownik nie wie jakiej sesji używa backtest
- Brak linku między session_id a backtest_results

**Rozwiązanie:**
- Nowy interfejs: `start_backtest(session_id=...)` - explicit session selection
- `QuestDBHistoricalDataSource(session_id=...)` - pobiera dane tylko z tej sesji
- `backtest_results.session_id` - link do użytej sesji
- Frontend: Dropdown selector sesji przed uruchomieniem backtestu

### Problem 3: Metadata w Dwóch Miejscach
**Gdzie:** Filesystem directories vs QuestDB

**Obecna implementacja:**
```python
# Filesystem: data/session_123456/BTC_USDT/prices.csv
# QuestDB: data_collection_sessions WHERE session_id='123456'
```

**Problem:**
- Redundancja - ta sama informacja w 2 miejscach
- Może być niespójność (session w DB ale brak plików, lub odwrotnie)
- _find_session_directory() skanuje filesystem
- list_sessions() musi sprawdzać oba miejsca

**Rozwiązanie:**
- USUNĄĆ katalogi session_* całkowicie
- Metadata tylko w data_collection_sessions
- list_sessions() = SELECT z QuestDB
- Brak skanowania filesystemu

### Problem 4: CSV Parsing Performance
**Gdzie:** `data_analysis_service._parse_price_csv()`

**Obecna implementacja:**
```python
# Parse entire CSV to memory
for row in reader:
    timestamp = self._normalize_timestamp(row.get("timestamp"))
    price = self._safe_float(row.get("price"))
    # ... build list
```

**Problem:**
- Cały plik wczytywany do pamięci
- Dla dużych sesji (1M+ ticks) = GB RAM
- Brak streamingu
- Brak indeksowania
- Wolne parsowanie CSV

**Rozwiązanie:**
- QuestDB query z LIMIT/OFFSET dla paginacji
- Downsampling na poziomie query (SAMPLE BY)
- Indeksy na timestamp, symbol, session_id
- 10-100x szybsze niż CSV parsing

### Problem 5: Brak Proper Error Handling dla QuestDB
**Gdzie:** `execution_controller`, `unified_trading_controller`, `container.py`

**Obecna implementacja:**
```python
if self.db_persistence_service:
    try:
        await self.db_persistence_service.persist_tick_prices(...)
    except Exception as db_error:
        self.logger.warning("...")  # Just log, continue
```

**Problem:**
- QuestDB failures są tylko logowane
- System kontynuuje z CSV jako fallback
- Użytkownik może nie zauważyć że dane nie trafiają do DB
- Brak fail-fast mechanism

**Rozwiązanie:**
- QuestDB MUSI działać - throw exception jeśli nie
- Nie startować data collection jeśli QuestDB unavailable
- Clear error message: "QuestDB connection required for data collection"
- Nie ma fallback - albo działa z QuestDB albo wcale

### Problem 6: Optional db_persistence_service
**Gdzie:** `execution_controller.__init__()`, `unified_trading_controller.initialize()`

**Obecna implementacja:**
```python
def __init__(self, ..., db_persistence_service=None):
    self.db_persistence_service = db_persistence_service  # Optional

# Later:
if self.db_persistence_service:  # Check everywhere
    await self.db_persistence_service.persist_tick_prices(...)
```

**Problem:**
- db_persistence_service jest optional
- Każde użycie musi sprawdzać `if self.db_persistence_service`
- Kod pełen conditional checks
- Backward compatibility która nie jest potrzebna

**Rozwiązanie:**
- db_persistence_service = REQUIRED parameter
- Throw exception w __init__ jeśli None
- Usunąć wszystkie `if self.db_persistence_service` checks
- Clear contract: data collection wymaga QuestDB

---

## Moduły Dotknięte Zmianą

### Zmiany Krytyczne (MUST CHANGE)

1. **execution_controller.py**
   - USUNĄĆ: Tworzenie katalogów session_*
   - USUNĄĆ: Tworzenie plików CSV
   - USUNĄĆ: Zapisy do CSV w _write_data_batch()
   - ZMIENIĆ: db_persistence_service = required
   - DODAĆ: Walidacja QuestDB connection na starcie

2. **data_analysis_service.py**
   - ZMIENIĆ: _load_symbol_data() → query QuestDB
   - ZMIENIĆ: _build_metadata_from_session() → query QuestDB
   - USUNĄĆ: _parse_price_csv()
   - USUNĄĆ: _summarize_price_csv()
   - ZMIENIĆ: _find_session_directory() → query QuestDB
   - DODAĆ: QuestDB provider dependency

3. **data_sources.py**
   - STWORZYĆ NOWĄ: QuestDBHistoricalDataSource
   - OZNACZYĆ DEPRECATED: HistoricalDataSource (lub usunąć)
   - ZMIENIĆ: Interface może potrzebować session_id parameter

4. **command_processor.py**
   - ZMIENIĆ: _handle_start_backtest() → use QuestDBHistoricalDataSource
   - DODAĆ: session_id parameter do backtest command
   - DODAĆ: Walidacja czy session exists w QuestDB

5. **unified_trading_controller.py**
   - ZMIENIĆ: db_persistence_service = required, nie optional
   - USUNĄĆ: try/except blok dla DB service creation
   - ZMIENIĆ: Throw exception jeśli QuestDB unavailable

6. **container.py**
   - Analogiczne zmiany jak unified_trading_controller.py

### Zmiany Secondary (NICE TO HAVE)

7. **data_analysis_routes.py**
   - SPRAWDZIĆ: Czy endpointy potrzebują zmian
   - PRAWDOPODOBNIE: Automatycznie fixed przez DataAnalysisService refactor

8. **offline_indicator_engine.py**
   - SPRAWDZIĆ: Jak używa CSV
   - ZMIENIĆ: Jeśli używa _load_symbol_data() to automatycznie fixed

### Zmiany Testów

9. **test_indicator_history_endpoint.py**
10. **test_indicator_time_grid.py**
    - ZMIENIĆ: Mock QuestDB zamiast CSV files
    - ZMIENIĆ: Przygotowanie test data do QuestDB

---

## Plan Implementacji Phase 2

### Krok 1: Przygotowanie - Walidacja QuestDB Required
**Cel:** System nie uruchamia się bez QuestDB

**Zmiany:**
1. unified_trading_controller.py:
   - Usunąć try/except dla db_persistence_service creation
   - Throw exception jeśli QuestDB unavailable
   - db_persistence_service = required parameter

2. container.py:
   - Analogiczne zmiany

3. execution_controller.py:
   - Zmienić __init__(db_persistence_service=None) → __init__(db_persistence_service)
   - Dodać assert db_persistence_service is not None
   - Throw clear error message

**Test:**
- Start bez QuestDB → clear error message
- Start z QuestDB → działa normalnie

### Krok 2: Usunięcie CSV Write
**Cel:** Dane zapisywane tylko do QuestDB

**Zmiany:**
1. execution_controller.py - start_data_collection():
   - USUNĄĆ tworzenie katalogów session_dir
   - USUNĄĆ tworzenie plików prices.csv, orderbook.csv
   - ZACHOWAĆ tylko db_persistence_service.create_session()

2. execution_controller.py - _write_data_batch():
   - USUNĄĆ cały blok CSV write (linie 1254-1337)
   - ZACHOWAĆ tylko QuestDB write
   - USUNĄĆ try/except wokół DB write - let it propagate
   - USUNĄĆ komentarze o "CSV write succeeded"

**Test:**
- Start data collection → session w QuestDB, brak katalogów
- Zbieraj dane → tylko DB writes, brak CSV files
- Stop collection → session completed w QuestDB

### Krok 3: QuestDB Data Provider dla DataAnalysisService
**Cel:** Czytanie danych z QuestDB zamiast CSV

**Nowa klasa:**
```python
class QuestDBDataProvider:
    """Provider for querying session data from QuestDB."""

    async def get_session_metadata(self, session_id: str) -> Dict:
        """Query data_collection_sessions."""

    async def get_tick_prices(self, session_id: str, symbol: str,
                               offset: int = 0, limit: int = 10000) -> List[Dict]:
        """Query tick_prices with pagination."""

    async def get_session_summary(self, session_id: str) -> Dict:
        """Aggregate statistics for session."""
```

**Zmiany w data_analysis_service.py:**
1. Dodać dependency: QuestDBProvider
2. _load_symbol_data():
   - USUNĄĆ _parse_price_csv()
   - DODAĆ query do tick_prices
3. _build_metadata_from_session():
   - USUNĄĆ _summarize_price_csv()
   - DODAĆ query do data_collection_sessions
4. list_sessions():
   - USUNĄĆ skanowanie directories
   - DODAĆ SELECT z data_collection_sessions

**Test:**
- list_sessions() → zwraca sesje z QuestDB
- get_session_data() → zwraca tick data z QuestDB
- analyze_session() → używa DB queries

### Krok 4: QuestDBHistoricalDataSource dla Backtestów
**Cel:** Backtest używa QuestDB zamiast CSV

**Nowa klasa:**
```python
class QuestDBHistoricalDataSource(IExecutionDataSource):
    """Historical data source using QuestDB for backtesting."""

    def __init__(self, db_provider: QuestDBProvider, session_id: str,
                 symbols: List[str], batch_size: int = 100):
        self.db_provider = db_provider
        self.session_id = session_id
        self.symbols = symbols
        self.batch_size = batch_size
        self._offset = 0
        self._total_rows = 0

    async def start_stream(self) -> None:
        """Initialize by counting total rows."""
        query = """
        SELECT COUNT(*) as total
        FROM tick_prices
        WHERE session_id = '{self.session_id}'
          AND symbol IN (...)
        """
        self._total_rows = result['total']

    async def get_next_batch(self) -> List[Dict]:
        """Get next batch using LIMIT/OFFSET."""
        query = """
        SELECT timestamp, symbol, price, volume, quote_volume
        FROM tick_prices
        WHERE session_id = '{self.session_id}'
          AND symbol IN (...)
        ORDER BY timestamp
        LIMIT {self.batch_size}
        OFFSET {self._offset}
        """
        self._offset += self.batch_size
        return results

    def get_progress(self) -> float:
        """Calculate progress based on offset vs total."""
        return (self._offset / self._total_rows) * 100
```

**Zmiany:**
1. data_sources.py:
   - DODAĆ QuestDBHistoricalDataSource
   - OZNACZYĆ HistoricalDataSource jako deprecated

2. command_processor.py:
   - ZMIENIĆ _handle_start_backtest():
     - Dodać session_id parameter (required)
     - Use QuestDBHistoricalDataSource zamiast HistoricalDataSource

**Test:**
- Start backtest z session_id → używa QuestDB
- Backtest progress → correct progress reporting
- Backtest results → session_id linked

### Krok 5: Frontend - Session Picker
**Cel:** Użytkownik wybiera sesję przed backtestem

**Zmiany:**
1. Dodać endpoint: GET /api/data-collection/sessions
   - Zwraca listę sesji z metadata
2. Frontend component:
   - Dropdown z listą sesji
   - Pokazuje: session_id, symbols, duration, records count, date
   - Selected session_id przekazywany do backtest

**Test:**
- Lista sesji widoczna w UI
- Wybór sesji przed backtestem
- Backtest używa wybranej sesji

### Krok 6: Cleanup - Usunięcie Dead Code
**Cel:** Kod czysty, bez zbędnych funkcji

**Do usunięcia:**
1. execution_controller.py:
   - Wszystkie references do CSV files
   - Katalogi session_*
2. data_analysis_service.py:
   - _parse_price_csv()
   - _summarize_price_csv()
   - _find_session_directory() (jeśli nie używana gdzie indziej)
3. data_sources.py:
   - HistoricalDataSource (jeśli deprecated)
4. Import `csv` gdzie nie używany
5. Import `aiofiles` jeśli nie używany gdzie indziej

---

## Ryzyka i Mitygacja

### Ryzyko 1: Breaking Change dla Istniejących Sesji CSV
**Problem:** Użytkownik ma istniejące sesje w CSV.
**Mitygacja:**
- Stworzyć migration script: import_csv_to_questdb.py
- Jednorazowy import starych sesji do QuestDB
- Po imporcie stare CSV można usunąć

### Ryzyko 2: QuestDB Downtime = System Unavailable
**Problem:** Jeśli QuestDB down, data collection nie działa.
**Mitygacja:**
- Clear error message: "QuestDB connection required"
- Dokumentacja: jak restartować QuestDB
- Health check endpoint: /health → sprawdza QuestDB
- Monitoring: Alert jeśli QuestDB unavailable

### Ryzyko 3: Performance - Large Sessions Query
**Problem:** Query dla sesji z 10M+ ticks może być wolny.
**Mitygacja:**
- Pagination: LIMIT/OFFSET w queries
- Downsampling: SAMPLE BY dla agregacji
- Indexes: timestamp, symbol, session_id
- Cache: Aggressive caching w DataAnalysisService

### Ryzyko 4: Migration Script Failures
**Problem:** Migration 003 może się nie udać jeśli QuestDB unavailable.
**Mitygacja:**
- Clear error message: "Run migration first"
- Automatic migration check on startup
- Health check: Verify tables exist

---

## Verification Checklist

### Pre-Implementation Verification
- [ ] Zidentyfikowane wszystkie CSV uses (DONE w tym dokumencie)
- [ ] Zidentyfikowane wszystkie moduły dotknięte (DONE)
- [ ] Zidentyfikowane architektura problemy (DONE - 6 problemów)
- [ ] Sprawdzony dead code potential (DONE)
- [ ] Sprawdzone duplikacje (DONE)

### Post-Implementation Verification
- [ ] Usunięte wszystkie CSV writes
- [ ] Usunięte wszystkie CSV reads
- [ ] Usunięte tworzenie katalogów session_*
- [ ] db_persistence_service = required
- [ ] QuestDB unavailable = clear error
- [ ] Backtest używa QuestDB
- [ ] Session picker w UI
- [ ] Migration script dla starych CSV
- [ ] Health check endpoint
- [ ] Dokumentacja updated
- [ ] Tests updated
- [ ] No dead code remaining

---

## Następny Krok

Po zatwierdzeniu tej analizy przez użytkownika:
1. Rozpocząć implementację Step 1 (QuestDB Required)
2. Testować każdy krok pojedynczo
3. Commit po każdym działającym kroku
4. Raportować progress i problemy

**Status:** Analiza COMPLETE - Czekam na approve użytkownika
