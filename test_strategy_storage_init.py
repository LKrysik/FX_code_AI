"""Test strategy storage initialization to reproduce the empty error"""
import asyncio
import traceback
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.domain.services.strategy_storage_questdb import QuestDBStrategyStorage

async def test_initialization():
    """Reproduce the initialization error"""
    print("Creating QuestDBStrategyStorage instance...")
    storage = QuestDBStrategyStorage(
        host="127.0.0.1",
        port=8812,
        user="admin",
        password="quest",
        database="qdb"
    )

    try:
        print("Calling initialize()...")
        await storage.initialize()
        print("[OK] Initialization successful!")

        # Test basic operation
        print("Testing list_strategies()...")
        strategies = await storage.list_strategies()
        print(f"[OK] Found {len(strategies)} strategies")

        await storage.close()
        print("[OK] Closed successfully")
        return True

    except Exception as e:
        print(f"[FAIL] Initialization failed")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: '{str(e)}'")
        print(f"   Error message length: {len(str(e))}")
        print(f"   Error repr: {repr(e)}")
        print(f"   Error is empty string: {str(e) == ''}")
        print(f"\n   Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_initialization())
    exit(0 if result else 1)
