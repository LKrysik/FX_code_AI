"""
Execute Migration 008 - Create Indicator Variants Table
"""
import asyncio
import asyncpg


async def run_migration():
    """Execute migration 008 via PostgreSQL wire protocol"""

    # Connect to QuestDB via PostgreSQL protocol
    conn = await asyncpg.connect(
        host='localhost',
        port=8812,
        user='admin',
        password='quest',
        database='qdb'
    )

    try:
        print("Connected to QuestDB")

        # Create table
        print("Creating indicator_variants table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS indicator_variants (
                id STRING,
                name STRING,
                base_indicator_type SYMBOL capacity 128 CACHE,
                variant_type SYMBOL capacity 16 CACHE,
                description STRING,
                parameters STRING,
                schema_version INT,
                is_system BOOLEAN,
                created_by STRING,
                user_id STRING,
                scope STRING,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                deleted_at TIMESTAMP,
                is_deleted BOOLEAN
            )
        """)
        print("[OK] Table created successfully")

        # Create indexes
        print("\nCreating indexes...")

        print("  - idx_variants_base_type...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_variants_base_type
            ON indicator_variants(base_indicator_type)
        """)
        print("  [OK] Created")

        print("  - idx_variants_type...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_variants_type
            ON indicator_variants(variant_type)
        """)
        print("  [OK] Created")

        print("  - idx_variants_user...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_variants_user
            ON indicator_variants(user_id)
        """)
        print("  [OK] Created")

        print("  - idx_variants_scope...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_variants_scope
            ON indicator_variants(scope)
        """)
        print("  [OK] Created")

        # Verify table creation
        print("\nVerifying table creation...")
        row = await conn.fetchrow("""
            SELECT table_name FROM tables()
            WHERE table_name = 'indicator_variants'
        """)

        if row:
            print(f"[OK] Table 'indicator_variants' exists")
        else:
            print("[ERROR] Table not found!")
            return False

        # Show table structure
        print("\nTable structure:")
        columns = await conn.fetch("SHOW COLUMNS FROM indicator_variants")
        for col in columns:
            print(f"  {col['column']}: {col['type']}")

        print("\n[OK] Migration 008 completed successfully!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await conn.close()
        print("\nConnection closed")


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)
