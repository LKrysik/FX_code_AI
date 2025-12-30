"""
BUG-008-5 Unit Tests: Subscription Lifecycle Management
========================================================
Story: BUG-008-5 - Subscription Lifecycle Management
Tests: Verify subscription states, auto-resubscription, retry logic

Acceptance Criteria:
- AC1: Expired subscriptions trigger automatic resubscription attempt
- AC2: Subscription has retry logic: 3 attempts with backoff (1s, 2s, 4s)
- AC3: After max retries, subscription marked as "failed" and logged at ERROR
- AC4: Late confirmations handled gracefully (no error, just log info)
- AC5: Subscription state machine: PENDING → ACTIVE → EXPIRED → RETRYING → FAILED
- AC6: Active subscriptions list is always accurate and queryable

Test Pattern: RED-GREEN-REFACTOR
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import asyncio

from src.infrastructure.exchanges.mexc.subscription.subscription_registry import (
    SubscriptionState,
    SubscriptionInfo,
    SubscriptionRegistry,
    VALID_SUBSCRIPTION_TRANSITIONS,
    SUBSCRIPTION_MAX_RETRIES,
    SUBSCRIPTION_RETRY_DELAYS
)


# ============================================================================
# AC5: Subscription State Machine
# ============================================================================

class TestSubscriptionState:
    """Tests for AC5: Subscription lifecycle states."""

    def test_subscription_state_values(self):
        """Verify all expected states are defined."""
        assert SubscriptionState.PENDING.value == "pending"
        assert SubscriptionState.ACTIVE.value == "active"
        assert SubscriptionState.EXPIRED.value == "expired"
        assert SubscriptionState.RETRYING.value == "retrying"
        assert SubscriptionState.FAILED.value == "failed"
        assert SubscriptionState.INACTIVE.value == "inactive"

    def test_state_count(self):
        """Verify exactly 6 states are defined."""
        states = list(SubscriptionState)
        assert len(states) == 6

    def test_state_enum_from_string(self):
        """Verify states can be created from string values."""
        assert SubscriptionState("pending") == SubscriptionState.PENDING
        assert SubscriptionState("active") == SubscriptionState.ACTIVE
        assert SubscriptionState("failed") == SubscriptionState.FAILED


class TestStateTransitions:
    """Tests for valid state transitions."""

    def test_initial_transition_to_pending(self):
        """New subscription can only transition to PENDING."""
        assert SubscriptionState.PENDING in VALID_SUBSCRIPTION_TRANSITIONS[None]

    def test_pending_transitions(self):
        """PENDING can transition to ACTIVE, EXPIRED, or FAILED."""
        allowed = VALID_SUBSCRIPTION_TRANSITIONS[SubscriptionState.PENDING]
        assert SubscriptionState.ACTIVE in allowed
        assert SubscriptionState.EXPIRED in allowed
        assert SubscriptionState.FAILED in allowed

    def test_active_transitions(self):
        """ACTIVE can transition to EXPIRED or INACTIVE."""
        allowed = VALID_SUBSCRIPTION_TRANSITIONS[SubscriptionState.ACTIVE]
        assert SubscriptionState.EXPIRED in allowed
        assert SubscriptionState.INACTIVE in allowed

    def test_expired_transitions(self):
        """EXPIRED can transition to RETRYING or FAILED."""
        allowed = VALID_SUBSCRIPTION_TRANSITIONS[SubscriptionState.EXPIRED]
        assert SubscriptionState.RETRYING in allowed
        assert SubscriptionState.FAILED in allowed

    def test_retrying_transitions(self):
        """RETRYING can transition to PENDING, ACTIVE, or FAILED."""
        allowed = VALID_SUBSCRIPTION_TRANSITIONS[SubscriptionState.RETRYING]
        assert SubscriptionState.PENDING in allowed
        assert SubscriptionState.ACTIVE in allowed
        assert SubscriptionState.FAILED in allowed

    def test_failed_is_terminal(self):
        """FAILED is a terminal state with no valid transitions."""
        allowed = VALID_SUBSCRIPTION_TRANSITIONS[SubscriptionState.FAILED]
        assert len(allowed) == 0

    def test_inactive_can_resubscribe(self):
        """INACTIVE can transition to PENDING (re-subscribe)."""
        allowed = VALID_SUBSCRIPTION_TRANSITIONS[SubscriptionState.INACTIVE]
        assert SubscriptionState.PENDING in allowed


# ============================================================================
# SubscriptionInfo Tests
# ============================================================================

class TestSubscriptionInfo:
    """Tests for SubscriptionInfo dataclass."""

    def test_creation_with_defaults(self):
        """SubscriptionInfo creates with sensible defaults."""
        info = SubscriptionInfo(
            symbol="BTC_USDT",
            channel="deal",
            connection_id=1
        )
        assert info.symbol == "BTC_USDT"
        assert info.channel == "deal"
        assert info.connection_id == 1
        assert info.state == SubscriptionState.PENDING
        assert info.retry_count == 0
        assert info.last_error is None
        assert info.confirmed_at is None

    def test_to_dict(self):
        """SubscriptionInfo serializes to dictionary."""
        info = SubscriptionInfo(
            symbol="ETH_USDT",
            channel="depth",
            connection_id=2
        )
        d = info.to_dict()
        assert d["symbol"] == "ETH_USDT"
        assert d["channel"] == "depth"
        assert d["connection_id"] == 2
        assert d["state"] == "pending"
        assert d["retry_count"] == 0


# ============================================================================
# AC6: SubscriptionRegistry Query Methods
# ============================================================================

class TestSubscriptionRegistryQueries:
    """Tests for AC6: Active subscriptions list and queries."""

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        logger = MagicMock()
        logger.debug = MagicMock()
        logger.info = MagicMock()
        logger.warning = MagicMock()
        logger.error = MagicMock()
        return logger

    @pytest.fixture
    def registry(self, mock_logger):
        """Create SubscriptionRegistry with mock logger."""
        return SubscriptionRegistry(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_register_subscription(self, registry):
        """Can register a new subscription."""
        info = await registry.register_subscription("BTC_USDT", "deal", 1)

        assert info.symbol == "BTC_USDT"
        assert info.channel == "deal"
        assert info.state == SubscriptionState.PENDING

    @pytest.mark.asyncio
    async def test_get_active_subscriptions_empty(self, registry):
        """Returns empty list when no active subscriptions."""
        active = registry.get_active_subscriptions()
        assert active == []

    @pytest.mark.asyncio
    async def test_get_active_subscriptions(self, registry):
        """AC6: Returns accurate list of active subscriptions."""
        # Register and confirm
        await registry.register_subscription("BTC_USDT", "deal", 1)
        await registry.confirm_subscription("BTC_USDT", "deal")

        await registry.register_subscription("ETH_USDT", "deal", 1)
        # Don't confirm ETH - should not appear in active

        active = registry.get_active_subscriptions()

        assert len(active) == 1
        assert active[0].symbol == "BTC_USDT"

    @pytest.mark.asyncio
    async def test_get_subscription_state(self, registry):
        """Can query subscription state."""
        await registry.register_subscription("BTC_USDT", "deal", 1)

        state = registry.get_subscription_state("BTC_USDT", "deal")
        assert state == SubscriptionState.PENDING

        # Confirm it
        await registry.confirm_subscription("BTC_USDT", "deal")
        state = registry.get_subscription_state("BTC_USDT", "deal")
        assert state == SubscriptionState.ACTIVE

    @pytest.mark.asyncio
    async def test_get_subscription_state_not_found(self, registry):
        """Returns None for unknown subscription."""
        state = registry.get_subscription_state("UNKNOWN", "deal")
        assert state is None

    @pytest.mark.asyncio
    async def test_get_subscriptions_by_state(self, registry):
        """Can filter subscriptions by state."""
        await registry.register_subscription("BTC_USDT", "deal", 1)
        await registry.register_subscription("ETH_USDT", "deal", 1)
        await registry.confirm_subscription("BTC_USDT", "deal")

        pending = registry.get_subscriptions_by_state(SubscriptionState.PENDING)
        active = registry.get_subscriptions_by_state(SubscriptionState.ACTIVE)

        assert len(pending) == 1
        assert pending[0].symbol == "ETH_USDT"
        assert len(active) == 1
        assert active[0].symbol == "BTC_USDT"


# ============================================================================
# AC4: Late Confirmation Handling
# ============================================================================

class TestLateConfirmations:
    """Tests for AC4: Late confirmations handled gracefully."""

    @pytest.fixture
    def mock_logger(self):
        logger = MagicMock()
        return logger

    @pytest.fixture
    def registry(self, mock_logger):
        return SubscriptionRegistry(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_late_confirmation_no_subscription(self, registry, mock_logger):
        """AC4: Late confirmation for unknown subscription logs info, not error."""
        result = await registry.confirm_subscription("UNKNOWN", "deal")

        assert result is False
        mock_logger.info.assert_called()
        # Should NOT log error
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_late_confirmation_expired_subscription(self, registry):
        """AC4: Late confirmation for expired subscription activates it."""
        await registry.register_subscription("BTC_USDT", "deal", 1)
        await registry.mark_expired("BTC_USDT", "deal", "TTL_exceeded")

        # Late confirmation arrives
        result = await registry.confirm_subscription("BTC_USDT", "deal")

        assert result is True
        state = registry.get_subscription_state("BTC_USDT", "deal")
        assert state == SubscriptionState.ACTIVE

    @pytest.mark.asyncio
    async def test_late_confirmation_retrying_subscription(self, registry):
        """AC4: Late confirmation during retry activates it."""
        await registry.register_subscription("BTC_USDT", "deal", 1)

        # Manually set to retrying
        info = registry._subscriptions[("BTC_USDT", "deal")]
        info.state = SubscriptionState.RETRYING

        # Late confirmation arrives
        result = await registry.confirm_subscription("BTC_USDT", "deal")

        assert result is True
        assert info.state == SubscriptionState.ACTIVE
        assert info.retry_count == 0  # Reset on success

    @pytest.mark.asyncio
    async def test_duplicate_confirmation_ignored(self, registry, mock_logger):
        """Duplicate confirmation for active subscription is ignored."""
        await registry.register_subscription("BTC_USDT", "deal", 1)
        await registry.confirm_subscription("BTC_USDT", "deal")

        # Duplicate confirmation
        result = await registry.confirm_subscription("BTC_USDT", "deal")

        assert result is False  # Already active


# ============================================================================
# AC3: Max Retries and Failed State
# ============================================================================

class TestFailedState:
    """Tests for AC3: After max retries, subscription marked as failed."""

    @pytest.fixture
    def mock_logger(self):
        logger = MagicMock()
        return logger

    @pytest.fixture
    def registry(self, mock_logger):
        return SubscriptionRegistry(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_mark_failed(self, registry, mock_logger):
        """AC3: Can mark subscription as failed with ERROR log."""
        await registry.register_subscription("BTC_USDT", "deal", 1)

        result = await registry.mark_failed("BTC_USDT", "deal", "max_retries_exceeded")

        assert result is True
        state = registry.get_subscription_state("BTC_USDT", "deal")
        assert state == SubscriptionState.FAILED
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_failed_is_terminal(self, registry):
        """AC3: Failed subscription cannot be confirmed."""
        await registry.register_subscription("BTC_USDT", "deal", 1)
        await registry.mark_failed("BTC_USDT", "deal", "error")

        # Try to confirm
        result = await registry.confirm_subscription("BTC_USDT", "deal")

        assert result is False
        state = registry.get_subscription_state("BTC_USDT", "deal")
        assert state == SubscriptionState.FAILED  # Still failed


# ============================================================================
# AC2: Retry Logic Configuration
# ============================================================================

class TestRetryConfiguration:
    """Tests for AC2: Retry logic with backoff."""

    def test_default_max_retries(self):
        """Default max retries is 3."""
        assert SUBSCRIPTION_MAX_RETRIES == 3

    def test_default_retry_delays(self):
        """Default retry delays are [1, 2, 4] seconds."""
        assert SUBSCRIPTION_RETRY_DELAYS == [1.0, 2.0, 4.0]

    def test_custom_configuration(self):
        """Can customize retry configuration."""
        registry = SubscriptionRegistry(
            max_retries=5,
            retry_delays=[0.5, 1.0, 2.0, 4.0, 8.0],
            ttl_seconds=60
        )

        assert registry.max_retries == 5
        assert registry.retry_delays == [0.5, 1.0, 2.0, 4.0, 8.0]
        assert registry.ttl_seconds == 60


# ============================================================================
# Subscription Lifecycle
# ============================================================================

class TestSubscriptionLifecycle:
    """Integration tests for full subscription lifecycle."""

    @pytest.fixture
    def mock_logger(self):
        logger = MagicMock()
        return logger

    @pytest.fixture
    def registry(self, mock_logger):
        return SubscriptionRegistry(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_full_success_lifecycle(self, registry):
        """Test: PENDING → ACTIVE lifecycle."""
        # Register
        info = await registry.register_subscription("BTC_USDT", "deal", 1)
        assert info.state == SubscriptionState.PENDING

        # Confirm
        await registry.confirm_subscription("BTC_USDT", "deal")
        assert registry.get_subscription_state("BTC_USDT", "deal") == SubscriptionState.ACTIVE

    @pytest.mark.asyncio
    async def test_expiration_lifecycle(self, registry):
        """Test: PENDING → EXPIRED lifecycle."""
        await registry.register_subscription("BTC_USDT", "deal", 1)

        # Expire
        await registry.mark_expired("BTC_USDT", "deal", "TTL_exceeded")

        state = registry.get_subscription_state("BTC_USDT", "deal")
        assert state == SubscriptionState.EXPIRED

    @pytest.mark.asyncio
    async def test_unsubscribe_lifecycle(self, registry):
        """Test: ACTIVE → INACTIVE lifecycle."""
        await registry.register_subscription("BTC_USDT", "deal", 1)
        await registry.confirm_subscription("BTC_USDT", "deal")

        # Unsubscribe
        await registry.unsubscribe("BTC_USDT", "deal")

        state = registry.get_subscription_state("BTC_USDT", "deal")
        assert state == SubscriptionState.INACTIVE

    @pytest.mark.asyncio
    async def test_reregistration_after_failed(self, registry):
        """Can re-register after failure."""
        await registry.register_subscription("BTC_USDT", "deal", 1)
        await registry.mark_failed("BTC_USDT", "deal", "error")

        # Re-register
        info = await registry.register_subscription("BTC_USDT", "deal", 1)

        assert info.state == SubscriptionState.PENDING


# ============================================================================
# Cleanup Methods
# ============================================================================

class TestCleanup:
    """Tests for cleanup methods."""

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def registry(self, mock_logger):
        return SubscriptionRegistry(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_clear(self, registry):
        """Clear removes all subscriptions."""
        await registry.register_subscription("BTC_USDT", "deal", 1)
        await registry.register_subscription("ETH_USDT", "deal", 1)

        registry.clear()

        assert len(registry._subscriptions) == 0

    @pytest.mark.asyncio
    async def test_remove_connection_subscriptions(self, registry):
        """Remove all subscriptions for a connection."""
        await registry.register_subscription("BTC_USDT", "deal", 1)
        await registry.register_subscription("ETH_USDT", "deal", 1)
        await registry.register_subscription("SOL_USDT", "deal", 2)  # Different connection

        removed = registry.remove_connection_subscriptions(1)

        assert removed == 2
        assert len(registry._subscriptions) == 1
        assert registry.get_subscription_state("SOL_USDT", "deal") == SubscriptionState.PENDING


# ============================================================================
# Activity Recording
# ============================================================================

class TestActivityRecording:
    """Tests for activity tracking."""

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def registry(self, mock_logger):
        return SubscriptionRegistry(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_record_activity_updates_timestamp(self, registry):
        """Activity recording updates last_activity_at."""
        await registry.register_subscription("BTC_USDT", "deal", 1)
        await registry.confirm_subscription("BTC_USDT", "deal")

        info = registry._subscriptions[("BTC_USDT", "deal")]
        old_activity = info.last_activity_at

        # Small delay
        await asyncio.sleep(0.01)

        # Record activity
        registry.record_activity("BTC_USDT", "deal")

        assert info.last_activity_at > old_activity

    @pytest.mark.asyncio
    async def test_record_activity_only_for_active(self, registry):
        """Activity recording only updates ACTIVE subscriptions."""
        await registry.register_subscription("BTC_USDT", "deal", 1)
        # Don't confirm - stays PENDING

        info = registry._subscriptions[("BTC_USDT", "deal")]
        old_activity = info.last_activity_at

        registry.record_activity("BTC_USDT", "deal")

        # Should not update for PENDING state
        assert info.last_activity_at == old_activity
