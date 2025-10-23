"""
Delta Compressor
================
Compresses data by sending only changes (deltas) instead of full payloads.
Production-ready with intelligent compression and memory management.
"""

import json
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from dataclasses import dataclass, field
from decimal import Decimal
import time
import zlib
import threading

from ..core.logger import StructuredLogger


@dataclass
class CompressionStats:
    """Statistics for compression operations"""

    total_original_bytes: int = 0
    total_compressed_bytes: int = 0
    total_deltas_created: int = 0
    total_full_updates: int = 0
    compression_ratio: float = 0.0
    average_delta_size: float = 0.0

    def update(self, original_size: int, compressed_size: int, is_delta: bool):
        """Update statistics with new compression data"""
        self.total_original_bytes += original_size
        self.total_compressed_bytes += compressed_size

        if is_delta:
            self.total_deltas_created += 1
        else:
            self.total_full_updates += 1

        # Recalculate ratios
        if self.total_original_bytes > 0:
            self.compression_ratio = (1 - (self.total_compressed_bytes / self.total_original_bytes)) * 100

        if self.total_deltas_created > 0:
            self.average_delta_size = self.total_compressed_bytes / self.total_deltas_created

    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics"""
        return {
            "total_original_bytes": self.total_original_bytes,
            "total_compressed_bytes": self.total_compressed_bytes,
            "total_deltas_created": self.total_deltas_created,
            "total_full_updates": self.total_full_updates,
            "compression_ratio_percent": self.compression_ratio,
            "average_delta_size_bytes": self.average_delta_size,
            "bandwidth_savings_percent": self.compression_ratio
        }


@dataclass
class ClientState:
    """Tracks client-specific state for delta compression"""

    client_id: str
    last_full_update: Dict[str, Any] = field(default_factory=dict)
    last_update_time: float = field(default_factory=time.time)
    consecutive_deltas: int = 0
    total_updates_sent: int = 0

    # Compression settings
    compression_enabled: bool = True
    max_consecutive_deltas: int = 10  # Send full update after this many deltas
    delta_threshold: float = 0.1  # Minimum change threshold for delta

    def should_send_full_update(self) -> bool:
        """Determine if a full update should be sent instead of delta"""
        return (
            self.consecutive_deltas >= self.max_consecutive_deltas or
            not self.last_full_update or
            time.time() - self.last_update_time > 300  # 5 minutes
        )

    def update_state(self, data: Dict[str, Any], is_delta: bool):
        """Update client state after sending data"""
        self.last_update_time = time.time()
        self.total_updates_sent += 1

        if is_delta:
            self.consecutive_deltas += 1
        else:
            self.consecutive_deltas = 0
            self.last_full_update = data.copy()

    def calculate_delta(self, new_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculate delta between last full update and new data"""
        if not self.last_full_update:
            return None

        delta = {}
        changes_found = False

        def compare_values(path: str, old_val: Any, new_val: Any):
            """Recursively compare values and build delta"""
            nonlocal changes_found

            if isinstance(old_val, dict) and isinstance(new_val, dict):
                # Compare dictionaries
                for key in set(old_val.keys()) | set(new_val.keys()):
                    old_item = old_val.get(key)
                    new_item = new_val.get(key)
                    compare_values(f"{path}.{key}" if path else key, old_item, new_item)
            elif isinstance(old_val, (list, tuple)) and isinstance(new_val, (list, tuple)):
                # Compare arrays (simple comparison)
                if old_val != new_val:
                    delta[path] = new_val
                    changes_found = True
            else:
                # Compare primitive values
                if self._values_differ(old_val, new_val):
                    delta[path] = new_val
                    changes_found = True

        compare_values("", self.last_full_update, new_data)
        return delta if changes_found else None

    def _values_differ(self, old_val: Any, new_val: Any) -> bool:
        """Check if two values differ significantly"""
        if old_val is None and new_val is None:
            return False
        if old_val is None or new_val is None:
            return True

        # Handle numeric types with threshold
        if isinstance(old_val, (int, float, Decimal)) and isinstance(new_val, (int, float, Decimal)):
            try:
                old_dec = Decimal(str(old_val))
                new_dec = Decimal(str(new_val))

                if old_dec == 0:
                    return abs(new_dec) > self.delta_threshold

                percent_change = abs((new_dec - old_dec) / old_dec)
                return percent_change >= self.delta_threshold
            except:
                return old_val != new_val

        # Default comparison
        return old_val != new_val


