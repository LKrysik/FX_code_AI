"""
Message Router
==============
Routes WebSocket messages between clients and backend with validation and error handling.
Production-ready with comprehensive message type support and security validation.
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import time
import re
from concurrent.futures import ThreadPoolExecutor

from ..core.logger import StructuredLogger
from .command_handler import CommandHandler


class MessageType(str, Enum):
    """Supported WebSocket message types"""

    # Client -> Server
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    COMMAND = "command"
    QUERY = "query"
    HEARTBEAT = "heartbeat"
    AUTH = "auth"

    # Server -> Client
    DATA = "data"
    SIGNAL = "signal"
    ALERT = "alert"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"

    # Session Management
    SESSION_START = "session_start"
    SESSION_STOP = "session_stop"
    SESSION_STATUS = "session_status"

    # Data Collection
    COLLECTION_START = "collection_start"
    COLLECTION_STOP = "collection_stop"
    COLLECTION_STATUS = "collection_status"

    # Results
    RESULTS_REQUEST = "results_request"

    # Strategy Management
    GET_STRATEGIES = "get_strategies"
    ACTIVATE_STRATEGY = "activate_strategy"
    DEACTIVATE_STRATEGY = "deactivate_strategy"
    GET_STRATEGY_STATUS = "get_strategy_status"
    VALIDATE_STRATEGY_CONFIG = "validate_strategy_config"
    UPSERT_STRATEGY = "upsert_strategy"
    HANDSHAKE = "handshake"


class MessagePriority(Enum):
    """Message processing priority levels"""

    CRITICAL = 1    # Trading orders, emergency commands
    HIGH = 2        # Real-time data, important signals
    NORMAL = 3      # Regular subscriptions, queries
    LOW = 4         # Heartbeats, status updates


@dataclass
class MessageValidationResult:
    """Result of message validation"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_message: Optional[Dict[str, Any]] = None


