"""Test indicator_variants table"""
import asyncio
import asyncpg
import json
from datetime import datetime


async def test_table():
    conn = await asyncpg.connect(
        host='localhost', port=8812, user='admin', password='quest', database='qdb'
    )

    try:
        print("Testing indicator_variants table...")

        # Test INSERT
        print("\n1. Testing INSERT...")
        await conn.execute("""
            INSERT INTO indicator_variants (
                id, name, base_indicator_type, variant_type, description,
                parameters, schema_version, is_system, created_by, user_id, scope,
                created_at, updated_at, is_deleted
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """,
            'test-variant-001',
            'TWPA 5 minutes TEST',
            'TWPA',
            'general',
            'Test variant for migration verification',
            json.dumps({"t1": 300.0, "t2": 0.0, "refresh_interval_seconds": 1.0}),
            1,
            False,
            'system',
            'admin',
            'global',
            datetime.utcnow(),
            datetime.utcnow(),
            False
        )
        print("[OK] INSERT successful")

        # Test SELECT by ID
        print("\n2. Testing SELECT by ID...")
        row = await conn.fetchrow("""
            SELECT * FROM indicator_variants WHERE id = $1 AND is_deleted = false
        """, 'test-variant-001')

        if row:
            print(f"[OK] Found variant: {row['name']}")
            print(f"     Parameters: {row['parameters']}")
        else:
            print("[ERROR] Variant not found!")
            return False

        # Test SELECT by base_indicator_type (SYMBOL column - optimized)
        print("\n3. Testing SELECT by base_indicator_type (SYMBOL)...")
        rows = await conn.fetch("""
            SELECT id, name, base_indicator_type FROM indicator_variants
            WHERE base_indicator_type = $1 AND is_deleted = false
        """, 'TWPA')
        print(f"[OK] Found {len(rows)} TWPA variant(s)")

        # Test SELECT by variant_type (SYMBOL column - optimized)
        print("\n4. Testing SELECT by variant_type (SYMBOL)...")
        rows = await conn.fetch("""
            SELECT id, name, variant_type FROM indicator_variants
            WHERE variant_type = $1 AND is_deleted = false
        """, 'general')
        print(f"[OK] Found {len(rows)} general variant(s)")

        # Test SELECT by scope
        print("\n5. Testing SELECT by scope...")
        rows = await conn.fetch("""
            SELECT id, name, scope FROM indicator_variants
            WHERE scope = $1 AND is_deleted = false
        """, 'global')
        print(f"[OK] Found {len(rows)} global variant(s)")

        # Test UPDATE
        print("\n6. Testing UPDATE...")
        new_params = json.dumps({"t1": 600.0, "t2": 0.0, "refresh_interval_seconds": 2.0})
        result = await conn.execute("""
            UPDATE indicator_variants
            SET parameters = $1, updated_at = $2
            WHERE id = $3 AND is_deleted = false
        """, new_params, datetime.utcnow(), 'test-variant-001')
        print(f"[OK] UPDATE successful: {result}")

        # Verify update
        row = await conn.fetchrow("""
            SELECT parameters FROM indicator_variants WHERE id = $1
        """, 'test-variant-001')
        updated_params = json.loads(row['parameters'])
        assert updated_params['t1'] == 600.0, "Parameters not updated!"
        print(f"[OK] Verified updated parameters: t1={updated_params['t1']}")

        # Test SOFT DELETE
        print("\n7. Testing SOFT DELETE...")
        result = await conn.execute("""
            UPDATE indicator_variants
            SET is_deleted = true, deleted_at = $1
            WHERE id = $2
        """, datetime.utcnow(), 'test-variant-001')
        print(f"[OK] Soft delete successful: {result}")

        # Verify soft delete (should not be found)
        row = await conn.fetchrow("""
            SELECT * FROM indicator_variants WHERE id = $1 AND is_deleted = false
        """, 'test-variant-001')
        assert row is None, "Soft deleted variant should not be found!"
        print("[OK] Verified soft delete (not found in active variants)")

        # Verify soft deleted variant exists with flag
        row = await conn.fetchrow("""
            SELECT is_deleted, deleted_at FROM indicator_variants WHERE id = $1
        """, 'test-variant-001')
        assert row['is_deleted'] == True, "is_deleted flag not set!"
        print(f"[OK] Soft deleted variant exists with is_deleted=true, deleted_at={row['deleted_at']}")

        # Test UNDELETE (rollback)
        print("\n8. Testing UNDELETE (rollback)...")
        result = await conn.execute("""
            UPDATE indicator_variants
            SET is_deleted = false, deleted_at = NULL
            WHERE id = $1
        """, 'test-variant-001')
        print(f"[OK] Undelete successful: {result}")

        # Verify undelete
        row = await conn.fetchrow("""
            SELECT * FROM indicator_variants WHERE id = $1 AND is_deleted = false
        """, 'test-variant-001')
        assert row is not None, "Undeleted variant should be found!"
        print("[OK] Verified undelete (variant is active again)")

        # Cleanup - physical delete for test
        print("\n9. Cleanup test data...")
        # QuestDB doesn't support DELETE, so we'll leave it soft-deleted
        await conn.execute("""
            UPDATE indicator_variants
            SET is_deleted = true, deleted_at = $1
            WHERE id = $2
        """, datetime.utcnow(), 'test-variant-001')
        print("[OK] Test data marked as deleted")

        print("\n" + "="*60)
        print("[SUCCESS] All tests passed!")
        print("="*60)
        print("\nTable is ready for production use:")
        print("- INSERT: Working")
        print("- SELECT (by ID, SYMBOL columns, scope): Working")
        print("- UPDATE: Working")
        print("- SOFT DELETE: Working")
        print("- UNDELETE: Working")
        print("- SYMBOL columns (base_indicator_type, variant_type): Optimized")

        return True

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(test_table())
    exit(0 if success else 1)
