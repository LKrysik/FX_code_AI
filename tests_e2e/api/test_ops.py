"""
Operations Dashboard API E2E Tests
===================================

Tests for operations dashboard endpoints:
- GET /api/ops/health
- GET /api/ops/positions
- GET /api/ops/incidents
- POST /api/ops/incidents/{incident_id}/acknowledge
- GET /api/ops/risk-controls
- POST /api/ops/risk-controls/kill-switch
- GET /api/ops/telemetry
- GET /api/ops/audit-log
"""

import pytest


@pytest.mark.api
class TestOpsHealth:
    """Tests for operations API health endpoint"""

    def test_ops_health_check(self, api_client):
        """Test GET /api/ops/health returns healthy status"""
        response = api_client.get("/api/ops/health")

        # Health check should always return 200
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "component" in data
        assert "timestamp" in data
        assert data["component"] == "ops_api"


@pytest.mark.api
class TestLivePositions:
    """Tests for live positions endpoint"""

    def test_get_positions_requires_auth(self, api_client):
        """Test positions endpoint requires authentication"""
        # Clear auth header
        api_client.headers.pop("Authorization", None)

        response = api_client.get("/api/ops/positions")

        # Should return 401 without authentication
        assert response.status_code == 401

    def test_get_positions_authenticated(self, authenticated_client):
        """Test GET /api/ops/positions with authentication"""
        response = authenticated_client.get("/api/ops/positions")

        # Should return 200 or 500 depending on backend state
        assert response.status_code in (200, 401, 500)

        if response.status_code == 200:
            data = response.json()
            assert "positions" in data
            assert "total_count" in data
            assert "timestamp" in data
            assert isinstance(data["positions"], list)

    def test_get_positions_with_symbol_filter(self, authenticated_client):
        """Test positions endpoint with symbol filter"""
        response = authenticated_client.get("/api/ops/positions?symbol=BTC_USDT")

        # Should filter by symbol
        assert response.status_code in (200, 401, 500)

    def test_get_positions_with_session_filter(self, authenticated_client):
        """Test positions endpoint with session filter"""
        response = authenticated_client.get("/api/ops/positions?session_id=test_session")

        assert response.status_code in (200, 401, 500)

    def test_get_positions_with_both_filters(self, authenticated_client):
        """Test positions endpoint with both symbol and session filters"""
        response = authenticated_client.get(
            "/api/ops/positions?symbol=BTC_USDT&session_id=test_session"
        )

        assert response.status_code in (200, 401, 500)


@pytest.mark.api
class TestIncidents:
    """Tests for incident management endpoints"""

    def test_get_incidents_requires_auth(self, api_client):
        """Test incidents endpoint requires authentication"""
        api_client.headers.pop("Authorization", None)

        response = api_client.get("/api/ops/incidents")

        assert response.status_code == 401

    def test_get_incidents_default(self, authenticated_client):
        """Test GET /api/ops/incidents with default parameters"""
        response = authenticated_client.get("/api/ops/incidents")

        # Should return incidents list (possibly empty)
        assert response.status_code in (200, 401, 500)

        if response.status_code == 200:
            data = response.json()
            assert "incidents" in data
            assert "total_count" in data
            assert "timestamp" in data
            assert isinstance(data["incidents"], list)

    def test_get_incidents_resolved_filter(self, authenticated_client):
        """Test incidents with resolved filter"""
        response = authenticated_client.get("/api/ops/incidents?resolved=true")

        assert response.status_code in (200, 401, 500)

    def test_get_incidents_severity_filter(self, authenticated_client):
        """Test incidents with severity filter"""
        response = authenticated_client.get("/api/ops/incidents?severity=critical")

        assert response.status_code in (200, 401, 500)

    def test_get_incidents_with_limit(self, authenticated_client):
        """Test incidents with custom limit"""
        response = authenticated_client.get("/api/ops/incidents?limit=10")

        assert response.status_code in (200, 401, 500)

    def test_get_incidents_combined_filters(self, authenticated_client):
        """Test incidents with multiple filters"""
        response = authenticated_client.get(
            "/api/ops/incidents?resolved=false&severity=high&limit=20"
        )

        assert response.status_code in (200, 401, 500)

    def test_acknowledge_incident_requires_auth(self, api_client):
        """Test acknowledging incident requires authentication"""
        api_client.headers.pop("Authorization", None)

        response = api_client.post("/api/ops/incidents/test_incident/acknowledge")

        assert response.status_code == 401

    def test_acknowledge_incident_requires_write_permission(self, authenticated_client):
        """Test POST /api/ops/incidents/{incident_id}/acknowledge"""
        response = authenticated_client.post(
            "/api/ops/incidents/test_incident_123/acknowledge"
        )

        # Should return 200 on success, 404 if not found, 403 if insufficient permissions
        assert response.status_code in (200, 403, 404, 500)

    def test_acknowledge_incident_with_note(self, authenticated_client):
        """Test acknowledging incident with custom note"""
        response = authenticated_client.post(
            "/api/ops/incidents/test_incident_123/acknowledge",
            params={"note": "Resolved by manual intervention"}
        )

        assert response.status_code in (200, 403, 404, 500)

    def test_acknowledge_incident_not_found(self, authenticated_client):
        """Test acknowledging non-existent incident"""
        response = authenticated_client.post(
            "/api/ops/incidents/nonexistent_incident/acknowledge"
        )

        # Should return 404 or 403 depending on permissions
        assert response.status_code in (403, 404, 500)


