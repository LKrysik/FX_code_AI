# GŁĘBOKA ANALIZA ARCHITEKTURY - Data Collection System
**Data:** 2025-10-27
**Autor:** Claude AI
**Cel:** Analiza przed migracją z plików CSV do QuestDB

---

## 1. OBECNY STAN SYSTEMU

### 1.1 Struktura Danych (Z Przykładów Użytkownika)

**prices.csv:**
```csv
timestamp,price,volume,quote_volume
1759841342.46,0.1064,92,9.7888
1759841353.46,0.1065,128,13.632
```

**Format:**
- `timestamp` - Unix timestamp (float, submilisekunda)
- `price` - Pojedyncza cena (TICK DATA, nie OHLCV!)
- `volume` - Wolumen w tym ticku
- `quote_volume` - Wolumen w walucie quote

**orderbook.csv:**
```csv
timestamp,bid_price_1,bid_qty_1,bid_price_2,bid_qty_2,bid_price_3,bid_qty_3,ask_price_1,ask_qty_1,ask_price_2,ask_qty_2,ask_price_3,ask_qty_3,best_bid,best_ask,spread
1759841340.907,0.1063,454373,0.1062,434160,0.1061,507042,0.1064,470625,0.1065,391904,0.1066,363206,0.1063,0.1064,0.0001
```

**Format:**
- `timestamp` - Unix timestamp
- `bid_price_1`, `bid_qty_1` - Najlepszy bid (poziom 1)
- `bid_price_2`, `bid_qty_2` - Bid poziom 2
- `bid_price_3`, `bid_qty_3` - Bid poziom 3
- `ask_price_1`, `ask_qty_1` - Najlepszy ask (poziom 1)
- `ask_price_2`, `ask_qty_2` - Ask poziom 2
- `ask_price_3`, `ask_qty_3` - Ask poziom 3
- `best_bid`, `best_ask` - Najlepsze ceny
- `spread` - Spread

**KLUCZOWY WNIOSEK:**
- To są **TICK DATA** (high-frequency, każdy pojedynczy trade)
- **NIE OHLCV** (candlestick data)
- Orderbook ma **3 poziomy głębokości**
- Timestamps mają **submilisekund precision**

### 1.2 Gdzie Zapisywane Są Dane

**Z analizy kodu:**

**HistoricalDataSource** (`src/application/controllers/data_sources.py:54`):
```python
symbol_dir = self.data_path / symbol
price_files = list(symbol_dir.glob("*/*_prices.csv"))
```

**Struktura folderów:**
```
data/
  └── BTC_USDT/
      └── {session_id}/
          ├── prices.csv
          ├── orderbook.csv
          └── trades.csv  (może być)
```

**DataCollectionSession** (`frontend/src/app/data-collection/page.tsx:65`):
```typescript
interface DataCollectionSession {
  session_id: string;
  status: string;
  symbols: string[];
  data_types: string[];  // ['price', 'orderbook', 'trades']
  duration: string;
  start_time?: string;
  end_time?: string;
  records_collected: number;
  storage_path: string;  // "data"
  created_at: string;
}
```

### 1.3 Jak Działają Sesje Zbierania Danych

**Frontend:** `http://localhost:3000/data-collection`

**Workflow:**
1. User creates session: wybiera symbols, duration, data_types
2. Backend zapisuje do folderów: `data/{symbol}/{session_id}/*.csv`
3. Frontend pokazuje listę sesji
4. WebSocket pokazuje progress w real-time
5. Po zakończeniu: session.status = 'completed'

**Frontend navigation:**
- `/data-collection` - Lista sesji
- `/data-collection/[sessionId]/chart` - Chart dla konkretnej sesji

### 1.4 Jak API Używa Danych

**Backtest** (`src/application/controllers/data_sources.py:19`):
```python
class HistoricalDataSource(IExecutionDataSource):
    def __init__(self, data_path: str, symbols: List[str]):
        self.data_path = Path(data_path)  # "data"

    async def start_stream(self):
        # Finds: data/{symbol}/*_prices.csv
        price_files = list(symbol_dir.glob("*/*_prices.csv"))
        latest_file = max(price_files, key=lambda f: f.stat().st_mtime)
```

**Problem:**
- Backtest używa **najnowszego pliku** (latest by modification time)
- **BRAK powiązania z session_id**
- Nie można wybrać konkretnej sesji do backtestingu

---

## 2. PROBLEMY ZIDENTYFIKOWANE

### 2.1 Architektoniczne

