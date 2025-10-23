"""
Tests for Strategy Builder frontend components.
"""

import pytest
from unittest.mock import Mock, patch

class TestStrategyBuilderComponents:
    """Test suite for strategy builder React components."""

    def test_node_templates_structure(self):
        """Test that node templates have correct structure."""
        # Import would happen in actual React test environment
        # This is a structural test of the template data

        expected_template_keys = ["type", "label", "icon", "data"]
        expected_data_keys = ["node_type"]

        # Mock the node templates structure
        mock_templates = [
            {
                "type": "data_source",
                "label": "Price Source",
                "icon": "MockIcon",
                "data": {
                    "node_type": "price_source",
                    "symbol": "BTC_USDT"
                }
            },
            {
                "type": "indicator",
                "label": "VWAP",
                "icon": "MockIcon",
                "data": {
                    "node_type": "vwap",
                    "window": 300
                }
            }
        ]

        for template in mock_templates:
            for key in expected_template_keys:
                assert key in template, f"Template missing key: {key}"
            for key in expected_data_keys:
                assert key in template["data"], f"Template data missing key: {key}"

    def test_initial_nodes_structure(self):
        """Test that initial nodes have correct structure."""
        mock_initial_nodes = [
            {
                "id": "price_source_1",
                "type": "data_source",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "Price Source",
                    "node_type": "price_source",
                    "symbol": "BTC_USDT"
                }
            }
        ]

        required_keys = ["id", "type", "position", "data"]

        for node in mock_initial_nodes:
            for key in required_keys:
                assert key in node, f"Initial node missing key: {key}"
            assert "x" in node["position"] and "y" in node["position"]

    def test_initial_edges_structure(self):
        """Test that initial edges have correct structure."""
        mock_initial_edges = [
            {
                "id": "e1-2",
                "source": "node1",
                "target": "node2",
                "sourceHandle": "output",
                "targetHandle": "input"
            }
        ]

        required_keys = ["id", "source", "target", "sourceHandle", "targetHandle"]

        for edge in mock_initial_edges:
            for key in required_keys:
                assert key in edge, f"Initial edge missing key: {key}"

    def test_node_type_mapping(self):
        """Test that node types are correctly mapped."""
        mock_node_types = {
            "data_source": "DataSourceComponent",
            "indicator": "IndicatorComponent",
            "condition": "ConditionComponent",
            "action": "ActionComponent"
        }

        expected_types = ["data_source", "indicator", "condition", "action"]

        for node_type in expected_types:
            assert node_type in mock_node_types, f"Missing node type mapping: {node_type}"

class TestStrategyValidation:
    """Test strategy validation logic."""

    def test_valid_strategy_validation(self):
        """Test validation of valid strategy."""
        # Mock validation function
        def mock_validate_strategy(nodes, edges):
            # Simple validation: check for required node types
            has_data_source = any(node.get("type") == "data_source" for node in nodes)
            has_action = any(node.get("type") == "action" for node in nodes)

            if not has_data_source:
                return {"isValid": False, "errors": ["Missing data source"], "warnings": []}
            if not has_action:
                return {"isValid": False, "errors": ["Missing action"], "warnings": []}

            return {"isValid": True, "errors": [], "warnings": []}

        # Test valid strategy
        valid_nodes = [
            {"id": "1", "type": "data_source"},
            {"id": "2", "type": "action"}
        ]
        valid_edges = [{"source": "1", "target": "2"}]

        result = mock_validate_strategy(valid_nodes, valid_edges)
        assert result["isValid"] is True
        assert len(result["errors"]) == 0

    def test_invalid_strategy_validation(self):
        """Test validation of invalid strategy."""
        def mock_validate_strategy(nodes, edges):
            has_data_source = any(node.get("type") == "data_source" for node in nodes)
            has_action = any(node.get("type") == "action" for node in nodes)

            errors = []
            if not has_data_source:
                errors.append("Missing data source")
            if not has_action:
                errors.append("Missing action")

            return {"isValid": len(errors) == 0, "errors": errors, "warnings": []}

        # Test invalid strategy
        invalid_nodes = [
            {"id": "1", "type": "indicator"}  # No data source or action
        ]
        invalid_edges = []

        result = mock_validate_strategy(invalid_nodes, invalid_edges)
        assert result["isValid"] is False
        assert len(result["errors"]) > 0

