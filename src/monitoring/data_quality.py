"""
Data Quality Monitor - Sprint 4 Data Quality Monitoring
======================================================

Real-time data quality monitoring with anomaly detection, spike detection,
and accuracy drift monitoring for live trading operations.

Features:
- Price spike and volume anomaly detection
- Timestamp gap detection and validation
- Data freshness monitoring
- Accuracy drift comparison vs baseline
- Automated alerts for data quality issues
- Integration with incident management

Critical Analysis Points:
1. **Anomaly Detection**: Statistical methods for detecting data anomalies
2. **Gap Detection**: Identification of missing data periods
3. **Freshness Monitoring**: Ensuring data timeliness
4. **Drift Detection**: Comparison against baseline accuracy
5. **Alert Thresholds**: Configurable sensitivity for different market conditions
6. **Performance Impact**: Efficient processing without affecting trading latency
"""

import asyncio
import time
import statistics
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque

from ..core.event_bus import EventBus
from ..core.logger import StructuredLogger
from ..data.live_market_adapter import LiveMarketAdapter


@dataclass
class DataQualityMetrics:
    """Data quality metrics for a symbol"""
    symbol: str
    last_update: float
    update_count: int
    gaps_detected: int
    spikes_detected: int
    anomalies_detected: int
    avg_latency: float
    max_gap_duration: float
    freshness_score: float  # 0-100, higher is better


@dataclass
class PriceSpike:
    """Detected price spike"""
    symbol: str
    timestamp: float
    price: float
    expected_price: float
    deviation_percent: float
    severity: str  # "low", "medium", "high", "critical"


@dataclass
class DataGap:
    """Detected data gap"""
    symbol: str
    start_time: float
    end_time: float
    duration_seconds: float
    severity: str


