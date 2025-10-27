#!/usr/bin/env python3
"""
Seed Strategy Templates - Phase 2 Sprint 2
==========================================

Script to load pre-built strategy templates into the database.
Run this after database migration 002_strategy_templates.sql.
"""

import asyncio
import asyncpg
import json
import logging
from pathlib import Path
from uuid import uuid4

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def seed_templates():
    """Load templates from JSON and insert into database."""

    # Load templates from JSON file
    templates_file = Path(__file__).parent.parent / "database" / "seed_data" / "strategy_templates.json"

    if not templates_file.exists():
        logger.error(f"Templates file not found: {templates_file}")
        return

    with open(templates_file, 'r') as f:
        templates = json.load(f)

    logger.info(f"Loaded {len(templates)} templates from {templates_file}")

    # Connect to database
    # TODO: Use proper config for connection
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        database="fx_trading",
        user="fx_user",
        password="fx_password"
    )

    try:
        # Check if templates already exist
        count = await conn.fetchval("SELECT COUNT(*) FROM strategy_templates")

        if count > 0:
            logger.warning(f"Database already has {count} templates. Delete them first? (y/n)")
            response = input().strip().lower()
            if response == 'y':
                await conn.execute("DELETE FROM strategy_templates")
                logger.info("Deleted existing templates")
            else:
                logger.info("Skipping seed - templates already exist")
                return

        # Insert templates
        inserted = 0

        for template in templates:
            try:
                template_id = uuid4()

                await conn.execute(
                    """
                    INSERT INTO strategy_templates (
                        id, name, description, category, strategy_json,
                        author, is_public, is_featured, tags
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    template_id,
                    template["name"],
                    template["description"],
                    template["category"],
                    template["strategy_json"],
                    template["author"],
                    template["is_public"],
                    template["is_featured"],
                    template["tags"]
                )

                inserted += 1
                logger.info(f"✓ Inserted: {template['name']} (ID: {template_id})")

            except Exception as e:
                logger.error(f"✗ Failed to insert {template['name']}: {e}")

        logger.info(f"\n{'='*60}")
        logger.info(f"Seed completed: {inserted}/{len(templates)} templates inserted")
        logger.info(f"{'='*60}\n")

        # Show summary
        summary = await conn.fetch(
            """
            SELECT
                category,
                COUNT(*) as count,
                COUNT(*) FILTER (WHERE is_featured) as featured
            FROM strategy_templates
            GROUP BY category
            ORDER BY count DESC
            """
        )

        logger.info("Templates by category:")
        for row in summary:
            logger.info(f"  {row['category']}: {row['count']} total, {row['featured']} featured")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed_templates())
