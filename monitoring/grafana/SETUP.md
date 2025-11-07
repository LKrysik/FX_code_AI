# Grafana Dashboards Setup Guide

## Overview

This directory contains 5 production-ready Grafana dashboards for monitoring the live trading system. These dashboards provide real-time insights into trading performance, risk metrics, system health, strategy performance, and exchange integration.

## Prerequisites

1. **Prometheus** - Must be running and scraping metrics from the backend
   - Default endpoint: `http://localhost:8080/metrics/prometheus`
   - Scrape interval: 5s recommended

2. **Grafana** - Version 9.0+ recommended
   - Installation: https://grafana.com/docs/grafana/latest/setup-grafana/installation/

3. **Backend Server** - Must be running with Prometheus metrics enabled
   - Metrics are automatically exposed at `/metrics/prometheus`
   - PrometheusMetrics must be initialized in container.py

## Quick Start

### 1. Install Prometheus

Download and configure Prometheus:

```bash
# Download Prometheus (Windows)
# Visit: https://prometheus.io/download/

# Or use package manager (Linux/Mac)
# Linux: sudo apt-get install prometheus
# Mac: brew install prometheus
```

Create `prometheus.yml` configuration:

```yaml
global:
  scrape_interval: 5s
  evaluation_interval: 5s

scrape_configs:
  - job_name: 'fx-trading-backend'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics/prometheus'
```

Start Prometheus:

```bash
# Windows
prometheus.exe --config.file=prometheus.yml

# Linux/Mac
prometheus --config.file=prometheus.yml
```

Verify Prometheus is running: http://localhost:9090

### 2. Install Grafana

Download and install Grafana:

```bash
# Windows: Download installer from https://grafana.com/grafana/download
# Linux (Ubuntu/Debian)
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
sudo apt-get update
sudo apt-get install grafana

# Mac
brew install grafana
```

Start Grafana:

```bash
# Windows (if installed as service)
net start grafana

# Linux
sudo systemctl start grafana-server
sudo systemctl enable grafana-server

# Mac
brew services start grafana
```

Access Grafana: http://localhost:3000
- Default login: admin / admin
- You'll be prompted to change the password

### 3. Configure Prometheus Data Source in Grafana

1. Open Grafana: http://localhost:3000
2. Go to **Configuration** → **Data Sources**
3. Click **Add data source**
4. Select **Prometheus**
5. Configure:
   - Name: `Prometheus` (or any name you prefer)
   - URL: `http://localhost:9090`
   - Access: `Server (default)`
6. Click **Save & Test**
7. Verify you see "Data source is working"

### 4. Import Dashboards

#### Method 1: Via Grafana UI (Recommended)

1. In Grafana, go to **Dashboards** → **Import**
2. Click **Upload JSON file**
3. Select dashboard file (e.g., `01_trading_overview.json`)
4. Select your Prometheus data source
5. Click **Import**
6. Repeat for all 5 dashboards

#### Method 2: Via API (Automated)

```bash
# Set Grafana credentials
GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASS="your_password"

# Import all dashboards
for dashboard in monitoring/grafana/dashboards/*.json; do
  curl -X POST "$GRAFANA_URL/api/dashboards/db" \
    -u "$GRAFANA_USER:$GRAFANA_PASS" \
    -H "Content-Type: application/json" \
    -d @"$dashboard"
done
```

#### Method 3: Provisioning (Production)

1. Create provisioning directory:

```bash
mkdir -p /etc/grafana/provisioning/dashboards
mkdir -p /etc/grafana/provisioning/datasources
```

2. Create datasource config (`/etc/grafana/provisioning/datasources/prometheus.yml`):

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    editable: false
```

3. Create dashboard config (`/etc/grafana/provisioning/dashboards/fx-trading.yml`):

```yaml
apiVersion: 1

providers:
  - name: 'FX Trading Dashboards'
    orgId: 1
    folder: 'Live Trading'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /path/to/FX_code_AI/monitoring/grafana/dashboards
```

4. Restart Grafana:

```bash
# Linux
sudo systemctl restart grafana-server

# Windows
net stop grafana && net start grafana

