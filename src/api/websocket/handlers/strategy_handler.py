"""
StrategyMessageHandler - Strategy Management Operations
=======================================================
Handles strategy lifecycle: list, activate, deactivate, status, validate, upsert.

Responsibilities:
- List available strategies
- Activate/deactivate strategies for symbols
- Query strategy status
- Validate strategy configurations
- Create/update strategy configurations (upsert)

Extracted from WebSocketAPIServer (lines 1415-1779)
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, Set
import re
from src.api.websocket.utils import ErrorHandler


class StrategyMessageHandler:
    """
    Handles strategy management messages.

    Strategy operations:
    - GET_STRATEGIES: List all available strategies
    - ACTIVATE_STRATEGY: Activate strategy for symbol
    - DEACTIVATE_STRATEGY: Deactivate strategy for symbol
    - GET_STRATEGY_STATUS: Query strategy status
    - VALIDATE_STRATEGY_CONFIG: Validate configuration (no side effects)
    - UPSERT_STRATEGY: Create or update strategy configuration

    Dependencies:
    - strategy_manager: For strategy operations
    - controller: For session context (optional)
    - error_handler: For standardized error responses
    - symbol_validator: Regex pattern and allowed symbols for validation
    """

    def __init__(self,
                 strategy_manager,
                 controller,
                 error_handler: ErrorHandler,
                 symbol_pattern: Optional[re.Pattern] = None,
                 allowed_symbols: Optional[Set[str]] = None,
                 logger = None):
        """
        Initialize strategy handler.

        Args:
            strategy_manager: StrategyManager for strategy operations
            controller: Trading controller for session context
            error_handler: ErrorHandler for standardized errors
            symbol_pattern: Pre-compiled regex for symbol validation
            allowed_symbols: Set of allowed trading symbols
            logger: Optional logger for diagnostics
        """
        self.strategy_manager = strategy_manager
        self.controller = controller
        self.error_handler = error_handler
        self.symbol_pattern = symbol_pattern or re.compile(r'^[A-Z]{2,10}_[A-Z]{2,10}$')
        self.allowed_symbols = allowed_symbols or set()
        self.logger = logger

    def _get_session_id_safe(self) -> Optional[str]:
        """
        Safely extract session ID from controller.

        Returns:
            Session ID if available, None otherwise
        """
        try:
            if self.controller:
                sess = self.controller.get_execution_status()
                if isinstance(sess, dict) and sess.get("session_id"):
                    return sess.get("session_id")
        except Exception:
            pass
        return None

    async def handle_get_strategies(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle get strategies list request.

        Message format:
        {
            "type": "get_strategies"
        }

        Success response:
        {
            "type": "response",
            "status": "strategies_list",
            "strategies": [
                {"strategy_name": "MovingAverageCross", ...},
                {"strategy_name": "RSIStrategy", ...}
            ],
            "session_id": "session_abc123",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Get strategies message

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:1415-1484 (_handle_get_strategies)
        """
        session_id = self._get_session_id_safe()

        if not self.strategy_manager:
            return {
                "type": "error",
                "error_code": "service_unavailable",
                "error_message": "Strategy manager not available",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

        try:
            strategies = self.strategy_manager.get_all_strategies()

            return {
                "type": "response",
                "status": "strategies_list",
                "strategies": strategies,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

        except (AttributeError, TypeError) as e:
            if self.logger:
                self.logger.debug("websocket_strategy.strategies_retrieval_error", {
                    "error": str(e),
                    "client_id": client_id
                })
            return {
                "type": "error",
                "error_code": "strategies_retrieval_failed",
                "error_message": f"Strategy manager access error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            if self.logger:
                self.logger.error("websocket_strategy.strategies_retrieval_unexpected", {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "client_id": client_id
                })
            return {
                "type": "error",
                "error_code": "strategies_retrieval_failed",
                "error_message": f"Unexpected error retrieving strategies: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    async def handle_activate_strategy(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle activate strategy request.

        Message format:
        {
            "type": "activate_strategy",
            "strategy_name": "MovingAverageCross",
            "symbol": "BTC_USDT"
        }

        Success response:
        {
            "type": "response",
            "status": "strategy_activated",
            "strategy_name": "MovingAverageCross",
            "symbol": "BTC_USDT",
            "session_id": "session_abc123",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Activate strategy message

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:1486-1560 (_handle_activate_strategy)
        """
        session_id = self._get_session_id_safe()

        if not self.strategy_manager:
            return {
                "type": "error",
                "error_code": "service_unavailable",
                "error_message": "Strategy manager not available",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

        strategy_name = message.get("strategy_name")
        symbol = message.get("symbol", "").upper()

        # Validate symbol format
        if not symbol or not self.symbol_pattern.match(symbol):
            return {
                "type": "error",
                "error_code": "strategy_activation_failed",
                "error_message": f"Invalid symbol format: {symbol}",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

        # Validate symbol is allowed
        if symbol not in self.allowed_symbols:
            return {
                "type": "error",
                "error_code": "strategy_activation_failed",
                "error_message": f"Unknown symbol: {symbol}",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

        # Validate required parameters
        if not strategy_name or not symbol:
            return {
                "type": "error",
                "error_code": "missing_parameters",
                "error_message": "strategy_name and symbol are required",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

        try:
            success = self.strategy_manager.activate_strategy_for_symbol(strategy_name, symbol)

            if success:
                return {
                    "type": "response",
                    "status": "strategy_activated",
                    "strategy_name": strategy_name,
                    "symbol": symbol,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "type": "error",
                    "error_code": "strategy_activation_failed",
                    "error_message": f"Failed to activate {strategy_name} for {symbol}",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            return {
                "type": "error",
                "error_code": "strategy_activation_failed",
                "error_message": str(e),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

    async def handle_deactivate_strategy(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle deactivate strategy request.

        Message format:
        {
            "type": "deactivate_strategy",
            "strategy_name": "MovingAverageCross",
            "symbol": "BTC_USDT"
        }

        Success response:
        {
            "type": "response",
            "status": "strategy_deactivated",
            "strategy_name": "MovingAverageCross",
            "symbol": "BTC_USDT",
            "session_id": "session_abc123",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Deactivate strategy message

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:1562-1617 (_handle_deactivate_strategy)
        """
        session_id = self._get_session_id_safe()

        if not self.strategy_manager:
            return {
                "type": "error",
                "error_code": "service_unavailable",
                "error_message": "Strategy manager not available",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

        strategy_name = message.get("strategy_name")
        symbol = message.get("symbol", "").upper()

        # Validate required parameters
        if not strategy_name or not symbol:
            return {
                "type": "error",
                "error_code": "missing_parameters",
                "error_message": "strategy_name and symbol are required",
                "timestamp": datetime.now().isoformat()
            }

        try:
            success = self.strategy_manager.deactivate_strategy_for_symbol(strategy_name, symbol)

            if success:
                return {
                    "type": "response",
                    "status": "strategy_deactivated",
                    "strategy_name": strategy_name,
                    "symbol": symbol,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "type": "error",
                    "error_code": "deactivation_failed",
                    "error_message": f"Failed to deactivate {strategy_name} for {symbol}",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            return {
                "type": "error",
                "error_code": "deactivation_error",
                "error_message": str(e),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

    async def handle_get_strategy_status(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle get strategy status request.

        Message format (specific strategy):
        {
            "type": "get_strategy_status",
            "strategy_name": "MovingAverageCross",
            "symbol": "BTC_USDT"  // optional
        }

        Message format (all strategies):
        {
            "type": "get_strategy_status"
        }

        Args:
            client_id: Unique client identifier
            message: Get strategy status message

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:1619-1706 (_handle_get_strategy_status)
        """
        if not self.strategy_manager:
            return {
                "type": "error",
                "error_code": "service_unavailable",
                "error_message": "Strategy manager not available",
                "timestamp": datetime.now().isoformat()
            }

        try:
            strategy_name = message.get("strategy_name")
            symbol = (message.get("symbol") or "").upper() if message.get("symbol") else None

            # If specific strategy requested
            if strategy_name:
                status = self.strategy_manager.get_strategy_status(strategy_name)

                if status:
                    # Optional symbol check when provided
                    if symbol and status.get("symbol") and status.get("symbol") != symbol:
                        return {
                            "type": "error",
                            "error_code": "strategy_not_found",
                            "error_message": f"No status for {strategy_name} on {symbol}",
                            "timestamp": datetime.now().isoformat()
                        }

                    session_id = self._get_session_id_safe()

                    return {
                        "type": "response",
                        "status": "strategy_status",
                        "strategy_name": strategy_name,
                        "symbol": symbol,
                        "strategy_data": status,
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "type": "error",
                        "error_code": "strategy_not_found",
                        "error_message": f"Strategy {strategy_name} not found",
                        "timestamp": datetime.now().isoformat()
                    }

            # Otherwise, return all strategies status
            strategies = []
            try:
                all_defs = self.strategy_manager.get_all_strategies() or []
                names = [
                    s.get("strategy_name")
                    for s in all_defs
                    if isinstance(s, dict) and s.get("strategy_name")
                ]

                for name in names:
                    st = self.strategy_manager.get_strategy_status(name)
                    if st:
                        strategies.append({"strategy_name": name, **st})

            except (json.JSONDecodeError, ValueError) as e:
                if self.logger:
                    self.logger.debug("websocket_strategy.json_parsing_error", {
                        "client_id": client_id,
                        "error": str(e)
                    })
            except Exception as e:
                if self.logger:
                    self.logger.warning("websocket_strategy.status_collection_error", {
                        "client_id": client_id,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })

            return {
                "type": "response",
                "status": "all_strategies_status",
                "strategies": strategies,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "type": "error",
                "error_code": "strategy_status_error",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def handle_validate_strategy_config(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle validate strategy configuration request (no side effects).

        Message format:
        {
            "type": "validate_strategy_config",
            "strategy_config": {
                "strategy_name": "MyStrategy",
                ...configuration fields...
            }
        }

        Response:
        {
            "type": "response",
            "status": "strategy_validation",
            "valid": true,
            "errors": [],
            "warnings": [],
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Validate strategy config message

        Returns:
            Response dict with validation results

        Original location: websocket_server.py:1708-1720 (_handle_validate_strategy_config)
        """
        from src.domain.services.strategy_schema import validate_strategy_config

        cfg = message.get("strategy_config") or {}
        result = validate_strategy_config(cfg if isinstance(cfg, dict) else {})

        return {
            "type": "response",
            "status": "strategy_validation",
            "valid": result.get("valid", False),
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
            "timestamp": datetime.now().isoformat()
        }

    async def handle_upsert_strategy(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle upsert (create or update) strategy configuration.

        Creates/updates strategy configuration file and loads into StrategyManager.

        Message format:
        {
            "type": "upsert_strategy",
            "strategy_config": {
                "strategy_name": "MyStrategy",
                ...configuration fields...
            }
        }

        Success response:
        {
            "type": "response",
            "status": "strategy_upserted",
            "strategy_name": "MyStrategy",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Upsert strategy message

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:1722-1779 (_handle_upsert_strategy)
        """
        if not self.strategy_manager:
            return {
                "type": "error",
                "error_code": "service_unavailable",
                "error_message": "Strategy manager not available",
                "timestamp": datetime.now().isoformat()
            }

        cfg = message.get("strategy_config") or {}

        # Validate config structure
        if not isinstance(cfg, dict) or not cfg.get("strategy_name"):
            return {
                "type": "error",
                "error_code": "validation_error",
                "error_message": "strategy_config with non-empty strategy_name is required",
                "timestamp": datetime.now().isoformat()
            }

        # Validate configuration
        from src.domain.services.strategy_schema import validate_strategy_config
        result = validate_strategy_config(cfg)

        if not result.get("valid"):
            return {
                "type": "error",
                "error_code": "validation_error",
                "error_message": f"Invalid strategy_config: {result.get('errors')}",
                "timestamp": datetime.now().isoformat()
            }

        # Persist to config/strategies
        try:
            os.makedirs(os.path.join("config", "strategies"), exist_ok=True)
            path = os.path.join("config", "strategies", f"{cfg['strategy_name']}.json")

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)

        except Exception as e:
            return {
                "type": "error",
                "error_code": "command_failed",
                "error_message": f"Failed to persist strategy: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

        # Update StrategyManager in-memory
        try:
            strategy = self.strategy_manager.create_strategy_from_config(cfg)
            self.strategy_manager.add_strategy(strategy)

            return {
                "type": "response",
                "status": "strategy_upserted",
                "strategy_name": cfg["strategy_name"],
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "type": "error",
                "error_code": "command_failed",
                "error_message": f"Failed to load strategy: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
