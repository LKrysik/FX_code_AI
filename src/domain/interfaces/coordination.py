"""
Trading Coordination Interfaces - Mediator Pattern
===================================================
Interfaces for decoupled coordination between market adapter and session manager.
Eliminates circular dependency through event-driven communication.

Architecture:
- ISubscriptionCoordinator: Mediates subscription requests
- ISessionStateProvider: Provides session state without direct coupling
- ITradingCoordinator: Full mediator combining both responsibilities
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum


class SubscriptionDecision(Enum):
    """Decision result for subscription requests"""
    ALLOWED = "allowed"
    DENIED_RATE_LIMIT = "denied_rate_limit"
    DENIED_CIRCUIT_OPEN = "denied_circuit_open"
    DENIED_NO_SESSION = "denied_no_session"
    DENIED_QUOTA_EXCEEDED = "denied_quota_exceeded"


class ISubscriptionCoordinator(ABC):
    """
    Interface for coordinating symbol subscriptions.
    Decouples LiveMarketAdapter from SessionManager.
    """

    @abstractmethod
    async def request_subscription(self, symbol: str, requester_id: str = "market_adapter") -> SubscriptionDecision:
        """
        Request permission to subscribe to a symbol.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            requester_id: Identifier of the requesting component

        Returns:
            SubscriptionDecision indicating if subscription is allowed
        """
        pass

    @abstractmethod
    async def notify_subscription_success(self, symbol: str) -> None:
        """Notify coordinator that subscription succeeded"""
        pass

    @abstractmethod
    async def notify_subscription_failure(self, symbol: str, error: str) -> None:
        """Notify coordinator that subscription failed"""
        pass

    @abstractmethod
    async def request_unsubscription(self, symbol: str) -> bool:
        """Request to unsubscribe from a symbol"""
        pass


class ISessionStateProvider(ABC):
    """
    Interface for providing session state without direct coupling.
    Read-only access to session information.
    """

    @abstractmethod
    async def is_session_active(self, session_id: Optional[str] = None) -> bool:
        """Check if any (or specific) session is active"""
        pass

    @abstractmethod
    async def get_active_symbols(self) -> List[str]:
        """Get list of symbols with active subscriptions"""
        pass

    @abstractmethod
    async def get_circuit_breaker_state(self, symbol: str) -> Dict[str, Any]:
        """Get circuit breaker state for a symbol"""
        pass

    @abstractmethod
    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        pass


class ITradingCoordinator(ISubscriptionCoordinator, ISessionStateProvider):
    """
    Full trading coordinator interface combining subscription and state.
    Acts as mediator between LiveMarketAdapter and SessionManager.

    Design Principles:
    - Single Responsibility: Only coordinates, no business logic
    - Dependency Inversion: Both sides depend on this interface
    - Open/Closed: New coordination rules via EventBus handlers
    """

    @abstractmethod
    async def start(self) -> None:
        """Start coordinator and subscribe to EventBus topics"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop coordinator and cleanup subscriptions"""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Return coordinator health status"""
        pass
