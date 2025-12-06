# PEŁNY OPIS INTERFEJSU UI - FXcrypto

**Wersja:** 3.0 | **Data:** 2025-12-06

**Powiązane dokumenty:**
- `docs/UI_BACKLOG.md` - Priorytetyzowana lista funkcji do implementacji

---

## JAK AKTUALIZOWAĆ TEN DOKUMENT

### Kiedy aktualizować
- Po dodaniu nowej strony/funkcji do UI
- Po implementacji elementu z backlogu (`docs/UI_BACKLOG.md`)
- Co kilka iteracji pracy nad frontendem

### Jak przygotować aktualizację (prompt dla agenta)

```
Wciel się w tradera i przejdź przez interfejs:

1. Zobacz jakie są funkcjonalności interfejsu - poszczególnych jego stron
2. Zobacz do czego został stworzony
3. Opisz go słownie - jakie funkcje daje traderowi, co mu umożliwia zrobić
4. Uzasadnij że dobrze rozumiesz interfejs i niczego nie przegapiłeś
5. Zbuduj kompletny obraz tego co trader może zrobić - jak podróż przez interfejs

Następnie oceń krytycznie i obiektywnie:
- Czy ten sposób działania i te funkcje rzeczywiście spełniają oczekiwania tradera?
- Czy są rzeczy których brakuje? (ustawianie, przełączanie widoków, oglądanie szczegółów zleceń)
- Czy można obejrzeć wykres, przewijać go, powiększać?
- Czy konfiguracja strategii pozwala na dodawanie/usuwanie warunków?
- Pomyśl co zawiera dobry interfejs dla tradera - jakie funkcje, opcje które ułatwiają działanie, oglądanie.
```

### Format sekcji dla nowej strony

```markdown
## STRONA X: NAZWA (`/path`)

### Cel
[1-2 zdania: co trader tu robi]

### Układ
[ASCII diagram pokazujący layout strony]

### Funkcje
| Element | Funkcja | Interakcja |
|---------|---------|------------|
| [nazwa] | [co robi] | [jak trader wchodzi w interakcję] |

### Braki (jeśli są)
| Problem | Dlaczego ważne | Priorytet |
|---------|----------------|-----------|
```

---

## CEL SYSTEMU

**FXcrypto to system do wykrywania PUMP/DUMP i shortowania na szczycie pumpu.**

```
PUMP wykryty → Czekaj na SZCZYT → SHORT na szczycie → Zamknij gdy dump się kończy
```

### Główny przypadek użycia:

1. **Wykryj PUMP** - nagły wzrost ceny + volume surge + wysoka velocity
2. **Identyfikuj SZCZYT** - pump zwalnia, RSI overbought, exhaustion
3. **Wejdź SHORT** - na szczycie, przed dumpem
4. **Zarządzaj pozycją** - SL powyżej szczytu (jeśli pump kontynuuje), TP na dumpie

### Co trader robi w systemie:

1. **Tworzy warianty wskaźników** - konfiguruje czułość detekcji (jak szybko wykryć pump)
2. **Definiuje strategię** - kiedy wykryć pump (S1), kiedy wejść short (Z1), kiedy zamknąć (ZE1)
3. **Testuje na historii** - czy strategia poprawnie wykrywa szczyty?
4. **Monitoruje na żywo** - obserwuje sygnały i pozycje

---

## ARCHITEKTURA SYSTEMU (KLUCZOWE!)

### WSKAŹNIKI - Predefiniowane w systemie

**NIE TWORZYMY wskaźników od zera!** System ma 20+ wbudowanych algorytmów:

| Kategoria | Wskaźniki |
|-----------|-----------|
| **Pump Detection** | `PUMP_MAGNITUDE_PCT`, `PRICE_VELOCITY`, `VOLUME_SURGE_RATIO`, `PUMP_PROBABILITY` |
| **Techniczne** | `RSI`, `SMA`, `EMA`, `MACD`, `BOLLINGER_BANDS`, `VWAP` |
| **Momentum** | `PRICE_MOMENTUM`, `MOMENTUM_REVERSAL_INDEX`, `VELOCITY_CASCADE` |
| **Risk** | `POSITION_RISK_SCORE`, `UNREALIZED_PNL_PCT`, `PORTFOLIO_EXPOSURE_PCT` |
| **Liquidity** | `BID_ASK_IMBALANCE`, `LIQUIDITY_DRAIN_INDEX`, `DUMP_EXHAUSTION_SCORE` |
| **Market Data** | `PRICE`, `VOLUME`, `SPREAD_PCT`, `BEST_BID`, `BEST_ASK` |

