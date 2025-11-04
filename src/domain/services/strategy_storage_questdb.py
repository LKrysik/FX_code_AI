"""
Strategy Storage - QuestDB-based persistence for trading strategies
===================================================================
Implements strategy CRUD operations using QuestDB relational table.
Replaces file-based storage with database persistence.

Table: strategies (from migration 012_create_strategies_table.sql)
Connection: PostgreSQL protocol (port 8812)
"""

import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncpg


class StrategyStorageError(Exception):
    """Base exception for strategy storage operations"""
    pass


class StrategyNotFoundError(StrategyStorageError):
    """Raised when strategy is not found"""
    pass


class StrategyValidationError(StrategyStorageError):
    """Raised when strategy validation fails"""
    pass


class QuestDBStrategyStorage:
    """
    QuestDB-based storage for trading strategies.
    Uses PostgreSQL protocol to connect to QuestDB (port 8812).

    Table schema (from migration 012):
    - id: UUID as string (primary key)
    - strategy_name: User-defined name
    - direction: LONG/SHORT/BOTH
    - enabled: boolean
    - strategy_json: Full config as JSON string
    - author: Strategy creator
    - category: Optional category
    - tags: Comma-separated tags
    - template_id: Optional template reference
    - created_at, updated_at, last_activated_at: timestamps
    """

    def __init__(self,
                 host: str = "127.0.0.1",
                 port: int = 8812,
                 user: str = "admin",
                 password: str = "quest",
                 database: str = "qdb"):
        """
        Initialize QuestDB strategy storage.

        Args:
            host: QuestDB host
            port: PostgreSQL protocol port (default: 8812)
            user: Database user
            password: Database password
            database: Database name
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        """Initialize connection pool to QuestDB."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=2,
                max_size=10,
                command_timeout=30
            )

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def _get_connection(self) -> asyncpg.Connection:
        """Get connection from pool."""
        if self._pool is None:
            await self.initialize()
        return await self._pool.acquire()

    async def _release_connection(self, conn: asyncpg.Connection) -> None:
        """Release connection back to pool."""
        if self._pool:
            await self._pool.release(conn)

    async def create_strategy(self, strategy_data: Dict[str, Any]) -> str:
        """
        Create a new strategy with UUID assignment.

        Args:
            strategy_data: Strategy configuration dict (5-section format)

        Returns:
            Generated UUID string

        Raises:
            StrategyValidationError: If strategy data is invalid
            StrategyStorageError: If database operation fails
        """
        conn = None
        try:
            # Generate UUID
            strategy_id = str(uuid.uuid4())

            # Extract metadata
            strategy_name = strategy_data.get("strategy_name")
            if not strategy_name:
                raise StrategyValidationError("strategy_name is required")

            direction = strategy_data.get("direction", "LONG")
            enabled = strategy_data.get("enabled", True)
            author = strategy_data.get("created_by", "user")
            description = strategy_data.get("description", "")
            category = strategy_data.get("category", "")
            tags = strategy_data.get("tags", "")
            template_id = strategy_data.get("template_id")

            # Serialize full config as JSON
            strategy_json = json.dumps(strategy_data)

            # Current timestamp
            now = datetime.utcnow()

            # Insert into QuestDB
            conn = await self._get_connection()

            query = """
                INSERT INTO strategies (
                    id, strategy_name, description, direction, enabled,
                    strategy_json, author, category, tags, template_id,
                    created_at, updated_at, last_activated_at
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9, $10,
                    $11, $12, $13
                )
            """

            await conn.execute(
                query,
                strategy_id, strategy_name, description, direction, enabled,
                strategy_json, author, category, tags, template_id,
                now, now, None  # last_activated_at starts as NULL
            )

            return strategy_id

        except asyncpg.UniqueViolationError:
            raise StrategyStorageError(f"Strategy with name '{strategy_name}' already exists")
        except Exception as e:
            raise StrategyStorageError(f"Failed to create strategy: {e}")
        finally:
            if conn:
                await self._release_connection(conn)

    async def read_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """
        Read strategy by UUID.

        Args:
            strategy_id: Strategy UUID

        Returns:
            Strategy configuration dict

        Raises:
            StrategyNotFoundError: If strategy doesn't exist
            StrategyStorageError: If database operation fails
        """
        conn = None
        try:
            conn = await self._get_connection()

            query = """
                SELECT id, strategy_name, description, direction, enabled,
                       strategy_json, author, category, tags, template_id,
                       created_at, updated_at, last_activated_at
                FROM strategies
                WHERE id = $1
            """

            row = await conn.fetchrow(query, strategy_id)

            if not row:
                raise StrategyNotFoundError(f"Strategy {strategy_id} not found")

            # Deserialize JSON config
            strategy_data = json.loads(row['strategy_json'])

            # Add metadata fields
            strategy_data['id'] = row['id']
            strategy_data['created_at'] = row['created_at'].isoformat() if row['created_at'] else None
            strategy_data['updated_at'] = row['updated_at'].isoformat() if row['updated_at'] else None
            strategy_data['last_activated_at'] = row['last_activated_at'].isoformat() if row['last_activated_at'] else None

            return strategy_data

        except StrategyNotFoundError:
            raise
        except Exception as e:
            raise StrategyStorageError(f"Failed to read strategy {strategy_id}: {e}")
        finally:
            if conn:
                await self._release_connection(conn)

    async def update_strategy(self, strategy_id: str, strategy_data: Dict[str, Any]) -> None:
        """
        Update existing strategy.

        Args:
            strategy_id: Strategy UUID
            strategy_data: Updated strategy configuration

        Raises:
            StrategyNotFoundError: If strategy doesn't exist
            StrategyValidationError: If strategy data is invalid
            StrategyStorageError: If database operation fails
        """
        conn = None
        try:
            # Verify strategy exists
            existing = await self.read_strategy(strategy_id)

            # Extract updated metadata
            strategy_name = strategy_data.get("strategy_name", existing.get("strategy_name"))
            direction = strategy_data.get("direction", existing.get("direction", "LONG"))
            enabled = strategy_data.get("enabled", existing.get("enabled", True))
            description = strategy_data.get("description", existing.get("description", ""))
            category = strategy_data.get("category", existing.get("category", ""))
            tags = strategy_data.get("tags", existing.get("tags", ""))

            # Serialize full config as JSON
            strategy_json = json.dumps(strategy_data)

            # Update timestamp
            now = datetime.utcnow()

            # Update in QuestDB
            conn = await self._get_connection()

            query = """
                UPDATE strategies
                SET strategy_name = $2,
                    description = $3,
                    direction = $4,
                    enabled = $5,
                    strategy_json = $6,
                    category = $7,
                    tags = $8,
                    updated_at = $9
                WHERE id = $1
            """

            result = await conn.execute(
                query,
                strategy_id, strategy_name, description, direction, enabled,
                strategy_json, category, tags, now
            )

            # Check if any rows were updated
            if result == "UPDATE 0":
                raise StrategyNotFoundError(f"Strategy {strategy_id} not found")

        except StrategyNotFoundError:
            raise
        except Exception as e:
            raise StrategyStorageError(f"Failed to update strategy {strategy_id}: {e}")
        finally:
            if conn:
                await self._release_connection(conn)

    async def delete_strategy(self, strategy_id: str) -> None:
        """
        Delete strategy by UUID.

        Args:
            strategy_id: Strategy UUID

        Raises:
            StrategyNotFoundError: If strategy doesn't exist
            StrategyStorageError: If database operation fails
        """
        conn = None
        try:
            conn = await self._get_connection()

            query = "DELETE FROM strategies WHERE id = $1"
            result = await conn.execute(query, strategy_id)

            if result == "DELETE 0":
                raise StrategyNotFoundError(f"Strategy {strategy_id} not found")

        except StrategyNotFoundError:
            raise
        except Exception as e:
            raise StrategyStorageError(f"Failed to delete strategy {strategy_id}: {e}")
        finally:
            if conn:
                await self._release_connection(conn)

    async def list_strategies(self) -> List[Dict[str, Any]]:
        """
        List all strategies with basic metadata.

        Returns:
            List of strategy summary dicts

        Raises:
            StrategyStorageError: If database operation fails
        """
        conn = None
        try:
            conn = await self._get_connection()

            query = """
                SELECT id, strategy_name, direction, enabled,
                       created_at, updated_at, last_activated_at
                FROM strategies
                ORDER BY updated_at DESC
            """

            rows = await conn.fetch(query)

            strategies = []
            for row in rows:
                strategies.append({
                    "id": row['id'],
                    "strategy_name": row['strategy_name'],
                    "direction": row['direction'],
                    "enabled": row['enabled'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                    "last_activated_at": row['last_activated_at'].isoformat() if row['last_activated_at'] else None
                })

            return strategies

        except Exception as e:
            raise StrategyStorageError(f"Failed to list strategies: {e}")
        finally:
            if conn:
                await self._release_connection(conn)

    async def mark_activated(self, strategy_id: str) -> None:
        """
        Mark strategy as activated (update last_activated_at timestamp).

        Args:
            strategy_id: Strategy UUID

        Raises:
            StrategyNotFoundError: If strategy doesn't exist
            StrategyStorageError: If database operation fails
        """
        conn = None
        try:
            conn = await self._get_connection()

            now = datetime.utcnow()
            query = "UPDATE strategies SET last_activated_at = $2 WHERE id = $1"
            result = await conn.execute(query, strategy_id, now)

            if result == "UPDATE 0":
                raise StrategyNotFoundError(f"Strategy {strategy_id} not found")

        except StrategyNotFoundError:
            raise
        except Exception as e:
            raise StrategyStorageError(f"Failed to mark strategy as activated: {e}")
        finally:
            if conn:
                await self._release_connection(conn)

    async def get_enabled_strategies(self) -> List[Dict[str, Any]]:
        """
        Get all enabled strategies.

        Returns:
            List of enabled strategy dicts

        Raises:
            StrategyStorageError: If database operation fails
        """
        conn = None
        try:
            conn = await self._get_connection()

            query = """
                SELECT id, strategy_name, description, direction, enabled,
                       strategy_json, author, category, tags, template_id,
                       created_at, updated_at, last_activated_at
                FROM strategies
                WHERE enabled = true
                ORDER BY strategy_name
            """

            rows = await conn.fetch(query)

            strategies = []
            for row in rows:
                strategy_data = json.loads(row['strategy_json'])
                strategy_data['id'] = row['id']
                strategy_data['created_at'] = row['created_at'].isoformat() if row['created_at'] else None
                strategy_data['updated_at'] = row['updated_at'].isoformat() if row['updated_at'] else None
                strategies.append(strategy_data)

            return strategies

        except Exception as e:
            raise StrategyStorageError(f"Failed to get enabled strategies: {e}")
        finally:
            if conn:
                await self._release_connection(conn)
