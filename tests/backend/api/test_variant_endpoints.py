import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from src.api.unified_server import app


class TestVariantEndpoints:
    """Test variant CRUD operations via API endpoints"""

    def setup_method(self):
        """Setup test client and mocks"""
        self.client = TestClient(app)
        self.mock_controller = MagicMock()
        self.mock_indicator_engine = MagicMock()

        # Mock the controller and indicator engine
        app.state.rest_service = MagicMock()
        app.state.rest_service.get_controller = AsyncMock(return_value=self.mock_controller)
        self.mock_controller.indicator_engine = self.mock_indicator_engine

    @pytest.mark.asyncio
    async def test_get_variants_success(self):
        """Test successful variant listing"""
        mock_variants = [
            {
                "id": "variant-1",
                "name": "Test Variant",
                "base_indicator_type": "RSI",
                "variant_type": "general",
                "description": "Test variant",
                "parameters": {"period": 14},
                "is_active": True
            }
        ]

        self.mock_indicator_engine.list_variants = MagicMock(return_value=mock_variants)

        response = self.client.get("/variants")

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "response"
        assert data["data"]["status"] == "variants_list"
        assert len(data["data"]["data"]["variants"]) == 1
        assert data["data"]["data"]["variants"][0]["name"] == "Test Variant"

    @pytest.mark.asyncio
    async def test_get_variants_with_type_filter(self):
        """Test variant listing with type filter"""
        mock_variants = [
            {
                "id": "variant-1",
                "name": "Risk Variant",
                "base_indicator_type": "RISK_LEVEL",
                "variant_type": "risk",
                "description": "Risk variant",
                "parameters": {"threshold": 0.5},
                "is_active": True
            }
        ]

        self.mock_indicator_engine.list_variants = MagicMock(return_value=mock_variants)

        response = self.client.get("/variants?type_filter=risk")

        assert response.status_code == 200
        self.mock_indicator_engine.list_variants.assert_called_once_with("risk")

    @pytest.mark.asyncio
    async def test_create_variant_success(self):
        """Test successful variant creation"""
        variant_data = {
            "name": "New Variant",
            "base_indicator_type": "VWAP",
            "variant_type": "price",
            "description": "New VWAP variant",
            "parameters": {"t1": 3600, "t2": 0},
            "created_by": "test_user"
        }

        self.mock_indicator_engine.create_variant = MagicMock(return_value="variant-123")

        response = self.client.post("/variants", json=variant_data)

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "response"
        assert data["data"]["status"] == "variant_created"
        assert data["data"]["data"]["variant_id"] == "variant-123"

        self.mock_indicator_engine.create_variant.assert_called_once_with(
            name="New Variant",
            base_indicator_type="VWAP",
            variant_type="price",
            description="New VWAP variant",
            parameters={"t1": 3600, "t2": 0},
            created_by="test_user",
            parameter_definitions=None
        )

    @pytest.mark.asyncio
    async def test_create_variant_validation_error(self):
        """Test variant creation with missing required fields"""
        incomplete_data = {
            "name": "Incomplete Variant"
            # Missing required fields
        }

        response = self.client.post("/variants", json=incomplete_data)

        assert response.status_code == 400
        data = response.json()
        assert data["type"] == "error"
        assert "validation_error" in data["error_code"]

    @pytest.mark.asyncio
    async def test_update_variant_success(self):
        """Test successful variant update"""
        variant_id = "variant-123"
        update_data = {
            "parameters": {"period": 21}
        }

        self.mock_indicator_engine.update_variant_parameters = MagicMock(return_value=True)

        response = self.client.put(f"/variants/{variant_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "response"
        assert data["data"]["status"] == "variant_updated"
        assert data["data"]["data"]["variant_id"] == variant_id

        self.mock_indicator_engine.update_variant_parameters.assert_called_once_with(
            variant_id, {"period": 21}
        )

    @pytest.mark.asyncio
    async def test_update_variant_not_found(self):
        """Test variant update for non-existent variant"""
        variant_id = "non-existent"
        update_data = {
            "parameters": {"period": 21}
        }

        self.mock_indicator_engine.update_variant_parameters = MagicMock(return_value=False)

        response = self.client.put(f"/variants/{variant_id}", json=update_data)

        assert response.status_code == 404
        data = response.json()
        assert data["type"] == "error"
        assert "not_found" in data["error_code"]

    @pytest.mark.asyncio
    async def test_delete_variant_success(self):
        """Test successful variant deletion"""
        variant_id = "variant-123"

        self.mock_indicator_engine.delete_variant = MagicMock(return_value=True)

        response = self.client.delete(f"/variants/{variant_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "response"
        assert data["data"]["status"] == "variant_deleted"
        assert data["data"]["data"]["variant_id"] == variant_id

        self.mock_indicator_engine.delete_variant.assert_called_once_with(variant_id)

    @pytest.mark.asyncio
    async def test_delete_variant_not_found(self):
        """Test variant deletion for non-existent variant"""
        variant_id = "non-existent"

        self.mock_indicator_engine.delete_variant = MagicMock(return_value=False)

        response = self.client.delete(f"/variants/{variant_id}")

        assert response.status_code == 404
        data = response.json()
        assert data["type"] == "error"
        assert "not_found" in data["error_code"]

    @pytest.mark.asyncio
    async def test_variant_endpoints_service_unavailable(self):
        """Test variant endpoints when service is unavailable"""
        # Mock service unavailable
        app.state.rest_service.get_controller = AsyncMock(side_effect=Exception("Service unavailable"))

        response = self.client.get("/variants")

        assert response.status_code == 400  # This is expected based on the current implementation
        data = response.json()
        assert data["type"] == "error"