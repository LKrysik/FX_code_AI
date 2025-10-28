# Database Performance

Optimization guide for QuestDB.

## Query Optimization

### Use LATEST BY for current values
\`\`\`sql
SELECT * FROM indicators
WHERE symbol = 'BTC_USDT'
LATEST BY symbol, indicator_id;
\`\`\`

### Leverage partitioning
\`\`\`sql
SELECT * FROM tick_prices
WHERE timestamp > '2025-10-27'  -- Uses partition pruning
  AND symbol = 'BTC_USDT';
\`\`\`

## Write Optimization

- Use InfluxDB Line Protocol for bulk writes (1M+ rows/sec)
- Batch inserts when possible
- Avoid frequent commits

See [QUESTDB.md](QUESTDB.md) for performance benchmarks.
