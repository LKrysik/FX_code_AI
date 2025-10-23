# Miary Pump & Dump - Szczegółowa Specyfikacja z Parametrami

## GRUPA A: MIARY FUNDAMENTALNE

### A1. Agregatory Cenowe dla Deals

#### max_price(t1, t2)
**Opis**: Maksymalna cena transakcji w oknie czasowym
**Wzór**: `MAX(price WHERE timestamp ∈ [t1, t2])`
**Parametry**:
- `t1` (timestamp): początek okna czasowego (sekundy wstecz od teraz)
- `t2` (timestamp): koniec okna czasowego (sekundy wstecz od teraz)
**Znaczenie**: t1 > t2 (np. t1=300, t2=0 oznacza "od 5 minut temu do teraz")
**Przykład**: `max_price(300, 0)` = najwyższa cena z ostatnich 5 minut

#### min_price(t1, t2)
**Opis**: Minimalna cena transakcji w oknie czasowym
**Wzór**: `MIN(price WHERE timestamp ∈ [t1, t2])`
**Parametry**: Identyczne jak max_price
**Przykład**: `min_price(600, 300)` = najniższa cena między 10 a 5 minut temu

#### first_price(t1, t2), last_price(t1, t2)
**Opis**: Pierwsza/ostatnia cena w oknie czasowym
**Wzór**: 
- `first_price = price WHERE timestamp = MIN(timestamp ∈ [t1, t2])`
- `last_price = price WHERE timestamp = MAX(timestamp ∈ [t1, t2])`
**Parametry**: Identyczne jak powyżej

### A2. Agregatory Wolumenowe dla Deals

#### sum_volume(t1, t2)
**Opis**: Suma wolumenu wszystkich transakcji w oknie
**Wzór**: `SUM(volume WHERE timestamp ∈ [t1, t2])`
**Parametry**:
- `t1, t2`: okno czasowe (jak wyżej)
**Przykład**: `sum_volume(60, 0)` = całkowity wolumen z ostatniej minuty

#### avg_volume(t1, t2)
**Opis**: Średni wolumen transakcji w oknie
**Wzór**: `SUM(volume) / COUNT(deals) WHERE timestamp ∈ [t1, t2]`
**Uwaga**: To średnia per transakcja, nie średnia w czasie

#### count_deals(t1, t2)
**Opis**: Liczba transakcji w oknie czasowym
**Wzór**: `COUNT(deals WHERE timestamp ∈ [t1, t2])`

### A3. Agregatory Order Book (Time-Weighted)

#### avg_best_bid(t1, t2)
**Opis**: Średnia wartość best_bid ważona czasem utrzymywania
**Wzór**: `Σ(best_bid_i × duration_i) / Σ(duration_i)`
**Parametry**:
- `t1, t2`: okno czasowe
- `duration_i`: czas utrzymywania poziomu `best_bid_i`
**Kalkulacja duration**:
```
duration_i = min(timestamp_{i+1}, current_time - t2) - max(timestamp_i, current_time - t1)
```
**Znaczenie**: Długo utrzymywane poziomy mają większą wagę

#### avg_best_ask(t1, t2), avg_bid_qty(t1, t2), avg_ask_qty(t1, t2)
**Opis**: Analogiczne time-weighted averages dla ask, bid_qty, ask_qty
**Parametry**: Identyczne jak avg_best_bid

### A4. Time-Weighted Averages (KLUCZOWE)

#### TWPA(t1, t2) - Time-Weighted Price Average
**Opis**: Średnia cena ważona czasem trwania każdej ceny
**Wzór**: `Σ(price_i × duration_i) / Σ(duration_i)`
**Parametry**:
- `t1, t2`: okno czasowe
- Automatyczna kalkulacja duration z timestampów deals
**Kalkulacja**:
```
Dla każdej transakcji i w oknie [t1, t2]:
duration_i = min(timestamp_{i+1}, current_time - t2) - max(timestamp_i, current_time - t1)
weight_i = duration_i
TWPA = Σ(price_i × weight_i) / Σ(weight_i)
```
**Znaczenie**: Ceny utrzymywane dłużej mają większy wpływ na średnią

### MAX_TWPA (t1, t2, miara typu TWPA)
Maksymalna wartośc wyliczeń wskazanej miary TWPA
Wyliczenie dzieje sie co jakiś czas więc musi być przechowywane wartości TWPA a następnie liczona wartośc MAX
Jako parametr jest podawana miara typu TWPA, użytkownik tworzy miare TWPA nazywa my_measure 
i następnie tworzy miar my_max_twpa = MAX_TWPA(10 min, 5 min, my_measure)
Tak samo średnią, oraz tak samo dla innych miar

### MIN_TWPA itd itd 

#### VTWPA(t1, t2) - Volume-Time Weighted Price Average
**Opis**: Średnia cena ważona wolumenem I czasem
**Wzór**: `Σ(price_i × volume_i × duration_i) / Σ(volume_i × duration_i)`
**Parametry**:
- `t1, t2`: okno czasowe
- Wymaga poprzedniego obliczenia duration (jak w TWPA)
**Znaczenie**: Duże transakcje utrzymywane długo mają ogromną wagę

#### TW_MidPrice(t1, t2) - Time-Weighted Mid Price
**Opis**: Średnia cena mid-point z order book ważona czasem
**Wzór**: `Σ(midprice_i × duration_i) / Σ(duration_i)`
**Parametry**:
- `t1, t2`: okno czasowe
- `midprice_i = (best_bid_i + best_ask_i) / 2`
**Zależności**: Wymaga avg_best_bid(t1,t2) i avg_best_ask(t1,t2)

## GRUPA B: MIARY VELOCITY I MOMENTUM

### B1. Price Velocity (Konfigurowalny)

#### Velocity(current_window, baseline_window, price_method)
**Opis**: Prędkość zmiany ceny między dwoma oknami czasowymi
**Wzór**: `(price_method(current_window) - price_method(baseline_window)) / price_method(baseline_window) × 100`
**Parametry**:
- `current_window`: tuple (t1, t2) dla obecnej ceny
- `baseline_window`: tuple (t1, t2) dla ceny bazowej
- `price_method`: funkcja do obliczenia ceny ("last_price", "TWPA", "VTWPA", "TW_MidPrice")

**Przykłady konfiguracji**:
```python
# Velocity obecnej ceny vs średnia z ostatniej minuty
SimpleVelocity_1min = Velocity((0,0), (60,0), "last_price")

# Velocity TWPA vs TWPA z 5min do 1min wstecz
TWPA_Velocity_5min = Velocity((0,0), (300,60), "TWPA")

# Velocity VTWPA vs baseline
VTWPA_Velocity_15min = Velocity((0,0), (900,0), "VTWPA")
```

**Zależności**: 
- Dla price_method="TWPA" wymaga TWPA(t1,t2)
- Dla price_method="VTWPA" wymaga VTWPA(t1,t2)
- Dla price_method="TW_MidPrice" wymaga TW_MidPrice(t1,t2)

### B2. Multi-Timeframe Velocity Cascade

#### Velocity_Cascade
**Opis**: Zestaw velocity dla różnych okien czasowych
**Parametry**:
- `timeframes`: lista okien czasowych [30, 60, 120, 300, 600, 900] sekund
- `price_method`: metoda obliczenia ceny (domyślnie "TWPA")
**Kalkulacja**:
```python
V_cascade = []
for t in timeframes:
    V_t = Velocity((0,0), (t,0), price_method)
    V_cascade.append(V_t)
```
**Wynik**: Lista [V_30s, V_1min, V_2min, V_5min, V_10min, V_15min]

#### Velocity_Acceleration
**Opis**: Różnica między krótko- i długoterminowym velocity
**Wzór**: `V_short - V_long`
**Parametry**:
- `short_window`: krótkie okno (np. 60s)
- `long_window`: długie okno (np. 300s)
- `price_method`: metoda obliczenia ceny
**Przykład**: `VA_5min_vs_1min = Velocity((0,0), (60,0), "TWPA") - Velocity((0,0), (300,0), "TWPA")`
**Interpretacja**: Dodatnie = przyspieszenie, ujemne = zwolnienie

`VA_5min_vs_1min = Velocity((0,0), (t1,t2), "TWPA") - Velocity((0,0), (t2,t2), "TWPA")`

Parametry czasowe: t1, t2, t3, t4


### B3. Momentum Persistence

#### Momentum_Streak
**Opis**: Liczba kolejnych okresów z tym samym kierunkiem velocity
**Parametry**:
- `period_length`: długość pojedynczego okresu (np. 60s)
- `lookback_periods`: ile okresów analizować wstecz (np. 10)
- `price_method`: metoda velocity
**Kalkulacja**:
```python
velocities = []
for i in range(lookback_periods):
    start_time = i * period_length
    end_time = (i + 1) * period_length
    v = Velocity((start_time, start_time), (end_time, start_time), price_method)
    velocities.append(v)

# Zlicz kolejne okresy z tym samym kierunkiem (+ lub -)
```

#### Direction_Consistency
**Opis**: Odsetek okresów z tym samym kierunkiem ruchu
**Wzór**: `COUNT(same_direction_moves) / total_periods`
**Parametry**: Identyczne jak Momentum_Streak
**Zakres**: 0.0 (chaos) do 1.0 (pełna konsystencja)

## GRUPA C: MIARY WOLUMENOWE I AKTYWNOŚCI

### C1. Volume Dynamics

#### Volume_Surge(t1, t2, baseline_t1, baseline_t2)
**Opis**: Stosunek wolumenu obecnego do bazowego
**Wzór**: `sum_volume(t1,t2) / sum_volume(baseline_t1,baseline_t2)`
**Parametry**:
- `t1, t2`: okno obecne
- `baseline_t1, baseline_t2`: okno bazowe
**Przykład**: `Volume_Surge(0, 300, 300, 3600)` = ostatnie 5min vs poprzednia godzina
**Zależności**: Wymaga sum_volume(t1,t2)

#### Volume_Concentration
**Opis**: Koncentracja wolumenu w krótkim oknie vs długim
**Wzór**: `sum_volume(short_window) / sum_volume(long_window)`
**Parametry**:
- `short_window`: tuple (t1, t2) dla krótkiego okna
- `long_window`: tuple (t1, t2) dla długiego okna
**Przykład**: `VC_5min = sum_volume(0,300) / sum_volume(0,3600)`

#### Volume_Acceleration
**Opis**: Zmiana w volume surge między okresami
**Wzór**: `Volume_Surge(current) - Volume_Surge(previous)`
**Parametry**:
- `current_window`, `previous_window`: dwa okresy do porównania
- `baseline_window`: stały baseline dla obu okresów

### C2. Trade Activity Metrics

#### Trade_Frequency(t1, t2)
**Opis**: Częstotliwość transakcji
**Wzór**: `count_deals(t1,t2) / (t1-t2) * 60` [deals per minute]
**Parametry**:
- `t1, t2`: okno czasowe w sekundach
**Zależności**: Wymaga count_deals(t1,t2)

#### Average_Trade_Size(t1, t2)
**Opis**: Średni rozmiar transakcji w oknie
**Wzór**: `sum_volume(t1,t2) / count_deals(t1,t2)`
**Parametry**: `t1, t2` - okno czasowe
**Zależności**: Wymaga sum_volume(t1,t2) i count_deals(t1,t2)

#### Trade_Size_Momentum
**Opis**: Stosunek obecnego średniego rozmiaru do bazowego
**Wzór**: `ATS(current_window) / ATS(baseline_window)`
**Parametry**:
- `current_window`: okno obecne
- `baseline_window`: okno bazowe
**Zależności**: Wymaga Average_Trade_Size dla obu okien

### C3. Volume-Price Relationship

#### VWAP(t1, t2) - Volume Weighted Average Price
**Opis**: Klasyczna średnia ważona wolumenem (bez czasu)
**Wzór**: `Σ(price_i × volume_i) / Σ(volume_i)`
**Parametry**: `t1, t2` - okno czasowe
**Różnica od VTWPA**: Nie uwzględnia czasu trwania, tylko wolumen

#### Volume_Price_Correlation(t1, t2)
**Opis**: Korelacja między zmianami ceny a zmianami wolumenu
**Wzór**: `CORRELATION(price_changes[], volume_changes[])`
**Parametry**:
- `t1, t2`: okno czasowe
- `min_deals`: minimalna liczba transakcji do obliczenia (np. 10)
**Kalkulacja**:
```python
price_changes = [price_i - price_{i-1} for każdej transakcji]
volume_changes = [volume_i - avg_volume for każdej transakcji]
correlation = pearson_correlation(price_changes, volume_changes)
```
**Zakres**: -1.0 do +1.0

## GRUPA D: MIARY ORDER BOOK I MIKROSTRUKTURY

### D1. Bid-Ask Analysis

#### Bid_Ask_Imbalance(t1, t2)
**Opis**: Nierównowaga między ilością na bid vs ask
**Wzór**: `(avg_bid_qty(t1,t2) - avg_ask_qty(t1,t2)) / (avg_bid_qty(t1,t2) + avg_ask_qty(t1,t2))`
**Parametry**: `t1, t2` - okno czasowe
**Zależności**: Wymaga avg_bid_qty(t1,t2) i avg_ask_qty(t1,t2)
**Zakres**: -1.0 (dominacja ask/sprzedaży) do +1.0 (dominacja bid/kupna)

#### Mid_Price_Velocity
**Opis**: Velocity mid price z order book
**Wzór**: `(TW_MidPrice(0,0) - TW_MidPrice(t,0)) / TW_MidPrice(t,0) × 100`
**Parametry**:
- `t`: czas wstecz dla porównania (sekundy)
**Zależności**: Wymaga TW_MidPrice(t1,t2)

#### Spread_Percentage
**Opis**: Spread jako procent mid price
**Wzór**: `avg_spread(t1,t2) / TW_MidPrice(t1,t2) × 100`
**Parametry**: `t1, t2` - okno czasowe
**Zależności**: Wymaga avg_spread(t1,t2) i TW_MidPrice(t1,t2)

### D2. Liquidity Measures

#### Total_Liquidity(t1, t2)
**Opis**: Suma płynności po obu stronach order book
**Wzór**: `avg_bid_qty(t1,t2) + avg_ask_qty(t1,t2)`
**Parametry**: `t1, t2` - okno czasowe
**Zależności**: Wymaga avg_bid_qty i avg_ask_qty

#### Liquidity_Ratio
**Opis**: Stosunek obecnej płynności do bazowej
**Wzór**: `Total_Liquidity(current) / Total_Liquidity(baseline)`
**Parametry**:
- `current_window`: okno obecne
- `baseline_window`: okno bazowe
**Zależności**: Wymaga Total_Liquidity dla obu okien

#### Liquidity_Drain_Index
**Opis**: Spadek płynności względem baseline
**Wzór**: `(Total_Liquidity(baseline) - Total_Liquidity(current)) / Total_Liquidity(baseline)`
**Parametry**:
- `current_window`: okno obecne (np. (0, 300))
- `baseline_window`: okno bazowe (np. (300, 600))
**Zależności**: Wymaga Total_Liquidity
**Interpretacja**: 0.6 = 60% spadek płynności

### D3. Price-OrderBook Divergence

#### Deal_vs_Mid_Deviation
**Opis**: Odchylenie ceny transakcji od mid price order book
**Wzór**: `|TWPA(t1,t2) - TW_MidPrice(t1,t2)| / TW_MidPrice(t1,t2) × 100`
**Parametry**: `t1, t2` - okno czasowe
**Zależności**: Wymaga TWPA(t1,t2) i TW_MidPrice(t1,t2)
**Interpretacja**: Wysokie wartości = agresywne transakcje poza mid price

#### Spread_Volatility
**Opis**: Zmienność spread'u w oknie czasowym
**Wzór**: `STDEV(spread_values(t1,t2))`
**Parametry**:
- `t1, t2`: okno czasowe
- `min_samples`: minimalna liczba próbek (np. 5)
**Kalkulacja**: Odchylenie standardowe wszystkich wartości spread w oknie

## GRUPA E: MIARY TIMING I BEHAVIORAL

### E1. Decision Timing Analysis

#### Inter_Deal_Intervals
**Opis**: Lista czasów między kolejnymi transakcjami
**Wzór**: `[timestamp_{i+1} - timestamp_i for wszystkich deals w oknie]`
**Parametry**: `t1, t2` - okno czasowe
**Wynik**: Lista interwałów w sekundach

#### Decision_Density_Acceleration
**Opis**: Przyspieszenie tempa podejmowania decyzji
**Wzór**: `MEDIAN(intervals_baseline) / MEDIAN(intervals_current)`
**Parametry**:
- `current_window`: okno obecne
- `baseline_window`: okno bazowe
**Zależności**: Wymaga Inter_Deal_Intervals dla obu okien
**Interpretacja**: 5.0 = decyzje 5x szybsze niż baseline

#### Trade_Clustering_Coefficient
**Opis**: Miara grupowania transakcji w czasie
**Wzór**: `VARIANCE(intervals) / (MEAN(intervals))²`
**Parametry**:
- `t1, t2`: okno czasowe
- `min_deals`: minimalna liczba transakcji (np. 5)
**Zależności**: Wymaga Inter_Deal_Intervals
**Interpretacja**: Wysokie TCC = transakcje w klasterach (panika/FOMO)

### E2. Market Stress Indicators

#### Price_Volatility(t1, t2)
**Opis**: Zmienność zwrotów cenowych
**Wzór**: `STDEV([price_i - price_{i-1}] / price_{i-1}) × 100`
**Parametry**:
- `t1, t2`: okno czasowe
- `min_deals`: minimalna liczba transakcji
**Kalkulacja**: Odchylenie standardowe zwrotów procentowych

#### Deal_Size_Volatility(t1, t2)
**Opis**: Względna zmienność rozmiarów transakcji
**Wzór**: `STDEV(volume_values) / MEAN(volume_values)`
**Parametry**: `t1, t2` - okno czasowe
**Zakres**: 0.0 (stałe rozmiary) do >1.0 (bardzo zróżnicowane)

#### Market_Stress_Index
**Opis**: Kompozytowy wskaźnik stresu rynkowego
**Wzór**: `Price_Volatility × Deal_Size_Volatility × Spread_Volatility`
**Parametry**: `t1, t2` - okno czasowe
**Zależności**: Wymaga Price_Volatility, Deal_Size_Volatility, Spread_Volatility

## GRUPA F: MIARY COMPOSITE I SYGNAŁOWE

### F1. Pump Detection Composite

#### Pump_Strength_Score
**Opis**: Zagregowany wskaźnik siły pumpa
**Wzór**: `w1×norm(Velocity) + w2×norm(Volume_Surge) + w3×norm(Bid_Imbalance) + w4×norm(Decision_Density)`
**Parametry**:
- `velocity_window`: okno dla velocity (np. (0,0) vs (300,0))
- `volume_windows`: current i baseline dla volume surge
- `imbalance_window`: okno dla bid-ask imbalance
- `decision_windows`: current i baseline dla decision density
- `weights`: [w1, w2, w3, w4] domyślnie [0.3, 0.25, 0.25, 0.2]
**Zależności**: Wymaga Velocity, Volume_Surge, Bid_Ask_Imbalance, Decision_Density_Acceleration
**Normalizacja**: Wszystkie składniki normalizowane do [0,1] przed agregacją

### F2. Peak/Reversal Indicators

#### Momentum_Death_Index
**Opis**: Spadek momentum względem szczytu
**Wzór**: `(max_velocity_in_window - current_velocity) / max_velocity_in_window`
**Parametry**:
- `current_velocity_params`: parametry dla obecnego velocity
- `lookback_window`: okno szukania max velocity (np. 600s)
- `velocity_method`: metoda obliczenia velocity
**Zależności**: Wymaga Velocity i znajdowanie maksimum w oknie
**Interpretacja**: 0.8 = 80% spadek od szczytu momentum

#### Exhaustion_Score
**Opis**: Kompozytowy wskaźnik wyczerpania pumpa
**Wzór**: `Liquidity_Drain_Index × Momentum_Death_Index × Volume_Deceleration`
**Parametry**:
- `liquidity_windows`: current i baseline dla drain index
- `momentum_params`: parametry dla momentum death
- `volume_decel_params`: parametry dla volume deceleration
**Zależności**: Wymaga Liquidity_Drain_Index, Momentum_Death_Index, Volume_Deceleration
**Interpretacja**: Im wyższe, tym większe prawdopodobieństwo szczytu

### F3. Confidence Measures

#### Signal_Confidence
**Opis**: Pewność sygnału pump/dump
**Wzór**: `Consistency_Score × Magnitude_Score × Duration_Score`
**Parametry**:
- `consistency_params`: parametry dla Direction_Consistency
- `magnitude_threshold`: minimalny pump magnitude (np. 10%)
- `duration_threshold`: minimalny czas trwania sygnału (np. 120s)
**Składniki**:
```python
Consistency_Score = Direction_Consistency # z B3
Magnitude_Score = min(1.0, current_pump_magnitude / magnitude_threshold)
Duration_Score = min(1.0, signal_duration / duration_threshold)
```
**Zakres**: 0.0 do 1.0

## KONFIGURACJA PARAMETRÓW

### Domyślne Okna Czasowe
```json
{
  "ultra_short": [10, 30, 60],
  "short": [60, 120, 300],  
  "medium": [600, 900, 1800],
  "long": [3600, 7200, 14400],
  "baseline": [3600, 4500, 5400]
}
```

### Domyślne Progi
```json
{
  "velocity_significant": 5.0,
  "velocity_major": 10.0, 
  "velocity_pump": 20.0,
  "volume_surge": 3.0,
  "volume_spike": 5.0,
  "imbalance_strong": 0.6,
  "liquidity_drain_significant": 0.4,
  "confidence_minimum": 0.6
}
```

## GRUPA G: MIARY PREDYKCYJNE I RISK MANAGEMENT

### G1. Pump Peak Prediction

#### Velocity_Divergence_Index
**Opis**: Rozbieżność między krótko- i długoterminowym velocity jako sygnał zbliżającego się szczytu
**Wzór**: `abs(V_short - V_long) / max(abs(V_short), abs(V_long))`
**Parametry**:
- `short_window`: krótkie okno velocity (np. 60s)
- `long_window`: długie okno velocity (np. 600s)
- `price_method`: metoda obliczenia velocity
**Zależności**: Wymaga Velocity dla obu okien
**Interpretacja**: Wysokie wartości (>0.7) = możliwy szczyt

#### Price_Acceleration_Profile
**Opis**: Profil przyspieszenia ceny do wykrycia inflection point
**Wzór**: 
```
acceleration = velocity_current - velocity_previous
jerk = acceleration_current - acceleration_previous
```
**Parametry**:
- `time_step`: krok czasowy dla różniczkowania (np. 30s)
- `smoothing_window`: okno wygładzania (np. 3 kroki)
**Kalkulacja**:
```python
velocities = [Velocity(i*time_step, (i+1)*time_step) for i in range(10)]
accelerations = [velocities[i] - velocities[i-1] for i in range(1, len(velocities))]
jerk = [accelerations[i] - accelerations[i-1] for i in range(1, len(accelerations))]
```
**Sygnał szczytu**: Jerk < 0 (przyspieszenie maleje)

#### Maximum_Price_Estimator
**Opis**: Szacowanie maksymalnej ceny pumpa na podstawie momentum
**Wzór**: `current_price * (1 + estimated_remaining_potential)`
**Parametry**:
- `momentum_window`: okno analizy momentum (np. 300s)
- `historical_pump_ratios`: dane historyczne pump ratios
- `volatility_adjustment`: korekta na zmienność
**Składniki**:
```python
current_momentum = Velocity(0, 0, momentum_window, "VTWPA")
momentum_sustainability = 1 - Momentum_Death_Index
volume_support = Volume_Surge(current) / avg_historical_surge
estimated_remaining = momentum_sustainability * volume_support * historical_avg_pump_ratio
```

### G2. Dump Transition Detection

#### Pump_to_Dump_Transition_Score
**Opis**: Prawdopodobieństwo przejścia z pumpa do dumpa
**Wzór**: `w1×Liquidity_Drain + w2×Momentum_Death + w3×Volume_Exhaustion + w4×Order_Flow_Reversal`
**Parametry**:
- `liquidity_params`: okna dla Liquidity_Drain_Index
- `momentum_params`: okna dla Momentum_Death_Index  
- `volume_params`: okna dla Volume_Exhaustion
- `flow_params`: parametry dla Order_Flow_Reversal
- `weights`: [w1, w2, w3, w4] domyślnie [0.3, 0.25, 0.25, 0.2]
**Próg sygnału**: >0.7 = wysokie prawdopodobieństwo przejścia

#### Order_Flow_Reversal_Index
**Opis**: Wykrycie odwrócenia przepływu zleceń z kupna na sprzedaż
**Wzór**: `(Bid_Imbalance_baseline - Bid_Imbalance_current) / (1 + abs(Bid_Imbalance_baseline))`
**Parametry**:
- `current_window`: obecne okno (np. 60s)
- `baseline_window`: bazowe okno (np. 300s do 600s wstecz)
**Zależności**: Wymaga Bid_Ask_Imbalance
**Interpretacja**: >0.5 = znaczące odwrócenie flow

#### Volume_Exhaustion_Index
**Opis**: Wyczerpanie wolumenu kupującego
**Wzór**: `1 - (current_volume_surge / max_volume_surge_in_pump)`
**Parametry**:
- `current_surge_params`: parametry dla obecnego volume surge
- `pump_start_time`: czas rozpoczęcia pumpa (do znajdowania maksimum)
**Kalkulacja**:
```python
max_surge = max([Volume_Surge(t, t+60, baseline) for t in range(pump_start, current_time, 30)])
current_surge = Volume_Surge(0, 60, baseline)
exhaustion = 1 - (current_surge / max_surge)
```

### G3. Dump End Prediction

#### Support_Level_Proximity
**Opis**: Odległość od poziomu wsparcia technicznego
**Wzór**: `(current_price - support_level) / current_price`
**Parametry**:
- `support_lookback`: okres szukania wsparcia (np. 3600s)
- `support_touch_threshold`: próg uznania za wsparcie (np. 2%)
- `min_touches`: minimalna liczba dotknięć (np. 3)
**Kalkulacja**:
```python
# Znajdź lokalne minima w historical data
local_mins = find_local_minima(price_history, support_lookback)
# Grupuj podobne poziomy (w ramach threshold)
support_levels = cluster_price_levels(local_mins, support_touch_threshold)
# Wybierz najbliższy poziom poniżej current_price
nearest_support = max([level for level in support_levels if level < current_price])
```

#### Dump_Velocity_Deceleration
**Opis**: Spowolnienie velocity dumpa jako sygnał końca
**Wzór**: `(max_dump_velocity - current_dump_velocity) / max_dump_velocity`
**Parametry**:
- `dump_start_time`: czas rozpoczęcia dumpa
- `velocity_window`: okno obliczania velocity (np. 60s)
**Interpretacja**: >0.7 = znaczące spowolnienie dumpa

#### Minimum_Price_Estimator
**Opis**: Szacowanie minimalnej ceny dumpa
**Wzór**: `pump_peak * (1 - estimated_retracement_ratio)`
**Parametry**:
- `pump_peak_price`: szczyt pumpa
- `historical_retracement_data`: historyczne dane retracement
- `volume_factor`: korekta na wolumen
**Składniki**:
```python
base_retracement = median(historical_retracement_ratios)  # np. 0.6 (60%)
volume_intensity_factor = current_dump_volume / avg_dump_volume
adjusted_retracement = base_retracement * (1 + 0.2 * volume_intensity_factor)
estimated_minimum = pump_peak * (1 - adjusted_retracement)
```

### G4. Risk Management Measures

#### Optimal_Short_Entry_Price
**Opis**: Optymalna cena wejścia w pozycję short
**Wzór**: `current_price * (1 - safety_margin) * confidence_adjustment`
**Parametry**:
- `safety_margin`: margines bezpieczeństwa (np. 0.02 = 2%)
- `confidence_score`: wynik z Signal_Confidence
- `max_wait_time`: maksymalny czas oczekiwania na cenę (np. 120s)
**Kalkulacja**:
```python
base_entry = current_price * (1 - safety_margin)
confidence_adj = 0.5 + 0.5 * confidence_score  # 0.5-1.0 range
optimal_entry = base_entry * confidence_adj
```

#### Dynamic_Stop_Loss_Calculator
**Opis**: Dynamiczny stop loss uwzględniający zmienność i momentum
**Wzór**: `entry_price * (1 + base_stop + volatility_adjustment + momentum_adjustment)`
**Parametry**:
- `entry_price`: cena wejścia w short
- `base_stop`: bazowy stop loss % (np. 0.05 = 5%)
- `volatility_window`: okno obliczania zmienności (np. 3600s)
- `momentum_factor`: siła momentum (z Momentum_Death_Index)
**Składniki**:
```python
price_volatility = Price_Volatility(volatility_window)
volatility_adj = min(0.03, price_volatility * 0.5)  # max 3% dodatkowe
momentum_strength = 1 - Momentum_Death_Index
momentum_adj = momentum_strength * 0.02  # max 2% dodatkowe
dynamic_stop = entry_price * (1 + base_stop + volatility_adj + momentum_adj)
```

#### Adaptive_Take_Profit_Calculator
**Opis**: Adaptacyjny take profit na podstawie szacowanego retracement
**Wzór**: `entry_price * (1 - target_retracement * confidence_multiplier)`
**Parametry**:
- `entry_price`: cena wejścia w short
- `target_retracement`: docelowy retracement (np. 0.4 = 40%)
- `pump_magnitude`: wielkość pumpa przed wejściem
- `liquidity_factor`: korekta na płynność
**Składniki**:
```python
base_target = target_retracement
magnitude_bonus = min(0.2, pump_magnitude * 0.01)  # większy pump = większy target
liquidity_penalty = max(0, (0.3 - current_liquidity_ratio) * 0.5)
adjusted_retracement = base_target + magnitude_bonus - liquidity_penalty
take_profit = entry_price * (1 - adjusted_retracement)
```

### G5. Confidence and Risk Scoring

#### Multi_Timeframe_Confidence
**Opis**: Pewność sygnału na różnych skalach czasowych
**Wzór**: `weighted_average([confidence_1min, confidence_5min, confidence_15min])`
**Parametry**:
- `timeframes`: lista okien czasowych [60, 300, 900]
- `weights`: wagi dla każdego timeframe [0.5, 0.3, 0.2]
**Kalkulacja**:
```python
confidences = []
for tf in timeframes:
    pump_score = Pump_Strength_Score(tf_specific_params)
    signal_conf = Signal_Confidence(tf_specific_params)
    tf_confidence = (pump_score + signal_conf) / 2
    confidences.append(tf_confidence)
multi_tf_conf = weighted_average(confidences, weights)
```

#### Risk_Reward_Ratio_Estimator
**Opis**: Szacowany stosunek ryzyka do zysku dla short pozycji
**Wzór**: `expected_profit / maximum_loss`
**Parametry**:
- `entry_price`: planowana cena wejścia
- `stop_loss`: poziom stop loss
- `take_profit`: poziom take profit
- `success_probability`: prawdopodobieństwo sukcesu
**Kalkulacja**:
```python
max_loss = stop_loss - entry_price
expected_profit = (entry_price - take_profit) * success_probability
risk_reward = expected_profit / max_loss if max_loss > 0 else 0
```

#### Position_Size_Optimizer
**Opis**: Optymalna wielkość pozycji na podstawie Kelly Criterion
**Wzór**: `account_balance * kelly_fraction * safety_factor`
**Parametry**:
- `account_balance`: saldo konta
- `win_probability`: prawdopodobieństwo wygranej (z confidence measures)
- `avg_win_ratio`: średni zysk jako % ceny wejścia
- `avg_loss_ratio`: średnia strata jako % ceny wejścia
- `safety_factor`: czynnik bezpieczeństwa (np. 0.25)
**Kalkulacja Kelly**:
```python
kelly_fraction = (win_prob * avg_win_ratio - (1 - win_prob) * avg_loss_ratio) / avg_win_ratio
safe_kelly = kelly_fraction * safety_factor
optimal_size = account_balance * max(0.01, min(0.1, safe_kelly))  # 1-10% cap
```

### G6. Market Regime Context

#### Market_Regime_Classifier
**Opis**: Klasyfikacja reżimu rynkowego wpływającego na pump behavior
**Wzór**: Composite classifier based on multiple indicators
**Parametry**:
- `btc_correlation_window`: okno korelacji z BTC (jeśli dostępne)
- `overall_market_velocity`: velocity rynku ogółem
- `volume_regime_threshold`: próg dla high/low volume regime
**Klasyfikacja**:
```python
# High Volatility Bull: pumpy silniejsze, dłuższe
# High Volatility Bear: pumpy słabsze, krótsze  
# Low Volatility: pumpy bardziej predictable
# Sideways: pumpy isolated, większe różnice
```

#### Pump_Sustainability_Score
**Opis**: Prawdopodobieństwo że pump będzie trwał dłużej
**Wzór**: `volume_quality * momentum_consistency * market_support`
**Parametry**:
- `volume_quality_params`: parametry oceny jakości wolumenu
- `momentum_window`: okno analizy momentum consistency
- `market_support_indicators`: wskaźniki wsparcia rynkowego
**Składniki**:
```python
volume_quality = VTWPA_weight / simple_volume_weight  # jakość vs ilość
momentum_consistency = Direction_Consistency(short_windows)
market_support = (1 + Market_Regime_Multiplier) / 2
sustainability = volume_quality * momentum_consistency * market_support
```

## EXTENDED CONFIGURATION

### Risk Management Parameters
```json
{
  "stop_loss": {
    "base_percentage": 0.05,
    "max_volatility_adjustment": 0.03,
    "max_momentum_adjustment": 0.02
  },
  "take_profit": {
    "base_retracement": 0.4,
    "magnitude_bonus_factor": 0.01,
    "liquidity_penalty_factor": 0.5
  },
  "position_sizing": {
    "kelly_safety_factor": 0.25,
    "min_position_pct": 0.01,
    "max_position_pct": 0.1
  }
}
```

### Prediction Thresholds
```json
{
  "pump_peak_signals": {
    "velocity_divergence_threshold": 0.7,
    "jerk_negative_threshold": -0.1,
    "transition_score_threshold": 0.7
  },
  "dump_end_signals": {
    "deceleration_threshold": 0.7,
    "support_proximity_threshold": 0.02,
    "exhaustion_threshold": 0.8
  }
}
```

## GRUPA H: ZAAWANSOWANE MIARY PREDYKCYJNE

### H1. Pattern Recognition Predictors

#### Wave_Pattern_Analyzer
**Opis**: Rozpoznawanie wzorców falowych w strukturze ceny do predykcji kontynuacji/odwrócenia
**Wzór**: Analiza sekwencji lokalnych maksimów i minimów
**Parametry**:
- `wave_detection_window`: okno detekcji fal (np. 300s)
- `min_wave_magnitude`: minimalna wielkość fali (np. 2%)
- `fibonacci_levels`: poziomy Fibonacciego [0.236, 0.382, 0.618, 0.786]
**Kalkulacja**:
```python
# Znajdź lokalne ekstrema
peaks = find_local_maxima(price_history, wave_detection_window)
troughs = find_local_minima(price_history, wave_detection_window)

# Analizuj wzorzec 5-falowy (Elliott Wave-like)
if len(peaks) >= 3 and len(troughs) >= 2:
    wave_ratios = calculate_wave_ratios(peaks, troughs)
    fibonacci_alignment = check_fibonacci_levels(wave_ratios)
    pattern_strength = fibonacci_alignment * wave_consistency
```

#### Price_Channel_Breakout_Predictor
**Opis**: Predykcja breakout na podstawie zawężania się kanału cenowego
**Wzór**: `channel_width_current / channel_width_baseline`
**Parametry**:
- `channel_period`: okres formowania kanału (np. 600s)
- `breakout_threshold`: próg breakout (np. 0.3 = 70% zawężenie)
- `volume_confirmation_required`: czy wymagać potwierdzenia wolumenem
**Składniki**:
```python
upper_envelope = max_price(rolling_windows)
lower_envelope = min_price(rolling_windows)
channel_width = (upper_envelope - lower_envelope) / lower_envelope
width_compression = 1 - (channel_width_current / channel_width_baseline)
breakout_probability = width_compression * volume_buildup_factor
```

#### Support_Resistance_Strength_Index
**Opis**: Siła poziomów wsparcia/oporu jako predyktor odbicia lub przebicia
**Wzór**: `touch_count * volume_at_level * time_since_formation`
**Parametry**:
- `sr_detection_tolerance`: tolerancja poziomu (np. 1%)
- `min_touches`: minimalna liczba dotknięć (np. 3)
- `volume_weight_factor`: waga wolumenu przy poziomie
- `time_decay_factor`: spadek siły w czasie
**Kalkulacja**:
```python
# Dla każdego poziomu S/R
level_strength = 0
for touch in level_touches:
    volume_at_touch = get_volume_at_price_level(touch.price, touch.time)
    time_factor = exp(-time_decay_factor * (current_time - touch.time))
    level_strength += volume_at_touch * time_factor

resistance_strength = level_strength / avg_historical_strength
```

### H2. Momentum Predictors

#### Momentum_Oscillator_Divergence
**Opis**: Dywergencja między ceną a momentum do predykcji odwrócenia
**Wzór**: `correlation(price_highs, momentum_highs)` dla bullish divergence
**Parametry**:
- `oscillator_period`: okres oscylatora momentum (np. 300s)
- `divergence_lookback`: okres szukania dywergencji (np. 900s)
- `min_correlation_threshold`: próg istotnej dywergencji (np. -0.3)
**Składniki**:
```python
# Momentum oscillator podobny do RSI
momentum_values = []
for window in rolling_windows:
    up_moves = sum([max(0, price_i - price_i-1) for price changes])
    down_moves = sum([max(0, price_i-1 - price_i) for price changes])
    momentum = 100 - (100 / (1 + up_moves/down_moves))
    momentum_values.append(momentum)

# Szukaj dywergencji
price_peaks = find_peaks(price_history)
momentum_peaks = find_peaks(momentum_values)
divergence = correlation(price_peaks, momentum_peaks)
```

#### Velocity_Momentum_Cascade
**Opis**: Analiza cascade momentum na wielu poziomach do predykcji siły trendu
**Wzór**: `weighted_sum([momentum_1min, momentum_5min, momentum_15min])`
**Parametry**:
- `cascade_timeframes`: [60, 300, 900, 1800] sekund
- `momentum_weights`: wagi dla każdego timeframe [0.4, 0.3, 0.2, 0.1]
- `alignment_threshold`: próg zgodności kierunku (np. 0.8)
**Kalkulacja**:
```python
momentum_cascade = []
for tf in cascade_timeframes:
    velocity = Velocity((0,0), (tf,0), "VTWPA")
    acceleration = Price_Acceleration_Profile(tf/2)
    momentum_score = velocity * (1 + acceleration)
    momentum_cascade.append(momentum_score)

cascade_alignment = count_same_direction(momentum_cascade) / len(momentum_cascade)
cascade_strength = weighted_average(momentum_cascade, momentum_weights)
```

#### Momentum_Persistence_Forecast
**Opis**: Przewidywanie jak długo obecne momentum może się utrzymać
**Wzór**: `base_duration * momentum_strength * volume_sustainability`
**Parametry**:
- `historical_momentum_durations`: dane historyczne o trwałości momentum
- `momentum_decay_factor`: współczynnik zaniku momentum
- `volume_sustainability_window`: okno analizy trwałości wolumenu
**Składniki**:
```python
current_momentum = Velocity_Momentum_Cascade
historical_avg_duration = median(historical_momentum_durations)
momentum_strength_factor = min(2.0, current_momentum / avg_historical_momentum)
volume_trend = Volume_Concentration(short_window) / Volume_Concentration(long_window)
estimated_duration = historical_avg_duration * momentum_strength_factor * volume_trend
```

### H3. Volume-Based Predictors

#### Volume_Distribution_Analyzer
**Opis**: Analiza rozkładu wolumenu w różnych poziomach cen do predykcji wsparcia/oporu
**Wzór**: `volume_at_price_level / total_volume_in_range`
**Parametry**:
- `price_bucket_size`: wielkość przedziału cenowego (np. 0.5%)
- `volume_analysis_period`: okres analizy (np. 3600s)
- `significance_threshold`: próg istotności poziomu (np. 5% wolumenu)
**Kalkulacja**:
```python
# Pogrupuj transakcje według poziomów cen
price_buckets = create_price_buckets(price_bucket_size)
for deal in deals_in_period:
    bucket = find_bucket(deal.price, price_buckets)
    bucket.volume += deal.volume

# Znajdź poziomy z wysoką koncentracją wolumenu
high_volume_levels = [bucket for bucket in price_buckets 
                     if bucket.volume / total_volume > significance_threshold]
```

#### Smart_Money_Flow_Tracker
**Opis**: Śledzenie przepływu "inteligentnych" pieniędzy do predykcji kierunku
**Wzór**: `large_trades_direction_bias * patience_factor * timing_quality`
**Parametry**:
- `large_trade_threshold`: próg dużej transakcji (percentyl, np. 90)
- `patience_measurement_window`: okno pomiaru cierpliwości (np. 300s)
- `timing_quality_factors`: czynniki jakości timing'u
**Składniki**:
```python
large_trades = [deal for deal in deals if deal.volume > large_trade_threshold]

# Kierunkowy bias dużych transakcji
direction_bias = 0
for trade in large_trades:
    if trade.price > TWPA(before_trade):
        direction_bias += trade.volume  # aggressive buy
    else:
        direction_bias -= trade.volume  # aggressive sell

# Cierpliwość = mniejsza częstotliwość transakcji
patience_score = 1 / Trade_Frequency(large_trades_only)

# Jakość timing'u = czy duże transakcje przed ruchem ceny
timing_quality = correlation(large_trade_times, subsequent_price_moves)
```

#### Volume_Acceleration_Predictor
**Opis**: Predykcja przyspieszenia/zwolnienia na podstawie trendu wolumenu
**Wzór**: `volume_trend_slope * volume_momentum * seasonal_adjustment`
**Parametry**:
- `trend_analysis_windows`: [60, 300, 900] sekund
- `momentum_calculation_method`: metoda obliczania momentum wolumenu
- `seasonal_patterns`: wzorce sezonowe (jeśli dostępne)
**Kalkulacja**:
```python
# Trend wolumenu na różnych skalach
volume_trends = []
for window in trend_analysis_windows:
    recent_volume = sum_volume(0, window/2)
    older_volume = sum_volume(window/2, window)
    trend = (recent_volume - older_volume) / older_volume
    volume_trends.append(trend)

# Momentum wolumenu
volume_acceleration = volume_trends[0] - volume_trends[-1]
prediction_strength = abs(volume_acceleration) * trend_consistency
```

### H4. Microstructure Predictors

#### Order_Book_Depth_Gradient
**Opis**: Gradient głębokości order book jako predyktor kierunku przebicia
**Wzór**: `(deep_bid_levels - deep_ask_levels) / (surface_bid_levels - surface_ask_levels)`
**Parametry**:
- `surface_depth_levels`: poziomy powierzchniowe (np. 1% od mid)
- `deep_depth_levels`: poziomy głębokie (np. 5% od mid)
- `gradient_interpretation_threshold`: próg interpretacji (np. 2.0)
**Uwaga**: Wymaga rozszerzonych danych order book (pełna głębokość)
**Zastępnik dla dostępnych danych**:
```python
# Używając dostępnych bid_qty, ask_qty
surface_imbalance = (bid_qty - ask_qty) / (bid_qty + ask_qty)
historical_surface_imbalance = avg_surface_imbalance(baseline_window)
depth_change = surface_imbalance - historical_surface_imbalance
```

#### Spread_Dynamics_Predictor
**Opis**: Dynamika spread'u jako predyktor napięcia rynkowego i breakout
**Wzór**: `spread_velocity * spread_volatility * spread_mean_reversion`
**Parametry**:
- `spread_velocity_window`: okno velocity spread'u (np. 60s)
- `spread_volatility_period`: okres zmienności spread'u (np. 300s)
- `mean_reversion_lookback`: okres mean reversion (np. 900s)
**Składniki**:
```python
spread_velocity = (current_spread - avg_spread(spread_velocity_window)) / avg_spread(spread_velocity_window)
spread_volatility = Spread_Volatility(spread_volatility_period)
spread_mean = avg_spread(mean_reversion_lookback)
mean_reversion_force = (spread_mean - current_spread) / spread_mean

tension_index = spread_velocity * spread_volatility * (1 - mean_reversion_force)
```

#### Liquidity_Absorption_Rate
**Opis**: Tempo absorpcji płynności jako predyktor wyczerpania lub napływu
**Wzór**: `(liquidity_consumed_rate - liquidity_provided_rate) / baseline_liquidity_flow`
**Parametry**:
- `absorption_measurement_window`: okno pomiaru absorpcji (np. 120s)
- `baseline_flow_period`: okres baseline flow (np. 600s)
- `critical_absorption_threshold`: krytyczny poziom absorpcji
**Kalkulacja**:
```python
# Przybliżenie na podstawie dostępnych danych
liquidity_change_rate = (Total_Liquidity(current) - Total_Liquidity(previous)) / time_diff
volume_consumption_rate = sum_volume(measurement_window) / measurement_window
net_absorption = volume_consumption_rate - liquidity_change_rate

baseline_flow = avg_net_absorption(baseline_flow_period)
absorption_intensity = net_absorption / baseline_flow
```

