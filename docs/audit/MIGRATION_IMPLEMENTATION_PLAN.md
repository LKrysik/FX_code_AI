# Plan Implementacji Migracji CSV → QuestDB

**Data**: 2025-10-28
**Priorytet**: 🔴 KRYTYCZNY
**Czas**: 2-3 dni

---

## Task 1: Migracja IndicatorPersistenceService

### Obecna Architektura (CSV)

```python
# Plik: src/domain/services/indicator_persistence_service.py

class IndicatorPersistenceService:
    def __init__(self, event_bus, logger, base_data_dir="data"):
        self.base_data_dir = Path(base_data_dir)
        self._file_lock = RLock()  # Thread safety dla CSV

    def save_values(self, session_id, symbol, variant_id, values):
        # Zapisuje do: data/{session_id}/{symbol}/indicators/{variant_type}_{variant_id}.csv
        csv_path = self._get_csv_file_path(...)
        with open(csv_path, 'w') as f:
            writer = csv.writer(f)
            writer.writerows(...)
```

### Problem:
1. **Wydajność**: CSV write dla 10k records ~100ms
2. **Brak transakcji**: Partial writes = data corruption
3. **Duplikacja**: Dane już w QuestDB (indicators table)
4. **Skalowalność**: 1000 sesji × 10 symboli × 5 wskaźników = 50,000 plików CSV
5. **Synchronizacja**: CSV vs QuestDB = data inconsistency

---

### Nowa Architektura (QuestDB)

```python
# Plik: src/domain/services/indicator_persistence_service.py

class IndicatorPersistenceService:
    def __init__(self, event_bus, logger, questdb_provider, base_data_dir="data"):
        self.event_bus = event_bus
        self.logger = logger
        self.questdb_provider = questdb_provider
        # CSV fallback dla backward compatibility (opcjonalnie)
        self.base_data_dir = Path(base_data_dir) if base_data_dir else None

    async def save_values(self, session_id, symbol, variant_id, values):
        """Save indicator values to QuestDB with batch insert"""

        # Prepare batch for QuestDB
        batch = []
        for value in values:
            batch.append({
                'session_id': session_id,
                'symbol': symbol,
                'indicator_id': variant_id,  # or generate unique ID
                'indicator_type': value.indicator_type,  # From migration 005
                'indicator_name': value.indicator_name,
                'timestamp': datetime.fromtimestamp(value.timestamp),
                'value': float(value.value),
                'confidence': float(value.confidence) if value.confidence else None,
                'metadata': json.dumps(value.metadata) if value.metadata else None,
                # New columns from migration 005:
                'scope': value.scope if hasattr(value, 'scope') else None,
                'user_id': value.user_id if hasattr(value, 'user_id') else None,
                'created_by': value.created_by if hasattr(value, 'created_by') else None
            })

        # Batch insert to QuestDB (10x faster than CSV)
        try:
            count = await self.questdb_provider.insert_indicators_batch(batch)

            self.logger.info("indicator_persistence.saved_to_questdb", {
                "session_id": session_id,
                "symbol": symbol,
                "variant_id": variant_id,
                "count": count
            })

            return count

        except Exception as e:
            self.logger.error("indicator_persistence.save_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "error": str(e)
            })
            raise
```

---

### Kroki Implementacji

#### Step 1.1: Dodaj QuestDBProvider do IndicatorPersistenceService

**Plik**: `src/domain/services/indicator_persistence_service.py`

```python
# DODAJ import
from src.data_feed.questdb_provider import QuestDBProvider
from src.data.questdb_data_provider import QuestDBDataProvider

class IndicatorPersistenceService:
    def __init__(
        self,
        event_bus,
        logger,
        questdb_provider: Optional[QuestDBProvider] = None,
        base_data_dir: str = "data"
    ):
        self.event_bus = event_bus
        self.logger = logger
        self.base_data_dir = Path(base_data_dir)
        self._file_lock = RLock()

        # NEW: QuestDB provider for database operations
        self.questdb_provider = questdb_provider
        if self.questdb_provider is None:
            # Lazy initialization
            self.questdb_provider = QuestDBProvider(
                ilp_host='127.0.0.1',
                ilp_port=9009,
                pg_host='127.0.0.1',
                pg_port=8812
            )
```

