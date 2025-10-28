# Monitoring Dashboard Access Guide

## Overview
The Crypto Trading Bot includes comprehensive monitoring and health checking capabilities. The monitoring dashboard provides real-time visibility into system health, performance metrics, and alerting.

## Dashboard Access URLs

### Health Status Endpoints

#### Basic Health Check
- **URL**: `GET /health`
- **Purpose**: Ultra-fast liveness probe (<10ms response)
- **Response**: Basic healthy/unhealthy status with uptime

#### Detailed Health Status
- **URL**: `GET /health/detailed`
- **Purpose**: Comprehensive health check with system analysis
- **Response**: Detailed status including:
  - Overall system health
  - Service degradation information
  - Component status (REST API, telemetry, circuit breakers, health monitoring)
  - Health check results
  - Active alerts
  - Circuit breaker status

#### Health Status Summary
- **URL**: `GET /health/status`
- **Purpose**: Detailed health monitoring status
- **Response**: Complete health monitor state

### Metrics Endpoints

#### System Metrics
- **URL**: `GET /metrics`
- **Purpose**: Comprehensive system metrics via telemetry
- **Response**: All collected performance metrics

#### Health Metrics
- **URL**: `GET /metrics/health`
- **Purpose**: Health-specific metrics
- **Response**: Health check performance data

### Alert Management

#### Active Alerts
- **URL**: `GET /alerts`
- **Purpose**: View all currently active alerts
- **Response**: List of active alerts with severity and details

#### Resolve Alert
- **URL**: `POST /alerts/{alert_id}/resolve`
- **Purpose**: Manually resolve an active alert
- **Body**: None required

### Service Management

#### Registered Services
- **URL**: `GET /health/services`
- **Purpose**: List all registered services for health monitoring
- **Response**: Service registry with status and metadata

#### Service Status
- **URL**: `GET /health/services/{service_name}`
- **Purpose**: Get detailed status of a specific service
- **Response**: Service health check results

#### Enable/Disable Service
- **URL**: `POST /health/services/{service_name}/enable`
- **URL**: `POST /health/services/{service_name}/disable`
- **Purpose**: Control service monitoring
- **Response**: Service enable/disable confirmation

### Circuit Breaker Status
- **URL**: `GET /circuit-breakers`
- **Purpose**: View status of all circuit breakers
- **Response**: Circuit breaker states and failure counts

## Health Check Details

### Individual Health Check Info
- **URL**: `GET /health/checks/{check_name}`
- **Purpose**: Get detailed information for a specific health check
- **Response**: Check configuration, status, failure history

### Clear Health Cache
- **URL**: `POST /health/clear-cache`
- **Purpose**: Clear the health endpoint response cache
- **Response**: Cache clearing confirmation

## Monitoring Architecture

### Health Monitoring System
- **Frequency**: Health checks run every 45 seconds
- **Components Monitored**:
  - System resources (CPU, memory, disk)
  - Circuit breaker status
  - Telemetry system health
  - External service connectivity (MEXC API)
  - Database/storage availability

### Metrics Collection
- **Exporter**: Prometheus-compatible metrics export
- **Frequency**: Metrics exported every 15 seconds
- **Retention**: 1 hour of historical data
- **Metrics Include**:
  - System performance (CPU, memory, uptime)
  - Market adapter metrics (connections, latency, reconnections)
  - Session manager metrics (active sessions, operations, failures)
  - Circuit breaker status
  - Cache performance
  - Alert counts

### Alert System
- **Alert Types**:
  - High CPU usage (>85%)
  - Circuit breaker failures
  - Telemetry system issues
- **Cooldown**: 5 minutes between repeated alerts
- **Channels**: Log-based alerts (extensible to email, Slack, etc.)

## Accessing the Dashboard

### Web Interface
1. Start the application server
2. Access health endpoints via HTTP GET requests
3. Use browser or API client (Postman, curl) to view responses

### Example curl Commands

```bash
# Basic health check
curl http://localhost:8080/health

# Detailed health status
curl http://localhost:8080/health/detailed

# View active alerts
curl http://localhost:8080/alerts

# Get system metrics
curl http://localhost:8080/metrics
```

### Grafana Integration
The metrics are exported in Prometheus format and can be integrated with Grafana for dashboard visualization:

1. Configure Prometheus to scrape metrics from `/metrics` endpoint
2. Import Grafana dashboards for trading system monitoring
3. Set up alerting rules based on collected metrics

## Alert Thresholds

### Configured Thresholds
- **Latency P95**: >500ms triggers alert
- **Error Rate**: >5% triggers alert
- **Reconnect Count**: >10/hour triggers alert
- **Circuit Breaker Open**: Any open breakers trigger alert

### CPU/Memory Thresholds
- **Critical CPU**: >95%
- **High CPU**: >85%
- **Critical Memory**: >95%
- **High Memory**: >85%

## Troubleshooting

### Common Issues

#### Health Checks Failing
- Check system resources (CPU/memory)
- Verify external service connectivity
- Review application logs for errors

#### Metrics Not Updating
- Ensure telemetry is enabled (`ENABLE_TELEMETRY=1`)
- Check metrics exporter startup logs
- Verify EventBus connectivity

#### Alerts Not Clearing
- Manually resolve alerts via API
- Check underlying issue resolution
- Review alert cooldown settings

### Log Locations
- Health monitor logs: Application log files
- Metrics export logs: Application log files
- Alert notifications: Application log files

## Configuration

### Environment Variables
- `ENABLE_TELEMETRY`: Enable/disable telemetry collection (default: 1)
- `APP_ENV`: Environment setting affects cookie security

### Health Check Configuration
Health checks are configured in `src/core/health_monitor.py`:
- Intervals, timeouts, and thresholds
- Alert conditions and cooldowns
- Service registration and monitoring

This monitoring system provides comprehensive observability for the trading platform, enabling proactive issue detection and resolution.