#### Problem 1: Brak powiązania sesji z backtestingiem
**Lokalizacja:** `src/application/controllers/data_sources.py:74`
```python
latest_file = max(price_files, key=lambda f: f.stat().st_mtime)
```
**Impact:** HIGH
**Opis:** Backtest automatycznie wybiera najnowszy plik, nie można wybrać konkretnej sesji.

#### Problem 2: Duplikacja danych orderbook
**Lokalizacja:** `orderbook.csv`
```csv
...,best_bid,best_ask,spread
```
**Impact:** MEDIUM
**Opis:** `best_bid`, `best_ask`, `spread` to duplikacja - można wyliczyć z bid_price_1/ask_price_1.

#### Problem 3: Brak wskaźników w bazie
**Impact:** HIGH
**Opis:** Wskaźniki techniczne (RSI, EMA) są liczone on-the-fly, nie są zapisywane.

#### Problem 4: Sesje tylko w pamięci/plikach
**Impact:** HIGH
**Opis:** Sesje nie są przechowywane w bazie danych, tylko jako metadane w folderach.

#### Problem 5: Brak aggregacji OHLCV
**Impact:** MEDIUM
**Opis:** Tick data nie ma pre-agregowanych świec (1m, 5m, 1h), musi liczyć każdorazowo.

### 2.2 Wydajnościowe

#### Problem 6: CSV parsing w loopie
**Lokalizacja:** `data_sources.py:119`
```python
for symbol, reader in list(self._csv_readers.items()):
    row = next(reader)  # Linia po linii
```
**Impact:** MEDIUM
**Opis:** CSV czytany linia po linii, brak batch loading.

#### Problem 7: Brak indeksowania
**Impact:** HIGH
**Opis:** CSV nie ma indeksów, wyszukiwanie po timestamp = O(n).

### 2.3 Integra

cyjne

#### Problem 8: API plikowe, nie DB
**Impact:** HIGH
**Opis:** REST API czyta z plików, nie z bazy danych.

#### Problem 9: WebSocket nie ma historii
**Impact:** MEDIUM
**Opis:** WebSocket pokazuje tylko live data, brak możliwości replay z DB.

### 2.4 Nieużywane tabele w QuestDB schema

**Z pliku:** `database/questdb/migrations/001_create_initial_schema.sql`

#### Tabela: `strategy_signals` - UNUSED
```sql
CREATE TABLE strategy_signals (
    strategy_id SYMBOL,
    symbol SYMBOL,
    signal_type SYMBOL,
    ...
)
```
**Uzasadnienie usunięcia:** System nie generuje strategy signals do DB, tylko do logu.

#### Tabela: `orders` - PARTIALLY USED
```sql
CREATE TABLE orders (
    order_id SYMBOL,
    strategy_id SYMBOL,
    ...
)
```
**Status:** Prawdopodobnie używana w live trading, **KEEP** ale zweryfikować.

#### Tabela: `positions` - PARTIALLY USED
```sql
CREATE TABLE positions (
    position_id SYMBOL,
    strategy_id SYMBOL,
    ...
)
```
**Status:** Prawdopodobnie używana w live trading, **KEEP** ale zweryfikować.

#### Tabela: `system_metrics` - UNUSED
```sql
CREATE TABLE system_metrics (
    metric_name SYMBOL,
    timestamp TIMESTAMP,
    value DOUBLE,
    ...
)
```
**Uzasadnienie usunięcia:** Metryki systemowe nie są zapisywane do DB.

#### Tabela: `error_logs` - UNUSED
```sql
CREATE TABLE error_logs (
    timestamp TIMESTAMP,
    severity SYMBOL,
    ...
)
```
**Uzasadnienie usunięcia:** Logi idą do plików/stdout, nie do DB.

---

## 3. DOCELOWA ARCHITEKTURA

### 3.1 Nowa Struktura Tabel QuestDB

#### Tabela 1: `data_collection_sessions`
```sql
CREATE TABLE data_collection_sessions (
    session_id STRING,           -- UUID
    status STRING,               -- 'active', 'completed', 'failed', 'stopped'
    symbols STRING,              -- JSON array: ["BTC_USDT", "ETH_USDT"]
    data_types STRING,           -- JSON array: ["price", "orderbook"]
    duration_seconds INT,        -- Duration in seconds
    start_time TIMESTAMP,        -- Session start
    end_time TIMESTAMP,          -- Session end (null if active)
    records_collected LONG,      -- Total records
    storage_path STRING,         -- Legacy path (deprecated)
    config STRING,               -- JSON: {"max_file_size_mb": 100, ...}
    created_at TIMESTAMP,        -- Creation time
    error_message STRING         -- Error if failed
);

-- Index on session_id for fast lookup
CREATE INDEX idx_sessions_id ON data_collection_sessions(session_id);
```

