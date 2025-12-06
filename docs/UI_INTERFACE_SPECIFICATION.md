# PEŁNY OPIS INTERFEJSU UI - FXcrypto

**Wersja:** 4.0 | **Data:** 2025-12-06

**Powiązane dokumenty:**
- `docs/UI_BACKLOG.md` - Priorytetyzowana lista funkcji do implementacji

---

## CEL SYSTEMU

**FXcrypto to system do wykrywania PUMP/DUMP i shortowania na szczycie pumpu.**

```
PUMP wykryty → Czekaj na SZCZYT → SHORT na szczycie → Zamknij gdy dump się kończy
```

---

## STATE MACHINE - SERCE SYSTEMU

### Dlaczego State Machine jest kluczowa?

State machine **TO JEST** strategia tradingowa. Wszystko w UI musi:
1. **Pozwalać konfigurować** przejścia między stanami (Strategy Builder)
2. **Pokazywać aktualny stan** w czasie rzeczywistym (Dashboard)
3. **Zapisywać historię przejść** do analizy (Session History)

### Stany i przejścia

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STATE MACHINE - PUMP/DUMP SHORTING                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐                                                              │
│   │ INACTIVE │ ← Strategia gotowa, sesja nie uruchomiona                    │
│   └────┬─────┘                                                              │
│        │ [START SESSION]                                                    │
│        ▼                                                                    │
│   ┌──────────────┐                                                          │
│   │  MONITORING  │ ← Szukamy pumpu (sprawdzamy warunki S1)                  │
│   └──────┬───────┘                                                          │
│          │ S1 CONDITIONS MET (pump detected!)                               │
│          ▼                                                                  │
│   ┌─────────────────┐                                                       │
│   │ SIGNAL_DETECTED │ ← Pump wykryty! Szukamy szczytu (sprawdzamy Z1)       │
│   └────────┬────────┘                                                       │
│            │                                                                │
│      ┌─────┴─────┐                                                          │
│      │           │                                                          │
│      ▼           ▼                                                          │
│  ┌────────┐  ┌──────────────────┐                                           │
│  │O1 CANCEL│  │ENTRY_EVALUATION │ ← Z1 conditions met, weryfikacja entry    │
│  └────┬───┘  └────────┬─────────┘                                           │
│       │               │                                                     │
│       │               ▼                                                     │
│       │         ┌─────────────────┐                                         │
│       │         │ POSITION_ACTIVE │ ← SHORT otwarty na szczycie!            │
│       │         └────────┬────────┘                                         │
│       │                  │                                                  │
│       │            ┌─────┴─────┐                                            │
│       │            │           │                                            │
│       │            ▼           ▼                                            │
│       │      ┌──────────┐  ┌──────────────┐                                 │
│       │      │ZE1 CLOSE │  │E1 EMERGENCY  │ ← Pump kontynuuje! Uciekaj!     │
│       │      │(dump end)│  │EXIT          │                                 │
│       │      └────┬─────┘  └──────┬───────┘                                 │
│       │           │               │                                         │
│       │           ▼               ▼                                         │
│       │      ┌─────────────────────┐                                        │
│       └─────►│       EXITED        │ ← Pozycja zamknięta                    │
│              └──────────┬──────────┘                                        │
│                         │                                                   │
│                         │ [cooldown]                                        │
│                         ▼                                                   │
│                    MONITORING (restart)                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Co definiuje każde przejście (5-sekcja strategii)

| Przejście | Sekcja | Co konfigurujemy |
|-----------|--------|------------------|
| MONITORING → SIGNAL_DETECTED | **S1** | Warunki wykrycia pumpu (PUMP_MAGNITUDE > 5%, VELOCITY > 0.3) |
| SIGNAL_DETECTED → EXITED | **O1** | Warunki anulowania (timeout 60s, pump cofnął) |
| SIGNAL_DETECTED → POSITION_ACTIVE | **Z1** | Warunki wejścia na szczycie (VELOCITY < 0.1, REVERSAL > 0.7) + SL/TP |
| POSITION_ACTIVE → EXITED | **ZE1** | Warunki zamknięcia shorta (dump się kończy) |
| POSITION_ACTIVE → EXITED | **E1** | Warunki emergency exit (pump > 15%, loss > 5%) |

---

