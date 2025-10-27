"""
Enhanced Command Processor
==========================
Async command processing with validation, progress tracking, and cancellation support.
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from collections import deque

from ...core.event_bus import EventBus, EventPriority
from ...core.logger import StructuredLogger
from ..controllers.execution_controller import ExecutionController, ExecutionMode
from ..controllers.data_sources import LiveDataSource, QuestDBHistoricalDataSource
from ...domain.interfaces.market_data import IMarketDataProvider
from ...data.questdb_data_provider import QuestDBDataProvider
from ...data_feed.questdb_provider import QuestDBProvider


class CommandType(Enum):
    """Supported command types"""
    START_BACKTEST = "START_BACKTEST"
    START_TRADING = "START_TRADING"
    START_DATA_COLLECTION = "START_DATA_COLLECTION"
    STOP_EXECUTION = "STOP_EXECUTION"
    PAUSE_EXECUTION = "PAUSE_EXECUTION"
    RESUME_EXECUTION = "RESUME_EXECUTION"


class CommandStatus(Enum):
    """Command execution status"""
    PENDING = "pending"
    VALIDATING = "validating"
    EXECUTING = "executing"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CommandExecution:
    """Command execution tracking"""
    command_id: str
    command_type: CommandType
    parameters: Dict[str, Any]
    status: CommandStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class CommandValidationResult:
    """Command validation result"""
    valid: bool
    errors: List[str]
    warnings: List[str]


class AsyncCommandProcessor:
    """
    Enhanced async command processor with validation, progress tracking,
    and cancellation support.
    """
    
    def __init__(self,
                 execution_controller: ExecutionController,
                 market_data_provider: IMarketDataProvider,
                 event_bus: EventBus,
                 logger: StructuredLogger,
                 data_path: str = "data",
                 market_data_provider_factory=None):
        self.execution_controller = execution_controller
        self.market_data_provider = market_data_provider
        self.event_bus = event_bus
        self.logger = logger
        self.data_path = data_path
        self.market_data_provider_factory = market_data_provider_factory

        # Main lock for synchronizing access to shared dictionaries
        self._main_lock = asyncio.Lock()

        # Command tracking
        self._active_commands: Dict[str, CommandExecution] = {}
        self._command_tasks: Dict[str, asyncio.Task] = {}
        self._resource_locks: Dict[str, asyncio.Lock] = {}
        self._lock_owners: Dict[str, str] = {}  # Track lock ownership for debugging

        # Progress callbacks
        self._progress_callbacks: Dict[str, List[Callable[[float], None]]] = {}

        # Bounded command history to prevent memory leaks
        self._max_command_history = 1000
        self._command_history: deque[Dict[str, Any]] = deque(maxlen=self._max_command_history)
        
        # Command validators
        self._validators = {
            CommandType.START_BACKTEST: self._validate_start_backtest,
            CommandType.START_TRADING: self._validate_start_trading,
            CommandType.START_DATA_COLLECTION: self._validate_start_data_collection,
            CommandType.STOP_EXECUTION: self._validate_stop_execution,
            CommandType.PAUSE_EXECUTION: self._validate_pause_execution,
            CommandType.RESUME_EXECUTION: self._validate_resume_execution
        }

        # Command executors
        self._executors = {
            CommandType.START_BACKTEST: self._execute_start_backtest,
            CommandType.START_TRADING: self._execute_start_trading,
            CommandType.START_DATA_COLLECTION: self._execute_start_data_collection,
            CommandType.STOP_EXECUTION: self._execute_stop_execution,
            CommandType.PAUSE_EXECUTION: self._execute_pause_execution,
            CommandType.RESUME_EXECUTION: self._execute_resume_execution
        }
    
    async def execute_command(self,
                             command_type: CommandType,
                             parameters: Dict[str, Any],
                             progress_callback: Optional[Callable[[float], None]] = None) -> str:
        """
        Execute a command with validation and progress tracking.

        Returns:
            Command ID for tracking
        """
        command_id = str(uuid.uuid4())

        # Create command execution record
        command_execution = CommandExecution(
            command_id=command_id,
            command_type=command_type,
            parameters=parameters,
            status=CommandStatus.PENDING,
            created_at=datetime.now()
        )

        async with self._main_lock:
            self._active_commands[command_id] = command_execution

            if progress_callback:
                if command_id not in self._progress_callbacks:
                    self._progress_callbacks[command_id] = []
                self._progress_callbacks[command_id].append(progress_callback)

            # Start command execution task
            task = asyncio.create_task(self._execute_command_async(command_id))
            self._command_tasks[command_id] = task

        self.logger.info("command.created", {
            "command_id": command_id,
            "command_type": command_type.value,
            "parameters": parameters
        })

        return command_id
    
    async def cancel_command(self, command_id: str) -> bool:
        """Race-condition safe cancellation"""
        async with self._main_lock:
            if command_id not in self._active_commands:
                return False

            command_execution = self._active_commands[command_id]

            # Atomic state check and transition
            if command_execution.status in [CommandStatus.COMPLETED, CommandStatus.FAILED, CommandStatus.CANCELLED]:
                return False  # Already finished

            # Mark as cancelling to prevent double-cancel
            if command_execution.status == CommandStatus.CANCELLING:
                return True  # Already being cancelled

            command_execution.status = CommandStatus.CANCELLING

            # Get task reference
            task = self._command_tasks.get(command_id)

        # Cancel outside of lock
        if task and not task.done():
            task.cancel()

            # Wait for graceful shutdown with timeout
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass  # Expected for cancellation
            except Exception as e:
                self.logger.error("cancel_task_error", {"error": str(e)})

        # Final status update
        async with self._main_lock:
            if command_id in self._active_commands:
                self._active_commands[command_id].status = CommandStatus.CANCELLED
                self._active_commands[command_id].completed_at = datetime.now()

        self.logger.info("command.cancelled", {
            "command_id": command_id
        })

        await self.event_bus.publish(
            "command.cancelled",
            {"command_id": command_id},
            priority=EventPriority.HIGH
        )

        return True
    
    async def get_command_status(self, command_id: str) -> Optional[CommandExecution]:
        """Get command execution status"""
        async with self._main_lock:
            return self._active_commands.get(command_id)

    async def get_active_commands(self) -> List[CommandExecution]:
        """Get all active commands"""
        async with self._main_lock:
            return [cmd for cmd in self._active_commands.values()
                    if cmd.status in [CommandStatus.PENDING, CommandStatus.VALIDATING, CommandStatus.EXECUTING]]

    async def get_command_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent command history"""
        async with self._main_lock:
            return list(self._command_history)[-limit:]
    
    async def _execute_command_async(self, command_id: str) -> None:
        """Execute command asynchronously"""
        command_execution = self._active_commands[command_id]
        
        try:
            # Validation phase
            command_execution.status = CommandStatus.VALIDATING
            await self._update_progress(command_id, 10.0)
            
            validation_result = await self._validate_command(command_execution)
            if not validation_result.valid:
                raise ValueError(f"Command validation failed: {', '.join(validation_result.errors)}")
            
            # Resource locking
            await self._acquire_resource_locks(command_execution)
            
            # Execution phase
            command_execution.status = CommandStatus.EXECUTING
            command_execution.started_at = datetime.now()
            await self._update_progress(command_id, 20.0)
            
            # Execute the command
            result = await self._execute_command_logic(command_execution)
            
            # Completion
            command_execution.status = CommandStatus.COMPLETED
            command_execution.completed_at = datetime.now()
            command_execution.result = result
            await self._update_progress(command_id, 100.0)
            
            self.logger.info("command.completed", {
                "command_id": command_id,
                "duration": (command_execution.completed_at - command_execution.started_at).total_seconds()
            })
            
            await self.event_bus.publish(
                "command.completed",
                {
                    "command_id": command_id,
                    "result": result
                },
                priority=EventPriority.HIGH
            )
            
        except asyncio.CancelledError:
            command_execution.status = CommandStatus.CANCELLED
            command_execution.completed_at = datetime.now()
            self.logger.info("command.cancelled_during_execution", {
                "command_id": command_id
            })
            
        except Exception as e:
            command_execution.status = CommandStatus.FAILED
            command_execution.completed_at = datetime.now()
            command_execution.error = str(e)
            
            self.logger.error("command.failed", {
                "command_id": command_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            
            await self.event_bus.publish(
                "command.failed",
                {
                    "command_id": command_id,
                    "error": str(e)
                },
                priority=EventPriority.HIGH
            )
            
        finally:
            # Release resource locks
            await self._release_resource_locks(command_execution)

            # Cleanup with synchronization
            async with self._main_lock:
                if command_id in self._command_tasks:
                    del self._command_tasks[command_id]
                if command_id in self._progress_callbacks:
                    del self._progress_callbacks[command_id]
    
    async def _validate_command(self, command_execution: CommandExecution) -> CommandValidationResult:
        """Validate command parameters"""
        validator = self._validators.get(command_execution.command_type)
        if not validator:
            return CommandValidationResult(
                valid=False,
                errors=[f"No validator for command type {command_execution.command_type}"],
                warnings=[]
            )
        
        return await validator(command_execution.parameters)
    
    async def _execute_command_logic(self, command_execution: CommandExecution) -> Dict[str, Any]:
        """Execute command logic"""
        executor = self._executors.get(command_execution.command_type)
        if not executor:
            raise ValueError(f"No executor for command type {command_execution.command_type}")
        
        return await executor(command_execution)
    
    async def _acquire_resource_locks(self, command_execution: CommandExecution) -> List[str]:
        """Acquire necessary resource locks and return list of acquired locks"""
        acquired_locks = []
        command_id = command_execution.command_id

        try:
            if command_execution.command_type in [CommandType.START_BACKTEST, CommandType.START_TRADING, CommandType.START_DATA_COLLECTION]:
                # Pre-create lock if needed (outside main lock to prevent lock-in-lock)
                if "execution" not in self._resource_locks:
                    self._resource_locks["execution"] = asyncio.Lock()

                # Acquire lock outside main lock to prevent deadlock
                await self._resource_locks["execution"].acquire()
                acquired_locks.append("execution")
                self._lock_owners["execution"] = command_id

            # Store acquired locks in command for cleanup
            command_execution.acquired_locks = acquired_locks
            return acquired_locks

        except Exception:
            # Clean up any partially acquired locks
            await self._release_locks_by_list(acquired_locks, command_id)
            raise

    async def _release_resource_locks(self, command_execution: CommandExecution) -> None:
        """Safe release with ownership tracking"""
        acquired_locks = getattr(command_execution, 'acquired_locks', [])
        await self._release_locks_by_list(acquired_locks, command_execution.command_id)

    async def _release_locks_by_list(self, locks: List[str], command_id: str) -> None:
        """Release specific locks safely"""
        for lock_name in locks:
            try:
                if lock_name == "execution":
                    if self._lock_owners.get("execution") == command_id:
                        self._resource_locks["execution"].release()
                        del self._lock_owners["execution"]
            except RuntimeError as e:
                self.logger.error("lock_release_error", {
                    "lock_name": lock_name,
                    "command_id": command_id,
                    "error": str(e)
                })
    
    async def _update_progress(self, command_id: str, progress: float) -> None:
        """Update command progress"""
        callbacks_to_notify = []

        async with self._main_lock:
            if command_id in self._active_commands:
                self._active_commands[command_id].progress = progress

                # Copy callbacks to avoid holding lock during callback execution
                if command_id in self._progress_callbacks:
                    callbacks_to_notify = self._progress_callbacks[command_id].copy()

        # Notify callbacks outside the lock
        for callback in callbacks_to_notify:
            try:
                callback(progress)
            except Exception as e:
                self.logger.error("command.progress_callback_error", {
                    "command_id": command_id,
                    "error": str(e)
                })

        # Publish progress event
        await self.event_bus.publish(
            "command.progress",
            {
                "command_id": command_id,
                "progress": progress
            },
            priority=EventPriority.NORMAL
        )
    
    # Command validators
    async def _validate_start_backtest(self, parameters: Dict[str, Any]) -> CommandValidationResult:
        """Validate START_BACKTEST command"""
        errors = []
        warnings = []
        
        # Check required parameters
        if "symbols" not in parameters:
            errors.append("Missing required parameter: symbols")
        else:
            symbols = parameters["symbols"]
            if isinstance(symbols, str) and symbols.upper() == "ALL":
                # Will be resolved to actual symbols
                pass
            elif isinstance(symbols, list):
                if not symbols:
                    errors.append("Symbols list cannot be empty")
            else:
                errors.append("Symbols must be a list or 'ALL'")
        
        # Check optional parameters
        acceleration_factor = parameters.get("acceleration_factor", 10.0)
        if not isinstance(acceleration_factor, (int, float)) or acceleration_factor <= 0:
            errors.append("Acceleration factor must be a positive number")
        
        # Check if execution is already running
        current_session = self.execution_controller.get_current_session()
        if current_session and current_session.status.value in ["running", "starting"]:
            errors.append("Another execution is already running")
        
        return CommandValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def _validate_start_trading(self, parameters: Dict[str, Any]) -> CommandValidationResult:
        """Validate START_TRADING command"""
        errors = []
        warnings = []
        
        # Check required parameters
        if "symbols" not in parameters:
            errors.append("Missing required parameter: symbols")
        
        if "mode" not in parameters:
            errors.append("Missing required parameter: mode")
        elif parameters["mode"] not in ["paper", "live"]:
            errors.append("Mode must be 'paper' or 'live'")
        
        # Check if execution is already running
        current_session = self.execution_controller.get_current_session()
        if current_session and current_session.status.value in ["running", "starting"]:
            errors.append("Another execution is already running")
        
        return CommandValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def _validate_stop_execution(self, parameters: Dict[str, Any]) -> CommandValidationResult:
        """Validate STOP_EXECUTION command"""
        errors = []
        warnings = []
        
        # Check if there's an execution to stop
        current_session = self.execution_controller.get_current_session()
        if not current_session:
            errors.append("No active execution to stop")
        elif current_session.status.value in ["stopped", "stopping"]:
            warnings.append("Execution is already stopped or stopping")
        
        return CommandValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def _validate_pause_execution(self, parameters: Dict[str, Any]) -> CommandValidationResult:
        """Validate PAUSE_EXECUTION command"""
        errors = []
        warnings = []
        
        current_session = self.execution_controller.get_current_session()
        if not current_session:
            errors.append("No active execution to pause")
        elif current_session.status.value != "running":
            errors.append("Can only pause running execution")
        
        return CommandValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def _validate_resume_execution(self, parameters: Dict[str, Any]) -> CommandValidationResult:
        """Validate RESUME_EXECUTION command"""
        errors = []
        warnings = []

        current_session = self.execution_controller.get_current_session()
        if not current_session:
            errors.append("No active execution to resume")
        elif current_session.status.value != "paused":
            errors.append("Can only resume paused execution")

        return CommandValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    async def _validate_start_data_collection(self, parameters: Dict[str, Any]) -> CommandValidationResult:
        """Validate START_DATA_COLLECTION command"""
        errors = []
        warnings = []

        # Check required parameters
        if "symbols" not in parameters:
            errors.append("Missing required parameter: symbols")
        else:
            symbols = parameters["symbols"]
            if isinstance(symbols, str) and symbols.upper() == "ALL":
                # Will be resolved to actual symbols
                pass
            elif isinstance(symbols, list):
                if not symbols:
                    errors.append("Symbols list cannot be empty")
            else:
                errors.append("Symbols must be a list or 'ALL'")

        if "duration" not in parameters:
            errors.append("Missing required parameter: duration")

        # Note: Backend does not require collection_interval; ignore if present

        # Check if execution is already running
        current_session = self.execution_controller.get_current_session()
        if current_session and current_session.status.value in ["running", "starting"]:
            errors.append("Another execution is already running")

        return CommandValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    # Command executors
    async def _execute_start_backtest(self, command_execution: CommandExecution) -> Dict[str, Any]:
        """
        Execute START_BACKTEST command using QuestDB historical data.

        ✅ STEP 4.2: Updated to use QuestDBHistoricalDataSource with session_id
        """
        parameters = command_execution.parameters

        # ✅ STEP 4.2: Require session_id parameter
        data_session_id = parameters.get("session_id")
        if not data_session_id:
            raise ValueError(
                "session_id parameter is required for backtest.\n"
                "Specify the data collection session to replay for backtesting.\n"
                "Use GET /api/data-collection/sessions to list available sessions."
            )

        # Resolve symbols
        symbols = parameters.get("symbols")
        if not symbols:
            # If no symbols specified, get from session metadata
            symbols = await self._get_session_symbols(data_session_id)
        elif isinstance(symbols, str) and symbols.upper() == "ALL":
            # Get symbols from session metadata
            symbols = await self._get_session_symbols(data_session_id)

        # ✅ STEP 4.2: Create QuestDB data provider
        questdb_provider = QuestDBProvider(
            ilp_host='127.0.0.1',
            ilp_port=9009,
            pg_host='127.0.0.1',
            pg_port=8812
        )
        questdb_data_provider = QuestDBDataProvider(questdb_provider, self.logger)

        # ✅ STEP 4.2: Create QuestDB historical data source
        data_source = QuestDBHistoricalDataSource(
            session_id=data_session_id,
            symbols=symbols,
            db_provider=questdb_data_provider,
            acceleration_factor=parameters.get("acceleration_factor", 10.0),
            batch_size=parameters.get("batch_size", 100),
            logger=self.logger
        )

        # Start execution
        execution_session_id = await self.execution_controller.start_execution(
            mode=ExecutionMode.BACKTEST,
            symbols=symbols,
            data_source=data_source,
            parameters=parameters
        )

        command_execution.session_id = execution_session_id

        return {
            "session_id": execution_session_id,
            "data_session_id": data_session_id,  # Link to source data session
            "mode": "backtest",
            "symbols": symbols,
            "acceleration_factor": parameters.get("acceleration_factor", 10.0)
        }
    
    async def _execute_start_trading(self, command_execution: CommandExecution) -> Dict[str, Any]:
        """Execute START_TRADING command"""
        parameters = command_execution.parameters
        
        # Resolve symbols
        symbols = parameters["symbols"]
        if isinstance(symbols, str) and symbols.upper() == "ALL":
            symbols = self._get_available_symbols()
        
        # Create live data source
        data_source = LiveDataSource(
            market_data_provider=self.market_data_provider,
            symbols=symbols,
            logger=self.logger
        )
        
        # Start execution
        session_id = await self.execution_controller.start_execution(
            mode=ExecutionMode.LIVE,
            symbols=symbols,
            data_source=data_source,
            parameters=parameters
        )
        
        command_execution.session_id = session_id
        
        return {
            "session_id": session_id,
            "mode": parameters["mode"],
            "symbols": symbols
        }
    
    async def _execute_stop_execution(self, command_execution: CommandExecution) -> Dict[str, Any]:
        """Execute STOP_EXECUTION command"""
        parameters = command_execution.parameters
        force = parameters.get("force", False)
        
        await self.execution_controller.stop_execution(force=force)
        
        return {
            "status": "stopping",
            "force": force
        }
    
    async def _execute_pause_execution(self, command_execution: CommandExecution) -> Dict[str, Any]:
        """Execute PAUSE_EXECUTION command"""
        await self.execution_controller.pause_execution()
        
        return {
            "status": "paused"
        }
    
    async def _execute_resume_execution(self, command_execution: CommandExecution) -> Dict[str, Any]:
        """Execute RESUME_EXECUTION command"""
        await self.execution_controller.resume_execution()

        return {
            "status": "resumed"
        }

    async def _execute_start_data_collection(self, command_execution: CommandExecution) -> Dict[str, Any]:
        """Execute START_DATA_COLLECTION command"""
        parameters = command_execution.parameters

        self.logger.info("data_collection.starting", {
            "command_id": command_execution.command_id,
            "parameters": parameters
        })

        # Ensure storage path is present for file writes
        if "data_path" not in parameters:
            # Accept UI's storage_path alias if provided
            if "storage_path" in parameters:
                parameters["data_path"] = parameters["storage_path"]
            else:
                parameters["data_path"] = self.data_path or "data"

        self.logger.info("data_collection.data_path_resolved", {
            "data_path": parameters["data_path"]
        })

        # Resolve symbols
        symbols = parameters["symbols"]
        if isinstance(symbols, str) and symbols.upper() == "ALL":
            symbols = self._get_available_symbols()

        self.logger.info("data_collection.symbols_resolved", {
            "symbols": symbols,
            "symbol_count": len(symbols) if isinstance(symbols, list) else 1
        })

        # Start data collection using the execution controller's method
        # This includes proper factory validation and data source creation
        try:
            session_id = await self.execution_controller.start_data_collection(
                symbols,
                duration=parameters.get("duration", "1h"),
                **{k: v for k, v in parameters.items() if k not in ["duration", "symbols"]}
            )

            self.logger.info("data_collection.execution_started", {
                "session_id": session_id
            })

            command_execution.session_id = session_id

            return {
                "session_id": session_id,
                "mode": "data_collection",
                "symbols": symbols,
                "duration": parameters.get("duration", "1h")
            }
        except Exception as e:
            self.logger.error("data_collection.execution_start_failed", {
                "error": str(e),
                "error_type": type(e).__name__,
                "symbols": symbols,
                "data_path": parameters.get("data_path")
            })
            raise ValueError(f"Failed to start data collection: {str(e)}")
    
    def _get_available_symbols(self) -> List[str]:
        """Get available symbols from data directory"""
        from pathlib import Path
        
        symbols = []
        data_path = Path(self.data_path)
        
        if data_path.exists():
            for item in data_path.iterdir():
                if item.is_dir() and item.name.endswith("_USDT"):
                    symbols.append(item.name)
        
        return symbols[:10]  # Limit to first 10 symbols for safety

    async def _get_session_symbols(self, session_id: str) -> List[str]:
        """
        Get symbols from session metadata in QuestDB.
        
        ✅ STEP 4.2: Helper method to retrieve symbols from data collection session
        
        Args:
            session_id: Data collection session ID
            
        Returns:
            List of symbol strings
            
        Raises:
            ValueError: If session not found or has no symbols
        """
        # Create temporary QuestDB provider
        questdb_provider = QuestDBProvider(
            ilp_host='127.0.0.1',
            ilp_port=9009,
            pg_host='127.0.0.1',
            pg_port=8812
        )
        questdb_data_provider = QuestDBDataProvider(questdb_provider, self.logger)
        
        try:
            # Get session metadata
            metadata = await questdb_data_provider.get_session_metadata(session_id)
            
            if not metadata:
                raise ValueError(f"Data collection session '{session_id}' not found in QuestDB")
            
            symbols = metadata.get('symbols', [])
            
            if not symbols:
                raise ValueError(f"Session '{session_id}' has no symbols")
            
            self.logger.info("command_processor.session_symbols_resolved", {
                "session_id": session_id,
                "symbols": symbols
            })
            
            return symbols
            
        except Exception as e:
            self.logger.error("command_processor.get_session_symbols_failed", {
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise
