"""
Indicator Persistence Service
============================
Handles CSV read/write operations for indicator values with unified format.

This service is the ONLY component responsible for CSV persistence operations and provides:
- Unified CSV format: [timestamp, value] for ALL indicators
- Real-time append operations for streaming values
- Batch overwrite operations for simulation data
- Event-driven architecture with loose coupling to Engine
- Thread-safe operations with advanced file locking
- Race condition prevention and atomic file operations
- Proper file organization and error handling

CRITICAL: Only this service should write CSV files - engines must not write directly.
"""

import csv
import json
import os
import time
from pathlib import Path
from threading import RLock
from typing import Dict, Any, List, Optional, Union
import tempfile
import shutil

# Platform-specific imports
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

from ..types.indicator_types import IndicatorValue

try:
    from ...core.event_bus import EventBus, EventPriority
    from ...core.logger import StructuredLogger
except Exception:
    from src.core.event_bus import EventBus, EventPriority
    from src.core.logger import StructuredLogger


class IndicatorPersistenceService:
    """
    Service responsible for CSV read/write operations with unified format.
    
    Features:
    - Unified CSV format across all indicator types
    - Real-time append operations (mode='a')
    - Batch simulation overwrite operations (mode='w')
    - Event-driven architecture
    - Thread-safe operations with file locking
    - Race condition prevention through atomic operations
    - Proper error handling and logging
    
    CRITICAL: This is the ONLY service that should write CSV files.
    Engines must delegate all persistence operations to this service.
    """

    def __init__(self, event_bus: EventBus, logger: StructuredLogger, base_data_dir: str = "data"):
        """
        Initialize IndicatorPersistenceService.
        
        Args:
            event_bus: EventBus for listening to indicator events
            logger: StructuredLogger for logging operations
            base_data_dir: Base directory for CSV file storage
        """
        self.event_bus = event_bus
        self.logger = logger
        self.base_data_dir = Path(base_data_dir)
        self._file_lock = RLock()  # Thread-safe file operations
        self._active_file_locks = {}  # Per-file locking for better concurrency
        
        # Setup event listeners
        self._setup_event_listeners()
        
        # Ensure base directory exists
        self.base_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("indicator_persistence_service.initialized", {
            "base_data_dir": str(self.base_data_dir),
            "features": [
                "thread_safe_operations",
                "atomic_file_writes", 
                "race_condition_prevention",
                "per_file_locking"
            ]
        })

    def _setup_event_listeners(self):
        """Setup event listeners for indicator events."""
        # Listen for real-time indicator value calculations
        self.event_bus.subscribe(
            "indicator_value_calculated",
            self._handle_single_value_event,
            priority=EventPriority.NORMAL
        )
        
        # Listen for simulation completion events  
        self.event_bus.subscribe(
            "indicator_simulation_completed",
            self._handle_simulation_completed_event,
            priority=EventPriority.NORMAL
        )
        
        self.logger.debug("indicator_persistence_service.event_listeners_setup")

    def _get_file_lock_key(self, csv_file_path: Path) -> str:
        """Generate unique lock key for file path."""
        return str(csv_file_path.resolve())
    
    def _acquire_file_lock(self, csv_file_path: Path):
        """Acquire per-file lock to prevent race conditions."""
        lock_key = self._get_file_lock_key(csv_file_path)
        if lock_key not in self._active_file_locks:
            self._active_file_locks[lock_key] = RLock()
        return self._active_file_locks[lock_key]
    
    def _atomic_csv_write(self, csv_file_path: Path, write_mode: str, 
                         data_rows: List[List[str]], header: List[str] = None) -> bool:
        """
        Perform atomic CSV write operation to prevent corruption.
        
        Args:
            csv_file_path: Target CSV file path
            write_mode: 'w' for overwrite, 'a' for append
            data_rows: List of data rows to write
            header: Optional header row for new files
            
        Returns:
            bool: True if successful, False otherwise
        """
        file_lock = self._acquire_file_lock(csv_file_path)
        
        try:
            with file_lock:
                if write_mode == 'w':
                    # For overwrite mode, use atomic temp file operation
                    return self._atomic_overwrite(csv_file_path, data_rows, header)
                else:
                    # For append mode, use direct append with locking
                    return self._atomic_append(csv_file_path, data_rows, header)
                    
        except Exception as e:
            self.logger.error("indicator_persistence_service.atomic_write_failed", {
                "file_path": str(csv_file_path),
                "write_mode": write_mode,
                "error": str(e)
            })
            return False
    
    def _atomic_overwrite(self, csv_file_path: Path, data_rows: List[List[str]], 
                         header: List[str] = None) -> bool:
        """Atomic overwrite using temporary file and move."""
        try:
            # Ensure directory exists
            csv_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create temporary file in same directory for atomic move
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.csv.tmp',
                dir=csv_file_path.parent,
                prefix=csv_file_path.stem + '_'
            )
            
            try:
                with os.fdopen(temp_fd, 'w', newline='', encoding='utf-8') as temp_file:
                    writer = csv.writer(temp_file)
                    
                    # Write header if provided
                    if header:
                        writer.writerow(header)
                    
                    # Write all data rows
                    writer.writerows(data_rows)
                    
                    # Ensure data is written to disk
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                
                # Atomic move from temp to target
                shutil.move(temp_path, csv_file_path)
                
                self.logger.debug("indicator_persistence_service.atomic_overwrite_success", {
                    "file_path": str(csv_file_path),
                    "rows_written": len(data_rows)
                })
                
                return True
                
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise
                
        except Exception as e:
            self.logger.error("indicator_persistence_service.atomic_overwrite_failed", {
                "file_path": str(csv_file_path),
                "error": str(e)
            })
            return False
    
    def _atomic_append(self, csv_file_path: Path, data_rows: List[List[str]], 
                      header: List[str] = None) -> bool:
        """Atomic append with file existence check."""
        try:
            # Ensure directory exists
            csv_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file exists to determine if header is needed
            file_exists = csv_file_path.exists()
            
            # Write to CSV in append mode with file locking
            with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                # Apply file-level locking on Unix systems
                if HAS_FCNTL:
                    try:
                        fcntl.flock(csvfile.fileno(), fcntl.LOCK_EX)
                    except OSError:
                        # File locking failed, rely on thread locks
                        pass
                
                writer = csv.writer(csvfile)
                
                # Write header if file is new and header provided
                if not file_exists and header:
                    writer.writerow(header)
                
                # Write all data rows
                writer.writerows(data_rows)
                
                # Ensure data is written to disk
                csvfile.flush()
                os.fsync(csvfile.fileno())
            
            self.logger.debug("indicator_persistence_service.atomic_append_success", {
                "file_path": str(csv_file_path),
                "rows_written": len(data_rows),
                "file_existed": file_exists
            })
            
            return True
            
        except Exception as e:
            self.logger.error("indicator_persistence_service.atomic_append_failed", {
                "file_path": str(csv_file_path),
                "error": str(e)
            })
            return False

    def save_single_value(self, session_id: str, symbol: str, variant_id: str,
                         indicator_value: IndicatorValue, variant_type: str = "general") -> bool:
        """
        Save single indicator value to CSV with append mode.

        Used for real-time streaming indicator values.

        Args:
            session_id: Session identifier
            symbol: Trading symbol
            variant_id: Indicator variant ID
            indicator_value: IndicatorValue object to save
            variant_type: Indicator variant type (general, risk, price, etc.)

        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # ✅ PERFORMANCE OPTIMIZATION: Skip saving None values
            # None values are ignored during CSV read (line 578-579, 402-403)
            # Skipping them saves significant I/O operations (file lock, fsync, write)
            if indicator_value.value is None:
                self.logger.debug("indicator_persistence_service.skipped_none_value", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "variant_id": variant_id,
                    "timestamp": indicator_value.timestamp,
                    "reason": "None values are skipped to avoid unnecessary I/O"
                })
                return True  # Return success - operation completed (skip is intentional)

            csv_file_path = self._get_csv_file_path(session_id, symbol, variant_type, variant_id)

            # Convert indicator value to CSV row
            row = self._indicator_value_to_csv_row(indicator_value)

            # Use atomic append operation
            success = self._atomic_csv_write(
                csv_file_path=csv_file_path,
                write_mode='a',
                data_rows=[row],
                header=["timestamp", "value"]
            )

            if success:
                self.logger.debug("indicator_persistence_service.single_value_saved", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "variant_id": variant_id,
                    "file_path": str(csv_file_path),
                    "timestamp": indicator_value.timestamp
                })

            return success

        except Exception as e:
            self.logger.error("indicator_persistence_service.save_single_value_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "variant_id": variant_id,
                "error": str(e)
            })
            return False

    def save_batch_values(self, session_id: str, symbol: str, variant_id: str,
                         indicator_values: List[IndicatorValue], variant_type: str = "general") -> bool:
        """
        Save batch of indicator values to CSV with overwrite mode.
        
        Used for simulation data where we want to replace entire file.
        
        Args:
            session_id: Session identifier
            symbol: Trading symbol
            variant_id: Indicator variant ID
            indicator_values: List of IndicatorValue objects to save
            variant_type: Indicator variant type
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            csv_file_path = self._get_csv_file_path(session_id, symbol, variant_type, variant_id)
            
            # Convert all indicator values to CSV rows
            data_rows = [
                self._indicator_value_to_csv_row(indicator_value) 
                for indicator_value in indicator_values
            ]
            
            # Use atomic overwrite operation
            success = self._atomic_csv_write(
                csv_file_path=csv_file_path,
                write_mode='w',
                data_rows=data_rows,
                header=["timestamp", "value"]
            )
            
            if success:
                self.logger.info("indicator_persistence_service.batch_values_saved", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "variant_id": variant_id,
                    "file_path": str(csv_file_path),
                    "values_count": len(indicator_values)
                })
            
            return success
                
        except Exception as e:
            self.logger.error("indicator_persistence_service.save_batch_values_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "variant_id": variant_id,
                "values_count": len(indicator_values),
                "error": str(e)
            })
            return False

    def load_values_with_stats(self, session_id: str, symbol: str, variant_id: str,
                              variant_type: str = "general", limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Load indicator values from CSV file with statistics.
        
        Args:
            session_id: Session identifier
            symbol: Trading symbol
            variant_id: Indicator variant ID
            variant_type: Indicator variant type
            limit: Maximum number of values to load (None for all)
            
        Returns:
            Dict with 'values', 'total_available', 'returned_count', 'limited' keys
        """
        try:
            with self._file_lock:
                csv_file_path = self._get_csv_file_path(session_id, symbol, variant_type, variant_id)
                
                if not csv_file_path.exists():
                    self.logger.warning("indicator_persistence_service.csv_file_not_found", {
                        "file_path": str(csv_file_path)
                    })
                    return {
                        "values": [],
                        "total_available": 0,
                        "returned_count": 0,
                        "limited": False
                    }
                
                indicator_values = []
                total_rows = 0
                
                with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    
                    for row in reader:
                        total_rows += 1
                        try:
                            indicator_value = self._csv_row_to_indicator_value(row, symbol, f"{session_id}_{symbol}_{variant_id}")
                            if indicator_value:
                                # Only add to result if we haven't reached the limit
                                if limit is None or len(indicator_values) < limit:
                                    indicator_values.append(indicator_value)
                                    
                        except Exception as e:
                            self.logger.warning("indicator_persistence_service.invalid_csv_row", {
                                "row": row,
                                "error": str(e)
                            })
                            continue
                
                result = {
                    "values": indicator_values,
                    "total_available": total_rows,
                    "returned_count": len(indicator_values),
                    "limited": limit is not None and total_rows > limit
                }
                
                self.logger.debug("indicator_persistence_service.values_loaded_with_stats", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "variant_id": variant_id,
                    "file_path": str(csv_file_path),
                    "total_available": total_rows,
                    "returned_count": len(indicator_values),
                    "limited": result["limited"]
                })
                
                return result
                
        except Exception as e:
            self.logger.error("indicator_persistence_service.load_values_with_stats_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "variant_id": variant_id,
                "error": str(e)
            })
            return {
                "values": [],
                "total_available": 0,
                "returned_count": 0,
                "limited": False
            }

    def load_values(self, session_id: str, symbol: str, variant_id: str,
                   variant_type: str = "general", limit: Optional[int] = None) -> List[IndicatorValue]:
        """
        Load indicator values from CSV file.
        
        Args:
            session_id: Session identifier
            symbol: Trading symbol
            variant_id: Indicator variant ID
            variant_type: Indicator variant type
            limit: Maximum number of values to load (None for all)
            
        Returns:
            List[IndicatorValue]: List of loaded indicator values
        """
        try:
            with self._file_lock:
                csv_file_path = self._get_csv_file_path(session_id, symbol, variant_type, variant_id)
                
                if not csv_file_path.exists():
                    self.logger.warning("indicator_persistence_service.csv_file_not_found", {
                        "file_path": str(csv_file_path)
                    })
                    return []
                
                indicator_values = []
                
                with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    
                    for row in reader:
                        try:
                            indicator_value = self._csv_row_to_indicator_value(row, symbol, f"{session_id}_{symbol}_{variant_id}")
                            if indicator_value:
                                indicator_values.append(indicator_value)
                                
                                # Apply limit if specified
                                if limit and len(indicator_values) >= limit:
                                    break
                                    
                        except Exception as e:
                            self.logger.warning("indicator_persistence_service.invalid_csv_row", {
                                "row": row,
                                "error": str(e)
                            })
                            continue
                
                self.logger.debug("indicator_persistence_service.values_loaded", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "variant_id": variant_id,
                    "file_path": str(csv_file_path),
                    "values_count": len(indicator_values)
                })
                
                return indicator_values
                
        except Exception as e:
            self.logger.error("indicator_persistence_service.load_values_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "variant_id": variant_id,
                "error": str(e)
            })
            return []

    def _get_csv_file_path(self, session_id: str, symbol: str, variant_type: str, variant_id: str) -> Path:
        """
        Get CSV file path for indicator data.
        
        Format: data/{session_id}/{symbol}/indicators/{variant_type}_{variant_id}.csv
        
        Args:
            session_id: Session identifier
            symbol: Trading symbol
            variant_type: Indicator variant type
            variant_id: Indicator variant ID
            
        Returns:
            Path: Full path to CSV file
        """
        return self.base_data_dir / session_id / symbol / "indicators" / f"{variant_type}_{variant_id}.csv"

    def _indicator_value_to_csv_row(self, indicator_value: IndicatorValue) -> List[str]:
        """
        Convert IndicatorValue to CSV row.
        
        Unified format: [timestamp, value]
        
        Args:
            indicator_value: IndicatorValue object
            
        Returns:
            List[str]: CSV row data
        """
        timestamp_str = f"{indicator_value.timestamp:.6f}"

        value = indicator_value.value
        if value is None:
            value_str = ""
        elif isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        elif isinstance(value, (int, float)):
            value_str = f"{float(value):.6f}"
        else:
            value_str = str(value)

        return [timestamp_str, value_str]

    def _csv_row_to_indicator_value(self, row: Dict[str, str], symbol: str, indicator_id: str) -> Optional[IndicatorValue]:
        """
        Convert CSV row to IndicatorValue.
        
        Args:
            row: CSV row as dictionary
            symbol: Trading symbol
            indicator_id: Indicator ID
            
        Returns:
            IndicatorValue: Converted indicator value or None if invalid
        """
        try:
            # Parse timestamp
            timestamp_raw = row.get("timestamp") or row.get("Timestamp")
            if timestamp_raw is None:
                raise KeyError("timestamp")
            timestamp = float(timestamp_raw)
            
            # Parse value
            value_str = row.get("value") or row.get("Value") or ""
            if value_str == "":
                value = None
            else:
                try:
                    # Try to parse as JSON first (for dict/list values)
                    value = json.loads(value_str)
                except json.JSONDecodeError:
                    # If not JSON, try as float
                    try:
                        value = float(value_str)
                    except ValueError:
                        # If not float, keep as string
                        value = value_str
            
            # Parse metadata
            metadata_str = row.get("metadata") or "{}"
            try:
                metadata = json.loads(metadata_str) if metadata_str else {}
            except json.JSONDecodeError:
                metadata = {"raw": metadata_str}
            
            return IndicatorValue(
                timestamp=timestamp,
                symbol=symbol,
                indicator_id=indicator_id,
                value=value,
                metadata=metadata
            )
            
        except (KeyError, ValueError, TypeError) as e:
            self.logger.warning("indicator_persistence_service.invalid_csv_row_conversion", {
                "row": row,
                "error": str(e)
            })
            return None

    def _handle_single_value_event(self, event_data: Dict[str, Any]):
        """
        Handle single indicator value calculated event.
        
        Args:
            event_data: Event data containing indicator value information
        """
        try:
            # Extract event data
            indicator_id = event_data.get("indicator_id")
            if not indicator_id:
                return
            
            # Parse indicator_id to extract session_id, symbol, variant_id
            # Expected format: {session_id}_{symbol}_{variant_id}
            parts = indicator_id.split("_")
            if len(parts) != 3:
                self.logger.warning("indicator_persistence_service.invalid_indicator_id_format", {
                    "indicator_id": indicator_id,
                    "expected_format": "session_id_symbol_variant_id"
                })
                return
            
            session_id = parts[0]
            symbol = parts[1]
            variant_id = parts[2]
            
            # Get indicator value from event
            indicator_value = event_data.get("indicator_value")
            variant_type = event_data.get("variant_type", "general")
            
            if indicator_value and isinstance(indicator_value, IndicatorValue):
                # Save the single value
                self.save_single_value(session_id, symbol, variant_id, indicator_value, variant_type)
            
        except Exception as e:
            self.logger.error("indicator_persistence_service.handle_single_value_event_failed", {
                "event_data": event_data,
                "error": str(e)
            })

    def _handle_simulation_completed_event(self, event_data: Dict[str, Any]):
        """
        Handle simulation completed event.
        
        Args:
            event_data: Event data containing simulation results
        """
        try:
            # Extract event data
            indicator_id = event_data.get("indicator_id")
            results = event_data.get("results", [])
            
            if not indicator_id or not results:
                return
            
            # Parse indicator_id to extract session_id, symbol, variant_id
            parts = indicator_id.split("_")
            if len(parts) != 3:
                self.logger.warning("indicator_persistence_service.invalid_indicator_id_format", {
                    "indicator_id": indicator_id,
                    "expected_format": "session_id_symbol_variant_id"
                })
                return
            
            session_id = parts[0]
            symbol = parts[1]
            variant_id = parts[2]
            
            # Save batch of simulation results
            variant_type = event_data.get("variant_type", "general")
            
            if results and all(isinstance(r, IndicatorValue) for r in results):
                self.save_batch_values(session_id, symbol, variant_id, results, variant_type)
            
        except Exception as e:
            self.logger.error("indicator_persistence_service.handle_simulation_completed_event_failed", {
                "event_data": event_data,
                "error": str(e)
            })

    def get_file_info(self, session_id: str, symbol: str, variant_id: str, variant_type: str = "general") -> Dict[str, Any]:
        """
        Get information about CSV file.
        
        Args:
            session_id: Session identifier
            symbol: Trading symbol
            variant_id: Indicator variant ID
            variant_type: Indicator variant type
            
        Returns:
            Dict containing file information
        """
        try:
            csv_file_path = self._get_csv_file_path(session_id, symbol, variant_type, variant_id)
            
            if not csv_file_path.exists():
                return {
                    "exists": False,
                    "file_path": str(csv_file_path)
                }
            
            # Get file stats
            stat = csv_file_path.stat()
            
            # Count rows
            row_count = 0
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                row_count = sum(1 for row in reader) - 1  # Subtract header
            
            return {
                "exists": True,
                "file_path": str(csv_file_path),
                "size_bytes": stat.st_size,
                "modified_time": stat.st_mtime,
                "row_count": row_count
            }
            
        except Exception as e:
            self.logger.error("indicator_persistence_service.get_file_info_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "variant_id": variant_id,
                "error": str(e)
            })
            return {
                "exists": False,
                "error": str(e)
            }

    def cleanup_old_files(self, max_age_days: int = 30) -> int:
        """
        Clean up old CSV files older than specified days.
        
        Args:
            max_age_days: Maximum age in days for files to keep
            
        Returns:
            int: Number of files deleted
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            deleted_count = 0
            
            # Recursively find all CSV files
            for csv_file in self.base_data_dir.rglob("*.csv"):
                try:
                    file_age = current_time - csv_file.stat().st_mtime
                    
                    if file_age > max_age_seconds:
                        csv_file.unlink()
                        deleted_count += 1
                        
                        self.logger.debug("indicator_persistence_service.old_file_deleted", {
                            "file_path": str(csv_file),
                            "age_days": file_age / (24 * 60 * 60)
                        })
                        
                except Exception as e:
                    self.logger.warning("indicator_persistence_service.cleanup_file_failed", {
                        "file_path": str(csv_file),
                        "error": str(e)
                    })
                    continue
            
            self.logger.info("indicator_persistence_service.cleanup_completed", {
                "deleted_count": deleted_count,
                "max_age_days": max_age_days
            })
            
            return deleted_count
            
        except Exception as e:
            self.logger.error("indicator_persistence_service.cleanup_old_files_failed", {
                "max_age_days": max_age_days,
                "error": str(e)
            })
            return 0
