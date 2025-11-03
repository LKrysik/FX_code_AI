"""
Memory Monitor - Extracted from StreamingIndicatorEngine
=========================================================
Proactive memory management with leak detection for 24/7 stability.

Features:
- Memory usage tracking with psutil
- Leak detection using growth analysis
- Progressive cleanup (standard → force → emergency)
- Memory stability reporting
"""

import time
import psutil
from typing import Dict, Any, List
from collections import deque


class MemoryMonitor:
    """
    Monitors memory usage and triggers cleanup actions.

    Extracted from StreamingIndicatorEngine to follow Single Responsibility Principle.
    Prevents memory leaks in long-running systems (24/7 operation).
    """

    def __init__(self, logger, max_memory_mb: int = 512):
        """
        Initialize memory monitor.

        Args:
            logger: StructuredLogger instance
            max_memory_mb: Maximum memory limit in MB
        """
        self.logger = logger
        self.max_memory_mb = max_memory_mb

        # Memory tracking
        self._memory_samples: deque = deque(maxlen=100)
        self._last_memory_check = time.time()
        self._check_interval = 30  # Check every 30 seconds

        # Memory thresholds (percentage of max)
        self._cleanup_threshold_pct = 70.0  # Standard cleanup at 70%
        self._force_cleanup_threshold_pct = 85.0  # Force cleanup at 85%
        self._emergency_threshold_pct = 95.0  # Emergency cleanup at 95%

        # Leak detection
        self._leak_threshold_mb = 50  # 50MB growth = potential leak
        self._growth_window_minutes = 10
        self._last_growth_check = time.time()
        self._alerts_triggered = 0

        # Performance metrics
        self._metrics = {
            "memory_usage_mb": 0.0,
            "memory_growth_mb": 0.0,
            "cleanup_count": 0,
            "force_cleanup_count": 0,
            "emergency_cleanup_count": 0
        }

    def check_limits(self) -> bool:
        """
        Check if memory is within limits.

        Returns:
            True if within limits, False if cleanup needed
        """
        current_time = time.time()

        # Only check periodically
        if current_time - self._last_memory_check < self._check_interval:
            return True

        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self._metrics["memory_usage_mb"] = memory_mb
            self._last_memory_check = current_time

            # Record sample for leak detection
            self._memory_samples.append({
                "timestamp": current_time,
                "memory_mb": memory_mb
            })

            # Detect memory leaks
            self.detect_leaks()

            # Calculate memory percentage
            memory_pct = (memory_mb / self.max_memory_mb) * 100

            # Trigger appropriate cleanup level
            if memory_pct >= self._emergency_threshold_pct:
                self.logger.error("memory_monitor.emergency_threshold", {
                    "memory_mb": memory_mb,
                    "memory_pct": memory_pct,
                    "limit_mb": self.max_memory_mb
                })
                self._metrics["emergency_cleanup_count"] += 1
                return False  # Trigger emergency cleanup

            elif memory_pct >= self._force_cleanup_threshold_pct:
                self.logger.warning("memory_monitor.force_threshold", {
                    "memory_mb": memory_mb,
                    "memory_pct": memory_pct,
                    "limit_mb": self.max_memory_mb
                })
                self._metrics["force_cleanup_count"] += 1
                return False  # Trigger force cleanup

            elif memory_pct >= self._cleanup_threshold_pct:
                self.logger.info("memory_monitor.standard_threshold", {
                    "memory_mb": memory_mb,
                    "memory_pct": memory_pct,
                    "limit_mb": self.max_memory_mb
                })
                self._metrics["cleanup_count"] += 1
                return False  # Trigger standard cleanup

            return True  # Within limits

        except Exception as e:
            self.logger.error("memory_monitor.check_failed", {"error": str(e)})
            return True  # Allow operation if check fails

    def detect_leaks(self) -> None:
        """
        Detect potential memory leaks using growth analysis.

        Analyzes memory growth over time window to identify leaks.
        """
        current_time = time.time()

        # Only check periodically
        if current_time - self._last_growth_check < 60:  # Check every minute
            return

        if len(self._memory_samples) < 10:
            return  # Need enough samples

        # Get samples in time window
        window_start = current_time - (self._growth_window_minutes * 60)
        window_samples = [
            s for s in self._memory_samples
            if s["timestamp"] >= window_start
        ]

        if len(window_samples) < 5:
            return

        # Calculate memory growth
        first_sample = window_samples[0]["memory_mb"]
        last_sample = window_samples[-1]["memory_mb"]
        growth_mb = last_sample - first_sample

        self._metrics["memory_growth_mb"] = growth_mb
        self._last_growth_check = current_time

        # Check for leak
        if growth_mb > self._leak_threshold_mb:
            self._alerts_triggered += 1
            self.logger.warning("memory_monitor.leak_detected", {
                "growth_mb": growth_mb,
                "window_minutes": self._growth_window_minutes,
                "current_memory_mb": last_sample,
                "alert_count": self._alerts_triggered
            })

    def get_current_memory_mb(self) -> float:
        """
        Get current memory usage in MB.

        Returns:
            Memory usage in megabytes
        """
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    def get_stability_report(self) -> Dict[str, Any]:
        """
        Get memory stability report.

        Returns:
            Dictionary with memory metrics and leak detection status
        """
        if len(self._memory_samples) < 2:
            return {
                "status": "UNKNOWN",
                "current_memory_mb": 0.0,
                "memory_growth_mb": 0.0,
                "leak_detected": False
            }

        # Calculate statistics
        recent_samples = list(self._memory_samples)[-20:]  # Last 20 samples
        memory_values = [s["memory_mb"] for s in recent_samples]

        current_memory = memory_values[-1] if memory_values else 0.0
        avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0.0
        min_memory = min(memory_values) if memory_values else 0.0
        max_memory = max(memory_values) if memory_values else 0.0

        # Determine status
        memory_pct = (current_memory / self.max_memory_mb) * 100
        if memory_pct >= self._emergency_threshold_pct:
            status = "CRITICAL"
        elif memory_pct >= self._force_cleanup_threshold_pct:
            status = "WARNING"
        elif memory_pct >= self._cleanup_threshold_pct:
            status = "ELEVATED"
        else:
            status = "HEALTHY"

        # Leak detection status
        leak_detected = self._metrics["memory_growth_mb"] > self._leak_threshold_mb

        return {
            "status": status,
            "current_memory_mb": current_memory,
            "avg_memory_mb": avg_memory,
            "min_memory_mb": min_memory,
            "max_memory_mb": max_memory,
            "memory_limit_mb": self.max_memory_mb,
            "utilization_pct": memory_pct,
            "memory_growth_mb": self._metrics["memory_growth_mb"],
            "leak_detected": leak_detected,
            "cleanup_stats": {
                "standard_cleanups": self._metrics["cleanup_count"],
                "force_cleanups": self._metrics["force_cleanup_count"],
                "emergency_cleanups": self._metrics["emergency_cleanup_count"]
            },
            "samples_count": len(self._memory_samples),
            "alerts_triggered": self._alerts_triggered
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get memory metrics.

        Returns:
            Dictionary with memory performance metrics
        """
        return self._metrics.copy()

    def reset_alerts(self) -> None:
        """Reset memory leak alert counter."""
        self._alerts_triggered = 0
        self.logger.info("memory_monitor.alerts_reset")
