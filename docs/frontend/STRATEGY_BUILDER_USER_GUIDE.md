# Strategy Builder User Guide - Visual Strategy Design (Design-Only)

**Version:** 1.0.1
**Last Updated:** 2025-09-28
**Status:** Design-Only Tool - No Execution Capabilities
**Target Audience:** Traders, Strategy Developers, Operations Team

---

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Interface Components](#interface-components)
4. [Creating Your First Strategy](#creating-your-first-strategy)
5. [Node Types and Configuration](#node-types-and-configuration)
6. [Validation and Error Handling](#validation-and-error-handling)
7. [Saving and Deployment](#saving-and-deployment)
8. [Advanced Features](#advanced-features)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

---

## Overview

Strategy Builder to wizualny interfejs typu "drag & drop" do **projektowania** strategii tradingowych bez pisania kodu. To **narzędzie do tworzenia diagramów strategii** - nie platforma wykonawcza.

⚠️ **KRYTYCZNE OGRANICZENIE:** Strategy Builder **NIE WYKONUJE** strategii tradingowych. Nie ma:
- Obliczeń wskaźników z parametrami czasowymi
- Wykonywania transakcji (nawet wirtualnych)
- Monitorowania P&L w czasie rzeczywistym
- Zarządzania ryzykiem czy pozycji
- Połączenia z rynkiem lub danymi handlowymi

**Aktualnie:** Tylko narzędzie do projektowania wizualnego i zapisywania schematów strategii.

### Kluczowe Funkcje (Tylko Projektowanie)
- **Wizualne Płótno:** Przeciąganie i upuszczanie komponentów strategii
- **Walidacja Struktury:** Sprawdzanie poprawności połączeń między węzłami
- **Biblioteka Szablonów:** Wstępnie zbudowane szablony strategii
- **Blueprint Storage:** Zapis strategii jako blueprintów do przyszłego wykorzystania
- **Zarządzanie Węzłami:** Dodawanie, usuwanie i łączenie komponentów
- **Podgląd Schematu:** Wizualizacja logiki strategii

### Aktualna Wartość Biznesowa
- **Wizualne projektowanie** strategii bez pisania kodu (vs YAML)
- **Strukturalna walidacja** podczas budowy strategii
- **Standaryzacja komponentów** dla spójności strategii
- **Zapis blueprintów** dla dokumentacji i przyszłego wykorzystania
- **Ułatwienie komunikacji** między traderami a zespołem technicznym

### Przyszła Wartość Biznesowa (Sprint 6A+)
- **Live indicator values** - zobacz prawdziwe obliczenia VWAP
- **Real-time signals** - obserwuj automatyczne sygnały kupna/sprzedaży
- **Virtual trading** - testuj strategie z wirtualnymi pieniędzmi
- **Risk management** - kontroluj ryzyko z automatycznymi stop-loss
- **End-to-end automation** - od pomysłu do automatycznego tradingu

---

## Pierwsze Kroki

### Wymagania wstępne
1. **Autoryzacja:** Prawidłowe dane logowania do platformy
2. **Przeglądarka:** Nowoczesna przeglądarka z włączonym JavaScript
3. **Sieć:** Stabilne połączenie internetowe dla walidacji w czasie rzeczywistym

### Dostęp do Strategy Builder
1. Zaloguj się do platformy tradingowej
2. Przejdź do `/strategy-builder` w przeglądarce
3. Interfejs załaduje się z domyślną strategią pump-detection

### Pierwsze Uruchomienie
- **Domyślna Strategia:** Podstawowa strategia detekcji pomp jest wstępnie załadowana
- **Biblioteka Węzłów:** Dostępne komponenty są pokazane w lewym panelu
- **Status Walidacji:** Zielony znacznik ✓ wskazuje prawidłową strategię

---

## Komponenty Interfejsu

### 1. Górny Pasek Narzędzi
```
┌─────────────────────────────────────────────────────────────────────┐
│ Strategy Builder - Visual Graph Editor                              │
│ ┌─────────────────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │Nazwa Strategii      │ │Validate  │ │ Load    │ │ Save    │ │ Run     │ │
│ └─────────────────────┘ └──────────┘ └─────────┘ └─────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

**Nazwa Strategii:** Edytowalne pole nazwy strategii (wymagane)
**Validate:** Sprawdza poprawność strategii i pokazuje błędy
**Load:** Ładuje wcześniej zapisaną strategię z biblioteki blueprintów
**Save:** Zapisuje strategię jako blueprint do przyszłego wykorzystania
**Run:** Obecnie tylko loguje wiadomość do konsoli (wykonanie strategii niedostępne - Sprint 6)

### 2. Lewy Panel - Biblioteka Węzłów
```
┌─────────────────────┐
│ Node Library        │
├─────────────────────┤
│ 📊 Data Sources     │
│   • Price Source    │
│   • Volume Source   │
├─────────────────────┤
│ 📈 Indicators       │
│   • VWAP            │
│   • Volume Surge    │
│   • Price Velocity  │
├─────────────────────┤
│ ⚖️ Conditions       │
│   • Threshold       │
│   • Duration        │
├─────────────────────┤
│ 🎯 Actions          │
│   • Buy Signal      │
│   • Sell Signal     │
│   • Alert Action    │
└─────────────────────┘
```

**Przeciąganie:** Kliknij i przeciągnij węzły na płótno
**Kategorie:** Organizowane wg funkcji (Dane → Analiza → Decyzja → Akcja)
**Dodaj Węzeł:** Kliknij na węzeł w bibliotece aby dodać go na płótno

### 3. Główne Płótno (Canvas)
```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │Price Source     │ -> │VWAP            │ -> │Threshold        │ │
│  │BTC/USDT 1000ms  │    │Window: 300     │    │> 0.5            │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
│                                                                     │
│  ┌─────────────────┐                                                │
│  │Volume Source    │ -> [Punkty Połączeń]                           │
│  │BTC/USDT trade   │                                                │
│  └─────────────────┘                                                │
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐                         │
│  │Threshold        │ -> │Buy Signal      │                         │
│  │Result           │    │$100.00 0.001%  │                         │
│  └─────────────────┘    └─────────────────┘                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Zoom:** Kółko myszki do powiększania/pomniejszania
**Pan:** Kliknij i przeciągnij puste miejsce aby przesunąć
**Wybór:** Kliknij węzeł aby go zaznaczyć
**Połączenia:** Przeciągnij od wyjścia do wejścia węzła
**Usuwanie:** Zaznacz węzeł i naciśnij klawisz Delete lub Backspace

### 4. Prawy Panel - Właściwości Węzła
```
┌─────────────────────┐
│ Node Properties     │
├─────────────────────┤
│ Selected: VWAP      │
├─────────────────────┤
│ Window Size:        │
│ [300] seconds       │
├─────────────────────┤
│ Description:        │
│ Volume Weighted     │
│ Average Price       │
└─────────────────────┘
```

**Pola Dynamiczne:** Zmieniają się w zależności od typu węzła
**Aktualizacje Real-time:** Zmiany są natychmiast stosowane na płótnie
**Walidacja:** Nieprawidłowe wartości pokazują wskaźniki błędów

### 5. Dolny Pasek Statusu
```
┌─────────────────────────────────────────────────────────────────────┐
│ Nodes: 5 | Edges: 4 | Status: ✓ Valid | Last Saved: 2 min ago        │
└─────────────────────────────────────────────────────────────────────┘
```

**Statystyki:** Aktualna liczba węzłów i połączeń
**Status Walidacji:** Zielony ✓ (prawidłowy), Żółty ⚠️ (ostrzeżenia), Czerwony ✗ (błędy)
**Ostatnio Zapisane:** Znacznik czasu ostatniego zapisu

---

## Tworzenie Pierwszej Strategii

### Krok 1: Rozpocznij od Domyślnej Strategii
Po otwarciu Strategy Builder zobaczysz wstępnie załadowaną strategię pump-detection składającą się z:
- **Price Source:** Pobiera dane cenowe BTC/USDT
- **Volume Source:** Pobiera dane wolumenowe
- **VWAP:** Oblicza średnią cenę ważoną wolumenem
- **Threshold Condition:** Porównuje VWAP z progiem 0.5
- **Buy Signal:** Generuje sygnał kupna za $100

### Krok 2: Zrozum Jak Działa Strategia
1. **Price Source** łączy się z **VWAP** (wejście "price")
2. **Volume Source** łączy się z **VWAP** (wejście "volume")
3. **VWAP** łączy się z **Threshold** (wyjście "vwap")
4. **Threshold** łączy się z **Buy Signal** (wyjście "result")

Strategia kupuje gdy VWAP przekroczy 0.5.

### Krok 3: Przetestuj Strategię
1. Kliknij **"Validate"** - powinien pokazać ✓ Valid
2. Wprowadź nazwę strategii w polu "Blueprint Name"
3. Kliknij **"Save"** - strategia zostanie zapisana jako blueprint
4. **Uwaga:** Przycisk "Run" obecnie tylko loguje wiadomość do konsoli (wykonanie strategii niedostępne)

### Krok 4: Dostosuj Strategię
1. **Zmień Parametry:**
   - Kliknij węzeł VWAP
   - W prawym panelu zmień "Window Size" z 300 na 600 sekund
   - Kliknij węzeł Threshold i zmień próg z 0.5 na 0.3

2. **Dodaj Nowe Komponenty:**
   - Przeciągnij "Volume Surge Ratio" z biblioteki na płótno
   - Połącz Volume Source → Volume Surge Ratio
   - Dodaj nowy "Threshold Condition"
   - Połącz Volume Surge Ratio → nowy Threshold
   - Połącz nowy Threshold → "Alert Action"

3. **Usuń Węzły:**
   - Zaznacz węzeł który chcesz usunąć
   - Naciśnij klawisz Delete lub Backspace

### Krok 5: Zapisz i Wdróż
1. Kliknij **"Validate"** aby sprawdzić strategię
2. Wprowadź nową nazwę w "Blueprint Name"
3. Kliknij **"Save"** aby zapisać
4. Strategia będzie dostępna do deploymentu przez operacje

---

## Typy Węzłów i Konfiguracja

### Węzły Źródeł Danych

#### Price Source (Źródło Cen)
**Cel:** Dostarcza dane cenowe w czasie rzeczywistym do analizy
**Parametry:**
- **Symbol:** Para tradingowa (np. "BTC/USDT")
- **Update Frequency:** Jak często pobierać dane (milisekundy)
- **Data Type:** Typ danych cenowych

#### Volume Source (Źródło Wolumenu)
**Cel:** Dostarcza dane wolumenowe w czasie rzeczywistym
**Parametry:**
- **Symbol:** Para tradingowa
- **Aggregation:** Metoda agregacji wolumenu ("trade")
- **Time Window:** Okno czasowe dla kalkulacji

### Węzły Wskaźników

#### VWAP (Volume Weighted Average Price)
**Cel:** Oblicza średnią cenę ważoną wolumenem
**Parametry:**
- **Window:** Okno czasowe w sekundach (domyślnie: 300)
- **Symbol:** Para tradingowa (dziedziczona z wejścia)
**Wyjścia:** Wartość VWAP, odchylenie od VWAP

#### Volume Surge Ratio
**Cel:** Wykrywa nagłe wzrosty wolumenu wskazujące na pompę
**Parametry:**
- **Baseline Window:** Okno bazowe w sekundach (domyślnie: 3600)
- **Surge Threshold:** Próg wzrostu (domyślnie: 2.0)

#### Price Velocity
**Cel:** Mierzy prędkość zmian ceny (momentum)
**Parametry:**
- **Period:** Okres kalkulacji w sekundach (domyślnie: 60)

### Węzły Warunków

#### Threshold Condition (Warunek Progowy)
**Cel:** Porównuje wartość wejściową z progiem
**Parametry:**
- **Operator:** Operator porównania (">", "<", ">=", "<=", "==", "!=")
- **Threshold:** Wartość progu (domyślnie: 0.5)

#### Duration Condition (Warunek Czasowy)
**Cel:** Wymaga spełnienia warunku przez określony czas
**Parametry:**
- **Duration Seconds:** Czas w sekundach (domyślnie: 30)
- **Reset on False:** Resetuj timer gdy warunek stanie się fałszywy

### Węzły Akcji

#### Buy Signal (Sygnał Kupna)
**Cel:** Generuje zlecenie kupna gdy zostanie wywołany
**Parametry:**
- **Position Size:** Wielkość pozycji w USD (domyślnie: 100.0)
- **Max Slippage:** Maksymalne dozwolone odchylenie ceny (%) (domyślnie: 0.001)

#### Sell Signal (Sygnał Sprzedaży)
**Cel:** Generuje zlecenie sprzedaży gdy zostanie wywołany
**Parametry:**
- **Position Size:** Wielkość pozycji w USD (domyślnie: 100.0)

#### Alert Action (Akcja Alertu)
**Cel:** Wysyła powiadomienie gdy zostanie wywołany
**Parametry:**
- **Message:** Treść alertu (domyślnie: "Strategy condition met")
- **Priority:** Priorytet ("medium")

---

## Validation and Error Handling

### Real-time Validation
The Strategy Builder validates your strategy continuously:

**✓ Valid (Green):** Strategy is correct and ready for deployment
**⚠️ Warnings (Yellow):** Strategy works but has potential issues
**✗ Errors (Red):** Strategy has critical problems that prevent deployment

### Common Validation Errors

#### Connection Errors
```
Error: Invalid connection - Indicator cannot connect to Action
Solution: Check node compatibility in the Node Library
```

#### Parameter Errors
```
Error: Invalid window size - must be between 60-3600 seconds
Solution: Adjust parameter values in the Properties panel
```

#### Logic Errors
```
Error: Circular dependency detected
Solution: Remove connections that create loops
```

#### Missing Requirements
```
Error: Data Source required for Indicator
Solution: Add appropriate data source node and connect it
```

### Validation Best Practices
1. **Validate Frequently:** Click "Validate" after major changes
2. **Check Connections:** Ensure all required connections are made
3. **Review Parameters:** Verify all node parameters are appropriate
4. **Test Logic:** Run paper trading to verify strategy behavior

---

## Saving and Deployment

### Saving Strategies
1. Enter a **Blueprint Name** in the top toolbar
2. Click **"Save"** button
3. Strategy blueprint is stored in the system database

### Loading Strategies
1. Click **"Load"** button in the top toolbar
2. Select a strategy from the list of saved blueprints
3. Click on a strategy name to load it into the canvas
4. The strategy graph and name will be restored from the blueprint

### What Actually Happens When You Save
- **Blueprint Storage:** Your visual strategy graph is converted to JSON format and saved via the `/api/strategy-blueprints` API endpoint
- **Version Control:** Each save creates a new version with metadata (timestamp, user)
- **No Automatic Deployment:** Saved blueprints are stored but **do not automatically deploy to live trading systems**
- **Future Use:** Blueprints can be loaded back into the builder for editing or used by other system components

### What Happens When You Click "Run"
⚠️ **Current Limitation:** The "Run" button currently only logs a message to the browser console and **does not execute the strategy**.

**Console Output:** `Run strategy` (no actual execution)

**What Does NOT Exist Yet:**
- ❌ No deployment pipeline connection
- ❌ No paper trading execution
- ❌ No real-time market data processing
- ❌ No P&L tracking or performance metrics
- ❌ No emergency controls or risk management
- ❌ No strategy-to-execution translation
- ❌ No indicator calculations with time parameters
- ❌ No session management or trading controls

**Future Implementation (Sprint 6+):** Full end-to-end execution workflow

### Current Limitations & Workarounds
- **No Live Execution:** Strategies cannot be run directly from the builder
- **No Real-Time Monitoring:** Cannot view live strategy performance or signals
- **No Deployment Pipeline:** No automated approval, staging, or production deployment
- **Manual Process Required:** Strategy execution requires separate setup outside the builder

**Workaround:** Use Strategy Builder for design and validation, then manually configure strategies through other system interfaces for actual execution.

### Future Deployment Process (Sprint 6+)
1. **Blueprint Selection:** Choose saved blueprint from Strategy Builder
2. **Validation:** Server-side validation of graph logic and resource requirements
3. **Approval Workflow:** Optional review and approval by operations team
4. **Staging Deployment:** Test deployment with paper trading
5. **Production Deployment:** Live deployment with monitoring and emergency controls

### Future Deployment Modes (Sprint 6+)
- **Paper Trading:** Simulated trading with virtual money and real-time metrics
- **Live Trading:** Real money trading with full risk controls
- **Backtesting:** Historical data testing with performance analytics

### Future Monitoring Features (Sprint 6+)
- **Operations Dashboard Integration:** Real-time P&L and performance metrics
- **Live Signal Feed:** View strategy signals and conditions in real-time
- **Emergency Controls:** Kill-switch and position management
- **Hot Reload:** Update running strategies without downtime

---

## Zaawansowane Funkcje

### Klonowanie Strategii
1. Otwórz istniejącą strategię w Strategy Builder
2. Zmodyfikuj parametry lub połączenia węzłów
3. Zmień nazwę w polu "Blueprint Name"
4. Kliknij "Save" aby zapisać jako nową strategię

### Zarządzanie Węzłami
- **Przenoszenie:** Przeciągnij węzeł aby zmienić jego pozycję
- **Wybór Wielu:** Przytrzymaj Ctrl/Shift aby zaznaczyć wiele węzłów
- **Kopiowanie:** Zaznacz węzeł i przeciągnij z Shift aby skopiować
- **Wyrównanie:** Węzły automatycznie wyrównują się do siatki

### Optymalizacja Wydajności
- **Throttle Walidacji:** Walidacja jest ograniczana aby nie obciążać systemu
- **Lazy Loading:** Duże strategie ładują się stopniowo
- **Memory Management:** Automatyczne czyszczenie nieużywanych zasobów

### Debugowanie Strategii
- **Status Walidacji:** Real-time informacje o błędach i ostrzeżeniach
- **Podgląd Połączeń:** Wizualne wskaźniki poprawności połączeń
- **Testowanie Parametrów:** Możliwość testowania różnych wartości bez zapisywania

---

## Rozwiązywanie Problemów

### Problemy z Płótnem

**Problem:** Węzły nie chcą się połączyć
**Rozwiązanie:**
- Sprawdź kompatybilność węzłów w Bibliotece Węzłów
- Upewnij się, że przeciągasz od uchwytu wyjścia do wejścia
- Sprawdź czy nie ma zależności cyklicznych

**Problem:** Płótno jest puste po odświeżeniu
**Rozwiązanie:**
- Sprawdź konsolę przeglądarki pod błędami
- Wyczyść cache przeglądarki i przeładuj
- Skontaktuj się z supportem jeśli problem trwa

**Problem:** Nie mogę usunąć węzła
**Rozwiązanie:**
- Zaznacz węzeł kliknięciem
- Naciśnij klawisz Delete lub Backspace
- Lub kliknij prawym przyciskiem i wybierz "Delete"

### Problemy z Walidacją

**Problem:** Trwałe błędy walidacji
**Rozwiązanie:**
- Kliknij "Validate" aby odświeżyć status walidacji
- Sprawdź czy wszystkie parametry węzłów są prawidłowe
- Upewnij się, że wszystkie wymagane połączenia są wykonane
- Przejrzyj komunikaty błędów pod konkretnymi wskazówkami

**Problem:** Strategia działa w paper trading ale nie przechodzi walidacji
**Rozwiązanie:**
- Sprawdź warunki wyścigu w danych real-time
- Zweryfikuj kalkulacje wskaźników pod kątem stabilności
- Przejrzyj parametry zarządzania ryzykiem

### Problemy z Wydajnością

**Problem:** Interfejs jest wolny przy dużych strategiach
**Rozwiązanie:**
- Zmniejsz liczbę węzłów (celuj w <20 węzłów)
- Walidacja throttling jest wbudowana
- Zamknij niepotrzebne zakładki przeglądarki
- Użyj Chrome/Firefox dla najlepszej wydajności

### Problemy z Połączeniami

**Problem:** Nie mogę połączyć węzłów różnych typów
**Rozwiązanie:**
- Sprawdź reguły kompatybilności:
  - Data Source → Indicator
  - Indicator → Condition
  - Condition → Action
  - Indicator → Indicator (łańcuchowanie)
- Przeciągaj tylko między kompatybilnymi uchwytami

### Problemy z Zapisem

**Problem:** Nie mogę zapisać strategii
**Rozwiązanie:**
- Upewnij się, że nazwa strategii nie jest pusta
- Sprawdź czy jesteś zalogowany (401 błąd)
- Zweryfikuj czy strategia przechodzi walidację
- Sprawdź połączenie z backendem

### Problemy z Autoryzacją

**Problem:** Błędy 401 Unauthorized
**Rozwiązanie:**
- Wyloguj się i zaloguj ponownie
- Wyczyść localStorage przeglądarki
- Sprawdź wygaśnięcie tokenu
- Skontaktuj się z adminem w sprawie konta

---

## Najlepsze Praktyki

### Projektowanie Strategii
1. **Zaczynaj Prosto:** Rozpocznij od podstawowych strategii i stopniowo dodawaj złożoność
2. **Testuj Dokładnie:** Zawsze używaj paper trading przed live deployment
3. **Monitoruj Wydajność:** Regularnie przeglądaj metryki wydajności strategii
4. **Zaczynaj od Domyślnej:** Użyj wstępnie załadowanej strategii jako punktu wyjścia

### Konfiguracja Węzłów
1. **Odpowiednie Parametry:** Wybieraj wartości na podstawie timeframe tradingu
2. **Zarządzanie Ryzykiem:** Zawsze uwzględniaj stop-loss i limity wielkości pozycji
3. **Jakość Danych:** Upewnij się, że źródła danych są wiarygodne i aktualne

### Praca z Interfejsem
1. **Częste Zapisywanie:** Regularnie zapisuj strategię podczas pracy
2. **Walidacja:** Sprawdzaj strategię po każdej większej zmianie
3. **Organizacja:** Używaj sensownych nazw węzłów i strategii
4. **Czyszczenie:** Usuwaj nieużywane węzły aby utrzymać przejrzystość

### Bezpieczeństwo i Kontrola
1. **Kontrola Dostępu:** Deployuj tylko strategie które rozumiesz
2. **Limity Ryzyka:** Zawsze ustawiaj odpowiednie wielkości pozycji i stop-loss
3. **Ścieżka Audytu:** Przeglądaj historię deploymentów i zmian
4. **Backup:** Zapisuj ważne strategie pod różnymi nazwami

---

## Support and Resources

### Getting Help
- **Documentation:** This user guide and technical documentation
- **Support Team:** Contact via the platform support system
- **Community:** Strategy Builder user forum
- **Training:** Scheduled training sessions for new users

### Additional Resources
- **Video Tutorials:** Step-by-step strategy building guides
- **API Documentation:** Technical details for advanced users
- **Strategy Examples:** Real-world strategy implementations
- **Performance Reports:** Analysis of deployed strategies

---

## Przyszłe Usprawnienia

### Sprint 6 (Adaptive Strategies)
- **Optymalizacja Automatyczna:** Strategie adaptujące się do warunków rynkowych
- **Integracja Portfolio:** Zarządzanie wieloma strategiami w portfolio
- **Zaawansowane Analityki:** Analiza trendów wydajności

### Sprint 7 (Enhanced UI & Security)
- **Kompletny Redesign UI:** Nowoczesny design system i lepsza użyteczność
- **Dostępność:** Zgodność z WCAG 2.1 AA
- **Obsługa Mobile:** Podstawowa obsługa urządzeń mobilnych
- **Tryb Dark Mode:** Pełne wsparcie dla ciemnego motywu

### Sprint 8+ (Enterprise & Marketplace)
- **Marketplace Strategii:** Kupno/sprzedaż strategii od społeczności
- **Zaawansowane Backtesting:** Symulacje Monte Carlo i testy stresowe
- **Wsparcie AI:** Sugestie strategii wspomagane AI

---

## What's Coming Next

### Sprint 6A: Live Indicator Display (2 weeks)
**Timeline:** Next sprint

**New Features:**
- **Live VWAP Values:** Real-time VWAP calculations with live market data
- **Time Window Parameters:** Proper temporal calculations with reference timestamps
- **UI Integration:** Live indicator values displayed in Strategy Builder canvas

**What You'll Be Able To Do:**
- See live VWAP values updating in real-time
- Understand how time windows affect indicator calculations
- Verify indicator accuracy against market data

### Sprint 6B: Strategy Signal Generation (2 weeks)
**Timeline:** Sprint after next

**New Features:**
- **Condition Evaluation:** VWAP threshold conditions evaluated in real-time
- **Live Signals:** Buy/sell signals generated from live market conditions
- **Signal Display:** Real-time signal notifications in Strategy Builder

**What You'll Be Able To Do:**
- See automated buy/sell signals from real market data
- Understand how strategy conditions trigger trading decisions
- Test basic strategy logic with live data

### Sprint 7A: Virtual Trading (2 weeks)
**Timeline:** Later sprints

**New Features:**
- **Paper Trading:** Virtual balance and position management
- **P&L Tracking:** Real-time profit/loss calculations
- **Position Display:** Virtual portfolio monitoring

**What You'll Be Able To Do:**
- Test strategies with virtual money
- See how trading decisions affect portfolio value
- Learn trading without financial risk

### Sprint 7B: Risk Management (2 weeks)
**Timeline:** Future sprints

**New Features:**
- **Emergency Controls:** Stop-loss and position limit enforcement
- **Risk Monitoring:** Real-time risk assessment
- **Safety Features:** Automatic position closure for risk control

**What You'll Be Able To Do:**
- Trade safely with automatic risk controls
- Prevent losses through emergency stop functionality
- Manage risk parameters during virtual trading

### Sprint 7: Enterprise Features & Security
**Expected Timeline:** Sprint after next (3 weeks)

**New Features:**
- **Multi-Tenant Support:** Isolated workspaces for different users/teams
- **Advanced Security:** JWT authentication, encrypted API keys, audit trails
- **Compliance Features:** PII handling, retention policies, exportable logs
- **UI/UX Overhaul:** Modern design system, accessibility compliance, dark mode

**What You'll Be Able To Do:**
- Collaborate securely with team members
- Meet enterprise security and compliance requirements
- Use the platform in production environments
- Access advanced administrative features

### Sprint 8+: Advanced Analytics & AI
**Expected Timeline:** Future sprints (8+ weeks)

**Planned Features:**
- **Adaptive Strategies:** AI-powered parameter optimization
- **Portfolio Intelligence:** Multi-strategy risk management
- **Strategy Marketplace:** Community templates and sharing
- **Mobile Support:** Progressive Web App for mobile devices

**What You'll Be Able To Do:**
- Let AI optimize your strategy parameters automatically
- Manage complex portfolios with correlation analysis
- Discover and share strategies with the community
- Monitor trading on mobile devices

### How to Stay Updated
- **Documentation:** This guide will be updated with each sprint
- **Release Notes:** Check sprint completion reports for new features
- **Roadmap:** See `docs/ROADMAP.md` for detailed timelines
- **Support:** Contact the development team for feature requests

---

*This guide will be updated as new features are added. Check regularly for the latest information.*