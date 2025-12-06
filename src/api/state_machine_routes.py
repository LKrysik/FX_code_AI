"""
State Machine API Routes
=========================

REST endpoints for exposing state machine status to UI.

Endpoints:
- GET /api/sessions/{session_id}/state - Current execution state + strategy instances
- GET /api/sessions/{session_id}/transitions - State transition history

Architecture:
- ExecutionController manages session-level state (IDLE, STARTING, RUNNING, PAUSED, STOPPING, STOPPED, ERROR)
- StrategyManager manages per-strategy-instance state (MONITORING, SIGNAL_DETECTED, ENTRY_EVALUATION, POSITION_ACTIVE, etc.)
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

from src.core.logger import get_logger
from src.api.response_envelope import ensure_envelope
from src.application.controllers.execution_controller import ExecutionState

logger = get_logger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["state_machine"])

# Dependency injection - will be set during app startup
_execution_controller = None
_strategy_manager = None


def initialize_state_machine_dependencies(execution_controller, strategy_manager):
    """
    Initialize dependencies for state machine routes.
    Called from unified_server.py during startup.

    Args:
        execution_controller: ExecutionController instance
        strategy_manager: StrategyManager instance
    """
    global _execution_controller, _strategy_manager
    _execution_controller = execution_controller
    _strategy_manager = strategy_manager
    logger.info("state_machine_routes.dependencies_initialized")


def _ensure_dependencies():
    """Verify dependencies are initialized."""
    if _execution_controller is None or _strategy_manager is None:
        raise RuntimeError(
            "State machine routes dependencies not initialized. "
            "Call initialize_state_machine_dependencies() during app startup."
        )
    return _execution_controller, _strategy_manager


def _get_allowed_transitions(current_state: ExecutionState) -> List[str]:
    """
    Get list of allowed state transitions from current state.
    Based on ExecutionController._valid_transitions.

    Args:
        current_state: Current ExecutionState

    Returns:
        List of allowed next states (as string values)
    """
    # Mapping from ExecutionController._valid_transitions (line 375-383)
    valid_transitions = {
        ExecutionState.IDLE: [ExecutionState.STARTING],
        ExecutionState.STARTING: [ExecutionState.RUNNING, ExecutionState.ERROR],
        ExecutionState.RUNNING: [ExecutionState.PAUSED, ExecutionState.STOPPING, ExecutionState.ERROR],
        ExecutionState.PAUSED: [ExecutionState.RUNNING, ExecutionState.STOPPING],
        ExecutionState.STOPPING: [ExecutionState.STOPPED, ExecutionState.ERROR, ExecutionState.STARTING],
        ExecutionState.STOPPED: [ExecutionState.STARTING],
        ExecutionState.ERROR: [ExecutionState.STARTING, ExecutionState.STOPPED]
    }

    allowed = valid_transitions.get(current_state, [])
    return [state.value for state in allowed]


@router.get("/{session_id}/state")
async def get_session_state(
    session_id: str = Path(..., description="Session ID")
) -> JSONResponse:
    """
    Get current state machine status for a session.

    Returns session-level state (ExecutionController) plus per-instance states (StrategyManager).

    Performance Target: <50ms

    Path Parameters:
    - session_id: Session identifier

    Returns:
        {
            "session_id": "exec_20251206_100000_abc123",
            "current_state": "RUNNING",
            "since": "2025-12-06T10:00:00Z",
            "mode": "paper",
            "allowed_transitions": ["PAUSED", "STOPPING"],
            "instances": [
                {
                    "strategy_id": "pump_peak_short",
                    "symbol": "BTC_USDT",
                    "state": "MONITORING",
                    "since": "2025-12-06T10:00:00Z"
                }
            ]
        }
    """
    try:
        controller, strategy_manager = _ensure_dependencies()

        # Get session from ExecutionController
        session = controller.get_current_session()

        if not session or session.session_id != session_id:
            # Session not found or session_id mismatch
            return ensure_envelope({
                "session_id": session_id,
                "current_state": "IDLE",
                "since": None,
                "mode": None,
                "allowed_transitions": ["STARTING"],
                "instances": []
            })

        # Build response with session-level state
        response_data = {
            "session_id": session.session_id,
            "current_state": session.status.value.upper(),
            "since": session.start_time.isoformat() if session.start_time else None,
            "mode": session.mode.value,
            "allowed_transitions": _get_allowed_transitions(session.status),
            "instances": []
        }

        # Get strategy instances from StrategyManager
        # For each symbol in the session, get active strategies
        if strategy_manager and session.symbols:
            for symbol in session.symbols:
                try:
                    active_strategies = strategy_manager.get_active_strategies_for_symbol(symbol)

                    for strategy_info in active_strategies:
                        # Get full strategy details to include state_since timestamp
                        strategy = strategy_manager.strategies.get(strategy_info["strategy_name"])

                        if strategy:
                            # Determine "since" timestamp based on current state
                            state_since = None
                            if strategy.current_state.value == "signal_detected" and strategy.signal_detection_time:
                                state_since = strategy.signal_detection_time.isoformat()
                            elif strategy.current_state.value == "position_active" and strategy.entry_time:
                                state_since = strategy.entry_time.isoformat()
                            elif strategy.current_state.value == "exited" and strategy.exit_time:
                                state_since = strategy.exit_time.isoformat()

                            response_data["instances"].append({
                                "strategy_id": strategy.strategy_name,
                                "symbol": symbol,
                                "state": strategy.current_state.value.upper(),
                                "since": state_since
                            })
                except Exception as strategy_error:
                    logger.warning("state_machine.get_strategy_error", {
                        "session_id": session_id,
                        "symbol": symbol,
                        "error": str(strategy_error)
                    })
                    continue

        return ensure_envelope(response_data)

    except Exception as e:
        logger.error("state_machine.get_state_error", {
            "session_id": session_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session state: {str(e)}"
        )


@router.get("/{session_id}/transitions")
async def get_session_transitions(
    session_id: str = Path(..., description="Session ID")
) -> JSONResponse:
    """
    Get state transition history for a session.

    NOTE: This is a PLACEHOLDER implementation. Full transition history tracking
    requires event persistence (EventBus -> QuestDB).

    For MVP, returns empty list. Full implementation in future sprint.

    Performance Target: <100ms

    Path Parameters:
    - session_id: Session identifier

    Returns:
        {
            "session_id": "exec_20251206_100000_abc123",
            "transitions": []
        }

    Future format (when event persistence is implemented):
        {
            "session_id": "exec_20251206_100000_abc123",
            "transitions": [
                {
                    "timestamp": "2025-12-06T10:05:23Z",
                    "strategy_id": "pump_peak_short",
                    "symbol": "ETH_USDT",
                    "from_state": "MONITORING",
                    "to_state": "SIGNAL_DETECTED",
                    "trigger": "S1",
                    "conditions": {
                        "PUMP_MAGNITUDE_PCT": {
                            "value": 7.2,
                            "threshold": 5.0,
                            "operator": ">",
                            "met": true
                        }
                    }
                }
            ]
        }
    """
    try:
        controller, strategy_manager = _ensure_dependencies()

        # Verify session exists
        session = controller.get_current_session()

        if not session or session.session_id != session_id:
            # Session not found
            return ensure_envelope({
                "session_id": session_id,
                "transitions": []
            })

        # TODO: Implement full transition history tracking
        # Requires:
        # 1. EventBus event persistence (strategy.state_transition events -> QuestDB)
        # 2. Query QuestDB for historical transitions
        # 3. Parse condition details from event payloads
        #
        # For now, return empty list as placeholder

        logger.debug("state_machine.transitions_placeholder", {
            "session_id": session_id,
            "note": "Transition history not yet implemented - requires event persistence"
        })

        return ensure_envelope({
            "session_id": session_id,
            "transitions": []
        })

    except Exception as e:
        logger.error("state_machine.get_transitions_error", {
            "session_id": session_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session transitions: {str(e)}"
        )


@router.get("/{session_id}/conditions")
async def get_session_conditions(
    session_id: str = Path(..., description="Session ID"),
    symbol: str = None
) -> JSONResponse:
    """
    Get current condition progress for a session.

    Returns which conditions are met/pending for each condition group (S1, O1, Z1, ZE1, E1).
    Used by ConditionProgress UI component.

    Performance Target: <50ms

    Path Parameters:
    - session_id: Session identifier

    Query Parameters:
    - symbol: Optional filter by symbol (default: returns all symbols)

    Returns:
        {
            "session_id": "exec_20251206_100000_abc123",
            "instances": [
                {
                    "strategy_id": "pump_peak_short",
                    "symbol": "BTC_USDT",
                    "state": "MONITORING",
                    "groups": [
                        {
                            "name": "S1 - Signal Detection",
                            "id": "signal_detection",
                            "is_relevant": true,
                            "conditions": [
                                {
                                    "name": "PUMP_MAGNITUDE_PCT",
                                    "operator": ">=",
                                    "threshold": 5.0,
                                    "current_value": 3.2,
                                    "met": false
                                }
                            ]
                        }
                    ]
                }
            ]
        }

    Architecture Decision:
    - Conditions are evaluated against cached indicator values from IndicatorEngine
    - Each strategy instance has 5 condition groups: S1, O1, Z1, ZE1, E1
    - Only the "relevant" group for current state is highlighted in UI
    - state MONITORING → S1 relevant, SIGNAL_DETECTED → Z1 relevant, POSITION_ACTIVE → ZE1/E1 relevant
    """
    try:
        controller, strategy_manager = _ensure_dependencies()

        # Verify session exists
        session = controller.get_current_session()

        if not session or session.session_id != session_id:
            return ensure_envelope({
                "session_id": session_id,
                "instances": []
            })

        # Build response with conditions for each strategy instance
        instances = []

        # Filter symbols if specified
        symbols_to_check = [symbol] if symbol else (session.symbols or [])

        for sym in symbols_to_check:
            try:
                active_strategies = strategy_manager.get_active_strategies_for_symbol(sym)

                for strategy_info in active_strategies:
                    strategy = strategy_manager.strategies.get(strategy_info["strategy_name"])

                    if not strategy:
                        continue

                    # Get current indicator values from IndicatorEngine cache
                    # IndicatorEngine is accessed via strategy_manager._indicator_engine
                    indicator_values = {}
                    if hasattr(strategy_manager, '_indicator_engine') and strategy_manager._indicator_engine:
                        try:
                            indicator_values = strategy_manager._indicator_engine.get_all_values(sym)
                        except Exception as ind_err:
                            logger.debug("state_machine.conditions.indicator_error", {
                                "symbol": sym,
                                "error": str(ind_err)
                            })

                    # Determine which group is relevant based on current state
                    # MONITORING → S1, SIGNAL_DETECTED → Z1, POSITION_ACTIVE → ZE1/E1
                    current_state_value = strategy.current_state.value.lower()
                    relevant_groups = {
                        "inactive": ["signal_detection"],
                        "monitoring": ["signal_detection"],
                        "signal_detected": ["entry_conditions", "signal_cancellation"],
                        "entry_evaluation": ["entry_conditions"],
                        "position_active": ["close_order_detection", "emergency_exit"],
                        "exited": [],
                        "error": []
                    }
                    relevant_for_state = relevant_groups.get(current_state_value, [])

                    # Build groups array
                    groups = []

                    # S1 - Signal Detection
                    groups.append(_build_condition_group(
                        group=strategy.signal_detection,
                        display_name="S1 - Signal Detection",
                        group_id="signal_detection",
                        is_relevant="signal_detection" in relevant_for_state,
                        indicator_values=indicator_values
                    ))

                    # O1 - Signal Cancellation
                    groups.append(_build_condition_group(
                        group=strategy.signal_cancellation,
                        display_name="O1 - Signal Cancellation",
                        group_id="signal_cancellation",
                        is_relevant="signal_cancellation" in relevant_for_state,
                        indicator_values=indicator_values
                    ))

                    # Z1 - Entry Conditions
                    groups.append(_build_condition_group(
                        group=strategy.entry_conditions,
                        display_name="Z1 - Entry Conditions",
                        group_id="entry_conditions",
                        is_relevant="entry_conditions" in relevant_for_state,
                        indicator_values=indicator_values
                    ))

                    # ZE1 - Close Order Detection
                    groups.append(_build_condition_group(
                        group=strategy.close_order_detection,
                        display_name="ZE1 - Close Order Detection",
                        group_id="close_order_detection",
                        is_relevant="close_order_detection" in relevant_for_state,
                        indicator_values=indicator_values
                    ))

                    # E1 - Emergency Exit
                    groups.append(_build_condition_group(
                        group=strategy.emergency_exit,
                        display_name="E1 - Emergency Exit",
                        group_id="emergency_exit",
                        is_relevant="emergency_exit" in relevant_for_state,
                        indicator_values=indicator_values
                    ))

                    instances.append({
                        "strategy_id": strategy.strategy_name,
                        "symbol": sym,
                        "state": strategy.current_state.value.upper(),
                        "groups": groups
                    })

            except Exception as strategy_error:
                logger.warning("state_machine.get_conditions_error", {
                    "session_id": session_id,
                    "symbol": sym,
                    "error": str(strategy_error)
                })
                continue

        return ensure_envelope({
            "session_id": session_id,
            "instances": instances
        })

    except Exception as e:
        logger.error("state_machine.get_conditions_error", {
            "session_id": session_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session conditions: {str(e)}"
        )


def _build_condition_group(
    group,
    display_name: str,
    group_id: str,
    is_relevant: bool,
    indicator_values: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build condition group response object.

    Args:
        group: ConditionGroup object from Strategy
        display_name: Human-readable name (e.g., "S1 - Signal Detection")
        group_id: Technical ID (e.g., "signal_detection")
        is_relevant: Whether this group is relevant for current state
        indicator_values: Current indicator values for evaluation

    Returns:
        Dictionary with group info and condition statuses
    """
    conditions_data = []

    for condition in group.conditions:
        # Get current value for this condition from indicator_values
        # Case-insensitive lookup (matching Condition.evaluate() behavior)
        condition_key = condition.condition_type.lower()
        current_value = None

        for key, value in indicator_values.items():
            if key.lower() == condition_key:
                current_value = value
                break

        # Evaluate condition
        from src.domain.services.strategy_manager import ConditionResult
        result = condition.evaluate(indicator_values)
        is_met = result == ConditionResult.TRUE

        conditions_data.append({
            "name": condition.name or condition.condition_type,
            "condition_type": condition.condition_type,
            "operator": condition.operator,
            "threshold": condition.value,
            "current_value": current_value,
            "met": is_met,
            "enabled": condition.enabled,
            "description": condition.description
        })

    # Calculate progress (how many conditions are met)
    enabled_conditions = [c for c in conditions_data if c["enabled"]]
    met_count = sum(1 for c in enabled_conditions if c["met"])
    total_count = len(enabled_conditions)

    return {
        "name": display_name,
        "id": group_id,
        "is_relevant": is_relevant,
        "require_all": group.require_all,
        "progress": {
            "met": met_count,
            "total": total_count,
            "percentage": (met_count / total_count * 100) if total_count > 0 else 0
        },
        "conditions": conditions_data
    }