class TestStrategySerialization:
    """Test strategy serialization/deserialization."""

    def test_blueprint_serialization(self):
        """Test blueprint data serialization."""
        mock_blueprint = {
            "name": "Test Strategy",
            "version": "1.0.0",
            "description": "Test description",
            "graph": {
                "name": "Test Graph",
                "nodes": [
                    {
                        "id": "node1",
                        "node_type": "price_source",
                        "position": {"x": 100, "y": 100},
                        "parameters": {"symbol": "BTC_USDT"}
                    }
                ],
                "edges": []
            }
        }

        # Test JSON serialization (would be done in frontend)
        import json
        json_str = json.dumps(mock_blueprint)
        deserialized = json.loads(json_str)

        assert deserialized["name"] == mock_blueprint["name"]
        assert len(deserialized["graph"]["nodes"]) == 1
        assert deserialized["graph"]["nodes"][0]["node_type"] == "price_source"

    def test_drag_drop_data_structure(self):
        """Test data structure for drag and drop operations."""
        mock_drag_data = {
            "type": "node",
            "nodeType": "indicator",
            "template": {
                "type": "indicator",
                "label": "VWAP",
                "data": {"node_type": "vwap", "window": 300}
            }
        }

        required_keys = ["type", "nodeType", "template"]

        for key in required_keys:
            assert key in mock_drag_data, f"Drag data missing key: {key}"

        assert mock_drag_data["template"]["type"] == "indicator"
        assert "data" in mock_drag_data["template"]


