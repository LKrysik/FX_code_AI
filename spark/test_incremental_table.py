"""
Test script for new "Incremental Table" operation_type
Author: Claude Code
Date: 2025-11-24
Version: 3.15

This script demonstrates the usage of the new Incremental Table operation_type
and can be used to validate the implementation.

Usage:
    Copy this code into a Synapse Spark notebook and run it.
"""

# ===================================================================================
# EXAMPLE 1: Basic Incremental Table
# ===================================================================================

print("=" * 80)
print("Example 1: Basic Incremental Table - Full Load + Delta Load")
print("=" * 80)

# Define metadata
metadata_json = '''
{
    "target_table": {
        "target_schema": "process",
        "target_table": "test_incremental_basic",
        "format": "delta",
        "operation_type": "Incremental Table",
        "incremental_params": {
            "id_key_column": "id",
            "log_history": false
        },
        "params": {
            "drop_table": "True",
            "skip_data_lineage": true
        }
    },
    "source_tables": [
        {"schema": "process", "table": "test_source_data", "view": "source"}
    ],
    "env": "''' + str(ENV) + '''",
    "project_name": "''' + str(PROJECT_NAME) + '''"
}
'''

# Create test source data
print("\n1. Creating test source data...")
test_data = [
    (1, "Alice", 100, "2024-01-01"),
    (2, "Bob", 200, "2024-01-01"),
    (3, "Charlie", 300, "2024-01-01")
]
df_source = spark.createDataFrame(test_data, ["id", "name", "value", "date"])
df_source.createOrReplaceTempView("test_source_data")
print(f"   Created {df_source.count()} source records")

# Prepare environment
print("\n2. Preparing environment...")
make_env_tables(metadata_json)

# First run - FULL LOAD
print("\n3. Running FULL LOAD (target doesn't exist)...")
df_result = create_table(metadata_json, df_source)
print(f"   Full load completed with {df_result.count()} records")

# Show results
target_name = get_table_env_name("process", "test_incremental_basic", ENV, PROJECT_NAME, False, False)
print(f"\n4. Target table: {target_name}")
spark.sql(f"SELECT * FROM {target_name}").show()

# Update source data - add Insert, Update, Delete
print("\n5. Modifying source data...")
test_data_updated = [
    (1, "Alice", 150, "2024-01-02"),      # UPDATE - value changed
    (2, "Bob", 200, "2024-01-02"),        # NO CHANGE
    # (3, "Charlie", ...) - DELETED
    (4, "David", 400, "2024-01-02")       # INSERT - new record
]
df_source_updated = spark.createDataFrame(test_data_updated, ["id", "name", "value", "date"])
df_source_updated.createOrReplaceTempView("test_source_data")

# Second run - DELTA LOAD
print("\n6. Running DELTA LOAD (target exists)...")
df_delta_result = create_table(metadata_json, df_source_updated)

if df_delta_result:
    print(f"   Delta load completed with {df_delta_result.count()} changes")
    print("\n7. Changes detected:")
    df_delta_result.select("id", "name", "value", "operation_type", "last_update_dt").show()
else:
    print("   No changes detected")

# Show final state
print("\n8. Final target table state:")
spark.sql(f"SELECT * FROM {target_name} ORDER BY id").show()

print("\n✓ Example 1 completed successfully!")


# ===================================================================================
# EXAMPLE 2: Incremental Table with History Logging
# ===================================================================================

print("\n" + "=" * 80)
print("Example 2: Incremental Table with History Logging")
print("=" * 80)

metadata_with_history = '''
{
    "target_table": {
        "target_schema": "process",
        "target_table": "test_incremental_with_history",
        "format": "delta",
        "operation_type": "Incremental Table",
        "incremental_params": {
            "id_key_column": "customer_id",
            "log_history": true,
            "history_table_name": "test_incremental_history",
            "history_retention_days": 30,
            "excluded_columns_for_hash": ["last_modified"]
        },
        "params": {
            "drop_table": "True",
            "skip_data_lineage": true
        }
    },
    "source_tables": [
        {"schema": "process", "table": "test_customer_source", "view": "source"}
    ],
    "env": "''' + str(ENV) + '''",
    "project_name": "''' + str(PROJECT_NAME) + '''"
}
'''

# Create customer test data
print("\n1. Creating customer source data...")
customer_data = [
    (101, "Company A", "active", "2024-01-01", "2024-01-01"),
    (102, "Company B", "active", "2024-01-01", "2024-01-01")
]
df_customers = spark.createDataFrame(customer_data,
                                      ["customer_id", "name", "status", "created_date", "last_modified"])
df_customers.createOrReplaceTempView("test_customer_source")

