"""
Execution Domain Interfaces
===========================
Abstract interfaces for execution-related components.
Provides clean separation and dependency injection support.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class IExecutionProcessor(ABC):
    """Interface for execution processors"""

    @abstractmethod
    async def process_execution_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Process an execution event"""
        pass

    @abstractmethod
    def get_session_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for a specific session"""
        pass

    @abstractmethod
    async def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        pass


class IEventBridge(ABC):
    """Interface for event bridge components"""

    @abstractmethod
    async def start(self) -> None:
        """Start the event bridge"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the event bridge"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics"""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        pass