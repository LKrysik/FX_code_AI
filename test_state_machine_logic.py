#!/usr/bin/env python3
"""
Test State Machine Logic (Unit Test)
Tests _get_allowed_transitions() function without starting server.
"""

from src.application.controllers.execution_controller import ExecutionState
from src.api.state_machine_routes import _get_allowed_transitions


def test_allowed_transitions():
    """Test allowed transitions for all states"""
    print("=== Testing _get_allowed_transitions() ===\n")

    test_cases = [
        (ExecutionState.IDLE, ["STARTING"]),
        (ExecutionState.STARTING, ["RUNNING", "ERROR"]),
        (ExecutionState.RUNNING, ["PAUSED", "STOPPING", "ERROR"]),
        (ExecutionState.PAUSED, ["RUNNING", "STOPPING"]),
        (ExecutionState.STOPPING, ["STOPPED", "ERROR", "STARTING"]),
        (ExecutionState.STOPPED, ["STARTING"]),
        (ExecutionState.ERROR, ["STARTING", "STOPPED"])
    ]

    all_passed = True

    for state, expected in test_cases:
        result = _get_allowed_transitions(state)
        # Convert to uppercase for comparison
        expected_upper = [s.upper() for s in expected]
        result_upper = [s.upper() for s in result]

        if set(result_upper) == set(expected_upper):
            print(f"[PASS] {state.value:12} -> {', '.join(result_upper)}")
        else:
            print(f"[FAIL] {state.value:12} -> Expected: {expected_upper}, Got: {result_upper}")
            all_passed = False

    print()
    if all_passed:
        print("[SUCCESS] All tests passed!")
        return 0
    else:
        print("[FAILED] Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(test_allowed_transitions())
