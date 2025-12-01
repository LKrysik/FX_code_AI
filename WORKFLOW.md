# Workflow Pracy Claude - FXcrypto

## Cel Biznesowy (Nadrzędny)

**Dostarczenie funkcjonalnego narzędzia do wykrywania pump-and-dump z łatwym interfejsem UI.**

Kluczowe funkcjonalności:
1. **Strategy Builder** - tworzenie strategii wykrywających pump/dump
2. **Backtesting** - testowanie strategii na danych historycznych
3. **Sygnały i transakcje** - generowanie i logowanie sygnałów
4. **Observability** - pełne logowanie błędów, brak maskowania

---

## Cykl Pracy (Obowiązkowy)

### FAZA 1: DIAGNOZA (przed jakąkolwiek zmianą)

```
1. Uruchom wszystkie usługi (backend, frontend, QuestDB)
2. Zweryfikuj że działają:
   - curl http://localhost:8080/health → musi zwrócić {"status": "healthy"}
   - curl http://localhost:3000 → musi zwrócić HTML
   - python scripts/dev_tools.py status → wszystkie [OK]
3. Jeśli coś nie działa → NAPRAW TO NAJPIERW
```

### FAZA 2: IDENTYFIKACJA PROBLEMU

```
1. Wybierz JEDEN konkretny problem do naprawy
2. Udokumentuj problem:
   - Co nie działa? (konkretny endpoint, komponent, funkcja)
   - Jak to zweryfikować? (curl, test, screenshot)
   - Jaki jest oczekiwany rezultat?
3. Uzasadnij biznesowo: Dlaczego to jest ważne dla celu (pump/dump detection)?
```

### FAZA 3: TEST NAJPIERW (Red-Green-Refactor)

```
1. NAPISZ TEST który FAILUJE (pokazuje problem)
   - Uruchom test → musi być RED (failing)
   - Pokaż output testu jako dowód
2. NAPRAW KOD
3. URUCHOM TEST PONOWNIE → musi być GREEN (passing)
   - Pokaż output testu jako dowód
4. URUCHOM WSZYSTKIE TESTY → muszą przejść
   - python run_tests.py --fast
   - Pokaż output jako dowód
```

### FAZA 4: WERYFIKACJA (Definition of Done)

```
Zmiana jest UKOŃCZONA tylko gdy WSZYSTKIE są spełnione:
[ ] Test jednostkowy przechodzi (output pokazany)
[ ] Wszystkie istniejące testy przechodzą (output pokazany)
[ ] Backend nie ma nowych błędów w logach
[ ] Frontend renderuje się bez błędów w konsoli (screenshot jeśli UI)
[ ] Curl/API call pokazuje oczekiwany rezultat (output pokazany)
```

### FAZA 5: DOKUMENTACJA

```
1. Zaktualizuj CLAUDE.md jeśli zmiana architekturalna
2. Zaktualizuj testy jeśli zmiana API
3. Dodaj komentarz w kodzie jeśli decyzja nieoczywista
```

### FAZA 6: NASTĘPNY KROK

```
1. Wróć do FAZY 2 z następnym problemem
2. Priorytetyzuj według wpływu na cel biznesowy
```

---

## Reguły Bezwzględne

### NIGDY:
- Nie ogłaszaj sukcesu bez dowodu (output testu, curl, screenshot)
- Nie wprowadzaj zmian bez uruchomienia testów
- Nie naprawiaj wielu rzeczy naraz (1 problem = 1 iteracja)
- Nie zakładaj że coś działa - SPRAWDŹ

### ZAWSZE:
- Najpierw test który failuje, potem fix
- Pokazuj output jako dowód
- Uzasadniaj zmiany biznesowo
- Małe kroki z weryfikacją po każdym

---

## Priorytetyzacja Biznesowa

### Krytyczne (blokują użycie):
1. Frontend się uruchamia i renderuje
2. Strategy Builder pozwala tworzyć strategie
3. Backtesting generuje sygnały na danych testowych
4. Wyniki są widoczne w UI

### Ważne (poprawiają użycie):
1. Wskaźniki obliczają się poprawnie
2. Strategie można zapisywać/ładować
3. Logi są czytelne i pomocne

### Nice-to-have:
1. Optymalizacja wydajności
2. Dodatkowe wskaźniki
3. Eksport danych

---

## Narzędzia Weryfikacji

```bash
# Status usług
python scripts/dev_tools.py status

# Health check backend
curl http://localhost:8080/health

# Uruchom testy
python run_tests.py --fast

# Generuj dane testowe
python scripts/dev_tools.py gen-data

# Sprawdź bazę danych
python scripts/dev_tools.py check-db
```

---

## Checkpointy (wymagają mojego potwierdzenia)

Po każdej naprawie KRYTYCZNEGO problemu - weryfiku i uzasadnij biznesowo i ustal dowody że zmiany działają i są zgodne z celem biznesowym i poprawiają funkcjonalnośc dla traderów. Zawsze planuj kolejne działania i weryfikację kod pod wzgledem osiagnięcia zamierzonego celu biznesowego. 
Dla problemów WAŻNYCH - kontynuuj jeśli testy przechodzą, jezeli nie przechodzą to przejdź do szukania rozwiązania problemu, możesz też rozbudować logowanie błędów w celu szybszego wykrycia przyczyny. 
Zawsze mierz zgodność rozwiazania z celem biznesowym.Ustal sobie wskaźniki w każdym obszarze tego rozwiązania (trading, bactesting, strategy builder, wskaźniki, UI) które mierzą poprawność działania kodu 1-10, zgodność z celami biznesowymi 1-10, użyteczność kodu dla traderów 1-10, prostota użycia 1-10, prostota utrzymania kodu 1-10, łatwość konfiguracji programu dla traderów 1-10, wydajność programu 1-10,  obervability 1-10, ryzyka 1-10. Na tej podstawie planuj kolejne działania. Dokumentuj postepy tych wskaźników podczas checkpointów. Musisz też oceniać na ile sensone jest wprowadzanie nowych zmian oraz funckjonalności, czy lepiej skupić się na poprawie istniejących rozwiązań oraz czy wprowadzanie nowych rozwiazań ma sens biznesowy (czy realny, czy znikomy, czy negatywny i na ile). Posłuży to do wyboru ścieżki rozwoju projektu.
Przygotuj lub aktualizuj ścieżkę rozwoju projektu w oparciu o te wskaźniki i cele biznesowe i zgodnosc z celami bizneswowymi. 
Jeżeli pojawią się istotne przesłanki to aktualizuj dokument WORKFLOW.md w celu poprawy procesu pracy nad projektem ale musisz to uzasadnić sobie biznesowo i technicznie. Jeżeli zmiany w workflow.md przyniosą dla ciebie poprawę efektywności pracy i lepsze wyniki biznesowe to wprowadź je.