"""
Strategy Schema Validation (5-Section Format)
Lightweight validator for 5-section strategy JSON configs without extra dependencies.

SEC-0-2: Enhanced with security validation to prevent JSON injection attacks.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Set, Optional

from ...core.logger import get_logger

# =============================================================================
# SEC-0-2: Security Allowlists for Strategy Validation
# =============================================================================

# Import IndicatorType enum to build allowlist
try:
    from src.domain.services.streaming_indicator_engine.core.types import IndicatorType
    ALLOWED_INDICATOR_TYPES: Set[str] = {t.value for t in IndicatorType}
except ImportError:
    # Fallback if import fails - define known indicator types explicitly
    ALLOWED_INDICATOR_TYPES: Set[str] = {
        "PRICE", "VOLUME", "BEST_BID", "BEST_ASK", "BID_QTY", "ASK_QTY",
        "SPREAD_PCT", "VOLUME_24H", "LIQUIDITY_SCORE",
        "SMA", "EMA", "RSI", "MACD", "BOLLINGER_BANDS",
        "PUMP_MAGNITUDE_PCT", "VOLUME_SURGE_RATIO", "PRICE_VELOCITY",
        "PRICE_MOMENTUM", "BASELINE_PRICE", "PUMP_PROBABILITY",
        "SIGNAL_AGE_SECONDS", "CONFIDENCE_SCORE", "RISK_LEVEL", "VOLATILITY",
        "MARKET_STRESS_INDICATOR", "POSITION_RISK_SCORE", "PORTFOLIO_EXPOSURE_PCT",
        "UNREALIZED_PNL_PCT", "CLOSE_ORDER_PRICE",
        "TWPA", "TWPA_RATIO", "LAST_PRICE", "FIRST_PRICE", "MAX_PRICE", "MIN_PRICE",
        "VELOCITY", "VOLUME_SURGE", "AVG_BEST_BID", "AVG_BEST_ASK",
        "AVG_BID_QTY", "AVG_ASK_QTY", "TW_MIDPRICE",
        "SUM_VOLUME", "AVG_VOLUME", "COUNT_DEALS", "VWAP",
        "VOLUME_CONCENTRATION", "VOLUME_ACCELERATION", "TRADE_FREQUENCY",
        "AVERAGE_TRADE_SIZE", "BID_ASK_IMBALANCE", "SPREAD_PERCENTAGE",
        "SPREAD_VOLATILITY", "VOLUME_PRICE_CORRELATION",
        "MAX_TWPA", "MIN_TWPA", "VTWPA", "VELOCITY_CASCADE", "VELOCITY_ACCELERATION",
        "MOMENTUM_REVERSAL_INDEX", "DUMP_EXHAUSTION_SCORE", "SUPPORT_LEVEL_PROXIMITY",
        "VELOCITY_STABILIZATION_INDEX", "MOMENTUM_STREAK", "DIRECTION_CONSISTENCY",
        "TRADE_SIZE_MOMENTUM", "MID_PRICE_VELOCITY", "TOTAL_LIQUIDITY",
        "LIQUIDITY_RATIO", "LIQUIDITY_DRAIN_INDEX", "DEAL_VS_MID_DEVIATION",
        "INTER_DEAL_INTERVALS", "DECISION_DENSITY_ACCELERATION",
        "TRADE_CLUSTERING_COEFFICIENT", "PRICE_VOLATILITY", "DEAL_SIZE_VOLATILITY"
    }

ALLOWED_CONDITION_OPERATORS: Set[str] = {">", "<", ">=", "<=", "==", "!="}

ALLOWED_POSITION_SIZE_TYPES: Set[str] = {"fixed", "percentage"}

# COH-001-5: UUID pattern for indicator variant IDs from frontend
# Matches standard UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

ALLOWED_CALCULATION_MODES: Set[str] = {"ABSOLUTE", "RELATIVE_TO_ENTRY"}

# Security logger
_security_logger = get_logger("security.strategy_validation")


class StrategySecurityError(Exception):
    """Raised when strategy contains security-sensitive content."""

    def __init__(self, field: str, value: str, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"{field}: {reason} (value: {value[:50]}...)" if len(str(value)) > 50 else f"{field}: {reason}")


def _hash_payload(payload: Dict[str, Any]) -> str:
    """Generate a short hash of payload for security logging."""
    import json
    try:
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(payload_str.encode()).hexdigest()[:16]
    except Exception:
        return "hash_failed"


def _log_security_rejection(
    field: str,
    value: str,
    reason: str,
    payload: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None
) -> None:
    """Log security-related validation rejections."""
    truncated_value = str(value)[:100]
    payload_hash = _hash_payload(payload) if payload else "no_payload"
    _security_logger.warning(
        f"SECURITY: Strategy validation rejected | field={field}, value={truncated_value}, "
        f"reason={reason}, ip={client_ip or 'unknown'}, hash={payload_hash}"
    )


def validate_indicator_id(indicator_id: str, field_path: str, errors: List[str], payload: Optional[Dict] = None) -> bool:
    """
    SEC-0-2 + COH-001-5: Validate indicator ID.

    Accepts two formats (backwards compatible):
    1. UUID format - indicator variant IDs from frontend (e.g., 'e15a3064-424c-4f7a-8b8b-77a04e3e7ab3')
    2. Type names - indicator type names from allowlist (e.g., 'RSI', 'SMA')

    Returns True if valid, False if rejected.
    """
    if not isinstance(indicator_id, str):
        errors.append(f"{field_path} must be a string")
        return False

    # Normalize: strip whitespace
    normalized = indicator_id.strip()

    if not normalized:
        errors.append(f"{field_path} cannot be empty")
        return False

    # COH-001-5: Accept UUID format (indicator variant IDs from frontend)
    # UUIDs are safe - only contain hex chars and dashes
    if UUID_PATTERN.match(normalized):
        # Valid UUID format - skip type allowlist check
        # Still perform injection pattern check below for defense in depth
        pass
    # Also accept known indicator TYPE names (backwards compatibility)
    elif normalized.upper() not in ALLOWED_INDICATOR_TYPES:
        errors.append(f"{field_path} contains unknown indicator type: '{indicator_id}'")
        _log_security_rejection(field_path, indicator_id, "Unknown indicator type", payload)
        return False

    # Check for injection patterns (extra safety - defense in depth)
    dangerous_patterns = ["<script", "javascript:", "eval(", "exec(", "__", "${", "{{"]
    for pattern in dangerous_patterns:
        if pattern.lower() in indicator_id.lower():
            errors.append(f"{field_path} contains suspicious pattern")
            _log_security_rejection(field_path, indicator_id, f"Dangerous pattern: {pattern}", payload)
            return False

    return True


def validate_security_patterns(value: Any, field_path: str, errors: List[str], payload: Optional[Dict] = None) -> bool:
    """
    SEC-0-2: Check for common injection patterns in string values.
    """
    if not isinstance(value, str):
        return True

    # SQL injection patterns
    sql_patterns = ["'; DROP", "1=1", "OR 1=1", "UNION SELECT", "--", "/*"]

    # Script injection patterns
    script_patterns = ["<script", "javascript:", "onerror=", "onclick=", "onload="]

    # Command injection patterns
    cmd_patterns = ["$(", "`", "| ", "; ", "&& ", "|| "]

    value_lower = value.lower()

    for pattern in sql_patterns + script_patterns + cmd_patterns:
        if pattern.lower() in value_lower:
            errors.append(f"{field_path} contains potentially dangerous pattern")
            _log_security_rejection(field_path, value, f"Injection pattern: {pattern}", payload)
            return False

    return True


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _validate_risk_scaling(path: str, risk_scaling: Dict[str, Any], errors: List[str]) -> None:
    """Validate risk scaling configuration."""
    if not isinstance(risk_scaling, dict):
        errors.append(f"{path} must be an object")
        return

    if not risk_scaling.get("enabled"):
        return  # Skip validation if disabled

    # Required fields when enabled
    if "riskIndicatorId" not in risk_scaling or not risk_scaling["riskIndicatorId"]:
        errors.append(f"{path}.riskIndicatorId is required when enabled")

    # Thresholds validation
    for field in ["lowRiskThreshold", "highRiskThreshold"]:
        if field in risk_scaling:
            val = risk_scaling[field]
            if not _is_number(val) or val < 0 or val > 100:
                errors.append(f"{path}.{field} must be between 0 and 100")

    # Scales validation
    for field in ["lowRiskScale", "highRiskScale"]:
        if field in risk_scaling:
            val = risk_scaling[field]
            if not _is_number(val) or val < 10 or val > 200:
                errors.append(f"{path}.{field} must be between 10 and 200 (percentage)")

    # Cross-field validation
    if "lowRiskThreshold" in risk_scaling and "highRiskThreshold" in risk_scaling:
        low = risk_scaling["lowRiskThreshold"]
        high = risk_scaling["highRiskThreshold"]
        if _is_number(low) and _is_number(high) and low >= high:
            errors.append(f"{path}: lowRiskThreshold must be less than highRiskThreshold")


def validate_strategy_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate 5-section strategy config against schema.

    Returns dict with: {"valid": bool, "errors": List[str], "warnings": List[str]}
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(config, dict):
        return {"valid": False, "errors": ["Config must be an object"], "warnings": []}

    # Required: strategy_name
    name = config.get("strategy_name")
    if not isinstance(name, str) or not name.strip():
        errors.append("strategy_name must be a non-empty string")

    # Required sections
    required_sections = ["s1_signal", "z1_entry", "ze1_close", "o1_cancel", "emergency_exit"]
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")
        elif not isinstance(config[section], dict):
            errors.append(f"{section} must be an object")

    # Validate S1 Signal section
    if "s1_signal" in config and isinstance(config["s1_signal"], dict):
        s1 = config["s1_signal"]
        if "conditions" not in s1:
            errors.append("s1_signal.conditions is required")
        elif not isinstance(s1["conditions"], list):
            errors.append("s1_signal.conditions must be an array")
        else:
            _validate_conditions_list("s1_signal.conditions", s1["conditions"], errors, config)

    # Validate Z1 Entry section
    if "z1_entry" in config and isinstance(config["z1_entry"], dict):
        z1 = config["z1_entry"]
        if "conditions" not in z1:
            errors.append("z1_entry.conditions is required")
        elif not isinstance(z1["conditions"], list):
            errors.append("z1_entry.conditions must be an array")
        else:
            _validate_conditions_list("z1_entry.conditions", z1["conditions"], errors, config)

        if "positionSize" not in z1:
            errors.append("z1_entry.positionSize is required")
        elif isinstance(z1["positionSize"], dict):
            pos_size = z1["positionSize"]
            if pos_size.get("type") not in ["fixed", "percentage"]:
                errors.append("z1_entry.positionSize.type must be 'fixed' or 'percentage'")
            if not _is_number(pos_size.get("value", 0)) or pos_size["value"] < 0:
                errors.append("z1_entry.positionSize.value must be a non-negative number")

            # Validate riskScaling if present
            if "riskScaling" in pos_size:
                _validate_risk_scaling("z1_entry.positionSize.riskScaling", pos_size["riskScaling"], errors)

        # Validate stop loss
        if "stopLoss" in z1 and isinstance(z1["stopLoss"], dict):
            sl = z1["stopLoss"]
            if sl.get("enabled") and "offsetPercent" in sl:
                offset = sl["offsetPercent"]
                if not _is_number(offset) or offset < 0 or offset > 100:
                    errors.append("z1_entry.stopLoss.offsetPercent must be between 0 and 100")

            # Validate calculationMode if present
            if "calculationMode" in sl:
                mode = sl["calculationMode"]
                if mode not in ["ABSOLUTE", "RELATIVE_TO_ENTRY"]:
                    errors.append("z1_entry.stopLoss.calculationMode must be 'ABSOLUTE' or 'RELATIVE_TO_ENTRY'")

            # Validate riskScaling if present
            if "riskScaling" in sl:
                _validate_risk_scaling("z1_entry.stopLoss.riskScaling", sl["riskScaling"], errors)

        # Validate take profit (required if enabled)
        if "takeProfit" in z1 and isinstance(z1["takeProfit"], dict):
            tp = z1["takeProfit"]
            if tp.get("enabled"):
                if "offsetPercent" not in tp:
                    errors.append("z1_entry.takeProfit.offsetPercent is required when enabled")
                elif not _is_number(tp["offsetPercent"]) or tp["offsetPercent"] < 0 or tp["offsetPercent"] > 1000:
                    errors.append("z1_entry.takeProfit.offsetPercent must be between 0 and 1000")

            # Validate calculationMode if present
            if "calculationMode" in tp:
                mode = tp["calculationMode"]
                if mode not in ["ABSOLUTE", "RELATIVE_TO_ENTRY"]:
                    errors.append("z1_entry.takeProfit.calculationMode must be 'ABSOLUTE' or 'RELATIVE_TO_ENTRY'")

            # Validate riskScaling if present
            if "riskScaling" in tp:
                _validate_risk_scaling("z1_entry.takeProfit.riskScaling", tp["riskScaling"], errors)

        # Validate leverage (TIER 1.4 - Futures trading)
        if "leverage" in z1 and z1["leverage"] is not None:
            leverage = z1["leverage"]
            if not _is_number(leverage):
                errors.append("z1_entry.leverage must be a number")
            elif leverage < 1 or leverage > 10:
                errors.append("z1_entry.leverage must be between 1 and 10 (recommended: 1-3x for SHORT strategies)")
            elif leverage > 5:
                warnings.append(f"z1_entry.leverage={leverage}x is HIGH RISK. Liquidation occurs at {(100/leverage):.1f}% price movement. Recommended: 1-3x for SHORT strategies")
            elif leverage > 3:
                warnings.append(f"z1_entry.leverage={leverage}x is MODERATE RISK. Consider 3x or lower for pump & dump strategies with high volatility")

    # Validate ZE1 Close section
    if "ze1_close" in config and isinstance(config["ze1_close"], dict):
       ze1 = config["ze1_close"]
       if "conditions" not in ze1:
           errors.append("ze1_close.conditions is required")
       elif not isinstance(ze1["conditions"], list):
           errors.append("ze1_close.conditions must be an array")
       else:
           _validate_conditions_list("ze1_close.conditions", ze1["conditions"], errors, config)

       # Validate risk-adjusted pricing if present
       if "riskAdjustedPricing" in ze1 and isinstance(ze1["riskAdjustedPricing"], dict):
           rap = ze1["riskAdjustedPricing"]
           if rap.get("enabled"):
               if "scalingFactor" in rap:
                   sf = rap["scalingFactor"]
                   if not _is_number(sf) or sf < 0.1 or sf > 2.0:
                       errors.append("ze1_close.riskAdjustedPricing.scalingFactor must be between 0.1 and 2.0")

               if "minAdjustment" in rap:
                   min_adj = rap["minAdjustment"]
                   if not _is_number(min_adj) or min_adj < -50 or min_adj > 0:
                       errors.append("ze1_close.riskAdjustedPricing.minAdjustment must be between -50 and 0")

               if "maxAdjustment" in rap:
                   max_adj = rap["maxAdjustment"]
                   if not _is_number(max_adj) or max_adj < 0 or max_adj > 50:
                       errors.append("ze1_close.riskAdjustedPricing.maxAdjustment must be between 0 and 50")

    # Validate O1 Cancel section
    if "o1_cancel" in config and isinstance(config["o1_cancel"], dict):
        o1 = config["o1_cancel"]
        if "timeoutSeconds" not in o1:
            errors.append("o1_cancel.timeoutSeconds is required")
        elif not isinstance(o1["timeoutSeconds"], int) or o1["timeoutSeconds"] < 0:
            errors.append("o1_cancel.timeoutSeconds must be a non-negative integer")

        if "conditions" not in o1:
            errors.append("o1_cancel.conditions is required")
        elif not isinstance(o1["conditions"], list):
            errors.append("o1_cancel.conditions must be an array")
        else:
            _validate_conditions_list("o1_cancel.conditions", o1["conditions"], errors, config)

    # Validate Emergency Exit section
    if "emergency_exit" in config and isinstance(config["emergency_exit"], dict):
        emergency = config["emergency_exit"]
        if "conditions" not in emergency:
            errors.append("emergency_exit.conditions is required")
        elif not isinstance(emergency["conditions"], list):
            errors.append("emergency_exit.conditions must be an array")
        else:
            _validate_conditions_list("emergency_exit.conditions", emergency["conditions"], errors, config)

        if "cooldownMinutes" not in emergency:
            errors.append("emergency_exit.cooldownMinutes is required")
        elif not isinstance(emergency["cooldownMinutes"], int) or emergency["cooldownMinutes"] < 0 or emergency["cooldownMinutes"] > 1440:
            errors.append("emergency_exit.cooldownMinutes must be between 0 and 1440")

        if "actions" not in emergency:
            errors.append("emergency_exit.actions is required")
        elif isinstance(emergency["actions"], dict):
            actions = emergency["actions"]
            required_actions = ["cancelPending", "closePosition", "logEvent"]
            for action in required_actions:
                if action not in actions:
                    errors.append(f"emergency_exit.actions.{action} is required")
                elif not isinstance(actions[action], bool):
                    errors.append(f"emergency_exit.actions.{action} must be a boolean")

    # Global limits validation with business logic
    gl = config.get("global_limits", {})
    if gl and not isinstance(gl, dict):
        errors.append("global_limits must be an object")
    elif gl:
        # Validate critical business constraints
        if "base_position_pct" in gl:
            val = gl["base_position_pct"]
            if not _is_number(val) or val <= 0 or val > 1:
                errors.append("global_limits.base_position_pct must be between 0 and 1")

        if "max_leverage" in gl:
            val = gl["max_leverage"]
            # TIER 3.1: Synchronized with order_manager and mexc_futures_adapter (1-10)
            if not _is_number(val) or val < 1 or val > 10:
                errors.append("global_limits.max_leverage must be between 1 and 10 (synchronized with system-wide limits)")
            elif val > 5:
                warnings.append(f"global_limits.max_leverage={val}x is HIGH RISK. Liquidation at {(100/val):.1f}% price movement. Recommended: 1-3x")

        if "stop_loss_buffer_pct" in gl:
            val = gl["stop_loss_buffer_pct"]
            if not _is_number(val) or val <= 0 or val > 50:
                errors.append("global_limits.stop_loss_buffer_pct must be between 0 and 50")

    # Cross-field validation
    if "global_limits" in config and isinstance(config["global_limits"], dict):
        gl = config["global_limits"]
        if "min_position_size_usdt" in gl and "max_position_size_usdt" in gl:
            min_pos = gl["min_position_size_usdt"]
            max_pos = gl["max_position_size_usdt"]
            if _is_number(min_pos) and _is_number(max_pos) and min_pos >= max_pos:
                errors.append("global_limits.min_position_size_usdt must be less than max_position_size_usdt")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def _validate_conditions_list(path: str, conditions: List[Dict[str, Any]], errors: List[str], payload: Optional[Dict] = None) -> None:
    """Validate a list of conditions with SEC-0-2 security checks."""
    for i, condition in enumerate(conditions):
        if not isinstance(condition, dict):
            errors.append(f"{path}[{i}] must be an object")
            continue

        required_fields = ["id", "indicatorId", "operator", "value"]
        for field in required_fields:
            if field not in condition:
                errors.append(f"{path}[{i}].{field} is required")

        # SEC-0-2: Validate indicatorId against allowlist (AC1)
        if "indicatorId" in condition:
            validate_indicator_id(condition["indicatorId"], f"{path}[{i}].indicatorId", errors, payload)

        # SEC-0-2: Validate operator against allowlist (AC2)
        if "operator" in condition and condition["operator"] not in ALLOWED_CONDITION_OPERATORS:
            errors.append(f"{path}[{i}].operator must be one of: {', '.join(ALLOWED_CONDITION_OPERATORS)}")
            _log_security_rejection(f"{path}[{i}].operator", condition["operator"], "Invalid operator", payload)

        if "value" in condition and not _is_number(condition["value"]):
            errors.append(f"{path}[{i}].value must be a number")

        # SEC-0-2: Check for injection patterns in string fields
        for field in ["id", "indicatorId", "label", "description"]:
            if field in condition and isinstance(condition[field], str):
                validate_security_patterns(condition[field], f"{path}[{i}].{field}", errors, payload)

