#!/usr/bin/env python3
"""
Sprint 1 Final Validation Report
================================

Comprehensive validation of all Sprint 1 deliverables and go/no-go decision.
"""

import asyncio
import time
import sys
import os
from typing import Dict, Any
from dataclasses import dataclass

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.event_bus import EventBus
from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine


@dataclass
class ValidationResult:
    """Result of a validation check."""
    name: str
    success: bool
    details: str
    metrics: Dict[str, Any] = None


class Sprint1Validator:
    """Comprehensive validator for Sprint 1 deliverables."""

    def __init__(self):
        self.results = []

    async def validate_eventbus_race_conditions(self) -> ValidationResult:
        """Validate EventBus race condition fixes."""
        try:
            # Import the race condition test
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tests'))
            from test_eventbus_race_conditions import (
                test_eventbus_concurrent_subscribe_publish,
                test_eventbus_cleanup_during_publish,
                test_eventbus_high_frequency_burst
            )

            # Run race condition tests
            await test_eventbus_concurrent_subscribe_publish()
            await test_eventbus_cleanup_during_publish()
            await test_eventbus_high_frequency_burst()

            return ValidationResult(
                name="EventBus Race Conditions",
                success=True,
                details="All race condition tests passed - no crashes or deadlocks detected",
                metrics={"tests_passed": 3, "tests_total": 3}
            )

        except Exception as e:
            return ValidationResult(
                name="EventBus Race Conditions",
                success=False,
                details=f"Race condition tests failed: {e}",
                metrics={"error": str(e)}
            )

    async def validate_eventbus_performance(self) -> ValidationResult:
        """Validate EventBus performance under load."""
        try:
            # Import benchmark
            from benchmark_eventbus_performance import EventBusBenchmark

            benchmark = EventBusBenchmark(target_rate=100, test_duration=10)  # Shorter test
            results = await benchmark.run_benchmark()

            success = results["success"]
            details = f"Achieved {results['actual_rate']:.1f} msg/s, {results['errors']} errors, {results['avg_latency_ms']:.1f}ms latency"

            return ValidationResult(
                name="EventBus Performance",
                success=success,
                details=details,
                metrics={
                    "target_rate": results["target_rate"],
                    "actual_rate": results["actual_rate"],
                    "errors": results["errors"],
                    "avg_latency_ms": results["avg_latency_ms"]
                }
            )

        except Exception as e:
            return ValidationResult(
                name="EventBus Performance",
                success=False,
                details=f"Performance benchmark failed: {e}",
                metrics={"error": str(e)}
            )

    async def validate_streaming_indicator_engine(self) -> ValidationResult:
        """Validate StreamingIndicatorEngine functionality."""
        try:
            # Import tests
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tests'))
            from test_streaming_indicator_engine import (
                test_streaming_indicator_engine_basic,
                test_streaming_indicator_engine_integration,
                test_market_data_handling,
                test_multiple_indicators,
                test_indicator_error_handling
            )

            # Run all tests
            await test_streaming_indicator_engine_basic()
            await test_streaming_indicator_engine_integration()
            await test_market_data_handling()
            await test_multiple_indicators()
            await test_indicator_error_handling()

            return ValidationResult(
                name="StreamingIndicatorEngine",
                success=True,
                details="All StreamingIndicatorEngine tests passed",
                metrics={"tests_passed": 5, "tests_total": 5}
            )

        except Exception as e:
            return ValidationResult(
                name="StreamingIndicatorEngine",
                success=False,
                details=f"StreamingIndicatorEngine tests failed: {e}",
                metrics={"error": str(e)}
            )

    async def validate_vwap_calculation(self) -> ValidationResult:
        """Validate VWAP calculation accuracy."""
        try:
            # Import VWAP tests
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tests'))
            from test_streaming_indicator_engine import (
                test_vwap_calculation,
                test_vwap_indicator_registration,
                test_vwap_empty_data,
                test_vwap_time_window
            )

            # Run VWAP tests
            await test_vwap_calculation()
            await test_vwap_indicator_registration()
            await test_vwap_empty_data()
            await test_vwap_time_window()

            return ValidationResult(
                name="VWAP Calculation",
                success=True,
                details="VWAP calculation tests passed - accurate volume-weighted averages",
                metrics={"tests_passed": 4, "tests_total": 4}
            )

        except Exception as e:
            return ValidationResult(
                name="VWAP Calculation",
                success=False,
                details=f"VWAP calculation tests failed: {e}",
                metrics={"error": str(e)}
            )

    async def validate_full_integration(self) -> ValidationResult:
        """Validate full system integration."""
        try:
            # Import integration tests
            from test_full_integration import (
                test_full_system_integration,
                test_error_handling_integration,
                test_concurrent_load_integration
            )

            # Run integration tests
            await test_full_system_integration()
            await test_error_handling_integration()
            await test_concurrent_load_integration()

            return ValidationResult(
                name="Full System Integration",
                success=True,
                details="EventBus + StreamingIndicatorEngine + VWAP integration successful",
                metrics={"tests_passed": 3, "tests_total": 3}
            )

        except Exception as e:
            return ValidationResult(
                name="Full System Integration",
                success=False,
                details=f"Integration tests failed: {e}",
                metrics={"error": str(e)}
            )

    async def validate_business_value(self) -> ValidationResult:
        """Validate business value - does VWAP provide trading edge?"""
        try:
            # Import signal validation
            from validate_vwap_signals import main as validate_signals

            # Run signal validation
            success = await validate_signals()

            if success:
                details = "VWAP signals show statistically significant edge"
            else:
                details = "VWAP signals do not show reliable edge in test data"

            return ValidationResult(
                name="Business Value Validation",
                success=success,
                details=details,
                metrics={"has_edge": success}
            )

        except Exception as e:
            return ValidationResult(
                name="Business Value Validation",
                success=False,
                details=f"Business validation failed: {e}",
                metrics={"error": str(e)}
            )

    async def run_all_validations(self) -> Dict[str, Any]:
        """Run all Sprint 1 validations."""
        print(" Running Sprint 1 Final Validation...")

        validations = [
            self.validate_eventbus_race_conditions(),
            self.validate_eventbus_performance(),
            self.validate_streaming_indicator_engine(),
            self.validate_vwap_calculation(),
            self.validate_full_integration(),
            self.validate_business_value()
        ]

        results = []
        for validation in validations:
            result = await validation
            results.append(result)
            status = "" if result.success else ""
            print(f"{status} {result.name}: {result.details}")

        # Calculate overall success
        successful_validations = sum(1 for r in results if r.success)
        total_validations = len(results)

        # Core technical requirements (must pass)
        core_technical = [
            r for r in results
            if r.name in ["EventBus Race Conditions", "EventBus Performance",
                         "StreamingIndicatorEngine", "VWAP Calculation", "Full System Integration"]
        ]
        core_success = all(r.success for r in core_technical)

        # Business value (nice to have)
        business_result = next((r for r in results if r.name == "Business Value Validation"), None)
        business_success = business_result.success if business_result else False

        # Overall assessment
        sprint_success = core_success  # Technical success is mandatory
        go_decision = "GO" if sprint_success else "NO-GO"

        return {
            "sprint_success": sprint_success,
            "go_decision": go_decision,
            "core_technical_success": core_success,
            "business_value_success": business_success,
            "successful_validations": successful_validations,
            "total_validations": total_validations,
            "validation_results": [
                {
                    "name": r.name,
                    "success": r.success,
                    "details": r.details,
                    "metrics": r.metrics
                }
                for r in results
            ],
            "generated_at": int(time.time() * 1000)
        }


