# PEŁNY OPIS INTERFEJSU UI - FXcrypto

**Wersja:** 1.0 | **Data:** 2025-12-05

---

## CEL SYSTEMU

FXcrypto to **system do automatycznego wykrywania pump/dump na kryptowalutach**. Trader używa tego interfejsu, żeby:

1. **Zdefiniować strategię** - warunki wejścia/wyjścia oparte na wskaźnikach (RSI, MACD, Volume Surge)
2. **Przetestować strategię na historii** (backtest) - sprawdzić czy strategia zarabia na danych z przeszłości
3. **Uruchomić symulację** (paper trading) - obserwować sygnały w czasie rzeczywistym bez ryzykowania pieniędzy
4. **Handlować na żywo** (live trading) - prawdziwe transakcje na giełdzie MEXC

---

## ARCHITEKTURA STRON

```
┌─────────────────────────────────────────────────────────────────┐
│                        STRONY INTERFEJSU                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PRZYGOTOWANIE                  WYKONANIE            ANALIZA    │
│  ─────────────                  ─────────            ───────    │
│                                                                 │
│  /strategy-builder    ───►    /trading-session    ───►  /dashboard
│  (tworzenie strategii)        (start sesji)           (monitoring)
│                                                                 │
│  /data-collection     ───►    /dashboard?mode=backtest          │
│  (zbieranie danych)           (backtest viewing)                │
│                                                                 │
│  /indicators                  /market-scanner                   │
│  (warianty wskaźników)        (skanowanie rynku)                │
│                                                                 │
│  /settings                    /strategies                       │
│  (konfiguracja)               (lista strategii)                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## STRONA 1: GŁÓWNY DASHBOARD (`/`)

### Cel
Punkt wejścia do aplikacji. Pokazuje przegląd rynku i szybkie akcje.

### Układ

```
┌─────────────────────────────────────────────────────────────────┐
│ 🚀 Pump & Dump Trading Dashboard              [Refresh] [🔔 3]  │
├─────────────────────────────────────────────────────────────────┤
│ System Status: 🟢 Backend Connected | 🟢 WebSocket | 🟢 MEXC   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ QUICK ACTIONS                                                   │
│ ┌─────────┬─────────┬─────────┬─────────┬─────────┐            │
│ │  Pump   │  Live   │  Paper  │ Backtest│  Risk   │            │
│ │ Scanner │ Trading │ Trading │         │  Mgmt   │            │
│ └─────────┴─────────┴─────────┴─────────┴─────────┘            │
│                                                                 │
├───────────────────────────────────┬─────────────────────────────┤
│ MARKET SCANNER                    │ ACTIVE SIGNALS              │
│ ┌───────┬───────┬───────┬──────┐ │ ┌─────────────────────────┐ │
│ │Symbol │ Price │ 24h % │ Mag. │ │ │ 🔴 BTC_USDT PUMP +15%   │ │
│ ├───────┼───────┼───────┼──────┤ │ │    Magnitude: 15.2%     │ │
│ │BTC/USD│$65,234│ +5.2% │ 5.2% │ │ │    Confidence: 85%      │ │
│ │ETH/USD│ $3,456│ +2.1% │ 2.1% │ │ │    [Trade]              │ │
│ │SOL/USD│  $142 │+12.3% │12.3% │ │ └─────────────────────────┘ │
│ └───────┴───────┴───────┴──────┘ │                             │
│                                   │ RISK & PERFORMANCE          │
│ Actions: [Trade] [Monitor]        │ Portfolio: $1,234.56        │
│                                   │ Today P&L: +$45.23          │
│                                   │ Win Rate: 68%               │
│                                   │ [Emergency Stop] [Close All]│
└───────────────────────────────────┴─────────────────────────────┘
```

### Funkcje
| Element | Funkcja | Interakcja |
|---------|---------|------------|
| Quick Actions | Szybkie przejście do funkcji | Kliknięcie → redirect |
| Market Scanner | Tabela symboli z danymi | Kliknięcie wiersza → Trade/Monitor |
| Active Signals | Lista wykrytych sygnałów | [Trade] → start sesji |
| Risk Panel | Podsumowanie portfolio | [Emergency Stop] → zatrzymaj wszystko |

---

## STRONA 2: TRADING SESSION (`/trading-session`)

### Cel
**CENTRUM STARTOWE** - tu trader konfiguruje i uruchamia sesję tradingową.

### Układ

```
┌─────────────────────────────────────────────────────────────────┐
│ Configure Trading Session                                       │
│ Complete configuration for Live, Paper, and Backtesting         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─────────────────────────────────────┐ ┌─────────────────────┐ │
│ │ 1. SELECT TRADING MODE              │ │ SESSION SUMMARY     │ │
│ │ ┌─────────┬─────────┬─────────────┐ │ │                     │ │
│ │ │  LIVE   │  PAPER  │  BACKTEST   │ │ │ Mode: PAPER         │ │
│ │ │⚠️ Real  │✅ Simul │⏮️ History  │ │ │ Strategies: 2       │ │
│ │ └─────────┴─────────┴─────────────┘ │ │ Symbols: 3          │ │
│ │                                     │ │ Budget: $1000       │ │
│ │ ⚠️ Paper trading simulates real    │ │ SL/TP: 5%/10%       │ │
│ │    trading with virtual funds      │ │                     │ │
│ └─────────────────────────────────────┘ │ ┌─────────────────┐ │ │
│                                         │ │ ⚠️ Select 1+    │ │ │
│ ┌─────────────────────────────────────┐ │ │    strategy     │ │ │
│ │ 2. SELECT STRATEGIES                │ │ └─────────────────┘ │ │
│ │ ┌──┬────────────────┬────────────┐  │ │                     │ │
│ │ │☑️│ pump_detector_v1│ [Enabled] │  │ │ ┌─────────────────┐ │ │
│ │ │☐ │ volume_surge    │ [Enabled] │  │ │ │ START PAPER     │ │ │
│ │ │☐ │ trend_follower  │ [Disabled]│  │ │ │ SESSION         │ │ │
│ │ └──┴────────────────┴────────────┘  │ │ └─────────────────┘ │ │
│ │ [Refresh]                           │ │                     │ │
│ └─────────────────────────────────────┘ │ [Go to Dashboard]   │ │
│                                         │                     │ │
│ ┌─────────────────────────────────────┐ └─────────────────────┘ │
│ │ 3. SELECT SYMBOLS                   │                         │
│ │ [BTC_USDT✓] [ETH_USDT] [ADA_USDT✓] │                         │
│ │ [SOL_USDT✓] [DOT_USDT]             │                         │
│ │ [Top 3] [Clear All]                 │                         │
│ └─────────────────────────────────────┘                         │
│                                                                 │
│ ┌─────────────────────────────────────┐                         │
│ │ 4. BUDGET & RISK MANAGEMENT         │                         │
│ │ Global Budget: [$1000 USDT    ]     │                         │
│ │ Max Position:  [$100 USDT     ]     │                         │
│ │ Stop Loss:     [5  %          ]     │                         │
│ │ Take Profit:   [10 %          ]     │                         │
│ └─────────────────────────────────────┘                         │
│                                                                 │
│ ┌─────────────────────────────────────┐  (tylko dla BACKTEST)   │
│ │ HISTORICAL DATA SESSION             │                         │
│ │ ┌─────────────────────────────────┐ │                         │
│ │ │ 2024-12-05 BTC,ETH (12,450 rec)▼│ │                         │
│ │ └─────────────────────────────────┘ │                         │
│ │ Acceleration: [═══○═══════] 10x     │                         │
│ └─────────────────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

