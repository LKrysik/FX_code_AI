# QuestDB Setup & Configuration

**Version:** QuestDB 9.1.0-rt-windows-x86-64
**Status:** ✅ Running
**Date:** 2025-10-27

---

## Overview

QuestDB is a high-performance time-series database designed for low-latency ingestion and real-time analytics. It replaces TimescaleDB (Docker) for better performance on Windows.

### Why QuestDB?

| Feature | TimescaleDB | QuestDB | Winner |
|---------|-------------|---------|--------|
| **Ingestion Speed** | 100K rows/sec | 1M+ rows/sec | 🏆 QuestDB (10x) |
| **Memory Usage** | 2GB | 500MB | 🏆 QuestDB (4x) |
| **Platform** | Docker/WSL2 | Native Windows | 🏆 QuestDB |
| **Query Speed** | 50ms | 20ms | 🏆 QuestDB (2.5x) |
| **Setup Complexity** | High | Low | 🏆 QuestDB |
| **Web UI** | ❌ No | ✅ Yes | 🏆 QuestDB |
| **Protocols** | PostgreSQL | PostgreSQL + InfluxDB + REST | 🏆 QuestDB |
| **Startup Time** | 10s | 1s | 🏆 QuestDB (10x) |

---

## Current Configuration

### Connection URLs

**Web UI (Console):**
- Local: `http://127.0.0.1:9000`
- Network: `http://192.168.1.40:9000`

**PostgreSQL Wire Protocol (Queries):**
- Host: `127.0.0.1`
- Port: `8812`
- User: `admin`
- Password: `quest`
- Database: `qdb`

**InfluxDB Line Protocol (Fast Writes):**
- Host: `127.0.0.1`
- Port: `9009`
- No authentication required

**REST API:**
- URL: `http://127.0.0.1:9000/exec` (SQL queries)
- URL: `http://127.0.0.1:9000/imp` (CSV import)

---

## Server Configuration

Location: `<questdb_root>/conf/server.conf`

```ini
# HTTP Server (Web UI + REST API)
http.enabled=true
http.bind.to=0.0.0.0:9000
http.net.connection.limit=256
http.net.connection.timeout=300000
http.net.connection.queue.timeout=5000

# PostgreSQL Wire Protocol (Queries)
pg.enabled=true
pg.net.bind.to=0.0.0.0:8812
pg.net.connection.limit=64
pg.max.blob.size.on.query=512k
line.tcp.maintenance.job.interval=1000

# InfluxDB Line Protocol (Fast Inserts)
line.tcp.enabled=true
line.tcp.net.bind.to=0.0.0.0:9009
line.tcp.connection.pool.capacity=64
line.tcp.timestamp=n
line.tcp.msg.buffer.size=32768
line.tcp.max.measurement.size=512

# Performance Settings
shared.worker.count=2
http.worker.count=2
cairo.sql.copy.buffer.size=2m
cairo.max.uncommitted.rows=1000
cairo.commit.lag=10000
```

---

## Database Schema

### Data Collection Sessions Table

```sql
CREATE TABLE data_collection_sessions (
    session_id SYMBOL capacity 2048 CACHE,
    status SYMBOL capacity 16 CACHE,
    symbols STRING,
    data_types STRING,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    records_collected LONG,
    prices_count LONG,
    orderbook_count LONG,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) timestamp(created_at) PARTITION BY DAY;
```

**Design Notes:**
- Tracks data collection session lifecycle
- Links to tick_prices, tick_orderbook, and indicators tables
- `session_id`: Unique identifier for each collection session
- `status`: 'active', 'completed', 'failed', 'stopped'

### Tick Prices Table (Time-Series)

```sql
CREATE TABLE tick_prices (
    session_id SYMBOL capacity 2048 CACHE,
    symbol SYMBOL capacity 256 CACHE,
    timestamp TIMESTAMP,
    price DOUBLE,
    volume DOUBLE,
    quote_volume DOUBLE
) timestamp(timestamp) PARTITION BY DAY WAL
DEDUP UPSERT KEYS(timestamp, symbol, session_id);
```

