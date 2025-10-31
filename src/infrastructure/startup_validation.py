"""
Startup Validation - Fail-Fast System Health Checks
===================================================
Validates critical dependencies before application startup.
Provides clear error messages to guide users to solutions.

✅ ARCHITECTURAL FIX: Fail-fast validation prevents silent failures
and provides actionable error messages when dependencies are unavailable.

Usage:
    validator = StartupValidator(settings, logger)
    is_valid, errors = await validator.validate_all()
    if not is_valid:
        for error in errors:
            print(f"❌ {error}")
        sys.exit(1)
"""

import asyncio
from typing import List, Tuple, Optional
from ..core.logger import StructuredLogger


class StartupValidator:
    """
    Validates application dependencies and configuration before startup.

    Performs fail-fast checks to prevent running with missing or misconfigured
    dependencies, providing clear error messages to guide users.
    """

    def __init__(self, settings, logger: StructuredLogger):
        """
        Initialize startup validator.

        Args:
            settings: Application settings (AppSettings)
            logger: Structured logger instance
        """
        self.settings = settings
        self.logger = logger

    async def validate_all(self) -> Tuple[bool, List[str]]:
        """
        Run all startup validations.

        Returns:
            Tuple of (is_valid, error_messages)
            - is_valid: True if all validations passed
            - error_messages: List of error messages (empty if valid)
        """
        errors = []

        # 1. Validate QuestDB connectivity (CRITICAL)
        self.logger.info("startup_validation.checking_questdb")
        questdb_ok, questdb_errors = await self._validate_questdb()
        if not questdb_ok:
            errors.extend(questdb_errors)

        # 2. Validate configuration
        self.logger.info("startup_validation.checking_configuration")
        config_ok, config_errors = self._validate_configuration()
        if not config_ok:
            errors.extend(config_errors)

        # 3. Validate dependencies
        self.logger.info("startup_validation.checking_dependencies")
        deps_ok, deps_errors = self._validate_dependencies()
        if not deps_ok:
            errors.extend(deps_errors)

        is_valid = len(errors) == 0

        if is_valid:
            self.logger.info("startup_validation.passed", {
                "checks": ["questdb", "configuration", "dependencies"],
                "status": "all_passed"
            })
        else:
            self.logger.error("startup_validation.failed", {
                "error_count": len(errors),
                "errors": errors
            })

        return is_valid, errors

    async def _validate_questdb(self) -> Tuple[bool, List[str]]:
        """
        Validate QuestDB connectivity.

        ✅ CRITICAL: QuestDB is required for data collection and persistence.
        Tests both ILP (port 9009) and PostgreSQL (port 8812) connectivity.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            from ..data_feed.questdb_provider import QuestDBProvider

            # Create provider (no pool initialization yet)
            provider = QuestDBProvider(
                ilp_host='127.0.0.1',
                ilp_port=9009,
                pg_host='127.0.0.1',
                pg_port=8812
            )

            # Initialize connection pools
            await provider.initialize()

            # Run health check
            is_healthy = await provider.is_healthy()

            # Cleanup
            await provider.close()

            if not is_healthy:
                errors.append(
                    "QuestDB health check FAILED\n"
                    "  The database is not accepting connections.\n"
                    "  \n"
                    "  ⚠️  CRITICAL: QuestDB must be running for data collection.\n"
                    "  \n"
                    "  Solutions:\n"
                    "  1. On Windows: Run start_all.ps1 to start QuestDB\n"
                    "  2. Or start QuestDB manually:\n"
                    "     C:\\...\\questdb.exe\n"
                    "  3. Verify QuestDB is running:\n"
                    "     - Web UI: http://127.0.0.1:9000\n"
                    "     - ILP port: 127.0.0.1:9009\n"
                    "     - PostgreSQL port: 127.0.0.1:8812\n"
                    "  4. If not installed:\n"
                    "     - Download: https://questdb.io/download/\n"
                    "     - Extract and run questdb.exe"
                )
            else:
                self.logger.info("startup_validation.questdb_ok", {
                    "ilp_port": 9009,
                    "pg_port": 8812,
                    "status": "healthy"
                })

        except Exception as e:
            errors.append(
                f"QuestDB validation error: {str(e)}\n"
                f"  \n"
                f"  This usually means QuestDB is not running.\n"
                f"  Please start QuestDB before running the application.\n"
                f"  \n"
                f"  See instructions above for starting QuestDB."
            )
            self.logger.error("startup_validation.questdb_error", {
                "error": str(e),
                "error_type": type(e).__name__
            })

        return len(errors) == 0, errors

    def _validate_configuration(self) -> Tuple[bool, List[str]]:
        """
        Validate application configuration.

        Checks:
        - Trading mode requires symbols
        - Valid symbol format
        - Required configuration fields

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            # Check symbols for trading modes
            if self.settings.trading.mode.value != "collect":
                if not self.settings.trading.default_symbols:
                    errors.append(
                        f"Trading mode '{self.settings.trading.mode.value}' requires "
                        f"at least one symbol to be configured.\n"
                        f"  \n"
                        f"  Add symbols in configuration:\n"
                        f"  - Environment: TRADING__DEFAULT_SYMBOLS=BTC_USDT,ETH_USDT\n"
                        f"  - Or update src/infrastructure/config/settings.py"
                    )

            # Validate symbol format
            for symbol in self.settings.trading.default_symbols:
                if '_' not in symbol or len(symbol) < 3:
                    errors.append(
                        f"Invalid symbol format: '{symbol}'\n"
                        f"  Expected format: 'BASE_QUOTE' (e.g., 'BTC_USDT')"
                    )

            if len(errors) == 0:
                self.logger.info("startup_validation.configuration_ok", {
                    "trading_mode": self.settings.trading.mode.value,
                    "symbols": len(self.settings.trading.default_symbols)
                })

        except Exception as e:
            errors.append(f"Configuration validation error: {str(e)}")
            self.logger.error("startup_validation.configuration_error", {
                "error": str(e),
                "error_type": type(e).__name__
            })

        return len(errors) == 0, errors

    def _validate_dependencies(self) -> Tuple[bool, List[str]]:
        """
        Validate required Python dependencies.

        Checks:
        - questdb.ingress (ILP client)
        - asyncpg (PostgreSQL client)
        - pandas (data processing)

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        missing_deps = []

        # Check required dependencies
        required_deps = [
            ('questdb.ingress', 'questdb-connect'),
            ('asyncpg', 'asyncpg'),
            ('pandas', 'pandas'),
            ('pydantic', 'pydantic'),
            ('fastapi', 'fastapi')
        ]

        for import_name, package_name in required_deps:
            try:
                __import__(import_name)
            except ImportError:
                missing_deps.append(package_name)

        if missing_deps:
            deps_list = ', '.join(missing_deps)
            errors.append(
                f"Missing required dependencies: {deps_list}\n"
                f"  \n"
                f"  Install with: pip install {' '.join(missing_deps)}"
            )
        else:
            self.logger.info("startup_validation.dependencies_ok", {
                "checked": [dep[0] for dep in required_deps],
                "status": "all_found"
            })

        return len(errors) == 0, errors