### H5. Cross-Market Predictors

#### Correlation_Breakdown_Predictor
**Opis**: Predykcja na podstawie załamania korelacji z rynkiem głównym
**Wzór**: `rolling_correlation_change * isolation_strength * breakout_potential`
**Parametry**:
- `correlation_windows`: [300, 900, 1800] sekund dla rolling correlation
- `main_market_proxy`: referencyjny symbol (BTC/ETH - jeśli dostępny)
- `isolation_threshold`: próg izolacji (np. korelacja < 0.3)
**Uwaga**: Wymaga danych z innych rynków
**Zastępnik** (analiza wewnętrzna):
```python
# Używając tylko danych tokena - analiza self-correlation w różnych timeframes
short_term_pattern = price_pattern(60s_windows)
medium_term_pattern = price_pattern(300s_windows)
long_term_pattern = price_pattern(900s_windows)

pattern_divergence = correlation(short_term, medium_term) - correlation(medium_term, long_term)
isolation_strength = 1 - abs(pattern_divergence)
```

#### Market_Microstructure_Regime_Shift
**Opis**: Wykrywanie zmiany reżimu mikrostruktury jako predyktor zmian behawioralnych
**Wzór**: Composite klasyfikator na podstawie multiple mikrostrukturalnych features
**Parametry**:
- `regime_features`: lista cech [spread, depth, frequency, size]
- `regime_detection_window`: okno detekcji reżimu (np. 600s)
- `regime_shift_threshold`: próg zmiany reżimu
**Składniki**:
```python
current_regime_vector = [
    Spread_Percentage(regime_detection_window),
    Total_Liquidity(regime_detection_window),
    Trade_Frequency(regime_detection_window),
    Average_Trade_Size(regime_detection_window)
]

historical_regime_vector = [same_features dla baseline_period]
regime_distance = euclidean_distance(current_regime_vector, historical_regime_vector)
regime_shift_probability = min(1.0, regime_distance / historical_volatility_of_regime)
```

### H6. Time-Series Forecasting Predictors

#### Autoregressive_Price_Predictor
**Opis**: Prosty model autoregresywny do predykcji kolejnej ceny
**Wzór**: `price_t+1 = α₁*price_t + α₂*price_t-1 + ... + αₙ*price_t-n+1`
**Parametry**:
- `ar_order`: rząd modelu AR (np. 5)
- `training_window`: okno trenowania modelu (np. 1800s)
- `update_frequency`: częstotliwość aktualizacji modelu (np. 300s)
**Kalkulacja**:
```python
# Użyj ostatnich N cen do predykcji następnej
price_history = [TWPA(i*30, (i+1)*30) for i in range(ar_order)]
weights = calculate_ar_weights(price_history, training_window)
predicted_price = sum([weights[i] * price_history[i] for i in range(ar_order)])
price_prediction_confidence = 1 - prediction_error_variance
```

#### Velocity_Extrapolation_Model
**Opis**: Ekstrapolacja obecnego velocity z uwzględnieniem decay
**Wzór**: `future_price = current_price * (1 + velocity * time_horizon * decay_factor)`
**Parametry**:
- `time_horizon`: horyzont predykcji (np. 300s)
- `velocity_decay_rate`: tempo zaniku velocity (np. 0.1 per minute)
- `confidence_decay_rate`: spadek pewności w czasie
**Składniki**:
```python
current_velocity = Velocity((0,0), (60,0), "VTWPA")
velocity_sustainability = Momentum_Persistence_Forecast
decay_factor = exp(-velocity_decay_rate * time_horizon / 60)

extrapolated_return = current_velocity * (time_horizon / 60) * decay_factor * velocity_sustainability
predicted_price = current_price * (1 + extrapolated_return / 100)
prediction_confidence = exp(-confidence_decay_rate * time_horizon / 60)
```

#### Cyclical_Pattern_Predictor
**Opis**: Wykrywanie i predykcja wzorców cyklicznych w danych
**Wzór**: Fourier analysis + pattern matching
**Parametry**:
- `cycle_detection_period`: okres detekcji cykli (np. 3600s)
- `min_cycle_length`: minimalna długość cyklu (np. 120s)
- `max_cycle_length`: maksymalna długość cyklu (np. 1800s)
**Kalkulacja**:
```python
# Simplified cyclic detection
price_differences = [price_i - TWPA(long_window) for każdej ceny]
autocorrelations = [correlation(price_differences[:-lag], price_differences[lag:]) 
                   for lag in range(min_cycle, max_cycle)]

dominant_cycle = find_max_correlation_lag(autocorrelations)
cycle_strength = max(autocorrelations)
cycle_phase = current_position_in_cycle(dominant_cycle)

if cycle_strength > threshold:
    predicted_next_phase = extrapolate_cycle(cycle_phase, dominant_cycle)
```

## ENHANCED CONFIGURATION

### Predictive Model Parameters
```json
{
  "pattern_recognition": {
    "wave_detection_sensitivity": 0.02,
    "fibonacci_tolerance": 0.05,
    "channel_compression_threshold": 0.3
  },
  "momentum_prediction": {
    "oscillator_period": 300,
    "divergence_threshold": -0.3,
    "cascade_alignment_threshold": 0.8
  },
  "volume_prediction": {
    "large_trade_percentile": 90,
    "smart_money_patience_weight": 0.3,
    "volume_trend_periods": [60, 300, 900]
  },
  "time_series": {
    "ar_model_order": 5,
    "velocity_decay_rate": 0.1,
    "cycle_detection_threshold": 0.6
  }
}
```

### Prediction Confidence Scoring
```json
{
  "confidence_factors": {
    "pattern_strength_weight": 0.25,
    "momentum_alignment_weight": 0.25,
    "volume_confirmation_weight": 0.25,
    "microstructure_support_weight": 0.25
  },
  "time_horizon_adjustments": {
    "1min_confidence_factor": 0.9,
    "5min_confidence_factor": 0.7,
    "15min_confidence_factor": 0.5
  }
}
```

### Zależności Rozszerzone
```
GRUPA A (fundamentalne) → nie ma zależności
GRUPA B (velocity) → wymaga GRUPA A
GRUPA C (volume) → wymaga GRUPA A  
GRUPA D (order book) → wymaga GRUPA A
GRUPA E (timing) → wymaga GRUPA A
GRUPA F (composite) → wymaga GRUPA B, C, D, E
GRUPA G (predykcyjne) → wymaga GRUPA A-F
GRUPA H (zaawansowane predykcyjne) → wymaga GRUPA A-G
```