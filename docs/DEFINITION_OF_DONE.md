# Definition of Done (DoD) - FXcrypto

## Filozofia

Definition of Done to **kontrakt jakościowy** - zestaw kryteriów, które muszą być spełnione, zanim uznamy pracę za "gotową". Nie jest to checklist do odhaczania na ślepo, ale **mentalny model** zapewniający, że dostarczamy wartość bez wprowadzania regresji.

### Zasady Przewodnie

1. **Zaufaj testom, nie intuicji** - Jeśli testy przechodzą, kod działa. Jeśli nie masz testu na coś, napisz go.
2. **Mniej znaczy więcej** - Minimalny zakres zmiany = mniejsze ryzyko regresji
3. **Nie zostawiaj długu** - Napraw to, co psujesz. Nie dodawaj TODO bez terminu.
4. **Weryfikuj na żywo** - Test manualny ≠ test automatyczny. Oba są potrzebne.

---

## Poziomy DoD

Różne typy zmian wymagają różnego poziomu weryfikacji:

| Poziom | Typ zmiany | Przykład | Czas weryfikacji |
|--------|-----------|----------|------------------|
| **L1** | Hotfix | Poprawka literówki, fix crashu | ~15 min |
| **L2** | Bug fix | Naprawa logiki, edge case | ~30 min |
| **L3** | Feature | Nowy endpoint, nowy wskaźnik | ~1-2h |
| **L4** | Critical | Logika tradingowa, risk management | ~2-4h |
| **L5** | Architecture | Refactoring warstwy, nowy adapter | ~4h+ |

---

## L1: Hotfix

**Kiedy:** Crashe, literówki, oczywiste błędy bez wpływu na logikę biznesową

### Checklist

```
[ ] Zmiana naprawia konkretny problem
[ ] Testy jednostkowe przechodzą: python run_tests.py --unit
[ ] Kod się buduje bez błędów
[ ] Brak nowych warningów w logach
```

### Szybka weryfikacja
```bash
python run_tests.py --unit --fast
curl http://localhost:8080/health  # jeśli backend
```

---

## L2: Bug Fix

**Kiedy:** Naprawa błędów logicznych, edge cases, regression fix

### Checklist

```
[ ] ZROZUMIENIE
    [ ] Przeczytałem istniejący kod przed zmianą
    [ ] Rozumiem root cause (nie tylko symptom)
    [ ] Sprawdziłem czy bug nie występuje gdzie indziej

[ ] IMPLEMENTACJA
    [ ] Zmiana jest minimalna i celowa
    [ ] Nie wprowadzam nowych zależności bez potrzeby
    [ ] Nie "ulepszam" kodu wokół - tylko naprawiam bug

[ ] TESTY
    [ ] Testy jednostkowe: python run_tests.py --unit
    [ ] Testy integracyjne (jeśli dotyczy DB/API): python run_tests.py --integration
    [ ] Dodałem test regresji dla tego buga

[ ] WERYFIKACJA
    [ ] Logi nie zawierają nowych błędów/ostrzeżeń
    [ ] Przetestowałem ręcznie scenariusz, który był zepsuty
```

### Komendy weryfikacyjne
```bash
# Testy
python run_tests.py --unit --integration

# Linting
ruff check src/

# Type checking (jeśli dotyczy typów)
mypy src/domain/services/nazwa_pliku.py
```

---

## L3: Feature

**Kiedy:** Nowa funkcjonalność, nowy endpoint, nowy wskaźnik, UI feature

### Checklist

```
[ ] PLANOWANIE
    [ ] Rozumiem wymagania i acceptance criteria
    [ ] Sprawdziłem czy podobna funkcjonalność już nie istnieje
    [ ] Wiem gdzie zmiana powinna się znajdować (warstwa, moduł)

[ ] IMPLEMENTACJA
    [ ] Kod jest w odpowiedniej warstwie (domain/application/infrastructure)
    [ ] Używam Dependency Injection - nie globalnych zmiennych
    [ ] Brak hardcoded wartości - wszystko z konfiguracji
    [ ] Nazewnictwo spójne z resztą kodu

[ ] TESTY
    [ ] Testy jednostkowe dla nowej logiki
    [ ] Testy integracyjne dla nowych endpointów/przepływów
    [ ] Pokrycie: nowy kod ma testy (nie musi być 100%)

[ ] JAKOŚĆ
    [ ] python run_tests.py (pełny zestaw)
    [ ] ruff check src/ - brak nowych błędów
    [ ] mypy src/ - brak nowych błędów typów
    [ ] black --check src/ - formatowanie OK

[ ] WERYFIKACJA MANUALNA
    [ ] Przetestowałem happy path ręcznie
    [ ] Przetestowałem edge cases (puste dane, błędne inputy)
    [ ] Sprawdziłem że nie zepsułem istniejącej funkcjonalności

[ ] DOKUMENTACJA (jeśli potrzebna)
    [ ] Docstring dla publicznych funkcji/klas
    [ ] Aktualizacja API docs jeśli nowy endpoint
    [ ] NIE tworzę nowych plików MD bez wyraźnej potrzeby
```

