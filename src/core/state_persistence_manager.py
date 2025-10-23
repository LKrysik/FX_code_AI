#!/usr/bin/env python3
"""
State Persistence Manager - Redis-based persistence for temporal conditions
===========================================================================

Handles persistence and recovery of state machines for duration and sequence conditions.
Ensures zero state loss across system restarts for reliable live execution.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import asyncio

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from .logger import get_logger

logger = get_logger(__name__)


class StatePersistenceManager:
    """
    Redis-based state persistence with recovery capabilities.

    Manages persistence of temporal condition states to ensure zero state loss
    during system restarts. Uses structured Redis keys for efficient storage
    and recovery.
    """

    def __init__(self, redis_url: Optional[str] = None, settings = None):
        """
        Initialize the state persistence manager.

        Args:
            redis_url: Redis connection URL (optional, will use settings if not provided)
            settings: Application settings object
        """
        if redis_url:
            self.redis_url = redis_url
        elif settings and hasattr(settings, 'redis'):
            self.redis_url = settings.redis.url
        else:
            self.redis_url = "redis://localhost:6379/0"

        self.redis: Optional[redis.Redis] = None
        self._connected = False
        self.settings = settings

    async def connect(self) -> None:
        """Establish Redis connection."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, state persistence disabled")
            self._connected = False
            return

        if self.redis is None:
            self.redis = redis.from_url(self.redis_url)
        try:
            await self.redis.ping()
            self._connected = True
            logger.info("Connected to Redis for state persistence")
        except Exception as e:
            logger.error("Redis connection failed", {"error": str(e)})
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self.redis = None
            self._connected = False
            logger.info("Disconnected from Redis")

    async def persist_temporal_state(self, strategy_name: str, symbol: str,
                                   condition_id: str, state: Dict[str, Any]) -> bool:
        """
        Persist temporal condition state to Redis.

        Args:
            strategy_name: Name of the strategy
            symbol: Trading symbol (e.g., 'BTCUSDT')
            condition_id: Unique condition identifier
            state: State dictionary to persist

        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            await self.connect()

        try:
            key = f"strategy:{strategy_name}:temporal:{symbol}:{condition_id}"

            # Add metadata
            state_data = {
                **state,
                "last_update": datetime.now(timezone.utc).isoformat(),
                "strategy_name": strategy_name,
                "symbol": symbol,
                "condition_id": condition_id
            }

            # Set with TTL (24 hours for cleanup)
            success = await self.redis.set(key, json.dumps(state_data), ex=86400)

            if success:
                logger.debug(f"Persisted temporal state for {strategy_name}:{symbol}:{condition_id}")
            else:
                logger.warning(f"Failed to persist temporal state for {strategy_name}:{symbol}:{condition_id}")

            return bool(success)

        except Exception as e:
            logger.error("State persistence error", {"error": str(e), "operation": "persist_temporal_state"})
            return False

    async def recover_temporal_states(self, strategy_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Recover all temporal states for a strategy on startup.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Dictionary mapping condition keys to state data
        """
        if not self._connected:
            await self.connect()

        try:
            pattern = f"strategy:{strategy_name}:temporal:*:*"
            keys = await self.redis.keys(pattern)

            states = {}
            for key in keys:
                try:
                    state_data = await self.redis.get(key)
                    if state_data:
                        state_dict = json.loads(state_data)
                        states[key.decode('utf-8')] = state_dict
                        logger.debug(f"Recovered temporal state for key: {key}")
                except Exception as e:
                    logger.warning(f"Failed to recover state for key {key}: {e}")

            logger.info(f"Recovered {len(states)} temporal states for strategy {strategy_name}")
            return states

        except Exception as e:
            logger.error("Temporal state recovery error", {"error": str(e), "operation": "recover_temporal_states"})
            return {}

    async def recover_temporal_state(self, strategy_name: str, symbol: str,
                                   condition_id: str) -> Optional[Dict[str, Any]]:
        """
        Recover a specific temporal state.

        Args:
            strategy_name: Name of the strategy
            symbol: Trading symbol
            condition_id: Condition identifier

        Returns:
            State dictionary if found, None otherwise
        """
        if not self._connected:
            await self.connect()

        try:
            key = f"strategy:{strategy_name}:temporal:{symbol}:{condition_id}"
            state_data = await self.redis.get(key)

            if state_data:
                state_dict = json.loads(state_data)
                logger.debug(f"Recovered temporal state for {strategy_name}:{symbol}:{condition_id}")
                return state_dict
            else:
                logger.debug(f"No temporal state found for {strategy_name}:{symbol}:{condition_id}")
                return None

        except Exception as e:
            logger.error("Temporal state recovery error", {"error": str(e), "operation": "recover_temporal_state"})
            return None

    async def delete_temporal_state(self, strategy_name: str, symbol: str,
                                  condition_id: str) -> bool:
        """
        Delete a temporal state (for cleanup).

        Args:
            strategy_name: Name of the strategy
            symbol: Trading symbol
            condition_id: Condition identifier

        Returns:
            True if deleted, False otherwise
        """
        if not self._connected:
            await self.connect()

        try:
            key = f"strategy:{strategy_name}:temporal:{symbol}:{condition_id}"
            result = await self.redis.delete(key)

            if result:
                logger.debug(f"Deleted temporal state for {strategy_name}:{symbol}:{condition_id}")
            else:
                logger.debug(f"No temporal state found to delete for {strategy_name}:{symbol}:{condition_id}")

            return bool(result)

        except Exception as e:
            logger.error("Temporal state deletion error", {"error": str(e), "operation": "delete_temporal_state"})
            return False

    async def cleanup_expired_states(self, max_age_hours: int = 24) -> int:
        """
        Clean up expired temporal states.

        Args:
            max_age_hours: Maximum age in hours for state cleanup

        Returns:
            Number of states cleaned up
        """
        if not self._connected:
            await self.connect()

        try:
            # Get all temporal state keys
            pattern = "strategy:*:temporal:*:*"
            keys = await self.redis.keys(pattern)

            cleaned_count = 0
            cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)

            for key in keys:
                try:
                    state_data = await self.redis.get(key)
                    if state_data:
                        state_dict = json.loads(state_data)
                        last_update = state_dict.get("last_update")

                        if last_update:
                            # Parse ISO format timestamp
                            update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00')).timestamp()

                            if update_time < cutoff_time:
                                await self.redis.delete(key)
                                cleaned_count += 1
                                logger.debug(f"Cleaned up expired state: {key}")
                except Exception as e:
                    logger.warning(f"Error checking state for cleanup {key}: {e}")

            logger.info(f"Cleaned up {cleaned_count} expired temporal states")
            return cleaned_count

        except Exception as e:
            logger.error("State cleanup error", {"error": str(e), "operation": "cleanup_expired_states"})
            return 0

    async def get_state_stats(self, strategy_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about persisted states.

        Args:
            strategy_name: Optional strategy name filter

        Returns:
            Statistics dictionary
        """
        if not self._connected:
            await self.connect()

        try:
            if strategy_name:
                pattern = f"strategy:{strategy_name}:temporal:*:*"
            else:
                pattern = "strategy:*:temporal:*:*"

            keys = await self.redis.keys(pattern)

            stats = {
                "total_states": len(keys),
                "strategies": set(),
                "symbols": set()
            }

            for key in keys:
                key_str = key.decode('utf-8')
                parts = key_str.split(':')
                if len(parts) >= 4:
                    stats["strategies"].add(parts[1])
                    stats["symbols"].add(parts[3])

            stats["strategies"] = list(stats["strategies"])
            stats["symbols"] = list(stats["symbols"])

            return stats

        except Exception as e:
            logger.error("State stats error", {"error": str(e), "operation": "get_state_stats"})
            return {"error": str(e)}


# Global instance
state_persistence_manager = StatePersistenceManager()