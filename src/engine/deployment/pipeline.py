#!/usr/bin/env python3
"""
Deployment Pipeline - Controlled Strategy Rollout
=================================================

Implements staged deployment pipeline for graph-based strategies with
validation, approval, staging, and rollback capabilities.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

from ...core.logger import StructuredLogger
from ...strategy_graph.serializer import StrategyGraph
from ...strategy_graph.validators import GraphValidator
from ..graph_adapter import ExecutionPlan, GraphAdapter
from ...trading.session_manager import SessionManager


class DeploymentStage(Enum):
    """Stages in the deployment pipeline."""
    CREATED = "created"
    VALIDATING = "validating"
    VALIDATED = "validated"
    APPROVAL_PENDING = "approval_pending"
    APPROVED = "approved"
    STAGING = "staging"
    STAGED = "staged"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentStatus(Enum):
    """Overall deployment status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DeploymentStep:
    """A step in the deployment pipeline."""
    id: str
    name: str
    stage: DeploymentStage
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Deployment:
    """A strategy deployment through the pipeline."""
    id: str
    blueprint_id: str
    blueprint_name: str
    graph: StrategyGraph
    execution_plan: Optional[ExecutionPlan] = None
    status: DeploymentStatus = DeploymentStatus.ACTIVE
    current_stage: DeploymentStage = DeploymentStage.CREATED
    steps: List[DeploymentStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    approved_by: Optional[str] = None
    deployed_session_id: Optional[str] = None
    symbol: str = "BTCUSDT"  # FIX F1: Primary trading symbol for this deployment
    rollback_data: Dict[str, Any] = field(default_factory=dict)


class DeploymentPipelineError(Exception):
    """Raised when deployment pipeline operations fail."""
    pass


class DeploymentPipeline:
    """
    Manages the deployment pipeline for strategy graphs.

    Provides controlled rollout with validation, approval, staging,
    deployment, and rollback capabilities.
    """

    def __init__(self, logger: StructuredLogger, session_manager: SessionManager):
        self.logger = logger
        self.session_manager = session_manager
        self.graph_adapter = GraphAdapter()
        self.validator = GraphValidator()

        # In-memory storage (would be database in production)
        self.deployments: Dict[str, Deployment] = {}
        self.approval_callbacks: List[Callable] = []

    def create_deployment(self, blueprint_id: str, blueprint_name: str,
                         graph: StrategyGraph, created_by: str,
                         symbol: str = "BTCUSDT") -> str:
        """
        Create a new deployment for a strategy blueprint.

        Args:
            blueprint_id: ID of the blueprint being deployed
            blueprint_name: Name of the blueprint
            graph: The strategy graph to deploy
            created_by: User creating the deployment
            symbol: Primary trading symbol for this deployment (default: BTCUSDT)
                    FIX F1: Explicit symbol parameter ensures symbol is always defined.
                    Risk mitigation: #66 Dependency Risk - eliminates SPOF

        Returns:
            Deployment ID
        """
        deployment_id = str(uuid.uuid4())

        # FIX F1 + #165 Constructive Counterexample: Handle empty string case
        effective_symbol = symbol if symbol and symbol.strip() else "BTCUSDT"

        deployment = Deployment(
            id=deployment_id,
            blueprint_id=blueprint_id,
            blueprint_name=blueprint_name,
            graph=graph,
            created_by=created_by,
            symbol=effective_symbol
        )

        # Add initial step
        deployment.steps.append(DeploymentStep(
            id=str(uuid.uuid4()),
            name="Deployment Created",
            stage=DeploymentStage.CREATED,
            status="completed",
            completed_at=datetime.now(),
            metadata={"blueprint_id": blueprint_id}
        ))

        self.deployments[deployment_id] = deployment

        self.logger.info("deployment.created", {
            "deployment_id": deployment_id,
            "blueprint_id": blueprint_id,
            "created_by": created_by
        })

        return deployment_id

    async def start_validation(self, deployment_id: str) -> bool:
        """
        Start the validation phase of deployment.

        Args:
            deployment_id: The deployment to validate

        Returns:
            True if validation passed
        """
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            raise DeploymentPipelineError(f"Deployment {deployment_id} not found")

        if deployment.current_stage != DeploymentStage.CREATED:
            raise DeploymentPipelineError(f"Cannot validate deployment in stage {deployment.current_stage.value}")

        # Update stage
        deployment.current_stage = DeploymentStage.VALIDATING
        deployment.updated_at = datetime.now()

        # Add validation step
        step = DeploymentStep(
            id=str(uuid.uuid4()),
            name="Graph Validation",
            stage=DeploymentStage.VALIDATING,
            started_at=datetime.now()
        )
        deployment.steps.append(step)

        try:
            # Validate graph
            errors, warnings = self.validator.validate(deployment.graph)

            step.completed_at = datetime.now()

            if errors:
                step.status = "failed"
                step.error = f"Validation failed: {len(errors)} errors"
                step.metadata = {
                    "errors": [{"type": e.error_type, "message": e.message} for e in errors],
                    "warnings": [{"type": w.error_type, "message": w.message} for w in warnings]
                }
                deployment.current_stage = DeploymentStage.FAILED
                return False
            else:
                step.status = "completed"
                step.metadata = {
                    "warnings": [{"type": w.error_type, "message": w.message} for w in warnings]
                }
                deployment.current_stage = DeploymentStage.VALIDATED
                return True

        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now()
            deployment.current_stage = DeploymentStage.FAILED
            raise DeploymentPipelineError(f"Validation failed: {str(e)}")

    async def request_approval(self, deployment_id: str) -> None:
        """
        Move deployment to approval pending stage.

        Args:
            deployment_id: The deployment requesting approval
        """
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            raise DeploymentPipelineError(f"Deployment {deployment_id} not found")

        if deployment.current_stage != DeploymentStage.VALIDATED:
            raise DeploymentPipelineError(f"Cannot request approval for deployment in stage {deployment.current_stage.value}")

        # Update stage
        deployment.current_stage = DeploymentStage.APPROVAL_PENDING
        deployment.updated_at = datetime.now()

        # Add approval step
        step = DeploymentStep(
            id=str(uuid.uuid4()),
            name="Approval Requested",
            stage=DeploymentStage.APPROVAL_PENDING,
            status="pending",
            started_at=datetime.now(),
            metadata={"requires_approval": True}
        )
        deployment.steps.append(step)

        # Notify approval callbacks
        for callback in self.approval_callbacks:
            try:
                await callback(deployment_id, deployment)
            except Exception as e:
                self.logger.error("approval_callback_failed", {
                    "deployment_id": deployment_id,
                    "error": str(e)
                })

        self.logger.info("deployment.approval_requested", {
            "deployment_id": deployment_id,
            "blueprint_name": deployment.blueprint_name
        })

    async def approve_deployment(self, deployment_id: str, approved_by: str) -> None:
        """
        Approve a deployment for staging.

        Args:
            deployment_id: The deployment to approve
            approved_by: User approving the deployment
        """
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            raise DeploymentPipelineError(f"Deployment {deployment_id} not found")

        if deployment.current_stage != DeploymentStage.APPROVAL_PENDING:
            raise DeploymentPipelineError(f"Cannot approve deployment in stage {deployment.current_stage.value}")

        # Update stage
        deployment.current_stage = DeploymentStage.APPROVED
        deployment.approved_by = approved_by
        deployment.updated_at = datetime.now()

        # Complete approval step
        approval_step = next((s for s in deployment.steps if s.stage == DeploymentStage.APPROVAL_PENDING), None)
        if approval_step:
            approval_step.status = "completed"
            approval_step.completed_at = datetime.now()
            approval_step.metadata["approved_by"] = approved_by

        self.logger.info("deployment.approved", {
            "deployment_id": deployment_id,
            "approved_by": approved_by
        })

    async def stage_deployment(self, deployment_id: str) -> None:
        """
        Stage the deployment by creating execution plan.

        Args:
            deployment_id: The deployment to stage
        """
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            raise DeploymentPipelineError(f"Deployment {deployment_id} not found")

        if deployment.current_stage != DeploymentStage.APPROVED:
            raise DeploymentPipelineError(f"Cannot stage deployment in stage {deployment.current_stage.value}")

        # Update stage
        deployment.current_stage = DeploymentStage.STAGING
        deployment.updated_at = datetime.now()

        # Add staging step
        step = DeploymentStep(
            id=str(uuid.uuid4()),
            name="Execution Plan Creation",
            stage=DeploymentStage.STAGING,
            started_at=datetime.now()
        )
        deployment.steps.append(step)

        try:
            # Create execution plan
            execution_plan = await self.graph_adapter.adapt_graph(deployment.graph, deployment.symbol or "BTCUSDT")
            deployment.execution_plan = execution_plan

            step.status = "completed"
            step.completed_at = datetime.now()
            step.metadata = {
                "execution_plan_id": execution_plan.id,
                "node_count": len(execution_plan.nodes),
                "execution_order_length": len(execution_plan.execution_order)
            }

            deployment.current_stage = DeploymentStage.STAGED

            self.logger.info("deployment.staged", {
                "deployment_id": deployment_id,
                "execution_plan_id": execution_plan.id
            })

        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now()
            deployment.current_stage = DeploymentStage.FAILED
            raise DeploymentPipelineError(f"Staging failed: {str(e)}")

    async def deploy_to_paper_trading(self, deployment_id: str, symbols: List[str]) -> str:
        """
        Deploy the staged strategy to paper trading.

        Args:
            deployment_id: The deployment to deploy
            symbols: Trading symbols for the session

        Returns:
            Session ID of the deployed strategy
        """
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            raise DeploymentPipelineError(f"Deployment {deployment_id} not found")

        if deployment.current_stage != DeploymentStage.STAGED:
            raise DeploymentPipelineError(f"Cannot deploy deployment in stage {deployment.current_stage.value}")

        if not deployment.execution_plan:
            raise DeploymentPipelineError("No execution plan available for deployment")

        # Update stage
        deployment.current_stage = DeploymentStage.DEPLOYING
        deployment.updated_at = datetime.now()

        # Add deployment step
        step = DeploymentStep(
            id=str(uuid.uuid4()),
            name="Paper Trading Deployment",
            stage=DeploymentStage.DEPLOYING,
            started_at=datetime.now()
        )
        deployment.steps.append(step)

        try:
            # Create strategy config for session manager
            strategy_config = {
                "name": deployment.blueprint_name,
                "version": "1.0.0",
                "execution_plan": {
                    "id": deployment.execution_plan.id,
                    "nodes": {k: {"id": v.id, "type": v.node_type.value, "dependencies": list(v.dependencies)}
                             for k, v in deployment.execution_plan.nodes.items()},
                    "execution_order": deployment.execution_plan.execution_order,
                    "data_flow": deployment.execution_plan.data_flow
                }
            }

            # Start paper trading session
            session_id = await self.session_manager.start_paper_trading_session(
                strategy_config=strategy_config,
                symbols=symbols,
                user_id=deployment.created_by
            )

            deployment.deployed_session_id = session_id
            deployment.current_stage = DeploymentStage.DEPLOYED

            step.status = "completed"
            step.completed_at = datetime.now()
            step.metadata = {
                "session_id": session_id,
                "symbols": symbols,
                "mode": "paper_trading"
            }

            # Store rollback data
            deployment.rollback_data = {
                "session_id": session_id,
                "strategy_config": strategy_config,
                "symbols": symbols
            }

            self.logger.info("deployment.deployed", {
                "deployment_id": deployment_id,
                "session_id": session_id,
                "mode": "paper_trading"
            })

            return session_id

        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now()
            deployment.current_stage = DeploymentStage.FAILED
            raise DeploymentPipelineError(f"Deployment failed: {str(e)}")

    async def rollback_deployment(self, deployment_id: str, reason: str) -> None:
        """
        Rollback a deployment.

        Args:
            deployment_id: The deployment to rollback
            reason: Reason for rollback
        """
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            raise DeploymentPipelineError(f"Deployment {deployment_id} not found")

        # Add rollback step
        step = DeploymentStep(
            id=str(uuid.uuid4()),
            name="Deployment Rollback",
            stage=DeploymentStage.ROLLED_BACK,
            started_at=datetime.now(),
            metadata={"reason": reason}
        )
        deployment.steps.append(step)

        try:
            # Stop deployed session if it exists
            if deployment.deployed_session_id:
                await self.session_manager.stop_session(
                    deployment.deployed_session_id,
                    deployment.created_by
                )

            deployment.current_stage = DeploymentStage.ROLLED_BACK
            deployment.status = DeploymentStatus.CANCELLED
            deployment.updated_at = datetime.now()

            step.status = "completed"
            step.completed_at = datetime.now()

            self.logger.info("deployment.rolled_back", {
                "deployment_id": deployment_id,
                "reason": reason,
                "session_id": deployment.deployed_session_id
            })

        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now()
            raise DeploymentPipelineError(f"Rollback failed: {str(e)}")

    def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Get a deployment by ID."""
        return self.deployments.get(deployment_id)

    def list_deployments(self, status_filter: Optional[DeploymentStatus] = None) -> List[Deployment]:
        """List deployments, optionally filtered by status."""
        deployments = list(self.deployments.values())

        if status_filter:
            deployments = [d for d in deployments if d.status == status_filter]

        # Sort by creation time (newest first)
        return sorted(deployments, key=lambda d: d.created_at, reverse=True)

    def add_approval_callback(self, callback: Callable) -> None:
        """Add a callback for approval notifications."""
        self.approval_callbacks.append(callback)

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        total = len(self.deployments)
        by_status = {}
        by_stage = {}

        for deployment in self.deployments.values():
            status_key = deployment.status.value
            stage_key = deployment.current_stage.value

            by_status[status_key] = by_status.get(status_key, 0) + 1
            by_stage[stage_key] = by_stage.get(stage_key, 0) + 1

        return {
            "total_deployments": total,
            "by_status": by_status,
            "by_stage": by_stage,
            "active_deployments": by_status.get("active", 0),
            "completed_deployments": by_status.get("completed", 0),
            "failed_deployments": by_status.get("failed", 0)
        }


# Global pipeline instance (would be injected in production)
deployment_pipeline = DeploymentPipeline(None, None)  # Placeholder