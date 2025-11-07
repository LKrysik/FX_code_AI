# Grafana Dashboard Visual Descriptions

This document provides visual descriptions of each dashboard panel layout, helping you understand what to expect when viewing the dashboards.

---

## Dashboard 1: Trading Overview

**Purpose:** Real-time order flow, execution performance, and P&L monitoring

### Layout (Grid: 24 columns wide)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LIVE TRADING OVERVIEW                                    [Symbol: All ▼]   │
│  [Last 1h ▼] [Refresh: 5s ▼]                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                              │                               │
│  Orders Per Minute                          │  Fill Rate                    │
│  [Line graph showing order rate over time]  │  [Large percentage: 85.3%]    │
│   📈 5-10 orders/min typical                │  [Gauge: Green zone]          │
│   Peak: 15 orders/min at 14:32             │  Target: >80%                 │
│                                              │                               │
│  (12 cols wide, 8 rows tall)                │  (6 cols, 8 rows)             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Total Orders (24h)                         │  Orders Failed (24h)          │
│  [142]                                      │  [3]                          │
│  (Blue background)                          │  (Green bg - low count)       │
│  (6 cols, 4 rows)                           │  (6 cols, 4 rows)             │
├─────────────────────────────────────────────┼───────────────────────────────┤
│                                              │                               │
│  Orders Failed by Reason                    │  Order Submission Latency     │
│  [Horizontal bar chart]                     │  [Line graph with 3 lines]    │
│   ▰▰▰▰▰▰▰▰▰▰ rate_limit: 5                 │   p50: ~0.2s (blue)           │
│   ▰▰▰ insufficient_margin: 2               │   p95: ~0.8s (yellow)         │
│   ▰ invalid_order: 1                        │   p99: ~1.5s (red)            │
│                                              │                               │
│  (12 cols, 8 rows)                          │  (12 cols, 8 rows)            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Live Unrealized P&L (USD)                                                   │
│  [Area chart showing P&L trends]                                             │
│   BTC_USDT: +$45.32 (green line)                                            │
│   ETH_USDT: -$12.50 (red line)                                              │
│   Total P&L: +$32.82 (thick blue line)                                      │
│                                                                               │
│  (24 cols, 8 rows)                                                           │
├─────────────────────────────────────────────┬───────────────────────────────┤
│  Orders by Symbol (Last Hour)               │  Average Submission Latency   │
│  [Table]                                    │  [0.345s]                     │
│  Symbol    | Side | Orders                 │  [Gauge chart]                │
│  BTC_USDT  | BUY  | 12                     │  Green zone (<1s)             │
│  BTC_USDT  | SELL | 8                      │                               │
│  ETH_USDT  | BUY  | 15                     │  (12 cols, 8 rows)            │
│  ETH_USDT  | SELL | 10                     │                               │
│                                              │                               │
│  (12 cols, 8 rows)                          │                               │
└─────────────────────────────────────────────────────────────────────────────┘

