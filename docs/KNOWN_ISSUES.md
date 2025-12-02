# Znane Problemy i Ograniczenia

## Aktywne Problemy

### KI1: Backtest czasem nie generuje sygnałów
**Objawy:** ticks_processed > 0, ale signals_detected = 0
**Przyczyna:** Progi w strategii mogą być zbyt wysokie dla danego datasetu
**Workaround:** Użyj niższych progów (np. velocity_threshold = 0.00001)
**Status:** Wymaga lepszej dokumentacji domyślnych progów

### KI2: WebSocket reconnection nie zawsze działa
**Objawy:** Frontend traci połączenie i nie odzyskuje automatycznie
**Przyczyna:** Brak pełnej implementacji reconnection logic
**Workaround:** Odśwież stronę (F5)
**Status:** Do naprawy

### KI3: Memory usage rośnie przy długich sesjach
**Objawy:** Backend zużywa coraz więcej RAM przy >24h pracy
**Przyczyna:** Niektóre struktury danych nie są czyszczone
**Workaround:** Restartuj backend co 24h
**Status:** Wymaga audytu memory management

---

## Ograniczenia Architektury

### OA1: Tylko MEXC Futures
System obecnie wspiera tylko giełdę MEXC Futures. Inne giełdy (Binance, Bybit) wymagają nowych adapterów.

### OA2: Single-node deployment
System nie jest zaprojektowany na skalowanie horyzontalne. Dla wysokich obciążeń potrzebna byłaby architektura distributed.

### OA3: Brak persystencji stanu strategii
Restart backendu resetuje stan strategii (np. czy jest w trakcie oczekiwania na entry). Warunki czasowe (duration) tracą kontekst.

---

## Naprawione Problemy (Historia)

### [NAPRAWIONE 2025-12] Bug G1: Dead code w evaluate_risk_assessment
Metoda `evaluate_risk_assessment()` odwoływała się do nieistniejącego `self.risk_assessment`.
**Fix:** Usunięto dead code

### [NAPRAWIONE 2025-12] Bug G2: Brakujące metody w RiskManager
`strategy_manager.py` wywoływał `assess_position_risk()` i `can_open_position_sync()` które nie istniały.
**Fix:** Dodano brakujące metody

### [NAPRAWIONE 2025-11] Security fixes Sprint 16
- Credentials w logach
- Słabe JWT secrets
- CORS issues
**Fix:** 7 poprawek bezpieczeństwa

### [NAPRAWIONE 2025-11] Race conditions
5 race conditions w StrategyManager i ExecutionController
**Fix:** Dodano locki i synchronizację

---

## Jak Zgłaszać Nowe Problemy

1. Sprawdź czy problem nie jest już na liście
2. Dodaj sekcję z formatem:

```markdown
### KI[numer]: [Krótki tytuł]
**Objawy:** Co użytkownik widzi
**Przyczyna:** Jeśli znana
**Workaround:** Tymczasowe rozwiązanie
**Status:** Do naprawy / Wymaga analizy / Niski priorytet
```

3. Jeśli naprawiłeś problem, przenieś do sekcji "Naprawione Problemy"
