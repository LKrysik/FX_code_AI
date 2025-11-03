"""
Cache Manager - Extracted from StreamingIndicatorEngine
========================================================
Manages indicator value caching with adaptive TTL and LRU eviction.

Features:
- Hierarchical caching with performance tracking
- Adaptive TTL based on indicator volatility
- LRU eviction when cache reaches capacity
- >90% hit ratio optimization
"""

import time
from typing import Dict, Any, Optional
from collections import deque


class CacheManager:
    """
    Manages caching for indicator values.

    Extracted from StreamingIndicatorEngine to follow Single Responsibility Principle.
    """

    def __init__(self, logger, max_size: int = 10000):
        """
        Initialize cache manager.

        Args:
            logger: StructuredLogger instance
            max_size: Maximum number of cache entries
        """
        self.logger = logger
        self.max_size = max_size

        # Cache storage
        self._cache: Dict[str, Dict[str, Any]] = {}

        # Cache configuration
        self._base_ttl_seconds = 60  # 1 minute base TTL
        self._bucket_size = 60  # 1 minute time buckets
        self._high_watermark = int(max_size * 0.8)  # 80% capacity

        # Performance tracking
        self._hits = 0
        self._misses = 0
        self._access_history: deque = deque(maxlen=1000)
        self._performance_window = 300  # 5 minutes

        # Volatility tracking for adaptive TTL
        self._indicator_volatility: Dict[str, float] = {}
        self._volatility_update_interval = 600  # 10 minutes
        self._last_volatility_update = time.time()

        # LRU tracking
        self._access_order: Dict[str, float] = {}

    def resolve_bucket(self, indicator_type: str, params: Dict[str, Any]) -> int:
        """
        Calculate cache bucket for time-based cache keys.

        Args:
            indicator_type: Type of indicator
            params: Indicator parameters

        Returns:
            Cache bucket (time rounded to bucket_size)
        """
        # For time-driven indicators, use time bucketing
        if indicator_type in {"TWPA", "VELOCITY", "VOLUME_SURGE"}:
            current_time = time.time()
            bucket = int(current_time / self._bucket_size) * self._bucket_size
            return bucket
        return 0  # No bucketing for event-driven indicators

    def get_cache_key(self, indicator_type: str, symbol: str, timeframe: str, params: Dict[str, Any]) -> str:
        """
        Generate cache key for indicator value.

        Args:
            indicator_type: Type of indicator
            symbol: Trading symbol
            timeframe: Timeframe string
            params: Indicator parameters

        Returns:
            Unique cache key string
        """
        import json, hashlib

        # Get cache bucket for time-based indicators
        bucket = self.resolve_bucket(indicator_type, params)

        # Create stable parameter fingerprint
        params_only = {k: v for k, v in params.items() if k not in ("scope", "cache_bucket")}
        try:
            param_str = json.dumps(params_only, sort_keys=True, separators=(",", ":"))
            param_hash = hashlib.sha1(param_str.encode("utf-8")).hexdigest()[:8]
        except Exception:
            param_hash = "default"

        # Build cache key
        if bucket > 0:
            cache_key = f"{symbol}:{indicator_type}:{timeframe}:{param_hash}:bucket_{bucket}"
        else:
            cache_key = f"{symbol}:{indicator_type}:{timeframe}:{param_hash}"

        return cache_key

    def get(self, cache_key: str) -> Optional[float]:
        """
        Get cached value if valid.

        Args:
            cache_key: Cache key to look up

        Returns:
            Cached value if valid and not expired, None otherwise
        """
        if cache_key not in self._cache:
            self.record_access(cache_key, hit=False)
            return None

        entry = self._cache[cache_key]
        current_time = time.time()

        # Check TTL expiration
        ttl = entry.get("ttl", self._base_ttl_seconds)
        timestamp = entry.get("timestamp", 0)

        if current_time - timestamp > ttl:
            # Expired - remove from cache
            del self._cache[cache_key]
            if cache_key in self._access_order:
                del self._access_order[cache_key]
            self.record_access(cache_key, hit=False)
            return None

        # Valid cache hit
        self.record_access(cache_key, hit=True)
        entry["hits"] = entry.get("hits", 0) + 1
        entry["access_time"] = current_time
        self._access_order[cache_key] = current_time

        return entry.get("value")

    def set(self, cache_key: str, value: float, ttl: Optional[int] = None) -> None:
        """
        Set cached value with TTL.

        Args:
            cache_key: Cache key
            value: Value to cache
            ttl: Optional TTL in seconds (uses adaptive TTL if None)
        """
        current_time = time.time()

        # Calculate TTL (adaptive or provided)
        if ttl is None:
            ttl = self.calculate_ttl(cache_key)

        # Create cache entry
        self._cache[cache_key] = {
            "value": value,
            "timestamp": current_time,
            "ttl": ttl,
            "hits": 0,
            "access_time": current_time
        }
        self._access_order[cache_key] = current_time

        # Enforce cache limits if needed
        if len(self._cache) >= self._high_watermark:
            self.enforce_limits()

    def calculate_ttl(self, cache_key: str) -> int:
        """
        Calculate adaptive TTL based on access patterns and volatility.

        Args:
            cache_key: Cache key

        Returns:
            TTL in seconds
        """
        base_ttl = self._base_ttl_seconds

        # Extract indicator type from cache key
        parts = cache_key.split(":")
        if len(parts) < 2:
            return base_ttl

        indicator_type = parts[1]

        # Get volatility factor
        volatility = self._indicator_volatility.get(indicator_type, 1.0)

        # Higher volatility = shorter TTL
        if volatility > 2.0:
            return int(base_ttl * 0.5)  # 30 seconds
        elif volatility > 1.5:
            return int(base_ttl * 0.75)  # 45 seconds
        elif volatility < 0.5:
            return int(base_ttl * 2.0)  # 120 seconds
        else:
            return base_ttl  # 60 seconds

    def calculate_frequency_factor(self, cache_key: str) -> float:
        """
        Calculate access frequency factor for a cache key.

        Args:
            cache_key: Cache key

        Returns:
            Frequency factor (0.0 to 1.0+)
        """
        if cache_key not in self._cache:
            return 0.0

        entry = self._cache[cache_key]
        hits = entry.get("hits", 0)

        # Calculate frequency based on hits in time window
        access_time = entry.get("access_time", 0)
        age = time.time() - entry.get("timestamp", time.time())

        if age <= 0:
            return 0.0

        frequency = hits / max(1, age / 60)  # hits per minute
        return min(frequency / 10.0, 1.0)  # Normalize to 0-1

    def cleanup(self) -> int:
        """
        Cleanup expired cache entries.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = []

        for key, entry in self._cache.items():
            ttl = entry.get("ttl", self._base_ttl_seconds)
            timestamp = entry.get("timestamp", 0)

            if current_time - timestamp > ttl:
                expired_keys.append(key)

        # Remove expired entries
        for key in expired_keys:
            if key in self._cache:
                del self._cache[key]
            if key in self._access_order:
                del self._access_order[key]

        if expired_keys:
            self.logger.debug("cache_manager.cleanup", {
                "expired_count": len(expired_keys)
            })

        return len(expired_keys)

    def enforce_limits(self) -> None:
        """Enforce cache size limits using LRU eviction."""
        if len(self._cache) < self._high_watermark:
            return

        # Calculate how many to evict (20% of cache)
        num_to_evict = max(1, len(self._cache) // 5)
        self.evict(num_to_evict)

    def evict(self, num_entries: int) -> None:
        """
        Evict least recently used cache entries.

        Args:
            num_entries: Number of entries to evict
        """
        if not self._access_order:
            return

        # Sort by access time (oldest first)
        sorted_keys = sorted(self._access_order.items(), key=lambda x: x[1])

        # Evict oldest entries
        evicted = 0
        for key, _ in sorted_keys:
            if evicted >= num_entries:
                break

            if key in self._cache:
                del self._cache[key]
            if key in self._access_order:
                del self._access_order[key]
            evicted += 1

        self.logger.debug("cache_manager.eviction", {
            "evicted_count": evicted,
            "remaining_entries": len(self._cache)
        })

    def record_access(self, cache_key: str, hit: bool) -> None:
        """
        Record cache access for performance tracking.

        Args:
            cache_key: Cache key accessed
            hit: Whether it was a cache hit
        """
        if hit:
            self._hits += 1
        else:
            self._misses += 1

        self._access_history.append({
            "timestamp": time.time(),
            "key": cache_key,
            "hit": hit
        })

    def update_volatility(self) -> None:
        """
        Update indicator volatility metrics for adaptive TTL.

        Volatility is calculated as cache miss rate with exponential smoothing.
        Higher miss rate = higher volatility = shorter TTL.
        """
        current_time = time.time()

        # Only update periodically
        if current_time - self._last_volatility_update < self._volatility_update_interval:
            return

        # Calculate volatility from access history based on hit/miss rate
        indicator_stats: Dict[str, Dict[str, int]] = {}

        for access in self._access_history:
            key = access.get("key", "")
            parts = key.split(":")
            if len(parts) >= 2:
                indicator_type = parts[1]  # parts[1] is indicator_type (e.g., "TWPA")

                if indicator_type not in indicator_stats:
                    indicator_stats[indicator_type] = {'hits': 0, 'misses': 0}

                if access.get('hit', False):
                    indicator_stats[indicator_type]['hits'] += 1
                else:
                    indicator_stats[indicator_type]['misses'] += 1

        # Calculate volatility as miss rate with exponential smoothing
        for indicator_type, stats in indicator_stats.items():
            total = stats['hits'] + stats['misses']
            if total > 0:
                miss_rate = stats['misses'] / total
                # Exponential moving average: smooth volatility updates
                current_volatility = self._indicator_volatility.get(indicator_type, 0.5)
                self._indicator_volatility[indicator_type] = (current_volatility * 0.7) + (miss_rate * 0.3)

        self._last_volatility_update = current_time

    def get_hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            Hit rate as percentage (0.0 to 1.0)
        """
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    def calculate_recent_hit_rate(self, window_seconds: int = 300) -> float:
        """
        Calculate hit rate over recent time window.

        Args:
            window_seconds: Time window in seconds (default 300 = 5 minutes)

        Returns:
            Hit rate over the time window (0.0 to 1.0)
        """
        current_time = time.time()
        recent_accesses = [
            access for access in self._access_history
            if current_time - access['timestamp'] < window_seconds
        ]

        if not recent_accesses:
            return 0.0

        recent_hits = sum(1 for access in recent_accesses if access.get('hit', False))
        return recent_hits / len(recent_accesses)

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        self._access_order.clear()

        self.logger.info("cache_manager.cleared", {
            "entries_cleared": count,
            "hits_before_clear": self._hits,
            "misses_before_clear": self._misses
        })

        return count

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Updates volatility before returning stats to ensure fresh metrics.

        Returns:
            Dictionary with cache metrics including volatility and recent hit rates
        """
        # Update volatility metrics before returning statistics
        self.update_volatility()

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "utilization_pct": (len(self._cache) / self.max_size) * 100,
            "hit_rate": self.get_hit_rate(),
            "hits": self._hits,
            "misses": self._misses,
            "total_accesses": self._hits + self._misses,
            "volatility_scores": self._indicator_volatility.copy(),
            "recent_hit_rate_5m": self.calculate_recent_hit_rate(300)
        }
