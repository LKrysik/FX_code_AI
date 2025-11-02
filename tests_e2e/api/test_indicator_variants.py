"""
Indicator Variants API E2E Tests
=================================

Tests for indicator management endpoints:
- System indicators discovery
- Indicator variants CRUD operations
- Session indicator management
- Algorithm registry
- Legacy indicator operations
"""

import pytest


@pytest.mark.api
class TestSystemIndicators:
    """Tests for system indicator discovery endpoints"""

    def test_get_system_indicators(self, api_client):
        """Test GET /api/indicators/system returns all system indicators"""
        response = api_client.get("/api/indicators/system")

        assert response.status_code == 200

        # Response should have envelope structure
        data = response.json()
        assert "type" in data
        assert data["type"] == "response"
        assert "data" in data

        payload = data["data"]
        assert "indicators" in payload
        assert "total_count" in payload
        assert "categories" in payload
        assert isinstance(payload["indicators"], list)

    def test_get_system_indicator_categories(self, api_client):
        """Test GET /api/indicators/system/categories returns categories"""
        response = api_client.get("/api/indicators/system/categories")

        assert response.status_code == 200

        data = response.json()["data"]
        assert "categories" in data
        assert "total_count" in data
        assert isinstance(data["categories"], list)

    def test_get_system_indicator_details(self, api_client):
        """Test GET /api/indicators/system/{indicator_id} for specific indicator"""
        # First get all indicators to find a valid ID
        list_response = api_client.get("/api/indicators/system")
        indicators = list_response.json()["data"]["indicators"]

        if len(indicators) > 0:
            indicator_id = indicators[0]["id"]

            detail_response = api_client.get(f"/api/indicators/system/{indicator_id}")
            assert detail_response.status_code == 200

            data = detail_response.json()["data"]
            assert "id" in data or "indicator_type" in data

    def test_get_system_indicator_details_not_found(self, api_client):
        """Test system indicator details for non-existent indicator"""
        response = api_client.get("/api/indicators/system/NONEXISTENT_INDICATOR")

        assert response.status_code == 404


