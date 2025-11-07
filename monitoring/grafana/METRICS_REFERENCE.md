# Grafana Metrics Quick Reference Card

**Purpose:** Quick lookup guide for all Prometheus metrics used in dashboards

---

## Prometheus Metrics Overview

### Order Metrics

| Metric Name | Type | Labels | Description | Example Query |
|------------|------|--------|-------------|---------------|
| `orders_submitted_total` | Counter | symbol, side, order_type | Total orders submitted to exchange | `sum(rate(orders_submitted_total[1m])) * 60` |
| `orders_filled_total` | Counter | symbol, side | Total orders filled by exchange | `sum(rate(orders_filled_total[5m]))` |
| `orders_failed_total` | Counter | symbol, reason | Total orders failed | `sum by (reason) (increase(orders_failed_total[1h]))` |
| `order_submission_latency_seconds` | Histogram | symbol | Order submission latency | `histogram_quantile(0.95, sum(rate(order_submission_latency_seconds_bucket[5m])) by (le))` |

**Bucket Ranges:** `[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]` seconds

### Position Metrics

| Metric Name | Type | Labels | Description | Example Query |
|------------|------|--------|-------------|---------------|
| `positions_open_total` | Gauge | symbol | Total number of open positions | `sum(positions_open_total)` |
| `unrealized_pnl_usd` | Gauge | symbol | Unrealized P&L in USD | `sum by (symbol) (unrealized_pnl_usd)` |
| `margin_ratio_percent` | Gauge | symbol | Margin ratio (equity / maintenance_margin * 100) | `min(margin_ratio_percent)` |

### Risk Metrics

| Metric Name | Type | Labels | Description | Example Query |
|------------|------|--------|-------------|---------------|
| `risk_alerts_total` | Counter | severity, alert_type | Total risk alerts triggered | `sum by (severity) (rate(risk_alerts_total[1m]))` |
| `daily_loss_percent` | Gauge | - | Daily loss as percentage of capital | `daily_loss_percent` |

**Severity Values:** `CRITICAL`, `WARNING`, `INFO`
**Alert Types:** `MARGIN_LOW`, `DAILY_LOSS_LIMIT`, `POSITION_LIMIT`, `CONCENTRATION`, `DRAWDOWN`

### System Metrics

| Metric Name | Type | Labels | Description | Example Query |
|------------|------|--------|-------------|---------------|
| `event_bus_messages_total` | Counter | topic | Total EventBus messages published | `sum by (topic) (rate(event_bus_messages_total[1m]))` |
| `circuit_breaker_state` | Gauge | service | Circuit breaker state (0=CLOSED, 1=HALF_OPEN, 2=OPEN) | `circuit_breaker_state{service="mexc_adapter"}` |

**EventBus Topics:**
- `market_data`
- `indicator_updated`
- `signal_generated`
- `order_created`
- `order_filled`
- `position_updated`
- `risk_alert`

**Circuit Breaker Services:**
- `mexc_adapter`
- `order_manager`
- `position_sync`

### Process Metrics (Standard Prometheus)

| Metric Name | Type | Description |
|------------|------|-------------|
| `process_resident_memory_bytes` | Gauge | Process memory usage |
| `process_cpu_seconds_total` | Counter | CPU time consumed |
| `process_open_fds` | Gauge | Number of open file descriptors |
| `process_max_fds` | Gauge | Maximum file descriptors allowed |
| `process_start_time_seconds` | Gauge | Process start time (Unix timestamp) |

---

## Critical Thresholds

### Trading Performance

| Metric | Green (Good) | Yellow (Warning) | Red (Critical) | Action Required |
|--------|--------------|------------------|----------------|-----------------|
| **Fill Rate** | >80% | 50-80% | <50% | Check exchange API, review order types |
| **Order Submission Latency (p95)** | <1s | 1-3s | >3s | Check network, MEXC API status |
| **Order Error Rate** | <5% | 5-10% | >10% | Review error reasons, check exchange status |

### Risk Management

