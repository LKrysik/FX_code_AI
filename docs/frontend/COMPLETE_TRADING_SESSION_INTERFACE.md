# Complete Trading Session Interface

**URL:** http://localhost:3000/trading-session

**Status:** ✅ FULLY FUNCTIONAL MOCKUP - All controls work with artificial data

---

## Co Zostało Zrobione

Stworzyłem **KOMPLETNY interfejs konfiguracji sesji tradingowej** z:

### ✅ Wszystkie Kontrolki Działają

1. **Wybór trybu (Live / Paper / Backtest)**
   - Toggle buttons z opisami
   - Warningi dla każdego trybu
   - Blokada podczas sesji

2. **Wybór strategii (multi-select)**
   - Tabela ze wszystkimi strategiami
   - Checkbox selection
   - Win rate i avg profit dla każdej strategii
   - Status (Active/Inactive)
   - Możliwość wyboru wielu strategii jednocześnie

3. **Wybór symboli (multi-select)**
   - Chip interface z cenami
   - Kliknięcie = wybór/odznacz
   - Przyciski szybkiego wyboru (Top 3, Clear All)
   - Pokazuje aktualną cenę dla każdego symbolu

4. **Konfiguracja budżetu i ryzyka**
   - Global Budget (USDT)
   - Max Position Size (USDT)
   - Stop Loss (%)
   - Take Profit (%)

5. **Dla Backtest: Specjalne opcje**
   - Wybór sesji historycznej (dropdown)
   - Slider acceleration factor (1x - 100x)
   - Pokazuje liczbę rekordów i czas trwania sesji

6. **Panel podsumowania (prawy panel)**
   - Podsumowanie wszystkich wyborów
   - Walidacja (czy można wystartować)
   - Przycisk Start Session
   - Przycisk Stop Session (podczas sesji)

### ✅ Walidacja Formularza

- Wymaga minimum 1 strategii
- Wymaga minimum 1 symbolu
- Dla backtest: wymaga wyboru sesji historycznej
- Przycisk Start zablokowany jeśli walidacja nie przechodzi

### ✅ Wszystkie Dane MOCKUP (Oznaczone w Kodzie)

```typescript
// ⚠️ MOCKUP DATA - Replace with real API calls
const MOCK_STRATEGIES = [...];  // TODO: GET /api/strategies
const MOCK_SYMBOLS = [...];     // TODO: GET /api/exchange/symbols
const MOCK_DATA_SESSIONS = [...]; // TODO: GET /api/data-collection/sessions
```

**Każda sekcja ma ostrzeżenie:**
- Subheader: "⚠️ MOCKUP DATA - TODO: Replace with GET /api/..."
- Banner na górze strony: Warning o MOCKUP mode
- Alert przy przycisku: "TODO: Implement POST /api/sessions/start"

---

## Jak Używać

### 1. Uruchom Frontend

```bash
cd frontend
npm run dev
```

### 2. Otwórz Stronę

```
http://localhost:3000/trading-session
```

### 3. Skonfiguruj Sesję

**Krok 1:** Wybierz tryb (Paper Trading recommended for testing)

**Krok 2:** Wybierz strategie
- Kliknij na wiersz w tabeli aby zaznaczyć
- Możesz wybrać wiele strategii
- Zobacz win rate i avg profit

**Krok 3:** Wybierz symbole
- Kliknij chip aby wybrać/odznaczyć
- Lub użyj "Top 3" dla szybkiego wyboru

**Krok 4:** Ustaw budżet i ryzyko
- Global Budget: 1000 USDT (default)
- Max Position: 100 USDT (default)
- Stop Loss: 5% (default)
- Take Profit: 10% (default)

**Krok 5:** (Tylko dla Backtest) Wybierz sesję historyczną
- Dropdown z dostępnymi sesjami
- Slider acceleration factor

**Krok 6:** Kliknij "Start SESSION"
- Zobaczysz alert z podsumowaniem (MOCKUP)
- W konsoli będzie pełny config
- Session ID pojawi się w prawym panelu

### 4. Zatrzymaj Sesję

- Kliknij "Stop Session"
- Console log z session_id
- Stan wróci do początkowego

---

## Co NIE Działa (MOCKUP)

❌ **Dane nie są pobierane z API**
- Strategie są hardcoded
- Symbole są hardcoded
- Sesje historyczne są hardcoded

❌ **Przycisk Start nie wywołuje API**
- Tylko pokazuje alert i loguje do konsoli
- TODO: `await apiService.startSession(config)`

❌ **Przycisk Stop nie wywołuje API**
- Tylko zmienia local state
- TODO: `await apiService.stopSession(sessionId)`

❌ **Brak przekierowania**
- Po starcie sesji powinien redirect do /dashboard
- TODO: `router.push('/dashboard')`

---

## TODO Lista do Wdrożenia Produkcyjnego

### Backend API Endpoints Needed:

```typescript
// 1. Get available strategies
GET /api/strategies
Response: {
  strategies: [
    {
      id: string,
      name: string,
      description: string,
      winRate: number,
      avgProfit: number,
      enabled: boolean,
      category: string
    }
  ]
}

// 2. Get tradeable symbols
GET /api/exchange/symbols
Response: {
  symbols: [
    {
      symbol: string,
      name: string,
      price: number,
      volume24h: number,
      change24h: number
    }
  ]
}

// 3. Get historical data sessions (for backtest)
GET /api/data-collection/sessions
Response: {
  sessions: [
    {
      id: string,
      date: string,
      symbols: string[],
      duration: string,
      records: number,
      status: string
    }
  ]
}

// 4. Start session
POST /api/sessions/start
Body: {
  mode: 'live' | 'paper' | 'backtest',
  strategies: string[],
  symbols: string[],
  config: {
    global_budget: number,
    max_position_size: number,
    stop_loss_percent: number,
    take_profit_percent: number,
    session_id?: string,  // For backtest
    acceleration_factor?: number  // For backtest
  }
}
Response: {
  session_id: string,
  status: string
}

// 5. Stop session
POST /api/sessions/stop
Body: {
  session_id: string
}
```

### Frontend Changes Needed:

1. **Dodaj useEffect do pobierania danych:**

```typescript
useEffect(() => {
  // Fetch strategies
  apiService.getStrategies().then(data => setStrategies(data.strategies));

  // Fetch symbols
  apiService.getSymbols().then(data => setSymbols(data.symbols));

  // Fetch data sessions (if backtest mode)
  if (mode === 'backtest') {
    apiService.getDataSessions().then(data => setDataSessions(data.sessions));
  }
}, [mode]);
```

2. **Zmień handleStartSession:**

```typescript
const handleStartSession = async () => {
  try {
    setLoading(true);

    const config = {
      mode,
      strategies: selectedStrategies,
      symbols: selectedSymbols,
      config: {
        global_budget: globalBudget,
        max_position_size: maxPositionSize,
        stop_loss_percent: stopLoss,
        take_profit_percent: takeProfit,
        ...(mode === 'backtest' && {
          session_id: backtestSessionId,
          acceleration_factor: accelerationFactor,
        }),
      },
    };

    const response = await apiService.startSession(config);

    setCurrentSessionId(response.session_id);
    setIsSessionRunning(true);

    // Redirect to dashboard
    router.push('/dashboard');

  } catch (error) {
    console.error('Failed to start session:', error);
    alert('Failed to start session: ' + error.message);
  } finally {
    setLoading(false);
  }
};
```

3. **Zmień handleStopSession:**

```typescript
const handleStopSession = async () => {
  try {
    await apiService.stopSession(currentSessionId);
    setIsSessionRunning(false);
    setCurrentSessionId(null);
  } catch (error) {
    console.error('Failed to stop session:', error);
    alert('Failed to stop session: ' + error.message);
  }
};
```

4. **Usuń MOCKUP warningi:**
- Usuń warning banner na górze
- Usuń subheadery "⚠️ MOCKUP DATA"
- Usuń alert przy przycisku Start

5. **Dodaj loading states:**
```typescript
const [loading, setLoading] = useState(false);
const [strategiesLoading, setStrategiesLoading] = useState(true);
const [symbolsLoading, setSymbolsLoading] = useState(true);
```

---

## Przykłady Użycia

### Scenariusz 1: Paper Trading z 2 Strategiami

1. Wybierz "Paper Trading"
2. Zaznacz "Pump Detection v2" i "Dump Detection v2"
3. Wybierz "BTC_USDT", "ETH_USDT"
4. Ustaw budget na 1000 USDT
5. Kliknij "Start PAPER Session"
6. Zobacz alert z podsumowaniem
7. Sprawdź console dla pełnego configu

### Scenariusz 2: Backtest z Historycznymi Danymi

1. Wybierz "Backtest"
2. Wybierz sesję "2025-11-18 12:05:30" z dropdown
3. Ustaw acceleration factor na 50x (slider)
4. Zaznacz strategie
5. Wybierz symbole (muszą pasować do sesji)
6. Kliknij "Start BACKTEST Session"

### Scenariusz 3: Live Trading (Ostrzeżenie!)

1. Wybierz "Live Trading" - pojawi się czerwony warning
2. Skonfiguruj bardzo ostrożnie
3. Użyj małego budżetu na start
4. Kliknij "Start LIVE Session"

---

## Pliki

**Strona główna:**
- `frontend/src/app/trading-session/page.tsx` (650+ linii)

**Komponenty pomocnicze (opcjonalne):**
- `frontend/src/components/trading/SessionConfigMockup.tsx` - Można przenieść logikę tutaj
- `frontend/src/components/trading/SessionConfigDialog.tsx` - Dialog wrapper

**Dokumentacja:**
- `docs/frontend/SESSION_CONFIG_INTEGRATION_GUIDE.md` - Przewodnik integracji
- Ten plik - Kompletna dokumentacja interfejsu

---

## Pytania & Odpowiedzi

**Q: Czy to działa?**
A: Tak! Wszystkie kontrolki działają, walidacja działa, ale dane są MOCKUP.

**Q: Czy mogę to użyć w produkcji?**
A: NIE bez wdrożenia TODO listy. Musisz podłączyć prawdziwe API.

**Q: Gdzie są strategie pobierane?**
A: Obecnie hardcoded w `MOCK_STRATEGIES`. Zamień na GET /api/strategies.

**Q: Czy mogę dodać więcej strategii?**
A: Tak, dodaj do `MOCK_STRATEGIES` array, lub lepiej - podłącz prawdziwe API.

**Q: Jak sprawdzić co zostało wybrane?**
A: Kliknij "Start Session" i sprawdź console.log - zobaczysz pełny config.

**Q: Czy mogę zmienić domyślne wartości?**
A: Tak, zmień initial state (linia ~85-95 w pliku).

---

**Gotowe do użycia!** Otwórz http://localhost:3000/trading-session i przetestuj.
