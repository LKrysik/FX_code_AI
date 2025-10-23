"""
Error Mapper
============
Centralizes mapping of internal error codes/exceptions to a stable
taxonomy with human-readable messages and (optional) HTTP statuses.

This is a minimal scaffolding used by both WS and REST layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class ErrorInfo:
    error_code: str
    error_message: str
    http_status: int = 400


DEFAULT_ERRORS: Dict[str, ErrorInfo] = {
    # Validation and routing
    "validation_error": ErrorInfo("validation_error", "Validation failed", 400),
    "routing_error": ErrorInfo("routing_error", "Routing error", 500),
    "handler_error": ErrorInfo("handler_error", "Handler error", 500),
    "command_failed": ErrorInfo("command_failed", "Command failed", 500),
    "invalid_request_type": ErrorInfo("invalid_request_type", "Invalid request type", 400),

    # Auth
    "authentication_required": ErrorInfo("authentication_required", "Authentication required", 401),
    "auth_failed": ErrorInfo("auth_failed", "Authentication failed", 401),

    # Sessions / strategies / services
    "invalid_session_type": ErrorInfo("invalid_session_type", "Invalid session type", 400),
    "missing_strategy_config": ErrorInfo("missing_strategy_config", "Missing strategy configuration", 400),
    "strategy_activation_failed": ErrorInfo("strategy_activation_failed", "Strategy activation failed", 409),
    "session_conflict": ErrorInfo("session_conflict", "Session conflict", 409),
    "service_unavailable": ErrorInfo("service_unavailable", "Service unavailable", 503),
    "message_processing_error": ErrorInfo("message_processing_error", "Failed to process message", 400),
}


class ErrorMapper:
    """Maps error codes / exceptions to ErrorInfo"""

    def __init__(self, overrides: Optional[Dict[str, ErrorInfo]] = None):
        self._map = dict(DEFAULT_ERRORS)
        if overrides:
            self._map.update(overrides)

    def map(self, error_code: str, message: Optional[str] = None, exc: Optional[BaseException] = None) -> ErrorInfo:
        base = self._map.get(error_code)
        if not base:
            # Unknown code => generic
            base = ErrorInfo(error_code=error_code or "command_failed",
                             error_message="Command failed",
                             http_status=500)
        if message:
            return ErrorInfo(error_code=base.error_code, error_message=message, http_status=base.http_status)
        if exc and str(exc).strip():
            return ErrorInfo(error_code=base.error_code, error_message=str(exc), http_status=base.http_status)
        return base

