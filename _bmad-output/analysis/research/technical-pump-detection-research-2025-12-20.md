---
title: "Technical Research: Pump Detection Algorithms & Strategies"
date: 2025-12-20
author: Mary (Business Analyst)
project: FX Agent AI
research_type: technical
status: completed
sources_verified: true
---

# Technical Research: Pump Detection Algorithms & Strategies

**Cel:** Walidacja Twoich pomysłów na detekcję pump oraz znalezienie praktycznych alternatyw opartych na aktualnych źródłach.

---

## Executive Summary

Twoje podejście oparte na **TWPA jako baseline**, **volume surge**, **price velocity** i **count_deals ratio** jest **solidne i zgodne z najlepszymi praktykami**. Badania wskazują jednak na kilka kluczowych usprawnień:

1. **EWMA z 20-dniowym oknem** działa lepiej niż proste średnie
2. **Count_deals (Trade Frequency)** jest **niedoceniany** w literaturze, ale Twój pomysł jest słuszny
3. **Order Book Imbalance** działa tylko w krótkich horyzontach (~10s)
4. **Multi-threshold approach** z walidacją volume + price jest optymalny

---

## Część 1: Walidacja Twoich Pomysłów

### 1.1 TWPA jako Baseline - POTWIERDZONE

**Twój pomysł:** Użycie TWPA (Time-Weighted Price Average) jako baseline do porównań.

