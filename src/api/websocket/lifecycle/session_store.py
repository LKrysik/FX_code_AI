"""
SessionStore - Client Session Persistence for Reconnection Support
===================================================================
Manages WebSocket client session persistence with TTL-based expiration.

This component enables clients to reconnect and restore their session state
(authentication, subscriptions, preferences) within a configurable timeout window.

Features:
- Session persistence with TTL (default: 1 hour)
- Automatic cleanup of expired sessions
- Reconnect token generation
- Reconnection statistics tracking
- Memory-safe with explicit cleanup

Extracted from WebSocketAPIServer (lines 357-363, 2980-3023, usage at 771, 788, 855)
"""

import time
import secrets
from datetime import datetime
from typing import Dict, Any, Optional


class SessionStore:
    """
    Manages client session persistence for reconnection support.

    Session lifecycle:
    1. Client connects → session data saved on disconnect
    2. Client disconnects → session persisted with TTL
    3. Client reconnects within timeout → session restored
    4. TTL expires → session automatically cleaned up

    Thread-safety: Methods are synchronous but safe for async contexts.
    Memory safety: Explicit TTL-based cleanup prevents unbounded growth.
    """

    def __init__(self,
                 session_timeout: int = 3600,
                 logger = None):
        """
        Initialize session store.

        Args:
            session_timeout: TTL in seconds for session persistence (default: 1 hour)
            logger: Optional logger for diagnostics
        """
        self.session_timeout = session_timeout
        self.logger = logger

        # Session storage: client_id -> session metadata
        self._sessions: Dict[str, Dict[str, Any]] = {}

        # TTL tracking: client_id -> last_access_timestamp
        self._ttl: Dict[str, float] = {}

        # Statistics
        self._total_reconnects = 0
        self._total_sessions_restored = 0
        self._total_sessions_expired = 0

    def save_session(self, client_id: str, session_data: Dict[str, Any]) -> None:
        """
        Save client session data for potential reconnection.

        Session data typically includes:
        - client_ip: Client IP address
        - authenticated: Authentication status
        - subscriptions: Active subscriptions
        - last_seen: Timestamp of last activity

        Args:
            client_id: Unique client identifier
            session_data: Session state to persist

        Original location: websocket_server.py:2999-3006 (_save_client_session)
        Called from: websocket_server.py:855 (on disconnect)
        """
        self._sessions[client_id] = {
            "session_data": session_data,
            "saved_at": datetime.now().isoformat(),
            "client_ip": session_data.get("client_ip", "unknown")
        }
        self._ttl[client_id] = time.time()

        if self.logger:
            self.logger.debug("session_store.session_saved", {
                "client_id": client_id,
                "client_ip": session_data.get("client_ip", "unknown"),
                "total_sessions": len(self._sessions)
            })

    def restore_session(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore client session data for reconnection.

        Behavior:
        - If session exists and not expired: return session data, update TTL
        - If session expired or not found: return None

        Args:
            client_id: Unique client identifier

        Returns:
            Session data dict if found, None otherwise

        Original location: websocket_server.py:3008-3015 (_restore_client_session)
        Called from: websocket_server.py:788 (on reconnect)
        """
        if client_id not in self._sessions:
            if self.logger:
                self.logger.debug("session_store.session_not_found", {
                    "client_id": client_id
                })
            return None

        # Check if session expired
        if client_id in self._ttl:
            elapsed = time.time() - self._ttl[client_id]
            if elapsed > self.session_timeout:
                # Session expired, clean it up
                self._sessions.pop(client_id, None)
                self._ttl.pop(client_id, None)

                if self.logger:
                    self.logger.debug("session_store.session_expired_on_restore", {
                        "client_id": client_id,
                        "elapsed_seconds": elapsed
                    })
                return None

        # Session valid, restore and update TTL
        session_info = self._sessions[client_id]
        self._ttl[client_id] = time.time()  # Update TTL on access

        # Update statistics
        self._total_sessions_restored += 1
        self._total_reconnects += 1

        if self.logger:
            self.logger.info("session_store.session_restored", {
                "client_id": client_id,
                "saved_at": session_info.get("saved_at"),
                "client_ip": session_info.get("client_ip", "unknown"),
                "total_reconnects": self._total_reconnects
            })

        return session_info["session_data"]

    def generate_reconnect_token(self, client_id: str) -> str:
        """
        Generate a secure token for reconnection.

        Token format: "{client_id}:{random_token}"

        Note: In production, these tokens should be stored securely with
        expiration tracking. Current implementation generates stateless tokens.

        Args:
            client_id: Unique client identifier

        Returns:
            Secure reconnect token string

        Original location: websocket_server.py:3017-3022 (_generate_reconnect_token)
        Called from: websocket_server.py:771 (on connection)
        """
        token = secrets.token_urlsafe(32)

        if self.logger:
            self.logger.debug("session_store.token_generated", {
                "client_id": client_id
            })

        # In production, this should be stored securely with expiration
        return f"{client_id}:{token}"

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired client sessions based on TTL.

        This method should be called periodically (e.g., every 5 minutes)
        to prevent unbounded memory growth.

        Returns:
            Number of sessions cleaned up

        Original location: websocket_server.py:2980-2997 (cleanup_expired_client_sessions)
        Called from: websocket_server.py:3034 (health_check)
        """
        now = time.time()
        expired_clients = []

        # Identify expired sessions
        for client_id, last_access in self._ttl.items():
            if now - last_access > self.session_timeout:
                expired_clients.append(client_id)

        # Remove expired sessions
        for client_id in expired_clients:
            self._sessions.pop(client_id, None)
            self._ttl.pop(client_id, None)

        # Update statistics
        self._total_sessions_expired += len(expired_clients)

        if expired_clients and self.logger:
            self.logger.info("session_store.cleanup_completed", {
                "expired_sessions_cleaned": len(expired_clients),
                "remaining_sessions": len(self._sessions),
                "total_expired_lifetime": self._total_sessions_expired
            })

        return len(expired_clients)

    def remove_session(self, client_id: str) -> bool:
        """
        Explicitly remove a session (e.g., on logout or explicit disconnect).

        Args:
            client_id: Unique client identifier

        Returns:
            True if session was removed, False if not found
        """
        session_existed = client_id in self._sessions

        self._sessions.pop(client_id, None)
        self._ttl.pop(client_id, None)

        if session_existed and self.logger:
            self.logger.debug("session_store.session_removed", {
                "client_id": client_id,
                "remaining_sessions": len(self._sessions)
            })

        return session_existed

    def get_stats(self) -> Dict[str, Any]:
        """
        Get session store statistics.

        Returns:
            Dict with reconnect metrics and session counts
        """
        return {
            "active_sessions": len(self._sessions),
            "total_reconnects": self._total_reconnects,
            "total_sessions_restored": self._total_sessions_restored,
            "total_sessions_expired": self._total_sessions_expired,
            "session_timeout_seconds": self.session_timeout
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check and return status.

        Returns:
            Health status dict with session metrics
        """
        # Trigger cleanup during health check
        cleaned = await self.cleanup_expired_sessions()

        stats = self.get_stats()

        return {
            "healthy": True,
            "component": "SessionStore",
            "stats": stats,
            "last_cleanup_removed": cleaned,
            "timestamp": datetime.now().isoformat()
        }

    def clear_all(self) -> None:
        """
        Clear all sessions (for testing or shutdown).

        Warning: This will prevent any pending reconnections.
        """
        session_count = len(self._sessions)

        self._sessions.clear()
        self._ttl.clear()

        if self.logger:
            self.logger.info("session_store.all_sessions_cleared", {
                "sessions_cleared": session_count
            })
