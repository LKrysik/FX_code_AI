# Driver - Prompty i Pytania

## Rozpoczęcie iteracji

```
Rozpoczynam iterację [N].

1. Status środowiska:
   - curl localhost:8080/health → ?
   - curl localhost:3000 → ?
   - python run_tests.py → X/Y PASS

2. Metryki obszarów (z WORKFLOW.md):
   [tabela metryk]

3. Wybieram obszar: [X] bo ma najniższą średnią / blokuje inne.

4. Zadania dla Executorów:
   [lista z AC/DoD]
```

## Pytania weryfikacyjne (używaj regularnie)

### Status zadania
```
Jaki jest status [zadania X]?
- Które AC są spełnione? Pokaż output testów.
- Które AC nie są spełnione? Dlaczego?
- Jakie masz blokery?
```

### Weryfikacja kodu
```
Sprawdź kod pod kątem:
1. grep -rn "TODO\|FIXME" [zmienione pliki] → wynik?
2. grep -rn "NotImplementedError" src/ → wynik?
3. grep -rn "pass$" [zmienione pliki] → wynik?
4. Czy są mocki w produkcyjnym kodzie?
```

### Weryfikacja testów
```
Stan testów:
1. python run_tests.py → ile PASS/FAIL?
2. Czy nowe testy pokrywają AC?
3. Czy są regresje w starych testach?
Pokaż pełny output.
```

### Wykrywanie halucynacji
```
Twierdzisz że [X] działa. Pokaż dowód:
- Output testu
- Output curl
- Screenshot (jeśli UI)
Bez dowodu nie akceptuję.
```

### Problemy i ryzyka
```
Jakie problemy/ryzyka widzisz?
- W kodzie który zmieniasz
- W architekturze
- W zależnościach
- W wydajności

Format: Problem | Plik:linia | Severity | Propozycja
```

### Pomysły i feedback
```
Executor, potrzebuję twojego wkładu:
1. Co byś poprawił w tym obszarze?
2. Jakie widzisz możliwości optymalizacji?
3. Co cię frustruje w obecnym kodzie?
4. Jakie ryzyka widzisz na przyszłość?
```

## Zamknięcie iteracji

```
## RAPORT ITERACJI [N]

### A. Status środowiska
- Backend: [output]
- Frontend: [output]
- Testy: [X/Y PASS]

### B. Completion rate
| Zadanie | AC% | DoD% | Status |
|---------|-----|------|--------|
| T1 | 100% | 100% | DONE |
| T2 | 60% | 75% | PARTIAL |

**Completion: X/Y zadań (Z%)**

### C. Metryki przed/po
| Obszar | Przed | Po | Zmiana |
|--------|-------|-----|--------|
| [X] | 5/10 | 6/10 | +1 |

### D. Problemy zidentyfikowane
[lista z pliki:linia]

### E. Następna iteracja
- Obszar: [Y]
- Uzasadnienie: [najsłabszy / bloker]
- Zadania: [lista]

GOTO iteracja [N+1]
```

## Eskalacja do właściciela

```
## ESKALACJA: [temat]

**Przyczyna eskalacji:**
[ ] Zmiana architekturalna (>3 obszary)
[ ] Usunięcie funkcjonalności
[ ] Zmiana logiki biznesowej
[ ] WGP spada 2 iteracje
[ ] Sprzeczne wymagania

**Kontekst:**
[opis sytuacji]

**Opcje:**
1. [A] - konsekwencje: [...]
2. [B] - konsekwencje: [...]

**Moja rekomendacja:** [X]

**Potrzebuję:** decyzji właściciela
```

## Tworzenie dokumentacji biznesowej

```
## BUSINESS_GOALS.md

### Cel główny
[cel z perspektywy tradera]

### Mierzalne cele
| Cel | Metryka | Obecna wartość | Docelowa |
|-----|---------|----------------|----------|
| Accuracy | % poprawnych sygnałów | ?% | >80% |
| Latency | czas reakcji | ?ms | <1000ms |
| Uptime | dostępność | ?% | >99.9% |

### Priorytety (Q[X])
1. [najważniejsze]
2. [drugie]
3. [trzecie]

### Ryzyka biznesowe
- [ryzyko] → [mitygacja]
```

## Porządkowanie dokumentacji

```
Audyt dokumentacji:

1. Sprawdź docs/:
   - Które pliki są aktualne?
   - Które są przestarzałe?
   - Które się duplikują?

2. Akcje:
   - USUŃ: [lista przestarzałych]
   - AKTUALIZUJ: [lista nieaktualnych]
   - KONSOLIDUJ: [lista duplikatów → jeden plik]

3. Weryfikacja:
   - Czy docs odzwierciedla rzeczywistość kodu?
   - Czy ścieżki plików są poprawne?
```
