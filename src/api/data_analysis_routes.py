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
from fastapi import APIRouter, HTTPException, Query, Response
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

# ✅ STEP 3.3: Initialize QuestDB provider and data provider
# ✅ LOGGER FIX: Removed duplicate StructuredLogger, using logger from line 26
questdb_provider = QuestDBProvider(
    ilp_host='127.0.0.1',
    ilp_port=9009,
    pg_host='127.0.0.1',
    pg_port=8812
)
questdb_data_provider = QuestDBDataProvider(questdb_provider, logger)

# Initialize services with QuestDB provider
# ✅ BUG-003 FIX: Pass db_provider to DataExportService
# ✅ BUG-005 FIX: Pass db_provider to DataQualityService
analysis_service = DataAnalysisService(db_provider=questdb_data_provider)
export_service = DataExportService(db_provider=questdb_data_provider)
quality_service = DataQualityService(db_provider=questdb_data_provider)

@router.get("/{session_id}/analysis")
async def get_session_analysis(
    session_id: str,
    include_quality: bool = Query(True, description="Include quality metrics in analysis")
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

        logger.info(f"Analysis requested for session {session_id}")
        return analysis

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get analysis for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{session_id}/chart-data")
async def get_chart_data(
    session_id: str,
    symbol: str = Query(..., description="Trading symbol to analyze"),
    max_points: int = Query(10000, description="Maximum data points to return", ge=100, le=50000)
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

        logger.info(f"Chart data requested for {symbol} in session {session_id} ({len(chart_data)} points)")
        return {
            'session_id': session_id,
            'symbol': symbol,
            'data_points': len(chart_data),
            'data': chart_data
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Debug: logger type: {type(logger)}, error: {e}")
        logger.error(f"Failed to get chart data for {symbol} in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{session_id}/export")
async def export_session_data(
    session_id: str,
    format: str = Query("csv", description="Export format: csv, json, or zip"),
    symbol: Optional[str] = Query(None, description="Specific symbol to export (optional)")
):
    """
    Export session data in specified format

    Supports CSV, JSON, and ZIP archive formats
    """
    try:
        # Validate export request
        if not export_service.validate_export_request(session_id, format, symbol):
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
        logger.error(f"Failed to export session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Export failed")

@router.get("/{session_id}/quality")
async def get_data_quality(
    session_id: str,
    symbol: Optional[str] = Query(None, description="Specific symbol to analyze (optional)")
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

        logger.info(f"Quality assessment completed for session {session_id}, symbol {target_symbol}")
        return quality_report

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get quality metrics for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Quality assessment failed")

@router.get("/{session_id}/export/estimate")
async def get_export_estimate(
    session_id: str,
    format: str = Query("csv", description="Export format"),
    symbol: Optional[str] = Query(None, description="Specific symbol to export")
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
        logger.error(f"Failed to get export estimate for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Estimate calculation failed")

@router.get("/sessions")
async def list_sessions(
    limit: int = Query(50, description="Maximum sessions to return", ge=1, le=200),
    include_stats: bool = Query(False, description="Include basic statistics for each session")
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
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a data collection session and its associated files."""
    try:
        result = await analysis_service.delete_session(session_id)
        if result.get('success'):
            return {
                'success': True,
                'message': f'Session {session_id} deleted successfully',
                'deleted_files': result.get('deleted_files', [])
            }
        else:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found or could not be deleted")
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