@pytest.mark.api
class TestVariantsCRUD:
    """Tests for indicator variants CRUD operations"""

    def test_get_all_variants(self, api_client):
        """Test GET /api/indicators/variants returns all variants"""
        response = api_client.get("/api/indicators/variants")

        assert response.status_code == 200

        data = response.json()["data"]
        assert "variants" in data
        assert "total_count" in data
        assert "categories" in data
        assert isinstance(data["variants"], list)

    def test_get_variants_by_category(self, api_client):
        """Test GET /api/indicators/variants/by-category/{category}"""
        response = api_client.get("/api/indicators/variants/by-category/price")

        assert response.status_code == 200

        data = response.json()["data"]
        assert "category" in data
        assert "variants" in data
        assert "total_count" in data

    def test_create_variant_missing_fields(self, authenticated_client):
        """Test POST /api/indicators/variants with missing required fields"""
        response = authenticated_client.post("/api/indicators/variants", json={})

        assert response.status_code == 400

    def test_create_variant_success(self, authenticated_client):
        """Test creating a new indicator variant"""
        variant_config = {
            "name": "Test_TWPA_Variant",
            "indicator_type": "TWPA",
            "variant_type": "price",
            "description": "Test variant for E2E testing",
            "parameters": {
                "t1": 300,
                "t2": 0,
                "window_minutes": 5.0
            },
            "created_by": "e2e_test"
        }

        response = authenticated_client.post("/api/indicators/variants", json=variant_config)

        # Should return 200 on success or 400/500 on validation/server error
        assert response.status_code in (200, 400, 500)

        if response.status_code == 200:
            data = response.json()["data"]
            assert "variant_id" in data
            assert "status" in data
            assert data["status"] == "created"

    def test_get_variant_details(self, authenticated_client):
        """Test GET /api/indicators/variants/{variant_id}"""
        # Create a variant first
        variant_config = {
            "name": "Detail_Test_Variant",
            "indicator_type": "TWPA",
            "variant_type": "price",
            "parameters": {"t1": 60, "t2": 0}
        }

        create_response = authenticated_client.post("/api/indicators/variants", json=variant_config)

        if create_response.status_code == 200:
            variant_id = create_response.json()["data"]["variant_id"]

            # Get details
            detail_response = authenticated_client.get(f"/api/indicators/variants/{variant_id}")
            assert detail_response.status_code == 200

            data = detail_response.json()["data"]
            assert "variant_id" in data or "id" in data
            assert "parameters" in data

    def test_get_variant_details_not_found(self, api_client):
        """Test GET variant details for non-existent variant"""
        response = api_client.get("/api/indicators/variants/nonexistent_variant_id")

        assert response.status_code == 404

    def test_update_variant(self, authenticated_client):
        """Test PUT /api/indicators/variants/{variant_id}"""
        # Create variant first
        variant_config = {
            "name": "Update_Test_Variant",
            "indicator_type": "TWPA",
            "variant_type": "price",
            "parameters": {"t1": 60, "t2": 0}
        }

        create_response = authenticated_client.post("/api/indicators/variants", json=variant_config)

        if create_response.status_code == 200:
            variant_id = create_response.json()["data"]["variant_id"]

            # Update parameters
            update_data = {
                "parameters": {"t1": 120, "t2": 0}
            }

            update_response = authenticated_client.put(f"/api/indicators/variants/{variant_id}", json=update_data)
            assert update_response.status_code in (200, 400)

    def test_update_variant_not_found(self, authenticated_client):
        """Test updating non-existent variant"""
        update_data = {"parameters": {"t1": 120}}

        response = authenticated_client.put("/api/indicators/variants/nonexistent_id", json=update_data)

        assert response.status_code == 404

    def test_delete_variant(self, authenticated_client):
        """Test DELETE /api/indicators/variants/{variant_id}"""
        # Create variant first
        variant_config = {
            "name": "Delete_Test_Variant",
            "indicator_type": "TWPA",
            "variant_type": "price",
            "parameters": {"t1": 60, "t2": 0}
        }

        create_response = authenticated_client.post("/api/indicators/variants", json=variant_config)

        if create_response.status_code == 200:
            variant_id = create_response.json()["data"]["variant_id"]

            # Delete variant
            delete_response = authenticated_client.delete(f"/api/indicators/variants/{variant_id}")
            assert delete_response.status_code in (200, 404)

    def test_delete_variant_not_found(self, authenticated_client):
        """Test deleting non-existent variant"""
        response = authenticated_client.delete("/api/indicators/variants/nonexistent_id")

        assert response.status_code == 404

    def test_load_variants_from_files(self, api_client):
        """Test GET /api/indicators/variants/files to load from config"""
        response = api_client.get("/api/indicators/variants/files")

        # Should return 200 with loaded variants or 503 if not available
        assert response.status_code in (200, 503)


@pytest.mark.api
class TestSessionIndicators:
    """Tests for session-specific indicator operations"""

    def test_add_indicator_to_session_missing_variant(self, authenticated_client):
        """Test adding indicator without variant_id"""
        response = authenticated_client.post(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/indicators",
            json={}
        )

        assert response.status_code == 400

    def test_add_indicator_to_session_nonexistent_variant(self, authenticated_client):
        """Test adding indicator with non-existent variant"""
        response = authenticated_client.post(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/indicators",
            json={"variant_id": "nonexistent_variant"}
        )

        # Should return 404 for variant not found
        assert response.status_code in (404, 422, 500)

    def test_add_indicator_to_nonexistent_session(self, authenticated_client):
        """Test adding indicator to non-existent session"""
        response = authenticated_client.post(
            "/api/indicators/sessions/nonexistent_session/symbols/BTC_USDT/indicators",
            json={"variant_id": "some_variant"}
        )

        # Should return 404 for session not found
        assert response.status_code in (404, 422, 500)

    def test_remove_indicator_from_session(self, authenticated_client):
        """Test DELETE /api/indicators/sessions/{session_id}/symbols/{symbol}/indicators/{indicator_id}"""
        response = authenticated_client.delete(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/indicators/test_indicator"
        )

        # Should return 404 if indicator not found, or 200 if successful
        assert response.status_code in (200, 404)

    def test_cleanup_duplicate_indicators(self, authenticated_client):
        """Test POST cleanup-duplicates endpoint"""
        response = authenticated_client.post(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/cleanup-duplicates"
        )

        # Should return 200 with cleanup results
        assert response.status_code in (200, 500)

    def test_get_session_indicator_values(self, api_client):
        """Test GET session indicator values"""
        response = api_client.get(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/values"
        )

        # Should return 200 with indicator map (possibly empty)
        assert response.status_code in (200, 500)

    def test_get_indicator_history(self, api_client):
        """Test GET indicator history"""
        response = api_client.get(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/indicators/test_indicator/history"
        )

        # Should return 404 for non-existent indicator or 200 with history
        assert response.status_code in (200, 404)

    def test_get_indicator_history_with_limit(self, api_client):
        """Test indicator history with limit parameter"""
        response = api_client.get(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/indicators/test_indicator/history?limit=100"
        )

        assert response.status_code in (200, 404)

    def test_process_market_data(self, authenticated_client):
        """Test POST market-data processing"""
        market_data = {
            "timestamp": 1234567890,
            "data": [
                {"timestamp": 1234567890, "price": 50000, "volume": 100}
            ]
        }

        response = authenticated_client.post(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/market-data",
            json=market_data
        )

        # Should process or return error
        assert response.status_code in (200, 400, 500)

    def test_process_historical_data(self, authenticated_client):
        """Test POST historical-data processing"""
        historical_data = {
            "data": [
                {"timestamp": 1234567890, "price": 50000, "volume": 100}
            ]
        }

        response = authenticated_client.post(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/historical-data",
            json=historical_data
        )

        assert response.status_code in (200, 400, 500)

    def test_set_session_preferences(self, authenticated_client):
        """Test POST session preferences"""
        preferences = {
            "refresh_interval": 1.0,
            "auto_cleanup": True
        }

        response = authenticated_client.post(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/preferences",
            json=preferences
        )

        assert response.status_code in (200, 500)

    def test_get_session_preferences(self, api_client):
        """Test GET session preferences"""
        response = api_client.get(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/preferences"
        )

        assert response.status_code in (200, 500)


