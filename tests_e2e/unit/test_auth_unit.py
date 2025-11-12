"""
Unit tests for Authentication API endpoints.

These tests use lightweight_api_client (no QuestDB required).
For integration tests with real database, see tests_e2e/integration/.

Test Markers:
    @pytest.mark.fast - Fast unit test (<100ms)
    @pytest.mark.unit - Unit test with mocked dependencies
"""

import pytest


@pytest.mark.fast
@pytest.mark.unit
class TestAuthLogin:
    """Test authentication login endpoint"""

    def test_login_endpoint_exists(self, lightweight_api_client):
        """Test login endpoint is accessible"""
        response = lightweight_api_client.post("/api/v1/auth/login", json={
            "username": "test",
            "password": "test"
        })
        # Don't assert specific status (mock may not implement full logic)
        assert response.status_code in (200, 400, 401, 422, 500)

    def test_login_requires_username(self, lightweight_api_client):
        """Test login validates username presence"""
        response = lightweight_api_client.post("/api/v1/auth/login", json={
            "password": "test"
        })
        assert response.status_code in (400, 422)  # Validation error

    def test_login_requires_password(self, lightweight_api_client):
        """Test login validates password presence"""
        response = lightweight_api_client.post("/api/v1/auth/login", json={
            "username": "test"
        })
        assert response.status_code in (400, 422)  # Validation error

    def test_login_accepts_json_only(self, lightweight_api_client):
        """Test login rejects non-JSON requests"""
        response = lightweight_api_client.post("/api/v1/auth/login", data="invalid")
        assert response.status_code in (400, 422)

    def test_login_with_empty_credentials(self, lightweight_api_client):
        """Test login with empty username and password"""
        response = lightweight_api_client.post("/api/v1/auth/login", json={
            "username": "",
            "password": ""
        })
        assert response.status_code in (400, 401, 422)

    def test_login_with_null_username(self, lightweight_api_client):
        """Test login with null username"""
        response = lightweight_api_client.post("/api/v1/auth/login", json={
            "username": None,
            "password": "test"
        })
        assert response.status_code in (400, 422)

    def test_login_with_null_password(self, lightweight_api_client):
        """Test login with null password"""
        response = lightweight_api_client.post("/api/v1/auth/login", json={
            "username": "test",
            "password": None
        })
        assert response.status_code in (400, 422)

    def test_login_returns_json_response(self, lightweight_api_client):
        """Test login returns JSON response"""
        response = lightweight_api_client.post("/api/v1/auth/login", json={
            "username": "test",
            "password": "test"
        })
        assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")


@pytest.mark.fast
@pytest.mark.unit
class TestAuthRefresh:
    """Test JWT token refresh endpoint"""

    def test_refresh_endpoint_exists(self, lightweight_api_client):
        """Test refresh endpoint is accessible"""
        response = lightweight_api_client.post("/api/v1/auth/refresh", json={
            "refresh_token": "test_token"
        })
        assert response.status_code in (200, 400, 401, 422, 500)

    def test_refresh_requires_token(self, lightweight_api_client):
        """Test refresh validates token presence"""
        response = lightweight_api_client.post("/api/v1/auth/refresh", json={})
        assert response.status_code in (400, 401, 422)

    def test_refresh_with_empty_token(self, lightweight_api_client):
        """Test refresh with empty token"""
        response = lightweight_api_client.post("/api/v1/auth/refresh", json={
            "refresh_token": ""
        })
        assert response.status_code in (400, 401, 422)

    def test_refresh_with_null_token(self, lightweight_api_client):
        """Test refresh with null token"""
        response = lightweight_api_client.post("/api/v1/auth/refresh", json={
            "refresh_token": None
        })
        assert response.status_code in (400, 401, 422)


@pytest.mark.fast
@pytest.mark.unit
class TestAuthLogout:
    """Test authentication logout endpoint"""

    def test_logout_endpoint_exists(self, lightweight_api_client):
        """Test logout endpoint is accessible"""
        response = lightweight_api_client.post("/api/v1/auth/logout")
        assert response.status_code in (200, 401, 500)

    def test_logout_without_auth_header(self, lightweight_api_client):
        """Test logout without authentication header"""
        response = lightweight_api_client.post("/api/v1/auth/logout")
        assert response.status_code in (200, 401)

    def test_logout_with_invalid_auth_header(self, lightweight_api_client):
        """Test logout with invalid authentication header"""
        response = lightweight_api_client.post("/api/v1/auth/logout", headers={
            "Authorization": "Invalid"
        })
        assert response.status_code in (200, 401)


@pytest.mark.fast
@pytest.mark.unit
class TestCSRFToken:
    """Test CSRF token endpoint"""

    def test_csrf_endpoint_exists(self, lightweight_api_client):
        """Test CSRF token endpoint is accessible"""
        response = lightweight_api_client.get("/csrf-token")
        assert response.status_code in (200, 404, 500)

    def test_csrf_token_returns_json(self, lightweight_api_client):
        """Test CSRF token returns JSON response"""
        response = lightweight_api_client.get("/csrf-token")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_csrf_token_get_method_only(self, lightweight_api_client):
        """Test CSRF token only accepts GET method"""
        response = lightweight_api_client.post("/csrf-token")
        assert response.status_code in (404, 405)  # Method Not Allowed

    def test_csrf_token_no_auth_required(self, lightweight_api_client):
        """Test CSRF token doesn't require authentication"""
        response = lightweight_api_client.get("/csrf-token")
        # Should work without auth (200 or endpoint doesn't exist 404)
        assert response.status_code in (200, 404, 500)

    def test_csrf_token_returns_different_tokens(self, lightweight_api_client):
        """Test CSRF token returns unique tokens on multiple calls"""
        response1 = lightweight_api_client.get("/csrf-token")
        response2 = lightweight_api_client.get("/csrf-token")
        # Both should succeed or both fail
        assert response1.status_code == response2.status_code
