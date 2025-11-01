# Prosty System Monitoringu Pamięci

## Problem
Obecny system ma już mechanizmy ochrony pamięci, ale **nie ma dashboardu** do monitorowania.

## Co JUŻ DZIAŁA w kodzie

```python
# src/domain/services/streaming_indicator_engine.py (linia 361-375)

# ✅ JUŻ JEST: Memory leak detection
self._memory_samples = deque(maxlen=100)
self._memory_leak_threshold_mb = 50
self._memory_growth_window_minutes = 10

# ✅ JUŻ JEST: Aggressive cleanup thresholds
self._memory_cleanup_threshold_pct = 75  # Cleanup at 75%
self._memory_force_cleanup_threshold_pct = 85  # Force at 85%
self._memory_emergency_threshold_pct = 95  # Emergency at 95%

# ✅ JUŻ JEST: TTL cleanup (600 sekund)
self._data_ttl_seconds = 600
self._cleanup_interval_seconds = 300  # Co 5 minut
```

## Brakuje TYLKO: Endpoint API + Frontend Dashboard

### 1. API Endpoint (30 linii kodu)

```python
# src/api/monitoring_routes.py

@router.get("/api/monitoring/memory")
async def get_memory_stats():
    """
    Zwróć statystyki pamięci dla wszystkich komponentów.
    """
    stats = {
        'system': {
            'total_mb': psutil.virtual_memory().total / 1024 / 1024,
            'available_mb': psutil.virtual_memory().available / 1024 / 1024,
            'used_mb': psutil.virtual_memory().used / 1024 / 1024,
            'percent': psutil.virtual_memory().percent,
            'process_mb': psutil.Process().memory_info().rss / 1024 / 1024
        },
        'components': {}
    }

    # StreamingIndicatorEngine stats
    if streaming_engine:
        stats['components']['streaming_engine'] = {
            'price_buffers': len(streaming_engine._price_data),
            'orderbook_buffers': len(streaming_engine._orderbook_data),
            'deal_buffers': len(streaming_engine._deal_data),
            'cache_size': len(streaming_engine._indicator_cache),
            'cache_hits': streaming_engine._cache_hits,
            'cache_misses': streaming_engine._cache_misses,
            'cache_hit_ratio': streaming_engine._cache_hits /
                               (streaming_engine._cache_hits + streaming_engine._cache_misses + 1),
            'memory_samples': list(streaming_engine._memory_samples)
        }

    # EventBus stats
    if event_bus:
        stats['components']['event_bus'] = {
            'queue_sizes': {
                priority.name: event_bus._priority_queues[priority].qsize()
                for priority in event_bus._priority_queues
            }
        }

    # MEXC Adapter stats
    if mexc_adapter:
        stats['components']['mexc_adapter'] = {
            'cache_size': len(mexc_adapter._market_data_cache),
            'connections': len(mexc_adapter._websockets),
            'subscriptions': sum(len(subs) for subs in mexc_adapter._subscription_map.values())
        }

    return stats


@router.get("/api/monitoring/memory/trend")
async def get_memory_trend(hours: int = 1):
    """
    Zwróć trend użycia pamięci w ostatnich N godzinach.

    Wymaga: logowanie metryk do QuestDB (już masz!)
    """
    async with questdb_provider.pg_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                timestamp,
                component,
                memory_mb,
                buffer_count,
                cache_size
            FROM system_metrics
            WHERE timestamp > now() - INTERVAL '$1 hours'
            ORDER BY timestamp DESC
        """, hours)

    return {
        'trend': [dict(r) for r in rows],
        'hours': hours
    }
```

### 2. Logowanie Metryk Do QuestDB (50 linii kodu)

```python
# src/application/services/metrics_logger.py

class MetricsLogger:
    """
    Loguje metryki systemowe do QuestDB co minutę.
    """

    def __init__(self, questdb_provider, streaming_engine, event_bus, mexc_adapter):
        self.db = questdb_provider
        self.streaming_engine = streaming_engine
        self.event_bus = event_bus
        self.mexc_adapter = mexc_adapter
        self._task = None

    async def start(self):
        """Start background metrics logging"""
        self._task = asyncio.create_task(self._log_loop())

    async def _log_loop(self):
        """Log metrics every 60 seconds"""
        while True:
            try:
                await self._log_metrics()
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Metrics logging error: {e}")
                await asyncio.sleep(60)

    async def _log_metrics(self):
        """Collect and log current metrics"""
        timestamp = time.time_ns()

        # System memory
        await self.db.insert_metric(
            component='system',
            metric_name='memory_mb',
            value=psutil.Process().memory_info().rss / 1024 / 1024,
            timestamp=timestamp
        )

        # StreamingIndicatorEngine
        if self.streaming_engine:
            await self.db.insert_metric(
                component='streaming_engine',
                metric_name='buffer_count',
                value=len(self.streaming_engine._price_data),
                timestamp=timestamp
            )
            await self.db.insert_metric(
                component='streaming_engine',
                metric_name='cache_size',
                value=len(self.streaming_engine._indicator_cache),
                timestamp=timestamp
            )

        # EventBus
        if self.event_bus:
            for priority, queue in self.event_bus._priority_queues.items():
                await self.db.insert_metric(
                    component='event_bus',
                    metric_name=f'queue_{priority.name}',
                    value=queue.qsize(),
                    timestamp=timestamp
                )
```