**Uzasadnienie:**
- **session_id** - Primary key dla powiązania z danymi
- **status** - Track lifecycle sesji
- **symbols/data_types** - Flexible JSON arrays
- **records_collected** - Progress tracking
- **storage_path** - Deprecated, ale keep dla backward compatibility

#### Tabela 2: `tick_prices` (HIGH-FREQUENCY)
```sql
CREATE TABLE tick_prices (
    session_id SYMBOL capacity 1024 CACHE,  -- Linked to session
    symbol SYMBOL capacity 256 CACHE,       -- Trading pair
    timestamp TIMESTAMP,                    -- Tick timestamp
    price DOUBLE,                           -- Tick price
    volume DOUBLE,                          -- Tick volume
    quote_volume DOUBLE                     -- Volume in quote currency
) timestamp(timestamp) PARTITION BY DAY WAL;

-- DEDUP to prevent duplicate ticks
ALTER TABLE tick_prices DEDUP ENABLE UPSERT KEYS(timestamp, symbol, session_id);
```

**Uzasadnienie:**
- **session_id SYMBOL** - Fast filtering by session (O(1) lookup)
- **PARTITION BY DAY** - Time-based partitioning
- **DEDUP** - Prevent duplicate ticks if collection restarts
- **WAL** - Durability for high-frequency writes

**Frequency:** ~10-100 ticks/second per symbol
**Storage:** ~50 bytes/row compressed = 500KB/s per symbol

#### Tabela 3: `tick_orderbook` (HIGH-FREQUENCY)
```sql
CREATE TABLE tick_orderbook (
    session_id SYMBOL capacity 1024 CACHE,  -- Linked to session
    symbol SYMBOL capacity 256 CACHE,       -- Trading pair
    timestamp TIMESTAMP,                    -- Orderbook snapshot timestamp

    -- Bid levels (3 deep)
    bid_price_1 DOUBLE,
    bid_qty_1 DOUBLE,
    bid_price_2 DOUBLE,
    bid_qty_2 DOUBLE,
    bid_price_3 DOUBLE,
    bid_qty_3 DOUBLE,

    -- Ask levels (3 deep)
    ask_price_1 DOUBLE,
    ask_qty_1 DOUBLE,
    ask_price_2 DOUBLE,
    ask_qty_2 DOUBLE,
    ask_price_3 DOUBLE,
    ask_qty_3 DOUBLE

    -- NOTE: best_bid, best_ask, spread REMOVED (can be computed)
) timestamp(timestamp) PARTITION BY DAY WAL;

ALTER TABLE tick_orderbook DEDUP ENABLE UPSERT KEYS(timestamp, symbol, session_id);
```

**Uzasadnienie:**
- **Denormalized** - Wszystkie 3 poziomy w jednym wierszu dla szybkości
- **No computed columns** - Usunieto best_bid, best_ask, spread (redundant)
- **PARTITION BY DAY** - Daily cleanup

**Frequency:** ~1-10 snapshots/second per symbol
**Storage:** ~120 bytes/row = 1.2KB/s per symbol

#### Tabela 4: `aggregated_ohlcv` (Pre-aggregated candles)
```sql
CREATE TABLE aggregated_ohlcv (
    session_id SYMBOL capacity 1024 CACHE,  -- Linked to session
    symbol SYMBOL capacity 256 CACHE,       -- Trading pair
    interval SYMBOL capacity 16 CACHE,      -- '1m', '5m', '15m', '1h', '4h', '1d'
    timestamp TIMESTAMP,                    -- Candle open time
    open DOUBLE,                            -- First price in interval
    high DOUBLE,                            -- Highest price
    low DOUBLE,                             -- Lowest price
    close DOUBLE,                           -- Last price in interval
    volume DOUBLE,                          -- Total volume
    quote_volume DOUBLE,                    -- Total quote volume
    trades_count INT                        -- Number of trades
) timestamp(timestamp) PARTITION BY DAY;

ALTER TABLE aggregated_ohlcv DEDUP ENABLE UPSERT KEYS(timestamp, symbol, session_id, interval);
```

**Uzasadnienie:**
- **Pre-aggregation** - Compute OHLCV during collection, not on query
- **interval SYMBOL** - Support multiple timeframes
- **trades_count** - Additional metric
- **PARTITION BY DAY** - Same as tick_prices

