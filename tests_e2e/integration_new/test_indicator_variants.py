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

        assert response.status_code == 200
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
            assert update_response.status_code == 200
            data = update_response.json()["data"]
            assert "variant_id" in data or "status" in data

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
            assert delete_response.status_code == 200
            data = delete_response.json()["data"]
            assert "variant_id" in data or "status" in data

    def test_delete_variant_not_found(self, authenticated_client):
        """Test deleting non-existent variant"""
        response = authenticated_client.delete("/api/indicators/variants/nonexistent_id")

        assert response.status_code == 404

    def test_load_variants_from_files(self, api_client):
        """Test GET /api/indicators/variants/files to load from config"""
        response = api_client.get("/api/indicators/variants/files")

        assert response.status_code == 200
        data = response.json()["data"]
        assert "variants" in data or "loaded_count" in data


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

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    def test_add_indicator_to_nonexistent_session(self, authenticated_client):
        """Test adding indicator to non-existent session"""
        response = authenticated_client.post(
            "/api/indicators/sessions/nonexistent_session/symbols/BTC_USDT/indicators",
            json={"variant_id": "some_variant"}
        )

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    def test_remove_indicator_from_session(self, authenticated_client):
        """Test DELETE /api/indicators/sessions/{session_id}/symbols/{symbol}/indicators/{indicator_id}"""
        response = authenticated_client.delete(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/indicators/test_indicator"
        )

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    def test_cleanup_duplicate_indicators(self, authenticated_client):
        """Test POST cleanup-duplicates endpoint"""
        response = authenticated_client.post(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/cleanup-duplicates"
        )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "data" in data

    def test_get_session_indicator_values(self, api_client):
        """Test GET session indicator values"""
        response = api_client.get(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/values"
        )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "data" in data

    def test_get_indicator_history(self, api_client):
        """Test GET indicator history"""
        response = api_client.get(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/indicators/test_indicator/history"
        )

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    def test_get_indicator_history_with_limit(self, api_client):
        """Test indicator history with limit parameter"""
        response = api_client.get(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/indicators/test_indicator/history?limit=100"
        )

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

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

        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "data" in data

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

        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "data" in data

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

        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "data" in data

    def test_get_session_preferences(self, api_client):
        """Test GET session preferences"""
        response = api_client.get(
            "/api/indicators/sessions/test_session/symbols/BTC_USDT/preferences"
        )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "data" in data


@pytest.mark.api
class TestAlgorithmRegistry:
    """Tests for algorithm registry endpoints"""

    def test_algorithm_registry_comprehensive(self, api_client):
        """Comprehensive test for algorithm registry endpoints"""
        # Test 1: Get all available algorithms
        algorithms_response = api_client.get("/api/indicators/algorithms")
        assert algorithms_response.status_code == 200
        algorithms_data = algorithms_response.json()
        assert "status" in algorithms_data
        assert "data" in algorithms_data
        assert "algorithms" in algorithms_data["data"]
        assert "statistics" in algorithms_data["data"]

        # Test 2: Get algorithm categories
        categories_response = api_client.get("/api/indicators/algorithms/categories")
        assert categories_response.status_code == 200
        categories_data = categories_response.json()["data"]
        assert "categories" in categories_data

        # Test 3: Get algorithm details for a common algorithm type
        details_response = api_client.get("/api/indicators/algorithms/TWPA")
        assert details_response.status_code == 200
        details_data = details_response.json()["data"]
        assert "algorithm_type" in details_data or "name" in details_data

    def test_get_algorithm_details_not_found(self, api_client):
        """Test algorithm details for non-existent algorithm"""
        response = api_client.get("/api/indicators/algorithms/NONEXISTENT_ALGO")

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

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

        assert response.status_code == 200
        data = response.json()["data"]
        assert "refresh_interval" in data or "interval" in data


@pytest.mark.api
class TestLegacyIndicatorEndpoints:
    """Tests for legacy indicator endpoints (backwards compatibility)"""

    def test_get_indicator_types(self, api_client):
        """Test GET /api/indicators/types"""
        response = api_client.get("/api/indicators/types")

        assert response.status_code == 200
        response_json = response.json()
        # Handle both flat and nested response formats
        data = response_json.get("data", response_json)
        assert "types" in data or "indicators" in data
        if "types" in data:
            assert isinstance(data["types"], list)

    def test_list_indicators(self, api_client):
        """Test GET /api/indicators/list"""
        response = api_client.get("/api/indicators/list")

        assert response.status_code == 200
        response_json = response.json()
        # Handle both flat and nested response formats
        data = response_json.get("data", response_json)
        assert "indicators" in data

    def test_list_indicators_with_filters(self, api_client):
        """Test indicator list with filters"""
        response = api_client.get("/api/indicators/list?symbol=BTC_USDT&type=TWPA")

        assert response.status_code == 200
        response_json = response.json()
        # Handle both flat and nested response formats
        data = response_json.get("data", response_json)
        assert "status" in response_json or "data" in response_json

    def test_add_single_indicator(self, authenticated_client):
        """Test POST /api/indicators/add"""
        indicator_data = {
            "symbol": "BTC_USDT",
            "indicator_type": "TWPA",
            "timeframe": "1m",
            "period": 20
        }

        response = authenticated_client.post("/api/indicators/add", json=indicator_data)

        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "data" in data

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

        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "data" in data

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

        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "data" in data

    def test_delete_indicator_by_key(self, authenticated_client):
        """Test DELETE /api/indicators/{key}"""
        response = authenticated_client.delete("/api/indicators/test_indicator_key")

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response

    def test_update_indicator(self, authenticated_client):
        """Test PUT /api/indicators/{key}"""
        update_data = {
            "symbol": "BTC_USDT",
            "indicator_type": "TWPA",
            "period": 30
        }

        response = authenticated_client.put("/api/indicators/test_key", json=update_data)

        assert response.status_code == 404
        error_response = response.json()
        assert "error" in error_response or "detail" in error_response


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
            assert update_response.status_code == 200
            data = update_response.json()["data"]
            assert "variant_id" in data or "status" in data

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
