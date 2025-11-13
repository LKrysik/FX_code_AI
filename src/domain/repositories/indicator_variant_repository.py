"""
Indicator Variant Repository
============================

Repository for indicator variant CRUD operations with QuestDB persistence.

Responsibilities:
- Parameter validation against algorithm definitions
- Parameter encoding/decoding (JSON)
- Database operations (INSERT, UPDATE, soft DELETE, SELECT)
- Soft delete handling
- Type coercion and range validation

Architecture:
- Uses QuestDBProvider for database access
- Uses IndicatorAlgorithmRegistry for parameter validation
- Validates parameters at write time (fail fast)
- Trusts parameters at read time (already validated)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json
import uuid
import traceback

from ...data_feed.questdb_provider import QuestDBProvider
from ...domain.services.indicators.algorithm_registry import IndicatorAlgorithmRegistry
from ...domain.services.streaming_indicator_engine import IndicatorVariant
from ...domain.types.indicator_types import VariantParameter  # ✅ IMPORT FIX: VariantParameter is in types module
from ...core.logger import StructuredLogger, get_logger


class IndicatorVariantRepository:
    """
    Repository for indicator variant persistence in QuestDB.

    Implements CRUD operations with:
    - Parameter validation against algorithm definitions
    - Type coercion and range checking
    - Soft delete support
    - Transactional safety
    """

    def __init__(
        self,
        questdb_provider: QuestDBProvider,
        algorithm_registry: IndicatorAlgorithmRegistry,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize repository.

        Args:
            questdb_provider: QuestDB data provider for database access
            algorithm_registry: Algorithm registry for parameter validation
            logger: Structured logger (optional)
        """
        self.db = questdb_provider
        self.algorithms = algorithm_registry
        self.logger = logger or get_logger(__name__)

    # ========================================================================
    # CREATE
    # ========================================================================

    async def create_variant(self, variant_data: Dict[str, Any]) -> str:
        """
        Create new indicator variant with validation.

        Process:
        1. Generate UUID for variant
        2. Get algorithm definition
        3. Validate and encode parameters
        4. INSERT into database
        5. Return variant ID

        Args:
            variant_data: Variant configuration with keys:
                - name: str (required)
                - base_indicator_type: str (required)
                - variant_type: str (required)
                - description: str (optional)
                - parameters: Dict[str, Any] (required)
                - created_by: str (required)
                - user_id: str (optional, defaults to created_by)
                - scope: str (optional, defaults to "user_{user_id}")
                - is_system: bool (optional, defaults to False)

        Returns:
            Variant ID (UUID string)

        Raises:
            ValueError: If validation fails
            Exception: If database operation fails
        """
        # Generate variant ID
        variant_id = str(uuid.uuid4())

        # Extract fields with defaults
        name = variant_data['name']
        base_indicator_type = variant_data['base_indicator_type'].upper()
        variant_type = variant_data['variant_type']
        description = variant_data.get('description', '')
        parameters = variant_data['parameters']
        created_by = variant_data['created_by']
        user_id = variant_data.get('user_id', created_by)
        scope = variant_data.get('scope', f"user_{user_id}")
        is_system = variant_data.get('is_system', False)

        # Get algorithm for parameter validation
        algorithm = self.algorithms.get_algorithm(base_indicator_type)
        if not algorithm:
            raise ValueError(
                f"Unknown indicator type: {base_indicator_type}. "
                f"Available types: {list(self.algorithms.get_all_algorithms().keys())}"
            )

        # Validate and encode parameters
        parameters_json = self._encode_parameters(algorithm, parameters)

        # Prepare INSERT query
        # ✅ FORWARD-COMPATIBLE FIX: Explicit CAST to BOOLEAN for QuestDB compatibility
        # QuestDB PostgreSQL protocol requires explicit type casting for BOOLEAN values
        query = """
            INSERT INTO indicator_variants (
                id, name, base_indicator_type, variant_type, description,
                parameters, schema_version, is_system, created_by, user_id, scope,
                created_at, updated_at, is_deleted
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, CAST($8 AS BOOLEAN), $9, $10, $11, $12, $13, CAST($14 AS BOOLEAN))
        """

        # ✅ FIX: Convert timezone-aware datetime to naive UTC for QuestDB compatibility
        # QuestDB/asyncpg expects naive UTC datetimes for TIMESTAMP columns
        # Error was: "can't subtract offset-naive and offset-aware datetimes" in asyncpg codec
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        params = [
            variant_id,
            name,
            base_indicator_type,
            variant_type,
            description,
            parameters_json,
            1,  # schema_version
            is_system,  # Will be cast to BOOLEAN in query
            created_by,
            user_id,
            scope,
            now_utc,  # created_at - naive UTC datetime
            now_utc,  # updated_at - naive UTC datetime
            False  # is_deleted - Will be cast to BOOLEAN in query
        ]

        try:
            await self.db.initialize()
            async with self.db.pg_pool.acquire() as conn:
                await conn.execute(query, *params)

            self.logger.info("indicator_variant_repository.created", {
                "variant_id": variant_id,
                "name": name,
                "base_indicator_type": base_indicator_type,
                "variant_type": variant_type,
                "created_by": created_by
            })

            return variant_id

        except Exception as e:
            # ✅ IMPROVED: Log full traceback for debugging
            self.logger.error("indicator_variant_repository.create_failed", {
                "variant_id": variant_id,
                "name": name,
                "base_indicator_type": base_indicator_type,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            })
            raise

    # ========================================================================
    # READ
    # ========================================================================

    async def get_variant(self, variant_id: str) -> Optional[IndicatorVariant]:
        """
        Get variant by ID.

        Args:
            variant_id: Variant identifier (UUID)

        Returns:
            IndicatorVariant object or None if not found or deleted
        """
        query = """
            SELECT * FROM indicator_variants
            WHERE id = $1 AND is_deleted = false
        """

        try:
            await self.db.initialize()
            async with self.db.pg_pool.acquire() as conn:
                row = await conn.fetchrow(query, variant_id)

            if not row:
                return None

            return self._row_to_variant(row)

        except Exception as e:
            # ✅ IMPROVED: Log full traceback for debugging
            self.logger.error("indicator_variant_repository.get_failed", {
                "variant_id": variant_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            })
            raise

    async def list_variants(
        self,
        variant_type: Optional[str] = None,
        base_indicator_type: Optional[str] = None,
        scope: Optional[str] = None,
        user_id: Optional[str] = None,
        include_global: bool = True
    ) -> List[IndicatorVariant]:
        """
        List variants with optional filters.

        Args:
            variant_type: Filter by variant type (e.g., "general", "price")
            base_indicator_type: Filter by indicator type (e.g., "TWPA")
            scope: Filter by specific scope
            user_id: Filter by user ownership (includes global if include_global=True)
            include_global: Include global variants when filtering by user_id

        Returns:
            List of IndicatorVariant objects
        """
        # Build query with filters
        # ✅ FORWARD-COMPATIBLE: Simple BOOLEAN comparison (assumes correct types in database)
        # With explicit CAST in INSERT, is_deleted is always proper BOOLEAN type
        where_clauses = ["is_deleted = false"]
        params = []
        param_idx = 1

        if variant_type:
            where_clauses.append(f"variant_type = ${param_idx}")
            params.append(variant_type)
            param_idx += 1

        if base_indicator_type:
            where_clauses.append(f"base_indicator_type = ${param_idx}")
            params.append(base_indicator_type.upper())
            param_idx += 1

        if user_id:
            if include_global:
                where_clauses.append(f"(user_id = ${param_idx} OR scope = 'global')")
                params.append(user_id)
                param_idx += 1
            else:
                where_clauses.append(f"user_id = ${param_idx}")
                params.append(user_id)
                param_idx += 1
        elif scope:
            where_clauses.append(f"scope = ${param_idx}")
            params.append(scope)
            param_idx += 1

        query = f"""
            SELECT * FROM indicator_variants
            WHERE {' AND '.join(where_clauses)}
            ORDER BY created_at DESC
        """

        try:
            await self.db.initialize()
            async with self.db.pg_pool.acquire() as conn:
                rows = await conn.fetch(query, *params)

            variants = [self._row_to_variant(row) for row in rows]

            self.logger.debug("indicator_variant_repository.list", {
                "count": len(variants),
                "filters": {
                    "variant_type": variant_type,
                    "base_indicator_type": base_indicator_type,
                    "scope": scope,
                    "user_id": user_id
                }
            })

            return variants

        except Exception as e:
            # ✅ IMPROVED: Log full traceback for debugging
            self.logger.error("indicator_variant_repository.list_failed", {
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            })
            raise

    async def load_all_variants(self) -> List[IndicatorVariant]:
        """
        Load all active variants (for engine startup).

        Returns:
            List of all non-deleted IndicatorVariant objects
        """
        return await self.list_variants()

    # ========================================================================
    # UPDATE
    # ========================================================================

    async def update_variant(
        self,
        variant_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update variant fields.

        Supported updates:
        - name: str
        - description: str
        - parameters: Dict[str, Any] (will be validated)
        - scope: str

        Args:
            variant_id: Variant identifier
            updates: Dictionary of fields to update

        Returns:
            True if updated, False if variant not found

        Raises:
            ValueError: If parameter validation fails
        """
        # Get existing variant to validate against algorithm
        existing = await self.get_variant(variant_id)
        if not existing:
            return False

        # ✅ FIX: QuestDB doesn't support bind variables in UPDATE for TIMESTAMP
        # Build UPDATE query with literal timestamp
        set_clauses = []
        params = []
        param_idx = 1

        # Always update updated_at - use literal value for QuestDB compatibility
        # ✅ FIX: Convert to naive UTC for QuestDB compatibility
        updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        updated_at_str = updated_at.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        set_clauses.append(f"updated_at = '{updated_at_str}'")

        # Process updates
        if 'name' in updates:
            set_clauses.append(f"name = ${param_idx}")
            params.append(updates['name'])
            param_idx += 1

        if 'description' in updates:
            set_clauses.append(f"description = ${param_idx}")
            params.append(updates['description'])
            param_idx += 1

        if 'parameters' in updates:
            # Validate and encode parameters
            algorithm = self.algorithms.get_algorithm(existing.base_indicator_type)
            if not algorithm:
                raise ValueError(f"Algorithm not found: {existing.base_indicator_type}")

            parameters_json = self._encode_parameters(algorithm, updates['parameters'])
            set_clauses.append(f"parameters = ${param_idx}")
            params.append(parameters_json)
            param_idx += 1

        if 'scope' in updates:
            set_clauses.append(f"scope = ${param_idx}")
            params.append(updates['scope'])
            param_idx += 1

        # Add variant_id as last parameter
        params.append(variant_id)

        query = f"""
            UPDATE indicator_variants
            SET {', '.join(set_clauses)}
            WHERE id = ${param_idx} AND is_deleted = false
        """

        try:
            await self.db.initialize()
            async with self.db.pg_pool.acquire() as conn:
                result = await conn.execute(query, *params)

            # Check if any rows were updated
            updated = result.split()[-1] if result else "0"
            success = updated != "0"

            if success:
                self.logger.info("indicator_variant_repository.updated", {
                    "variant_id": variant_id,
                    "fields": list(updates.keys()),
                    "updated_at": updated_at_str
                })

            return success

        except Exception as e:
            # ✅ IMPROVED: Log full traceback for debugging
            self.logger.error("indicator_variant_repository.update_failed", {
                "variant_id": variant_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "query": query,
                "params_count": len(params)
            })
            raise

    # ========================================================================
    # DELETE
    # ========================================================================

    async def delete_variant(self, variant_id: str) -> bool:
        """
        Soft delete variant.

        Sets is_deleted=true and deleted_at=now() without physical deletion.

        Args:
            variant_id: Variant identifier

        Returns:
            True if deleted, False if variant not found
        """
        # ✅ FORWARD-COMPATIBLE FIX: Explicit CAST to BOOLEAN for type safety
        # QuestDB requires explicit type casting for BOOLEAN values in UPDATE
        # ✅ FIX: Convert to naive UTC for QuestDB compatibility
        deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        deleted_at_str = deleted_at.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        query = f"""
            UPDATE indicator_variants
            SET is_deleted = CAST(true AS BOOLEAN), deleted_at = '{deleted_at_str}'
            WHERE id = $1 AND is_deleted = false
        """

        try:
            await self.db.initialize()
            async with self.db.pg_pool.acquire() as conn:
                result = await conn.execute(query, variant_id)

            # Check if any rows were updated
            deleted = result.split()[-1] if result else "0"
            success = deleted != "0"

            if success:
                self.logger.info("indicator_variant_repository.deleted", {
                    "variant_id": variant_id,
                    "deleted_at": deleted_at_str
                })
            else:
                self.logger.warning("indicator_variant_repository.delete_not_found", {
                    "variant_id": variant_id
                })

            return success

        except Exception as e:
            # ✅ IMPROVED: Log full traceback for debugging
            self.logger.error("indicator_variant_repository.delete_failed", {
                "variant_id": variant_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "query": query
            })
            raise

    # ========================================================================
    # PARAMETER ENCODING/DECODING
    # ========================================================================

    def _encode_parameters(
        self,
        algorithm: Any,
        parameters: Dict[str, Any]
    ) -> str:
        """
        Validate and encode parameters to JSON string.

        Process:
        1. Get parameter definitions from algorithm
        2. Validate each parameter (type, range, required)
        3. Apply defaults for missing optional parameters
        4. Serialize to JSON

        Args:
            algorithm: IndicatorAlgorithm instance
            parameters: User-provided parameters

        Returns:
            JSON string (sorted keys for consistency)

        Raises:
            ValueError: If validation fails
        """
        # Get parameter definitions (source of truth)
        param_definitions = {p.name: p for p in algorithm.get_parameters()}

        validated_params = {}

        # Validate provided parameters
        for name, value in parameters.items():
            if name not in param_definitions:
                raise ValueError(
                    f"Unknown parameter '{name}' for {algorithm.get_indicator_type()}. "
                    f"Valid parameters: {list(param_definitions.keys())}"
                )

            param_def = param_definitions[name]

            # Validate and coerce type
            validated_value = self._validate_and_coerce(value, param_def)
            validated_params[name] = validated_value

        # Check required parameters
        for param_def in param_definitions.values():
            if param_def.name not in parameters:
                if param_def.is_required:
                    if param_def.default_value is not None:
                        # Use default
                        validated_params[param_def.name] = param_def.default_value
                    else:
                        raise ValueError(
                            f"Required parameter '{param_def.name}' is missing"
                        )

        # Serialize to JSON (sorted keys for consistency)
        return json.dumps(validated_params, sort_keys=True)

    def _validate_and_coerce(
        self,
        value: Any,
        param_def: VariantParameter
    ) -> Any:
        """
        Validate and coerce single parameter value.

        Args:
            value: Parameter value
            param_def: Parameter definition

        Returns:
            Coerced value (correct type)

        Raises:
            ValueError: If validation fails
        """
        param_type = param_def.parameter_type
        param_name = param_def.name

        # Type coercion
        try:
            if param_type == "int":
                value = int(value)
            elif param_type == "float":
                value = float(value)
            elif param_type == "boolean":
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
                else:
                    value = bool(value)
            elif param_type == "string":
                value = str(value)
            elif param_type == "json":
                if isinstance(value, str):
                    value = json.loads(value)
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            raise ValueError(
                f"Parameter '{param_name}': cannot convert '{value}' to {param_type}: {e}"
            )

        # Range validation (for numeric types)
        if param_type in ("int", "float"):
            if param_def.min_value is not None and value < param_def.min_value:
                raise ValueError(
                    f"Parameter '{param_name}': value {value} is below minimum {param_def.min_value}"
                )
            if param_def.max_value is not None and value > param_def.max_value:
                raise ValueError(
                    f"Parameter '{param_name}': value {value} exceeds maximum {param_def.max_value}"
                )

        # Enum validation
        if param_def.allowed_values is not None:
            if value not in param_def.allowed_values:
                raise ValueError(
                    f"Parameter '{param_name}': value '{value}' not in allowed values {param_def.allowed_values}"
                )

        return value

    def _decode_parameters(self, parameters_json: str) -> Dict[str, Any]:
        """
        Decode parameters from JSON string.

        Simple deserialization - validation already done at write time.

        Args:
            parameters_json: JSON string from database

        Returns:
            Parameters dictionary
        """
        if not parameters_json:
            return {}

        return json.loads(parameters_json)

    # ========================================================================
    # ROW MAPPING
    # ========================================================================

    def _row_to_variant(self, row: Any) -> IndicatorVariant:
        """
        Convert database row to IndicatorVariant object.

        Args:
            row: asyncpg.Record from database

        Returns:
            IndicatorVariant dataclass instance
        """
        parameters = self._decode_parameters(row['parameters'])

        return IndicatorVariant(
            id=row['id'],
            name=row['name'],
            base_indicator_type=row['base_indicator_type'],
            variant_type=row['variant_type'],
            description=row['description'] or '',
            parameters=parameters,
            is_system=row['is_system'],
            created_by=row['created_by'],
            created_at=row['created_at'].timestamp() if row['created_at'] else 0.0,
            updated_at=row['updated_at'].timestamp() if row['updated_at'] else 0.0
        )
