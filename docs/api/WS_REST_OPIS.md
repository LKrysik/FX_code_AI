Opis Słowny Interfejsów WebSocket i REST

Cel i zakres
- Cel: przedstawić pełny, słowny opis działania interfejsów WebSocket i REST w systemie tradingowo-analitycznym, w tym zasady spójności, obsługę błędów, sesje strategii, subskrypcje danych i wskaźników oraz aspekty niezawodności.
- Zakres: zachowanie protokołów, semantyka odpowiedzi, idempotencja, taksonomia błędów, bezpieczeństwo, stabilność, limitowanie, odzyskiwanie połączeń i zalecane scenariusze integracji. Bez fragmentów kodu i schematów JSON.

Wspólne zasady dla WebSocket i REST
- Wersjonowanie i czas: każda odpowiedź zawiera pole wersji protokołu (np. 1.0) oraz znacznik czasu generacji po stronie serwera. Ułatwia to diagnostykę, korelację i porządkowanie zdarzeń.
- Envelopa odpowiedzi: odpowiedzi mają spójną strukturę semantyczną obejmującą typ komunikatu (sukces, błąd, status, dane, sygnał, alert), status operacji, ewentualny identyfikator żądania oraz część danych. Dzięki temu klient obsługuje oba kanały w ujednolicony sposób.
- Idempotencja: wybrane operacje, w szczególności uruchamianie sesji strategii, mogą być wykonywane w trybie idempotentnym. Gdy istnieje zgodny stan (tryb, zestaw instrumentów, stabilny skrót konfiguracji), serwer zwraca istniejący wynik zamiast tworzyć duplikat.
- Korelacja żądań: klient dołącza identyfikator żądania, a serwer odzwierciedla go w odpowiedzi. Pozwala to śledzić przepływ w logach i rozróżniać równoległe operacje.
- Taksonomia błędów: błędy klasyfikowane są do rozłącznych kategorii, m.in. validation_error, missing_strategy_config, invalid_session_type, strategy_activation_failed, session_conflict, authentication_required, service_unavailable, routing_error, handler_error, command_failed. Kategoria i komunikat są zwięzłe i jednoznaczne.
- Bezpieczeństwo: gdy to wymagane, operacje są uwierzytelniane tokenem. Brak lub nieważny token skutkuje odmową z kategorią authentication_required. W środowisku produkcyjnym komunikacja jest szyfrowana (HTTPS/WSS), a dane wrażliwe minimalizowane w logach.
- Spójność semantyczna: nazwy pól, struktur i statusów są spójne pomiędzy WebSocket i REST, co upraszcza implementację klientów oraz SDK.

