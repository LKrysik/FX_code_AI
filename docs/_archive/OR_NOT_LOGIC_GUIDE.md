# OR/NOT Logic Guide - Phase 2 Sprint 1

**Complete guide to using OR/NOT/AND logic in Strategy Builder**

---

## Table of Contents

1. [Overview](#overview)
2. [Basic Concepts](#basic-concepts)
3. [Simple Examples](#simple-examples)
4. [Complex Strategies](#complex-strategies)
5. [Real-World Use Cases](#real-world-use-cases)
6. [Best Practices](#best-practices)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting](#troubleshooting)

---

## Overview

Phase 2 Sprint 1 adds powerful OR/NOT/AND logic to Strategy Builder, allowing you to create complex trading strategies with multiple conditions.

### What's New

✅ **AND Logic** (default): All conditions must be TRUE
✅ **OR Logic**: Any condition can be TRUE
✅ **NOT Logic**: Condition must be FALSE
✅ **Nested Groups**: Combine groups with different logic
✅ **Short-circuit**: Faster evaluation (stops early when possible)

### Quick Example

**Before (only AND):**
```
Condition 1: RSI < 30      [AND]
Condition 2: Volume > 1M   [AND]

Result: Both must be TRUE
```

**After (with OR/NOT):**
```
Condition 1: RSI < 30          [OR]
Condition 2: RSI > 70          [AND]
Condition 3: Volume > 5M       [NOT]

Result: (RSI < 30 OR RSI > 70) AND NOT (Volume > 5M)
```

---

## Basic Concepts

### Logic Operators

| Operator | Symbol | Meaning | Example |
|----------|--------|---------|---------|
| **AND** | 🔵 Blue | All must be TRUE | A AND B |
| **OR** | 🟢 Green | Any can be TRUE | A OR B |
| **NOT** | 🔴 Red | Must be FALSE | NOT A |

### How Logic Works

```
Condition 1: A      [Logic Operator]
Condition 2: B      [Logic Operator]
Condition 3: C

Evaluation: A [Logic] B [Logic] C
```

**Important:** Logic operator applies to the NEXT condition.

---

## Simple Examples

### Example 1: Simple OR (Oversold or Overbought)

**Strategy:** Buy when RSI is either oversold OR overbought

```json
{
  "s1_signal": {
    "conditions": [
      {
        "id": "rsi_oversold",
        "indicatorId": "RSI_14",
        "operator": "<",
        "value": 30,
        "logic": "OR"
      },
      {
        "id": "rsi_overbought",
        "indicatorId": "RSI_14",
        "operator": ">",
        "value": 70
      }
    ]
  }
}
```

**Evaluation:**
- RSI = 25 → TRUE (oversold)
- RSI = 75 → TRUE (overbought)
- RSI = 50 → FALSE (neither)

**Result:** `(RSI < 30) OR (RSI > 70)`

---

### Example 2: Simple NOT (Avoid High Volume)

**Strategy:** Buy when price is good BUT NOT when volume is too high

```json
{
  "s1_signal": {
    "conditions": [
      {
        "id": "price_above_ema",
        "indicatorId": "Price",
        "operator": ">",
        "value": 50000,
        "logic": "AND"
      },
      {
        "id": "not_high_volume",
        "indicatorId": "Volume",
        "operator": ">",
        "value": 5000000,
        "logic": "NOT"
      }
    ]
  }
}
```

**Evaluation:**
- Price = 51000, Volume = 1M → TRUE (price good, volume low)
- Price = 51000, Volume = 6M → FALSE (volume too high)
- Price = 49000, Volume = 1M → FALSE (price too low)

**Result:** `(Price > 50000) AND NOT (Volume > 5000000)`

---

### Example 3: Combine OR and AND

**Strategy:** Buy when oversold OR (trending up with high volume)

```json
{
  "s1_signal": {
    "conditions": [
      {
        "id": "rsi_oversold",
        "indicatorId": "RSI_14",
        "operator": "<",
        "value": 30,
        "logic": "OR"
      },
      {
        "id": "price_above_ema",
        "indicatorId": "Price",
        "operator": ">",
        "value": 50000,
        "logic": "AND"
      },
      {
        "id": "high_volume",
        "indicatorId": "Volume",
        "operator": ">",
        "value": 1000000
      }
    ]
  }
}
```

**Evaluation:**
- RSI = 25, Price = any, Volume = any → TRUE (oversold, short-circuit)
- RSI = 50, Price = 51k, Volume = 1.5M → TRUE (trending with volume)
- RSI = 50, Price = 51k, Volume = 500k → FALSE (low volume)
- RSI = 50, Price = 49k, Volume = 1.5M → FALSE (price too low)

**Result:** `(RSI < 30) OR (Price > 50000 AND Volume > 1000000)`

---

## Complex Strategies

### Example 4: Multiple OR Conditions

**Strategy:** Buy on any of these signals: oversold, overbought, or VWAP breakout

```json
{
  "s1_signal": {
    "conditions": [
      {
        "id": "rsi_oversold",
        "indicatorId": "RSI_14",
        "operator": "<",
        "value": 30,
        "logic": "OR"
      },
      {
        "id": "rsi_overbought",
        "indicatorId": "RSI_14",
        "operator": ">",
        "value": 70,
        "logic": "OR"
      },
      {
        "id": "vwap_breakout",
        "indicatorId": "Price",
        "operator": ">",
        "value": 52000
      }
    ]
  }
}
```

**Result:** `(RSI < 30) OR (RSI > 70) OR (Price > 52000)`

---

### Example 5: NOT with Multiple Conditions

**Strategy:** Buy when trending up, but NOT during pump (high volume) or dump (high volatility)

```json
{
  "s1_signal": {
    "conditions": [
      {
        "id": "price_above_ema",
        "indicatorId": "Price",
        "operator": ">",
        "value": 50000,
        "logic": "AND"
      },
      {
        "id": "not_pump",
        "indicatorId": "Volume",
        "operator": ">",
        "value": 5000000,
        "logic": "NOT"
      },
      {
        "id": "not_dump",
        "indicatorId": "Volatility",
        "operator": ">",
        "value": 0.05,
        "logic": "NOT"
      }
    ]
  }
}
```

**Result:** `(Price > 50000) AND NOT (Volume > 5000000) AND NOT (Volatility > 0.05)`

---

### Example 6: Nested Groups (Advanced)

**Strategy:** (Oversold OR Overbought) AND (High Volume OR Breakout)

**Using ConditionGroup component:**

```typescript
// Group 1: RSI signals (OR)
const rsiGroup: ConditionGroup = {
  id: "rsi_group",
  logic: "OR",
  conditions: [
    {
      id: "1",
      indicatorId: "RSI_14",
      operator: "<",
      value: 30
    },
    {
      id: "2",
      indicatorId: "RSI_14",
      operator: ">",
      value: 70
    }
  ]
};

// Group 2: Confirmation signals (OR)
const confirmGroup: ConditionGroup = {
  id: "confirm_group",
  logic: "OR",
  conditions: [
    {
      id: "3",
      indicatorId: "Volume",
      operator: ">",
      value: 1000000
    },
    {
      id: "4",
      indicatorId: "Price",
      operator: ">",
      value: 52000
    }
  ]
};

// Root group combines both (AND)
const rootGroup: ConditionGroup = {
  id: "root",
  logic: "AND",
  conditions: [],
  groups: [rsiGroup, confirmGroup]
};
```

**Result:** `(RSI < 30 OR RSI > 70) AND (Volume > 1M OR Price > 52k)`

---

## Real-World Use Cases

### Use Case 1: Mean Reversion Strategy

**Goal:** Buy when oversold and NOT during high volatility

```json
{
  "s1_signal": {
    "conditions": [
      {
        "id": "rsi_oversold",
        "indicatorId": "RSI_14",
        "operator": "<",
        "value": 30,
        "logic": "AND"
      },
      {
        "id": "bollinger_low",
        "indicatorId": "Price",
        "operator": "<",
        "value": 49000,
        "logic": "AND"
      },
      {
        "id": "not_volatile",
        "indicatorId": "ATR",
        "operator": ">",
        "value": 1000,
        "logic": "NOT"
      }
    ]
  }
}
```

**Why:** Avoid mean reversion trades during high volatility (ATR).

---

### Use Case 2: Trend Following with Filters

**Goal:** Buy on trend breakout OR momentum, but NOT during low liquidity

```json
{
  "s1_signal": {
    "conditions": [
      {
        "id": "ema_breakout",
        "indicatorId": "Price",
        "operator": ">",
        "value": 50000,
        "logic": "OR"
      },
      {
        "id": "macd_positive",
        "indicatorId": "MACD",
        "operator": ">",
        "value": 0,
        "logic": "AND"
      },
      {
        "id": "not_low_liquidity",
        "indicatorId": "Volume",
        "operator": "<",
        "value": 100000,
        "logic": "NOT"
      }
    ]
  }
}
```

**Result:** `(Price > 50k OR MACD > 0) AND NOT (Volume < 100k)`

---

### Use Case 3: Multi-Signal Entry

**Goal:** Buy on any of these: technical signal, fundamental signal, or sentiment signal

```json
{
  "s1_signal": {
    "conditions": [
      {
        "id": "technical",
        "indicatorId": "RSI_14",
        "operator": "<",
        "value": 30,
        "logic": "OR"
      },
      {
        "id": "fundamental",
        "indicatorId": "PriceEarnings",
        "operator": "<",
        "value": 15,
        "logic": "OR"
      },
      {
        "id": "sentiment",
        "indicatorId": "SocialScore",
        "operator": ">",
        "value": 0.7
      }
    ]
  }
}
```

**Benefit:** Multiple entry signals increase opportunity without sacrificing quality.

---

## Best Practices

### 1. Keep It Simple

❌ **Bad:** Too many nested groups
```
(A AND B) OR ((C OR D) AND (E OR (F AND G)))
```

✅ **Good:** 2-3 levels max
```
(A AND B) OR (C AND D)
```

### 2. Use NOT Sparingly

❌ **Bad:** Multiple NOTs
```
NOT A AND NOT B AND NOT C
```

✅ **Good:** Positive conditions
```
A OR B OR C
```

**Why:** NOT logic can be confusing and harder to test.

### 3. Order Matters for Performance

✅ **Good:** Put likely conditions first (OR short-circuits)
```json
[
  {"id": "cheap_check", "operator": ">", "value": 100, "logic": "OR"},
  {"id": "expensive_db_query", "operator": ">", "value": 200}
]
```

❌ **Bad:** Expensive checks first
```json
[
  {"id": "expensive_db_query", "operator": ">", "value": 200, "logic": "OR"},
  {"id": "cheap_check", "operator": ">", "value": 100}
]
```

### 4. Test Your Logic

Use the **Validation** feature:
1. Build your strategy
2. Click "Validate Strategy"
3. Check which conditions trigger
4. Test with historical data

---

## Performance Considerations

### Short-Circuit Optimization

**AND logic:**
- Stops evaluating after first FALSE
- Put unlikely conditions first

**OR logic:**
- Stops evaluating after first TRUE
- Put likely conditions first

**Example:**
```json
[
  {
    "id": "fast_check",
    "indicatorId": "Price",
    "operator": ">",
    "value": 50000,
    "logic": "OR"
  },
  {
    "id": "slow_check",
    "indicatorId": "ComplexIndicator",
    "operator": ">",
    "value": 100
  }
]
```

If Price > 50000, ComplexIndicator is never evaluated (saved computation).

### Indicator Caching

All indicators are cached, but:
- Complex indicators (VWAP, TWPA) are slower
- Simple comparisons (Price > 50k) are faster

**Tip:** Group slow indicators with OR logic so they might not need evaluation.

---

## Troubleshooting

### Issue 1: Condition Never Triggers

**Problem:** Strategy never enters position

**Check:**
1. Verify indicator values are in expected range
2. Use "Preview Indicators" to see current values
3. Check if NOT is inverting unintentionally
4. Verify logic connectors (AND vs OR)

**Debug:**
```json
// Add debug logging
{
  "id": "debug_price",
  "indicatorId": "Price",
  "operator": ">",
  "value": 0  // Always true, just to log
}
```

---

### Issue 2: Too Many Triggers

**Problem:** Strategy enters too often

**Solution:** Add filters with AND
```json
{
  "conditions": [
    {"id": "main_signal", "..."},  // Your main signal
    {"id": "volume_filter", "indicatorId": "Volume", "operator": ">", "value": 100000, "logic": "AND"},
    {"id": "volatility_filter", "indicatorId": "ATR", "operator": "<", "value": 1000, "logic": "AND"}
  ]
}
```

---

### Issue 3: NOT Logic Confusing

**Problem:** NOT behaves unexpectedly

**Understanding NOT:**
```
Condition: Volume > 1000, Logic: NOT

When Volume = 1500:
  - Condition evaluates to TRUE (1500 > 1000)
  - NOT inverts to FALSE
  - Result: FALSE

When Volume = 500:
  - Condition evaluates to FALSE (500 NOT > 1000)
  - NOT inverts to TRUE
  - Result: TRUE
```

**Tip:** Think of NOT as "when condition is FALSE"

---

## UI Guide

### Creating OR Conditions

1. Add Condition 1
2. Select "OR" from dropdown
3. Add Condition 2
4. Result: Condition 1 OR Condition 2

**Visual:**
```
┌─────────────────────────────┐
│ Condition 1                 │
│ RSI < 30                    │
│ [🟢 OR ▼]          [❌]    │
└─────────────────────────────┘
        ↓ OR
┌─────────────────────────────┐
│ Condition 2                 │
│ RSI > 70                    │
│                    [❌]    │
└─────────────────────────────┘
```

---

### Creating Nested Groups

1. Click "Add Nested Group"
2. Select group logic (AND/OR)
3. Add conditions to group
4. Repeat for multiple groups

**Visual:**
```
┌─────────────────────────────────────┐
│ Group 1 (OR)                        │
│ ┌─────────────────────────────┐   │
│ │ RSI < 30                    │   │
│ └─────────────────────────────┘   │
│ ┌─────────────────────────────┐   │
│ │ RSI > 70                    │   │
│ └─────────────────────────────┘   │
└─────────────────────────────────────┘
        ↓ AND
┌─────────────────────────────────────┐
│ Group 2 (AND)                       │
│ ┌─────────────────────────────┐   │
│ │ Volume > 1M                 │   │
│ └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

---

## Summary

✅ **OR Logic:** Any condition TRUE → Strategy triggers
✅ **NOT Logic:** Condition FALSE → Inverts to TRUE
✅ **AND Logic:** All conditions TRUE → Strategy triggers
✅ **Short-circuit:** Faster evaluation
✅ **Nested Groups:** Complex strategies

**Next Steps:**
1. Try simple OR/NOT in your strategies
2. Test with historical data
3. Monitor performance
4. Iterate and improve

**Need Help?**
- Check examples in this guide
- Run validation before backtest
- Start simple, add complexity gradually

---

Generated: 2025-10-26
Author: Claude AI
Phase: 2 Sprint 1
Feature: OR/NOT Logic
