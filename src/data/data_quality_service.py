"""
Data Quality Service for Sprint 5A - Data Collection Enhancements

Provides comprehensive data quality assessment including:
- Completeness analysis
- Gap detection
- Anomaly identification
- Quality scoring algorithms
- Data validation rules
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from ..core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class DataQualityMetrics:
    """Comprehensive data quality metrics"""
    completeness_score: float  # 0-100
    gap_count: int
    total_gap_duration_ms: int
    anomaly_count: int
    data_points: int
    missing_values: int
    unrealistic_values: int
    timestamp_issues: int
    overall_score: float  # 0-100 weighted score

@dataclass
class GapInfo:
    """Information about data gaps"""
    start_time: int
    end_time: int
    duration_ms: int
    missing_points: int
    severity: str  # 'minor', 'moderate', 'critical'

@dataclass
class AnomalyInfo:
    """Information about data anomalies"""
    timestamp: int
    field: str
    value: Any
    expected_range: Tuple[float, float]
    severity: str

class DataQualityService:
    """
    Service for monitoring and assessing data quality

    Provides methods to:
    - Calculate completeness percentages
    - Detect gaps in time series
    - Identify data anomalies
    - Generate quality scores
    - Provide improvement recommendations

    ✅ BUG-005 FIX: Changed to load data from QuestDB instead of accepting data_points parameter
    """

    def __init__(self, db_provider=None):
        """
        Initialize DataQualityService with QuestDB provider.

        Args:
            db_provider: QuestDBDataProvider instance for database access

        Raises:
            ValueError: If db_provider is None

        ✅ BUG-005 FIX: Now requires QuestDBDataProvider (was parameter-less)
        """
        if db_provider is None:
            raise ValueError(
                "QuestDBDataProvider is required for DataQualityService.\n"
                "Data must be loaded from QuestDB for quality assessment."
            )

        self.db_provider = db_provider

        # Quality thresholds
        self.expected_interval_ms = 1000  # 1 second
        self.gap_thresholds = {
            'minor': 5000,      # 5 seconds
            'moderate': 30000,  # 30 seconds
            'critical': 300000  # 5 minutes
        }
        self.max_quality_score = 100

    async def assess_session_quality(self, session_id: str, symbol: str) -> DataQualityMetrics:
        """
        Perform comprehensive quality assessment for a session.

        ✅ BUG-005 FIX: Now loads data from QuestDB instead of accepting data_points parameter

        Args:
            session_id: Session identifier
            symbol: Trading pair symbol to assess

        Returns:
            Complete quality metrics

        Raises:
            ValueError: If session not found or symbol has no data
        """
        try:
            # Load tick price data from QuestDB
            tick_prices = await self.db_provider.get_tick_prices(
                session_id=session_id,
                symbol=symbol
                # No limit - quality assessment needs full dataset
            )

            if not tick_prices:
                raise ValueError(f"No data found for session {session_id}, symbol {symbol}")

            # Convert QuestDB format to analysis format
            data_points = []
            for tick in tick_prices:
                # Convert timestamp if needed
                timestamp = tick.get('timestamp')
                if isinstance(timestamp, datetime):
                    timestamp = int(timestamp.timestamp() * 1000)  # milliseconds

                data_points.append({
                    'timestamp': timestamp,
                    'price': float(tick.get('price', 0)),
                    'volume': float(tick.get('volume', 0))
                })

            # Calculate individual quality components
            completeness = self._calculate_completeness(data_points)
            gaps = self._detect_gaps(data_points)
            anomalies = self._detect_anomalies(data_points)
            timestamp_issues = self._check_timestamp_ordering(data_points)

            # Calculate weighted overall score
            overall_score = self._calculate_overall_score(
                completeness=completeness,
                gap_count=len(gaps),
                anomaly_count=len(anomalies),
                timestamp_issues=timestamp_issues,
                total_points=len(data_points)
            )

            metrics = DataQualityMetrics(
                completeness_score=completeness,
                gap_count=len(gaps),
                total_gap_duration_ms=sum(gap.duration_ms for gap in gaps),
                anomaly_count=len(anomalies),
                data_points=len(data_points),
                missing_values=self._count_missing_values(data_points),
                unrealistic_values=len(anomalies),
                timestamp_issues=timestamp_issues,
                overall_score=overall_score
            )

            logger.info(f"Quality assessment for session {session_id}: score={overall_score:.1f}, "
                       f"gaps={len(gaps)}, anomalies={len(anomalies)}")
            return metrics

        except Exception as e:
            logger.error(f"Failed to assess quality for session {session_id}: {e}")
            # Return minimal metrics on error
            return DataQualityMetrics(
                completeness_score=0,
                gap_count=0,
                total_gap_duration_ms=0,
                anomaly_count=0,
                data_points=len(data_points),
                missing_values=0,
                unrealistic_values=0,
                timestamp_issues=1,
                overall_score=0
            )

    def _calculate_completeness(self, data_points: List[Dict[str, Any]]) -> float:
        """Calculate data completeness percentage"""
        if not data_points:
            return 0.0

        total_fields = 0
        valid_fields = 0

        for point in data_points:
            # Check required fields
            required_fields = ['timestamp', 'price', 'volume']

            for field in required_fields:
                total_fields += 1
                value = point.get(field)

                # Check if value is present and valid
                if value is not None and value != 0 and value != "":
                    # Additional validation for numeric fields
                    if field in ['price', 'volume']:
                        try:
                            float(value)
                            valid_fields += 1
                        except (ValueError, TypeError):
                            pass  # Invalid numeric value
                    else:
                        valid_fields += 1

        return (valid_fields / total_fields * 100) if total_fields > 0 else 0.0

    def _detect_gaps(self, data_points: List[Dict[str, Any]]) -> List[GapInfo]:
        """Detect gaps in time series data"""
        if len(data_points) < 2:
            return []

        gaps = []
        sorted_points = sorted(data_points, key=lambda x: x.get('timestamp', 0))

        for i in range(1, len(sorted_points)):
            current_time = sorted_points[i].get('timestamp', 0)
            previous_time = sorted_points[i-1].get('timestamp', 0)

            if current_time <= previous_time:
                continue  # Skip invalid timestamps

            gap_duration = current_time - previous_time
            expected_duration = self.expected_interval_ms

            # Check if gap exceeds minimum threshold
            if gap_duration > expected_duration * 2:
                missing_points = int(gap_duration / expected_duration) - 1

                # Determine severity
                severity = 'minor'
                if gap_duration >= self.gap_thresholds['critical']:
                    severity = 'critical'
                elif gap_duration >= self.gap_thresholds['moderate']:
                    severity = 'moderate'

                gap_info = GapInfo(
                    start_time=previous_time,
                    end_time=current_time,
                    duration_ms=gap_duration,
                    missing_points=missing_points,
                    severity=severity
                )
                gaps.append(gap_info)

        return gaps

    def _detect_anomalies(self, data_points: List[Dict[str, Any]]) -> List[AnomalyInfo]:
        """Detect data anomalies"""
        if len(data_points) < 10:  # Need minimum data for statistical analysis
            return []

        anomalies = []

        # Extract numeric fields for analysis
        prices = []
        volumes = []

        for point in data_points:
            try:
                price = float(point.get('price', 0))
                volume = float(point.get('volume', 0))

                if price > 0:
                    prices.append(price)
                if volume >= 0:  # Volume can be 0
                    volumes.append(volume)
            except (ValueError, TypeError):
                continue

        # Calculate statistical bounds
        price_bounds = self._calculate_statistical_bounds(prices)
        volume_bounds = self._calculate_statistical_bounds(volumes)

        # Check each point for anomalies
        for point in data_points:
            timestamp = point.get('timestamp', 0)

            # Check price anomalies
            try:
                price = float(point.get('price', 0))
                if price > 0 and not (price_bounds[0] <= price <= price_bounds[1]):
                    anomalies.append(AnomalyInfo(
                        timestamp=timestamp,
                        field='price',
                        value=price,
                        expected_range=price_bounds,
                        severity='high' if price > price_bounds[1] * 2 else 'medium'
                    ))
            except (ValueError, TypeError):
                pass

            # Check volume anomalies
            try:
                volume = float(point.get('volume', 0))
                if volume >= 0 and not (volume_bounds[0] <= volume <= volume_bounds[1]):
                    anomalies.append(AnomalyInfo(
                        timestamp=timestamp,
                        field='volume',
                        value=volume,
                        expected_range=volume_bounds,
                        severity='high' if volume > volume_bounds[1] * 3 else 'medium'
                    ))
            except (ValueError, TypeError):
                pass

        return anomalies

    def _calculate_statistical_bounds(self, values: List[float], z_threshold: float = 3.0) -> Tuple[float, float]:
        """Calculate statistical bounds using z-score method"""
        if len(values) < 3:
            # Fallback to simple range
            return min(values), max(values)

        try:
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)

            lower_bound = mean - (z_threshold * stdev)
            upper_bound = mean + (z_threshold * stdev)

            # Ensure bounds are reasonable
            lower_bound = max(lower_bound, min(values) * 0.1)  # Don't go below 10% of min
            upper_bound = min(upper_bound, max(values) * 10)   # Don't go above 10x max

            return lower_bound, upper_bound

        except statistics.StatisticsError:
            # Fallback to percentile method
            sorted_values = sorted(values)
            lower_idx = int(len(sorted_values) * 0.01)  # 1st percentile
            upper_idx = int(len(sorted_values) * 0.99)  # 99th percentile

            return sorted_values[lower_idx], sorted_values[upper_idx]

    def _check_timestamp_ordering(self, data_points: List[Dict[str, Any]]) -> int:
        """Check for timestamp ordering issues"""
        if not data_points:
            return 0

        issues = 0
        previous_time = None

        for point in data_points:
            current_time = point.get('timestamp')
            if current_time is None:
                issues += 1
                continue

            if previous_time is not None and current_time < previous_time:
                issues += 1

            previous_time = current_time

        return issues

    def _count_missing_values(self, data_points: List[Dict[str, Any]]) -> int:
        """Count total missing values across all fields"""
        missing_count = 0

        for point in data_points:
            for field in ['timestamp', 'price', 'volume']:
                value = point.get(field)
                if value is None or value == "" or str(value).lower() in ['null', 'none']:
                    missing_count += 1

        return missing_count

    def _calculate_overall_score(self, completeness: float, gap_count: int,
                               anomaly_count: int, timestamp_issues: int,
                               total_points: int) -> float:
        """Calculate weighted overall quality score"""
        if total_points == 0:
            return 0.0

        # Base score from completeness
        score = completeness

        # Penalty for gaps (weighted by severity and count)
        gap_penalty = min(30, gap_count * 2)
        score -= gap_penalty

        # Penalty for anomalies
        anomaly_penalty = min(20, anomaly_count * 1.5)
        score -= anomaly_penalty

        # Penalty for timestamp issues
        timestamp_penalty = min(15, timestamp_issues * 3)
        score -= timestamp_penalty

        # Bonus for large datasets (more data = potentially better quality)
        if total_points > 1000:
            score += 5
        elif total_points > 100:
            score += 2

        return max(0.0, min(100.0, score))

    async def get_quality_report(self, session_id: str, symbol: str) -> Dict[str, Any]:
        """
        Generate detailed quality report with recommendations.

        ✅ BUG-005 FIX: Now loads data from QuestDB instead of accepting data_points parameter

        Args:
            session_id: Session identifier
            symbol: Trading pair symbol to assess

        Returns:
            Detailed quality report with recommendations
        """
        try:
            # Load data and assess quality (single call now)
            metrics = await self.assess_session_quality(session_id, symbol)

            # Load data again for gap/anomaly details
            # (Already loaded in assess_session_quality, but kept separate for clarity)
            tick_prices = await self.db_provider.get_tick_prices(
                session_id=session_id,
                symbol=symbol
            )

            # Convert to analysis format
            data_points = []
            for tick in tick_prices:
                timestamp = tick.get('timestamp')
                if isinstance(timestamp, datetime):
                    timestamp = int(timestamp.timestamp() * 1000)

                data_points.append({
                    'timestamp': timestamp,
                    'price': float(tick.get('price', 0)),
                    'volume': float(tick.get('volume', 0))
                })

            gaps = self._detect_gaps(data_points)
            anomalies = self._detect_anomalies(data_points)

            # Generate recommendations
            recommendations = self._generate_recommendations(metrics, gaps, anomalies)

            report = {
                'session_id': session_id,
                'assessment_timestamp': datetime.utcnow().isoformat(),
                'metrics': {
                    'overall_score': metrics.overall_score,
                    'completeness_score': metrics.completeness_score,
                    'gap_count': metrics.gap_count,
                    'anomaly_count': metrics.anomaly_count,
                    'data_points': metrics.data_points,
                    'missing_values': metrics.missing_values,
                    'timestamp_issues': metrics.timestamp_issues
                },
                'gaps': [
                    {
                        'start_time': gap.start_time,
                        'end_time': gap.end_time,
                        'duration_ms': gap.duration_ms,
                        'missing_points': gap.missing_points,
                        'severity': gap.severity
                    } for gap in gaps[:10]  # Limit to top 10
                ],
                'anomalies': [
                    {
                        'timestamp': anomaly.timestamp,
                        'field': anomaly.field,
                        'value': anomaly.value,
                        'expected_range': anomaly.expected_range,
                        'severity': anomaly.severity
                    } for anomaly in anomalies[:10]  # Limit to top 10
                ],
                'recommendations': recommendations
            }

            return report

        except Exception as e:
            logger.error(f"Failed to generate quality report for session {session_id}: {e}")
            return {
                'session_id': session_id,
                'error': str(e),
                'metrics': {'overall_score': 0}
            }

    def _generate_recommendations(self, metrics: DataQualityMetrics,
                                gaps: List[GapInfo], anomalies: List[AnomalyInfo]) -> List[str]:
        """Generate improvement recommendations based on quality assessment"""
        recommendations = []

        # Completeness recommendations
        if metrics.completeness_score < 80:
            recommendations.append("Improve data completeness - consider increasing collection frequency or fixing data source issues")

        # Gap recommendations
        if metrics.gap_count > 0:
            critical_gaps = [g for g in gaps if g.severity == 'critical']
            if critical_gaps:
                recommendations.append(f"Address {len(critical_gaps)} critical data gaps - review connection stability")
            else:
                recommendations.append(f"Monitor {metrics.gap_count} data gaps - may indicate temporary connection issues")

        # Anomaly recommendations
        if metrics.anomaly_count > 0:
            price_anomalies = [a for a in anomalies if a.field == 'price']
            volume_anomalies = [a for a in anomalies if a.field == 'volume']

            if price_anomalies:
                recommendations.append(f"Review {len(price_anomalies)} price anomalies - may indicate data feed issues")
            if volume_anomalies:
                recommendations.append(f"Investigate {len(volume_anomalies)} volume anomalies - check for data corruption")

        # Timestamp recommendations
        if metrics.timestamp_issues > 0:
            recommendations.append(f"Fix {metrics.timestamp_issues} timestamp ordering issues - ensure monotonic timestamps")

        # Overall score recommendations
        if metrics.overall_score < 70:
            recommendations.append("Overall data quality needs improvement - consider implementing data validation at collection time")
        elif metrics.overall_score >= 90:
            recommendations.append("Data quality is excellent - maintain current collection practices")

        # Data volume recommendations
        if metrics.data_points < 100:
            recommendations.append("Low data volume detected - extend collection duration or increase frequency")

        return recommendations if recommendations else ["Data quality is acceptable - continue monitoring"]