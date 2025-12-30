"""
Session Lifecycle Models
=========================
BUG-008-8: Session Lifecycle Tracking

Provides:
- SessionState enum with explicit lifecycle states
- SessionLookupResult for enhanced "not found" responses
- Session ID validation utilities
- Session audit log entry model
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Dict, Literal


class SessionState(Enum):
    """
    BUG-008-8 AC1: Explicit session lifecycle states.

    State Machine:
        [CREATING] ──success──► [ACTIVE] ──pause──► [PAUSED]
             │                      │                   │
             │                      │                   │
             │                      ▼                   ▼
             │                  [STOPPED] ◄──stop──────┘
             │                      │
          failure                   │
             │                   delete
             ▼                      ▼
          [null]                [DELETED]
    """
    CREATING = "creating"      # Session being initialized
    ACTIVE = "active"          # Session running normally
    PAUSED = "paused"          # Session temporarily paused
    STOPPED = "stopped"        # Session completed/stopped
    DELETED = "deleted"        # Session soft-deleted (still queryable)


# Session ID format: exec_YYYYMMDD_HHMMSS_xxxxxxxx
SESSION_ID_PATTERN = re.compile(
    r'^exec_\d{8}_\d{6}_[a-f0-9]{8}$'
)

# Alternative patterns for legacy session IDs
LEGACY_SESSION_ID_PATTERNS = [
    re.compile(r'^paper_\d{8}_\d{6}_[a-f0-9]{8}$'),  # Paper trading
    re.compile(r'^live_\d{8}_\d{6}_[a-f0-9]{8}$'),   # Live trading
    re.compile(r'^backtest_\d{8}_\d{6}_[a-f0-9]{8}$'),  # Backtest
]


def validate_session_id(session_id: str) -> bool:
    """
    BUG-008-8 AC5: Validate session ID format.

    Valid formats:
    - exec_YYYYMMDD_HHMMSS_xxxxxxxx (main format)
    - paper_YYYYMMDD_HHMMSS_xxxxxxxx (paper trading)
    - live_YYYYMMDD_HHMMSS_xxxxxxxx (live trading)
    - backtest_YYYYMMDD_HHMMSS_xxxxxxxx (backtest)

    Args:
        session_id: Session ID to validate

    Returns:
        True if valid format, False otherwise
    """
    if not session_id or not isinstance(session_id, str):
        return False

    # Check main pattern
    if SESSION_ID_PATTERN.match(session_id):
        return True

    # Check legacy patterns
    for pattern in LEGACY_SESSION_ID_PATTERNS:
        if pattern.match(session_id):
            return True

    return False


class SessionLookupReason(Enum):
    """
    BUG-008-8 AC4: Reasons for session lookup results.
    """
    OK = "ok"                           # Session found and valid
    INVALID_FORMAT = "invalid_format"   # Session ID format is invalid
    NEVER_EXISTED = "never_existed"     # Session was never created
    DELETED = "deleted"                 # Session was soft-deleted
    ARCHIVED = "archived"               # Session moved to archive


@dataclass
class SessionLookupResult:
    """
    BUG-008-8 AC4: Enhanced session lookup result with reason.

    Provides clear feedback on why a session lookup succeeded or failed,
    enabling better error messages and debugging.
    """
    found: bool
    reason: SessionLookupReason
    session: Optional[Dict[str, Any]] = None
    deleted_at: Optional[datetime] = None

    @property
    def is_valid(self) -> bool:
        """Check if session is valid (found and not deleted)."""
        return self.found and self.reason == SessionLookupReason.OK

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            "found": self.found,
            "reason": self.reason.value
        }
        if self.session:
            result["session"] = self.session
        if self.deleted_at:
            result["deleted_at"] = self.deleted_at.isoformat()
        return result


@dataclass
class SessionAuditEntry:
    """
    BUG-008-8 AC6: Audit log entry for session lifecycle transitions.

    Captures all state changes for debugging and compliance.
    """
    session_id: str
    timestamp: datetime
    old_state: Optional[SessionState]
    new_state: SessionState
    trigger: str  # "user_action", "system_timeout", "api_call", "error"
    actor: str    # user_id or "system"
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/logging."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "old_state": self.old_state.value if self.old_state else None,
            "new_state": self.new_state.value,
            "trigger": self.trigger,
            "actor": self.actor,
            "reason": self.reason,
            "metadata": self.metadata
        }


# Valid state transitions
VALID_STATE_TRANSITIONS = {
    None: [SessionState.CREATING],  # Initial state
    SessionState.CREATING: [SessionState.ACTIVE],  # Creation succeeded
    SessionState.ACTIVE: [SessionState.PAUSED, SessionState.STOPPED, SessionState.DELETED],
    SessionState.PAUSED: [SessionState.ACTIVE, SessionState.STOPPED, SessionState.DELETED],
    SessionState.STOPPED: [SessionState.DELETED],  # Can only delete after stop
    SessionState.DELETED: [],  # Terminal state
}


def is_valid_transition(from_state: Optional[SessionState], to_state: SessionState) -> bool:
    """
    Check if a state transition is valid.

    Args:
        from_state: Current state (None for new session)
        to_state: Target state

    Returns:
        True if transition is valid, False otherwise
    """
    allowed = VALID_STATE_TRANSITIONS.get(from_state, [])
    return to_state in allowed