| Metric | Green (Safe) | Yellow (Warning) | Red (CRITICAL) | Action Required |
|--------|--------------|------------------|----------------|-----------------|
| **Margin Ratio** | >30% | 15-30% | **<15%** | **CLOSE POSITIONS IMMEDIATELY** |
| **Daily Loss %** | <3% | 3-5% | **>5%** | **STOP TRADING FOR DAY** |
| **Open Positions** | 0-1 | 2 | **≥3** | **CANNOT OPEN MORE** |
| **Position Concentration** | <30% | 30-40% | >40% | Diversify, close largest position |

### System Health

| Metric | Green (Healthy) | Yellow (Warning) | Red (Alert) | Action Required |
|--------|-----------------|------------------|-------------|-----------------|
| **EventBus Throughput** | <500 msg/s | 500-900 msg/s | >900 msg/s | Optimize event publishing, reduce scrape interval |
| **Circuit Breaker State** | CLOSED (0) | HALF_OPEN (1) | **OPEN (2)** | **Wait for recovery, check logs** |
| **Memory Usage** | <512MB | 512MB-1GB | >1GB | Restart service, investigate memory leak |
| **CPU Usage** | <50% | 50-80% | >80% | Optimize calculations, scale horizontally |
| **Position Sync Delay** | <30s | 30-60s | **>60s** | **Manual position reconciliation required** |

### Exchange Integration

| Metric | Green (Good) | Yellow (Warning) | Red (Critical) | Action Required |
|--------|--------------|------------------|----------------|-----------------|
| **MEXC API Latency (avg)** | <0.5s | 0.5-2s | >2s | Check MEXC status, network connectivity |
| **API Request Rate** | <8 req/s | 8-10 req/s | ≥10 req/s | Rate limit hit, reduce order frequency |
| **API Error Rate** | <5% | 5-10% | >10% | Check error reasons, MEXC status page |
| **Rate Limit Margin** | >5 req/s | 2-5 req/s | <2 req/s | Approaching rate limit, slow down |

### Strategy Performance

| Metric | Excellent (Blue) | Good (Green) | Fair (Yellow) | Poor (Red) |
|--------|------------------|--------------|---------------|------------|
| **Win Rate** | N/A | >55% | 40-55% | <40% |
| **Sharpe Ratio** | >2.0 | 1.0-2.0 | 0.5-1.0 | <0.5 |
| **Profit Factor** | >2.0 | 1.5-2.0 | 1.0-1.5 | <1.0 |

---

## PromQL Query Patterns

### Rate Calculations

```promql
# Orders per minute
sum(rate(orders_submitted_total[1m])) * 60

# Messages per second
sum(rate(event_bus_messages_total[1m]))

# Error rate percentage
(sum(rate(orders_failed_total[5m])) / sum(rate(orders_submitted_total[5m]))) * 100
```

### Percentile Calculations

```promql
# p50 latency
histogram_quantile(0.50, sum(rate(order_submission_latency_seconds_bucket[5m])) by (le))

# p95 latency
histogram_quantile(0.95, sum(rate(order_submission_latency_seconds_bucket[5m])) by (le))

# p99 latency
histogram_quantile(0.99, sum(rate(order_submission_latency_seconds_bucket[5m])) by (le))
```

### Aggregations

```promql
# Sum across all symbols
sum(positions_open_total)

# Sum by symbol
sum by (symbol) (unrealized_pnl_usd)

# Count unique strategies
count(count by (strategy_name) (signal_generated_total))

# Minimum margin ratio
min(margin_ratio_percent)

# Maximum circuit breaker state
max(circuit_breaker_state)
```

### Increase Over Time

```promql
# Total orders in last 24 hours
sum(increase(orders_submitted_total[24h]))

# Total risk alerts in last hour
sum by (severity) (increase(risk_alerts_total[1h]))

# Failed orders in last 5 minutes
sum by (reason) (increase(orders_failed_total[5m]))
```

### Derived Metrics

