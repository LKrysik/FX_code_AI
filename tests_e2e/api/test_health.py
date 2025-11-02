"""
Health Check API E2E Tests
===========================

Tests for health monitoring endpoints:
- GET /health
- GET /health/detailed
- GET /health/status
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
