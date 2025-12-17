"""
Risk Manager - Live Trading Risk Management
==========================================
Implements 6 critical risk checks for live trading:
1. Max position size (10% of capital)
2. Max number of positions (3 concurrent)
3. Position concentration (max 30% in one symbol)
4. Daily loss limit (5% of capital)
5. Total drawdown (15% from peak)
6. Margin utilization (< 80% of available margin)

All limits configurable via settings.py.
Emits risk_alert events to EventBus.
Thread-safe for async operations.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum

from ..models.trading import Position, Order, OrderSide
from ...core.event_bus import EventBus
# ✅ ARCHITECTURE FIX (2025-11-30):
# Removed AppSettings import - Domain should not depend on Infrastructure.
# RiskManager now accepts risk_config directly (duck-typed object with required attributes).
# See Container.create_risk_manager() for how config is passed.

logger = logging.getLogger(__name__)


class RiskAlertSeverity(str, Enum):
    """Risk alert severity levels"""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class RiskAlertType(str, Enum):
    """Risk alert types"""
    POSITION_SIZE_EXCEEDED = "POSITION_SIZE_EXCEEDED"
    MAX_POSITIONS_EXCEEDED = "MAX_POSITIONS_EXCEEDED"
    CONCENTRATION_EXCEEDED = "CONCENTRATION_EXCEEDED"
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    MARGIN_UTILIZATION_HIGH = "MARGIN_UTILIZATION_HIGH"
    MARGIN_RATIO_LOW = "MARGIN_RATIO_LOW"
    ORDER_REJECTED = "ORDER_REJECTED"


@dataclass
class RiskCheckResult:
    """Result of risk validation"""
    can_proceed: bool
    reason: Optional[str] = None  # If False, explains why
    risk_score: float = 0.0  # 0-100 (higher = riskier)
    failed_checks: List[str] = None  # List of failed check names

    def __post_init__(self):
        if self.failed_checks is None:
            self.failed_checks = []


class RiskManager:
    """
    Live trading risk manager with 6 safety checks.

    Features:
    - Configurable limits via settings.py (NO hardcoded values)
    - Emits risk_alert events to EventBus
    - Thread-safe (async-safe) state management
    - Tracks equity peak for drawdown calculation
    - Daily P&L tracking with automatic reset at midnight
    """

    def __init__(self, event_bus: EventBus, risk_config: Any, initial_capital: Decimal = Decimal('10000')):
        """
        Initialize RiskManager.

        ✅ ARCHITECTURE FIX (2025-11-30):
        Changed from `settings: AppSettings` to `risk_config: Any` to remove
        Domain → Infrastructure dependency. Container passes settings.risk_management.risk_manager.

        DECISION: Domain layer should not import from Infrastructure.
        Changes in this area require business owner approval.

        Args:
            event_bus: EventBus instance for publishing risk alerts
            risk_config: Risk configuration object with attributes:
                - max_position_size_percent: Decimal
                - max_concurrent_positions: int
                - max_symbol_concentration_percent: Decimal
                - daily_loss_limit_percent: Decimal
                - max_drawdown_percent: Decimal
                - margin_utilization_warning_percent: Decimal
            initial_capital: Initial capital in USDT
        """
        self.event_bus = event_bus
        self.risk_config = risk_config

        # Capital tracking
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.equity_peak = initial_capital

        # Daily tracking
        self.daily_pnl = Decimal('0')
        self.daily_reset_date = datetime.now(timezone.utc).date()

        # Budget allocation per strategy (strategy_name -> reserved_amount)
        self._allocated_budgets: Dict[str, Decimal] = {}

        # Thread safety
        self._lock = asyncio.Lock()

        logger.info(
            "RiskManager initialized",
            extra={
                "initial_capital": float(initial_capital),
                "max_position_size_pct": float(self.risk_config.max_position_size_percent),
                "max_positions": self.risk_config.max_concurrent_positions,
                "daily_loss_limit_pct": float(self.risk_config.daily_loss_limit_percent),
                "max_drawdown_pct": float(self.risk_config.max_drawdown_percent)
            }
        )

    async def can_open_position(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        current_positions: List[Position],
        current_margin_ratio: Optional[Decimal] = None,
        available_margin: Optional[Decimal] = None
    ) -> RiskCheckResult:
        """
        Validate if new position can be opened.

        Runs all 6 risk checks:
        1. Max position size
        2. Max number of positions
        3. Position concentration
        4. Daily loss limit
        5. Total drawdown
        6. Margin utilization

        Args:
            symbol: Trading symbol (e.g., "BTC_USDT")
            side: "buy" or "sell" (long or short)
            quantity: Position size
            price: Entry price
            current_positions: List of currently open positions
            current_margin_ratio: Current margin ratio (equity / maintenance_margin)
            available_margin: Available margin for new positions

        Returns:
            RiskCheckResult with can_proceed=True/False and reason
        """
        async with self._lock:
            # Reset daily P&L if new day
            self._check_daily_reset()

            # Calculate position notional value
            position_value = quantity * price

            # Initialize result
            result = RiskCheckResult(can_proceed=True, risk_score=0.0, failed_checks=[])

            # Check 1: Max position size
            check1_passed, check1_reason, check1_score = self._check_max_position_size(position_value)
            if not check1_passed:
                result.can_proceed = False
                result.failed_checks.append("max_position_size")
                if result.reason is None:
                    result.reason = check1_reason
            result.risk_score += check1_score

            # Check 2: Max number of positions
            check2_passed, check2_reason, check2_score = self._check_max_positions(current_positions)
            if not check2_passed:
                result.can_proceed = False
                result.failed_checks.append("max_concurrent_positions")
                if result.reason is None:
                    result.reason = check2_reason
            result.risk_score += check2_score

            # Check 3: Position concentration
            check3_passed, check3_reason, check3_score = self._check_position_concentration(
                symbol, position_value, current_positions
            )
            if not check3_passed:
                result.can_proceed = False
                result.failed_checks.append("symbol_concentration")
                if result.reason is None:
                    result.reason = check3_reason
            result.risk_score += check3_score

            # Check 4: Daily loss limit
            check4_passed, check4_reason, check4_score = self._check_daily_loss_limit()
            if not check4_passed:
                result.can_proceed = False
                result.failed_checks.append("daily_loss_limit")
                if result.reason is None:
                    result.reason = check4_reason
            result.risk_score += check4_score

            # Check 5: Total drawdown
            check5_passed, check5_reason, check5_score = self._check_max_drawdown()
            if not check5_passed:
                result.can_proceed = False
                result.failed_checks.append("max_drawdown")
                if result.reason is None:
                    result.reason = check5_reason
            result.risk_score += check5_score

            # Check 6: Margin utilization
            check6_passed, check6_reason, check6_score = self._check_margin_utilization(
                position_value, available_margin, current_margin_ratio
            )
            if not check6_passed:
                result.can_proceed = False
                result.failed_checks.append("margin_utilization")
                if result.reason is None:
                    result.reason = check6_reason
            result.risk_score += check6_score

            # Emit risk alert if rejected
            if not result.can_proceed:
                await self._emit_risk_alert(
                    severity=RiskAlertSeverity.WARNING,
                    alert_type=RiskAlertType.ORDER_REJECTED,
                    message=f"Position opening rejected for {symbol}: {result.reason}",
                    details={
                        "symbol": symbol,
                        "side": side,
                        "quantity": float(quantity),
                        "price": float(price),
                        "position_value": float(position_value),
                        "failed_checks": result.failed_checks,
                        "risk_score": result.risk_score
                    }
                )

            logger.info(
                f"Risk check result: {'APPROVED' if result.can_proceed else 'REJECTED'}",
                extra={
                    "symbol": symbol,
                    "position_value": float(position_value),
                    "can_proceed": result.can_proceed,
                    "risk_score": result.risk_score,
                    "failed_checks": result.failed_checks,
                    "reason": result.reason
                }
            )

            return result

    async def validate_order(self, order: Order, current_positions: List[Position]) -> RiskCheckResult:
        """
        Validate order before submission.

        This is a convenience wrapper around can_open_position().

        Args:
            order: Order object to validate
            current_positions: List of current open positions

        Returns:
            RiskCheckResult
        """
        # Use average_fill_price if available, otherwise use order price
        price = order.average_fill_price if order.average_fill_price else order.price
        if price is None:
            # Market order - can't validate without price, return approved
            logger.warning(f"Cannot validate market order without price: {order.order_id}")
            return RiskCheckResult(can_proceed=True, risk_score=0.0)

        return await self.can_open_position(
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
            price=price,
            current_positions=current_positions
        )

    async def update_capital(self, new_capital: Decimal, pnl_change: Decimal = Decimal('0')):
        """
        Update current capital and track equity peak.

        Args:
            new_capital: New capital value
            pnl_change: P&L change since last update
        """
        async with self._lock:
            self.current_capital = new_capital

            # Update equity peak
            if new_capital > self.equity_peak:
                self.equity_peak = new_capital

            # Update daily P&L
            self.daily_pnl += pnl_change

            # Check if drawdown alert needed
            drawdown_pct = self._calculate_drawdown_percent()
            if drawdown_pct >= float(self.risk_config.max_drawdown_percent) * 0.8:  # 80% of limit
                await self._emit_risk_alert(
                    severity=RiskAlertSeverity.WARNING,
                    alert_type=RiskAlertType.MAX_DRAWDOWN,
                    message=f"Drawdown at {drawdown_pct:.2f}% (limit: {self.risk_config.max_drawdown_percent}%)",
                    details={
                        "current_capital": float(new_capital),
                        "equity_peak": float(self.equity_peak),
                        "drawdown_percent": drawdown_pct
                    }
                )

    async def check_margin_ratio(self, margin_ratio: Decimal):
        """
        Check margin ratio and emit alerts if too low.

        Args:
            margin_ratio: Current margin ratio (equity / maintenance_margin) as percentage
        """
        if margin_ratio <= self.risk_config.critical_margin_ratio_percent:
            await self._emit_risk_alert(
                severity=RiskAlertSeverity.CRITICAL,
                alert_type=RiskAlertType.MARGIN_RATIO_LOW,
                message=f"CRITICAL: Margin ratio at {margin_ratio:.2f}% - Liquidation risk!",
                details={"margin_ratio": float(margin_ratio)}
            )
        elif margin_ratio <= self.risk_config.warning_margin_ratio_percent:
            await self._emit_risk_alert(
                severity=RiskAlertSeverity.WARNING,
                alert_type=RiskAlertType.MARGIN_RATIO_LOW,
                message=f"WARNING: Margin ratio at {margin_ratio:.2f}%",
                details={"margin_ratio": float(margin_ratio)}
            )

    # === Internal Risk Checks ===

    def _check_max_position_size(self, position_value: Decimal) -> tuple[bool, Optional[str], float]:
        """
        Check 1: Max position size (% of capital).

        Returns:
            (passed, reason, risk_score)
        """
        max_value = self.current_capital * (self.risk_config.max_position_size_percent / 100)

        if position_value > max_value:
            return (
                False,
                f"Position size {float(position_value):.2f} USDT exceeds max {float(max_value):.2f} USDT ({self.risk_config.max_position_size_percent}% of capital)",
                25.0  # High risk score
            )

        # Risk score based on utilization
        utilization_pct = (position_value / max_value) * 100 if max_value > 0 else 0
        risk_score = float(utilization_pct / 10)  # 0-10 range

        return (True, None, risk_score)

    def _check_max_positions(self, current_positions: List[Position]) -> tuple[bool, Optional[str], float]:
        """
        Check 2: Max number of concurrent positions.

        Returns:
            (passed, reason, risk_score)
        """
        open_positions = [p for p in current_positions if p.is_open]
        num_open = len(open_positions)

        if num_open >= self.risk_config.max_concurrent_positions:
            return (
                False,
                f"Max positions reached: {num_open}/{self.risk_config.max_concurrent_positions}",
                20.0
            )

        # Risk score based on position count
        utilization_pct = (num_open / self.risk_config.max_concurrent_positions) * 100
        risk_score = float(utilization_pct / 10)  # 0-10 range

        return (True, None, risk_score)

    def _check_position_concentration(
        self,
        symbol: str,
        new_position_value: Decimal,
        current_positions: List[Position]
    ) -> tuple[bool, Optional[str], float]:
        """
        Check 3: Position concentration (max % in one symbol).

        Returns:
            (passed, reason, risk_score)
        """
        # Calculate existing exposure to symbol
        existing_exposure = Decimal('0')
        for pos in current_positions:
            if pos.symbol == symbol and pos.is_open:
                existing_exposure += pos.notional_value

        total_exposure = existing_exposure + new_position_value
        max_exposure = self.current_capital * (self.risk_config.max_symbol_concentration_percent / 100)

        if total_exposure > max_exposure:
            return (
                False,
                f"Symbol concentration for {symbol} would be {float(total_exposure):.2f} USDT, exceeds max {float(max_exposure):.2f} USDT ({self.risk_config.max_symbol_concentration_percent}% of capital)",
                30.0
            )

        # Risk score based on concentration
        concentration_pct = (total_exposure / max_exposure) * 100 if max_exposure > 0 else 0
        risk_score = float(concentration_pct / 10)  # 0-10 range

        return (True, None, risk_score)

    def _check_daily_loss_limit(self) -> tuple[bool, Optional[str], float]:
        """
        Check 4: Daily loss limit (% of capital).

        Returns:
            (passed, reason, risk_score)
        """
        daily_loss_limit = self.current_capital * (self.risk_config.daily_loss_limit_percent / 100)

        if self.daily_pnl < -daily_loss_limit:
            return (
                False,
                f"Daily loss {float(self.daily_pnl):.2f} USDT exceeds limit {float(daily_loss_limit):.2f} USDT ({self.risk_config.daily_loss_limit_percent}% of capital)",
                40.0  # Very high risk
            )

        # Risk score based on daily loss
        if self.daily_pnl < 0:
            loss_pct = (abs(self.daily_pnl) / daily_loss_limit) * 100
            risk_score = float(loss_pct / 10)  # 0-10 range
        else:
            risk_score = 0.0  # Positive P&L = no risk

        return (True, None, risk_score)

    def _check_max_drawdown(self) -> tuple[bool, Optional[str], float]:
        """
        Check 5: Total drawdown from peak (% of capital).

        Returns:
            (passed, reason, risk_score)
        """
        drawdown_pct = self._calculate_drawdown_percent()
        max_drawdown_pct = float(self.risk_config.max_drawdown_percent)

        if drawdown_pct >= max_drawdown_pct:
            return (
                False,
                f"Drawdown {drawdown_pct:.2f}% exceeds max {max_drawdown_pct}%",
                50.0  # Critical risk
            )

        # Risk score based on drawdown
        risk_score = float((drawdown_pct / max_drawdown_pct) * 10)  # 0-10 range

        return (True, None, risk_score)

    def _check_margin_utilization(
        self,
        new_position_value: Decimal,
        available_margin: Optional[Decimal],
        current_margin_ratio: Optional[Decimal]
    ) -> tuple[bool, Optional[str], float]:
        """
        Check 6: Margin utilization (% of available margin).

        Returns:
            (passed, reason, risk_score)
        """
        # If margin data not available, skip check
        if available_margin is None or current_margin_ratio is None:
            return (True, None, 0.0)

        # Check if margin utilization would be too high
        max_margin_pct = float(self.risk_config.max_margin_utilization_percent)

        # Current margin ratio already above limit
        if float(current_margin_ratio) >= max_margin_pct:
            return (
                False,
                f"Margin utilization {float(current_margin_ratio):.2f}% exceeds max {max_margin_pct}%",
                35.0
            )

        # Check if new position would push margin too high (simplified estimate)
        estimated_margin_increase = (new_position_value / self.current_capital) * 100
        estimated_new_margin = float(current_margin_ratio) + float(estimated_margin_increase)

        if estimated_new_margin >= max_margin_pct:
            return (
                False,
                f"New position would push margin to ~{estimated_new_margin:.2f}%, exceeds max {max_margin_pct}%",
                35.0
            )

        # Risk score based on margin utilization
        risk_score = float((float(current_margin_ratio) / max_margin_pct) * 10)  # 0-10 range

        return (True, None, risk_score)

    # === Helper Methods ===

    def _calculate_drawdown_percent(self) -> float:
        """Calculate current drawdown from equity peak."""
        if self.equity_peak <= 0:
            return 0.0

        drawdown = self.equity_peak - self.current_capital
        drawdown_pct = (drawdown / self.equity_peak) * 100
        return float(drawdown_pct)

    def _check_daily_reset(self):
        """Reset daily P&L if new day started."""
        current_date = datetime.now(timezone.utc).date()
        if current_date > self.daily_reset_date:
            logger.info(f"Daily P&L reset: {self.daily_pnl:.2f} USDT")
            self.daily_pnl = Decimal('0')
            self.daily_reset_date = current_date

    async def _emit_risk_alert(
        self,
        severity: RiskAlertSeverity,
        alert_type: RiskAlertType,
        message: str,
        details: Dict[str, Any]
    ):
        """
        Emit risk alert event to EventBus.

        Args:
            severity: Alert severity (CRITICAL, WARNING, INFO)
            alert_type: Type of risk alert
            message: Human-readable message
            details: Additional alert details
        """
        alert_data = {
            "type": "risk_alert",  # WebSocket message type
            "alert_id": f"risk_{datetime.now(timezone.utc).timestamp()}",
            "severity": severity.value,
            "alert_type": alert_type.value,
            "message": message,
            "details": details,
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)  # Epoch milliseconds
        }

        await self.event_bus.publish("risk_alert", alert_data)

        # Log based on severity
        if severity == RiskAlertSeverity.CRITICAL:
            logger.error(f"RISK ALERT [CRITICAL]: {message}", extra=details)
        elif severity == RiskAlertSeverity.WARNING:
            logger.warning(f"RISK ALERT [WARNING]: {message}", extra=details)
        else:
            logger.info(f"RISK ALERT [INFO]: {message}", extra=details)

    # === Public Risk Assessment ===

    def assess_position_risk(
        self,
        symbol: str,
        position_size: float,
        current_price: float,
        volatility: float = 0.02,
        max_drawdown: float = 0.05,
        sharpe_ratio: float = 1.5
    ) -> Dict[str, Any]:
        """
        Assess risk metrics for a potential position.

        Called by StrategyManager before opening positions.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            position_size: Position size as percentage of capital
            current_price: Current market price
            volatility: Estimated volatility (default: 2%)
            max_drawdown: Max acceptable drawdown (default: 5%)
            sharpe_ratio: Expected Sharpe ratio (default: 1.5)

        Returns:
            Dict with risk assessment metrics:
            - risk_score: Overall risk score (0.0-1.0, higher = riskier)
            - position_ok: Whether position is within limits
            - warnings: List of risk warnings
            - recommended_size: Suggested position size if current exceeds limits
        """
        warnings = []
        risk_score = 0.0

        # Check position size against max allowed
        max_position_pct = float(self.risk_config.max_position_size_percent) / 100.0
        # ✅ FIX: Handle 1.0 (100%) correctly as ratio.
        # Previously STRICT < 1 treated 1.0 as 1% (1.0/100).
        position_size_decimal = position_size if position_size <= 1.0 else position_size / 100.0

        if position_size_decimal > max_position_pct:
            warnings.append(f"Position size {position_size_decimal*100:.1f}% exceeds max {max_position_pct*100:.1f}%")
            risk_score += 0.3

        # Adjust for volatility - higher volatility = higher risk
        volatility_risk = min(volatility / 0.05, 1.0)  # Normalize: 5% vol = max risk
        risk_score += volatility_risk * 0.2

        # Adjust for drawdown expectation
        drawdown_risk = min(max_drawdown / 0.10, 1.0)  # Normalize: 10% drawdown = max risk
        risk_score += drawdown_risk * 0.2

        # Consider current drawdown
        current_drawdown = self._calculate_drawdown_percent() / 100.0
        if current_drawdown > 0.05:
            warnings.append(f"Portfolio drawdown {current_drawdown*100:.1f}% - consider reducing exposure")
            risk_score += 0.2

        # Check daily loss limit proximity
        daily_loss_limit = float(self.risk_config.daily_loss_limit_percent) / 100.0
        daily_pnl_pct = float(self.daily_pnl / self.initial_capital) if self.initial_capital > 0 else 0.0
        if daily_pnl_pct < -daily_loss_limit * 0.7:
            warnings.append("Approaching daily loss limit")
            risk_score += 0.1

        # Calculate recommended size
        recommended_size = min(position_size_decimal, max_position_pct)
        if volatility > 0.03:
            recommended_size *= 0.8  # Reduce size in high volatility

        return {
            "risk_score": min(risk_score, 1.0),
            "position_ok": risk_score < 0.7,
            "warnings": warnings,
            "recommended_size": recommended_size,
            "volatility_adjusted": volatility > 0.03,
            "symbol": symbol,
            "current_price": current_price
        }

    def can_open_position_sync(
        self,
        strategy_name: str,
        symbol: str,
        position_size_usdt: float,
        risk_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synchronous check if position can be opened (for StrategyManager).

        This is a simplified check used by StrategyManager before opening positions.
        For full async checks with position tracking, use can_open_position().

        Args:
            strategy_name: Name of the strategy requesting position
            symbol: Trading symbol
            position_size_usdt: Position size in USDT
            risk_metrics: Risk metrics from assess_position_risk()

        Returns:
            Dict with:
            - approved: bool - whether position is approved
            - warnings: List[str] - risk warnings
            - reasons: List[str] - rejection reasons if not approved
        """
        warnings = risk_metrics.get("warnings", [])
        reasons = []

        # Check if position_ok from risk assessment
        if not risk_metrics.get("position_ok", True):
            reasons.append("Risk score too high")

        # Check position size against limits
        max_position_usdt = float(self.current_capital) * float(self.risk_config.max_position_size_percent) / 100.0
        if position_size_usdt > max_position_usdt:
            reasons.append(f"Position size ${position_size_usdt:.2f} exceeds max ${max_position_usdt:.2f}")

        # Check current drawdown
        current_drawdown = self._calculate_drawdown_percent()
        if current_drawdown > float(self.risk_config.max_drawdown_percent):
            reasons.append(f"Max drawdown exceeded: {current_drawdown:.1f}%")

        # Check daily loss limit
        daily_pnl_pct = float(self.daily_pnl / self.initial_capital) * 100 if self.initial_capital > 0 else 0.0
        if daily_pnl_pct < -float(self.risk_config.daily_loss_limit_percent):
            reasons.append(f"Daily loss limit exceeded: {daily_pnl_pct:.1f}%")

        return {
            "approved": len(reasons) == 0,
            "warnings": warnings,
            "reasons": reasons,
            "strategy_name": strategy_name,
            "symbol": symbol,
            "position_size_usdt": position_size_usdt
        }

    # === Public Getters ===

    def get_risk_summary(self) -> Dict[str, Any]:
        """
        Get current risk status summary.

        Returns:
            Dict with all risk metrics
        """
        return {
            "current_capital": float(self.current_capital),
            "initial_capital": float(self.initial_capital),
            "equity_peak": float(self.equity_peak),
            "drawdown_percent": self._calculate_drawdown_percent(),
            "daily_pnl": float(self.daily_pnl),
            "daily_reset_date": self.daily_reset_date.isoformat(),
            "limits": {
                "max_position_size_percent": float(self.risk_config.max_position_size_percent),
                "max_concurrent_positions": self.risk_config.max_concurrent_positions,
                "max_symbol_concentration_percent": float(self.risk_config.max_symbol_concentration_percent),
                "daily_loss_limit_percent": float(self.risk_config.daily_loss_limit_percent),
                "max_drawdown_percent": float(self.risk_config.max_drawdown_percent),
                "max_margin_utilization_percent": float(self.risk_config.max_margin_utilization_percent)
            },
            "allocated_budgets": {k: float(v) for k, v in self._allocated_budgets.items()},
            "total_allocated": float(sum(self._allocated_budgets.values())),
            "available_capital": float(self.current_capital - sum(self._allocated_budgets.values()))
        }

    # === Budget Allocation Methods ===

    def use_budget(self, strategy_name: str, amount: float) -> bool:
        """
        Reserve budget for a strategy position.

        This is a synchronous method for use in strategy evaluation flow.
        Checks if enough unallocated capital is available and reserves it.

        Args:
            strategy_name: Name of the strategy requesting budget
            amount: Amount in USDT to reserve

        Returns:
            True if budget was successfully reserved, False if insufficient funds
        """
        amount_decimal = Decimal(str(amount))

        # Calculate available capital (total - already allocated)
        total_allocated = sum(self._allocated_budgets.values())
        available = self.current_capital - total_allocated

        if amount_decimal > available:
            logger.warning(
                "Budget allocation failed - insufficient funds",
                extra={
                    "strategy_name": strategy_name,
                    "requested": float(amount_decimal),
                    "available": float(available),
                    "total_allocated": float(total_allocated),
                    "current_capital": float(self.current_capital)
                }
            )
            return False

        # Reserve the budget
        if strategy_name in self._allocated_budgets:
            self._allocated_budgets[strategy_name] += amount_decimal
        else:
            self._allocated_budgets[strategy_name] = amount_decimal

        logger.info(
            "Budget allocated for strategy",
            extra={
                "strategy_name": strategy_name,
                "amount": float(amount_decimal),
                "total_for_strategy": float(self._allocated_budgets[strategy_name]),
                "remaining_available": float(available - amount_decimal)
            }
        )
        return True

    def release_budget(self, strategy_name: str, amount: Optional[float] = None) -> bool:
        """
        Release previously allocated budget for a strategy.

        Called when a position is closed or cancelled.

        Args:
            strategy_name: Name of the strategy releasing budget
            amount: Specific amount to release (None = release all for strategy)

        Returns:
            True if budget was released, False if strategy had no allocation
        """
        if strategy_name not in self._allocated_budgets:
            logger.warning(
                "Cannot release budget - no allocation found",
                extra={"strategy_name": strategy_name}
            )
            return False

        if amount is None:
            # Release all budget for this strategy
            released = self._allocated_budgets.pop(strategy_name)
            logger.info(
                "All budget released for strategy",
                extra={
                    "strategy_name": strategy_name,
                    "released": float(released)
                }
            )
        else:
            amount_decimal = Decimal(str(amount))
            current = self._allocated_budgets[strategy_name]

            if amount_decimal >= current:
                # Release all
                released = self._allocated_budgets.pop(strategy_name)
            else:
                # Partial release
                self._allocated_budgets[strategy_name] -= amount_decimal
                released = amount_decimal

            logger.info(
                "Budget partially released for strategy",
                extra={
                    "strategy_name": strategy_name,
                    "released": float(released),
                    "remaining": float(self._allocated_budgets.get(strategy_name, Decimal('0')))
                }
            )
        return True

    def get_allocated_budget(self, strategy_name: str) -> float:
        """
        Get currently allocated budget for a strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Allocated amount in USDT (0.0 if no allocation)
        """
        return float(self._allocated_budgets.get(strategy_name, Decimal('0')))

    def get_available_capital(self) -> float:
        """
        Get available capital for new positions.

        Returns:
            Available capital (current_capital - total_allocated)
        """
        total_allocated = sum(self._allocated_budgets.values())
        return float(self.current_capital - total_allocated)