### WARIANTY WSKAŹNIKÓW - Konfiguracje parametrów

**Wariant = wskaźnik bazowy + konkretne parametry**

```
Wskaźnik bazowy: PUMP_MAGNITUDE_PCT
Parametry: t1=10s (current window), t3=60s (baseline start), d=30s (baseline length)

Wariant 1: "Fast Pump" → t1=5s, t3=30s, d=15s  (szybsze wykrycie)
Wariant 2: "Slow Pump" → t1=20s, t3=120s, d=60s (mniej fałszywych)
```

**Typy wariantów (gdzie pokazywać na wykresie):**
- `general` - wykres pomocniczy (0-1 lub 0-100)
- `price` - główny wykres (wartości cenowe)
- `stop_loss` - linie SL na wykresie
- `take_profit` - linie TP na wykresie

### STRATEGIA 5-SEKCYJNA (dla pump/dump shorting)

```
┌─────────────────────────────────────────────────────────────────────┐
│              STRATEGIA 5-SEKCYJNA - PUMP/DUMP SHORTING              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  S1: PUMP DETECTION (wykrycie pumpu)                                │
│  ├─ PUMP_MAGNITUDE_PCT > 5%  (cena wzrosła o 5%)                   │
│  ├─ PRICE_VELOCITY > 0.5     (szybkość wzrostu)                    │
│  ├─ VOLUME_SURGE_RATIO > 3   (volume 3x większy niż normalnie)     │
│  └─ Wynik: "Mamy pumpa!" → szukaj szczytu                          │
│                                                                     │
│  O1: FALSE SIGNAL CANCELLATION (fałszywy alarm)                     │
│  ├─ Timeout: 60s - jeśli szczyt nie znaleziony → anuluj           │
│  ├─ PRICE_VELOCITY < 0 (cena zaczęła spadać PRZED shortem)         │
│  ├─ PUMP_MAGNITUDE_PCT < 2% (pump się "rozmył")                    │
│  └─ Cooldown: 5 min przed kolejnym sygnałem                        │
│                                                                     │
│  Z1: PEAK ENTRY - SHORT (wejście na szczycie)                       │
│  ├─ PRICE_VELOCITY < 0.1     (pump zwalnia!)                       │
│  ├─ MOMENTUM_REVERSAL_INDEX > 0.7 (sygnał odwrócenia)              │
│  ├─ DUMP_EXHAUSTION_SCORE < 0.3 (kupujący się wyczerpują)          │
│  │                                                                  │
│  ├─ Position Size: 10% kapitału                                    │
│  ├─ Stop Loss: +3% POWYŻEJ entry (jeśli pump kontynuuje)           │
│  ├─ Take Profit: -5% PONIŻEJ entry (gdy dump)                      │
│  └─ Leverage: 2x                                                   │
│                                                                     │
│  ZE1: DUMP END DETECTION (koniec dumpu - zamknij short)             │
│  ├─ PRICE_VELOCITY > -0.1   (dump zwalnia)                         │
│  ├─ DUMP_EXHAUSTION_SCORE > 0.8 (sprzedający wyczerpani)           │
│  └─ Wynik: zamknij short z zyskiem                                 │
│                                                                     │
│  E1: EMERGENCY EXIT (pump kontynuuje!)                              │
│  ├─ PUMP_MAGNITUDE_PCT > 15% (pump jest większy niż oczekiwano)    │
│  ├─ UNREALIZED_PNL_PCT < -5% (strata > 5%)                         │
│  └─ Akcje: zamknij natychmiast, cooldown 30 min                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### KLUCZOWE WSKAŹNIKI DLA PUMP/DUMP

| Wskaźnik | Co mierzy | Użycie w strategii |
|----------|-----------|-------------------|
| `PUMP_MAGNITUDE_PCT` | % wzrostu od baseline | S1: wykrycie pumpu (>5%) |
| `PRICE_VELOCITY` | szybkość zmiany ceny/s | S1: pump trwa, Z1: pump zwalnia |
| `VOLUME_SURGE_RATIO` | mnożnik volume vs normal | S1: potwierdzenie pumpu |
| `MOMENTUM_REVERSAL_INDEX` | sygnał odwrócenia trendu | Z1: szczyt osiągnięty |
| `DUMP_EXHAUSTION_SCORE` | wyczerpanie pressure | Z1: sprzedający wchodzą, ZE1: kończą |
| `UNREALIZED_PNL_PCT` | P&L otwartej pozycji | E1: max loss reached |

### WARUNEK - Struktura

```json
{
  "id": "pump_detected",
  "indicatorId": "PUMP_MAGNITUDE_PCT_fast",  ← nazwa WARIANTU wskaźnika
  "operator": ">",                            ← >, <, >=, <=, ==, between
  "value": 5.0,                               ← wartość progowa
  "enabled": true
}
```

### MASZYNA STANÓW STRATEGII

```
INACTIVE → MONITORING → SIGNAL_DETECTED → ENTRY_EVALUATION →
                ↓               ↓
         (O1 timeout)    (O1 conditions)
                ↓               ↓
           SIGNAL_CANCELLED ←───┘
                ↓
             cooldown
                ↓
           MONITORING (restart)