### Komendy weryfikacyjne
```bash
# Pełne testy
python run_tests.py

# Jakość kodu
ruff check src/
mypy src/
black --check src/

# Ręczna weryfikacja API
curl http://localhost:8080/api/[nowy-endpoint]

# Ręczna weryfikacja frontendu
# Otwórz http://localhost:3000 i przetestuj flow
```

---

## L4: Critical - Logika Tradingowa

**Kiedy:** Zmiany w: StrategyManager, RiskManager, ExecutionController, wskaźnikach używanych w strategiach, logice wejścia/wyjścia z pozycji

### Dodatkowe wymagania ponad L3

```
[ ] ANALIZA WPŁYWU
    [ ] Zidentyfikowałem wszystkie miejsca używające zmienianego kodu
    [ ] Sprawdziłem czy zmiana wpływa na istniejące strategie
    [ ] Rozumiem implikacje finansowe błędu w tym kodzie

[ ] TESTY SPECJALISTYCZNE
    [ ] Testy jednostkowe dla wszystkich edge cases
    [ ] Test z danymi syntetycznymi (pump pattern)
    [ ] Test backtestu: python scripts/test_strategy_builder_e2e.py

[ ] WERYFIKACJA FINANSOWA
    [ ] Przetestowałem na paper trading (jeśli możliwe)
    [ ] Sprawdziłem że risk limits są respektowane
    [ ] Logika wejścia/wyjścia działa zgodnie z definicją strategii

[ ] REVIEW
    [ ] Przegląd kodu przez drugą osobę LUB
    [ ] Szczegółowe self-review po 1h przerwy
```

### Komendy weryfikacyjne
```bash
# Wszystkie testy
python run_tests.py

# Test E2E strategii
python scripts/test_strategy_builder_e2e.py

# Sprawdzenie risk managera
python -m pytest tests_e2e/integration/test_risk.py -v

# Test na żywym środowisku (paper trading)
# 1. Uruchom z konfiguracją paper
# 2. Włącz strategię
# 3. Obserwuj przez 10-15 minut
```

---

## L5: Architecture - Refactoring/Nowy Adapter

**Kiedy:** Zmiany w Container, nowy adapter giełdy, zmiana wzorców architektonicznych, migracja danych

### Dodatkowe wymagania ponad L4

```
[ ] PLANOWANIE ARCHITEKTONICZNE
    [ ] Mam jasny diagram/opis zmiany
    [ ] Zmiana jest zgodna z istniejącymi ADR (docs/architecture/DECISIONS.md)
    [ ] Jeśli łamię ADR - dokumentuję dlaczego i tworzę nowy

[ ] BACKWARD COMPATIBILITY
    [ ] Stare API działa (jeśli publiczne)
    [ ] Migracja danych jest zaplanowana (jeśli potrzebna)
    [ ] NIE tworzę hacków kompatybilności - naprawiam źródło

[ ] TESTY ARCHITEKTURY
    [ ] Testy weryfikujące że DI działa poprawnie
    [ ] Testy że interfejsy są spełniane
    [ ] Testy wydajnościowe (jeśli zmiana może wpłynąć na performance)

[ ] DEPLOYMENT
    [ ] Mogę wdrożyć bez downtime (blue-green ready)
    [ ] Rollback jest możliwy i przetestowany
    [ ] Monitoring wyłapie problemy po wdrożeniu
```

### Komendy weryfikacyjne
```bash
# Pełne testy
python run_tests.py

# Test container/DI
python -m pytest tests_e2e/unit/ -v -k "container or inject"

# Test wydajności (jeśli masz)
python -m pytest tests_e2e/ -m performance

# Weryfikacja importów
pylint src/ --disable=all --enable=import-error,cyclic-import

# Sprawdzenie memory leaks (długi test)
# Uruchom backend, obserwuj memory usage przez 30 min
```

---

## Checklista Uniwersalna - ZAWSZE Sprawdź

Niezależnie od poziomu, przed merge/push ZAWSZE:

```
[ ] 1. Testy przechodzą
       python run_tests.py --unit

[ ] 2. Linting OK
       ruff check src/

[ ] 3. Nie wprowadzam security issues
       - Brak credentials w kodzie
       - Brak SQL injection (używam parametrized queries)
       - Brak command injection

[ ] 4. Health check działa
       curl http://localhost:8080/health

[ ] 5. Logi są czyste
       - Brak ERROR/CRITICAL podczas normalnej pracy
       - Brak stacktrace'ów
```