```promql
# Fill rate percentage
(sum(rate(orders_filled_total[5m])) / sum(rate(orders_submitted_total[5m]))) * 100

# Average latency
sum(rate(order_submission_latency_seconds_sum[5m])) / sum(rate(order_submission_latency_seconds_count[5m]))

# Win rate (positions with profit)
(sum(unrealized_pnl_usd > 0) / sum(positions_open_total)) * 100

# Profit factor
sum(unrealized_pnl_usd > 0) / abs(sum(unrealized_pnl_usd < 0))

# Sharpe ratio (estimated from 24h data)
avg_over_time(unrealized_pnl_usd[24h]) / stddev_over_time(unrealized_pnl_usd[24h])

# Rate limit margin (headroom before 10 req/s limit)
10 - sum(rate(order_submission_latency_seconds_count[1m]))

# Time since last position sync
time() - position_sync_last_success_timestamp

# Uptime
time() - process_start_time_seconds
```

### Time Windows

```promql
# Common time windows used in queries:
[1m]   # 1 minute - real-time rates
[5m]   # 5 minutes - smoothed rates, latency percentiles
[1h]   # 1 hour - recent activity summary
[24h]  # 24 hours - daily totals, trends
[7d]   # 7 days - weekly analysis
```

---

## Alert Rules (Prometheus Alertmanager)

### Critical Alerts (Immediate Action Required)

```yaml
# 1. Margin Ratio Low
- alert: MarginRatioLow
  expr: margin_ratio_percent < 15
  for: 30s
  labels:
    severity: critical
  annotations:
    summary: "Margin ratio < 15% - LIQUIDATION RISK"
    description: "Margin ratio is {{ $value }}%. Close positions immediately."

# 2. Daily Loss Limit Exceeded
- alert: DailyLossLimitExceeded
  expr: daily_loss_percent > 5
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Daily loss limit exceeded (>5%)"
    description: "Daily loss is {{ $value }}%. STOP TRADING."

# 3. Circuit Breaker Open
- alert: CircuitBreakerOpen
  expr: circuit_breaker_state == 2
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Circuit breaker is OPEN"
    description: "Service {{ $labels.service }} circuit breaker is OPEN. All requests blocked."

# 7. Position Sync Failure
- alert: PositionSyncFailure
  expr: time() - position_sync_last_success_timestamp > 60
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Position sync failed (>60s since last sync)"
    description: "Last successful sync was {{ $value }}s ago. Manual reconciliation required."
```

### Warning Alerts (Attention Required)

```yaml
# 4. Order Submission Latency High
- alert: OrderSubmissionLatencyHigh
  expr: histogram_quantile(0.95, order_submission_latency_seconds) > 5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Order submission latency p95 > 5s"
    description: "p95 latency is {{ $value }}s. Check MEXC API status."

# 5. No Order Fills
- alert: NoOrderFills
  expr: rate(orders_filled_total[5m]) == 0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "No order fills in last 5 minutes"
    description: "Orders submitted but none filled. Check exchange connectivity."

# 6. High Error Rate
- alert: HighErrorRate
  expr: rate(orders_failed_total[5m]) / rate(orders_submitted_total[5m]) > 0.1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Order error rate > 10%"
    description: "Error rate is {{ $value }}%. Review error reasons."
```

---

## Metric Collection Points (EventBus Integration)

### How Metrics Are Collected

PrometheusMetrics subscribes to EventBus topics and updates metrics in real-time:

```python
# Order Created Event → orders_submitted_total.inc()
event_bus.publish("order_created", {
    "symbol": "BTC_USDT",
    "side": "BUY",
    "order_type": "MARKET",
    "submission_latency": 0.345  # seconds
})

# Order Filled Event → orders_filled_total.inc()
event_bus.publish("order_filled", {
    "symbol": "BTC_USDT",
    "side": "BUY",
    "filled_price": 50000.0,
    "filled_quantity": 0.1
})

# Position Updated Event → margin_ratio_percent.set(), unrealized_pnl_usd.set()
event_bus.publish("position_updated", {
    "symbol": "BTC_USDT",
    "unrealized_pnl": 45.32,
    "margin_ratio": 0.285  # 28.5%
})

# Risk Alert Event → risk_alerts_total.inc()
event_bus.publish("risk_alert", {
    "severity": "WARNING",
    "alert_type": "MARGIN_LOW",
    "message": "Margin ratio approaching limit"
})
```

