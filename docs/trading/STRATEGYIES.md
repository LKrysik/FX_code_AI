# Strategie – Specyfikacja Koncepcyjna i Techniczna

## Advanced Strategy Architecture Overview

### Multi-Dimensional Strategy Definition

Nowoczesne strategie tradingowe nie są statycznymi konfiguracjami, ale **systemami adaptacyjnymi**, które:

1.  **Odpowiadają na Reżimy Rynkowe**: Ta sama strategia bazowa zachowuje się inaczej w okresach wysokiej i niskiej zmienności.
2.  **Uczą się na podstawie Wyników**: Parametry strategii są ciągle optymalizowane na podstawie rzeczywistych rezultatów.
3.  **Zarządzają Ryzykiem na Poziomie Portfela**: Indywidualne decyzje strategii są pod wpływem ogólnego stanu portfela.
4.  **Adaptują się do Charakterystyki Symbolu**: Strategia dostosowuje parametry dla płynnych i niepłynnych symboli.

### Strategy Lifecycle Management

**Faza Rozwoju (Development Phase)**:
- Definicja strategii w elastycznym formacie konfiguracyjnym.
- Backtesting z uwzględnieniem wielu reżimów rynkowych i okresów.
- Testy A/B potencjalnych adaptacji.
- Analiza atrybucji wydajności.

**Faza Wdrożenia (Deployment Phase)**:
- Stopniowy rollout z grupami kontrolnymi.
- Monitorowanie wydajności w czasie rzeczywistym.
- Zautomatyzowana adaptacja na podstawie warunków rynkowych.
- Awaryjne wyłączniki bezpieczeństwa (circuit breakers).

**Faza Optymalizacji (Optimization Phase)**:
- Ciągłe uczenie się na podstawie nowych danych rynkowych.
- Dostrajanie parametrów w oparciu o rzeczywistą wydajność.
- Udoskonalanie reguł adaptacji.
- Zarządzanie wersjami strategii.

## 1. Definicja Koncepcyjna Strategii

**Strategia** to konfigurowalny zbiór reguł, który definiuje kompletny cykl życia decyzji tradingowej. Nie jest to pojedynczy algorytm, lecz **framework warunkowy**, który operuje na wartościach dostarczanych przez **Wskaźniki**.

Strategia jest całkowicie oddzielona od logiki obliczeniowej – nie wie, *jak* wskaźniki są liczone, a jedynie konsumuje ich wyniki (np. `Velocity > 15.0`).

## 2. Struktura Strategii Adaptacyjnej

### Definicja Strategii Bazowej (Base Strategy)
Rdzeń logiki strategii, który pozostaje spójny niezależnie od warunków rynkowych. Definiowany jest za pomocą 5-filarowego modelu.

### Warstwa Reguł Adaptacyjnych (Adaptation Rules Layer)
Konfigurowalne reguły, które modyfikują zachowanie strategii bazowej w oparciu o:
- Reżim zmienności rynkowej
- Warunki płynności
- Środowisko korelacji
- Charakterystykę danego symbolu
- Poziom ryzyka portfela

### Warstwa Ucząca się (Performance Learning Layer)
System, który ciągle optymalizuje strategię na podstawie:
- Historycznej wydajności transakcji
- Skuteczności w danych warunkach rynkowych
- Wpływu poszczególnych reguł adaptacji
- Zwrotów skorygowanych o ryzyko

### Model 5 Filarów (Struktura Bazowa)
**Uwaga:** Model 5 filarów jest **modelem koncepcyjnym** do logicznego grupowania warunków. Jego techniczna implementacja **nie może być sztywno sekwencyjna**, co zostało zidentyfikowane jako krytyczny problem architektoniczny. Nowoczesny `StrategyEvaluator` musi pozwalać na równoległą ocenę i obsługę priorytetów (np. warunki `Emergency Exit` muszą mieć najwyższy priorytet i móc przerwać wszystko inne).

Każda strategia jest logicznie podzielona na pięć sekwencyjnych grup warunków (filarów), które muszą być spełnione w określonej kolejności.

---

