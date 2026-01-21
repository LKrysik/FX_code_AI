"""
API Module - WebSocket, Broadcasting, API Endpoints
====================================================

Container module for API-related dependency injection.
Extracted from monolithic container.py for maintainability.

Responsibilities:
- WebSocket server management
- Event broadcasting to clients
- Event bridge (EventBus -> WebSocket)
- Metrics and monitoring APIs
- Notification services
"""

import os
from typing import Optional, TYPE_CHECKING
from .base import ContainerModule

if TYPE_CHECKING:
    from ..container import Container


class ApiModule(ContainerModule):
    """
    API domain container module.

    Factory methods for all API-related services.
    """

    async def create_websocket_server(self) -> 'WebSocketServer':
        """
        Create WebSocket server for real-time client communication.

        Returns:
            Configured WebSocketServer singleton
        """
        async def _create():
            try:
                from ...api.websocket_server import WebSocketServer

                # JWT secret resolution (3 priorities)
                jwt_secret = (
                    os.environ.get('JWT_SECRET') or
                    getattr(self.settings, 'jwt_secret', None) or
                    'dev-secret-change-in-production'
                )

                if jwt_secret == 'dev-secret-change-in-production':
                    self.logger.warning("api_module.using_dev_jwt_secret", {
                        "message": "Using development JWT secret - change in production!"
                    })

                server = WebSocketServer(
                    event_bus=self.event_bus,
                    logger=self.logger,
                    jwt_secret=jwt_secret
                )

                self.logger.info("api_module.websocket_server_created")
                return server

            except Exception as e:
                self.logger.error("api_module.websocket_server_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create WebSocket server: {str(e)}") from e

        return await self._get_or_create_singleton_async("websocket_server", _create)

    async def create_broadcast_provider(self) -> 'BroadcastProvider':
        """
        Create broadcast provider for sending messages to WebSocket clients.

        Returns:
            Configured BroadcastProvider singleton
        """
        async def _create():
            try:
                from ...api.broadcast_provider import BroadcastProvider

                websocket_server = await self.create_websocket_server()

                provider = BroadcastProvider(
                    websocket_server=websocket_server,
                    logger=self.logger
                )

                self.logger.info("api_module.broadcast_provider_created")
                return provider

            except Exception as e:
                self.logger.error("api_module.broadcast_provider_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create broadcast provider: {str(e)}") from e

        return await self._get_or_create_singleton_async("broadcast_provider", _create)

    async def create_event_bridge(self) -> 'EventBridge':
        """
        Create event bridge connecting EventBus to WebSocket broadcasting.

        Returns:
            Configured EventBridge singleton
        """
        async def _create():
            try:
                from ...api.event_bridge import EventBridge

                broadcast_provider = await self.create_broadcast_provider()

                bridge = EventBridge(
                    event_bus=self.event_bus,
                    broadcast_provider=broadcast_provider,
                    logger=self.logger
                )

                self.logger.info("api_module.event_bridge_created", {
                    "status": "created"
                })
                return bridge

            except Exception as e:
                self.logger.error("api_module.event_bridge_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create event bridge: {str(e)}") from e

        return await self._get_or_create_singleton_async("event_bridge", _create)

    async def create_execution_processor(self) -> 'ExecutionProcessor':
        """
        Create execution processor for command handling.

        Returns:
            Configured ExecutionProcessor singleton
        """
        async def _create():
            try:
                from ...api.command_handler import ExecutionProcessor

                processor = ExecutionProcessor(
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("api_module.execution_processor_created")
                return processor

            except Exception as e:
                self.logger.error("api_module.execution_processor_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create execution processor: {str(e)}") from e

        return await self._get_or_create_singleton_async("execution_processor", _create)

    async def create_ops_api(self) -> 'OpsAPI':
        """
        Create operations API for monitoring and management.

        Returns:
            Configured OpsAPI singleton
        """
        async def _create():
            try:
                from ...api.ops.ops_api import OpsAPI

                # JWT secret resolution
                jwt_secret = (
                    os.environ.get('JWT_SECRET') or
                    getattr(self.settings, 'jwt_secret', None) or
                    'dev-secret-change-in-production'
                )

                ops_api = OpsAPI(
                    event_bus=self.event_bus,
                    logger=self.logger,
                    jwt_secret=jwt_secret,
                    settings=self.settings
                )

                self.logger.info("api_module.ops_api_created")
                return ops_api

            except Exception as e:
                self.logger.error("api_module.ops_api_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create ops API: {str(e)}") from e

        return await self._get_or_create_singleton_async("ops_api", _create)

    async def create_metrics_exporter(self) -> 'MetricsExporter':
        """
        Create metrics exporter for Prometheus integration.

        Returns:
            Configured MetricsExporter singleton
        """
        async def _create():
            try:
                from ...monitoring.metrics_exporter import MetricsExporter

                exporter = MetricsExporter(
                    event_bus=self.event_bus,
                    logger=self.logger
                )

                self.logger.info("api_module.metrics_exporter_created")
                return exporter

            except Exception as e:
                self.logger.error("api_module.metrics_exporter_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create metrics exporter: {str(e)}") from e

        return await self._get_or_create_singleton_async("metrics_exporter", _create)

    async def create_prometheus_metrics(self) -> 'PrometheusMetrics':
        """
        Create Prometheus metrics collector.

        Returns:
            Configured PrometheusMetrics singleton
        """
        async def _create():
            try:
                from ...infrastructure.monitoring.metrics_exporter import PrometheusMetrics

                metrics = PrometheusMetrics(
                    logger=self.logger
                )

                self.logger.info("api_module.prometheus_metrics_created")
                return metrics

            except Exception as e:
                self.logger.error("api_module.prometheus_metrics_creation_failed", {
                    "error": str(e)
                })
                raise RuntimeError(f"Failed to create Prometheus metrics: {str(e)}") from e

        return await self._get_or_create_singleton_async("prometheus_metrics", _create)

    def create_notification_service(self) -> Optional['INotificationService']:
        """
        Create notification service for alerts.

        Returns:
            Configured notification service or None if not configured
        """
        def _create():
            try:
                notification_config = getattr(self.settings, 'notifications', None)

                if not notification_config or not notification_config.get('enabled', False):
                    self.logger.info("api_module.notification_service_disabled")
                    return None

                from ...domain.interfaces.notifications import INotificationService

                # Factory based on notification type
                notification_type = notification_config.get('type', 'console')

                if notification_type == 'telegram':
                    from ...infrastructure.adapters.telegram_notifier import TelegramNotifier
                    return TelegramNotifier(
                        config=notification_config,
                        logger=self.logger
                    )
                elif notification_type == 'discord':
                    from ...infrastructure.adapters.discord_notifier import DiscordNotifier
                    return DiscordNotifier(
                        config=notification_config,
                        logger=self.logger
                    )
                else:
                    from ...infrastructure.adapters.console_notifier import ConsoleNotifier
                    return ConsoleNotifier(logger=self.logger)

            except Exception as e:
                self.logger.error("api_module.notification_service_creation_failed", {
                    "error": str(e)
                })
                return None

        return self._get_or_create_singleton("notification_service", _create)