Annotations: Red vertical lines mark circuit breaker events
```

**Key Visual Indicators:**
- 🟢 Green: Good performance (fill rate >80%, latency <1s)
- 🟡 Yellow: Warning (fill rate 50-80%, latency 1-3s)
- 🔴 Red: Alert (fill rate <50%, latency >3s)

---

## Dashboard 2: Risk Monitoring

**Purpose:** Track risk metrics, margin ratios, and prevent liquidations

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RISK MONITORING DASHBOARD                                [Symbol: All ▼]   │
│  [Last 1h ▼] [Refresh: 5s ▼]                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Margin Ratio                │  Daily Loss Percentage  │  Total Open        │
│  (CRITICAL < 15%)            │  (ALERT > 5%)           │  Positions         │
│                              │                         │                    │
│  [Gauge: 28.5%]             │  [Gauge: 2.3%]          │  [2]               │
│  🟢 SAFE                     │  🟢 WITHIN LIMIT        │  🟡 WARNING        │
│  (needle in green zone)      │  (needle in green)      │  (approaching 3)   │
│                              │                         │                    │
│  (8 cols, 8 rows)            │  (8 cols, 8 rows)       │  (8 cols, 8 rows)  │
├─────────────────────────────────────────────┬───────────────────────────────┤
│                                              │                               │
│  Position Concentration by Symbol            │  Risk Alerts Timeline         │
│  [Pie chart]                                │  [Bar chart over time]        │
│   🟦 BTC_USDT: 55%                          │  [Stacked bars by severity]   │
│   🟧 ETH_USDT: 45%                          │   🔴 CRITICAL: 0              │
│   Total: 2 positions                        │   🟡 WARNING: 3               │
│   ⚠️ BTC_USDT exceeds 30% concentration     │   🔵 INFO: 12                 │
│                                              │                               │
│  (12 cols, 10 rows)                         │  (12 cols, 10 rows)           │
├─────────────────────────────────────────────┼───────────────────────────────┤
│                                              │                               │
│  Margin Ratio Trend (All Positions)         │  Risk Alerts by Type          │
│  [Line graph with threshold line]           │  [Table]                      │
│   BTC_USDT: 32% (green line)                │  Alert Type      | Sev | Cnt │
│   ETH_USDT: 25% (yellow line)               │  MARGIN_LOW      | WAR | 2   │
│   --- 15% RED ALERT LINE ---                │  POSITION_LIMIT  | INF | 1   │
│   Annotations mark alerts                   │  DAILY_LOSS      | INF | 0   │
│                                              │                               │
│  (12 cols, 8 rows)                          │  (12 cols, 8 rows)            │
├─────────────────────────────────────────────┼──────────┬─────────┬──────────┤
│  Total Exposure                             │Critical  │Warning  │Info      │
│  [Stat: $1,234.56]                          │Alerts    │Alerts   │Alerts    │
│  (Green bg - within limits)                 │[0]       │[3]      │[12]      │
│  (8 cols, 6 rows)                           │(8 cols)  │(8 cols) │(8 cols)  │
└─────────────────────────────────────────────┴──────────┴─────────┴──────────┘

Annotations: Red markers show CRITICAL risk events
```

**Critical Thresholds:**
- 🔴 Margin ratio < 15%: **LIQUIDATION RISK** - Close positions immediately
- 🔴 Daily loss > 5%: **DAILY LIMIT** - Stop trading for the day
- 🟡 Open positions >= 2: Approaching max (3)
- 🔴 Open positions >= 3: **MAX LIMIT** - Cannot open more

---

## Dashboard 3: System Health

