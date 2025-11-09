"""
Data Analysis API Routes for Sprint 5A - Data Collection Enhancements

Provides REST endpoints for:
- Session data analysis
- Chart data retrieval
- Data export functionality
- Quality metrics assessment

✅ STEP 3.3: Updated to use QuestDB for data access
"""

import logging
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response, Request, Depends
from fastapi.responses import StreamingResponse

from ..data.data_analysis_service import DataAnalysisService
from ..data.data_export_service import DataExportService
from ..data.data_quality_service import DataQualityService
from ..data.questdb_data_provider import QuestDBDataProvider
from ..data_feed.questdb_provider import QuestDBProvider
from ..core.logger import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/data-collection", tags=["data-analysis"])

# ✅ DEPENDENCY INJECTION FIX: Providers are now initialized in unified_server.py lifespan
# and stored in app.state. Services are created per-request using Depends() pattern.
# This eliminates module-level global state and enables proper testing.

# Helper function to get services from app.state (Dependency Injection)
def get_analysis_service(request: Request) -> DataAnalysisService:
    """Get DataAnalysisService with injected dependencies from app.state"""
    questdb_data_provider = request.app.state.questdb_data_provider
    return DataAnalysisService(db_provider=questdb_data_provider)

def get_export_service(request: Request) -> DataExportService:
    """Get DataExportService with injected dependencies from app.state"""
    questdb_data_provider = request.app.state.questdb_data_provider
    return DataExportService(db_provider=questdb_data_provider)

def get_quality_service(request: Request) -> DataQualityService:
    """Get DataQualityService with injected dependencies from app.state"""
    questdb_data_provider = request.app.state.questdb_data_provider
    return DataQualityService(db_provider=questdb_data_provider)