async def main():
    """Generate Sprint 1 final validation report."""
    validator = Sprint1Validator()
    report = await validator.run_all_validations()

    # Print comprehensive report
    print("\n" + "="*80)
    print("SPRINT 1 FINAL VALIDATION REPORT")
    print("="*80)

    print(f"Sprint Success: {' YES' if report['sprint_success'] else ' NO'}")
    print(f"Go Decision: {report['go_decision']}")
    print(f"Core Technical: {' PASSED' if report['core_technical_success'] else ' FAILED'}")
    print(f"Business Value: {' EDGE FOUND' if report['business_value_success'] else ' NO EDGE'}")
    print(f"Validations Passed: {report['successful_validations']}/{report['total_validations']}")

    print("\nDetailed Results:")
    for result in report["validation_results"]:
        status = "" if result["success"] else ""
        print(f"  {status} {result['name']}: {result['details']}")

    print("\n" + "="*80)

    if report["sprint_success"]:
        print(" SPRINT 1 SUCCESSFUL!")
        print(" All core technical requirements met")
        print(" System is production-ready")
        if report["business_value_success"]:
            print(" VWAP shows trading edge - proceed to strategy development")
        else:
            print(" VWAP does not show edge in test data - consider alternative indicators")
        print("\nNext Steps:")
        print("  • Sprint 2: Build strategy using validated indicators")
        print("  • Sprint 3: Add resilience and monitoring")
        print("  • Sprint 4: Expand to additional indicators and markets")
    else:
        print(" SPRINT 1 ISSUES DETECTED")
        print(" Core technical requirements not met")
        print("\nAction Required:")
        print("  • Fix failing validations")
        print("  • Re-test critical components")
        print("  • Address race conditions and performance issues")

    print("="*80)

    return report["sprint_success"]


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)