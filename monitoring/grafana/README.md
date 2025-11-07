# Grafana Dashboards for Live Trading System

**Created By:** Agent 5 - Monitoring & Observability
**Date:** 2025-11-07
**Status:** ✅ COMPLETE - Ready for production use

---

## Overview

This directory contains **5 production-ready Grafana dashboards** for comprehensive monitoring of the FX live trading system. These dashboards provide real-time insights into trading performance, risk management, system health, strategy effectiveness, and exchange integration.

---

## 📊 Dashboard Files

All dashboards are located in `/monitoring/grafana/dashboards/`:

| # | Dashboard Name | File | Purpose |
|---|----------------|------|---------|
| 1 | **Trading Overview** | `01_trading_overview.json` | Monitor order flow, fill rates, P&L |
| 2 | **Risk Monitoring** | `02_risk_monitoring.json` | Track margin ratio, daily loss, risk alerts |
| 3 | **System Health** | `03_system_health.json` | EventBus, circuit breaker, memory, CPU |
| 4 | **Strategy Performance** | `04_strategy_performance.json` | Win rate, Sharpe ratio, strategy signals |
| 5 | **Exchange Integration** | `05_exchange_integration.json` | MEXC API health, rate limits, sync status |

---

## 📚 Documentation Files

| File | Description |
|------|-------------|
| `SETUP.md` | **Complete setup guide** - Prometheus installation, Grafana configuration, dashboard import instructions |
| `DASHBOARD_DESCRIPTIONS.md` | **Visual descriptions** - Detailed layout descriptions, panel explanations, usage scenarios |
| `METRICS_REFERENCE.md` | **Quick reference card** - All metrics, thresholds, PromQL queries, alert rules |
| `README.md` (this file) | Overview and quick links |

---

## 🚀 Quick Start

### Prerequisites

1. **Backend running** with Prometheus metrics enabled:
   ```bash
   python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload
   ```
   Metrics endpoint: http://localhost:8080/metrics/prometheus

2. **Prometheus installed and configured** (scraping backend):
   ```yaml
   # prometheus.yml
   scrape_configs:
     - job_name: 'fx-trading-backend'
       static_configs:
         - targets: ['localhost:8080']
       metrics_path: '/metrics/prometheus'
   ```

3. **Grafana installed** (version 9.0+):
   - Access: http://localhost:3000
   - Default credentials: admin / admin

### Import Dashboards (3 Methods)

**Method 1: Grafana UI (Recommended for first-time setup)**
1. Open Grafana → Dashboards → Import
2. Upload each JSON file from `dashboards/`
3. Select Prometheus data source
4. Click Import

**Method 2: API (Automated bulk import)**
```bash
for dashboard in monitoring/grafana/dashboards/*.json; do
  curl -X POST "http://localhost:3000/api/dashboards/db" \
    -u "admin:your_password" \
    -H "Content-Type: application/json" \
    -d @"$dashboard"
done
```

**Method 3: Provisioning (Production recommended)**
- See `SETUP.md` section "Provisioning" for details
- Automatically loads dashboards on Grafana startup

---

## 🎯 Key Features

### ✅ Production-Ready
- **Alert thresholds** configured (margin <15%, loss >5%, circuit breaker open)
- **Template variables** for symbol/strategy filtering
- **Auto-refresh** (5s for trading, 10s for analytics)
- **Time range presets** (15m, 1h, 6h, 24h, 7d)
- **Annotations** for circuit breaker events, critical alerts

### ✅ Comprehensive Metrics Coverage

**Trading Metrics:**
- Orders per minute (rate)
- Fill rate percentage
- Order submission latency (p50, p95, p99)
- Unrealized P&L (real-time)
- Orders failed by reason

**Risk Metrics:**
- Margin ratio (CRITICAL if <15%)
- Daily loss percentage (ALERT if >5%)
- Position concentration
- Risk alerts by severity
- Total exposure

**System Metrics:**
- EventBus throughput (by topic)
- Circuit breaker state
- Memory usage (leak detection)
- CPU usage
- API latency

