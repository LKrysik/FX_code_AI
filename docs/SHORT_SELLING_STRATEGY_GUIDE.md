# SHORT SELLING Strategy Guide - Pump & Dump Hunter

## 📋 Spis treści

1. [Przegląd strategii](#przegląd-strategii)
2. [Architektura wskaźników](#architektura-wskaźników)
3. [Konfiguracja strategii](#konfiguracja-strategii)
4. [Parametry wskaźników](#parametry-wskaźników)
5. [Testowanie i optymalizacja](#testowanie-i-optymalizacja)
6. [Zarządzanie ryzykiem](#zarządzanie-ryzykiem)
7. [Typowe scenariusze](#typowe-scenariusze)

---

## Przegląd strategii

### Cel strategii
Strategia **SHORT SELLING - Pump & Dump Hunter** wykrywa pump (sztuczne pompowanie ceny) i gra dump (spadek) poprzez otwarcie pozycji SHORT w momencie peak pumpu i zamknięcie pozycji gdy dump się wyczerpuje.

### Typowy cykl pump & dump
```
Pump (2-5 min)      Dump (3-10 min)
     ▲                  ▼
     │                  │
     │  ┌──────┐        │
     │  │ PEAK │        │
     │ ╱        ╲       │
    ╱ ╱          ╲      │
   ╱╱              ╲    │
  ──                ╲   │
Baseline             ╲ ╱
                      ─────
                     Support
```

### Fazy strategii

1. **S1 - Signal Detection (Entry Signal)**
   - Wykrywa początek pumpu
   - 4 wskaźniki muszą dać sygnał jednocześnie
   - Czas reakcji: < 1 sekunda

2. **Z1 - Entry Execution**
   - Otwiera pozycję SHORT
   - Timeout: 60 sekund
   - Position size: 2% portfela

3. **O1 - Cancellation Logic**
   - Anuluje pozycję jeśli pump trwa dalej
   - Timeout: 300 sekund (5 minut)
   - Cooldown: 5 minut po anulowaniu

4. **ZE1 - Close Position**
   - Zamyka pozycję gdy dump się wyczerpuje
   - 3 wskaźniki (OR logic): jeden wystarczy
   - Cel: wychwycenie 10-30% spadku

5. **Emergency Exit**
   - Awaryjne zamknięcie przy nagłym odwróceniu
   - Stop loss: momentum reversal > 50%
   - Cooldown: 60 minut

---

## Architektura wskaźników

### Tier 1 - Detekcja pumpu (Entry)

#### 1. PUMP_MAGNITUDE_PCT
**Plik:** `config/indicators/price/pump_magnitude_pct_default.json`

```python
Formula: ((TWPA(t1,0) - TWPA(t3-d,t3)) / TWPA(t3-d,t3)) * 100

Parametry:
- t1 = 10s    # Current price window
- t3 = 60s    # Baseline lookback
- d = 10s     # Baseline window length
- r = 1s      # Refresh interval
```

**Interpretacja:**
- Value >= 15%: Znaczący pump (entry signal)
- Value 5-15%: Umiarkowany wzrost
- Value < 5%: Normalny ruch

**Użycie w strategii:**
```json
{
  "indicatorId": "pump-magnitude-001",
  "operator": ">=",
  "value": 15.0
}
```

---

#### 2. VOLUME_SURGE_RATIO
**Plik:** `config/indicators/general/volume_surge_ratio_default.json`

```python
Formula: volume_avg(t1,t2) / volume_median(t3,t4)

Parametry:
- t1 = 30s    # Current window start
- t2 = 0s     # Current window end
- t3 = 600s   # Baseline start (10 min ago)
- t4 = 30s    # Baseline end
- r = 1s      # Refresh interval
```

**Interpretacja:**
- Value >= 3.0: Silny surge (3x normalny wolumen)
- Value 2.0-3.0: Umiarkowany surge
- Value < 2.0: Normalny wolumen

**Użycie w strategii:**
```json
{
  "indicatorId": "volume-surge-001",
  "operator": ">=",
  "value": 3.0
}
```

---

#### 3. PRICE_VELOCITY
**Plik:** `config/indicators/general/price_velocity_default.json`

```python
Formula: ((TWPA_current - TWPA_baseline) / TWPA_baseline * 100) / time_diff

Parametry:
- t1 = 10s    # Current window length
- t3 = 40s    # Baseline lookback
- d = 10s     # Baseline window length
- r = 1s      # Refresh interval
```

**Interpretacja:**
- Value >= 0.5%/s: Szybki wzrost (30%/min)
- Value 0.2-0.5%/s: Umiarkowany wzrost
- Value < 0.2%/s: Wolny wzrost

**Użycie w strategii:**
```json
{
  "indicatorId": "price-velocity-001",
  "operator": ">=",
  "value": 0.5
}
```

---

#### 4. VELOCITY_CASCADE
**Plik:** `config/indicators/general/velocity_cascade_default.json`

```python
Formula: Cascade index from multiple timeframe velocities

Parametry:
- windows: [
    {t1: 5, t3: 15, d: 5},   # Ultra short (5s)
    {t1: 10, t3: 40, d: 10}, # Short (10s)
    {t1: 20, t3: 80, d: 20}  # Medium (20s)
  ]
- r = 2s
```

**Interpretacja:**
- Value > 0.5: Przyspieszenie (acceleration)
- Value 0 to 0.5: Stabilne tempo
- Value < 0: Spowolnienie (deceleration)

**Użycie w strategii:**
```json
{
  "indicatorId": "velocity-cascade-001",
  "operator": ">=",
  "value": 0.5
}
```

---

### Tier 1 Part 2 - Monitoring

#### 5. MOMENTUM_REVERSAL_INDEX
**Plik:** `config/indicators/general/momentum_reversal_index_default.json`

```python
Formula: ((velocity_current - velocity_peak) / abs(velocity_peak)) * 100

Parametry:
- t1_current = 10s
- t3_current = 40s
- d_current = 10s
- t1_peak = 20s
- t3_peak = 80s
- d_peak = 20s
- r = 1s
```

**Interpretacja:**
- Value < -20%: Pump trwa (anuluj entry)
- Value -20% to 0%: Pump stabilizuje się
- Value > 0%: Początek dumpu
- Value > 50%: Nagłe odwrócenie (emergency exit)

**Użycie w strategii:**
```json
// O1 Cancel
{
  "indicatorId": "momentum-reversal-001",
  "operator": "<",
  "value": -20.0
}

// Emergency Exit
{
  "indicatorId": "momentum-reversal-001",
  "operator": ">=",
  "value": 50.0
}
```

---

### Tier 2 - Wykrywanie końca dumpu (Exit)

#### 6. DUMP_EXHAUSTION_SCORE
**Plik:** `config/indicators/general/dump_exhaustion_score_default.json`

```python
Formula: Weighted sum of 4 factors (max 100 points)

Factors:
1. Velocity stabilization (30 pts): abs(velocity) < 0.1%/s
2. Volume normalization (25 pts): current_volume < baseline * 0.8
3. Retracement depth (25 pts): retracement >= 40%
4. Bid-ask balance (20 pts): imbalance > -10%

Parametry:
- velocity_t1 = 10s
- velocity_t3 = 40s
- velocity_d = 10s
- volume_t1 = 30s
- volume_t2 = 0s
- volume_t3 = 600s
- volume_t4 = 30s
- imbalance_t1 = 30s
- imbalance_t2 = 0s
- peak_price = 0.0     # Set dynamically
- current_price = 0.0  # Set dynamically
- velocity_threshold = 0.1
- volume_threshold = 0.8
- retracement_threshold = 40.0
- imbalance_threshold = -10.0
- r = 2s
```

**Interpretacja:**
- Score >= 70: Dump wyczerpany (exit signal)
- Score 50-70: Dump blisko końca
- Score < 50: Dump aktywny

**Użycie w strategii:**
```json
{
  "indicatorId": "dump-exhaustion-001",
  "operator": ">=",
  "value": 70.0
}
```

---

#### 7. SUPPORT_LEVEL_PROXIMITY
**Plik:** `config/indicators/close_order/support_level_proximity_default.json`

```python
Formula: ((current_price - support_level) / support_level) * 100

Parametry:
- t1 = 10s                # Current price window
- t_support_start = 3600s # 1 hour ago (pre-pump)
- t_support_end = 600s    # 10 min ago
- proximity_threshold = 2.0
- r = 1s
```

**Interpretacja:**
- Value > 5%: Daleko od wsparcia
- Value 0-5%: Blisko wsparcia (exit zone)
- Value < 0%: Poniżej wsparcia (overshoot)

**Użycie w strategii:**
```json
{
  "indicatorId": "support-proximity-001",
  "operator": "<=",
  "value": 2.0
}
```

---

#### 8. VELOCITY_STABILIZATION_INDEX
**Plik:** `config/indicators/general/velocity_stabilization_index_default.json`

```python
Formula: std_dev(velocities) / mean_abs(velocities)

Parametry:
- num_samples = 3
- sample_interval = 5s
- t1 = 10s
- t3 = 40s
- d = 10s
- r = 2s
```

**Interpretacja:**
- Value < 0.5: Wysokostabilne (exit signal)
- Value 0.5-1.5: Umiarkowana stabilność
- Value > 1.5: Wysoka zmienność

**Użycie w strategii:**
```json
{
  "indicatorId": "velocity-stabilization-001",
  "operator": "<=",
  "value": 0.5
}
```

---

## Konfiguracja strategii

### Plik strategii
**Lokalizacja:** `config/strategies/short_selling_pump_dump_v1.json`

### S1 - Signal Detection
```json
"s1_signal": {
  "conditions": [
    {"indicatorId": "pump-magnitude-001", "operator": ">=", "value": 15.0},
    {"indicatorId": "volume-surge-001", "operator": ">=", "value": 3.0},
    {"indicatorId": "price-velocity-001", "operator": ">=", "value": 0.5},
    {"indicatorId": "velocity-cascade-001", "operator": ">=", "value": 0.5}
  ],
  "logic": "AND"
}
```

**Logika:** Wszystkie 4 warunki muszą być spełnione jednocześnie.

**Progi:**
- Pump >= 15%: Wyklucza małe ruchy, celuje w wyraźne pumpy
- Volume >= 3x: Potwierdza nienaturalną aktywność
- Velocity >= 0.5%/s: Zapewnia szybki ruch (30%/min)
- Cascade >= 0.5: Potwierdzenie przyspieszenia na wielu timeframe'ach

---

### Z1 - Entry Execution
```json
"z1_entry": {
  "conditions": [],
  "positionSize": {
    "type": "percentage",
    "value": 2.0
  },
  "timeoutSeconds": 60
}
```

**Position Sizing:** 2% portfela
- Konserwatywne dla short sellingu
- Można skalować 1-5% w zależności od risk appetite

**Timeout:** 60 sekund
- Jeśli nie uda się otworzyć pozycji w 60s, anuluj
- Zapobiega entry po peaku

---

### O1 - Cancellation Logic
```json
"o1_cancel": {
  "timeoutSeconds": 300,
  "conditions": [
    {"indicatorId": "momentum-reversal-001", "operator": "<", "value": -20.0}
  ],
  "cooldownMinutes": 5
}
```

**Warunek anulowania:**
- Momentum < -20%: Pump wciąż przyspiesza (zły entry timing)

**Timeout:** 300 sekund (5 minut)
- Jeśli pump trwa > 5 min, anuluj (nietypowy pump)

**Cooldown:** 5 minut
- Po anulowaniu czekaj 5 min przed następnym sygnałem
- Zapobiega rapid re-entry na tym samym pumpie

---

### ZE1 - Close Position
```json
"ze1_close": {
  "conditions": [
    {"indicatorId": "dump-exhaustion-001", "operator": ">=", "value": 70.0},
    {"indicatorId": "support-proximity-001", "operator": "<=", "value": 2.0},
    {"indicatorId": "velocity-stabilization-001", "operator": "<=", "value": 0.5}
  ],
  "logic": "OR"
}
```

**Logika:** Jeden z trzech warunków wystarczy do zamknięcia.

**Warunki:**
1. **Exhaustion >= 70:** Multi-factor score pokazuje wyczerpanie
2. **Support <= 2%:** Cena blisko pre-pump support
3. **Stabilization <= 0.5:** Prędkość się stabilizuje

**Strategia:** Konserwatywne wyjście
- "OR" logic = wyjdź przy pierwszym sygnale końca dumpu
- Preferuje pewny profit nad maksymalizacją zysku

---

### Emergency Exit
```json
"emergency_exit": {
  "conditions": [
    {"indicatorId": "momentum-reversal-001", "operator": ">=", "value": 50.0}
  ],
  "cooldownMinutes": 60,
  "actions": {
    "cancelPending": true,
    "closePosition": true,
    "logEvent": true
  }
}
```

**Warunek:**
- Momentum >= 50%: Nagłe odwrócenie w górę (pump resumes)

**Akcje:**
- Anuluj pending orders
- Zamknij pozycję natychmiast
- Loguj event do analizy

**Cooldown:** 60 minut
- Po emergency exit czekaj godzinę
- System potrzebuje "ochłonąć" po false alarm

---

## Parametry wskaźników

### Dostrajanie progów S1

#### Scenariusz: Zbyt mało sygnałów
**Problem:** Strategia nie generuje sygnałów przez kilka godzin.

**Rozwiązanie:** Złagodź progi
```json
// Zamiast:
{"indicatorId": "pump-magnitude-001", "operator": ">=", "value": 15.0}

// Użyj:
{"indicatorId": "pump-magnitude-001", "operator": ">=", "value": 10.0}
```

**Inne progi do złagodzenia:**
- Volume surge: 3.0 → 2.5
- Price velocity: 0.5 → 0.3
- Velocity cascade: 0.5 → 0.3

---

#### Scenariusz: Zbyt wiele false positives
**Problem:** Dużo sygnałów, ale niska skuteczność.

**Rozwiązanie:** Zaostrz progi
```json
// Zamiast:
{"indicatorId": "pump-magnitude-001", "operator": ">=", "value": 15.0}

// Użyj:
{"indicatorId": "pump-magnitude-001", "operator": ">=", "value": 20.0}
```

**Inne progi do zaostrzenia:**
- Volume surge: 3.0 → 4.0
- Price velocity: 0.5 → 0.7
- Velocity cascade: 0.5 → 0.7

---

### Dostrajanie ZE1 Exit

#### Scenariusz: Zbyt wczesne wyjście (missed profits)
**Problem:** Pozycja zamyka się zanim dump się skończy.

**Rozwiązanie:** Zaostrz progi exit
```json
// Zamiast:
{"indicatorId": "dump-exhaustion-001", "operator": ">=", "value": 70.0}

// Użyj:
{"indicatorId": "dump-exhaustion-001", "operator": ">=", "value": 80.0}
```

**Inne dostrojenia:**
- Support proximity: 2.0% → 1.0%
- Velocity stabilization: 0.5 → 0.3

---

#### Scenariusz: Zbyt późne wyjście (give back profits)
**Problem:** Dump kończy się, ale pozycja wciąż otwarta.

**Rozwiązanie:** Złagodź progi exit
```json
// Zamiast:
{"indicatorId": "dump-exhaustion-001", "operator": ">=", "value": 70.0}

// Użyj:
{"indicatorId": "dump-exhaustion-001", "operator": ">=", "value": 60.0}
```

**Inne dostrojenia:**
- Support proximity: 2.0% → 3.0%
- Velocity stabilization: 0.5 → 0.7

---

### Dostrajanie parametrów czasowych

#### Window lengths (t1, t3, d)

**Szybsze monety (high volatility):**
```json
{
  "t1": 5.0,   // Zamiast 10.0
  "t3": 30.0,  // Zamiast 60.0
  "d": 5.0     // Zamiast 10.0
}
```

**Wolniejsze monety (low volatility):**
```json
{
  "t1": 20.0,  // Zamiast 10.0
  "t3": 120.0, // Zamiast 60.0
  "d": 20.0    // Zamiast 10.0
}
```

---

## Testowanie i optymalizacja

### 1. Backtesting na danych historycznych

**Krok 1:** Zbierz dane z poprzednich pump & dump
```bash
# Zakładając, że masz historical data
python scripts/backtest_strategy.py \
  --strategy short_selling_pump_dump_v1 \
  --symbol BTC_USDT \
  --start-date 2025-10-01 \
  --end-date 2025-10-25
```

**Metryki do śledzenia:**
- Win rate: >= 60%
- Average profit: 10-30% per trade
- Max drawdown: < 10%
- Sharpe ratio: > 1.5

---

### 2. Paper trading

**Krok 1:** Włącz strategię w trybie paper trading
```json
{
  "id": "short-selling-pump-dump-v1",
  "enabled": true,
  "paper_trading": true  // Dodaj tę flagę
}
```

**Krok 2:** Monitoruj przez 24-48h
- Sprawdź frequency of signals
- Obserwuj false positives
- Analizuj missed opportunities

---

### 3. Optimization loop

```
1. Uruchom backtest z parametrami domyślnymi
2. Zidentyfikuj weakness (np. late exits)
3. Dostosuj parametry (np. ZE1 thresholds)
4. Uruchom backtest ponownie
5. Porównaj metryki
6. Jeśli lepsza -> keep, inaczej -> revert
7. Powtarzaj aż Sharpe ratio > 2.0
```

---

## Zarządzanie ryzykiem

### Position Sizing

**Konserwatywny (recommended):**
```json
{"type": "percentage", "value": 1.0}  // 1% portfela
```

**Umiarkowany:**
```json
{"type": "percentage", "value": 2.0}  // 2% portfela
```

**Agresywny (ryzykowny):**
```json
{"type": "percentage", "value": 5.0}  // 5% portfela
```

**Zaawansowane - skalowanie oparte na magnitude:**
```json
{
  "type": "percentage",
  "value": 2.0,
  "riskScaling": {
    "enabled": true,
    "riskIndicatorId": "pump-magnitude-001",
    "lowRiskThreshold": 10.0,  // Pump < 10%
    "lowRiskScale": 1.0,       // -> 1% position
    "highRiskThreshold": 25.0, // Pump > 25%
    "highRiskScale": 3.0       // -> 3% position
  }
}
```

---

### Stop Loss Strategy

**Hard stop loss (nie zalecane dla pump & dump):**
- Pump & dump są zbyt volatile
- Hard SL często triggeruje się przedwcześnie

**Soft stop loss (zalecane):**
- Użyj MOMENTUM_REVERSAL_INDEX jako "soft SL"
- Emergency exit przy momentum > 50%
- Pozwala na naturalne fluktuacje

---

### Diversification

**Nie traduj jednej monety:**
- Aplikuj strategię na 5-10 low-cap coins jednocześnie
- Różne monety = różne pump patterns
- Spread risk across multiple positions

**Przykład alokacji:**
```
Portfolio: $10,000
Position size: 2% = $200
Max concurrent positions: 5
Max exposure: 10% = $1,000
```

---

## Typowe scenariusze

### Scenariusz 1: Perfect Pump & Dump

**Timeline:**
```
00:00 - Baseline (price: 100)
00:30 - S1 signal (price: 115, +15%)
00:31 - Z1 entry SHORT @ 115
00:35 - Peak (price: 130, +30%)
01:00 - Dump begins
01:05 - ZE1 exit @ 102 (near support)
Result: +11.3% profit (115 → 102)
```

**Wskaźniki:**
- S1: ✓ All 4 indicators triggered
- O1: Nie anulowane (momentum stabilny)
- ZE1: Support proximity < 2%
- Emergency: Nie triggered

---

### Scenariusz 2: False Start (Anulowanie)

**Timeline:**
```
00:00 - Baseline (price: 100)
00:30 - S1 signal (price: 112, +12%)
00:31 - Z1 entry SHORT @ 112
00:32 - Price continues up to 125
00:33 - O1 cancel (momentum < -20%)
Result: -11.6% loss (112 → 125)
```

**Wskaźniki:**
- S1: ✓ Triggered (false positive)
- O1: ✓ Anulowane (pump trwa)
- Emergency: Nie triggered

**Lesson:** O1 cancel system działa - ograniczył stratę

---

### Scenariusz 3: Emergency Exit

**Timeline:**
```
00:00 - Baseline (price: 100)
00:30 - S1 signal (price: 115)
00:31 - Z1 entry SHORT @ 115
00:35 - Dump do 105
00:37 - Nagłe odwrócenie (whale buy)
00:38 - Price skacze do 120
00:39 - Emergency exit @ 120
Result: -4.3% loss (115 → 120)
```

**Wskaźniki:**
- ZE1: Nie zdążyło trigger
- Emergency: ✓ Momentum > 50%

**Lesson:** Emergency exit chroni przed dużymi stratami

---

### Scenariusz 4: Optimal Exit

**Timeline:**
```
00:00 - Baseline (price: 100)
00:30 - S1 signal (price: 118)
00:31 - Z1 entry SHORT @ 118
01:00 - Dump exhaustion score = 72
01:01 - ZE1 exit @ 95
Result: +19.5% profit (118 → 95)
```

**Wskaźniki:**
- ZE1: ✓ Exhaustion >= 70
- Support proximity: 4% (nie triggered)
- Velocity stabilization: 0.8 (nie triggered)

**Lesson:** Jeden wskaźnik wystarczył (OR logic)

---

## Monitoring i Logging

### Kluczowe metryki do śledzenia

```json
{
  "daily_stats": {
    "signals_generated": 12,
    "positions_opened": 8,
    "positions_cancelled": 2,
    "positions_closed": 6,
    "emergency_exits": 1,
    "win_rate": 75.0,
    "avg_profit": 15.2,
    "max_drawdown": 4.8,
    "sharpe_ratio": 1.8
  }
}
```

---

### Alerty do ustawienia

1. **High win rate alert (> 80%):**
   - Może oznaczać, że progi są zbyt konserwatywne
   - Sprawdź czy nie tracisz opportunities

2. **Low win rate alert (< 50%):**
   - Progi mogą być zbyt agresywne
   - Zbyt wiele false positives

3. **High emergency exit rate (> 20%):**
   - Może oznaczać problemy z timing entry
   - Rozważ zaostrzenie S1

4. **Low signal frequency (< 5/day):**
   - Sprawdź czy system działa
   - Może złagodź progi S1

---

## FAQ

### Q: Dlaczego używacie TWPA zamiast raw prices?
**A:** TWPA (Time-Weighted Price Average) redukuje noise i daje stabilniejsze sygnały. Raw prices mogą mieć spike'i które prowadzą do false signals.

### Q: Czy mogę użyć AND logic w ZE1 zamiast OR?
**A:** Tak, ale zwiększa ryzyko late exit. AND wymaga wszystkich 3 warunków, co może opóźnić exit gdy dump się odwraca.

### Q: Jak często powinienem rebalansować parametry?
**A:** Co 2-4 tygodnie, lub gdy win rate spadnie poniżej 55%. Market conditions się zmieniają.

### Q: Czy strategia działa na wszystkich monetach?
**A:** Najlepsze rezultaty na low-cap, volatile coins. High-cap (BTC, ETH) mają mniej wyraźne pump & dump patterns.

### Q: Co jeśli dump trwa dłużej niż 10 minut?
**A:** Exit signals (ZE1) nie zależą od czasu, tylko od wskaźników. Jeśli dump trwa 20 min, pozycja będzie otwarta dopóki exhaustion >= 70.

---

## Changelog

### v1.0 (2025-10-26)
- Initial release
- 8 TWPA-based indicators
- 5-section strategy framework
- Multi-factor exit system

---

## Kontakt i wsparcie

**Autor:** Claude AI
**Wersja:** 1.0
**Data:** 2025-10-26

**Repository:** `FX_code_AI`
**Branch:** `claude/analyze-data-collection-011CUUKaSfAhFt14iHqyw5qi`
