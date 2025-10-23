"""
Strategy Storage - File-based persistence for trading strategies
===============================================================
Implements atomic file operations with UUID-based storage per ADR-002.
Handles concurrent access, schema validation, and backup management.
"""

import uuid
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError
from contextlib import asynccontextmanager
import os
import tempfile
import shutil


class StrategyConfig(BaseModel):
    """Pydantic model for strategy JSON serialization"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_name: str
    enabled: bool = True

    # 5-section strategy configuration (using frontend naming convention)
    s1_signal: Dict[str, Any] = Field(default_factory=lambda: {"conditions": []})
    z1_entry: Dict[str, Any] = Field(default_factory=lambda: {
        "conditions": [],
        "timeoutSeconds": 300,
        "positionSize": {"type": "percent", "value": 0.5},
        "stopLoss": {"enabled": False, "offsetPercent": 1.5},
        "takeProfit": {"enabled": False, "offsetPercent": 3.0}
    })
    o1_cancel: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False,
        "timeoutEnabled": False,
        "timeoutSeconds": 300,
        "conditions": [],
        "cooldownMinutes": 5
    })
    ze1_close: Dict[str, Any] = Field(default_factory=lambda: {
        "conditions": [],
        "closeMethod": "market"
    })
    emergency_exit: Dict[str, Any] = Field(default_factory=lambda: {
        "conditions": [],
        "cooldownMinutes": 15
    })

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = None
    version: str = "1.0"

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class StrategyStorageError(Exception):
    """Base exception for strategy storage operations"""
    pass


class StrategyNotFoundError(StrategyStorageError):
    """Raised when strategy is not found"""
    pass


class StrategyValidationError(StrategyStorageError):
    """Raised when strategy validation fails"""
    pass


class StrategyStorage:
    """
    File-based storage for trading strategies with atomic operations.
    Implements ADR-002: File-Based Configuration Storage.
    """

    def __init__(self, storage_path: Union[str, Path] = "config/strategies"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def create_strategy(self, strategy_data: Dict[str, Any]) -> str:
        """
        Create a new strategy with UUID assignment.
        Returns the generated UUID.
        """
        try:
            # Generate UUID
            strategy_id = str(uuid.uuid4())

            # Prepare strategy config
            config_data = strategy_data.copy()
            config_data["id"] = strategy_id
            config_data["created_at"] = datetime.now()
            config_data["updated_at"] = datetime.now()
            config_data["version"] = "1.0"

            # Validate with Pydantic
            strategy_config = StrategyConfig(**config_data)

            # Save atomically
            await self._save_strategy_atomic(strategy_config)

            return strategy_id

        except ValidationError as e:
            raise StrategyValidationError(f"Invalid strategy data: {e}")
        except Exception as e:
            raise StrategyStorageError(f"Failed to create strategy: {e}")

    async def read_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """
        Read strategy by UUID.
        Raises StrategyNotFoundError if not found.
        """
        file_path = self.storage_path / f"{strategy_id}.json"

        try:
            if not file_path.exists():
                raise StrategyNotFoundError(f"Strategy {strategy_id} not found")

            async with self._file_lock_context(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Validate loaded data
                strategy_config = StrategyConfig(**data)
                return strategy_config.model_dump(mode='json')

        except json.JSONDecodeError as e:
            raise StrategyValidationError(f"Invalid JSON in strategy file: {e}")
        except ValidationError as e:
            raise StrategyValidationError(f"Invalid strategy data: {e}")
        except Exception as e:
            raise StrategyStorageError(f"Failed to read strategy {strategy_id}: {e}")

    async def update_strategy(self, strategy_id: str, strategy_data: Dict[str, Any]) -> None:
        """
        Update existing strategy.
        Creates backup before updating.
        """
        try:
            # Read existing strategy
            existing = await self.read_strategy(strategy_id)

            # Create backup
            await self._create_backup(strategy_id, existing)

            # Prepare updated data
            updated_data = strategy_data.copy()
            updated_data["id"] = strategy_id
            updated_data["created_at"] = existing.get("created_at", datetime.now())
            updated_data["updated_at"] = datetime.now()
            updated_data["version"] = existing.get("version", "1.0")

            # Validate
            strategy_config = StrategyConfig(**updated_data)

            # Save atomically
            await self._save_strategy_atomic(strategy_config)

        except StrategyNotFoundError:
            raise
        except ValidationError as e:
            raise StrategyValidationError(f"Invalid strategy data: {e}")
        except Exception as e:
            raise StrategyStorageError(f"Failed to update strategy {strategy_id}: {e}")

    async def delete_strategy(self, strategy_id: str) -> None:
        """
        Delete strategy by UUID.
        """
        file_path = self.storage_path / f"{strategy_id}.json"

        try:
            if not file_path.exists():
                raise StrategyNotFoundError(f"Strategy {strategy_id} not found")

            # Remove file
            file_path.unlink()

        except Exception as e:
            raise StrategyStorageError(f"Failed to delete strategy {strategy_id}: {e}")

    async def list_strategies(self) -> List[Dict[str, Any]]:
        """
        List all strategies with basic metadata.
        """
        strategies = []

        try:
            for file_path in self.storage_path.glob("*.json"):
                try:
                    strategy_id = file_path.stem
                    strategy_data = await self.read_strategy(strategy_id)

                    # Return summary
                    strategies.append({
                        "id": strategy_data["id"],
                        "strategy_name": strategy_data["strategy_name"],
                        "enabled": strategy_data["enabled"],
                        "created_at": strategy_data["created_at"],
                        "updated_at": strategy_data["updated_at"]
                    })

                except Exception:
                    # Skip invalid files but continue
                    continue

            return strategies

        except Exception as e:
            raise StrategyStorageError(f"Failed to list strategies: {e}")

    async def _save_strategy_atomic(self, strategy_config: StrategyConfig) -> None:
        """
        Save strategy atomically using temporary file + rename.
        """
        strategy_id = strategy_config.id
        file_path = self.storage_path / f"{strategy_id}.json"
        temp_path = self.storage_path / f"{strategy_id}.tmp"

        try:
            # Write to temporary file first - use Pydantic v2's model_dump_json() which handles datetime serialization
            with open(temp_path, 'w', encoding='utf-8') as f:
                json_data = strategy_config.model_dump_json(indent=2)
                f.write(json_data)

            # Atomic rename
            temp_path.replace(file_path)

        except Exception:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise

    async def _create_backup(self, strategy_id: str, strategy_data: Dict[str, Any]) -> None:
        """
        Create backup of existing strategy before update.
        """
        file_path = self.storage_path / f"{strategy_id}.json"
        backup_path = self.storage_path / f"{strategy_id}.backup"

        try:
            shutil.copy2(file_path, backup_path)
        except Exception:
            # Backup failure shouldn't block update
            pass

    @asynccontextmanager
    async def _file_lock_context(self, file_path: Path):
        """
        Simple file locking context manager.
        Uses basic file existence check for now.
        """
        lock_path = file_path.with_suffix('.lock')

        # Simple spin lock with timeout
        import asyncio
        timeout = 5.0
        start_time = asyncio.get_event_loop().time()

        while lock_path.exists():
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise StrategyStorageError(f"File lock timeout for {file_path}")
            await asyncio.sleep(0.01)

        try:
            # Create lock file
            lock_path.touch()
            yield
        finally:
            # Remove lock file
            try:
                lock_path.unlink(missing_ok=True)
            except Exception:
                pass

    async def validate_strategy_data(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate strategy data without saving.
        Returns validation result.
        """
        try:
            StrategyConfig(**strategy_data)
            return {"valid": True, "errors": []}
        except ValidationError as e:
            return {"valid": False, "errors": [str(error) for error in e.errors()]}

    async def migrate_strategy_if_needed(self, strategy_id: str) -> None:
        """
        Handle schema migrations for existing strategies.
        """
        # For now, just validate and update version if needed
        try:
            strategy_data = await self.read_strategy(strategy_id)
            if strategy_data.get("version", "1.0") != "1.0":
                # Apply migrations here in future
                strategy_data["version"] = "1.0"
                await self.update_strategy(strategy_id, strategy_data)
        except Exception:
            # Migration failures shouldn't break reads
            pass