## TRZY FAZY PRACY TRADERA

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   FAZA 1: KONFIGURACJA         FAZA 2: MONITORING         FAZA 3: ANALIZA  │
│   ═══════════════════         ═════════════════         ════════════════   │
│                                                                             │
│   ┌─────────────────┐         ┌─────────────────┐       ┌────────────────┐  │
│   │ /indicators     │         │ /trading-session│       │ /session-history│ │
│   │ Warianty        │         │ Start sesji     │       │ Lista sesji    │  │
│   └────────┬────────┘         └────────┬────────┘       └───────┬────────┘  │
│            │                           │                        │           │
│            ▼                           ▼                        ▼           │
│   ┌─────────────────┐         ┌─────────────────┐       ┌────────────────┐  │
│   │ /strategy-builder│        │ /dashboard      │       │ /session/[id]  │  │
│   │ State Machine   │────────►│ Live Monitoring │──────►│ Replay & Stats │  │
│   │ Configuration   │         │ Real-time State │       │ Transition Log │  │
│   └─────────────────┘         └─────────────────┘       └────────────────┘  │
│                                                                             │
│   Pytania tradera:            Pytania tradera:          Pytania tradera:   │
│   • Kiedy wykryć pump?        • Jaki jest stan?         • Dlaczego weszło? │
│   • Kiedy wejść short?        • Które warunki           • Czy peak był     │
│   • Jakie SL/TP?                spełnione?                trafiony?        │
│                               • Gdzie jest cena          • Co poprawić?    │
│                                 vs entry?                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## FAZA 1: KONFIGURACJA

### Cel
Trader definiuje **kiedy state machine przechodzi między stanami**.

### 1.1 Indicator Variants (`/indicators`)

**Cel:** Dostrojenie czułości wskaźników pump detection.

**NIE TWORZYMY wskaźników!** System ma 20+ wbudowanych:

| Kategoria | Wskaźniki |
|-----------|-----------|
| **Pump Detection** | `PUMP_MAGNITUDE_PCT`, `PRICE_VELOCITY`, `VOLUME_SURGE_RATIO`, `PUMP_PROBABILITY` |
| **Peak Detection** | `MOMENTUM_REVERSAL_INDEX`, `VELOCITY_CASCADE`, `DUMP_EXHAUSTION_SCORE` |
| **Risk** | `UNREALIZED_PNL_PCT`, `POSITION_RISK_SCORE`, `PORTFOLIO_EXPOSURE_PCT` |
| **Technical** | `RSI`, `MACD`, `BOLLINGER_BANDS`, `VWAP`, `SMA`, `EMA` |

**Wariant = wskaźnik bazowy + parametry czułości**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ INDICATOR VARIANTS                                          [+ New Variant] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ [Pump Detection] [Peak Detection] [Risk] [Technical]                        │
│                                                                             │
│ ┌───────────────┬────────────────────┬─────────────────────────────────────┐│
│ │ Variant Name  │ Base Indicator     │ Parameters                          ││
│ ├───────────────┼────────────────────┼─────────────────────────────────────┤│
│ │ PumpFast      │ PUMP_MAGNITUDE_PCT │ t1=5s, t3=30s, d=15s (szybki)       ││
│ │ PumpMedium    │ PUMP_MAGNITUDE_PCT │ t1=10s, t3=60s, d=30s (standard)    ││
│ │ VelocityQuick │ PRICE_VELOCITY     │ window=10s (responsywny)            ││
│ │ ReversalSens  │ MOMENTUM_REV_INDEX │ threshold=0.5 (czuły na peak)       ││
│ └───────────────┴────────────────────┴─────────────────────────────────────┘│
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ PREVIEW: PumpFast vs PumpMedium                                         │ │
│ │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│ │ │ [Wykres: oba warianty na historycznych danych]                      │ │ │
│ │ │                                                                     │ │ │
│ │ │ PumpFast: ▲ 12 sygnałów / 24h (więcej false positives)             │ │ │
│ │ │ PumpMedium: ▲ 5 sygnałów / 24h (mniej, ale dokładniejsze)          │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

