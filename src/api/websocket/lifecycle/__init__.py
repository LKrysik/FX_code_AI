"""
WebSocket Connection Lifecycle Management
==========================================
Components for managing WebSocket connection lifecycle and session state.

Components:
- ConnectionLifecycle: Connection accept, handling, cleanup
- SessionStore: Session persistence for reconnection support

These components handle the low-level WebSocket connection management
while keeping the main server class focused on orchestration.
"""

from .session_store import SessionStore

__all__ = ["SessionStore"]