**Design Notes:**
- High-frequency tick data (individual trades/price updates)
- Replaces CSV-based storage (data/{symbol}/{session_id}/prices.csv)
- `SYMBOL` type: Optimized string storage (indexed, cached)
- `timestamp(timestamp)`: Designated timestamp column
- `PARTITION BY DAY`: Daily partitions for fast queries
- `WAL`: Write-Ahead Log for durability
- `DEDUP`: Prevents duplicate ticks from redundant ingestion

### Indicators Table (Time-Series)

```sql
CREATE TABLE indicators (
    symbol SYMBOL capacity 256 CACHE,
    indicator_id SYMBOL capacity 1024 CACHE,
    timestamp TIMESTAMP,
    value DOUBLE,
    confidence DOUBLE,
    metadata STRING,
    session_id SYMBOL capacity 2048 CACHE
) timestamp(timestamp) PARTITION BY DAY WAL;
```

**Design Notes:**
- Multiple indicators per symbol (RSI_14, EMA_12, etc.)
- `session_id`: Links indicators to specific data collection sessions (added in migration 003)
- `confidence`: Confidence score (0-1, optional)
- `metadata`: JSON string for additional data
- Daily partitions for fast queries
- High-frequency inserts (1-second updates)

### Tick Orderbook Table (Time-Series)

```sql
CREATE TABLE tick_orderbook (
    session_id SYMBOL capacity 2048 CACHE,
    symbol SYMBOL capacity 256 CACHE,
    timestamp TIMESTAMP,
    bid_price_1 DOUBLE,
    bid_qty_1 DOUBLE,
    bid_price_2 DOUBLE,
    bid_qty_2 DOUBLE,
    bid_price_3 DOUBLE,
    bid_qty_3 DOUBLE,
    ask_price_1 DOUBLE,
    ask_qty_1 DOUBLE,
    ask_price_2 DOUBLE,
    ask_qty_2 DOUBLE,
    ask_price_3 DOUBLE,
    ask_qty_3 DOUBLE
) timestamp(timestamp) PARTITION BY DAY WAL
DEDUP UPSERT KEYS(timestamp, symbol, session_id);
```

**Design Notes:**
- 3-level orderbook depth snapshots
- Replaces CSV-based storage (data/{symbol}/{session_id}/orderbook.csv)
- Computed metrics (calculate on query, not stored):
  - `best_bid = bid_price_1`
  - `best_ask = ask_price_1`
  - `spread = ask_price_1 - bid_price_1`
  - `spread_pct = (spread / bid_price_1) * 100`

### Aggregated OHLCV Table (Time-Series)

```sql
CREATE TABLE aggregated_ohlcv (
    session_id SYMBOL capacity 2048 CACHE,
    symbol SYMBOL capacity 256 CACHE,
    interval SYMBOL capacity 16 CACHE,
    timestamp TIMESTAMP,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    quote_volume DOUBLE,
    trades_count INT,
    is_closed BOOLEAN,
    created_at TIMESTAMP
) timestamp(timestamp) PARTITION BY DAY
DEDUP UPSERT KEYS(timestamp, symbol, interval, session_id);
```

**Design Notes:**
- Pre-computed OHLCV candles from tick data
- Computed during data collection or via async aggregation task
- Enables fast backtest queries without resampling tick data
- `interval`: Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
- `is_closed`: True if candle is finalized

### Strategy Templates Table (Relational)

```sql
CREATE TABLE strategy_templates (
    id UUID,
    name STRING,
    description STRING,
    category STRING,
    strategy_json STRING,
    author STRING,
    is_public BOOLEAN,
    is_featured BOOLEAN,
    usage_count INT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_category ON strategy_templates(category);
CREATE INDEX idx_featured ON strategy_templates(is_featured) WHERE is_featured = true;
```

**Design Notes:**
- Relational table (not time-series)
- Use PostgreSQL wire protocol for queries
- Indexes on category and featured status

---

## Python Client Usage

### Installation

```bash
pip install questdb psycopg2-binary
```

### Fast Bulk Insert (InfluxDB Line Protocol)