class MessageValidator:
    """Validates incoming WebSocket messages"""

    def __init__(self):
        # Message schema definitions
        self.schemas = {
            MessageType.SUBSCRIBE: {
                "required": ["type", "stream"],
                "properties": {
                    "type": {"enum": [MessageType.SUBSCRIBE]},
                    "stream": {"type": "string", "max_length": 100},
                    "params": {"type": "object"},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.UNSUBSCRIBE: {
                "required": ["type", "stream"],
                "properties": {
                    "type": {"enum": [MessageType.UNSUBSCRIBE]},
                    "stream": {"type": "string", "max_length": 100},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.COMMAND: {
                "required": ["type", "action"],
                "properties": {
                    "type": {"enum": [MessageType.COMMAND]},
                    "action": {"type": "string", "max_length": 50},
                    "params": {"type": "object"},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.QUERY: {
                "required": ["type", "query_type"],
                "properties": {
                    "type": {"enum": [MessageType.QUERY]},
                    "query_type": {"type": "string", "max_length": 50},
                    "params": {"type": "object"},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.HEARTBEAT: {
                "required": ["type"],
                "properties": {
                    "type": {"enum": [MessageType.HEARTBEAT]},
                    # Allow both string and number timestamps for flexibility
                    "timestamp": {"type": ["number", "string"]}
                }
            },
            MessageType.AUTH: {
                "required": ["type", "token"],
                "properties": {
                    "type": {"enum": [MessageType.AUTH]},
                    "token": {"type": "string", "max_length": 1000}
                }
            },
            MessageType.SESSION_START: {
                "required": ["type", "session_type", "strategy_config"],
                "properties": {
                    "type": {"enum": [MessageType.SESSION_START]},
                    "session_type": {"enum": ["backtest", "live", "paper"]},
                    "strategy_config": {
                        "type": "object",
                        "description": "Strategy-to-symbols mapping: {'strategy_name': ['SYMBOL1', 'SYMBOL2']}"
                    },
                    "config": {"type": "object"},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.SESSION_STOP: {
                "required": ["type", "session_id"],
                "properties": {
                    "type": {"enum": [MessageType.SESSION_STOP]},
                    "session_id": {"type": "string", "max_length": 50},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.SESSION_STATUS: {
                "required": ["type", "session_id"],
                "properties": {
                    "type": {"enum": [MessageType.SESSION_STATUS]},
                    "session_id": {"type": "string", "max_length": 50},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.COLLECTION_START: {
                "required": ["type", "symbols"],
                "properties": {
                    "type": {"enum": [MessageType.COLLECTION_START]},
                    "symbols": {"type": "array", "max_items": 100},
                    "duration": {"type": "string", "max_length": 20},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.COLLECTION_STOP: {
                "required": ["type", "collection_id"],
                "properties": {
                    "type": {"enum": [MessageType.COLLECTION_STOP]},
                    "collection_id": {"type": "string", "max_length": 50},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.RESULTS_REQUEST: {
                "required": ["type", "request_type"],
                "properties": {
                    "type": {"enum": [MessageType.RESULTS_REQUEST]},
                    "request_type": {"enum": ["session_results", "symbol_results", "strategy_results", "collection_list"]},
                    "session_id": {"type": "string", "max_length": 50},
                    "symbol": {"type": "string", "max_length": 20},
                    "strategy": {"type": "string", "max_length": 50},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            # Strategy management schemas
            MessageType.GET_STRATEGIES: {
                "required": ["type"],
                "properties": {
                    "type": {"enum": [MessageType.GET_STRATEGIES]},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.ACTIVATE_STRATEGY: {
                "required": ["type", "strategy_name", "symbol"],
                "properties": {
                    "type": {"enum": [MessageType.ACTIVATE_STRATEGY]},
                    "strategy_name": {"type": "string", "max_length": 100},
                    "symbol": {"type": "string", "max_length": 50},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.DEACTIVATE_STRATEGY: {
                "required": ["type", "strategy_name", "symbol"],
                "properties": {
                    "type": {"enum": [MessageType.DEACTIVATE_STRATEGY]},
                    "strategy_name": {"type": "string", "max_length": 100},
                    "symbol": {"type": "string", "max_length": 50},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.GET_STRATEGY_STATUS: {
                "required": ["type"],
                "properties": {
                    "type": {"enum": [MessageType.GET_STRATEGY_STATUS]},
                    "strategy_name": {"type": "string", "max_length": 100},
                    "symbol": {"type": "string", "max_length": 50},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.VALIDATE_STRATEGY_CONFIG: {
                "required": ["type", "strategy_config"],
                "properties": {
                    "type": {"enum": [MessageType.VALIDATE_STRATEGY_CONFIG]},
                    "strategy_config": {"type": "object"},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.UPSERT_STRATEGY: {
                "required": ["type", "strategy_config"],
                "properties": {
                    "type": {"enum": [MessageType.UPSERT_STRATEGY]},
                    "strategy_config": {"type": "object"},
                    "id": {"type": "string", "max_length": 50}
                }
            },
            MessageType.HANDSHAKE: {
                "required": ["type", "version", "client_id", "capabilities"],
                "properties": {
                    "type": {"enum": [MessageType.HANDSHAKE]},
                    "version": {"type": "string"},
                    "client_id": {"type": "string", "max_length": 100},
                    "capabilities": {"type": "array"},
                    "id": {"type": "string", "max_length": 50}
                }
            }
        }

        # Security patterns for input sanitization - pre-compiled for performance
        self.dangerous_patterns = [
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE), # Script tags
            re.compile(r'javascript:', re.IGNORECASE),                # JavaScript URLs
            re.compile(r'on\w+\s*=', re.IGNORECASE),                  # Event handlers
            re.compile(r'vbscript:', re.IGNORECASE),                  # VBScript
            re.compile(r'data:text/html', re.IGNORECASE),             # Data URLs
        ]

        # ✅ PERFORMANCE FIX: Pre-compile symbol validation regex
        self._symbol_pattern = re.compile(r'^[A-Z0-9_]+$')

    def validate_message(self, message: Dict[str, Any]) -> MessageValidationResult:
        """
        Validate message format and content.

        Args:
            message: Raw message dictionary

        Returns:
            Validation result with errors, warnings, and sanitized message
        """
        errors = []
        warnings = []
        sanitized = message.copy()

        # Basic structure validation
        if not isinstance(message, dict):
            errors.append("Message must be a JSON object")
            return MessageValidationResult(False, errors, warnings)

        # Check message type
        msg_type = message.get("type")
        if not msg_type:
            errors.append("Message must have 'type' field")
            return MessageValidationResult(False, errors, warnings)

        if msg_type not in [mt.value for mt in MessageType]:
            errors.append(f"Unknown message type: {msg_type}")
            return MessageValidationResult(False, errors, warnings)

        # Schema validation
        schema = self.schemas.get(msg_type)
        if schema:
            schema_errors = self._validate_against_schema(message, schema)
            errors.extend(schema_errors)

        # Content validation based on type
        if msg_type == MessageType.SUBSCRIBE:
            type_errors, type_warnings = self._validate_subscription(message)
            errors.extend(type_errors)
            warnings.extend(type_warnings)
        elif msg_type == MessageType.COMMAND:
            type_errors, type_warnings = self._validate_command(message)
            errors.extend(type_errors)
            warnings.extend(type_warnings)
        elif msg_type == MessageType.AUTH:
            type_errors, type_warnings = self._validate_auth(message)
            errors.extend(type_errors)
            warnings.extend(type_warnings)

        # Security validation
        security_errors, security_warnings = self._validate_security(message)
        errors.extend(security_errors)
        warnings.extend(security_warnings)

        # Size validation
        size_errors = self._validate_size(message)
        errors.extend(size_errors)

        # Sanitize message
        if not errors:  # Only sanitize if message is valid
            sanitized = self._sanitize_message(message)

        return MessageValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_message=sanitized if not errors else None
        )

    def _validate_against_schema(self, message: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Validate message against schema"""
        errors = []

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in message:
                errors.append(f"Missing required field: {field}")

        # Check field types and constraints
        properties = schema.get("properties", {})
        for field, constraints in properties.items():
            if field in message:
                value = message[field]
                expected_type = constraints.get("type")

                # Type validation
                if isinstance(expected_type, list):
                    # Multiple allowed types (e.g., ["number", "string"])
                    type_valid = False
                    for allowed_type in expected_type:
                        if allowed_type == "string" and isinstance(value, str):
                            type_valid = True
                            break
                        elif allowed_type == "number" and isinstance(value, (int, float)):
                            type_valid = True
                            break
                        elif allowed_type == "object" and isinstance(value, dict):
                            type_valid = True
                            break
                        elif allowed_type == "array" and isinstance(value, list):
                            type_valid = True
                            break
                    if not type_valid:
                        errors.append(f"Field '{field}' must be one of types: {expected_type}")
                else:
                    if expected_type == "string" and not isinstance(value, str):
                        errors.append(f"Field '{field}' must be a string")
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        errors.append(f"Field '{field}' must be a number")
                    elif expected_type == "object" and not isinstance(value, dict):
                        errors.append(f"Field '{field}' must be an object")
                    elif expected_type == "enum" and value not in constraints.get("enum", []):
                        errors.append(f"Field '{field}' must be one of: {constraints.get('enum', [])}")

                # Length constraints
                if expected_type == "string" and "max_length" in constraints:
                    if len(value) > constraints["max_length"]:
                        errors.append(f"Field '{field}' exceeds maximum length of {constraints['max_length']}")

        return errors

    def _validate_subscription(self, message: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Validate subscription-specific content"""
        errors = []
        warnings = []

        stream = message.get("stream", "")
        params = message.get("params", {})

        # Validate stream type
        valid_streams = [
            "market_data", "indicators", "signals", "orders", "positions",
            "portfolio", "execution_status", "system_health",
            "health_check",  # Added missing stream type
            "comprehensive_health_check"  # Also add this variant
        ]
        if stream not in valid_streams:
            errors.append(f"Invalid stream type: {stream}. Must be one of: {valid_streams}")

        # Validate subscription parameters
        if stream == "market_data":
            symbols = params.get("symbols", [])
            if not symbols:
                errors.append("Market data subscription must specify symbols")
            elif len(symbols) > 100:
                errors.append("Maximum 100 symbols per subscription")

            # ✅ PERFORMANCE FIX: Use pre-compiled regex pattern
            for symbol in symbols:
                if not self._symbol_pattern.match(symbol):
                    errors.append(f"Invalid symbol format: {symbol}")

        elif stream == "indicators":
            symbol = params.get("symbol")
            symbols = params.get("symbols")
            if not symbol and not symbols:
                errors.append("Indicator subscription must specify symbol or symbols")

            indicators = params.get("indicators", [])
            if not indicators:
                warnings.append("No indicators specified, subscribing to all")

        return errors, warnings

    def _validate_command(self, message: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Validate command-specific content"""
        errors = []
        warnings = []

        action = message.get("action", "")
        params = message.get("params", {})

        # Validate command actions
        valid_actions = [
            "start_backtest", "stop_execution", "start_live_trading",
            "cancel_order", "get_status", "health_check"
        ]
        if action not in valid_actions:
            errors.append(f"Invalid command action: {action}. Must be one of: {valid_actions}")

        # Validate command parameters
        if action == "start_backtest":
            if "symbols" not in params:
                errors.append("Backtest command must specify symbols")
            if "timeframe" not in params:
                errors.append("Backtest command must specify timeframe")
            if "date_range" not in params:
                errors.append("Backtest command must specify date_range")

        return errors, warnings

    def _validate_auth(self, message: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Validate authentication message"""
        errors = []
        warnings = []

        token = message.get("token", "")

        # Basic token format validation
        if not token or len(token.strip()) == 0:
            errors.append("Authentication token cannot be empty")

        # Check for potentially malicious tokens
        if len(token) > 1000:
            errors.append("Authentication token too long")

        return errors, warnings

    def _validate_security(self, message: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Validate message for security issues"""
        errors = []
        warnings = []

        def check_string_for_dangerous_content(value: str, field_path: str):
            """Check string value for dangerous patterns"""
            for pattern in self.dangerous_patterns:
                if pattern.search(value):  # ✅ PERFORMANCE FIX: Use pre-compiled pattern
                    errors.append(f"Potentially dangerous content detected in {field_path}")

        def traverse_dict(obj: Any, path: str = ""):
            """Recursively traverse dictionary/object"""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if isinstance(value, str):
                        check_string_for_dangerous_content(value, current_path)
                    elif isinstance(value, (dict, list)):
                        traverse_dict(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{path}[{i}]"
                    if isinstance(item, str):
                        check_string_for_dangerous_content(item, current_path)
                    elif isinstance(item, (dict, list)):
                        traverse_dict(item, current_path)

        traverse_dict(message)
        return errors, warnings

    def _validate_size(self, message: Dict[str, Any]) -> List[str]:
        """Validate message size constraints"""
        errors = []

        # Convert to JSON string to check size
        try:
            message_json = json.dumps(message)
            size_bytes = len(message_json.encode('utf-8'))

            # 1MB limit
            if size_bytes > 1024 * 1024:
                errors.append(f"Message too large: {size_bytes} bytes (max 1MB)")

        except Exception as e:
            errors.append(f"Failed to calculate message size: {str(e)}")

        return errors

    def _sanitize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize message content"""
        sanitized = {}

        for key, value in message.items():
            if isinstance(value, str):
                # Basic HTML entity encoding
                sanitized_value = value.replace('<', '<').replace('>', '>')
                sanitized[key] = sanitized_value
            elif isinstance(value, (dict, list)):
                # Recursively sanitize nested structures
                sanitized[key] = self._sanitize_message(value) if isinstance(value, dict) else value
            else:
                sanitized[key] = value

        return sanitized


class MessageRouter:
    """
    Routes WebSocket messages between clients and backend.

    Features:
    - Message validation and sanitization
    - Type-based routing to appropriate handlers
    - Error handling and response formatting
    - Performance monitoring
    - Security validation
    """

    def __init__(self,
                 command_handler: Optional[CommandHandler] = None,
                 logger: Optional[StructuredLogger] = None):
        """
        Initialize MessageRouter.

        Args:
            command_handler: Optional CommandHandler instance for processing commands
            logger: Optional logger instance
        """
        self.logger = logger
        self.validator = MessageValidator()
        self.command_handler = command_handler

        # Message handlers registry
        self.handlers: Dict[str, Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {}

        # Performance tracking
        self.messages_processed = 0
        self.messages_failed = 0
        self.average_processing_time = 0.0
        self.processing_times = []
        self._processing_time_sum = 0.0

        # ✅ PERFORMANCE FIX: Thread pool for CPU-bound JSON operations
        self._json_executor_active = 0
        self._json_executor_peak_active = 0
        workers = self._determine_json_workers()
        self._json_executor_max_workers = workers
        self._json_executor = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="MessageRouter-JSON"
        )
        if self.logger:
            self.logger.info("message_router.json_executor_config", {
                "max_workers": self._json_executor_max_workers
            })

        # Register default handlers
        self._register_default_handlers()

    def _determine_json_workers(self) -> int:
        env_value = os.getenv("MESSAGE_ROUTER_JSON_WORKERS")
        requested = 0
        if env_value:
            try:
                requested = int(env_value)
            except ValueError:
                requested = 0
        if requested <= 0:
            requested = os.cpu_count() or 4
        return max(2, min(requested, 8))

    async def _parse_json(self, raw_message: str) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        self._json_executor_active += 1
        if self._json_executor_active > self._json_executor_peak_active:
            self._json_executor_peak_active = self._json_executor_active
        try:
            return await loop.run_in_executor(self._json_executor, json.loads, raw_message)
        finally:
            self._json_executor_active = max(0, self._json_executor_active - 1)

    def register_handler(self,
                        message_type: str,
                        handler: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        """
        Register a handler for a specific message type.

        Args:
            message_type: Message type to handle
            handler: Async handler function (client_id, message) -> response
        """
        self.handlers[message_type] = handler

        if self.logger:
            self.logger.info("message_router.handler_registered", {
                "message_type": message_type,
                "handler": handler.__name__
            })

    async def route_message(self,
                          client_id: str,
                          message: Dict[str, Any],
                          priority: MessagePriority = MessagePriority.NORMAL) -> Dict[str, Any]:
        """
        Route incoming message to appropriate handler.

        Args:
            client_id: Client ID sending the message
            message: Parsed message dictionary
            priority: Message processing priority

        Returns:
            Response message dictionary
        """
        start_time = time.time()
        self.messages_processed += 1
        try:
            # Validate message
            validation_result = self.validator.validate_message(message)

            if not validation_result.is_valid:
                error_msg = "; ".join(validation_result.errors)
                if self.logger:
                    self.logger.warning("message_router.validation_failed", {
                        "client_id": client_id,
                        "errors": validation_result.errors,
                        "message_type": message.get("type", "unknown")
                    })
                # Map specific validation cases to domain-specific error codes for better UX
                msg_type_str = message.get("type", "")
                if msg_type_str == MessageType.SESSION_START and any("Missing required field: strategy_config" in e for e in validation_result.errors):
                    return self._create_error_response("missing_strategy_config", "strategy_config is required with strategy-to-symbol mapping")
                if msg_type_str == MessageType.SESSION_START and any("Missing required field: session_type" in e for e in validation_result.errors):
                    return self._create_error_response("invalid_session_type", "session_type must be one of: backtest, live, paper")
                return self._create_error_response("validation_error", error_msg)

            # Log warnings if any
            if validation_result.warnings and self.logger:
                self.logger.warning("message_router.validation_warnings", {
                    "client_id": client_id,
                    "warnings": validation_result.warnings
                })

            # Use sanitized message
            sanitized_message = validation_result.sanitized_message or message
            message_type = sanitized_message.get("type")

            # Route to handler
            if message_type in self.handlers:
                try:
                    response = await self.handlers[message_type](client_id, sanitized_message)

                    # Track processing time
                    processing_time = (time.time() - start_time) * 1000
                    self.processing_times.append(processing_time)
                    self._processing_time_sum += processing_time
                    if len(self.processing_times) > 1000:
                        removed = self.processing_times.pop(0)
                        self._processing_time_sum -= removed

                    # Update average
                    if self.processing_times:
                        self.average_processing_time = self._processing_time_sum / len(self.processing_times)

                    if self.logger:
                        self.logger.debug("message_router.message_processed", {
                            "client_id": client_id,
                            "message_type": message_type,
                            "processing_time_ms": processing_time,
                            "message_id": sanitized_message.get("id")
                        })

                    return response

                except Exception as e:
                    self.messages_failed += 1
                    if self.logger:
                        self.logger.error("message_router.handler_error", {
                            "client_id": client_id,
                            "message_type": message_type,
                            "error": str(e),
                            "error_type": type(e).__name__
                        })
                    return self._create_error_response("handler_error", f"Handler error: {str(e)}")
            else:
                return self._create_error_response("unknown_message_type", f"No handler for message type: {message_type}")

        except Exception as e:
            self.messages_failed += 1
            if self.logger:
                self.logger.error("message_router.routing_error", {
                    "client_id": client_id,
                    "error": str(e), 
                    "error_type": type(e).__name__
                })
            return self._create_error_response("routing_error", f"Routing error: {str(e)}")

    def _register_default_handlers(self):
        """Register default message handlers"""
        # Register command handler if available
        if self.command_handler:
            async def handle_command(client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
                return await self.command_handler.handle_command(client_id, message)

            self.register_handler(MessageType.COMMAND, handle_command)

        # Register heartbeat handler
        async def handle_heartbeat(client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
            # Return pong response that frontend can recognize
            # Frontend checks: message.type === 'pong' || message.type === 'status' && message.status === 'pong'
            return {
                "type": "status",
                "status": "pong",
                "timestamp": datetime.now().isoformat(),
                "server_time": datetime.now().timestamp(),
                "message_id": message.get("id")
            }

        self.register_handler(MessageType.HEARTBEAT, handle_heartbeat)

    def _create_error_response(self, error_code: str, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "type": MessageType.ERROR,
            "error_code": error_code,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0"
        }

    def _create_success_response(self,
                               message_type: str,
                               data: Any = None,
                               message_id: Optional[str] = None) -> Dict[str, Any]:
        """Create standardized success response"""
        response = {
            "type": MessageType.RESPONSE,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0"
        }

        if message_id:
            response["id"] = message_id
        if data is not None:
            response["data"] = data

        return response

    def get_stats(self) -> Dict[str, Any]:
        """Get router performance statistics"""
        return {
            "messages_processed": self.messages_processed,
            "messages_failed": self.messages_failed,
            "success_rate": (self.messages_processed - self.messages_failed) / max(self.messages_processed, 1),
            "average_processing_time_ms": self.average_processing_time,
            "registered_handlers": len(self.handlers),
            "handler_types": list(self.handlers.keys()),
            "json_executor": {
                "max_workers": self._json_executor_max_workers,
                "active_tasks": self._json_executor_active,
                "peak_active": self._json_executor_peak_active
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "healthy": True,
            "component": "MessageRouter",
            "stats": self.get_stats(),
            "timestamp": datetime.now().isoformat()
        }
