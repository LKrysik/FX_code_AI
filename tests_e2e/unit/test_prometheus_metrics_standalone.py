"""
Standalone Tests for Prometheus Metrics
========================================

These tests can run independently without pytest conftest issues.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.infrastructure.monitoring.prometheus_metrics import PrometheusMetrics
from src.infrastructure.monitoring import set_metrics_instance
from src.core.event_bus import EventBus
from src.api.monitoring_routes import get_prometheus_metrics, get_metrics_health


async def test_basic_functionality():
    """Test basic PrometheusMetrics functionality"""
    print("\n=== Test 1: Basic Functionality ===")

    eb = EventBus()
    pm = PrometheusMetrics(eb)

    print("✓ PrometheusMetrics created")

    await pm.subscribe_to_events()
    print("✓ Subscribed to EventBus")

    health = pm.get_health()
    assert health['status'] == 'healthy'
    assert health['subscribed_to_eventbus'] is True
    print("✓ Health check passed")

    await pm.unsubscribe_from_events()
    print("✓ Unsubscribed from EventBus")

    return True


async def test_order_metrics():
    """Test order-related metrics collection"""
    print("\n=== Test 2: Order Metrics ===")

    eb = EventBus()
    pm = PrometheusMetrics(eb)
    await pm.subscribe_to_events()

    # Simulate order created
    await eb.publish('order_created', {
        'order_id': 'order_001',
        'symbol': 'BTC_USDT',
        'side': 'BUY',
        'order_type': 'LIMIT',
        'submission_latency': 0.5
    })
    print("✓ Published order_created event")

    # Simulate order filled
    await eb.publish('order_filled', {
        'order_id': 'order_001',
        'symbol': 'BTC_USDT',
        'side': 'BUY',
        'filled_price': 50000.0,
        'filled_quantity': 0.1
    })
    print("✓ Published order_filled event")

    # Wait for processing
    await asyncio.sleep(0.1)

    # Get metrics
    metrics = pm.get_metrics()
    assert len(metrics) > 0
    print("✓ Metrics collected successfully")

    await pm.unsubscribe_from_events()
    return True


async def test_position_metrics():
    """Test position-related metrics collection"""
    print("\n=== Test 3: Position Metrics ===")

    eb = EventBus()
    pm = PrometheusMetrics(eb)
    await pm.subscribe_to_events()

    # Simulate position update
    await eb.publish('position_updated', {
        'position_id': 'pos_001',
        'symbol': 'BTC_USDT',
        'quantity': 0.1,
        'unrealized_pnl': 100.0,
        'margin_ratio': 0.25
    })
    print("✓ Published position_updated event")

    await asyncio.sleep(0.1)

    metrics = pm.get_metrics()
    assert len(metrics) > 0
    print("✓ Position metrics collected")

    await pm.unsubscribe_from_events()
    return True


async def test_risk_metrics():
    """Test risk-related metrics collection"""
    print("\n=== Test 4: Risk Metrics ===")

    eb = EventBus()
    pm = PrometheusMetrics(eb)
    await pm.subscribe_to_events()

    # Simulate risk alert
    await eb.publish('risk_alert', {
        'severity': 'CRITICAL',
        'alert_type': 'margin_low',
        'message': 'Margin ratio below 15%'
    })
    print("✓ Published risk_alert event")

    await asyncio.sleep(0.1)

    metrics = pm.get_metrics()
    assert len(metrics) > 0
    print("✓ Risk metrics collected")

    await pm.unsubscribe_from_events()
    return True


async def test_manual_updates():
    """Test manual metric updates"""
    print("\n=== Test 5: Manual Updates ===")

    eb = EventBus()
    pm = PrometheusMetrics(eb)

    # Update circuit breaker state
    pm.update_circuit_breaker_state('mexc_adapter', 'CLOSED')
    pm.update_circuit_breaker_state('mexc_adapter', 'OPEN')
    print("✓ Circuit breaker state updated")

    # Update daily loss
    pm.update_daily_loss_percent(5.0)
    print("✓ Daily loss percentage updated")

    return True


async def test_api_endpoints():
    """Test FastAPI monitoring endpoints"""
    print("\n=== Test 6: API Endpoints ===")

    eb = EventBus()
    pm = PrometheusMetrics(eb)
    await pm.subscribe_to_events()
    set_metrics_instance(pm)

    # Test /metrics endpoint
    response = await get_prometheus_metrics()
    assert response.status_code == 200
    assert 'text/plain' in response.media_type
    print("✓ GET /metrics endpoint (status: 200)")

    # Test /health/metrics endpoint
    health = await get_metrics_health()
    assert health['status'] == 'healthy'
    assert health['subscribed_to_eventbus'] is True
    print("✓ GET /health/metrics endpoint (status: healthy)")

    await pm.unsubscribe_from_events()
    return True


async def test_full_trading_flow():
    """Test full trading flow with metrics"""
    print("\n=== Test 7: Full Trading Flow ===")

    eb = EventBus()
    pm = PrometheusMetrics(eb)
    await pm.subscribe_to_events()

    # 1. Order created
    await eb.publish('order_created', {
        'symbol': 'ETH_USDT',
        'side': 'SELL',
        'order_type': 'MARKET',
        'submission_latency': 0.3
    })

    # 2. Order filled
    await eb.publish('order_filled', {
        'symbol': 'ETH_USDT',
        'side': 'SELL',
        'filled_price': 3000.0
    })

    # 3. Position updated
    await eb.publish('position_updated', {
        'symbol': 'ETH_USDT',
        'quantity': 0.5,
        'unrealized_pnl': 50.0,
        'margin_ratio': 0.30
    })

    # 4. Risk alert (optional)
    await eb.publish('risk_alert', {
        'severity': 'WARNING',
        'alert_type': 'daily_loss_approaching'
    })

    await asyncio.sleep(0.2)

    # Get metrics
    metrics = pm.get_metrics()
    metrics_text = metrics.decode('utf-8')

    print("✓ Full trading flow simulated")
    print(f"✓ Metrics output: {len(metrics_text)} bytes")

    await pm.unsubscribe_from_events()
    return True


async def generate_example_output():
    """Generate example metrics output"""
    print("\n=== Example Metrics Output ===")

    eb = EventBus()
    pm = PrometheusMetrics(eb)
    await pm.subscribe_to_events()

    # Simulate various events
    await eb.publish('order_created', {
        'symbol': 'BTC_USDT', 'side': 'BUY', 'order_type': 'LIMIT', 'submission_latency': 0.5
    })
    await eb.publish('order_filled', {
        'symbol': 'BTC_USDT', 'side': 'BUY'
    })
    await eb.publish('position_updated', {
        'symbol': 'BTC_USDT', 'quantity': 0.1, 'unrealized_pnl': 100.0, 'margin_ratio': 0.25
    })
    await eb.publish('risk_alert', {
        'severity': 'WARNING', 'alert_type': 'test_alert'
    })

    pm.update_circuit_breaker_state('mexc_adapter', 'CLOSED')
    pm.update_daily_loss_percent(2.5)

    await asyncio.sleep(0.2)

    metrics = pm.get_metrics()
    metrics_text = metrics.decode('utf-8')

    # Extract relevant metrics
    lines = metrics_text.split('\n')
    relevant_lines = [
        line for line in lines
        if any(metric in line for metric in [
            'orders_submitted_total',
            'orders_filled_total',
            'positions_open_total',
            'unrealized_pnl_usd',
            'margin_ratio_percent',
            'risk_alerts_total',
            'circuit_breaker_state',
            'daily_loss_percent'
        ]) and not line.startswith('#')
    ]

    print("\nKey Metrics:")
    for line in relevant_lines[:20]:  # Show first 20 relevant metrics
        if line.strip():
            print(f"  {line}")

    await pm.unsubscribe_from_events()
    return True


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Prometheus Metrics - Standalone Test Suite")
    print("=" * 60)

    tests = [
        test_basic_functionality,
        test_order_metrics,
        test_position_metrics,
        test_risk_metrics,
        test_manual_updates,
        test_api_endpoints,
        test_full_trading_flow,
        generate_example_output
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