### Funkcje
| Element | Funkcja | Interakcja |
|---------|---------|------------|
| Mode Toggle | Wybór Live/Paper/Backtest | Kliknięcie przycisku |
| Strategy Table | Wybór strategii | Checkbox zaznaczenie |
| Symbol Chips | Wybór symboli | Kliknięcie chip |
| Budget Fields | Konfiguracja ryzyka | Input text |
| Data Session | Wybór danych do backtestu | Dropdown |
| Acceleration | Szybkość backtestu | Slider 1x-100x |
| START Button | Uruchomienie sesji | Kliknięcie → redirect do /dashboard |

---

## STRONA 3: UNIFIED DASHBOARD (`/dashboard`)

### Cel
**CENTRUM MONITORINGU** - obserwacja działającej sesji.

### Układ (sesja aktywna)

```
┌─────────────────────────────────────────────────────────────────┐
│ 📝 Paper Trading Dashboard                                      │
│ [Paper▼|Live|Backtest]     [Single|Grid]  [Refresh] [⏹️ STOP]   │
├─────────────────────────────────────────────────────────────────┤
│ ℹ️ Active Session: paper_abc123 | Mode: PAPER | Status: Running │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ SUMMARY CARDS                                                   │
│ ┌───────────────┬───────────────┬───────────────┬─────────────┐ │
│ │ Global P&L    │ Positions     │ Total Signals │ Budget Use  │ │
│ │ +$45.23       │ 2             │ 15            │ 23%         │ │
│ │ 🟢            │               │               │             │ │
│ └───────────────┴───────────────┴───────────────┴─────────────┘ │
│                                                                 │
├────────────────────────────────┬────────────────────────────────┤
│ EQUITY CURVE                   │ DRAWDOWN ANALYSIS              │
│ ┌────────────────────────────┐ │ ┌────────────────────────────┐ │
│ │      ╱╲    ▲BUY            │ │ │ ─────────────────          │ │
│ │    ╱╲ ╲  ╱  ▼SELL          │ │ │         ╲                  │ │
│ │  ╱    ╲╱                   │ │ │          ╲────╱            │ │
│ │ ╱                          │ │ │ Max DD: -3.2%              │ │
│ └────────────────────────────┘ │ └────────────────────────────┘ │
├────────────────────────────────┴────────────────────────────────┤
│                                                                 │
│ ┌────────────┐ ┌────────────────────────────────────────────┐   │
│ │ WATCHLIST  │ │ BTC_USDT CHART                             │   │
│ │            │ │ ┌────────────────────────────────────────┐ │   │
│ │ BTC_USDT ◀ │ │ │     ■                                  │ │   │
│ │ $65,234    │ │ │   ■ ■■     (candlestick chart)         │ │   │
│ │ +5.2%      │ │ │  ■■ ■ ■■                               │ │   │
│ │            │ │ │ ■■     ■                               │ │   │
│ │ ETH_USDT   │ │ └────────────────────────────────────────┘ │   │
│ │ $3,456     │ │                                            │   │
│ │ +2.1%      │ │ LIVE INDICATORS                            │   │
│ │            │ │ ┌────────────────────────────────────────┐ │   │
│ │ SOL_USDT   │ │ │ RSI(14): 68.5  MACD: 0.0023           │ │   │
│ │ $142       │ │ │ Volume_Surge: 2.3x  TWAP: 65,100      │ │   │
│ │ +12.3%     │ │ └────────────────────────────────────────┘ │   │
│ └────────────┘ └────────────────────────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [📊 Signal History] [💰 Transaction History]                    │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────┬──────────┬────────┬──────────┬────────┬──────────┐  │
│ │ Time    │ Symbol   │ Type   │ Conf.    │ Status │ Action   │  │
│ ├─────────┼──────────┼────────┼──────────┼────────┼──────────┤  │
│ │ 12:34:56│ BTC_USDT │ S1_LONG│ 85%      │EXECUTED│ [Details]│  │
│ │ 12:33:12│ ETH_USDT │ Z1_LONG│ 72%      │ PENDING│ [Details]│  │
│ │ 12:30:45│ BTC_USDT │ ZE1    │ 90%      │ FILLED │ [Details]│  │
│ └─────────┴──────────┴────────┴──────────┴────────┴──────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Funkcje
| Element | Funkcja | Interakcja |
|---------|---------|------------|
| Mode Switcher | Zmiana trybu (gdy brak sesji) | Toggle buttons |
| View Toggle | Single/Grid view | Toggle buttons |
| STOP Button | Zatrzymanie sesji | Kliknięcie → potwierdź |
| Summary Cards | Kluczowe metryki | Tylko wyświetlanie |
| Equity Curve | Wykres kapitału | Hover → szczegóły |
| Watchlist | Lista symboli | Kliknięcie → zmiana wykresu |
| Chart | Wykres świecowy | (obecnie brak interakcji) |
| Live Indicators | Wartości wskaźników | Auto-refresh |
| Signal History | Tabela sygnałów | [Details] → panel szczegółów |
| Transaction History | Tabela transakcji | [Details] → szczegóły |

---

## STRONA 4: STRATEGY BUILDER (`/strategy-builder`)

### Cel
**KREATOR STRATEGII** - definiowanie warunków wejścia/wyjścia.

### Układ

```
┌─────────────────────────────────────────────────────────────────┐
│ Strategy Builder                                                │
│ [Strategies List] [Create Strategy]                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ TAB 1: STRATEGIES LIST                                          │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Name              │ Description      │ Created  │ Actions  │  │
│ ├───────────────────┼──────────────────┼──────────┼──────────┤  │
│ │ pump_detector_v1  │ Fast pump detect │ 12-05    │ ✏️ 🗑️    │  │
│ │ volume_surge      │ Volume based     │ 12-04    │ ✏️ 🗑️    │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                           [+ Create New Strategy]│
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ TAB 2: STRATEGY EDITOR (5-Section Builder)                      │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Strategy Name: [pump_detector_v2                         ] │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ S1: SIGNAL DETECTION (wykrycie potencjalnego pumpu)        │  │
│ │ ┌────────────────────────────────────────────────────────┐ │  │
│ │ │ Condition 1: [RSI▼] [>▼] [70    ]           [🗑️]      │ │  │
│ │ │ Condition 2: [Volume_Surge▼] [>▼] [2.0  ]   [🗑️]      │ │  │
│ │ │ Condition 3: [Price_Change▼] [>▼] [5%   ]   [🗑️]      │ │  │
│ │ │                                                        │ │  │
│ │ │ [+ Add Condition]                                      │ │  │
│ │ └────────────────────────────────────────────────────────┘ │  │
│ │ Logic: [AND▼] all conditions must be true                  │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Z1: ENTRY CONFIRMATION (otwarcie pozycji)                  │  │
│ │ Position Size: [Percentage▼] [1  %]                        │  │
│ │ Direction: [LONG▼]                                         │  │
│ │ Entry Conditions:                                          │  │
│ │ ┌────────────────────────────────────────────────────────┐ │  │
│ │ │ [Price▼] [crosses above▼] [TWAP_300▼]        [🗑️]     │ │  │
│ │ │ [+ Add Condition]                                      │ │  │
│ │ └────────────────────────────────────────────────────────┘ │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ O1: ORDER CANCEL (timeout/anulowanie)                      │  │
│ │ Timeout: [300   ] seconds                                  │  │
│ │ Cooldown: [5    ] minutes                                  │  │
│ │ Cancel Conditions:                                         │  │
│ │ ┌────────────────────────────────────────────────────────┐ │  │
│ │ │ [RSI▼] [<▼] [50    ] (signal weakness)        [🗑️]    │ │  │
│ │ │ [+ Add Condition]                                      │ │  │
│ │ └────────────────────────────────────────────────────────┘ │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ ZE1: EXIT STRATEGY (zamknięcie pozycji)                    │  │
│ │ ┌────────────────────────────────────────────────────────┐ │  │
│ │ │ Take Profit: [5    %]                                  │ │  │
│ │ │ Stop Loss:   [2    %]                                  │ │  │
│ │ │ Trailing Stop: [☐] [1    %]                            │ │  │
│ │ └────────────────────────────────────────────────────────┘ │  │
│ │ Exit Conditions:                                           │  │
│ │ ┌────────────────────────────────────────────────────────┐ │  │
│ │ │ [RSI▼] [<▼] [30    ] (momentum loss)          [🗑️]    │ │  │
│ │ │ [Volume▼] [<▼] [avg_volume * 0.5]             [🗑️]    │ │  │
│ │ │ [+ Add Condition]                                      │ │  │
│ │ └────────────────────────────────────────────────────────┘ │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ EMERGENCY EXIT (awaryjne wyjście)                          │  │
│ │ ☑️ Cancel all pending orders                               │  │
│ │ ☑️ Close position immediately                              │  │
│ │ ☑️ Log event                                               │  │
│ │ Cooldown after emergency: [60   ] minutes                  │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │                    [Validate]  [Save Strategy]             │  │
│ └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Funkcje
| Element | Funkcja | Interakcja |
|---------|---------|------------|
| Strategy List | Przeglądanie strategii | ✏️ Edit, 🗑️ Delete |
| Strategy Name | Nazwa strategii | Text input |
| S1 Conditions | Warunki wykrycia sygnału | Dropdown + input |
| Add Condition | Dodanie warunku | Kliknięcie |
| Remove Condition | Usunięcie warunku | 🗑️ kliknięcie |
| Logic Selector | AND/OR dla warunków | Dropdown |
| Z1 Entry | Konfiguracja wejścia | Dropdowns + inputs |
| ZE1 Exit | Take Profit / Stop Loss | Inputs + checkboxy |
| Validate | Sprawdzenie poprawności | Kliknięcie → walidacja |
| Save | Zapisanie strategii | Kliknięcie → API call |

---

## STRONA 5: DATA COLLECTION (`/data-collection`)

### Cel
Zbieranie danych historycznych do backtestów.

### Układ

```
┌─────────────────────────────────────────────────────────────────┐
│ Data Collection                              [Refresh] [+ Start] │
│ WebSocket: 🟢 Connected                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ STATISTICS                                                      │
│ ┌───────────────┬───────────────┬───────────────┬─────────────┐ │
│ │ Active        │ Completed     │ Total Records │ Storage     │ │
│ │ 1             │ 5             │ 156,000       │ ~15.6 MB    │ │
│ └───────────────┴───────────────┴───────────────┴─────────────┘ │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ DATA COLLECTION SESSIONS                                        │
│ ┌─────────┬────────┬───────────┬────────┬─────────┬───────────┐ │
│ │ Session │ Status │ Symbols   │ Dur.   │ Records │ Actions   │ │
│ ├─────────┼────────┼───────────┼────────┼─────────┼───────────┤ │
│ │ abc123  │🟢 run  │ BTC,ETH   │ 1h     │ 12,450  │ ⏹️        │ │
│ │         │        │           │        │ ████░ 65%           │ │
│ │         │        │           │        │ ETA: 21m            │ │
│ ├─────────┼────────┼───────────┼────────┼─────────┼───────────┤ │
│ │ xyz789  │ ✓ done │ BTC       │ 24h    │ 86,400  │ 📊 ⬇️ 🗑️  │ │
│ │ def456  │ ✓ done │ BTC,ETH,SOL│ 2h    │ 45,600  │ 📊 ⬇️ 🗑️  │ │
│ │ ghi012  │ ❌ err │ ADA       │ 1h     │ 5,230   │ 🗑️        │ │
│ └─────────┴────────┴───────────┴────────┴─────────┴───────────┘ │
│                                                                 │
│ Actions: ⏹️ Stop | 📊 View Chart | ⬇️ Download | 🗑️ Delete     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ COLLECTION DETAILS (expanded for xyz789)                        │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Session ID: xyz789                                          │ │
│ │ Status: Completed                                           │ │
│ │ Records: 86,400                                             │ │
│ │ Storage: data/historical/xyz789                             │ │
│ │ Start: 2024-12-04 10:00:00                                  │ │
│ │ End: 2024-12-05 10:00:00                                    │ │
│ │ Data Types: price, orderbook, trades                        │ │
│ │ Symbols: [BTC_USDT]                                         │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Dialog: Start Collection

```
┌─────────────────────────────────────────────────────────────────┐
│ Start Data Collection                                     [X]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Symbols:                                                        │
│ [BTC_USDT✓] [ETH_USDT✓] [ADA_USDT] [SOL_USDT✓] [DOT_USDT]      │
│                                                                 │
│ Duration:                                                       │
│ [1        ] [hours  ▼]                                          │
│ (Enter 0 for continuous collection)                             │
│                                                                 │
│ Storage Path:                                                   │
│ [data/historical                                            ]   │
│                                                                 │
│ ℹ️ Data Collection: Continuously gather market data for         │
│    analysis. Data stored as CSV organized by symbol and date.  │
│                                                                 │
│                                    [Cancel] [Start Collection]  │
└─────────────────────────────────────────────────────────────────┘
```

### Funkcje
| Element | Funkcja | Interakcja |
|---------|---------|------------|
| Start Button | Otwiera dialog | Kliknięcie |
| Sessions Table | Lista sesji | Kliknięcie wiersza → expand |
| Progress Bar | Postęp zbierania | Auto-update przez WebSocket |
| Stop | Zatrzymanie zbierania | Kliknięcie |
| View Chart | Podgląd danych | Redirect do /data-collection/[id]/chart |
| Download | Pobranie danych | (nie zaimplementowane) |
| Delete | Usunięcie sesji | Kliknięcie → potwierdź |

---

## STRONA 6: INDICATORS (`/indicators`)

### Cel
Zarządzanie wariantami wskaźników technicznych.

### Układ

```
┌─────────────────────────────────────────────────────────────────┐
│ Indicator Variants                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ AVAILABLE VARIANTS                          [+ Create New] │  │
│ ├────────────────────────────────────────────────────────────┤  │
│ │ Name          │ Base Type │ Parameters          │ Actions  │  │
│ ├───────────────┼───────────┼─────────────────────┼──────────┤  │
│ │ RSI_14        │ RSI       │ period=14           │ ✏️ 🗑️    │  │
│ │ RSI_21        │ RSI       │ period=21           │ ✏️ 🗑️    │  │
│ │ MACD_12_26_9  │ MACD      │ fast=12,slow=26,sig=9│ ✏️ 🗑️   │  │
│ │ Volume_Surge  │ VOLUME    │ lookback=20         │ ✏️ 🗑️    │  │
│ │ TWAP_300      │ TWAP      │ window=300          │ ✏️ 🗑️    │  │
│ └───────────────┴───────────┴─────────────────────┴──────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Funkcje
| Element | Funkcja | Interakcja |
|---------|---------|------------|
| Create New | Tworzenie wariantu | Dialog z parametrami |
| Edit | Edycja parametrów | ✏️ kliknięcie |
| Delete | Usunięcie wariantu | 🗑️ kliknięcie |