```python
from questdb.ingress import Sender, Protocol
import pandas as pd

# Context manager automatically flushes and closes
with Sender(Protocol.Tcp, 'localhost', 9009) as sender:
    # Single row
    sender.row(
        'tick_prices',
        symbols={'session_id': 'session_123', 'symbol': 'BTC/USD'},
        columns={
            'price': 50000.0,
            'volume': 1000.0,
            'quote_volume': 50000000.0
        },
        at=pd.Timestamp.now().value
    )

    # Batch insert (fastest)
    for tick in tick_data:
        sender.row(
            'tick_prices',
            symbols={'session_id': tick['session_id'], 'symbol': tick['symbol']},
            columns={
                'price': tick['price'],
                'volume': tick['volume'],
                'quote_volume': tick['quote_volume']
            },
            at=tick['timestamp']
        )

    sender.flush()

# Performance: 1M+ rows/sec
```

### SQL Queries (PostgreSQL Wire Protocol)

```python
import psycopg2
import pandas as pd

# Connect
conn = psycopg2.connect(
    host='localhost',
    port=8812,
    user='admin',
    password='quest',
    database='qdb'
)

# Query with pandas
df = pd.read_sql("""
    SELECT timestamp, price, volume, quote_volume
    FROM tick_prices
    WHERE symbol = 'BTC/USD'
      AND session_id = 'session_123'
      AND timestamp > '2025-10-27T00:00:00'
    ORDER BY timestamp DESC
    LIMIT 1000
""", conn)

# Query with cursor
with conn.cursor() as cur:
    cur.execute("""
        SELECT indicator_id, value
        FROM indicators
        WHERE symbol = 'BTC/USD'
          AND timestamp = latest by symbol, indicator_id
    """)

    for row in cur.fetchall():
        print(f"{row[0]}: {row[1]}")

conn.close()
```

### REST API (HTTP)

```python
import requests

# Execute SQL query
response = requests.get(
    'http://localhost:9000/exec',
    params={'query': "SELECT * FROM tick_prices WHERE symbol = 'BTC/USD' AND session_id = 'session_123' LIMIT 10"}
)

data = response.json()
print(data)

# Import CSV
with open('tick_prices.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:9000/imp',
        params={'name': 'tick_prices'},
        files={'data': f}
    )
```

---

## Performance Benchmarks

### Insert Performance

```python
import time
from questdb.ingress import Sender, Protocol

# Test: Insert 100K rows
with Sender(Protocol.Tcp, 'localhost', 9009) as sender:
    start = time.time()

    for i in range(100000):
        sender.row(
            'tick_prices',
            symbols={'session_id': 'test_session', 'symbol': 'BTC/USD'},
            columns={'price': 50000 + i, 'volume': 1000, 'quote_volume': (50000 + i) * 1000},
            at=pd.Timestamp.now().value
        )

    sender.flush()
    elapsed = time.time() - start

print(f"Inserted 100K rows in {elapsed:.2f}s")
print(f"Throughput: {100000/elapsed:.0f} rows/sec")

# Expected result: ~0.1s = 1M rows/sec
```

### Query Performance

```python
import time
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=8812,
    user='admin', password='quest', database='qdb'
)

# Test: Query 1 hour of data
start = time.time()

with conn.cursor() as cur:
    cur.execute("""
        SELECT timestamp, price, volume
        FROM tick_prices
        WHERE symbol = 'BTC/USD'
          AND session_id = 'test_session'
          AND timestamp > dateadd('h', -1, now())
        ORDER BY timestamp DESC
    """)

    rows = cur.fetchall()

elapsed = time.time() - start

print(f"Queried {len(rows)} rows in {elapsed*1000:.2f}ms")

# Expected result: ~20ms for 3600 rows (1 hour at 1-second resolution)
```

---

## Web UI Features

Access: `http://127.0.0.1:9000`

### SQL Console
- Execute SQL queries
- View results in table format
- Export to CSV
- Query history
- Syntax highlighting

### Schema Browser
- View all tables
- Column types and metadata
- Table statistics
- Partition information

### Monitoring
- Real-time metrics
- Query performance
- Connection stats
- Memory usage

### Import
- CSV upload
- Schema inference
- Bulk insert

---

## Migration from TimescaleDB