ENTRY_EVALUATION → POSITION_ACTIVE → CLOSE_ORDER_EVALUATION → EXITED
                          ↓                    ↓
                    (E1 emergency)       (ZE1 conditions / SL / TP)
                          ↓                    ↓
                    EMERGENCY_EXIT ←───────────┘
```

### CO UI MUSI WSPIERAĆ (dla pump/dump trading)

| Funkcja | Dlaczego potrzebne |
|---------|-------------------|
| **Tworzenie wariantów wskaźników** | Dostrojenie czułości wykrywania (szybki vs dokładny pump detection) |
| **Budowanie strategii 5-sekcyjnej** | S1: kiedy pump, Z1: kiedy szczyt, ZE1: kiedy dump kończy |
| **Wizualizacja wskaźników na wykresie** | Widzieć PUMP_MAGNITUDE, VELOCITY w czasie rzeczywistym |
| **Oznaczanie sygnałów na wykresie** | Gdzie był S1 (pump), Z1 (short entry), ZE1 (close) |
| **Backtest z wizualizacją** | Czy strategia poprawnie wykrywa szczyty? Gdzie były błędy? |
| **Real-time monitoring** | Aktualny pump magnitude, velocity, czy zbliża się szczyt? |
| **Analiza wyników** | Ile szczytów trafiono, ile fałszywych alarmów, avg P&L |

### CO TRADER CHCE WIDZIEĆ W UI

```
DASHBOARD podczas pump detection:
┌─────────────────────────────────────────────────────────────────────┐
│ BTC_USDT - PUMP W TOKU!                                             │
│                                                                     │
│ ⚡ PUMP_MAGNITUDE: 7.3%    ← jak duży pump                         │
│ 🚀 PRICE_VELOCITY: 0.42   ← pump nadal szybki                      │
│ 📊 VOLUME_SURGE: 4.2x     ← bardzo wysokie volume                  │
│                                                                     │
│ 🔴 Status: SIGNAL_DETECTED (S1 triggered 23s ago)                   │
│ ⏳ Czekam na szczyt... (Z1 conditions monitoring)                   │
│                                                                     │
│ [Wykres z zaznaczonym momentem S1 i aktualnym poziomem ceny]        │
│                                                                     │
│ Z1 Warunki:                                                         │
│ ├─ PRICE_VELOCITY < 0.1  ❌ (teraz: 0.42)                           │
│ ├─ MOMENTUM_REV > 0.7    ❌ (teraz: 0.35)                           │
│ └─ DUMP_EXHAUST < 0.3    ✅ (teraz: 0.22)                           │
│                                                                     │
│ Gdy Z1 spełnione → AUTO SHORT @ market                              │
│ SL: +3% | TP: -5%                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

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

### Braki
| Problem | Dlaczego ważne | Priorytet |
|---------|----------------|-----------|
| Brak mini-wykresu przy symbolu | Trader nie widzi setupu bez wykresu | HIGH |
| Brak stanu konta z giełdy | "Portfolio" - ale ile naprawdę na MEXC? | HIGH |
| Brak szczegółów aktywnych pozycji | 2 pozycje - ale KTÓRE? Na jakim P&L? | CRITICAL |
| Brak historii przegapionych sygnałów | Czy wczoraj były dobre sygnały? | MEDIUM |

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