### 3. Tabela w QuestDB (Już masz infrastrukturę!)

```sql
-- database/questdb/migrations/011_system_metrics.sql

CREATE TABLE system_metrics (
    timestamp TIMESTAMP,
    component SYMBOL capacity 32 CACHE,
    metric_name SYMBOL capacity 64 CACHE,
    value DOUBLE,
    metadata STRING
) timestamp(timestamp) PARTITION BY DAY WAL;
```

### 4. Frontend Dashboard (React Component)

```typescript
// frontend/components/MemoryDashboard.tsx

import { Line } from 'react-chartjs-2';

export function MemoryDashboard() {
  const [stats, setStats] = useState(null);
  const [trend, setTrend] = useState(null);

  useEffect(() => {
    // Fetch current stats every 5 seconds
    const interval = setInterval(async () => {
      const response = await fetch('/api/monitoring/memory');
      setStats(await response.json());
    }, 5000);

    // Fetch trend once
    fetch('/api/monitoring/memory/trend?hours=1')
      .then(r => r.json())
      .then(setTrend);

    return () => clearInterval(interval);
  }, []);

  if (!stats) return <div>Loading...</div>;

  return (
    <div className="memory-dashboard">
      <h2>Memory Usage</h2>

      {/* Current Stats */}
      <div className="stats-grid">
        <StatCard
          title="System Memory"
          value={stats.system.used_mb.toFixed(0)}
          unit="MB"
          percent={stats.system.percent}
        />
        <StatCard
          title="Process Memory"
          value={stats.system.process_mb.toFixed(0)}
          unit="MB"
        />
        <StatCard
          title="Cache Hit Ratio"
          value={(stats.components.streaming_engine.cache_hit_ratio * 100).toFixed(1)}
          unit="%"
        />
        <StatCard
          title="Active Buffers"
          value={stats.components.streaming_engine.price_buffers}
          unit="symbols"
        />
      </div>

      {/* Memory Trend Chart */}
      <div className="trend-chart">
        <Line
          data={{
            labels: trend?.trend.map(t => new Date(t.timestamp)),
            datasets: [{
              label: 'Memory Usage (MB)',
              data: trend?.trend.map(t => t.memory_mb),
              borderColor: 'rgb(75, 192, 192)',
            }]
          }}
          options={{
            responsive: true,
            scales: {
              y: {
                beginAtZero: true,
                title: { display: true, text: 'Memory (MB)' }
              }
            }
          }}
        />
      </div>

      {/* Component Details */}
      <div className="component-details">
        <h3>Component Breakdown</h3>
        <table>
          <thead>
            <tr>
              <th>Component</th>
              <th>Metric</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Streaming Engine</td>
              <td>Price Buffers</td>
              <td>{stats.components.streaming_engine.price_buffers}</td>
            </tr>
            <tr>
              <td>Streaming Engine</td>
              <td>Cache Size</td>
              <td>{stats.components.streaming_engine.cache_size}</td>
            </tr>
            <tr>
              <td>Event Bus</td>
              <td>HIGH Queue</td>
              <td>{stats.components.event_bus.queue_sizes.HIGH}</td>
            </tr>
            <tr>
              <td>MEXC Adapter</td>
              <td>Cache Size</td>
              <td>{stats.components.mexc_adapter.cache_size}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

## Korzyści

1. ✅ **Widoczność** - widzisz użycie pamięci w czasie rzeczywistym
2. ✅ **Proste** - tylko 200 linii kodu (API + frontend)
3. ✅ **Używa istniejącej infrastruktury** - QuestDB, EventBus
4. ✅ **Nie zmienia logiki** - tylko dodaje monitoring
5. ✅ **Historyczne trendy** - QuestDB przechowuje metryki
6. ✅ **Alerting gotowy** - możesz dodać alerty jeśli memory > threshold

## Implementacja (2 dni)

### Dzień 1: Backend
- Endpoint `/api/monitoring/memory` (30 linii)
- Endpoint `/api/monitoring/memory/trend` (20 linii)
- MetricsLogger task (50 linii)
- QuestDB migration (tabela system_metrics)

### Dzień 2: Frontend
- React component MemoryDashboard (150 linii)
- Dodaj do menu nawigacji
- Testowanie

## Alert System (Bonus - 1 godzina)

```python
# src/application/services/memory_alerting.py

class MemoryAlertService:
    """
    Wysyła alerty gdy pamięć przekracza threshold.
    """

    async def check_memory_threshold(self):
        process_memory = psutil.Process().memory_info().rss / 1024 / 1024

        if process_memory > 500:  # 500MB threshold
            await self.send_alert(
                level='WARNING',
                message=f'High memory usage: {process_memory:.0f} MB',
                component='system'
            )

        if process_memory > 1000:  # 1GB threshold
            await self.send_alert(
                level='CRITICAL',
                message=f'Critical memory usage: {process_memory:.0f} MB',
                component='system'
            )
            # Optional: Trigger emergency cleanup
            await self.streaming_engine.force_cleanup()

    async def send_alert(self, level, message, component):
        # Log to QuestDB
        await self.db.insert_alert(level, message, component, timestamp=time.time_ns())

        # Publish to EventBus for real-time notifications
        await self.event_bus.publish('system.alert', {
            'level': level,
            'message': message,
            'component': component,
            'timestamp': time.time()
        })

        # Optional: Send email/Slack notification
        # await self.notification_service.send(level, message)
```
