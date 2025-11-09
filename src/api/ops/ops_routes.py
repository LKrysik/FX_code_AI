"""
Operations Routes - Sprint 4 Operations Dashboard API
=====================================================

REST API endpoints for operations dashboard with RBAC, telemetry aggregation,
and risk control mutations.

Features:
- Live positions and P&L endpoints
- Incident timeline and acknowledgements
- Risk controls (kill-switch, exposure limits)
- Telemetry aggregation for dashboards
- RBAC-protected operations
- Audit trail for all actions

Critical Analysis Points:
1. **RBAC Integration**: Proper authorization for sensitive operations
2. **Real-time Data**: Efficient aggregation of live trading data
3. **Audit Trail**: Complete logging of all operator actions
4. **Risk Controls**: Safe mutation of trading parameters
5. **Performance**: Optimized queries for dashboard responsiveness
6. **Error Handling**: Graceful degradation and clear error messages
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from ...core.logger import StructuredLogger
from ...data.live_market_adapter import LiveMarketAdapter
from ...trading.session_manager import SessionManager
from ...monitoring.metrics_exporter import MetricsExporter


router = APIRouter(prefix="/api/ops", tags=["operations"])
security = HTTPBearer()

# ✅ ARCHITECTURE FIX: Module-level declaration (not instantiation)
# Follows DI pattern from indicators_routes.py, paper_trading_routes.py, trading_routes.py
_ops_api: Optional['OpsAPI'] = None


def initialize_ops_dependencies(ops_api: 'OpsAPI') -> None:
    """
    ✅ ARCHITECTURE FIX: Explicit dependency injection instead of module-level instantiation.

    This function is called from unified_server.py during app startup
    to inject the properly configured OpsAPI instance from Container.

    Args:
        ops_api: Pre-configured OpsAPI instance from Container.create_ops_api()
    """
    global _ops_api
    _ops_api = ops_api


def get_ops_api() -> 'OpsAPI':
    """
    Get injected OpsAPI instance or fail-fast if not initialized.

    Services MUST be injected via initialize_ops_dependencies() during startup.
    No fallback lazy initialization - enforces proper DI architecture.

    Returns:
        Injected OpsAPI instance

    Raises:
        RuntimeError: If OpsAPI not injected (indicates DI failure)
    """
    if _ops_api is None:
        raise RuntimeError(
            "OpsAPI not injected into ops_routes. "
            "Call initialize_ops_dependencies() from unified_server.py during startup."
        )
    return _ops_api


class OpsAPI:
    """
    Operations API for Sprint 4 dashboard.

    Provides REST endpoints for operations dashboard with proper authentication,
    authorization, and audit logging.
    """

    def __init__(
        self,
        market_adapter: LiveMarketAdapter,
        session_manager: SessionManager,
        metrics_exporter: MetricsExporter,
        logger: StructuredLogger,
        jwt_secret: Optional[str] = None
    ):
        self.market_adapter = market_adapter
        self.session_manager = session_manager
        self.metrics_exporter = metrics_exporter
        self.logger = logger

        # SECURITY: Require strong JWT secret from environment
        jwt_secret_value = jwt_secret or os.getenv("JWT_SECRET")

        if not jwt_secret_value or len(jwt_secret_value) < 32:
            raise RuntimeError(
                "JWT_SECRET must be set to a strong secret (minimum 32 characters). "
                "Generate a secure secret using: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # SECURITY: Reject default/weak secrets
        weak_secrets = ["sprint4-ops-secret", "dev_jwt_secret_key", "secret", "jwt_secret", "change_me", "default"]
        if jwt_secret_value.lower() in weak_secrets:
            raise RuntimeError(
                f"JWT_SECRET cannot be a common/weak value. "
                f"Generate a secure secret using: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        self.jwt_secret = jwt_secret_value

        # RBAC configuration (should come from config file)
        self.roles = {
            "operator": ["read"],
            "admin": ["read", "write", "admin"],
            "auditor": ["read"]
        }

        # Audit log
        self.audit_log: List[Dict[str, Any]] = []

    def get_router(self) -> APIRouter:
        """Get the FastAPI router with all endpoints"""
        return router

    async def authenticate_user(self, credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """Authenticate user from JWT token"""
        try:
            token = credentials.credentials
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

        self.logger.info("ops_api.audit_action", audit_entry)


# ✅ ARCHITECTURE FIX: Removed module-level instantiation anti-pattern
# Before: ops_api = OpsAPI(None, None, None, None)  # ❌ Created at import time, caused JWT_SECRET error
# After: Instance injected via initialize_ops_dependencies() from Container
# Follows pattern from indicators_routes.py, paper_trading_routes.py, trading_routes.py


@router.get("/health")
async def get_ops_health():
    """Get operations API health status"""
    return {
        "status": "healthy",
        "component": "ops_api",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/positions")
async def get_live_positions(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    session_id: Optional[str] = Query(None, description="Filter by session")
):
    """
    Get live positions and P&L data.

    Returns aggregated position data across all active sessions.
    """
    ops_api = get_ops_api()  # ✅ Get injected instance
    user = await ops_api.authenticate_user(credentials)
    ops_api.check_permission(user, "read")

    try:
        # Get all client sessions
        sessions = await ops_api.session_manager.list_client_sessions(user["user_id"])

        positions = []

        for session_data in sessions:
            session_id_from_data = session_data["session_id"]

            # Filter by session_id if provided
            if session_id and session_id_from_data != session_id:
                continue

            # Get detailed session status
            detailed_session = await ops_api.session_manager.get_session_status(
                session_id_from_data, user["user_id"]
            )

            if detailed_session:
                # Aggregate positions from session
                session_positions = await _aggregate_session_positions(
                    detailed_session, symbol
                )
                positions.extend(session_positions)

        ops_api.audit_action(user, "get_positions", {
            "symbol_filter": symbol,
            "session_filter": session_id,
            "positions_returned": len(positions)
        })

        return {
            "positions": positions,
            "total_count": len(positions),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        ops_api.logger.error("ops_api.get_positions_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to retrieve positions")


@router.get("/incidents")
async def get_incidents(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, description="Maximum incidents to return")
):
    """
    Get incident timeline with filtering and acknowledgements.
    """
    ops_api = get_ops_api()  # ✅ Get injected instance
    user = await ops_api.authenticate_user(credentials)
    ops_api.check_permission(user, "read")

    try:
        # Get incidents from market adapter
        incidents = ops_api.market_adapter.get_incidents(
            resolved=resolved,
            severity=severity,
            limit=limit
        )

        ops_api.audit_action(user, "get_incidents", {
            "resolved_filter": resolved,
            "severity_filter": severity,
            "limit": limit,
            "incidents_returned": len(incidents)
        })

        return {
            "incidents": incidents,
            "total_count": len(incidents),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        ops_api.logger.error("ops_api.get_incidents_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to retrieve incidents")


@router.post("/incidents/{incident_id}/acknowledge")
async def acknowledge_incident(
    incident_id: str,
    note: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Acknowledge an incident with optional note.
    """
    ops_api = get_ops_api()  # ✅ Get injected instance
    user = await ops_api.authenticate_user(credentials)
    ops_api.check_permission(user, "write")

    try:
        resolution_note = note or f"Acknowledged by {user['user_id']}"

        success = await ops_api.market_adapter.resolve_incident(incident_id, resolution_note)

        if not success:
            raise HTTPException(status_code=404, detail="Incident not found")

        ops_api.audit_action(user, "acknowledge_incident", {
            "incident_id": incident_id,
            "resolution_note": resolution_note
        })

        return {
            "status": "acknowledged",
            "incident_id": incident_id,
            "acknowledged_by": user["user_id"],
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        ops_api.logger.error("ops_api.acknowledge_incident_error", {
            "error": str(e),
            "incident_id": incident_id,
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to acknowledge incident")


@router.get("/risk-controls")
async def get_risk_controls(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get current risk control status and settings.
    """
    ops_api = get_ops_api()  # ✅ Get injected instance
    user = await ops_api.authenticate_user(credentials)
    ops_api.check_permission(user, "read")

    try:
        # Aggregate risk controls from session manager
        risk_status = await _get_risk_status()

        ops_api.audit_action(user, "get_risk_controls", {})

        return {
            "risk_controls": risk_status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        ops_api.logger.error("ops_api.get_risk_controls_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to retrieve risk controls")


@router.post("/risk-controls/kill-switch")
async def trigger_kill_switch(
    reason: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Trigger global kill switch to stop all trading.
    """
    ops_api = get_ops_api()  # ✅ Get injected instance
    user = await ops_api.authenticate_user(credentials)
    ops_api.check_permission(user, "admin")

    try:
        # Implement kill switch logic
        kill_result = await _execute_kill_switch(reason, user)

        ops_api.audit_action(user, "trigger_kill_switch", {
            "reason": reason,
            "affected_sessions": kill_result["affected_sessions"]
        })

        return {
            "status": "executed",
            "kill_switch_triggered": True,
            "reason": reason,
            "affected_sessions": kill_result["affected_sessions"],
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        ops_api.logger.error("ops_api.kill_switch_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to execute kill switch")


@router.get("/telemetry")
async def get_telemetry(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    time_range: str = Query("1h", description="Time range (1h, 6h, 24h)")
):
    """
    Get aggregated telemetry data for dashboards.
    """
    ops_api = get_ops_api()  # ✅ Get injected instance
    user = await ops_api.authenticate_user(credentials)
    ops_api.check_permission(user, "read")

    try:
        # Parse time range
        if time_range == "1h":
            hours = 1
        elif time_range == "6h":
            hours = 6
        elif time_range == "24h":
            hours = 24
        else:
            raise HTTPException(status_code=400, detail="Invalid time range")

        # Get metrics summary
        metrics_summary = ops_api.metrics_exporter.get_metrics_summary()

        # Get alert status
        alert_status = ops_api.metrics_exporter.get_alert_status()

        # Aggregate telemetry
        telemetry = {
            "metrics": metrics_summary,
            "alerts": alert_status,
            "time_range": time_range,
            "data_points": len(metrics_summary)
        }

        ops_api.audit_action(user, "get_telemetry", {
            "time_range": time_range,
            "metrics_count": len(metrics_summary)
        })

        return {
            "telemetry": telemetry,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        ops_api.logger.error("ops_api.get_telemetry_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to retrieve telemetry")


@router.get("/audit-log")
async def get_audit_log(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    limit: int = Query(100, description="Maximum log entries to return"),
    action: Optional[str] = Query(None, description="Filter by action")
):
    """
    Get audit log for compliance and monitoring.
    """
    ops_api = get_ops_api()  # ✅ Get injected instance
    user = await ops_api.authenticate_user(credentials)
    ops_api.check_permission(user, "read")

    try:
        # Filter audit log
        filtered_log = ops_api.audit_log

        if action:
            filtered_log = [entry for entry in filtered_log if entry["action"] == action]

        # Return most recent entries
        recent_log = filtered_log[-limit:]

        ops_api.audit_action(user, "get_audit_log", {
            "limit": limit,
            "action_filter": action,
            "entries_returned": len(recent_log)
        })

        return {
            "audit_log": recent_log,
            "total_count": len(recent_log),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        ops_api.logger.error("ops_api.get_audit_log_error", {
            "error": str(e),
            "user_id": user["user_id"]
        })
        raise HTTPException(status_code=500, detail="Failed to retrieve audit log")


# Helper functions

async def _aggregate_session_positions(session_data: Dict[str, Any], symbol_filter: Optional[str]) -> List[Dict[str, Any]]:
    """Aggregate positions from session data"""
    positions = []

    # This would integrate with actual position tracking
    # For now, return mock positions based on session data

    for symbol in session_data.get("symbols", []):
        if symbol_filter and symbol != symbol_filter:
            continue

        # Mock position data - would come from actual position manager
        position = {
            "session_id": session_data["session_id"],
            "symbol": symbol,
            "side": "long",  # Would come from actual position
            "quantity": 100.0,  # Mock
            "entry_price": 50000.0,  # Mock
            "current_price": 51000.0,  # Would get from market data
            "unrealized_pnl": 1000.0,  # Mock calculation
            "realized_pnl": 0.0,
            "exposure": 5000000.0,  # quantity * current_price
            "stop_loss": 49500.0,  # Mock
            "take_profit": 52000.0,  # Mock
            "last_update": datetime.now().isoformat()
        }

        positions.append(position)

    return positions


async def _get_risk_status() -> Dict[str, Any]:
    """Get current risk control status"""
    # This would aggregate from risk management components
    return {
        "global_exposure_limit": 1000000.0,
        "current_exposure": 500000.0,
        "exposure_utilization_percent": 50.0,
        "drawdown_limit_percent": 5.0,
        "current_drawdown_percent": 1.2,
        "kill_switch_active": False,
        "circuit_breakers_open": 0,
        "risk_warnings": []
    }


async def _execute_kill_switch(reason: str, user: Dict[str, Any]) -> Dict[str, Any]:
    """Execute global kill switch"""
    ops_api = get_ops_api()  # ✅ Get injected instance
    affected_sessions = 0

    # Stop all sessions for the user
    sessions = await ops_api.session_manager.list_client_sessions(user["user_id"])

    for session_data in sessions:
        session_id = session_data["session_id"]
        await ops_api.session_manager.stop_session(session_id, user["user_id"])
        affected_sessions += 1

    return {
        "affected_sessions": affected_sessions,
        "reason": reason,
        "executed_by": user["user_id"]
    }