**Purpose:** Monitor EventBus, circuit breaker, and system resources

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SYSTEM HEALTH DASHBOARD                                                     │
│  [Last 1h ▼] [Refresh: 5s ▼]                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                              │                │               │
│  EventBus Throughput (Messages/sec by Topic) │ EventBus Total │Circuit Breaker│
│  [Multi-line graph]                         │ Messages/sec   │State          │
│   market_data: 50 msg/s (blue)              │                │               │
│   signal_generated: 2 msg/s (green)         │  [68.5 msg/s]  │  [CLOSED]     │
│   order_created: 1 msg/s (yellow)           │  🟢 Normal     │  🟢 NORMAL    │
│   position_updated: 0.5 msg/s (orange)      │  (6 cols)      │  (6 cols)     │
│                                              │                │               │
│  (12 cols, 10 rows)                         │  (6 cols, 10)  │  (6 cols, 10) │
├─────────────────────────────────────────────┼────────────────────────────────┤
│                                              │                               │
│  API Latency (Order Submission)             │  Circuit Breaker Timeline     │
│  [Line graph with 3 percentiles]            │  [Step graph]                 │
│   p50: 0.15s (blue)                         │  🟢 CLOSED (0): Normal ops    │
│   p95: 0.45s (yellow)                       │  🟡 HALF_OPEN (1): Testing    │
│   p99: 0.89s (red)                          │  🔴 OPEN (2): Blocking        │
│   All within acceptable range               │  Shows state transitions      │
│                                              │                               │
│  (12 cols, 8 rows)                          │  (12 cols, 8 rows)            │
├─────────────────────────────────────────────┼───────────────────────────────┤
│  EventBus Message Breakdown (Last 5 min)    │  Process Memory Usage         │
│  [Table sorted by count]                    │  [Large stat with trend]      │
│  Topic             | Messages               │  [487.3 MB]                   │
│  market_data       | 15,234                 │  🟢 Normal (<512MB)           │
│  signal_generated  | 623                    │  [Area graph showing trend]   │
│  order_created     | 142                    │                               │
│  position_updated  | 89                     │                               │
│                                              │                               │
│  (12 cols, 8 rows)                          │  (12 cols, 8 rows)            │
├──────────┬──────────┬──────────┬────────────┴───────────────────────────────┤
│ Uptime   │ CPU Usage│Open FDs  │ Max FDs                                   │
│ [3d 4h]  │ [12.5%]  │ [234]    │ [1024]                                    │
│ 🔵 Info  │ 🟢 Normal│ 🟢 Normal│ 🔵 Info                                   │
│ (6 cols) │ (6 cols) │ (6 cols) │ (6 cols)                                  │
└──────────┴──────────┴──────────┴────────────────────────────────────────────┘

Annotations: Red/yellow lines mark circuit breaker state changes
```

**Health Indicators:**
- 🟢 Green: System healthy, all metrics normal
- 🟡 Yellow: Warning - approaching limits (EventBus >500 msg/s, Memory >512MB, CPU >50%)
- 🔴 Red: Alert - Circuit breaker OPEN, Memory >1GB, CPU >80%

---

## Dashboard 4: Strategy Performance

**Purpose:** Evaluate strategy effectiveness and performance metrics

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STRATEGY PERFORMANCE DASHBOARD           [Strategy: All ▼] [Symbol: All ▼] │
│  [Last 24h ▼] [Refresh: 10s ▼]                                             │
├─────────────────────────────────────────────┬───────────────────────────────┤
│                                              │                               │
│  Signals Generated per Strategy (24h)       │  Signal Generation Rate       │
│  [Horizontal bar gauge]                     │  [Multi-line time series]     │
│   ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰ Strategy_A: 45          │  Strategy_A: 1.8 sig/hour     │
│   ▰▰▰▰▰▰▰▰▰ Strategy_B: 28                 │  Strategy_B: 1.2 sig/hour     │
│   ▰▰▰▰▰ Strategy_C: 12                     │  Strategy_C: 0.5 sig/hour     │
│                                              │                               │
│  (12 cols, 8 rows)                          │  (12 cols, 8 rows)            │
├────────────────────┬───────────────────────┼───────────────────────────────┤
│ Signal Distribution│ Win Rate              │ Average P&L per Position      │
│ [Pie chart]        │ [Gauge]               │ [Large stat]                  │
│  🟦 Strategy_A: 54%│                       │                               │
│  🟧 Strategy_B: 33%│  [62.5%]              │  [$8.75]                      │
│  🟩 Strategy_C: 13%│  🟢 GOOD              │  🟢 PROFITABLE                │
│                    │  (>55% target)        │  (Green bg)                   │
│                    │                       │                               │
│ (8 cols, 8 rows)   │ (8 cols, 8 rows)      │ (8 cols, 8 rows)              │
├────────────────────┴───────────────────────┼───────────────────────────────┤
│  Strategy Performance Summary               │  Signal Confidence            │
│  [Table]                                    │  [Multi-line graph]           │
│  Strategy   | Signals (24h) | Color         │  Strategy_A p50: 0.72         │
│  Strategy_A | 45            | 🟧 Yellow     │  Strategy_A p95: 0.89         │
│  Strategy_B | 28            | 🟡 Yellow     │  Strategy_B p50: 0.68         │
│  Strategy_C | 12            | 🟢 Green      │  Strategy_B p95: 0.85         │
│                                              │                               │
│  (12 cols, 8 rows)                          │  (12 cols, 8 rows)            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Cumulative P&L Over Time                                                    │
│  [Large area chart with threshold]                                           │
│   Starting: $0 → Current: $32.82 (green area above zero line)               │
│   Shows upward trend with minor drawdowns                                    │
│   --- Zero line ---                                                          │
│                                                                               │
│  (24 cols, 8 rows)                                                           │
├──────────┬──────────┬──────────────┬────────────────────────────────────────┤
│ Total    │ Active   │ Sharpe Ratio │ Profit Factor                         │
│ Signals  │Strategies│ (Estimated)  │                                       │
│ [85]     │ [3]      │ [1.45]       │ [1.82]                                │
│ 🔵 Info  │ 🔵 Info  │ 🟢 Good      │ 🟢 Good                               │
│ (6 cols) │ (6 cols) │ (6 cols)     │ (6 cols)                              │
└──────────┴──────────┴──────────────┴────────────────────────────────────────┘

Annotations: Blue markers show signal bursts (>10 signals in 5 min)
```