### Braki
| Problem | Dlaczego ważne | Priorytet |
|---------|----------------|-----------|
| Brak podglądu strategii | Zaznaczam strategię ale NIE WIDZĘ jej warunków | HIGH |
| Brak rekomendacji symboli | Skaner widzi pump na SOL, ale brak połączenia z tą stroną | MEDIUM |
| Brak porównania strategii | Mam 3 strategie - która lepsza? Brak statystyk | MEDIUM |
| Brak ostrzeżenia o konflikcie | Co jeśli 2 strategie na ten sam symbol? | LOW |

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

### Braki (CRITICAL - najważniejsza strona!)
| Problem | Dlaczego ważne | Priorytet |
|---------|----------------|-----------|
| Brak zoom na wykresie | Muszę widzieć detale świecy, formację | CRITICAL |
| Brak scroll/przewijania wykresu | Chcę zobaczyć historię - co było 1h temu? | CRITICAL |
| Brak wskaźników na wykresie | RSI/MACD pokazane jako liczby - muszę WIDZIEĆ na wykresie | CRITICAL |
| Brak poziomu entry/SL/TP na wykresie | Nie widzę gdzie wszedłem i gdzie mam stopy | CRITICAL |
| Brak szczegółów sygnału | [Details] - ale gdzie panel ze szczegółami? | CRITICAL |
| Brak ręcznego zamknięcia pozycji | Widzę że idzie źle - JAK SZYBKO ZAMKNĄĆ? | CRITICAL |
| Brak modyfikacji SL/TP | Chcę przesunąć stop loss - gdzie to zrobić? | CRITICAL |
| Brak rysowania linii | Chcę narysować trend line, support/resistance | HIGH |
| Brak orderbook | Gdzie jest głębokość rynku? | HIGH |
| Brak trade tape | Chcę widzieć ostatnie transakcje na rynku | HIGH |
| Brak multi-timeframe | Widzę 1m, ale co na 5m, 15m, 1h? | HIGH |

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
│ TAB 2: STRATEGY EDITOR (5-Section Pump/Dump Builder)            │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Strategy Name: [pump_peak_shorting_v1                    ] │  │
│ │ Direction: [SHORT ▼] ← bo shortujemy na szczycie pumpu    │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ S1: PUMP DETECTION (wykrycie pumpu)                        │  │
│ │ ┌────────────────────────────────────────────────────────┐ │  │
│ │ │ [PumpFast▼]        [>▼]  [5.0  %]  ← pump > 5%  [🗑️] │ │  │
│ │ │ [VelocityQuick▼]   [>▼]  [0.3  ]   ← szybki wzrost    │ │  │
│ │ │ [VolumeSurge3x▼]   [>▼]  [2.5  x]  ← volume spikes    │ │  │
│ │ │ [+ Add Condition]                                      │ │  │
│ │ └────────────────────────────────────────────────────────┘ │  │
│ │ Logic: [AND▼] - wszystkie muszą być true                   │  │
│ │ ℹ️ Gdy S1 spełnione: "PUMP WYKRYTY!" → szukaj szczytu     │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ O1: FALSE SIGNAL CANCEL (fałszywy alarm)                   │  │
│ │ Timeout: [60    ] seconds ← jeśli szczyt nie w 60s        │  │
│ │ Cooldown: [5    ] minutes ← przed kolejnym sygnałem       │  │
│ │ Cancel if:                                                 │  │
│ │ ┌────────────────────────────────────────────────────────┐ │  │
│ │ │ [VelocityQuick▼]   [<▼]  [0   ]   ← pump cofnął [🗑️] │ │  │
│ │ │ [PumpFast▼]        [<▼]  [2.0 %]  ← pump rozmył się   │ │  │
│ │ │ [+ Add Condition]                                      │ │  │
│ │ └────────────────────────────────────────────────────────┘ │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Z1: PEAK ENTRY - SHORT (wejście na szczycie)               │  │
│ │ Position Size: [Percentage▼] [10 %]                        │  │
│ │ Leverage: [2   x]                                          │  │
│ │                                                            │  │
│ │ Entry when PEAK detected:                                  │  │
│ │ ┌────────────────────────────────────────────────────────┐ │  │
│ │ │ [VelocityQuick▼]       [<▼]  [0.1 ]   ← pump zwalnia  │ │  │
│ │ │ [ReversalSensitive▼]   [>▼]  [0.6 ]   ← sygnał zwrotu │ │  │
│ │ │ [+ Add Condition]                                      │ │  │
│ │ └────────────────────────────────────────────────────────┘ │  │
│ │                                                            │  │
│ │ Risk Management:                                           │  │
│ │ Stop Loss:   [+3   %] POWYŻEJ entry (pump kontynuuje)     │  │
│ │ Take Profit: [-5   %] PONIŻEJ entry (dump nastąpił)       │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ ZE1: DUMP END DETECTION (zamknij short gdy dump kończy)    │  │
│ │ ┌────────────────────────────────────────────────────────┐ │  │
│ │ │ [VelocityQuick▼]        [>▼]  [-0.1]  ← dump zwalnia  │ │  │
│ │ │ [DUMP_EXHAUSTION▼]      [>▼]  [0.7 ]  ← sprzedaż kończy│ │  │
│ │ │ [+ Add Condition]                                      │ │  │
│ │ └────────────────────────────────────────────────────────┘ │  │
│ │ ℹ️ Zamknij short z zyskiem zanim odbicie                  │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ E1: EMERGENCY EXIT (pump kontynuuje - uciekaj!)            │  │
│ │ ┌────────────────────────────────────────────────────────┐ │  │
│ │ │ [PumpFast▼]            [>▼]  [15  %]  ← mega pump!     │ │  │
│ │ │ [UNREALIZED_PNL_PCT▼]  [<▼]  [-5  %]  ← max loss       │ │  │
│ │ │ [+ Add Condition]                                      │ │  │
│ │ └────────────────────────────────────────────────────────┘ │  │
│ │ Actions: ☑️ Cancel pending ☑️ Close immediately ☑️ Log    │  │
│ │ Cooldown: [30   ] minutes                                  │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │           [Validate]  [Backtest Preview]  [Save Strategy]  │  │
│ └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Funkcje
| Element | Funkcja | Interakcja |
|---------|---------|------------|
| Strategy List | Przeglądanie strategii | ✏️ Edit, 🗑️ Delete |
| Strategy Name + Direction | Nazwa + SHORT/LONG | Text + dropdown |
| S1 Conditions | Warunki wykrycia PUMPU | Dropdown (warianty) + operator + value |
| O1 Cancel | Timeout + warunki anulowania | Inputs + conditions |
| Z1 Peak Entry | Warunki SZCZYTU + position size + SL/TP | Conditions + risk config |
| ZE1 Dump End | Warunki końca dumpu | Conditions |
| E1 Emergency | Warunki awaryjne + akcje | Conditions + checkboxy |
| Validate | Sprawdzenie poprawności | Kliknięcie → walidacja |
| Backtest Preview | Szybki test na ostatnich danych | Kliknięcie → mini-backtest |
| Save | Zapisanie strategii | Kliknięcie → API call |

