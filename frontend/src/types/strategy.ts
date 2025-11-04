// 5-Section Strategy Types for user_feedback.md implementation

// Phase 2 Sprint 1: OR/NOT Logic Support
export type LogicOperator = 'AND' | 'OR' | 'NOT';

export interface Condition {
  id: string;
  indicatorId: string;
  operator: '>' | '<' | '>=' | '<=' | '==';  // Added '==' for equality
  value: number;
  logic?: LogicOperator;  // Phase 2: Logic connector to next condition (default: AND)
}

// Phase 2 Sprint 1: Condition Groups for complex logic
// Allows expressions like: (A AND B) OR (C AND D)
export interface ConditionGroup {
  id: string;
  logic: 'AND' | 'OR';  // How this group combines with next group
  conditions: Condition[];
  groups?: ConditionGroup[];  // Nested groups for complex logic
}

export interface OrderConfig {
  priceIndicatorId?: string;
  timeoutSeconds?: number; // SPRINT_GOAL_04: Z1 timeout functionality
  stopLoss?: {
    enabled: boolean;
    indicatorId?: string;
    offsetPercent: number;
    calculationMode?: 'ABSOLUTE' | 'RELATIVE_TO_ENTRY'; // For SHORT positions
    riskScaling?: { // SPRINT_GOAL_04: Risk scaling for SL
      enabled: boolean;
      riskIndicatorId?: string;
      lowRiskThreshold: number;
      lowRiskScale: number;
      highRiskThreshold: number;
      highRiskScale: number;
    };
  };
  takeProfit?: {
    enabled: boolean;
    indicatorId?: string;
    offsetPercent: number;
    calculationMode?: 'ABSOLUTE' | 'RELATIVE_TO_ENTRY'; // For SHORT positions
    riskScaling?: { // SPRINT_GOAL_04: Risk scaling for TP
      enabled: boolean;
      riskIndicatorId?: string;
      lowRiskThreshold: number;
      lowRiskScale: number;
      highRiskThreshold: number;
      highRiskScale: number;
    };
  };
  positionSize: {
    type: 'fixed' | 'percentage';
    value: number;
    riskScaling?: { // SPRINT_GOAL_04: Risk scaling for position size
      enabled: boolean;
      riskIndicatorId?: string;
      lowRiskThreshold: number;
      lowRiskScale: number;
      highRiskThreshold: number;
      highRiskScale: number;
    };
  };
  leverage?: number; // TIER 1.4: Leverage multiplier for futures trading (1-10x, default: 1)
  riskAdjustment?: {
    enabled: boolean;
    indicatorId: string;
    minRiskPercent: number;
    maxRiskPercent: number;
    scalingPoints: Array<{
      riskValue: number;
      positionSizePercent: number;
    }>;
  };
}

export interface CloseOrderConfig {
  priceIndicatorId?: string;
  riskAdjustedPricing?: { // SPRINT_GOAL_04: Risk-adjusted close pricing for ZE1
    enabled: boolean;
    riskIndicatorId?: string;
    lowRiskThreshold: number;
    lowRiskAdjustment: number;
    highRiskThreshold: number;
    highRiskAdjustment: number;
  };
  riskAdjustment?: {
    enabled: boolean;
    indicatorId: string;
    minRiskPercent: number;
    maxRiskPercent: number;
    scalingPoints: Array<{
      riskValue: number;
      priceAdjustmentPercent: number;
    }>;
  };
}

export interface CancellationConfig {
  timeoutSeconds: number;
  conditions: Condition[];
  cooldownMinutes: number; // SPRINT_GOAL_04: O1 cooldown functionality
}

export interface EmergencyConfig {
  conditions: Condition[];
  cooldownMinutes: number;
  actions: {
    cancelPending: boolean;
    closePosition: boolean;
    logEvent: boolean;
  };
}

export interface Strategy5Section {
  id?: string;
  name: string;
  direction?: 'LONG' | 'SHORT' | 'BOTH';  // Trading direction (default: LONG)
  s1_signal: {
    conditions: Condition[];
  };
  z1_entry: {
    conditions: Condition[];
  } & OrderConfig;
  o1_cancel: CancellationConfig;
  ze1_close: {
    conditions: Condition[];
  } & CloseOrderConfig;
  emergency_exit: EmergencyConfig;
  // SPRINT_GOAL_04: Section 4 (ZE1) is now optional
  ze1_enabled?: boolean;
  created_at?: string;
  updated_at?: string;
}

// Legacy alias for backward compatibility
export interface Strategy4Section extends Strategy5Section {}

export interface IndicatorVariant {
  id: string;
  name: string;
  baseType: string;
  parameters: Record<string, any>;
  type: 'general' | 'risk' | 'stop_loss_price' | 'take_profit_price' | 'order_price' | 'close_price';
  description: string;
  isActive: boolean;
  lastValue?: number;
  lastUpdate?: string;
}

export interface StrategyValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  sectionErrors: {
    s1?: string[];
    z1?: string[];
    o1?: string[];
    ze1?: string[];
    emergency?: string[];
  };
}