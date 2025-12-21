---
title: "Technical Research: Backtesting Frameworks Comparison"
date: 2025-12-20
author: Mary (Business Analyst)
project: FX Agent AI
research_type: technical
status: completed
sources_verified: true
---

# Technical Research: Backtesting Frameworks Comparison

**Cel:** Porównanie frameworków do backtestingu dla Python i TypeScript, z fokusem na crypto trading i integrację z Twoim istniejącym stackiem.

---

## Executive Summary

Dla Twojego projektu **FX Agent AI** rekomendacje:

| Podejście | Framework | Uzasadnienie |
|-----------|-----------|--------------|
| **Primary (Python)** | **VectorBT** | Najszybszy, idealny dla pump detection research |
| **Alternative (Python)** | **Freqtrade** | Kompletne rozwiązanie z ML, live trading |
| **TypeScript** | **BacktestJS** | Natywne TypeScript, Binance support |
| **Hybrid** | Custom + CCXT | Pełna kontrola, Twoje istniejące wskaźniki |

**Kluczowy insight:** Możesz zintegrować **VectorBT** do szybkich badań z Twoim istniejącym systemem wskaźników z QuestDB.

---

## Część 1: Porównanie Głównych Frameworków Python

### 1.1 Overview Table

| Framework | Stars | Speed | Live Trading | Crypto | Maintained | Difficulty |
|-----------|-------|-------|--------------|--------|------------|------------|
| **VectorBT** | 4.5k+ | ⚡⚡⚡⚡⚡ | ❌ | ✅ | ✅ (Pro) | Medium |
| **Backtrader** | 14k+ | ⚡⚡ | ✅ | ✅ | ❌ (2018) | Easy |
| **Freqtrade** | 39.9k+ | ⚡⚡⚡ | ✅ | ✅✅ | ✅ | Medium |
| **Jesse** | 6.5k+ | ⚡⚡⚡ | ✅ | ✅✅ | ✅ | Easy |
| **Zipline** | 18k+ | ⚡⚡ | ❌ | ❌ | ❌ | Hard |
| **Backtesting.py** | 5k+ | ⚡⚡⚡ | ❌ | ✅ | ✅ | Very Easy |

### 1.2 VectorBT - Najszybszy

**Opis:** Fully vectorized backtesting engine built on NumPy, Pandas, and Numba.