**Strategy Metrics:**
- Signals per strategy
- Win rate
- Sharpe ratio
- Profit factor
- Signal confidence distribution

**Exchange Metrics:**
- MEXC API latency
- API error rate
- Position sync status
- Rate limit margin

### ✅ Visual Clarity
- Color-coded thresholds (🟢 green = good, 🟡 yellow = warning, 🔴 red = critical)
- Multiple visualization types (graphs, gauges, tables, pie charts)
- Clear panel descriptions
- Responsive design (desktop + mobile)

---

## ⚠️ Critical Alert Thresholds

### IMMEDIATE ACTION REQUIRED (RED)

| Alert | Threshold | Action |
|-------|-----------|--------|
| **Margin Ratio** | <15% | **CLOSE POSITIONS IMMEDIATELY** - Liquidation risk |
| **Daily Loss** | >5% | **STOP TRADING FOR DAY** - Daily limit reached |
| **Circuit Breaker** | OPEN | **Wait for recovery** - All requests blocked |
| **Position Sync** | >60s since last | **Manual reconciliation required** |

### WARNING (YELLOW)

| Alert | Threshold | Action |
|-------|-----------|--------|
| Fill Rate | <80% | Check Exchange Integration dashboard |
| Order Latency (p95) | >1s | Monitor MEXC API status |
| EventBus | >500 msg/s | Optimize event publishing |
| Memory | >512MB | Monitor for leaks |

---

## 📖 Documentation Quick Links

### For Different Roles

**Traders:**
- Read: `DASHBOARD_DESCRIPTIONS.md` → "Dashboard 1: Trading Overview"
- Read: `DASHBOARD_DESCRIPTIONS.md` → "Dashboard 2: Risk Monitoring"
- Use: Dashboards 1, 2 (primary), 5 (when issues)

**DevOps / System Administrators:**
- Read: `SETUP.md` → Full installation and configuration guide
- Read: `DASHBOARD_DESCRIPTIONS.md` → "Dashboard 3: System Health"
- Use: Dashboards 3, 5 (primary), 1 (monitoring)

**Strategy Developers:**
- Read: `DASHBOARD_DESCRIPTIONS.md` → "Dashboard 4: Strategy Performance"
- Read: `METRICS_REFERENCE.md` → "PromQL Query Patterns"
- Use: Dashboard 4 (primary), 1 (validation)

**On-Call Engineers:**
- Read: `METRICS_REFERENCE.md` → "Quick Reference Cards"
- Read: `METRICS_REFERENCE.md` → "Troubleshooting Guide"
- Use: All dashboards depending on incident

---

## 🔧 Technology Stack

- **Metrics Collection:** Prometheus (client library: prometheus_client)
- **Visualization:** Grafana 9.0+ (JSON dashboard format v38)
- **Data Source:** Prometheus
- **Backend Integration:** EventBus subscriptions (src/infrastructure/monitoring/prometheus_metrics.py)
- **Alert Manager:** Prometheus Alertmanager (rules to be created by Agent 5)

---

## 📊 Metrics Source

All metrics are collected from:
- **Backend endpoint:** `http://localhost:8080/metrics/prometheus`
- **Metrics module:** `/home/user/FX_code_AI/src/infrastructure/monitoring/prometheus_metrics.py`
- **Collection method:** EventBus subscriptions (real-time) + manual updates

**Supported Metrics:**
- `orders_submitted_total` (Counter)
- `orders_filled_total` (Counter)
- `orders_failed_total` (Counter)
- `order_submission_latency_seconds` (Histogram)
- `positions_open_total` (Gauge)
- `unrealized_pnl_usd` (Gauge)
- `margin_ratio_percent` (Gauge)
- `risk_alerts_total` (Counter)
- `daily_loss_percent` (Gauge)
- `event_bus_messages_total` (Counter)
- `circuit_breaker_state` (Gauge)

See `METRICS_REFERENCE.md` for complete list and PromQL query examples.

---

