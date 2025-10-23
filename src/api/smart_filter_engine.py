"""
Smart Filter Engine
==================
Intelligent filtering engine for bandwidth optimization and data prioritization.
Production-ready with adaptive filtering based on client preferences and network conditions.
"""

import asyncio
from typing import Dict, Any, Optional, List, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import time
import threading

from ..core.logger import StructuredLogger


class BandwidthProfile(str, Enum):
    """Bandwidth usage profiles"""

    LOW = "low"         # Minimal data, essential updates only
    MEDIUM = "medium"   # Balanced data, important updates
    HIGH = "high"       # Full data stream, all updates
    UNLIMITED = "unlimited"  # No filtering, maximum data


class DataPriority(str, Enum):
    """Data priority levels for filtering decisions"""

    CRITICAL = "critical"    # Trading signals, order updates
    HIGH = "high"           # Market data, position changes
    NORMAL = "normal"       # Regular updates, indicators
    LOW = "low"            # Analytics, logs, status updates


@dataclass
class ClientProfile:
    """Client filtering profile with preferences and limits"""

    client_id: str
    bandwidth_profile: BandwidthProfile = BandwidthProfile.MEDIUM
    priority_symbols: Set[str] = field(default_factory=set)
    data_types: Set[str] = field(default_factory=lambda: {"price", "volume", "change_24h"})
    indicator_types: Set[str] = field(default_factory=lambda: {"RSI", "SMA"})
    signal_sensitivity: str = "medium"  # low, medium, high
    max_updates_per_second: int = 10
    compression_enabled: bool = True

    # Dynamic state
    current_bandwidth_usage: int = 0  # bytes per second
    last_update_time: float = field(default_factory=time.time)
    update_count_this_second: int = 0

    # Adaptive filtering
    filter_strength: float = 1.0  # 0.0 = no filtering, 1.0 = maximum filtering
    consecutive_rejections: int = 0

    # Thread safety
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)

    def should_receive_update(self, data_priority: DataPriority, symbol: str, data_type: str) -> bool:
        """Determine if client should receive this update (thread-safe)"""

        # Always allow critical updates
        if data_priority == DataPriority.CRITICAL:
            return True

        with self._lock:
            # Check rate limiting with atomic operations
            current_time = time.time()
            if current_time - self.last_update_time >= 1.0:
                # Reset counter every second
                self.update_count_this_second = 0
                self.last_update_time = current_time

            # Check if this update would exceed the limit
            if self.update_count_this_second >= self.max_updates_per_second:
                return False

            # Apply bandwidth-based filtering
            if self.bandwidth_profile == BandwidthProfile.LOW:
                # Only priority symbols and critical data
                if symbol not in self.priority_symbols and data_priority != DataPriority.HIGH:
                    return False
                if data_type not in ["price", "change_24h"]:
                    return False

            elif self.bandwidth_profile == BandwidthProfile.MEDIUM:
                # Balanced filtering
                if symbol not in self.priority_symbols and len(self.priority_symbols) > 0:
                    # Filter non-priority symbols for non-critical data
                    if data_priority.value <= DataPriority.NORMAL.value:
                        return False

            # Apply data type filtering
            if data_type not in self.data_types:
                return False

            # Apply adaptive filtering based on consecutive rejections
            if self.consecutive_rejections > 5:
                # Increase filtering strength
                self.filter_strength = min(1.0, self.filter_strength + 0.1)
                # Only allow high priority data
                if data_priority.value < DataPriority.NORMAL.value:
                    return False

            return True

    def record_update_sent(self, data_size: int):
        """Record that an update was sent to this client (thread-safe)"""
        with self._lock:
            self.update_count_this_second += 1
            self.current_bandwidth_usage += data_size
            self.consecutive_rejections = 0  # Reset rejection counter

    def record_update_rejected(self):
        """Record that an update was rejected for this client (thread-safe)"""
        with self._lock:
            self.consecutive_rejections += 1

    def adapt_filtering(self, network_conditions: Dict[str, Any]):
        """Adapt filtering based on network conditions (thread-safe)"""
        with self._lock:
            latency = network_conditions.get("latency_ms", 100)
            packet_loss = network_conditions.get("packet_loss_pct", 0)

            # Increase filtering under poor network conditions
            if latency > 500 or packet_loss > 5:
                self.filter_strength = min(1.0, self.filter_strength + 0.2)
                self.max_updates_per_second = max(1, self.max_updates_per_second // 2)
            elif latency < 100 and packet_loss < 1:
                # Reduce filtering under good conditions
                self.filter_strength = max(0.0, self.filter_strength - 0.1)
                self.max_updates_per_second = min(50, self.max_updates_per_second + 1)


@dataclass
class FilterRule:
    """Filtering rule with conditions and actions"""

    rule_id: str
    name: str
    conditions: Dict[str, Any]
    action: str  # "allow", "deny", "throttle"
    priority: int = 0

    def matches(self, data: Dict[str, Any], client_profile: ClientProfile) -> bool:
        """Check if this rule matches the data and client"""

        # Check symbol conditions
        if "symbols" in self.conditions:
            symbol_list = self.conditions["symbols"]
            if isinstance(symbol_list, list) and data.get("symbol") not in symbol_list:
                return False
            elif isinstance(symbol_list, str) and symbol_list == "priority_only":
                if data.get("symbol") not in client_profile.priority_symbols:
                    return False

        # Check data type conditions
        if "data_types" in self.conditions:
            if data.get("data_type") not in self.conditions["data_types"]:
                return False

        # Check value conditions
        if "min_value" in self.conditions:
            value = data.get("value", 0)
            if isinstance(value, (int, float)) and value < self.conditions["min_value"]:
                return False

        if "max_value" in self.conditions:
            value = data.get("value", 0)
            if isinstance(value, (int, float)) and value > self.conditions["max_value"]:
                return False

        # Check time conditions
        if "time_range" in self.conditions:
            # Could implement time-based filtering
            pass

        return True


class SmartFilterEngine:
    """
    Intelligent filtering engine for bandwidth optimization.

    Features:
    - Client-specific filtering profiles
    - Adaptive filtering based on network conditions
    - Priority-based data delivery
    - Bandwidth usage monitoring
    - Rule-based filtering system
    - Thread-safe operations
    """

    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger

        # Client profiles
        self.client_profiles: Dict[str, ClientProfile] = {}
        self._profiles_lock = threading.RLock()

        # Filtering rules
        self.filter_rules: List[FilterRule] = []
        self._rules_lock = threading.RLock()
        self._setup_default_rules()

        # Performance tracking
        self.total_updates_processed = 0
        self.total_updates_sent = 0
        self.total_updates_filtered = 0
        self.bandwidth_saved_bytes = 0
        self._stats_lock = threading.RLock()

        # Network condition monitoring
        self.network_conditions: Dict[str, Any] = {
            "latency_ms": 100,
            "packet_loss_pct": 0,
            "bandwidth_mbps": 10
        }
        self._network_lock = threading.RLock()

        # Adaptive adjustment timer
        self.last_adaptation_time = time.time()

    def _setup_default_rules(self):
        """Setup default filtering rules"""

        # High priority rule - always allow trading signals
        self.filter_rules.append(FilterRule(
            rule_id="high_priority_signals",
            name="High Priority Signals",
            conditions={"data_types": ["signal"]},
            action="allow",
            priority=100
        ))

        # Medium priority rule - allow market data for priority symbols
        self.filter_rules.append(FilterRule(
            rule_id="priority_market_data",
            name="Priority Market Data",
            conditions={"symbols": "priority_only", "data_types": ["price", "volume"]},
            action="allow",
            priority=50
        ))

        # Low priority rule - throttle non-essential data
        self.filter_rules.append(FilterRule(
            rule_id="throttle_non_essential",
            name="Throttle Non-Essential Data",
            conditions={"data_types": ["analytics", "logs"]},
            action="throttle",
            priority=10
        ))

    def create_client_profile(self,
                            client_id: str,
                            bandwidth_profile: BandwidthProfile = BandwidthProfile.MEDIUM,
                            priority_symbols: Optional[List[str]] = None,
                            preferences: Optional[Dict[str, Any]] = None) -> ClientProfile:
        """
        Create or update client filtering profile.

        Args:
            client_id: Client identifier
            bandwidth_profile: Bandwidth usage profile
            priority_symbols: List of priority symbols
            preferences: Additional client preferences

        Returns:
            Created or updated client profile
        """
        profile = ClientProfile(
            client_id=client_id,
            bandwidth_profile=bandwidth_profile
        )

        if priority_symbols:
            profile.priority_symbols = set(priority_symbols)

        if preferences:
            # Apply preferences
            if "data_types" in preferences:
                profile.data_types = set(preferences["data_types"])
            if "indicator_types" in preferences:
                profile.indicator_types = set(preferences["indicator_types"])
            if "signal_sensitivity" in preferences:
                profile.signal_sensitivity = preferences["signal_sensitivity"]
            if "max_updates_per_second" in preferences:
                profile.max_updates_per_second = preferences["max_updates_per_second"]
            if "compression_enabled" in preferences:
                profile.compression_enabled = preferences["compression_enabled"]

        with self._profiles_lock:
            self.client_profiles[client_id] = profile

        if self.logger:
            self.logger.info("smart_filter.client_profile_created", {
                "client_id": client_id,
                "bandwidth_profile": bandwidth_profile,
                "priority_symbols_count": len(profile.priority_symbols),
                "max_updates_per_second": profile.max_updates_per_second
            })

        return profile

    def should_send_to_client(self,
                             client_id: str,
                             data: Dict[str, Any],
                             data_size_bytes: int = 1024) -> tuple[bool, str]:
        """
        Determine if data should be sent to client and why (thread-safe).

        Args:
            client_id: Target client ID
            data: Data to be sent
            data_size_bytes: Estimated size of data in bytes

        Returns:
            Tuple of (should_send, reason)
        """
        with self._stats_lock:
            self.total_updates_processed += 1

        # Get client profile (thread-safe)
        with self._profiles_lock:
            profile = self.client_profiles.get(client_id)
            if not profile:
                # Create default profile for unknown clients
                profile = self.create_client_profile(client_id)

        # Determine data priority
        data_priority = self._calculate_data_priority(data)

        # Extract data attributes
        symbol = data.get("symbol", "")
        data_type = data.get("data_type", data.get("type", "unknown"))

        # Apply rule-based filtering first
        rule_result = self._apply_filter_rules(data, profile)
        if rule_result[0] is False:
            with self._stats_lock:
                self.total_updates_filtered += 1
                self.bandwidth_saved_bytes += data_size_bytes
            profile.record_update_rejected()
            return rule_result

        # Apply client-specific filtering
        should_send = profile.should_receive_update(data_priority, symbol, data_type)

        if should_send:
            profile.record_update_sent(data_size_bytes)
            with self._stats_lock:
                self.total_updates_sent += 1
            return True, "client_profile_allowed"
        else:
            with self._stats_lock:
                self.total_updates_filtered += 1
                self.bandwidth_saved_bytes += data_size_bytes
            profile.record_update_rejected()
            return False, "client_profile_filtered"

    def _apply_filter_rules(self, data: Dict[str, Any], profile: ClientProfile) -> tuple[bool, str]:
        """Apply filtering rules to data"""

        # Sort rules by priority (highest first)
        sorted_rules = sorted(self.filter_rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            if rule.matches(data, profile):
                if rule.action == "allow":
                    return True, f"rule_allowed:{rule.rule_id}"
                elif rule.action == "deny":
                    return False, f"rule_denied:{rule.rule_id}"
                elif rule.action == "throttle":
                    # Apply throttling logic
                    if self._should_throttle(data, profile):
                        return False, f"rule_throttled:{rule.rule_id}"

        # No rules matched, allow by default
        return True, "no_rule_matched"

    def _should_throttle(self, data: Dict[str, Any], profile: ClientProfile) -> bool:
        """Determine if data should be throttled"""
        # Simple throttling based on data type and client state
        data_type = data.get("data_type", "")

        if data_type in ["analytics", "logs"] and profile.bandwidth_profile in [BandwidthProfile.LOW, BandwidthProfile.MEDIUM]:
            return True

        return False

    def _calculate_data_priority(self, data: Dict[str, Any]) -> DataPriority:
        """Calculate priority level for data"""

        data_type = data.get("data_type", data.get("type", ""))

        # Critical priority
        if data_type in ["signal", "order_update", "position_update"]:
            return DataPriority.CRITICAL

        # High priority
        if data_type in ["market_data", "price_update", "trade"]:
            return DataPriority.HIGH

        # Normal priority
        if data_type in ["indicator", "volume_update"]:
            return DataPriority.NORMAL

        # Low priority (default)
        return DataPriority.LOW

    def update_network_conditions(self, conditions: Dict[str, Any]):
        """Update network condition monitoring (thread-safe)"""
        with self._network_lock:
            self.network_conditions.update(conditions)

            # Adapt client profiles based on new conditions
            current_time = time.time()
            if current_time - self.last_adaptation_time > 60:  # Adapt every minute
                self._adapt_client_profiles()
                self.last_adaptation_time = current_time

        if self.logger:
            self.logger.debug("smart_filter.network_conditions_updated", conditions)

    def _adapt_client_profiles(self):
        """Adapt all client profiles based on current network conditions (thread-safe)"""
        # Create a snapshot to avoid "dictionary changed size during iteration"
        with self._profiles_lock:
            profiles_snapshot = list(self.client_profiles.values())

        # Adapt each profile (each profile has its own lock)
        for profile in profiles_snapshot:
            profile.adapt_filtering(self.network_conditions)

    def add_filter_rule(self,
                        rule_id: str,
                        name: str,
                        conditions: Dict[str, Any],
                        action: str,
                        priority: int = 0):
        """Add a custom filtering rule (thread-safe)"""
        with self._rules_lock:
            # Remove existing rule with same ID
            self.filter_rules = [r for r in self.filter_rules if r.rule_id != rule_id]

            # Add new rule
            rule = FilterRule(
                rule_id=rule_id,
                name=name,
                conditions=conditions,
                action=action,
                priority=priority
            )

            self.filter_rules.append(rule)

        if self.logger:
            self.logger.info("smart_filter.rule_added", {
                "rule_id": rule_id,
                "name": name,
                "action": action,
                "priority": priority
            })

    def remove_filter_rule(self, rule_id: str):
        """Remove a filtering rule (thread-safe)"""
        with self._rules_lock:
            initial_count = len(self.filter_rules)
            self.filter_rules = [r for r in self.filter_rules if r.rule_id != rule_id]

        if len(self.filter_rules) < initial_count and self.logger:
            self.logger.info("smart_filter.rule_removed", {"rule_id": rule_id})

    def get_client_profile(self, client_id: str) -> Optional[ClientProfile]:
        """Get client filtering profile (thread-safe)"""
        with self._profiles_lock:
            return self.client_profiles.get(client_id)

    def get_filtering_stats(self) -> Dict[str, Any]:
        """Get comprehensive filtering statistics (thread-safe)"""
        with self._profiles_lock:
            total_clients = len(self.client_profiles)
            if total_clients > 0:
                avg_bandwidth_usage = sum(p.current_bandwidth_usage for p in self.client_profiles.values()) / total_clients
                avg_filter_strength = sum(p.filter_strength for p in self.client_profiles.values()) / total_clients
            else:
                avg_bandwidth_usage = 0
                avg_filter_strength = 0

        with self._stats_lock:
            stats = {
                "total_updates_processed": self.total_updates_processed,
                "total_updates_sent": self.total_updates_sent,
                "total_updates_filtered": self.total_updates_filtered,
                "bandwidth_saved_bytes": self.bandwidth_saved_bytes,
                "filtering_efficiency": (self.total_updates_filtered / max(self.total_updates_processed, 1)) * 100,
                "total_clients": total_clients,
                "average_bandwidth_usage": avg_bandwidth_usage,
                "average_filter_strength": avg_filter_strength,
            }

        with self._rules_lock:
            stats["active_rules"] = len(self.filter_rules)

        with self._network_lock:
            stats["network_conditions"] = self.network_conditions.copy()

        return stats

    def reset_stats(self):
        """Reset filtering statistics (thread-safe)"""
        with self._stats_lock:
            self.total_updates_processed = 0
            self.total_updates_sent = 0
            self.total_updates_filtered = 0
            self.bandwidth_saved_bytes = 0

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "healthy": True,
            "component": "SmartFilterEngine",
            "stats": self.get_filtering_stats(),
            "timestamp": datetime.now().isoformat()
        }