**Walidacja:**
- TWAP/TWPA jest **standardem w algorytmicznym tradingu** dla redukcji wpływu manipulacji
- Oracles DeFi używają time-weighted averaging do **tłumienia ryzyka manipulacji** [[1]](https://coinmarketcap.com/academy/article/twap-vs-vwap)
- TWPA lepiej oddaje "fair value" niż spot price

**Rekomendacja:** ✅ **Zachowaj TWPA jako baseline**. Rozważ dodanie VTWPA (Volume-Time Weighted) dla transakcji z wysokim wolumenem.

### 1.2 Volume Surge Ratio - POTWIERDZONE z ulepszeniami

**Twój pomysł:** `current_volume / baseline_volume` z progiem ~3.5x

**Walidacja z badań:**
- Progi **300-500%** (3-5x) są standardem w detekcji pump [[2]](https://wundertrading.com/journal/en/learn/article/crypto-pump-detector)
- Najlepsze wyniki: **EWMA 20-dniowe + volatility adjustment** [[3]](https://arxiv.org/html/2503.08692v1)

**Optymalne formuły:**

```
# Podstawowa (Twoja)
Volume_Surge = sum_volume(t1,t2) / sum_volume(baseline_t1, baseline_t2)
Próg: > 3.5x

# Ulepszona (z badań)
V > 0.70 × EWMA_20d + 2 × σ_daily  AND  V > 0.60 × V_max
```

**Dodatkowe kryterium:** W pump event, **≥30% miesięcznego wolumenu** pojawia się w dniu pump, a spike musi osiągnąć **≥60% maksymalnego wolumenu** z 30 dni [[3]](https://arxiv.org/html/2503.08692v1).

### 1.3 Price Velocity - POTWIERDZONE

**Twój pomysł:** `velocity = (price_current - price_baseline) / price_baseline × 100`

**Walidacja:**
- **VAcc (Velocity & Acceleration)** indicator pokazuje, że velocity + acceleration razem dają lepsze sygnały niż MACD [[4]](https://www.tradingview.com/script/J0JW9FCX-VAcc-Velocity-Acceleration/)
- "Strong Up" = velocity > threshold AND acceleration > 0
- "Strong Down" = velocity < threshold AND acceleration < 0

**Optymalne progi z badań:**

| Warunek | Threshold |
|---------|-----------|
| Significant velocity | 5% |
| Major velocity | 10% |
| Pump velocity | 20% |
| Price increase (with 400% volume) | 90% |

**Rekomendacja:** ✅ **Velocity Cascade** (multi-timeframe) jest lepszy niż single velocity.

### 1.4 Count_Deals / Trade Frequency Spike - WALIDACJA TWOJEGO POMYSŁU

**Twój pomysł:** `count_deals(current) / count_deals(baseline)` jako wczesny sygnał.

**Analiza:**
To jest **niedoceniony wskaźnik** w literaturze! Większość badań skupia się na volume, ale:

- **Trade Frequency Spike** może być **wcześniejszym sygnałem** niż volume spike
- Bot-driven pumps generują **wiele małych transakcji** przed dużymi
- Wysoki count_deals przy niskim volume = **boty akumulują**
- Wysoki count_deals przy wysokim volume = **pump w toku**

**Proponowana implementacja:**

```python
Trade_Frequency_Spike = count_deals(t1,t2) / (count_deals(baseline_t1, baseline_t2) * time_ratio)
Próg: > 3.0x (sugerowany)

# Kombinacja z volume
Trade_Size_Ratio = avg_volume_per_deal(current) / avg_volume_per_deal(baseline)

# Interpretacja:
# High Frequency + Low Size = early accumulation (bots)
# High Frequency + High Size = pump in progress
```

**Rekomendacja:** ✅ **ZAIMPLEMENTUJ** - to może być Twoja **przewaga konkurencyjna**.

---

## Część 2: Alternatywne Podejścia

### 2.1 Order Flow Imbalance

**Formuła:**

```
ρ = (V_bid - V_ask) / (V_bid + V_ask)
```

**Gdzie:**
- ρ ≈ +1 = dominacja kupujących (bullish)
- ρ ≈ -1 = dominacja sprzedających (bearish)
- ρ ≈ 0 = równowaga

**Wyniki z badań crypto (ETHUSD):**
- **Korelacja z ceną jest niska** w crypto vs tradycyjne rynki [[5]](https://towardsdatascience.com/price-impact-of-order-book-imbalance-in-cryptocurrency-markets-bf39695246f6/)
- Maksymalna predykcja: **~10 sekund** do przodu
- Hit ratio: **~53-54%** (marginalnie lepszy niż random)

**Praktyczne progi:**

| Regime | ρ Range | Interpretacja |
|--------|---------|---------------|
| Strong Sell | -1 to -0.6 | ~52% prob spadku |
| Weak Sell | -0.6 to -0.2 | Lekka presja sprzedaży |
| Neutral | -0.2 to 0.2 | Równowaga |
| Weak Buy | 0.2 to 0.6 | Lekka presja kupna |
| Strong Buy | 0.6 to 1 | ~54% prob wzrostu |

**Rekomendacja:** ⚠️ **Używaj jako potwierdzenie**, nie jako główny sygnał. Order book imbalance sam nie wystarcza do profitable strategy w crypto (fees > returns).

### 2.2 Liquidity Drain Index

**Twój istniejący wskaźnik** jest świetny! Z badań:

- **Thin liquidity** pozwala małym kwotom znacząco wpływać na cenę [[6]](https://www.altrady.com/crypto-trading/onchain-blockchain-analytics-for-traders/how-to-spot-crypto-pump-and-dump-schemes-blockchain-analysis)
- Nagłe **transfery dużych ilości** do exchange = pre-dump signal
- **Tokeny < $100k daily volume** są najbardziej podatne na manipulację

**Ulepszenie:**

```python
Liquidity_Drain_Alert = (
    (Total_Liquidity(baseline) - Total_Liquidity(current)) / Total_Liquidity(baseline)
    > 0.30  # 30% drain = warning
    AND
    Volume_Surge > 2.0x
)
```

### 2.3 Machine Learning Approach (opcjonalnie)

**Najlepszy model z badań:**
- **Random Forest** z danymi w **30-sekundowych chunkach**
- Moving window: **1 godzina**
- Może flagować pump **60 minut przed** szczytem [[7]](https://arxiv.org/html/2412.18848v1)

**Features do ML:**
1. Volume surge ratio
2. Price velocity
3. Trade frequency
4. Order book imbalance
5. Spread changes
6. Liquidity metrics

**Rekomendacja:** 💡 Rozważ ML jako **second-stage filter** po rule-based detection.

---

## Część 3: Optymalne Progi i Parametry

### 3.1 Wykrywanie Pump - Combined Thresholds

**Najlepsze kombinacje z badań:**

| Konfiguracja | Price Threshold | Volume Threshold | Skuteczność |
|--------------|-----------------|------------------|-------------|
| **Recommended** | +90% (vs 12h MA) | 400% surge | F1: 0.71, Precision: 0.84 |
| Conservative | +70% | 300% | Lower FP, lower recall |
| Aggressive | +100% | 400% | Higher recall, more FP |

### 3.2 Twoje Progi (z brainstorming session) - WALIDACJA

| Wskaźnik | Twój Próg | Walidacja |
|----------|-----------|-----------|
| pump_magnitude | ≥ 7% | ✅ Dobry dla wczesnej detekcji, 10%+ dla potwierdzenia |
| volume_surge | ≥ 3.5x | ✅ Zgodne z literaturą (300-500%) |
| spread_pct | ≤ 1.0% | ✅ Rozsądne dla płynności |
| unrealized_pnl | ≥ 15% | ✅ Agresywny, ale sensowny TP |

### 3.3 Time Windows - Rekomendacje

```python
TIME_WINDOWS = {
    "ultra_short": [10, 30, 60],      # sekundy - micro signals
    "short": [60, 120, 300],          # 1-5 min - pump detection
    "medium": [600, 900, 1800],       # 10-30 min - confirmation
    "baseline": [3600, 7200, 14400],  # 1-4h - baseline calculation
    "ewma_optimal": 20 * 86400        # 20 days for EWMA
}
```

---

## Część 4: Rekomendacje Implementacyjne

### 4.1 Composite Pump Score (ulepszona wersja)

```python
def calculate_pump_score(
    velocity: float,           # price velocity %
    volume_surge: float,       # volume multiplier
    trade_freq_spike: float,   # YOUR NEW INDICATOR
    bid_ask_imbalance: float,  # -1 to +1
    liquidity_drain: float     # 0 to 1
) -> float:
    """
    Weighted composite pump detection score.
    Returns: 0-100 pump probability score
    """
    # Normalize all inputs to 0-1 range
    v_norm = min(1.0, velocity / 20.0)           # 20% = max
    vol_norm = min(1.0, (volume_surge - 1) / 4)  # 5x = max
    freq_norm = min(1.0, (trade_freq_spike - 1) / 4)  # NEW
    imb_norm = (bid_ask_imbalance + 1) / 2       # -1,+1 → 0,1
    liq_norm = liquidity_drain                    # already 0-1

    # Weights (sum = 1.0)
    weights = {
        'velocity': 0.25,
        'volume': 0.25,
        'trade_freq': 0.20,  # YOUR EDGE
        'imbalance': 0.15,
        'liquidity': 0.15
    }

    score = (
        v_norm * weights['velocity'] +
        vol_norm * weights['volume'] +
        freq_norm * weights['trade_freq'] +
        imb_norm * weights['imbalance'] +
        liq_norm * weights['liquidity']
    ) * 100

    return score

# Thresholds:
# score > 60: Pump likely
# score > 80: Strong pump signal
```

### 4.2 Early Warning System (Twój count_deals + inne)

```python
def early_pump_warning(
    trade_freq_spike: float,
    volume_surge: float,
    avg_trade_size_change: float
) -> str:
    """
    Early detection based on YOUR count_deals idea.
    """
    # Pattern 1: Bot accumulation (many small trades)
    if trade_freq_spike > 2.0 and avg_trade_size_change < 0.5:
        return "EARLY_WARNING: Bot accumulation detected"

    # Pattern 2: Whale entry (few large trades)
    if trade_freq_spike < 1.5 and avg_trade_size_change > 3.0:
        return "EARLY_WARNING: Large player entry"

    # Pattern 3: Pump starting (many trades + volume)
    if trade_freq_spike > 3.0 and volume_surge > 2.5:
        return "PUMP_STARTING: High frequency + volume"

    return "NORMAL"
```

### 4.3 Wskaźniki do Zaimplementowania (priorytet)

| Priorytet | Wskaźnik | Status | Uzasadnienie |
|-----------|----------|--------|--------------|
| P0 | Trade_Frequency_Spike | ⚡ NEW | Twoja przewaga konkurencyjna |
| P0 | Decision_Density_Acceleration | ⚡ NEW | Tempo decyzji = panika/FOMO |
| P1 | EWMA_Volume_Baseline | 🔄 Upgrade | Lepsza od prostej średniej |
| P1 | Composite_Pump_Score | ⚡ NEW | Agregacja wszystkich sygnałów |
| P2 | Smart_Money_Flow | ⚡ NEW | Large trades vs small trades |

---

## Część 5: Wnioski

### Co Twoje Podejście Robi Dobrze ✅

1. **TWPA jako baseline** - industry standard
2. **Volume surge 3.5x** - zgodne z badaniami
3. **Multi-indicator approach** - composite lepszy niż single
4. **State machine architecture** - pozwala na sekwencyjną walidację
5. **Liquidity drain tracking** - wczesne ostrzeżenie

### Co Warto Dodać 💡

1. **Trade Frequency Spike** - Twój pomysł z count_deals jest ŚWIETNY
2. **EWMA 20-dniowe** zamiast prostych średnich dla baseline
3. **Volatility adjustment** do thresholds
4. **Time-decay confidence** - pewność maleje z czasem

### Czego Unikać ⚠️

1. **Order book imbalance jako główny sygnał** - zbyt niski hit ratio w crypto
2. **Single threshold** - zawsze używaj kombinacji
3. **Ignorowanie fees** - 10bps+ może zjeść zyski z micro-signals

---

## Sources

1. [TWAP vs VWAP in Crypto Trading - CoinMarketCap](https://coinmarketcap.com/academy/article/twap-vs-vwap)
2. [What Is a Crypto Pump Detector - WunderTrading](https://wundertrading.com/journal/en/learn/article/crypto-pump-detector)
3. [Detecting Crypto Pump-and-Dump Schemes: Thresholding Approach - arXiv 2025](https://arxiv.org/html/2503.08692v1)
4. [VAcc (Velocity & Acceleration) Indicator - TradingView](https://www.tradingview.com/script/J0JW9FCX-VAcc-Velocity-Acceleration/)
5. [Price Impact of Order Book Imbalance in Cryptocurrency Markets - Towards Data Science](https://towardsdatascience.com/price-impact-of-order-book-imbalance-in-cryptocurrency-markets-bf39695246f6/)
6. [How to Spot Crypto Pump & Dump Schemes - Altrady](https://www.altrady.com/crypto-trading/onchain-blockchain-analytics-for-traders/how-to-spot-crypto-pump-and-dump-schemes-blockchain-analysis)
7. [Machine Learning-Based Detection of Pump-and-Dump Schemes - arXiv 2024](https://arxiv.org/html/2412.18848v1)
8. [Order Flow Imbalance - High Frequency Trading Signal](https://dm13450.github.io/2022/02/02/Order-Flow-Imbalance.html)
9. [Velocity and Acceleration Signals Indicator - TradingView](https://www.tradingview.com/script/CUuh28js-Velocity-and-Acceleration-Signals/)
10. [Pump Detection Bots - WunderTrading](https://wundertrading.com/journal/en/learn/article/pump-detection-bots)
11. [Common Market Manipulation Typologies - TRM Labs](https://www.trmlabs.com/resources/blog/common-market-manipulation-typologies-in-crypto-and-how-to-spot-them)
12. [Chainalysis: Crypto Market Manipulation 2025](https://www.chainalysis.com/blog/crypto-market-manipulation-wash-trading-pump-and-dump-2025/)

---

*Research conducted: 2025-12-20*
*Facilitator: Mary (Business Analyst)*
*Project: FX Agent AI*
