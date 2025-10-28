# REST API — Results History Merge (Supplement)

## Endpoint
- POST `/results/history/merge`

## Body
```
{
  "base_dir": "backtest/backtest_results",  // optional
  "session_ids": ["exec_2025...", "exec_2025..."] // optional (omit to auto-discover)
}
```

## Response 200
```
{
  "type": "response",
  "status": "results_merged",
  "version": "1.0",
  "timestamp": "...",
  "data": {
    "sessions": [
      {"session_id": "...", "trades_count": 10, "signals_count": 20, "summary": {...}}
    ],
    "totals": {
      "total_trades": 30,
      "winning_trades": 18,
      "losing_trades": 12,
      "win_rate": 60.0,
      "total_pnl": 123.4,
      "total_fees": 5.4,
      "net_pnl": 118.0,
      "best_trade": {"trade_id": "...", "total_pnl": 20.0},
      "worst_trade": {"trade_id": "...", "total_pnl": -5.0}
    },
    "symbols": ["ALU_USDT", "BTC_USDT", "ETH_USDT"]
  }
}
```

## Notes
- Designed for dashboard “History/Compare” views.
- Works with exported session files under `backtest/backtest_results/{session_id}`.
- Future: support per-`scope` directories for multi-tenant isolation.