**Performance Indicators:**
- **Win Rate:** >55% = 🟢 Good, 40-55% = 🟡 Average, <40% = 🔴 Poor
- **Sharpe Ratio:** >2.0 = 🔵 Excellent, >1.0 = 🟢 Good, >0.5 = 🟡 Fair, <0.5 = 🔴 Poor
- **Profit Factor:** >2.0 = 🔵 Excellent, >1.5 = 🟢 Good, >1.0 = 🟡 Fair, <1.0 = 🔴 Poor

---

## Dashboard 5: Exchange Integration

**Purpose:** Monitor MEXC API health, rate limits, and position sync

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  EXCHANGE INTEGRATION DASHBOARD                           [Symbol: All ▼]   │
│  [Last 1h ▼] [Refresh: 5s ▼]                                               │
├─────────────────────────────────────────────┬───────┬───────────────────────┤
│                                              │Average│MEXC API              │
│  MEXC API Latency (Order Operations)        │Latency│Requests/sec          │
│  [Line graph with 3 percentiles]            │       │                      │
│   p50: 0.23s (blue)                         │[0.45s]│ [3.2 req/s]          │
│   p95: 0.78s (yellow)                       │🟢 Good│ 🟢 Safe              │
│   p99: 1.45s (red)                          │       │ (well below 10/s)    │
│   All acceptable                            │       │                      │
│                                              │       │                      │
│  (12 cols, 8 rows)                          │(6 c)  │ (6 cols)             │
├─────────────────────────────────────────────┼───────┴───────────────────────┤
│                                              │                               │
│  MEXC API Error Rate                        │  Exchange Errors by Reason    │
│  [Time series with threshold shading]       │  [Table]                      │
│   Current: 2.3% (green area)                │  Reason          | Count      │
│   --- 5% Warning line ---                   │  rate_limit      | 2          │
│   --- 10% Alert line ---                    │  timeout         | 1          │
│   Stable and low                            │  invalid_order   | 0          │
│                                              │                               │
│  (12 cols, 8 rows)                          │  (12 cols, 8 rows)            │
├──────────────────────┬──────────────────────┼───────────────────────────────┤
│ Position Sync Status │Circuit Breaker Status│ Total Orders (24h)            │
│                      │ (MEXC)               │                               │
│ [8 seconds ago]      │ [CLOSED]             │ [142]                         │
│ 🟢 SYNCING           │ 🟢 NORMAL            │ 🔵 Info                       │
│ (Last sync: 14:32:08)│ (All requests OK)    │                               │
│                      │                      │                               │
│ (8 cols, 6 rows)     │ (8 cols, 6 rows)     │ (8 cols, 6 rows)              │
├──────────────────────┴──────────────────────┼───────────────────────────────┤
│                                              │                               │
│  Order Book Depth (if available)            │  Position Sync Frequency      │
│  [Area chart with dual axes]                │  [Line graph]                 │
│   🟢 Bids (green area)                      │  Target: 6 syncs/min          │
│   🔴 Asks (red area)                        │  Current: 5.8 syncs/min       │
│   Shows market liquidity                    │  🟢 Within range              │
│                                              │                               │
│  (12 cols, 8 rows)                          │  (12 cols, 8 rows)            │
├─────────────────────────────────────────────┼───────────────────────────────┤
│  Latest Orders Status                       │  Rate Limit Margin            │
│  [Table with join of submitted & filled]    │  [Large stat with trend]      │
│  Symbol    | Side | Submitted | Filled      │  [6.8 req/s headroom]         │
│  BTC_USDT  | BUY  | 8         | 7           │  🟢 SAFE                      │
│  BTC_USDT  | SELL | 5         | 5           │  (10 - 3.2 = 6.8)            │
│  ETH_USDT  | BUY  | 10        | 9           │  [Area graph showing usage]   │
│                                              │                               │
│  (12 cols, 8 rows)                          │  (12 cols, 8 rows)            │
└─────────────────────────────────────────────┴───────────────────────────────┘

