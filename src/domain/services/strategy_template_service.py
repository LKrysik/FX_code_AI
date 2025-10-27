#!/usr/bin/env python3
"""
Strategy Template Service - Phase 2 Sprint 2
============================================

Service for managing strategy templates including:
- CRUD operations
- Search and filtering
- Usage tracking
- Template categories and tags
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import asyncpg

logger = logging.getLogger(__name__)


class StrategyTemplate:
    """Strategy Template model."""

    def __init__(
        self,
        id: UUID,
        name: str,
        description: Optional[str],
        category: str,
        strategy_json: Dict[str, Any],
        author: str = "system",
        is_public: bool = True,
        is_featured: bool = False,
        usage_count: int = 0,
        success_rate: Optional[float] = None,
        avg_return: Optional[float] = None,
        version: int = 1,
        parent_template_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.category = category
        self.strategy_json = strategy_json
        self.author = author
        self.is_public = is_public
        self.is_featured = is_featured
        self.usage_count = usage_count
        self.success_rate = success_rate
        self.avg_return = avg_return
        self.version = version
        self.parent_template_id = parent_template_id
        self.tags = tags or []
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "strategy_json": self.strategy_json,
            "author": self.author,
            "is_public": self.is_public,
            "is_featured": self.is_featured,
            "usage_count": self.usage_count,
            "success_rate": float(self.success_rate) if self.success_rate else None,
            "avg_return": float(self.avg_return) if self.avg_return else None,
            "version": self.version,
            "parent_template_id": str(self.parent_template_id) if self.parent_template_id else None,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def from_db_row(row: asyncpg.Record) -> "StrategyTemplate":
        """Create template from database row."""
        return StrategyTemplate(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            category=row["category"],
            strategy_json=row["strategy_json"],
            author=row["author"],
            is_public=row["is_public"],
            is_featured=row["is_featured"],
            usage_count=row["usage_count"],
            success_rate=row["success_rate"],
            avg_return=row["avg_return"],
            version=row["version"],
            parent_template_id=row["parent_template_id"],
            tags=row["tags"] or [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class StrategyTemplateService:
    """Service for managing strategy templates."""

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize service.

        Args:
            db_pool: PostgreSQL connection pool
        """
        self.db_pool = db_pool
        logger.info("StrategyTemplateService initialized")

    async def create_template(
        self,
        name: str,
        description: Optional[str],
        category: str,
        strategy_json: Dict[str, Any],
        author: str = "system",
        is_public: bool = True,
        is_featured: bool = False,
        tags: Optional[List[str]] = None,
        parent_template_id: Optional[UUID] = None,
    ) -> StrategyTemplate:
        """
        Create a new strategy template.

        Args:
            name: Template name
            description: Template description
            category: Template category
            strategy_json: Strategy configuration (5-section format)
            author: Template author
            is_public: Whether template is public
            is_featured: Whether template is featured
            tags: Search tags
            parent_template_id: Parent template (for variations)

        Returns:
            Created template
        """
        template_id = uuid4()

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO strategy_templates (
                    id, name, description, category, strategy_json,
                    author, is_public, is_featured, tags, parent_template_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING *
                """,
                template_id,
                name,
                description,
                category,
                strategy_json,
                author,
                is_public,
                is_featured,
                tags or [],
                parent_template_id,
            )

        template = StrategyTemplate.from_db_row(row)
        logger.info(f"Created template: {template.name} (ID: {template.id})")
        return template

    async def get_template(self, template_id: UUID) -> Optional[StrategyTemplate]:
        """
        Get template by ID.

        Args:
            template_id: Template ID

        Returns:
            Template or None if not found
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM strategy_templates WHERE id = $1",
                template_id,
            )

        if row:
            return StrategyTemplate.from_db_row(row)
        return None

    async def get_all_templates(
        self,
        category: Optional[str] = None,
        is_public: bool = True,
        is_featured: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[StrategyTemplate]:
        """
        Get all templates with optional filtering.

        Args:
            category: Filter by category
            is_public: Filter by public status
            is_featured: Filter by featured status
            limit: Maximum templates to return
            offset: Pagination offset

        Returns:
            List of templates
        """
        query = "SELECT * FROM strategy_templates WHERE is_public = $1"
        params: List[Any] = [is_public]
        param_count = 1

        if category:
            param_count += 1
            query += f" AND category = ${param_count}"
            params.append(category)

        if is_featured is not None:
            param_count += 1
            query += f" AND is_featured = ${param_count}"
            params.append(is_featured)

        query += " ORDER BY is_featured DESC, usage_count DESC, created_at DESC"
        query += f" LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [StrategyTemplate.from_db_row(row) for row in rows]

    async def search_templates(
        self,
        search_query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[StrategyTemplate]:
        """
        Search templates by text query and filters.

        Args:
            search_query: Full-text search query
            category: Filter by category
            tags: Filter by tags (any match)
            limit: Maximum templates to return

        Returns:
            List of matching templates
        """
        query = """
            SELECT *
            FROM strategy_templates
            WHERE is_public = true
        """
        params: List[Any] = []
        param_count = 0

        # Full-text search
        if search_query:
            param_count += 1
            query += f"""
                AND to_tsvector('english', name || ' ' || COALESCE(description, ''))
                @@ plainto_tsquery('english', ${param_count})
            """
            params.append(search_query)

        # Category filter
        if category:
            param_count += 1
            query += f" AND category = ${param_count}"
            params.append(category)

        # Tags filter (any match)
        if tags:
            param_count += 1
            query += f" AND tags && ${param_count}"
            params.append(tags)

        query += " ORDER BY usage_count DESC, created_at DESC"
        query += f" LIMIT ${param_count + 1}"
        params.append(limit)

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [StrategyTemplate.from_db_row(row) for row in rows]

    async def get_templates_by_category(self, category: str) -> List[StrategyTemplate]:
        """
        Get all public templates in a category.

        Args:
            category: Category name

        Returns:
            List of templates
        """
        return await self.get_all_templates(category=category, is_public=True)

    async def get_featured_templates(self, limit: int = 10) -> List[StrategyTemplate]:
        """
        Get featured templates.

        Args:
            limit: Maximum templates to return

        Returns:
            List of featured templates
        """
        return await self.get_all_templates(is_featured=True, limit=limit)

    async def get_popular_templates(self, limit: int = 10) -> List[StrategyTemplate]:
        """
        Get most popular templates by usage count.

        Args:
            limit: Maximum templates to return

        Returns:
            List of popular templates
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM strategy_templates
                WHERE is_public = true
                ORDER BY usage_count DESC, created_at DESC
                LIMIT $1
                """,
                limit,
            )

        return [StrategyTemplate.from_db_row(row) for row in rows]

    async def update_template(
        self,
        template_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        strategy_json: Optional[Dict[str, Any]] = None,
        is_public: Optional[bool] = None,
        is_featured: Optional[bool] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[StrategyTemplate]:
        """
        Update template fields.

        Args:
            template_id: Template ID
            name: New name
            description: New description
            category: New category
            strategy_json: New strategy config
            is_public: New public status
            is_featured: New featured status
            tags: New tags

        Returns:
            Updated template or None if not found
        """
        updates = []
        params: List[Any] = []
        param_count = 0

        if name is not None:
            param_count += 1
            updates.append(f"name = ${param_count}")
            params.append(name)

        if description is not None:
            param_count += 1
            updates.append(f"description = ${param_count}")
            params.append(description)

        if category is not None:
            param_count += 1
            updates.append(f"category = ${param_count}")
            params.append(category)

        if strategy_json is not None:
            param_count += 1
            updates.append(f"strategy_json = ${param_count}")
            params.append(strategy_json)

        if is_public is not None:
            param_count += 1
            updates.append(f"is_public = ${param_count}")
            params.append(is_public)

        if is_featured is not None:
            param_count += 1
            updates.append(f"is_featured = ${param_count}")
            params.append(is_featured)

        if tags is not None:
            param_count += 1
            updates.append(f"tags = ${param_count}")
            params.append(tags)

        if not updates:
            return await self.get_template(template_id)

        param_count += 1
        query = f"""
            UPDATE strategy_templates
            SET {', '.join(updates)}
            WHERE id = ${param_count}
            RETURNING *
        """
        params.append(template_id)

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        if row:
            template = StrategyTemplate.from_db_row(row)
            logger.info(f"Updated template: {template.name} (ID: {template.id})")
            return template

        return None

    async def delete_template(self, template_id: UUID) -> bool:
        """
        Delete template.

        Args:
            template_id: Template ID

        Returns:
            True if deleted, False if not found
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM strategy_templates WHERE id = $1",
                template_id,
            )

        deleted = result.split()[-1] == "1"
        if deleted:
            logger.info(f"Deleted template ID: {template_id}")
        return deleted

    async def increment_usage(self, template_id: UUID, user_id: Optional[str] = None) -> bool:
        """
        Increment template usage count and track usage.

        Args:
            template_id: Template ID
            user_id: User ID (optional)

        Returns:
            True if successful
        """
        async with self.db_pool.acquire() as conn:
            # Increment usage count
            await conn.execute(
                "SELECT increment_template_usage($1)",
                template_id,
            )

            # Track usage in history
            await conn.execute(
                """
                INSERT INTO template_usage_history (template_id, user_id, action, metadata)
                VALUES ($1, $2, 'use', $3)
                """,
                template_id,
                user_id,
                {"timestamp": datetime.utcnow().isoformat()},
            )

        logger.debug(f"Incremented usage for template: {template_id}")
        return True

    async def track_usage(
        self,
        template_id: UUID,
        action: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Track template usage action.

        Args:
            template_id: Template ID
            action: Action type ('view', 'use', 'fork', 'backtest')
            user_id: User ID (optional)
            metadata: Additional metadata

        Returns:
            True if successful
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO template_usage_history (template_id, user_id, action, metadata)
                VALUES ($1, $2, $3, $4)
                """,
                template_id,
                user_id,
                action,
                metadata or {},
            )

        logger.debug(f"Tracked {action} for template: {template_id}")
        return True

    async def fork_template(
        self,
        template_id: UUID,
        new_name: str,
        author: str,
        modifications: Optional[Dict[str, Any]] = None,
    ) -> Optional[StrategyTemplate]:
        """
        Create a forked copy of a template.

        Args:
            template_id: Original template ID
            new_name: Name for forked template
            author: Author of forked template
            modifications: Modifications to strategy_json

        Returns:
            Forked template or None if original not found
        """
        # Get original template
        original = await self.get_template(template_id)
        if not original:
            return None

        # Create modified strategy
        strategy_json = original.strategy_json.copy()
        if modifications:
            strategy_json.update(modifications)

        # Create fork
        fork = await self.create_template(
            name=new_name,
            description=f"Forked from: {original.name}",
            category=original.category,
            strategy_json=strategy_json,
            author=author,
            is_public=False,  # Forks are private by default
            is_featured=False,
            tags=original.tags,
            parent_template_id=original.id,
        )

        # Track fork action
        await self.track_usage(
            template_id=template_id,
            action="fork",
            user_id=author,
            metadata={"fork_id": str(fork.id)},
        )

        logger.info(f"Forked template {original.name} -> {new_name} (ID: {fork.id})")
        return fork

    async def get_template_stats(self, template_id: UUID) -> Dict[str, Any]:
        """
        Get usage statistics for a template.

        Args:
            template_id: Template ID

        Returns:
            Statistics dictionary
        """
        async with self.db_pool.acquire() as conn:
            # Get template info
            template_row = await conn.fetchrow(
                "SELECT * FROM strategy_templates WHERE id = $1",
                template_id,
            )

            if not template_row:
                return {}

            # Get usage breakdown
            usage_stats = await conn.fetch(
                """
                SELECT action, COUNT(*) as count
                FROM template_usage_history
                WHERE template_id = $1
                GROUP BY action
                """,
                template_id,
            )

            # Get recent usage
            recent_usage = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as last_week,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') as last_month
                FROM template_usage_history
                WHERE template_id = $1
                """,
                template_id,
            )

        return {
            "template_id": str(template_id),
            "name": template_row["name"],
            "total_usage": template_row["usage_count"],
            "usage_by_action": {row["action"]: row["count"] for row in usage_stats},
            "usage_last_week": recent_usage["last_week"],
            "usage_last_month": recent_usage["last_month"],
            "success_rate": float(template_row["success_rate"]) if template_row["success_rate"] else None,
            "avg_return": float(template_row["avg_return"]) if template_row["avg_return"] else None,
        }

    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Get all categories with template counts.

        Returns:
            List of categories with counts
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT category, COUNT(*) as count
                FROM strategy_templates
                WHERE is_public = true
                GROUP BY category
                ORDER BY count DESC
                """
            )

        return [{"category": row["category"], "count": row["count"]} for row in rows]

    async def update_backtest_stats(
        self,
        template_id: UUID,
        success_rate: float,
        avg_return: float,
    ) -> bool:
        """
        Update template backtest statistics.

        Args:
            template_id: Template ID
            success_rate: Success rate percentage (0-100)
            avg_return: Average return percentage

        Returns:
            True if successful
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE strategy_templates
                SET success_rate = $1, avg_return = $2
                WHERE id = $3
                """,
                success_rate,
                avg_return,
                template_id,
            )

        logger.info(f"Updated backtest stats for template: {template_id}")
        return True
