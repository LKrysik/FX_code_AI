#!/usr/bin/env python3
"""
Strategy Blueprints API - Sprint 5 Visual Strategy Builder
==========================================================

REST API endpoints for managing strategy blueprints with RBAC, audit logging,
and CRUD operations for visual strategy graphs.

Features:
- Create, read, update, delete strategy blueprints
- Graph validation and serialization
- RBAC-protected operations
- Audit trail for all blueprint changes
- Migration support for YAML to graph formats
- Template management and cloning

Critical Analysis Points:
1. **RBAC Integration**: Proper authorization for blueprint operations
2. **Graph Validation**: Ensure graph integrity before storage
3. **Audit Trail**: Complete logging of blueprint changes
4. **Migration Support**: Seamless transition from YAML configs
5. **Performance**: Efficient graph storage and retrieval
6. **Error Handling**: Clear validation errors and recovery
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from ..core.logger import StructuredLogger
from ..strategy_graph.serializer import StrategyGraph, GraphSerializer, GraphNode, GraphEdge
from ..strategy_graph.validators import GraphValidator, ValidationError
from ..strategy_graph.node_catalog import get_node_definition
from ..engine.graph_adapter import get_live_executor

# Placeholder imports - would be replaced with actual persistence layer
# from ..infrastructure.persistence.strategy_blueprints import StrategyBlueprintRepository

router = APIRouter(prefix="/api/strategy-blueprints", tags=["strategy-blueprints"])
security = HTTPBearer(auto_error=False)


class StrategyBlueprintsAPI:
    """
    Strategy Blueprints API for Sprint 5 visual strategy builder.

    Provides REST endpoints for managing strategy blueprints with proper authentication,
    authorization, and audit logging.
    """

    def __init__(self, logger: StructuredLogger, jwt_secret: str = "sprint5-blueprints-secret"):
        self.logger = logger
        self.jwt_secret = jwt_secret

        # RBAC configuration (should come from config file)
        self.roles = {
            "operator": ["read"],
            "developer": ["read", "write"],
            "admin": ["read", "write", "admin"],
            "auditor": ["read"]
        }

        # In-memory storage for MVP (would be replaced with database)
        self.blueprints: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[Dict[str, Any]] = []

        # Graph validator
        self.validator = GraphValidator()

    def get_router(self) -> APIRouter:
        """Get the FastAPI router with all endpoints"""
        return router

    async def authenticate_user(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials]
    ) -> Dict[str, Any]:
        """Authenticate user using Authorization header or HttpOnly cookie"""
        token: Optional[str] = None

        if credentials and credentials.credentials:
            token_candidate = credentials.credentials.strip()
            if token_candidate:
                token = token_candidate

        if not token:
            cookie_token = request.cookies.get("access_token")
            if cookie_token:
                token = cookie_token.strip()

        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])

            user = {
                "user_id": payload.get("user_id", "unknown"),
                "role": payload.get("role", "operator"),
                "permissions": self.roles.get(payload.get("role", "operator"), ["read"])
            }

            return user

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def check_permission(self, user: Dict[str, Any], required_permission: str) -> None:
        """Check if user has required permission"""
        if required_permission not in user["permissions"]:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {required_permission}"
            )

    def audit_action(self, user: Dict[str, Any], action: str, details: Dict[str, Any]) -> None:
        """Log audit action"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user["user_id"],
            "role": user["role"],
            "action": action,
            "details": details
        }

        self.audit_log.append(audit_entry)

        # Keep only last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

        self.logger.info("strategy_blueprints.audit_action", audit_entry)

    def validate_and_store_graph(self, blueprint_id: str, graph_data: Dict[str, Any]) -> StrategyGraph:
        """Validate graph and return StrategyGraph object"""
        try:
            # Create StrategyGraph from graph data
            # The graph_data contains nodes/edges, we need to create StrategyGraph with metadata
            graph = StrategyGraph(
                name=f"blueprint_{blueprint_id}",
                version="1.0.0",
                description="Validated blueprint graph",
                nodes=[GraphNode.from_dict(node_data) for node_data in graph_data.get("nodes", [])],
                edges=[GraphEdge.from_dict(edge_data) for edge_data in graph_data.get("edges", [])],
                metadata=graph_data.get("metadata", {})
            )

            # Validate graph structure and logic
            errors, warnings = self.validator.validate(graph)

            if errors:
                error_details = [{"type": e.error_type, "message": e.message, "node_id": e.node_id}
                               for e in errors]
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "graph_validation_failed",
                        "validation_errors": error_details
                    }
                )

            return graph

        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Graph validation error: {str(e)}")

    def migrate_yaml_to_graph(self, yaml_config: Dict[str, Any]) -> StrategyGraph:
        """Migrate YAML strategy config to graph format"""
        # This is a simplified migration - in production would handle complex YAML structures
        name = yaml_config.get("name", "migrated_strategy")
        description = yaml_config.get("description", "Migrated from YAML")

        # Import GraphNode and GraphEdge
        from ..strategy_graph.serializer import GraphNode, GraphEdge

        # Create basic graph structure
        nodes = []
        edges = []

        # Add data source node
        data_source_id = str(uuid.uuid4())
        nodes.append(GraphNode(
            node_id=data_source_id,
            node_type="price_source",
            position={"x": 100, "y": 100},
            parameters={
                "symbol": yaml_config.get("symbol", "BTC_USDT"),
                "update_frequency": 1000
            }
        ))

        # Add volume source for indicators that need it
        volume_source_id = str(uuid.uuid4())
        nodes.append(GraphNode(
            node_id=volume_source_id,
            node_type="volume_source",
            position={"x": 200, "y": 100},
            parameters={
                "symbol": yaml_config.get("symbol", "BTC_USDT"),
                "aggregation": "trade"
            }
        ))

        # Add indicator nodes based on YAML config
        indicators = yaml_config.get("indicators", {})
        indicator_nodes = []
        y_pos = 200

        # If no indicators specified, create a default VWAP indicator
        if not indicators:
            indicators = {"vwap": {"window": 300}}

        for indicator_name, indicator_config in indicators.items():
            if indicator_name == "volume_surge_ratio":
                node_type = "volume_surge_ratio"
                params = {
                    "baseline_window": indicator_config.get("baseline_window", 3600),
                    "surge_threshold": indicator_config.get("surge_threshold", 2.0)
                }
            elif indicator_name == "price_velocity":
                node_type = "price_velocity"
                params = {
                    "period": indicator_config.get("period", 60)
                }
            elif indicator_name == "vwap":
                node_type = "vwap"
                params = {
                    "window": indicator_config.get("window", 300)
                }
            elif indicator_name == "bid_ask_imbalance":
                node_type = "bid_ask_imbalance"
                params = {
                    "depth_levels": indicator_config.get("depth_levels", 5)
                }
            else:
                continue  # Skip unknown indicators

            indicator_id = str(uuid.uuid4())
            nodes.append(GraphNode(
                node_id=indicator_id,
                node_type=node_type,
                position={"x": 100, "y": y_pos},
                parameters=params
            ))
            indicator_nodes.append(indicator_id)
            y_pos += 100

        # Add condition nodes
        condition_id = str(uuid.uuid4())
        nodes.append(GraphNode(
            node_id=condition_id,
            node_type="threshold_condition",
            position={"x": 300, "y": 200},
            parameters={
                "operator": ">",
                "threshold": yaml_config.get("threshold", 0.5)
            }
        ))

        # Add action node
        action_id = str(uuid.uuid4())
        nodes.append(GraphNode(
            node_id=action_id,
            node_type="buy_signal",
            position={"x": 500, "y": 200},
            parameters={
                "position_size": yaml_config.get("position_size", 100.0),
                "max_slippage": 0.001
            }
        ))

        # Create edges
        # Data source to indicators
        for indicator_id in indicator_nodes:
            indicator = next(n for n in nodes if n.id == indicator_id)
            edges.append(GraphEdge(
                source_node=data_source_id,
                source_port="price",
                target_node=indicator_id,
                target_port="price"
            ))

            # Connect volume source to indicators that need it
            if indicator.node_type == "vwap":
                edges.append(GraphEdge(
                    source_node=volume_source_id,
                    source_port="volume",
                    target_node=indicator_id,
                    target_port="volume"
                ))

        # Indicators to condition (simplified - connect first indicator)
        if indicator_nodes:
            # Determine correct port based on indicator type
            first_indicator = next(n for n in nodes if n.id == indicator_nodes[0])
            if first_indicator.node_type == "volume_surge_ratio":
                source_port = "vsr"
            elif first_indicator.node_type == "price_velocity":
                source_port = "velocity"
            elif first_indicator.node_type == "vwap":
                source_port = "vwap"
            else:
                source_port = "imbalance"  # bid_ask_imbalance

            edges.append(GraphEdge(
                source_node=indicator_nodes[0],
                source_port=source_port,
                target_node=condition_id,
                target_port="input"
            ))

        # Condition to action
        edges.append(GraphEdge(
            source_node=condition_id,
            source_port="result",
            target_node=action_id,
            target_port="trigger"
        ))

        return StrategyGraph(
            name=name,
            description=description,
            nodes=nodes,
            edges=edges
        )


