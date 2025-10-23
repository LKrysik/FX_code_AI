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
    """

    def __init__(self, data_directory: str = "data/historical"):
        self.data_directory = Path(data_directory)
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

    def validate_export_request(self, session_id: str, format: str, symbol: str = None) -> bool:
        """
        Validate export request parameters

        Args:
            session_id: Session identifier
            format: Export format
            symbol: Optional symbol filter

        Returns:
            True if request is valid
        """
        # Validate format
        if format not in ["csv", "json", "zip"]:
            return False

        # Validate session exists
        session_path = self.data_directory / session_id
        if not session_path.exists():
            return False

        # Validate symbol if specified
        if symbol:
            session_meta = self._load_session_metadata_sync(session_id)
            if not session_meta or symbol not in session_meta.get('symbols', []):
                return False

        return True

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
        """Load session metadata"""
        try:
            meta_file = self.data_directory / session_id / "session_metadata.json"
            if not meta_file.exists():
                return None

            with open(meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load session metadata for {session_id}: {e}")
            return None

    def _load_session_metadata_sync(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous version for validation"""
        try:
            meta_file = self.data_directory / session_id / "session_metadata.json"
            if not meta_file.exists():
                return None

            with open(meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    async def _load_symbol_data(self, session_id: str, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """Load data points for a specific symbol"""
        try:
            data_file = self.data_directory / session_id / f"{symbol}.json"
            if not data_file.exists():
                return None

            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return data
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