WebSocket
- Przeznaczenie: kanał dwukierunkowy o niskich opóźnieniach do strumieniowania danych rynkowych i wskaźników, przekazywania sygnałów i alertów oraz sterowania sesjami strategii w czasie rzeczywistym.
- Nawiązanie połączenia: po udanym handshaku serwer komunikuje stan gotowości (połączony). Od tego momentu przyjmuje komendy oraz emituje odpowiedzi i komunikaty asynchroniczne.
- Model komunikacji: klient wysyła komendy (np. uruchomienie, zatrzymanie lub zapytanie o status sesji, subskrypcje strumieni), serwer odsyła odpowiedzi skorelowane z żądaniami oraz niezależne komunikaty danych, statusów i alertów, zależnie od kontekstu.
- Potwierdzenia i statusy: każda subskrypcja jest potwierdzana wyraźnym statusem (subscribed) wraz z echem parametrów. Zmiany stanu są informowane komunikatami statusowymi.
- Subskrypcje danych: obsługiwane są strumienie danych rynkowych dla wielu instrumentów oraz strumienie wskaźników dla pojedynczego instrumentu lub listy instrumentów. Serwer wysyła tylko aktualizacje wynikające ze zmian stanu lub nowych obliczeń.
- Heartbeat i stabilność: serwer odpowiada na zapytania heartbeat (pong) lub utrzymuje własny rytm sygnałów kontrolnych, co ułatwia wykrywanie problemów z łącznością. W warunkach przeciążenia stosowany jest mechanizm backpressure: komunikaty o niższym priorytecie mogą być opóźniane lub agregowane.
- Kolejność i priorytety: kolejność komunikatów jest gwarantowana w obrębie danego strumienia. Serwer nadaje priorytety, zapewniając pierwszeństwo sygnałom i alertom przed telemetrią o charakterze informacyjnym. Dla danych o charakterze „ostatni stan wygrywa” możliwe jest łączenie aktualizacji.
- Sesje strategii: uruchomienie sesji weryfikuje typ i konfigurację strategii; w trybie idempotentnym zwracana jest istniejąca, zgodna sesja. Zatrzymanie sesji kończy działanie strategii i zwraca końcowy status wraz z metadanymi. Zapytanie o status zwraca aktualny stan, parametry i podstawowe metryki.
- Obsługa błędów: błędy walidacji komend są klasyfikowane jako validation_error z czytelnym opisem. Konflikty przy uruchamianiu sesji skutkują session_conflict. Nieobsługiwany typ sesji to invalid_session_type, brak wymaganej konfiguracji to missing_strategy_config. Błędy warstwy usług i wykonania klasyfikowane są odpowiednio jako service_unavailable, routing_error, handler_error lub command_failed.
- Zamykanie połączeń: w razie poważnych problemów serwer może zamknąć połączenie, podając przyczynę. Klient powinien stosować ponowne łączenie z kontrolowanym opóźnieniem i odtwarzaniem stanu.
- Odzyskiwanie i rekonfiguracja: po ponownym połączeniu klient odtwarza subskrypcje i w razie potrzeby pobiera migawki przez REST, aby wyrównać stan. Dynamiczne dodawanie i usuwanie subskrypcji jest potwierdzane odpowiednimi statusami.
- Przepływ danych w systemie: komunikaty WebSocket są obsługiwane przez kontroler tradingowy i silnik wskaźników korzystające z wewnętrznej szyny zdarzeń i dostawcy danych rynkowych. Dane i sygnały przepływają do klienta w czasie rzeczywistym, a komendy sterujące trafiają do modułów wykonawczych.

REST API
- Przeznaczenie: interfejs do operacji nie-strumieniowych i transakcyjnych, takich jak zarządzanie sesjami, walidacja i obsługa konfiguracji strategii, pobieranie metadanych, migawek wskaźników, list instrumentów oraz punktów zdrowia systemu. REST uzupełnia WebSocket, zapewniając spójny model zasobów.
- Wersjonowanie: interfejs wersjonowany spójnie z WebSocket. Zmiany łamiące są publikowane w nowych wersjach, a starsze wspierane przez okres przejściowy.
- Konwencja odpowiedzi: odpowiedzi REST odwzorowują semantykę WebSocket (typ komunikatu, status, dane, wersja i znacznik czasu), co ułatwia jednolitą obsługę po stronie klienta.
- Zasoby i operacje: 
  • Sesje: tworzenie lub uruchamianie sesji strategii, pobieranie statusu, zatrzymywanie, przegląd historii i podstawowych metryk. Semantyka zgodna z komendami WebSocket, w tym idempotencja i rozstrzyganie konfliktów.
  • Strategie: walidacja konfiguracji z jasnym raportem naruszeń oraz zarządzanie schematami i wartościami domyślnymi.
  • Rynki: pobieranie listy dostępnych instrumentów i parametrów rynkowych oraz informacji o dostępnych strumieniach danych.
  • Wskaźniki: pobieranie migawek i metadanych wskaźników, w tym wymaganego okna danych i oczekiwanego opóźnienia obliczeń.
  • Zdrowie i meta: punkty stanu zdrowia i gotowości oraz informacje o wersjach usług i środowisku wykonawczym.
- Idempotencja i bezpieczeństwo metod: operacje odczytu są bezpieczne i nie wywołują skutków ubocznych. Operacje modyfikujące mogą wykorzystywać klucze idempotencji dla pewności raz-wykonania przy ponawianiu. Dostęp wymaga poprawnego uwierzytelnienia i, jeśli dotyczy, autoryzacji.
- Filtrowanie, paginacja i sortowanie: standardowe kryteria filtrowania po czasie, instrumentach, stanie sesji oraz typie zasobu. Paginacja oparta o kursory lub limit i offset. Domyślny porządek po czasie utworzenia lub aktualizacji, z opcją wyboru kolumny sortowania.
- Mapowanie błędów na HTTP: błędy walidacji odpowiadają statusom klienta (np. żądanie niepoprawne), brak uwierzytelnienia lub uprawnień przekłada się na odpowiednie kody odmowy, konflikty stanu na konflikt zasobu, a problemy serwerowe na kategorie błędów 5xx, z ewentualnymi wskazówkami ponowienia.
- Limitowanie i ponawianie: serwer komunikuje limity żądań i okna resetu. Klient ponawia tylko operacje bezpieczne lub te, które są kontrolowane poprzez idempotencję, stosując strategię kontrolowanego opóźnienia i losowego rozproszenia.
- Spójność z WebSocket: klient może pobrać migawkę stanu przez REST i następnie dołączyć do strumienia aktualizacji przez WebSocket. Cykl życia sesji i semantyka błędów są zgodne w obu kanałach.

