"""
WebSocket Utilities
===================
Shared utility functions and helpers.

Components:
- ErrorHandler: Centralized error response generation
- ClientUtils: Client information extraction (IP, metadata)

These utilities eliminate code duplication and provide consistent
patterns across the WebSocket server.
"""

from .error_handler import ErrorHandler
from .client_utils import ClientUtils

__all__ = ["ErrorHandler", "ClientUtils"]
