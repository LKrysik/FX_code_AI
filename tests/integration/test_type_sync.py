"""
Test Type Synchronization
=========================
Validates that MessageType enum in Python matches the shared message-types.json.
Ensures backend/frontend type definitions stay synchronized.

Part of COH-001-1: Synchronize MessageType Definitions
"""

import json
import pytest
from pathlib import Path


class TestMessageTypeSync:
    """Test that Python MessageType enum stays synchronized with shared definition"""

    @pytest.fixture
    def shared_message_types(self) -> set:
        """Load message types from shared JSON file"""
        shared_path = Path(__file__).parent.parent.parent / "shared" / "message-types.json"
        assert shared_path.exists(), f"Shared message types file not found: {shared_path}"

        with open(shared_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return set(data["messageTypes"])

    @pytest.fixture
    def python_message_types(self) -> set:
        """Extract all MessageType enum values from Python"""
        from src.api.message_router import MessageType
        return {mt.value for mt in MessageType}

    def test_message_types_synchronized(
        self, shared_message_types: set, python_message_types: set
    ):
        """
        Verify Python MessageType enum matches shared JSON definition.

        AC3: TypeScript compilation fails if types are out of sync
        (This test ensures Python side is validated; frontend has corresponding Jest test)
        """
        # Find differences
        in_shared_only = shared_message_types - python_message_types
        in_python_only = python_message_types - shared_message_types

        errors = []

        if in_shared_only:
            errors.append(
                f"Message types in shared/message-types.json but NOT in Python MessageType enum:\n"
                f"  {sorted(in_shared_only)}\n"
                f"  → Add these to src/api/message_router.py MessageType class"
            )

        if in_python_only:
            errors.append(
                f"Message types in Python MessageType enum but NOT in shared/message-types.json:\n"
                f"  {sorted(in_python_only)}\n"
                f"  → Add these to shared/message-types.json"
            )

        assert not errors, "\n\n".join(errors)

    def test_message_types_count_matches(
        self, shared_message_types: set, python_message_types: set
    ):
        """Verify the count of message types matches between shared JSON and Python"""
        assert len(shared_message_types) == len(python_message_types), (
            f"Message type count mismatch: "
            f"shared={len(shared_message_types)}, python={len(python_message_types)}"
        )

    def test_shared_json_structure(self):
        """Validate the structure of shared message-types.json"""
        shared_path = Path(__file__).parent.parent.parent / "shared" / "message-types.json"

        with open(shared_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Required fields
        assert "messageTypes" in data, "Missing 'messageTypes' array"
        assert isinstance(data["messageTypes"], list), "'messageTypes' must be an array"
        assert len(data["messageTypes"]) > 0, "'messageTypes' cannot be empty"

        # All items should be strings
        for msg_type in data["messageTypes"]:
            assert isinstance(msg_type, str), f"Message type must be string: {msg_type}"
            assert msg_type == msg_type.lower(), f"Message type should be lowercase: {msg_type}"

        # No duplicates
        assert len(data["messageTypes"]) == len(set(data["messageTypes"])), "Duplicate message types found"

    def test_categories_cover_all_types(self):
        """Verify categories in JSON cover all message types (if present)"""
        shared_path = Path(__file__).parent.parent.parent / "shared" / "message-types.json"

        with open(shared_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "categories" not in data:
            pytest.skip("No categories defined in shared JSON")

        all_types = set(data["messageTypes"])
        categorized_types = set()

        for category, types in data["categories"].items():
            categorized_types.update(types)

        uncategorized = all_types - categorized_types
        if uncategorized:
            pytest.fail(f"Message types not in any category: {sorted(uncategorized)}")