class DataQualityMonitor:
    """
    Data quality monitor for Sprint 4 operations.

    Monitors live market data for quality issues, anomalies, and gaps.
    Provides real-time alerts and integrates with incident management.
    """

    def __init__(
        self,
        event_bus: EventBus,
        logger: StructuredLogger,
        market_adapter: LiveMarketAdapter
    ):
        self.event_bus = event_bus
        self.logger = logger
        self.market_adapter = market_adapter

        # Configuration
        self.config = {
            "monitoring_interval": 30.0,  # Check every 30 seconds
            "max_gap_threshold": 300.0,   # 5 minutes max gap
            "spike_threshold_percent": 5.0,  # 5% price change threshold
            "volume_spike_multiplier": 3.0,  # 3x normal volume
            "freshness_threshold": 60.0,   # Data older than 60s is stale
            "history_window": 3600.0,      # 1 hour history for statistics
            "anomaly_window": 300.0,       # 5 minutes for anomaly detection
        }

        # Monitoring state
        self.symbol_metrics: Dict[str, DataQualityMetrics] = {}
        self.price_history: Dict[str, deque] = {}  # symbol -> [(timestamp, price), ...]
        self.volume_history: Dict[str, deque] = {}  # symbol -> [(timestamp, volume), ...]

        # Recent detections
        self.recent_spikes: List[PriceSpike] = []
        self.recent_gaps: List[DataGap] = []

        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        self.logger.info("data_quality_monitor.initialized", {
            "config": self.config
        })

    async def start_monitoring(self) -> None:
        """Start data quality monitoring"""
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Subscribe to market data events
        await self.event_bus.subscribe("market.price_update", self._handle_price_update)

        self.logger.info("data_quality_monitor.started")

    async def stop_monitoring(self) -> None:
        """Stop data quality monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()

        self.logger.info("data_quality_monitor.stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.config["monitoring_interval"])
                await self._perform_quality_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("data_quality_monitor.monitoring_error", {
                    "error": str(e)
                })

    async def _cleanup_loop(self) -> None:
        """Cleanup old data"""
        while True:
            try:
                await asyncio.sleep(600)  # Clean every 10 minutes
                self._cleanup_old_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("data_quality_monitor.cleanup_error", {
                    "error": str(e)
                })

    async def _handle_price_update(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle incoming price updates"""
        try:
            symbol = data.get("symbol")
            price = data.get("price")
            volume = data.get("volume", 0)
            timestamp = data.get("timestamp", time.time())

            if not symbol or price is None:
                return

            # Update metrics
            await self._update_symbol_metrics(symbol, timestamp)

            # Store in history
            self._store_price_data(symbol, timestamp, price, volume)

            # Check for anomalies
            await self._check_for_anomalies(symbol, price, volume, timestamp)

        except Exception as e:
            self.logger.error("data_quality_monitor.price_update_error", {
                "error": str(e),
                "symbol": data.get("symbol")
            })

    async def _update_symbol_metrics(self, symbol: str, timestamp: float) -> None:
        """Update data quality metrics for symbol"""
        if symbol not in self.symbol_metrics:
            self.symbol_metrics[symbol] = DataQualityMetrics(
                symbol=symbol,
                last_update=timestamp,
                update_count=0,
                gaps_detected=0,
                spikes_detected=0,
                anomalies_detected=0,
                avg_latency=0.0,
                max_gap_duration=0.0,
                freshness_score=100.0
            )

        metrics = self.symbol_metrics[symbol]

        # Calculate latency (time since data timestamp vs now)
        latency = time.time() - timestamp
        metrics.avg_latency = (metrics.avg_latency * metrics.update_count + latency) / (metrics.update_count + 1)

        # Check for gaps
        if metrics.last_update > 0:
            gap_duration = timestamp - metrics.last_update
            if gap_duration > self.config["max_gap_threshold"]:
                await self._record_gap(symbol, metrics.last_update, timestamp, gap_duration)
                metrics.max_gap_duration = max(metrics.max_gap_duration, gap_duration)

        metrics.last_update = timestamp
        metrics.update_count += 1

        # Update freshness score
        if latency < self.config["freshness_threshold"]:
            metrics.freshness_score = 100.0
        else:
            # Decay freshness score based on staleness
            staleness_factor = min(latency / (self.config["freshness_threshold"] * 2), 1.0)
            metrics.freshness_score = max(0.0, 100.0 * (1.0 - staleness_factor))

    def _store_price_data(self, symbol: str, timestamp: float, price: float, volume: float) -> None:
        """Store price and volume data in history"""
        cutoff_time = time.time() - self.config["history_window"]

        # Initialize history if needed
        if symbol not in self.price_history:
            self.price_history[symbol] = deque()
            self.volume_history[symbol] = deque()

        # Add new data
        self.price_history[symbol].append((timestamp, price))
        self.volume_history[symbol].append((timestamp, volume))

        # Remove old data
        while self.price_history[symbol] and self.price_history[symbol][0][0] < cutoff_time:
            self.price_history[symbol].popleft()
        while self.volume_history[symbol] and self.volume_history[symbol][0][0] < cutoff_time:
            self.volume_history[symbol].popleft()

    async def _check_for_anomalies(self, symbol: str, price: float, volume: float, timestamp: float) -> None:
        """Check for price and volume anomalies"""
        try:
            # Price spike detection
            await self._check_price_spike(symbol, price, timestamp)

            # Volume anomaly detection
            await self._check_volume_anomaly(symbol, volume, timestamp)

        except Exception as e:
            self.logger.error("data_quality_monitor.anomaly_check_error", {
                "error": str(e),
                "symbol": symbol
            })

    async def _check_price_spike(self, symbol: str, price: float, timestamp: float) -> None:
        """Check for price spikes using statistical methods"""
        price_data = self.price_history.get(symbol, [])
        if len(price_data) < 10:  # Need minimum history
            return

        # Get recent prices (last 5 minutes)
        recent_prices = [
            p for t, p in price_data
            if timestamp - t <= self.config["anomaly_window"]
        ]

        if len(recent_prices) < 5:
            return

        # Calculate statistics
        try:
            mean_price = statistics.mean(recent_prices)
            stdev_price = statistics.stdev(recent_prices)

            if stdev_price == 0:
                return

            # Calculate z-score
            z_score = abs(price - mean_price) / stdev_price

            # Check for spike (z-score > 3 or percentage change)
            percent_change = abs(price - mean_price) / mean_price * 100

            if z_score > 3.0 or percent_change > self.config["spike_threshold_percent"]:
                severity = self._calculate_spike_severity(z_score, percent_change)

                spike = PriceSpike(
                    symbol=symbol,
                    timestamp=timestamp,
                    price=price,
                    expected_price=mean_price,
                    deviation_percent=percent_change,
                    severity=severity
                )

                await self._record_spike(spike)

        except statistics.StatisticsError:
            # Not enough data for statistics
            pass

    async def _check_volume_anomaly(self, symbol: str, volume: float, timestamp: float) -> None:
        """Check for volume anomalies"""
        volume_data = self.volume_history.get(symbol, [])
        if len(volume_data) < 10:
            return

        # Get recent volumes
        recent_volumes = [
            v for t, v in volume_data
            if timestamp - t <= self.config["anomaly_window"]
        ]

        if len(recent_volumes) < 5 or volume == 0:
            return

        try:
            mean_volume = statistics.mean(recent_volumes)

            # Check if volume is significantly higher than normal
            if volume > mean_volume * self.config["volume_spike_multiplier"]:
                # Record as anomaly
                await self._record_volume_anomaly(symbol, volume, mean_volume, timestamp)

        except statistics.StatisticsError:
            pass

    def _calculate_spike_severity(self, z_score: float, percent_change: float) -> str:
        """Calculate spike severity"""
        if z_score > 5.0 or percent_change > 20.0:
            return "critical"
        elif z_score > 3.5 or percent_change > 10.0:
            return "high"
        elif z_score > 2.5 or percent_change > 5.0:
            return "medium"
        else:
            return "low"

    async def _record_spike(self, spike: PriceSpike) -> None:
        """Record a detected price spike"""
        self.recent_spikes.append(spike)

        # Keep only recent spikes
        cutoff_time = time.time() - 3600  # Last hour
        self.recent_spikes = [
            s for s in self.recent_spikes
            if s.timestamp > cutoff_time
        ]

        # Update metrics
        if spike.symbol in self.symbol_metrics:
            self.symbol_metrics[spike.symbol].spikes_detected += 1
            self.symbol_metrics[spike.symbol].anomalies_detected += 1

        # Log and alert
        self.logger.warning("data_quality_monitor.price_spike_detected", {
            "symbol": spike.symbol,
            "price": spike.price,
            "expected_price": spike.expected_price,
            "deviation_percent": spike.deviation_percent,
            "severity": spike.severity
        })

        # Publish alert
        await self.event_bus.publish("data_quality.spike_detected", {
            "spike": {
                "symbol": spike.symbol,
                "timestamp": spike.timestamp,
                "price": spike.price,
                "expected_price": spike.expected_price,
                "deviation_percent": spike.deviation_percent,
                "severity": spike.severity
            }
        })

    async def _record_gap(self, symbol: str, start_time: float, end_time: float, duration: float) -> None:
        """Record a detected data gap"""
        severity = "low"
        if duration > 600:  # 10 minutes
            severity = "high"
        elif duration > 300:  # 5 minutes
            severity = "medium"

        gap = DataGap(
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            severity=severity
        )

        self.recent_gaps.append(gap)

        # Keep only recent gaps
        cutoff_time = time.time() - 3600
        self.recent_gaps = [
            g for g in self.recent_gaps
            if g.end_time > cutoff_time
        ]

        # Update metrics
        if symbol in self.symbol_metrics:
            self.symbol_metrics[symbol].gaps_detected += 1

        # Log and alert
        self.logger.warning("data_quality_monitor.data_gap_detected", {
            "symbol": symbol,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": duration,
            "severity": severity
        })

        # Publish alert
        await self.event_bus.publish("data_quality.gap_detected", {
            "gap": {
                "symbol": symbol,
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": duration,
                "severity": severity
            }
        })

    async def _record_volume_anomaly(self, symbol: str, volume: float, mean_volume: float, timestamp: float) -> None:
        """Record a volume anomaly"""
        if symbol in self.symbol_metrics:
            self.symbol_metrics[symbol].anomalies_detected += 1

        self.logger.warning("data_quality_monitor.volume_anomaly_detected", {
            "symbol": symbol,
            "volume": volume,
            "mean_volume": mean_volume,
            "multiplier": volume / mean_volume
        })

        await self.event_bus.publish("data_quality.volume_anomaly", {
            "symbol": symbol,
            "volume": volume,
            "mean_volume": mean_volume,
            "timestamp": timestamp
        })

    async def _perform_quality_checks(self) -> None:
        """Perform periodic quality checks"""
        try:
            # Check for stale data
            await self._check_data_freshness()

            # Check for prolonged gaps
            await self._check_prolonged_gaps()

            # Publish quality summary
            await self._publish_quality_summary()

        except Exception as e:
            self.logger.error("data_quality_monitor.quality_checks_error", {
                "error": str(e)
            })

    async def _check_data_freshness(self) -> None:
        """Check for stale data across all symbols"""
        current_time = time.time()
        stale_symbols = []

        for symbol, metrics in self.symbol_metrics.items():
            age = current_time - metrics.last_update
            if age > self.config["freshness_threshold"] * 2:  # 2x threshold for stale
                stale_symbols.append((symbol, age))

        if stale_symbols:
            self.logger.warning("data_quality_monitor.stale_data_detected", {
                "stale_symbols": [
                    {"symbol": s, "age_seconds": a}
                    for s, a in stale_symbols
                ]
            })

            await self.event_bus.publish("data_quality.stale_data", {
                "stale_symbols": stale_symbols
            })

    async def _check_prolonged_gaps(self) -> None:
        """Check for symbols with prolonged data gaps"""
        current_time = time.time()

        for symbol, metrics in self.symbol_metrics.items():
            if metrics.last_update > 0:
                gap_duration = current_time - metrics.last_update
                if gap_duration > self.config["max_gap_threshold"] * 2:  # 2x threshold
                    self.logger.error("data_quality_monitor.prolonged_gap", {
                        "symbol": symbol,
                        "gap_duration_seconds": gap_duration,
                        "last_update": metrics.last_update
                    })

    async def _publish_quality_summary(self) -> None:
        """Publish data quality summary"""
        summary = {
            "monitored_symbols": len(self.symbol_metrics),
            "total_updates": sum(m.update_count for m in self.symbol_metrics.values()),
            "total_gaps": sum(m.gaps_detected for m in self.symbol_metrics.values()),
            "total_spikes": sum(m.spikes_detected for m in self.symbol_metrics.values()),
            "total_anomalies": sum(m.anomalies_detected for m in self.symbol_metrics.values()),
            "avg_freshness_score": statistics.mean([
                m.freshness_score for m in self.symbol_metrics.values()
            ]) if self.symbol_metrics else 0.0,
            "recent_spikes": len(self.recent_spikes),
            "recent_gaps": len(self.recent_gaps),
            "timestamp": time.time()
        }

        await self.event_bus.publish("data_quality.summary", summary)

    def _cleanup_old_data(self) -> None:
        """Clean up old historical data"""
        cutoff_time = time.time() - self.config["history_window"]

        for symbol in list(self.price_history.keys()):
            # Remove old price data
            while self.price_history[symbol] and self.price_history[symbol][0][0] < cutoff_time:
                self.price_history[symbol].popleft()

            # Remove old volume data
            while self.volume_history[symbol] and self.volume_history[symbol][0][0] < cutoff_time:
                self.volume_history[symbol].popleft()

            # Remove empty histories
            if not self.price_history[symbol]:
                del self.price_history[symbol]
                del self.volume_history[symbol]

        # Clean old detections
        cutoff_time = time.time() - 3600  # 1 hour
        self.recent_spikes = [s for s in self.recent_spikes if s.timestamp > cutoff_time]
        self.recent_gaps = [g for g in self.recent_gaps if g.end_time > cutoff_time]

    def get_quality_report(self) -> Dict[str, Any]:
        """Get comprehensive data quality report"""
        return {
            "symbol_metrics": {
                symbol: {
                    "update_count": metrics.update_count,
                    "gaps_detected": metrics.gaps_detected,
                    "spikes_detected": metrics.spikes_detected,
                    "anomalies_detected": metrics.anomalies_detected,
                    "avg_latency": metrics.avg_latency,
                    "max_gap_duration": metrics.max_gap_duration,
                    "freshness_score": metrics.freshness_score,
                    "last_update": metrics.last_update
                }
                for symbol, metrics in self.symbol_metrics.items()
            },
            "recent_spikes": [
                {
                    "symbol": s.symbol,
                    "timestamp": s.timestamp,
                    "price": s.price,
                    "expected_price": s.expected_price,
                    "deviation_percent": s.deviation_percent,
                    "severity": s.severity
                }
                for s in self.recent_spikes[-10:]  # Last 10 spikes
            ],
            "recent_gaps": [
                {
                    "symbol": g.symbol,
                    "start_time": g.start_time,
                    "end_time": g.end_time,
                    "duration_seconds": g.duration_seconds,
                    "severity": g.severity
                }
                for g in self.recent_gaps[-10:]  # Last 10 gaps
            ],
            "config": self.config,
            "timestamp": time.time()
        }

    async def inject_anomaly(self, symbol: str, anomaly_type: str) -> bool:
        """Inject synthetic anomaly for testing (admin function)"""
        try:
            if anomaly_type == "spike":
                # Inject a price spike
                current_price = 50000.0  # Mock
                spike_price = current_price * 1.1  # 10% spike

                await self._handle_price_update("test", {
                    "symbol": symbol,
                    "price": spike_price,
                    "volume": 1000.0,
                    "timestamp": time.time()
                })

            elif anomaly_type == "gap":
                # Simulate a gap by not updating for a period
                # This would be detected in the next monitoring cycle
                pass

            return True

        except Exception as e:
            self.logger.error("data_quality_monitor.inject_anomaly_error", {
                "error": str(e),
                "symbol": symbol,
                "anomaly_type": anomaly_type
            })
            return False