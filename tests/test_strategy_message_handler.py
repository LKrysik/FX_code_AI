"""
Unit tests for StrategyMessageHandler
======================================
Tests strategy management operations: list, activate, deactivate, status, validate, upsert.

Test coverage:
- Get strategies list
- Activate/deactivate strategies
- Get strategy status (single and all)
- Validate strategy configuration
- Upsert strategy configuration
- Symbol validation
- Error handling
"""

import pytest
import re
from unittest.mock import Mock, AsyncMock, mock_open, patch
from src.api.websocket.handlers import StrategyMessageHandler
from src.api.websocket.utils import ErrorHandler


class TestStrategyHandlerGetStrategies:
    """Test get strategies (handle_get_strategies)"""

    @pytest.mark.asyncio
    async def test_get_strategies_without_manager(self):
        """Test get strategies fails when strategy_manager not available"""
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=None,  # No manager
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        message = {}
        response = await handler.handle_get_strategies("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "service_unavailable"

    @pytest.mark.asyncio
    async def test_get_strategies_success(self):
        """Test successful get strategies"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Setup strategies list
        mock_strategy_manager.get_all_strategies.return_value = [
            {"strategy_name": "MovingAverageCross", "type": "trend"},
            {"strategy_name": "RSIStrategy", "type": "momentum"}
        ]

        message = {}
        response = await handler.handle_get_strategies("client", message)

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "strategies_list"
        assert len(response["strategies"]) == 2
        assert response["strategies"][0]["strategy_name"] == "MovingAverageCross"

    @pytest.mark.asyncio
    async def test_get_strategies_includes_session_id(self):
        """Test get strategies includes session_id when available"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        mock_strategy_manager.get_all_strategies.return_value = []
        mock_controller.get_execution_status.return_value = {"session_id": "session_123"}

        message = {}
        response = await handler.handle_get_strategies("client", message)

        # Verify session_id included
        assert response["session_id"] == "session_123"


class TestStrategyHandlerActivate:
    """Test activate strategy (handle_activate_strategy)"""

    @pytest.mark.asyncio
    async def test_activate_strategy_success(self):
        """Test successful strategy activation"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        # Create handler with symbol validation
        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler,
            symbol_pattern=re.compile(r'^[A-Z]{2,10}_[A-Z]{2,10}$'),
            allowed_symbols={"BTC_USDT", "ETH_USDT"}
        )

        # Setup activation success
        mock_strategy_manager.activate_strategy_for_symbol.return_value = True

        message = {
            "strategy_name": "MovingAverageCross",
            "symbol": "BTC_USDT"
        }
        response = await handler.handle_activate_strategy("client", message)

        # Verify call
        mock_strategy_manager.activate_strategy_for_symbol.assert_called_once_with(
            "MovingAverageCross", "BTC_USDT"
        )

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "strategy_activated"
        assert response["strategy_name"] == "MovingAverageCross"
        assert response["symbol"] == "BTC_USDT"

    @pytest.mark.asyncio
    async def test_activate_strategy_invalid_symbol_format(self):
        """Test activation fails for invalid symbol format"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler,
            symbol_pattern=re.compile(r'^[A-Z]{2,10}_[A-Z]{2,10}$'),
            allowed_symbols={"BTC_USDT"}
        )

        # Invalid symbol format
        message = {
            "strategy_name": "Strategy",
            "symbol": "invalid-symbol"
        }
        response = await handler.handle_activate_strategy("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "strategy_activation_failed"
        assert "Invalid symbol format" in response["error_message"]

    @pytest.mark.asyncio
    async def test_activate_strategy_unknown_symbol(self):
        """Test activation fails for unknown symbol"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler,
            symbol_pattern=re.compile(r'^[A-Z]{2,10}_[A-Z]{2,10}$'),
            allowed_symbols={"BTC_USDT"}  # Only BTC_USDT allowed
        )

        # Valid format but not allowed
        message = {
            "strategy_name": "Strategy",
            "symbol": "XRP_USDT"  # Not in allowed_symbols
        }
        response = await handler.handle_activate_strategy("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "strategy_activation_failed"
        assert "Unknown symbol" in response["error_message"]

    @pytest.mark.asyncio
    async def test_activate_strategy_missing_parameters(self):
        """Test activation fails for missing parameters"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler,
            allowed_symbols={"BTC_USDT"}
        )

        # Missing symbol
        message = {"strategy_name": "Strategy"}
        response = await handler.handle_activate_strategy("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "missing_parameters"


class TestStrategyHandlerDeactivate:
    """Test deactivate strategy (handle_deactivate_strategy)"""

    @pytest.mark.asyncio
    async def test_deactivate_strategy_success(self):
        """Test successful strategy deactivation"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Setup deactivation success
        mock_strategy_manager.deactivate_strategy_for_symbol.return_value = True

        message = {
            "strategy_name": "RSIStrategy",
            "symbol": "ETH_USDT"
        }
        response = await handler.handle_deactivate_strategy("client", message)

        # Verify call
        mock_strategy_manager.deactivate_strategy_for_symbol.assert_called_once_with(
            "RSIStrategy", "ETH_USDT"
        )

        # Verify response
        assert response["status"] == "strategy_deactivated"
        assert response["strategy_name"] == "RSIStrategy"

    @pytest.mark.asyncio
    async def test_deactivate_strategy_failure(self):
        """Test deactivation failure"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Setup deactivation failure
        mock_strategy_manager.deactivate_strategy_for_symbol.return_value = False

        message = {
            "strategy_name": "UnknownStrategy",
            "symbol": "BTC_USDT"
        }
        response = await handler.handle_deactivate_strategy("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "deactivation_failed"


class TestStrategyHandlerStatus:
    """Test get strategy status (handle_get_strategy_status)"""

    @pytest.mark.asyncio
    async def test_get_specific_strategy_status(self):
        """Test get status for specific strategy"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Setup strategy status
        mock_strategy_manager.get_strategy_status.return_value = {
            "current_state": "active",
            "symbol": "BTC_USDT"
        }

        message = {"strategy_name": "MovingAverageCross"}
        response = await handler.handle_get_strategy_status("client", message)

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "strategy_status"
        assert response["strategy_name"] == "MovingAverageCross"
        assert response["strategy_data"]["current_state"] == "active"

    @pytest.mark.asyncio
    async def test_get_all_strategies_status(self):
        """Test get status for all strategies"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Setup all strategies
        mock_strategy_manager.get_all_strategies.return_value = [
            {"strategy_name": "Strategy1"},
            {"strategy_name": "Strategy2"}
        ]
        mock_strategy_manager.get_strategy_status.side_effect = [
            {"current_state": "active"},
            {"current_state": "inactive"}
        ]

        message = {}  # No specific strategy_name
        response = await handler.handle_get_strategy_status("client", message)

        # Verify response
        assert response["status"] == "all_strategies_status"
        assert len(response["strategies"]) == 2

    @pytest.mark.asyncio
    async def test_get_strategy_status_not_found(self):
        """Test get status for non-existent strategy"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Strategy not found
        mock_strategy_manager.get_strategy_status.return_value = None

        message = {"strategy_name": "UnknownStrategy"}
        response = await handler.handle_get_strategy_status("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "strategy_not_found"


class TestStrategyHandlerValidate:
    """Test validate strategy config (handle_validate_strategy_config)"""

    @pytest.mark.asyncio
    @patch('src.api.websocket.handlers.strategy_handler.validate_strategy_config')
    async def test_validate_strategy_config_valid(self, mock_validate):
        """Test validate strategy config for valid configuration"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Setup validation success
        mock_validate.return_value = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        message = {
            "strategy_config": {
                "strategy_name": "MyStrategy",
                "parameters": {}
            }
        }
        response = await handler.handle_validate_strategy_config("client", message)

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "strategy_validation"
        assert response["valid"] is True
        assert response["errors"] == []

    @pytest.mark.asyncio
    @patch('src.api.websocket.handlers.strategy_handler.validate_strategy_config')
    async def test_validate_strategy_config_invalid(self, mock_validate):
        """Test validate strategy config for invalid configuration"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Setup validation failure
        mock_validate.return_value = {
            "valid": False,
            "errors": ["Missing required field: strategy_name"],
            "warnings": []
        }

        message = {"strategy_config": {}}
        response = await handler.handle_validate_strategy_config("client", message)

        # Verify response
        assert response["valid"] is False
        assert len(response["errors"]) > 0


class TestStrategyHandlerUpsert:
    """Test upsert strategy (handle_upsert_strategy)"""

    @pytest.mark.asyncio
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('src.api.websocket.handlers.strategy_handler.validate_strategy_config')
    async def test_upsert_strategy_success(self, mock_validate, mock_makedirs, mock_file):
        """Test successful strategy upsert"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Setup validation success
        mock_validate.return_value = {"valid": True}

        # Setup strategy creation
        mock_strategy = Mock()
        mock_strategy_manager.create_strategy_from_config.return_value = mock_strategy

        message = {
            "strategy_config": {
                "strategy_name": "NewStrategy",
                "parameters": {}
            }
        }
        response = await handler.handle_upsert_strategy("client", message)

        # Verify file operations
        mock_makedirs.assert_called_once()
        mock_file.assert_called_once()

        # Verify strategy manager operations
        mock_strategy_manager.create_strategy_from_config.assert_called_once()
        mock_strategy_manager.add_strategy.assert_called_once_with(mock_strategy)

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "strategy_upserted"
        assert response["strategy_name"] == "NewStrategy"

    @pytest.mark.asyncio
    async def test_upsert_strategy_missing_name(self):
        """Test upsert fails for missing strategy_name"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Missing strategy_name
        message = {"strategy_config": {}}
        response = await handler.handle_upsert_strategy("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "validation_error"

    @pytest.mark.asyncio
    @patch('src.api.websocket.handlers.strategy_handler.validate_strategy_config')
    async def test_upsert_strategy_validation_failure(self, mock_validate):
        """Test upsert fails for invalid configuration"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Setup validation failure
        mock_validate.return_value = {
            "valid": False,
            "errors": ["Invalid parameter"]
        }

        message = {
            "strategy_config": {
                "strategy_name": "InvalidStrategy"
            }
        }
        response = await handler.handle_upsert_strategy("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "validation_error"


class TestStrategyHandlerEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_activate_with_lowercase_symbol(self):
        """Test activation converts symbol to uppercase"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler,
            allowed_symbols={"BTC_USDT"}
        )

        mock_strategy_manager.activate_strategy_for_symbol.return_value = True

        # Lowercase symbol
        message = {
            "strategy_name": "Strategy",
            "symbol": "btc_usdt"  # lowercase
        }
        response = await handler.handle_activate_strategy("client", message)

        # Verify uppercase conversion
        mock_strategy_manager.activate_strategy_for_symbol.assert_called_with(
            "Strategy", "BTC_USDT"
        )

    @pytest.mark.asyncio
    async def test_session_id_safe_extraction(self):
        """Test safe session ID extraction handles errors"""
        mock_strategy_manager = Mock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = StrategyMessageHandler(
            strategy_manager=mock_strategy_manager,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Controller raises exception
        mock_controller.get_execution_status.side_effect = Exception("Controller error")

        # Should return None without raising
        session_id = handler._get_session_id_safe()
        assert session_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