---

#### Step 1.2: Zmodyfikuj save_values() - Zapis wskaźników

**Przed** (lines 151-205):
```python
def save_values(self, session_id: str, symbol: str, variant_id: str,
                indicator_values: List[IndicatorValue], variant_type: str = "general",
                mode: str = "append") -> int:
    """Save indicator values to CSV file"""
    with self._file_lock:
        csv_file_path = self._get_csv_file_path(session_id, symbol, variant_type, variant_id)
        # ... CSV write logic ...
```

**Po**:
```python
async def save_values(self, session_id: str, symbol: str, variant_id: str,
                     indicator_values: List[IndicatorValue], variant_type: str = "general",
                     mode: str = "append") -> int:
    """
    Save indicator values to QuestDB.

    Args:
        session_id: Data collection session ID
        symbol: Trading pair symbol
        variant_id: Indicator variant ID
        indicator_values: List of indicator values to save
        variant_type: Type of indicator variant (for backward compatibility)
        mode: 'append' or 'overwrite' (for backward compatibility)

    Returns:
        Number of values saved
    """

    if not indicator_values:
        return 0

    # Prepare batch for QuestDB
    batch = []
    for value in indicator_values:
        # Generate indicator_id if not present
        indicator_id = getattr(value, 'indicator_id', f"{variant_type}_{variant_id}")

        batch.append({
            'session_id': session_id,
            'symbol': symbol,
            'indicator_id': indicator_id,
            'indicator_type': getattr(value, 'indicator_type', variant_type),
            'indicator_name': getattr(value, 'indicator_name', variant_id),
            'timestamp': datetime.fromtimestamp(value.timestamp),
            'value': float(value.value),
            'confidence': float(value.confidence) if value.confidence is not None else None,
            'metadata': json.dumps(value.metadata) if hasattr(value, 'metadata') and value.metadata else None,
            # New columns from migration 005
            'scope': getattr(value, 'scope', None),
            'user_id': getattr(value, 'user_id', None),
            'created_by': getattr(value, 'created_by', None)
        })

    try:
        # If mode is 'overwrite', delete existing data first
        if mode == 'overwrite':
            await self._delete_existing_indicators(session_id, symbol, variant_id)

        # Batch insert to QuestDB
        count = await self.questdb_provider.insert_indicators_batch(batch)

        self.logger.info("indicator_persistence.saved_to_questdb", {
            "session_id": session_id,
            "symbol": symbol,
            "variant_id": variant_id,
            "count": count,
            "mode": mode
        })

        return count

    except Exception as e:
        self.logger.error("indicator_persistence.save_failed", {
            "session_id": session_id,
            "symbol": symbol,
            "variant_id": variant_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise

async def _delete_existing_indicators(self, session_id: str, symbol: str, variant_id: str):
    """Delete existing indicators for overwrite mode"""
    query = f"""
        DELETE FROM indicators
        WHERE session_id = '{session_id}'
          AND symbol = '{symbol}'
          AND indicator_id LIKE '%{variant_id}%'
    """
    await self.questdb_provider.execute_query(query)
```

---

#### Step 1.3: Zmodyfikuj load_values() - Odczyt wskaźników

**Przed** (lines 461-531):
```python
def load_values(self, session_id: str, symbol: str, variant_id: str,
               variant_type: str = "general", limit: Optional[int] = None) -> List[IndicatorValue]:
    """Load indicator values from CSV file"""
    with self._file_lock:
        csv_file_path = self._get_csv_file_path(...)
        with open(csv_file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            # ... CSV read logic ...
```

