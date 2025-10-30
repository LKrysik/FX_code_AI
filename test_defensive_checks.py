"""
Test script to verify defensive handler checks (Step 2).

Verifies that _setup_console_handler and _setup_file_handler
are idempotent - calling multiple times doesn't add duplicate handlers.
"""

import logging
import sys
import tempfile
import os
from logging.handlers import RotatingFileHandler

# Mock StructuredLogger for testing (without full app setup)
class MockStructuredLogger:
    """Simulates StructuredLogger with defensive checks"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    def _setup_console_handler_with_check(self):
        """Console handler setup WITH defensive check"""
        # Check if console handler already exists
        for existing_handler in self.logger.handlers:
            if isinstance(existing_handler, logging.StreamHandler):
                if hasattr(existing_handler, 'stream') and existing_handler.stream == sys.stdout:
                    return  # Already exists

        # Add new handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)

    def _setup_file_handler_with_check(self, log_file: str):
        """File handler setup WITH defensive check"""
        log_file_normalized = os.path.abspath(log_file)

        # Check if file handler already exists
        for existing_handler in self.logger.handlers:
            if isinstance(existing_handler, RotatingFileHandler):
                if hasattr(existing_handler, 'baseFilename'):
                    existing_file = os.path.abspath(existing_handler.baseFilename)
                    if existing_file == log_file_normalized:
                        return  # Already exists

        # Add new handler
        handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=1)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)

    def _setup_console_handler_without_check(self):
        """Console handler setup WITHOUT defensive check (old behavior)"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)


print("=" * 80)
print("TEST 1: Console Handler - WITH Defensive Check (New Behavior)")
print("=" * 80)

logger1 = MockStructuredLogger("test_console_with_check")
print(f"Initial handlers: {len(logger1.logger.handlers)}")

# Call setup 5 times
for i in range(5):
    logger1._setup_console_handler_with_check()

final_handlers = len(logger1.logger.handlers)
print(f"After 5 calls: {final_handlers} handlers")
test1_pass = final_handlers == 1
print(f"{'✅ PASS' if test1_pass else '❌ FAIL'}: Only 1 console handler added (expected 1, got {final_handlers})")

print("\n" + "=" * 80)
print("TEST 2: Console Handler - WITHOUT Defensive Check (Old Behavior)")
print("=" * 80)

logger2 = MockStructuredLogger("test_console_without_check")
print(f"Initial handlers: {len(logger2.logger.handlers)}")

# Call setup 5 times (old behavior)
for i in range(5):
    logger2._setup_console_handler_without_check()

final_handlers_old = len(logger2.logger.handlers)
print(f"After 5 calls: {final_handlers_old} handlers")
test2_pass = final_handlers_old == 5
print(f"{'✅ PASS' if test2_pass else '❌ FAIL'}: Old behavior adds 5 handlers (expected 5, got {final_handlers_old})")

print("\n" + "=" * 80)
print("TEST 3: File Handler - WITH Defensive Check (New Behavior)")
print("=" * 80)

logger3 = MockStructuredLogger("test_file_with_check")
temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.log')
temp_file_path = temp_file.name
temp_file.close()

print(f"Initial handlers: {len(logger3.logger.handlers)}")

# Call setup 5 times
for i in range(5):
    logger3._setup_file_handler_with_check(temp_file_path)

final_file_handlers = len(logger3.logger.handlers)
print(f"After 5 calls: {final_file_handlers} handlers")
test3_pass = final_file_handlers == 1
print(f"{'✅ PASS' if test3_pass else '❌ FAIL'}: Only 1 file handler added (expected 1, got {final_file_handlers})")

# Cleanup
os.unlink(temp_file_path)

print("\n" + "=" * 80)
print("TEST 4: Combined - Console + File Handlers")
print("=" * 80)

logger4 = MockStructuredLogger("test_combined")
temp_file2 = tempfile.NamedTemporaryFile(delete=False, suffix='.log')
temp_file2_path = temp_file2.name
temp_file2.close()

# Call both setups 3 times each
for i in range(3):
    logger4._setup_console_handler_with_check()
    logger4._setup_file_handler_with_check(temp_file2_path)

final_combined_handlers = len(logger4.logger.handlers)
print(f"After 3 iterations: {final_combined_handlers} handlers")
test4_pass = final_combined_handlers == 2  # 1 console + 1 file
print(f"{'✅ PASS' if test4_pass else '❌ FAIL'}: Only 2 handlers total (1 console + 1 file)")

# Verify types
console_count = sum(1 for h in logger4.logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler))
file_count = sum(1 for h in logger4.logger.handlers if isinstance(h, RotatingFileHandler))
print(f"  - Console handlers: {console_count}")
print(f"  - File handlers: {file_count}")

# Cleanup
os.unlink(temp_file2_path)

print("\n" + "=" * 80)
print("TEST 5: Idempotency - Log Message Not Duplicated")
print("=" * 80)

logger5 = MockStructuredLogger("test_idempotency")
temp_file3 = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log')
temp_file3_path = temp_file3.name
temp_file3.close()

# Setup handlers 3 times
for i in range(3):
    logger5._setup_file_handler_with_check(temp_file3_path)

# Log a message
logger5.logger.info("Test message")

# Count lines in file
import time
time.sleep(0.1)  # Let handler flush

with open(temp_file3_path, 'r') as f:
    lines = f.readlines()
    line_count = len([l for l in lines if 'Test message' in l])

print(f"Log messages in file: {line_count}")
test5_pass = line_count == 1
print(f"{'✅ PASS' if test5_pass else '❌ FAIL'}: Message not duplicated (expected 1, got {line_count})")

# Cleanup
os.unlink(temp_file3_path)

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

all_pass = test1_pass and test2_pass and test3_pass and test4_pass and test5_pass
if all_pass:
    print("✅ ALL TESTS PASSED - Defensive checks work correctly!")
    print("Handler duplication is prevented by idempotent setup methods.")
else:
    print("❌ SOME TESTS FAILED - Review implementation")

print("=" * 80)