### Braki
| Problem | Dlaczego ważne | Priorytet |
|---------|----------------|-----------|
| Brak wizualizacji "gdzie by był S1" | Chcę zobaczyć na wykresie gdzie by strategia wykryła pump | CRITICAL |
| Brak preview maszyny stanów | Jak strategia przechodzi S1→O1/Z1→ZE1/E1? | CRITICAL |
| Brak Backtest Preview | Ile szczytów trafiłbym z tą strategią? | HIGH |
| Brak walidacji logiki | Czy Z1 warunki mają sens po S1? | HIGH |
| Brak opisu wariantów | Dropdown pokazuje "PumpFast" ale co to znaczy? | MEDIUM |
| Brak importu/eksportu | Backup strategii, współdzielenie | MEDIUM |

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

### Braki
| Problem | Dlaczego ważne | Priorytet |
|---------|----------------|-----------|
| Download nie działa | "nie zaimplementowane" - a chcę analizować w Excelu! | HIGH |
| Brak jakości danych | Czy są luki? Missing candles? | MEDIUM |
| Brak statystyk danych | Ile świec, jaki zakres cen, avg volume | LOW |

---

## STRONA 6: INDICATOR VARIANTS (`/indicators`)

### Cel
**Konfiguracja wariantów predefiniowanych wskaźników** - dostrajanie czułości detekcji pump/dump.

**WAŻNE:** NIE tworzymy nowych wskaźników! Wybieramy z 20+ wbudowanych i konfigurujemy parametry.

### Układ