**Po**:
```python
async def load_values(self, session_id: str, symbol: str, variant_id: str,
                     variant_type: str = "general", limit: Optional[int] = None) -> List[IndicatorValue]:
    """
    Load indicator values from QuestDB.

    Args:
        session_id: Data collection session ID
        symbol: Trading pair symbol
        variant_id: Indicator variant ID
        variant_type: Type of indicator variant (for filtering)
        limit: Maximum number of values to load

    Returns:
        List of IndicatorValue objects
    """

    try:
        # Build query
        query = f"""
            SELECT
                session_id,
                symbol,
                indicator_id,
                indicator_type,
                indicator_name,
                timestamp,
                value,
                confidence,
                metadata,
                scope,
                user_id,
                created_by
            FROM indicators
            WHERE session_id = '{session_id}'
              AND symbol = '{symbol}'
              AND indicator_id LIKE '%{variant_id}%'
            ORDER BY timestamp ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        # Execute query
        results = await self.questdb_provider.execute_query(query)

        # Convert to IndicatorValue objects
        indicator_values = []
        for row in results:
            timestamp = row.get('timestamp')
            if isinstance(timestamp, datetime):
                timestamp = timestamp.timestamp()
            elif timestamp:
                timestamp = float(timestamp)

            # Parse metadata JSON if present
            metadata = row.get('metadata')
            if metadata and isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}

            value = IndicatorValue(
                timestamp=timestamp,
                value=float(row.get('value', 0)),
                confidence=float(row.get('confidence')) if row.get('confidence') is not None else None,
                indicator_id=row.get('indicator_id'),
                indicator_type=row.get('indicator_type'),
                indicator_name=row.get('indicator_name'),
                metadata=metadata or {}
            )

            # Add new fields from migration 005
            if row.get('scope'):
                value.scope = row.get('scope')
            if row.get('user_id'):
                value.user_id = row.get('user_id')
            if row.get('created_by'):
                value.created_by = row.get('created_by')

            indicator_values.append(value)

        self.logger.debug("indicator_persistence.loaded_from_questdb", {
            "session_id": session_id,
            "symbol": symbol,
            "variant_id": variant_id,
            "count": len(indicator_values)
        })

        return indicator_values

    except Exception as e:
        self.logger.error("indicator_persistence.load_failed", {
            "session_id": session_id,
            "symbol": symbol,
            "variant_id": variant_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
        return []
```

---

#### Step 1.4: Zmodyfikuj get_file_info() - Statystyki wskaźników

**Przed** (lines 712-801):
```python
def get_file_info(self, session_id: str, symbol: str, variant_id: str,
                 variant_type: str = "general") -> Dict[str, Any]:
    """Get file information from CSV"""
    csv_file_path = self._get_csv_file_path(...)
    if not csv_file_path.exists():
        return {"exists": False}

    # Count rows in CSV
    with open(csv_file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        rows = sum(1 for _ in reader) - 1  # -1 for header
```

**Po**:
```python
async def get_file_info(self, session_id: str, symbol: str, variant_id: str,
                       variant_type: str = "general") -> Dict[str, Any]:
    """
    Get indicator storage information from QuestDB.

    Returns information about stored indicator values including:
    - Total count
    - Storage path (now: questdb://indicators)
    - Size estimate

    Args:
        session_id: Data collection session ID
        symbol: Trading pair symbol
        variant_id: Indicator variant ID
        variant_type: Type of indicator variant

    Returns:
        Dictionary with file/storage info
    """

    try:
        # Count indicators in QuestDB
        query = f"""
            SELECT COUNT(*) as count
            FROM indicators
            WHERE session_id = '{session_id}'
              AND symbol = '{symbol}'
              AND indicator_id LIKE '%{variant_id}%'
        """

        results = await self.questdb_provider.execute_query(query)

        if results and len(results) > 0:
            count = results[0].get('count', 0)

            return {
                "exists": count > 0,
                "path": f"questdb://indicators/{session_id}/{symbol}/{variant_id}",
                "rows": count,
                "size": count * 100,  # Estimate: ~100 bytes per row
                "storage": "questdb",
                "session_id": session_id,
                "symbol": symbol,
                "variant_id": variant_id
            }
        else:
            return {
                "exists": False,
                "path": f"questdb://indicators/{session_id}/{symbol}/{variant_id}",
                "storage": "questdb"
            }

    except Exception as e:
        self.logger.error("indicator_persistence.get_file_info_failed", {
            "session_id": session_id,
            "symbol": symbol,
            "variant_id": variant_id,
            "error": str(e)
        })
        return {"exists": False, "error": str(e)}
```

---

