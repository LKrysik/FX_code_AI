"""
Trading Chart Generator
=======================
Interactive charts for analyzing trading results with trade visualization
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

from ..core.logger import StructuredLogger
from ..visualization.analysis_export import TradingAnalysisExporter


class TradingChartGenerator:
    """Generates interactive charts for trading analysis"""
    
    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.trades_data = []
        self.price_data = []
        self.flash_pump_signals = []
        self.config_data = {}  # Store configuration parameters for analysis
        self.backtest_metadata = {}  # Store backtest session metadata
        self.analysis_exporter = TradingAnalysisExporter(logger)
    
    def set_configuration(self, symbol_config: Dict[str, Any], main_config: Dict[str, Any]):
        """Store configuration parameters for visualization context"""
        self.config_data = {
            'symbol_config': symbol_config,
            'main_config': main_config,
            'detection_params': {
                'window_s': symbol_config.get('detection_parameters', {}).get('window_s', 60),
                'up_threshold_pct': symbol_config.get('detection_parameters', {}).get('up_threshold_pct', 7.0),
                'down_threshold_pct': symbol_config.get('detection_parameters', {}).get('down_threshold_pct', 7.0),
                'cooldown_s': symbol_config.get('detection_parameters', {}).get('cooldown_s', 1800),
                'min_pump_magnitude': symbol_config.get('flash_pump_detection', {}).get('min_pump_magnitude', 7.0),
                'max_pump_magnitude': symbol_config.get('flash_pump_detection', {}).get('max_pump_magnitude', 50.0),
                'volume_surge_multiplier': symbol_config.get('flash_pump_detection', {}).get('volume_surge_multiplier', 3.0),
                'price_velocity_threshold': symbol_config.get('flash_pump_detection', {}).get('price_velocity_threshold', 0.5),
            },
            'risk_params': {
                'base_risk_pct': symbol_config.get('position_sizing', {}).get('base_risk_pct', 1.0),
                'max_position_size_usdt': symbol_config.get('position_sizing', {}).get('max_position_size_usdt', 500),
                'max_leverage': symbol_config.get('position_sizing', {}).get('max_leverage', 3.0),
                'stop_loss_peak_buffer': symbol_config.get('risk_management', {}).get('stop_loss', {}).get('peak_buffer_pct', 3.0),
                'take_profit_levels': symbol_config.get('risk_management', {}).get('take_profit', {}).get('levels', []),
            },
            'entry_conditions': symbol_config.get('entry_conditions', {}),
            'emergency_exits': symbol_config.get('risk_management', {}).get('emergency_exits', {}),
        }
    
    def set_backtest_metadata(self, metadata: Dict[str, Any]):
        """Store backtest session metadata"""
        self.backtest_metadata = metadata
        
    def add_price_data(self, timestamp: str, price: float, volume: float):
        """Add price data point"""
        # Handle both Unix timestamp and ISO string formats
        if isinstance(timestamp, (int, float)):
            # Unix timestamp
            timestamp_dt = pd.to_datetime(timestamp, unit='s')
        elif isinstance(timestamp, str) and timestamp.replace('.', '').replace('-', '').isdigit():
            # String that looks like a Unix timestamp
            timestamp_dt = pd.to_datetime(float(timestamp), unit='s')
        else:
            # ISO string or other datetime format
            timestamp_dt = pd.to_datetime(timestamp)
            
        self.price_data.append({
            'timestamp': timestamp_dt,
            'price': price,
            'volume': volume
        })
    
    def add_flash_pump_signal(self, signal_data: Dict[str, Any]):
        """Add flash pump detection signal"""
        timestamp = signal_data.get('timestamp')
        
        # Handle both Unix timestamp and ISO string formats
        if isinstance(timestamp, (int, float)):
            # Unix timestamp
            timestamp_dt = pd.to_datetime(timestamp, unit='s')
        elif isinstance(timestamp, str) and timestamp.replace('.', '').replace('-', '').isdigit():
            # String that looks like a Unix timestamp
            timestamp_dt = pd.to_datetime(float(timestamp), unit='s')
        else:
            # ISO string or other datetime format
            timestamp_dt = pd.to_datetime(timestamp)
            
        self.flash_pump_signals.append({
            'timestamp': timestamp_dt,
            'price': signal_data.get('price'),
            'magnitude': signal_data.get('magnitude', 0),
            'volume_surge': signal_data.get('volume_surge', 0),
            'confidence': signal_data.get('confidence', 0),
            'signal_id': signal_data.get('signal_id', len(self.flash_pump_signals))
        })
    
    def add_trade(self, trade_data: Dict[str, Any]):
        """Add trade execution data"""
        def convert_timestamp(timestamp):
            if timestamp is None:
                return None
            if isinstance(timestamp, (int, float)):
                # Unix timestamp
                return pd.to_datetime(timestamp, unit='s')
            elif isinstance(timestamp, str) and timestamp.replace('.', '').replace('-', '').isdigit():
                # String that looks like a Unix timestamp
                return pd.to_datetime(float(timestamp), unit='s')
            else:
                # ISO string or other datetime format
                return pd.to_datetime(timestamp)
        
        self.trades_data.append({
            'trade_id': trade_data.get('trade_id'),
            'entry_time': convert_timestamp(trade_data.get('entry_time')),
            'exit_time': convert_timestamp(trade_data.get('exit_time')),
            'entry_price': trade_data.get('entry_price'),
            'exit_price': trade_data.get('exit_price'),
            'stop_loss': trade_data.get('stop_loss'),
            'take_profit_levels': trade_data.get('take_profit_levels', []),
            'size': trade_data.get('size'),
            'leverage': trade_data.get('leverage'),
            'pnl': trade_data.get('pnl', 0),
            'pnl_pct': trade_data.get('pnl_pct', 0),
            'duration_minutes': trade_data.get('duration_minutes', 0),
            'close_reason': trade_data.get('close_reason', 'unknown'),
            'risk_reward': trade_data.get('risk_reward', 0),
            'max_drawdown': trade_data.get('max_drawdown', 0),
            'signal_id': trade_data.get('signal_id')
        })
    
    def update_trade_exit(self, exit_data: Dict[str, Any]):
        """Update existing trade with exit information"""
        trade_id = exit_data.get('trade_id')
        if not trade_id:
            return
        
        # Find and update the trade
        for trade in self.trades_data:
            if trade.get('trade_id') == trade_id:
                # Convert timestamp if needed
                exit_time = exit_data.get('exit_time')
                if exit_time is not None:
                    if isinstance(exit_time, (int, float)):
                        exit_time = pd.to_datetime(exit_time, unit='s')
                    elif isinstance(exit_time, str) and exit_time.replace('.', '').replace('-', '').isdigit():
                        exit_time = pd.to_datetime(float(exit_time), unit='s')
                    else:
                        exit_time = pd.to_datetime(exit_time)
                
                # Update trade data
                trade.update({
                    'exit_time': exit_time,
                    'exit_price': exit_data.get('exit_price'),
                    'pnl': exit_data.get('pnl', 0),
                    'pnl_pct': exit_data.get('pnl_percentage', 0),
                    'duration_minutes': exit_data.get('duration', 0) / 60 if exit_data.get('duration') else 0,
                    'close_reason': exit_data.get('exit_reason', 'unknown')
                })
                break
    
    def generate_interactive_chart(self, symbol: str, output_dir: str = "results") -> str:
        """Generate comprehensive interactive chart"""
        
        if not self.price_data:
            self.logger.warning("chart_generator.no_price_data", {"symbol": symbol})
            return ""
        
        # Convert to DataFrames
        df_price = pd.DataFrame(self.price_data)
        df_trades = pd.DataFrame(self.trades_data) if self.trades_data else pd.DataFrame()
        df_signals = pd.DataFrame(self.flash_pump_signals) if self.flash_pump_signals else pd.DataFrame()
        
        # Create enhanced subplots with risk metrics panel
        fig = make_subplots(
            rows=5, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            subplot_titles=(
                f'{symbol} Price Chart with Flash Pump Signals & Trades',
                'Volume',
                'Trade P&L',
                'Cumulative Performance',
                'Risk Metrics & Configuration Analysis'
            ),
            row_heights=[0.4, 0.15, 0.15, 0.15, 0.15],
            specs=[[{"secondary_y": False}],
                   [{"secondary_y": False}],
                   [{"secondary_y": False}],
                   [{"secondary_y": False}],
                   [{"secondary_y": True}]]  # Risk metrics with dual y-axis
        )
        
        # 1. Price Chart
        fig.add_trace(
            go.Scatter(
                x=df_price['timestamp'],
                y=df_price['price'],
                mode='lines',
                name='Price',
                line=dict(color='#2E86AB', width=1),
                hovertemplate='<b>Price</b><br>' +
                            'Time: %{x}<br>' +
                            'Price: $%{y:.6f}<br>' +
                            '<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 2. Enhanced Flash Pump Signals with Configuration Context
        if not df_signals.empty:
            # Create color scale based on configuration compliance
            colors = []
            sizes = []
            for _, signal in df_signals.iterrows():
                magnitude = signal.get('magnitude', 0)
                confidence = signal.get('confidence', 0)
                
                # Color based on how well signal meets configured thresholds
                if magnitude >= self.config_data.get('detection_params', {}).get('max_pump_magnitude', 50):
                    colors.append('purple')  # Exceeds max threshold
                elif magnitude >= self.config_data.get('detection_params', {}).get('min_pump_magnitude', 7) * 1.5:
                    colors.append('darkred')  # Strong signal
                elif magnitude >= self.config_data.get('detection_params', {}).get('min_pump_magnitude', 7):
                    colors.append('red')  # Meets minimum
                else:
                    colors.append('orange')  # Below threshold (shouldn't happen)
                
                # Size based on confidence and magnitude combined
                size = 8 + (confidence / 10) + (magnitude / 5)
                sizes.append(min(size, 20))  # Cap at 20
            
            fig.add_trace(
                go.Scatter(
                    x=df_signals['timestamp'],
                    y=df_signals['price'],
                    mode='markers',
                    name='Flash Pump Detected',
                    marker=dict(
                        color=colors,
                        size=sizes,
                        symbol='triangle-up',
                        line=dict(color='darkred', width=2)
                    ),
                    hovertemplate='<b>🚀 Flash Pump Signal</b><br>' +
                                '<b>Basic Info:</b><br>' +
                                'Time: %{x}<br>' +
                                'Price: $%{y:.6f}<br>' +
                                'Signal ID: %{customdata[0]}<br>' +
                                '<br><b>Detection Metrics:</b><br>' +
                                'Magnitude: %{customdata[1]:.2f}%<br>' +
                                'Volume Surge: %{customdata[2]:.1f}x<br>' +
                                'Confidence: %{customdata[3]:.1f}%<br>' +
                                'Direction: %{customdata[4]}<br>' +
                                '<br><b>Configuration Context:</b><br>' +
                                'Min Threshold: ' + str(self.config_data.get('detection_params', {}).get('min_pump_magnitude', 7.0)) + '%<br>' +
                                'Max Threshold: ' + str(self.config_data.get('detection_params', {}).get('max_pump_magnitude', 50.0)) + '%<br>' +
                                'Volume Multiplier: ' + str(self.config_data.get('detection_params', {}).get('volume_surge_multiplier', 3.0)) + 'x<br>' +
                                'Detection Window: ' + str(self.config_data.get('detection_params', {}).get('window_s', 60)) + 's<br>' +
                                '<br><b>Advanced Metrics:</b><br>' +
                                'Price Velocity: %{customdata[5]:.3f}<br>' +
                                'Baseline Price: $%{customdata[6]:.6f}<br>' +
                                'Peak Price: $%{customdata[7]:.6f}<br>' +
                                '<extra></extra>',
                    customdata=self._prepare_signal_customdata(df_signals)
                ),
                row=1, col=1
            )
        
        # 3. Enhanced Trade Entry/Exit Points with Configuration Context
        if not df_trades.empty:
            # Entry points with size-based visualization
            entry_sizes = []
            entry_colors = []
            for _, trade in df_trades.iterrows():
                # Size based on position size relative to max configured
                max_size = self.config_data.get('risk_params', {}).get('max_position_size_usdt', 500)
                size_ratio = trade.get('size', 0) / max_size
                entry_sizes.append(8 + (size_ratio * 12))  # 8-20 range
                
                # Color based on leverage used
                leverage = trade.get('leverage', 1)
                max_leverage = self.config_data.get('risk_params', {}).get('max_leverage', 3.0)
                if leverage >= max_leverage:
                    entry_colors.append('red')  # Max leverage
                elif leverage >= max_leverage * 0.7:
                    entry_colors.append('orange')  # High leverage
                else:
                    entry_colors.append('yellow')  # Conservative leverage
            
            fig.add_trace(
                go.Scatter(
                    x=df_trades['entry_time'],
                    y=df_trades['entry_price'],
                    mode='markers',
                    name='Trade Entry (Short)',
                    marker=dict(
                        color=entry_colors,
                        size=entry_sizes,
                        symbol='arrow-down',
                        line=dict(color='darkorange', width=2)
                    ),
                    hovertemplate='<b>💼 Trade Entry</b><br>' +
                                '<b>Basic Info:</b><br>' +
                                'Time: %{x}<br>' +
                                'Entry Price: $%{y:.6f}<br>' +
                                'Trade ID: %{customdata[0]}<br>' +
                                '<br><b>Position Details:</b><br>' +
                                'Size: %{customdata[1]:.2f} USDT<br>' +
                                'Leverage: %{customdata[2]}x<br>' +
                                'Margin: %{customdata[3]:.2f} USDT<br>' +
                                'Side: %{customdata[4]}<br>' +
                                '<br><b>Risk Management:</b><br>' +
                                'Stop Loss: $%{customdata[5]:.6f}<br>' +
                                'Risk/Reward: %{customdata[6]:.2f}<br>' +
                                'Max Loss: %{customdata[7]:.2f} USDT<br>' +
                                '<br><b>Configuration Context:</b><br>' +
                                'Max Position Size: ' + str(self.config_data.get('risk_params', {}).get('max_position_size_usdt', 500)) + ' USDT<br>' +
                                'Max Leverage: ' + str(self.config_data.get('risk_params', {}).get('max_leverage', 3.0)) + 'x<br>' +
                                'Base Risk: ' + str(self.config_data.get('risk_params', {}).get('base_risk_pct', 1.0)) + '%<br>' +
                                '<br><b>Market Context:</b><br>' +
                                'Confidence: %{customdata[8]:.1f}%<br>' +
                                'Entry Reason: %{customdata[9]}<br>' +
                                '<extra></extra>',
                    customdata=self._prepare_trade_customdata(df_trades)
                ),
                row=1, col=1
            )
            
            # Exit points (only for closed trades)
            closed_trades = df_trades[df_trades['exit_time'].notna()]
            if not closed_trades.empty:
                # Color based on profit/loss
                colors = ['green' if pnl > 0 else 'red' for pnl in closed_trades['pnl']]
                
                fig.add_trace(
                    go.Scatter(
                        x=closed_trades['exit_time'],
                        y=closed_trades['exit_price'],
                        mode='markers',
                        name='Trade Exit',
                        marker=dict(
                            color=colors,
                            size=10,
                            symbol='arrow-up',
                            line=dict(color='black', width=1)
                        ),
                        hovertemplate='<b>Trade Exit</b><br>' +
                                    'Time: %{x}<br>' +
                                    'Exit Price: $%{y:.6f}<br>' +
                                    'P&L: $%{customdata[0]:.2f}<br>' +
                                    'P&L %: %{customdata[1]:.2f}%<br>' +
                                    'Duration: %{customdata[2]:.0f} min<br>' +
                                    'Reason: %{customdata[3]}<br>' +
                                    '<extra></extra>',
                        customdata=closed_trades[['pnl', 'pnl_pct', 'duration_minutes', 'close_reason']].values
                    ),
                    row=1, col=1
                )
            
            # Stop Loss Lines
            for _, trade in df_trades.iterrows():
                if pd.notna(trade['stop_loss']):
                    fig.add_shape(
                        type="line",
                        x0=trade['entry_time'],
                        x1=trade['exit_time'] if pd.notna(trade['exit_time']) else df_price['timestamp'].iloc[-1],
                        y0=trade['stop_loss'],
                        y1=trade['stop_loss'],
                        line=dict(color="red", width=1, dash="dash"),
                        row=1, col=1
                    )
            
            # Take Profit Lines
            for _, trade in df_trades.iterrows():
                if trade['take_profit_levels']:
                    for tp_level in trade['take_profit_levels']:
                        fig.add_shape(
                            type="line",
                            x0=trade['entry_time'],
                            x1=trade['exit_time'] if pd.notna(trade['exit_time']) else df_price['timestamp'].iloc[-1],
                            y0=tp_level,
                            y1=tp_level,
                            line=dict(color="green", width=1, dash="dot"),
                            row=1, col=1
                        )
        
        # 4. Volume Chart
        fig.add_trace(
            go.Bar(
                x=df_price['timestamp'],
                y=df_price['volume'],
                name='Volume',
                marker_color='lightblue',
                opacity=0.7,
                hovertemplate='<b>Volume</b><br>' +
                            'Time: %{x}<br>' +
                            'Volume: %{y:,.0f}<br>' +
                            '<extra></extra>'
            ),
            row=2, col=1
        )
        
        # 5. Individual Trade P&L
        if not df_trades.empty:
            colors = ['green' if pnl > 0 else 'red' for pnl in df_trades['pnl']]
            fig.add_trace(
                go.Bar(
                    x=df_trades['entry_time'],
                    y=df_trades['pnl'],
                    name='Trade P&L',
                    marker_color=colors,
                    hovertemplate='<b>Trade P&L</b><br>' +
                                'Entry: %{x}<br>' +
                                'P&L: $%{y:.2f}<br>' +
                                '<extra></extra>'
                ),
                row=3, col=1
            )
        
        # 6. Cumulative Performance
        if not df_trades.empty:
            df_trades_sorted = df_trades.sort_values('entry_time')
            cumulative_pnl = df_trades_sorted['pnl'].cumsum()
            
            fig.add_trace(
                go.Scatter(
                    x=df_trades_sorted['entry_time'],
                    y=cumulative_pnl,
                    mode='lines+markers',
                    name='Cumulative P&L',
                    line=dict(color='purple', width=2),
                    marker=dict(size=6),
                    hovertemplate='<b>Cumulative P&L</b><br>' +
                                'Time: %{x}<br>' +
                                'Total P&L: $%{y:.2f}<br>' +
                                '<extra></extra>'
                ),
                row=4, col=1
            )
        
        # 7. Risk Metrics Panel (5th row)
        if not df_trades.empty:
            # Add risk metrics visualization
            self._add_risk_metrics_panel(fig, df_trades, 5)
        
        # Add interactive controls
        self._add_interactive_controls(fig)
        
        # Update layout
        fig.update_layout(
            title=dict(
                text=f'<b>{symbol} Backtest Analysis</b><br>' +
                     f'<span style="font-size:14px">Signals: {len(df_signals)} | ' +
                     f'Trades: {len(df_trades)} | ' +
                     f'Win Rate: {self._calculate_win_rate(df_trades):.1f}%</span>',
                x=0.5,
                font=dict(size=18)
            ),
            height=1000,
            showlegend=True,
            hovermode='x unified',
            template='plotly_white'
        )
        
        # Update axes
        fig.update_xaxes(title_text="Time", row=5, col=1)
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        fig.update_yaxes(title_text="P&L ($)", row=3, col=1)
        fig.update_yaxes(title_text="Cumulative P&L ($)", row=4, col=1)
        fig.update_yaxes(title_text="Risk Metrics", row=5, col=1)
        
        # Save chart
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_filename = f"{symbol}_trading_chart_{timestamp}.html"
        chart_path = output_path / chart_filename
        
        fig.write_html(
            str(chart_path),
            include_plotlyjs='cdn',
            config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
            }
        )
        
        # Generate summary report
        summary_path = self._generate_summary_report(symbol, df_trades, df_signals, output_path, timestamp)
        
        self.logger.info("chart_generator.chart_created", {
            "symbol": symbol,
            "chart_path": str(chart_path),
            "summary_path": str(summary_path),
            "signals": len(df_signals),
            "trades": len(df_trades)
        })
        
        return str(chart_path)
    
    def _calculate_win_rate(self, df_trades: pd.DataFrame) -> float:
        """Calculate win rate from trades"""
        if df_trades.empty:
            return 0.0
        
        winning_trades = len(df_trades[df_trades['pnl'] > 0])
        total_trades = len(df_trades)
        return (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
    
    def _generate_summary_report(self, symbol: str, df_trades: pd.DataFrame, 
                                df_signals: pd.DataFrame, output_path: Path, 
                                timestamp: str) -> str:
        """Generate detailed summary report"""
        
        summary = {
            "symbol": symbol,
            "backtest_timestamp": timestamp,
            "summary_stats": {
                "total_signals": len(df_signals),
                "total_trades": len(df_trades),
                "win_rate": self._calculate_win_rate(df_trades),
                "total_pnl": df_trades['pnl'].sum() if not df_trades.empty else 0,
                "avg_pnl_per_trade": df_trades['pnl'].mean() if not df_trades.empty else 0,
                "best_trade": df_trades['pnl'].max() if not df_trades.empty else 0,
                "worst_trade": df_trades['pnl'].min() if not df_trades.empty else 0,
                "avg_trade_duration": df_trades['duration_minutes'].mean() if not df_trades.empty else 0
            },
            "signal_analysis": [],
            "trade_details": []
        }
        
        # Add signal details
        for _, signal in df_signals.iterrows():
            summary["signal_analysis"].append({
                "signal_id": signal['signal_id'],
                "timestamp": signal['timestamp'].isoformat(),
                "price": signal['price'],
                "magnitude": signal['magnitude'],
                "volume_surge": signal['volume_surge'],
                "confidence": signal['confidence']
            })
        
        # Add trade details
        for _, trade in df_trades.iterrows():
            summary["trade_details"].append({
                "trade_id": trade['trade_id'],
                "signal_id": trade['signal_id'],
                "entry_time": trade['entry_time'].isoformat(),
                "exit_time": trade['exit_time'].isoformat() if pd.notna(trade['exit_time']) else None,
                "entry_price": trade['entry_price'],
                "exit_price": trade['exit_price'],
                "size": trade['size'],
                "leverage": trade['leverage'],
                "pnl": trade['pnl'],
                "pnl_pct": trade['pnl_pct'],
                "duration_minutes": trade['duration_minutes'],
                "close_reason": trade['close_reason'],
                "stop_loss": trade['stop_loss'],
                "take_profit_levels": trade['take_profit_levels']
            })
        
        # Save summary
        summary_filename = f"{symbol}_trading_summary_{timestamp}.json"
        summary_path = output_path / summary_filename
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        return str(summary_path)
    
    def _add_interactive_controls(self, fig):
        """Add interactive filtering and analysis controls"""
        
        # Add range selector for time filtering
        fig.update_layout(
            xaxis=dict(
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1h", step="hour", stepmode="backward"),
                        dict(count=6, label="6h", step="hour", stepmode="backward"),
                        dict(count=1, label="1d", step="day", stepmode="backward"),
                        dict(count=7, label="7d", step="day", stepmode="backward"),
                        dict(step="all")
                    ])
                ),
                rangeslider=dict(visible=True),
                type="date"
            )
        )
        
        # Add configuration info as annotations
        if self.config_data:
            config_text = self._generate_config_annotation()
            fig.add_annotation(
                text=config_text,
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                showarrow=False,
                font=dict(size=10, color="gray"),
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="gray",
                borderwidth=1,
                align="left"
            )
    
    def _generate_config_annotation(self) -> str:
        """Generate configuration summary for annotation"""
        if not self.config_data:
            return ""
        
        detection = self.config_data.get('detection_params', {})
        risk = self.config_data.get('risk_params', {})
        
        return (
            f"<b>Configuration Summary:</b><br>"
            f"• Detection Window: {detection.get('window_s', 60)}s<br>"
            f"• Magnitude Range: {detection.get('min_pump_magnitude', 7.0)}%-{detection.get('max_pump_magnitude', 50.0)}%<br>"
            f"• Volume Multiplier: {detection.get('volume_surge_multiplier', 3.0)}x<br>"
            f"• Max Leverage: {risk.get('max_leverage', 3.0)}x<br>"
            f"• Max Position: ${risk.get('max_position_size_usdt', 500)}<br>"
            f"• Base Risk: {risk.get('base_risk_pct', 1.0)}%"
        )
    
    def generate_configuration_comparison_chart(
        self,
        symbol: str,
        comparison_data: List[Dict[str, Any]],
        output_dir: str = "results"
    ) -> str:
        """Generate chart comparing different configuration results"""
        
        if not comparison_data:
            return ""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Win Rate by Configuration',
                'Total P&L by Configuration',
                'Signal Count by Configuration',
                'Risk-Adjusted Returns'
            ),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # Extract data for comparison
        config_names = [d['config_name'] for d in comparison_data]
        win_rates = [d['performance']['win_rate'] for d in comparison_data]
        total_pnls = [d['performance']['total_pnl'] for d in comparison_data]
        signal_counts = [d['performance']['signal_count'] for d in comparison_data]
        sharpe_ratios = [d['performance'].get('sharpe_ratio', 0) for d in comparison_data]
        
        # Win Rate comparison
        fig.add_trace(
            go.Bar(x=config_names, y=win_rates, name='Win Rate (%)', marker_color='green'),
            row=1, col=1
        )
        
        # P&L comparison
        colors = ['green' if pnl > 0 else 'red' for pnl in total_pnls]
        fig.add_trace(
            go.Bar(x=config_names, y=total_pnls, name='Total P&L ($)', marker_color=colors),
            row=1, col=2
        )
        
        # Signal count comparison
        fig.add_trace(
            go.Bar(x=config_names, y=signal_counts, name='Signal Count', marker_color='blue'),
            row=2, col=1
        )
        
        # Risk-adjusted returns
        fig.add_trace(
            go.Scatter(
                x=total_pnls, y=sharpe_ratios,
                mode='markers+text',
                text=config_names,
                textposition="top center",
                name='Risk-Adjusted Returns',
                marker=dict(size=10, color='purple')
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title=f'<b>{symbol} Configuration Comparison Analysis</b>',
            height=800,
            showlegend=False
        )
        
        # Save comparison chart
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comparison_filename = f"{symbol}_config_comparison_{timestamp}.html"
        comparison_path = output_path / comparison_filename
        
        fig.write_html(str(comparison_path), include_plotlyjs='cdn')
        
        return str(comparison_path)
    
    def generate_interactive_dashboard(
        self,
        symbol: str,
        output_dir: str = "results"
    ) -> str:
        """Generate comprehensive interactive dashboard"""
        
        if not self.flash_pump_signals and not self.trades_data:
            return ""
        
        # Create dashboard with multiple tabs/sections
        dashboard_html = self._create_dashboard_html(symbol)
        
        # Save dashboard
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dashboard_filename = f"{symbol}_interactive_dashboard_{timestamp}.html"
        dashboard_path = output_path / dashboard_filename
        
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
        
        return str(dashboard_path)
    
    def _create_dashboard_html(self, symbol: str) -> str:
        """Create comprehensive HTML dashboard"""
        
        # Generate summary statistics
        summary_stats = self._generate_dashboard_summary()
        
        # Create configuration summary
        config_summary = self._generate_config_summary_html()
        
        # Generate recommendations
        recommendations = self._generate_recommendations_html()
        
        dashboard_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{symbol} Trading Analysis Dashboard</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                .section {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #f8f9fa; border-radius: 5px; min-width: 150px; text-align: center; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
                .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
                .neutral {{ color: #6c757d; }}
                .config-item {{ margin: 5px 0; padding: 5px; background: #e9ecef; border-radius: 3px; }}
                .recommendation {{ margin: 10px 0; padding: 10px; border-left: 4px solid #007bff; background: #f8f9fa; }}
                .high-priority {{ border-left-color: #dc3545; }}
                .medium-priority {{ border-left-color: #ffc107; }}
                .low-priority {{ border-left-color: #28a745; }}
                .tabs {{ display: flex; margin-bottom: 20px; }}
                .tab {{ padding: 10px 20px; background: #e9ecef; border: none; cursor: pointer; border-radius: 5px 5px 0 0; margin-right: 5px; }}
                .tab.active {{ background: white; border-bottom: 2px solid #007bff; }}
                .tab-content {{ display: none; }}
                .tab-content.active {{ display: block; }}
            </style>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 {symbol} Trading Analysis Dashboard</h1>
                    <p>Comprehensive analysis with configuration impact assessment</p>
                    <p><small>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</small></p>
                </div>
                
                <div class="tabs">
                    <button class="tab active" onclick="showTab('overview')">Overview</button>
                    <button class="tab" onclick="showTab('signals')">Signals Analysis</button>
                    <button class="tab" onclick="showTab('trades')">Trade Analysis</button>
                    <button class="tab" onclick="showTab('config')">Configuration</button>
                    <button class="tab" onclick="showTab('recommendations')">Recommendations</button>
                </div>
                
                <div id="overview" class="tab-content active">
                    <div class="section">
                        <h2>📈 Performance Overview</h2>
                        {summary_stats}
                    </div>
                </div>
                
                <div id="signals" class="tab-content">
                    <div class="section">
                        <h2>🚀 Signal Analysis</h2>
                        <div id="signals-chart"></div>
                    </div>
                </div>
                
                <div id="trades" class="tab-content">
                    <div class="section">
                        <h2>💼 Trade Analysis</h2>
                        <div id="trades-chart"></div>
                    </div>
                </div>
                
                <div id="config" class="tab-content">
                    <div class="section">
                        <h2>⚙️ Configuration Analysis</h2>
                        {config_summary}
                    </div>
                </div>
                
                <div id="recommendations" class="tab-content">
                    <div class="section">
                        <h2>💡 Optimization Recommendations</h2>
                        {recommendations}
                    </div>
                </div>
            </div>
            
            <script>
                function showTab(tabName) {{
                    // Hide all tab contents
                    var contents = document.getElementsByClassName('tab-content');
                    for (var i = 0; i < contents.length; i++) {{
                        contents[i].classList.remove('active');
                    }}
                    
                    // Remove active class from all tabs
                    var tabs = document.getElementsByClassName('tab');
                    for (var i = 0; i < tabs.length; i++) {{
                        tabs[i].classList.remove('active');
                    }}
                    
                    // Show selected tab content and mark tab as active
                    document.getElementById(tabName).classList.add('active');
                    event.target.classList.add('active');
                }}
            </script>
        </body>
        </html>
        """
        
        return dashboard_html
    
    def _generate_dashboard_summary(self) -> str:
        """Generate HTML summary statistics for dashboard"""
        
        if not self.trades_data:
            return "<p>No trade data available</p>"
        
        df_trades = pd.DataFrame(self.trades_data)
        completed_trades = df_trades[df_trades['exit_time'].notna()]
        
        if completed_trades.empty:
            return "<p>No completed trades available</p>"
        
        # Calculate key metrics
        total_trades = len(completed_trades)
        winning_trades = len(completed_trades[completed_trades['pnl'] > 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        total_pnl = completed_trades['pnl'].sum()
        avg_pnl = completed_trades['pnl'].mean()
        best_trade = completed_trades['pnl'].max()
        worst_trade = completed_trades['pnl'].min()
        
        # Generate HTML
        return f"""
        <div class="metric">
            <div class="metric-value {'positive' if total_pnl > 0 else 'negative'}">${total_pnl:.2f}</div>
            <div class="metric-label">Total P&L</div>
        </div>
        <div class="metric">
            <div class="metric-value">{total_trades}</div>
            <div class="metric-label">Total Trades</div>
        </div>
        <div class="metric">
            <div class="metric-value {'positive' if win_rate >= 50 else 'negative'}">{win_rate:.1f}%</div>
            <div class="metric-label">Win Rate</div>
        </div>
        <div class="metric">
            <div class="metric-value {'positive' if avg_pnl > 0 else 'negative'}">${avg_pnl:.2f}</div>
            <div class="metric-label">Avg P&L per Trade</div>
        </div>
        <div class="metric">
            <div class="metric-value positive">${best_trade:.2f}</div>
            <div class="metric-label">Best Trade</div>
        </div>
        <div class="metric">
            <div class="metric-value negative">${worst_trade:.2f}</div>
            <div class="metric-label">Worst Trade</div>
        </div>
        <div class="metric">
            <div class="metric-value">{len(self.flash_pump_signals)}</div>
            <div class="metric-label">Signals Detected</div>
        </div>
        """
    
    def _generate_config_summary_html(self) -> str:
        """Generate HTML configuration summary"""
        
        if not self.config_data:
            return "<p>No configuration data available</p>"
        
        detection = self.config_data.get('detection_params', {})
        risk = self.config_data.get('risk_params', {})
        entry = self.config_data.get('entry_conditions', {})
        
        return f"""
        <h3>Detection Parameters</h3>
        <div class="config-item"><strong>Detection Window:</strong> {detection.get('window_s', 60)} seconds</div>
        <div class="config-item"><strong>Magnitude Range:</strong> {detection.get('min_pump_magnitude', 7.0)}% - {detection.get('max_pump_magnitude', 50.0)}%</div>
        <div class="config-item"><strong>Volume Multiplier:</strong> {detection.get('volume_surge_multiplier', 3.0)}x</div>
        <div class="config-item"><strong>Velocity Threshold:</strong> {detection.get('price_velocity_threshold', 0.5)}</div>
        <div class="config-item"><strong>Cooldown Period:</strong> {detection.get('cooldown_s', 1800)} seconds</div>
        
        <h3>Risk Management</h3>
        <div class="config-item"><strong>Base Risk:</strong> {risk.get('base_risk_pct', 1.0)}%</div>
        <div class="config-item"><strong>Max Position Size:</strong> ${risk.get('max_position_size_usdt', 500)}</div>
        <div class="config-item"><strong>Max Leverage:</strong> {risk.get('max_leverage', 3.0)}x</div>
        <div class="config-item"><strong>Stop Loss Buffer:</strong> {risk.get('stop_loss_peak_buffer', 3.0)}%</div>
        <div class="config-item"><strong>Take Profit Levels:</strong> {len(risk.get('take_profit_levels', []))}</div>
        
        <h3>Entry Conditions</h3>
        <div class="config-item"><strong>Max Entry Delay:</strong> {entry.get('max_entry_delay', 20)} seconds</div>
        <div class="config-item"><strong>Min Pump Age:</strong> {entry.get('min_pump_age', 10)} seconds</div>
        <div class="config-item"><strong>RSI Threshold:</strong> {entry.get('rsi_threshold', 75)}</div>
        <div class="config-item"><strong>Min Liquidity:</strong> ${entry.get('min_liquidity_usdt', 10000)}</div>
        """
    
    def _generate_recommendations_html(self) -> str:
        """Generate HTML recommendations"""
        
        if not self.trades_data or not self.config_data:
            return "<p>Insufficient data for recommendations</p>"
        
        # Generate recommendations using the analysis exporter
        recommendations = self.analysis_exporter._generate_optimization_suggestions(
            self.flash_pump_signals, self.trades_data, self.config_data
        )
        
        if not recommendations:
            return "<p>No specific recommendations at this time. System appears to be performing within expected parameters.</p>"
        
        html = ""
        for rec in recommendations:
            priority_class = f"{rec.get('priority', 'medium')}-priority"
            html += f"""
            <div class="recommendation {priority_class}">
                <strong>{rec.get('category', 'General')}:</strong> {rec.get('suggestion', '')}
                <br><small>Priority: {rec.get('priority', 'medium').title()}</small>
            </div>
            """
        
        return html
    
    def _prepare_signal_customdata(self, df_signals: pd.DataFrame):
        """Prepare customdata for signals with safe column access"""
        if df_signals.empty:
            return []
        
        customdata = []
        for _, signal in df_signals.iterrows():
            row = [
                signal.get('signal_id', 'N/A'),
                signal.get('magnitude', 0),
                signal.get('volume_surge', 0),
                signal.get('confidence', 0),
                signal.get('direction', 'unknown'),
                signal.get('price_velocity', 0),
                signal.get('baseline_price', 0),
                signal.get('peak_price', 0)
            ]
            customdata.append(row)
        return customdata
    
    def _add_risk_metrics_panel(self, fig, df_trades: pd.DataFrame, row: int):
        """Add risk metrics visualization to the specified row"""
        if df_trades.empty:
            return
        
        # Calculate risk metrics over time
        df_trades_sorted = df_trades.sort_values('entry_time')
        
        # Risk/Reward ratio over time
        risk_rewards = df_trades_sorted['risk_reward_ratio'].fillna(0)
        
        fig.add_trace(
            go.Scatter(
                x=df_trades_sorted['entry_time'],
                y=risk_rewards,
                mode='lines+markers',
                name='Risk/Reward Ratio',
                line=dict(color='orange', width=2),
                marker=dict(size=4),
                hovertemplate='<b>Risk/Reward Ratio</b><br>' +
                            'Time: %{x}<br>' +
                            'Ratio: %{y:.2f}<br>' +
                            '<extra></extra>'
            ),
            row=row, col=1
        )
        
        # Add configuration thresholds as horizontal lines
        if self.config_data:
            max_leverage = self.config_data.get('risk_params', {}).get('max_leverage', 3.0)
            fig.add_hline(
                y=max_leverage,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Max Leverage: {max_leverage}x",
                row=row, col=1
            )
    
    def _prepare_trade_customdata(self, df_trades: pd.DataFrame):
        """Prepare customdata for trades with safe column access"""
        if df_trades.empty:
            return []
        
        customdata = []
        for _, trade in df_trades.iterrows():
            row = [
                trade.get('trade_id', 'N/A'),
                trade.get('size', 0),
                trade.get('leverage', 1),
                trade.get('margin', 0),
                trade.get('side', 'unknown'),
                trade.get('stop_loss', 0),
                trade.get('risk_reward_ratio', 0),
                trade.get('max_loss_usdt', 0),
                trade.get('confidence_score', 0),
                trade.get('entry_reason', 'unknown')
            ]
            customdata.append(row)
        return customdata

    def clear_data(self):
        """Clear all collected data"""
        self.trades_data.clear()
        self.price_data.clear()
        self.flash_pump_signals.clear()
        self.config_data.clear()
        self.backtest_metadata.clear()