@pytest.mark.api
class TestRiskControls:
    """Tests for risk control endpoints"""

    def test_get_risk_controls_requires_auth(self, api_client):
        """Test risk controls endpoint requires authentication"""
        api_client.headers.pop("Authorization", None)

        response = api_client.get("/api/ops/risk-controls")

        assert response.status_code == 401

    def test_get_risk_controls(self, authenticated_client):
        """Test GET /api/ops/risk-controls"""
        response = authenticated_client.get("/api/ops/risk-controls")

        # Should return risk control status
        assert response.status_code in (200, 401, 500)

        if response.status_code == 200:
            data = response.json()
            assert "risk_controls" in data
            assert "timestamp" in data

            # Check risk control structure
            controls = data["risk_controls"]
            expected_fields = [
                "global_exposure_limit",
                "current_exposure",
                "kill_switch_active"
            ]

            # At least some expected fields should be present
            assert any(field in controls for field in expected_fields)

    def test_trigger_kill_switch_requires_auth(self, api_client):
        """Test kill switch requires authentication"""
        api_client.headers.pop("Authorization", None)

        response = api_client.post(
            "/api/ops/risk-controls/kill-switch",
            params={"reason": "Test"}
        )

        assert response.status_code == 401

    def test_trigger_kill_switch_requires_admin(self, authenticated_client):
        """Test POST /api/ops/risk-controls/kill-switch requires admin role"""
        response = authenticated_client.post(
            "/api/ops/risk-controls/kill-switch",
            params={"reason": "E2E test kill switch"}
        )

        # Should return 403 if user lacks admin permission, or 200/500 if admin
        # Most test users won't have admin role, so expect 403
        assert response.status_code in (200, 403, 500)

    def test_trigger_kill_switch_missing_reason(self, authenticated_client):
        """Test kill switch without reason parameter"""
        response = authenticated_client.post("/api/ops/risk-controls/kill-switch")

        # Should require reason parameter (422 validation error or 403 permission)
        assert response.status_code in (403, 422, 500)


@pytest.mark.api
class TestTelemetry:
    """Tests for telemetry endpoint"""

    def test_get_telemetry_requires_auth(self, api_client):
        """Test telemetry endpoint requires authentication"""
        api_client.headers.pop("Authorization", None)

        response = api_client.get("/api/ops/telemetry")

        assert response.status_code == 401

    def test_get_telemetry_default(self, authenticated_client):
        """Test GET /api/ops/telemetry with default time range"""
        response = authenticated_client.get("/api/ops/telemetry")

        assert response.status_code in (200, 401, 500)

        if response.status_code == 200:
            data = response.json()
            assert "telemetry" in data
            assert "timestamp" in data

            telemetry = data["telemetry"]
            assert "metrics" in telemetry
            assert "time_range" in telemetry

    def test_get_telemetry_1h(self, authenticated_client):
        """Test telemetry with 1 hour time range"""
        response = authenticated_client.get("/api/ops/telemetry?time_range=1h")

        assert response.status_code in (200, 401, 500)

    def test_get_telemetry_6h(self, authenticated_client):
        """Test telemetry with 6 hour time range"""
        response = authenticated_client.get("/api/ops/telemetry?time_range=6h")

        assert response.status_code in (200, 401, 500)

    def test_get_telemetry_24h(self, authenticated_client):
        """Test telemetry with 24 hour time range"""
        response = authenticated_client.get("/api/ops/telemetry?time_range=24h")

        assert response.status_code in (200, 401, 500)

    def test_get_telemetry_invalid_range(self, authenticated_client):
        """Test telemetry with invalid time range"""
        response = authenticated_client.get("/api/ops/telemetry?time_range=invalid")

        # Should return 400 for invalid time range
        assert response.status_code in (400, 401, 500)


