"""
Measure Registry
================
Defines supported indicator/measure types, parameter schemas, and basic validation.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple


_MEASURES: Dict[str, Dict[str, Any]] = {
    # Basic technical/market measures are pre-existing in IndicatorType
    # Parametric measures we standardize here
    "TWPA": {
        "category": "price_window",
        "params": {
            "t1": {"type": "number", "required": True, "desc": "seconds back (start)"},
            "t2": {"type": "number", "required": True, "desc": "seconds back (end)"},
        },
        "description": "Time-Weighted Price Average over [now - t1, now - t2]",
    },
    "LAST_PRICE": {
        "category": "price_window",
        "params": {"t1": {"type": "number"}, "t2": {"type": "number"}},
        "description": "Last price in window [now - t1, now - t2]",
    },
    "FIRST_PRICE": {
        "category": "price_window",
        "params": {"t1": {"type": "number"}, "t2": {"type": "number"}},
        "description": "First price in window [now - t1, now - t2]",
    },
    "MAX_PRICE": {
        "category": "price_window",
        "params": {"t1": {"type": "number"}, "t2": {"type": "number"}},
        "description": "Max price in window [now - t1, now - t2]",
    },
    "MIN_PRICE": {
        "category": "price_window",
        "params": {"t1": {"type": "number"}, "t2": {"type": "number"}},
        "description": "Min price in window [now - t1, now - t2]",
    },
    "VELOCITY": {
        "category": "price_change",
        "params": {
            "current_window": {
                "type": "object",
                "required": True,
                "schema": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
            },
            "baseline_window": {
                "type": "object",
                "required": True,
                "schema": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
            },
            "price_method": {"type": "string", "enum": ["LAST_PRICE", "TWPA"], "required": False},
        },
        "description": "Percent change between current and baseline windows using price method",
    },
    # Orderbook time-weighted measures
    "AVG_BEST_BID": {
        "category": "orderbook_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "Time-weighted average of best_bid over window",
    },
    "AVG_BEST_ASK": {
        "category": "orderbook_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "Time-weighted average of best_ask over window",
    },
    "AVG_BID_QTY": {
        "category": "orderbook_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "Time-weighted average of top-level bid quantity",
    },
    "AVG_ASK_QTY": {
        "category": "orderbook_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "Time-weighted average of top-level ask quantity",
    },
    "TW_MIDPRICE": {
        "category": "orderbook_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "Time-weighted mid price over window",
    },
    # Volume/Deals
    "SUM_VOLUME": {
        "category": "deals_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "Sum of volumes in window",
    },
    "AVG_VOLUME": {
        "category": "deals_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "Average volume per deal in window",
    },
    "COUNT_DEALS": {
        "category": "deals_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "Number of deals in window",
    },
    "VWAP": {
        "category": "deals_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "Volume Weighted Average Price in window",
    },
    "VOLUME_SURGE": {
        "category": "deals_compare",
        "params": {
            "current_window": {"type": "object", "required": True, "schema": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}}},
            "baseline_window": {"type": "object", "required": True, "schema": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}}},
        },
        "description": "Ratio of current sum(volume) to baseline sum(volume)",
    },
    "VOLUME_CONCENTRATION": {
        "category": "deals_compare",
        "params": {
            "short_window": {"type": "object", "required": True, "schema": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}}},
            "long_window": {"type": "object", "required": True, "schema": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}}},
        },
        "description": "sum_volume(short) / sum_volume(long)",
    },
    "VOLUME_ACCELERATION": {
        "category": "deals_compare",
        "params": {
            "current_window": {"type": "object", "required": True, "schema": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}}},
            "previous_window": {"type": "object", "required": True, "schema": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}}},
            "baseline_window": {"type": "object", "required": True, "schema": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}}},
        },
        "description": "Volume_Surge(current) - Volume_Surge(previous) with common baseline",
    },
    "TRADE_FREQUENCY": {
        "category": "deals_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "count_deals / window_seconds * 60",
    },
    "AVERAGE_TRADE_SIZE": {
        "category": "deals_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "sum_volume / count_deals",
    },
    "BID_ASK_IMBALANCE": {
        "category": "orderbook_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "(avg_bid_qty - avg_ask_qty) / (avg_bid_qty + avg_ask_qty)",
    },
    "SPREAD_PERCENTAGE": {
        "category": "orderbook_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "avg_spread / mid * 100",
    },
    "SPREAD_VOLATILITY": {
        "category": "orderbook_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}},
        "description": "std dev of spread values in window",
    },
    "VOLUME_PRICE_CORRELATION": {
        "category": "deals_window",
        "params": {"t1": {"type": "number", "required": True}, "t2": {"type": "number", "required": True}, "min_deals": {"type": "number"}},
        "description": "Pearson correlation(price diffs, volume deviations)",
    },
}


def list_measures() -> List[Dict[str, Any]]:
    items = []
    for name, spec in _MEASURES.items():
        items.append({
            "name": name,
            "category": spec.get("category"),
            "params": spec.get("params"),
            "description": spec.get("description"),
        })
    return items


def validate_params(measure_name: str, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    spec = _MEASURES.get(str(measure_name).upper())
    if not spec:
        return True, errors  # Unknown here; base types validated elsewhere

    pdef = spec.get("params", {})
    for key, rule in pdef.items():
        if rule.get("required") and key not in params:
            errors.append(f"Missing required param: {key}")
            continue
        if key not in params:
            continue
        val = params.get(key)
        typ = rule.get("type")
        if typ == "number" and not isinstance(val, (int, float)):
            errors.append(f"Param {key} must be a number")
        elif typ == "string" and not isinstance(val, str):
            errors.append(f"Param {key} must be a string")
        elif typ == "object":
            if not isinstance(val, dict):
                errors.append(f"Param {key} must be an object")
            else:
                subschema = rule.get("schema", {})
                for sk, sr in subschema.items():
                    if sr.get("required") and sk not in val:
                        errors.append(f"{key}.{sk} is required")
                    else:
                        v = val.get(sk)
                        if v is not None and sr.get("type") == "number" and not isinstance(v, (int, float)):
                            errors.append(f"{key}.{sk} must be a number")
        if "enum" in rule and val is not None and str(val).upper() not in [e for e in rule.get("enum", [])]:
            errors.append(f"Param {key} must be one of {rule['enum']}")

    return (len(errors) == 0), errors
