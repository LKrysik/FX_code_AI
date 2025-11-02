#!/usr/bin/env python3
"""
Unit Tests for Strategy Template Service - Phase 2 Sprint 2
===========================================================

Tests for StrategyTemplateService covering:
- CRUD operations
- Search and filtering
- Usage tracking
- Template forking
- Statistics
"""

import pytest
import asyncpg
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime
from src.domain.services.strategy_template_service import (
    StrategyTemplateService,
    StrategyTemplate
)


@pytest.fixture
def mock_db_pool():
    """Create mock database pool."""
    pool = AsyncMock(spec=asyncpg.Pool)
    return pool


@pytest.fixture
def sample_strategy_json():
    """Sample strategy configuration."""
    return {
        "name": "Test Strategy",
        "s1_signal": {"conditions": []},
        "z1_entry": {"conditions": [], "positionSize": {"type": "percentage", "value": 10}},
        "ze1_close": {"conditions": []},
        "o1_cancel": {"timeoutSeconds": 300, "conditions": [], "cooldownMinutes": 60},
        "emergency_exit": {
            "conditions": [],
            "cooldownMinutes": 120,
            "actions": {"cancelPending": True, "closePosition": True, "logEvent": True}
        }
    }


@pytest.fixture
def sample_db_row():
    """Sample database row."""
    return {
        "id": uuid4(),
        "name": "Test Template",
        "description": "Test description",
        "category": "trend_following",
        "strategy_json": {"name": "Test"},
        "author": "system",
        "is_public": True,
        "is_featured": False,
        "usage_count": 10,
        "success_rate": 75.5,
        "avg_return": 5.2,
        "version": 1,
        "parent_template_id": None,
        "tags": ["test", "demo"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


class TestStrategyTemplate:
    """Test StrategyTemplate model."""

    def test_to_dict(self, sample_db_row):
        """Test converting template to dictionary."""
        template = StrategyTemplate.from_db_row(sample_db_row)
        result = template.to_dict()

        assert result["id"] == str(sample_db_row["id"])
        assert result["name"] == sample_db_row["name"]
        assert result["category"] == sample_db_row["category"]
        assert result["usage_count"] == sample_db_row["usage_count"]
        assert result["success_rate"] == float(sample_db_row["success_rate"])

    def test_from_db_row(self, sample_db_row):
        """Test creating template from database row."""
        template = StrategyTemplate.from_db_row(sample_db_row)

        assert template.id == sample_db_row["id"]
        assert template.name == sample_db_row["name"]
        assert template.category == sample_db_row["category"]
        assert template.tags == sample_db_row["tags"]


@pytest.mark.asyncio
class TestCreateTemplate:
    """Test template creation."""

    async def test_create_template_success(self, mock_db_pool, sample_strategy_json, sample_db_row):
        """Test successful template creation."""
        # Setup mock
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = sample_db_row
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Create service and template
        service = StrategyTemplateService(mock_db_pool)
        template = await service.create_template(
            name="Test Template",
            description="Test description",
            category="trend_following",
            strategy_json=sample_strategy_json,
            tags=["test", "demo"]
        )

        # Verify
        assert template.name == sample_db_row["name"]
        assert template.category == sample_db_row["category"]
        mock_conn.fetchrow.assert_called_once()

    async def test_create_template_with_parent(self, mock_db_pool, sample_strategy_json, sample_db_row):
        """Test creating template with parent (fork)."""
        parent_id = uuid4()
        sample_db_row["parent_template_id"] = parent_id

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = sample_db_row
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        template = await service.create_template(
            name="Forked Template",
            description="Forked",
            category="trend_following",
            strategy_json=sample_strategy_json,
            parent_template_id=parent_id
        )

        assert template.parent_template_id == parent_id


@pytest.mark.asyncio
class TestGetTemplate:
    """Test template retrieval."""

    async def test_get_template_found(self, mock_db_pool, sample_db_row):
        """Test getting existing template."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = sample_db_row
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        template = await service.get_template(sample_db_row["id"])

        assert template is not None
        assert template.id == sample_db_row["id"]
        assert template.name == sample_db_row["name"]

    async def test_get_template_not_found(self, mock_db_pool):
        """Test getting non-existent template."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        template = await service.get_template(uuid4())

        assert template is None


@pytest.mark.asyncio
class TestGetAllTemplates:
    """Test listing templates with filters."""

    async def test_get_all_templates_no_filter(self, mock_db_pool, sample_db_row):
        """Test getting all public templates."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [sample_db_row, sample_db_row]
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        templates = await service.get_all_templates()

        assert len(templates) == 2
        assert all(t.is_public for t in templates)

    async def test_get_all_templates_with_category(self, mock_db_pool, sample_db_row):
        """Test filtering by category."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [sample_db_row]
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        templates = await service.get_all_templates(category="trend_following")

        assert len(templates) == 1
        assert templates[0].category == "trend_following"

    async def test_get_featured_templates(self, mock_db_pool, sample_db_row):
        """Test getting featured templates."""
        sample_db_row["is_featured"] = True
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [sample_db_row]
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        templates = await service.get_featured_templates(limit=10)

        assert len(templates) == 1
        assert templates[0].is_featured is True


@pytest.mark.asyncio
class TestSearchTemplates:
    """Test template search."""

    async def test_search_by_query(self, mock_db_pool, sample_db_row):
        """Test full-text search."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [sample_db_row]
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        templates = await service.search_templates(search_query="trend")

        assert len(templates) == 1

    async def test_search_by_tags(self, mock_db_pool, sample_db_row):
        """Test search by tags."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [sample_db_row]
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        templates = await service.search_templates(search_query="", tags=["test"])

        assert len(templates) == 1
        assert "test" in templates[0].tags


@pytest.mark.asyncio
class TestUpdateTemplate:
    """Test template updates."""

    async def test_update_template_name(self, mock_db_pool, sample_db_row):
        """Test updating template name."""
        updated_row = sample_db_row.copy()
        updated_row["name"] = "Updated Name"

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = updated_row
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        template = await service.update_template(
            template_id=sample_db_row["id"],
            name="Updated Name"
        )

        assert template is not None
        assert template.name == "Updated Name"

    async def test_update_template_multiple_fields(self, mock_db_pool, sample_db_row):
        """Test updating multiple fields."""
        updated_row = sample_db_row.copy()
        updated_row["name"] = "New Name"
        updated_row["is_featured"] = True
        updated_row["tags"] = ["new", "tags"]

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = updated_row
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        template = await service.update_template(
            template_id=sample_db_row["id"],
            name="New Name",
            is_featured=True,
            tags=["new", "tags"]
        )

        assert template.name == "New Name"
        assert template.is_featured is True
        assert template.tags == ["new", "tags"]

    async def test_update_template_not_found(self, mock_db_pool):
        """Test updating non-existent template."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        template = await service.update_template(
            template_id=uuid4(),
            name="New Name"
        )

        assert template is None


@pytest.mark.asyncio
class TestDeleteTemplate:
    """Test template deletion."""

    async def test_delete_template_success(self, mock_db_pool):
        """Test successful deletion."""
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 1"
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        result = await service.delete_template(uuid4())

        assert result is True

    async def test_delete_template_not_found(self, mock_db_pool):
        """Test deleting non-existent template."""
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 0"
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        result = await service.delete_template(uuid4())

        assert result is False


@pytest.mark.asyncio
class TestUsageTracking:
    """Test usage tracking functionality."""

    async def test_increment_usage(self, mock_db_pool):
        """Test incrementing usage count."""
        mock_conn = AsyncMock()
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        result = await service.increment_usage(uuid4(), user_id="test_user")

        assert result is True
        assert mock_conn.execute.call_count == 2  # increment + track

    async def test_track_usage_action(self, mock_db_pool):
        """Test tracking specific actions."""
        mock_conn = AsyncMock()
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        result = await service.track_usage(
            template_id=uuid4(),
            action="view",
            user_id="test_user",
            metadata={"source": "web"}
        )

        assert result is True
        mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
class TestForkTemplate:
    """Test template forking."""

    async def test_fork_template_success(self, mock_db_pool, sample_db_row, sample_strategy_json):
        """Test successful fork."""
        # Original template
        original_row = sample_db_row.copy()

        # Forked template
        forked_row = sample_db_row.copy()
        forked_row["id"] = uuid4()
        forked_row["name"] = "Forked Template"
        forked_row["parent_template_id"] = original_row["id"]
        forked_row["is_public"] = False

        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [original_row, forked_row]  # get + create
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        fork = await service.fork_template(
            template_id=original_row["id"],
            new_name="Forked Template",
            author="test_user"
        )

        assert fork is not None
        assert fork.name == "Forked Template"
        assert fork.parent_template_id == original_row["id"]
        assert fork.is_public is False

    async def test_fork_template_not_found(self, mock_db_pool):
        """Test forking non-existent template."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        fork = await service.fork_template(
            template_id=uuid4(),
            new_name="Fork",
            author="test_user"
        )

        assert fork is None


@pytest.mark.asyncio
class TestStatistics:
    """Test template statistics."""

    async def test_get_template_stats(self, mock_db_pool, sample_db_row):
        """Test getting template statistics."""
        usage_stats = [
            {"action": "view", "count": 100},
            {"action": "use", "count": 50},
            {"action": "fork", "count": 10},
        ]

        recent_usage = {
            "last_week": 20,
            "last_month": 80,
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [sample_db_row, recent_usage]
        mock_conn.fetch.return_value = usage_stats
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        stats = await service.get_template_stats(sample_db_row["id"])

        assert stats["template_id"] == str(sample_db_row["id"])
        assert stats["total_usage"] == sample_db_row["usage_count"]
        assert stats["usage_by_action"]["view"] == 100
        assert stats["usage_last_week"] == 20

    async def test_get_categories(self, mock_db_pool):
        """Test getting category counts."""
        category_data = [
            {"category": "trend_following", "count": 5},
            {"category": "mean_reversion", "count": 3},
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = category_data
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        categories = await service.get_categories()

        assert len(categories) == 2
        assert categories[0]["category"] == "trend_following"
        assert categories[0]["count"] == 5

    async def test_update_backtest_stats(self, mock_db_pool):
        """Test updating backtest statistics."""
        mock_conn = AsyncMock()
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        result = await service.update_backtest_stats(
            template_id=uuid4(),
            success_rate=75.5,
            avg_return=5.2
        )

        assert result is True
        mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
class TestPopularTemplates:
    """Test getting popular templates."""

    async def test_get_popular_templates(self, mock_db_pool, sample_db_row):
        """Test getting most used templates."""
        popular_row1 = sample_db_row.copy()
        popular_row1["usage_count"] = 1000

        popular_row2 = sample_db_row.copy()
        popular_row2["id"] = uuid4()
        popular_row2["usage_count"] = 500

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [popular_row1, popular_row2]
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        service = StrategyTemplateService(mock_db_pool)
        templates = await service.get_popular_templates(limit=10)

        assert len(templates) == 2
        assert templates[0].usage_count >= templates[1].usage_count


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