### Manual Metric Updates

Some metrics are updated manually (not via EventBus):

```python
# Circuit breaker state change
prometheus_metrics.update_circuit_breaker_state("mexc_adapter", "OPEN")

# Daily loss calculation (updated periodically)
prometheus_metrics.update_daily_loss_percent(2.3)
```

---

## Troubleshooting Guide

### Problem: No Data in Grafana Dashboards

**Check 1:** Prometheus Scraping
```bash
# Open Prometheus UI
http://localhost:9090

# Go to Status → Targets
# Verify fx-trading-backend is UP
```

**Check 2:** Metrics Endpoint
```bash
# Test metrics endpoint directly
curl http://localhost:8080/metrics/prometheus

# Should see metrics like:
# orders_submitted_total{symbol="BTC_USDT",side="BUY",order_type="MARKET"} 42
```

**Check 3:** PrometheusMetrics Initialization
```python
# In container.py, verify:
prometheus_metrics = PrometheusMetrics(event_bus)
prometheus_metrics.subscribe_to_events()  # MUST be called
```

**Check 4:** EventBus Events
```python
# Check logs for:
"PrometheusMetrics subscribed to EventBus topics"
"Metric recorded: order_created (symbol=BTC_USDT, side=BUY)"
```

### Problem: Stale Data (Not Updating)

**Check 1:** Trading Session Active
- Verify live trading or backtesting session is running
- No data = no events = no metric updates

**Check 2:** Prometheus Scrape Interval
```yaml
# prometheus.yml
scrape_interval: 5s  # Reduce if needed
```

**Check 3:** EventBus Publishing
```python
# Check that components are publishing events
# Look for logs: "EventBus: Published to topic: order_created"
```

### Problem: High Memory Usage in Prometheus

**Solution:** Reduce retention or increase resources
```yaml
# prometheus.yml
storage:
  tsdb:
    retention.time: 15d  # Reduce from 30d
    retention.size: 20GB  # Reduce from 50GB
```

---

## Quick Reference Cards

### For Traders (Dashboard 1, 2)

| **CHECK THIS** | **EVERY** | **ACTION IF** |
|----------------|-----------|---------------|
| Fill Rate | 1 min | <80% → Check Exchange Integration |
| Margin Ratio | 1 min | <15% → **CLOSE POSITIONS NOW** |
| Daily Loss % | 5 min | >5% → **STOP TRADING** |
| P&L Chart | Continuous | Large drawdown → Review strategy |
| Open Positions | Before opening | ≥3 → Cannot open more |

### For DevOps (Dashboard 3, 5)

| **CHECK THIS** | **EVERY** | **ACTION IF** |
|----------------|-----------|---------------|
| Circuit Breaker | 1 min | OPEN → Check logs, wait for recovery |
| EventBus Throughput | 5 min | >900 msg/s → Optimize publishing |
| Memory Usage | 10 min | >1GB → Restart, check for leaks |
| Position Sync | 1 min | >60s → Manual reconciliation |
| API Latency | 5 min | p95 >3s → Check MEXC status |
| Rate Limit Margin | 1 min | <2 req/s → Slow down orders |

### For Strategy Developers (Dashboard 4)

| **CHECK THIS** | **EVERY** | **ACTION IF** |
|----------------|-----------|---------------|
| Win Rate | Daily | <40% → Tune or disable strategy |
| Sharpe Ratio | Daily | <0.5 → Poor risk-adjusted returns |
| Profit Factor | Daily | <1.0 → Net losing strategy |
| Signal Distribution | Daily | One strategy >80% → Over-reliance |
| Cumulative P&L | Continuous | Downward trend → Re-evaluate |

---

**Document Version:** 1.0
**Last Updated:** 2025-11-07
**Created By:** Agent 5 (Monitoring & Observability)
**Related Files:** `SETUP.md`, `DASHBOARD_DESCRIPTIONS.md`