**Key Stats:**
- **Speed:** ~1000x faster than Backtrader [[1]](https://github.com/polakowo/vectorbt)
- **Performance:** Rolling metrics up to 1000x speedup
- **Parallel:** Built-in multiprocessing support

**Pros:**
- Blazing fast - test thousands of strategies in seconds
- Great for parameter optimization
- Excellent visualization
- NumPy/Pandas native - easy integration with your indicators

**Cons:**
- Opinionated syntax - learning curve
- No native live trading
- Pro version for advanced features (subscription)
- Complex strategies harder to implement

**Code Example:**

```python
import vectorbt as vbt
import pandas as pd

# Load your QuestDB data
price = pd.read_sql(
    "SELECT timestamp, close FROM tick_prices WHERE symbol = 'BTC_USDT'",
    questdb_connection
)

# Your existing TWPA indicator
twpa = your_twpa_calculation(price)

# Generate signals based on pump detection
entries = (
    (price['close'] > twpa * 1.07) &  # 7% pump
    (volume_surge > 3.5)               # Volume surge
)
exits = (
    (price['close'] < twpa * 0.95) |   # 5% drop
    (unrealized_pnl > 0.20)            # 20% profit
)

# Run backtest - BLAZING FAST
pf = vbt.Portfolio.from_signals(
    close=price['close'],
    entries=entries,
    exits=exits,
    fees=0.001,  # 0.1% fee
    freq='1T'    # 1 minute
)

# Results
print(f"Total Return: {pf.total_return():.2%}")
print(f"Sharpe Ratio: {pf.sharpe_ratio():.2f}")
print(f"Max Drawdown: {pf.max_drawdown():.2%}")

# Parameter optimization - test 1000s of combinations
param_grid = {
    'pump_threshold': [5, 7, 10, 15],
    'volume_multiplier': [2.5, 3.0, 3.5, 4.0, 5.0],
    'take_profit': [10, 15, 20, 25, 30]
}

# VectorBT can test ALL combinations in seconds!
```

**Best For:** Research, parameter optimization, testing thousands of variations.

**Installation:** `pip install vectorbt`

---

### 1.3 Freqtrade - Complete Crypto Solution

**Opis:** Full-featured open-source crypto trading bot with ML optimization.

**Key Stats:**
- **GitHub Stars:** 39.9k+ (largest community)
- **Exchanges:** All major via CCXT
- **ML:** FreqAI module for adaptive strategies

**Pros:**
- Complete solution (backtest + live trading)
- Telegram/WebUI management
- Machine learning optimization (FreqAI)
- Hyperparameter optimization built-in
- Huge community and documentation

**Cons:**
- Steeper learning curve
- Opinionated project structure
- May conflict with your existing architecture
- Overkill if you only need backtesting

**Code Example:**

```python
# Freqtrade strategy file
from freqtrade.strategy import IStrategy
from pandas import DataFrame

class PumpDetectionStrategy(IStrategy):
    # Your 5-section logic mapped to Freqtrade

    minimal_roi = {"0": 0.20}  # 20% take profit
    stoploss = -0.05           # 5% stop loss

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # S1: Pump detection indicators
        dataframe['twpa'] = self.calculate_twpa(dataframe)
        dataframe['pump_magnitude'] = (
            (dataframe['close'] - dataframe['twpa']) / dataframe['twpa'] * 100
        )
        dataframe['volume_surge'] = (
            dataframe['volume'] / dataframe['volume'].rolling(window=60).mean()
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # S1 + Z1 conditions
        dataframe.loc[
            (dataframe['pump_magnitude'] >= 7) &
            (dataframe['volume_surge'] >= 3.5) &
            (dataframe['spread_pct'] <= 1.0),  # Z1
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # ZE1 + E1 conditions
        dataframe.loc[
            (dataframe['pump_magnitude'] <= -5),  # E1 emergency
            'exit_long'
        ] = 1
        return dataframe
```

**Best For:** Complete trading bot solution with live trading.

**Installation:**
```bash
pip install freqtrade
freqtrade create-userdir --userdir user_data
```

---

### 1.4 Jesse - Crypto-Native, Simpler

**Opis:** Advanced crypto trading framework focused on simplicity.

**Key Stats:**
- **GitHub Stars:** 6.5k+
- **Focus:** Crypto-only, accurate backtests
- **AI:** JesseGPT for strategy assistance

**Pros:**
- Clean, simple syntax
- Multi-timeframe, multi-symbol without look-ahead bias
- 300+ built-in indicators
- Accurate backtesting (partial fills, slippage)
- Visual charts auto-generated

**Cons:**
- Paid subscription for full features
- Crypto-only (no stocks/forex)
- Smaller community than Freqtrade

**Code Example:**

```python
from jesse.strategies import Strategy
import jesse.indicators as ta

class PumpStrategy(Strategy):

    @property
    def pump_detected(self) -> bool:
        """S1: Signal Detection"""
        return (
            self.pump_magnitude >= 7.0 and
            self.volume_surge >= 3.5 and
            self.price_velocity >= 0.5
        )

    @property
    def entry_valid(self) -> bool:
        """Z1: Entry Conditions"""
        return self.spread_pct <= 1.0

    @property
    def should_long(self) -> bool:
        return self.pump_detected and self.entry_valid

    @property
    def should_cancel_entry(self) -> bool:
        """O1: Signal Cancellation"""
        return self.pump_magnitude <= 3.0

    def go_long(self):
        qty = self.position_size * 0.10  # 10% position
        self.buy = qty, self.price

    def on_open_position(self, order):
        """Set stop loss and take profit"""
        self.stop_loss = self.position.qty, self.position.entry_price * 0.95
        self.take_profit = self.position.qty, self.position.entry_price * 1.20

    def update_position(self):
        """E1: Emergency Exit"""
        if self.pump_magnitude <= -5.0:
            self.liquidate()
```

**Best For:** Clean crypto-focused development with accurate backtests.

**Installation:** `pip install jesse`

---

### 1.5 Backtesting.py - Simplest

**Opis:** Lightweight, intuitive backtesting library.

**Key Stats:**
- **GitHub Stars:** 5k+
- **Lines of Code:** ~700 (very simple)
- **Speed:** Reasonable (vectorized where possible)

**Pros:**
- Extremely simple API
- Interactive plots
- Easy to learn
- Good for quick prototyping

**Cons:**
- No live trading
- Less features than competitors
- Not optimized for HFT

**Code Example:**

```python
from backtesting import Backtest, Strategy

class PumpStrategy(Strategy):
    pump_threshold = 7.0
    volume_multiplier = 3.5

    def init(self):
        self.twpa = self.I(calculate_twpa, self.data.Close)

    def next(self):
        pump_magnitude = (self.data.Close[-1] - self.twpa[-1]) / self.twpa[-1] * 100

        if pump_magnitude >= self.pump_threshold:
            if not self.position:
                self.buy(size=0.10)  # 10% position

        if self.position:
            if self.position.pl_pct >= 0.20:  # 20% profit
                self.position.close()
            elif pump_magnitude <= -5:  # Emergency exit
                self.position.close()

# Run backtest
bt = Backtest(data, PumpStrategy, cash=10000, commission=0.001)
stats = bt.run()
bt.plot()

# Optimization
stats, heatmap = bt.optimize(
    pump_threshold=range(5, 15),
    volume_multiplier=[2.5, 3.0, 3.5, 4.0, 5.0],
    maximize='Sharpe Ratio'
)
```

**Best For:** Quick prototyping, learning, simple strategies.

**Installation:** `pip install backtesting`

---

## Część 2: TypeScript/JavaScript Frameworks

### 2.1 Overview

| Framework | npm Downloads | Crypto Support | TypeScript | Maintained |
|-----------|---------------|----------------|------------|------------|
| **BacktestJS** | ~500/week | ✅ Binance | ✅ Native | ✅ |
| **CCXT** | 100k+/week | ✅✅ 100+ exchanges | ✅ | ✅ |
| **Grandmaster** | ~50/week | ✅ | ❌ JS only | ⚠️ |

### 2.2 BacktestJS - Native TypeScript

**Opis:** TypeScript-first backtesting framework.

**Pros:**
- Native TypeScript
- Binance data download built-in
- SQLite storage (no external DB needed)
- CLI and UI results

**Cons:**
- Smaller community
- Limited exchange support
- No live trading

**Code Example:**

```typescript
import { Backtest, DataSource, Strategy } from '@backtest/framework';

interface PumpContext {
  twpa: number;
  pumpMagnitude: number;
  volumeSurge: number;
}

const pumpStrategy: Strategy<PumpContext> = {
  name: 'PumpDetection',

  init: (ctx) => ({
    twpa: 0,
    pumpMagnitude: 0,
    volumeSurge: 0,
  }),

  next: (data, ctx, position) => {
    // Calculate indicators
    ctx.twpa = calculateTWPA(data, 300);
    ctx.pumpMagnitude = ((data.close - ctx.twpa) / ctx.twpa) * 100;
    ctx.volumeSurge = data.volume / averageVolume(data, 60);

    // S1: Signal Detection
    if (ctx.pumpMagnitude >= 7 && ctx.volumeSurge >= 3.5) {
      if (!position) {
        return { action: 'buy', size: 0.10 };
      }
    }

    // E1: Emergency Exit
    if (position && ctx.pumpMagnitude <= -5) {
      return { action: 'sell', size: position.size };
    }

    // ZE1: Take Profit
    if (position && position.unrealizedPnlPct >= 20) {
      return { action: 'sell', size: position.size };
    }

    return { action: 'hold' };
  }
};

// Run backtest
const backtest = new Backtest({
  strategy: pumpStrategy,
  data: await DataSource.binance('BTCUSDT', '1m', '2024-01-01', '2024-12-01'),
  initialCapital: 10000,
  commission: 0.001,
});

const results = await backtest.run();
console.log(results.summary());
```

**Installation:** `npm install @backtest/framework`

### 2.3 Custom Solution with CCXT

**Dla Twojego projektu** - integracja z istniejącym kodem:

```typescript
// frontend/src/lib/backtest/engine.ts
import ccxt from 'ccxt';

interface BacktestConfig {
  symbol: string;
  startDate: Date;
  endDate: Date;
  initialCapital: number;
  strategy: StrategyConfig;  // Your 5-section config
}

interface BacktestResult {
  trades: Trade[];
  metrics: {
    totalReturn: number;
    sharpeRatio: number;
    maxDrawdown: number;
    winRate: number;
  };
}

export class BacktestEngine {
  private exchange: ccxt.Exchange;
  private indicators: IndicatorEngine;  // Your existing indicators

  constructor() {
    this.exchange = new ccxt.binance({ enableRateLimit: true });
  }

  async run(config: BacktestConfig): Promise<BacktestResult> {
    // Fetch historical data
    const ohlcv = await this.exchange.fetchOHLCV(
      config.symbol,
      '1m',
      config.startDate.getTime(),
      undefined
    );

    // Run your 5-section state machine
    const trades: Trade[] = [];
    let state: TradingState = 'MONITORING';
    let position: Position | null = null;

    for (const candle of ohlcv) {
      const [timestamp, open, high, low, close, volume] = candle;

      // Calculate indicators (reuse your existing code!)
      const indicators = await this.calculateIndicators({
        timestamp, open, high, low, close, volume
      });

      // Evaluate 5-section conditions
      const evaluation = this.evaluateStrategy(config.strategy, indicators, state);

      // Execute state transitions
      if (evaluation.transition) {
        state = evaluation.newState;

        if (evaluation.action === 'OPEN_POSITION') {
          position = this.openPosition(close, config.initialCapital * 0.10);
        } else if (evaluation.action === 'CLOSE_POSITION' && position) {
          trades.push(this.closePosition(position, close, timestamp));
          position = null;
        }
      }
    }

    return {
      trades,
      metrics: this.calculateMetrics(trades, config.initialCapital)
    };
  }
}
```

---

## Część 3: Event-Driven vs Vectorized

### 3.1 Comparison

| Aspekt | Event-Driven | Vectorized |
|--------|--------------|------------|
| **Speed** | Slower (bar-by-bar) | Much faster (array ops) |
| **Accuracy** | More realistic | May miss nuances |
| **Complexity** | Handles complex logic | Simpler strategies |
| **Examples** | Backtrader, Freqtrade, Jesse | VectorBT, Backtesting.py |
| **Your Use Case** | Live trading simulation | Parameter optimization |

### 3.2 Recommendation for FX Agent AI

**Hybrid Approach:**

1. **VectorBT dla research:** Szybkie testowanie parametrów (thresholds, timeframes)
2. **Custom engine dla validation:** Event-driven z Twoją 5-section logiką
3. **Paper trading dla final test:** Freqtrade lub Jesse z live data

```
Research Pipeline:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  VectorBT   │ →  │   Custom    │ →  │  Freqtrade  │
│  (fast)     │    │  (accurate) │    │  (live)     │
│             │    │             │    │             │
│ 1000s tests │    │ 10 best     │    │ Paper trade │
│ per minute  │    │ candidates  │    │ validation  │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## Część 4: Integracja z Twoim Systemem

### 4.1 Wykorzystanie Istniejących Komponentów

Twój system już ma:
- ✅ QuestDB z historycznymi danymi (tick_prices, aggregated_ohlcv)
- ✅ 20+ wskaźników (TWPA, velocity, volume_surge, etc.)
- ✅ 5-section strategy schema
- ✅ State machine logic

**Strategia integracji:**

```python
# backend/src/backtest/vectorbt_adapter.py

import vectorbt as vbt
import pandas as pd
from src.infrastructure.questdb import QuestDBClient
from src.domain.services.indicators import IndicatorEngine

class VectorBTAdapter:
    """
    Bridge between your existing indicator system and VectorBT
    """

    def __init__(self, questdb: QuestDBClient, indicators: IndicatorEngine):
        self.db = questdb
        self.indicators = indicators

    def load_data(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Load OHLCV from QuestDB"""
        query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM aggregated_ohlcv
            WHERE symbol = '{symbol}'
              AND interval = '1m'
              AND timestamp BETWEEN '{start}' AND '{end}'
            ORDER BY timestamp
        """
        return pd.read_sql(query, self.db.connection, index_col='timestamp')

    def calculate_indicators(self, data: pd.DataFrame) -> dict:
        """
        Reuse your existing indicator calculations!
        """
        return {
            'twpa': self.indicators.twpa(data, t1=300, t2=0),
            'pump_magnitude': self.indicators.pump_magnitude_pct(data),
            'volume_surge': self.indicators.volume_surge_ratio(data, t1=60, baseline=3600),
            'price_velocity': self.indicators.price_velocity(data),
            # ... all your indicators
        }

    def run_backtest(
        self,
        symbol: str,
        start: str,
        end: str,
        strategy_config: dict
    ) -> vbt.Portfolio:
        """Run VectorBT backtest with your strategy config"""

        # Load data
        data = self.load_data(symbol, start, end)

        # Calculate indicators
        indicators = self.calculate_indicators(data)

        # Generate signals based on 5-section config
        entries = self._evaluate_s1_z1(indicators, strategy_config)
        exits = self._evaluate_ze1_e1(indicators, strategy_config)

        # Run VectorBT
        pf = vbt.Portfolio.from_signals(
            close=data['close'],
            entries=entries,
            exits=exits,
            fees=strategy_config.get('fees', 0.001),
            sl_stop=strategy_config['e1']['stop_loss_pct'] / 100,
            tp_stop=strategy_config['ze1']['take_profit_pct'] / 100,
        )

        return pf

    def optimize(
        self,
        symbol: str,
        start: str,
        end: str,
        param_grid: dict
    ) -> pd.DataFrame:
        """
        Optimize strategy parameters using VectorBT's speed
        """
        data = self.load_data(symbol, start, end)

        # Generate all parameter combinations
        results = []
        for params in self._generate_combinations(param_grid):
            indicators = self.calculate_indicators(data)
            entries = self._evaluate_with_params(indicators, params)
            exits = self._evaluate_exits_with_params(indicators, params)

            pf = vbt.Portfolio.from_signals(
                close=data['close'],
                entries=entries,
                exits=exits,
                fees=0.001
            )

            results.append({
                **params,
                'total_return': pf.total_return(),
                'sharpe_ratio': pf.sharpe_ratio(),
                'max_drawdown': pf.max_drawdown(),
                'win_rate': pf.trades.win_rate
            })

        return pd.DataFrame(results).sort_values('sharpe_ratio', ascending=False)
```

### 4.2 Frontend Integration

```typescript
// frontend/src/hooks/useBacktest.ts

import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface BacktestParams {
  symbol: string;
  startDate: string;
  endDate: string;
  strategyId: string;
}

interface BacktestResult {
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  trades: Trade[];
  equityCurve: { timestamp: string; value: number }[];
}

export function useBacktest() {
  return useMutation({
    mutationFn: async (params: BacktestParams): Promise<BacktestResult> => {
      const response = await api.post('/api/backtest/run', params);
      return response.data;
    },
  });
}

export function useBacktestOptimization() {
  return useMutation({
    mutationFn: async (params: OptimizationParams) => {
      const response = await api.post('/api/backtest/optimize', params);
      return response.data;
    },
  });
}
```

---

## Część 5: Rekomendacje

### 5.1 Dla FX Agent AI - Action Plan

| Faza | Framework | Cel |
|------|-----------|-----|
| **Phase 1** | VectorBT | Szybka walidacja pump detection thresholds |
| **Phase 2** | Custom adapter | Integracja z Twoimi wskaźnikami z QuestDB |
| **Phase 3** | Freqtrade/Jesse | Paper trading validation |

### 5.2 Wybór Frameworka

**Jeśli chcesz...**

| Cel | Framework | Powód |
|-----|-----------|-------|
| Najszybszy research | **VectorBT** | 1000x szybszy |
| Kompletne rozwiązanie | **Freqtrade** | Backtest + live + ML |
| Prostota | **Backtesting.py** | 700 linii kodu |
| Crypto-focused | **Jesse** | Accurate, partial fills |
| TypeScript | **BacktestJS** | Native TS |
| Pełna kontrola | **Custom + CCXT** | Twoje wskaźniki |

### 5.3 Moja Rekomendacja

Dla Twojego projektu:

```
┌────────────────────────────────────────────────────────┐
│                    RECOMMENDED STACK                    │
├────────────────────────────────────────────────────────┤
│                                                         │
│  RESEARCH:        VectorBT + your QuestDB indicators   │
│                   → Fast parameter optimization         │
│                                                         │
│  VALIDATION:      Custom Python adapter                 │
│                   → Accurate 5-section simulation       │
│                                                         │
│  PRODUCTION:      Your existing system                  │
│                   → Already built, working              │
│                                                         │
│  FRONTEND:        BacktestJS or Custom TypeScript       │
│                   → UI for backtest results             │
│                                                         │
└────────────────────────────────────────────────────────┘
```

---

## Sources

1. [VectorBT - GitHub](https://github.com/polakowo/vectorbt)
2. [VectorBT Getting Started](https://vectorbt.dev/)
3. [Freqtrade - GitHub](https://github.com/freqtrade/freqtrade)
4. [Jesse Trading Framework](https://jesse.trade/)
5. [Backtesting.py - GitHub](https://github.com/kernc/backtesting.py)
6. [BacktestJS Framework](https://backtestjs.com/)
7. [CCXT - GitHub](https://github.com/ccxt/ccxt)
8. [Battle-Tested Backtesters Comparison](https://medium.com/@trading.dude/battle-tested-backtesters-comparing-vectorbt-zipline-and-backtrader-for-financial-strategy-dee33d33a9e0)
9. [Freqtrade vs Jesse Comparison](https://theforexgeek.com/freqtrade-vs-jesse-trade/)
10. [VectorBT Alpaca Tutorial](https://alpaca.markets/learn/introduction-to-backtesting-with-vectorbt)
11. [Backtrader vs VectorBT vs Zipline](https://autotradelab.com/blog/backtrader-vs-nautilusttrader-vs-vectorbt-vs-zipline-reloaded)
12. [Crypto Bot Backtesting Tools 2025 - TokenMetrics](https://www.tokenmetrics.com/blog/crypto-bot-backtesting-tools-platforms-apis-scripts-2025)

---

*Research conducted: 2025-12-20*
*Facilitator: Mary (Business Analyst)*
*Project: FX Agent AI*
