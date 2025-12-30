"""
EventType Synchronization Tests
================================
Validates that EventType class in Python matches the shared event-types.json.
Ensures backend/frontend type definitions stay synchronized.

Part of COH-001-3: Create TypeScript EventType Definitions
"""

import json
import pytest
from pathlib import Path


class TestEventTypeSync:
    """Test that Python EventType class stays synchronized with shared definition"""

    @pytest.fixture
    def shared_event_types(self) -> set:
        """Load event types from shared JSON file"""
        shared_path = Path(__file__).parent.parent.parent / "shared" / "event-types.json"
        assert shared_path.exists(), f"Shared event types file not found: {shared_path}"

        with open(shared_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return set(data["eventTypes"])

    @pytest.fixture
    def python_event_types(self) -> set:
        """Extract all EventType class attribute values from Python"""
        from src.core.events import EventType

        # Get all uppercase class attributes (constants)
        return {
            getattr(EventType, attr)
            for attr in dir(EventType)
            if attr.isupper() and not attr.startswith("_")
        }

    def test_event_types_synchronized(
        self, shared_event_types: set, python_event_types: set
    ):
        """
        Verify Python EventType class matches shared JSON definition.

        AC4: Adding new event requires update in both places (with CI check)
        """
        # Find differences
        in_shared_only = shared_event_types - python_event_types
        in_python_only = python_event_types - shared_event_types

        errors = []

        if in_shared_only:
            errors.append(
                f"Event types in shared/event-types.json but NOT in Python EventType class:\n"
                f"  {sorted(in_shared_only)}\n"
                f"  → Add these to src/core/events.py EventType class"
            )

        if in_python_only:
            errors.append(
                f"Event types in Python EventType class but NOT in shared/event-types.json:\n"
                f"  {sorted(in_python_only)}\n"
                f"  → Add these to shared/event-types.json"
            )

        assert not errors, "\n\n".join(errors)

    def test_event_types_count_matches(
        self, shared_event_types: set, python_event_types: set
    ):
        """Verify the count of event types matches between shared JSON and Python"""
        assert len(shared_event_types) == len(python_event_types), (
            f"Event type count mismatch: "
            f"shared={len(shared_event_types)}, python={len(python_event_types)}"
        )

    def test_shared_json_structure(self):
        """Validate the structure of shared event-types.json"""
        shared_path = Path(__file__).parent.parent.parent / "shared" / "event-types.json"

        with open(shared_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Required fields
        assert "eventTypes" in data, "Missing 'eventTypes' array"
        assert isinstance(data["eventTypes"], list), "'eventTypes' must be an array"
        assert len(data["eventTypes"]) > 0, "'eventTypes' cannot be empty"

        # All items should be strings following naming convention
        for event_type in data["eventTypes"]:
            assert isinstance(event_type, str), f"Event type must be string: {event_type}"
            assert "." in event_type, f"Event type should follow category.action format: {event_type}"

        # No duplicates
        assert len(data["eventTypes"]) == len(set(data["eventTypes"])), "Duplicate event types found"

    def test_categories_cover_all_types(self):
        """Verify categories in JSON cover all event types (if present)"""
        shared_path = Path(__file__).parent.parent.parent / "shared" / "event-types.json"

        with open(shared_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "categories" not in data:
            pytest.skip("No categories defined in shared JSON")

        all_types = set(data["eventTypes"])
        categorized_types = set()

        for category, types in data["categories"].items():
            categorized_types.update(types)

        uncategorized = all_types - categorized_types
        if uncategorized:
            pytest.fail(f"Event types not in any category: {sorted(uncategorized)}")

    def test_all_category_entries_are_valid(self):
        """Verify all entries in categories are valid event types"""
        shared_path = Path(__file__).parent.parent.parent / "shared" / "event-types.json"

        with open(shared_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "categories" not in data:
            pytest.skip("No categories defined in shared JSON")

        all_types = set(data["eventTypes"])
        invalid_entries = []

        for category, types in data["categories"].items():
            for event_type in types:
                if event_type not in all_types:
                    invalid_entries.append(f"{category}: {event_type}")

        if invalid_entries:
            pytest.fail(f"Category entries not in eventTypes: {invalid_entries}")