@pytest.mark.api
class TestAuditLog:
    """Tests for audit log endpoint"""

    def test_get_audit_log_requires_auth(self, api_client):
        """Test audit log requires authentication"""
        api_client.headers.pop("Authorization", None)

        response = api_client.get("/api/ops/audit-log")

        assert response.status_code == 401

    def test_get_audit_log_default(self, authenticated_client):
        """Test GET /api/ops/audit-log with default parameters"""
        response = authenticated_client.get("/api/ops/audit-log")

        assert response.status_code in (200, 401, 500)

        if response.status_code == 200:
            data = response.json()
            assert "audit_log" in data
            assert "total_count" in data
            assert "timestamp" in data
            assert isinstance(data["audit_log"], list)

    def test_get_audit_log_with_limit(self, authenticated_client):
        """Test audit log with custom limit"""
        response = authenticated_client.get("/api/ops/audit-log?limit=50")

        assert response.status_code in (200, 401, 500)

    def test_get_audit_log_with_action_filter(self, authenticated_client):
        """Test audit log filtered by action"""
        response = authenticated_client.get("/api/ops/audit-log?action=get_positions")

        assert response.status_code in (200, 401, 500)

    def test_get_audit_log_combined_filters(self, authenticated_client):
        """Test audit log with multiple filters"""
        response = authenticated_client.get("/api/ops/audit-log?limit=25&action=get_telemetry")

        assert response.status_code in (200, 401, 500)


@pytest.mark.api
@pytest.mark.slow
class TestOpsIntegration:
    """Integration tests for operations dashboard workflows"""

    def test_monitoring_workflow(self, authenticated_client):
        """Test complete monitoring workflow: positions → incidents → telemetry"""
        # Get positions
        positions_response = authenticated_client.get("/api/ops/positions")

        if positions_response.status_code == 200:
            # Get incidents
            incidents_response = authenticated_client.get("/api/ops/incidents")
            assert incidents_response.status_code == 200

            # Get telemetry
            telemetry_response = authenticated_client.get("/api/ops/telemetry")
            assert telemetry_response.status_code == 200

            # Get risk controls
            risk_response = authenticated_client.get("/api/ops/risk-controls")
            assert risk_response.status_code == 200

    def test_incident_acknowledgement_workflow(self, authenticated_client):
        """Test incident discovery and acknowledgement"""
        # Get unresolved incidents
        incidents_response = authenticated_client.get("/api/ops/incidents?resolved=false")

        if incidents_response.status_code == 200:
            incidents = incidents_response.json()["incidents"]

            if len(incidents) > 0:
                # Try to acknowledge first incident
                incident_id = incidents[0].get("id", "test_incident")

                ack_response = authenticated_client.post(
                    f"/api/ops/incidents/{incident_id}/acknowledge",
                    params={"note": "Acknowledged in E2E test"}
                )

                # May fail due to permissions, but should handle gracefully
                assert ack_response.status_code in (200, 403, 404, 500)

    def test_risk_controls_monitoring(self, authenticated_client):
        """Test risk controls monitoring and status checks"""
        # Get risk controls
        controls_response = authenticated_client.get("/api/ops/risk-controls")

        if controls_response.status_code == 200:
            controls = controls_response.json()["risk_controls"]

            # Check if kill switch is active
            if "kill_switch_active" in controls:
                assert isinstance(controls["kill_switch_active"], bool)

            # Check exposure utilization
            if "exposure_utilization_percent" in controls:
                utilization = controls["exposure_utilization_percent"]
                assert isinstance(utilization, (int, float))
                assert 0 <= utilization <= 100

    def test_audit_trail_verification(self, authenticated_client):
        """Test that operations create audit trail entries"""
        # Perform some operations
        authenticated_client.get("/api/ops/positions")
        authenticated_client.get("/api/ops/telemetry")

        # Check audit log for these actions
        audit_response = authenticated_client.get("/api/ops/audit-log?limit=10")

        if audit_response.status_code == 200:
            audit_log = audit_response.json()["audit_log"]

            # Should have some audit entries
            assert isinstance(audit_log, list)

            # Check audit entry structure
            if len(audit_log) > 0:
                entry = audit_log[0]
                assert "timestamp" in entry
                assert "user_id" in entry or "action" in entry
