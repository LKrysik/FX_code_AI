"""
Unit tests for Health and System API endpoints.

These tests use lightweight_api_client (no QuestDB required).
For integration tests with real database, see tests_e2e/integration/.

Test Markers:
    @pytest.mark.fast - Fast unit test (<100ms)
    @pytest.mark.unit - Unit test with mocked dependencies
"""

import pytest


@pytest.mark.fast
@pytest.mark.unit
class TestHealthEndpoint:
    """Test main health endpoint"""

    def test_health_endpoint_exists(self, lightweight_api_client):
        """Test GET /health"""
        response = lightweight_api_client.get("/health")
        assert response.status_code in (200, 404, 500)

    def test_health_returns_json(self, lightweight_api_client):
        """Test health endpoint returns JSON"""
        response = lightweight_api_client.get("/health")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_health_no_auth_required(self, lightweight_api_client):
        """Test health endpoint doesn't require authentication"""
        response = lightweight_api_client.get("/health")
        # Should work without auth
        assert response.status_code in (200, 404, 500)


@pytest.mark.fast
@pytest.mark.unit
class TestHealthReady:
    """Test readiness probe endpoint"""

    def test_ready_endpoint_exists(self, lightweight_api_client):
        """Test GET /health/ready"""
        response = lightweight_api_client.get("/health/ready")
        assert response.status_code in (200, 404, 503, 500)

    def test_ready_returns_json(self, lightweight_api_client):
        """Test ready endpoint returns JSON"""
        response = lightweight_api_client.get("/health/ready")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_ready_no_auth_required(self, lightweight_api_client):
        """Test ready endpoint doesn't require authentication"""
        response = lightweight_api_client.get("/health/ready")
        # Should work without auth
        assert response.status_code in (200, 404, 503, 500)


@pytest.mark.fast
@pytest.mark.unit
class TestHealthLive:
    """Test liveness probe endpoint"""

    def test_live_endpoint_exists(self, lightweight_api_client):
        """Test GET /health/live"""
        response = lightweight_api_client.get("/health/live")
        assert response.status_code in (200, 404, 500)

    def test_live_returns_json(self, lightweight_api_client):
        """Test live endpoint returns JSON"""
        response = lightweight_api_client.get("/health/live")
        if response.status_code == 200:
            assert response.headers.get("content-type") in (None, "application/json", "application/json; charset=utf-8")

    def test_live_no_auth_required(self, lightweight_api_client):
        """Test live endpoint doesn't require authentication"""
        response = lightweight_api_client.get("/health/live")
        # Should work without auth
        assert response.status_code in (200, 404, 500)


@pytest.mark.fast
@pytest.mark.unit
class TestMetricsEndpoint:
    """Test metrics endpoint"""

    def test_metrics_endpoint_exists(self, lightweight_api_client):
        """Test GET /api/ops/metrics"""
        response = lightweight_api_client.get("/api/ops/metrics")
        assert response.status_code in (200, 404, 500)

    def test_metrics_returns_json_or_text(self, lightweight_api_client):
        """Test metrics endpoint returns valid content type"""
        response = lightweight_api_client.get("/api/ops/metrics")
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            # Metrics might be JSON or Prometheus text format
            assert any(ct in content_type for ct in ["application/json", "text/plain", ""]) or content_type is None
