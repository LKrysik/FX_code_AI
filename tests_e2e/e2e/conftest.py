"""
Frontend-specific pytest fixtures
==================================

Fixtures for Playwright-based frontend E2E tests.
"""

import pytest
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from typing import Generator


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """
    Browser instance (session-scoped).

    Uses Chromium by default. Can be changed to firefox or webkit.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,  # Set to False for debugging
            slow_mo=0  # Add delay for debugging (ms)
        )
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """
    Browser context (function-scoped, isolated per test).
    """
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/New_York"
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """
    Page instance (function-scoped).

    Usage:
        def test_homepage(page: Page):
            page.goto("http://localhost:3000")
            assert page.title() == "Trading Dashboard"
    """
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture
def authenticated_page(page: Page, test_config) -> Page:
    """
    Authenticated page (logged in).

    Usage:
        def test_dashboard(authenticated_page: Page):
            authenticated_page.goto("http://localhost:3000/dashboard")
            # Already logged in
    """
    # Navigate to root page (inline authentication via AuthGuard)
    page.goto(f"{test_config['frontend_base_url']}/")

    # Wait for login form to appear
    page.wait_for_selector('input[name="username"]', timeout=10000)

    # Fill login form
    page.fill('input[name="username"]', test_config["admin_username"])
    page.fill('input[name="password"]', test_config["admin_password"])

    # Submit
    page.click('button[type="submit"]')

    # Wait for successful login - frontend uses inline AuthGuard, so after login
    # the page content changes but URL stays at / (root IS the dashboard)
    page.wait_for_load_state("networkidle", timeout=10000)

    # Verify we're authenticated by checking dashboard navigation is visible
    page.wait_for_selector('a[href="/"]', timeout=5000)

    return page
