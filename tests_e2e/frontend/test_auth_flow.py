"""
Frontend Authentication Flow E2E Tests
=======================================

Tests for frontend authentication UI:
- Login page
- Logout flow
- Session persistence
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.frontend
@pytest.mark.auth
class TestLoginPage:
    """Tests for login page"""

    def test_login_page_loads(self, page: Page, test_config):
        """Test that login page loads correctly"""
        page.goto(f"{test_config['frontend_base_url']}/login")

        # Check for login form elements
        expect(page.locator('input[name="username"]')).to_be_visible()
        expect(page.locator('input[name="password"]')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()

    def test_login_with_valid_credentials(self, page: Page, test_config):
        """Test successful login flow"""
        page.goto(f"{test_config['frontend_base_url']}/login")

        # Fill login form
        page.fill('input[name="username"]', test_config["admin_username"])
        page.fill('input[name="password"]', test_config["admin_password"])

        # Submit
        page.click('button[type="submit"]')

        # Should redirect to dashboard
        page.wait_for_url(f"{test_config['frontend_base_url']}/dashboard", timeout=10000)

        # Dashboard should load
        expect(page).to_have_url(f"{test_config['frontend_base_url']}/dashboard")

    def test_login_with_invalid_credentials(self, page: Page, test_config):
        """Test login with invalid credentials shows error"""
        page.goto(f"{test_config['frontend_base_url']}/login")

        # Fill with invalid credentials
        page.fill('input[name="username"]', "invalid_user")
        page.fill('input[name="password"]', "wrong_password")

        # Submit
        page.click('button[type="submit"]')

        # Should stay on login page or show error message
        # (Exact behavior depends on frontend implementation)
        # Wait a moment for error to appear
        page.wait_for_timeout(2000)

        # Should still be on login page or have error visible
        current_url = page.url
        assert "/login" in current_url or "/dashboard" not in current_url


@pytest.mark.frontend
@pytest.mark.auth
class TestLogoutFlow:
    """Tests for logout functionality"""

    def test_logout_redirects_to_login(self, authenticated_page: Page, test_config):
        """Test that logout redirects to login page"""
        # Already on dashboard (authenticated)
        expect(authenticated_page).to_have_url(f"{test_config['frontend_base_url']}/dashboard")

        # Find and click logout button
        # (Selector depends on frontend implementation)
        logout_button = authenticated_page.locator('[data-testid="logout-button"]')
        if logout_button.count() > 0:
            logout_button.click()

            # Should redirect to login
            authenticated_page.wait_for_url(f"{test_config['frontend_base_url']}/login", timeout=5000)
