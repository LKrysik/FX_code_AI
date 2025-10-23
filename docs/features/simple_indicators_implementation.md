# Simple Indicators Implementation for Strategy Builder

## Executive Summary

Implement simple, reliable indicators for Strategy Builder based on existing streaming indicator engine. Focus on fundamental aggregators (GRUPA A) and basic velocity/momentum indicators (GRUPA B) that can be used immediately in trading strategies.

**Business Value**: Enable users to build basic trading strategies using proven indicators without complex dependencies or timing issues.

**Technical Approach**: Leverage existing StreamingIndicatorEngine, fix critical architectural problems, and integrate with Strategy Builder node catalog.

## Functional Requirements

### Core Indicators to Implement

#### GRUPA A: Fundamental Aggregators (Priority 1)
- [ ] `max_price(t1, t2)` - Maximum price in time window
- [ ] `min_price(t1, t2)` - Minimum price in time window
- [ ] `first_price(t1, t2)` - First price in time window
- [ ] `last_price(t1, t2)` - Last price in time window
- [ ] `sum_volume(t1, t2)` - Total volume in time window
- [ ] `avg_volume(t1, t2)` - Average volume per deal
- [ ] `count_deals(t1, t2)` - Number of deals in time window
- [ ] `TWPA(t1, t2)` - Time-weighted price average
- [ ] `VWAP(t1, t2)` - Volume-weighted average price

#### GRUPA B: Basic Velocity & Momentum (Priority 2)
- [ ] `Velocity(current_window, baseline_window, price_method)` - Price velocity between windows
- [ ] `Volume_Surge(t1, t2, baseline_t1, baseline_t2)` - Volume surge ratio
- [ ] `Volume_Concentration(short_window, long_window)` - Volume concentration ratio

### Strategy Builder Integration
- [ ] Add indicator nodes to node catalog
- [ ] Implement drag-and-drop indicator placement
- [ ] Real-time indicator value display
- [ ] Parameter configuration UI
- [ ] Indicator-to-condition connections

## Technical Architecture

### Component Integration

```
Strategy Builder UI
        ↓
Node Catalog (Indicator Nodes)
        ↓
StreamingIndicatorEngine
        ↓
Market Data (LiveMarketAdapter)
```

### Critical Problem Resolution

#### Problem 1: Time Window Semantics
**Current Issue**: `TWPA(300, 0)` is ambiguous - does it mean "last 5 minutes" or "5 minutes ago to now"?

**Solution**:
- Standardize on `t1 > t2` convention where `t1` is seconds ago for start, `t2` is seconds ago for end
- Example: `TWPA(300, 0)` = "from 5 minutes ago to now"
- Add validation to prevent `t1 < t2` usage
- Document semantics clearly in API

#### Problem 2: DAG Dependency Risks
**Current Issue**: Indicator dependencies can cause cascading failures and deadlocks.

**Solution**:
- Implement circuit breaker pattern for indicator calculations
- Add timeout protection (5 second max per calculation)
- Graceful degradation - return last known value on failure
- Dependency validation to prevent circular references

#### Problem 3: Cache Timing Issues
**Current Issue**: Cache keys without timestamps cause stale data usage.

**Solution**:
- Implement time-bucketed cache keys: `"TWPA:BTC_USDT:1m:300:0:1727209200"`
- Automatic cache invalidation on time bucket changes
- Cache TTL based on indicator type (1-60 seconds)

### Implementation Plan

#### Phase 1: Core Infrastructure Fixes (Week 1)
1. Fix time window semantics validation
2. Implement circuit breaker for indicator calculations
3. Add time-bucketed caching system
4. Create indicator health monitoring

#### Phase 2: Simple Indicators Implementation (Week 2)
1. Implement GRUPA A fundamental aggregators
2. Add comprehensive unit tests
3. Integrate with Strategy Builder node catalog
4. Add parameter validation and error handling

#### Phase 3: Basic Velocity Indicators (Week 3)
1. Implement Velocity and Volume_Surge indicators
2. Add multi-timeframe support
3. Create indicator composition patterns
4. Performance optimization and caching

