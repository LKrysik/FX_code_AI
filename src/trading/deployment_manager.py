#!/usr/bin/env python3
"""
Deployment Manager - Hot Reload and Kill Switch Integration
==========================================================

Manages live deployment of graph-based strategies with hot reload capabilities,
kill-switch integration, and session coordination.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from ..core.logger import StructuredLogger
from ..core.event_bus import EventBus
from ..strategy_graph.serializer import StrategyGraph
from ..engine.graph_adapter import ExecutionPlan, GraphAdapter, graph_adapter
from ..engine.strategy_evaluator import StrategyEvaluator, StrategyConfig
from .session_manager import SessionManager


class DeploymentMode(Enum):
    """Deployment modes for strategies."""
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"
    BACKTEST = "backtest"


class DeploymentState(Enum):
    """States of a deployed strategy."""
    STARTING = "starting"
    RUNNING = "running"
    RELOADING = "reloading"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    KILLED = "killed"


@dataclass
class ActiveDeployment:
    """An actively running strategy deployment."""
    id: str
    blueprint_id: str
    blueprint_name: str
    graph: StrategyGraph
    execution_plan: ExecutionPlan
    mode: DeploymentMode
    state: DeploymentState
    session_id: str
    symbols: List[str]
    strategy_evaluator: Optional[StrategyEvaluator] = None
    deployed_at: datetime = field(default_factory=datetime.now)
    last_reload: Optional[datetime] = None
    reload_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DeploymentManagerError(Exception):
    """Raised when deployment management operations fail."""
    pass


class DeploymentManager:
    """
    Manages live deployment of graph-based strategies.

    Provides hot reload capabilities, kill-switch integration,
    and coordination with session management.
    """

    def __init__(self, event_bus: EventBus, session_manager: SessionManager,
                 logger: StructuredLogger):
        self.event_bus = event_bus
        self.session_manager = session_manager
        self.logger = logger
        self.graph_adapter = GraphAdapter()

        # Active deployments
        self.active_deployments: Dict[str, ActiveDeployment] = {}
        self.deployment_lock = asyncio.Lock()

        # Kill switch state
        self.kill_switch_active = False
        self.kill_switch_reason = ""

        # Event subscriptions (set up lazily)
        self._event_subscriptions_setup = False

    async def _setup_event_subscriptions(self):
        """Set up event bus subscriptions."""
        if not self._event_subscriptions_setup and self.event_bus:
            await self.event_bus.subscribe("kill_switch.activated", self._handle_kill_switch)
            await self.event_bus.subscribe("kill_switch.deactivated", self._handle_kill_switch_deactivation)
            self._event_subscriptions_setup = True

    async def deploy_strategy(self, blueprint_id: str, blueprint_name: str,
                            graph: StrategyGraph, mode: DeploymentMode,
                            symbols: List[str], user_id: str) -> str:
        """
        Deploy a strategy graph to the specified mode.

        Args:
            blueprint_id: ID of the blueprint being deployed
            blueprint_name: Name of the blueprint
            graph: The strategy graph to deploy
            mode: Deployment mode (paper/live/backtest)
            symbols: Trading symbols
            user_id: User deploying the strategy

        Returns:
            Deployment ID
        """
        # Ensure event subscriptions are set up
        await self._setup_event_subscriptions()

        async with self.deployment_lock:
            # Check kill switch
            if self.kill_switch_active:
                raise DeploymentManagerError(f"Cannot deploy: kill switch is active - {self.kill_switch_reason}")

            deployment_id = str(uuid.uuid4())

            try:
                # Adapt graph to execution plan
                execution_plan = await self.graph_adapter.adapt_graph(graph, symbols[0] if symbols else "BTCUSDT")

                # Create strategy config for evaluator
                strategy_config = StrategyConfig(
                    name=blueprint_name,
                    version="1.0.0",
                    indicators={},  # Will be populated by execution plan
                    weights={},     # Not used in graph-based strategies
                    thresholds={},  # Not used in graph-based strategies
                    risk_limits={
                        "min_confidence": 0.5,
                        "base_position_size": 100.0,
                        "max_position_size": 1000.0
                    },
                    emergency_stops={}
                )

                # Create strategy evaluator
                strategy_evaluator = StrategyEvaluator(self.event_bus, strategy_config)

                # Start session based on mode
                if mode == DeploymentMode.PAPER_TRADING:
                    session_id = await self.session_manager.start_paper_trading_session(
                        strategy_config=strategy_config.__dict__,
                        symbols=symbols,
                        user_id=user_id
                    )
                elif mode == DeploymentMode.LIVE_TRADING:
                    session_id = await self.session_manager.start_live_trading_session(
                        strategy_config=strategy_config.__dict__,
                        symbols=symbols,
                        user_id=user_id
                    )
                elif mode == DeploymentMode.BACKTEST:
                    session_id = await self.session_manager.start_backtest_session(
                        strategy_config=strategy_config.__dict__,
                        symbols=symbols,
                        user_id=user_id
                    )
                else:
                    raise DeploymentManagerError(f"Unsupported deployment mode: {mode}")

                # Start strategy evaluator
                await strategy_evaluator.start()

                # Create active deployment record
                deployment = ActiveDeployment(
                    id=deployment_id,
                    blueprint_id=blueprint_id,
                    blueprint_name=blueprint_name,
                    graph=graph,
                    execution_plan=execution_plan,
                    mode=mode,
                    state=DeploymentState.RUNNING,
                    session_id=session_id,
                    symbols=symbols,
                    strategy_evaluator=strategy_evaluator,
                    metadata={
                        "user_id": user_id,
                        "deployment_mode": mode.value,
                        "session_type": mode.value
                    }
                )

                self.active_deployments[deployment_id] = deployment

                self.logger.info("strategy.deployed", {
                    "deployment_id": deployment_id,
                    "blueprint_id": blueprint_id,
                    "mode": mode.value,
                    "session_id": session_id,
                    "symbols": symbols
                })

                return deployment_id

            except Exception as e:
                self.logger.error("strategy.deployment_failed", {
                    "deployment_id": deployment_id,
                    "blueprint_id": blueprint_id,
                    "error": str(e)
                })
                raise DeploymentManagerError(f"Deployment failed: {str(e)}")

    async def hot_reload_strategy(self, deployment_id: str, new_graph: StrategyGraph) -> None:
        """
        Perform hot reload of a running strategy with new graph.

        Args:
            deployment_id: ID of the deployment to reload
            new_graph: New strategy graph
        """
        async with self.deployment_lock:
            deployment = self.active_deployments.get(deployment_id)
            if not deployment:
                raise DeploymentManagerError(f"Deployment {deployment_id} not found")

            if deployment.state != DeploymentState.RUNNING:
                raise DeploymentManagerError(f"Cannot reload deployment in state {deployment.state.value}")

            try:
                # Update deployment state
                deployment.state = DeploymentState.RELOADING
                deployment.reload_count += 1

                # Adapt new graph
                new_execution_plan = await self.graph_adapter.adapt_graph(new_graph, deployment.symbols[0] if deployment.symbols else "BTCUSDT")

                # Update deployment
                deployment.graph = new_graph
                deployment.execution_plan = new_execution_plan
                deployment.last_reload = datetime.now()

                # Update strategy evaluator if needed
                if deployment.strategy_evaluator:
                    # In a full implementation, this would update the evaluator's execution plan
                    # For now, we just update the metadata
                    pass

                deployment.state = DeploymentState.RUNNING

                self.logger.info("strategy.hot_reloaded", {
                    "deployment_id": deployment_id,
                    "reload_count": deployment.reload_count,
                    "blueprint_id": deployment.blueprint_id
                })

            except Exception as e:
                deployment.state = DeploymentState.FAILED
                deployment.error_count += 1

                self.logger.error("strategy.reload_failed", {
                    "deployment_id": deployment_id,
                    "error": str(e)
                })
                raise DeploymentManagerError(f"Hot reload failed: {str(e)}")

    async def stop_deployment(self, deployment_id: str, reason: str = "User requested") -> None:
        """
        Stop a running deployment.

        Args:
            deployment_id: ID of the deployment to stop
            reason: Reason for stopping
        """
        async with self.deployment_lock:
            deployment = self.active_deployments.get(deployment_id)
            if not deployment:
                raise DeploymentManagerError(f"Deployment {deployment_id} not found")

            try:
                deployment.state = DeploymentState.STOPPING

                # Stop strategy evaluator
                if deployment.strategy_evaluator:
                    await deployment.strategy_evaluator.stop()

                # Stop session
                await self.session_manager.stop_session(
                    deployment.session_id,
                    deployment.metadata.get("user_id", "system")
                )

                deployment.state = DeploymentState.STOPPED

                self.logger.info("strategy.stopped", {
                    "deployment_id": deployment_id,
                    "session_id": deployment.session_id,
                    "reason": reason
                })

                # Remove from active deployments
                del self.active_deployments[deployment_id]

            except Exception as e:
                deployment.state = DeploymentState.FAILED
                self.logger.error("strategy.stop_failed", {
                    "deployment_id": deployment_id,
                    "error": str(e)
                })
                raise DeploymentManagerError(f"Stop failed: {str(e)}")

    async def activate_kill_switch(self, reason: str, user_id: str) -> Dict[str, Any]:
        """
        Activate global kill switch - stop all deployments.

        Args:
            reason: Reason for kill switch activation
            user_id: User activating the kill switch

        Returns:
            Summary of stopped deployments
        """
        async with self.deployment_lock:
            if self.kill_switch_active:
                raise DeploymentManagerError("Kill switch already active")

            self.kill_switch_active = True
            self.kill_switch_reason = reason

            stopped_deployments = []
            failed_stops = []

            # Stop all active deployments
            for deployment_id, deployment in list(self.active_deployments.items()):
                try:
                    await self.stop_deployment(deployment_id, f"Kill switch activated: {reason}")
                    stopped_deployments.append({
                        "deployment_id": deployment_id,
                        "blueprint_name": deployment.blueprint_name,
                        "mode": deployment.mode.value
                    })
                except Exception as e:
                    failed_stops.append({
                        "deployment_id": deployment_id,
                        "error": str(e)
                    })

            # Publish kill switch event
            await self.event_bus.publish("kill_switch.activated", {
                "reason": reason,
                "user_id": user_id,
                "stopped_deployments": len(stopped_deployments),
                "failed_stops": len(failed_stops),
                "timestamp": datetime.now().isoformat()
            })

            self.logger.info("kill_switch.activated", {
                "reason": reason,
                "user_id": user_id,
                "stopped_count": len(stopped_deployments),
                "failed_count": len(failed_stops)
            })

            return {
                "kill_switch_active": True,
                "reason": reason,
                "stopped_deployments": stopped_deployments,
                "failed_stops": failed_stops
            }

    async def deactivate_kill_switch(self, user_id: str) -> None:
        """
        Deactivate the kill switch.

        Args:
            user_id: User deactivating the kill switch
        """
        async with self.deployment_lock:
            if not self.kill_switch_active:
                return

            self.kill_switch_active = False
            self.kill_switch_reason = ""

            # Publish kill switch deactivation event
            await self.event_bus.publish("kill_switch.deactivated", {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            })

            self.logger.info("kill_switch.deactivated", {
                "user_id": user_id
            })

    async def _handle_kill_switch(self, data: Dict[str, Any]) -> None:
        """Handle kill switch activation event."""
        self.kill_switch_active = True
        self.kill_switch_reason = data.get("reason", "External kill switch")

        self.logger.warning("kill_switch_handled", {
            "reason": self.kill_switch_reason,
            "active_deployments": len(self.active_deployments)
        })

    async def _handle_kill_switch_deactivation(self, data: Dict[str, Any]) -> None:
        """Handle kill switch deactivation event."""
        self.kill_switch_active = False
        self.kill_switch_reason = ""

        self.logger.info("kill_switch_deactivation_handled", {
            "user_id": data.get("user_id")
        })

    def get_deployment(self, deployment_id: str) -> Optional[ActiveDeployment]:
        """Get an active deployment by ID."""
        return self.active_deployments.get(deployment_id)

    def list_active_deployments(self) -> List[ActiveDeployment]:
        """List all active deployments."""
        return list(self.active_deployments.values())

    def get_kill_switch_status(self) -> Dict[str, Any]:
        """Get kill switch status."""
        return {
            "active": self.kill_switch_active,
            "reason": self.kill_switch_reason,
            "active_deployments_count": len(self.active_deployments),
            "timestamp": datetime.now().isoformat()
        }

    def get_deployment_stats(self) -> Dict[str, Any]:
        """Get deployment statistics."""
        total = len(self.active_deployments)
        by_mode = {}
        by_state = {}

        for deployment in self.active_deployments.values():
            mode_key = deployment.mode.value
            state_key = deployment.state.value

            by_mode[mode_key] = by_mode.get(mode_key, 0) + 1
            by_state[state_key] = by_state.get(state_key, 0) + 1

        return {
            "total_active": total,
            "by_mode": by_mode,
            "by_state": by_state,
            "kill_switch_active": self.kill_switch_active,
            "total_reloads": sum(d.reload_count for d in self.active_deployments.values()),
            "total_errors": sum(d.error_count for d in self.active_deployments.values())
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all active deployments."""
        health_status = {
            "healthy_deployments": 0,
            "unhealthy_deployments": 0,
            "failed_checks": [],
            "timestamp": datetime.now().isoformat()
        }

        for deployment in self.active_deployments.values():
            try:
                # Check if session is still active
                session_status = await self.session_manager.get_session_status(
                    deployment.session_id,
                    deployment.metadata.get("user_id", "system")
                )

                if session_status and session_status.get("status") in ["running", "active"]:
                    health_status["healthy_deployments"] += 1
                else:
                    health_status["unhealthy_deployments"] += 1
                    health_status["failed_checks"].append({
                        "deployment_id": deployment.id,
                        "blueprint_name": deployment.blueprint_name,
                        "issue": "Session not active"
                    })

            except Exception as e:
                health_status["unhealthy_deployments"] += 1
                health_status["failed_checks"].append({
                    "deployment_id": deployment.id,
                    "blueprint_name": deployment.blueprint_name,
                    "issue": str(e)
                })

        return health_status


# Global deployment manager instance (would be injected in production)
deployment_manager = DeploymentManager(None, None, None)  # Placeholder