---

## Anti-patterns - Czego NIE Robić

### NIE rób tego, nawet jeśli "działa"

1. **Nie commituj bez testów**
   ```
   # ŹLE: "Testuję potem"
   # DOBRZE: Najpierw test, potem commit
   ```

2. **Nie naprawiaj symtomu zamiast przyczyny**
   ```python
   # ŹLE:
   try:
       result = broken_function()
   except:
       result = "default"  # ukrywa prawdziwy problem

   # DOBRZE:
   # Znajdź i napraw broken_function()
   ```

3. **Nie dodawaj backward compatibility hacków**
   ```python
   # ŹLE:
   def old_method():
       """Deprecated, use new_method"""
       return new_method()  # zostawione "na wszelki wypadek"

   # DOBRZE:
   # Usuń old_method, zaktualizuj wszystkie wywołania
   ```

4. **Nie "ulepszaj" kodu wokół**
   ```python
   # ŹLE: Miałem naprawić bug w linii 50, ale "przy okazji"
   # poprawiłem formatowanie, dodałem docstringi,
   # zrefaktorowałem funkcję pomocniczą...

   # DOBRZE: Naprawiam TYLKO buga. Reszta to osobny PR.
   ```

5. **Nie ignoruj warningów**
   ```bash
   # ŹLE: "To tylko warning, działa"
   # DOBRZE: Warning = potencjalny bug. Napraw lub zrozum dlaczego jest OK.
   ```

---

## Jak Używać DoD w Praktyce

### Przed rozpoczęciem pracy

1. Określ poziom zmiany (L1-L5)
2. Otwórz odpowiednią checklistę
3. Zaplanuj czas na weryfikację

### W trakcie pracy

1. Uruchamiaj testy często (`python run_tests.py --unit`)
2. Commituj małe, atomowe zmiany
3. Pisz testy równolegle z kodem

### Przed zakończeniem

1. Przejdź przez checklistę punkt po punkcie
2. Nie skracaj - jeśli punkt nie pasuje, zaznacz N/A z uzasadnieniem
3. Jeśli coś nie przechodzi - napraw przed oznaczeniem jako done

### Dla Claude Code

Kiedy realizujesz zadanie:

```
1. Na początku: Określ poziom DoD (L1-L5)
2. Użyj TodoWrite aby zaplanować kroki włącznie z weryfikacją
3. Po implementacji: Uruchom testy i sprawdź checklistę
4. Przed commit: Weryfikacja manualna + linting
5. Raportuj: Co zostało zweryfikowane i jakie testy przeszły
```

---

## Metryki Sukcesu

Dobre DoD powinno prowadzić do:

| Metryka | Cel | Jak mierzyć |
|---------|-----|-------------|
| Regresje | <5% PR wprowadza regresję | Bug reports po release |
| Test coverage | >70% dla nowego kodu | pytest --cov |
| Build success | >95% buildów przechodzi | CI/CD metrics |
| Time to fix | <2h dla L1-L2 bugów | Tracking time |

---

## Aktualizacja DoD

Definition of Done powinno ewoluować z projektem:

- **Dodaj** nowy punkt gdy powtarza się typ błędu
- **Usuń** punkt gdy staje się automatyczny (np. przez CI)
- **Uprość** gdy punkt jest zawsze N/A

**Ostatnia aktualizacja:** 2025-12

---

## Quick Reference Card

```
╔═══════════════════════════════════════════════════════════════╗
║                    DoD Quick Reference                         ║
╠═══════════════════════════════════════════════════════════════╣
║ ZAWSZE:                                                        ║
║   python run_tests.py --unit    # Testy jednostkowe           ║
║   ruff check src/               # Linting                      ║
║   curl localhost:8080/health    # Health check                 ║
║                                                                ║
║ POZIOMY:                                                       ║
║   L1 Hotfix:   --unit                                          ║
║   L2 Bug fix:  --unit --integration + test regresji           ║
║   L3 Feature:  pełne testy + manual test                      ║
║   L4 Critical: + E2E + paper trading                          ║
║   L5 Arch:     + performance + rollback test                  ║
║                                                                ║
║ RED FLAGS - STOP jeśli:                                        ║
║   - Testy nie przechodzą                                       ║
║   - Nie rozumiesz co zmieniasz                                 ║
║   - "Potem napiszę testy"                                      ║
║   - "To tylko mała zmiana"                                     ║
╚═══════════════════════════════════════════════════════════════╝
```
