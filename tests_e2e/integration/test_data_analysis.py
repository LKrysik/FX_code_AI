"""
Data Analysis API E2E Tests
============================

Tests for data collection and analysis endpoints:
- GET /api/data-collection/{session_id}/analysis
- GET /api/data-collection/{session_id}/chart-data
- GET /api/data-collection/{session_id}/export
- GET /api/data-collection/{session_id}/quality
- GET /api/data-collection/{session_id}/export/estimate
- GET /api/data-collection/sessions
- DELETE /api/data-collection/sessions/{session_id}
"""

import pytest


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.database
class TestDataCollectionSessions:
    """Tests for data collection sessions listing"""

    def test_list_sessions_default(self, api_client):
        """Test GET /api/data-collection/sessions with default parameters"""
        response = api_client.get("/api/data-collection/sessions")

        assert response.status_code == 200

        response_json = response.json()
        # Handle both flat and nested response formats
        data = response_json.get("data", response_json)
        assert "sessions" in data
        assert "total_count" in data
        assert "limit" in data
        assert isinstance(data["sessions"], list)
        assert isinstance(data["total_count"], int)
        assert data["total_count"] >= 0
        assert isinstance(data["limit"], int)
        assert data["limit"] > 0
        # If sessions exist, validate structure
        if len(data["sessions"]) > 0:
            session = data["sessions"][0]
            assert "session_id" in session
            assert isinstance(session["session_id"], str)
            assert "status" in session

    def test_list_sessions_with_limit(self, api_client):
        """Test session listing with custom limit"""
        response = api_client.get("/api/data-collection/sessions?limit=10")

        assert response.status_code == 200

        response_json = response.json()
        # Handle both flat and nested response formats
        data = response_json.get("data", response_json)
        assert data["limit"] == 10
        assert "sessions" in data
        assert isinstance(data["sessions"], list)
        # Validate actual session count <= limit
        assert len(data["sessions"]) <= 10
        assert isinstance(data["total_count"], int)

    def test_list_sessions_with_stats(self, api_client):
        """Test session listing with statistics included"""
        response = api_client.get("/api/data-collection/sessions?include_stats=true")

        assert response.status_code == 200

        response_json = response.json()
        # Handle both flat and nested response formats
        data = response_json.get("data", response_json)
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

        # If sessions exist, validate stats fields are present
        if len(data["sessions"]) > 0:
            session = data["sessions"][0]
            assert "session_id" in session
            # When include_stats=true, expect statistics fields
            # Common stat fields: records_collected, prices_count, duration, etc.
            has_stats = any(key in session for key in
                          ["records_collected", "prices_count", "orderbook_count", "duration", "data_quality"])
            # Stats may be in nested object or at session level
            assert has_stats or "stats" in session


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.database
class TestSessionAnalysis:
    """Tests for session analysis endpoint"""

    def test_get_session_analysis_not_found(self, api_client):
        """Test analysis for non-existent session returns 404"""
        response = api_client.get("/api/data-collection/nonexistent_session/analysis")

        assert response.status_code == 404
        error_response = response.json()
        # Validate error response structure
        assert "error" in error_response or "detail" in error_response
        # Verify it's a not found error
        if "error" in error_response:
            assert "not found" in error_response["error"].lower() or "not_found" in str(error_response.get("error_code", "")).lower()

    def test_get_session_analysis_with_quality(self, api_client):
        """Test analysis endpoint with quality metrics"""
        # This would need a real session_id in production
        response = api_client.get("/api/data-collection/test_session_123/analysis?include_quality=true")

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    def test_get_session_analysis_without_quality(self, api_client):
        """Test analysis endpoint without quality metrics"""
        response = api_client.get("/api/data-collection/test_session_123/analysis?include_quality=false")

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.database
class TestChartData:
    """Tests for chart data endpoint"""

    def test_get_chart_data_missing_symbol(self, api_client):
        """Test chart data without symbol parameter returns 422"""
        response = api_client.get("/api/data-collection/test_session/chart-data")

        # FastAPI validation error for missing required param
        assert response.status_code == 422

    def test_get_chart_data_with_symbol(self, api_client):
        """Test chart data with symbol parameter"""
        response = api_client.get("/api/data-collection/test_session/chart-data?symbol=BTC_USDT")

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    def test_get_chart_data_with_max_points(self, api_client):
        """Test chart data with custom max_points"""
        response = api_client.get("/api/data-collection/test_session/chart-data?symbol=BTC_USDT&max_points=1000")

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    def test_get_chart_data_max_points_validation(self, api_client):
        """Test chart data max_points boundary validation"""
        # Test below minimum (should fail)
        response = api_client.get("/api/data-collection/test_session/chart-data?symbol=BTC_USDT&max_points=50")
        assert response.status_code == 422

        # Test above maximum (should fail)
        response = api_client.get("/api/data-collection/test_session/chart-data?symbol=BTC_USDT&max_points=100000")
        assert response.status_code == 422


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.database
class TestDataExport:
    """Tests for data export endpoints"""

    def test_get_export_estimate_not_found(self, api_client):
        """Test export estimate for non-existent session"""
        response = api_client.get("/api/data-collection/nonexistent/export/estimate")

        assert response.status_code == 404
        error_response = response.json()
        # Validate error response structure
        assert "error" in error_response or "detail" in error_response

    def test_get_export_estimate_with_symbol(self, api_client):
        """Test export estimate with specific symbol"""
        response = api_client.get("/api/data-collection/test_session/export/estimate?symbol=BTC_USDT")

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    def test_export_session_csv(self, api_client):
        """Test CSV export format"""
        response = api_client.get("/api/data-collection/test_session/export?format=csv")

        # 400=invalid format, 404=not found
        assert response.status_code in (400, 404)
        error_response = response.json()
        assert "error" in error_response or "error_code" in error_response or "detail" in error_response

    def test_export_session_json(self, api_client):
        """Test JSON export format"""
        response = api_client.get("/api/data-collection/test_session/export?format=json")

        # 400=invalid format, 404=not found
        assert response.status_code in (400, 404)
        error_response = response.json()
        assert "error" in error_response or "error_code" in error_response or "detail" in error_response

    def test_export_session_zip(self, api_client):
        """Test ZIP export format"""
        response = api_client.get("/api/data-collection/test_session/export?format=zip")

        # 400=invalid format, 404=not found
        assert response.status_code in (400, 404)
        error_response = response.json()
        assert "error" in error_response or "error_code" in error_response or "detail" in error_response

    def test_export_invalid_format(self, api_client):
        """Test export with unsupported format"""
        response = api_client.get("/api/data-collection/test_session/export?format=invalid")

        assert response.status_code == 400
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    def test_export_with_symbol_filter(self, api_client):
        """Test export with specific symbol"""
        response = api_client.get("/api/data-collection/test_session/export?format=csv&symbol=BTC_USDT")

        # 400=invalid format, 404=not found
        assert response.status_code in (400, 404)
        error_response = response.json()
        assert "error" in error_response or "error_code" in error_response or "detail" in error_response


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.database
class TestDataQuality:
    """Tests for data quality assessment endpoint"""

    def test_get_quality_metrics_not_found(self, api_client):
        """Test quality metrics for non-existent session"""
        response = api_client.get("/api/data-collection/nonexistent/quality")

        assert response.status_code == 404
        error_response = response.json()
        # Validate error response structure
        assert "error" in error_response or "detail" in error_response

    def test_get_quality_metrics_default(self, api_client):
        """Test quality metrics with default symbol (first available)"""
        response = api_client.get("/api/data-collection/test_session/quality")

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    def test_get_quality_metrics_with_symbol(self, api_client):
        """Test quality metrics for specific symbol"""
        response = api_client.get("/api/data-collection/test_session/quality?symbol=BTC_USDT")

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.database
class TestSessionDeletion:
    """Tests for session deletion endpoint"""

    def test_delete_session_not_found(self, api_client):
        """Test deleting non-existent session returns 404"""
        response = api_client.delete("/api/data-collection/sessions/nonexistent_session")

        assert response.status_code == 404
        error_response = response.json()
        # Validate error response structure
        assert "error" in error_response or "detail" in error_response

    def test_delete_session_unauthorized(self, api_client):
        """Test session deletion without authentication (if required)"""
        # Clear any auth headers
        api_client.headers.pop("Authorization", None)

        response = api_client.delete("/api/data-collection/sessions/test_session")

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    def test_delete_session_structure(self, authenticated_client):
        """Test successful deletion response structure"""
        response = authenticated_client.delete("/api/data-collection/sessions/test_session_for_deletion")

        # Will be 404 if session doesn't exist, 200 if successful
        if response.status_code == 200:
            response_json = response.json()
            # Handle both flat and nested response formats
            data = response_json.get("data", response_json)
            assert "success" in data
            assert "message" in data
            assert "session_id" in data
            assert "deleted_counts" in data


@pytest.mark.api
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.database
class TestDataCollectionIntegration:
    """Integration tests for data collection workflow"""

    def test_session_lifecycle_analysis(self, api_client):
        """Test complete session analysis workflow"""
        # List sessions
        list_response = api_client.get("/api/data-collection/sessions?limit=10")
        assert list_response.status_code == 200

        sessions = list_response.json()["sessions"]

        if len(sessions) > 0:
            session_id = sessions[0]["session_id"]

            # Get analysis
            analysis_response = api_client.get(f"/api/data-collection/{session_id}/analysis")
            # Should succeed if session exists
            assert analysis_response.status_code == 200

    def test_export_workflow(self, api_client):
        """Test export estimation and actual export"""
        session_id = "test_session"

        # Get estimate first
        estimate_response = api_client.get(f"/api/data-collection/{session_id}/export/estimate")

        # If session exists and has data
        if estimate_response.status_code == 200:
            estimate = estimate_response.json()

            # Check if export is allowed (not too large)
            if estimate.get("can_export", False):
                # Try actual export
                export_response = api_client.get(f"/api/data-collection/{session_id}/export?format=csv")
                assert export_response.status_code == 200