#### Phase 4: Strategy Builder Integration (Week 4)
1. Add indicator nodes to UI palette
2. Implement real-time value display
3. Add indicator-to-condition connections
4. Create example strategies using new indicators

## Code Changes

### New Files
- `src/indicators/simple_indicators.py` - Simple indicator implementations
- `src/strategy_builder/indicator_nodes.py` - Strategy Builder indicator nodes
- `tests/test_simple_indicators.py` - Comprehensive test suite

### Modified Files
- `src/domain/services/streaming_indicator_engine.py` - Add fixes for critical problems
- `src/strategy_graph/node_catalog.py` - Add simple indicator nodes
- `src/application/services/strategy_builder_api.py` - Add indicator support

## Testing Strategy

### Unit Tests
- Individual indicator calculation accuracy
- Parameter validation and error handling
- Cache behavior and TTL functionality
- Circuit breaker activation and recovery

### Integration Tests
- End-to-end indicator pipeline from market data to UI
- Strategy Builder indicator node functionality
- Multi-indicator strategy execution
- Performance under load (100+ concurrent indicators)

### Performance Benchmarks
- Indicator calculation latency (<100ms target)
- Memory usage stability
- Cache hit rates (>80% target)
- Concurrent user scalability

## Risk Mitigation

### Technical Risks
- **Cache Corruption**: Implement atomic cache operations with rollback
- **Memory Leaks**: Add comprehensive TTL cleanup and monitoring
- **Calculation Deadlocks**: Circuit breaker with timeout protection
- **Data Staleness**: Time-bucketed cache invalidation

### Business Risks
- **Complex Dependencies**: Start with simple indicators, add complexity gradually
- **Performance Issues**: Implement performance monitoring from day 1
- **User Confusion**: Clear documentation and validation for time windows

## Success Metrics

### Technical Metrics
- All indicators calculate within 100ms
- 99.9% calculation success rate
- Cache hit rate > 80%
- Memory usage stable under load

### Business Metrics
- 10+ simple indicators available in Strategy Builder
- Users can build basic momentum strategies
- Indicator values update in real-time (<2s latency)
- No critical timing or calculation errors in production

## Dependencies & Blockers

### Prerequisites
- ✅ StreamingIndicatorEngine operational (GOAL_02 completed)
- ✅ Strategy Builder UI functional (Sprint 7A completed)
- ✅ Live market data pipeline working (GOAL_02 completed)

### External Dependencies
- Market data feed reliability
- Frontend WebSocket connectivity
- Database performance for caching

## Migration & Deployment

### Deployment Strategy
1. Deploy infrastructure fixes first (no breaking changes)
2. Add simple indicators incrementally
3. Update Strategy Builder UI separately
4. Full integration testing before production release

### Rollback Plan
- Feature flags for all new indicators
- Circuit breaker can disable problematic indicators
- Cache can be flushed if corruption detected
- Previous indicator implementations remain available

## Documentation Updates

### User Documentation
- Indicator reference guide with examples
- Strategy Builder tutorial for indicator usage
- Time window semantics explanation
- Troubleshooting guide for common issues

### Technical Documentation
- API reference for indicator calculations
- Cache architecture documentation
- Performance monitoring guide
- Circuit breaker configuration

## Success Criteria

### Functional Completeness
- [ ] 10+ simple indicators implemented and tested
- [ ] Strategy Builder can use indicators in strategies
- [ ] Real-time indicator values displayed in UI
- [ ] Parameter configuration working
- [ ] Error handling and validation implemented

### Quality Assurance
- [ ] 95%+ test coverage for new code
- [ ] Performance benchmarks met
- [ ] No critical bugs in production
- [ ] Documentation complete and accurate

### User Acceptance
- [ ] Indicators work reliably in live trading conditions
- [ ] Strategy Builder UX intuitive for indicator usage
- [ ] Performance acceptable for real-time trading
- [ ] Error messages helpful for troubleshooting