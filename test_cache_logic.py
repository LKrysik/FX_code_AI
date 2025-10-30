"""
Simplified test for logger cache logic (Step 1).

Tests the cache mechanism without full application setup.
"""

import threading
from typing import Dict

# Simulate the cache logic from logger.py
_test_cache: Dict[str, object] = {}
_test_lock = threading.RLock()

def simulated_get_logger(name: str):
    """Simulated get_logger with cache logic"""
    # Fast path: check cache without lock
    if name in _test_cache:
        return _test_cache[name]

    # Slow path: acquire lock and create
    with _test_lock:
        # Double-check locking
        if name in _test_cache:
            return _test_cache[name]

        # Create new object (simulating StructuredLogger)
        logger_obj = {"name": name, "id": id(object())}
        _test_cache[name] = logger_obj
        return logger_obj

print("=" * 80)
print("TEST: Logger Cache Logic Verification")
print("=" * 80)

# Test 1: Same name returns same instance
logger1 = simulated_get_logger("test")
logger2 = simulated_get_logger("test")
logger3 = simulated_get_logger("test")

print(f"✓ logger1 created: id={id(logger1)}")
print(f"✓ logger2 retrieved: id={id(logger2)}")
print(f"✓ logger3 retrieved: id={id(logger3)}")

test1_pass = (logger1 is logger2) and (logger2 is logger3)
print(f"{'✅ PASS' if test1_pass else '❌ FAIL'}: Same name returns same cached instance")

# Test 2: Different names create different instances
logger_a = simulated_get_logger("module_a")
logger_b = simulated_get_logger("module_b")

test2_pass = logger_a is not logger_b
print(f"{'✅ PASS' if test2_pass else '❌ FAIL'}: Different names create different instances")

# Test 3: Cache size verification
print(f"\nCache contains {len(_test_cache)} loggers")
print(f"Cached names: {list(_test_cache.keys())}")

test3_pass = len(_test_cache) == 3  # test, module_a, module_b
print(f"{'✅ PASS' if test3_pass else '❌ FAIL'}: Cache size correct (expected 3, got {len(_test_cache)})")

# Test 4: Thread safety (concurrent access)
import time

results = []
errors = []

def concurrent_get_logger(thread_id):
    try:
        for i in range(100):
            logger = simulated_get_logger("concurrent_test")
            results.append((thread_id, id(logger)))
    except Exception as e:
        errors.append((thread_id, str(e)))

threads = []
for i in range(10):
    t = threading.Thread(target=concurrent_get_logger, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

unique_ids = set(id_val for _, id_val in results)
test4_pass = len(unique_ids) == 1 and len(errors) == 0

print(f"{'✅ PASS' if test4_pass else '❌ FAIL'}: Thread-safe cache (10 threads, {len(results)} accesses, {len(unique_ids)} unique instance)")
if errors:
    print(f"  Errors: {errors[:5]}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
if test1_pass and test2_pass and test3_pass and test4_pass:
    print("✅ ALL TESTS PASSED - Cache logic is correct!")
else:
    print("❌ SOME TESTS FAILED - Review implementation")
print("=" * 80)
