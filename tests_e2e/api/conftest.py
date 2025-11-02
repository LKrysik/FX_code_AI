"""
API-specific pytest fixtures
=============================

Additional fixtures for API endpoint testing.
"""

import pytest
from typing import Dict, Any


@pytest.fixture
def valid_login_credentials(test_config) -> Dict[str, str]:
    """Valid login credentials for testing"""
    return {
        "username": test_config["admin_username"],
        "password": test_config["admin_password"]
    }


@pytest.fixture
def invalid_login_credentials() -> Dict[str, str]:
    """Invalid login credentials for testing"""
    return {
        "username": "invalid_user",
        "password": "wrong_password"
    }
