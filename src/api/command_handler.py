"""
Command Handler
===============
Handles trading commands from WebSocket clients.
Supports backtest execution, live trading, and execution control.
Production-ready with validation, session management, and progress tracking.
"""

import asyncio
import json
import uuid
import random
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import time

from ..core.logger import StructuredLogger
# ✅ REMOVED: BacktestingEngine import (file deleted - was using deleted FileConnector)
# Backtesting now handled by command_processor.py with QuestDBHistoricalDataSource

@dataclass
class ExecutionSession:
    """Represents an active execution session"""

    session_id: str
    client_id: str
    command_type: str
    status: str = "initializing"
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    progress: float = 0.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    last_update: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for WebSocket transmission"""
        return {
            "session_id": self.session_id,
            "client_id": self.client_id,
            "command_type": self.command_type,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "progress": self.progress,
            "parameters": self.parameters,
            "results": self.results,
            "error_message": self.error_message,
            "last_update": self.last_update.isoformat(),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds()
        }

@dataclass
class CommandValidationResult:
    """Result of command validation"""

    is_valid: bool
    validated_params: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class CommandHandler:
    """
    Handles trading commands from WebSocket clients.

    Features:
    - Command validation and parameter checking
    - Session management for long-running executions
    - Progress tracking and status updates
    - Integration with backend services via Container
    - EventBus integration for progress notifications
    - Resource management and cleanup
    """

    def __init__(self,
                 container: Any,
                 event_bus: Any,
                 logger: Optional[StructuredLogger] = None):
        """
        Initialize CommandHandler.

        Args:
            container: Dependency injection container for accessing backend services
            event_bus: EventBus for publishing progress updates
            logger: Optional logger instance
        """
        self.container = container
        self.event_bus = event_bus
        self.logger = logger

        # Session management
        self.active_sessions: Dict[str, ExecutionSession] = {}
        self.completed_sessions: deque[ExecutionSession] = deque(maxlen=1000)
        self.session_lock = asyncio.Lock()

        # Command definitions
        self.supported_commands = {
            "start_backtest": self._handle_start_backtest,
            "stop_execution": self._handle_stop_execution,
            "start_live_trading": self._handle_start_live_trading,
            "stop_live_trading": self._handle_stop_live_trading,
            "get_session_status": self._handle_get_session_status,
            "list_sessions": self._handle_list_sessions
        }

        # Performance tracking
        self.commands_processed = 0
        self.commands_failed = 0
        self.active_session_count = 0
        self.total_sessions_created = 0
        self.processing_times: deque[float] = deque(maxlen=1000)
        self.average_processing_time = 0.0

        # Configuration
        self.max_concurrent_sessions_per_client = 5
        self.max_total_sessions = 100
        self.session_timeout_hours = 24

    async def handle_command(self,
                           client_id: str,
                           command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming command from client.

        Args:
            client_id: ID of the client sending the command
            command: Command data from WebSocket message

        Returns:
            Response dictionary for WebSocket transmission
        """
        start_time = time.time()
        command_id = command.get("id", str(uuid.uuid4()))

        try:
            # Validate command structure
            validation = await self._validate_command_structure(command)
            if not validation.is_valid:
                return await self._create_error_response(
                    command_id, "invalid_command", validation.errors
                )

            command_type = command["action"]

            # Check if command is supported
            if command_type not in self.supported_commands:
                return await self._create_error_response(
                    command_id, "unsupported_command",
                    [f"Command '{command_type}' is not supported"]
                )

            # Validate command parameters
            param_validation = await self._validate_command_parameters(
                command_type, command.get("params", {})
            )
            if not param_validation.is_valid:
                return await self._create_error_response(
                    command_id, "invalid_parameters", param_validation.errors
                )

            # Check session limits
            if command_type in ["start_backtest", "start_live_trading"]:
                limit_check = await self._check_session_limits(client_id)
                if not limit_check["allowed"]:
                    return await self._create_error_response(
                        command_id, "session_limit_exceeded",
                        [limit_check["reason"]]
                    )

            # Execute command
            handler = self.supported_commands[command_type]
            result = await handler(client_id, command_id, param_validation.validated_params)

            # Track processing time
            processing_time = (time.time() - start_time) * 1000
            self.processing_times.append(processing_time)
            self.average_processing_time = sum(self.processing_times) / len(self.processing_times)
            self.commands_processed += 1

            if self.logger:
                self.logger.info("command_handler.command_processed", {
                    "command_type": command_type,
                    "client_id": client_id,
                    "command_id": command_id,
                    "processing_time_ms": processing_time,
                    "result_status": result.get("status")
                })

            return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.commands_failed += 1

            if self.logger:
                self.logger.error("command_handler.command_error", {
                    "command_type": command.get("action"),
                    "client_id": client_id,
                    "command_id": command_id,
                    "error": str(e),
                    "processing_time_ms": processing_time
                })

            return await self._create_error_response(
                command_id, "internal_error", [str(e)]
            )

    async def _validate_command_structure(self, command: Dict[str, Any]) -> CommandValidationResult:
        """Validate basic command structure"""
        errors = []

        # Required fields
        required_fields = ["type", "action", "id"]
        for field in required_fields:
            if field not in command:
                errors.append(f"Missing required field: {field}")

        if errors:
            return CommandValidationResult(False, errors=errors)

        # Validate command type
        if command["type"] != "command":
            errors.append("Command type must be 'command'")

        # Validate action
        if not isinstance(command["action"], str) or not command["action"].strip():
            errors.append("Action must be a non-empty string")

        return CommandValidationResult(True)

    async def _validate_command_parameters(self,
                                         command_type: str,
                                         params: Dict[str, Any]) -> CommandValidationResult:
        """Validate command-specific parameters"""
        validated_params = params.copy()
        errors = []
        warnings = []

        if command_type == "start_backtest":
            # Validate symbols
            symbols = params.get("symbols", [])
            if not symbols or not isinstance(symbols, list):
                errors.append("Symbols must be a non-empty list")
            elif len(symbols) > 50:
                errors.append("Maximum 50 symbols per backtest")
            else:
                # Validate symbol format
                for symbol in symbols:
                    if not isinstance(symbol, str) or "_" not in symbol:
                        errors.append(f"Invalid symbol format: {symbol}")

            # Validate timeframe
            timeframe = params.get("timeframe", "1h")
            valid_timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
            if timeframe not in valid_timeframes:
                errors.append(f"Invalid timeframe: {timeframe}. Must be one of {valid_timeframes}")

            # Validate date range
            date_range = params.get("date_range", {})
            if not date_range:
                errors.append("Date range is required")
            else:
                try:
                    start = datetime.fromisoformat(date_range["start"].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(date_range["end"].replace('Z', '+00:00'))

                    if start >= end:
                        errors.append("Start date must be before end date")

                    if (end - start).days > 365:
                        warnings.append("Date range exceeds 1 year, this may take longer to process")

                except (KeyError, ValueError) as e:
                    errors.append(f"Invalid date format: {e}")

            # Validate strategy
            strategy_graph = params.get("strategy_graph")
            if not strategy_graph:
                errors.append("Strategy graph is required")
            else:
                # Basic validation for strategy graph structure
                if not isinstance(strategy_graph, dict):
                    errors.append("Strategy graph must be a dictionary")
                elif "nodes" not in strategy_graph or "edges" not in strategy_graph:
                    errors.append("Strategy graph must contain 'nodes' and 'edges' fields")
                elif not isinstance(strategy_graph["nodes"], list) or not isinstance(strategy_graph["edges"], list):
                    errors.append("Strategy graph 'nodes' and 'edges' must be lists")

        elif command_type == "stop_execution":
            session_id = params.get("session_id")
            if not session_id:
                errors.append("Session ID is required for stop_execution")

        elif command_type in ["start_live_trading", "stop_live_trading"]:
            # Validate trading mode
            mode = params.get("mode", "paper")
            if mode not in ["paper", "live"]:
                errors.append("Mode must be 'paper' or 'live'")

        return CommandValidationResult(
            len(errors) == 0,
            validated_params,
            errors,
            warnings
        )

    async def _check_session_limits(self, client_id: str) -> Dict[str, Any]:
        """Check if client can create new session"""
        async with self.session_lock:
            client_sessions = [
                s for s in self.active_sessions.values()
                if s.client_id == client_id
            ]

            if len(client_sessions) >= self.max_concurrent_sessions_per_client:
                return {
                    "allowed": False,
                    "reason": f"Maximum {self.max_concurrent_sessions_per_client} concurrent sessions per client"
                }

            if len(self.active_sessions) >= self.max_total_sessions:
                return {
                    "allowed": False,
                    "reason": f"Maximum {self.max_total_sessions} total active sessions reached"
                }

            return {"allowed": True}
    async def _handle_start_backtest(self,
                                   client_id: str,
                                   command_id: str,
                                   params: Dict[str, Any]) -> Dict[str, Any]:
        """
        ❌ DEPRECATED: start_backtest command is no longer supported.

        BacktestingEngine was removed because it depended on deleted FileConnector.
        Use the proper backtest API instead: POST /sessions/start with mode=BACKTEST

        New backtest system uses:
        - QuestDBHistoricalDataSource (session-based data replay)
        - ExecutionController (unified execution engine)
        - command_processor.py (proper command handling)
        """
        return {
            "type": "error",
            "id": command_id,
            "status": "deprecated",
            "error_code": "COMMAND_DEPRECATED",
            "error_message": (
                "start_backtest command is deprecated and has been removed.\n\n"
                "Use the proper backtest API instead:\n"
                "POST /sessions/start with:\n"
                "{\n"
                '  "mode": "BACKTEST",\n'
                '  "session_id": "<data_collection_session_id>",\n'
                '  "symbols": ["BTC_USDT"],\n'
                '  "acceleration_factor": 10.0\n'
                "}\n\n"
                "List available sessions: GET /api/data-collection/sessions"
            )
        }

    async def _handle_stop_execution(self,
                                   client_id: str,
                                   command_id: str,
                                   params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stop_execution command"""
        session_id = params.get("session_id")

        async with self.session_lock:
            session = self.active_sessions.get(session_id)
            if not session:
                return await self._create_error_response(
                    command_id, "session_not_found",
                    [f"Session {session_id} not found"]
                )

            if session.client_id != client_id:
                return await self._create_error_response(
                    command_id, "access_denied",
                    ["Cannot stop session owned by another client"]
                )

            # Mark session for stopping
            session.status = "stopping"
            session.last_update = datetime.now()

        # Trigger graceful shutdown
        asyncio.create_task(self._stop_execution_session(session_id))

        return {
            "type": "response",
            "id": command_id,
            "status": "accepted",
            "data": {
                "session_id": session_id,
                "message": "Stop request accepted, session will be terminated gracefully"
            }
        }

    async def _handle_start_live_trading(self,
                                       client_id: str,
                                       command_id: str,
                                       params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle start_live_trading command"""
        session_id = f"live_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        # Create execution session
        session = ExecutionSession(
            session_id=session_id,
            client_id=client_id,
            command_type="live_trading",
            parameters=params,
            status="starting"
        )

        async with self.session_lock:
            self.active_sessions[session_id] = session
            self.active_session_count += 1
            self.total_sessions_created += 1

        # Start live trading
        asyncio.create_task(self._execute_live_trading(session))

        return {
            "type": "response",
            "id": command_id,
            "status": "accepted",
            "data": {
                "session_id": session_id,
                "mode": params.get("mode", "paper"),
                "symbols": params.get("symbols", []),
                "message": "Live trading session started"
            }
        }

    async def _handle_stop_live_trading(self,
                                       client_id: str,
                                       command_id: str,
                                       params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stop_live_trading command"""
        session_id = params.get("session_id")

        async with self.session_lock:
            session = self.active_sessions.get(session_id)
            if not session:
                return await self._create_error_response(
                    command_id, "session_not_found",
                    [f"Session {session_id} not found"]
                )

            if session.client_id != client_id:
                return await self._create_error_response(
                    command_id, "access_denied",
                    ["Cannot stop session owned by another client"]
                )

            if session.command_type != "live_trading":
                return await self._create_error_response(
                    command_id, "invalid_session_type",
                    ["Session is not a live trading session"]
                )

            session.status = "stopping"
            session.last_update = datetime.now()

        # Stop live trading
        asyncio.create_task(self._stop_live_trading_session(session_id))

        return {
            "type": "response",
            "id": command_id,
            "status": "accepted",
            "data": {
                "session_id": session_id,
                "message": "Live trading stop request accepted"
            }
        }

    async def _handle_get_session_status(self,
                                       client_id: str,
                                       command_id: str,
                                       params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_session_status command"""
        session_id = params.get("session_id")

        async with self.session_lock:
            session = self.active_sessions.get(session_id)
            if not session:
                return await self._create_error_response(
                    command_id, "session_not_found",
                    [f"Session {session_id} not found"]
                )

            if session.client_id != client_id:
                return await self._create_error_response(
                    command_id, "access_denied",
                    ["Cannot access session owned by another client"]
                )

        return {
            "type": "response",
            "id": command_id,
            "status": "success",
            "data": session.to_dict()
        }

    async def _handle_list_sessions(self,
                                  client_id: str,
                                  command_id: str,
                                  params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_sessions command"""
        async with self.session_lock:
            client_sessions = [
                s.to_dict() for s in self.active_sessions.values()
                if s.client_id == client_id
            ]

        return {
            "type": "response",
            "id": command_id,
            "status": "success",
            "data": {
                "sessions": client_sessions,
                "total_count": len(client_sessions),
                "active_count": len([s for s in client_sessions if s["status"] in ["running", "starting"]])
            }
        }

    # ✅ REMOVED: _execute_backtest method (105 lines)
    # BacktestingEngine was deleted because it depended on deleted FileConnector
    # Use ExecutionController + QuestDBHistoricalDataSource instead (command_processor.py)

    async def _execute_live_trading(self, session: ExecutionSession):
        """Execute live trading in background"""
        try:
            session.status = "running"
            session.last_update = datetime.now()

            # Publish session started event
            await self._publish_execution_event(session, "session_started")

            # Live trading runs indefinitely until stopped
            while session.status == "running":
                await asyncio.sleep(1)  # Heartbeat

                # Update session timestamp
                session.last_update = datetime.now()

                # Publish periodic status updates
                await self._publish_execution_event(session, "progress_update")

        except Exception as e:
            session.status = "failed"
            session.error_message = str(e)
            session.end_time = datetime.now()

            if self.logger:
                self.logger.error("command_handler.live_trading_error", {
                    "session_id": session.session_id,
                    "error": str(e)
                })

            await self._publish_execution_event(session, "session_failed")

        finally:
            async with self.session_lock:
                if session.session_id in self.active_sessions:
                    self.active_sessions.pop(session.session_id, None)
                    if self.active_session_count > 0:
                        self.active_session_count -= 1
                    self.completed_sessions.append(session)

    async def _stop_execution_session(self, session_id: str):
        """Stop execution session gracefully"""
        async with self.session_lock:
            session = self.active_sessions.get(session_id)
            if session:
                session.status = "stopped"
                session.end_time = datetime.now()

                # Move to completed
                self.completed_sessions.append(session)
                self.active_sessions.pop(session_id, None)
                self.active_session_count -= 1

                await self._publish_execution_event(session, "session_completed")

    async def _stop_live_trading_session(self, session_id: str):
        """Stop live trading session"""
        async with self.session_lock:
            session = self.active_sessions.get(session_id)
            if session:
                session.status = "stopped"
                session.end_time = datetime.now()

                # Move to completed
                self.completed_sessions.append(session)
                self.active_sessions.pop(session_id, None)
                self.active_session_count -= 1

                await self._publish_execution_event(session, "session_completed")

    async def _publish_execution_event(self, session: ExecutionSession, event_type: str):
        """Publish execution event to EventBus"""
        event_data = {
            "session_id": session.session_id,
            "client_id": session.client_id,
            "command_type": session.command_type,
            "status": session.status,
            "progress": session.progress,
            "timestamp": datetime.now().isoformat(),
            "parameters": session.parameters,
            "results": session.results,
            "error_message": session.error_message
        }

        # Publish to EventBus
        await self.event_bus.publish(f"execution.{event_type}", event_data)

    async def _create_error_response(self,
                                   command_id: str,
                                   error_type: str,
                                   errors: List[str]) -> Dict[str, Any]:
        """Create error response"""
        return {
            "type": "response",
            "id": command_id,
            "status": "error",
            "error": {
                "type": error_type,
                "messages": errors
            }
        }

    def _estimate_backtest_duration(self, params: Dict[str, Any]) -> int:
        """Estimate backtest duration in seconds"""
        symbols_count = len(params.get("symbols", []))
        date_range = params.get("date_range", {})
        timeframe = params.get("timeframe", "1h")

        # Calculate date range in days
        try:
            start = datetime.fromisoformat(date_range["start"].replace('Z', '+00:00'))
            end = datetime.fromisoformat(date_range["end"].replace('Z', '+00:00'))
            days = (end - start).days
        except (KeyError, ValueError, TypeError) as e:
            if self.logger:
                self.logger.warning("command_handler.date_parsing_error", {
                    "error": str(e),
                    "fallback_days": 30
                })
            days = 30  # Default

        # Timeframe multiplier
        timeframe_multipliers = {
            "1m": 1440,  # Minutes per day
            "5m": 288,
            "15m": 96,
            "1h": 24,
            "4h": 6,
            "1d": 1
        }

        data_points = days * timeframe_multipliers.get(timeframe, 24) * symbols_count

        # Estimate processing time (rough approximation)
        return max(10, min(3600, data_points // 1000))

    def _calculate_data_points(self, params: Dict[str, Any]) -> int:
        """Calculate total data points for backtest"""
        symbols_count = len(params.get("symbols", []))
        date_range = params.get("date_range", {})
        timeframe = params.get("timeframe", "1h")

        try:
            start = datetime.fromisoformat(date_range["start"].replace('Z', '+00:00'))
            end = datetime.fromisoformat(date_range["end"].replace('Z', '+00:00'))
            days = (end - start).days
        except (KeyError, ValueError, TypeError) as e:
            if self.logger:
                self.logger.warning("command_handler.date_parsing_error", {
                    "error": str(e),
                    "fallback_days": 30
                })
            days = 30

        timeframe_multipliers = {
            "1m": 1440,
            "5m": 288,
            "15m": 96,
            "1h": 24,
            "4h": 6,
            "1d": 1
        }

        return days * timeframe_multipliers.get(timeframe, 24) * symbols_count

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.now()
        expired_sessions = []

        async with self.session_lock:
            for session_id, session in self.active_sessions.items():
                if (current_time - session.start_time).total_seconds() > (self.session_timeout_hours * 3600):
                    expired_sessions.append(session_id)
                    session.status = "expired"
                    session.end_time = current_time
                    self.completed_sessions.append(session)

            for session_id in expired_sessions:
                self.active_sessions.pop(session_id, None)
                self.active_session_count -= 1

        if expired_sessions and self.logger:
            self.logger.info("command_handler.expired_sessions_cleaned", {
                "expired_count": len(expired_sessions)
            })

    def get_stats(self) -> Dict[str, Any]:
        """Get CommandHandler statistics"""
        return {
            "commands_processed": self.commands_processed,
            "commands_failed": self.commands_failed,
            "active_sessions": self.active_session_count,
            "total_sessions_created": self.total_sessions_created,
            "completed_sessions_count": len(self.completed_sessions),
            "average_processing_time_ms": self.average_processing_time,
            "processing_times_count": len(self.processing_times)
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "healthy": True,
            "component": "CommandHandler",
            "stats": self.get_stats(),
            "timestamp": datetime.now().isoformat()
        }
