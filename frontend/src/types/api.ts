// API Response Types
export interface ApiResponse<T = any> {
  type: 'response' | 'error';
  version: string;
  timestamp: string;
  id?: string;
  status?: string;
  data?: T;
  error_code?: string;
  error_message?: string;
}

// Strategy Types
export interface Strategy {
  strategy_name: string;
  enabled: boolean;
  current_state: string;
  symbol?: string;
  active_symbols_count?: number;
  last_event?: any;
  last_state_change?: string;
}

export interface StrategyConfig {
  strategy_name: string;
  enabled?: boolean;
  global_limits?: {
    base_position_pct?: number;
    max_position_size_usdt?: number;
    min_position_size_usdt?: number;
    max_leverage?: number;
    stop_loss_buffer_pct?: number;
    target_profit_pct?: number;
    max_allocation_pct?: number;
  };
  signal_detection_conditions?: Record<string, any>;
  risk_assessment_conditions?: Record<string, any>;
  entry_conditions?: Record<string, any>;
  emergency_exit_conditions?: Record<string, any>;
}

// Indicator Types
export interface Indicator {
  key: string;
  symbol: string;
  indicator: string;
  timeframe: string;
  data_points?: number;
  period?: number;
  scope?: string;
  value?: number;
  timestamp?: string;
  metadata?: Record<string, any>;
}

export interface IndicatorValue {
  symbol: string;
  indicator: string;
  timeframe: string;
  current_value: number;
  timestamp: string;
}

// Order Types
export interface Order {
  order_id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  type: string;
  quantity: number;
  price: number;
  status: string;
  timestamp: string;
  pnl?: number;
}

// Position Types
export interface Position {
  session_id?: string;
  position_id?: string;
  symbol: string;
  side?: 'LONG' | 'SHORT';
  quantity: number;
  avg_price?: number;
  entry_price?: number;
  current_price?: number;
  liquidation_price?: number;
  unrealized_pnl: number;
  unrealized_pnl_pct?: number;
  margin?: number;
  leverage?: number;
  margin_ratio?: number;
  opened_at?: string;
  updated_at?: string;
  status?: 'OPEN' | 'CLOSED' | 'LIQUIDATED';
  stop_loss_price?: number;
  take_profit_price?: number;
  strategy_name?: string;
}

// Trading Performance
export interface TradingPerformance {
  total_trades: number;
  winning_trades: number;
  win_rate: number;
  total_pnl: number;
  max_drawdown: number;
  active_positions: number;
}

// Wallet Types
export interface WalletBalance {
  timestamp: string;
  assets: Record<string, {
    free: number;
    locked: number;
  }>;
  total_usd_estimate: number;
  source: string;
}

// WebSocket Message Types
export type WSMessageType =
  | 'subscribe'
  | 'unsubscribe'
  | 'command'
  | 'query'
  | 'heartbeat'
  | 'auth'
  | 'data'
  | 'signal'
  | 'alert'
  | 'response'
  | 'error'
  | 'status'
  | 'session_start'
  | 'session_stop'
  | 'session_status'
  | 'collection_start'
  | 'collection_stop'
  | 'collection_status'
  | 'results_request'
  | 'get_strategies'
  | 'activate_strategy'
  | 'deactivate_strategy'
  | 'get_strategy_status'
  | 'validate_strategy_config'
  | 'upsert_strategy'
  | 'handshake';

export interface WSMessage {
  type: WSMessageType;
  id?: string;
  stream?: string;
  data?: any;
  error_code?: string;
  error_message?: string;
}

// Strategy Node Types for Canvas
export interface StrategyNode {
  id: string;
  type: 'indicator' | 'condition' | 'action';
  position: { x: number; y: number };
  data: {
    label: string;
    config: Record<string, any>;
    validation_errors?: string[];
  };
}

export interface StrategyEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

// Session Types
export interface TradingSession {
  session_id: string;
  mode: string;
  status: string;
  symbols: string[];
  progress?: number;
  start_time?: string;
  metrics?: Record<string, any>;
}