class DeltaCompressor:
    """
    Compresses data streams by sending only changes (deltas) instead of full payloads.

    Features:
    - Intelligent delta calculation based on data changes
    - Client-specific state tracking
    - Compression ratio monitoring
    - Automatic full update fallback
    - Memory-efficient operation
    """

    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger

        # Thread safety locks
        self._client_states_lock = threading.RLock()  # Protects client_states dict
        self._stats_lock = threading.Lock()  # Protects stats updates

        # Client state tracking
        self.client_states: Dict[str, ClientState] = {}

        # Global compression statistics
        self.stats = CompressionStats()

        # Configuration
        self.default_compression_level = 6  # zlib compression level
        self.max_client_states = 10000  # Maximum client states to track
        self.cleanup_interval_seconds = 3600  # 1 hour cleanup interval

        # Performance tracking
        self.last_cleanup_time = time.time()

    def compress_data(self, client_id: str, data: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
        """
        Compress data for client by calculating delta or sending full update.

        Args:
            client_id: Client identifier
            data: Data to compress

        Returns:
            Tuple of (compressed_data, is_delta)
        """
        # Get or create client state
        client_state = self._get_or_create_client_state(client_id)

        # Check if we should send a full update
        if client_state.should_send_full_update():
            return self._create_full_update(client_state, data)

        # Calculate delta
        delta = client_state.calculate_delta(data)

        if delta:
            # Send delta
            return self._create_delta_update(client_state, delta, data)
        else:
            # No significant changes, send full update to reset state
            return self._create_full_update(client_state, data)

    def _create_full_update(self, client_state: ClientState, data: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
        """Create a full update message"""
        full_update = {
            "type": "full_update",
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        # Compress if enabled
        if client_state.compression_enabled:
            compressed_data = self._compress_payload(full_update)
            original_size = len(json.dumps(full_update).encode('utf-8'))
            compressed_size = len(compressed_data)

            with self._stats_lock:
                self.stats.update(original_size, compressed_size, is_delta=False)
            client_state.update_state(data, is_delta=False)

            return {"compressed": compressed_data.decode('latin-1')}, False
        else:
            original_size = len(json.dumps(full_update).encode('utf-8'))
            with self._stats_lock:
                self.stats.update(original_size, original_size, is_delta=False)
            client_state.update_state(data, is_delta=False)

            return full_update, False

    def _create_delta_update(self, client_state: ClientState, delta: Dict[str, Any], full_data: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
        """Create a delta update message"""
        delta_update = {
            "type": "delta_update",
            "timestamp": datetime.now().isoformat(),
            "delta": delta,
            "base_timestamp": datetime.fromtimestamp(client_state.last_update_time).isoformat()
        }

        # Compress if enabled
        if client_state.compression_enabled:
            compressed_data = self._compress_payload(delta_update)
            original_size = len(json.dumps(delta_update).encode('utf-8'))
            compressed_size = len(compressed_data)

            with self._stats_lock:
                self.stats.update(original_size, compressed_size, is_delta=True)
            client_state.update_state(full_data, is_delta=True)

            return {"compressed": compressed_data.decode('latin-1')}, True
        else:
            original_size = len(json.dumps(delta_update).encode('utf-8'))
            with self._stats_lock:
                self.stats.update(original_size, original_size, is_delta=True)
            client_state.update_state(full_data, is_delta=True)

            return delta_update, True

    def decompress_data(self, client_id: str, compressed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decompress received data for client.

        Args:
            client_id: Client identifier
            compressed_data: Compressed data received

        Returns:
            Decompressed data
        """
        # Check if data is compressed
        if "compressed" in compressed_data:
            # Decompress
            compressed_bytes = compressed_data["compressed"].encode('latin-1')
            decompressed_bytes = self._decompress_payload(compressed_bytes)
            decompressed_data = json.loads(decompressed_bytes.decode('utf-8'))
        else:
            decompressed_data = compressed_data

        # Apply delta if needed
        if decompressed_data.get("type") == "delta_update":
            return self._apply_delta(client_id, decompressed_data)
        else:
            # Full update - update client state
            with self._client_states_lock:
                client_state = self.client_states.get(client_id)
                if client_state and "data" in decompressed_data:
                    client_state.last_full_update = decompressed_data["data"]
                    client_state.consecutive_deltas = 0
            return decompressed_data

    def _apply_delta(self, client_id: str, delta_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply delta to reconstruct full data"""
        with self._client_states_lock:
            client_state = self.client_states.get(client_id)

            if not client_state or not client_state.last_full_update:
                # No base data available, return delta as-is
                return delta_data

            # Apply delta to base data
            reconstructed = self._apply_delta_to_dict(client_state.last_full_update.copy(), delta_data["delta"])

            # Update client state
            client_state.last_full_update = reconstructed
            client_state.consecutive_deltas += 1

        return {
            "type": "full_update",
            "timestamp": delta_data["timestamp"],
            "data": reconstructed
        }

    def _apply_delta_to_dict(self, base: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
        """Apply delta changes to base dictionary"""
        result = base.copy()

        for key, value in delta.items():
            if "." in key:
                # Nested key (e.g., "market.btc_usdt.price")
                parts = key.split(".")
                current = result
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                # Direct key
                result[key] = value

        return result

    def _compress_payload(self, data: Dict[str, Any]) -> bytes:
        """Compress data payload using zlib"""
        json_str = json.dumps(data, separators=(',', ':'), default=self._json_serializer)
        return zlib.compress(json_str.encode('utf-8'), level=self.default_compression_level)

    def _json_serializer(self, obj):
        """JSON serializer for custom types"""
        if isinstance(obj, Decimal):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def _decompress_payload(self, compressed_data: bytes) -> bytes:
        """Decompress data payload"""
        return zlib.decompress(compressed_data)

    def _get_or_create_client_state(self, client_id: str) -> ClientState:
        """Get or create client state"""
        with self._client_states_lock:
            if client_id not in self.client_states:
                self.client_states[client_id] = ClientState(client_id=client_id)

                # Cleanup old states if we have too many
                if len(self.client_states) > self.max_client_states:
                    self._cleanup_old_states()

            return self.client_states[client_id]

    def _cleanup_old_states(self):
        """Cleanup old/inactive client states"""
        current_time = time.time()
        cutoff_time = current_time - (self.cleanup_interval_seconds * 2)  # 2x cleanup interval

        # Remove old states
        to_remove = []
        with self._client_states_lock:
            for client_id, state in self.client_states.items():
                if state.last_update_time < cutoff_time:
                    to_remove.append(client_id)

            for client_id in to_remove:
                del self.client_states[client_id]

        if self.logger and to_remove:
            self.logger.info("delta_compressor.states_cleaned", {
                "removed_count": len(to_remove),
                "remaining_count": len(self.client_states)
            })

    def configure_client(self, client_id: str, settings: Dict[str, Any]):
        """Configure compression settings for a client"""
        client_state = self._get_or_create_client_state(client_id)

        if "compression_enabled" in settings:
            client_state.compression_enabled = settings["compression_enabled"]
        if "max_consecutive_deltas" in settings:
            client_state.max_consecutive_deltas = settings["max_consecutive_deltas"]
        if "delta_threshold" in settings:
            client_state.delta_threshold = settings["delta_threshold"]

        if self.logger:
            self.logger.info("delta_compressor.client_configured", {
                "client_id": client_id,
                "settings": settings
            })

    def get_client_stats(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific client"""
        with self._client_states_lock:
            client_state = self.client_states.get(client_id)
            if not client_state:
                return None

        return {
            "client_id": client_id,
            "total_updates_sent": client_state.total_updates_sent,
            "consecutive_deltas": client_state.consecutive_deltas,
            "compression_enabled": client_state.compression_enabled,
            "last_update_time": client_state.last_update_time,
            "time_since_last_update": time.time() - client_state.last_update_time
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive compression statistics"""
        with self._client_states_lock:
            active_clients = len(self.client_states)
        return {
            "global_stats": self.stats.get_stats(),
            "active_clients": active_clients,
            "max_clients": self.max_client_states,
            "compression_level": self.default_compression_level,
            "cleanup_interval_seconds": self.cleanup_interval_seconds
        }

    def reset_stats(self):
        """Reset compression statistics"""
        self.stats = CompressionStats()

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "healthy": True,
            "component": "DeltaCompressor",
            "stats": self.get_stats(),
            "timestamp": datetime.now().isoformat()
        }