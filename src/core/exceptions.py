"""
Core Exceptions - FX Agent AI
=============================
Centralized exception definitions for the trading system.
"""


class PositionOperationError(Exception):
    """Base exception for position-related operations."""
    pass


class PositionAlreadyClosingError(PositionOperationError):
    """
    Raised when attempting to close a position that is already being closed.

    This prevents race conditions where multiple concurrent close requests
    could result in double-close bugs, incorrect P&L calculations, or orphaned orders.

    HTTP Status: 409 Conflict
    """
    def __init__(self, position_id: str, message: str = None):
        self.position_id = position_id
        self.message = message or f"Position {position_id} is already being closed"
        super().__init__(self.message)


class PositionLockTimeoutError(PositionOperationError):
    """
    Raised when acquiring a position lock times out.

    This indicates the lock was held for too long, possibly due to a crash
    or long-running operation. The caller should retry after a delay.

    HTTP Status: 503 Service Unavailable (retry later)
    """
    def __init__(self, position_id: str, timeout: float):
        self.position_id = position_id
        self.timeout = timeout
        self.message = f"Timeout acquiring lock for position {position_id} after {timeout}s"
        super().__init__(self.message)


class PositionNotFoundError(PositionOperationError):
    """
    Raised when a position is not found or already closed.

    HTTP Status: 404 Not Found
    """
    def __init__(self, position_id: str):
        self.position_id = position_id
        self.message = f"Position not found: {position_id}"
        super().__init__(self.message)


class PositionModifyError(PositionOperationError):
    """
    Raised when position modification fails.

    HTTP Status: 400 Bad Request
    """
    def __init__(self, position_id: str, reason: str):
        self.position_id = position_id
        self.reason = reason
        self.message = f"Cannot modify position {position_id}: {reason}"
        super().__init__(self.message)