# Prepare and run full load
print("\n2. Running FULL LOAD with history logging...")
make_env_tables(metadata_with_history)
df_result = create_table(metadata_with_history, df_customers)
print(f"   Full load completed")

# Update customer data
print("\n3. Updating customer data...")
customer_data_updated = [
    (101, "Company A Updated", "active", "2024-01-01", "2024-01-02"),    # UPDATE
    (102, "Company B", "inactive", "2024-01-01", "2024-01-02"),          # UPDATE (status)
    (103, "Company C", "active", "2024-01-02", "2024-01-02")             # INSERT
]
df_customers_updated = spark.createDataFrame(customer_data_updated,
                                             ["customer_id", "name", "status", "created_date", "last_modified"])
df_customers_updated.createOrReplaceTempView("test_customer_source")

# Run delta load
print("\n4. Running DELTA LOAD...")
df_delta = create_table(metadata_with_history, df_customers_updated)

if df_delta:
    print(f"   Changes detected: {df_delta.count()}")

# Check history table
history_name = get_table_env_name("process", "test_incremental_history", ENV, PROJECT_NAME, False, False)
print(f"\n5. History table: {history_name}")
spark.sql(f"""
    SELECT customer_id, name, status, operation_type, _audit_operation, _audit_timestamp
    FROM {history_name}
    ORDER BY _audit_timestamp
""").show(truncate=False)

print("\n✓ Example 2 completed successfully!")


# ===================================================================================
# EXAMPLE 3: Schema Evolution Test
# ===================================================================================

print("\n" + "=" * 80)
print("Example 3: Schema Evolution (new columns)")
print("=" * 80)

metadata_schema_evolution = '''
{
    "target_table": {
        "target_schema": "process",
        "target_table": "test_schema_evolution",
        "format": "delta",
        "operation_type": "Incremental Table",
        "incremental_params": {
            "id_key_column": "product_id",
            "ignore_new_columns_as_change": true,
            "log_history": false
        },
        "params": {
            "drop_table": "True",
            "skip_data_lineage": true
        }
    },
    "source_tables": [
        {"schema": "process", "table": "test_product_source", "view": "source"}
    ],
    "env": "''' + str(ENV) + '''",
    "project_name": "''' + str(PROJECT_NAME) + '''"
}
'''

# Initial product data (3 columns)
print("\n1. Creating initial product data (3 columns)...")
product_data = [
    (1, "Product A", 100),
    (2, "Product B", 200)
]
df_products = spark.createDataFrame(product_data, ["product_id", "name", "price"])
df_products.createOrReplaceTempView("test_product_source")

# Full load
print("\n2. Running FULL LOAD...")
make_env_tables(metadata_schema_evolution)
create_table(metadata_schema_evolution, df_products)

# Show initial schema
target_name = get_table_env_name("process", "test_schema_evolution", ENV, PROJECT_NAME, False, False)
print(f"\n3. Initial schema:")
spark.sql(f"DESCRIBE {target_name}").show()

# Add new column to source (4 columns)
print("\n4. Adding new column 'category' to source...")
product_data_with_new_col = [
    (1, "Product A", 100, "Electronics"),       # NEW COLUMN
    (2, "Product B", 200, "Furniture"),         # NEW COLUMN
    (3, "Product C", 300, "Electronics")        # NEW ROW + NEW COLUMN
]
df_products_new_col = spark.createDataFrame(product_data_with_new_col,
                                            ["product_id", "name", "price", "category"])
df_products_new_col.createOrReplaceTempView("test_product_source")

# Delta load with schema evolution
print("\n5. Running DELTA LOAD with new column...")
df_delta = create_table(metadata_schema_evolution, df_products_new_col)

# Show evolved schema
print(f"\n6. Evolved schema (should have 'category' column):")
spark.sql(f"DESCRIBE {target_name}").show()

print(f"\n7. Final data:")
spark.sql(f"SELECT * FROM {target_name} ORDER BY product_id").show()

print("\n✓ Example 3 completed successfully!")


# ===================================================================================
# CLEANUP (optional)
# ===================================================================================

print("\n" + "=" * 80)
print("Cleanup (uncomment if you want to drop test tables)")
print("=" * 80)

# Uncomment below to cleanup test tables:
# spark.sql("DROP TABLE IF EXISTS process.test_incremental_basic")
# spark.sql("DROP TABLE IF EXISTS process.test_incremental_with_history")
# spark.sql("DROP TABLE IF EXISTS process.test_incremental_history")
# spark.sql("DROP TABLE IF EXISTS process.test_schema_evolution")
# print("✓ Cleanup completed")

print("\n" + "=" * 80)
print("All tests completed successfully! ✓")
print("=" * 80)