# Mac
brew services restart grafana
```

## Dashboard Overview

### 1. Trading Overview Dashboard (`01_trading_overview.json`)

**Purpose:** Monitor order flow, execution performance, and P&L in real-time

**Key Panels:**
- Orders Per Minute (rate graph)
- Fill Rate (percentage gauge with thresholds)
- Orders Failed by Reason (bar chart)
- Order Submission Latency (p50, p95, p99)
- Live Unrealized P&L (time series with per-symbol breakdown)
- Orders by Symbol (table)
- Average Submission Latency (stat with thresholds)

**Alerts:**
- Fill rate < 80% (yellow)
- Fill rate < 50% (red)
- Average latency > 3s (red)
- Circuit breaker state changes (annotation)

**Best For:** Day-to-day trading monitoring, identifying execution issues

### 2. Risk Monitoring Dashboard (`02_risk_monitoring.json`)

**Purpose:** Track risk metrics and prevent catastrophic losses

**Key Panels:**
- Margin Ratio Gauge (CRITICAL if < 15%)
- Daily Loss Percentage (ALERT if > 5%)
- Total Open Positions (with limit warnings)
- Position Concentration by Symbol (pie chart)
- Risk Alerts Timeline (by severity)
- Margin Ratio Trend (with alert threshold line)
- Risk Alerts by Type (table)
- Total Exposure (absolute P&L)
- Critical/Warning Alert Counts (24h)

**Alerts:**
- Margin ratio < 15% (RED - liquidation risk)
- Daily loss > 5% (RED - daily limit)
- Open positions >= 3 (RED - max position limit)
- Critical risk alerts (annotations)

**Best For:** Risk management, liquidation prevention, compliance monitoring

### 3. System Health Dashboard (`03_system_health.json`)

**Purpose:** Monitor system performance, EventBus, and circuit breaker health

**Key Panels:**
- EventBus Throughput (by topic)
- EventBus Total Messages/sec (stat with capacity warnings)
- Circuit Breaker State (stat with color coding)
- API Latency (order submission percentiles)
- Circuit Breaker State Timeline
- EventBus Message Breakdown (table)
- Process Memory Usage (memory leak detection)
- Uptime, CPU Usage, File Descriptors

**Alerts:**
- Circuit breaker OPEN (RED - system blocking requests)
- EventBus > 900 msg/sec (yellow - approaching capacity)
- Memory > 1GB (red - potential leak)
- CPU > 80% (red - performance issue)

**Best For:** DevOps, system reliability, performance tuning, memory leak detection

### 4. Strategy Performance Dashboard (`04_strategy_performance.json`)

**Purpose:** Evaluate trading strategy effectiveness and performance metrics

**Key Panels:**
- Signals Generated per Strategy (bar gauge)
- Signal Generation Rate (time series)
- Signal Distribution by Strategy (pie chart)
- Win Rate (gauge - positions in profit)
- Average P&L per Position
- Strategy Performance Summary (table)
- Signal Confidence Distribution
- Cumulative P&L Over Time
- Sharpe Ratio (estimated from 24h data)
- Profit Factor (gross profit / gross loss)

**Metrics Explained:**
- **Win Rate:** % of open positions with unrealized_pnl > 0
- **Sharpe Ratio:** mean(P&L) / stddev(P&L) - measures risk-adjusted returns
  - > 1.0 = good
  - > 2.0 = excellent
- **Profit Factor:** sum(profits) / abs(sum(losses))
  - > 1.5 = good
  - > 2.0 = excellent

**Best For:** Strategy optimization, performance analysis, A/B testing strategies

### 5. Exchange Integration Dashboard (`05_exchange_integration.json`)

**Purpose:** Monitor MEXC API health, rate limits, and position synchronization

**Key Panels:**
- MEXC API Latency (order operations)
- Average MEXC API Latency (stat)
- MEXC API Requests/sec (rate limit monitoring)
- MEXC API Error Rate (percentage)
- Exchange Errors by Reason (table)
- Position Sync Status (seconds since last sync)
- Circuit Breaker Status (MEXC-specific)
- Order Book Depth (if available)
- Position Sync Frequency
- Rate Limit Margin (headroom before limit)

**Alerts:**
- API latency > 2s (red - slow exchange)
- Request rate > 8/s (yellow - approaching rate limit of 10/s)
- Error rate > 10% (red - exchange issues)
- Position sync > 60s (red - sync failure)
- Circuit breaker OPEN (red - MEXC blocked)

**Best For:** Exchange connectivity monitoring, rate limit management, troubleshooting MEXC issues

## Template Variables

All dashboards include template variables for filtering:

- **$symbol** - Filter by trading symbol (e.g., BTC_USDT, ETH_USDT)
  - Multi-select enabled
  - "All" option available
  - Dynamically populated from metrics

- **$strategy** - Filter by strategy name (Dashboard 4 only)
  - Multi-select enabled
  - "All" option available

## Time Range Presets

All dashboards include standard time ranges:
- Last 15 minutes
- Last 1 hour
- Last 6 hours
- Last 24 hours
- Last 7 days

Auto-refresh options:
- 5 seconds (Dashboards 1-3)
- 10 seconds (Dashboard 4)
- Manual refresh

## Alert Configuration

### Grafana Alerting Setup

1. Go to **Alerting** → **Notification channels**
2. Add notification channel (Email, Slack, PagerDuty, etc.)
3. Configure channel settings
4. Test notification

### Alertmanager Integration (Advanced)

See `/monitoring/prometheus/alerts.yml` for Prometheus Alertmanager rules (created by Agent 5).

Key alerts defined:
- MarginRatioLow (< 15%, 30s)
- DailyLossLimitExceeded (> 5%, 1m)
- CircuitBreakerOpen (2m)
- OrderSubmissionLatencyHigh (p95 > 5s, 5m)
- NoOrderFills (5m)
- HighErrorRate (> 10%, 5m)
- PositionSyncFailure (> 60s, 2m)

## Troubleshooting

### No Data in Dashboards

1. Verify Prometheus is scraping:
   - Open http://localhost:9090
   - Go to **Status** → **Targets**
   - Verify `fx-trading-backend` is **UP**

2. Verify metrics are exposed:
   - Open http://localhost:8080/metrics/prometheus
   - Should see metrics like `orders_submitted_total`, `positions_open_total`, etc.

3. Verify PrometheusMetrics is initialized:
   - Check `src/infrastructure/container.py`
   - Ensure `PrometheusMetrics` is created and `subscribe_to_events()` is called

4. Check Grafana data source:
   - Go to **Configuration** → **Data Sources** → **Prometheus**
   - Click **Save & Test**
   - Should see "Data source is working"

### Metrics Not Updating

1. Check EventBus is publishing events:
   - Verify trading session is active
   - Check logs for EventBus message counts

2. Verify PrometheusMetrics subscriptions:
   - Check that `subscribe_to_events()` was called
   - Look for log: "PrometheusMetrics subscribed to EventBus topics"

3. Check Prometheus scrape interval:
   - Default is 5s - adjust in `prometheus.yml` if needed

### Dashboard Import Errors

1. "Dashboard with same UID already exists"
   - Solution: Change `uid` field in JSON or delete existing dashboard

2. "Data source not found"
   - Solution: Ensure Prometheus data source is configured with correct name

3. "Invalid dashboard JSON"
   - Solution: Validate JSON syntax with https://jsonlint.com/

## Performance Optimization

### Prometheus Storage

For long-term data retention, configure Prometheus storage:

```yaml
# prometheus.yml
global:
  scrape_interval: 5s
  evaluation_interval: 5s