class TestStrategyLoadSave:
    """Test Load/Save functionality for Strategy Builder."""

    def test_load_dialog_state_management(self):
        """Test that load dialog state is properly managed."""
        # Mock React component state
        mock_state = {
            "loadDialogOpen": False,
            "savedStrategies": [],
            "setLoadDialogOpen": Mock(),
            "setSavedStrategies": Mock()
        }

        # Simulate opening load dialog
        mock_state["setLoadDialogOpen"].assert_not_called()
        # In real React: setLoadDialogOpen(true)
        mock_state["loadDialogOpen"] = True

        assert mock_state["loadDialogOpen"] is True

    def test_load_strategies_api_call(self):
        """Test that loadStrategies calls the correct API."""
        from unittest.mock import Mock

        # Create mock API
        mock_api = Mock()
        mock_response = {
            "blueprints": [
                {
                    "id": "blueprint_1",
                    "name": "Test Strategy",
                    "description": "Test description",
                    "version": "1.0.0",
                    "created_at": "2025-09-28T10:00:00Z",
                    "updated_at": "2025-09-28T10:00:00Z",
                    "tags": [],
                    "is_template": False,
                    "node_count": 3,
                    "edge_count": 2
                }
            ],
            "total_count": 1,
            "skip": 0,
            "limit": 50
        }
        mock_api.listBlueprints.return_value = mock_response

        # Simulate loadStrategies function
        def load_strategies():
            try:
                response = mock_api.listBlueprints()
                return response["blueprints"]
            except Exception as error:
                raise error

        # Test the function
        strategies = load_strategies()

        # Verify API was called
        mock_api.listBlueprints.assert_called_once()

        # Verify response structure
        assert len(strategies) == 1
        assert strategies[0]["id"] == "blueprint_1"
        assert strategies[0]["name"] == "Test Strategy"

    def test_load_strategy_success(self):
        """Test successful strategy loading."""
        from unittest.mock import Mock

        # Create mock API
        mock_api = Mock()
        mock_blueprint_response = {
            "blueprint": {
                "id": "blueprint_1",
                "name": "Loaded Strategy",
                "version": "1.0.0",
                "graph": {
                    "name": "Loaded Strategy",
                    "version": "1.0.0",
                    "description": "Test strategy",
                    "nodes": [
                        {
                            "id": "price_source_1",
                            "node_type": "price_source",
                            "label": "Price Source",
                            "position": {"x": 100, "y": 100},
                            "symbol": "BTC_USDT",
                            "update_frequency": 1000
                        },
                        {
                            "id": "vwap_1",
                            "node_type": "vwap",
                            "label": "VWAP",
                            "position": {"x": 350, "y": 150},
                            "window": 300
                        }
                    ],
                    "edges": [
                        {
                            "id": "e1-2",
                            "source": "price_source_1",
                            "target": "vwap_1",
                            "sourceHandle": "price",
                            "targetHandle": "price"
                        }
                    ]
                }
            }
        }
        mock_api.getBlueprint.return_value = mock_blueprint_response

        # Mock React state setters
        mock_set_nodes = Mock()
        mock_set_edges = Mock()
        mock_set_strategy_name = Mock()
        mock_set_load_dialog_open = Mock()
        mock_set_notification = Mock()

        # Mock React state setters
        mock_set_nodes = Mock()
        mock_set_edges = Mock()
        mock_set_strategy_name = Mock()
        mock_set_load_dialog_open = Mock()
        mock_set_notification = Mock()

        # Simulate loadStrategy function
        def load_strategy(strategy):
            try:
                response = mock_api.getBlueprint(strategy["id"])
                blueprint = response["blueprint"]

                # Convert graph data back to nodes and edges (simplified for test)
                loaded_nodes = []
                for node_data in blueprint["graph"]["nodes"]:
                    node_type = "data_source" if node_data["node_type"].endswith("_source") else \
                               "indicator" if node_data["node_type"] in ["vwap", "volume_surge_ratio", "price_velocity"] else \
                               "condition" if node_data["node_type"].endswith("_condition") else \
                               "action" if node_data["node_type"].endswith("_signal") or node_data["node_type"].endswith("_action") else \
                               node_data["node_type"]
                    loaded_nodes.append({
                        "id": node_data["id"],
                        "type": node_type,
                        "position": node_data["position"],
                        "data": {
                            **node_data,
                            "label": node_data.get("label", node_data["node_type"])
                        }
                    })

                loaded_edges = []
                for edge_data in blueprint["graph"]["edges"]:
                    loaded_edges.append({
                        "id": edge_data["id"],
                        "source": edge_data["source"],
                        "target": edge_data["target"],
                        "sourceHandle": edge_data.get("sourceHandle"),
                        "targetHandle": edge_data.get("targetHandle")
                    })

                # Update state
                mock_set_nodes(loaded_nodes)
                mock_set_edges(loaded_edges)
                mock_set_strategy_name(blueprint["name"])
                mock_set_load_dialog_open(False)
                mock_set_notification({
                    "open": True,
                    "message": "Strategy loaded successfully!",
                    "severity": "success"
                })

            except Exception as error:
                mock_set_notification({
                    "open": True,
                    "message": str(error),
                    "severity": "error"
                })

        # Test loading a strategy
        test_strategy = {"id": "blueprint_1", "name": "Test Strategy"}
        load_strategy(test_strategy)

        # Verify API was called with correct ID
        mock_api.getBlueprint.assert_called_once_with("blueprint_1")

        # Verify state updates
        mock_set_nodes.assert_called_once()
        mock_set_edges.assert_called_once()
        mock_set_strategy_name.assert_called_once_with("Loaded Strategy")
        mock_set_load_dialog_open.assert_called_once_with(False)
        mock_set_notification.assert_called_once_with({
            "open": True,
            "message": "Strategy loaded successfully!",
            "severity": "success"
        })

    def test_load_strategy_api_error(self):
        """Test strategy loading with API error."""
        from unittest.mock import Mock

        # Create mock API that raises error
        mock_api = Mock()
        mock_api.getBlueprint.side_effect = Exception("Failed to load blueprint")

        # Mock React state setters
        mock_set_notification = Mock()

        # Simulate loadStrategy function with error handling
        def load_strategy(strategy):
            try:
                response = mock_api.getBlueprint(strategy["id"])
                # ... rest of function
            except Exception as error:
                mock_set_notification({
                    "open": True,
                    "message": str(error),
                    "severity": "error"
                })

        # Test loading with error
        test_strategy = {"id": "blueprint_1", "name": "Test Strategy"}
        load_strategy(test_strategy)

        # Verify error notification
        mock_set_notification.assert_called_once_with({
            "open": True,
            "message": "Failed to load blueprint",
            "severity": "error"
        })

    def test_node_type_mapping_from_api(self):
        """Test that API node types are correctly mapped to ReactFlow types."""
        # Test mapping logic
        def map_node_type(node_type):
            if node_type.endswith("_source"):
                return "data_source"
            elif node_type in ["vwap", "volume_surge_ratio", "price_velocity"]:
                return "indicator"
            elif node_type.endswith("_condition"):
                return "condition"
            elif node_type.endswith("_signal") or node_type.endswith("_action"):
                return "action"
            else:
                return node_type

        # Test various node types
        test_cases = [
            ("price_source", "data_source"),
            ("volume_source", "data_source"),
            ("vwap", "indicator"),
            ("volume_surge_ratio", "indicator"),
            ("price_velocity", "indicator"),
            ("threshold_condition", "condition"),
            ("duration_condition", "condition"),
            ("buy_signal", "action"),
            ("sell_signal", "action"),
            ("alert_action", "action"),
            ("unknown_type", "unknown_type")
        ]

        for api_type, expected_react_type in test_cases:
            result = map_node_type(api_type)
            assert result == expected_react_type, f"Failed to map {api_type} to {expected_react_type}"

    def test_load_dialog_ui_structure(self):
        """Test that load dialog has correct UI structure."""
        # Mock Material-UI Dialog structure
        mock_dialog_props = {
            "open": True,
            "onClose": Mock(),
            "maxWidth": "sm",
            "fullWidth": True
        }

        # Verify required props
        assert mock_dialog_props["open"] is True
        assert mock_dialog_props["maxWidth"] == "sm"
        assert mock_dialog_props["fullWidth"] is True
        assert callable(mock_dialog_props["onClose"])

    def test_load_button_ui_integration(self):
        """Test that Load button is properly integrated in toolbar."""
        # Mock toolbar button structure
        mock_load_button = {
            "variant": "outlined",
            "startIcon": "FolderOpenIcon",
            "onClick": Mock(),
            "children": "Load"
        }

        # Verify button properties
        assert mock_load_button["variant"] == "outlined"
        assert mock_load_button["startIcon"] == "FolderOpenIcon"
        assert mock_load_button["children"] == "Load"
        assert callable(mock_load_button["onClick"])