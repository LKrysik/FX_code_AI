# AGENT HANDOFF - GOAL_03: Real Indicators Implementation

## Sprint Assignment: SPRINT_GOAL_03
**Agent**: Developer
**Mode**: Code Implementation
**Priority**: HIGH
**Deadline**: 3 weeks from assignment

## Context
SPRINT_GOAL_02 completed successfully with production-grade Indicator Variants System. GOAL_03 focuses on removing mock values and implementing Priority 1-2 mathematical indicators from INDICATORS_TO_IMPLEMENT.md specification.

## Task Overview
Implement 25 mathematical indicators by replacing mock returns with real calculations and adding new indicator functions to StreamingIndicatorEngine.

## Detailed Requirements

### Phase 1: Mock Removal (6 indicators)
Replace fixed return values with real mathematical calculations:

1. **VOLUME_24H** (currently returns 1000000.0)
   - Calculate: Sum of volume over last 24 hours from deal data
   - Location: `_calculate_volume_24h()` in StreamingIndicatorEngine
   - Dependencies: Deal data aggregation

2. **PUMP_PROBABILITY** (currently returns 65.0)
   - Calculate: Algorithmic pump probability based on velocity, volume surge, momentum
   - Location: `_calculate_pump_probability()` in StreamingIndicatorEngine
   - Dependencies: Velocity, Volume_Surge indicators

3. **MARKET_STRESS_INDICATOR** (currently returns 15.0)
   - Calculate: Composite stress index from volatility, spread, volume metrics
   - Location: `_calculate_market_stress_indicator()` in StreamingIndicatorEngine
   - Dependencies: Price_Volatility, Spread_Percentage, Volume_Surge

4. **PORTFOLIO_EXPOSURE_PCT** (currently returns 5.0)
   - Calculate: Current portfolio exposure as percentage
   - Location: `_calculate_portfolio_exposure_pct()` in StreamingIndicatorEngine
   - Dependencies: Position data integration

5. **UNREALIZED_PNL_PCT** (currently returns 2.5)
   - Calculate: Unrealized profit/loss percentage
   - Location: `_calculate_unrealized_pnl_pct()` in StreamingIndicatorEngine
   - Dependencies: Position data, current prices

6. **BOLLINGER_BANDS** (currently returns SMA)
   - Fix: Implement proper Bollinger Bands with standard deviation
   - Location: `_calculate_bollinger_bands()` in StreamingIndicatorEngine
   - Formula: SMA ± (2 × Standard Deviation)

### Phase 2: Priority 1 - Foundation (8 indicators)

#### Group A Extensions:
7. **MAX_TWPA(t1,t2,measure)**
   - Find maximum TWPA value over time window
   - Parameters: t1, t2 (time window), measure (TWPA variant)
   - Implementation: Track TWPA values and return maximum

8. **MIN_TWPA(t1,t2,measure)**
   - Find minimum TWPA value over time window
   - Parameters: Same as MAX_TWPA
   - Implementation: Track TWPA values and return minimum

9. **VTWPA(t1,t2)**
   - Volume-Time Weighted Price Average
   - Formula: Σ(price_i × volume_i × duration_i) / Σ(volume_i × duration_i)
   - Parameters: t1, t2 (time window)
   - Dependencies: Deal data with volume and timestamps

#### Group B Extensions:
10. **Velocity_Cascade**
    - Multi-timeframe velocity analysis
    - Parameters: timeframes [30, 60, 120, 300, 600, 900], price_method
    - Returns: List of velocity values for each timeframe

11. **Velocity_Acceleration**
    - Velocity rate of change
    - Formula: V_short - V_long
    - Parameters: short_window, long_window, price_method

12. **Momentum_Streak**
    - Count consecutive periods with same direction
    - Parameters: period_length, lookback_periods, price_method
    - Returns: Length of current directional streak