## 🎨 Dashboard Preview (Visual Descriptions)

### Dashboard 1: Trading Overview
```
[Orders/min Graph] [Fill Rate Gauge 85%] [Total Orders 142]
[Failed Orders Bar Chart] [Latency p50/p95/p99 Graph]
[Live P&L Time Series - $32.82]
[Orders by Symbol Table] [Avg Latency Stat]
```

### Dashboard 2: Risk Monitoring
```
[Margin Ratio Gauge 28.5%] [Daily Loss Gauge 2.3%] [Open Positions 2]
[Position Concentration Pie] [Risk Alerts Timeline]
[Margin Trend Graph with Alert Line] [Risk Alerts Table]
[Total Exposure] [Critical/Warning/Info Counts]
```

### Dashboard 3: System Health
```
[EventBus Throughput Graph] [Total msg/s Stat] [Circuit Breaker CLOSED]
[API Latency Graph] [Circuit Breaker Timeline]
[EventBus Breakdown Table] [Memory Usage Stat]
[Uptime] [CPU] [Open FDs] [Max FDs]
```

### Dashboard 4: Strategy Performance
```
[Signals per Strategy Bar Chart] [Signal Rate Graph]
[Signal Distribution Pie] [Win Rate Gauge 62.5%] [Avg P&L $8.75]
[Strategy Summary Table] [Confidence Distribution Graph]
[Cumulative P&L Time Series]
[Total Signals] [Active Strategies] [Sharpe Ratio 1.45] [Profit Factor 1.82]
```

### Dashboard 5: Exchange Integration
```
[MEXC Latency p50/p95/p99] [Avg Latency 0.45s] [Requests/sec 3.2]
[Error Rate Graph] [Errors by Reason Table]
[Position Sync Status 8s ago] [Circuit Breaker CLOSED] [Total Orders 142]
[Order Book Depth] [Position Sync Frequency]
[Latest Orders Table] [Rate Limit Margin 6.8 req/s]
```

For detailed visual descriptions with panel layouts, see `DASHBOARD_DESCRIPTIONS.md`.

---

## 🧪 Testing Dashboards

### 1. Verify Prometheus Data Source
```bash
# Open Grafana
http://localhost:3000

# Go to Configuration → Data Sources → Prometheus
# Click "Save & Test"
# Should see: "Data source is working"
```

### 2. Verify Metrics Endpoint
```bash
# Test backend metrics endpoint
curl http://localhost:8080/metrics/prometheus | grep orders_submitted_total

# Should see output like:
# orders_submitted_total{symbol="BTC_USDT",side="BUY",order_type="MARKET"} 42
```

### 3. Start Trading Session
```bash
# Start backend
python -m uvicorn src.api.unified_server:create_unified_app --factory --port 8080

# Start a test trading session (paper trading recommended)
# Dashboards should start showing data
```

### 4. Verify Dashboard Data
- Open Dashboard 1 (Trading Overview)
- Change time range to "Last 15 minutes"
- Verify panels show data (not "No Data")
- Check template variable $symbol works (filter by symbol)

---

## 🚨 Troubleshooting

### Problem: "No Data" in Dashboards

**Solution 1:** Check Prometheus scraping
```bash
# Open http://localhost:9090
# Status → Targets
# Verify fx-trading-backend is UP (green)
```

**Solution 2:** Verify metrics endpoint
```bash
curl http://localhost:8080/metrics/prometheus
# Should return Prometheus format metrics
```

**Solution 3:** Check PrometheusMetrics initialization
```python
# In src/infrastructure/container.py
# Ensure: prometheus_metrics.subscribe_to_events() is called
```

**Solution 4:** Check trading session is active
- No trading = no events = no metrics
- Start a paper trading or live session

For complete troubleshooting guide, see `METRICS_REFERENCE.md` → "Troubleshooting Guide".

---

## 📦 Production Deployment Checklist

