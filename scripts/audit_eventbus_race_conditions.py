#!/usr/bin/env python3
"""
EventBus Race Condition Analysis Script
========================================

Analyzes the EventBus code for potential race conditions and concurrent access issues.
Part of Sprint 1: System audit and race condition analysis.
"""

import ast
import inspect
from typing import Dict, List, Set, Tuple
import re


class EventBusRaceConditionAnalyzer:
    """
    Analyzes EventBus code for potential race conditions in async operations.
    """

    def __init__(self, eventbus_file: str = "src/core/event_bus.py"):
        self.eventbus_file = eventbus_file
        self.shared_state_vars: Set[str] = set()
        self.locked_operations: Dict[str, List[str]] = {}
        self.potential_race_conditions: List[Dict] = []

    def analyze(self) -> Dict:
        """Perform complete race condition analysis."""
        print("Starting EventBus Race Condition Analysis...")

        # Read and parse the EventBus code
        with open(self.eventbus_file, 'r', encoding='utf-8') as f:
            source_code = f.read()

        tree = ast.parse(source_code)

        # Identify shared state variables
        self._identify_shared_state(tree)

        # Analyze async methods for concurrent access patterns
        self._analyze_async_methods(tree)

        # Check for proper locking patterns
        self._check_locking_patterns(tree)

        # Generate analysis report
        report = self._generate_report()

        print(f"Analysis complete. Found {len(self.potential_race_conditions)} potential race conditions.")
        return report

    def _identify_shared_state(self, tree: ast.AST):
        """Identify variables that represent shared state."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "EventBus":
                # Look for instance variables in __init__
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        for stmt in item.body:
                            if isinstance(stmt, ast.Assign):
                                for target in stmt.targets:
                                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                                        var_name = target.attr
                                        # Check if it's a shared data structure
                                        if any(keyword in var_name.lower() for keyword in ['queue', 'subscriber', 'metric', 'rate', 'circuit']):
                                            self.shared_state_vars.add(var_name)
                                            print(f"Identified shared state variable: {var_name}")

    def _analyze_async_methods(self, tree: ast.AST):
        """Analyze async methods for concurrent access to shared state."""
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                method_name = node.name
                accesses = self._find_shared_state_accesses(node)

                if accesses:
                    print(f"Analyzing async method: {method_name}")
                    print(f"   Shared state accesses: {list(accesses.keys())}")

                    # Check for potential race conditions
                    self._check_method_race_conditions(method_name, accesses, node)

    def _find_shared_state_accesses(self, node: ast.AST) -> Dict[str, List[str]]:
        """Find accesses to shared state variables in a method."""
        accesses = {}

        for child in ast.walk(node):
            if isinstance(child, ast.Attribute):
                if (isinstance(child.value, ast.Name) and
                    child.value.id == "self" and
                    child.attr in self.shared_state_vars):
                    var_name = child.attr
                    if var_name not in accesses:
                        accesses[var_name] = []
                    accesses[var_name].append("access")

            # Check for modifications (assignments)
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Attribute):
                        if (isinstance(target.value, ast.Name) and
                            target.value.id == "self" and
                            target.attr in self.shared_state_vars):
                            var_name = target.attr
                            if var_name not in accesses:
                                accesses[var_name] = []
                            accesses[var_name].append("modify")

        return accesses

    def _check_method_race_conditions(self, method_name: str, accesses: Dict[str, List[str]], node: ast.AST):
        """Check a method for potential race conditions."""
        # Look for locking patterns
        has_locking = self._method_uses_locking(node)

        for var_name, operations in accesses.items():
            if "modify" in operations and not has_locking:
                race_condition = {
                    "method": method_name,
                    "variable": var_name,
                    "operations": operations,
                    "has_locking": has_locking,
                    "severity": "HIGH" if len(operations) > 1 else "MEDIUM",
                    "description": f"Method {method_name} modifies shared state {var_name} without proper locking"
                }
                self.potential_race_conditions.append(race_condition)
                print(f"POTENTIAL RACE CONDITION: {race_condition['description']}")

    def _method_uses_locking(self, node: ast.AST) -> bool:
        """Check if a method uses proper locking."""
        for child in ast.walk(node):
            # Look for async context managers (likely locks)
            if isinstance(child, ast.AsyncWith):
                return True

            # Look for lock acquire/release patterns
            if isinstance(child, ast.Attribute):
                if child.attr in ["acquire", "release", "__aenter__", "__aexit__"]:
                    return True

        return False

    def _check_locking_patterns(self, tree: ast.AST):
        """Check for consistent locking patterns across the codebase."""
        # This would analyze lock ordering and consistency
        # For now, just check that locks are used
        pass

    def _generate_report(self) -> Dict:
        """Generate comprehensive analysis report."""
        return {
            "shared_state_variables": list(self.shared_state_vars),
            "potential_race_conditions": self.potential_race_conditions,
            "total_race_conditions": len(self.potential_race_conditions),
            "severity_breakdown": {
                "HIGH": len([rc for rc in self.potential_race_conditions if rc["severity"] == "HIGH"]),
                "MEDIUM": len([rc for rc in self.potential_race_conditions if rc["severity"] == "MEDIUM"]),
                "LOW": len([rc for rc in self.potential_race_conditions if rc["severity"] == "LOW"])
            },
            "recommendations": self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        if self.potential_race_conditions:
            recommendations.append("Implement proper locking for shared state modifications")
            recommendations.append("Use consistent lock ordering to prevent deadlocks")
            recommendations.append("Consider atomic operations for simple state updates")

        if len(self.shared_state_vars) > 5:
            recommendations.append("Review if all identified variables truly need to be shared state")

        return recommendations


def main():
    """Main analysis function."""
    analyzer = EventBusRaceConditionAnalyzer()
    report = analyzer.analyze()

    print("\n" + "="*60)
    print("EVENTBUS RACE CONDITION ANALYSIS REPORT")
    print("="*60)

    print(f"Shared State Variables: {len(report['shared_state_variables'])}")
    for var in report['shared_state_variables']:
        print(f"  • {var}")

    print(f"\nPotential Race Conditions: {report['total_race_conditions']}")
    print(f"Severity Breakdown: {report['severity_breakdown']}")

    if report['potential_race_conditions']:
        print("\nDetailed Race Conditions:")
        for i, rc in enumerate(report['potential_race_conditions'], 1):
            print(f"{i}. {rc['description']} (Severity: {rc['severity']})")

    print("\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  • {rec}")

    print("\n" + "="*60)

    # Return analysis results for testing
    return report


if __name__ == "__main__":
    report = main()

    # For testing purposes
    if report['total_race_conditions'] > 0:
        print("❌ Race conditions detected - requires fixes")
        exit(1)
    else:
        print("No race conditions detected")
        exit(0)