Annotations:
- Red lines: MEXC circuit breaker events
- Orange lines: Rate limit hits
```

**Exchange Health Indicators:**
- 🟢 Green: API latency <1s, error rate <5%, sync <30s, rate margin >5 req/s
- 🟡 Yellow: API latency 1-2s, error rate 5-10%, sync 30-60s, rate margin 2-5 req/s
- 🔴 Red: API latency >2s, error rate >10%, sync >60s, rate margin <2 req/s, circuit breaker OPEN

---

## Common Visual Elements Across All Dashboards

### Color Scheme

**Threshold Colors:**
- 🟢 **Green:** Good / Healthy / Within limits
- 🟡 **Yellow:** Warning / Approaching limits / Needs attention
- 🔴 **Red:** Critical / Alert / Action required immediately
- 🔵 **Blue:** Informational / Neutral metric

**Chart Types Used:**
- **Line Graph:** Time-series data (latency, throughput, P&L trends)
- **Bar Gauge:** Comparisons between categories (signals per strategy, errors by reason)
- **Gauge:** Single-value metrics with thresholds (margin ratio, win rate, Sharpe ratio)
- **Stat:** Large single-value display with background color coding
- **Table:** Detailed breakdowns with sortable columns
- **Pie Chart:** Distribution percentages (position concentration, signal distribution)
- **Area Chart:** Cumulative metrics (P&L over time, memory usage)

### Legend Patterns

All time-series graphs include:
- **Solid lines:** Actual metrics
- **Dashed lines:** Thresholds or targets
- **Shaded areas:** Zones (green = safe, yellow = warning, red = danger)

### Responsive Design

Dashboards automatically adjust:
- Panel sizes scale to screen width
- Text sizes remain readable
- Mobile view stacks panels vertically
- Desktop view uses full 24-column grid

---

## Dashboard Usage Scenarios

### Scenario 1: Live Trading Monitoring (Active Session)

**Primary Dashboard:** Trading Overview (1)
**Secondary Dashboards:** Risk Monitoring (2), System Health (3)

**Monitoring Flow:**
1. Start with Trading Overview - watch order flow and P&L
2. Check Risk Monitoring every 5 minutes - ensure margin >15%, daily loss <5%
3. Check System Health periodically - circuit breaker should be CLOSED

**Alert Response:**
- **Fill rate drops <80%:** Check Exchange Integration dashboard for API issues
- **Margin ratio <15%:** CRITICAL - close positions immediately
- **Daily loss >5%:** STOP TRADING - daily limit reached
- **Circuit breaker OPEN:** Check System Health logs, wait for recovery

### Scenario 2: Strategy Optimization (Post-Trading Analysis)

**Primary Dashboard:** Strategy Performance (4)
**Secondary Dashboards:** Trading Overview (1)

**Analysis Flow:**
1. Review win rate - target >55%
2. Check Sharpe ratio - target >1.0 (ideally >2.0)
3. Analyze signal distribution - identify over/under-performing strategies
4. Review cumulative P&L trend - should be upward with controlled drawdowns
5. Compare signal confidence vs. actual P&L - high confidence should = better performance

**Optimization Actions:**
- **Win rate <40%:** Disable or tune strategy parameters
- **Sharpe ratio <0.5:** Strategy has poor risk-adjusted returns - review entry/exit logic
- **One strategy generates >80% signals:** Over-diversification issues
- **P&L trend downward:** Re-evaluate strategy assumptions

### Scenario 3: Incident Response (Exchange Down / Circuit Breaker Open)

**Primary Dashboard:** Exchange Integration (5)
**Secondary Dashboards:** System Health (3), Trading Overview (1)

**Troubleshooting Flow:**
1. Check Circuit Breaker Status - identify which service is OPEN
2. Review Exchange Errors by Reason - identify root cause (rate_limit, timeout, etc.)
3. Check MEXC API Latency - if >3s, exchange may be slow/down
4. Review Position Sync Status - if >60s, manual position reconciliation needed
5. Monitor Rate Limit Margin - ensure not hitting MEXC's 10 req/s limit

**Recovery Actions:**
- **Circuit breaker OPEN:** Wait 30s for HALF_OPEN, then 1 successful call → CLOSED
- **Rate limit exceeded:** Reduce order frequency, wait for rate limit window reset
- **Position sync failure:** Manually verify positions on MEXC web UI
- **High error rate:** Check MEXC status page, consider pausing trading

### Scenario 4: Performance Tuning (System Optimization)

**Primary Dashboard:** System Health (3)
**Secondary Dashboard:** Trading Overview (1)

**Optimization Flow:**
1. Check EventBus throughput - target <1000 msg/s
2. Monitor memory usage - should be stable (not growing)
3. Review CPU usage - target <50%
4. Check file descriptors - ensure not approaching max
5. Analyze API latency percentiles - p95 should be <1s

**Tuning Actions:**
- **EventBus >900 msg/s:** Reduce scrape interval, optimize event publishing
- **Memory growing:** Memory leak - check for cleanup issues, restart service
- **CPU >80%:** Optimize indicator calculations, consider horizontal scaling
- **Open FDs >800:** Connection leak - review adapter cleanup logic

---

## Tips for Effective Dashboard Usage

### 1. **Set Up Multiple Monitors**
- Monitor 1: Trading Overview + Risk Monitoring (side-by-side)
- Monitor 2: System Health + Strategy Performance
- Monitor 3: Exchange Integration

### 2. **Configure Alerts**
- Critical alerts → PagerDuty / SMS (margin low, circuit breaker open, daily loss limit)
- Warning alerts → Slack / Email (high error rate, approaching limits)
- Info alerts → Dashboard notifications only

### 3. **Use Time Range Presets**
- **Real-time monitoring:** Last 15 minutes
- **Session analysis:** Last 1 hour or 6 hours
- **Daily review:** Last 24 hours
- **Weekly review:** Last 7 days

### 4. **Filter with Template Variables**
- Select specific symbols to focus on
- Filter strategies during A/B testing
- Use "All" for overview, specific values for deep-dive

### 5. **Leverage Annotations**
- Annotations automatically mark important events
- Circuit breaker changes, critical alerts, signal bursts
- Hover over annotations for details

---

**Document Version:** 1.0
**Last Updated:** 2025-11-07
**Created By:** Agent 5 (Monitoring & Observability)