Scenariusze integracji
- Uruchomienie strategii i streamingu: klient waliduje konfigurację strategii przez REST, uruchamia sesję w trybie idempotentnym (REST lub WebSocket), otrzymuje identyfikator sesji, a następnie subskrybuje strumienie danych rynkowych i wskaźników przez WebSocket. Potwierdzenia subskrypcji i statusy sesji wskazują gotowość i bieżący stan.
- Szybkie wznowienie połączenia: po utracie połączenia WebSocket klient wznawia kanał, odtwarza subskrypcje i, jeśli konieczne, pobiera migawki przez REST, aby wyrównać stan. Następnie znów polega na strumieniu aktualizacji.
- Obsługa błędów strategii: w przypadku niepowodzenia aktywacji strategii lub błędów wykonawczych klient prezentuje alert użytkownikowi, zbiera szczegóły diagnostyczne (np. status i podstawowe logi dostępne przez REST) i umożliwia korektę konfiguracji lub ponowną próbę.

- Budowa i Walidacja Strategii Grafowej (v2):
  1. UI (Canvas) przy każdej zmianie w grafie (dodanie węzła, połączenie) wysyła całą strukturę grafu do backendu przez REST na endpoint `POST /strategies` z flagą `validate_only: true`.
  2. Backend (StrategyEvaluator) symuluje wykonanie grafu, sprawdzając poprawność połączeń, typów danych i logiki biznesowej.
  3. Serwer zwraca odpowiedź JSON z listą błędów lub ostrzeżeń, z których każde jest przypisane do konkretnego ID węzła w grafie.
  4. UI odbiera odpowiedź i podświetla w grafie węzły zawierające błędy, wyświetlając przy nich odpowiednie komunikaty.
  5. Gdy użytkownik jest zadowolony ze strategii i walidacja przechodzi pomyślnie, klika "Zapisz". UI wysyła ten sam graf na `POST /strategies` bez flagi `validate_only`, co powoduje trwały zapis strategii w bazie danych.


Niezawodność i obserwowalność
- Logowanie i korelacja: identyfikatory żądań przesyłane przez klienta są zapisywane w logach serwera i odzwierciedlane w odpowiedziach. Wspólny znacznik czasu i wersja protokołu ułatwiają korelację między kanałami.
- Metryki i alerting: mierzone są czasy odpowiedzi, przepływ i opóźnienia w strumieniach, wykorzystanie zasobów, częstość błędów oraz stabilność połączeń. Progi wyzwalają alerty operacyjne.
- Zgodność czasowa: system korzysta ze stabilnego źródła czasu, a klient, jeśli to możliwe, synchronizuje zegar, aby poprawnie interpretować znaczniki czasu i porządkować zdarzenia.

Słownik statusów i kategorii błędów
- Kluczowe statusy po stronie WebSocket: połączony, subscribed, unsubscribed, status sesji, heartbeat i odpowiedź typu pong, alert lub sygnał.
- Kategorie błędów: validation_error, missing_strategy_config, invalid_session_type, strategy_activation_failed, session_conflict, authentication_required, service_unavailable, routing_error, handler_error, command_failed. Każda odpowiedź błędu zawiera zwięzły opis problemu i, jeśli możliwe, wskazówki naprawcze.

Uwagi końcowe (koniecznie wdrożyć!)
- Zaleca się stosowanie jednolitej warstwy klienckiej obsługującej oba kanały zgodnie z opisanymi tu zasadami. W razie doprecyzowania planowanych zasobów REST (konkretne ścieżki i nazwy pól) sekcję REST można rozszerzyć o bardziej szczegółowy opis semantyki zasobów bez wprowadzania fragmentów kodu.
