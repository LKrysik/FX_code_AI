"""
Detect Pump Signals Use Case
============================
Application layer orchestrating pump detection workflow.
Coordinates domain services and handles cross-cutting concerns.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import asyncio

from ...domain.services.pump_detector import PumpDetectionService, PumpDetectionConfig
from ...domain.services.risk_assessment import RiskAssessmentService, RiskLimits, EntryConditions
from ...domain.models.market_data import MarketData
from ...domain.models.signals import FlashPumpSignal, ReversalSignal, SignalType
from ...domain.interfaces.market_data import IMarketDataProvider
from ...domain.interfaces.notifications import INotificationService
# Removed get_settings import - violates Service Locator anti-pattern


@dataclass
class PumpDetectionResult:
    """Result of pump detection analysis"""
    signal: Optional[FlashPumpSignal] = None
    reversal: Optional[ReversalSignal] = None
    entry_allowed: bool = False
    rejection_reasons: Dict[str, Any] = None
    emergency_conditions: Dict[str, Any] = None


class DetectPumpSignalsUseCase:
    """
    Use case for detecting and validating pump signals.
    
    This orchestrates the pump detection workflow:
    1. Analyze market data for pump patterns
    2. Assess risk and entry conditions
    3. Check safety limits and emergency conditions
    4. Emit validated signals
    """
    
    def __init__(self,
                 pump_detection_service: PumpDetectionService,
                 risk_assessment_service: RiskAssessmentService,
                 event_bus,
                 notification_service: Optional[INotificationService] = None,
                 logger = None):
        self.pump_detection = pump_detection_service
        self.risk_assessment = risk_assessment_service
        self.event_bus = event_bus
        self.notification_service = notification_service
        
        # Use provided logger or create simple fallback
        if logger:
            self.logger = logger
        else:
            from ...core.logger import get_logger
            self.logger = get_logger("DetectPumpSignals")
        
        # Track confirmed pumps for reversal detection
        self._confirmed_pumps: Dict[str, FlashPumpSignal] = {}
        
        # Subscribe to market data events for pump detection
        self._setup_event_subscriptions()
    
    def _setup_event_subscriptions(self):
        """Setup event subscriptions for pump detection"""
        import asyncio
        asyncio.create_task(self.event_bus.subscribe('market.price_update', self._handle_market_data_event))
    
    async def _handle_market_data_event(self, event_data: dict):
        """
        Handle market.price_update events from the EventBus.
        Converts event data to MarketData and runs pump detection analysis.
        """
        try:
            # Debug logging to track event reception
            self.logger.debug("detect_pump_signals.event_received", {
                "event_data_keys": list(event_data.keys()) if isinstance(event_data, dict) else "not_dict",
                "event_data": event_data
            })
            
            # Extract data from event
            if 'data' in event_data:
                data = event_data['data']
            else:
                data = event_data
            
            symbol = data.get('symbol')
            if not symbol:
                self.logger.debug("detect_pump_signals.no_symbol", {"event_data": event_data})
                return
            
            self.logger.debug("detect_pump_signals.processing_symbol", {"symbol": symbol})
            
            # Convert to MarketData domain model
            market_data = MarketData(
                symbol=symbol,
                exchange=data.get('exchange', 'file'),
                price=Decimal(str(data.get('price', 0))),
                volume=Decimal(str(data.get('volume', 0))),
                timestamp=datetime.fromtimestamp(float(data.get('timestamp', 0))),
                volume_24h_usdt=Decimal(str(data.get('volume_24h_usdt', float(data.get('volume', 0)) * float(data.get('price', 0)) * 24))),
                liquidity_usdt=Decimal(str(data.get('liquidity_usdt', 0)))
            )
            
            # Log the received liquidity data
            self.logger.debug("market_data_prepared", {
                "symbol": symbol,
                "price": str(market_data.price),
                "volume": str(market_data.volume),
                "liquidity_usdt": str(market_data.liquidity_usdt),
                "data_source": "orderbook" if data.get('liquidity_usdt', 0) > 0 else "estimated"
            })
            
            # Run pump detection analysis
            result = await self.analyze_market_data(symbol, market_data)
            
            # Publish pump detection results if any signals found
            if result.signal:
                await self.event_bus.publish('pump.detected', {
                    'timestamp': result.signal.detection_time.timestamp(),
                    'source': self.__class__.__name__,
                    'symbol': symbol,
                    'data': {
                        'signal': result.signal,
                        'entry_allowed': result.entry_allowed,
                        'rejection_reasons': result.rejection_reasons
                    }
                })
            
            if result.reversal:
                await self.event_bus.publish('reversal.detected', {
                    'timestamp': result.reversal.detection_time.timestamp(),
                    'source': self.__class__.__name__,
                    'symbol': symbol,
                    'data': result.reversal
                })
                
        except Exception as e:
            # Log error but don't crash the event handling
            if hasattr(self, 'logger'):
                self.logger.error("pump_detection.event_handler_error", {
                    "error": str(e),
                    "event_data": event_data
                })
    
    async def analyze_market_data(self, symbol: str, market_data: MarketData) -> PumpDetectionResult:
        """
        Analyze market data for pump signals with full validation.
        
        Args:
            symbol: Trading symbol
            market_data: Current market data
            
        Returns:
            PumpDetectionResult with analysis results
        """
        self.logger.debug("analyze_market_data.start", {
            "symbol": symbol,
            "price": str(market_data.price),
            "volume": str(market_data.volume),
            "timestamp": market_data.timestamp.isoformat()
        })
        
        result = PumpDetectionResult()
        
        try:
            # Step 1: Check safety limits first
            self.logger.debug("analyze_market_data.step1_safety_limits", {"symbol": symbol})
            limits_ok, safety_violations = self.risk_assessment.check_safety_limits()
            if not limits_ok:
                self.logger.debug("analyze_market_data.safety_limits_failed", {
                    "symbol": symbol, 
                    "violations": safety_violations
                })
                result.rejection_reasons = {
                    "safety_limits": safety_violations
                }
                return result
            
            # Step 2: Check emergency conditions
            self.logger.debug("analyze_market_data.step2_emergency_conditions", {"symbol": symbol})
            spread_pct = getattr(market_data, 'spread_pct', None)
            liquidity_usdt = getattr(market_data, 'liquidity_usdt', 0.0)
            
            is_safe, emergency_reasons = self.risk_assessment.assess_emergency_conditions(
                market_data, spread_pct, liquidity_usdt
            )
            
            if not is_safe:
                self.logger.debug("analyze_market_data.emergency_conditions_failed", {
                    "symbol": symbol,
                    "reasons": emergency_reasons
                })
                result.emergency_conditions = {
                    "reasons": emergency_reasons,
                    "spread_pct": spread_pct,
                    "liquidity_usdt": liquidity_usdt
                }
                return result
            
            # Step 3: Analyze for pump patterns
            self.logger.debug("analyze_market_data.step3_pump_analysis", {"symbol": symbol})
            pump_signal = self.pump_detection.analyze_price_event(symbol, market_data)
            
            if pump_signal:
                self.logger.info("pump_signal_detected", {
                    "symbol": symbol,
                    "signal": pump_signal.__dict__ if hasattr(pump_signal, '__dict__') else str(pump_signal)
                })
                
                # Step 4: Check peak confirmation for active pumps
                self.logger.debug("analyze_market_data.step4_peak_confirmation", {"symbol": symbol})
                confirmed_signal = self.pump_detection.check_peak_confirmation(symbol, market_data)
                
                if confirmed_signal:
                    self.logger.info("pump_signal_confirmed", {
                        "symbol": symbol,
                        "confirmed_signal": confirmed_signal.__dict__ if hasattr(confirmed_signal, '__dict__') else str(confirmed_signal)
                    })
                    
                    # Step 5: Validate entry conditions
                    self.logger.debug("analyze_market_data.step5_entry_validation", {"symbol": symbol})
                    entry_allowed, validation_results = self.risk_assessment.validate_entry_conditions(
                        confirmed_signal, 
                        spread_pct, 
                        liquidity_usdt,
                        getattr(market_data, 'rsi', None)
                    )
                    
                    result.signal = confirmed_signal
                    result.entry_allowed = entry_allowed
                    
                    if not entry_allowed:
                        result.rejection_reasons = validation_results
                    else:
                        # Store for reversal detection
                        self._confirmed_pumps[symbol] = confirmed_signal
                        
                        # Notify if service available
                        if self.notification_service:
                            await self._notify_pump_detected(confirmed_signal, entry_allowed)
            
            # Step 6: Check for reversals on confirmed pumps
            if symbol in self._confirmed_pumps:
                original_signal = self._confirmed_pumps[symbol]
                reversal_signal = self.pump_detection.check_reversal(
                    symbol, market_data, original_signal
                )
                
                if reversal_signal:
                    result.reversal = reversal_signal
                    # Remove from tracking after reversal
                    del self._confirmed_pumps[symbol]
                    
                    # Notify reversal
                    if self.notification_service:
                        await self._notify_reversal_detected(reversal_signal)
            
            return result
            
        except Exception as e:
            # Log error but don't crash the system
            if self.notification_service:
                await self.notification_service.send_error_notification(
                    f"Pump detection error for {symbol}: {str(e)}"
                )
            
            result.rejection_reasons = {
                "system_error": str(e)
            }
            return result
    
    async def update_trade_result(self, symbol: str, pnl: float, success: bool) -> None:
        """
        Update system with trade result for safety tracking.
        
        Args:
            symbol: Trading symbol
            pnl: Profit/loss amount
            success: Whether trade was successful
        """
        # Update risk assessment metrics
        self.risk_assessment.update_trade_result(pnl)
        
        # Clean up tracking if position closed
        if symbol in self._confirmed_pumps:
            del self._confirmed_pumps[symbol]
        
        # Clear pump detection history for symbol
        self.pump_detection.clear_history(symbol)
        
        # Notify trade result
        if self.notification_service:
            await self.notification_service.send_trade_result(
                symbol=symbol,
                pnl=pnl,
                success=success
            )
    
    async def reset_daily_metrics(self) -> None:
        """Reset daily metrics (call at midnight)"""
        self.risk_assessment.reset_daily_metrics()
        
        if self.notification_service:
            await self.notification_service.send_info_notification(
                "Daily metrics reset completed"
            )
    
    def get_active_pumps(self) -> Dict[str, FlashPumpSignal]:
        """Get currently confirmed pumps being tracked"""
        return self._confirmed_pumps.copy()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status and metrics"""
        safety_metrics = self.risk_assessment.get_safety_metrics()
        active_pumps = self.pump_detection.get_active_pumps()
        
        limits_ok, safety_violations = self.risk_assessment.check_safety_limits()
        
        return {
            "safety_limits_ok": limits_ok,
            "safety_violations": safety_violations,
            "daily_trades": safety_metrics.daily_trades_count,
            "consecutive_losses": safety_metrics.consecutive_losses,
            "daily_pnl": safety_metrics.daily_pnl,
            "active_pumps_count": len(active_pumps),
            "confirmed_pumps_count": len(self._confirmed_pumps),
            "active_pump_symbols": list(active_pumps.keys()),
            "confirmed_pump_symbols": list(self._confirmed_pumps.keys())
        }
    
    async def _notify_pump_detected(self, signal: FlashPumpSignal, entry_allowed: bool) -> None:
        """Send pump detection notification"""
        try:
            message = (
                f"🚀 Pump detected: {signal.symbol}\n"
                f"Magnitude: {signal.pump_magnitude:.1f}%\n"
                f"Confidence: {signal.confidence_score:.1f}\n"
                f"Entry allowed: {'✅' if entry_allowed else '❌'}"
            )
            
            await self.notification_service.send_signal_notification(
                signal_type="pump_detected",
                symbol=signal.symbol,
                message=message,
                priority="high" if entry_allowed else "medium"
            )
        except Exception as e:
            # Don't let notification errors break the main flow
            pass
    
    async def _notify_reversal_detected(self, reversal: ReversalSignal) -> None:
        """Send reversal detection notification"""
        try:
            message = (
                f"📉 Reversal detected: {reversal.symbol}\n"
                f"Retracement: {reversal.retracement_pct:.1f}%\n"
                f"Volume decline: {reversal.volume_decline_ratio*100:.1f}%\n"
                f"Emergency: {'⚠️' if reversal.emergency_exit else '📊'}"
            )
            
            await self.notification_service.send_signal_notification(
                signal_type="reversal_detected",
                symbol=reversal.symbol,
                message=message,
                priority="high" if reversal.emergency_exit else "medium"
            )
        except Exception as e:
            # Don't let notification errors break the main flow
            pass


# Factory function removed - violates Composition Root pattern
# Use Container.create_pump_detection_use_case() instead
# This follows dependency injection principles defined in .github/copilot-instructions.md