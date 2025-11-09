"""
Test EventBus logging configuration and functionality.

Verifies that:
1. configure_module_logger() creates dedicated log files
2. EventBus logs are written to logs/event_bus.jsonl
3. Log format is valid JSONL
4. Idempotency: multiple calls don't create duplicate handlers
"""

import pytest
import asyncio
import json
import os
import tempfile
import shutil
from pathlib import Path
from src.core.event_bus import EventBus
from src.core.logger import configure_module_logger


class TestEventBusLogging:
    """Test EventBus logging configuration."""

    def setup_method(self):
        """Create temporary log directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "event_bus.jsonl")

    def teardown_method(self):
        """Clean up temporary directory."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_configure_module_logger_creates_file(self):
        """Test that configure_module_logger creates log file."""
        logger = configure_module_logger(
            module_name="test.event_bus",
            log_file=self.log_file,
            level="DEBUG",
            console_enabled=False
        )

        # Write a log message
        logger.info("Test message")

        # Verify file was created
        assert os.path.exists(self.log_file), "Log file should be created"

        # Verify content is valid JSON
        with open(self.log_file, 'r', encoding='utf-8') as f:
            line = f.readline()
            log_entry = json.loads(line)
            assert log_entry["message"] == "Test message"
            assert log_entry["level"] == "INFO"
            assert log_entry["module"] == "test_event_bus_logging"

    def test_configure_module_logger_idempotent(self):
        """Test that calling configure_module_logger twice doesn't duplicate handlers."""
        # Configure logger twice
        logger1 = configure_module_logger(
            module_name="test.event_bus.idempotent",
            log_file=self.log_file,
            level="DEBUG"
        )

        logger2 = configure_module_logger(
            module_name="test.event_bus.idempotent",
            log_file=self.log_file,
            level="DEBUG"
        )

        # Both should return the same logger instance
        assert logger1 is logger2

        # Write one message
        logger1.info("Single message")

        # Verify only one entry in log (not duplicated)
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 1, "Should only have 1 log entry, not duplicated"

    @pytest.mark.asyncio
    async def test_eventbus_logs_to_configured_file(self):
        """Test that EventBus actually logs to the configured file."""
        # Configure logger for EventBus
        configure_module_logger(
            module_name="src.core.event_bus",
            log_file=self.log_file,
            level="DEBUG",
            console_enabled=False
        )

        # Create EventBus and perform operations
        bus = EventBus()

        received = []

        async def handler(data):
            received.append(data)

        await bus.subscribe("test_topic", handler)
        await bus.publish("test_topic", {"value": 123})

        # Wait for async processing
        await asyncio.sleep(0.2)

        await bus.shutdown()

        # Verify log file exists
        assert os.path.exists(self.log_file), "Log file should exist"

        # Verify log entries
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) > 0, "Should have log entries"

            # Parse and verify JSONL format
            log_entries = [json.loads(line) for line in lines]

            # Check for expected log messages
            messages = [entry.get("message", "") for entry in log_entries]

            # EventBus should log initialization
            assert any("EventBus initialized" in msg for msg in messages), \
                "Should log EventBus initialization"

            # EventBus should log subscription
            assert any("Subscribed to" in msg for msg in messages), \
                "Should log subscription"

            # EventBus should log publishing
            assert any("Publishing to" in msg for msg in messages), \
                "Should log publishing"

    @pytest.mark.asyncio
    async def test_eventbus_log_levels(self):
        """Test that EventBus respects DEBUG level and logs all operations."""
        configure_module_logger(
            module_name="src.core.event_bus",
            log_file=self.log_file,
            level="DEBUG",
            console_enabled=False
        )

        bus = EventBus()

        async def handler(data):
            pass

        await bus.subscribe("test", handler)
        await bus.publish("test", {"data": "value"})
        await asyncio.sleep(0.1)

        # Read log file
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            log_entries = [json.loads(line) for line in lines]

            # Check that we have DEBUG level logs
            levels = [entry.get("level") for entry in log_entries]
            assert "DEBUG" in levels, "Should have DEBUG level logs"
            assert "INFO" in levels, "Should have INFO level logs"

    def test_configure_module_logger_without_file(self):
        """Test that configure_module_logger handles directory creation."""
        # Use nested directory that doesn't exist
        nested_log_file = os.path.join(self.temp_dir, "nested", "dir", "event_bus.jsonl")

        logger = configure_module_logger(
            module_name="test.nested",
            log_file=nested_log_file,
            level="INFO"
        )

        logger.info("Test message")

        # Verify nested directories were created
        assert os.path.exists(nested_log_file), "Nested log file should be created"

    @pytest.mark.asyncio
    async def test_eventbus_logs_shutdown(self):
        """Test that EventBus logs shutdown operations."""
        configure_module_logger(
            module_name="src.core.event_bus",
            log_file=self.log_file,
            level="INFO",
            console_enabled=False
        )

        bus = EventBus()
        await bus.shutdown()

        # Verify shutdown was logged
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            log_entries = [json.loads(line) for line in lines]
            messages = [entry.get("message", "") for entry in log_entries]

            assert any("EventBus shutdown initiated" in msg for msg in messages), \
                "Should log shutdown initiation"
            assert any("EventBus shutdown completed" in msg for msg in messages), \
                "Should log shutdown completion"

    def test_json_formatter_handles_dict_messages(self):
        """Test that JsonFormatter handles dict messages correctly."""
        logger = configure_module_logger(
            module_name="test.json_format",
            log_file=self.log_file,
            level="INFO"
        )

        # Log a dict message (common in structured logging)
        test_dict = {"event": "test_event", "value": 42, "nested": {"key": "value"}}
        logger.info(test_dict)

        # Verify it was logged correctly
        with open(self.log_file, 'r', encoding='utf-8') as f:
            line = f.readline()
            log_entry = json.loads(line)

            # Should have flattened the dict into the log entry
            assert "event" in log_entry or "message" in log_entry
            assert log_entry["level"] == "INFO"
