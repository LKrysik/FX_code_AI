"""
BUG-008-8 Unit Tests: Session Lifecycle Tracking
=================================================
Story: BUG-008-8 - Session Lifecycle Tracking
Tests: Verify session states, validation, lookup, and audit logging

Acceptance Criteria:
- AC1: Sessions have explicit lifecycle states: CREATING, ACTIVE, STOPPED, DELETED
- AC2: Soft delete: deleted sessions remain queryable with include_deleted=true
- AC3: Session creation is atomic: either fully created or not at all
- AC4: "Session not found" response includes reason: never_existed, deleted, archived
- AC5: Session ID validation before queries (fail fast on invalid format)
- AC6: Audit log for session lifecycle transitions

Test Pattern: RED-GREEN-REFACTOR
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.domain.models.session_lifecycle import (
    SessionState,
    SessionLookupResult,
    SessionLookupReason,
    SessionAuditEntry,
    validate_session_id,
    is_valid_transition,
    VALID_STATE_TRANSITIONS
)


# ============================================================================
# AC1: Session Lifecycle States
# ============================================================================

class TestSessionStates:
    """Tests for AC1: Explicit session lifecycle states."""

    def test_session_state_values(self):
        """Verify all expected states are defined."""
        assert SessionState.CREATING.value == "creating"
        assert SessionState.ACTIVE.value == "active"
        assert SessionState.PAUSED.value == "paused"
        assert SessionState.STOPPED.value == "stopped"
        assert SessionState.DELETED.value == "deleted"

    def test_state_count(self):
        """Verify exactly 5 states are defined."""
        states = list(SessionState)
        assert len(states) == 5

    def test_state_enum_from_string(self):
        """Verify states can be created from string values."""
        assert SessionState("creating") == SessionState.CREATING
        assert SessionState("active") == SessionState.ACTIVE
        assert SessionState("deleted") == SessionState.DELETED


class TestStateTransitions:
    """Tests for valid state transitions."""

    def test_initial_transition_to_creating(self):
        """New session can only transition to CREATING."""
        assert is_valid_transition(None, SessionState.CREATING)
        assert not is_valid_transition(None, SessionState.ACTIVE)
        assert not is_valid_transition(None, SessionState.DELETED)

    def test_creating_to_active(self):
        """CREATING can only transition to ACTIVE."""
        assert is_valid_transition(SessionState.CREATING, SessionState.ACTIVE)
        assert not is_valid_transition(SessionState.CREATING, SessionState.STOPPED)
        assert not is_valid_transition(SessionState.CREATING, SessionState.DELETED)

    def test_active_transitions(self):
        """ACTIVE can transition to PAUSED, STOPPED, or DELETED."""
        assert is_valid_transition(SessionState.ACTIVE, SessionState.PAUSED)
        assert is_valid_transition(SessionState.ACTIVE, SessionState.STOPPED)
        assert is_valid_transition(SessionState.ACTIVE, SessionState.DELETED)
        assert not is_valid_transition(SessionState.ACTIVE, SessionState.CREATING)

    def test_paused_transitions(self):
        """PAUSED can transition to ACTIVE, STOPPED, or DELETED."""
        assert is_valid_transition(SessionState.PAUSED, SessionState.ACTIVE)
        assert is_valid_transition(SessionState.PAUSED, SessionState.STOPPED)
        assert is_valid_transition(SessionState.PAUSED, SessionState.DELETED)

    def test_stopped_transitions(self):
        """STOPPED can only transition to DELETED."""
        assert is_valid_transition(SessionState.STOPPED, SessionState.DELETED)
        assert not is_valid_transition(SessionState.STOPPED, SessionState.ACTIVE)
        assert not is_valid_transition(SessionState.STOPPED, SessionState.PAUSED)

    def test_deleted_is_terminal(self):
        """DELETED is a terminal state with no valid transitions."""
        assert not is_valid_transition(SessionState.DELETED, SessionState.ACTIVE)
        assert not is_valid_transition(SessionState.DELETED, SessionState.STOPPED)
        assert not is_valid_transition(SessionState.DELETED, SessionState.CREATING)


# ============================================================================
# AC5: Session ID Validation
# ============================================================================

class TestSessionIdValidation:
    """Tests for AC5: Session ID validation."""

    def test_valid_exec_session_id(self):
        """Valid exec_YYYYMMDD_HHMMSS_xxxxxxxx format."""
        assert validate_session_id("exec_20251230_143052_a1b2c3d4")
        assert validate_session_id("exec_20240101_000000_00000000")
        assert validate_session_id("exec_20251231_235959_ffffffff")

    def test_valid_paper_session_id(self):
        """Valid paper_YYYYMMDD_HHMMSS_xxxxxxxx format."""
        assert validate_session_id("paper_20251230_143052_a1b2c3d4")

    def test_valid_live_session_id(self):
        """Valid live_YYYYMMDD_HHMMSS_xxxxxxxx format."""
        assert validate_session_id("live_20251230_143052_a1b2c3d4")

    def test_valid_backtest_session_id(self):
        """Valid backtest_YYYYMMDD_HHMMSS_xxxxxxxx format."""
        assert validate_session_id("backtest_20251230_143052_a1b2c3d4")

    def test_invalid_empty_string(self):
        """Empty string is invalid."""
        assert not validate_session_id("")

    def test_invalid_none(self):
        """None is invalid."""
        assert not validate_session_id(None)

    def test_invalid_wrong_prefix(self):
        """Wrong prefix is invalid."""
        assert not validate_session_id("test_20251230_143052_a1b2c3d4")
        assert not validate_session_id("session_20251230_143052_a1b2c3d4")

    def test_invalid_short_date(self):
        """Short date format is invalid."""
        assert not validate_session_id("exec_2025123_143052_a1b2c3d4")

    def test_invalid_short_time(self):
        """Short time format is invalid."""
        assert not validate_session_id("exec_20251230_14305_a1b2c3d4")

    def test_invalid_short_hash(self):
        """Short hash is invalid."""
        assert not validate_session_id("exec_20251230_143052_a1b2c3")

    def test_invalid_uppercase_hash(self):
        """Uppercase hex is invalid (must be lowercase)."""
        assert not validate_session_id("exec_20251230_143052_A1B2C3D4")

    def test_invalid_non_hex_hash(self):
        """Non-hex characters in hash are invalid."""
        assert not validate_session_id("exec_20251230_143052_ghijklmn")


# ============================================================================
# AC4: Session Lookup Results
# ============================================================================

class TestSessionLookupResult:
    """Tests for AC4: Enhanced session lookup results."""

    def test_found_session_is_valid(self):
        """Found session with OK reason is valid."""
        result = SessionLookupResult(
            found=True,
            reason=SessionLookupReason.OK,
            session={"session_id": "test"}
        )
        assert result.is_valid
        assert result.found

    def test_deleted_session_not_valid(self):
        """Deleted session is found but not valid."""
        result = SessionLookupResult(
            found=True,
            reason=SessionLookupReason.DELETED,
            session={"session_id": "test"},
            deleted_at=datetime.now(timezone.utc)
        )
        assert result.found
        assert not result.is_valid

    def test_not_found_not_valid(self):
        """Not found session is not valid."""
        result = SessionLookupResult(
            found=False,
            reason=SessionLookupReason.NEVER_EXISTED
        )
        assert not result.found
        assert not result.is_valid

    def test_invalid_format_result(self):
        """Invalid format result."""
        result = SessionLookupResult(
            found=False,
            reason=SessionLookupReason.INVALID_FORMAT
        )
        assert not result.found
        assert result.reason == SessionLookupReason.INVALID_FORMAT

    def test_to_dict_includes_reason(self):
        """to_dict includes all fields."""
        result = SessionLookupResult(
            found=False,
            reason=SessionLookupReason.NEVER_EXISTED
        )
        d = result.to_dict()
        assert d["found"] is False
        assert d["reason"] == "never_existed"

    def test_to_dict_includes_deleted_at(self):
        """to_dict includes deleted_at when present."""
        now = datetime.now(timezone.utc)
        result = SessionLookupResult(
            found=True,
            reason=SessionLookupReason.DELETED,
            deleted_at=now
        )
        d = result.to_dict()
        assert "deleted_at" in d
        assert d["deleted_at"] == now.isoformat()


class TestSessionLookupReason:
    """Tests for lookup reason enum."""

    def test_all_reasons_defined(self):
        """Verify all expected reasons exist."""
        assert SessionLookupReason.OK.value == "ok"
        assert SessionLookupReason.INVALID_FORMAT.value == "invalid_format"
        assert SessionLookupReason.NEVER_EXISTED.value == "never_existed"
        assert SessionLookupReason.DELETED.value == "deleted"
        assert SessionLookupReason.ARCHIVED.value == "archived"


# ============================================================================
# AC6: Session Audit Log
# ============================================================================

class TestSessionAuditEntry:
    """Tests for AC6: Session audit logging."""

    def test_audit_entry_creation(self):
        """Audit entry captures all required fields."""
        entry = SessionAuditEntry(
            session_id="exec_20251230_143052_a1b2c3d4",
            timestamp=datetime.now(timezone.utc),
            old_state=SessionState.ACTIVE,
            new_state=SessionState.STOPPED,
            trigger="user_action",
            actor="user123",
            reason="User clicked stop button"
        )
        assert entry.session_id == "exec_20251230_143052_a1b2c3d4"
        assert entry.old_state == SessionState.ACTIVE
        assert entry.new_state == SessionState.STOPPED
        assert entry.trigger == "user_action"
        assert entry.actor == "user123"

    def test_audit_entry_to_dict(self):
        """Audit entry serializes correctly."""
        now = datetime.now(timezone.utc)
        entry = SessionAuditEntry(
            session_id="exec_20251230_143052_a1b2c3d4",
            timestamp=now,
            old_state=None,
            new_state=SessionState.CREATING,
            trigger="api_call",
            actor="system"
        )
        d = entry.to_dict()
        assert d["session_id"] == "exec_20251230_143052_a1b2c3d4"
        assert d["timestamp"] == now.isoformat()
        assert d["old_state"] is None
        assert d["new_state"] == "creating"
        assert d["trigger"] == "api_call"

    def test_audit_entry_metadata(self):
        """Audit entry includes metadata."""
        entry = SessionAuditEntry(
            session_id="exec_20251230_143052_a1b2c3d4",
            timestamp=datetime.now(timezone.utc),
            old_state=SessionState.ACTIVE,
            new_state=SessionState.STOPPED,
            trigger="error",
            actor="system",
            metadata={"error_code": 500, "message": "Connection lost"}
        )
        assert entry.metadata["error_code"] == 500
        assert "message" in entry.metadata


# ============================================================================
# Session Service Integration Tests
# ============================================================================

class TestSessionServiceLookup:
    """Integration tests for SessionService lookup methods."""

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        logger = MagicMock()
        logger.debug = MagicMock()
        logger.info = MagicMock()
        logger.warning = MagicMock()
        logger.error = MagicMock()
        return logger

    @pytest.fixture
    def mock_db_provider(self):
        """Create mock DB provider."""
        provider = MagicMock()
        provider.get_session_metadata = AsyncMock(return_value=None)
        return provider

    @pytest.fixture
    def mock_execution_controller(self):
        """Create mock execution controller."""
        controller = MagicMock()
        controller.get_execution_status = MagicMock(return_value=None)
        return controller

    @pytest.fixture
    def session_service(self, mock_execution_controller, mock_db_provider, mock_logger):
        """Create SessionService with mocks."""
        from src.domain.services.session_service import SessionService
        return SessionService(
            execution_controller=mock_execution_controller,
            db_provider=mock_db_provider,
            logger=mock_logger
        )

    @pytest.mark.asyncio
    async def test_lookup_invalid_session_id(self, session_service):
        """AC5: Invalid session ID returns INVALID_FORMAT immediately."""
        result = await session_service.lookup_session("invalid-id")

        assert not result.found
        assert result.reason == SessionLookupReason.INVALID_FORMAT

    @pytest.mark.asyncio
    async def test_lookup_never_existed(self, session_service, mock_db_provider):
        """AC4: Session not in DB returns NEVER_EXISTED."""
        mock_db_provider.get_session_metadata.return_value = None

        result = await session_service.lookup_session("exec_20251230_143052_a1b2c3d4")

        assert not result.found
        assert result.reason == SessionLookupReason.NEVER_EXISTED

    @pytest.mark.asyncio
    async def test_lookup_deleted_session_excluded_by_default(self, session_service, mock_db_provider):
        """AC2: Deleted sessions excluded by default."""
        mock_db_provider.get_session_metadata.return_value = {
            "session_id": "exec_20251230_143052_a1b2c3d4",
            "status": "stopped",
            "is_deleted": True,
            "deleted_at": datetime.now(timezone.utc)
        }

        result = await session_service.lookup_session("exec_20251230_143052_a1b2c3d4")

        assert not result.found
        assert result.reason == SessionLookupReason.DELETED

    @pytest.mark.asyncio
    async def test_lookup_deleted_session_included_when_requested(self, session_service, mock_db_provider):
        """AC2: Deleted sessions included when include_deleted=True."""
        mock_db_provider.get_session_metadata.return_value = {
            "session_id": "exec_20251230_143052_a1b2c3d4",
            "status": "stopped",
            "is_deleted": True,
            "deleted_at": datetime.now(timezone.utc)
        }

        result = await session_service.lookup_session(
            "exec_20251230_143052_a1b2c3d4",
            include_deleted=True
        )

        assert result.found
        assert result.reason == SessionLookupReason.DELETED

    @pytest.mark.asyncio
    async def test_lookup_active_session_from_controller(self, session_service, mock_execution_controller):
        """Active session found in controller."""
        mock_execution_controller.get_execution_status.return_value = {
            "session_id": "exec_20251230_143052_a1b2c3d4",
            "status": "running",
            "mode": "paper",
            "symbols": ["BTC_USDT"]
        }

        result = await session_service.lookup_session("exec_20251230_143052_a1b2c3d4")

        assert result.found
        assert result.reason == SessionLookupReason.OK
        assert result.session["is_active"]

    @pytest.mark.asyncio
    async def test_lookup_completed_session_from_db(self, session_service, mock_db_provider):
        """Completed session found in database."""
        mock_db_provider.get_session_metadata.return_value = {
            "session_id": "exec_20251230_143052_a1b2c3d4",
            "status": "completed",
            "symbols": ["BTC_USDT"],
            "is_deleted": False
        }

        result = await session_service.lookup_session("exec_20251230_143052_a1b2c3d4")

        assert result.found
        assert result.reason == SessionLookupReason.OK
        assert not result.session["is_active"]


class TestSessionServiceAuditLog:
    """Tests for SessionService audit logging."""

    @pytest.fixture
    def session_service(self):
        """Create SessionService with mocks."""
        from src.domain.services.session_service import SessionService
        return SessionService(
            execution_controller=MagicMock(),
            db_provider=MagicMock(),
            logger=MagicMock()
        )

    def test_log_state_transition(self, session_service):
        """AC6: State transition is logged."""
        entry = session_service.log_state_transition(
            session_id="exec_20251230_143052_a1b2c3d4",
            old_state=SessionState.ACTIVE,
            new_state=SessionState.STOPPED,
            trigger="user_action",
            actor="user123",
            reason="User stopped session"
        )

        assert entry.session_id == "exec_20251230_143052_a1b2c3d4"
        assert entry.old_state == SessionState.ACTIVE
        assert entry.new_state == SessionState.STOPPED
        session_service.logger.info.assert_called()

    def test_get_audit_log_all_entries(self, session_service):
        """AC6: Can retrieve all audit entries."""
        session_service.log_state_transition(
            session_id="session1",
            old_state=None,
            new_state=SessionState.CREATING,
            trigger="api_call",
            actor="system"
        )
        session_service.log_state_transition(
            session_id="session2",
            old_state=None,
            new_state=SessionState.CREATING,
            trigger="api_call",
            actor="system"
        )

        entries = session_service.get_session_audit_log()
        assert len(entries) == 2

    def test_get_audit_log_filtered_by_session(self, session_service):
        """AC6: Can filter audit log by session ID."""
        session_service.log_state_transition(
            session_id="session1",
            old_state=None,
            new_state=SessionState.CREATING,
            trigger="api_call",
            actor="system"
        )
        session_service.log_state_transition(
            session_id="session2",
            old_state=None,
            new_state=SessionState.CREATING,
            trigger="api_call",
            actor="system"
        )

        entries = session_service.get_session_audit_log(session_id="session1")
        assert len(entries) == 1
        assert entries[0]["session_id"] == "session1"

    def test_validate_state_transition_valid(self, session_service):
        """Validate valid state transition."""
        is_valid, error = session_service.validate_state_transition(
            session_id="test",
            current_state=SessionState.ACTIVE,
            target_state=SessionState.STOPPED
        )
        assert is_valid
        assert error is None

    def test_validate_state_transition_invalid(self, session_service):
        """Validate invalid state transition."""
        is_valid, error = session_service.validate_state_transition(
            session_id="test",
            current_state=SessionState.DELETED,
            target_state=SessionState.ACTIVE
        )
        assert not is_valid
        assert "Invalid state transition" in error


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_valid_transitions_coverage(self):
        """All states have defined transitions."""
        # None (initial) should have transitions
        assert None in VALID_STATE_TRANSITIONS

        # All enum states should have transitions defined
        for state in SessionState:
            assert state in VALID_STATE_TRANSITIONS

    def test_audit_entry_default_metadata(self):
        """Audit entry has empty dict as default metadata."""
        entry = SessionAuditEntry(
            session_id="test",
            timestamp=datetime.now(timezone.utc),
            old_state=None,
            new_state=SessionState.CREATING,
            trigger="test",
            actor="test"
        )
        assert entry.metadata == {}

    def test_session_id_validation_type_check(self):
        """Session ID validation handles non-string inputs."""
        assert not validate_session_id(12345)
        assert not validate_session_id(["exec_20251230_143052_a1b2c3d4"])
        assert not validate_session_id({"id": "exec_20251230_143052_a1b2c3d4"})