**KRYTYCZNE WYMAGANIA:**
| Funkcja | Dlaczego potrzebna | Status |
|---------|-------------------|--------|
| Preview wariantu na wykresie | Widzieć jak reaguje na pump | ❌ BRAK |
| Porównanie wariantów | Fast vs Medium - który lepszy | ❌ BRAK |
| Opis parametrów | Co robi t1, t3, d? | ❌ BRAK |
| Ile sygnałów by wygenerował | Test na historii | ❌ BRAK |

---

### 1.2 Strategy Builder (`/strategy-builder`)

**Cel:** Definiowanie warunków przejść state machine (S1, O1, Z1, ZE1, E1).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STRATEGY BUILDER                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ Strategy Name: [pump_peak_shorting_v1        ]  Direction: [SHORT ▼]        │
│                                                                             │
│ ┌─────────────────────────────────────┬─────────────────────────────────────┐
│ │                                     │ STATE MACHINE PREVIEW               │
│ │ SECTIONS CONFIGURATION              │ ┌─────────────────────────────────┐ │
│ │                                     │ │                                 │ │
│ │ ┌─────────────────────────────────┐ │ │    [MONITORING]                 │ │
│ │ │ S1: PUMP DETECTION              │ │ │         │                       │ │
│ │ │ ┌─────────────────────────────┐ │ │ │    S1: pump>5% ∧ vel>0.3        │ │
│ │ │ │[PumpFast▼] [>] [5.0%] [🗑️]│ │ │ │         ▼                       │ │
│ │ │ │[VelocityQ▼] [>] [0.3] [🗑️]│ │ │ │  [SIGNAL_DETECTED]              │ │
│ │ │ │[+ Add Condition]            │ │ │ │     /         \                 │ │
│ │ │ └─────────────────────────────┘ │ │ │  O1:timeout   Z1:vel<0.1       │ │
│ │ │ Logic: AND                      │ │ │     ▼              ▼            │ │
│ │ └─────────────────────────────────┘ │ │ [EXITED]    [POSITION_ACTIVE]  │ │
│ │                                     │ │                  /      \       │ │
│ │ ┌─────────────────────────────────┐ │ │            ZE1:dump   E1:pump  │ │
│ │ │ O1: FALSE SIGNAL CANCEL         │ │ │                 ▼        ▼     │ │
│ │ │ Timeout: [60  ] sec             │ │ │              [EXITED]          │ │
│ │ │ Cooldown: [5   ] min            │ │ │                                 │ │
│ │ │ Cancel if:                      │ │ └─────────────────────────────────┘ │
│ │ │ ┌─────────────────────────────┐ │ │                                     │
│ │ │ │[VelocityQ▼] [<] [0  ] [🗑️]│ │ │ ┌─────────────────────────────────┐ │
│ │ │ └─────────────────────────────┘ │ │ │ QUICK BACKTEST (last 7 days)   │ │
│ │ └─────────────────────────────────┘ │ │ ┌─────────────────────────────┐ │ │
│ │                                     │ │ │ Pumpy wykryte (S1): 23      │ │ │
│ │ ┌─────────────────────────────────┐ │ │ │ Szczyty trafione (Z1): 18   │ │ │
│ │ │ Z1: PEAK ENTRY - SHORT          │ │ │ │ False alarms (O1): 5        │ │ │
│ │ │ Position: [10 %] Leverage: [2x] │ │ │ │ Accuracy: 78%               │ │ │
│ │ │ SL: [+3 %] TP: [-5 %]           │ │ │ │ Avg profit: +$42            │ │ │
│ │ │ Entry when:                     │ │ │ │                             │ │ │
│ │ │ ┌─────────────────────────────┐ │ │ │ │ [Show on Chart]            │ │ │
│ │ │ │[VelocityQ▼] [<] [0.1] [🗑️]│ │ │ └─────────────────────────────┘ │ │
│ │ │ │[ReversalS▼] [>] [0.7] [🗑️]│ │ │                                     │
│ │ │ └─────────────────────────────┘ │ │ ┌─────────────────────────────────┐ │
│ │ └─────────────────────────────────┘ │ │ WHERE WOULD S1 TRIGGER?        │ │
│ │                                     │ │ ┌─────────────────────────────┐ │ │
│ │ ┌─────────────────────────────────┐ │ │ │ [Wykres z zaznaczonymi      │ │ │
│ │ │ ZE1: DUMP END - CLOSE SHORT     │ │ │ │  momentami S1, Z1, ZE1]     │ │ │
│ │ │ ┌─────────────────────────────┐ │ │ │ │                             │ │ │
│ │ │ │[VelocityQ▼] [>] [-0.1][🗑️]│ │ │ │ │  ▲S1  ▼Z1      ▲ZE1         │ │ │
│ │ │ │[DumpExh▼]   [>] [0.7] [🗑️]│ │ │ │ │   │   │        │            │ │ │
│ │ │ └─────────────────────────────┘ │ │ │ └─────────────────────────────┘ │ │
│ │ └─────────────────────────────────┘ │ └─────────────────────────────────┘ │
│ │                                     │                                     │
│ │ ┌─────────────────────────────────┐ │                                     │
│ │ │ E1: EMERGENCY EXIT              │ │                                     │
│ │ │ ┌─────────────────────────────┐ │ │                                     │
│ │ │ │[PumpFast▼]  [>] [15%] [🗑️]│ │ │                                     │
│ │ │ │[UnrealPnL▼] [<] [-5%] [🗑️]│ │ │                                     │
│ │ │ └─────────────────────────────┘ │ │                                     │
│ │ │ Cooldown: [30  ] min            │ │                                     │
│ │ └─────────────────────────────────┘ │                                     │
│ │                                     │                                     │
│ └─────────────────────────────────────┴─────────────────────────────────────┘
│                                                                             │
│                        [Validate]  [Save Strategy]                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**KRYTYCZNE WYMAGANIA:**
| Funkcja | Dlaczego potrzebna | Status |
|---------|-------------------|--------|
| State machine diagram | Wizualizacja przepływu stanów | ❌ BRAK |
| Quick backtest | Ile pumpów by wykryła, ile szczytów trafiła | ❌ BRAK |
| "Where would S1 trigger" | Zaznaczenie na wykresie gdzie byłyby sygnały | ❌ BRAK |
| Tooltip przy wariantach | Co robi PumpFast vs PumpMedium | ❌ BRAK |

