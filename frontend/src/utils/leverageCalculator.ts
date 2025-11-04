/**
 * Leverage Calculator - Liquidation Price and Risk Calculations
 * =============================================================
 * Utilities for calculating liquidation prices, margin requirements,
 * and risk metrics for leveraged trading positions.
 */

export interface LeverageCalculation {
  leverage: number;
  entryPrice: number;
  direction: 'LONG' | 'SHORT';
  liquidationPrice: number;
  liquidationDistance: number; // Percentage distance to liquidation
  marginRequirement: number; // Percentage of position value
  riskLevel: 'LOW' | 'MODERATE' | 'HIGH' | 'EXTREME';
}

/**
 * Calculate liquidation price for a leveraged position.
 *
 * Formula:
 * - LONG: liquidation = entry × (1 - 1/leverage)
 * - SHORT: liquidation = entry × (1 + 1/leverage)
 *
 * @param entryPrice Entry price
 * @param leverage Leverage multiplier (1-200)
 * @param direction Position direction
 * @returns Liquidation price
 *
 * @example
 * calculateLiquidationPrice(50000, 3, 'SHORT')
 * // Returns: 66666.67 (33.33% above entry)
 */
export function calculateLiquidationPrice(
  entryPrice: number,
  leverage: number,
  direction: 'LONG' | 'SHORT'
): number {
  if (leverage <= 1.0) {
    // No liquidation for non-leveraged positions
    return direction === 'LONG' ? 0 : Infinity;
  }

  if (direction === 'LONG') {
    // LONG: liquidation when price drops by (1/leverage)%
    // Example: 3x leverage → liquidation @ -33.33%
    return entryPrice * (1 - 1 / leverage);
  } else {
    // SHORT: liquidation when price rises by (1/leverage)%
    // Example: 3x leverage → liquidation @ +33.33%
    return entryPrice * (1 + 1 / leverage);
  }
}

/**
 * Calculate percentage distance from current price to liquidation.
 *
 * @param currentPrice Current market price
 * @param liquidationPrice Liquidation price
 * @param direction Position direction
 * @returns Distance to liquidation as percentage (positive = safe, negative = liquidated)
 *
 * @example
 * calculateLiquidationDistance(55000, 66666, 'SHORT')
 * // Returns: 17.5 (17.5% away from liquidation)
 */
export function calculateLiquidationDistance(
  currentPrice: number,
  liquidationPrice: number,
  direction: 'LONG' | 'SHORT'
): number {
  if (direction === 'SHORT') {
    // SHORT: distance = (liquidation - current) / current
    return ((liquidationPrice - currentPrice) / currentPrice) * 100;
  } else {
    // LONG: distance = (current - liquidation) / liquidation
    return ((currentPrice - liquidationPrice) / liquidationPrice) * 100;
  }
}

/**
 * Calculate margin requirement percentage.
 *
 * @param leverage Leverage multiplier
 * @returns Margin requirement as percentage
 *
 * @example
 * calculateMarginRequirement(3)
 * // Returns: 33.33 (need 33.33% margin for 3x leverage)
 */
export function calculateMarginRequirement(leverage: number): number {
  return (1 / leverage) * 100;
}

/**
 * Assess risk level based on leverage.
 *
 * @param leverage Leverage multiplier
 * @returns Risk level
 */
export function assessLeverageRisk(leverage: number): 'LOW' | 'MODERATE' | 'HIGH' | 'EXTREME' {
  if (leverage <= 1) return 'LOW';
  if (leverage <= 2) return 'MODERATE';
  if (leverage <= 5) return 'HIGH';
  return 'EXTREME';
}

/**
 * Get comprehensive leverage calculation.
 *
 * @param entryPrice Entry price
 * @param leverage Leverage multiplier
 * @param direction Position direction
 * @returns Complete leverage calculation
 */
export function getLeverageCalculation(
  entryPrice: number,
  leverage: number,
  direction: 'LONG' | 'SHORT'
): LeverageCalculation {
  const liquidationPrice = calculateLiquidationPrice(entryPrice, leverage, direction);
  const liquidationDistance = calculateLiquidationDistance(entryPrice, liquidationPrice, direction);
  const marginRequirement = calculateMarginRequirement(leverage);
  const riskLevel = assessLeverageRisk(leverage);

  return {
    leverage,
    entryPrice,
    direction,
    liquidationPrice,
    liquidationDistance,
    marginRequirement,
    riskLevel,
  };
}

/**
 * Format leverage for display.
 *
 * @param leverage Leverage multiplier
 * @returns Formatted string
 *
 * @example
 * formatLeverage(3)
 * // Returns: "3x"
 */
export function formatLeverage(leverage: number): string {
  return `${leverage}x`;
}

/**
 * Format liquidation price for display.
 *
 * @param price Liquidation price
 * @param direction Position direction
 * @returns Formatted string with direction indicator
 *
 * @example
 * formatLiquidationPrice(66666.67, 'SHORT')
 * // Returns: "$66,666.67 ↑"
 */
export function formatLiquidationPrice(price: number, direction: 'LONG' | 'SHORT'): string {
  if (!isFinite(price) || price <= 0) {
    return 'N/A';
  }

  const formatted = price.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const arrow = direction === 'SHORT' ? '↑' : '↓';
  return `${formatted} ${arrow}`;
}

/**
 * Get recommended leverage for pump & dump SHORT strategies.
 *
 * @returns Recommended leverage and reasoning
 */
export function getRecommendedLeverage(): {
  leverage: number;
  reasoning: string;
} {
  return {
    leverage: 3,
    reasoning:
      '3x leverage is optimal for SHORT strategies: balances profit potential (3x gains) ' +
      'with acceptable liquidation risk (33% price increase). Higher leverage (5x+) risks ' +
      'liquidation during pump volatility.',
  };
}