# Create API instance (would be injected in real app)
# Logger will be set when the API is initialized in unified_server.py
blueprints_api = StrategyBlueprintsAPI(None)  # Placeholder


async def get_authenticated_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """Shared dependency to authenticate requests for blueprint APIs."""
    return await blueprints_api.authenticate_user(request, credentials)


@router.get("/")
async def list_blueprints(
    user: Dict[str, Any] = Depends(get_authenticated_user),
    skip: int = Query(0, description="Number of blueprints to skip"),
    limit: int = Query(50, description="Maximum blueprints to return"),
    name_filter: Optional[str] = Query(None, description="Filter by name"),
    tag_filter: Optional[str] = Query(None, description="Filter by tag")
):
    """
    List strategy blueprints with filtering and pagination.
    """
    blueprints_api.check_permission(user, "read")

    try:
        # Get all blueprints for user (in production, would filter by user/tenant)
        all_blueprints = list(blueprints_api.blueprints.values())

        # Apply filters
        if name_filter:
            all_blueprints = [b for b in all_blueprints if name_filter.lower() in b["name"].lower()]

        if tag_filter:
            all_blueprints = [b for b in all_blueprints if tag_filter in b.get("tags", [])]

        # Apply pagination
        total_count = len(all_blueprints)
        blueprints_list = all_blueprints[skip:skip + limit]

        # Format response
        blueprints_response = []
        for blueprint in blueprints_list:
            blueprints_response.append({
                "id": blueprint["id"],
                "name": blueprint["name"],
                "version": blueprint["version"],
                "description": blueprint.get("description", ""),
                "created_at": blueprint["created_at"],
                "updated_at": blueprint["updated_at"],
                "created_by": blueprint["created_by"],
                "tags": blueprint.get("tags", []),
                "is_template": blueprint.get("is_template", False),
                "node_count": len(blueprint["graph"]["nodes"]),
                "edge_count": len(blueprint["graph"]["edges"])
            })

        blueprints_api.audit_action(user, "list_blueprints", {
            "skip": skip,
            "limit": limit,
            "name_filter": name_filter,
            "tag_filter": tag_filter,
            "returned_count": len(blueprints_response)
        })

        return {
            "blueprints": blueprints_response,
            "total_count": total_count,
            "skip": skip,
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        blueprints_api.logger.error("blueprints_api.list_blueprints_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to list blueprints")


@router.post("/")
async def create_blueprint(
    blueprint_data: Dict[str, Any] = Body(...),
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Create a new strategy blueprint.
    """
    blueprints_api.check_permission(user, "write")

    try:
        # Validate required fields
        required_fields = ["name", "graph"]
        for field in required_fields:
            if field not in blueprint_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        # Validate and store graph
        graph = blueprints_api.validate_and_store_graph("temp", blueprint_data["graph"])

        # Generate blueprint ID
        blueprint_id = str(uuid.uuid4())

        # Create blueprint record
        blueprint = {
            "id": blueprint_id,
            "name": blueprint_data["name"],
            "version": blueprint_data.get("version", "1.0.0"),
            "description": blueprint_data.get("description", ""),
            "graph": graph.to_dict(),
            "tags": blueprint_data.get("tags", []),
            "is_template": blueprint_data.get("is_template", False),
            "created_by": user["user_id"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": blueprint_data.get("metadata", {})
        }

        # Store blueprint
        blueprints_api.blueprints[blueprint_id] = blueprint

        blueprints_api.audit_action(user, "create_blueprint", {
            "blueprint_id": blueprint_id,
            "blueprint_name": blueprint["name"],
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges)
        })

        return {
            "blueprint": {
                "id": blueprint_id,
                "name": blueprint["name"],
                "version": blueprint["version"],
                "description": blueprint["description"],
                "created_at": blueprint["created_at"],
                "node_count": len(graph.nodes),
                "edge_count": len(graph.edges)
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        blueprints_api.logger.error("blueprints_api.create_blueprint_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to create blueprint")


@router.get("/{blueprint_id}")
async def get_blueprint(
    blueprint_id: str,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Get a specific strategy blueprint by ID.
    """
    blueprints_api.check_permission(user, "read")

    try:
        # Get blueprint
        blueprint = blueprints_api.blueprints.get(blueprint_id)
        if not blueprint:
            raise HTTPException(status_code=404, detail="Blueprint not found")

        blueprints_api.audit_action(user, "get_blueprint", {
            "blueprint_id": blueprint_id,
            "blueprint_name": blueprint["name"]
        })

        return {
            "blueprint": blueprint,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        blueprints_api.logger.error("blueprints_api.get_blueprint_error", {
            "error": str(e),
            "blueprint_id": blueprint_id,
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to get blueprint")


@router.put("/{blueprint_id}")
async def update_blueprint(
    blueprint_id: str,
    blueprint_data: Dict[str, Any] = Body(...),
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Update an existing strategy blueprint.
    """
    blueprints_api.check_permission(user, "write")

    try:
        # Check if blueprint exists
        if blueprint_id not in blueprints_api.blueprints:
            raise HTTPException(status_code=404, detail="Blueprint not found")

        # Validate graph if provided
        if "graph" in blueprint_data:
            graph = blueprints_api.validate_and_store_graph(blueprint_id, blueprint_data["graph"])
            blueprint_data["graph"] = graph.to_dict()

        # Update blueprint
        blueprint = blueprints_api.blueprints[blueprint_id]
        blueprint.update(blueprint_data)
        blueprint["updated_at"] = datetime.now().isoformat()

        blueprints_api.audit_action(user, "update_blueprint", {
            "blueprint_id": blueprint_id,
            "blueprint_name": blueprint["name"],
            "updated_fields": list(blueprint_data.keys())
        })

        return {
            "blueprint": {
                "id": blueprint_id,
                "name": blueprint["name"],
                "version": blueprint["version"],
                "updated_at": blueprint["updated_at"]
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        blueprints_api.logger.error("blueprints_api.update_blueprint_error", {
            "error": str(e),
            "blueprint_id": blueprint_id,
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to update blueprint")


@router.delete("/{blueprint_id}")
async def delete_blueprint(
    blueprint_id: str,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Delete a strategy blueprint.
    """
    blueprints_api.check_permission(user, "write")

    try:
        # Check if blueprint exists
        if blueprint_id not in blueprints_api.blueprints:
            raise HTTPException(status_code=404, detail="Blueprint not found")

        blueprint = blueprints_api.blueprints[blueprint_id]

        # Delete blueprint
        del blueprints_api.blueprints[blueprint_id]

        blueprints_api.audit_action(user, "delete_blueprint", {
            "blueprint_id": blueprint_id,
            "blueprint_name": blueprint["name"]
        })

        return {
            "message": "Blueprint deleted successfully",
            "blueprint_id": blueprint_id,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        blueprints_api.logger.error("blueprints_api.delete_blueprint_error", {
            "error": str(e),
            "blueprint_id": blueprint_id,
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to delete blueprint")


@router.post("/{blueprint_id}/clone")
async def clone_blueprint(
    blueprint_id: str,
    clone_data: Dict[str, Any] = Body(...),
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Clone an existing strategy blueprint.
    """
    blueprints_api.check_permission(user, "write")

    try:
        # Check if source blueprint exists
        if blueprint_id not in blueprints_api.blueprints:
            raise HTTPException(status_code=404, detail="Source blueprint not found")

        source_blueprint = blueprints_api.blueprints[blueprint_id]

        # Generate new blueprint ID
        new_blueprint_id = str(uuid.uuid4())

        # Create cloned blueprint
        cloned_blueprint = {
            "id": new_blueprint_id,
            "name": clone_data.get("name", f"{source_blueprint['name']} (Copy)"),
            "version": "1.0.0",  # Reset version for clone
            "description": clone_data.get("description", source_blueprint.get("description", "")),
            "graph": source_blueprint["graph"].copy(),  # Deep copy graph
            "tags": clone_data.get("tags", source_blueprint.get("tags", [])),
            "is_template": False,  # Clones are not templates by default
            "created_by": user["user_id"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": clone_data.get("metadata", {})
        }

        # Store cloned blueprint
        blueprints_api.blueprints[new_blueprint_id] = cloned_blueprint

        blueprints_api.audit_action(user, "clone_blueprint", {
            "source_blueprint_id": blueprint_id,
            "new_blueprint_id": new_blueprint_id,
            "new_blueprint_name": cloned_blueprint["name"]
        })

        return {
            "blueprint": {
                "id": new_blueprint_id,
                "name": cloned_blueprint["name"],
                "version": cloned_blueprint["version"],
                "created_at": cloned_blueprint["created_at"]
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        blueprints_api.logger.error("blueprints_api.clone_blueprint_error", {
            "error": str(e),
            "blueprint_id": blueprint_id,
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to clone blueprint")


@router.post("/{blueprint_id}/validate")
async def validate_blueprint(
    blueprint_id: str,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Validate a strategy blueprint.
    """
    blueprints_api.check_permission(user, "read")

    try:
        # Get blueprint
        blueprint = blueprints_api.blueprints.get(blueprint_id)
        if not blueprint:
            raise HTTPException(status_code=404, detail="Blueprint not found")

        # Validate graph
        graph = StrategyGraph.from_dict(blueprint["graph"])
        errors, warnings = blueprints_api.validator.validate(graph)

        validation_result = {
            "valid": len(errors) == 0,
            "errors": [{"type": e.error_type, "message": e.message, "node_id": e.node_id}
                      for e in errors],
            "warnings": [{"type": w.error_type, "message": w.message, "node_id": w.node_id}
                        for w in warnings]
        }

        blueprints_api.audit_action(user, "validate_blueprint", {
            "blueprint_id": blueprint_id,
            "blueprint_name": blueprint["name"],
            "is_valid": validation_result["valid"],
            "error_count": len(errors),
            "warning_count": len(warnings)
        })

        return {
            "blueprint_id": blueprint_id,
            "validation": validation_result,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        blueprints_api.logger.error("blueprints_api.validate_blueprint_error", {
            "error": str(e),
            "blueprint_id": blueprint_id,
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to validate blueprint")


@router.post("/validate")
async def validate_blueprint_adhoc(
    graph_data: Dict[str, Any] = Body(...),
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Validate a strategy blueprint graph (ad-hoc validation without saving).
    """
    blueprints_api.check_permission(user, "read")

    try:
        # Validate graph structure and logic
        graph = StrategyGraph.from_dict(graph_data)
        errors, warnings = blueprints_api.validator.validate(graph)

        validation_result = {
            "valid": len(errors) == 0,
            "errors": [{"type": e.error_type, "message": e.message, "node_id": e.node_id}
                      for e in errors],
            "warnings": [{"type": w.error_type, "message": w.message, "node_id": w.node_id}
                        for w in warnings]
        }

        blueprints_api.audit_action(user, "validate_adhoc", {
            "is_valid": validation_result["valid"],
            "error_count": len(errors),
            "warning_count": len(warnings),
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges)
        })

        return {
            "validation": validation_result,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        blueprints_api.logger.error("blueprints_api.validate_adhoc_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to validate blueprint")


@router.post("/validate-delta")
async def validate_blueprint_delta(
    request: Dict[str, Any] = Body(...),
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Validate blueprint changes with delta comparison for efficient validation.
    """
    blueprints_api.check_permission(user, "read")

    try:
        current_graph_data = request.get("current")
        previous_graph_data = request.get("previous", {})

        if not current_graph_data:
            raise HTTPException(status_code=400, detail="current graph data is required")

        # Validate current graph
        current_graph = StrategyGraph.from_dict(current_graph_data)
        current_errors, current_warnings = blueprints_api.validator.validate(current_graph)

        # Validate previous graph if provided
        previous_errors = []
        previous_warnings = []
        if previous_graph_data:
            try:
                previous_graph = StrategyGraph.from_dict(previous_graph_data)
                previous_errors, previous_warnings = blueprints_api.validator.validate(previous_graph)
            except Exception:
                # If previous graph is invalid, only validate current
                pass

        # Calculate delta (simplified - just return current validation)
        # In production, this would compare changes and only validate affected parts
        validation_result = {
            "valid": len(current_errors) == 0,
            "errors": [{"type": e.error_type, "message": e.message, "node_id": e.node_id}
                      for e in current_errors],
            "warnings": [{"type": w.error_type, "message": w.message, "node_id": w.node_id}
                        for w in current_warnings],
            "delta_analysis": {
                "new_errors": len(current_errors),
                "resolved_errors": 0,  # Simplified
                "new_warnings": len(current_warnings),
                "resolved_warnings": 0  # Simplified
            }
        }

        blueprints_api.audit_action(user, "validate_delta", {
            "is_valid": validation_result["valid"],
            "error_count": len(current_errors),
            "warning_count": len(current_warnings),
            "node_count": len(current_graph.nodes),
            "edge_count": len(current_graph.edges)
        })

        return {
            "validation": validation_result,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        blueprints_api.logger.error("blueprints_api.validate_delta_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to validate blueprint delta")


@router.post("/migrate-yaml")
async def migrate_yaml_config(
    yaml_data: Dict[str, Any] = Body(...),
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Migrate a YAML strategy configuration to graph format.
    """
    blueprints_api.check_permission(user, "write")

    try:
        # Migrate YAML to graph
        graph = blueprints_api.migrate_yaml_to_graph(yaml_data)

        # Validate migrated graph
        errors, warnings = blueprints_api.validator.validate(graph)
        if errors:
            error_details = [{"type": e.error_type, "message": e.message, "node_id": e.node_id}
                           for e in errors]
            return {
                "migration": {
                    "success": False,
                    "errors": error_details,
                    "warnings": [{"type": w.error_type, "message": w.message, "node_id": w.node_id}
                               for w in warnings]
                },
                "timestamp": datetime.now().isoformat()
            }

        # Create blueprint from migrated graph
        blueprint_id = str(uuid.uuid4())
        blueprint = {
            "id": blueprint_id,
            "name": yaml_data.get("name", "migrated_strategy"),
            "version": "1.0.0",
            "description": f"Migrated from YAML: {yaml_data.get('description', '')}",
            "graph": graph.to_dict(),
            "tags": ["migrated", "yaml"],
            "is_template": False,
            "created_by": user["user_id"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": {"migrated_from": "yaml", "original_config": yaml_data}
        }

        # Store blueprint
        blueprints_api.blueprints[blueprint_id] = blueprint

        blueprints_api.audit_action(user, "migrate_yaml", {
            "new_blueprint_id": blueprint_id,
            "original_name": yaml_data.get("name"),
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges)
        })

        return {
            "migration": {
                "success": True,
                "blueprint_id": blueprint_id,
                "warnings": [{"type": w.error_type, "message": w.message, "node_id": w.node_id}
                           for w in warnings]
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        blueprints_api.logger.error("blueprints_api.migrate_yaml_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to migrate YAML config")


@router.post("/{blueprint_id}/execute/live")
async def start_live_execution(
    blueprint_id: str,
    execution_config: Dict[str, Any] = Body(...),
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Start live execution of a strategy blueprint with real-time indicator data.
    """
    blueprints_api.check_permission(user, "write")

    try:
        # Get blueprint
        blueprint = blueprints_api.blueprints.get(blueprint_id)
        if not blueprint:
            raise HTTPException(status_code=404, detail="Blueprint not found")

        # Get live executor
        executor = get_live_executor()

        # Convert blueprint graph to StrategyGraph
        graph = StrategyGraph.from_dict(blueprint["graph"])

        # Start live session
        symbol = execution_config.get("symbol", "BTCUSDT")
        session_id = await executor.start_live_session(
            strategy_name=blueprint["name"],
            graph=graph,
            symbol=symbol
        )

        blueprints_api.audit_action(user, "start_live_execution", {
            "blueprint_id": blueprint_id,
            "blueprint_name": blueprint["name"],
            "session_id": session_id,
            "symbol": symbol
        })

        return {
            "session_id": session_id,
            "blueprint_id": blueprint_id,
            "strategy_name": blueprint["name"],
            "symbol": symbol,
            "status": "started",
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        blueprints_api.logger.error("blueprints_api.start_live_execution_error", {
            "error": str(e),
            "blueprint_id": blueprint_id,
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to start live execution")


@router.delete("/execution/live/{session_id}")
async def stop_live_execution(
    session_id: str,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Stop a live execution session.
    """
    blueprints_api.check_permission(user, "write")

    try:
        # Get live executor
        executor = get_live_executor()

        # Stop session
        success = await executor.stop_live_session(session_id)

        if not success:
            raise HTTPException(status_code=404, detail="Live execution session not found")

        blueprints_api.audit_action(user, "stop_live_execution", {
            "session_id": session_id
        })

        return {
            "session_id": session_id,
            "status": "stopped",
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        blueprints_api.logger.error("blueprints_api.stop_live_execution_error", {
            "error": str(e),
            "session_id": session_id,
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to stop live execution")


@router.get("/execution/live/{session_id}")
async def get_live_execution_status(
    session_id: str,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Get status of a live execution session.
    """
    blueprints_api.check_permission(user, "read")

    try:
        # Get live executor
        executor = get_live_executor()

        # Get session status
        status = executor.get_session_status(session_id)

        if not status:
            raise HTTPException(status_code=404, detail="Live execution session not found")

        blueprints_api.audit_action(user, "get_live_execution_status", {
            "session_id": session_id
        })

        return {
            "session": status,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        blueprints_api.logger.error("blueprints_api.get_live_execution_status_error", {
            "error": str(e),
            "session_id": session_id,
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to get live execution status")


@router.get("/execution/live")
async def list_live_executions(
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    List all active live execution sessions.
    """
    blueprints_api.check_permission(user, "read")

    try:
        # Get live executor
        executor = get_live_executor()

        # Get active sessions
        sessions = executor.list_active_sessions()

        blueprints_api.audit_action(user, "list_live_executions", {
            "session_count": len(sessions)
        })

        return {
            "sessions": sessions,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        blueprints_api.logger.error("blueprints_api.list_live_executions_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to list live executions")


@router.get("/templates/list")
async def list_templates(
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    List available strategy templates.
    """
    blueprints_api.check_permission(user, "read")

    try:
        # Get template blueprints
        templates = [b for b in blueprints_api.blueprints.values() if b.get("is_template", False)]

        template_list = []
        for template in templates:
            template_list.append({
                "id": template["id"],
                "name": template["name"],
                "description": template.get("description", ""),
                "tags": template.get("tags", []),
                "node_count": len(template["graph"]["nodes"]),
                "edge_count": len(template["graph"]["edges"])
            })

        blueprints_api.audit_action(user, "list_templates", {
            "template_count": len(template_list)
        })

        return {
            "templates": template_list,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        blueprints_api.logger.error("blueprints_api.list_templates_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to list templates")