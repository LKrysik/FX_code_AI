"""
Storage Interfaces - Ports for data persistence
===============================================
Abstract interfaces for data storage and retrieval.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncIterator
from datetime import datetime
import json


class IDataStorage(ABC):
    """
    Interface for general data storage.
    Abstracts away specific storage implementations (files, databases, etc.).
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Initialize connection to storage"""
        raise NotImplementedError
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to storage"""
        raise NotImplementedError
    
    @abstractmethod
    async def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store data with a key.
        Returns True if stored successfully.
        """
        raise NotImplementedError
    
    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data by key"""
        raise NotImplementedError
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in storage"""
        raise NotImplementedError
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete data by key"""
        pass
    
    @abstractmethod
    async def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys, optionally filtered by prefix"""
        pass
    
    @abstractmethod
    async def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a key"""
        pass
    
    @abstractmethod
    async def update_metadata(self, key: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for a key"""
        pass
    
    @abstractmethod
    async def cleanup_old_data(self, older_than_days: int) -> int:
        """Clean up data older than specified days"""
        pass
    
    @abstractmethod
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        pass
    
    @abstractmethod
    def get_storage_type(self) -> str:
        """Get storage type name"""
        pass


class IConfigStorage(ABC):
    """
    Interface for configuration storage.
    Specialized for configuration data with validation.
    """
    
    @abstractmethod
    async def load_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Load configuration by name"""
        pass
    
    @abstractmethod
    async def save_config(self, config_name: str, config_data: Dict[str, Any]) -> bool:
        """Save configuration data"""
        pass
    
    @abstractmethod
    async def get_config_version(self, config_name: str) -> Optional[str]:
        """Get configuration version"""
        pass
    
    @abstractmethod
    async def list_configs(self) -> List[str]:
        """List all available configurations"""
        pass
    
    @abstractmethod
    async def backup_config(self, config_name: str) -> str:
        """
        Create backup of configuration.
        Returns backup identifier.
        """
        pass
    
    @abstractmethod
    async def restore_config(self, config_name: str, backup_id: str) -> bool:
        """Restore configuration from backup"""
        pass
    
    @abstractmethod
    async def validate_config(self, config_name: str, config_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate configuration data.
        Returns (is_valid, error_messages)
        """
        pass
    
    @abstractmethod
    async def get_config_schema(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration schema for validation"""
        pass


class ITimeSeriesStorage(ABC):
    """
    Interface for time series data storage.
    Optimized for time-based data like market data and performance metrics.
    """
    
    @abstractmethod
    async def write_point(
        self,
        measurement: str,
        tags: Dict[str, str],
        fields: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Write a single data point"""
        pass
    
    @abstractmethod
    async def write_points(
        self,
        measurement: str,
        points: List[Dict[str, Any]]
    ) -> int:
        """
        Write multiple data points.
        Returns number of points written successfully.
        """
        pass
    
    @abstractmethod
    async def query_range(
        self,
        measurement: str,
        start_time: datetime,
        end_time: datetime,
        tags: Optional[Dict[str, str]] = None,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Query data points in time range"""
        pass
    
    @abstractmethod
    async def query_latest(
        self,
        measurement: str,
        tags: Optional[Dict[str, str]] = None,
        limit: int = 1
    ) -> List[Dict[str, Any]]:
        """Query latest data points"""
        pass
    
    @abstractmethod
    async def aggregate(
        self,
        measurement: str,
        start_time: datetime,
        end_time: datetime,
        aggregation: str,  # sum, avg, min, max, count
        interval: str,  # 1m, 5m, 1h, 1d
        tags: Optional[Dict[str, str]] = None,
        field: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Aggregate data over time intervals"""
        pass
    
    @abstractmethod
    async def delete_range(
        self,
        measurement: str,
        start_time: datetime,
        end_time: datetime,
        tags: Optional[Dict[str, str]] = None
    ) -> int:
        """Delete data points in time range"""
        pass
    
    @abstractmethod
    async def get_measurements(self) -> List[str]:
        """Get list of all measurements"""
        pass
    
    @abstractmethod
    async def get_tag_keys(self, measurement: str) -> List[str]:
        """Get tag keys for a measurement"""
        pass
    
    @abstractmethod
    async def get_field_keys(self, measurement: str) -> List[str]:
        """Get field keys for a measurement"""
        pass


class ILogStorage(ABC):
    """
    Interface for log storage and retrieval.
    Specialized for application logs and audit trails.
    """
    
    @abstractmethod
    async def write_log(
        self,
        level: str,
        message: str,
        component: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Write a log entry"""
        pass
    
    @abstractmethod
    async def query_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[str] = None,
        component: Optional[str] = None,
        search_text: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query log entries with filters"""
        pass
    
    @abstractmethod
    async def get_log_levels(self) -> List[str]:
        """Get all available log levels"""
        pass
    
    @abstractmethod
    async def get_components(self) -> List[str]:
        """Get all components that have logged"""
        pass
    
    @abstractmethod
    async def get_error_summary(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, int]:
        """Get summary of errors by component"""
        pass
    
    @abstractmethod
    async def archive_old_logs(self, older_than_days: int) -> int:
        """Archive logs older than specified days"""
        pass


class ICacheStorage(ABC):
    """
    Interface for cache storage.
    High-performance storage for frequently accessed data.
    """
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set cache value with optional TTL"""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get cache value"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete cache entry"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass
    
    @abstractmethod
    async def expire(self, key: str, ttl_seconds: int) -> bool:
        """Set expiration time for key"""
        pass
    
    @abstractmethod
    async def ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key"""
        pass
    
    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value"""
        pass
    
    @abstractmethod
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement numeric value"""
        pass
    
    @abstractmethod
    async def set_multiple(self, key_values: Dict[str, Any]) -> int:
        """Set multiple key-value pairs"""
        pass
    
    @abstractmethod
    async def get_multiple(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values by keys"""
        pass
    
    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        pass
    
    @abstractmethod
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics and info"""
        pass


class IBackupStorage(ABC):
    """
    Interface for backup and restore operations.
    Handles data backup and disaster recovery.
    """
    
    @abstractmethod
    async def create_backup(
        self,
        backup_name: str,
        data_sources: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create backup of specified data sources.
        Returns backup identifier.
        """
        pass
    
    @abstractmethod
    async def restore_backup(self, backup_id: str, target_location: Optional[str] = None) -> bool:
        """Restore data from backup"""
        pass
    
    @abstractmethod
    async def list_backups(self, data_source: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available backups"""
        pass
    
    @abstractmethod
    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup"""
        pass
    
    @abstractmethod
    async def verify_backup(self, backup_id: str) -> tuple[bool, List[str]]:
        """
        Verify backup integrity.
        Returns (is_valid, error_messages)
        """
        pass
    
    @abstractmethod
    async def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed backup information"""
        pass
    
    @abstractmethod
    async def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """Clean up old backups, keeping specified count"""
        pass
    
    @abstractmethod
    async def schedule_backup(
        self,
        backup_name: str,
        data_sources: List[str],
        schedule: str,  # cron expression
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Schedule automatic backup"""
        pass
    
    @abstractmethod
    async def cancel_scheduled_backup(self, schedule_id: str) -> bool:
        """Cancel scheduled backup"""
        pass


class IStorageManager(ABC):
    """
    Interface for managing multiple storage backends.
    Coordinates different storage types and provides unified access.
    """
    
    @abstractmethod
    async def register_storage(self, name: str, storage: IDataStorage) -> None:
        """Register a storage backend"""
        pass
    
    @abstractmethod
    async def unregister_storage(self, name: str) -> None:
        """Unregister a storage backend"""
        pass
    
    @abstractmethod
    async def get_storage(self, name: str) -> Optional[IDataStorage]:
        """Get storage backend by name"""
        pass
    
    @abstractmethod
    async def get_primary_storage(self) -> IDataStorage:
        """Get primary storage backend"""
        pass
    
    @abstractmethod
    async def set_primary_storage(self, name: str) -> bool:
        """Set primary storage backend"""
        pass
    
    @abstractmethod
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all storage backends"""
        pass
    
    @abstractmethod
    async def get_storage_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all storage backends"""
        pass
    
    @abstractmethod
    async def migrate_data(self, from_storage: str, to_storage: str, data_filter: Optional[str] = None) -> int:
        """
        Migrate data between storage backends.
        Returns number of items migrated.
        """
        pass
    
    @abstractmethod
    async def replicate_data(self, source_storage: str, target_storages: List[str]) -> Dict[str, int]:
        """
        Replicate data to multiple storage backends.
        Returns dict of target_storage -> items_replicated.
        """
        pass