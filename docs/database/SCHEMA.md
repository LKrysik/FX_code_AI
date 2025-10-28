# Database Schema

QuestDB schema for the FX Cryptocurrency Trading System.

## Time-Series Tables

### tick_prices
Real-time market price data (1-second resolution).

\`\`\`sql
CREATE TABLE tick_prices (
    session_id SYMBOL capacity 256 CACHE,
    symbol SYMBOL capacity 256 CACHE,
    timestamp TIMESTAMP,
    price DOUBLE,
    volume DOUBLE,
    quote_volume DOUBLE
) timestamp(timestamp) PARTITION BY DAY WAL;
\`\`\`

### indicators
Calculated indicator values.

\`\`\`sql
CREATE TABLE indicators (
    symbol SYMBOL capacity 256 CACHE,
    indicator_id SYMBOL capacity 1024 CACHE,
    timestamp TIMESTAMP,
    value DOUBLE,
    confidence DOUBLE,
    metadata STRING
) timestamp(timestamp) PARTITION BY DAY WAL;
\`\`\`

## Relational Tables

### data_collection_sessions
Session metadata and statistics.

\`\`\`sql
CREATE TABLE data_collection_sessions (
    session_id STRING,
    symbols STRING,
    data_types STRING,
    status STRING,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    records_collected INT,
    prices_count INT,
    orderbook_count INT
);
\`\`\`

---

For full setup guide, see [QUESTDB.md](QUESTDB.md).
