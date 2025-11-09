"""
Unified Session Lookup Service

✅ SESSION-003 FIX: Provides consistent session lookup across all endpoints

This service centralizes session lookups to prevent inconsistent behavior:
- Before: Different endpoints used different lookup strategies
- After: Single service with unified lookup logic

Lookup Strategy:
1. Check ExecutionController (for active/running sessions)
2. Check QuestDB (for completed/stopped sessions)
3. Return None if not found
"""

from typing import Optional, Dict, Any, List
from datetime import datetime


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
