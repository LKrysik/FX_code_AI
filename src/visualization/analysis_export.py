"""
Analysis Export Module
======================
Export and analysis tools for backtest results with configuration context
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from ..core.logger import StructuredLogger


class TradingAnalysisExporter:
    """Export and analyze trading results with configuration impact analysis"""
    
    def __init__(self, logger: StructuredLogger):
        self.logger = logger
    
    def export_comprehensive_analysis(
        self, 
        symbol: str,
        signals_data: List[Dict],
        trades_data: List[Dict],
        price_data: List[Dict],
        config_data: Dict,
        backtest_metadata: Dict,
        output_dir: str = "backtest_results"
    ) -> Dict[str, str]:
        """Export comprehensive analysis with multiple formats"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{symbol}_analysis_{timestamp}"
        
        exported_files = {}
        
        # 1. Export detailed CSV data
        csv_path = self._export_csv_data(
            symbol, signals_data, trades_data, price_data, 
            output_path, base_filename
        )
        exported_files['csv'] = csv_path
        
        # 2. Export JSON analysis
        json_path = self._export_json_analysis(
            symbol, signals_data, trades_data, config_data, 
            backtest_metadata, output_path, base_filename
        )
        exported_files['json'] = json_path
        
        # 3. Export configuration impact report
        config_report_path = self._export_configuration_impact_report(
            symbol, signals_data, trades_data, config_data,
            output_path, base_filename
        )
        exported_files['config_report'] = config_report_path
        
        # 4. Export performance metrics
        metrics_path = self._export_performance_metrics(
            symbol, trades_data, config_data, output_path, base_filename
        )
        exported_files['metrics'] = metrics_path
        
        self.logger.info("analysis_export.comprehensive_export_complete", {
            "symbol": symbol,
            "files_exported": len(exported_files),
            "output_directory": str(output_path)
        })
        
        return exported_files
    
    def _export_csv_data(
        self, 
        symbol: str, 
        signals_data: List[Dict], 
        trades_data: List[Dict], 
        price_data: List[Dict],
        output_path: Path, 
        base_filename: str
    ) -> str:
        """Export raw data to CSV files"""
        
        # Signals CSV
        if signals_data:
            df_signals = pd.DataFrame(signals_data)
            signals_csv = output_path / f"{base_filename}_signals.csv"
            df_signals.to_csv(signals_csv, index=False)
        
        # Trades CSV
        if trades_data:
            df_trades = pd.DataFrame(trades_data)
            trades_csv = output_path / f"{base_filename}_trades.csv"
            df_trades.to_csv(trades_csv, index=False)
        
        # Price data CSV (sample for large datasets)
        if price_data:
            df_price = pd.DataFrame(price_data)
            if len(df_price) > 10000:  # Sample large datasets
                df_price = df_price.sample(n=10000).sort_values('timestamp')
            price_csv = output_path / f"{base_filename}_price_data.csv"
            df_price.to_csv(price_csv, index=False)
        
        return str(output_path / f"{base_filename}_data.csv")
    
    def _export_json_analysis(
        self,
        symbol: str,
        signals_data: List[Dict],
        trades_data: List[Dict],
        config_data: Dict,
        backtest_metadata: Dict,
        output_path: Path,
        base_filename: str
    ) -> str:
        """Export comprehensive JSON analysis"""
        
        analysis = {
            "metadata": {
                "symbol": symbol,
                "export_timestamp": datetime.now().isoformat(),
                "backtest_metadata": backtest_metadata,
                "configuration_hash": backtest_metadata.get('configuration_hash'),
            },
            "configuration_analysis": self._analyze_configuration_impact(
                signals_data, trades_data, config_data
            ),
            "signal_analysis": self._analyze_signals(signals_data, config_data),
            "trade_analysis": self._analyze_trades(trades_data, config_data),
            "performance_summary": self._calculate_performance_summary(trades_data),
            "risk_analysis": self._analyze_risk_metrics(trades_data, config_data),
            "optimization_suggestions": self._generate_optimization_suggestions(
                signals_data, trades_data, config_data
            )
        }
        
        json_path = output_path / f"{base_filename}_analysis.json"
        with open(json_path, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        return str(json_path)
    
    def _analyze_configuration_impact(
        self, 
        signals_data: List[Dict], 
        trades_data: List[Dict], 
        config_data: Dict
    ) -> Dict[str, Any]:
        """Analyze how configuration parameters impacted results"""
        
        if not config_data:
            return {}
        
        detection_params = config_data.get('detection_params', {})
        risk_params = config_data.get('risk_params', {})
        
        # Analyze signal detection efficiency
        signal_efficiency = {}
        if signals_data:
            magnitudes = [s.get('magnitude', 0) for s in signals_data]
            min_threshold = detection_params.get('min_pump_magnitude', 7.0)
            max_threshold = detection_params.get('max_pump_magnitude', 50.0)
            
            signal_efficiency = {
                'total_signals': len(signals_data),
                'signals_above_min': len([m for m in magnitudes if m >= min_threshold]),
                'signals_above_max': len([m for m in magnitudes if m >= max_threshold]),
                'average_magnitude': sum(magnitudes) / len(magnitudes) if magnitudes else 0,
                'magnitude_efficiency': (sum(magnitudes) / len(magnitudes)) / min_threshold if magnitudes and min_threshold > 0 else 0,
            }
        
        # Analyze risk parameter effectiveness
        risk_effectiveness = {}
        if trades_data:
            leverages = [t.get('leverage', 1) for t in trades_data]
            position_sizes = [t.get('size', 0) for t in trades_data]
            max_leverage = risk_params.get('max_leverage', 3.0)
            max_position = risk_params.get('max_position_size_usdt', 500)
            
            risk_effectiveness = {
                'average_leverage_used': sum(leverages) / len(leverages) if leverages else 0,
                'leverage_utilization_pct': (sum(leverages) / len(leverages)) / max_leverage * 100 if leverages and max_leverage > 0 else 0,
                'average_position_size': sum(position_sizes) / len(position_sizes) if position_sizes else 0,
                'position_size_utilization_pct': (sum(position_sizes) / len(position_sizes)) / max_position * 100 if position_sizes and max_position > 0 else 0,
            }
        
        return {
            'signal_detection_efficiency': signal_efficiency,
            'risk_parameter_effectiveness': risk_effectiveness,
            'configuration_utilization': {
                'detection_window': detection_params.get('window_s', 60),
                'cooldown_period': detection_params.get('cooldown_s', 1800),
                'volume_threshold': detection_params.get('volume_surge_multiplier', 3.0),
            }
        }
    
    def _analyze_signals(self, signals_data: List[Dict], config_data: Dict) -> Dict[str, Any]:
        """Analyze signal characteristics and quality"""
        
        if not signals_data:
            return {}
        
        df_signals = pd.DataFrame(signals_data)
        
        return {
            'total_signals': len(signals_data),
            'signal_quality_distribution': {
                'high_confidence': len(df_signals[df_signals['confidence'] >= 80]),
                'medium_confidence': len(df_signals[(df_signals['confidence'] >= 60) & (df_signals['confidence'] < 80)]),
                'low_confidence': len(df_signals[df_signals['confidence'] < 60]),
            },
            'magnitude_analysis': {
                'min_magnitude': df_signals['magnitude'].min(),
                'max_magnitude': df_signals['magnitude'].max(),
                'avg_magnitude': df_signals['magnitude'].mean(),
                'median_magnitude': df_signals['magnitude'].median(),
            },
            'volume_analysis': {
                'min_volume_surge': df_signals['volume_surge'].min(),
                'max_volume_surge': df_signals['volume_surge'].max(),
                'avg_volume_surge': df_signals['volume_surge'].mean(),
            },
            'temporal_analysis': {
                'signals_per_hour': self._calculate_signals_per_hour(df_signals),
                'peak_detection_hours': self._find_peak_detection_hours(df_signals),
            }
        }
    
    def _analyze_trades(self, trades_data: List[Dict], config_data: Dict) -> Dict[str, Any]:
        """Analyze trade execution and outcomes"""
        
        if not trades_data:
            return {}
        
        df_trades = pd.DataFrame(trades_data)
        
        # Filter completed trades
        completed_trades = df_trades[df_trades['exit_time'].notna()]
        
        return {
            'execution_analysis': {
                'total_trades': len(trades_data),
                'completed_trades': len(completed_trades),
                'completion_rate': len(completed_trades) / len(trades_data) * 100 if trades_data else 0,
            },
            'outcome_analysis': {
                'winning_trades': len(completed_trades[completed_trades['pnl'] > 0]) if not completed_trades.empty else 0,
                'losing_trades': len(completed_trades[completed_trades['pnl'] <= 0]) if not completed_trades.empty else 0,
                'win_rate': len(completed_trades[completed_trades['pnl'] > 0]) / len(completed_trades) * 100 if not completed_trades.empty else 0,
            },
            'duration_analysis': {
                'avg_trade_duration_minutes': completed_trades['duration_minutes'].mean() if not completed_trades.empty else 0,
                'min_duration': completed_trades['duration_minutes'].min() if not completed_trades.empty else 0,
                'max_duration': completed_trades['duration_minutes'].max() if not completed_trades.empty else 0,
            },
            'exit_reason_analysis': {
                'stop_loss_exits': len(completed_trades[completed_trades['close_reason'].str.contains('stop_loss', na=False)]) if not completed_trades.empty else 0,
                'take_profit_exits': len(completed_trades[completed_trades['close_reason'].str.contains('take_profit', na=False)]) if not completed_trades.empty else 0,
                'emergency_exits': len(completed_trades[completed_trades['close_reason'].str.contains('emergency', na=False)]) if not completed_trades.empty else 0,
            }
        }
    
    def _calculate_performance_summary(self, trades_data: List[Dict]) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        
        if not trades_data:
            return {}
        
        df_trades = pd.DataFrame(trades_data)
        completed_trades = df_trades[df_trades['exit_time'].notna()]
        
        if completed_trades.empty:
            return {}
        
        total_pnl = completed_trades['pnl'].sum()
        winning_trades = completed_trades[completed_trades['pnl'] > 0]
        losing_trades = completed_trades[completed_trades['pnl'] <= 0]
        
        return {
            'profitability': {
                'total_pnl': total_pnl,
                'average_pnl_per_trade': completed_trades['pnl'].mean(),
                'best_trade': completed_trades['pnl'].max(),
                'worst_trade': completed_trades['pnl'].min(),
                'profit_factor': abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if not losing_trades.empty and losing_trades['pnl'].sum() != 0 else float('inf'),
            },
            'consistency': {
                'win_rate': len(winning_trades) / len(completed_trades) * 100,
                'average_win': winning_trades['pnl'].mean() if not winning_trades.empty else 0,
                'average_loss': losing_trades['pnl'].mean() if not losing_trades.empty else 0,
                'largest_winning_streak': self._calculate_largest_streak(completed_trades, True),
                'largest_losing_streak': self._calculate_largest_streak(completed_trades, False),
            },
            'risk_metrics': {
                'sharpe_ratio': self._calculate_sharpe_ratio(completed_trades['pnl']),
                'max_drawdown': self._calculate_max_drawdown(completed_trades),
                'recovery_factor': total_pnl / abs(self._calculate_max_drawdown(completed_trades)) if self._calculate_max_drawdown(completed_trades) != 0 else float('inf'),
            }
        }
    
    def _analyze_risk_metrics(self, trades_data: List[Dict], config_data: Dict) -> Dict[str, Any]:
        """Analyze risk management effectiveness"""
        
        if not trades_data:
            return {}
        
        df_trades = pd.DataFrame(trades_data)
        completed_trades = df_trades[df_trades['exit_time'].notna()]
        
        if completed_trades.empty:
            return {}
        
        return {
            'leverage_analysis': {
                'average_leverage': completed_trades['leverage'].mean(),
                'max_leverage_used': completed_trades['leverage'].max(),
                'leverage_efficiency': self._calculate_leverage_efficiency(completed_trades),
            },
            'position_sizing': {
                'average_position_size': completed_trades['size'].mean(),
                'position_size_consistency': completed_trades['size'].std(),
                'size_vs_performance_correlation': completed_trades['size'].corr(completed_trades['pnl']),
            },
            'stop_loss_effectiveness': {
                'stop_loss_hit_rate': len(completed_trades[completed_trades['close_reason'].str.contains('stop_loss', na=False)]) / len(completed_trades) * 100,
                'average_stop_loss_distance': self._calculate_avg_stop_distance(completed_trades),
            }
        }
    
    def _generate_optimization_suggestions(
        self, 
        signals_data: List[Dict], 
        trades_data: List[Dict], 
        config_data: Dict
    ) -> List[Dict[str, str]]:
        """Generate optimization suggestions based on analysis"""
        
        suggestions = []
        
        if not signals_data or not trades_data:
            return suggestions
        
        df_signals = pd.DataFrame(signals_data)
        df_trades = pd.DataFrame(trades_data)
        completed_trades = df_trades[df_trades['exit_time'].notna()]
        
        # Signal quality suggestions
        if not df_signals.empty:
            avg_confidence = df_signals['confidence'].mean()
            if avg_confidence < 70:
                suggestions.append({
                    'category': 'Signal Quality',
                    'suggestion': f'Consider increasing detection thresholds. Average confidence is {avg_confidence:.1f}%',
                    'priority': 'high'
                })
        
        # Win rate suggestions
        if not completed_trades.empty:
            win_rate = len(completed_trades[completed_trades['pnl'] > 0]) / len(completed_trades) * 100
            if win_rate < 50:
                suggestions.append({
                    'category': 'Strategy Performance',
                    'suggestion': f'Win rate is {win_rate:.1f}%. Consider tightening entry conditions or adjusting risk management',
                    'priority': 'high'
                })
        
        # Risk management suggestions
        if config_data and not completed_trades.empty:
            avg_leverage = completed_trades['leverage'].mean()
            max_leverage = config_data.get('risk_params', {}).get('max_leverage', 3.0)
            
            if avg_leverage < max_leverage * 0.5:
                suggestions.append({
                    'category': 'Risk Management',
                    'suggestion': f'Low leverage utilization ({avg_leverage:.1f}x avg vs {max_leverage}x max). Consider increasing position sizes',
                    'priority': 'medium'
                })
        
        return suggestions
    
    def _calculate_signals_per_hour(self, df_signals: pd.DataFrame) -> float:
        """Calculate average signals per hour"""
        if df_signals.empty:
            return 0
        
        df_signals['timestamp'] = pd.to_datetime(df_signals['timestamp'])
        time_span = (df_signals['timestamp'].max() - df_signals['timestamp'].min()).total_seconds() / 3600
        return len(df_signals) / time_span if time_span > 0 else 0
    
    def _find_peak_detection_hours(self, df_signals: pd.DataFrame) -> List[int]:
        """Find hours with most signal detections"""
        if df_signals.empty:
            return []
        
        df_signals['timestamp'] = pd.to_datetime(df_signals['timestamp'])
        df_signals['hour'] = df_signals['timestamp'].dt.hour
        hourly_counts = df_signals['hour'].value_counts()
        return hourly_counts.head(3).index.tolist()
    
    def _calculate_largest_streak(self, df_trades: pd.DataFrame, winning: bool) -> int:
        """Calculate largest winning or losing streak"""
        if df_trades.empty:
            return 0
        
        df_sorted = df_trades.sort_values('entry_time')
        wins = (df_sorted['pnl'] > 0) if winning else (df_sorted['pnl'] <= 0)
        
        max_streak = 0
        current_streak = 0
        
        for win in wins:
            if win:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate Sharpe ratio"""
        if returns.empty or returns.std() == 0:
            return 0
        return returns.mean() / returns.std()
    
    def _calculate_max_drawdown(self, df_trades: pd.DataFrame) -> float:
        """Calculate maximum drawdown"""
        if df_trades.empty:
            return 0
        
        df_sorted = df_trades.sort_values('entry_time')
        cumulative_pnl = df_sorted['pnl'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = cumulative_pnl - running_max
        return drawdown.min()
    
    def _calculate_leverage_efficiency(self, df_trades: pd.DataFrame) -> float:
        """Calculate leverage efficiency (return per unit of leverage)"""
        if df_trades.empty:
            return 0
        
        total_return = df_trades['pnl'].sum()
        total_leverage_used = df_trades['leverage'].sum()
        return total_return / total_leverage_used if total_leverage_used > 0 else 0
    
    def _calculate_avg_stop_distance(self, df_trades: pd.DataFrame) -> float:
        """Calculate average stop loss distance as percentage"""
        if df_trades.empty:
            return 0
        
        stop_distances = []
        for _, trade in df_trades.iterrows():
            if pd.notna(trade['stop_loss']) and trade['entry_price'] > 0:
                distance = abs(trade['stop_loss'] - trade['entry_price']) / trade['entry_price'] * 100
                stop_distances.append(distance)
        
        return sum(stop_distances) / len(stop_distances) if stop_distances else 0
    
    def _export_configuration_impact_report(
        self,
        symbol: str,
        signals_data: List[Dict],
        trades_data: List[Dict],
        config_data: Dict,
        output_path: Path,
        base_filename: str
    ) -> str:
        """Export detailed configuration impact report"""
        
        config_analysis = self._analyze_configuration_impact(signals_data, trades_data, config_data)
        
        report = {
            'symbol': symbol,
            'report_timestamp': datetime.now().isoformat(),
            'configuration_summary': config_data,
            'impact_analysis': config_analysis,
            'recommendations': self._generate_configuration_recommendations(config_analysis, config_data)
        }
        
        report_path = output_path / f"{base_filename}_config_impact.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return str(report_path)
    
    def _export_performance_metrics(
        self,
        symbol: str,
        trades_data: List[Dict],
        config_data: Dict,
        output_path: Path,
        base_filename: str
    ) -> str:
        """Export performance metrics summary"""
        
        performance = self._calculate_performance_summary(trades_data)
        risk_analysis = self._analyze_risk_metrics(trades_data, config_data)
        
        metrics = {
            'symbol': symbol,
            'export_timestamp': datetime.now().isoformat(),
            'performance_summary': performance,
            'risk_analysis': risk_analysis,
            'configuration_context': config_data
        }
        
        metrics_path = output_path / f"{base_filename}_performance.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        
        return str(metrics_path)
    
    def _generate_configuration_recommendations(
        self, 
        config_analysis: Dict, 
        current_config: Dict
    ) -> List[Dict[str, str]]:
        """Generate specific configuration recommendations"""
        
        recommendations = []
        
        signal_efficiency = config_analysis.get('signal_detection_efficiency', {})
        risk_effectiveness = config_analysis.get('risk_parameter_effectiveness', {})
        
        # Signal detection recommendations
        if signal_efficiency.get('magnitude_efficiency', 0) < 1.5:
            recommendations.append({
                'parameter': 'min_pump_magnitude',
                'current_value': str(current_config.get('detection_params', {}).get('min_pump_magnitude', 7.0)),
                'recommendation': 'Consider lowering minimum magnitude threshold to capture more signals',
                'impact': 'More signals, potentially lower quality'
            })
        
        # Risk management recommendations
        leverage_util = risk_effectiveness.get('leverage_utilization_pct', 0)
        if leverage_util < 50:
            recommendations.append({
                'parameter': 'max_leverage',
                'current_value': str(current_config.get('risk_params', {}).get('max_leverage', 3.0)),
                'recommendation': 'Low leverage utilization. Consider increasing max leverage or position sizes',
                'impact': 'Higher potential returns, increased risk'
            })
        
        return recommendations