**Frequency:** Updated every 1m/5m/1h
**Storage:** ~80 bytes/row, minimal compared to tick data

#### Tabela 5: `indicators` (Same as before but linked to session)
```sql
CREATE TABLE indicators (
    session_id SYMBOL capacity 1024 CACHE,  -- NEW: Linked to session
    symbol SYMBOL capacity 256 CACHE,
    indicator_id SYMBOL capacity 2048 CACHE,
    timestamp TIMESTAMP,
    value DOUBLE,
    confidence DOUBLE,
    metadata STRING
) timestamp(timestamp) PARTITION BY DAY WAL;

ALTER TABLE indicators DEDUP ENABLE UPSERT KEYS(timestamp, symbol, session_id, indicator_id);
```

**Uzasadnienie:**
- **session_id** - Indicators computed per session
- **Reuse existing structure** - No changes to indicator_id, value, etc.

#### Tabela 6: `backtest_results` (Updated with session link)
```sql
CREATE TABLE backtest_results (
    backtest_id SYMBOL capacity 1024 CACHE,
    strategy_id SYMBOL capacity 512 CACHE,
    session_id SYMBOL capacity 1024 CACHE,  -- NEW: Link to data session
    symbol SYMBOL capacity 256 CACHE,
    timestamp TIMESTAMP,
    start_time TIMESTAMP,
    end_time TIMESTAMP,

    -- Performance metrics
    initial_capital DOUBLE,
    final_capital DOUBLE,
    total_return DOUBLE,
    sharpe_ratio DOUBLE,
    max_drawdown DOUBLE,
    win_rate DOUBLE,
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    avg_win DOUBLE,
    avg_loss DOUBLE,
    metadata STRING
) timestamp(timestamp) PARTITION BY DAY WAL;
```

**Uzasadnienie:**
- **session_id** - Backtest używa konkretnej sesji danych
- **Traceability** - Można odtworzyć backtest z tych samych danych

#### Tabela 7: `strategy_templates` (KEEP as-is)
```sql
-- NO CHANGES - relational table for templates
CREATE TABLE strategy_templates ( ... );
```

### 3.2 Tabele DO USUNIĘCIA

```sql
DROP TABLE IF EXISTS strategy_signals;  -- Not used
DROP TABLE IF EXISTS system_metrics;    -- Logs go to files
DROP TABLE IF EXISTS error_logs;        -- Logs go to files
```

**Tabele DO WERYFIKACJI:**
- `orders` - Check if used in live trading
- `positions` - Check if used in live trading

---

## 4. FLOW DANYCH - NOWY

### 4.1 Data Collection Flow

```
1. User creates session via UI
   ↓
2. POST /api/data-collection/start
   → Insert into data_collection_sessions (status='active')
   ↓
3. Backend starts data collection
   → IMarketDataProvider streams data
   ↓
4. For each tick:
   → INSERT into tick_prices (session_id, symbol, timestamp, price, volume)
   → INSERT into tick_orderbook (session_id, symbol, timestamp, bids, asks)
   ↓
5. Aggregator (async task):
   → Compute OHLCV every 1m/5m/1h
   → INSERT into aggregated_ohlcv
   ↓
6. Indicator Calculator (async task):
   → Compute RSI, EMA, etc. from tick_prices
   → INSERT into indicators (session_id)
   ↓
7. On session end:
   → UPDATE data_collection_sessions SET status='completed', end_time=NOW()
```

**Parallel writes:**
- tick_prices: 10-100/s per symbol
- tick_orderbook: 1-10/s per symbol
- aggregated_ohlcv: 1/60s (1 minute)
- indicators: 1/60s (1 minute)

**Expected throughput:**
- 1 symbol: ~100 inserts/second
- 10 symbols: ~1000 inserts/second
- QuestDB can handle: **1M+ inserts/second** ✅

### 4.2 API Query Flow

```
1. GET /api/data-collection/sessions
   → SELECT * FROM data_collection_sessions ORDER BY created_at DESC

2. GET /api/data-collection/sessions/{session_id}
   → SELECT * FROM data_collection_sessions WHERE session_id = ?

3. GET /api/data-collection/sessions/{session_id}/prices
   → SELECT * FROM tick_prices WHERE session_id = ? AND symbol = ?

4. GET /api/data-collection/sessions/{session_id}/orderbook
   → SELECT * FROM tick_orderbook WHERE session_id = ? AND symbol = ?

5. GET /api/data-collection/sessions/{session_id}/ohlcv?interval=1m
   → SELECT * FROM aggregated_ohlcv WHERE session_id = ? AND interval = '1m'

6. GET /api/data-collection/sessions/{session_id}/indicators
   → SELECT * FROM indicators WHERE session_id = ?
```