```
┌─────────────────────────────────────────────────────────────────┐
│ Indicator Variants - Pump/Dump Detection Configuration          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ KATEGORIE:                                                      │
│ [Pump Detection] [Momentum] [Risk] [Market Data]               │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ PUMP DETECTION VARIANTS                     [+ Create New] │  │
│ ├────────────────────────────────────────────────────────────┤  │
│ │ Name              │ Base Type          │ Parameters        │  │
│ ├───────────────────┼────────────────────┼───────────────────┤  │
│ │ PumpFast          │ PUMP_MAGNITUDE_PCT │ t1=5s, t3=30s     │  │
│ │ PumpMedium        │ PUMP_MAGNITUDE_PCT │ t1=10s, t3=60s    │  │
│ │ VelocityQuick     │ PRICE_VELOCITY     │ window=10s        │  │
│ │ VolumeSurge3x     │ VOLUME_SURGE_RATIO │ lookback=20       │  │
│ │ ReversalSensitive │ MOMENTUM_REV_INDEX │ threshold=0.5     │  │
│ └───────────────────┴────────────────────┴───────────────────┘  │
│                                                                 │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ CREATE VARIANT                                         [X] │  │
│ │                                                            │  │
│ │ Base Indicator: [PUMP_MAGNITUDE_PCT ▼]                     │  │
│ │ Variant Name:   [Fast_Pump_Detection    ]                  │  │
│ │                                                            │  │
│ │ PARAMETERS:                                                │  │
│ │ ├─ t1 (current window):  [5   ] seconds                    │  │
│ │ ├─ t3 (baseline start):  [30  ] seconds                    │  │
│ │ ├─ d  (baseline length): [15  ] seconds                    │  │
│ │ └─ r  (refresh interval):[1.0 ] seconds                    │  │
│ │                                                            │  │
│ │ PREVIEW:                                                   │  │
│ │ [Wykres pokazujący jak wariant reaguje na dane historyczne]│  │
│ │                                                            │  │
│ │                              [Cancel] [Save Variant]        │  │
│ └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Funkcje
| Element | Funkcja | Interakcja |
|---------|---------|------------|
| Kategorie | Filtrowanie wskaźników | Tabs: Pump, Momentum, Risk |
| Variants Table | Lista wariantów użytkownika | Kliknięcie → szczegóły |
| Create New | Tworzenie nowego wariantu | Dialog z parametrami |
| Base Indicator | Wybór z predefiniowanych | Dropdown z opisami |
| Parameters | Konfiguracja czułości | Inputy z walidacją |
| Preview | Wizualizacja jak wariant działa | Wykres real-time |

### Braki
| Problem | Dlaczego ważne | Priorytet |
|---------|----------------|-----------|
| Brak preview na danych historycznych | Jak ma się zachowywać PumpFast vs PumpMedium? | CRITICAL |
| Brak opisu parametrów | Co robi t1 vs t3? Jaki efekt ma zmiana? | HIGH |
| Brak porównania wariantów | Wykresy obok siebie: Fast vs Medium | HIGH |
| Brak testu "ile sygnałów by dał" | Ile S1 wygenerowałby ten wariant w ostatnich 24h? | MEDIUM |

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

### Braki
| Problem | Dlaczego ważne | Priorytet |
|---------|----------------|-----------|
| Brak mini-wykresu w tabeli | Symbol ma +12% - ale jak wygląda wykres? | HIGH |
| Brak historii sygnału | Ten symbol dał sygnał - ale co było ostatnio? | MEDIUM |
| Brak statystyk trafności | "STRONG signal" - ale ile % było trafnych? | MEDIUM |
| Brak szczegółów po kliknięciu | Klikam wiersz - chcę panel ze szczegółami | MEDIUM |

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

### Braki
| Problem | Dlaczego ważne | Priorytet |
|---------|----------------|-----------|
| Brak domyślnych SL/TP | Chcę ustawić domyślnie 3% SL, 6% TP | HIGH |
| Brak klawiszy skrótów | Szybko zamknij pozycję = jakiś klawisz? | MEDIUM |
| Brak profili | Jeden profil dla scalping, inny dla swing | MEDIUM |
| Brak backup/restore | Jak przenieść ustawienia na inny komputer? | LOW |
| Brak 2FA | Bezpieczeństwo konta | LOW |

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

## BRAKUJĄCE FUNKCJE SYSTEMOWE

### 1. Panel Zarządzania SHORT Pozycją (CRITICAL)
```
┌─────────────────────────────────────────────────────────────────┐
│ BTC_USDT SHORT 🔴 (shorting na szczycie pumpu)                  │
│                                                                 │
│ Entry: $65,500 (peak) | Current: $64,200 | P&L: +$130 (+1.98%) │
│ Size: 0.1 BTC | Leverage: 2x                                   │
│ SL: $67,500 (+3%) ⬆️ | TP: $62,200 (-5%) ⬇️                    │
│ Time in position: 12m 45s                                      │
│                                                                 │
│ Strategy State: POSITION_ACTIVE                                 │
│ ZE1 monitoring: DUMP_EXHAUSTION = 0.45 (waiting for 0.7)       │
│                                                                 │
│ ┌─────────┬─────────┬─────────┬─────────┐                      │
│ │ Close   │ Close   │ Modify  │ Emergency│                      │
│ │ 100%    │ 50%     │ SL/TP   │ Exit    │                      │
│ └─────────┴─────────┴─────────┴─────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Strona Raportów Pump/Dump (/reports)
```
PUMP/DUMP DETECTION STATS:
- Pumpy wykryte (S1): 47
- Szczyty trafione (Z1): 32 (68% accuracy)
- Fałszywe alarmy (O1 cancel): 15

TRADING PERFORMANCE:
- Win Rate: 71%
- Avg Win: +$85 (dump caught) | Avg Loss: -$35 (pump continued)
- Profit Factor: 2.4
- Max Drawdown: -$180 (-6.2%)

PER SYMBOL:
- BTC_USDT: 89% accuracy, +$450
- ETH_USDT: 65% accuracy, +$120
- SOL_USDT: 45% accuracy, -$80 (too volatile)
```