**OCENA AKTUALNEGO STANU:** 5/10
- ✅ 5-sekcyjna struktura zaimplementowana
- ✅ Wybór wariantów z dropdown
- ❌ Brak wizualizacji state machine
- ❌ Brak preview na wykresie
- ❌ Brak quick backtest

---

## FAZA 2: LIVE MONITORING

### Cel
Trader obserwuje **aktualny stan state machine** w czasie rzeczywistym.

### 2.1 Trading Session (`/trading-session`)

**Cel:** Uruchomienie sesji - przypisanie strategii do symboli.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CONFIGURE TRADING SESSION                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ 1. MODE:  [LIVE ⚠️]  [PAPER ✓]  [BACKTEST]                                 │
│                                                                             │
│ 2. STRATEGIES (click to see state machine):                                 │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ ☑️ pump_peak_shorting_v1                                                │ │
│ │    S1: PumpFast>5%, VelocityQ>0.3 → Z1: VelocityQ<0.1, ReversalS>0.7   │ │
│ │    SL: +3% | TP: -5% | Leverage: 2x                                     │ │
│ │ ☐ volume_surge_strategy                                                 │ │
│ │    S1: VolumeSurge>4x → Z1: ...                                        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ 3. SYMBOLS:                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ [BTC_USDT ✓]  [ETH_USDT ✓]  [SOL_USDT ✓]  [ADA_USDT]  [DOT_USDT]       │ │
│ │                                                                         │ │
│ │ 💡 SOL_USDT: Volume surge detected! Good for pump detection            │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ 4. SESSION MATRIX (what will run):                                          │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                        │ BTC_USDT │ ETH_USDT │ SOL_USDT │               │ │
│ │ pump_peak_shorting_v1  │    ✓     │    ✓     │    ✓     │ = 3 instances │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                               [START SESSION →]                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**KRYTYCZNE WYMAGANIA:**
| Funkcja | Dlaczego potrzebna | Status |
|---------|-------------------|--------|
| Strategy preview (warunki S1/Z1) | Widzieć co zaznaczyłem | ❌ BRAK |
| Symbol recommendation | Które symbole mają wysoki volume | ❌ BRAK |
| Session matrix | Jasne: 1 strategia × 3 symbole = 3 instancje | ❌ BRAK |

---