---

## STRONA 7: MARKET SCANNER (`/market-scanner`)

### Cel
Real-time skanowanie rynku w poszukiwaniu pump/dump.

### Układ

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔍 Real-Time Market Scanner           [🔔 3] [Refresh] [Auto ✓] │
├─────────────────────────────────────────────────────────────────┤
│ 🚨 3 New Signals Detected! BTC_USDT (15.2%), SOL_USDT (12.3%)  │
├────────────────────┬────────────────────────────────────────────┤
│ SCANNER SETTINGS   │ SCANNER RESULTS (5 matches)               │
│ ┌────────────────┐ │ ┌──────────────────────────────────────┐   │
│ │ Min Pump Mag:  │ │ │Symbol│Price │24h% │Mag. │Surge│Signal│   │
│ │ [═══○═══] 5%   │ │ ├──────┼──────┼─────┼─────┼─────┼──────┤   │
│ │                │ │ │BTC/USD│$65234│+5.2%│5.2% │2.3x │MEDIUM│   │
│ │ Min Vol Surge: │ │ │SOL/USD│ $142│+12% │12.3%│4.5x │STRONG│   │
│ │ [═══○═══] 2x   │ │ │ETH/USD│$3456│+2.1%│2.1% │1.5x │ WEAK │   │
│ │                │ │ └──────┴──────┴─────┴─────┴─────┴──────┘   │
│ │ Min Confidence:│ │                                            │
│ │ [═════○═] 50%  │ │ Actions per row:                           │
│ │                │ │ [▶️ Quick Trade] [📊 Monitor] [🔔 Alert]   │
│ │ Max Volatility:│ │                                            │
│ │ [═══════○] 20% │ │                                            │
│ │                │ │                                            │
│ │ ☑️ Enable Alerts│ │                                           │
│ │                │ │                                            │
│ │ Refresh: [30s▼]│ │                                            │
│ └────────────────┘ │                                            │
├────────────────────┴────────────────────────────────────────────┤
│ ADVANCED FILTERS                                            [▼] │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Monitored Symbols:                                          │ │
│ │ [BTC_USDT✓] [ETH_USDT✓] [SOL_USDT✓] [ADA_USDT] ...         │ │
│ │ [Save Preset] [Load Preset]                                 │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Funkcje
| Element | Funkcja | Interakcja |
|---------|---------|------------|
| Sliders | Filtrowanie wyników | Przesunięcie |
| Auto Refresh | Automatyczne odświeżanie | Toggle |
| Results Table | Wyniki skanowania | Sortowanie po kolumnach |
| Quick Trade | Szybki start tradingu | Kliknięcie |
| Monitor | Dodanie do obserwacji | Kliknięcie |
| Alert | Ustawienie alertu | Kliknięcie |

