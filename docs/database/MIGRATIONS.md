# Database Migrations

Guide for managing QuestDB schema changes and data migrations.

## Creating a Migration

1. Create SQL file: `database/questdb/migrations/YYYYMMDD_description.sql`
2. Test migration on local QuestDB
3. Document changes in this file

## Running Migrations

\`\`\`bash
# Connect to QuestDB
psql -h localhost -p 8812 -U admin -d qdb

# Run migration
\i database/questdb/migrations/20251028_add_new_table.sql
\`\`\`

## Migration History

### 2025-10-27: Initial Schema
- Created tick_prices table
- Created indicators table
- Created data_collection_sessions table

---

For schema reference, see [SCHEMA.md](SCHEMA.md).