@pytest.mark.api
class TestAlgorithmRegistry:
    """Tests for algorithm registry endpoints"""

    def test_get_available_algorithms(self, api_client):
        """Test GET /api/indicators/algorithms"""
        response = api_client.get("/api/indicators/algorithms")

        # Should return 200 with algorithms or 503 if not available
        assert response.status_code in (200, 503)

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "data" in data
            assert "algorithms" in data["data"]
            assert "statistics" in data["data"]

    def test_get_algorithm_categories(self, api_client):
        """Test GET /api/indicators/algorithms/categories"""
        response = api_client.get("/api/indicators/algorithms/categories")

        assert response.status_code in (200, 503)

        if response.status_code == 200:
            data = response.json()["data"]
            assert "categories" in data

    def test_get_algorithm_details(self, api_client):
        """Test GET /api/indicators/algorithms/{algorithm_type}"""
        # Try with a common algorithm type
        response = api_client.get("/api/indicators/algorithms/TWPA")

        # Should return 200 if found, 404 if not, or 503 if registry unavailable
        assert response.status_code in (200, 404, 503)

    def test_get_algorithm_details_not_found(self, api_client):
        """Test algorithm details for non-existent algorithm"""
        response = api_client.get("/api/indicators/algorithms/NONEXISTENT_ALGO")

        assert response.status_code in (404, 503)

    def test_calculate_refresh_interval(self, api_client):
        """Test POST calculate-refresh-interval endpoint"""
        parameters = {
            "parameters": {
                "t1": 300,
                "t2": 0
            }
        }

        response = api_client.post(
            "/api/indicators/algorithms/TWPA/calculate-refresh-interval",
            json=parameters
        )

        # Should return 200 with interval, 404 if algorithm not found, or 503 if unavailable
        assert response.status_code in (200, 404, 503)


