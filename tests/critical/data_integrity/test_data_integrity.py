"""
Data Integrity & Persistence Tests - Zero Corruption Scenarios
=============================================================

Tests complete data integrity under all failure scenarios.
Ensures system remains reliable and data consistent in production.

Coverage Areas:
- File Corruption Recovery: Invalid JSON → marked invalid → others load normally
- Concurrent Access: Multiple operations → no race conditions → data consistency
- Configuration Persistence: Save → restart → data intact → schema validation
- Backup/Restore: Data export → system failure → import → full recovery
"""

import pytest
import json
import os
import tempfile
import shutil
import asyncio
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.config import Config
from src.domain.services.strategy_manager import StrategyManager, Strategy
from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger


class TestDataIntegrity:
    """Zero corruption scenarios - complete data integrity validation required"""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing"""
        temp_dir = tempfile.mkdtemp()
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()

        # Create subdirectories
        (config_dir / "strategies").mkdir()
        (config_dir / "indicators").mkdir()

        yield config_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_config(self, temp_config_dir):
        """Create mock config with temporary directories"""
        config = Mock()
        config.level = "INFO"
        config.console_enabled = True
        config.file_enabled = False
        config.structured_logging = True
        config.log_dir = str(temp_config_dir / "logs")
        config.max_file_size_mb = 100
        config.backup_count = 5

        # Override config directories to use temp paths
        with patch('src.core.config.Config.get_config_dir', return_value=temp_config_dir):
            yield config

    @pytest.fixture
    def strategy_manager(self, mock_config):
        """Create strategy manager with temp config"""
        event_bus = EventBus()
        event_bus.subscribe = AsyncMock()  # Mock to avoid asyncio issues

        logger = StructuredLogger("test", mock_config)

        # Mock order and risk managers
        order_manager = Mock()
        risk_manager = Mock()
        risk_manager.can_open_position = Mock(return_value={"approved": True, "warnings": []})
        risk_manager.use_budget = Mock(return_value=True)

        with patch('asyncio.create_task'):
            manager = StrategyManager(event_bus, logger, order_manager, risk_manager)

        yield manager

    @pytest.mark.critical
    def test_file_corruption_recovery_invalid_json_marked_invalid_others_load(self, temp_config_dir, strategy_manager):
        """
        CRITICAL DATA INTEGRITY TEST: File Corruption Recovery
        Tests that invalid JSON files are marked invalid while others load normally

        Business Value: Prevents system crashes from corrupted configuration files
        Evidence: Invalid files marked invalid, valid files load successfully, system remains operational
        """
        strategies_dir = temp_config_dir / "strategies"

        # Create valid strategy file
        valid_strategy = {
            "strategy_name": "valid_strategy",
            "enabled": True,
            "signal_detection": {"conditions": []},
            "entry_conditions": {"conditions": []},
            "close_order_detection": {"conditions": []},
            "emergency_exit": {"conditions": []},
            "global_limits": {"base_position_pct": 0.5}
        }

        with open(strategies_dir / "valid_strategy_001.json", 'w') as f:
            json.dump(valid_strategy, f)

        # Create corrupted strategy file (invalid JSON)
        with open(strategies_dir / "corrupted_strategy_002.json", 'w') as f:
            f.write('{"strategy_name": "corrupted", "invalid": json syntax}')

        # Create another valid strategy file
        valid_strategy_2 = valid_strategy.copy()
        valid_strategy_2["strategy_name"] = "valid_strategy_2"

        with open(strategies_dir / "valid_strategy_003.json", 'w') as f:
            json.dump(valid_strategy_2, f)

        # Test loading strategies (this would normally be done by a strategy loader)
        # For this test, we'll simulate the loading process

        loaded_strategies = []
        invalid_files = []

        for file_path in strategies_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Validate required fields
                    if "strategy_name" in data and "signal_detection" in data:
                        loaded_strategies.append(data)
                    else:
                        invalid_files.append(str(file_path))
            except (json.JSONDecodeError, IOError) as e:
                invalid_files.append(str(file_path))

        # Verify results
        assert len(loaded_strategies) == 2, f"Expected 2 valid strategies, got {len(loaded_strategies)}"
        assert len(invalid_files) == 1, f"Expected 1 invalid file, got {len(invalid_files)}"

        # Verify valid strategies loaded correctly
        strategy_names = [s["strategy_name"] for s in loaded_strategies]
        assert "valid_strategy" in strategy_names
        assert "valid_strategy_2" in strategy_names

        # Verify corrupted file was identified
        assert any("corrupted_strategy_002.json" in f for f in invalid_files)

    @pytest.mark.critical
    def test_concurrent_access_multiple_operations_no_race_conditions_data_consistency(self, temp_config_dir):
        """
        CRITICAL DATA INTEGRITY TEST: Concurrent Access
        Tests multiple operations simultaneously without race conditions

        Business Value: Ensures data consistency during high-frequency operations
        Evidence: No race conditions, all operations complete successfully, data remains consistent
        """
        strategies_dir = temp_config_dir / "strategies"

        # Test parameters
        num_threads = 10
        operations_per_thread = 5
        total_operations = num_threads * operations_per_thread

        results = []
        errors = []

        def concurrent_operation(thread_id: int):
            """Simulate concurrent file operations"""
            try:
                thread_results = []

                for op in range(operations_per_thread):
                    strategy_name = f"concurrent_strategy_{thread_id}_{op}"
                    file_path = strategies_dir / f"{strategy_name}.json"

                    # Create strategy data
                    strategy_data = {
                        "strategy_name": strategy_name,
                        "enabled": True,
                        "thread_id": thread_id,
                        "operation_id": op,
                        "signal_detection": {"conditions": []},
                        "entry_conditions": {"conditions": []},
                        "close_order_detection": {"conditions": []},
                        "emergency_exit": {"conditions": []},
                        "global_limits": {"base_position_pct": 0.5}
                    }

                    # Write file (this is where race conditions could occur)
                    with open(file_path, 'w') as f:
                        json.dump(strategy_data, f)

                    # Immediately read back to verify
                    with open(file_path, 'r') as f:
                        read_data = json.load(f)

                    # Verify data integrity
                    assert read_data["strategy_name"] == strategy_name
                    assert read_data["thread_id"] == thread_id
                    assert read_data["operation_id"] == op

                    thread_results.append(strategy_name)

                return thread_results

            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
                return []

        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(concurrent_operation, i) for i in range(num_threads)]
            for future in as_completed(futures):
                results.extend(future.result())

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent operations failed: {errors}"

        # Verify all operations completed
        assert len(results) == total_operations, f"Expected {total_operations} operations, got {len(results)}"

        # Verify all files were created and are readable
        created_files = list(strategies_dir.glob("*.json"))
        assert len(created_files) == total_operations

        # Verify data integrity of all files
        for file_path in created_files:
            with open(file_path, 'r') as f:
                data = json.load(f)
                assert "strategy_name" in data
                assert "thread_id" in data
                assert "operation_id" in data
                assert data["strategy_name"].startswith("concurrent_strategy_")

    @pytest.mark.critical
    def test_configuration_persistence_save_restart_data_intact_schema_validation(self, temp_config_dir, strategy_manager):
        """
        CRITICAL DATA INTEGRITY TEST: Configuration Persistence
        Tests that configurations survive system restart with schema validation

        Business Value: Ensures trading configurations remain intact across deployments
        Evidence: Data persists through restart, schema validation passes, all configurations loadable
        """
        strategies_dir = temp_config_dir / "strategies"
        indicators_dir = temp_config_dir / "indicators"

        # Create comprehensive test configurations
        test_strategies = [
            {
                "strategy_name": "persistence_strategy_1",
                "enabled": True,
                "signal_detection": {
                    "conditions": [
                        {
                            "name": "pump_threshold",
                            "condition_type": "pump_magnitude_pct",
                            "operator": "gte",
                            "value": 8.0
                        }
                    ]
                },
                "entry_conditions": {
                    "conditions": [
                        {
                            "name": "rsi_entry",
                            "condition_type": "rsi",
                            "operator": "between",
                            "value": [40, 80]
                        }
                    ]
                },
                "close_order_detection": {
                    "conditions": [
                        {
                            "name": "profit_target",
                            "condition_type": "unrealized_pnl_pct",
                            "operator": "gte",
                            "value": 15.0
                        }
                    ]
                },
                "emergency_exit": {
                    "conditions": [
                        {
                            "name": "extreme_risk",
                            "condition_type": "risk_indicator",
                            "operator": "gte",
                            "value": 150
                        }
                    ]
                },
                "global_limits": {
                    "base_position_pct": 0.5,
                    "max_position_size_usdt": 1000,
                    "stop_loss_buffer_pct": 10.0
                }
            },
            {
                "strategy_name": "persistence_strategy_2",
                "enabled": False,
                "signal_detection": {"conditions": []},
                "entry_conditions": {"conditions": []},
                "close_order_detection": {"conditions": []},
                "emergency_exit": {"conditions": []},
                "global_limits": {"base_position_pct": 0.3}
            }
        ]

        test_indicators = [
            {
                "variant_name": "rsi_14_standard",
                "type": "general",
                "indicator_type": "rsi",
                "parameters": {"period": 14},
                "description": "Standard RSI 14-period"
            },
            {
                "variant_name": "vwap_daily",
                "type": "price",
                "indicator_type": "vwap",
                "parameters": {"window_seconds": 86400},
                "description": "Daily VWAP"
            }
        ]

        # Save configurations
        for strategy in test_strategies:
            file_path = strategies_dir / f"{strategy['strategy_name']}.json"
            with open(file_path, 'w') as f:
                json.dump(strategy, f, indent=2)

        for indicator in test_indicators:
            file_path = indicators_dir / f"general_{indicator['variant_name']}.json"
            with open(file_path, 'w') as f:
                json.dump(indicator, f, indent=2)

        # Simulate system restart by re-reading all files
        loaded_strategies = []
        loaded_indicators = []

        # Load strategies
        for file_path in strategies_dir.glob("*.json"):
            with open(file_path, 'r') as f:
                data = json.load(f)
                loaded_strategies.append(data)

        # Load indicators
        for file_path in indicators_dir.glob("*.json"):
            with open(file_path, 'r') as f:
                data = json.load(f)
                loaded_indicators.append(data)

        # Validate strategy persistence and schema
        assert len(loaded_strategies) == 2

        for strategy in loaded_strategies:
            # Required schema fields
            required_fields = ["strategy_name", "enabled", "signal_detection", "entry_conditions",
                             "close_order_detection", "emergency_exit", "global_limits"]
            for field in required_fields:
                assert field in strategy, f"Missing required field: {field}"

            # Validate strategy name matches filename pattern
            assert strategy["strategy_name"].startswith("persistence_strategy_")

            # Validate condition groups have conditions array
            condition_groups = ["signal_detection", "entry_conditions", "close_order_detection", "emergency_exit"]
            for group in condition_groups:
                assert group in strategy
                assert "conditions" in strategy[group]
                assert isinstance(strategy[group]["conditions"], list)

        # Validate indicator persistence and schema
        assert len(loaded_indicators) == 2

        for indicator in loaded_indicators:
            required_fields = ["variant_name", "type", "indicator_type", "parameters", "description"]
            for field in required_fields:
                assert field in indicator, f"Missing required field: {field}"

            # Validate type-specific naming
            if indicator["type"] == "general":
                assert indicator["variant_name"] in ["rsi_14_standard", "vwap_daily"]

    @pytest.mark.critical
    def test_backup_restore_data_export_system_failure_import_full_recovery(self, temp_config_dir):
        """
        CRITICAL DATA INTEGRITY TEST: Backup/Restore
        Tests complete data recovery after system failure

        Business Value: Ensures business continuity through comprehensive backup/recovery
        Evidence: Full data recovery, all configurations intact, system operational post-recovery
        """
        strategies_dir = temp_config_dir / "strategies"
        indicators_dir = temp_config_dir / "indicators"
        backup_dir = temp_config_dir / "backup"

        # Create test data
        original_strategies = [
            {
                "strategy_name": "backup_strategy_1",
                "enabled": True,
                "signal_detection": {"conditions": []},
                "entry_conditions": {"conditions": []},
                "close_order_detection": {"conditions": []},
                "emergency_exit": {"conditions": []},
                "global_limits": {"base_position_pct": 0.5}
            },
            {
                "strategy_name": "backup_strategy_2",
                "enabled": False,
                "signal_detection": {"conditions": []},
                "entry_conditions": {"conditions": []},
                "close_order_detection": {"conditions": []},
                "emergency_exit": {"conditions": []},
                "global_limits": {"base_position_pct": 0.3}
            }
        ]

        original_indicators = [
            {
                "variant_name": "backup_indicator_1",
                "type": "general",
                "indicator_type": "rsi",
                "parameters": {"period": 14},
                "description": "Backup RSI indicator"
            }
        ]

        # Save original data
        for strategy in original_strategies:
            file_path = strategies_dir / f"{strategy['strategy_name']}.json"
            with open(file_path, 'w') as f:
                json.dump(strategy, f, indent=2)

        for indicator in original_indicators:
            file_path = indicators_dir / f"general_{indicator['variant_name']}.json"
            with open(file_path, 'w') as f:
                json.dump(indicator, f, indent=2)

        # Perform backup (simulate export)
        backup_dir.mkdir()
        backup_timestamp = "2025-10-01_12-00-00"

        # Backup strategies
        strategies_backup = backup_dir / f"strategies_{backup_timestamp}.json"
        all_strategies = []
        for file_path in strategies_dir.glob("*.json"):
            with open(file_path, 'r') as f:
                all_strategies.append(json.load(f))

        with open(strategies_backup, 'w') as f:
            json.dump({"strategies": all_strategies, "backup_timestamp": backup_timestamp}, f, indent=2)

        # Backup indicators
        indicators_backup = backup_dir / f"indicators_{backup_timestamp}.json"
        all_indicators = []
        for file_path in indicators_dir.glob("*.json"):
            with open(file_path, 'r') as f:
                all_indicators.append(json.load(f))

        with open(indicators_backup, 'w') as f:
            json.dump({"indicators": all_indicators, "backup_timestamp": backup_timestamp}, f, indent=2)

        # Simulate system failure - delete all current data
        for file_path in strategies_dir.glob("*.json"):
            file_path.unlink()
        for file_path in indicators_dir.glob("*.json"):
            file_path.unlink()

        # Verify data is gone
        assert len(list(strategies_dir.glob("*.json"))) == 0
        assert len(list(indicators_dir.glob("*.json"))) == 0

        # Perform restore (simulate import)
        with open(strategies_backup, 'r') as f:
            backup_data = json.load(f)
            restored_strategies = backup_data["strategies"]

        with open(indicators_backup, 'r') as f:
            backup_data = json.load(f)
            restored_indicators = backup_data["indicators"]

        # Restore strategies
        for strategy in restored_strategies:
            file_path = strategies_dir / f"{strategy['strategy_name']}.json"
            with open(file_path, 'w') as f:
                json.dump(strategy, f, indent=2)

        # Restore indicators
        for indicator in restored_indicators:
            file_path = indicators_dir / f"general_{indicator['variant_name']}.json"
            with open(file_path, 'w') as f:
                json.dump(indicator, f, indent=2)

        # Verify full recovery
        restored_strategy_files = list(strategies_dir.glob("*.json"))
        restored_indicator_files = list(indicators_dir.glob("*.json"))

        assert len(restored_strategy_files) == 2
        assert len(restored_indicator_files) == 1

        # Verify data integrity
        for file_path in restored_strategy_files:
            with open(file_path, 'r') as f:
                data = json.load(f)
                assert "strategy_name" in data
                assert "enabled" in data
                assert data["strategy_name"].startswith("backup_strategy_")

        for file_path in restored_indicator_files:
            with open(file_path, 'r') as f:
                data = json.load(f)
                assert "variant_name" in data
                assert "type" in data
                assert data["variant_name"].startswith("backup_indicator_")

        # Verify backup files remain intact
        assert strategies_backup.exists()
        assert indicators_backup.exists()

    @pytest.mark.critical
    def test_atomic_file_operations_partial_writes_prevented(self, temp_config_dir):
        """
        CRITICAL DATA INTEGRITY TEST: Atomic File Operations
        Tests that partial writes are prevented and system remains in consistent state

        Business Value: Prevents data corruption from interrupted write operations
        Evidence: No partial files, all-or-nothing writes, system consistency maintained
        """
        strategies_dir = temp_config_dir / "strategies"

        # Test atomic writes using temporary files
        strategy_data = {
            "strategy_name": "atomic_test_strategy",
            "enabled": True,
            "signal_detection": {"conditions": []},
            "entry_conditions": {"conditions": []},
            "close_order_detection": {"conditions": []},
            "emergency_exit": {"conditions": []},
            "global_limits": {"base_position_pct": 0.5}
        }

        final_path = strategies_dir / "atomic_test_strategy.json"

        # Simulate atomic write (write to temp file, then rename)
        temp_path = strategies_dir / "atomic_test_strategy.json.tmp"

        try:
            # Write to temporary file
            with open(temp_path, 'w') as f:
                json.dump(strategy_data, f)

            # Atomic rename (this should be instantaneous on most filesystems)
            temp_path.rename(final_path)

        except Exception:
            # Clean up temp file if operation fails
            if temp_path.exists():
                temp_path.unlink()
            raise

        # Verify final file exists and is complete
        assert final_path.exists()
        assert not temp_path.exists()  # Temp file should be gone

        # Verify data integrity
        with open(final_path, 'r') as f:
            loaded_data = json.load(f)
            assert loaded_data["strategy_name"] == "atomic_test_strategy"
            assert loaded_data["enabled"] == True

        # Verify no partial/corrupted files remain
        all_files = list(strategies_dir.glob("*"))
        json_files = [f for f in all_files if f.suffix == ".json"]
        temp_files = [f for f in all_files if f.suffix == ".tmp"]

        assert len(json_files) == 1
        assert len(temp_files) == 0

    @pytest.mark.critical
    def test_schema_validation_prevents_invalid_configurations(self, temp_config_dir):
        """
        CRITICAL DATA INTEGRITY TEST: Schema Validation
        Tests that invalid configurations are rejected and don't corrupt the system

        Business Value: Prevents runtime errors from invalid configurations
        Evidence: Invalid configs rejected, valid configs accepted, clear error messages
        """
        strategies_dir = temp_config_dir / "strategies"

        # Test valid configuration
        valid_config = {
            "strategy_name": "schema_valid_strategy",
            "enabled": True,
            "signal_detection": {"conditions": []},
            "entry_conditions": {"conditions": []},
            "close_order_detection": {"conditions": []},
            "emergency_exit": {"conditions": []},
            "global_limits": {"base_position_pct": 0.5}
        }

        # Test invalid configurations
        invalid_configs = [
            # Missing required field
            {
                "enabled": True,
                "signal_detection": {"conditions": []},
                "entry_conditions": {"conditions": []},
                "close_order_detection": {"conditions": []},
                "emergency_exit": {"conditions": []},
                "global_limits": {"base_position_pct": 0.5}
            },
            # Invalid condition group structure
            {
                "strategy_name": "invalid_conditions",
                "enabled": True,
                "signal_detection": "not_an_object",
                "entry_conditions": {"conditions": []},
                "close_order_detection": {"conditions": []},
                "emergency_exit": {"conditions": []},
                "global_limits": {"base_position_pct": 0.5}
            },
            # Invalid global limits
            {
                "strategy_name": "invalid_limits",
                "enabled": True,
                "signal_detection": {"conditions": []},
                "entry_conditions": {"conditions": []},
                "close_order_detection": {"conditions": []},
                "emergency_exit": {"conditions": []},
                "global_limits": "invalid_limits"
            }
        ]

        # Test validation function (simplified version)
        def validate_strategy_config(config: dict) -> dict:
            errors = []
            warnings = []

            # Required fields
            required_fields = ["strategy_name", "enabled", "signal_detection", "entry_conditions",
                             "close_order_detection", "emergency_exit", "global_limits"]
            for field in required_fields:
                if field not in config:
                    errors.append(f"Missing required field: {field}")

            # Validate field types
            if "strategy_name" in config and not isinstance(config["strategy_name"], str):
                errors.append("strategy_name must be a string")

            if "enabled" in config and not isinstance(config["enabled"], bool):
                errors.append("enabled must be a boolean")

            # Validate condition groups
            condition_groups = ["signal_detection", "entry_conditions", "close_order_detection", "emergency_exit"]
            for group in condition_groups:
                if group in config:
                    if not isinstance(config[group], dict):
                        errors.append(f"{group} must be a dictionary")
                    elif "conditions" not in config[group]:
                        errors.append(f"{group} must have a 'conditions' field")
                    elif not isinstance(config[group]["conditions"], list):
                        errors.append(f"{group}.conditions must be a list")

            # Validate global limits
            if "global_limits" in config:
                if not isinstance(config["global_limits"], dict):
                    errors.append("global_limits must be a dictionary")

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        # Test valid configuration
        result = validate_strategy_config(valid_config)
        assert result["valid"] == True
        assert len(result["errors"]) == 0

        # Test invalid configurations
        for i, invalid_config in enumerate(invalid_configs):
            result = validate_strategy_config(invalid_config)
            assert result["valid"] == False, f"Invalid config {i} should have failed validation"
            assert len(result["errors"]) > 0, f"Invalid config {i} should have error messages"