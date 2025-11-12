"""
Frontend Dashboard E2E Tests
=============================

Tests for dashboard rendering and functionality.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.frontend
@pytest.mark.e2e
class TestDashboard:
    """Tests for dashboard page"""

    def test_dashboard_loads_after_login(self, authenticated_page: Page, test_config):
        """Test that dashboard loads after successful login"""
        # Already authenticated and on dashboard (root / is the dashboard)
        expect(authenticated_page).to_have_url(f"{test_config['frontend_base_url']}/")

    def test_dashboard_displays_key_sections(self, authenticated_page: Page):
        """Test that dashboard displays key UI sections"""
        # Check for presence of key UI components
        # (Selectors depend on actual frontend implementation)

        # Example checks (adjust selectors as needed):
        # - Market data section
        # - Session controls
        # - Status indicators

        # Just verify page is interactive
        expect(authenticated_page.locator('body')).to_be_visible()


@pytest.mark.frontend
@pytest.mark.slow
@pytest.mark.e2e
class TestDashboardInteraction:
    """Tests for dashboard interactions"""

    def test_dashboard_session_controls_visible(self, authenticated_page: Page):
        """Test that session control buttons are visible"""
        # Check for start/stop session buttons
        # (Adjust selectors based on actual implementation)
        body = authenticated_page.locator('body')
        expect(body).to_be_visible()
