"""
Monitoring Routes - FastAPI Endpoints for Prometheus Metrics
============================================================

Provides HTTP endpoints for Prometheus metrics scraping and health checks.

Endpoints:
- GET /metrics - Prometheus metrics endpoint (for Prometheus scraper)
- GET /health/metrics - Metrics system health check
"""

from fastapi import APIRouter, Response
from typing import Dict, Any

from ..infrastructure.monitoring import get_metrics_instance
from ..core.logger import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter()


@router.get("/metrics")
async def get_prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format for scraping.
    This endpoint should be configured in prometheus.yml:

    ```yaml
    scrape_configs:
      - job_name: 'fx_trading_system'
        static_configs:
          - targets: ['localhost:8080']
        metrics_path: '/metrics'
    ```

    Returns:
        Response: Metrics in Prometheus format with correct content type
    """
    try:
        metrics_instance = get_metrics_instance()

        if metrics_instance is None:
            logger.error("PrometheusMetrics instance not initialized")
            return Response(
                content="# PrometheusMetrics not initialized\n",
                media_type="text/plain",
                status_code=503
            )

        # Get metrics in Prometheus format
        metrics_content = metrics_instance.get_metrics()
        content_type = metrics_instance.get_metrics_content_type()

        logger.debug("Metrics scraped successfully")

        return Response(
            content=metrics_content,
            media_type=content_type
        )

    except Exception as e:
        logger.error(f"Error generating metrics: {e}", exc_info=True)
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            media_type="text/plain",
            status_code=500
        )


@router.get("/health/metrics")
async def get_metrics_health() -> Dict[str, Any]:
    """
    Metrics system health check.

    Returns the health status of the metrics collection system,
    including whether it's subscribed to EventBus and which
    metrics are available.

    Returns:
        Dict containing:
        - status: "healthy" or "not_subscribed" or "not_initialized"
        - subscribed_to_eventbus: bool
        - metrics_available: list of metric names
        - message: human-readable status message
    """
    try:
        metrics_instance = get_metrics_instance()

        if metrics_instance is None:
            logger.warning("Metrics health check: PrometheusMetrics not initialized")
            return {
                "status": "not_initialized",
                "subscribed_to_eventbus": False,
                "metrics_available": [],
                "message": "PrometheusMetrics instance not initialized. Check container.py configuration."
            }

        health = metrics_instance.get_health()

        # Add human-readable message
        if health["status"] == "healthy":
            health["message"] = "Metrics system is healthy and collecting data from EventBus"
        elif health["status"] == "not_subscribed":
            health["message"] = "Metrics system initialized but not subscribed to EventBus. Call subscribe_to_events()."
        else:
            health["message"] = f"Metrics system status: {health['status']}"

        logger.debug(f"Metrics health: {health['status']}")

        return health

    except Exception as e:
        logger.error(f"Error checking metrics health: {e}", exc_info=True)
        return {
            "status": "error",
            "subscribed_to_eventbus": False,
            "metrics_available": [],
            "message": f"Error checking metrics health: {str(e)}"
        }


@router.get("/health/metrics/summary")
async def get_metrics_summary() -> Dict[str, Any]:
    """
    Get a summary of current metric values.

    This is a convenience endpoint for debugging and monitoring
    the live trading system without needing to parse Prometheus format.

    Returns:
        Dict containing current values of key metrics
    """
    try:
        metrics_instance = get_metrics_instance()

        if metrics_instance is None:
            return {
                "error": "PrometheusMetrics not initialized"
            }

        # For now, return health info
        # In the future, could parse metrics and return current values
        health = metrics_instance.get_health()

        return {
            "status": health["status"],
            "metrics_count": len(health["metrics_available"]),
            "note": "Use GET /metrics for full Prometheus metrics"
        }

    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}", exc_info=True)
        return {
            "error": str(e)
        }
