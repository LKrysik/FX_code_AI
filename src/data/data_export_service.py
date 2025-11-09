"""
Data Export Service for Sprint 5A - Data Collection Enhancements

Provides functionality to export collected market data in multiple formats:
- CSV format for spreadsheet analysis
- JSON format for programmatic processing
- Filtered exports by symbol and time range
"""

import csv
import json
import logging
from datetime import datetime
from io import StringIO, BytesIO
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from zipfile import ZipFile

from ..core.logger import get_logger

logger = get_logger(__name__)

class DataExportService:
    """
    Service for exporting collected market data in multiple formats

    Supports:
    - CSV export with proper headers and formatting
    - JSON export with structured metadata
    - Symbol-specific filtering
    - Time range filtering
    - Compressed archives for large datasets

    ✅ BUG-003 FIX: Changed from filesystem-based to QuestDB-based data loading
    """

    def __init__(self, db_provider=None):
        """
        Initialize DataExportService with QuestDB provider.

        Args:
            db_provider: QuestDBDataProvider instance for database access

        Raises:
            ValueError: If db_provider is None

        ✅ BUG-003 FIX: Now requires QuestDBDataProvider (was filesystem-based)
        """
        if db_provider is None:
            raise ValueError(
                "QuestDBDataProvider is required for DataExportService.\n"
                "Filesystem-based data access has been removed. All data now comes from QuestDB."
            )

        self.db_provider = db_provider
        self.max_export_size = 100000  # Maximum rows per export

    async def export_session_csv(self, session_id: str, symbol: str = None) -> bytes:
        """
        Export session data as CSV

        Args:
            session_id: Session identifier
            symbol: Optional symbol filter

        Returns:
            CSV data as bytes
        """
        try:
            # Load session data
            session_data = await self._load_session_export_data(session_id, symbol)
            if not session_data:
                raise ValueError(f"No data found for session {session_id}")

            # Convert to CSV
            csv_content = self._format_as_csv(session_data)

            logger.info(f"Exported {len(session_data['data_points'])} points as CSV for session {session_id}")
            return csv_content.encode('utf-8')

        except Exception as e:
            logger.error(f"Failed to export CSV for session {session_id}: {e}")
            raise

    async def export_session_json(self, session_id: str, symbol: str = None) -> Dict[str, Any]:
        """
        Export session data as JSON

        Args:
            session_id: Session identifier
            symbol: Optional symbol filter

        Returns:
            Structured JSON data
        """
        try:
            # Load session data
            session_data = await self._load_session_export_data(session_id, symbol)
            if not session_data:
                raise ValueError(f"No data found for session {session_id}")

            # Format as JSON
            json_data = self._format_as_json(session_data)

            logger.info(f"Exported {len(session_data['data_points'])} points as JSON for session {session_id}")
            return json_data

        except Exception as e:
            logger.error(f"Failed to export JSON for session {session_id}: {e}")
            raise

    async def export_session_zip(self, session_id: str, format: str = "csv") -> bytes:
        """
        Export complete session as compressed ZIP archive

        Args:
            session_id: Session identifier
            format: Export format ("csv" or "json")

        Returns:
            ZIP archive as bytes
        """
        try:
            buffer = BytesIO()

            with ZipFile(buffer, 'w') as zip_file:
                # Export each symbol separately
                session_meta = await self._load_session_metadata(session_id)
                if not session_meta:
                    raise ValueError(f"Session {session_id} not found")

                for symbol in session_meta['symbols']:
                    if format == "csv":
                        csv_data = await self.export_session_csv(session_id, symbol)
                        zip_file.writestr(f"{symbol}.csv", csv_data.decode('utf-8'))
                    elif format == "json":
                        json_data = await self.export_session_json(session_id, symbol)
                        zip_file.writestr(f"{symbol}.json", json.dumps(json_data, indent=2))

                # Include session metadata
                metadata = await self._load_session_metadata(session_id)
                if metadata:
                    zip_file.writestr("session_metadata.json", json.dumps(metadata, indent=2))

            logger.info(f"Created ZIP export for session {session_id} with {len(session_meta['symbols'])} symbols")
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Failed to create ZIP export for session {session_id}: {e}")
            raise

    async def validate_export_request(self, session_id: str, format: str, symbol: str = None) -> bool:
        """
        Validate export request parameters

        ✅ BUG-004 FIX: Converted to async and uses QuestDB instead of filesystem

        Args:
            session_id: Session identifier
            format: Export format
            symbol: Optional symbol filter

        Returns:
            True if request is valid
        """
        try:
            # Validate format
            if format not in ["csv", "json", "zip"]:
                logger.warning(f"Invalid export format: {format}")
                return False

            # Validate session exists in QuestDB
            session_meta = await self._load_session_metadata(session_id)
            if not session_meta:
                logger.warning(f"Session not found: {session_id}")
                return False

            # Validate symbol if specified
            if symbol:
                symbols = session_meta.get('symbols', [])
                if symbol not in symbols:
                    logger.warning(f"Symbol {symbol} not in session {session_id} symbols: {symbols}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating export request for session {session_id}: {e}")
            return False

    async def get_export_estimate(self, session_id: str, symbol: str = None) -> Dict[str, Any]:
        """
        Estimate export size and processing time

        Args:
            session_id: Session identifier
            symbol: Optional symbol filter

        Returns:
            Export estimation data
        """
        try:
            session_data = await self._load_session_export_data(session_id, symbol)
            if not session_data:
                return {'error': 'Session not found'}

            data_points = len(session_data['data_points'])

            # Estimate file sizes
            csv_size_kb = data_points * 0.1  # Rough estimate: 100 bytes per row
            json_size_kb = data_points * 0.15  # JSON is slightly larger

            # Estimate processing time (rough heuristic)
            processing_time_sec = min(30, data_points / 1000)  # Max 30 seconds

            return {
                'data_points': data_points,
                'estimated_csv_size_kb': round(csv_size_kb, 1),
                'estimated_json_size_kb': round(json_size_kb, 1),
                'estimated_processing_time_sec': round(processing_time_sec, 1),
                'can_export': data_points <= self.max_export_size
            }

        except Exception as e:
            logger.error(f"Failed to estimate export for session {session_id}: {e}")
            return {'error': str(e)}

    async def _load_session_export_data(self, session_id: str, symbol: str = None) -> Optional[Dict[str, Any]]:
        """Load session data for export"""
        try:
            # Load session metadata
            session_meta = await self._load_session_metadata(session_id)
            if not session_meta:
                return None

            # Determine which symbols to export
            symbols_to_export = [symbol] if symbol else session_meta['symbols']

            # Load data for each symbol
            all_data_points = []
            for sym in symbols_to_export:
                symbol_data = await self._load_symbol_data(session_id, sym)
                if symbol_data:
                    # Add symbol identifier to each point
                    for point in symbol_data:
                        point['symbol'] = sym
                    all_data_points.extend(symbol_data)

            # Sort by timestamp
            all_data_points.sort(key=lambda x: x['timestamp'])

            return {
                'session_id': session_id,
                'session_info': session_meta,
                'data_points': all_data_points[:self.max_export_size],  # Limit size
                'export_timestamp': datetime.utcnow().isoformat(),
                'total_points': len(all_data_points),
                'exported_points': min(len(all_data_points), self.max_export_size)
            }

        except Exception as e:
            logger.error(f"Failed to load export data for session {session_id}: {e}")
            return None

    async def _load_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load session metadata from QuestDB.

        ✅ BUG-003 FIX: Changed from filesystem to QuestDB query

        Args:
            session_id: Session identifier

        Returns:
            Session metadata dictionary or None if not found
        """
        try:
            metadata = await self.db_provider.get_session_metadata(session_id)
            return metadata
        except Exception as e:
            logger.error(f"Failed to load session metadata for {session_id}: {e}")
            return None

    async def _load_symbol_data(self, session_id: str, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        Load tick price data for symbol from QuestDB.

        ✅ BUG-003 FIX: Changed from filesystem to QuestDB query

        Args:
            session_id: Session identifier
            symbol: Trading pair symbol

        Returns:
            List of price tick dictionaries or None if not found
        """
        try:
            # Query all tick prices for session/symbol
            tick_prices = await self.db_provider.get_tick_prices(
                session_id=session_id,
                symbol=symbol
                # No limit - export needs all data
            )

            if not tick_prices:
                return None

            # Convert QuestDB format to export format
            # QuestDB returns: {timestamp, price, volume, quote_volume}
            # Export needs: {timestamp (ms), price, volume, ...}
            export_data = []
            for tick in tick_prices:
                # Convert timestamp if needed
                timestamp = tick.get('timestamp')
                if isinstance(timestamp, datetime):
                    timestamp = int(timestamp.timestamp() * 1000)  # Convert to milliseconds

                export_data.append({
                    'timestamp': timestamp,
                    'price': float(tick.get('price', 0)),
                    'volume': float(tick.get('volume', 0)),
                    'quote_volume': float(tick.get('quote_volume', 0))
                })

            return export_data

        except Exception as e:
            logger.error(f"Failed to load symbol data for {symbol} in session {session_id}: {e}")
            return None

    def _format_as_csv(self, session_data: Dict[str, Any]) -> str:
        """Format session data as CSV string"""
        data_points = session_data['data_points']
        if not data_points:
            return "timestamp,price,volume,symbol\n"

        # Determine all possible columns
        all_keys = set()
        for point in data_points[:10]:  # Sample first 10 points
            all_keys.update(point.keys())

        # Standard columns first, then additional ones
        standard_cols = ['timestamp', 'price', 'volume', 'symbol']
        additional_cols = sorted(all_keys - set(standard_cols))
        columns = standard_cols + additional_cols

        # Create CSV output
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(columns)

        # Write data rows
        for point in data_points:
            row = []
            for col in columns:
                value = point.get(col, '')

                # Format timestamp
                if col == 'timestamp' and isinstance(value, (int, float)):
                    try:
                        dt = datetime.fromtimestamp(value / 1000)
                        value = dt.isoformat()
                    except (ValueError, OSError):
                        value = str(value)

                # Format numeric values
                elif isinstance(value, float):
                    value = f"{value:.8f}".rstrip('0').rstrip('.')  # Remove trailing zeros
                elif isinstance(value, int):
                    value = str(value)
                else:
                    value = str(value) if value is not None else ''

                row.append(value)

            writer.writerow(row)

        return output.getvalue()

    def _format_as_json(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format session data as structured JSON"""
        # Create clean copy of data points
        clean_points = []
        for point in session_data['data_points']:
            clean_point = {}
            for key, value in point.items():
                # Format timestamp
                if key == 'timestamp' and isinstance(value, (int, float)):
                    try:
                        dt = datetime.fromtimestamp(value / 1000)
                        clean_point[key] = dt.isoformat()
                    except (ValueError, OSError):
                        clean_point[key] = value
                else:
                    clean_point[key] = value
            clean_points.append(clean_point)

        return {
            'session_info': {
                'session_id': session_data['session_id'],
                'start_time': session_data['session_info'].get('start_time'),
                'end_time': session_data['session_info'].get('end_time'),
                'symbols': session_data['session_info'].get('symbols', []),
                'data_types': session_data['session_info'].get('data_types', [])
            },
            'export_info': {
                'export_timestamp': session_data['export_timestamp'],
                'total_points': session_data['total_points'],
                'exported_points': session_data['exported_points'],
                'format': 'json'
            },
            'data_points': clean_points
        }