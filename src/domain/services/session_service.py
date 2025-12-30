"""
Unified Session Lookup Service

✅ SESSION-003 FIX: Provides consistent session lookup across all endpoints
✅ BUG-008-8: Session Lifecycle Tracking with enhanced lookup and validation

This service centralizes session lookups to prevent inconsistent behavior:
- Before: Different endpoints used different lookup strategies
- After: Single service with unified lookup logic

BUG-008-8 Enhancements:
- Session ID validation before queries (AC5)
- Enhanced "not found" responses with reasons (AC4)
- Session audit logging (AC6)

Lookup Strategy:
1. Validate session ID format first
2. Check ExecutionController (for active/running sessions)
3. Check QuestDB (for completed/stopped sessions)
4. Return detailed lookup result with reason
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from src.domain.models.session_lifecycle import (
    SessionState,
    SessionLookupResult,
    SessionLookupReason,
    SessionAuditEntry,
    validate_session_id,
    is_valid_transition
)


class SessionService:
    """
    Unified session management service.

    Provides consistent session lookup across all API endpoints,
    preventing "session not found" errors caused by inconsistent lookup strategies.
    """

    def __init__(
        self,
        execution_controller,
        db_provider,
        logger
    ):
        """
        Initialize session service.

        Args:
            execution_controller: ExecutionController instance
            db_provider: QuestDB data provider for database queries
            logger: Structured logger instance
        """
        self.execution_controller = execution_controller
        self.db_provider = db_provider
        self.logger = logger

        # BUG-008-8 AC6: Audit log for session lifecycle transitions
        self._audit_log: List[SessionAuditEntry] = []
        self._max_audit_entries = 1000  # Keep last 1000 entries in memory

    async def get_session(self, session_id: str, include_controller_status: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get session by ID using unified lookup strategy.

        Strategy:
        1. Check ExecutionController for active session
        2. If not found or not matching, check QuestDB
        3. Return None if session doesn't exist

        Args:
            session_id: Session ID to lookup
            include_controller_status: If True, include controller execution status when available

        Returns:
            Session dictionary with metadata, or None if not found
        """
        session_data = None
        found_in = None

        # Step 1: Check ExecutionController (for currently active session)
        if self.execution_controller:
            controller_status = self.execution_controller.get_execution_status()

            if controller_status and controller_status.get("session_id") == session_id:
                # Session is actively running in controller
                session_data = {
                    "session_id": session_id,
                    "status": controller_status.get("status", "running"),
                    "mode": controller_status.get("mode"),
                    "symbols": controller_status.get("symbols", []),
                    "start_time": controller_status.get("start_time"),
                    "source": "controller",
                    "is_active": True
                }

                if include_controller_status:
                    session_data["controller_status"] = controller_status

                found_in = "controller"

        # Step 2: If not found in controller, check QuestDB (for completed/stopped sessions)
        if not session_data:
            try:
                db_session = await self.db_provider.get_session_metadata(session_id)

                if db_session:
                    session_data = {
                        "session_id": db_session.get("session_id"),
                        "status": db_session.get("status", "completed"),
                        "symbols": db_session.get("symbols", []),
                        "data_types": db_session.get("data_types", []),
                        "start_time": db_session.get("start_time"),
                        "end_time": db_session.get("end_time"),
                        "records_collected": db_session.get("records_collected", 0),
                        "prices_count": db_session.get("prices_count", 0),
                        "orderbook_count": db_session.get("orderbook_count", 0),
                        "created_at": db_session.get("created_at"),
                        "source": "database",
                        "is_active": False
                    }
                    found_in = "database"

            except Exception as e:
                self.logger.error("session_service.db_lookup_failed", {
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                # Don't propagate DB errors - just return None
                return None

        if session_data:
            self.logger.debug("session_service.session_found", {
                "session_id": session_id,
                "found_in": found_in,
                "status": session_data.get("status")
            })
        else:
            self.logger.debug("session_service.session_not_found", {
                "session_id": session_id
            })

        return session_data

    async def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists (in controller or database).

        Args:
            session_id: Session ID to check

        Returns:
            True if session exists, False otherwise
        """
        session = await self.get_session(session_id, include_controller_status=False)
        return session is not None

    async def is_session_active(self, session_id: str) -> bool:
        """
        Check if a session is currently active in ExecutionController.

        Args:
            session_id: Session ID to check

        Returns:
            True if session is active in controller, False otherwise
        """
        if not self.execution_controller:
            return False

        controller_status = self.execution_controller.get_execution_status()
        return (
            controller_status is not None and
            controller_status.get("session_id") == session_id
        )

    async def list_sessions(
        self,
        limit: int = 50,
        include_active: bool = True,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List sessions from database, optionally including the currently active session.

        Args:
            limit: Maximum sessions to return
            include_active: If True, include active controller session at the top
            status_filter: Optional status filter (running, completed, stopped, failed)

        Returns:
            List of session dictionaries
        """
        sessions = []

        # Step 1: Get sessions from QuestDB
        try:
            db_sessions = await self.db_provider.get_sessions_list(
                limit=limit,
                status_filter=status_filter
            )

            for db_session in db_sessions:
                sessions.append({
                    "session_id": db_session.get("session_id"),
                    "status": db_session.get("status", "completed"),
                    "symbols": db_session.get("symbols", []),
                    "data_types": db_session.get("data_types", []),
                    "start_time": db_session.get("start_time"),
                    "end_time": db_session.get("end_time"),
                    "records_collected": db_session.get("records_collected", 0),
                    "prices_count": db_session.get("prices_count", 0),
                    "orderbook_count": db_session.get("orderbook_count", 0),
                    "created_at": db_session.get("created_at"),
                    "source": "database",
                    "is_active": False
                })

        except Exception as e:
            self.logger.error("session_service.list_sessions_db_failed", {
                "limit": limit,
                "status_filter": status_filter,
                "error": str(e),
                "error_type": type(e).__name__
            })
            # Continue with empty list - don't fail entire request

        # Step 2: Add active controller session if requested and not already in list
        if include_active and self.execution_controller:
            controller_status = self.execution_controller.get_execution_status()

            if controller_status:
                active_session_id = controller_status.get("session_id")

                # Check if already in list from DB
                already_included = any(s["session_id"] == active_session_id for s in sessions)

                if not already_included:
                    # Prepend active session to list
                    active_session = {
                        "session_id": active_session_id,
                        "status": controller_status.get("status", "running"),
                        "mode": controller_status.get("mode"),
                        "symbols": controller_status.get("symbols", []),
                        "start_time": controller_status.get("start_time"),
                        "source": "controller",
                        "is_active": True
                    }
                    sessions.insert(0, active_session)

        self.logger.debug("session_service.list_sessions", {
            "total_sessions": len(sessions),
            "limit": limit,
            "status_filter": status_filter
        })

        return sessions

    async def validate_session_for_operation(
        self,
        session_id: str,
        allowed_statuses: Optional[List[str]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that a session exists and is in an appropriate status for an operation.

        Args:
            session_id: Session ID to validate
            allowed_statuses: List of allowed statuses (e.g., ["running", "paused"])
                             If None, any existing session is valid

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, error_message) if invalid
        """
        session = await self.get_session(session_id, include_controller_status=False)

        if not session:
            return (False, f"Session {session_id} not found")

        if allowed_statuses:
            current_status = session.get("status")
            if current_status not in allowed_statuses:
                return (
                    False,
                    f"Session {session_id} is {current_status}, "
                    f"expected one of: {', '.join(allowed_statuses)}"
                )

        return (True, None)

    # =========================================================================
    # BUG-008-8: Enhanced Session Lookup with Validation
    # =========================================================================

    async def lookup_session(
        self,
        session_id: str,
        include_deleted: bool = False
    ) -> SessionLookupResult:
        """
        BUG-008-8 AC4, AC5: Enhanced session lookup with validation and reason.

        This method provides:
        - Session ID format validation before database queries
        - Clear reason when session is not found
        - Distinction between "never existed" vs "deleted" vs "invalid format"

        Args:
            session_id: Session ID to lookup
            include_deleted: If True, returns deleted sessions too

        Returns:
            SessionLookupResult with found status, reason, and session data
        """
        # AC5: Validate session ID format first (fail fast)
        if not validate_session_id(session_id):
            self.logger.warning("session_service.invalid_session_id_format", {
                "session_id": session_id,
                "reason": "format_validation_failed"
            })
            return SessionLookupResult(
                found=False,
                reason=SessionLookupReason.INVALID_FORMAT
            )

        # Check ExecutionController first (for active sessions)
        if self.execution_controller:
            controller_status = self.execution_controller.get_execution_status()

            if controller_status and controller_status.get("session_id") == session_id:
                session_data = {
                    "session_id": session_id,
                    "status": controller_status.get("status", "running"),
                    "state": SessionState.ACTIVE.value,
                    "mode": controller_status.get("mode"),
                    "symbols": controller_status.get("symbols", []),
                    "start_time": controller_status.get("start_time"),
                    "source": "controller",
                    "is_active": True
                }
                return SessionLookupResult(
                    found=True,
                    reason=SessionLookupReason.OK,
                    session=session_data
                )

        # Check database (with or without deleted sessions)
        try:
            db_session = await self.db_provider.get_session_metadata(
                session_id,
                include_deleted=include_deleted
            )

            if db_session:
                # Check if session is deleted
                is_deleted = db_session.get("is_deleted", False)
                deleted_at = db_session.get("deleted_at")

                if is_deleted and not include_deleted:
                    return SessionLookupResult(
                        found=False,
                        reason=SessionLookupReason.DELETED,
                        deleted_at=deleted_at
                    )

                session_data = {
                    "session_id": db_session.get("session_id"),
                    "status": db_session.get("status", "completed"),
                    "state": self._map_status_to_state(db_session.get("status"), is_deleted),
                    "symbols": db_session.get("symbols", []),
                    "data_types": db_session.get("data_types", []),
                    "start_time": db_session.get("start_time"),
                    "end_time": db_session.get("end_time"),
                    "records_collected": db_session.get("records_collected", 0),
                    "created_at": db_session.get("created_at"),
                    "is_deleted": is_deleted,
                    "deleted_at": deleted_at,
                    "source": "database",
                    "is_active": False
                }

                reason = SessionLookupReason.DELETED if is_deleted else SessionLookupReason.OK

                return SessionLookupResult(
                    found=True,
                    reason=reason,
                    session=session_data,
                    deleted_at=deleted_at
                )

            # Session not found in database
            self.logger.debug("session_service.session_never_existed", {
                "session_id": session_id
            })
            return SessionLookupResult(
                found=False,
                reason=SessionLookupReason.NEVER_EXISTED
            )

        except Exception as e:
            # BUG-008-8 AC3: Never log empty error messages
            error_msg = str(e) if str(e) else type(e).__name__
            self.logger.error("session_service.lookup_failed", {
                "session_id": session_id,
                "error": error_msg,
                "error_type": type(e).__name__
            })
            # Return "never existed" on DB error (graceful degradation)
            return SessionLookupResult(
                found=False,
                reason=SessionLookupReason.NEVER_EXISTED
            )

    def _map_status_to_state(self, status: Optional[str], is_deleted: bool) -> str:
        """Map legacy status to SessionState."""
        if is_deleted:
            return SessionState.DELETED.value

        status_mapping = {
            "active": SessionState.ACTIVE.value,
            "running": SessionState.ACTIVE.value,
            "paused": SessionState.PAUSED.value,
            "completed": SessionState.STOPPED.value,
            "stopped": SessionState.STOPPED.value,
            "failed": SessionState.STOPPED.value,
            "creating": SessionState.CREATING.value,
        }
        return status_mapping.get(status, SessionState.STOPPED.value)

    # =========================================================================
    # BUG-008-8: Session Audit Logging (AC6)
    # =========================================================================

    def log_state_transition(
        self,
        session_id: str,
        old_state: Optional[SessionState],
        new_state: SessionState,
        trigger: str,
        actor: str = "system",
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionAuditEntry:
        """
        BUG-008-8 AC6: Log session state transition to audit log.

        Args:
            session_id: Session ID
            old_state: Previous state (None for new sessions)
            new_state: New state
            trigger: What triggered the transition
            actor: Who/what performed the action
            reason: Optional reason for transition
            metadata: Additional context

        Returns:
            Created audit entry
        """
        entry = SessionAuditEntry(
            session_id=session_id,
            timestamp=datetime.now(timezone.utc),
            old_state=old_state,
            new_state=new_state,
            trigger=trigger,
            actor=actor,
            reason=reason,
            metadata=metadata or {}
        )

        # Add to in-memory audit log
        self._audit_log.append(entry)

        # Trim if exceeds max
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries:]

        # Log the transition
        self.logger.info("session_service.state_transition", entry.to_dict())

        return entry

    def get_session_audit_log(
        self,
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit log entries, optionally filtered by session.

        Args:
            session_id: Filter by session ID (None for all)
            limit: Maximum entries to return

        Returns:
            List of audit log entries as dictionaries
        """
        entries = self._audit_log

        if session_id:
            entries = [e for e in entries if e.session_id == session_id]

        # Return most recent entries
        return [e.to_dict() for e in entries[-limit:]]

    def validate_state_transition(
        self,
        session_id: str,
        current_state: Optional[SessionState],
        target_state: SessionState
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if a state transition is allowed.

        Args:
            session_id: Session ID for error messages
            current_state: Current session state
            target_state: Desired new state

        Returns:
            Tuple of (is_valid, error_message)
        """
        if is_valid_transition(current_state, target_state):
            return (True, None)

        current_name = current_state.value if current_state else "None"
        return (
            False,
            f"Invalid state transition for session {session_id}: "
            f"{current_name} -> {target_state.value}"
        )