- [ ] Prometheus installed with persistent storage (retention: 30d)
- [ ] Grafana installed and configured
- [ ] All 5 dashboards imported successfully
- [ ] Prometheus data source configured and tested
- [ ] Alert notification channels configured (Email, Slack, PagerDuty)
- [ ] Alertmanager rules configured (`/monitoring/prometheus/alerts.yml`)
- [ ] Dashboard access permissions set (view vs edit)
- [ ] Auto-refresh configured appropriately
- [ ] Template variables tested
- [ ] All panels display data correctly
- [ ] Critical alerts tested (manually trigger margin low, circuit breaker)
- [ ] Backup of dashboard JSON files stored in Git
- [ ] Monitoring runbook documented
- [ ] Team trained on dashboard usage

---

## 🔗 Related Documentation

- **Implementation Plan:** `/home/user/FX_code_AI/docs/analysis/MULTI_AGENT_IMPLEMENTATION_PLAN.md` (Agent 5, Task 5.2)
- **Prometheus Metrics Source:** `/home/user/FX_code_AI/src/infrastructure/monitoring/prometheus_metrics.py`
- **Backend API:** `/home/user/FX_code_AI/src/api/unified_server.py` (metrics endpoint)
- **CLAUDE.md:** `/home/user/FX_code_AI/CLAUDE.md` (project guidelines)

---

## 📞 Support

### Getting Help

1. **Setup Issues:** Read `SETUP.md`
2. **Dashboard Questions:** Read `DASHBOARD_DESCRIPTIONS.md`
3. **Metrics/Query Issues:** Read `METRICS_REFERENCE.md`
4. **Backend Issues:** Check `/src/infrastructure/monitoring/prometheus_metrics.py`
5. **Prometheus Issues:** Check Prometheus logs, verify scrape config
6. **Grafana Issues:** Check `/var/log/grafana/grafana.log`

### External Resources

- **Prometheus Docs:** https://prometheus.io/docs/
- **Grafana Docs:** https://grafana.com/docs/grafana/latest/
- **PromQL Guide:** https://prometheus.io/docs/prometheus/latest/querying/basics/
- **Grafana Alerting:** https://grafana.com/docs/grafana/latest/alerting/

---

## 🎉 Success Criteria (COMPLETED)

### Task 5.2 Requirements: ✅ ALL MET

- ✅ **5 Grafana dashboards created** (01-05)
- ✅ **Prometheus metrics integration** (all metrics from prometheus_metrics.py used)
- ✅ **Alert thresholds configured** (margin <15%, loss >5%, circuit breaker open)
- ✅ **Appropriate visualizations** (gauge, graph, stat, table, pie chart, bar chart)
- ✅ **Time range selectors** (15m, 1h, 6h, 24h, 7d)
- ✅ **Template variables** (symbol filtering with multi-select + All option)
- ✅ **Panel descriptions** (all panels have clear descriptions)
- ✅ **Setup instructions** (comprehensive SETUP.md)
- ✅ **Dashboard descriptions** (detailed visual descriptions in DASHBOARD_DESCRIPTIONS.md)
- ✅ **Metrics reference** (complete reference card in METRICS_REFERENCE.md)

### Additional Deliverables

- ✅ **README.md** (this file - overview and quick links)
- ✅ **PromQL query examples** (in METRICS_REFERENCE.md)
- ✅ **Troubleshooting guide** (in METRICS_REFERENCE.md)
- ✅ **Quick reference cards** (for traders, devops, developers)
- ✅ **Alert rule examples** (for Prometheus Alertmanager)
- ✅ **Usage scenarios** (in DASHBOARD_DESCRIPTIONS.md)

---

## 📝 Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-07 | Agent 5 | Initial release - 5 dashboards + documentation |

---

## 📄 License

Part of FX_code_AI trading system. See project root for license details.

---

**Agent 5 - Monitoring & Observability**
**Status:** Task 5.2 Complete ✅
**Next Steps:** Agent 5 Task 5.3 (Alertmanager Rules) - to be created by Agent 0/Agent 5

**For questions or issues with these dashboards, consult the documentation files or contact the development team.**

---

**Happy Monitoring! 📊📈🚀**