### 2.2 Dashboard - Live Monitoring (`/dashboard`)

**Cel:** Obserwacja state machine w czasie rzeczywistym.

**KLUCZOWE:** Dashboard musi pokazywać **STAN** każdej instancji (strategia × symbol).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LIVE MONITORING DASHBOARD                            [STOP ALL] [⚠️ E-STOP] │
├─────────────────────────────────────────────────────────────────────────────┤
│ Session: paper_abc123 | Running: 12m 34s | Mode: PAPER                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ STATE MACHINE OVERVIEW (all instances)                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Strategy              │ Symbol    │ STATE            │ Since  │ Action  │ │
│ ├───────────────────────┼───────────┼──────────────────┼────────┼─────────┤ │
│ │ pump_peak_shorting_v1 │ BTC_USDT  │ 🟢 MONITORING    │ 12m    │ [View]  │ │
│ │ pump_peak_shorting_v1 │ ETH_USDT  │ 🟡 SIGNAL_DETECT │ 23s    │ [View]  │ │
│ │ pump_peak_shorting_v1 │ SOL_USDT  │ 🔴 POSITION_ACT  │ 5m     │ [View]  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ═══════════════════════════════════════════════════════════════════════════ │
│ SELECTED: pump_peak_shorting_v1 × SOL_USDT [🔴 POSITION_ACTIVE - 5m 12s]    │
│ ═══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│ ┌──────────────────────────────────────┬────────────────────────────────────┐
│ │ CHART                                │ STATE MACHINE STATUS               │
│ │ ┌──────────────────────────────────┐ │ ┌────────────────────────────────┐ │
│ │ │                       ▲Z1 SHORT  │ │ │ ┌──────────┐                   │ │
│ │ │           ▲S1 pump    │          │ │ │ │MONITORING│ 10m               │ │
│ │ │            │    ╱╲────┤          │ │ │ └────┬─────┘                   │ │
│ │ │      ╱╲   │   ╱   ╲   │          │ │ │      │ S1: pump 7.2%          │ │
│ │ │    ╱╲  ╲  │  ╱     ╲  │ current  │ │ │      ▼                         │ │
│ │ │   ╱  ╲  ╲─┼─╱       ╲─┤ ←───     │ │ │ ┌─────────────────┐            │ │
│ │ │  ╱    ╲   │          ╲│          │ │ │ │ SIGNAL_DETECTED │ 45s        │ │
│ │ │ ╱      ╲──┴───────────┴──────    │ │ │ └────────┬────────┘            │ │
│ │ │ [─────────────────────SL +3%]    │ │ │          │ Z1: vel<0.1         │ │
│ │ │ [─────────────────────TP -5%]    │ │ │          ▼                     │ │
│ │ └──────────────────────────────────┘ │ │ ┌─────────────────┐            │ │
│ │ [🔍+] [🔍-] [◀] [▶] [1m|5m|15m|1h]  │ │ │ POSITION_ACTIVE │ ◀ CURRENT  │ │
│ │                                      │ │ │ 🔴 5m 12s       │            │ │
│ │ PUMP INDICATORS                      │ │ └────────┬────────┘            │ │
│ │ ┌──────────────────────────────────┐ │ │          │                     │ │
│ │ │ PUMP_MAGNITUDE: 7.2% ████████░░  │ │ │    ┌─────┴─────┐               │ │
│ │ │ PRICE_VELOCITY: 0.08 ███░░░░░░░  │ │ │    ▼           ▼               │ │
│ │ │ VOLUME_SURGE:   3.2x ██████░░░░  │ │ │ [ZE1 CLOSE] [E1 EMERGENCY]    │ │
│ │ │ REVERSAL_INDEX: 0.82 █████████░  │ │ │                               │ │
│ │ └──────────────────────────────────┘ │ └────────────────────────────────┘ │
│ └──────────────────────────────────────┤                                    │
│                                        │ ZE1 CONDITIONS (watching):         │
│ SHORT POSITION                         │ ┌────────────────────────────────┐ │
│ ┌──────────────────────────────────────┤ │ VelocityQ > -0.1  ✅ (0.08)    │ │
│ │ Entry: $142.50 (peak)                │ │ DumpExhaust > 0.7 ❌ (0.45)    │ │
│ │ Current: $138.20 (-3.0%)             │ └────────────────────────────────┘ │
│ │ P&L: +$43.00 (+3.0%) 🟢              │                                    │
│ │ Size: 10 SOL | Leverage: 2x          │ E1 CONDITIONS (emergency):         │
│ │ SL: $146.77 (+3%) ⬆️                 │ ┌────────────────────────────────┐ │
│ │ TP: $135.37 (-5%) ⬇️                 │ │ PumpFast > 15%    ❌ (7.2%)    │ │
│ │ Time: 5m 12s                         │ │ UnrealPnL < -5%   ❌ (+3.0%)   │ │
│ ├──────────────────────────────────────┤ └────────────────────────────────┘ │
│ │ [Close 100%] [Close 50%] [Modify SL] │                                    │
│ │ [🚨 EMERGENCY CLOSE]                 │ [View Transition Log]              │
│ └──────────────────────────────────────┴────────────────────────────────────┘
│                                                                             │
│ TRANSITION LOG (this instance):                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 12:34:12 │ MONITORING → SIGNAL_DETECTED │ S1: pump=7.2%, vel=0.42      │ │
│ │ 12:34:57 │ SIGNAL_DETECTED → POSITION   │ Z1: vel=0.08, rev=0.82       │ │
│ │ 12:34:57 │ SHORT opened @ $142.50       │ SL=$146.77, TP=$135.37       │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