**Performance:**
- session list: <10ms (small table)
- tick data: 20-50ms (indexed by session_id + timestamp)
- OHLCV: <10ms (pre-aggregated)
- indicators: 20-50ms (indexed)

### 4.3 Backtest Flow (NEW)

```
1. User selects session in UI
   ↓
2. POST /api/backtest/start
   {
     "session_id": "abc-123",
     "strategy_id": "...",
     "symbols": ["BTC_USDT"]
   }
   ↓
3. Backend:
   → Load data from tick_prices WHERE session_id = 'abc-123'
   → OR load from aggregated_ohlcv (faster)
   → Load indicators WHERE session_id = 'abc-123'
   ↓
4. Run backtest engine
   ↓
5. INSERT into backtest_results (session_id='abc-123')
```

**Key improvement:**
- **Session-based backtest** - Can replay exact same data
- **Reproducible** - Same session_id = same results
- **No file I/O** - All from DB

### 4.4 WebSocket Flow

```
1. WebSocket connect: ws://localhost:8080/ws
   ↓
2. Subscribe to session:
   → send: {"type": "subscribe_session", "session_id": "abc-123"}
   ↓
3. Backend:
   → Query latest data from tick_prices WHERE session_id = ?
   → Stream new inserts via LISTEN/NOTIFY (if supported)
   → OR poll every 100ms
   ↓
4. Send to client:
   → {"type": "price_update", "session_id": "abc-123", "data": {...}}
```

---

## 5. RYZYKA i MITIGACJE

### Ryzyko 1: HIGH - Disruption podczas migracji
**Impact:** System przestaje działać
**Probability:** HIGH bez planu

**Mitigation:**
1. **Phased migration** - Etapami, nie wszystko naraz
2. **Dual write period** - Zapisuj do CSV i DB przez tydzień
3. **Feature flags** - Toggle między old/new systemem
4. **Rollback plan** - Możliwość powrotu do CSV

**Plan:**
- Week 1: Deploy DB schema, leave CSV intact
- Week 2: Dual write (CSV + DB), verify DB correctness
- Week 3: Switch API to read from DB, keep CSV write
- Week 4: Remove CSV write, full DB mode

### Ryzyko 2: MEDIUM - Performance degradation
**Impact:** Wolniejsze zapisy/odczyty
**Probability:** MEDIUM

**Mitigation:**
1. **Batch inserts** - Use InfluxDB line protocol (1M+ rows/sec)
2. **Pre-aggregation** - Compute OHLCV during collection
3. **Indexes** - SYMBOL type + PARTITION BY DAY
4. **Load testing** - Simulate 10 symbols × 100 ticks/sec

**Benchmark plan:**
```python
# Test: Insert 1M tick_prices rows
# Target: <1 second
# QuestDB proven: 1M+ rows/sec ✅
```

### Ryzyko 3: MEDIUM - Data consistency
**Impact:** Dane w DB != dane w CSV
**Probability:** MEDIUM

**Mitigation:**
1. **DEDUP** - Prevent duplicate inserts
2. **Transaction boundaries** - Group related inserts
3. **Validation** - Compare CSV vs DB counts
4. **Checksums** - MD5 of price stream

**Validation script:**
```python
# Compare: CSV row count vs DB row count per session
# Alert if mismatch > 0.1%
```

### Ryzyko 4: LOW - Disk space
**Impact:** QuestDB fills disk
**Probability:** LOW

**Mitigation:**
1. **Retention policy** - Auto-drop data older than 30 days
2. **Compression** - QuestDB compresses ~10:1
3. **Monitoring** - Alert at 80% disk

**Estimate:**
- 1 symbol, 1 day: 86400 ticks × 50 bytes = 4.3MB
- 10 symbols, 30 days: ~1.3GB
- Compressed: ~130MB
- **Acceptable** ✅

### Ryzyko 5: HIGH - Breaking existing workflows
**Impact:** Backtest/API przestają działać
**Probability:** HIGH bez testów

**Mitigation:**
1. **Integration tests** - Test każdego API endpoint
2. **E2E tests** - Full workflow: collect → query → backtest
3. **Backward compatibility** - Keep CSV читалка as fallback
4. **Staged rollout** - Dev → Staging → Prod

