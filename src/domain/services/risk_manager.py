"""
Risk Manager - Budget and Risk Management for Trading Strategies
==================================================================
Manages budget allocation, position limits, and risk assessment for strategies.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ...core.logger import StructuredLogger


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BudgetAllocation:
    """Budget allocation for a strategy"""
    strategy_name: str
    allocated_amount: float
    used_amount: float = 0.0
    max_allocation_pct: float = 5.0  # Max 5% of total budget
    last_updated: datetime = field(default_factory=datetime.now)

    @property
    def available_amount(self) -> float:
        """Available budget for this strategy"""
        return self.allocated_amount - self.used_amount

    @property
    def utilization_pct(self) -> float:
        """Budget utilization percentage"""
        if self.allocated_amount == 0:
            return 0.0
        return (self.used_amount / self.allocated_amount) * 100


@dataclass
class RiskMetrics:
    """Risk metrics for a position or strategy"""
    symbol: str
    position_size: float
    volatility: float
    max_drawdown: float
    sharpe_ratio: float
    var_95: float  # Value at Risk 95%
    expected_return: float
    risk_level: RiskLevel

    def assess_risk_level(self) -> RiskLevel:
        """Assess overall risk level based on metrics"""
        risk_score = 0

        # High volatility increases risk
        if self.volatility > 0.05:  # 5% volatility
            risk_score += 2
        elif self.volatility > 0.03:  # 3% volatility
            risk_score += 1

        # Large drawdown increases risk
        if self.max_drawdown > 0.10:  # 10% drawdown
            risk_score += 2
        elif self.max_drawdown > 0.05:  # 5% drawdown
            risk_score += 1

        # Low Sharpe ratio increases risk
        if self.sharpe_ratio < 0.5:
            risk_score += 2
        elif self.sharpe_ratio < 1.0:
            risk_score += 1

        # High VaR increases risk
        if self.var_95 > 0.08:  # 8% VaR
            risk_score += 2
        elif self.var_95 > 0.05:  # 5% VaR
            risk_score += 1

        # Large position size increases risk
        if self.position_size > 0.05:  # 5% of portfolio
            risk_score += 1

        if risk_score >= 5:
            return RiskLevel.CRITICAL
        elif risk_score >= 3:
            return RiskLevel.HIGH
        elif risk_score >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


class RiskManager:
    """
    Risk manager for budget allocation and risk assessment.
    Handles strategy budget limits, position sizing, and risk monitoring.
    """

    def __init__(self, logger: StructuredLogger, total_budget: float = 10000.0):
        self.logger = logger
        self.total_budget = total_budget
        self.used_budget = 0.0

        # Budget allocations per strategy
        self.allocations: Dict[str, BudgetAllocation] = {}

        # Risk limits
        self.max_strategy_allocation_pct = 10.0  # Max 10% per strategy
        self.max_total_utilization_pct = 80.0  # Max 80% total utilization
        self.min_liquidity_buffer_pct = 20.0  # Keep 20% as liquidity buffer

        # Risk thresholds
        self.max_volatility_threshold = 0.08  # 8% max volatility
        self.max_drawdown_threshold = 0.15  # 15% max drawdown
        self.min_sharpe_threshold = 0.3  # Minimum Sharpe ratio

        # Position sizing settings
        self.default_position_size_pct = 2.0  # Default 2% of total budget per position
        self.max_position_size_pct = 5.0  # Max 5% of total budget per position
        self.kelly_fraction = 0.5  # Use half Kelly for safety

        # Stop-loss settings
        self.default_stop_loss_pct = 2.0  # Default 2% stop loss
        self.trailing_stop_enabled = True
        self.trailing_stop_distance_pct = 1.0  # 1% trailing stop distance

        self.logger.info("risk_manager.initialized", {
            "total_budget": total_budget,
            "max_strategy_allocation_pct": self.max_strategy_allocation_pct,
            "default_position_size_pct": self.default_position_size_pct
        })

    def allocate_budget(self, strategy_name: str, amount: float, max_allocation_pct: float = 5.0) -> bool:
        """Allocate budget for a strategy"""
        # Validate allocation limits
        if amount <= 0:
            self.logger.error("risk_manager.invalid_allocation", {
                "strategy_name": strategy_name,
                "amount": amount
            })
            return False

        # Check strategy allocation limit
        max_strategy_budget = self.total_budget * (max_allocation_pct / 100)
        if amount > max_strategy_budget:
            self.logger.warning("risk_manager.allocation_exceeds_limit", {
                "strategy_name": strategy_name,
                "requested": amount,
                "max_allowed": max_strategy_budget
            })
            return False

        # Check total budget availability
        available_budget = self.total_budget - self.used_budget
        if amount > available_budget:
            self.logger.warning("risk_manager.insufficient_budget", {
                "strategy_name": strategy_name,
                "requested": amount,
                "available": available_budget
            })
            return False

        # Create or update allocation
        if strategy_name in self.allocations:
            self.allocations[strategy_name].allocated_amount = amount
            self.allocations[strategy_name].max_allocation_pct = max_allocation_pct
        else:
            self.allocations[strategy_name] = BudgetAllocation(
                strategy_name=strategy_name,
                allocated_amount=amount,
                max_allocation_pct=max_allocation_pct
            )

        self.logger.info("risk_manager.budget_allocated", {
            "strategy_name": strategy_name,
            "amount": amount,
            "max_allocation_pct": max_allocation_pct
        })

        return True

    def use_budget(self, strategy_name: str, amount: float) -> bool:
        """Use budget for a trade"""
        if strategy_name not in self.allocations:
            self.logger.error("risk_manager.no_allocation", {
                "strategy_name": strategy_name
            })
            return False

        allocation = self.allocations[strategy_name]

        if allocation.available_amount < amount:
            self.logger.warning("risk_manager.insufficient_allocation", {
                "strategy_name": strategy_name,
                "requested": amount,
                "available": allocation.available_amount
            })
            return False

        allocation.used_amount += amount
        allocation.last_updated = datetime.now()
        self.used_budget += amount

        self.logger.info("risk_manager.budget_used", {
            "strategy_name": strategy_name,
            "amount": amount,
            "remaining": allocation.available_amount
        })

        return True

    def release_budget(self, strategy_name: str, amount: float) -> bool:
        """Release budget (e.g., when position is closed)"""
        if strategy_name not in self.allocations:
            return False

        allocation = self.allocations[strategy_name]
        released_amount = min(amount, allocation.used_amount)

        allocation.used_amount -= released_amount
        allocation.last_updated = datetime.now()
        self.used_budget -= released_amount

        self.logger.info("risk_manager.budget_released", {
            "strategy_name": strategy_name,
            "amount": released_amount
        })

        return True

    def assess_position_risk(self,
                           symbol: str,
                           position_size: float,
                           current_price: float,
                           volatility: float = 0.0,
                           max_drawdown: float = 0.0,
                           sharpe_ratio: float = 1.0) -> RiskMetrics:
        """Assess risk for a position"""
        # Calculate VaR (simplified)
        var_95 = volatility * 1.645  # 95% confidence

        # Estimate expected return based on Sharpe ratio
        expected_return = sharpe_ratio * volatility

        risk_metrics = RiskMetrics(
            symbol=symbol,
            position_size=position_size,
            volatility=volatility,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            var_95=var_95,
            expected_return=expected_return,
            risk_level=RiskLevel.LOW  # Will be assessed
        )

        risk_metrics.risk_level = risk_metrics.assess_risk_level()

        self.logger.debug("risk_manager.position_assessed", {
            "symbol": symbol,
            "position_size": position_size,
            "risk_level": risk_metrics.risk_level.value,
            "var_95": var_95
        })

        return risk_metrics

    def can_open_position(self,
                         strategy_name: str,
                         symbol: str,
                         position_size_usdt: float,
                         risk_metrics: Optional[RiskMetrics] = None) -> Dict[str, Any]:
        """Check if a position can be opened based on risk limits"""
        result = {
            "approved": True,
            "reasons": [],
            "warnings": []
        }

        # Check strategy allocation
        if strategy_name not in self.allocations:
            result["approved"] = False
            result["reasons"].append(f"No budget allocation for strategy: {strategy_name}")
            return result

        allocation = self.allocations[strategy_name]

        if allocation.available_amount < position_size_usdt:
            result["approved"] = False
            result["reasons"].append(
                f"Insufficient budget: requested {position_size_usdt}, available {allocation.available_amount}"
            )

        # Check total utilization
        total_utilization_pct = (self.used_budget / self.total_budget) * 100
        if total_utilization_pct > self.max_total_utilization_pct:
            result["approved"] = False
            result["reasons"].append(
                f"Total utilization too high: {total_utilization_pct:.1f}% > {self.max_total_utilization_pct}%"
            )

        # Check risk metrics if provided
        if risk_metrics:
            if risk_metrics.volatility > self.max_volatility_threshold:
                result["approved"] = False
                result["reasons"].append(
                    f"Volatility too high: {risk_metrics.volatility:.3f} > {self.max_volatility_threshold}"
                )

            if risk_metrics.max_drawdown > self.max_drawdown_threshold:
                result["approved"] = False
                result["reasons"].append(
                    f"Max drawdown too high: {risk_metrics.max_drawdown:.3f} > {self.max_drawdown_threshold}"
                )

            if risk_metrics.sharpe_ratio < self.min_sharpe_threshold:
                result["warnings"].append(
                    f"Low Sharpe ratio: {risk_metrics.sharpe_ratio:.2f} < {self.min_sharpe_threshold}"
                )

            if risk_metrics.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                result["warnings"].append(f"High risk level: {risk_metrics.risk_level.value}")

        return result

    def get_budget_summary(self) -> Dict[str, Any]:
        """Get budget utilization summary"""
        total_allocated = sum(alloc.allocated_amount for alloc in self.allocations.values())
        total_used = sum(alloc.used_amount for alloc in self.allocations.values())

        return {
            "total_budget": self.total_budget,
            "used_budget": self.used_budget,
            "available_budget": self.total_budget - self.used_budget,
            "utilization_pct": (self.used_budget / self.total_budget) * 100 if self.total_budget > 0 else 0,
            "total_allocated": total_allocated,
            "total_used": total_used,
            "allocations": [
                {
                    "strategy_name": alloc.strategy_name,
                    "allocated": alloc.allocated_amount,
                    "used": alloc.used_amount,
                    "available": alloc.available_amount,
                    "utilization_pct": alloc.utilization_pct,
                    "max_allocation_pct": alloc.max_allocation_pct
                }
                for alloc in self.allocations.values()
            ]
        }

    def get_strategy_allocation(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get budget allocation for a specific strategy"""
        if strategy_name not in self.allocations:
            return None

        alloc = self.allocations[strategy_name]
        return {
            "strategy_name": alloc.strategy_name,
            "allocated_amount": alloc.allocated_amount,
            "used_amount": alloc.used_amount,
            "available_amount": alloc.available_amount,
            "utilization_pct": alloc.utilization_pct,
            "max_allocation_pct": alloc.max_allocation_pct,
            "last_updated": alloc.last_updated.isoformat()
        }

    def emergency_stop(self, strategy_name: Optional[str] = None) -> List[str]:
        """Emergency stop - release all budget for strategy or all strategies"""
        released_strategies = []

        if strategy_name:
            if strategy_name in self.allocations:
                alloc = self.allocations[strategy_name]
                released_amount = alloc.used_amount
                alloc.used_amount = 0
                self.used_budget -= released_amount
                released_strategies.append(strategy_name)
        else:
            # Release all
            for alloc in self.allocations.values():
                released_amount = alloc.used_amount
                alloc.used_amount = 0
                self.used_budget -= released_amount
                released_strategies.append(alloc.strategy_name)

        if released_strategies:
            self.logger.warning("risk_manager.emergency_stop", {
                "released_strategies": released_strategies,
                "total_released": sum(self.allocations[s].used_amount for s in released_strategies)
            })

        return released_strategies

    def calculate_position_size(self,
                              strategy_name: str,
                              signal_confidence: float,
                              current_price: float,
                              volatility: float = 0.0,
                              sizing_method: str = "percentage") -> Dict[str, Any]:
        """
        Calculate position size using various risk management methods.

        Args:
            strategy_name: Name of the strategy
            signal_confidence: Signal confidence (0.0 to 1.0)
            current_price: Current market price
            volatility: Asset volatility (optional)
            sizing_method: "percentage", "kelly", or "fixed"

        Returns:
            Dict with position size details
        """
        result = {
            "position_size_usd": 0.0,
            "position_size_pct": 0.0,
            "max_position_usd": 0.0,
            "risk_amount_usd": 0.0,
            "stop_loss_price": 0.0,
            "method_used": sizing_method,
            "approved": False,
            "reasons": []
        }

        # Get available budget for strategy
        if strategy_name not in self.allocations:
            result["reasons"].append(f"No budget allocation for strategy: {strategy_name}")
            return result

        allocation = self.allocations[strategy_name]
        available_budget = allocation.available_amount

        if available_budget <= 0:
            result["reasons"].append("No available budget for strategy")
            return result

        # Calculate base position size
        if sizing_method == "kelly":
            position_size = self._calculate_kelly_position_size(
                available_budget, signal_confidence, volatility
            )
        elif sizing_method == "fixed":
            position_size = min(available_budget * 0.1, 1000.0)  # Fixed 10% or $1000 max
        else:  # percentage (default)
            position_size = self._calculate_percentage_position_size(
                available_budget, signal_confidence
            )

        # Apply maximum position limits
        max_position = self.total_budget * (self.max_position_size_pct / 100)
        position_size = min(position_size, max_position, available_budget)

        if position_size <= 0:
            result["reasons"].append("Calculated position size is zero or negative")
            return result

        # Calculate stop loss
        stop_loss_price = self._calculate_stop_loss_price(current_price, position_size)

        # Calculate risk amount
        risk_amount = abs(current_price - stop_loss_price) * (position_size / current_price)

        result.update({
            "position_size_usd": position_size,
            "position_size_pct": (position_size / self.total_budget) * 100,
            "max_position_usd": max_position,
            "risk_amount_usd": risk_amount,
            "stop_loss_price": stop_loss_price,
            "approved": True
        })

        self.logger.debug("risk_manager.position_size_calculated", {
            "strategy": strategy_name,
            "method": sizing_method,
            "size_usd": position_size,
            "confidence": signal_confidence,
            "stop_loss": stop_loss_price
        })

        return result

    def _calculate_percentage_position_size(self, available_budget: float, confidence: float) -> float:
        """Calculate position size using percentage-based method."""
        # Base position size as percentage of available budget
        base_pct = self.default_position_size_pct / 100

        # Adjust for confidence (0.5x to 2x multiplier)
        confidence_multiplier = 0.5 + (confidence * 1.5)

        position_pct = base_pct * confidence_multiplier
        position_size = available_budget * position_pct

        return position_size

    def _calculate_kelly_position_size(self,
                                     available_budget: float,
                                     confidence: float,
                                     volatility: float) -> float:
        """Calculate position size using Kelly Criterion."""
        # Simplified Kelly formula: f = (p - q) / b
        # Where p = win probability, q = loss probability, b = win/loss ratio

        # Estimate win probability from confidence
        win_prob = max(0.5, min(0.8, confidence))  # Clamp between 50% and 80%

        # Estimate win/loss ratio (simplified)
        avg_win_loss_ratio = 2.0  # Assume 2:1 win/loss ratio

        # Kelly fraction
        kelly_pct = (win_prob - (1 - win_prob)) / avg_win_loss_ratio
        kelly_pct *= self.kelly_fraction  # Use fraction of Kelly for safety

        # Adjust for volatility
        if volatility > 0.05:  # High volatility reduces position size
            kelly_pct *= 0.5

        position_size = available_budget * kelly_pct

        return max(0.0, position_size)

    def _calculate_stop_loss_price(self, current_price: float, position_size: float) -> float:
        """Calculate stop loss price based on risk tolerance."""
        # Simple percentage-based stop loss
        stop_loss_pct = self.default_stop_loss_pct / 100
        stop_loss_price = current_price * (1 - stop_loss_pct)

        return stop_loss_price

    def check_stop_loss_trigger(self,
                              symbol: str,
                              current_price: float,
                              entry_price: float,
                              position_size: float) -> Dict[str, Any]:
        """
        Check if stop loss should be triggered.

        Returns:
            Dict with trigger decision and details
        """
        result = {
            "trigger_stop_loss": False,
            "stop_loss_price": 0.0,
            "current_loss_pct": 0.0,
            "reason": ""
        }

        # Calculate stop loss price
        stop_loss_price = self._calculate_stop_loss_price(entry_price, position_size)
        result["stop_loss_price"] = stop_loss_price

        # Check if current price has hit stop loss
        if current_price <= stop_loss_price:
            loss_pct = ((entry_price - current_price) / entry_price) * 100
            result.update({
                "trigger_stop_loss": True,
                "current_loss_pct": loss_pct,
                "reason": f"Price {current_price:.2f} hit stop loss at {stop_loss_price:.2f} ({loss_pct:.2f}% loss)"
            })

            self.logger.warning("risk_manager.stop_loss_triggered", {
                "symbol": symbol,
                "current_price": current_price,
                "stop_loss_price": stop_loss_price,
                "loss_pct": loss_pct
            })

        return result

    def update_trailing_stop(self,
                           symbol: str,
                           current_price: float,
                           highest_price: float,
                           position_size: float) -> Dict[str, Any]:
        """
        Update trailing stop loss if enabled.

        Returns:
            Dict with updated stop loss details
        """
        if not self.trailing_stop_enabled:
            return {"updated": False, "reason": "Trailing stops disabled"}

        # Calculate new stop loss based on trailing distance from highest price
        trailing_distance_pct = self.trailing_stop_distance_pct / 100
        new_stop_loss = highest_price * (1 - trailing_distance_pct)

        result = {
            "updated": False,
            "new_stop_loss": new_stop_loss,
            "highest_price": highest_price,
            "reason": ""
        }

        # Only update if new stop is higher than current price (for long positions)
        # This is a simplified implementation
        if new_stop_loss > current_price * 0.95:  # Ensure minimum distance
            result["updated"] = True
            result["reason"] = f"Trailing stop updated to {new_stop_loss:.2f}"

        return result