### Filar 1: Warunki Wykrycia Sygnału (Signal Detection)
Cel: Określenie kiedy rozpocząć monitoring danego symbolu, aby nie obciążać CPU ciągłą analizą wszystkich symboli.
Przykładowe warunki:
pump_magnitude >= 7.0% AND pump_magnitude <= 300%
volume_surge_ratio >= 3.5
price_velocity >= 0.4
spread_pct <= 5.0
liquidity_usdt >= 200
Logika: Dopiero gdy wszystkie warunki wykrycia są spełnione, system zaczyna aktywnie monitorować symbol i przechodzi do następnej fazy.
### Filar 2: Warunki Oceny Bezpieczeństwa (Risk Assessment)
Cel: Po wykryciu sygnału sprawdzenie czy okazja jest bezpieczna i czy spełnia kryteria jakości.
Przykładowe warunki:
confidence_score >= 50.0
risk_level == "low" OR risk_level == "medium"
market_sentiment != "panic"
correlation_with_portfolio <= 0.7
daily_trades_count < max_daily_trades
consecutive_losses < 3
Logika: Jeśli warunki bezpieczeństwa nie są spełnione, sygnał jest odrzucany bez przejścia dalej.
### Filar 3: Warunki Wejścia (Entry)
Cel: Precyzyjne określenie momentu i parametrów wejścia w pozycję.
Przykładowe warunki:
pump_age_seconds >= 3 AND pump_age_seconds <= 30
rsi_value <= 80
macd_divergence == false
spread_pct <= 2.0
orderbook_depth_usdt >= 500
price_vs_baseline <= 1.15
Logika: Określa dokładny moment wejścia w transakcję i jakość timing.
### Filar 4: Kalkulator Wielkości Pozycji (Position Sizing)
Cel: Wyliczenie parametrów transakcji - wielkość pozycji, dźwignia, stop loss, take profit.
Przykładowe warunki i kalkulacje:
IF confidence_score >= 80 THEN position_size = base_position_size * 1.5
IF confidence_score < 60 THEN position_size = base_position_size * 0.5

leverage = MIN(max_leverage, 2.0) IF volatility <= 0.05 ELSE 1.0

stop_loss_price = peak_price * (1 - stop_loss_buffer_pct/100)
take_profit_price = entry_price * (1 + target_profit_pct/100)

IF expected_profit/max_loss < 2.0 THEN reject_trade = true
IF position_cost > max_position_size_usdt THEN reject_trade = true
Logika: Jeśli kalkulacje wskazują że transakcja nie ma sensu (za małe zyski, za duże ryzyko), pozycja nie jest otwierana.
### Filar 5: Warunki Wyjścia Awaryjnego (Emergency Exit)
Cel: Monitoring otwartej pozycji i określenie kiedy natychmiast zamknąć pozycję z powodu niebezpiecznych warunków rynkowych.
Przykładowe warunki:
spread_pct >= 10.0  // Spread blowout
volume_decline_pct >= 70.0  // Volume death
liquidity_usdt <= 100  // Liquidity crisis
position_loss_pct >= 15.0  // Excessive loss
market_panic_score >= 0.9  // Market panic
time_in_position >= max_position_time_minutes
Logika: Którykolwiek warunek emergency exit jest spełniony → natychmiastowe zamknięcie pozycji.
### Warunki Globalne Strategii
Dodatkowo strategia ma warunki globalne ograniczające ogólną aktywność:
max_daily_trades: 5
daily_loss_limit_pct: 3.0
max_concurrent_positions: 3
cooldown_after_loss_minutes: 20
max_portfolio_exposure_pct: 10.0

## 3. Architektura Techniczna Silnika Strategii

Logiczny model 5 filarów jest implementowany technicznie jako **skierowany graf acykliczny (DAG)**, zgodnie z architekturą opisaną w `MVP.md` i `TECHNICAL_IMPLEMENTATION_PLAN.md`.

### 3.1. Mapowanie Koncepcji na Węzły Grafu

- **Warunek → `ConditionNode`**: Każdy pojedynczy warunek (np. `pump_magnitude >= 7.0%`) jest reprezentowany w grafie jako **Węzeł Warunku (`ConditionNode`)**. Przyjmuje on na wejściu wartość wskaźnika i zwraca `TRUE` lub `FALSE`.

- **Grupa Warunków → `CompositionNode`**: Wszystkie warunki w ramach jednego filaru (np. `Signal Detection`) są łączone za pomocą **Węzła Kompozycyjnego (`CompositionNode`)** działającego w trybie `AND`. Oznacza to, że cała grupa jest spełniona tylko wtedy, gdy wszystkie jej warunki są `TRUE`.

- **Sekwencja Filarów → Połączenia między `CompositionNode`**: Wynik `TRUE` z węzła kompozycyjnego jednego filaru (np. `Signal Detection`) staje się sygnałem aktywującym dla następnego filaru (np. `Risk Assessment`). Tworzy to łańcuch zależności, który odzwierciedla logiczny przepływ strategii.