@router.get("/{session_id}/analysis")
async def get_session_analysis(
    session_id: str,
    include_quality: bool = Query(True, description="Include quality metrics in analysis"),
    analysis_service: DataAnalysisService = Depends(get_analysis_service),
    quality_service: DataQualityService = Depends(get_quality_service)
):
    """
    Get comprehensive analysis for a data collection session

    Returns price/volume statistics, data completeness, and quality metrics
    """
    try:
        # Get basic analysis
        analysis = await analysis_service.analyze_session_data(session_id)

        if not analysis:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Add quality assessment if requested
        if include_quality:
            # Get sample data for quality assessment (first symbol)
            session_info = analysis.get('session_info', {})
            symbols = session_info.get('symbols', [])

            if symbols:
                chart_data = await analysis_service.get_session_chart_data(session_id, symbols[0], max_points=1000)
                if chart_data:
                    # Convert chart data back to raw format for quality assessment
                    raw_data = [
                        {
                            'timestamp': point['timestamp'],
                            'price': point['price'],
                            'volume': point['volume']
                        } for point in chart_data
                    ]

                    quality_report = await quality_service.get_quality_report(session_id, raw_data)
                    analysis['quality'] = quality_report

        logger.info("session_analysis_requested", {
            "session_id": session_id,
            "symbols_count": len(analysis.get('symbols_analyzed', []))
        })
        return analysis

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("session_analysis_failed", {
            "session_id": session_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{session_id}/chart-data")
async def get_chart_data(
    session_id: str,
    symbol: str = Query(..., description="Trading symbol to analyze"),
    max_points: int = Query(10000, description="Maximum data points to return", ge=100, le=50000),
    analysis_service: DataAnalysisService = Depends(get_analysis_service)
):
    """
    Get time-series data formatted for frontend charting

    Returns price and volume data points optimized for visualization
    """
    try:
        chart_data = await analysis_service.get_session_chart_data(session_id, symbol, max_points)

        if not chart_data:
            raise HTTPException(
                status_code=404,
                detail=f"No chart data found for session {session_id}, symbol {symbol}"
            )

        logger.info("chart_data_requested", {
            "session_id": session_id,
            "symbol": symbol,
            "data_points": len(chart_data)
        })
        return {
            'session_id': session_id,
            'symbol': symbol,
            'data_points': len(chart_data),
            'data': chart_data
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("chart_data_failed", {
            "session_id": session_id,
            "symbol": symbol,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{session_id}/export")
async def export_session_data(
    session_id: str,
    format: str = Query("csv", description="Export format: csv, json, or zip"),
    symbol: Optional[str] = Query(None, description="Specific symbol to export (optional)"),
    export_service: DataExportService = Depends(get_export_service)
):
    """
    Export session data in specified format

    Supports CSV, JSON, and ZIP archive formats
    """
    try:
        # Validate export request
        if not await export_service.validate_export_request(session_id, format, symbol):
            raise HTTPException(status_code=400, detail="Invalid export request parameters")

        # Get export estimate first
        estimate = await export_service.get_export_estimate(session_id, symbol)
        if estimate.get('error'):
            raise HTTPException(status_code=404, detail=estimate['error'])

        if not estimate.get('can_export', False):
            raise HTTPException(
                status_code=413,
                detail=f"Export too large: {estimate['data_points']} points exceeds limit"
            )

        # Perform export based on format
        if format == "csv":
            csv_data = await export_service.export_session_csv(session_id, symbol)
            filename = f"{session_id}_{symbol or 'all'}.csv"
            return StreamingResponse(
                iter([csv_data]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        elif format == "json":
            json_data = await export_service.export_session_json(session_id, symbol)
            filename = f"{session_id}_{symbol or 'all'}.json"
            return StreamingResponse(
                iter([json.dumps(json_data, indent=2)]),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        elif format == "zip":
            zip_data = await export_service.export_session_zip(session_id, "csv")  # Default to CSV in ZIP
            filename = f"{session_id}_complete.zip"
            return StreamingResponse(
                iter([zip_data]),
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("session_export_failed", {
            "session_id": session_id,
            "format": format,
            "symbol": symbol,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Export failed")

@router.get("/{session_id}/quality")
async def get_data_quality(
    session_id: str,
    symbol: Optional[str] = Query(None, description="Specific symbol to analyze (optional)"),
    analysis_service: DataAnalysisService = Depends(get_analysis_service),
    quality_service: DataQualityService = Depends(get_quality_service)
):
    """
    Get detailed data quality metrics for a session.

    ✅ BUG-005 FIX: Simplified - quality_service now loads data directly from QuestDB

    Returns completeness scores, gap analysis, and improvement recommendations
    """
    try:
        # Get session metadata to determine available symbols
        session = await analysis_service._load_session_metadata(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        symbols = session.get('symbols', [])
        if not symbols:
            raise HTTPException(status_code=404, detail="No symbols found in session")

        # Use specified symbol or first available
        target_symbol = symbol or symbols[0]

        # Perform quality assessment (service loads data from QuestDB)
        quality_report = await quality_service.get_quality_report(session_id, target_symbol)

        logger.info("quality_assessment_completed", {
            "session_id": session_id,
            "symbol": target_symbol,
            "quality_score": quality_report.get('quality_score')
        })
        return quality_report

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("quality_metrics_failed", {
            "session_id": session_id,
            "symbol": symbol,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Quality assessment failed")

@router.get("/{session_id}/export/estimate")
async def get_export_estimate(
    session_id: str,
    format: str = Query("csv", description="Export format"),
    symbol: Optional[str] = Query(None, description="Specific symbol to export"),
    export_service: DataExportService = Depends(get_export_service)
):
    """
    Get export size and processing time estimate

    Helps users understand export requirements before initiating
    """
    try:
        estimate = await export_service.get_export_estimate(session_id, symbol)

        if estimate.get('error'):
            raise HTTPException(status_code=404, detail=estimate['error'])

        return estimate

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("export_estimate_failed", {
            "session_id": session_id,
            "format": format,
            "symbol": symbol,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Estimate calculation failed")

@router.get("/sessions")
async def list_sessions(
    limit: int = Query(50, description="Maximum sessions to return", ge=1, le=200),
    include_stats: bool = Query(False, description="Include basic statistics for each session"),
    analysis_service: DataAnalysisService = Depends(get_analysis_service)
):
    """List available data collection sessions discovered on disk."""
    try:
        result = await analysis_service.list_sessions(limit=limit, include_stats=include_stats)
        return {
            'sessions': result.get('sessions', []),
            'total_count': result.get('total_count', 0),
            'limit': limit
        }
    except Exception as e:
        logger.error("sessions_list_failed", {
            "limit": limit,
            "include_stats": include_stats,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    request: Request,
    analysis_service: DataAnalysisService = Depends(get_analysis_service)
):
    """
    Delete a data collection session and its associated data.

    Performs cascade delete of:
    - Session metadata
    - Tick prices
    - Orderbook snapshots
    - Aggregated OHLCV candles
    - Indicators
    - Backtest results

    CRITICAL FIX: Also stops the session if it's currently running in execution controller
    to prevent reappearance from /sessions/execution-status endpoint.

    Returns 404 if session not found, 409 if session is active.
    """
    try:
        # DEFENSE IN DEPTH LAYER 1: Check if session is active in execution controller
        # If yes, stop it before deleting from database
        try:
            # Access controller via REST service (proper dependency injection)
            rest_service = request.app.state.rest_service
            controller = await rest_service.get_controller()

            # Get current execution status
            current_status = controller.get_execution_status()

            # If the session to delete is the currently active session, stop it first
            if current_status and current_status.get('session_id') == session_id:
                logger.warning("delete_session_stopping_active_session", {
                    "session_id": session_id,
                    "current_status": current_status.get('status'),
                    "mode": current_status.get('mode')
                })

                # Stop the active session before deleting from database
                await controller.stop_execution()

                # Wait briefly for controller to update state (allows clean shutdown)
                import asyncio
                await asyncio.sleep(0.5)

                logger.info("delete_session_active_session_stopped", {
                    "session_id": session_id,
                    "stopped_successfully": True
                })

        except Exception as e:
            # Log but don't fail - session may not be in controller
            logger.warning("delete_session_controller_check_failed", {
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "continuing_with_database_delete": True
            })

        # Proceed with database deletion (validates session exists, not truly active, etc.)
        result = await analysis_service.delete_session(session_id)

        logger.info("session_deleted_successfully", {
            "session_id": session_id,
            "deleted_counts": result.get('deleted_counts', {})
        })

        return {
            'success': True,
            'message': result.get('message', f'Session {session_id} deleted successfully'),
            'session_id': session_id,
            'deleted_counts': result.get('deleted_counts', {})
        }

    except ValueError as e:
        # Validation errors: session not found, session active, invalid input
        error_msg = str(e)

        # Determine appropriate HTTP status code
        if "not found" in error_msg.lower():
            status_code = 404
        elif "active" in error_msg.lower() or "cannot delete" in error_msg.lower():
            status_code = 409  # Conflict
        else:
            status_code = 400  # Bad request

        logger.warning("session_deletion_validation_failed", {
            "session_id": session_id,
            "error": error_msg,
            "status_code": status_code
        })

        raise HTTPException(
            status_code=status_code,
            detail=f"Failed to delete session: {error_msg}"
        )

    except RuntimeError as e:
        # Database errors during deletion
        logger.error("session_deletion_database_error", {
            "session_id": session_id,
            "error": str(e),
            "error_type": type(e).__name__
        })

        raise HTTPException(
            status_code=500,
            detail=f"Database error during session deletion: {str(e)}"
        )

    except Exception as e:
        # Unexpected errors
        logger.error("session_deletion_unexpected_error", {
            "session_id": session_id,
            "error": str(e),
            "error_type": type(e).__name__
        })

        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during session deletion: {str(e)}"
        )

