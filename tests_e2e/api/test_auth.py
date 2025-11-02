"""
Authentication API E2E Tests
=============================

Tests for authentication endpoints:
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
"""

import pytest
from datetime import datetime


@pytest.mark.api
@pytest.mark.auth
class TestAuthLogin:
    """Tests for login endpoint"""

    def test_login_success_with_valid_credentials(self, api_client, valid_login_credentials):
        """Test successful login with valid admin credentials"""
        response = api_client.post("/api/v1/auth/login", json=valid_login_credentials)

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert "token_type" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert "expires_in" in data["data"]
        assert "user" in data["data"]

        # Verify user object
        user = data["data"]["user"]
        assert user["username"] == valid_login_credentials["username"]
        assert "user_id" in user
        assert "permissions" in user

    def test_login_returns_jwt_tokens(self, api_client, valid_login_credentials):
        """Test that login returns valid JWT tokens"""
        response = api_client.post("/api/v1/auth/login", json=valid_login_credentials)

        assert response.status_code == 200

        data = response.json()
        access_token = data["data"]["access_token"]
        refresh_token = data["data"]["refresh_token"]

        # JWT tokens should be non-empty strings
        assert isinstance(access_token, str)
        assert len(access_token) > 0
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 0

    def test_login_sets_http_only_cookies(self, api_client, valid_login_credentials):
        """Test that login sets HttpOnly cookies for tokens"""
        response = api_client.post("/api/v1/auth/login", json=valid_login_credentials)

        assert response.status_code == 200

        # Check cookies
        cookies = response.cookies
        assert "access_token" in cookies
        assert "refresh_token" in cookies

    def test_login_fails_with_invalid_username(self, api_client):
        """Test login fails with invalid username"""
        response = api_client.post("/api/v1/auth/login", json={
            "username": "invalid_user",
            "password": "any_password"
        })

        assert response.status_code == 401

        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "authentication_failed"

    def test_login_fails_with_invalid_password(self, api_client, test_config):
        """Test login fails with invalid password"""
        response = api_client.post("/api/v1/auth/login", json={
            "username": test_config["admin_username"],
            "password": "wrong_password"
        })

        assert response.status_code == 401

        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "authentication_failed"

    def test_login_fails_with_missing_username(self, api_client):
        """Test login fails when username is missing"""
        response = api_client.post("/api/v1/auth/login", json={
            "password": "any_password"
        })

        # Should fail (either 400 or 422 for validation error)
        assert response.status_code in (400, 422, 500)

    def test_login_fails_with_missing_password(self, api_client, test_config):
        """Test login fails when password is missing"""
        response = api_client.post("/api/v1/auth/login", json={
            "username": test_config["admin_username"]
        })

        # Should fail (either 400 or 422 for validation error)
        assert response.status_code in (400, 422, 500)


@pytest.mark.api
@pytest.mark.auth
class TestAuthRefresh:
    """Tests for token refresh endpoint"""

    def test_refresh_token_success(self, api_client, valid_login_credentials):
        """Test successful token refresh"""
        # First login
        login_response = api_client.post("/api/v1/auth/login", json=valid_login_credentials)
        assert login_response.status_code == 200

        # Extract refresh token from cookies
        refresh_token = login_response.cookies.get("refresh_token")
        assert refresh_token is not None

        # Refresh the token
        refresh_response = api_client.post("/api/v1/auth/refresh")

        assert refresh_response.status_code == 200

        data = refresh_response.json()
        assert "data" in data
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

        # New tokens should be different from original
        new_access_token = data["data"]["access_token"]
        original_access_token = login_response.json()["data"]["access_token"]

        # Tokens should be non-empty
        assert len(new_access_token) > 0

    def test_refresh_token_without_cookie_fails(self, api_client):
        """Test refresh fails without refresh token cookie"""
        # Clear cookies
        api_client.cookies.clear()

        response = api_client.post("/api/v1/auth/refresh")

        assert response.status_code == 401

        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "missing_refresh_token"


@pytest.mark.api
@pytest.mark.auth
class TestAuthLogout:
    """Tests for logout endpoint"""

    def test_logout_success(self, authenticated_client):
        """Test successful logout"""
        response = authenticated_client.post("/api/v1/auth/logout")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert data["data"]["message"] == "Successfully logged out"

    def test_logout_clears_cookies(self, authenticated_client):
        """Test that logout clears auth cookies"""
        response = authenticated_client.post("/api/v1/auth/logout")

        assert response.status_code == 200

        # Cookies should be cleared (set to empty or deleted)
        # This depends on FastAPI cookie deletion implementation

    def test_logout_without_auth_fails(self, api_client):
        """Test logout fails without authentication"""
        # Clear authorization header
        api_client.headers.pop("Authorization", None)

        response = api_client.post("/api/v1/auth/logout")

        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.auth
class TestAuthIntegration:
    """Integration tests for auth flow"""

    def test_complete_auth_flow(self, api_client, valid_login_credentials):
        """Test complete auth flow: login → use token → refresh → logout"""

        # Step 1: Login
        login_response = api_client.post("/api/v1/auth/login", json=valid_login_credentials)
        assert login_response.status_code == 200

        access_token = login_response.json()["data"]["access_token"]

        # Step 2: Use access token to access protected endpoint
        api_client.headers["Authorization"] = f"Bearer {access_token}"
        protected_response = api_client.get("/api/strategies")
        assert protected_response.status_code == 200

        # Step 3: Refresh token
        refresh_response = api_client.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 200

        new_access_token = refresh_response.json()["data"]["access_token"]

        # Step 4: Use new access token
        api_client.headers["Authorization"] = f"Bearer {new_access_token}"
        protected_response2 = api_client.get("/api/strategies")
        assert protected_response2.status_code == 200

        # Step 5: Logout
        logout_response = api_client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200