### Testing Plan dla Task 1

#### Unit Tests:
```python
# tests/unit/test_indicator_persistence_service.py

import pytest
from src.domain.services.indicator_persistence_service import IndicatorPersistenceService

@pytest.mark.asyncio
async def test_save_values_to_questdb(mock_questdb_provider):
    service = IndicatorPersistenceService(
        event_bus=mock_event_bus,
        logger=mock_logger,
        questdb_provider=mock_questdb_provider
    )

    values = [
        IndicatorValue(timestamp=1000, value=65.5, confidence=0.95),
        IndicatorValue(timestamp=2000, value=66.2, confidence=0.96)
    ]

    count = await service.save_values(
        session_id="test_session",
        symbol="BTC_USDT",
        variant_id="RSI_14",
        indicator_values=values
    )

    assert count == 2
    mock_questdb_provider.insert_indicators_batch.assert_called_once()

@pytest.mark.asyncio
async def test_load_values_from_questdb(mock_questdb_provider):
    # Mock QuestDB response
    mock_questdb_provider.execute_query.return_value = [
        {
            'timestamp': datetime(2025, 10, 28, 12, 0, 0),
            'value': 65.5,
            'confidence': 0.95,
            'indicator_id': 'RSI_14',
            'indicator_type': 'RSI',
            'indicator_name': 'RSI-14'
        }
    ]

    service = IndicatorPersistenceService(
        event_bus=mock_event_bus,
        logger=mock_logger,
        questdb_provider=mock_questdb_provider
    )

    values = await service.load_values(
        session_id="test_session",
        symbol="BTC_USDT",
        variant_id="RSI_14"
    )

    assert len(values) == 1
    assert values[0].value == 65.5
```

#### Integration Tests:
```python
# tests/integration/test_indicator_persistence_questdb.py

@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_and_load_roundtrip(real_questdb_connection):
    """Test full save→load roundtrip with real QuestDB"""

    service = IndicatorPersistenceService(
        event_bus=real_event_bus,
        logger=real_logger,
        questdb_provider=real_questdb_connection
    )

    # Save indicator values
    values = [IndicatorValue(timestamp=i, value=i*10) for i in range(100)]
    count = await service.save_values("session_001", "BTC_USDT", "RSI_14", values)
    assert count == 100

    # Load back
    loaded = await service.load_values("session_001", "BTC_USDT", "RSI_14")
    assert len(loaded) == 100
    assert loaded[0].value == 0
    assert loaded[99].value == 990
```

#### Performance Tests:
```python
# tests/performance/test_indicator_persistence_benchmark.py

@pytest.mark.performance
@pytest.mark.asyncio
async def test_save_performance_csv_vs_questdb():
    """Benchmark: CSV vs QuestDB write performance"""

    values = [IndicatorValue(timestamp=i, value=random.random()*100) for i in range(10000)]

    # CSV baseline
    start = time.time()
    csv_service.save_values("session", "BTC_USDT", "RSI", values)
    csv_time = time.time() - start

    # QuestDB
    start = time.time()
    await questdb_service.save_values("session", "BTC_USDT", "RSI", values)
    questdb_time = time.time() - start

    # QuestDB should be at least 5x faster
    assert questdb_time < csv_time / 5

    print(f"CSV: {csv_time:.2f}s, QuestDB: {questdb_time:.2f}s, Speedup: {csv_time/questdb_time:.1f}x")
```

---

## Task 2: Migracja OfflineIndicatorEngine

### Obecna Architektura (CSV)

```python
# Plik: src/domain/services/offline_indicator_engine.py

def _load_symbol_data(self, session_id: str, symbol: str) -> pd.DataFrame:
    """Load historical price data from CSV"""
    prices_file = self.base_data_dir / session_id / "prices.csv"

    if not prices_file.exists():
        raise FileNotFoundError(f"Prices file not found: {prices_file}")

    df = pd.read_csv(prices_file)
    df = df[df['symbol'] == symbol]  # Filter by symbol
    return df
```

### Problem:
1. Dane już są w QuestDB (`tick_prices`, `aggregated_ohlcv`)
2. CSV read dla 100k records ~500ms
3. Duplikacja storage

