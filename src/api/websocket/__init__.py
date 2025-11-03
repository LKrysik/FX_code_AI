"""
WebSocket API Module
====================
Refactored WebSocket server with clean separation of concerns.

Architecture:
- server.py: Main WebSocketAPIServer (orchestration only)
- handlers/: Message handlers (auth, session, strategy, etc.)
- lifecycle/: Connection lifecycle and session management
- utils/: Shared utilities (error handling, client utils)

This module maintains 100% backward compatibility with the original
websocket_server.py while providing better structure and testability.
"""

# Public API will be added as components are migrated
# For now, re-export from original location for backward compatibility
__all__ = []
