"""
WebSocket Message Handlers
===========================
Specialized handlers for different message types.

Each handler is responsible for processing one category of messages:
- AuthMessageHandler: Authentication and authorization
- SessionMessageHandler: Session management (start, stop, status)
- StrategyMessageHandler: Strategy operations
- CollectionMessageHandler: Data collection operations
- ProtocolMessageHandler: Protocol-level operations (handshake, heartbeat)
- SubscriptionMessageHandler: Subscription management

All handlers follow the same pattern:
1. Validate message
2. Check authentication/permissions
3. Delegate to appropriate service
4. Return standardized response
"""

from .auth_handler import AuthMessageHandler
from .subscription_handler import SubscriptionMessageHandler
from .protocol_handler import ProtocolMessageHandler

__all__ = ["AuthMessageHandler", "SubscriptionMessageHandler", "ProtocolMessageHandler"]
