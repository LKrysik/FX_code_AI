# Backlog Pomysłów na Rozwój

## Priorytet WYSOKI (Wartość dla tradera + Niska złożoność)

### I1: Lepsze wskaźniki pump detection
**Problem:** PRICE_VELOCITY jest podstawowy, potrzeba więcej sygnałów
**Propozycja:**
- Volume anomaly detection (nagły skok wolumenu)
- Bid/Ask imbalance (więcej kupujących niż sprzedających)
- Trade clustering (nagłe zagęszczenie transakcji)
**Wartość:** Wcześniejsze wykrycie pump, mniej fałszywych alarmów

### I2: Alerting/Notyfikacje
**Problem:** Użytkownik musi patrzeć na ekran żeby zobaczyć sygnał
**Propozycja:**
- Push notifications przez Telegram/Discord
- Email alerts
- Sound alerts w przeglądarce
**Wartość:** Trader nie przegapi okazji

### I3: Dashboard z real-time sygnałami
**Problem:** Brak widoku "co teraz się dzieje na rynku"
**Propozycja:**
- Lista aktywnych sygnałów
- Ranking symboli po "pump probability"
- Mapa cieplna aktywności
**Wartość:** Szybsza decyzja tradera

### I4: Szablony strategii
**Problem:** Użytkownik nie wie jak zacząć
**Propozycja:**
- "Flash Pump Strategy" - gotowy szablon
- "Conservative Long" - bezpieczna strategia
- Możliwość klonowania i modyfikacji
**Wartość:** Niższy próg wejścia

## Priorytet ŚREDNI (Wartość wysoka + Wyższa złożoność)

### I5: Multi-exchange support
**Problem:** Tylko MEXC
**Propozycja:** Binance, Bybit, OKX
**Złożoność:** Różne API, różne formaty danych
**Wartość:** Więcej okazji, arbitraż między giełdami

### I6: Backtesting z wizualizacją
**Problem:** Wyniki backestu to tylko liczby
**Propozycja:**
- Wykres equity curve
- Zaznaczone wejścia/wyjścia na wykresie ceny
- Analiza drawdown
**Wartość:** Lepsze zrozumienie strategii

### I7: Position sizing based on conviction
**Problem:** Stała wielkość pozycji
**Propozycja:**
- Większa pozycja gdy sygnał silniejszy
- Skalowanie oparte na volatility
**Wartość:** Lepsze wykorzystanie kapitału

### I8: Trailing stop-loss
**Problem:** Tylko fixed stop-loss
**Propozycja:**
- Stop podąża za ceną
- ATR-based trailing
**Wartość:** Ochrona zysków przy trendach

### I9: Strategy performance analytics
**Problem:** Brak analizy "która strategia działa lepiej"
**Propozycja:**
- Sharpe ratio, Sortino ratio
- Win rate per symbol
- Korelacja z rynkiem
**Wartość:** Optymalizacja portfela strategii

## Priorytet NISKI (Do rozważenia w przyszłości)

### I10: Machine Learning signals
**Złożoność:** WYSOKA
**Ryzyko:** Overfitting, trudne do wyjaśnienia
**Rozważ gdy:** Podstawowe wskaźniki okażą się niewystarczające

### I11: Social/Copy trading
**Złożoność:** WYSOKA (wymaga użytkowników, UI, modelu biznesowego)
**Rozważ gdy:** Produkt ma stabilną bazę użytkowników

### I12: API dla zewnętrznych botów
**Złożoność:** ŚREDNIA
**Rozważ gdy:** Są użytkownicy z własnymi systemami

### I13: Mobile app
**Złożoność:** WYSOKA
**Rozważ gdy:** Web app jest stabilny, jest popyt

## ODRZUCONE (z uzasadnieniem)

### X1: Blockchain integration / DEX trading
**Powód:** Komplikuje architekturę, CEX (MEXC) wystarczy na MVP
**Może wrócić:** Gdy CEX stracą popularność

### X2: On-premise deployment
**Powód:** Cloud-first pozwala na szybsze iteracje
**Może wrócić:** Gdy będą klienci enterprise

---

## Jak dodawać pomysły

Format:
```
### I[numer]: [Tytuł]
**Problem:** Co jest teraz źle / czego brakuje
**Propozycja:** Co zrobić
**Wartość dla tradera:** Dlaczego to ważne
**Złożoność:** NISKA / ŚREDNIA / WYSOKA
**Zależności:** Od czego zależy implementacja
```

## Zasady priorytetyzacji

```
WARTOŚĆ DLA TRADERA (wysoka) + ZŁOŻONOŚĆ (niska) = PRIORYTET WYSOKI
WARTOŚĆ DLA TRADERA (wysoka) + ZŁOŻONOŚĆ (wysoka) = PRIORYTET ŚREDNI
WARTOŚĆ DLA TRADERA (niska) = PRIORYTET NISKI lub ODRZUCONE
```