**KRYTYCZNE WYMAGANIA:**
| Funkcja | Dlaczego potrzebna | Status |
|---------|-------------------|--------|
| State overview table | Widzieć stan WSZYSTKICH instancji | ❌ BRAK |
| Current state display | Który stan teraz: MONITORING/SIGNAL/POSITION | ❌ BRAK |
| Condition progress | Które warunki ZE1/E1 spełnione, które pending | ❌ BRAK |
| Chart S1/Z1 markers | Gdzie był pump, gdzie short entry | ❌ BRAK |
| Chart zoom/scroll | Analiza szczegółów pumpu | ❌ BRAK |
| Position panel | Entry, P&L, SL/TP, time in position | ❌ BRAK |
| Emergency close | Szybkie zamknięcie gdy pump kontynuuje | ❌ BRAK |
| Transition log | Historia przejść state machine | ❌ BRAK |

**OCENA AKTUALNEGO STANU:** 3/10
- ✅ Watchlist z symbolami
- ✅ Basic chart (candlestick)
- ✅ Summary cards
- ❌ Brak state machine visibility
- ❌ Brak condition progress
- ❌ Brak zoom/scroll na wykresie
- ❌ Brak markerów S1/Z1/ZE1
- ❌ Brak position management panel
- ❌ Brak transition log

---

## FAZA 3: HISTORICAL REVIEW

### Cel
Trader analizuje **co state machine zrobiła** w przeszłych sesjach.

### 3.1 Session History (`/session-history`) - NOWA STRONA

**Cel:** Lista wszystkich przeszłych sesji z możliwością drill-down.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SESSION HISTORY                                               [Export CSV]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ FILTER: [All Modes ▼] [All Strategies ▼] [Last 7 days ▼]                   │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Session ID  │ Mode    │ Strategy            │ Duration │ P&L    │ Win% │ │
│ ├─────────────┼─────────┼─────────────────────┼──────────┼────────┼──────┤ │
│ │ paper_abc123│ PAPER   │ pump_peak_short_v1  │ 4h 23m   │ +$145  │ 72%  │ │
│ │ paper_xyz789│ PAPER   │ volume_surge        │ 2h 10m   │ -$32   │ 45%  │ │
│ │ back_def456 │ BACKTEST│ pump_peak_short_v1  │ 7 days   │ +$890  │ 78%  │ │
│ └─────────────┴─────────┴─────────────────────┴──────────┴────────┴──────┘ │
│                                                                             │
│ Click session to see details...                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Session Detail (`/session-history/[id]`)

