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

    def test_health_endpoint_comprehensive(self, api_client):
        """Comprehensive test validating all health endpoint fields"""
        response = api_client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        health_data = data["data"]

        # Status validation
        assert "status" in health_data
        assert health_data["status"] in ["healthy", "degraded", "unhealthy"]

        # Timestamp validation
        assert "timestamp" in health_data
        assert isinstance(health_data["timestamp"], (str, int, float))
        if isinstance(health_data["timestamp"], str):
            assert len(health_data["timestamp"]) > 0

        # Uptime validation
        assert "uptime" in health_data
        assert isinstance(health_data["uptime"], (int, float))
        assert health_data["uptime"] >= 0

        # Version validation
        assert "version" in health_data
        assert isinstance(health_data["version"], str)
        assert len(health_data["version"]) > 0
        # Version should be in semantic versioning format (contains digits)
        assert any(char.isdigit() for char in health_data["version"])


@pytest.mark.api
@pytest.mark.health
class TestHealthDetailed:
    """Tests for detailed health endpoint"""

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
class TestHealthChecks:
    """Tests for individual health checks"""

    def test_get_specific_health_check(self, api_client):
        """Test GET /health/checks/{check_name}"""
        response = api_client.get("/health/checks/database")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        check_data = data["data"]
        # Validate health check response structure
        assert isinstance(check_data, dict)
        # Health checks should have status information
        assert "status" in check_data or "healthy" in check_data or "check_name" in check_data

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
        # Validate service structure if any services exist
        if len(data["data"]["services"]) > 0:
            service = data["data"]["services"][0]
            assert isinstance(service, dict)
            # Services should have identifying information
            assert "name" in service or "service_name" in service or "id" in service

    def test_enable_service(self, authenticated_client):
        """Test POST /health/services/{service_name}/enable"""
        response = authenticated_client.post("/health/services/database/enable")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        service_data = data["data"]
        # Validate service enable response
        assert isinstance(service_data, dict)
        # Should confirm service is enabled
        assert "enabled" in service_data
        assert service_data["enabled"] == True

    def test_disable_service(self, authenticated_client):
        """Test POST /health/services/{service_name}/disable"""
        response = authenticated_client.post("/health/services/database/disable")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        service_data = data["data"]
        # Validate service disable response
        assert isinstance(service_data, dict)
        # Should confirm service is disabled
        assert "enabled" in service_data
        assert service_data["enabled"] == False

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