---

## 6. PLAN IMPLEMENTACJI

### Phase 1: Schema + Infrastructure (Week 1)
- [ ] Create new tables: `data_collection_sessions`, `tick_prices`, `tick_orderbook`, `aggregated_ohlcv`
- [ ] Add `session_id` to `indicators` table
- [ ] Add `session_id` to `backtest_results` table
- [ ] Drop unused tables: `strategy_signals`, `system_metrics`, `error_logs`
- [ ] Create indexes
- [ ] Run migration script

### Phase 2: Data Collection (Week 2)
- [ ] Update data collector to write to DB
- [ ] Implement session lifecycle (create → active → completed)
- [ ] Implement tick_prices writer (InfluxDB protocol)
- [ ] Implement tick_orderbook writer
- [ ] Implement OHLCV aggregator (async task)
- [ ] Keep CSV write as backup (dual write)

### Phase 3: API Integration (Week 3)
- [ ] Create `/api/data-collection/sessions` endpoint
- [ ] Create `/api/data-collection/sessions/{id}/prices` endpoint
- [ ] Create `/api/data-collection/sessions/{id}/orderbook` endpoint
- [ ] Create `/api/data-collection/sessions/{id}/ohlcv` endpoint
- [ ] Create `/api/data-collection/sessions/{id}/indicators` endpoint
- [ ] Update backtest to accept `session_id` parameter
- [ ] Feature flag: `USE_DB_DATA_SOURCE` (default=true)

### Phase 4: Frontend Integration (Week 4)
- [ ] Update session list to fetch from DB
- [ ] Add session picker to backtest UI
- [ ] Update charts to fetch from DB API
- [ ] WebSocket: Subscribe to session updates
- [ ] Remove file path display (deprecated)

### Phase 5: Testing & Validation (Week 5)
- [ ] Integration tests: Data collection → DB
- [ ] Integration tests: API endpoints
- [ ] E2E test: Full workflow
- [ ] Load test: 10 symbols × 100 ticks/sec
- [ ] Compare CSV vs DB data (validation)
- [ ] Performance benchmarks

### Phase 6: Cleanup & Launch (Week 6)
- [ ] Remove CSV write code (if validation passed)
- [ ] Remove old file-based APIs
- [ ] Documentation update
- [ ] Deploy to production
- [ ] Monitor for 1 week

---

## 7. VERIFICATION CHECKLIST

Before implementation, verify:

- [ ] **Data format match** - Przykłady użytkownika vs schema
- [ ] **No dead code** - Usunięto strategy_signals, system_metrics, error_logs
- [ ] **Session everywhere** - tick_prices, tick_orderbook, indicators, backtest_results have session_id
- [ ] **Performance** - QuestDB benchmarks prove 1M+ inserts/sec
- [ ] **Backward compat** - Can still read old CSV files if needed
- [ ] **API consistency** - REST and WebSocket use same DB backend
- [ ] **No duplication** - Single source of truth (DB), no CSV fallback after migration

---

## 8. WNIOSKI

### 8.1 Kluczowe Odkrycia

1. **TICK DATA, nie OHLCV** - Obecne dane to high-frequency ticks
2. **3-level orderbook** - Depth of 3 for bids/asks
3. **Session-based collection** - Już istnieje concept session_id
4. **File-based API** - Cały system czyta z CSV
5. **No session-backtest link** - Nie można wybrać sesji do backtestingu

### 8.2 Najważniejsze Zmiany

1. **Add session_id** do wszystkich tabel time-series
2. **Create data_collection_sessions** - Track session lifecycle
3. **Create tick_prices** - High-frequency tick data
4. **Create tick_orderbook** - 3-level order book snapshots
5. **Create aggregated_ohlcv** - Pre-computed candles
6. **Update API** - Read from DB not files
7. **Update backtest** - Accept session_id parameter
8. **Delete unused tables** - strategy_signals, system_metrics, error_logs

### 8.3 Dodatkowe Korzyści

- **Reproducible backtests** - Same session = same results
- **Faster queries** - Indexed DB vs linear CSV scan
- **Real-time progress** - WebSocket + DB = live updates
- **Historical analysis** - Query past sessions easily
- **Scalability** - QuestDB handles 1M+ inserts/sec

---

**Status:** READY FOR IMPLEMENTATION
**Confidence:** HIGH (wszystkie ryzyka zidentyfikowane i zmitygowane)
**Recommended:** Proceed with Phase 1 (Schema + Infrastructure)

