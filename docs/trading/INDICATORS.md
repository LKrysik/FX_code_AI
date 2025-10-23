# Wskaźniki Detekcji Manipulacji (Pump & Dump Detection Indicators)

**Cel:** Stworzenie skoncentrowanego katalogu wskaźników (cech) zaprojektowanych specjalnie do wykrywania krótkoterminowych manipulacji rynkowych typu "pump & dump". Odrzucamy podejście oparte na standardowej analizie technicznej na rzecz analizy anomalii.

---

## 1. Definicja i Rola Cech (Features) w Detekcji Manipulacji

**Cecha (Feature)**, w kontekście tego systemu, to parametryzowalna miara, która kwantyfikuje specyficzny aspekt anomalii rynkowej. W przeciwieństwie do tradycyjnych wskaźników (jak RSI czy MACD), te cechy są zaprojektowane do działania w bardzo krótkich oknach czasowych (sekundy/minuty) i do wychwytywania nagłych, nienaturalnych zmian.

**Kluczowe zasady:**
- **Niezależność**: Wskaźnik nie wie, jak jest wykorzystywany. Jego jedynym zadaniem jest poprawne wykonanie obliczeń na podstawie dostarczonych parametrów.
- **Reużywalność**: Ten sam wskaźnik (np. `VWAP(300, 0)`) może być używany przez wiele różnych strategii. System musi obliczać go tylko raz.
- **Zależności**: Wskaźniki mogą zależeć od innych wskaźników, tworząc graf zależności (DAG), który silnik musi poprawnie rozwiązać.

## 2. Katalog Cech do Detekcji "Pump & Dump"

### GRUPA 1: Anomalie Wolumenowe

#### Volume_Spike_Ratio(current_window_seconds, baseline_window_seconds, adaptive=True)
**Cel**: Wykrycie nienaturalnego wzrostu wolumenu, charakterystycznego dla rozpoczęcia manipulacji.
**Wzór**: `sum_volume(current_window) / (sum_volume(baseline_window) / (baseline_window_seconds / current_window_seconds))`
**Znaczenie**: Podstawowy wskaźnik inicjacji "pump". Wartości > 5.0 są silnym sygnałem.
**Parametry**:
- `current_window_seconds`: np. 30 (ostatnie 30 sekund)
- `baseline_window_seconds`: np. 1800 (ostatnie 30 minut jako baza)

#### Trade_Frequency_Spike(current_window_seconds, baseline_window_seconds)
**Cel**: Wykrycie nagłego wzrostu liczby transakcji, często generowanych przez boty.
**Wzór**: `count_deals(current_window) / (count_deals(baseline_window) / (baseline_window_seconds / current_window_seconds))`
**Znaczenie**: Uzupełnia `Volume_Spike_Ratio`, wskazując, czy wzrost wolumenu pochodzi z wielu małych transakcji.

### GRUPA 2: Anomalie Cenowe

#### Price_Acceleration(window_seconds, derivative_order=1)
**Cel**: Mierzenie "prędkości" (1. pochodna) lub "przyspieszenia" (2. pochodna) zmiany ceny.
**Wzór**: Oblicza pochodną numeryczną ceny w danym oknie.
**Znaczenie**: Manipulacje typu "pump" charakteryzują się nienaturalnie wysokim przyspieszeniem ceny.

#### Momentum_Decay(peak_lookback_seconds)
**Cel**: Wykrycie utraty impetu, co jest sygnałem zbliżającego się "dumpa".
**Wzór**: `(max_price_in_window - current_price) / max_price_in_window`
**Znaczenie**: Kluczowy wskaźnik do timingu wyjścia z pozycji.

### GRUPA 3: Anomalie w Mikrostrukturze Rynku (Order Book)

#### Order_Flow_Imbalance(window_seconds)
**Cel**: Wykrycie presji kupna/sprzedaży poprzez analizę agresywnych zleceń rynkowych.
**Wzór**: `(sum(buy_market_volume) - sum(sell_market_volume)) / (sum(buy_market_volume) + sum(sell_market_volume))`
**Znaczenie**: Silny dodatni wynik wskazuje na skoordynowaną akcję zakupową.

#### Spread_Widening_Ratio(current_window_seconds, baseline_window_seconds)
**Cel**: Wykrycie rozszerzenia spreadu, co często towarzyszy panice lub końcowi manipulacji.
**Wzór**: `avg_spread(current_window) / avg_spread(baseline_window)`
**Znaczenie**: Nagły wzrost spreadu może być sygnałem do natychmiastowego wyjścia.

#### Liquidity_Drain(window_seconds)
**Cel**: Wykrycie "wysysania" płynności z order booka, co jest typowe dla przygotowania do manipulacji.
**Wzór**: Analizuje zmiany w głębokości order booka na kluczowych poziomach cenowych.
**Znaczenie**: Może być wczesnym sygnałem ostrzegawczym przed gwałtownym ruchem.