---

### Nowa Architektura (QuestDB)

```python
# Plik: src/domain/services/offline_indicator_engine.py

async def _load_symbol_data(self, session_id: str, symbol: str) -> pd.DataFrame:
    """
    Load historical price data from QuestDB.

    Uses aggregated_ohlcv table for better performance.
    Falls back to tick_prices if aggregated data not available.
    """

    try:
        # Option 1: Try aggregated OHLCV first (faster)
        ohlcv_data = await self.questdb_data_provider.get_aggregated_ohlcv(
            session_id=session_id,
            symbol=symbol,
            interval='1m'  # 1-minute aggregation
        )

        if ohlcv_data:
            df = pd.DataFrame(ohlcv_data)
            # Use close price as main price
            df['price'] = df['close']
            return df

        # Option 2: Fall back to tick prices
        tick_prices = await self.questdb_data_provider.get_tick_prices(
            session_id=session_id,
            symbol=symbol
        )

        if tick_prices:
            df = pd.DataFrame(tick_prices)
            return df

        raise ValueError(f"No price data found for session {session_id}, symbol {symbol}")

    except Exception as e:
        self.logger.error("offline_indicator_engine.load_data_failed", {
            "session_id": session_id,
            "symbol": symbol,
            "error": str(e)
        })
        raise
```

### Kroki Implementacji

#### Step 2.1: Dodaj QuestDB dependency

```python
from src.data.questdb_data_provider import QuestDBDataProvider

class OfflineIndicatorEngine:
    def __init__(
        self,
        base_data_dir: str = "data",
        questdb_data_provider: Optional[QuestDBDataProvider] = None
    ):
        self.base_data_dir = Path(base_data_dir)
        self.questdb_data_provider = questdb_data_provider

        if self.questdb_data_provider is None:
            # Lazy init
            from src.data_feed.questdb_provider import QuestDBProvider
            from src.core.logger import get_logger

            questdb_provider = QuestDBProvider()
            logger = get_logger("offline_indicator_engine")
            self.questdb_data_provider = QuestDBDataProvider(questdb_provider, logger)
```

#### Step 2.2: Update _load_symbol_data()

Jak pokazano powyżej w "Nowa Architektura"

---

## Deployment Plan

### Pre-Deployment:
1. ✅ Run all tests (unit, integration, performance)
2. ✅ Backup existing CSV files
3. ✅ Apply migrations 005-007 to QuestDB
4. ✅ Migrate existing CSV data using migration scripts

### Deployment:
1. Deploy new code with QuestDB implementation
2. Monitor logs for errors
3. Verify indicator calculations match previous results
4. Check performance metrics

### Post-Deployment:
1. Monitor query latency (target: <50ms for indicator load)
2. Monitor storage usage (should decrease)
3. Check error rates (target: <0.1%)
4. Collect user feedback

### Rollback Plan:
If issues occur:
1. Revert code to use CSV (backward compatible)
2. Investigate QuestDB issues
3. Fix and re-deploy

---

## Success Criteria

✅ **Functionality**:
- All indicator save/load operations work
- Data integrity verified (checksums match)
- No data loss

✅ **Performance**:
- 5-10x faster than CSV
- Query latency <50ms
- Batch insert <10ms per 1000 records

✅ **Reliability**:
- Error rate <0.1%
- No crashes or exceptions
- Graceful error handling

✅ **Monitoring**:
- Metrics dashboards updated
- Alerts configured
- Logs properly structured

---

## Timeline

### Day 1:
- ✅ Morning: Implement Task 1.1-1.2 (save_values)
- ✅ Afternoon: Implement Task 1.3 (load_values)
- ✅ Evening: Unit tests

### Day 2:
- ✅ Morning: Implement Task 1.4 (get_file_info) + Task 2 (OfflineIndicatorEngine)
- ✅ Afternoon: Integration tests
- ✅ Evening: Performance benchmarks

### Day 3:
- ✅ Morning: Code review + fixes
- ✅ Afternoon: Deployment to staging
- ✅ Evening: Production deployment + monitoring

---

**Total**: 3 dni (20-24h effort)

**Status**: ⏳ Gotowe do implementacji
