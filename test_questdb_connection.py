import asyncio
import asyncpg
import traceback
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

async def test_connection():
    """Test QuestDB connection with detailed error reporting"""
    try:
        print("Attempting to connect to QuestDB...")
        conn = await asyncpg.connect(
            host='127.0.0.1',
            port=8812,
            user='admin',
            password='quest',
            database='qdb',
            timeout=5
        )
        print("[OK] Connection successful!")

        # Test query
        version = await conn.fetchval("SELECT version()")
        print(f"[OK] QuestDB version: {version}")

        # Check if strategies table exists
        table_exists = await conn.fetchval(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'strategies'"
        )
        print(f"[OK] Strategies table exists: {table_exists > 0}")

        await conn.close()
        print("[OK] Connection closed cleanly")
        return True

    except asyncpg.InvalidCatalogNameError as e:
        print(f"[FAIL] Database 'qdb' not found: {e}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error details: {str(e)}")
        traceback.print_exc()
        return False

    except asyncpg.InvalidPasswordError as e:
        print(f"[FAIL] Authentication failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        traceback.print_exc()
        return False

    except asyncpg.CannotConnectNowError as e:
        print(f"[FAIL] Cannot connect now: {e}")
        print(f"   Error type: {type(e).__name__}")
        traceback.print_exc()
        return False

    except ConnectionRefusedError as e:
        print(f"[FAIL] Connection refused (QuestDB not running?): {e}")
        print(f"   Error type: {type(e).__name__}")
        traceback.print_exc()
        return False

    except TimeoutError as e:
        print(f"[FAIL] Connection timeout: {e}")
        print(f"   Error type: {type(e).__name__}")
        traceback.print_exc()
        return False

    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error string: '{str(e)}'")
        print(f"   Error repr: {repr(e)}")
        print(f"   Error string length: {len(str(e))}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    exit(0 if result else 1)
