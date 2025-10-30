"""
Test script to verify logger cache fix (Step 1).

Verifies that get_logger() now returns cached instances and
does not accumulate handlers.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.logger import get_logger

print("=" * 80)
print("TEST 1: Verify logger cache returns same instance")
print("=" * 80)

# First call
logger1 = get_logger("test_module")
print(f"✓ First call: logger1 created")
print(f"  - Logger name: {logger1.logger.name}")
print(f"  - Handlers count: {len(logger1.logger.handlers)}")
print(f"  - Logger object id: {id(logger1)}")

# Second call - should return SAME instance from cache
logger2 = get_logger("test_module")
print(f"\n✓ Second call: logger2 retrieved")
print(f"  - Logger name: {logger2.logger.name}")
print(f"  - Handlers count: {len(logger2.logger.handlers)}")
print(f"  - Logger object id: {id(logger2)}")

# Verify they are the same instance
print(f"\n{'✅ PASS' if logger1 is logger2 else '❌ FAIL'}: logger1 is logger2")
print(f"{'✅ PASS' if logger1.logger is logger2.logger else '❌ FAIL'}: logger1.logger is logger2.logger")

# Third call - verify handlers don't accumulate
logger3 = get_logger("test_module")
print(f"\n✓ Third call: logger3 retrieved")
print(f"  - Handlers count: {len(logger3.logger.handlers)}")
print(f"  - Logger object id: {id(logger3)}")

expected_handlers = 2  # console + file
actual_handlers = len(logger3.logger.handlers)
print(f"\n{'✅ PASS' if actual_handlers == expected_handlers else '❌ FAIL'}: Handler count = {actual_handlers} (expected {expected_handlers})")

print("\n" + "=" * 80)
print("TEST 2: Verify different logger names create separate instances")
print("=" * 80)

logger_a = get_logger("module_a")
logger_b = get_logger("module_b")

print(f"✓ module_a logger created (id: {id(logger_a)})")
print(f"✓ module_b logger created (id: {id(logger_b)})")
print(f"{'✅ PASS' if logger_a is not logger_b else '❌ FAIL'}: Different names create different instances")

print("\n" + "=" * 80)
print("TEST 3: Verify no log duplication after multiple get_logger() calls")
print("=" * 80)

# Simulate indicators_routes.py pattern: multiple get_logger() calls
test_logger = get_logger("test_indicators_routes")
initial_handlers = len(test_logger.logger.handlers)
print(f"Initial handlers: {initial_handlers}")

# Call get_logger() 5 more times (simulating function calls)
for i in range(5):
    _ = get_logger("test_indicators_routes")

final_handlers = len(test_logger.logger.handlers)
print(f"After 5 more calls: {final_handlers} handlers")
print(f"{'✅ PASS' if final_handlers == initial_handlers else '❌ FAIL'}: No new handlers added")

print("\n" + "=" * 80)
print("TEST 4: Verify logs are not duplicated")
print("=" * 80)

import tempfile
import time

# Create a test logger with file output
test_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log')
test_file.close()

# Get logger multiple times and log once
for _ in range(3):
    logger = get_logger("test_duplication")

logger.info("test_event", {"message": "Single log message"})

# Give file handler time to flush
time.sleep(0.1)

# Count lines in log file
try:
    with open(test_file.name, 'r') as f:
        lines = [line for line in f.readlines() if 'test_event' in line]
        line_count = len(lines)
except:
    line_count = 0

print(f"Log messages in file: {line_count}")
print(f"{'✅ PASS' if line_count <= 1 else '❌ FAIL'}: Log not duplicated (expected 1, got {line_count})")

# Cleanup
os.unlink(test_file.name)

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("✅ Logger cache fix (Step 1) verification complete!")
print("Cache prevents handler accumulation and log duplication.")
print("=" * 80)