### 3.2. Rola `StrategyEvaluator`

**`StrategyEvaluator`** to wyspecjalizowany serwis backendowy, który jest odpowiedzialny za wykonanie grafu strategii w czasie rzeczywistym:

1.  **Wczytanie Grafu**: Przy starcie sesji, `StrategyEvaluator` otrzymuje definicję strategii w formie grafu (zbudowanego na podstawie konfiguracji użytkownika).
2.  **Subskrypcja Danych**: Analizuje graf, identyfikuje wszystkie wymagane wskaźniki i subskrybuje ich wartości z `IndicatorEngine` poprzez `EventBus`.
3.  **Reaktywna Ewaluacja**: Gdy nowa wartość wskaźnika pojawia się na `EventBus`, `StrategyEvaluator` "przepycha" ją przez graf:
    -   Aktualizuje odpowiedni `ConditionNode`.
    -   Przelicza `CompositionNode`, do którego jest on podłączony.
    -   Jeśli `CompositionNode` zwróci `TRUE`, sygnał jest propagowany dalej, aktywując kolejny filar strategii.
4.  **Uruchamianie Akcji**: Jeśli ewaluacja dojdzie do końca łańcucha i ostatni węzeł (np. `Entry`) zwróci `TRUE`, `StrategyEvaluator` wywołuje odpowiedni **Węzeł Akcji (`ActionNode`)**, który np. wysyła polecenie otwarcia pozycji do `TradeExecutor`.

### 3.3. Obsługa Warunków Czasowych

Złożone warunki, takie jak `duration` (`RSI > 70 przez 30 sekund`) czy `sequence`, są obsługiwane wewnątrz `StrategyEvaluator` za pomocą **maszyn stanów (State Machines)**.

- **Duration**: Dla warunku `duration`, `StrategyEvaluator` tworzy małą maszynę stanów, która śledzi, jak długo warunek jest nieprzerwanie spełniony. Zamiast sprawdzać to w każdej milisekundzie, reaguje na zmiany stanu (`TRUE` -> `FALSE` lub odwrotnie) i zarządza timerem.
- **Sequence**: Dla warunków sekwencyjnych, maszyna stanów śledzi, czy warunki A, B, C zostały spełnione w odpowiedniej kolejności.

## 4. Przykład Kompletnej Strategii "Flash Pump Detection"

Poniższy JSON reprezentuje konfigurację strategii zgodnie z nowym, zagnieżdżonym schematem, która jest następnie kompilowana do opisanego powyżej grafu.

```json
{
  "strategy_name": "flash_pump_detection",
  "signal_detection_conditions": {
    "and": [
      {"pump_magnitude_pct": {"min": 7.0, "max": 300.0}},
      {"volume_surge_ratio": {"min": 3.5}},
      {"price_velocity": {"min": 0.4}},
      {"spread_pct": {"max": 5.0}},
      {"liquidity_usdt": {"min": 200}}
    ]
  },
  "risk_assessment_conditions": {
    "and": [
      {"confidence_score": {"min": 50.0}},
      {"risk_level": {"allowed": ["low", "medium"]}},
      {"daily_trades_count": {"max": "max_daily_trades"}},
      {"consecutive_losses": {"max": 3}}
    ]
  },
  "entry_conditions": {
    "and": [
      {"pump_age_seconds": {"min": 3, "max": 30}},
      {"rsi_value": {"max": 80}},
      {"spread_pct": {"max": 2.0}},
      {"orderbook_depth_usdt": {"min": 500}}
    ]
  },
  "position_sizing_rules": {
    "base_position_pct": 0.5,
    "confidence_multiplier": {},
    "max_leverage": 2.0,
    "stop_loss_buffer_pct": 10.0,
    "target_profit_pct": 25.0,
    "min_risk_reward_ratio": 2.0
  },
  "emergency_exit_conditions": {
    "or": [
      {"spread_blowout_pct": {"min": 10.0}},
      {"volume_death_pct": {"min": 70.0}},
      {"liquidity_crisis_usdt": {"max": 100}},
      {"max_loss_pct": {"min": 15.0}},
      {"max_position_time_minutes": {"min": 10}}
    ]
  },
  "global_limits": {
    "max_daily_trades": 5,
    "daily_loss_limit_pct": 3.0,
    "max_concurrent_positions": 3,
    "cooldown_minutes": 20
  }
}
```
# Elastyczność i Konfigurowalność
Każdy warunek może być:

Włączony/wyłączony (enabled: true/false)
Parametryzowany z różnymi wartościami progowymi
Kombinowany z innymi warunkami (logika `AND`/`OR`/`NOT` realizowana przez `CompositionNode`)
Czasowo ograniczony (warunek przez X sekund)
Adaptacyjny (próg zależny od volatilności)

Przykład zaawansowanego warunku:
```
IF (rsi_value >= 70 FOR duration >= 30_seconds) 
   AND (volume_decline_pct >= 50 WITHIN last_60_seconds)
   AND (spread_pct <= 3.0)
THEN trigger_exit_evaluation()
```
To jest prawdziwa natura strategii - konfigurowalny zbiór warunków operujących na miarach wyliczanych przez backend, gdzie każdy warunek może być dostrojony niezależnie dla optymalnej wydajności w różnych warunkach rynkowych.

## Krytyczne Problemy Architektoniczne Modelu Strategii

### 🚨 **Problem 1: Sztywność Sekwencyjnego Modelu 5 Filarów**
**Aktualny Problem**: Wszystkie filary muszą być przetwarzane sekwencyjnie w ścisłej kolejności.

**Konsekwencje**:
- System nie może równolegle oceniać `risk_assessment` podczas gdy `entry_conditions` się zmieniają
- Krytyczne opóźnienia w szybko zmieniających się warunkach rynkowych
- Brak możliwości przerwania niższych priorytetów przez wyższe (emergency exit)

**Wymagane Rozwiązanie**:
- Model oparty na priorytetach zamiast ścisłej sekwencji
- Równoległa ocena niezależnych warunków
- Mechanizmy przerywania dla warunków krytycznych

### 🚨 **Problem 2: Zarządzanie Stanem Warunków Czasowych**
**Aktualny Problem**: Warunki `duration` i `sequence` wymagają stanu, ale nie ma gwarancji persystencji.

**Konsekwencje**:
- Stan `RSI > 70 przez 30s` ginie podczas restartu systemu
- Brak synchronizacji stanu między instancjami systemu
- Nieokreślony cleanup starego stanu dla nieaktywnych symboli

**Wymagane Rozwiązanie**:
- Persystencja stanu w Redis z TTL
- Synchronizacja między instancjami
- Automatyczny cleanup nieaktywnych stanów
- Mechanizmy recovery po restartach

### 🚨 **Problem 3: Niejednoznaczna Semantyka Czasowa**
**Aktualny Problem**: System (t1, t2) jest mylący w kontekście rozproszonym.

**Przykład Problemu**:
```python
TWPA(300, 0)  # "od 5 minut temu do teraz"
```
- Co oznacza "teraz" w systemie rozproszonym?
- Czas otrzymania danych ≠ czas przetwarzania ≠ timestamp transakcji
- Różnice mogą być krytyczne dla decyzji tradingowych

**Wymagane Rozwiązanie**:
- Jawny parametr `reference_time`
- Standaryzacja na timestamp ostatniej transakcji
- Precyzyjna dokumentacja semantyki wszystkich funkcji czasowych



## Polityka Konfliktów Symboli i Sesji
- Priorytety: sesje `live` > `backtest`.
- Idempotentność: `session_start` z `idempotent: true` może zwrócić istniejący `session_id` zamiast błędu konfliktu.
- Konfiguracja runtime: mapowanie `strategy_config` na symbole następuje przy `session_start`.
- Strategie są definicją logiczną w `config/strategies` (bez przypisania do symbolu).

## JSON Schema Strategii
- Definicja 5 grup warunków (signal detection, risk, entry, sizing, emergency); wartości progowe, operatory AND/OR, okresy (FOR duration).
- (TODO) Osobny plik schema dla walidacji podczas ładowania strategii.


## Strategie zastąpują konfiguracje Symbolu
- Strategie są teraz głównym miejscem określania parametrów które będa slużyć do wykrywania sygnałów, określania wszystkich parametrów, ryzyk.
- W konfiguracji config/strategies zastępują konfiguracje 'symbols'
- podczas wywoływania backtest określamy dla danego symbolu jakich strategi będziemy używać do testów
- podczas wywoływania trading określamy dla danego symbolu jakich strategi będziemy używać do trading




# Ważne! 
W strategii nie konfigurujemy miar tylko używamy miar
W strategii konfigurujemy warunki jakie mmuszą być spełnione by zadzialy sie pewne rzeczy (sygnal, trade, emergency exit) - na przykład ryzyko > 60% a średni wolume spada to emergency exit