**Cel:** Szczegółowa analiza jednej sesji - co state machine robiła i dlaczego.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SESSION DETAIL: paper_abc123                                    [Replay ▶️] │
├─────────────────────────────────────────────────────────────────────────────┤
│ Strategy: pump_peak_shorting_v1 | Duration: 4h 23m | P&L: +$145            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ SUMMARY STATS                                                               │
│ ┌───────────────┬───────────────┬───────────────┬───────────────┬─────────┐│
│ │ Pumpy wykryte │ Szczyty       │ False alarms  │ Emergency     │ Accuracy││
│ │ (S1)          │ trafione (Z1) │ (O1)          │ exits (E1)    │         ││
│ │ 12            │ 8             │ 3             │ 1             │ 72%     ││
│ └───────────────┴───────────────┴───────────────┴───────────────┴─────────┘│
│                                                                             │
│ TRANSITION TIMELINE                                                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 10:00  10:30  11:00  11:30  12:00  12:30  13:00  13:30  14:00          │ │
│ │   │      │      │      │      │      │      │      │      │            │ │
│ │   ●──────●S1────●Z1────●ZE1───●──────●S1────●O1────●──────●S1──...     │ │
│ │   │      │pump  │short │close │      │pump  │cancel│      │pump        │ │
│ │   │      │+7%   │entry │+$45  │      │+4%   │timeout      │+8%         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│ Click transition to see details...                                          │
│                                                                             │
│ DETAILED TRANSITIONS (click to expand)                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ ▼ 10:23:45 │ S1 TRIGGERED │ BTC_USDT │ PUMP DETECTED                    │ │
│ │   │                                                                     │ │
│ │   │ Conditions met:                                                     │ │
│ │   │ ├─ PumpFast = 7.2% (threshold: >5%)  ✅                             │ │
│ │   │ ├─ VelocityQ = 0.42 (threshold: >0.3)  ✅                           │ │
│ │   │ └─ VolumeSurge = 3.2x (threshold: >2.5x)  ✅                        │ │
│ │   │                                                                     │ │
│ │   │ Market snapshot:                                                    │ │
│ │   │ ├─ Price: $65,234                                                   │ │
│ │   │ ├─ Volume: 2,345 BTC (last 1m)                                      │ │
│ │   │ └─ RSI: 78                                                          │ │
│ ├───┴─────────────────────────────────────────────────────────────────────┤ │
│ │ ▶ 10:24:30 │ Z1 TRIGGERED │ BTC_USDT │ PEAK ENTRY - SHORT               │ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │ ▶ 10:31:15 │ ZE1 TRIGGERED│ BTC_USDT │ DUMP END - CLOSE SHORT           │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ CHART WITH ALL S1/Z1/ZE1 MARKERS                                            │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                   ▲S1      ▼Z1                      ▲ZE1                │ │
│ │                    │    ╱╲──┤                        │                  │ │
│ │              ╱╲    │   ╱   ╲│                        │                  │ │
│ │            ╱╲  ╲───┼──╱     ╲────────────────────────┤                  │ │
│ │           ╱  ╲     │         ╲                      │                   │ │
│ │          ╱    ╲────┴──────────╲────────────────────┘                    │ │
│ │         ╱                      ╲                                        │ │
│ │ [══════════════════════════════════════════════════════════════════]   │ │
│ │ [🔍+] [🔍-] [◀] [▶]                                                    │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ PER-TRADE BREAKDOWN                                                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Trade │ Symbol   │ Entry     │ Exit      │ P&L    │ Duration │ Exit    │ │
│ ├───────┼──────────┼───────────┼───────────┼────────┼──────────┼─────────┤ │
│ │ #1    │ BTC_USDT │ $65,500   │ $64,200   │ +$130  │ 6m 45s   │ ZE1     │ │
│ │ #2    │ BTC_USDT │ $66,100   │ $67,000   │ -$90   │ 2m 12s   │ E1 ⚠️   │ │
│ │ #3    │ BTC_USDT │ $64,800   │ $63,500   │ +$105  │ 8m 30s   │ TP hit  │ │
│ └───────┴──────────┴───────────┴───────────┴────────┴──────────┴─────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

**KRYTYCZNE WYMAGANIA dla Historical Review:**
| Funkcja | Dlaczego potrzebna | Status |
|---------|-------------------|--------|
| Session list | Przegląd wszystkich sesji | ❌ BRAK STRONY |
| Session summary stats | Ile S1, Z1, O1, E1, accuracy | ❌ BRAK |
| Transition timeline | Wizualizacja kiedy co się działo | ❌ BRAK |
| Transition details | Jakie wartości miały wskaźniki | ❌ BRAK |
| Chart with markers | Wykres z zaznaczonymi S1/Z1/ZE1 | ❌ BRAK |
| Per-trade breakdown | Każdy trade osobno z P&L | ❌ BRAK |
| Replay mode | Odtworzenie sesji krok po kroku | ❌ BRAK |

