"""
Health Check API E2E Tests
===========================

Tests for health monitoring endpoints:
- GET /health
- GET /health/detailed
- GET /health/status
- GET /health/checks/{check_name}
- GET /health/services
- GET /health/services/{service_name}
- POST /health/services/{service_name}/enable
- POST /health/services/{service_name}/disable
- POST /health/clear-cache
- GET /circuit-breakers
"""

import pytest


@pytest.mark.api
@pytest.mark.health
class TestHealthBasic:
    """Tests for basic health endpoint"""

    def test_health_endpoint_responds(self, api_client):
        """Test that health endpoint responds quickly"""
        response = api_client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "status" in data["data"]
        assert data["data"]["status"] == "healthy"

    def test_health_includes_timestamp(self, api_client):
        """Test that health response includes timestamp"""
        response = api_client.get("/health")

        assert response.status_code == 200

        data = response.json()["data"]
        assert "timestamp" in data
        assert "uptime" in data

    def test_health_includes_version(self, api_client):
        """Test that health response includes version"""
        response = api_client.get("/health")

        assert response.status_code == 200

        data = response.json()["data"]
        assert "version" in data


@pytest.mark.api
@pytest.mark.health
class TestHealthDetailed:
    """Tests for detailed health endpoint"""

    def test_health_detailed_responds(self, api_client):
        """Test that detailed health endpoint responds"""
        response = api_client.get("/health/detailed")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data

    def test_health_detailed_includes_components(self, api_client):
        """Test that detailed health includes component status"""
        response = api_client.get("/health/detailed")

        assert response.status_code == 200

        health_data = response.json()["data"]["data"]
        assert "components" in health_data
        assert "rest_api" in health_data["components"]

    def test_health_detailed_includes_degradation_info(self, api_client):
        """Test that detailed health includes degradation information"""
        response = api_client.get("/health/detailed")

        assert response.status_code == 200

        health_data = response.json()["data"]["data"]
        assert "degradation_info" in health_data
        assert "unavailable_services" in health_data["degradation_info"]
        assert "degraded_services" in health_data["degradation_info"]


@pytest.mark.api
@pytest.mark.health
class TestHealthStatus:
    """Tests for health status endpoint"""

    def test_health_status_responds(self, api_client):
        """Test that health status endpoint responds"""
        response = api_client.get("/health/status")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data


@pytest.mark.api
@pytest.mark.health
class TestCircuitBreakers:
    """Tests for circuit breaker endpoint"""

    def test_circuit_breakers_endpoint(self, api_client):
        """Test circuit breakers status endpoint"""
        response = api_client.get("/circuit-breakers")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data


@pytest.mark.api
@pytest.mark.health
class TestHealthChecks:
    """Tests for individual health checks"""

    def test_get_specific_health_check(self, api_client):
        """Test GET /health/checks/{check_name}"""
        response = api_client.get("/health/checks/database")

        # Should return 200 or 404 if check doesn't exist
        assert response.status_code in (200, 404)

    def test_get_nonexistent_health_check(self, api_client):
        """Test getting non-existent health check"""
        response = api_client.get("/health/checks/nonexistent_check")

        assert response.status_code == 404


@pytest.mark.api
@pytest.mark.health
class TestHealthServices:
    """Tests for health services endpoints"""

    def test_get_all_services(self, api_client):
        """Test GET /health/services returns all services"""
        response = api_client.get("/health/services")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "services" in data["data"]
        assert isinstance(data["data"]["services"], list)

    def test_get_specific_service(self, api_client):
        """Test GET /health/services/{service_name}"""
        response = api_client.get("/health/services/database")

        # Should return 200 or 404 if service doesn't exist
        assert response.status_code in (200, 404)

    def test_enable_service(self, authenticated_client):
        """Test POST /health/services/{service_name}/enable"""
        response = authenticated_client.post("/health/services/database/enable")

        # Should return 200 or 404 if service doesn't exist
        assert response.status_code in (200, 404)

    def test_disable_service(self, authenticated_client):
        """Test POST /health/services/{service_name}/disable"""
        response = authenticated_client.post("/health/services/database/disable")

        # Should return 200 or 404 if service doesn't exist
        assert response.status_code in (200, 404)

    def test_service_management_requires_auth(self, api_client):
        """Test service enable/disable require authentication"""
        # Clear auth header
        api_client.headers.pop("Authorization", None)

        enable_response = api_client.post("/health/services/database/enable")
        assert enable_response.status_code == 401

        disable_response = api_client.post("/health/services/database/disable")
        assert disable_response.status_code == 401


@pytest.mark.api
@pytest.mark.health
class TestHealthCache:
    """Tests for health cache management"""

    def test_clear_health_cache(self, authenticated_client):
        """Test POST /health/clear-cache"""
        response = authenticated_client.post("/health/clear-cache")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "message" in data["data"]

    def test_clear_cache_requires_auth(self, api_client):
        """Test cache clear requires authentication"""
        # Clear auth header
        api_client.headers.pop("Authorization", None)

        response = api_client.post("/health/clear-cache")

        assert response.status_code == 401
