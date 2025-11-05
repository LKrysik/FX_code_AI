"""
Strategy Schema Validation (5-Section Format)
Lightweight validator for 5-section strategy JSON configs without extra dependencies.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


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
            _validate_conditions_list("s1_signal.conditions", s1["conditions"], errors)

    # Validate Z1 Entry section
    if "z1_entry" in config and isinstance(config["z1_entry"], dict):
        z1 = config["z1_entry"]
        if "conditions" not in z1:
            errors.append("z1_entry.conditions is required")
        elif not isinstance(z1["conditions"], list):
            errors.append("z1_entry.conditions must be an array")
        else:
            _validate_conditions_list("z1_entry.conditions", z1["conditions"], errors)

        if "positionSize" not in z1:
            errors.append("z1_entry.positionSize is required")
        elif isinstance(z1["positionSize"], dict):
            pos_size = z1["positionSize"]
            if pos_size.get("type") not in ["fixed", "percentage"]:
                errors.append("z1_entry.positionSize.type must be 'fixed' or 'percentage'")
            if not _is_number(pos_size.get("value", 0)) or pos_size["value"] < 0:
                errors.append("z1_entry.positionSize.value must be a non-negative number")

        # Validate stop loss
        if "stopLoss" in z1 and isinstance(z1["stopLoss"], dict):
            sl = z1["stopLoss"]
            if sl.get("enabled") and "offsetPercent" in sl:
                offset = sl["offsetPercent"]
                if not _is_number(offset) or offset < 0 or offset > 100:
                    errors.append("z1_entry.stopLoss.offsetPercent must be between 0 and 100")

        # Validate take profit (required if enabled)
        if "takeProfit" in z1 and isinstance(z1["takeProfit"], dict):
            tp = z1["takeProfit"]
            if tp.get("enabled"):
                if "offsetPercent" not in tp:
                    errors.append("z1_entry.takeProfit.offsetPercent is required when enabled")
                elif not _is_number(tp["offsetPercent"]) or tp["offsetPercent"] < 0 or tp["offsetPercent"] > 1000:
                    errors.append("z1_entry.takeProfit.offsetPercent must be between 0 and 1000")

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
           _validate_conditions_list("ze1_close.conditions", ze1["conditions"], errors)

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
            _validate_conditions_list("o1_cancel.conditions", o1["conditions"], errors)

    # Validate Emergency Exit section
    if "emergency_exit" in config and isinstance(config["emergency_exit"], dict):
        emergency = config["emergency_exit"]
        if "conditions" not in emergency:
            errors.append("emergency_exit.conditions is required")
        elif not isinstance(emergency["conditions"], list):
            errors.append("emergency_exit.conditions must be an array")
        else:
            _validate_conditions_list("emergency_exit.conditions", emergency["conditions"], errors)

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


def _validate_conditions_list(path: str, conditions: List[Dict[str, Any]], errors: List[str]) -> None:
    """Validate a list of conditions."""
    for i, condition in enumerate(conditions):
        if not isinstance(condition, dict):
            errors.append(f"{path}[{i}] must be an object")
            continue

        required_fields = ["id", "indicatorId", "operator", "value"]
        for field in required_fields:
            if field not in condition:
                errors.append(f"{path}[{i}].{field} is required")

        if "operator" in condition and condition["operator"] not in [">", "<", ">=", "<="]:
            errors.append(f"{path}[{i}].operator must be one of: >, <, >=, <=")

        if "value" in condition and not _is_number(condition["value"]):
            errors.append(f"{path}[{i}].value must be a number")

