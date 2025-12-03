#!/usr/bin/env python3
"""
Strategy Builder Diagnostic Script
===================================

Diagnoses issues with Strategy Builder and Indicator Engine integration.

This script:
1. Loads test data from QuestDB
2. Tests indicator calculations
3. Tests strategy condition evaluation
4. Identifies mismatches between indicator_type and condition_type
5. Generates a diagnostic report

Usage:
    python scripts/diagnose_strategy_builder.py [session_id]
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger
from src.infrastructure.config.config_loader import get_settings_from_working_directory
from src.infrastructure.container import Container
from src.data_feed.questdb_provider import QuestDBProvider
from src.domain.services.strategy_manager import (
    Strategy, StrategyState, ConditionGroup, Condition, ConditionResult, StrategyManager
)
from src.domain.services.streaming_indicator_engine.core.types import IndicatorType


# =============================================================================
# DIAGNOSTIC REPORT
# =============================================================================

class DiagnosticReport:
    """Collects and formats diagnostic results"""

    def __init__(self):
        self.sections: List[Tuple[str, str, List[str]]] = []  # (title, status, details)
        self.problems: List[Dict[str, Any]] = []
        self.recommendations: List[str] = []

    def add_section(self, title: str, status: str, details: List[str]):
        self.sections.append((title, status, details))

    def add_problem(self, category: str, severity: str, description: str, solution: str):
        self.problems.append({
            "category": category,
            "severity": severity,
            "description": description,
            "solution": solution
        })

    def add_recommendation(self, text: str):
        self.recommendations.append(text)

    def print_report(self):
        print("\n" + "=" * 80)
        print("STRATEGY BUILDER DIAGNOSTIC REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.now().isoformat()}")

        # Sections
        for title, status, details in self.sections:
            print(f"\n{'=' * 40}")
            status_icon = "[OK]" if status == "OK" else ("[WARN]" if status == "WARN" else "[FAIL]")
            print(f"{status_icon} {title}: {status}")
            print("-" * 40)
            for detail in details:
                print(f"  {detail}")

        # Problems
        if self.problems:
            print(f"\n{'=' * 80}")
            print("PROBLEMS FOUND")
            print("=" * 80)

            for i, problem in enumerate(self.problems, 1):
                severity_icon = "[CRITICAL]" if problem["severity"] == "P0" else ("[HIGH]" if problem["severity"] == "P1" else "[LOW]")
                print(f"\n{severity_icon} [{problem['severity']}] Problem {i}: {problem['category']}")
                print(f"   Description: {problem['description']}")
                print(f"   Solution: {problem['solution']}")

        # Recommendations
        if self.recommendations:
            print(f"\n{'=' * 80}")
            print("RECOMMENDATIONS")
            print("=" * 80)
            for i, rec in enumerate(self.recommendations, 1):
                print(f"  {i}. {rec}")

        # Summary
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print("=" * 80)
        p0_count = sum(1 for p in self.problems if p["severity"] == "P0")
        p1_count = sum(1 for p in self.problems if p["severity"] == "P1")
        p2_count = sum(1 for p in self.problems if p["severity"] == "P2")
        print(f"  Problems: {len(self.problems)} total (P0: {p0_count}, P1: {p1_count}, P2: {p2_count})")
        print(f"  Recommendations: {len(self.recommendations)}")

        if p0_count > 0:
            print("\n  >>> CRITICAL: P0 issues must be fixed before trading!")

        print("=" * 80)


# =============================================================================
# DIAGNOSTIC TESTS
# =============================================================================

async def test_questdb_connection(report: DiagnosticReport) -> bool:
    """Test QuestDB connection"""
    provider = QuestDBProvider()
    try:
        await provider.initialize()
        health = await provider.health_check()

        details = [
            f"PostgreSQL protocol: {'OK' if health.get('postgresql') else 'FAIL'}",
            f"ILP protocol: {'OK' if health.get('ilp') else 'FAIL'}"
        ]

        if health.get('postgresql') and health.get('ilp'):
            report.add_section("QuestDB Connection", "OK", details)
            await provider.close()
            return True
        else:
            report.add_section("QuestDB Connection", "FAIL", details)
            report.add_problem(
                "Database",
                "P0",
                "QuestDB connection failed",
                "Start QuestDB using .\\start_all.ps1"
            )
            await provider.close()
            return False
    except Exception as e:
        report.add_section("QuestDB Connection", "FAIL", [str(e)])
        report.add_problem(
            "Database",
            "P0",
            f"QuestDB connection error: {e}",
            "Start QuestDB using .\\start_all.ps1"
        )
        return False


async def test_test_data_availability(provider: QuestDBProvider, session_id: str, report: DiagnosticReport) -> Tuple[bool, int]:
    """Test if test data is available in QuestDB"""
    try:
        await provider.initialize()

        # Query tick count
        query = f"SELECT COUNT(*) as cnt FROM tick_prices WHERE session_id = '{session_id}'"
        result = await provider.execute_query(query)
        tick_count = result[0]['cnt'] if result else 0

        details = [
            f"Session ID: {session_id}",
            f"Tick prices found: {tick_count}"
        ]

        if tick_count > 0:
            # Get price range
            query2 = f"""
            SELECT
                MIN(price) as min_price,
                MAX(price) as max_price,
                MIN(timestamp) as start_time,
                MAX(timestamp) as end_time
            FROM tick_prices
            WHERE session_id = '{session_id}'
            """
            stats = await provider.execute_query(query2)
            if stats:
                details.append(f"Price range: {stats[0]['min_price']:.4f} - {stats[0]['max_price']:.4f}")
                details.append(f"Time range: {stats[0]['start_time']} - {stats[0]['end_time']}")

            report.add_section("Test Data Availability", "OK", details)
            return True, tick_count
        else:
            report.add_section("Test Data Availability", "FAIL", details)
            report.add_problem(
                "Test Data",
                "P0",
                f"No test data found for session {session_id}",
                "Run: python scripts/generate_test_pump_data.py"
            )
            return False, 0
    except Exception as e:
        report.add_section("Test Data Availability", "FAIL", [str(e)])
        return False, 0


def test_indicator_types(report: DiagnosticReport) -> Dict[str, str]:
    """Test available indicator types"""
    available_types = {t.name: t.value for t in IndicatorType}

    # Check for pump/dump detection indicators
    required_indicators = [
        "PUMP_MAGNITUDE_PCT",
        "VOLUME_SURGE_RATIO",
        "PRICE_VELOCITY",
        "PRICE_MOMENTUM",
        "RSI",
        "SPREAD_PCT"
    ]

    missing = [ind for ind in required_indicators if ind not in available_types]

    details = [
        f"Total indicator types: {len(available_types)}",
        f"Required for pump detection: {len(required_indicators)}",
        f"Missing: {len(missing)}"
    ]

    if missing:
        details.extend([f"  - {m}" for m in missing])
        report.add_section("Indicator Types", "WARN", details)
        report.add_problem(
            "Indicators",
            "P1",
            f"Missing indicator types: {', '.join(missing)}",
            "Implement missing indicators in IndicatorType enum and calculation functions"
        )
    else:
        report.add_section("Indicator Types", "OK", details)

    return available_types


def test_strategy_condition_mapping(report: DiagnosticReport, available_indicators: Dict[str, str]) -> List[str]:
    """Test if strategy condition types map to available indicators"""

    # Default strategy condition types
    strategy_condition_types = [
        "pump_magnitude_pct",
        "volume_surge_ratio",
        "price_momentum",
        "rsi",
        "spread_pct",
        "unrealized_pnl_pct",
        "signal_age_seconds",
        "price_velocity"
    ]

    # Normalize for comparison
    available_normalized = {v.lower(): k for k, v in available_indicators.items()}

    mismatches = []
    details = []

    for cond_type in strategy_condition_types:
        normalized = cond_type.lower()
        if normalized in available_normalized:
            details.append(f"  [+] {cond_type} -> {available_normalized[normalized]}")
        else:
            mismatches.append(cond_type)
            details.append(f"  [-] {cond_type} -> NOT FOUND")

    if mismatches:
        report.add_section("Condition-to-Indicator Mapping", "FAIL", details)
        report.add_problem(
            "Mapping",
            "P0",
            f"Strategy conditions don't map to indicators: {', '.join(mismatches)}",
            "Add these indicators to IndicatorType enum OR rename condition_type in strategies"
        )
    else:
        report.add_section("Condition-to-Indicator Mapping", "OK", details)

    return mismatches


async def test_indicator_calculation(provider: QuestDBProvider, session_id: str, symbol: str, report: DiagnosticReport):
    """Test indicator calculation on test data"""
    try:
        settings = get_settings_from_working_directory()
        event_bus = EventBus()
        logger = StructuredLogger("DiagnosticTest", settings.logging)
        container = Container(settings, event_bus, logger)

        # Create offline indicator engine
        from src.domain.services.offline_indicator_engine import OfflineIndicatorEngine
        engine = OfflineIndicatorEngine()

        # Get test data
        query = f"""
        SELECT timestamp, price, volume, quote_volume
        FROM tick_prices
        WHERE session_id = '{session_id}'
        ORDER BY timestamp ASC
        LIMIT 1000
        """

        await provider.initialize()
        data = await provider.execute_query(query)

        if not data:
            report.add_section("Indicator Calculation", "FAIL", ["No data to calculate"])
            return

        # Test PRICE_VELOCITY calculation
        indicator_key = engine.add_indicator(
            symbol=symbol,
            indicator_type=IndicatorType.PRICE_VELOCITY,
            timeframe="1s",
            period=10,
            t1=60.0,  # 60 second window
            t2=0.0,
            refresh_interval_seconds=1.0
        )

        indicator_info = engine.get_indicator_value(indicator_key)

        if indicator_info:
            details = [
                f"Indicator key: {indicator_key}",
                f"Data points used: {indicator_info.get('data_points', 0)}",
                f"Current value: {indicator_info.get('current_value', 'N/A')}"
            ]

            if indicator_info.get('current_value') is not None:
                report.add_section("Indicator Calculation", "OK", details)
            else:
                report.add_section("Indicator Calculation", "WARN", details)
                report.add_problem(
                    "Calculation",
                    "P1",
                    "Indicator calculated but returned no value",
                    "Check if data has enough price variation for PRICE_VELOCITY"
                )
        else:
            report.add_section("Indicator Calculation", "FAIL", ["Failed to get indicator value"])

    except Exception as e:
        import traceback
        report.add_section("Indicator Calculation", "FAIL", [
            f"Error: {e}",
            f"Traceback: {traceback.format_exc()[:500]}"
        ])
        report.add_problem(
            "Calculation",
            "P0",
            f"Indicator calculation failed: {e}",
            "Check OfflineIndicatorEngine implementation and algorithm registry"
        )


async def test_strategy_evaluation(report: DiagnosticReport):
    """Test strategy condition evaluation logic"""
    try:
        # Create test strategy
        strategy = Strategy(
            strategy_name="diagnostic_test_strategy",
            enabled=True,
            direction="LONG"
        )

        # Add signal detection condition
        strategy.signal_detection.conditions.append(
            Condition(
                name="test_pump",
                condition_type="price_velocity",
                operator="gte",
                value=0.001  # Very low threshold
            )
        )

        # Test evaluation with matching indicator
        test_values_match = {"price_velocity": 0.01}
        result = strategy.evaluate_signal_detection(test_values_match)

        details = []

        if result == ConditionResult.TRUE:
            details.append("[+] Condition evaluates TRUE when indicator matches")
        else:
            details.append(f"[-] Condition returned {result.value} instead of TRUE")
            report.add_problem(
                "Evaluation",
                "P0",
                "Strategy condition evaluation failed",
                "Check Condition.evaluate() implementation"
            )

        # Test evaluation with missing indicator
        test_values_missing = {"other_indicator": 0.01}
        result_missing = strategy.evaluate_signal_detection(test_values_missing)

        if result_missing == ConditionResult.FALSE or result_missing == ConditionResult.PENDING:
            details.append("[+] Condition returns FALSE/PENDING when indicator missing")
        else:
            details.append(f"[-] Condition returned {result_missing.value} for missing indicator")

        # Test case sensitivity
        test_values_case = {"PRICE_VELOCITY": 0.01}  # Uppercase
        result_case = strategy.evaluate_signal_detection(test_values_case)
        details.append(f"Case sensitivity test (uppercase): {result_case.value}")

        if result == ConditionResult.TRUE:
            report.add_section("Strategy Evaluation", "OK", details)
        else:
            report.add_section("Strategy Evaluation", "FAIL", details)

    except Exception as e:
        report.add_section("Strategy Evaluation", "FAIL", [str(e)])


def test_event_flow(report: DiagnosticReport):
    """Test expected event flow for signal generation"""
    expected_flow = [
        "1. market.price_update → StreamingIndicatorEngine",
        "2. StreamingIndicatorEngine calculates indicator values",
        "3. indicator.updated → StrategyManager._on_indicator_update()",
        "4. StrategyManager stores indicator value under indicator_type key",
        "5. StrategyManager evaluates active strategies",
        "6. Condition.evaluate() compares condition_type with stored values",
        "7. If TRUE: signal_generated → OrderManager"
    ]

    issues = [
        "Issue: indicator.updated publishes 'indicator_type' (e.g., 'price_velocity')",
        "Issue: StrategyManager stores under 'indicator_type' key",
        "Issue: Condition uses 'condition_type' which MUST match 'indicator_type'",
        "",
        "Current mismatch examples:",
        "  - Strategy uses: pump_magnitude_pct",
        "  - Indicator publishes: PUMP_MAGNITUDE_PCT (uppercase)",
        "  - StrategyManager stores: pump_magnitude_pct (lowercase indicator_type)",
        "",
        "FIX APPLIED (line 1399-1403 in strategy_manager.py):",
        "  storage_key = indicator_type if indicator_type else indicator_name.lower()",
        "  self.indicator_values[symbol][storage_key] = value"
    ]

    report.add_section("Event Flow Analysis", "INFO", expected_flow + [""] + issues)


def generate_recommendations(report: DiagnosticReport, mismatches: List[str]):
    """Generate recommendations based on problems found"""

    if mismatches:
        report.add_recommendation(
            "Create a mapping layer that normalizes indicator_type to condition_type "
            "(e.g., lowercase conversion is already applied)"
        )

    report.add_recommendation(
        "Add unit tests that verify indicator_type matches expected condition_type in strategies"
    )

    report.add_recommendation(
        "Document the required indicator types for each strategy section (S1, O1, Z1, ZE1, E1)"
    )

    report.add_recommendation(
        "Add validation in Strategy Builder UI that shows available indicators"
    )

    report.add_recommendation(
        "Run this diagnostic script after any changes to indicators or strategies"
    )


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main diagnostic entry point"""
    # Get session ID from args or use latest
    session_id = sys.argv[1] if len(sys.argv) > 1 else None

    report = DiagnosticReport()

    print("\n" + "=" * 80)
    print("STRATEGY BUILDER DIAGNOSTIC")
    print("=" * 80)

    # 1. Test QuestDB connection
    print("\n[1/6] Testing QuestDB connection...")
    db_ok = await test_questdb_connection(report)

    if not db_ok:
        report.print_report()
        return 1

    provider = QuestDBProvider()

    # Find latest session if not specified
    if not session_id:
        try:
            await provider.initialize()
            query = """
            SELECT session_id
            FROM data_collection_sessions
            WHERE (is_deleted = false OR is_deleted IS NULL)
            AND session_id LIKE 'pump_test_%'
            ORDER BY created_at DESC
            LIMIT 1
            """
            result = await provider.execute_query(query)
            if result:
                session_id = result[0]['session_id']
                print(f"    Using latest session: {session_id}")
            else:
                print("    No pump_test sessions found, using default symbol")
                session_id = "pump_test_default"
        except Exception as e:
            print(f"    Could not find session: {e}")
            session_id = "pump_test_default"

    symbol = "PUMP_TEST_USDT"

    # 2. Test data availability
    print("\n[2/6] Testing test data availability...")
    data_ok, tick_count = await test_test_data_availability(provider, session_id, report)

    # 3. Test indicator types
    print("\n[3/6] Testing indicator types...")
    available_indicators = test_indicator_types(report)

    # 4. Test condition mapping
    print("\n[4/6] Testing condition-to-indicator mapping...")
    mismatches = test_strategy_condition_mapping(report, available_indicators)

    # 5. Test indicator calculation
    if data_ok:
        print("\n[5/6] Testing indicator calculation...")
        await test_indicator_calculation(provider, session_id, symbol, report)
    else:
        print("\n[5/6] Skipping indicator calculation (no test data)...")
        report.add_section("Indicator Calculation", "SKIP", ["No test data available"])

    # 6. Test strategy evaluation
    print("\n[6/6] Testing strategy evaluation...")
    await test_strategy_evaluation(report)

    # Analyze event flow
    test_event_flow(report)

    # Generate recommendations
    generate_recommendations(report, mismatches)

    # Print report
    report.print_report()

    # Cleanup
    await provider.close()

    return 0 if len(report.problems) == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