13. **Direction_Consistency**
    - Percentage of periods with consistent direction
    - Formula: COUNT(same_direction_moves) / total_periods
    - Parameters: Same as Momentum_Streak

### Phase 3: Priority 2 - Core Features (11 indicators)

#### Group C Extensions:
14. **Trade_Size_Momentum**
    - Relative change in average trade size
    - Formula: ATS(current_window) / ATS(baseline_window)
    - Parameters: current_window, baseline_window

#### Group D Extensions:
15. **Mid_Price_Velocity**
    - Velocity of order book mid price
    - Formula: (TW_MidPrice(0,0) - TW_MidPrice(t,0)) / TW_MidPrice(t,0) × 100
    - Parameters: t (comparison timeframe)

16. **Total_Liquidity**
    - Combined bid and ask liquidity
    - Formula: avg_bid_qty + avg_ask_qty
    - Parameters: t1, t2 (time window)

17. **Liquidity_Ratio**
    - Current vs baseline liquidity ratio
    - Formula: Total_Liquidity(current) / Total_Liquidity(baseline)
    - Parameters: current_window, baseline_window

18. **Liquidity_Drain_Index**
    - Liquidity depletion over time
    - Formula: (baseline - current) / baseline
    - Parameters: current_window, baseline_window

19. **Deal_vs_Mid_Deviation**
    - Price deviation from order book mid
    - Formula: |TWPA(t1,t2) - TW_MidPrice(t1,t2)| / TW_MidPrice(t1,t2) × 100
    - Parameters: t1, t2 (time window)

#### Group E Extensions:
20. **Inter_Deal_Intervals**
    - Time intervals between consecutive trades
    - Returns: List of intervals in seconds
    - Parameters: t1, t2 (time window)

21. **Decision_Density_Acceleration**
    - Change in trading decision frequency
    - Formula: MEDIAN(baseline_intervals) / MEDIAN(current_intervals)
    - Parameters: current_window, baseline_window

22. **Trade_Clustering_Coefficient**
    - Measure of trade timing clustering
    - Formula: VARIANCE(intervals) / MEAN(intervals)²
    - Parameters: t1, t2 (time window)

23. **Price_Volatility**
    - Standard deviation of price returns
    - Formula: STDEV([price_i - price_{i-1}] / price_{i-1})
    - Parameters: t1, t2 (time window)

24. **Deal_Size_Volatility**
    - Variability in trade sizes
    - Formula: STDEV(volume_values) / MEAN(volume_values)
    - Parameters: t1, t2 (time window)

## Technical Requirements
- All implementations in `src/domain/services/streaming_indicator_engine.py`
- Maintain existing performance: <50ms per calculation
- Memory efficient: No memory leaks, <500MB total usage
- Cache integration: Use existing time-bucketed caching
- Error handling: Graceful fallbacks for insufficient data
- Testing: Unit tests for each indicator with edge cases

## Success Criteria
- All 25 indicators return mathematically accurate values
- Performance regression <10% vs current implementation
- Memory stability maintained (91.2% stability score target)
- Cache hit rate >85% for new indicators
- Comprehensive test suite with >90% coverage

## Files to Review
- `src/domain/services/streaming_indicator_engine.py` (main implementation)
- `docs/trading/INDICATORS_TO_IMPLEMENT.md` (detailed specifications)
- `docs/MVP.md` (USER_REC_02 requirements)
- `tests/indicators_test.py` (existing test patterns)

## Evidence Requirements
- Unit tests for all 25 indicators
- Performance benchmarks before/after implementation
- Mathematical accuracy validation against reference implementations
- Memory usage profiling during extended operation

## Next Steps
1. Start with Phase 1 (mock removal) - lowest risk
2. Implement Phase 2 (foundation indicators)
3. Complete Phase 3 (advanced features)
4. Comprehensive testing and performance validation
5. Evidence collection and documentation

Ready for implementation. Contact orchestrator for questions or blockers.