---

## ARCHITEKTURA DANYCH DLA STATE MACHINE

### Co musi być zapisywane (dla historical review)

```json
{
  "session_id": "paper_abc123",
  "mode": "PAPER",
  "strategy_id": "pump_peak_shorting_v1",
  "symbol": "BTC_USDT",
  "start_time": "2024-12-06T10:00:00Z",
  "end_time": "2024-12-06T14:23:00Z",

  "transitions": [
    {
      "timestamp": "2024-12-06T10:23:45Z",
      "from_state": "MONITORING",
      "to_state": "SIGNAL_DETECTED",
      "trigger": "S1",
      "conditions": {
        "PumpFast": {"value": 7.2, "threshold": 5.0, "operator": ">", "met": true},
        "VelocityQ": {"value": 0.42, "threshold": 0.3, "operator": ">", "met": true}
      },
      "market_snapshot": {
        "price": 65234,
        "volume_1m": 2345,
        "rsi": 78
      }
    },
    {
      "timestamp": "2024-12-06T10:24:30Z",
      "from_state": "SIGNAL_DETECTED",
      "to_state": "POSITION_ACTIVE",
      "trigger": "Z1",
      "conditions": {...},
      "position_opened": {
        "entry_price": 65500,
        "size": 0.1,
        "leverage": 2,
        "sl": 67465,
        "tp": 62225
      }
    }
  ],

  "trades": [
    {
      "trade_id": 1,
      "entry_time": "2024-12-06T10:24:30Z",
      "entry_price": 65500,
      "exit_time": "2024-12-06T10:31:15Z",
      "exit_price": 64200,
      "exit_trigger": "ZE1",
      "pnl": 130,
      "pnl_pct": 1.98
    }
  ],

  "summary": {
    "s1_count": 12,
    "z1_count": 8,
    "o1_count": 3,
    "e1_count": 1,
    "accuracy": 0.72,
    "total_pnl": 145,
    "win_rate": 0.72
  }
}
```

---

## PODSUMOWANIE OCEN

### Aktualny stan implementacji

| Komponent | Ocena | Główne braki |
|-----------|-------|--------------|
| **Indicator Variants** | 4/10 | Brak preview, brak porównania wariantów |
| **Strategy Builder** | 5/10 | Brak state machine diagram, brak quick backtest |
| **Trading Session** | 5/10 | Brak strategy preview, brak session matrix |
| **Dashboard (Live)** | 3/10 | Brak state visibility, brak condition progress, brak zoom |
| **Session History** | 0/10 | **STRONA NIE ISTNIEJE** |

### Co jest CRITICAL dla state machine centric design

1. **State machine visibility** - trader MUSI widzieć aktualny stan
2. **Condition progress** - trader MUSI widzieć które warunki spełnione
3. **Transition log** - trader MUSI widzieć historię przejść
4. **Chart markers** - trader MUSI widzieć S1/Z1/ZE1 na wykresie
5. **Session history** - trader MUSI móc analizować przeszłe sesje

---

## CHANGELOG

### v4.0 (2025-12-06)
- **MAJOR REFACTOR:** Całość dokumentacji przeprojektowana pod STATE MACHINE CENTRIC DESIGN
- Dodano sekcję "STATE MACHINE - SERCE SYSTEMU" z pełnym diagramem stanów
- Nowa struktura: 3 FAZY PRACY TRADERA (Konfiguracja, Monitoring, Analiza)
- Dodano szczegółowy opis Session History (NOWA STRONA) dla historical review
- Dodano architekturę danych dla zapisywania transition log
- Zaktualizowano wszystkie mockupy aby pokazywały state machine status
- Dodano oceny aktualnego stanu każdego komponentu

### v3.0 (2025-12-06)
- Dodano architekturę systemu (wskaźniki, warianty, 5-sekcja)

### v2.0 (2025-12-05)
- Dodano instrukcje aktualizacji dokumentu

### v1.0 (2025-12-05)
- Początkowa wersja dokumentu