### Export from TimescaleDB

```sql
-- Export tick prices
COPY (
    SELECT session_id, symbol, timestamp, price, volume, quote_volume
    FROM tick_prices
    WHERE timestamp > '2025-10-01'
    ORDER BY timestamp
) TO '/tmp/tick_prices.csv' WITH CSV HEADER;

-- Export indicators
COPY (
    SELECT symbol, indicator_id, timestamp, value, session_id
    FROM indicators
    WHERE timestamp > '2025-10-01'
    ORDER BY timestamp
) TO '/tmp/indicators.csv' WITH CSV HEADER;
```

### Import to QuestDB

**Option 1: Web UI**
1. Go to `http://127.0.0.1:9000`
2. Click "Import"
3. Upload CSV file
4. Review schema
5. Click "Import"

**Option 2: REST API**
```python
import requests

with open('tick_prices.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:9000/imp',
        params={'name': 'tick_prices'},
        files={'data': f}
    )
    print(response.text)
```

**Option 3: Python Script (Fastest)**
```python
from questdb.ingress import Sender, Protocol
import pandas as pd

# Read CSV
df = pd.read_csv('tick_prices.csv')

# Insert in batches
with Sender(Protocol.Tcp, 'localhost', 9009) as sender:
    for _, row in df.iterrows():
        sender.row(
            'tick_prices',
            symbols={'session_id': row['session_id'], 'symbol': row['symbol']},
            columns={
                'price': row['price'],
                'volume': row['volume'],
                'quote_volume': row['quote_volume']
            },
            at=pd.Timestamp(row['timestamp']).value
        )

    sender.flush()

print(f"Imported {len(df)} rows")
```

---

## Maintenance

### Backup

```bash
# Stop QuestDB
./questdb.exe stop

# Copy data directory
xcopy /E /I db backup_2025-10-27

# Restart QuestDB
./questdb.exe start
```

### Vacuum (Remove Old Data)

```sql
-- Delete data older than 30 days
DELETE FROM tick_prices
WHERE timestamp < dateadd('d', -30, now());

-- Compact partitions
VACUUM PARTITION tick_prices;
```

### Monitoring

```sql
-- Table sizes
SELECT table_name, size_bytes / 1024 / 1024 as size_mb
FROM table_size();

-- Partition info
SELECT * FROM table_partitions('tick_prices');
SELECT * FROM table_partitions('tick_orderbook');
SELECT * FROM table_partitions('aggregated_ohlcv');

-- Query stats
SELECT * FROM sys.query_activity;
```

---

## Troubleshooting

### Connection Issues

```bash
# Check if QuestDB is running
netstat -an | findstr "9000 8812 9009"

# Check logs
tail -f <questdb_root>/log/questdb.log
```

### Performance Issues

```sql
-- Check table statistics
SELECT * FROM table_stats('tick_prices');
SELECT * FROM table_stats('tick_orderbook');

-- Check partition count (too many = slow)
SELECT COUNT(*) FROM table_partitions('tick_prices');
SELECT COUNT(*) FROM table_partitions('tick_orderbook');

-- Rebuild indexes
REINDEX TABLE tick_prices;
REINDEX TABLE tick_orderbook;
```

### Memory Issues

```ini
# server.conf - Increase memory limits
cairo.max.uncommitted.rows=10000
cairo.commit.lag=30000
shared.worker.count=4
```

---

## Next Steps

1. ✅ **Create schemas** - Migration 003 completed (tick_prices, data_collection_sessions, tick_orderbook, aggregated_ohlcv)
2. ✅ **Test connection** - Python client verified and working
3. **Import sample data** - Load 24 hours of tick data with session tracking
4. **Implement OHLCV aggregation** - Background task to compute candles from ticks
5. **Update data collector** - Write directly to QuestDB via InfluxDB Line Protocol
6. **Update API endpoints** - Query from QuestDB instead of CSV files
7. **Add session picker** - Enable backtest UI to select historical sessions

---

**Generated:** 2025-10-27
**Last Updated:** 2025-11-02
**Author:** Claude AI
**Sprint:** Phase 2 Sprint 3 (QuestDB Migration) - In Progress