storage:
  tsdb:
    retention.time: 30d  # Keep data for 30 days
    retention.size: 50GB  # Max storage size
```

### Grafana Query Optimization

If dashboards are slow:

1. Reduce scrape interval for less critical metrics
2. Use `$__interval` variable in queries for auto-downsampling
3. Limit dashboard time range to last 24h for production
4. Use Grafana dashboard caching (Enterprise feature)

## Production Deployment Checklist

- [ ] Prometheus configured with persistent storage
- [ ] Grafana dashboards imported and tested
- [ ] Alert notification channels configured (Email, Slack, PagerDuty)
- [ ] Alertmanager rules configured (`alerts.yml`)
- [ ] Dashboard access permissions configured
- [ ] Auto-refresh set to appropriate intervals
- [ ] Time ranges configured for production use
- [ ] Template variables tested
- [ ] All panels display data correctly
- [ ] Critical alerts tested (manually trigger margin low, circuit breaker open)
- [ ] Backup of dashboard JSON files stored in Git
- [ ] Monitoring documentation added to runbook

## Additional Resources

- Prometheus: https://prometheus.io/docs/
- Grafana: https://grafana.com/docs/grafana/latest/
- PromQL: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Grafana Alerting: https://grafana.com/docs/grafana/latest/alerting/

## Support

For issues with dashboards:
1. Check this setup guide
2. Verify Prometheus metrics are being exposed
3. Check Grafana logs: `/var/log/grafana/grafana.log`
4. Check Prometheus logs
5. Contact: DevOps team or system administrator

---

**Last Updated:** 2025-11-07
**Created By:** Agent 5 (Monitoring & Observability)
**Version:** 1.0
