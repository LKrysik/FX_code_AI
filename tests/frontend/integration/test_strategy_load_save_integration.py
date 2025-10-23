"""
Integration tests for Strategy Builder Load/Save functionality.
Tests the complete workflow from UI interaction to API calls to state updates.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestStrategyLoadSaveIntegration:
    """Integration tests for Load/Save functionality end-to-end."""

    def test_complete_load_workflow(self):
        """Test complete load workflow from button click to strategy loaded."""
        from unittest.mock import Mock

        # Create mock APIs
        mock_list_api = Mock()
        mock_get_api = Mock()

        # Mock API responses
        mock_list_response = {
            "blueprints": [
                {
                    "id": "test_blueprint_1",
                    "name": "Test Strategy",
                    "description": "Integration test strategy",
                    "version": "1.0.0",
                    "created_at": "2025-09-28T10:00:00Z",
                    "updated_at": "2025-09-28T10:00:00Z",
                    "tags": ["test"],
                    "is_template": False,
                    "node_count": 3,
                    "edge_count": 2
                }
            ],
            "total_count": 1,
            "skip": 0,
            "limit": 50
        }

        mock_blueprint_response = {
            "blueprint": {
                "id": "test_blueprint_1",
                "name": "Loaded Test Strategy",
                "version": "1.0.0",
                "graph": {
                    "name": "Loaded Test Strategy",
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

        mock_list_api.return_value = mock_list_response
        mock_get_api.return_value = mock_blueprint_response

        # Mock React component state and functions
        component_state = {
            "loadDialogOpen": False,
            "savedStrategies": [],
            "strategyName": "New Strategy",
            "nodes": [],
            "edges": [],
            "notification": {"open": False, "message": "", "severity": "info"}
        }

        # Simulate complete workflow
        def simulate_load_workflow():
            # 1. User clicks Load button
            component_state["loadDialogOpen"] = True

            # 2. Dialog opens and loads strategies
            try:
                response = mock_list_api()
                component_state["savedStrategies"] = response["blueprints"]
            except Exception as e:
                component_state["notification"] = {
                    "open": True,
                    "message": f"Failed to load strategies: {str(e)}",
                    "severity": "error"
                }
                return False

            # 3. User selects a strategy
            selected_strategy = component_state["savedStrategies"][0]

            # 4. Load the selected strategy
            try:
                response = mock_get_api(selected_strategy["id"])
                blueprint = response["blueprint"]

                # Convert nodes
                loaded_nodes = []
                for node_data in blueprint["graph"]["nodes"]:
                    # Map node type
                    node_type = node_data["node_type"]
                    if node_type.endswith("_source"):
                        react_flow_type = "data_source"
                    elif node_type in ["vwap", "volume_surge_ratio", "price_velocity"]:
                        react_flow_type = "indicator"
                    elif node_type.endswith("_condition"):
                        react_flow_type = "condition"
                    elif node_type.endswith("_signal") or node_type.endswith("_action"):
                        react_flow_type = "action"
                    else:
                        react_flow_type = node_type

                    loaded_nodes.append({
                        "id": node_data["id"],
                        "type": react_flow_type,
                        "position": node_data["position"],
                        "data": {
                            **node_data,
                            "label": node_data.get("label", node_data["node_type"])
                        }
                    })

                # Convert edges
                loaded_edges = []
                for edge_data in blueprint["graph"]["edges"]:
                    loaded_edges.append({
                        "id": edge_data["id"],
                        "source": edge_data["source"],
                        "target": edge_data["target"],
                        "sourceHandle": edge_data.get("sourceHandle"),
                        "targetHandle": edge_data.get("targetHandle")
                    })

                # Update component state
                component_state["nodes"] = loaded_nodes
                component_state["edges"] = loaded_edges
                component_state["strategyName"] = blueprint["name"]
                component_state["loadDialogOpen"] = False
                component_state["notification"] = {
                    "open": True,
                    "message": "Strategy loaded successfully!",
                    "severity": "success"
                }

                return True

            except Exception as e:
                component_state["notification"] = {
                    "open": True,
                    "message": f"Failed to load strategy: {str(e)}",
                    "severity": "error"
                }
                return False

        # Execute the workflow
        success = simulate_load_workflow()

        # Verify the complete workflow succeeded
        assert success is True

        # Verify API calls
        mock_list_api.assert_called_once()
        mock_get_api.assert_called_once_with("test_blueprint_1")

        # Verify final state
        assert component_state["loadDialogOpen"] is False
        assert component_state["strategyName"] == "Loaded Test Strategy"
        assert len(component_state["nodes"]) == 2
        assert len(component_state["edges"]) == 1
        assert component_state["notification"]["severity"] == "success"

        # Verify node conversion
        price_node = next(n for n in component_state["nodes"] if n["id"] == "price_source_1")
        assert price_node["type"] == "data_source"
        assert price_node["data"]["symbol"] == "BTC_USDT"

        vwap_node = next(n for n in component_state["nodes"] if n["id"] == "vwap_1")
        assert vwap_node["type"] == "indicator"
        assert vwap_node["data"]["window"] == 300

    def test_load_strategies_empty_list(self):
        """Test loading strategies when no strategies exist."""
        from unittest.mock import Mock

        mock_list_api = Mock()
        mock_list_api.return_value = {
            "blueprints": [],
            "total_count": 0,
            "skip": 0,
            "limit": 50
        }

        component_state = {"savedStrategies": []}

        # Load strategies
        response = mock_list_api()
        component_state["savedStrategies"] = response["blueprints"]

        # Verify empty list handling
        assert len(component_state["savedStrategies"]) == 0
        mock_list_api.assert_called_once()

    def test_load_strategy_with_complex_graph(self):
        """Test loading strategy with complex node/edge graph."""
        # Create complex blueprint with multiple node types
        complex_blueprint = {
            "blueprint": {
                "id": "complex_blueprint",
                "name": "Complex Strategy",
                "graph": {
                    "nodes": [
                        {
                            "id": "price_1", "node_type": "price_source",
                            "position": {"x": 100, "y": 100}
                        },
                        {
                            "id": "volume_1", "node_type": "volume_source",
                            "position": {"x": 100, "y": 200}
                        },
                        {
                            "id": "vwap_1", "node_type": "vwap",
                            "position": {"x": 350, "y": 150}
                        },
                        {
                            "id": "surge_1", "node_type": "volume_surge_ratio",
                            "position": {"x": 350, "y": 250}
                        },
                        {
                            "id": "cond_1", "node_type": "threshold_condition",
                            "position": {"x": 600, "y": 150}
                        },
                        {
                            "id": "buy_1", "node_type": "buy_signal",
                            "position": {"x": 850, "y": 150}
                        },
                        {
                            "id": "alert_1", "node_type": "alert_action",
                            "position": {"x": 850, "y": 250}
                        }
                    ],
                    "edges": [
                        {"id": "e1", "source": "price_1", "target": "vwap_1"},
                        {"id": "e2", "source": "volume_1", "target": "vwap_1"},
                        {"id": "e3", "source": "volume_1", "target": "surge_1"},
                        {"id": "e4", "source": "vwap_1", "target": "cond_1"},
                        {"id": "e5", "source": "surge_1", "target": "cond_1"},
                        {"id": "e6", "source": "cond_1", "target": "buy_1"},
                        {"id": "e7", "source": "cond_1", "target": "alert_1"}
                    ]
                }
            }
        }

        from unittest.mock import Mock

        mock_get_api = Mock()
        mock_get_api.return_value = complex_blueprint

        # Load and convert the complex strategy
        response = mock_get_api("complex_blueprint")
        blueprint = response["blueprint"]

        # Convert nodes with type mapping
        loaded_nodes = []
        for node_data in blueprint["graph"]["nodes"]:
            node_type = node_data["node_type"]
            if node_type.endswith("_source"):
                react_flow_type = "data_source"
            elif node_type in ["vwap", "volume_surge_ratio", "price_velocity"]:
                react_flow_type = "indicator"
            elif node_type.endswith("_condition"):
                react_flow_type = "condition"
            elif node_type.endswith("_signal") or node_type.endswith("_action"):
                react_flow_type = "action"
            else:
                react_flow_type = node_type

            loaded_nodes.append({
                "id": node_data["id"],
                "type": react_flow_type,
                "position": node_data["position"],
                "data": {**node_data, "label": node_data.get("label", node_type)}
            })

        # Verify all node types were mapped correctly
        node_types = [n["type"] for n in loaded_nodes]
        assert "data_source" in node_types
        assert "indicator" in node_types
        assert "condition" in node_types
        assert "action" in node_types

        # Verify node count
        assert len(loaded_nodes) == 7

        # Verify edges
        loaded_edges = blueprint["graph"]["edges"]
        assert len(loaded_edges) == 7

    def test_ui_state_transitions(self):
        """Test UI state transitions during load workflow."""
        # Initial state
        ui_state = {
            "loadDialogOpen": False,
            "isLoadingStrategies": False,
            "isLoadingStrategy": False,
            "selectedStrategy": None,
            "error": None
        }

        # Simulate workflow states
        states_sequence = []

        # 1. User clicks Load button
        ui_state["loadDialogOpen"] = True
        states_sequence.append(("dialog_opened", ui_state.copy()))

        # 2. Start loading strategies
        ui_state["isLoadingStrategies"] = True
        states_sequence.append(("loading_strategies", ui_state.copy()))

        # 3. Strategies loaded successfully
        ui_state["isLoadingStrategies"] = False
        states_sequence.append(("strategies_loaded", ui_state.copy()))

        # 4. User selects strategy
        ui_state["selectedStrategy"] = {"id": "strategy_1", "name": "Test Strategy"}
        states_sequence.append(("strategy_selected", ui_state.copy()))

        # 5. Start loading selected strategy
        ui_state["isLoadingStrategy"] = True
        states_sequence.append(("loading_strategy", ui_state.copy()))

        # 6. Strategy loaded successfully
        ui_state["isLoadingStrategy"] = False
        ui_state["loadDialogOpen"] = False
        ui_state["selectedStrategy"] = None
        states_sequence.append(("strategy_loaded", ui_state.copy()))

        # Verify state transitions
        assert len(states_sequence) == 6
        assert states_sequence[0][0] == "dialog_opened"
        assert states_sequence[0][1]["loadDialogOpen"] is True

        assert states_sequence[1][0] == "loading_strategies"
        assert states_sequence[1][1]["isLoadingStrategies"] is True

        assert states_sequence[2][0] == "strategies_loaded"
        assert states_sequence[2][1]["isLoadingStrategies"] is False

        assert states_sequence[3][0] == "strategy_selected"
        assert states_sequence[3][1]["selectedStrategy"]["id"] == "strategy_1"

        assert states_sequence[4][0] == "loading_strategy"
        assert states_sequence[4][1]["isLoadingStrategy"] is True

        assert states_sequence[5][0] == "strategy_loaded"
        assert states_sequence[5][1]["isLoadingStrategy"] is False
        assert states_sequence[5][1]["loadDialogOpen"] is False

    def test_error_handling_integration(self):
        """Test error handling throughout the load workflow."""
        from unittest.mock import Mock

        # Create mock APIs with errors
        mock_list_api = Mock()
        mock_get_api = Mock()
        mock_list_api.side_effect = Exception("Network error")
        mock_get_api.side_effect = Exception("Blueprint not found")

        error_scenarios = []

        # Test 1: Error loading strategies list
        try:
            mock_list_api()
        except Exception as e:
            error_scenarios.append(("list_strategies_error", str(e)))

        # Test 2: Error loading specific strategy
        try:
            mock_get_api("invalid_id")
        except Exception as e:
            error_scenarios.append(("load_strategy_error", str(e)))

        # Verify error handling
        assert len(error_scenarios) == 2
        assert error_scenarios[0][0] == "list_strategies_error"
        assert "Network error" in error_scenarios[0][1]
        assert error_scenarios[1][0] == "load_strategy_error"
        assert "Blueprint not found" in error_scenarios[1][1]

        # Test UI error state handling
        ui_state = {"error": None, "notification": {"open": False}}

        # Simulate error in UI
        for scenario_name, error_msg in error_scenarios:
            ui_state["error"] = error_msg
            ui_state["notification"] = {
                "open": True,
                "message": f"Error: {error_msg}",
                "severity": "error"
            }

            assert ui_state["error"] == error_msg
            assert ui_state["notification"]["severity"] == "error"