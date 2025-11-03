"""
Unit tests for SessionStore
============================
Tests session persistence, TTL expiration, reconnection support, and memory safety.

Test coverage:
- Session save/restore lifecycle
- TTL-based expiration
- Reconnect token generation
- Automatic cleanup
- Statistics tracking
- Memory safety (no unbounded growth)
- Health checks
- Edge cases (expired sessions, missing sessions, etc.)
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock
from src.api.websocket.lifecycle import SessionStore


class TestSessionStoreSaveRestore:
    """Test basic save and restore operations"""

    def test_save_session_creates_entry(self):
        """Test that save_session creates session entry"""
        store = SessionStore()

        session_data = {
            "client_ip": "192.168.1.100",
            "authenticated": True,
            "subscriptions": ["market_data", "indicators"]
        }

        store.save_session("client_123", session_data)

        # Verify internal state
        assert "client_123" in store._sessions
        assert "client_123" in store._ttl
        assert store._sessions["client_123"]["session_data"] == session_data

    def test_save_session_records_metadata(self):
        """Test that save_session records metadata"""
        store = SessionStore()

        session_data = {"client_ip": "192.168.1.100"}
        store.save_session("client_123", session_data)

        session_info = store._sessions["client_123"]
        assert "saved_at" in session_info
        assert session_info["client_ip"] == "192.168.1.100"

    def test_save_session_handles_missing_ip(self):
        """Test that save_session handles missing client_ip gracefully"""
        store = SessionStore()

        session_data = {"authenticated": True}
        store.save_session("client_123", session_data)

        session_info = store._sessions["client_123"]
        assert session_info["client_ip"] == "unknown"

    def test_restore_session_returns_data(self):
        """Test that restore_session returns saved data"""
        store = SessionStore()

        session_data = {"client_ip": "192.168.1.100", "authenticated": True}
        store.save_session("client_123", session_data)

        restored = store.restore_session("client_123")

        assert restored is not None
        assert restored == session_data

    def test_restore_session_updates_ttl(self):
        """Test that restore_session updates TTL on access"""
        store = SessionStore()

        session_data = {"client_ip": "192.168.1.100"}
        store.save_session("client_123", session_data)

        original_ttl = store._ttl["client_123"]
        time.sleep(0.1)  # Small delay

        store.restore_session("client_123")

        updated_ttl = store._ttl["client_123"]
        assert updated_ttl > original_ttl

    def test_restore_session_returns_none_for_missing(self):
        """Test that restore_session returns None for non-existent session"""
        store = SessionStore()

        restored = store.restore_session("nonexistent_client")

        assert restored is None

    def test_restore_session_updates_statistics(self):
        """Test that restore_session updates reconnect statistics"""
        store = SessionStore()

        session_data = {"client_ip": "192.168.1.100"}
        store.save_session("client_123", session_data)

        store.restore_session("client_123")

        stats = store.get_stats()
        assert stats["total_reconnects"] == 1
        assert stats["total_sessions_restored"] == 1


class TestSessionStoreTTL:
    """Test TTL-based expiration"""

    def test_restore_expired_session_returns_none(self):
        """Test that restoring expired session returns None"""
        store = SessionStore(session_timeout=1)  # 1 second timeout

        session_data = {"client_ip": "192.168.1.100"}
        store.save_session("client_123", session_data)

        # Wait for expiration
        time.sleep(1.1)

        restored = store.restore_session("client_123")

        assert restored is None

    def test_restore_expired_session_removes_data(self):
        """Test that restoring expired session cleans up data"""
        store = SessionStore(session_timeout=1)

        session_data = {"client_ip": "192.168.1.100"}
        store.save_session("client_123", session_data)

        time.sleep(1.1)

        store.restore_session("client_123")

        # Verify cleanup
        assert "client_123" not in store._sessions
        assert "client_123" not in store._ttl

    def test_restore_valid_session_within_timeout(self):
        """Test that session is valid within timeout window"""
        store = SessionStore(session_timeout=10)  # 10 second timeout

        session_data = {"client_ip": "192.168.1.100"}
        store.save_session("client_123", session_data)

        time.sleep(0.5)  # Wait but don't exceed timeout

        restored = store.restore_session("client_123")

        assert restored is not None
        assert restored == session_data

    @pytest.mark.asyncio
    async def test_cleanup_removes_expired_sessions(self):
        """Test that cleanup removes expired sessions"""
        store = SessionStore(session_timeout=1)

        # Create multiple sessions
        for i in range(5):
            store.save_session(f"client_{i}", {"client_ip": f"192.168.1.{i}"})

        # Wait for expiration
        time.sleep(1.1)

        cleaned = await store.cleanup_expired_sessions()

        assert cleaned == 5
        assert len(store._sessions) == 0
        assert len(store._ttl) == 0

    @pytest.mark.asyncio
    async def test_cleanup_preserves_valid_sessions(self):
        """Test that cleanup preserves valid sessions"""
        store = SessionStore(session_timeout=10)

        # Create sessions
        store.save_session("client_1", {"client_ip": "192.168.1.1"})
        store.save_session("client_2", {"client_ip": "192.168.1.2"})

        cleaned = await store.cleanup_expired_sessions()

        assert cleaned == 0
        assert len(store._sessions) == 2

    @pytest.mark.asyncio
    async def test_cleanup_mixed_expired_and_valid(self):
        """Test cleanup with mix of expired and valid sessions"""
        store = SessionStore(session_timeout=2)

        # Create initial sessions
        store.save_session("client_old_1", {"client_ip": "192.168.1.1"})
        store.save_session("client_old_2", {"client_ip": "192.168.1.2"})

        # Wait for expiration
        time.sleep(2.1)

        # Create new sessions
        store.save_session("client_new_1", {"client_ip": "192.168.1.3"})

        cleaned = await store.cleanup_expired_sessions()

        assert cleaned == 2
        assert len(store._sessions) == 1
        assert "client_new_1" in store._sessions

    @pytest.mark.asyncio
    async def test_cleanup_updates_statistics(self):
        """Test that cleanup updates expiration statistics"""
        store = SessionStore(session_timeout=1)

        store.save_session("client_1", {"client_ip": "192.168.1.1"})
        store.save_session("client_2", {"client_ip": "192.168.1.2"})

        time.sleep(1.1)

        await store.cleanup_expired_sessions()

        stats = store.get_stats()
        assert stats["total_sessions_expired"] == 2


class TestSessionStoreReconnectTokens:
    """Test reconnect token generation"""

    def test_generate_token_format(self):
        """Test that generated token has correct format"""
        store = SessionStore()

        token = store.generate_reconnect_token("client_123")

        assert token.startswith("client_123:")
        assert len(token) > len("client_123:")

    def test_generate_token_uniqueness(self):
        """Test that generated tokens are unique"""
        store = SessionStore()

        token1 = store.generate_reconnect_token("client_123")
        token2 = store.generate_reconnect_token("client_123")

        assert token1 != token2

    def test_generate_token_secure_length(self):
        """Test that token has secure length (urlsafe(32) ≈ 43 chars)"""
        store = SessionStore()

        token = store.generate_reconnect_token("client_123")
        token_part = token.split(":")[1]

        # secrets.token_urlsafe(32) produces ~43 characters
        assert len(token_part) >= 40


class TestSessionStoreExplicitRemoval:
    """Test explicit session removal"""

    def test_remove_session_deletes_entry(self):
        """Test that remove_session deletes session"""
        store = SessionStore()

        session_data = {"client_ip": "192.168.1.100"}
        store.save_session("client_123", session_data)

        removed = store.remove_session("client_123")

        assert removed is True
        assert "client_123" not in store._sessions
        assert "client_123" not in store._ttl

    def test_remove_nonexistent_session_returns_false(self):
        """Test that removing non-existent session returns False"""
        store = SessionStore()

        removed = store.remove_session("nonexistent")

        assert removed is False

    def test_remove_session_prevents_restore(self):
        """Test that removed session cannot be restored"""
        store = SessionStore()

        session_data = {"client_ip": "192.168.1.100"}
        store.save_session("client_123", session_data)

        store.remove_session("client_123")

        restored = store.restore_session("client_123")

        assert restored is None


class TestSessionStoreStatistics:
    """Test statistics tracking"""

    def test_get_stats_initial_state(self):
        """Test get_stats returns correct initial state"""
        store = SessionStore(session_timeout=3600)

        stats = store.get_stats()

        assert stats["active_sessions"] == 0
        assert stats["total_reconnects"] == 0
        assert stats["total_sessions_restored"] == 0
        assert stats["total_sessions_expired"] == 0
        assert stats["session_timeout_seconds"] == 3600

    def test_get_stats_tracks_active_sessions(self):
        """Test that active_sessions count is correct"""
        store = SessionStore()

        store.save_session("client_1", {"client_ip": "192.168.1.1"})
        store.save_session("client_2", {"client_ip": "192.168.1.2"})

        stats = store.get_stats()

        assert stats["active_sessions"] == 2

    def test_get_stats_tracks_reconnects(self):
        """Test that reconnect counts are tracked"""
        store = SessionStore()

        session_data = {"client_ip": "192.168.1.100"}
        store.save_session("client_123", session_data)

        store.restore_session("client_123")
        store.restore_session("client_123")

        stats = store.get_stats()

        assert stats["total_reconnects"] == 2
        assert stats["total_sessions_restored"] == 2

    @pytest.mark.asyncio
    async def test_get_stats_tracks_expired_sessions(self):
        """Test that expired session count is tracked"""
        store = SessionStore(session_timeout=1)

        store.save_session("client_1", {"client_ip": "192.168.1.1"})
        store.save_session("client_2", {"client_ip": "192.168.1.2"})

        time.sleep(1.1)

        await store.cleanup_expired_sessions()

        stats = store.get_stats()

        assert stats["total_sessions_expired"] == 2


class TestSessionStoreHealthCheck:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self):
        """Test that health_check returns healthy status"""
        store = SessionStore()

        health = await store.health_check()

        assert health["healthy"] is True
        assert health["component"] == "SessionStore"
        assert "stats" in health
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_health_check_triggers_cleanup(self):
        """Test that health_check triggers cleanup"""
        store = SessionStore(session_timeout=1)

        store.save_session("client_1", {"client_ip": "192.168.1.1"})
        time.sleep(1.1)

        health = await store.health_check()

        assert health["last_cleanup_removed"] == 1
        assert len(store._sessions) == 0

    @pytest.mark.asyncio
    async def test_health_check_includes_stats(self):
        """Test that health_check includes statistics"""
        store = SessionStore()

        store.save_session("client_1", {"client_ip": "192.168.1.1"})

        health = await store.health_check()

        assert "stats" in health
        assert health["stats"]["active_sessions"] == 1


class TestSessionStoreClearAll:
    """Test clear_all functionality"""

    def test_clear_all_removes_all_sessions(self):
        """Test that clear_all removes all sessions"""
        store = SessionStore()

        for i in range(5):
            store.save_session(f"client_{i}", {"client_ip": f"192.168.1.{i}"})

        store.clear_all()

        assert len(store._sessions) == 0
        assert len(store._ttl) == 0

    def test_clear_all_prevents_restore(self):
        """Test that cleared sessions cannot be restored"""
        store = SessionStore()

        store.save_session("client_123", {"client_ip": "192.168.1.100"})

        store.clear_all()

        restored = store.restore_session("client_123")

        assert restored is None


class TestSessionStoreLogging:
    """Test logging integration"""

    def test_save_session_logs_with_logger(self):
        """Test that save_session logs when logger provided"""
        mock_logger = Mock()
        store = SessionStore(logger=mock_logger)

        session_data = {"client_ip": "192.168.1.100"}
        store.save_session("client_123", session_data)

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert call_args[0][0] == "session_store.session_saved"

    def test_restore_session_logs_success(self):
        """Test that restore_session logs successful restore"""
        mock_logger = Mock()
        store = SessionStore(logger=mock_logger)

        session_data = {"client_ip": "192.168.1.100"}
        store.save_session("client_123", session_data)

        mock_logger.reset_mock()

        store.restore_session("client_123")

        # Should log info on successful restore
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "session_store.session_restored"

    @pytest.mark.asyncio
    async def test_cleanup_logs_when_sessions_expired(self):
        """Test that cleanup logs when sessions are removed"""
        mock_logger = Mock()
        store = SessionStore(session_timeout=1, logger=mock_logger)

        store.save_session("client_1", {"client_ip": "192.168.1.1"})
        time.sleep(1.1)

        mock_logger.reset_mock()

        await store.cleanup_expired_sessions()

        # Should log info when sessions cleaned
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "session_store.cleanup_completed"


class TestSessionStoreMemorySafety:
    """Test memory safety and unbounded growth prevention"""

    @pytest.mark.asyncio
    async def test_no_unbounded_growth_with_cleanup(self):
        """Test that cleanup prevents unbounded memory growth"""
        store = SessionStore(session_timeout=1)

        # Simulate many connections over time
        for i in range(100):
            store.save_session(f"client_{i}", {"client_ip": f"192.168.1.{i % 256}"})

        time.sleep(1.1)

        # Cleanup should remove all old sessions
        cleaned = await store.cleanup_expired_sessions()

        assert cleaned == 100
        assert len(store._sessions) == 0

        # Add new sessions - should not accumulate old data
        for i in range(100, 110):
            store.save_session(f"client_{i}", {"client_ip": f"192.168.1.{i % 256}"})

        assert len(store._sessions) == 10

    def test_explicit_removal_prevents_accumulation(self):
        """Test that explicit removal prevents accumulation"""
        store = SessionStore()

        # Create and remove sessions
        for i in range(100):
            store.save_session(f"client_{i}", {"client_ip": f"192.168.1.{i % 256}"})
            store.remove_session(f"client_{i}")

        assert len(store._sessions) == 0
        assert len(store._ttl) == 0


class TestSessionStoreEdgeCases:
    """Test edge cases and error handling"""

    def test_save_empty_session_data(self):
        """Test saving empty session data"""
        store = SessionStore()

        store.save_session("client_123", {})

        restored = store.restore_session("client_123")

        assert restored == {}

    def test_save_session_overwrites_existing(self):
        """Test that saving overwrites existing session"""
        store = SessionStore()

        store.save_session("client_123", {"data": "old"})
        store.save_session("client_123", {"data": "new"})

        restored = store.restore_session("client_123")

        assert restored["data"] == "new"

    def test_concurrent_save_restore(self):
        """Test concurrent save and restore operations"""
        store = SessionStore()

        session_data = {"client_ip": "192.168.1.100"}

        # Simulate concurrent operations
        store.save_session("client_123", session_data)
        restored1 = store.restore_session("client_123")
        restored2 = store.restore_session("client_123")

        assert restored1 == session_data
        assert restored2 == session_data

    @pytest.mark.asyncio
    async def test_cleanup_with_no_sessions(self):
        """Test cleanup with no sessions"""
        store = SessionStore()

        cleaned = await store.cleanup_expired_sessions()

        assert cleaned == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
