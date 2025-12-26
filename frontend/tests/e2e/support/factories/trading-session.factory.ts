/**
 * Trading Session Factory
 * ========================
 *
 * Faker-based factory for generating test trading session configurations.
 *
 * @see TEA Knowledge Base: data-factories.md
 */

import { faker } from '@faker-js/faker';
import { Strategy, createStrategy } from './strategy.factory';

// ============================================
// TYPE DEFINITIONS
// ============================================

export type TradingMode = 'Live' | 'Paper' | 'Backtest';

export type SessionStatus = 'idle' | 'configuring' | 'running' | 'paused' | 'stopped' | 'completed' | 'error';

export type TradingSessionConfig = {
  id: string;
  mode: TradingMode;
  strategies: string[]; // Strategy IDs
  symbols: string[];
  leverage: number;
  positionSize: number;
  stopLoss: number; // Percentage
  takeProfit: number; // Percentage
  maxOpenPositions: number;
  riskPerTrade: number; // Percentage of portfolio
};

export type TradingSession = {
  id: string;
  config: TradingSessionConfig;
  status: SessionStatus;
  startedAt: string | null;
  endedAt: string | null;
  createdAt: string;
  stats: SessionStats;
};

export type SessionStats = {
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  totalPnL: number;
  winRate: number;
  maxDrawdown: number;
  sharpeRatio: number;
};

// ============================================
// SYMBOL OPTIONS
// ============================================

export const COMMON_SYMBOLS = [
  'BTCUSDT',
  'ETHUSDT',
  'BNBUSDT',
  'XRPUSDT',
  'SOLUSDT',
  'ADAUSDT',
  'DOGEUSDT',
  'MATICUSDT',
  'DOTUSDT',
  'AVAXUSDT',
] as const;

// ============================================
// HELPER FACTORIES
// ============================================

/**
 * Generate random symbols for testing
 */
export const createSymbol = (): string => faker.helpers.arrayElement(COMMON_SYMBOLS);

/**
 * Generate multiple random symbols
 */
export const createSymbols = (count = 3): string[] =>
  faker.helpers.arrayElements(COMMON_SYMBOLS, Math.min(count, COMMON_SYMBOLS.length));

/**
 * Create session statistics
 */
export const createSessionStats = (overrides: Partial<SessionStats> = {}): SessionStats => {
  const totalTrades = overrides.totalTrades ?? faker.number.int({ min: 10, max: 100 });
  const winningTrades = overrides.winningTrades ?? faker.number.int({ min: 0, max: totalTrades });
  const losingTrades = totalTrades - winningTrades;

  return {
    totalTrades,
    winningTrades,
    losingTrades,
    totalPnL: faker.number.float({ min: -1000, max: 5000, fractionDigits: 2 }),
    winRate: totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0,
    maxDrawdown: faker.number.float({ min: 0, max: 30, fractionDigits: 2 }),
    sharpeRatio: faker.number.float({ min: -1, max: 3, fractionDigits: 2 }),
    ...overrides,
  };
};

// ============================================
// SESSION CONFIG FACTORY
// ============================================

/**
 * Create a trading session configuration
 */
export const createSessionConfig = (overrides: Partial<TradingSessionConfig> = {}): TradingSessionConfig => ({
  id: faker.string.uuid(),
  mode: 'Paper',
  strategies: [faker.string.uuid()], // Default: one strategy
  symbols: createSymbols(2),
  leverage: faker.helpers.arrayElement([1, 2, 3, 5, 10, 20]),
  positionSize: faker.number.float({ min: 0.01, max: 1.0, fractionDigits: 2 }),
  stopLoss: faker.number.float({ min: 1, max: 10, fractionDigits: 1 }),
  takeProfit: faker.number.float({ min: 2, max: 20, fractionDigits: 1 }),
  maxOpenPositions: faker.number.int({ min: 1, max: 10 }),
  riskPerTrade: faker.number.float({ min: 0.5, max: 5, fractionDigits: 1 }),
  ...overrides,
});

// ============================================
// SESSION FACTORY
// ============================================

/**
 * Create a complete trading session
 */
export const createTradingSession = (overrides: Partial<TradingSession> = {}): TradingSession => {
  const now = new Date().toISOString();

  return {
    id: faker.string.uuid(),
    config: createSessionConfig(overrides.config),
    status: 'idle',
    startedAt: null,
    endedAt: null,
    createdAt: now,
    stats: createSessionStats(),
    ...overrides,
  };
};

// ============================================
// SPECIALIZED FACTORIES
// ============================================

/**
 * Create a paper trading session (most common test case)
 */
export const createPaperSession = (overrides: Partial<TradingSession> = {}): TradingSession =>
  createTradingSession({
    config: createSessionConfig({ mode: 'Paper', ...overrides.config }),
    ...overrides,
  });

/**
 * Create a live trading session
 */
export const createLiveSession = (overrides: Partial<TradingSession> = {}): TradingSession =>
  createTradingSession({
    config: createSessionConfig({ mode: 'Live', leverage: 1, ...overrides.config }),
    ...overrides,
  });

/**
 * Create a backtest session
 */
export const createBacktestSession = (overrides: Partial<TradingSession> = {}): TradingSession =>
  createTradingSession({
    config: createSessionConfig({ mode: 'Backtest', ...overrides.config }),
    ...overrides,
  });

/**
 * Create a running session (for testing active state)
 */
export const createRunningSession = (overrides: Partial<TradingSession> = {}): TradingSession => {
  const startedAt = faker.date.recent({ days: 1 }).toISOString();

  return createTradingSession({
    status: 'running',
    startedAt,
    ...overrides,
  });
};

/**
 * Create a completed session with stats
 */
export const createCompletedSession = (overrides: Partial<TradingSession> = {}): TradingSession => {
  const startedAt = faker.date.recent({ days: 7 }).toISOString();
  const endedAt = faker.date.recent({ days: 1 }).toISOString();

  return createTradingSession({
    status: 'completed',
    startedAt,
    endedAt,
    stats: createSessionStats({ totalTrades: faker.number.int({ min: 20, max: 200 }) }),
    ...overrides,
  });
};

/**
 * Create a session with specific mode for UI testing
 */
export const createSessionForMode = (mode: TradingMode, strategyIds: string[] = []): TradingSession =>
  createTradingSession({
    config: createSessionConfig({
      mode,
      strategies: strategyIds.length > 0 ? strategyIds : [faker.string.uuid()],
    }),
  });

/**
 * Create session config for UI form testing
 */
export const createMinimalSessionConfig = (): TradingSessionConfig =>
  createSessionConfig({
    strategies: [],
    symbols: [],
    leverage: 1,
    positionSize: 0.1,
    stopLoss: 5,
    takeProfit: 10,
  });