---

## STRONA 8: SETTINGS (`/settings`)

### Cel
Konfiguracja aplikacji.

### Tabs

**Tab 1: API Configuration**
- Backend URL
- Request timeout
- Retry attempts
- Connection test

**Tab 2: Trading Settings**
- Default symbols
- Max concurrent positions
- Default budget
- Risk management toggle

**Tab 3: Notifications**
- Email notifications (on/off, address)
- Telegram notifications (on/off, bot token)
- Alert on trades
- Alert on errors

**Tab 4: Display**
- Theme (light/dark/auto)
- Language
- Timezone
- Date format

**Tab 5: Performance**
- Enable caching
- Cache timeout
- Enable compression
- Max connections

---

## GŁÓWNE FLOW UŻYTKOWNIKA

### Flow 1: Backtest nowej strategii
```
/strategy-builder → Tworzy strategię
        ↓
/data-collection → Zbiera lub wybiera dane historyczne
        ↓
/trading-session → Mode: BACKTEST, wybiera strategię + sesję danych
        ↓
/dashboard?mode=backtest → Obserwuje wyniki
```

### Flow 2: Paper Trading
```
/trading-session → Mode: PAPER, wybiera strategię + symbole
        ↓
/dashboard?mode=paper → Obserwuje sygnały w real-time
        ↓
STOP → Analiza wyników
```

### Flow 3: Live Trading
```
/settings → Konfiguruje MEXC API keys
        ↓
/trading-session → Mode: LIVE (ostrzeżenie!)
        ↓
/dashboard?mode=live → Prawdziwe transakcje
```

---

## UWAGI IMPLEMENTACYJNE

### Co jest zaimplementowane ✅
- Podstawowy dashboard z kartami
- Trading session configuration
- Strategy builder 5-section
- Data collection z WebSocket
- Signal history panel
- Transaction history panel
- Market scanner
- Settings page

### Co wymaga weryfikacji ⚠️
- Interakcje z wykresami (zoom, scroll)
- Szczegóły sygnałów (panel boczny)
- Szczegóły transakcji
- Download danych
- Real-time alerts

---

**Dokument jest podstawą do testowania interfejsu.**