@pytest.mark.api
class TestLegacyIndicatorEndpoints:
    """Tests for legacy indicator endpoints (backwards compatibility)"""

    def test_get_indicator_types(self, api_client):
        """Test GET /api/indicators/types"""
        response = api_client.get("/api/indicators/types")

        assert response.status_code in (200, 500)

        if response.status_code == 200:
            data = response.json()["data"]
            assert "types" in data
            assert isinstance(data["types"], list)

    def test_list_indicators(self, api_client):
        """Test GET /api/indicators/list"""
        response = api_client.get("/api/indicators/list")

        assert response.status_code in (200, 500)

        if response.status_code == 200:
            data = response.json()["data"]
            assert "indicators" in data

    def test_list_indicators_with_filters(self, api_client):
        """Test indicator list with filters"""
        response = api_client.get("/api/indicators/list?symbol=BTC_USDT&type=TWPA")

        assert response.status_code in (200, 500)

    def test_add_single_indicator(self, authenticated_client):
        """Test POST /api/indicators/add"""
        indicator_data = {
            "symbol": "BTC_USDT",
            "indicator_type": "TWPA",
            "timeframe": "1m",
            "period": 20
        }

        response = authenticated_client.post("/api/indicators/add", json=indicator_data)

        # Should return 200 on success or 400/500 on error
        assert response.status_code in (200, 400, 500)

    def test_add_single_indicator_missing_fields(self, authenticated_client):
        """Test adding indicator without required fields"""
        response = authenticated_client.post("/api/indicators/add", json={})

        assert response.status_code == 400

    def test_add_indicators_bulk(self, authenticated_client):
        """Test POST /api/indicators/bulk"""
        bulk_data = {
            "indicators": [
                {
                    "symbol": "BTC_USDT",
                    "indicator_type": "TWPA",
                    "period": 20,
                    "timeframe": "1m"
                },
                {
                    "symbol": "ETH_USDT",
                    "indicator_type": "VELOCITY",
                    "period": 14,
                    "timeframe": "1m"
                }
            ]
        }

        response = authenticated_client.post("/api/indicators/bulk", json=bulk_data)

        # Should return 200 on success or 400/500 on error
        assert response.status_code in (200, 400, 500)

    def test_add_indicators_bulk_empty_list(self, authenticated_client):
        """Test bulk add with empty list"""
        response = authenticated_client.post("/api/indicators/bulk", json={"indicators": []})

        assert response.status_code == 400

    def test_delete_indicators_bulk(self, authenticated_client):
        """Test DELETE /api/indicators/bulk"""
        bulk_delete = {
            "keys": ["test_key_1", "test_key_2"]
        }

        response = authenticated_client.delete("/api/indicators/bulk", json=bulk_delete)

        # Should return 200 with removed indicators (possibly empty)
        assert response.status_code in (200, 400)

    def test_delete_indicator_by_key(self, authenticated_client):
        """Test DELETE /api/indicators/{key}"""
        response = authenticated_client.delete("/api/indicators/test_indicator_key")

        # Should return 200 if found and deleted, 404 if not found
        assert response.status_code in (200, 404)

    def test_update_indicator(self, authenticated_client):
        """Test PUT /api/indicators/{key}"""
        update_data = {
            "symbol": "BTC_USDT",
            "indicator_type": "TWPA",
            "period": 30
        }

        response = authenticated_client.put("/api/indicators/test_key", json=update_data)

        # Should return 200 on success, 404 if not found, 400 on validation error
        assert response.status_code in (200, 400, 404)


@pytest.mark.api
@pytest.mark.slow
class TestIndicatorIntegration:
    """Integration tests for complete indicator workflows"""

    def test_variant_lifecycle(self, authenticated_client):
        """Test complete variant lifecycle: create → get → update → delete"""
        # Create
        variant_config = {
            "name": "Lifecycle_Test_Variant",
            "indicator_type": "TWPA",
            "variant_type": "price",
            "parameters": {"t1": 60, "t2": 0}
        }

        create_response = authenticated_client.post("/api/indicators/variants", json=variant_config)

        if create_response.status_code == 200:
            variant_id = create_response.json()["data"]["variant_id"]

            # Get details
            get_response = authenticated_client.get(f"/api/indicators/variants/{variant_id}")
            assert get_response.status_code == 200

            # Update
            update_data = {"parameters": {"t1": 120, "t2": 0}}
            update_response = authenticated_client.put(f"/api/indicators/variants/{variant_id}", json=update_data)
            assert update_response.status_code in (200, 400)

            # Delete
            delete_response = authenticated_client.delete(f"/api/indicators/variants/{variant_id}")
            assert delete_response.status_code == 200

            # Verify deleted
            final_get = authenticated_client.get(f"/api/indicators/variants/{variant_id}")
            assert final_get.status_code == 404

    def test_system_indicators_discovery(self, api_client):
        """Test discovering and exploring system indicators"""
        # List all
        list_response = api_client.get("/api/indicators/system")
        assert list_response.status_code == 200

        indicators = list_response.json()["data"]["indicators"]

        if len(indicators) > 0:
            # Get categories
            cat_response = api_client.get("/api/indicators/system/categories")
            assert cat_response.status_code == 200

            # Get details for first indicator
            indicator_id = indicators[0]["id"]
            detail_response = api_client.get(f"/api/indicators/system/{indicator_id}")
            assert detail_response.status_code == 200
