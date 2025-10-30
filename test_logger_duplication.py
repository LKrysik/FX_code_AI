"""
Test script to verify logger handler duplication issue.

This simulates what happens in indicators_routes.py when get_logger(__name__)
is called multiple times in the same module.
"""

import logging
import sys
import tempfile
from pathlib import Path

# Simulate StructuredLogger behavior
class SimulatedStructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        # PROBLEM: Always adds handlers without checking if they exist
        # This is what StructuredLogger does in __init__

        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        self.logger.addHandler(console_handler)

        # Add file handler
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log')
        file_handler = logging.FileHandler(temp_file.name)
        file_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)

        print(f"Created logger '{name}' with {len(self.logger.handlers)} handlers (total: {len(self.logger.handlers)})")

    def info(self, message: str):
        self.logger.info(message)

# Simulate get_logger() function
def simulated_get_logger(name: str):
    """This simulates what get_logger() does - creates new StructuredLogger every time"""
    return SimulatedStructuredLogger(name)

# Test scenario: Simulate indicators_routes.py behavior
print("=" * 80)
print("TEST: Simulating indicators_routes.py calling get_logger(__name__) multiple times")
print("=" * 80)

# First call (e.g., line 846 in indicators_routes.py)
logger1 = simulated_get_logger("indicators_routes")
print(f"After 1st call: logger has {len(logger1.logger.handlers)} handlers")

# Second call (e.g., line 886 in indicators_routes.py)
logger2 = simulated_get_logger("indicators_routes")
print(f"After 2nd call: logger has {len(logger2.logger.handlers)} handlers")

# Third call (e.g., line 899 in indicators_routes.py)
logger3 = simulated_get_logger("indicators_routes")
print(f"After 3rd call: logger has {len(logger3.logger.handlers)} handlers")

# Fourth call (e.g., line 928 in indicators_routes.py)
logger4 = simulated_get_logger("indicators_routes")
print(f"After 4th call: logger has {len(logger4.logger.handlers)} handlers")

# Fifth call (e.g., line 937 in indicators_routes.py)
logger5 = simulated_get_logger("indicators_routes")
print(f"After 5th call: logger has {len(logger5.logger.handlers)} handlers")

print("\n" + "=" * 80)
print("Verify they all reference the same underlying logger:")
print(f"logger1.logger is logger2.logger: {logger1.logger is logger2.logger}")
print(f"logger2.logger is logger3.logger: {logger2.logger is logger3.logger}")
print("=" * 80)

print("\n" + "=" * 80)
print("TEST: What happens when we log a message after 5 calls?")
print("=" * 80)
print("Expected: Message appears 10 times (5 calls * 2 handlers each)")
print("Actual output:\n")
logger5.info("Test message after 5 get_logger() calls")

print("\n" + "=" * 80)
print("CONCLUSION:")
print(f"Total handlers on logger: {len(logger5.logger.handlers)}")
print(f"Each log message will be written {len(logger5.logger.handlers)} times!")
print("=" * 80)

# Additional test: Simulate multiple endpoint calls
print("\n" + "=" * 80)
print("TEST: Simulating what happens when endpoint is called 3 times")
print("=" * 80)

# Clear the logger to start fresh
test_logger = logging.getLogger("test_endpoint")
test_logger.handlers.clear()
test_logger.setLevel(logging.INFO)
test_logger.propagate = False

def simulate_endpoint_call(call_number: int):
    """Simulate a single endpoint call that creates loggers multiple times"""
    print(f"\nEndpoint call #{call_number}:")

    # Simulate 5 get_logger() calls within endpoint (like in add_indicator_for_session)
    for i in range(5):
        # Each call adds 2 handlers (console + file)
        console_handler = logging.StreamHandler(sys.stdout)
        file_handler = logging.FileHandler(tempfile.NamedTemporaryFile(delete=False, suffix='.log').name)
        test_logger.addHandler(console_handler)
        test_logger.addHandler(file_handler)

    print(f"  After endpoint call #{call_number}: {len(test_logger.handlers)} total handlers")
    return len(test_logger.handlers)

# Simulate 3 endpoint calls
for call in range(1, 4):
    handler_count = simulate_endpoint_call(call)

print(f"\n" + "=" * 80)
print(f"After 3 endpoint calls with 5 get_logger() each:")
print(f"Total handlers: {len(test_logger.handlers)}")
print(f"Expected duplicates per log: {len(test_logger.handlers)}")
print("=" * 80)

print("\nFinal test - logging a message:")
test_logger.info("This message will be duplicated many times")