### 3. Interaktywny Wykres
```
TOOLBAR:
[🔍+] [🔍-] [📏] [✏️] [📐] [🔄] [⏱️ 1m|5m|15m|1h|4h|1d]

OVERLAYS:
- Poziom entry (zielona linia)
- Poziom SL (czerwona linia)
- Poziom TP (niebieska linia)
- RSI jako subplot poniżej
- Volume jako bars poniżej
- Sygnały S1/Z1/ZE1 jako markery

DRAWING TOOLS:
- Horizontal line
- Trend line
- Fibonacci retracement
- Rectangle (zone)

INTERACTIONS:
- Scroll: przewijanie historii
- Wheel: zoom in/out
- Drag: przesuwanie wykresu
- Click: crosshair z wartościami
```

### 4. Keyboard Shortcuts
```
ESC     - Emergency Stop All
C       - Close current position
S       - Toggle Scanner
D       - Go to Dashboard
T       - Go to Trading Session
1-9     - Switch symbols in watchlist
+/-     - Zoom chart
←→      - Scroll chart
F       - Full screen chart
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

### Priorytet implementacji
Patrz: `docs/UI_BACKLOG.md`

---

## CHANGELOG

### v3.0 (2025-12-06)
- **KLUCZOWE:** Dodano "ARCHITEKTURA SYSTEMU" - wyjaśnienie jak działają wskaźniki, warianty, strategia 5-sekcyjna
- Zmieniono cel systemu na: "wykrywanie pump/dump i shortowanie na szczycie"
- Strategia 5-sekcyjna teraz pokazuje przykład pump detection → peak shorting
- Zaktualizowano Strategy Builder z przykładem SHORT na szczycie pumpu
- Zaktualizowano Indicator Variants - wybór z predefiniowanych, nie tworzenie od zera
- Dodano kluczowe wskaźniki dla pump/dump (PUMP_MAGNITUDE_PCT, PRICE_VELOCITY, etc.)
- Dodano maszynę stanów strategii
- Zaktualizowano panel pozycji na SHORT
- Zaktualizowano raporty na pump/dump specific metrics

### v2.0 (2025-12-05)
- Dodano instrukcje aktualizacji dokumentu
- Dodano sekcje "Braki" do każdej strony
- Dodano "BRAKUJĄCE FUNKCJE SYSTEMOWE"
- Dodano link do UI_BACKLOG.md

### v1.0 (2025-12-05)
- Początkowa wersja dokumentu

---

**Dokument jest podstawą do testowania interfejsu i rozumienia systemu pump/dump detection.**
