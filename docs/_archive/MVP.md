
# USER REQUIREMENT: USER_REC_01


## FRONTEND

### /strategy-builder


  Strategie są zapisywane config/strategies/ jako json
  Stretegy Builder ma dwie zakładki, jedną z listą wszystkich strategi odczytanyumi z plików config/strategies/ , w momencie wczytania strategie są validowane (czy poprawnie stworzona, czy warianty wskaźników użyte w strategii istnieją), jeżeli któraś ma bład to jest oznaczana jako błedna. Strategie można edytować, albo kopiować/klonować oraz usuwać za pomocą tej listy
  W drugiej zakładce jest właściwy Builder gdzie się tworzy nowe strategie albo modyfikuje istniejące. 

  Frontend otrzymuje listę strategii przez GET rest api , backend dostarcza liste strategii odczytując wszystkie zapisane strategie w postaci json w onfig/strategies/
  W Fronted można edytować wybraną strategię, na liście strategii przy każdej strategii jest przyczisk Edytuj, wtedy otwiera sie zakładka z edycją wskazanej Strategii - klikając Edytuj pobierana jest cala definicja wybranej strategii przez GET rest api (pobierz definicję wybranej strategii o takim i takim identyfikatorze) - backend odczytuje definicję wybranej strategii  (o określonym identyfikatorze) z pliku json w config/strategies/
  Każda strategia ma unikalny identyfikator który jest używany jako nazwa pliku json gdzie zapisywana jest definicja strategii, to ułatwia identyfikację.
  W strategii zapisane są też identyfikatory wariantów wskaźnikików systemowych które są użyte w definicji strategii, 

#### Logika

    ✅ 5-sekcyjna struktura strategii (S1/Z1/O1/ZE1,E1) - Bardzo jasna i logiczna
    W strategii używane są jedynie warianty wskaźników odczytanych z config/indicators/

    1
    * SECTION 1: SIGNAL DETECTION (S1) - użytkownik za pomoca wskaźników określa kiedy będzie można uznać że mamy sygnał wykrycia pump - czyli użytkownik ustali, ze wskaźnik W1 > 0.50 a wskaźnik R1 < 100, wskaźnik W2 między 0.2 a 0.8, jeżeli warunek spełniony to mamy wykrycie pump i dany symbol jest blokowany i zaczyna się liczenie innych wskaźników. Sygnał wykrycia jeżeli zostanie ustanowiony na danym Symbolu blokuje możliwość zrobienia tego samego innym strategiom. 
    Jeżeli zostanie wykryty sygnal to zapisywane są wartości wskaźników użytych do wykrycia sygnału. 
    W tej sekcji można dodawać wiele warunkow na różne wskaźniki. Dodając nowy warunek wybiera się się z listy wskaźnikow ogólnych (wariant wskaźnika systemowego) oraz typu risk (wariant wskaźnika systemowego)

    2. SECTION 3: SIGNAL CANCELLATION (O1) Odwołanie sygnału (01) - Pozwala włączyć dwie opcje 
    a) za pomocą warunków zdefiniowanych przez wskaźniki określamy czy sygnał zostanie odwołany (tylko w przypadku kiedy nie otwarto zlecenia). spełnienie jakiś warunkow na wskaźnikach na przykład R1 wzrasta > 150  AND  W10 < 0.1 wtedy odwołanie
    b) timeout po jakim nastąpi odwołanie sygnału S1 
    Obie opcje są opcjonalne i mogą działać równocześnie 
    Możliwe jest też ustawienie cool down dla tej strategi po odwołaniu. Jest to opcjonalne.
    Jeżeli włączone jest odwoływanie sygnalu za pomocą warunków to zapisywane są wartości wskaźników użytych do odwołania sygnału
    W tej sekcji można dodawać wiele warunkow na różne wskaźniki. Dodając nowy warunek wybiera się się z listy wskaźnikow ogólnych (wariant wskaźnika systemowego) oraz typu risk (wariant wskaźnika systemowego)

    3.
    * SECTION 2. ORDER ENTRY (Z1) Wykrycie momentu złożenia zlecenia (Z1) - za pomocą warunków zdefiniowanych przez wskaźniki określamy moment złożenia zlecenia (tylko gdy Sygnal (S1) jest aktywny dla danej strategii) I Na przykład gdy WE1 > 0.4 AND RZ < 40 wtedy za pomocą odpowiednich wskaźników (dedykowanych) do wyliczania ceny zlecenia CZ tworzymy zlecenie  (takich wskaźników będziemy mieli dużo) , użytkownik będzie decydował w Strategy Builder którego wskażnika CZ użyć (może nie wybierać wskaźnika do ceny zlecenia wtedy zlecenie będzie po każdej cenie), do tego do zlecenia będzie używany wskaźnik Stop Loss (ST) oraz Take Profit (TP), użytkownik wybiera który wskaźnik ST i TP użyć w danej strategi do skladania zlecenia (ST - jest w tym wypadku opcjonalne)
    Wskaźniki typu "ryzyko" mogą służyc do Risk-adjusted sizing (większe ryzyko = mniejsza pozycja). czyli pomniejszania lub zwiększa wielkość zlecenia (Possition Size). O ile zostanie to ustawione w strategii. Wtedy określamy wartości brzegowe danego wskaźnika ryzyk czyli dla wartości ryzyka = 20 określamy procent wielkości pozycji otwarcia na przyklad 120% pozycji (czy to procentowej czy fixed), a jeżeli ryzyko będzie = 70 to Position Size zlecenia będzie 55% (pomniejszone), i przeliczamy dla wartości pośrednich , czyli określamy wartość i procent Position Size.
    Jeżeli określimy że dla ryzyka = 20 mamy 120% , to nie skaluje sie niżej, że dla ryzyka = 10 mamy 150% ceny , tak samo dla ryzyka 90 nie skaluje się do np 35%, natomiast wartości pośredne są wyliczane liniowo, na przyklad ryzyko = 30 to wielkości pozycji zlecenia to około 105% itd, 
    Jeżeli zlecenie zostanie zrealizowane (zawarte) to zapisywane są informacje o cenie zawarcia i wielkości, ryzyku, oraz innych wybranych parametrach, ta wartość jest używana przez wskaźniki wyliczania ceny zamknięcia (służą one jako wartość bazowa do określenia ceny zamknięcia pozycji)
    Zapisywane są pozostałe wartości wskaźników użytych do wykrycia momentu złożenia zlecenia

    Jak w fronted to wygląda:
    W pierwszej części definiowanie warunków do wykrycia sygnału Z1 - Dodając nowy warunek wybiera się się z listy wskaźnikow ogólnych oraz typu risk
    Poniżej wlącza się stop loss (V_SL) i/lub take profit (V_TP)

    W Z1 można też ustalic  time out po którym zlecenie zostanie zamknięte po każdej cenie (time out liczony w sekundach)

    LS
    Jeżeli włączony jest stop loss to wybiera się wskaźnik (wariant wskaźnika systemowego) wyliczający wartość stop loss (V_SL) , 
      Opcja (można włączyć):
    Skalowanie stop loss V_SL w zależności od wybranego wariantu wskaźnika typu ryzyko RZ - określamy skalowanie wartości V_SL w zależności od RZ - mamy 4 pola do ustalenia w skalowaniu , określamy dwie granice ryzyka RZ górną i dolną oraz dla tych granic podajemy jak wartość V_SL będzie zwiększona lub pomniejszone 
    Przykładowy wygląd:
    granica dolna RZ = 30 (małe ryzyko), skalowanie: V_SL * 150%
    górna granica RZ = 156 (duże ryzyko), skalowanie: V_SL * 60%
    Dla wartości ryzyka RZ międzye 30 a 156 będzie odpowiednio skalowane w przedziale od 150% do 60% (ale nie więcej i nie mniej)

    TP
    Jeżeli włączony jest take profit to wybiera się wskaźnik (wariant wskaźnika systemowego) wyliczający wartość take profit do złożenia zlecenia (V_TP) , 
      Opcja (można włączyć):
    Skalowanie take profit V_TP w zależności od wybranego wariantu wskaźnika typu ryzyko RZ - określamy skalowanie wartości V_TP w zależności od RZ - mamy 4 pola do ustalenia w skalowaniu , określamy dwie granice ryzyka RZ górną i dolną oraz dla tych granic podajemy jak wartość V_TP będzie zwiększona lub pomniejszone 
    Przykładowy wygląd:
    granica dolna RZ = 50 (małe ryzyko), skalowanie: V_TP * 120%
    górna granica RZ = 126 (duże ryzyko), skalowanie: V_TP * 80%
    Dla wartości ryzyka RZ międzye 30 (przykład) a 156 (przykład) będzie odpowiednio skalowane w przedziale od 150% do 60% (ale nie więcej i nie mniej)

    PS
    Wartość zlecenia (Position Size)
    Mamy do wyboru Fixed oraz Percent 
    Fixed to określona wartość
    Percent to procent całego dostepnego portfela
      Opcja (można włączyć):
    Skalowanie Position Size PS w zależności od wybranego wariantu wskaźnika typu ryzyko RZ - określamy skalowanie wartości PS w zależności od RZ - mamy 4 pola do ustalenia w skalowaniu , określamy dwie granice ryzyka RZ górną i dolną oraz dla tych granic podajemy jak wartość PS będzie zwiększona lub pomniejszone 
    Przykładowy wygląd:
    granica dolna RZ = 50 (małe ryzyko), skalowanie: PS * 120%
    górna granica RZ = 126 (duże ryzyko), skalowanie: PS * 80%
    Dla wartości ryzyka RZ międzye 50 (przykład) a 126 (przykład) będzie odpowiednio skalowane w przedziale od 150% do 60% (ale nie więcej i nie mniej)



    4
    * SECTION 4: ORDRE CLOSING DETECTION (ZE1) Wykrycie momentu zamknięcia zlecenia (ZE1) (realizacja zysku inaczej niż przez take profit, ale może działać równolegle do take profit) - za pomocą warunków zdefiniowanych przez wskaźniki określamy moment zamknięcia zlecenia (tylko gdy Sygnal (S1) jest aktywny) I Na przykład gdy WZ1 <= 0.6 oraz RZ > 80 wtedy za pomocą odpowiednich wskaźników (wariant wskaźnika systemowego).
    W ZE1 wybieramy czy zamknięcie zlecenia jest po każdej cenie czy po cenie wyliczonej przez odpowiedni wskaźni V_CO (typ close order price)

      Opcja (można włączyć):
    Skalowanie wartości V_CO w zależności od wybranego wariantu wskaźnika typu ryzyko RZ - określamy skalowanie wartości V_CO w zależności od RZ - mamy 4 pola do ustalenia w skalowaniu , określamy dwie granice ryzyka RZ górną i dolną oraz dla tych granic podajemy jak wartość PS będzie zwiększona lub pomniejszone 
    Przykładowy wygląd:
    granica dolna RZ = 20 (małe ryzyko), skalowanie: V_CO * 105% (zlecenie po lepszej cenie - więcej chcemy zarobić)
    górna granica RZ = 126 (duże ryzyko), skalowanie: V_CO * 95% (zlecenie po gorszej cenie, nie chcemy ryzykować)
    Dla wartości ryzyka RZ międzye 20 (przykład) a 126 (przykład) będzie odpowiednio skalowane w przedziale od 150% do 60% (ale nie więcej i nie mniej)





    5
    * SECTION 5: EMERGENCY EXIT Emergency Exit (E1) - także określane warunkami za pomocą wskaźników , na przyklad jeżeli wskaźnik Ryzyko1 > 200 oraz WT1 < 0.01 to wykonywana jest operacja emergency exit, czyli jeżeli złożono zlecenie ale nie doszło jeszcze do skuktu to natychmiast anulowane jest, jeżeli zlecenie doszlo do skutku to natychmiast pozycja zamykana jest po cenie jaka jest oferowana, jeżeli nie zlożono zlecenia ale otwarty jest sygnał S1 to jest odwoływny i robiony jest cooldown liczony w minutach określony przez użytkownika w strategii - czas kiedy na danym symbolu dana strategia nie monitoruje
    Cancel pending order (if not yet filled)
    Close position at market (if order filled)
    Jeżeli nastapi wykrycie Emergency Exit to zapisywane są wartości wskaźników użytych do Emergency Exit




    Wszystkie warunki mają warunek "AND" (add condition) - obecnie usunąć warunki "OR" 
    Operatory jakie można używać >=, >, <=, <


    Model " 5-sekcyjna struktura strategii (S1/Z1/O1/ZE1,E1) " jest event-driven, a nie sekwencyjny:
    S1 (Sygnał) → trigger startowy (jednorazowy)
    Z1 (Entry) → aktywuje się tylko gdy S1 jest aktywny
    O1/ZE1/E1 → mogą być oceniane równolegle po otwarciu pozycji
    2. Równoległość jest MOŻLIWA i NATURALNA
    3. Model "sztywnymi 5 filarami" - to STATE MACHINE

    Kluczowe punkty:

    E1 może przerwać w KAŻDYM momencie (najwyższy priorytet)
    O1 działa tylko w stanie SIGNAL_DETECTED
    ZE1 działa równolegle z TP/SL w stanie POSITION_OPEN

    Priorytet 1: E1 (emergency) - przerywa wszystko
    Priorytet 2: O1 (cancel) - tylko przed entry
    Priorytet 3: ZE1/TP/SL (exit) - równolegle


  #### Trading z Strategy
  
    Bardzo ważne, w systemie musi być konfiguracja ogólna która pozwala na wybór czy i ile strategii w danym momencie może mieć otwarte sygnały S1 
    na przyklad 1 - czyli jeżeli jedna strategia wykryje pump i będzie miała otwarty sygnał to pozostale nie mogą otworzyć, jeżeli 2 to dwie strategie mogą mieć na raz otwarte sygnaly i móc składać zlecenia. 

    Ta strategia która jest pierwsza ta blokuje dla siebie slot z dostepnych, po zakończeniu (zamknięciu sygnału, czy zakonczeniu procesu) slot jest zwlaniany 
    Można robić kopie strategii by przyspieszyć proces tworzenia nowej wersji jeżeli potrzeba
    Sloty to ustawienie globalne dla wszystkich strategii , na danym sygnale tylko jedna strategia może mieć otwarty sygnał w tym samym czasie. 



    lockowaniu symbolu - oznacza że jakaś strategia ma otwarty sygnał na danym symbolu - oznacza to, że symbol znika z monitorowania dla innych strategii do momentu przerwania sygnału (odwołanie, emergency, zakoczenie procesu zlecenie sprzedaży)



#### Interfejs
  strategy-builder ma dwie zakładki:
  - zakładka z listą strategii (Strategies, backend odczytje wszystkie strategie z config/strategies i przekazuje do frontend do wyświetlnia na liście) gdzie przy każdej strategii (na liście) jest przycisk edit (umożliwia edycje danej strategii w zakładce Edytor Strategii) / copy / delete (usuwa z listy strategię oraz jej definicję json w config/strategies )
  - Edytor Strategii gdzie można stworzyć nową strategię lub modyfikować istniejącą (są przyciski Zapisz - zapisuje jako json w config/strategies, Validate (weryfikuje poprawność), anuluj - przerywa proces)


# USER REQUIREMENT: USER_REC_02

## /indicators

Implementacja  niezawodnych wskaźników dla Strategy Builder opartych na istniejącym StreamingIndicatorEngine

### Wskaźniki systemowe 

Wskaźniki systemwe do implementacji
- **GRUPA A (Priorytet 1):** `max_price()`, `min_price()`, `first_price()`, `last_price()`, `sum_volume()`, `avg_volume()`, `count_deals()`, `TWPA()`, `VWAP()`
- **GRUPA B (Priorytet 2):** `Velocity()`, `Volume_Surge()`, `Volume_Concentration()`
**prawdziwymi algorytmami matematycznymi** opisanymi w `INDICATORS_TO_IMPLEMENT.md`. Zaczniemy od kluczowych grup (A, B, C), które są fundamentem dla reszty.



Rozwiązane Problemy Krytyczne:
-  **Problem 1: Semantyka Okien Czasowych** - Standaryzacja na `t1 > t2` gdzie `t1` to sekundy wstecz dla startu, `t2` dla end. Przykład: `TWPA(300, 0)` = "od 5 minut temu do teraz"
-  **Problem 3: Luka Cache Czasowa** - Time-bucketed cache klucze z timestamp buckets (60s granularity): `"TWPA:BTC_USDT:1m:300:0:1727209200"`

- **Cache Obliczeń:** Obliczanie wskaźników jest kosztowne. Jeśli 10 strategii używa `RSI(14)` dla `BTC_USDT`, nie chcemy liczyć go 10 razy. Wprowadzimy warstwę cache (z użyciem Redis), która będzie przechowywać wyniki obliczeń. Przed każdym obliczeniem system sprawdzi, czy wynik dla danego wskaźnika, symbolu i parametrów jest już w cache. Jeśli tak, pobierze go stamtąd, oszczędzając moc obliczeniową.



### Logika - warianty 

Tylko warianty wskaźników mogą być używane w Strategiach

Warianty wskaźników zapisywane są w config/indicators/ w podziale na typy (ryzyko, stop loss, take profit, general, price, close order price ) jako json 
W zakładce "Indicator Varianst" jest tylko lista wariantów wskaźników odczytana z config/indicators/. Wskaźniki (warianty) są weryfikowane (validowane) podczas wczytywania listy czy są poprawnie skonfigurowane w stosunku do wskaźników systemowych (czy parametry mają odpowiednio zapisane zgodnie z wymaganiami danego wskaźnika systemowego). Wskaźniki można edytować, kopiować, lub usunąć, edycja powoduje zmianę definicji w pliku json odpowiedniego wariantu, usunięcie powoduje usunięcie pliku json danego wariantu. Skopiowanie wariantu wskaźnika powoduje utworzenie nowego pliku json. Każdy wariant wskaźnika dostaje swój unikalny identyfikator (niepowtarzalny), ktory będzie użyty w strategiach do wskazania danego wariantu. Używamy unikalnego identyfikatora w programie do identyfikacji wariantów wskaźników
W zakładce "Create Variant" znajduję się lista System Indicators  w podziale na typy (all types, general, risk, price, stop loss, take profit, close order)
Tu jest list wszystkich wskaźników systemowych (System Indicators) wraz z nazwą, opisem i opisem parametrów. 





# USER REQUIREMENT: USER_REC_03


GOAL_03 nie został osiągnięty, wskaźniki mimo że fizycznie są w 
@/src/domain/services/streaming_indicator_engine.py 
to nie są dostepne w frontend żeby utworzyć ich wariant w indicators -> create variant -> system indicators

Założenie jest takie że frontend (strona  indicators ) otrzymuje  liste wskaźników systemowych backend które są zaimplementowane w streaming_indicator_engine.py  wraz z informacjami jakie parametry są konieczne do utworzenia wariantu i jakiego typu to jest wskaźnik. 


Należy modyfikować streaming_indicator_engine.py tak żeby wskaźniki systemowe (algorytmy) rejestrować w streaming_indicator_engine.
Każdy wskaźnik musi mieć swoją definicję, czyli jakie parametry wymaga wraz z ich opisem czym są (posłuży to do tworzenia wariantów)


Obbsługa wskaźników przez if elif też nie jest elegancka, jeżeli dodajemy wskaźnik systemowy to można to lepiej rozwiazać niż hardkodować nazwy 

  # Technical indicators (fallback to full calculation)
        if indicator_type == "SMA":
            return sum(prices) / len(prices)

        elif indicator_type == "EMA":
            return self._calculate_ema(prices, period)

        elif indicator_type == "RSI":
            return self._calculate_rsi(prices, period)



Tak więc do zmiany jest
1) Sposób dodawania wskaźnikow systemowych do streaming_indicator_engine i ich obsługa. Rejestracja algorytmu wskaźnika systemowego w streaming_indicator_engine (zarejestrowany wskaźnik jest rejestrowany w odpowiedniej grupie general, risk, stop loss price, take profit price, order price, close price)
2) get rest api z listą wskaźników systemowych  zarejestrowanych w streaming_indicator_engine oraz ich parametrami 
3) frontend otrzymouje "get rest api z listą wskaźników systemowych" i wyswietla wskaźniki systemowe w System Indicators
4) get rest api z listą wariantów wskaźnikow odczytaną z config/indicators. Odczytanie wszystkich json. Każdy json to oddzielny wariant wskaźnika systemowego 
5) Tworząc w frontend wariant wskaźnika systemowego, wysylane jest do backend post rest api dotyczące wywołania zapisu wariantu wskaźnika, backend wtedy zapisuje konfigurację takiego wariantu jako oddzielny plik json w config/indicators. Każdy wariant ma swój unikalny identyfikator, ten identyfikator będzie użyty do zapisu definicji warianktu w json - będzie zapisany pod nazwą general_[unikalny_identyfikator_wariantu].json, risk_[unikalny_identyfikator_wariantu].json, sl[unikalny_identyfikator_wariantu].json, tp_[unikalny_identyfikator_wariantu].json, co_[unikalny_identyfikator_wariantu].json
6) Nie ma hardcoded if indicator_type == "SMA": w streaming_indicator_engine tylko rejestracja wskaźnika systemowego
7) W strategy builder można wybrać odpowiednie wskaźniki w sekcjach "select Indicators" zgodznie z USER_REC_01 (opisową częscią)
8) Poprawiona zostaje funkcjonalność frontend tak żeby była zgodna z wymaganiami z USER_REC_01, boecnie frontend w Strategy Builder nie odpowiada temu co wpisano w tym wymaganiu. Przeczytaj USER REQUIREMENT:USER_REC_01 bo w zakresie dzialania to wymaganie USER_REC_01 nie zostało zrealizowane. 
9) Test 1 - zapis z frontend wariantu wskaźnika systemowego typu general. Sukces będzie jak powstanie plik json w config/indicators z definicją tego wskaźnika i wlaściwej nazie general_[unikalny_identyfikator_wariantu].json
10) Test 2 - odczyt z frontend wariantu wskaźnika systemowego typu general. Sukcjes to odczytanie w frontend wcześniej zapisanego wariantu w teście 1, czyli fronted wysyla zlecenie get rest api z identyfikatorem wariantu wskaźnika, a backend dostarcza definicję tego wariantu, odpowiedz rest api jest zgodna z teścią pliku json gdzie zapisany jest wariant
9) Test 3 - zapis z frontend wariantu wskaźnika systemowego typu risk. Sukces będzie jak powstanie plik json w config/indicators z definicją tego wskaźnika i wlaściwej nazie risk_[unikalny_identyfikator_wariantu].json
10) Test 4 - odczyt z frontend wariantu wskaźnika systemowego typu risk. Sukcjes to odczytanie w frontend wcześniej zapisanego wariantu w teście 3, czyli fronted wysyla zlecenie get rest api z identyfikatorem wariantu wskaźnika, a backend dostarcza definicję tego wariantu, odpowiedz rest api jest zgodna z teścią pliku json gdzie zapisany jest wariant
11) Test 5 - fronted wysyla get api by pobrać listę strategii, a backend dostarcza listę strategii (czyli wszystkie strategie identyfikatory i ich nazwy) które zostaly zapisane w config/strategies/ 
11) Test 6 - fronted zapisuje nową strategię, frontend wysyla polecenie do backend by zapisać strategie (definicję strategii), backend na podstawie przekazanych wartości zapisuje strategię pod unikalną nazwą [unikalny_identyfikator_strategii].json w folderze config/strategies/
12) Test 7 - fronted odczytuje uprzednio zapisaną strategię w teście 6, frontend wysyla polecenie (w poleceniu musi być podany identyfikator strategii) do backend by pobrać dane definicji strategii , backend odczytuje z pliku json definicję strategi i przekazuje treść do frontend



# USER REQUIREMENT: USER_REC_04

# STRATEGY STATE MACHINE - WYMAGANIA BIZNESOWE v2.1 (SHORT ONLY)

> **WAŻNE: System działa wyłącznie na pozycjach SHORT (sprzedaż)**

## SPIS TREŚCI

1. [Przegląd i cele](#1-przegląd-i-cele)
2. [Definicje stanów](#2-definicje-stanów)
3. [Typy wskaźników - ABSOLUTE vs RELATIVE](#3-typy-wskaźników)
4. [Reguły biznesowe](#4-reguły-biznesowe)
5. [Diagram przejść](#5-diagram-przejść)
6. [Obsługa konfliktów](#6-obsługa-konfliktów)
7. [Error handling](#7-error-handling)
8. [Scenariusze użycia](#8-scenariusze-użycia)

---

## 1. PRZEGLĄD I CELE

### 1.1 Cel systemu
System Strategy State Machine zarządza pełnym cyklem życia strategii tradingowej - od wykrycia sygnału pump, przez otwarcie pozycji, aż do jej zamknięcia.

### 1.2 Kluczowe wymagania
- **Deterministyczność**: Przewidywalne zachowanie dla tych samych warunków
- **Bezpieczeństwo kapitału**: Stop Loss i Emergency Exit priorytetowe
- **Izolacja strategii**: Jedna strategia = jeden symbol w danym momencie
- **Kontrola zasobów**: Globalny limit aktywnych sygnałów (slots)
- **Odporność na błędy**: Auto-recovery po awariach
- **⚠️ SHORT ONLY**: System otwiera wyłącznie pozycje SHORT (sell/sprzedaż)

---

## 2. DEFINICJE STANÓW

### 2.1 Lista stanów

| Stan | Opis |
|------|------|
| **IDLE** | Strategia monitoruje rynek, brak aktywnego sygnału |
| **SIGNAL_DETECTED** | S1 triggered, symbol zablokowany, czeka na Z1 |
| **WAITING_FOR_ENTRY** | Zlecenie wysłane, czeka na realizację |
| **PARTIALLY_FILLED** | Zlecenie częściowo zrealizowane |
| **POSITION_OPEN** | Pozycja otwarta, monitoruje exit conditions |
| **CLOSING** | Zlecenie zamknięcia wysłane |
| **EMERGENCY** | E1 triggered, natychmiastowe zamykanie |
| **CANCELLED** | Sygnał anulowany (O1 lub timeout) |
| **COOLDOWN** | Strategia nieaktywna przez określony czas |
| **COMPLETED** | Cykl zakończony, przejście do IDLE |
| **ERROR** | Błąd krytyczny, wymaga interwencji |

### 2.2 Główny flow (happy path)

```
IDLE 
  → SIGNAL_DETECTED (S1)
  → WAITING_FOR_ENTRY (Z1)
  → POSITION_OPEN (filled)
  → CLOSING (ZE1/TP/SL)
  → COMPLETED
  → IDLE
```

---

## 3. TYPY WSKAŹNIKÓW

### 3.1 ABSOLUTE (niezależne od entry)

**Definicja:** Wskaźnik zwraca konkretną cenę na podstawie danych rynkowych.

**Przykłady:**
- "SL na poziomie najniższej ceny z ostatnich 15 minut"
- "TP na poziomie VWAP z ostatniej godziny"
- "Close order na resistance $45,000"

**Konfiguracja wariantu:**
```json
{
  "indicator_variant_id": "sl_001",
  "system_indicator": "lowest_price_window",
  "type": "stop_loss",
  "reference_type": "ABSOLUTE",
  "parameters": {
    "window_seconds": 900
  }
}
```

**Flow:**
1. Z1 triggered → wylicz V_SL (np. $43,750)
2. Entry calculated = $43,300
3. Waliduj: **SL > entry** (dla SHORT - ochrona przed wzrostem)
4. Wyślij entry + SL
5. Entry filled at actual = $43,310
6. **SL NIE ZMIENIA SIĘ** (pozostaje $43,750)

**Charakterystyka:**
- ✅ Brak update po fill
- ✅ Oparte na poziomach technicznych
- ⚠️ Risk/reward może się zmienić przez slippage
- ⚠️ Skalowanie: **nie dotyczy** (lub apply na offset od entry - do decyzji)
- **SHORT**: SL zawsze > entry (ochrona przed wzrostem ceny)

---

### 3.2 RELATIVE_TO_ENTRY (względem ceny zakupu)

**Definicja:** Wskaźnik zwraca procent/offset od zaraportowanej ceny entry.

**Przykłady:**
- "SL 1.5% powyżej entry" (SHORT: ochrona przed wzrostem)
- "TP 3% poniżej entry" (SHORT: zysk ze spadku)
- "Close order 2.5% poniżej entry"

**Konfiguracja wariantu:**
```json
{
  "indicator_variant_id": "sl_002",
  "system_indicator": "percentage_from_entry",
  "type": "stop_loss",
  "reference_type": "RELATIVE_TO_ENTRY",
  "parameters": {
    "percentage": 1.5  // SHORT: dodatni (powyżej entry)
  }
}
```

**Flow:**
1. Z1 triggered
2. Entry calculated = $43,300
3. Wylicz V_SL: +1.5% → $43,300 * (1 + 0.015) = $43,949.50
4. Wyślij entry + SL (z calculated)
5. Entry filled at actual = $43,310
6. **PRZELICZ SL** używając actual: $43,310 * (1 + 0.015) = $43,959.65
7. Wyślij update SL do brokera

**Analogicznie TP:**
- TP: -3.0% (poniżej entry dla SHORT)
- $43,310 * (1 - 0.03) = $42,010.70

**Charakterystyka:**
- ✅ Stały risk/reward ratio
- ✅ Przewidywalny P&L
- ✅ Skalowanie działa naturalnie (na procent)
- ⚠️ Wymaga update po fill
- **SHORT**: SL = dodatni %, TP = ujemny %

---

### 3.3 Skalowanie dla każdego typu

**Dla RELATIVE_TO_ENTRY:**
```
Przykład SL (SHORT):
V_SL_base = +1.5% (powyżej entry)
RZ = 65
Skalowanie dla RZ=65: 110% (większe ryzyko = większy SL)

V_SL_scaled = +1.5% * 110% = +1.65%
SL_final = entry_actual * (1 + 0.0165) = $44,024.67

Przykład TP (SHORT):
V_TP_base = -3.0% (poniżej entry)
RZ = 65
Skalowanie: 95% (większe ryzyko = mniej czekamy na zysk)

V_TP_scaled = -3.0% * 95% = -2.85%
TP_final = entry_actual * (1 - 0.0285) = $42,075.14
```

**Dla ABSOLUTE:**
```
Opcja 1: Skalowanie NIE DZIAŁA (wyłączone w UI)
Opcja 2: Skalowanie działa na offset od entry (wymaga dodatkowej logiki)
```

**Rekomendacja:** Skalowanie tylko dla RELATIVE_TO_ENTRY.

---

### 3.4 ZE1 Close Order - analogicznie

**ABSOLUTE:**
```json
{
  "indicator_variant_id": "co_001",
  "system_indicator": "vwap",
  "type": "close_order_price",
  "reference_type": "ABSOLUTE",
  "parameters": {"window_seconds": 3600}
}
```
ZE1 → V_CO = VWAP = $42,850 → close LIMIT $42,850 (SHORT: kupujemy taniej)

**RELATIVE_TO_ENTRY:**
```json
{
  "indicator_variant_id": "co_002",
  "system_indicator": "percentage_from_entry",
  "type": "close_order_price",
  "reference_type": "RELATIVE_TO_ENTRY",
  "parameters": {"percentage": -2.5}  // SHORT: ujemny (poniżej entry = zysk)
}
```
ZE1 → Entry actual = $43,310 → V_CO = $43,310 * (1 - 0.025) = $42,227.25

---

## 4. REGUŁY BIZNESOWE

### 4.1 Zasoby globalne

**BR-001: Limit slotów**
- System może mieć max N aktywnych sygnałów (N konfigurowalne)
- Aktywny sygnał = stan: SIGNAL_DETECTED, WAITING_FOR_ENTRY, PARTIALLY_FILLED, POSITION_OPEN, CLOSING
- Slot zwalniany przy: COMPLETED, CANCELLED, EMERGENCY

**BR-002: Lock symbolu**
- Na symbolu może być tylko jeden aktywny sygnał
- Lock atomowy (first-come-first-served)
- Lock zwalniany po zakończeniu cyklu

**BR-003: Cooldown**
- Po O1 cancel: cooldown konfigurowalny (default 5 min)
- Po E1 emergency: cooldown konfigurowalny (default 15 min)
- W cooldown strategia NIE ewaluuje S1

---

### 4.2 Wykrywanie sygnału (S1)

**BR-010: Warunki S1**
- Wszystkie warunki AND logic
- Format: `indicator OPERATOR value`
- Operatory: `>`, `>=`, `<`, `<=`
- Snapshot zapisywany przy transition

**BR-011: Blokada zasobów**
- Atomically zablokuj symbol
- Atomically zajmij slot
- Jeśli fail: pozostań w IDLE

---

### 4.3 Złożenie zlecenia (Z1)

**BR-030: Entry price**
- Wskaźnik CZ (price) używany: LIMIT order
- Brak wskaźnika CZ: MARKET order

**BR-031: Position Size**
- Fixed: stała kwota USDT
- Percent: % dostępnego kapitału
- Skalowanie (opcjonalne): PS * scaling(RZ)
- Walidacja: PS_final <= dostępny kapitał

**BR-032: Stop Loss (opcjonalny)**

**Dla ABSOLUTE:**
1. Wylicz V_SL z wskaźnika (konkretna cena)
2. Walidacja: V_SL < entry_calculated (dla LONG)
3. Wyślij entry + SL
4. Po fill: SL **nie zmienia się**

**Dla RELATIVE_TO_ENTRY:**
1. Wylicz V_SL_percent z wskaźnika (np. -1.5%)
2. Zastosuj skalowanie (jeśli włączone): V_SL_scaled = V_SL * scaling(RZ)
3. Wylicz SL dla calculated entry: SL_calc = entry_calc * (1 + V_SL_scaled)
4. Wyślij entry + SL
5. Po fill actual:
   - SL_final = entry_actual * (1 + V_SL_scaled)
   - Wyślij update SL

**BR-033: Take Profit (opcjonalny)**
- Analogicznie do SL, ale dodatni procent/wyższa cena

**BR-034: Z1 timeout**
- Maksymalny czas oczekiwania na fill
- Po timeout: anuluj order, zamknij partial fill (jeśli jest)

---

### 4.4 Partial fills

**BR-040: Strategia postępowania**

Konfigurowalne w strategii:

1. **WAIT_FOR_FULL_FILL** (default)
   - Czekaj na 100% fill
   - Timeout: 30s (konfigurowalne)
   - Po timeout → akcja 2 lub 3

2. **ACCEPT_PARTIAL**
   - Anuluj remaining quantity
   - Przejdź do POSITION_OPEN z częściową pozycją
   - SL/TP proporcjonalne

3. **CANCEL_ALL**
   - Anuluj remaining
   - Zamknij filled part (MARKET)
   - Przejdź do CANCELLED

---

### 4.5 Zamknięcie pozycji (ZE1, TP, SL)

**BR-050: Close Order Price (ZE1)**

**Dla ABSOLUTE:**
- V_CO = konkretna cena z wskaźnika
- Close LIMIT na tej cenie
- Nie zmienia się

**Dla RELATIVE_TO_ENTRY:**
- V_CO_percent z wskaźnika (np. +2.5%)
- Zastosuj skalowanie: V_CO_scaled = V_CO * scaling(RZ)
- V_CO_final = entry_actual * (1 + V_CO_scaled)
- Close LIMIT na V_CO_final

**BR-051: Priorytet exit conditions**

Gdy wiele warunków spełnionych jednocześnie:

```
PRIORYTET 1: Stop Loss (ochrona kapitału)
PRIORYTET 2: Take Profit (realizacja zysku)
PRIORYTET 3: ZE1 conditions (logika strategii)
```

**Szczególny przypadek: TP vs ZE1**
- Jeśli oba triggered: porównaj ceny
- Dla LONG: wybierz wyższą cenę
- Dla SHORT: wybierz niższą cenę

---

### 4.6 Emergency Exit (E1)

**BR-060: Najwyższy priorytet**
- E1 przerywa wszystkie inne operacje
- Akcje zależne od stanu (SIGNAL_DETECTED, WAITING_FOR_ENTRY, POSITION_OPEN, etc.)

**BR-061: Akcje dla POSITION_OPEN:**
1. Anuluj wszystkie pending orders (SL, TP, close)
2. Zamknij pozycję MARKET (natychmiast)
3. Retry max 3x jeśli fail
4. Jeśli nadal fail: → ERROR (critical)
5. Zwolnij symbol i slot
6. Przejdź do COOLDOWN (wymuszony, długi)

---

### 4.7 Error handling

**BR-070: Klasyfikacja błędów**

**Transient (retry możliwy):**
- Network timeout < 5s
- Broker API rate limit
- Cache miss

**Recoverable (wymaga adjustmentu):**
- Order rejected - insufficient funds → zmniejsz PS, retry
- Order rejected - price out of range → użyj MARKET, retry

**Non-recoverable (ERROR state):**
- Broker disconnect > 30s
- Data corruption
- Invalid strategy config
- Unhandled exception

**BR-071: Retry policy**
- Max 3 attempts
- Delays: 1s, 2s, 4s (exponential backoff)
- Jeśli wszystkie fail: → ERROR

**BR-072: State reconciliation (auto-recovery)**

Po 60s w ERROR:
1. Reconnect do broker API
2. Query: czy pozycja otwarta? czy orders pending?
3. Porównaj z lokalnym stanem (DB)
4. Jeśli zgodne: przywróć stan, wznów działanie
5. Jeśli niespójne: pozostań w ERROR, alert admina

---

## 5. DIAGRAM PRZEJŚĆ

### 5.1 Przejścia główne

```
IDLE → SIGNAL_DETECTED
  Event: S1 conditions met
  Guards: Symbol free, slot available, not in cooldown
  Actions: Lock symbol, occupy slot, save S1 snapshot

SIGNAL_DETECTED → WAITING_FOR_ENTRY
  Event: Z1 conditions met
  Actions: Calculate order params, send entry order, set Z1 timeout

SIGNAL_DETECTED → CANCELLED
  Event: O1 conditions OR O1 timeout
  Actions: Unlock symbol, release slot, cooldown (if configured)

WAITING_FOR_ENTRY → POSITION_OPEN
  Event: Order 100% filled
  Actions: Save actual params, update SL/TP (if RELATIVE), start monitoring exits

WAITING_FOR_ENTRY → PARTIALLY_FILLED
  Event: Order < 100% filled
  Actions: Save partial info, start partial timeout

WAITING_FOR_ENTRY → CANCELLED
  Event: Z1 timeout OR order rejected
  Actions: Cancel order, close partial (if any), unlock resources

PARTIALLY_FILLED → POSITION_OPEN
  Event: Remaining filled OR accept partial
  Actions: Update position info

PARTIALLY_FILLED → CANCELLED
  Event: Cancel all
  Actions: Close filled part, unlock resources

POSITION_OPEN → CLOSING
  Event: ZE1 OR TP OR SL triggered
  Actions: Send close order, cancel other exits

CLOSING → COMPLETED
  Event: Close order filled
  Actions: Calculate P&L, unlock resources, save report

CANCELLED → COOLDOWN (if configured)
CANCELLED → COMPLETED (if no cooldown)

EMERGENCY → COOLDOWN (always)

COOLDOWN → IDLE
  Event: Cooldown expired

COMPLETED → IDLE (immediate)

ANY STATE → EMERGENCY
  Event: E1 conditions met
  Actions: Cancel/close everything immediately

ANY STATE → ERROR
  Event: Critical error
  Actions: Stop operations, save context, alert, schedule recovery
```

---

## 6. OBSŁUGA KONFLIKTÓW

### 6.1 Hierarchia priorytetów

Gdy wiele eventów w tym samym ticku:

```
0. CRITICAL ERROR (najwyższy)
1. EMERGENCY EXIT (E1)
2. STOP LOSS
3. CANCEL (O1) - tylko w SIGNAL_DETECTED
4. TAKE PROFIT
5. EXIT CONDITIONS (ZE1)
6. ENTRY CONDITIONS (Z1)
7. SIGNAL DETECTION (S1)
```

### 6.2 Race conditions

**Slot acquisition:**
- Użyj atomowego INCR
- Jeśli new_count > MAX: DECR i fail
- First-come-first-served

**Symbol locking:**
- Użyj atomowego SETNX
- Jeśli już zajęty: fail
- First wins

---

## 7. ERROR HANDLING

### 7.1 Auto-recovery process

```
1. Wykrycie błędu → ERROR state
2. STOP wszystkich operacji (nie zmieniaj pozycji/orders)
3. Zapisz pełny kontekst (position_id, prices, orders, etc.)
4. Alert admina (email/SMS dla critical)
5. Po 60s: próba reconciliation
6. Query broker: czy pozycja/orders istnieją?
7. Porównaj z DB:
   - Zgodne: przywróć stan
   - Niespójne: pozostań w ERROR
8. Jeśli success: wznów działanie
9. Jeśli fail: retry co 5 min, potem co 30 min
```

### 7.2 Manual intervention

Admin może:
- Force state transition (jeśli zna prawdziwy stan)
- Manually close position
- Sync with broker (reconciliation on demand)
- Mark as resolved
- Disable strategy

---

## 8. SCENARIUSZE UŻYCIA

### 8.1 Happy Path (RELATIVE SL/TP)

```
T0: IDLE → SIGNAL_DETECTED
  S1: W1 > 0.52 AND R1 < 95
  Symbol: BTC_USDT locked

T1: SIGNAL_DETECTED → WAITING_FOR_ENTRY
  Z1: WE1 > 0.45
  Entry calculated: $43,300
  V_SL (RELATIVE): -1.5% → SL calc = $42,650.50
  V_TP (RELATIVE): +3.0% → TP calc = $44,599
  Order sent with SL/TP

T2: WAITING_FOR_ENTRY → POSITION_OPEN
  Entry actual: $43,310 (slippage +$10)
  Update SL: $43,310 * (1-0.015) = $42,660.35
  Update TP: $43,310 * 1.03 = $44,609.30

T3: POSITION_OPEN (monitoring)
  Price moves to $44,609.30

T4: POSITION_OPEN → CLOSING
  TP hit at $44,609.30

T5: CLOSING → COMPLETED
  P&L: +$1,299.30 gross, +$1,295 net (+3.0%)
  Symbol unlocked, slot released

T6: COMPLETED → IDLE
```

---

### 8.2 Emergency Exit

```
T0-T2: Jak wyżej, pozycja otwarta at $43,310

T3: POSITION_OPEN (price $43,520, P&L +$230)

T4: Breaking news - market crash
  Ryzyko1 skacze do 245
  E1 triggered (Ryzyko1 > 200)

T5: POSITION_OPEN → EMERGENCY
  Anuluj SL/TP
  Zamknij MARKET natychmiast
  Fill at $43,415 (w 0.7s)
  P&L: +$115 (zamiast potencjalnie -$500 gdyby czekać)

T6: EMERGENCY → COOLDOWN (15 min)

T7: COOLDOWN → IDLE
```

---

### 8.3 Partial Fill → Accept

```
T0-T1: Jak scenariusz 8.1

T2: WAITING_FOR_ENTRY → PARTIALLY_FILLED
  Filled: 50% quantity
  Config: WAIT_FOR_FULL_FILL, timeout 30s

T3: Timeout expired, still 50%
  Action: ACCEPT_PARTIAL

T4: PARTIALLY_FILLED → POSITION_OPEN
  Position size: 50% of planned
  SL/TP updated dla 50% quantity

T5-T6: Jak scenariusz 8.1
  P&L: +$647.50 (50% of expected)
```

---

## 9. IMPLEMENTACJA

### 9.1 Backend checklist

**Core State Machine:**
- [ ] Enum stanów (11 total)
- [ ] Transition matrix z guards
- [ ] Actions przy przejściach
- [ ] Rollback mechanism

**Resource Management:**
- [ ] Redis locks (SETNX)
- [ ] Redis slot counter (INCR/DECR)
- [ ] Cooldown tracking
- [ ] Cleanup przy końcu cyklu

**Indicator Engine:**
- [ ] Support dla ABSOLUTE indicators
- [ ] Support dla RELATIVE_TO_ENTRY indicators
- [ ] Skalowanie (linear interpolation)
- [ ] Cache results

**Broker Integration:**
- [ ] Place order (LIMIT/MARKET + SL/TP)
- [ ] Update SL/TP (dla RELATIVE po fill)
- [ ] Cancel order
- [ ] Query status
- [ ] Websocket real-time updates
- [ ] Retry policy

**Error Handling:**
- [ ] Reconciliation algorithm
- [ ] Auto-recovery scheduler
- [ ] Alert system

---

### 9.2 Frontend checklist

**Strategy Builder:**
- [ ] Lista strategii (z config/strategies/)
- [ ] Edit/Copy/Delete
- [ ] Builder: S1, Z1, O1, ZE1, E1 sections
- [ ] Wybór wskaźników (z dropdownu)
- [ ] Skalowanie UI (RZ ranges)
- [ ] Save do JSON

**Indicator Variants:**
- [ ] Lista wariantów (z config/indicators/)
- [ ] Create variant (wybór system indicator)
- [ ] Parametr `reference_type`: ABSOLUTE lub RELATIVE_TO_ENTRY
- [ ] Save do JSON

**Monitoring:**
- [ ] Dashboard - system overview
- [ ] Dashboard - per strategy detail
- [ ] Live alerts feed
- [ ] Manual intervention UI (dla ERROR state)

---

### 9.3 Configuration

**Strategy JSON:**
```json
{
  "id": "strategy_001",
  "name": "BTC Pump Strategy",
  "enabled": true,
  "s1_conditions": [...],
  "z1_conditions": [...],
  "z1_params": {
    "sl_indicator_id": "sl_002",  // RELATIVE_TO_ENTRY
    "sl_enabled": true,
    "sl_scaling_enabled": true,
    "sl_scaling": {
      "rz_indicator_id": "risk_001",
      "rz_min": 50,
      "rz_max": 126,
      "scaling_min": 120,
      "scaling_max": 80
    },
    "tp_indicator_id": "tp_001",  // RELATIVE_TO_ENTRY
    "tp_enabled": true
  },
  "o1_timeout_seconds": 300,
  "o1_cooldown_minutes": 10,
  "ze1_conditions": [...],
  "ze1_params": {
    "co_indicator_id": "co_002"  // RELATIVE_TO_ENTRY
  },
  "e1_conditions": [...],
  "e1_cooldown_minutes": 15
}
```

**Indicator Variant JSON:**
```json
{
  "id": "sl_002",
  "type": "stop_loss",
  "system_indicator_id": "percentage_from_entry",
  "reference_type": "RELATIVE_TO_ENTRY",
  "parameters": {
    "percentage": -1.5
  }
}
```

---

## 10. METRYKI I MONITORING

### 10.1 KPI (per strategia)

- Win rate (% profitable trades)
- Average P&L (net, percent)
- % trades: COMPLETED success / loss / CANCELLED / EMERGENCY / ERROR
- Average duration per trade
- Max drawdown

### 10.2 KPI (systemowe)

- Uptime %
- % strategies in ERROR
- Average time to recovery
- Slot utilization
- Tick processing latency (< 50ms p95)
- Order placement latency (< 200ms p95)

### 10.3 Alerty

**CRITICAL:**
- Broker disconnect > 30s z otwartą pozycją
- Position cannot be closed (after 3 retries)
- Data corruption

**HIGH:**
- Strategy in ERROR
- Broker disconnect > 5s

**MEDIUM:**
- Multiple failures (3+ in 1 hour)
- Order rejected

---

## 11. PYTANIA OTWARTE (DO DECYZJI)

### Q1: Skalowanie dla ABSOLUTE indicators?
- **Opcja A:** Skalowanie wyłączone (tylko dla RELATIVE)
- **Opcja B:** Skalowanie działa na offset od entry (wymaga dodatkowej logiki)

**Rekomendacja:** Opcja A (prostsze, jasne)

---

### Q2: Co jeśli ABSOLUTE indicator daje invalid cenę?

Przykład: SL (ABSOLUTE) = $44,000, Entry = $43,300 (dla LONG: invalid!)

- **Opcja A:** ERROR state (nie wysyłaj zlecenia)
- **Opcja B:** Fallback: entry - 0.5%
- **Opcja C:** Wyłącz SL, wyślij tylko entry

**Rekomendacja:** Opcja A (bezpieczne, wymusza poprawną konfigurację)

---

### Q3: Update SL/TP dla RELATIVE - timing?

- **Opcja A:** Natychmiast po fill (może być okno bez ochrony 0.5-2s)
- **Opcja B:** Wyślij entry+SL/TP razem (z calculated), potem update
- **Opcja C:** Broker trailing stop (jeśli wspiera)

**Rekomendacja:** Opcja B (balans między ochroną a precision)

---


# USER REQUIREMENT:  USER_REC_05 

## BACKTESTING SYSTEM

### 1. PRZEGLĄD I CELE
**1.1 Cel systemu**
System backtestingu umożliwia walidację strategii tradingowych na historycznych danych rynkowych przed wdrożeniem ich w środowisku produkcyjnym. System wykorzystuje te same wskaźniki i definicje strategii co środowisko live, zapewniając spójność wyników.
**1.2 Kluczowe wymagania**

Wierność symulacji - replikacja State Machine zgodnie z USER_REC_04
Reużycie komponentów - te same wskaźniki i strategie co live trading
Analiza wielowymiarowa - testowanie wielu strategii na wielu symbolach
Szczegółowa diagnostyka - pełna inspekcja każdego sygnału i transakcji
Wizualizacja wyników - możliwość przeglądania wskaźników na wykresach


### 2. ODKRYWANIE I ZARZĄDZANIE SESJAMI DANYCH HISTORYCZNYCH
**2.1 Lokalizacja i struktura danych źródłowych**
Dane historyczne znajdują się w katalogu głównym aplikacji w podfolderze data. Każda sesja danych ma własny katalog z nazwą zawierającą datę, czas rozpoczęcia i unikalny identyfikator. Wewnątrz katalogu sesji znajdują się podfoldery dla każdego symbolu, a w nich pliki CSV z danymi rynkowymi zawierającymi timestamp, cenę, volume i liczbę transakcji.
**2.2 Automatyczne odkrywanie sesji**
Backend musi automatycznie skanować katalog z danymi i identyfikować wszystkie dostępne sesje. Dla każdej znalezionej sesji system ekstrahuje podstawowe informacje: identyfikator sesji, datę i czas rozpoczęcia, listę dostępnych symboli oraz liczbę symboli. Te informacje są udostępniane frontendowi bez konieczności manualnej konfiguracji.
**2.3 Szczegółowe informacje o sesji**
Dla każdej sesji system musi dostarczyć szczegółowych informacji o każdym symbolu: zakres czasowy danych (timestamp początku i końca), czas trwania w godzinach, liczbę ticków, oraz zakres cenowy (minimum i maksimum). Te metadane pozwalają użytkownikowi ocenić jakość i zakres danych przed rozpoczęciem backtestingu.
**2.4 Wymagania dotyczące odczytu danych**
System musi obsługiwać odczyt danych CSV z każdego symbolu. Dane zawierają timestamp, cenę, volume i liczbę transakcji. Backend nie wykonuje walidacji outliers - wszystkie wartości cen są akceptowane jako prawidłowe. System usuwa automatycznie duplikaty timestampów. W przypadku luk w danych (missing ticks) system wypełnia braki poprzez forward fill lub interpolację, informując o tym użytkownika bez blokowania backtestingu.

### 3. KONFIGURACJA BACKTESTINGU
**3.1 Wybór sesji danych**
Użytkownik może wybrać jedną lub wiele sesji danych do backtestingu. Frontend prezentuje listę dostępnych sesji w formie tabeli pokazującej identyfikator, datę, czas, czas trwania i liczbę symboli. Przy każdej sesji dostępny jest przycisk pozwalający wyświetlić szczegółowe informacje w oknie modalnym, gdzie użytkownik widzi pełną listę symboli z ich zakresami czasowymi i cenowymi.
**3.2 Mapowanie strategii do symboli**
Kluczowa funkcjonalność systemu to możliwość przypisania każdej strategii do wybranych symboli. Użytkownik może dodać wiele strategii do jednego backtestingu, a dla każdej strategii niezależnie wybrać zestaw symboli do testowania. Na przykład strategia pierwsza może być testowana na symbolach A, B i C, podczas gdy strategia druga na symbolach D i E. System prezentuje tylko symbole dostępne w wybranych sesjach danych.
**3.3 Kapitał początkowy**
Użytkownik określa całkowitą kwotę kapitału początkowego w USDT. Ta wartość jest współdzielona przez wszystkie strategie - jeśli jedna strategia otwiera pozycję, zmniejsza dostępny kapitał dla pozostałych.
**3.4 Ustawienia globalne**
System wymaga konfiguracji parametrów globalnych:
Limity slotów: Maksymalna liczba równocześnie aktywnych sygnałów we wszystkich strategiach. Jeśli limit zostanie osiągnięty, kolejne strategie nie mogą wykrywać nowych sygnałów dopóki sloty się nie zwolnią.
Model slippage: Użytkownik wybiera między brakiem slippage (idealna symulacja), stałym procentem, lub realistycznym modelem opartym na volume. Model realistyczny zwiększa slippage proporcjonalnie do wielkości zlecenia względem volume rynkowego.
Model prowizji: System wspiera model standardowy (Binance), brak prowizji, lub niestandardowy. Model standardowy rozróżnia maker i taker fees.
Symulacja opóźnień: Opcjonalnie system może symulować opóźnienia sieciowe i czasowe. Użytkownik określa średnie opóźnienie i zakres. Symulacja uwzględnia czas obliczania wskaźników, ewaluacji strategii, przesyłu sieciowego do brokera i potwierdzenia zlecenia. Całkowite opóźnienie wpływa na cenę wykonania - zlecenie jest realizowane po cenie aktualnej w momencie dotarcia do symulowanego brokera, nie w momencie generacji sygnału.

### 4. PROCES BACKTESTINGU
**4.1 Symulacja tick-by-tick**
Backend przetwarza dane historyczne chronologicznie, tick po ticku. Dla każdego timestampu system aktualizuje wartości wszystkich wskaźników dla wszystkich symboli, następnie ewaluuje każdą aktywną strategię na każdym jej symbolu, symuluje wykonanie oczekujących zleceń i zarządza globalnym stanem slotów i locków symboli.
**4.2 Reużycie komponentów live trading**
Backtest wykorzystuje dokładnie tę samą implementację State Machine co live trading - wszystkie stany i przejścia z USER_REC_04. Jedyna różnica to zastąpienie Broker API przez Order Simulator, real-time data przez historical playback i Redis locks przez in-memory locks specyficzne dla sesji backtestingu.
**4.3 Symulacja składania zleceń**
Order Simulator obsługuje zlecenia MARKET i LIMIT z uwzględnieniem slippage, opóźnień czasowych i prowizji. Dla zleceń MARKET cena wykonania to cena ask lub bid w momencie dotarcia zlecenia plus symulowany slippage. Dla zleceń LIMIT wykonanie następuje gdy cena rynkowa osiągnie lub przekroczy cenę limit. System symuluje również częściowe wykonania dla dużych zleceń względem volume - jeśli wielkość zlecenia przekracza próg, tylko część zostaje wypełniona, co triggeruje logikę partial fills zgodną ze strategią.
**4.4 Zbieranie danych podczas backtestingu**
Podczas przetwarzania każdego ticka system zbiera:

Wartości wszystkich wskaźników użytych w strategii dla każdego timestampu
Wszystkie sygnały (S1, Z1, O1, ZE1, E1) z ich kontekstem
Wszystkie transakcje z pełnymi szczegółami
Statystyki agregowane na bieżąco

Te dane są buforowane w pamięci i zapisywane do plików po zakończeniu przetwarzania każdej kombinacji strategia-symbol.

### 5. STRUKTURA ZAPISYWANIA WYNIKÓW
**5.1 Hierarchia katalogów**
*Wyniki każdego backtestingu zapisywane są w dedykowanym katalogu z unikalnym identyfikatorem (timestamp utworzenia). Struktura jest trzypoziomowa: poziom główny backtestingu, poziom strategii i poziom symbol. Każdy poziom zawiera własne pliki z danymi i podsumowaniami.
**5.2 Poziom główny backtestingu**
W katalogu głównym backtestingu znajdują się dwa pliki:
Plik konfiguracyjny zawiera kompletny opis konfiguracji backtestingu: identyfikator backtestingu, czas utworzenia, listę sesji danych historycznych użytych do testowania (z ich identyfikatorami, datami i czasem trwania), listę strategii wraz z przypisanymi im symbolami, oraz wszystkie ustawienia globalne (kapitał początkowy, maksymalna liczba slotów, wybrany model slippage, model prowizji, ustawienia symulacji opóźnień).
Plik globalnego podsumowania zawiera agregowane statystyki dla całego backtestingu: całkowitą liczbę transakcji, liczbę zyskownych transakcji, wskaźnik sukcesu w procentach, całkowity zysk lub stratę w USDT i procentach, maksymalny drawdown w USDT i procentach, średni czas trwania transakcji, kapitał początkowy i końcowy. Dodatkowo zawiera skrócone podsumowania dla każdej strategii z podstawowymi metrykami.
**5.3 Poziom strategii**
Każda strategia ma własny podkatalog zawierający plik podsumowania strategii oraz podfoldery dla każdego testowanego symbolu.
Plik podsumowania strategii zawiera: identyfikator i nazwę strategii, całkowitą liczbę transakcji, liczbę i procent zyskownych transakcji, całkowity zysk lub stratę w USDT, średni zysk na transakcję, maksymalny drawdown, wskaźnik Sharpe'a. Osobna sekcja zawiera statystyki sygnałów: ile razy wykryto S1, ile razy doszło do Z1, ile sygnałów zostało anulowanych przez O1 (z podziałem na timeout i warunki), ile pozycji otwarto, jak zamykano pozycje (liczba zamknięć przez TP, SL, ZE1, Emergency Exit). Na końcu znajduje się breakdown per symbol pokazujący dla każdego symbolu liczbę transakcji, wskaźnik sukcesu, zysk lub stratę oraz średni zysk na transakcję. Ta sekcja pozwala szybko zidentyfikować które symbole były najbardziej i najmniej zyskowne dla danej strategii.
**5.4 Poziom symbol (strategia-symbol)**
Dla każdej kombinacji strategia-symbol system tworzy osobny podkatalog zawierający cztery typy plików:
Plik wartości wskaźników w czasie - kluczowy dla wizualizacji. Zawiera timeseries wszystkich wskaźników użytych w strategii. Dla każdego timestampu z sesji historycznej zapisana jest cena oraz wartości wszystkich wskaźników (ogólne, risk, entry, exit, SL, TP, close order). Format pliku musi umożliwiać szybki odczyt dużych ilości danych, filtrowanie po zakresie czasowym oraz selektywny odczyt tylko wybranych wskaźników. System używa kolumnowego formatu z kompresją (Parquet) dla efektywności.
Plik sygnałów zawiera chronologiczną listę wszystkich sygnałów wykrytych podczas backtestingu. Każdy wpis opisuje: typ sygnału (S1, Z1, O1, ZE1, E1, fill, exit), dokładny timestamp, warunki które zostały spełnione (konkretne wyrażenia logiczne które były prawdziwe), wartości wszystkich wskaźników w momencie sygnału, outcome (co się stało w następstwie tego sygnału), oraz powiązania z innymi sygnałami (parent-child relationships tworzące pełną ścieżkę od S1 do zamknięcia pozycji). Dla sygnałów Z1 dodatkowo zapisywane są wyliczone parametry zlecenia (calculated entry price, SL, TP, position size, wartość wskaźnika risk użytego do skalowania). Dla fills zapisywane są rzeczywiste ceny wykonania, slippage, zaktualizowane wartości SL i TP (dla wskaźników RELATIVE_TO_ENTRY). Dla exits zapisywana jest cena zamknięcia, powód (TP/SL/ZE1/E1), oraz wyliczony P&L. Kluczowe: sygnały NIE zawierają duplikacji wartości wskaźników - przechowują tylko timestampy jako referencje. Wartości wskaźników odczytuje się z pliku wartości wskaźników poprzez lookup po timestamp.
Plik transakcji zawiera listę wszystkich zawartych i zamkniętych transakcji. Każda transakcja opisuje: unikalny identyfikator, symbol, referencje do sygnałów które ją spowodowały (ID sygnału S1 i Z1), czas i cena wejścia, wielkość pozycji, wartość w USDT, czas i cena wyjścia, powód zamknięcia (TP/SL/ZE1/E1), zysk lub stratę brutto i netto, łączne prowizje, ROI w procentach, czas trwania, poziomy SL i TP które były aktywne. Kluczowe: transakcje NIE zawierają kopii wartości wskaźników - zawierają tylko referencje do timestampów entry i exit. Wartości wskaźników w tych momentach odczytuje się z pliku wartości wskaźników.
Plik podsumowania symbolu zawiera zagregowane statystyki dla tej kombinacji strategia-symbol: liczbę transakcji, liczbę i procent zyskownych, łączny P&L, średni P&L na transakcję, maksymalny drawdown. Osobna sekcja ze statystykami sygnałów pokazuje ile razy wykryto S1, ile doszło do entry, ile zostało cancelled, ile emergency exits. Na końcu szczegółowe opisy najlepszej transakcji (największy zysk) i najgorszej transakcji (największa strata) z pełnymi szczegółami.
**5.5 Zasada single source of truth***
System musi zapewnić że wartości wskaźników są przechowywane tylko w jednym miejscu - w pliku wartości wskaźników. Wszystkie inne pliki (sygnały, transakcje) zawierają tylko referencje czasowe (timestampy). To eliminuje duplikację danych, zmniejsza rozmiar plików, zapobiega inconsistency i upraszcza maintenance. Backend przy odczycie danych automatycznie wykonuje lookup wartości wskaźników dla potrzebnych timestampów.

### 6. API BACKENDOWE
**6.1 Odkrywanie sesji danych**
System udostępnia endpoint zwracający listę wszystkich dostępnych sesji danych z katalogu źródłowego. Dla każdej sesji zwracane są: identyfikator, data, czas rozpoczęcia, lista symboli, liczba symboli.
Osobny endpoint dostarcza szczegółowych informacji o wybranej sesji. Dla każdego symbolu w sesji zwracane są: nazwa symbolu, zakres czasowy (start i end timestamp), czas trwania w sekundach, liczba ticków, zakres cenowy (minimum i maksimum). Dodatkowo zwracany jest globalny zakres czasowy sesji.
Trzeci endpoint pozwala na odczyt surowych danych CSV dla konkretnego symbolu z sesji, opcjonalnie z limitem liczby rekordów dla preview.
**6.2 Uruchamianie backtestingu**
Endpoint przyjmuje konfigurację backtestingu zawierającą: listę identyfikatorów sesji danych, listę strategii z przypisanymi symbolami dla każdej, kapitał początkowy w USDT, oraz ustawienia globalne (maksymalna liczba slotów, model slippage, model prowizji, ustawienia symulacji opóźnień). Po przyjęciu konfiguracji system generuje unikalny identyfikator backtestingu, kolejkuje zadanie do przetwarzania w tle i natychmiast zwraca identyfikator backtestingu oraz status "queued".
**6.3 Monitorowanie postępu**
Endpoint statusu zwraca aktualny stan backtestingu: status (queued, running, completed, stopped, error), procent ukończenia, aktualnie przetwarzany symbol i strategię, oraz oszacowany pozostały czas.
Endpoint stop pozwala na przerwanie działającego backtestingu.
**6.4 Pobieranie wyników**
Główny endpoint wyników zwraca zawartość pliku globalnego podsumowania z agregowanymi statystykami dla całego backtestingu.
Endpoint podsumowania strategii zwraca zawartość pliku podsumowania dla wybranej strategii.
Endpoint zwracający listę symboli pokazuje wszystkie symbole testowane przez daną strategię.
Endpoint podsumowania symbolu zwraca statystyki dla konkretnej kombinacji strategia-symbol.
Endpoint transakcji zwraca listę wszystkich transakcji dla kombinacji strategia-symbol.
Endpoint sygnałów zwraca listę wszystkich sygnałów dla kombinacji strategia-symbol.
Endpoint szczegółów sygnału zwraca pełny kontekst pojedynczego sygnału wraz z wartościami wskaźników w tym momencie (wartości są odczytywane z pliku wskaźników poprzez lookup po timestamp).
**6.5 Dane do wizualizacji wykresu**
Kluczowy endpoint zwraca dane potrzebne do wyrenderowania wykresu dla kombinacji strategia-symbol. Przyjmuje parametry opcjonalne: zakres czasowy (start i end timestamp), współczynnik downsamplingu (domyślnie 1), lista wskaźników do zwrócenia (domyślnie wszystkie).
Backend odczytuje plik wartości wskaźników, filtruje po zakresie czasowym, aplikuje downsampling jeśli wymagany, zwraca tylko wybrane wskaźniki. Format odpowiedzi to tablice wartości (nie obiekty) dla efektywności: osobna tablica timestampów, osobna tablica cen, osobny obiekt z tablicami wartości dla każdego wskaźnika.
Dodatkowo endpoint zwraca przefiltrowaną listę sygnałów w zakresie czasowym (dla renderowania markerów na wykresie) oraz listę transakcji (dla renderowania poziomów SL/TP i annotacji entry/exit).
Response zawiera również metadane: rzeczywisty zakres czasowy zwróconych danych, całkowitą liczbę punktów w pliku, liczbę zwróconych punktów po filtrowaniu i downsamplingu.
Ten endpoint został podzielony na trzy osobne endpointy dla optymalizacji:

Endpoint danych cenowych i wskaźników - zwraca tylko timeseries (timestamps, ceny, wartości wskaźników)
Endpoint sygnałów - zwraca tylko listę sygnałów w zakresie czasowym
Endpoint transakcji - zwraca tylko listę transakcji w zakresie czasowym

Podział pozwala frontendowi na równoległe ładowanie i progressive rendering - wykres może być wyświetlony zaraz po otrzymaniu danych cenowych, a markery sygnałów i transakcji są dodawane w miarę otrzymywania kolejnych odpowiedzi.
**6.6 Cachowanie wyników**
Backend musi implementować mechanizm cachowania dla wszystkich endpointów zwracających wyniki backtestingu. Każda odpowiedź zawiera nagłówki HTTP:
ETag: Unikalny hash zawartości odpowiedzi. Wyliczany na podstawie zawartości pliku i parametrów zapytania.
Cache-Control: Określa jak długo odpowiedź może być cache'owana. Dla wyników zakończonych backtestów wartość to długi okres (np. 24 godziny) ponieważ dane się nie zmieniają. Dla statusu działającego backtestingu wartość to krótki okres (np. 5 sekund).
Last-Modified: Timestamp ostatniej modyfikacji danych źródłowych.
Backend musi obsługiwać warunkowe requesty: jeśli frontend wysyła nagłówek If-None-Match z poprzednim ETag i zawartość się nie zmieniła, backend zwraca status 304 Not Modified bez przesyłania danych ponownie. To drastycznie redukuje transfer sieciowy i przyspiesza ładowanie dla powtarzających się zapytań.

### 7. INTERFEJS UŻYTKOWNIKA
**7.1 Wybór i konfiguracja**
Frontend prezentuje listę dostępnych sesji danych w formie tabeli z checkboxami pozwalającymi wybrać jedną lub wiele sesji. Kolumny tabeli pokazują identyfikator sesji, datę, czas, czas trwania, liczbę symboli. Przycisk przy każdej sesji otwiera okno modalne ze szczegółowymi informacjami o symbolach.
Sekcja konfiguracji strategii pozwala na dodanie wielu strategii poprzez przycisk "Dodaj strategię". Dla każdej dodanej strategii użytkownik wybiera strategię z dropdown listy oraz zaznacza symbole z dostępnych w wybranych sesjach. Możliwe jest użycie szybkich filtrów (wszystkie, żadne, top 10 po volume). Każda strategia ma własny zestaw wybranych symboli, niezależny od innych strategii.
Pole kapitału początkowego przyjmuje wartość w USDT.
Sekcja zaawansowanych ustawień zawiera konfigurację: maksymalnej liczby slotów (liczba), modelu slippage (dropdown), modelu prowizji (dropdown), oraz opcjonalnej symulacji opóźnień z checkboxem włączenia i polami na średnie opóźnienie i zakres.
Podsumowanie konfiguracji pokazuje: liczbę wybranych sesji, liczbę skonfigurowanych strategii z liczbą symboli każdej, kapitał początkowy, maksymalną liczbę slotów, oszacowany czas wykonania. Przycisk uruchomienia backtestingu.
**7.2 Monitorowanie wykonania**
Podczas backtestingu wyświetlany jest progress bar z procentem ukończenia, live countery pokazujące aktywne sygnały per strategia, otwarte pozycje per strategia, ukończone transakcje, aktualny P&L. Oszacowany pozostały czas. Stream logów w czasie rzeczywistym pokazujący kluczowe eventy (wykrycie sygnału, złożenie zlecenia, wykonanie, zamknięcie). Przyciski pause, resume i stop.
**7.3 Wyniki - widok główny**
Dashboard wyników pokazuje karty z kluczowymi metrykami: całkowita liczba transakcji, liczba i procent zyskownych, całkowity P&L w USDT i procentach, maksymalny drawdown, średni czas trwania transakcji.
Tabela porównawcza strategii z kolumnami: nazwa strategii, liczba transakcji, wskaźnik sukcesu, całkowity P&L, średni P&L, maksymalny drawdown, wskaźnik Sharpe'a. Sortowalna.
Tabela breakdown per symbol z kolumnami: symbol, liczba transakcji, wskaźnik sukcesu, całkowity P&L. Sortowalna.
Wykresy: krzywa kapitału (cumulative P&L w czasie), wykres drawdown w czasie, rozkład P&L (histogram), wskaźnik sukcesu w rolling window.
**7.4 Wyniki - analiza strategii**
Po wybraniu strategii z dropdown wyświetlane są szczegółowe statystyki sygnałów: liczba wykrytych S1, z tego ile doprowadziło do Z1, ile zostało anulowanych przez O1 (breakdown na timeout vs warunki), liczba złożonych zleceń Z1, z tego ile wypełnionych w 100%, ile częściowo wypełnionych, ile anulowanych przez timeout, liczba otwartych pozycji, z tego ile zamkniętych przez TP, SL, ZE1, Emergency Exit.
Tabela transakcji z kolumnami: ID transakcji, symbol, czas wejścia, cena wejścia, czas wyjścia, cena wyjścia, powód zamknięcia, P&L, czas trwania. Sortowalna, filtrowalna. Każdy wiersz klikalny.
Po kliknięciu transakcji wyświetlane jest okno modalne z pełną timeline wszystkich eventów od S1 do zamknięcia, wartościami wszystkich wskaźników w kluczowych momentach (S1, Z1, entry, exit), oraz małym wykresem pokazującym cenę, poziomy entry/SL/TP i punkt wyjścia.
Sekcja analizy wskaźników pokazuje dla każdego użytego wskaźnika: minimalną, maksymalną i średnią wartość, histogram rozkładu wartości, oraz korelację z P&L transakcji.
**7.5 Wyniki - eksploracja sygnałów**
Lista wszystkich sygnałów S1 dla wybranej strategii i symbolu. Filtry: outcome (wszystkie, zyskowne, stratne, anulowane, emergency), symbol, zakres dat. Tabela z kolumnami: ID sygnału, symbol, czas wykrycia, outcome, finalny P&L, czas trwania. Sortowalna.
Po kliknięciu sygnału wyświetlana jest szczegółowa strona z pełną timeline wszystkich powiązanych eventów (S1 → Z1 → fill → exit). Dla każdego eventu pokazane są: dokładny timestamp, spełnione warunki, wartości wszystkich wskaźników w tym momencie (odczytywane z pliku wskaźników przez lookup), akcje które zostały podjęte.
Wykresy: cena w czasie z zaznaczonymi punktami entry i exit, poziomami SL i TP, oraz osobne subploty dla każdego wskaźnika pokazujące jego wartość w czasie w zakresie tego sygnału.
**7.6 Wizualizacja wskaźników na wykresach**
Kluczowa funkcjonalność pozwalająca na szczegółową analizę zachowania wskaźników.
Użytkownik wybiera strategię z dropdown, następnie symbol z dropdown. System automatycznie ładuje dane dla tej kombinacji.
Kontrolki wykresu pozwalają na:

Wybór zakresu czasowego (pełny zakres lub custom)
Slider downsamplingu (1x, 5x, 10x) dla zmniejszenia liczby punktów przy overview
Panel wskaźników z checkboxami pozwalający włączać/wyłączać poszczególne wskaźniki (każdy w innym kolorze)

Główny wykres wyświetla:

Linię ceny jako główną oś
Linie każdego włączonego wskaźnika (każdy wskaźnik może mieć własną skalę na osobnej osi pionowej po prawej stronie)
Markery dla wszystkich sygnałów (różne kolory dla S1, Z1, entry, exit, każdy z labelką)
Poziome linie dla SL i TP każdej transakcji (pokazywane tylko w czasie trwania transakcji)
Annotacje przy punktach entry i exit pokazujące ceny i P&L

Interaktywność:

Hover nad wykresem pokazuje tooltip ze wszystkimi wartościami dla tego timestampu (czas, cena, wartości wszystkich wskaźników)
Kliknięcie markera sygnału otwiera okno modalne ze szczegółami tego sygnału
Zoom i pan - użytkownik może przybliżać interesujące obszary i przesuwać się w czasie
Przy zoomie system automatycznie dostosowuje downsampling lub ładuje dodatkowe dane jeśli potrzeba

Pod głównym wykresem znajduje się timeline pokazująca wszystkie sygnały jako punkty na osi czasu dla szybkiej nawigacji.
Panel wskaźników po prawej stronie pozwala na toggleowanie widoczności każdego wskaźnika oraz pokazuje aktualny kolor przypisany do każdego wskaźnika.
System implementuje progressive loading - najpierw ładuje i wyświetla dane cenowe i wskaźniki (najważniejsze dla wykresu), następnie dodaje markery sygnałów i transakcji w miarę otrzymywania danych z dodatkowych endpointów. To pozwala na szybkie wyświetlenie wykresu nawet jeśli sieć jest wolna.
Wszystkie requesty do API wykorzystują cachowanie - powtórne wyświetlenie tego samego wykresu jest natychmiastowe dzięki wykorzystaniu cache przeglądarki i nagłówków ETag.

### 8. WYMAGANIA TECHNICZNE NIEZWIĄZANE Z KODEM
**8.1 Performance**
System musi obsługiwać sesje danych o długości do 24 godzin z 50 symbolami bez znaczącej degradacji performance. Czas wykonania backtestingu nie powinien przekraczać 10 minut dla sesji 3-godzinnej z 20 symbolami i 5 strategiami.
Odczyt danych do wizualizacji wykresu musi być zoptymalizowany - windowing pozwala na ładowanie tylko wybranego zakresu czasowego, downsampling redukuje liczbę punktów dla overview, selektywny odczyt wskaźników pozwala na załadowanie tylko tych które użytkownik chce wyświetlić.
**8.2 Skalowalność danych**
Dla długich sesji (powyżej 6 godzin) system powinien implementować partycjonowanie plików wartości wskaźników - podział na mniejsze pliki per godzinę pozwala na ładowanie tylko potrzebnych partycji zamiast całego dużego pliku.
Format zapisu musi wykorzystywać kompresję - kolumnowy format z kompresją redukuje rozmiar o około 80% w porównaniu do niezkompresowanego CSV.
**8.3 Walidacja spójności**
Po zakończeniu backtestingu system musi przeprowadzić walidację referential integrity między plikami. Sprawdzane są: czy wszystkie referencje do sygnałów w transakcjach wskazują na istniejące sygnały, czy wszystkie timestampy w sygnałach i transakcjach istnieją w pliku wartości wskaźników, czy nie ma conflicting data. Jeśli walidacja wykryje błędy, backtest przechodzi w stan ERROR i wyniki nie są publikowane dopóki problem nie zostanie rozwiązany.
**8.4 Odporność na błędy**
System musi implementować checkpointing - periodyczne zapisywanie stanu po zakończeniu przetwarzania każdej kombinacji strategia-symbol. W przypadku crash podczas backtestingu system może wznowić od ostatniego checkpointu zamiast zaczynać od początku.
Bufferowanie w pamięci podczas przetwarzania - dane są zbierane w pamięci i zapisywane do plików asynchronicznie aby nie spowalniać głównej pętli backtestingu.
**8.5 Versioning**
Każdy katalog backtestingu powinien zawierać plik metadata z wersją schema struktury danych. Pozwala to na obsługę backtestów z różnych wersji systemu - backend sprawdza wersję i używa odpowiedniego parsera.

### 9. REALIZM SYMULACJI
**9.1 Slippage**
Model realistyczny oblicza slippage bazując na stosunku wielkości zlecenia do aktualnego volume rynkowego. Duże zlecenia względem volume mają większy slippage. Model fixed percent aplikuje stały procent slippage do każdego zlecenia. Model none nie aplikuje żadnego slippage (idealna symulacja).
**9.2 Opóźnienia**
System symuluje realistyczne opóźnienia czasowe składające się z: czasu obliczania wskaźników (10-50ms), czasu ewaluacji strategii (5-20ms), czasu przesyłu sieciowego do brokera (20-100ms), czasu potwierdzenia zlecenia przez brokera (50-200ms). Całkowite opóźnienie dla typowego scenariusza to około 150ms. Zlecenie jest realizowane po cenie aktualnej w momencie dotarcia do brokera (timestamp oryginalny plus opóźnienie), nie po cenie w momencie generacji sygnału.
**9.3 Częściowe wykonania**
Jeśli wielkość zlecenia przekracza określony próg względem volume (np. 20% volume per minutę), system symuluje częściowe wykonanie. Wypełniana jest tylko część zlecenia, a reszta pozostaje pending. Triggeruje to timeout częściowego wykonania zgodny z konfiguracją strategii (WAIT_FOR_FULL_FILL, ACCEPT_PARTIAL, CANCEL_ALL).
**9.4 Prowizje**
Model standardowy (Binance) rozróżnia maker fee (0.1%) i taker fee (0.1%). Zlecenia LIMIT które są wypełnione natychmiast (przekroczyły order book) płacą taker fee. Zlecenia LIMIT które czekają w order book i są wypełnione później płacą maker fee. Zlecenia MARKET zawsze płacą taker fee. Prowizje są odejmowane od P&L netto każdej transakcji.

### 10. KRYTYCZNA ANALIZA I UZASADNIENIA
**10.1 Rozwiązanie duplikacji danych**
Problem zidentyfikowany: Pierwotny design zawierał duplikację wartości wskaźników - te same wartości były zapisywane w pliku wartości wskaźników, w sygnałach i w transakcjach. To zwiększało rozmiar danych, ryzykowało inconsistency i komplikowało maintenance.
Rozwiązanie: Wprowadzono zasadę single source of truth. Wartości wskaźników są przechowywane wyłącznie w pliku wartości wskaźników. Sygnały i transakcje zawierają tylko referencje czasowe (timestampy). Backend przy odczycie szczegółów sygnału lub transakcji automatycznie wykonuje lookup wartości wskaźników z pliku wskaźników dla potrzebnych timestampów.
Uzasadnienie: To rozwiązanie eliminuje duplikację, zmniejsza rozmiar plików o około 30-40%, zapewnia consistency (tylko jedno miejsce do update), upraszcza maintenance. Trade-off: nieznacznie komplikuje queries (potrzebny lookup), ale to jest abstrakcja na poziomie backend która nie wpływa na frontend.
**10.2 Rozwiązanie braku cache headers**
Problem zidentyfikowany: Bez cache headers frontend robił powtarzające się requesty za każdym razem pobierając te same duże pliki (5-10 MB), marnując bandwidth i spowalniając UX.
Rozwiązanie: Backend implementuje pełne cachowanie z nagłówkami HTTP: ETag bazowany na hash zawartości, Cache-Control z odpowiednim max-age (długi dla completed backtests, krótki dla running), Last-Modified timestamp, oraz obsługa warunkowych requestów If-None-Match zwracających 304 Not Modified.
Uzasadnienie: Drastycznie redukuje transfer sieciowy (zero bytes dla cache hit), przyspiesza ładowanie (instant dla powtarzających się zapytań), redukuje load na serwerze. To jest must-have dla aplikacji zwracających duże statyczne pliki.
**10.3 Podział chart-data endpoint**
Problem zidentyfikowany: Jeden endpoint zwracający wszystko (price + indicators + signals + trades) generował bardzo duże payloady (5-10 MB JSON) co spowalniało transfer i parsing.
Rozwiązanie: Podział na trzy osobne endpointy: dane cenowe i wskaźniki (największy, najważniejszy), sygnały (średni), transakcje (najmniejszy). Frontend ładuje równolegle i może wyświetlić wykres zaraz po otrzymaniu pierwszej odpowiedzi.
Uzasadnienie: Progressive rendering - user widzi wykres szybciej nawet jeśli sieć jest wolna. Flexibility - nie zawsze potrzebujemy wszystkich danych (np. overview bez sygnałów). Lepsze wykorzystanie cachingu - różne endpointy mogą mieć różne cache timeouts.
**10.4 Wybór kolumnowego formatu z kompresją**
Decyzja: Użycie Parquet zamiast CSV lub JSON dla pliku wartości wskaźników.
Uzasadnienie: Parquet oferuje kompresję około 80% vs CSV, kolumnowy format pozwala na selektywny odczyt tylko potrzebnych wskaźników (nie trzeba wczytywać wszystkich 10 kolumn jeśli potrzebny jest tylko W1), fast query z metadata (min/max per column), type safety (schema embedded). Trade-off: wymaga dependencies (pandas, pyarrow) ale to jest akceptowalne bo mamy je już dla innych celów.
Alternatywa rozważana: SQLite database. Odrzucona dla MVP bo: większy file size niż Parquet, wolniejszy bulk insert podczas backtestingu, dodatkowa complexity (trzeba zarządzać connections, transactions, indexes). Może być rozważona w przyszłości jeśli potrzebne będą complex queries łączące indicators, signals i trades.
**10.5 Hierarchiczna struktura vs flat**
Decyzja: Hierarchia backtest → strategy → symbol z osobnymi plikami na każdym poziomie.
Uzasadnienie: Naturalne mapowanie do przypadków użycia (user myśli "chcę zobaczyć jak strategy_001 działała na ALU_USDT"), łatwe dodawanie strategii bez przebudowy, możliwość równoległego przetwarzania, clear ownership. Trade-off: więcej plików (complexity w file system), ale to jest abstrakcja - user nie widzi file structure.
Alternatywa rozważana: Wszystko w jednej bazie danych. Odrzucona dla MVP (over-engineering). Może być rozważona jeśli będziemy potrzebować complex aggregations across backtests.
**10.6 Progressive loading vs all-at-once**
Decyzja: Progressive loading - najpierw price+indicators, potem signals, potem trades.
Uzasadnienie: Lepsze perceived performance - user widzi coś szybko zamiast czekać na wszystko. Pozwala na interakcję z wykresem (zoom, pan) przed załadowaniem wszystkich danych. Trade-off: więcej requestów (3 zamiast 1), ale dzięki równoległemu ładowaniu całkowity czas jest podobny, a UX znacznie lepszy.
**10.7 Realistyczna symulacja vs idealna**
Decyzja: Opcjonalna realistyczna symulacja (slippage, opóźnienia, częściowe wykonania) z możliwością wyłączenia.
Uzasadnienie: Idealna symulacja (zero slippage, instant execution) daje over-optimistic wyniki prowadzące do rozczarowania w live trading. Realistyczna symulacja (150ms opóźnienia, slippage based on volume) daje bardziej wiarygodne wyniki, lepiej przygotowuje do reality. Możliwość wyłączenia pozwala na porównanie "best case" vs "realistic case". Trade-off: dodatkowa complexity w implementacji, ale to jest critically important dla wiarygodności wyników.
**10.8 Partycjonowanie dla długich sesji**
Decyzja: Opcjonalne partycjonowanie pliku wskaźników per godzinę dla sesji > 6h.
Uzasadnienie: 24h sesja z 50 symbolami i 20 wskaźnikami generuje ~686 MB RAW data. Nawet z kompresją to ~137 MB. Wczytanie całości do pamięci jest problematyczne. Partycjonowanie pozwala na ładowanie tylko needed chunks (np. user ogląda 17:00-18:00, ładujemy tylko hour_1.parquet). Trade-off: więcej plików, complexity w logice ładowania, ale to jest critical dla scalability.
Alternatywa: Windowing bez partycjonowania - czytamy cały plik ale zwracamy tylko requested range. Odrzucona bo nadal wymaga wczytania całego pliku do pamięci (bottleneck dla bardzo dużych plików).
**10.9 Checkpointing vs atomic write**
Decyzja: Checkpointing co każda strategia-symbol para.
Uzasadnienie: Backtest może trwać 10+ minut dla dużych konfiguracji. Crash w 9 minucie bez checkpointingu oznacza utratę całej pracy. Checkpointing po każdej strategy-symbol parze pozwala na resume from checkpoint. Trade-off: dodatkowa complexity, więcej I/O operations, ale to jest worthwhile dla reliability.
**10.10 Walidacja referential integrity**
Decyzja: Mandatory walidacja po zakończeniu backtestingu.
Uzasadnienie: Zapobiega publikowaniu corrupted data. Jeśli signal odnosi się do nieistniejącego trade_id, frontend crashuje. Walidacja wykrywa takie problemy before deployment. Trade-off: dodatkowy czas na końcu backtestingu (~5-10 sekund), ale to jest negligible w porównaniu do czasu całego backtestingu.

### 11. ROADMAP IMPLEMENTACJI
**Faza 1: MVP Core (2 tygodnie)**

Session discovery (automatyczne skanowanie katalogów)
Basic configuration UI (wybór sesji, strategii, symboli)
Tick-by-tick simulation engine
Order Simulator z basic slippage (fixed percent)
Reużycie Indicator Engine i Strategy State Machine
Basic file structure (bez partycjonowania)
Simple summaries (bez advanced metrics)

**Faza 2: Results Analysis (1 tydzień)**

Results storage (hierarchiczna struktura plików)
Summary metrics calculation (wszystkie KPIs)
Dashboard UI (wyniki główne, per-strategy, per-symbol)
Trade explorer (tabela, filtrowanie, sortowanie)
Eliminacja duplikacji danych (single source of truth)

**Faza 3: Visualization (1 tydzień)***

Chart integration (Plotly.js lub alternatywa)
Indicators rendering (multiple y-axes)
Signal markers i trade levels
Interactive features (tooltips, click handlers, zoom/pan)
Progressive loading
Cache headers implementation

**Faza 4: Realistic Simulation (1 tydzień)**

Realistic slippage model (volume-based)
Latency simulation (configurable)
Partial fills handling
Advanced fee models
Market impact (opcjonalnie)

**Faza 5: Scale & Polish (1+ tydzień)**

Partycjonowanie dla długich sesji
Walidacja referential integrity
Checkpointing i auto-recovery
Performance optimization
Error handling improvements
UI polish (guided insights, presets, mobile considerations)


### 12. SUCCESS CRITERIA
System uznaje się za sukces jeśli:

Użytkownik może przetestować 3 strategie na 10 symbolach z 3-godzinnej sesji w czasie krótszym niż 5 minut
Wyniki są prezentowane w sposób czytelny i intuicyjny - użytkownik w ciągu 30 sekund potrafi zidentyfikować best performing strategy
Wizualizacja wykresu jest płynna i responsywna - zoom, pan, toggle indicators działa bez lagów
Powtórne ładowanie wyników jest natychmiastowe dzięki cachowaniu
System może obsłużyć sesje do 24h z 50 symbolami bez crashowania
Wyniki backtestingu są realistyczne - performance w backtestingu nie różni się drastycznie od live trading (dzięki symulacji slippage i opóźnień)



# USER REQUIREMENT:  USER_REC_06

GSPIS TREŚCI

Wprowadzenie
Konwencje i Zasady
Wskaźniki GENERAL (0-1)

Momentum Cenowego
Wolumen
Order Book
Zmienność (Volatility)
Momentum Zmienności
Detekcja Początku Pump
Odległość od Szczytu
Przejście Pump→Dump
Wygasanie Dump


Wskaźniki RISK (0-100)
Wskaźniki PRICE (Entry)
Wskaźniki STOP_LOSS
Wskaźniki TAKE_PROFIT
Wskaźniki CLOSE_ORDER
Przykładowe Kombinacje


WPROWADZENIE
Ten dokument zawiera szczegółową specyfikację wszystkich wskaźników systemowych używanych do detekcji i tradingu pump & dump. Każdy wskaźnik jest opisany z perspektywą implementacyjną, zawierając:

Dokładny algorytm obliczeniowy
Wszystkie parametry konfiguracyjne
Interpretację wartości
Przykłady użycia

Źródła Danych
Wskaźniki wykorzystują dwa główne pliki CSV:
prices.csv:

timestamp: czas transakcji
price: cena wykonania
volume: wolumen transakcji
quote_volume: wolumen w walucie bazowej

orderbook.csv:

timestamp: czas snapshot order book
best_bid: najlepsza cena kupna
best_ask: najlepsza cena sprzedaży
bid_qty: wielkość na bid
ask_qty: wielkość na ask
spread: różnica ask-bid


KONWENCJE I ZASADY
Parametry Czasowe
Wszystkie parametry czasowe są w sekundach wstecz od bieżącego momentu:

t1 > t2 oznacza okno [t1 sekund temu, t2 sekund temu]
Przykład: TWPA(300, 0) = średnia z ostatnich 5 minut (od 300s temu do teraz)

Normalizacja

Wskaźniki GENERAL: zakres [0, 1] dla łatwej interpretacji
Wskaźniki RISK: zakres [0, 100] dla intuicyjnego % ryzyka
Wskaźniki PRICE/SL/TP/CO: ceny w USD lub offsety %

Funkcje Pomocnicze
TWPA (Time-Weighted Price Average):
TWPA(t1, t2):
  Dla każdej transakcji i w oknie [t1, t2]:
    duration_i = min(timestamp_{i+1}, current_time - t2) - max(timestamp_i, current_time - t1)
    weight_i = duration_i
  return Σ(price_i × weight_i) / Σ(weight_i)
Sigmoid:
sigmoid(x) = 1 / (1 + exp(-x))
Tanh:
tanh(x) = (exp(x) - exp(-x)) / (exp(x) + exp(-x))

WSKAŹNIKI GENERAL
Zakres: [0, 1]
MOMENTUM CENOWEGO
TWPA_Momentum_Ratio
Typ: general
Zakres: [0, 1]
Cel: Relatywna siła momentum cenowego z wygładzaniem TWPA
Algorytm:
1. recent_twpa = TWPA(t1_recent, t2_recent)
2. baseline_twpa = TWPA(t1_baseline, t2_baseline)
3. raw_ratio = recent_twpa / baseline_twpa
4. normalized = (raw_ratio - 0.5) / 1.5
5. result = max(0, min(1, normalized))
Parametry:

t1_recent (int): Start recent window w sekundach wstecz, np. 15

Znaczenie: Jak daleko w przeszłość sięga okno "teraz"


t2_recent (int): End recent window, np. 0

Znaczenie: Koniec okna "teraz" (0 = bieżący moment)


t1_baseline (int): Start baseline window, np. 300

Znaczenie: Początek okna bazowego (5 min temu)


t2_baseline (int): End baseline window, np. 180

Znaczenie: Koniec okna bazowego (3 min temu)



Interpretacja:

0.0-0.3: Słabe momentum, cena poniżej baseline
0.3-0.5: Neutralne momentum
0.5-0.7: Rosnące momentum
0.7-1.0: Silne momentum, potencjalny pump

Przykład konfiguracji:
json{
  "variant_id": "gen_momentum_fast",
  "system_indicator": "TWPA_Momentum_Ratio",
  "type": "general",
  "parameters": {
    "t1_recent": 15,
    "t2_recent": 0,
    "t1_baseline": 300,
    "t2_baseline": 180
  }
}

Velocity_Normalized
Typ: general
Zakres: [0, 1]
Cel: Znormalizowana prędkość zmiany ceny
Algorytm:
1. current_twpa = TWPA(t1_current, t2_current)
2. previous_twpa = TWPA(t1_previous, t2_previous)
3. raw_velocity = (current_twpa - previous_twpa) / previous_twpa
4. velocity_percent = raw_velocity * 100
5. result = sigmoid(velocity_percent / velocity_scale)
Parametry:

t1_current (int): np. 10

Znaczenie: Start okna "teraz" (10s temu)


t2_current (int): np. 0

Znaczenie: End okna "teraz" (teraz)


t1_previous (int): np. 60

Znaczenie: Start okna "wcześniej" (1 min temu)


t2_previous (int): np. 10

Znaczenie: End okna "wcześniej" (10s temu)


velocity_scale (float): np. 20.0

Znaczenie: Skala dla sigmoid - 20% velocity → sigmoid(1) = 0.73



Interpretacja:

0.0-0.3: Spadek ceny
0.4-0.6: Stabilna cena
0.7-0.9: Umiarkowany wzrost
0.9-1.0: Gwałtowny wzrost (pump)

Przykład:
json{
  "variant_id": "gen_velocity_30s",
  "system_indicator": "Velocity_Normalized",
  "type": "general",
  "parameters": {
    "t1_current": 10,
    "t2_current": 0,
    "t1_previous": 60,
    "t2_previous": 10,
    "velocity_scale": 20.0
  }
}

Acceleration_Index
Typ: general
Zakres: [0, 1]
Cel: Przyspieszenie/opóźnienie (2. pochodna ceny)
Algorytm:
1. velocity_now = (TWPA(t1_now, t2_now) - TWPA(t1_prev1, t2_prev1)) / TWPA(t1_prev1, t2_prev1)
2. velocity_before = (TWPA(t1_prev1, t2_prev1) - TWPA(t1_prev2, t2_prev2)) / TWPA(t1_prev2, t2_prev2)
3. acceleration = velocity_now - velocity_before
4. result = sigmoid(acceleration * 100 / accel_scale)
Parametry:

t1_now (int): np. 5
t2_now (int): np. 0
t1_prev1 (int): np. 20
t2_prev1 (int): np. 5
t1_prev2 (int): np. 35
t2_prev2 (int): np. 20
accel_scale (float): np. 10.0

Znaczenie: Skala acceleration - większa wartość = mniejsza wrażliwość



Interpretacja:

0.0-0.3: Opóźnienie, momentum słabnie
0.4-0.6: Stałe tempo
0.7-1.0: Przyspieszenie, pump nabiera siły


Price_Z_Score_Normalized
Typ: general
Zakres: [0, 1]
Cel: Standaryzowana odchyłka ceny (wykrywanie ekstremów)
Algorytm:
1. prices = zbierz_ceny(lookback_seconds, 0)
2. mean_price = średnia(prices)
3. std_price = odchylenie_standardowe(prices)
4. current_price = TWPA(current_price_window, 0)
5. z_score = (current_price - mean_price) / std_price
6. result = sigmoid(z_score / z_scale)
Parametry:

lookback_seconds (int): np. 1800 (30 min)

Znaczenie: Okno do obliczenia średniej i odchylenia


z_scale (float): np. 3.0

Znaczenie: Z-score=3 (3 sigma) → sigmoid(1) = 0.73


current_price_window (int): np. 5

Znaczenie: Okno wygładzania dla bieżącej ceny



Interpretacja:

0.0-0.3: Cena znacznie poniżej normy
0.4-0.6: Cena w normie
0.6-0.8: Cena powyżej normy
0.8-1.0: Cena ekstremalnie wysoka (>2-3 sigma, alarm!)

Przykład:
json{
  "variant_id": "gen_z_score_30min",
  "system_indicator": "Price_Z_Score_Normalized",
  "type": "general",
  "parameters": {
    "lookback_seconds": 1800,
    "z_scale": 3.0,
    "current_price_window": 5
  }
}

WOLUMEN
Volume_Surge_Normalized
Typ: general
Zakres: [0, 1]
Cel: Relatywny wzrost wolumenu
Algorytm:
1. current_volume = sum_volume(t1_current, t2_current)
2. baseline_volume = sum_volume(t1_baseline, t2_baseline)
3. time_adjusted_baseline = baseline_volume * (t1_current - t2_current) / (t1_baseline - t2_baseline)
4. raw_ratio = current_volume / time_adjusted_baseline
5. result = 1 - exp(-raw_ratio / surge_scale)
Parametry:

t1_current (int): np. 30
t2_current (int): np. 0
t1_baseline (int): np. 600
t2_baseline (int): np. 0
surge_scale (float): np. 3.0

Znaczenie: Surge 3x → 1-exp(-1) = 0.63



Interpretacja:

0.0-0.3: Niski wolumen
0.3-0.5: Normalny wolumen
0.5-0.7: Podwyższony wolumen
0.7-1.0: Spike wolumenu (potencjalny pump start)


Volume_Momentum_Ratio
Typ: general
Zakres: [0, 1]
Cel: Tempo wzrostu wolumenu
Algorytm:
1. recent_volume = sum_volume(t1_recent, t2_recent)
2. baseline_volume = sum_volume(t1_baseline, t2_baseline)
3. time_adj_baseline = baseline_volume * (t1_recent - t2_recent) / (t1_baseline - t2_baseline)
4. raw_ratio = recent_volume / time_adj_baseline
5. result = 1 - exp(-raw_ratio / momentum_scale)
Parametry:

t1_recent (int): np. 30
t2_recent (int): np. 0
t1_baseline (int): np. 300
t2_baseline (int): np. 60
momentum_scale (float): np. 3.0

Interpretacja:

0.0-0.3: Wolumen spada
0.3-0.5: Wolumen stabilny
0.5-0.7: Wolumen rośnie
0.7-1.0: Wolumen eksploduje


Trade_Frequency_Index
Typ: general
Zakres: [0, 1]
Cel: Intensywność transakcji
Algorytm:
1. current_freq = count_deals(t1_current, t2_current) / (t1_current - t2_current)
2. baseline_freq = count_deals(t1_baseline, t2_baseline) / (t1_baseline - t2_baseline)
3. raw_ratio = current_freq / baseline_freq
4. result = 1 - exp(-raw_ratio / freq_scale)
Parametry:

t1_current (int): np. 60
t2_current (int): np. 0
t1_baseline (int): np. 1800
t2_baseline (int): np. 0
freq_scale (float): np. 5.0

Interpretacja:

0.0-0.4: Spokojna aktywność
0.4-0.6: Normalna aktywność
0.6-0.8: Zwiększona aktywność
0.8-1.0: Ekstremalna aktywność (boty?)


Volume_Price_Correlation
Typ: general
Zakres: [0, 1]
Cel: Korelacja zmian ceny i wolumenu (autentyczność pump)
Algorytm:
1. ticks = zbierz_ticke(lookback_seconds, 0)
2. Dla każdego ticka i:
   price_change[i] = (price[i] - price[i-1]) / price[i-1]
   volume_change[i] = volume[i] - avg_volume
3. correlation = pearson_correlation(price_changes, volume_changes)
4. result = (correlation + 1) / 2  // mapowanie [-1,1] → [0,1]
Parametry:

lookback_seconds (int): np. 300 (5 min)

Znaczenie: Okno analizy korelacji


min_ticks_required (int): np. 20

Znaczenie: Minimalna liczba ticków dla wiarygodności



Interpretacja:

0.0-0.3: Negatywna korelacja (wzrost ceny bez vol = słabe)
0.3-0.5: Brak korelacji
0.5-0.7: Umiarkowana korelacja
0.7-1.0: Silna korelacja (prawdziwy pump z wolumenem!)

Przykład:
json{
  "variant_id": "gen_vol_price_corr_5min",
  "system_indicator": "Volume_Price_Correlation",
  "type": "general",
  "parameters": {
    "lookback_seconds": 300,
    "min_ticks_required": 20
  }
}

ORDER BOOK
Bid_Ask_Imbalance_Normalized
Typ: general
Zakres: [0, 1], gdzie 0.5 = równowaga
Cel: Przewaga popytu vs podaży
Algorytm:
1. avg_bid = time_weighted_average(bid_qty, t1, t2)
2. avg_ask = time_weighted_average(ask_qty, t1, t2)
3. raw_imbalance = (avg_bid - avg_ask) / (avg_bid + avg_ask)  // [-1, 1]
4. result = (raw_imbalance + 1) / 2  // mapowanie [0, 1]
Parametry:

t1 (int): np. 60
t2 (int): np. 0

Interpretacja:

0.0-0.3: Dominacja ask (presja sprzedaży)
0.4-0.6: Równowaga
0.7-1.0: Dominacja bid (presja kupna, pump!)


Spread_Percentage_Normalized
Typ: general
Zakres: [0, 1]
Cel: Relatywna szerokość spreadu
Algorytm:
1. current_spread = time_weighted_average(spread, t1_current, t2_current)
2. baseline_spread = time_weighted_average(spread, t1_baseline, t2_baseline)
3. mid_price = (best_bid + best_ask) / 2
4. spread_pct = current_spread / mid_price * 100
5. baseline_spread_pct = baseline_spread / mid_price * 100
6. raw_ratio = spread_pct / baseline_spread_pct
7. result = tanh(raw_ratio / spread_scale)
Parametry:

t1_current (int): np. 30
t2_current (int): np. 0
t1_baseline (int): np. 600
t2_baseline (int): np. 0
spread_scale (float): np. 2.0

Interpretacja:

0.0-0.3: Wąski spread (dobra płynność)
0.3-0.5: Normalny spread
0.5-0.7: Szeroki spread
0.7-1.0: Bardzo szeroki spread (panika/brak płynności)


Liquidity_Drain_Index
Typ: general
Zakres: [0, 1]
Cel: Spadek płynności względem baseline
Algorytm:
1. current_liquidity = avg(bid_qty, t1_current, t2_current) + avg(ask_qty, t1_current, t2_current)
2. baseline_liquidity = avg(bid_qty, t1_baseline, t2_baseline) + avg(ask_qty, t1_baseline, t2_baseline)
3. drain_ratio = (baseline_liquidity - current_liquidity) / baseline_liquidity
4. result = max(0, min(1, drain_ratio))
Parametry:

t1_current (int): np. 60
t2_current (int): np. 0
t1_baseline (int): np. 1800
t2_baseline (int): np. 600

Interpretacja:

0.0-0.2: Płynność normalna/wzrosła
0.2-0.4: Lekki spadek płynności
0.4-0.6: Umiarkowany drain
0.6-1.0: Silny drain (smart money wychodzi)


Orderbook_Depth_Ratio
Typ: general
Zakres: [0, 1]
Cel: Stosunek płynności bid do ask (rozszerzona imbalance)
Algorytm:
1. avg_bid_qty = time_weighted_average(bid_qty, t1, t2)
2. avg_ask_qty = time_weighted_average(ask_qty, t1, t2)
3. raw_ratio = avg_bid_qty / avg_ask_qty
4. result = sigmoid((raw_ratio - 1) / ratio_scale)
Parametry:

t1 (int): np. 60
t2 (int): np. 0
ratio_scale (float): np. 1.0

Znaczenie: Ratio=2 (2x więcej bid) → sigmoid(1) = 0.73



Interpretacja:

0.0-0.3: Dużo więcej ask niż bid (presja sprzedaży)
0.4-0.6: Równowaga
0.7-1.0: Dużo więcej bid niż ask (presja kupna)


ZMIENNOŚĆ (VOLATILITY)
EWMA_Volatility_Normalized
Typ: general
Zakres: [0, 1]
Cel: Wykładniczo ważona zmienność (szybsza reakcja niż STD)
Algorytm:
1. ticks = zbierz_ticke(lookback_seconds, 0)
2. returns = [(price[i] - price[i-1]) / price[i-1] for każdego ticka]
3. ewma = 0
4. alpha = 2 / (ewma_period + 1)
5. Dla każdego return (od najstarszego):
   ewma = alpha * return² + (1 - alpha) * ewma
6. volatility = sqrt(ewma)
7. result = tanh(volatility * 100 / vol_scale)
Parametry:

lookback_seconds (int): np. 300
ewma_period (int): np. 20

Znaczenie: "Pamięć" EWMA - niższe = szybsza reakcja


vol_scale (float): np. 5.0

Znaczenie: 5% volatility → tanh(1) = 0.76



Interpretacja:

0.0-0.3: Niska zmienność
0.3-0.5: Normalna zmienność
0.5-0.7: Podwyższona zmienność
0.7-1.0: Wysoka zmienność (pump/dump w toku)

Przykład:
json{
  "variant_id": "gen_ewma_vol_5min",
  "system_indicator": "EWMA_Volatility_Normalized",
  "type": "general",
  "parameters": {
    "lookback_seconds": 300,
    "ewma_period": 20,
    "vol_scale": 5.0
  }
}

Standard_Deviation_Volatility
Typ: general
Zakres: [0, 1]
Cel: Podstawowa miara zmienności
Algorytm:
1. ticks = zbierz_ticke(lookback_seconds, 0)
2. returns = [(price[i] - price[i-1]) / price[i-1] for każdego ticka]
3. std = odchylenie_standardowe(returns)
4. result = tanh(std * 100 / vol_scale)
Parametry:

lookback_seconds (int): np. 300
vol_scale (float): np. 5.0

Interpretacja:

0.0-0.3: Stabilna cena
0.3-0.5: Normalna zmienność
0.5-0.7: Podwyższona zmienność
0.7-1.0: Bardzo zmienna cena


MOMENTUM ZMIENNOŚCI
Momentum_Volatility_1
Typ: general
Zakres: [0, 1]
Cel: Momentum zmienności - teraz vs wcześniej (INNOWACYJNY!)
Algorytm:
1. recent_vol = EWMA_Volatility(t1_recent, t2_recent, ewma_period)
2. baseline_vol = EWMA_Volatility(t1_baseline, t2_baseline, ewma_period)
3. raw_ratio = recent_vol / baseline_vol
4. result = 1 - exp(-raw_ratio / momentum_scale)
Parametry:

t1_recent (int): np. 30 (ostatnie 30s)
t2_recent (int): np. 0
t1_baseline (int): np. 300 (5 min temu)
t2_baseline (int): np. 60 (do 1 min temu)
ewma_period (int): np. 10
momentum_scale (float): np. 3.0

Znaczenie: 3x zmienność → 1-exp(-1) = 0.63



Interpretacja:

0.0-0.3: Zmienność spadła
0.3-0.5: Zmienność bez zmian
0.5-0.7: Zmienność rośnie
0.7-0.9: Zmienność eksploduje
0.9-1.0: Ekstremalna eksplozja zmienności (ALARM!)

Przykład:
json{
  "variant_id": "gen_momentum_vol_1",
  "system_indicator": "Momentum_Volatility_1",
  "type": "general",
  "parameters": {
    "t1_recent": 30,
    "t2_recent": 0,
    "t1_baseline": 300,
    "t2_baseline": 60,
    "ewma_period": 10,
    "momentum_scale": 3.0
  }
}

Momentum_Volatility_2
Typ: general
Zakres: [0, 1]
Cel: Krótkookresowe momentum zmienności (szybsza detekcja)
Algorytm:
1. very_recent_vol = EWMA_Volatility(t1_very_recent, t2_very_recent, ewma_period)
2. recent_vol = EWMA_Volatility(t1_recent, t2_recent, ewma_period)
3. raw_ratio = very_recent_vol / recent_vol
4. result = 1 - exp(-raw_ratio / momentum_scale)
Parametry:

t1_very_recent (int): np. 15 (ostatnie 15s)
t2_very_recent (int): np. 0
t1_recent (int): np. 120 (2 min temu)
t2_recent (int): np. 30 (do 30s temu)
ewma_period (int): np. 5
momentum_scale (float): np. 3.0

Interpretacja:

Podobnie do Momentum_Vol_1, ale wykrywa NAJNOWSZE zmiany
Użyj razem z Momentum_Vol_1 do analizy "przyspieszenia"


Magnitude_Volatility
Typ: general
Zakres: [0, 1]
Cel: Przyspieszenie zmienności - 2. pochodna! (KLUCZOWY DLA PUMP/DUMP)
Algorytm:
1. momentum_1 = Momentum_Volatility_1(params_1)
2. momentum_2 = Momentum_Volatility_2(params_2)
3. magnitude = abs(momentum_2 - momentum_1) / (momentum_1 + epsilon)
4. result = tanh(magnitude / magnitude_scale)
Parametry:

params_momentum_1: dict z parametrami dla Momentum_Vol_1
params_momentum_2: dict z parametrami dla Momentum_Vol_2
magnitude_scale (float): np. 0.5

Znaczenie: 50% zmiana momentum → tanh(1) = 0.76


epsilon (float): np. 0.01 (avoid division by zero)

Interpretacja:

0.0-0.3: Momentum stabilne
0.3-0.5: Momentum zmienia się
0.5-0.7: Znacząca zmiana momentum
0.7-0.9: Dramatyczna zmiana (pump/dump start!)
0.9-1.0: EKSTREMALNA ZMIANA REŻIMU - NAJSILNIEJSZY SYGNAŁ!

Uwaga: To najlepszy wskaźnik do wykrycia momentu rozpoczęcia pump/dump!
Przykład:
json{
  "variant_id": "gen_magnitude_vol",
  "system_indicator": "Magnitude_Volatility",
  "type": "general",
  "parameters": {
    "params_momentum_1": {
      "t1_recent": 30,
      "t2_recent": 0,
      "t1_baseline": 300,
      "t2_baseline": 60,
      "ewma_period": 10,
      "momentum_scale": 3.0
    },
    "params_momentum_2": {
      "t1_very_recent": 15,
      "t2_very_recent": 0,
      "t1_recent": 120,
      "t2_recent": 30,
      "ewma_period": 5,
      "momentum_scale": 3.0
    },
    "magnitude_scale": 0.5,
    "epsilon": 0.01
  }
}

DETEKCJA POCZĄTKU PUMP
Early_Pump_Ignition_Score
Typ: general
Zakres: [0, 1]
Cel: Wykrycie bardzo wczesnej fazy pump (pierwsze sekundy)
Algorytm:
1. Volume acceleration:
   recent_vol = sum_volume(10, 0)
   baseline_vol = sum_volume(60, 10)
   vol_ratio = recent_vol / (baseline_vol / 5)
   vol_score = tanh(vol_ratio / 3.0)

2. Price spike:
   recent_twpa = TWPA(5, 0)
   baseline_twpa = TWPA(120, 60)
   price_jump = (recent_twpa - baseline_twpa) / baseline_twpa
   price_score = tanh(price_jump * 100 / 5.0)

3. Trade frequency burst:
   recent_freq = count_deals(15, 0) / 15
   baseline_freq = count_deals(300, 30) / 270
   freq_ratio = recent_freq / baseline_freq
   freq_score = tanh(freq_ratio / 4.0)

4. Bid pressure shift:
   recent_imbalance = avg(bid_qty - ask_qty, 15, 0) / avg(bid_qty + ask_qty, 15, 0)
   baseline_imbalance = avg(bid_qty - ask_qty, 300, 60) / avg(bid_qty + ask_qty, 300, 60)
   pressure_shift = recent_imbalance - baseline_imbalance
   pressure_score = sigmoid(pressure_shift * 5)

5. Composite:
   result = (vol_score * w_vol + price_score * w_price + 
            freq_score * w_freq + pressure_score * w_pressure) / sum(weights)
Parametry:

recent_volume_window (int): np. 10
baseline_volume_start (int): np. 60
baseline_volume_end (int): np. 10
volume_surge_threshold (float): np. 3.0
recent_price_window (int): np. 5
baseline_price_start (int): np. 120
baseline_price_end (int): np. 60
price_spike_scale (float): np. 5.0
recent_freq_window (int): np. 15
baseline_freq_start (int): np. 300
baseline_freq_end (int): np. 30
freq_surge_threshold (float): np. 4.0
recent_pressure_window (int): np. 15
baseline_pressure_start (int): np. 300
baseline_pressure_end (int): np. 60
pressure_sensitivity (float): np. 5.0
weight_volume (float): np. 0.35
weight_price (float): np. 0.30
weight_frequency (float): np. 0.20
weight_pressure (float): np. 0.15

Interpretacja:

0.0-0.3: Normalny rynek
0.3-0.5: Zwiększona aktywność
0.5-0.7: Prawdopodobne rozpoczęcie pump
0.7-0.9: Silny sygnał pump ignition
0.9-1.0: Ekstremalnie silny pump start


Coordinated_Action_Detector
Typ: general
Zakres: [0, 1]
Cel: Wykrycie skoordynowanej akcji (boty/grupa)
Algorytm:
1. Trade size uniformity:
   volumes = [vol_i dla wszystkich deals w oknie]
   cv = coefficient_of_variation(volumes)  // std/mean
   uniformity_score = 1 - tanh(cv)

2. Inter-deal interval regularity:
   intervals = [timestamp_i+1 - timestamp_i]
   interval_cv = coefficient_of_variation(intervals)
   regularity_score = 1 - tanh(interval_cv * 0.5)

3. Bid-ask simultaneous movement:
   bid_changes = [bid_i - bid_i-1]
   ask_changes = [ask_i - ask_i-1]
   correlation = pearson_correlation(bid_changes, ask_changes)
   sync_score = (correlation + 1) / 2

4. Volume clustering:
   volume_time_series = [sum_volume w sub-windows]
   variance = var(volume_time_series)
   mean = avg(volume_time_series)
   clustering = variance / (mean²)  // Fano factor
   cluster_score = tanh(clustering / 2.0)

5. Composite:
   result = (uniformity_score * w1 + regularity_score * w2 + 
            sync_score * w3 + cluster_score * w4) / sum(weights)
Parametry:

analysis_window (int): np. 60
min_deals_required (int): np. 10
sub_window_size (int): np. 10
weight_uniformity (float): np. 0.30
weight_regularity (float): np. 0.25
weight_synchronization (float): np. 0.25
weight_clustering (float): np. 0.20

Interpretacja:

0.0-0.3: Organiczny trading
0.3-0.5: Możliwa koordynacja
0.5-0.7: Prawdopodobna skoordynowana akcja
0.7-1.0: Wysoka pewność bot activity/pump group


Microstructure_Break_Detector
Typ: general
Zakres: [0, 1]
Cel: Wykrycie "złamania" normalnej mikrostruktury
Algorytm:
1. Spread compression anomaly:
   current_spread_pct = avg(spread / mid_price, 15, 0) * 100
   baseline_spread_pct = avg(spread / mid_price, 300, 60) * 100
   compression_ratio = current_spread_pct / baseline_spread_pct
   spread_score = 1 - tanh(compression_ratio)

2. Price-orderbook divergence:
   deal_twpa = TWPA(30, 0)
   mid_price_twpa = time_weighted_avg((bid + ask)/2, 30, 0)
   divergence = abs(deal_twpa - mid_price_twpa) / mid_price_twpa
   divergence_score = tanh(divergence * 100 / 0.5)

3. Liquidity imbalance surge:
   recent_imb = abs(Bid_Ask_Imbalance_Normalized(15, 0) - 0.5) * 2
   baseline_imb = abs(Bid_Ask_Imbalance_Normalized(300, 60) - 0.5) * 2
   imbalance_ratio = recent_imb / (baseline_imb + 0.1)
   imbalance_score = tanh(imbalance_ratio / 2.0)

4. Deal size explosion:
   recent_avg_size = avg_volume(15, 0) / count_deals(15, 0)
   baseline_avg_size = avg_volume(300, 60) / count_deals(300, 60)
   size_ratio = recent_avg_size / baseline_avg_size
   size_score = tanh(size_ratio / 3.0)

5. Composite:
   result = (spread_score * w1 + divergence_score * w2 + 
            imbalance_score * w3 + size_score * w4) / sum(weights)
Parametry:

recent_window (int): np. 15
baseline_start (int): np. 300
baseline_end (int): np. 60
weight_spread (float): np. 0.25
weight_divergence (float): np. 0.30
weight_imbalance (float): np. 0.25
weight_size (float): np. 0.20

Interpretacja:

0.0-0.3: Normalna mikrostruktura
0.3-0.5: Drobne anomalie
0.5-0.7: Znaczące złamanie struktury
0.7-1.0: Ekstremalna anomalia (pump imminent)


ODLEGŁOŚĆ OD SZCZYTU
Distance_To_Peak_Predictor
Typ: general
Zakres: [0, 1], gdzie 0 = szczyt, 1 = daleko od szczytu
Cel: Przewidywanie odległości od szczytu pump
Algorytm:
1. Momentum sustainability:
   current_velocity = (TWPA(5, 0) - TWPA(30, 5)) / TWPA(30, 5)
   peak_velocity = max([velocity_i w rolling windows, last 300s])
   momentum_component = current_velocity / peak_velocity

2. Volume exhaustion indicator:
   current_volume = sum_volume(30, 0)
   peak_volume = max([sum_volume w rolling 30s windows, last 300s])
   volume_component = current_volume / peak_volume

3. Price extension measure:
   current_price = TWPA(5, 0)
   baseline_price = TWPA(600, 300)
   pump_magnitude = current_price - baseline_price
   extension_ratio = pump_magnitude / baseline_price / historical_avg_magnitude
   price_component = max(0, 1 - extension_ratio)

4. Liquidity drain factor:
   liquidity_drain = Liquidity_Drain_Index(params)
   liquidity_component = 1 - liquidity_drain

5. Bid pressure decay:
   current_pressure = Bid_Ask_Imbalance_Normalized(30, 0)
   peak_pressure = max([Bid_Ask_Imbalance w rolling, last 300s])
   pressure_component = current_pressure / max(peak_pressure, 0.5)

6. Composite distance:
   result = (momentum_component * w1 + volume_component * w2 + 
            price_component * w3 + liquidity_component * w4 + 
            pressure_component * w5) / sum(weights)
Parametry:

velocity_current_window (int): np. 5
velocity_previous_window (int): np. 30
velocity_lookback (int): np. 300
volume_current_window (int): np. 30
volume_lookback (int): np. 300
price_current_window (int): np. 5
price_baseline_start (int): np. 600
price_baseline_end (int): np. 300
historical_avg_pump_pct (float): np. 0.15 (assume 15% avg pump)
liquidity_drain_params (dict): parametry dla Liquidity_Drain_Index
pressure_window (int): np. 30
pressure_lookback (int): np. 300
weight_momentum (float): np. 0.30
weight_volume (float): np. 0.25
weight_price_extension (float): np. 0.20
weight_liquidity (float): np. 0.15
weight_pressure (float): np. 0.10

Interpretacja:

0.9-1.0: Daleko od szczytu, pump dopiero się rozkręca
0.7-0.9: Średnia odległość, pump trwa
0.5-0.7: Zbliżamy się do szczytu
0.3-0.5: Blisko szczytu, przygotuj się
0.0-0.3: Prawdopodobnie jesteśmy na szczycie lub tuż po


Peak_Proximity_Score
Typ: general
Zakres: [0, 1], gdzie 1 = najbliżej szczytu
Cel: Odwrotność Distance_To_Peak (łatwiejsza interpretacja)
Algorytm:
1. distance = Distance_To_Peak_Predictor(params)
2. result = 1 - distance
Parametry:

distance_params (dict): wszystkie parametry z Distance_To_Peak_Predictor

Interpretacja:

0.0-0.2: Daleko od szczytu
0.2-0.5: Średnia odległość
0.5-0.7: Blisko szczytu
0.7-1.0: Jesteśmy przy szczycie


Pump_Lifecycle_Stage
Typ: general
Zakres: [0, 1], gdzie 0=ignition, 0.5=peak, 1=exhaustion
Cel: Określenie fazy pump lifecycle
Algorytm:
1. Zidentyfikuj pump start:
   Scan backwards dla momentu gdzie:
   - Volume surge > 3x baseline
   - Price velocity > 10%/min
   Save pump_start_time

2. Time elapsed ratio:
   time_since_start = current_time - pump_start_time
   time_ratio = min(1.0, time_since_start / typical_pump_duration)

3. Acceleration phase indicator:
   current_accel = Acceleration_Index(params)
   if current_accel > 0.6: phase_adjust = -0.2
   elif current_accel < 0.4: phase_adjust = +0.2
   else: phase_adjust = 0

4. Volume pattern analysis:
   volume_history = [sum_volume w rolling 30s windows od pump_start]
   current_volume_rank = percentile_rank(current_volume, volume_history)
   volume_indicator = 1 - current_volume_rank

5. Composite stage:
   raw_stage = (time_ratio * 0.4 + volume_indicator * 0.4 + 
               Peak_Proximity_Score * 0.2) + phase_adjust
   result = max(0, min(1, raw_stage))
Parametry:

pump_detection_volume_threshold (float): np. 3.0
pump_detection_velocity_threshold (float): np. 10.0
typical_pump_duration (int): np. 180 sekund
max_lookback_for_start (int): np. 600
acceleration_params (dict): parametry dla Acceleration_Index
volume_window (int): np. 30

Interpretacja:

0.0-0.2: Ignition phase (pump starts)
0.2-0.4: Acceleration phase (pump growing)
0.4-0.6: Peak zone (szczyt blisko)
0.6-0.8: Deceleration phase (momentum dying)
0.8-1.0: Exhaustion phase (pump ending)


PRZEJŚCIE PUMP→DUMP
Pump_To_Dump_Transition_Score
Typ: general
Zakres: [0, 1], gdzie 1 = pewne przejście
Cel: Wykrycie momentu przejścia z pump do dump
Algorytm:
1. Momentum reversal:
   recent_velocity = (TWPA(5, 0) - TWPA(20, 5)) / TWPA(20, 5)
   previous_velocity = (TWPA(20, 5) - TWPA(35, 20)) / TWPA(35, 20)
   
   if recent_velocity < 0 and previous_velocity > 0:
     reversal_strength = abs(recent_velocity) / (abs(previous_velocity) + 0.01)
     reversal_component = tanh(reversal_strength)
   else:
     reversal_component = 0

2. Volume divergence:
   distance_from_peak = Distance_To_Peak_Predictor(params)
   volume_exhaustion = Volume_Exhaustion_Risk(params) / 100
   
   if distance_from_peak < 0.3 and volume_exhaustion > 0.7:
     divergence_component = (0.3 - distance_from_peak) / 0.3 * volume_exhaustion
   else:
     divergence_component = 0

3. Order flow reversal:
   recent_imbalance = Bid_Ask_Imbalance_Normalized(20, 0)
   baseline_imbalance = Bid_Ask_Imbalance_Normalized(120, 60)
   
   if baseline_imbalance > 0.6 and recent_imbalance < 0.4:
     flow_reversal = (baseline_imbalance - recent_imbalance) / baseline_imbalance
     flow_component = flow_reversal
   else:
     flow_component = 0

4. Spread widening panic:
   recent_spread = avg(spread / mid_price, 15, 0) * 100
   baseline_spread = avg(spread / mid_price, 120, 60) * 100
   spread_expansion = recent_spread / baseline_spread
   panic_component = tanh((spread_expansion - 1.0) / 2.0)

5. Price acceleration negative:
   accel = Acceleration_Index(params)
   if accel < 0.3:
     accel_component = 1 - accel / 0.3
   else:
     accel_component = 0

6. Composite (używa max + avg contribution):
   transition_score = max(
     reversal_component * 0.9,
     divergence_component * 0.85,
     flow_component * 0.8,
     panic_component * 0.75,
     accel_component * 0.7
   )
   
   avg_contribution = (reversal_component + divergence_component + 
                      flow_component + panic_component + accel_component) / 5 * 0.3
   
   result = min(1.0, transition_score + avg_contribution)
Parametry:

velocity_recent_window (int): np. 5
velocity_previous_window (int): np. 20
distance_to_peak_params (dict)
volume_exhaustion_params (dict)
imbalance_recent_window (int): np. 20
imbalance_baseline_start (int): np. 120
imbalance_baseline_end (int): np. 60
imbalance_pump_threshold (float): np. 0.6
imbalance_reversal_threshold (float): np. 0.4
spread_recent_window (int): np. 15
spread_baseline_start (int): np. 120
spread_baseline_end (int): np. 60
acceleration_params (dict)

Interpretacja:

0.0-0.2: Pump trwa
0.2-0.4: Wczesne sygnały osłabienia
0.4-0.6: Prawdopodobne przejście rozpoczęte
0.6-0.8: Silne sygnały przejścia
0.8-1.0: Pewne przejście pump→dump


Dump_Initiation_Confidence
Typ: general
Zakres: [0, 1]
Cel: Pewność że dump właśnie się zaczął
Algorytm:
1. Price drop confirmation:
   max_price_recent = max_price(60, 0)
   current_price = TWPA(3, 0)
   drop_pct = (max_price_recent - current_price) / max_price_recent
   drop_score = tanh(drop_pct * 100 / 3.0)

2. Consecutive negative ticks:
   prices = [price_i for last 10 ticks]
   negative_count = count(prices[i] < prices[i-1])
   consecutive_score = negative_count / 10

3. Volume on downmove:
   down_ticks = [tick gdzie price dropped]
   volume_on_down = sum([volume_i for down_ticks])
   total_volume = sum_volume(30, 0)
   volume_confirmation = volume_on_down / total_volume

4. Spread during drop:
   spread_during_drop = avg([spread_i podczas down_ticks])
   baseline_spread = avg(spread, 120, 60)
   spread_ratio = spread_during_drop / baseline_spread
   spread_confirmation = tanh((spread_ratio - 1) / 2)

5. Transition score confirmation:
   transition = Pump_To_Dump_Transition_Score(params)

6. Composite:
   result = (drop_score * w1 + consecutive_score * w2 + 
            volume_confirmation * w3 + spread_confirmation * w4 + 
            transition * w5) / sum(weights)
Parametry:

max_price_lookback (int): np. 60
current_price_window (int): np. 3
drop_threshold_scale (float): np. 3.0
consecutive_ticks_count (int): np. 10
volume_analysis_window (int): np. 30
spread_baseline_start (int): np. 120
spread_baseline_end (int): np. 60
transition_score_params (dict)
weight_price_drop (float): np. 0.30
weight_consecutive (float): np. 0.15
weight_volume (float): np. 0.25
weight_spread (float): np. 0.15
weight_transition (float): np. 0.15

Interpretacja:

0.0-0.3: Brak potwierdzenia dump
0.3-0.5: Możliwy dump
0.5-0.7: Prawdopodobny dump
0.7-0.9: Silne potwierdzenie dump
0.9-1.0: Pewny dump w toku


WYGASANIE DUMP
Dump_Exhaustion_Score
Typ: general
Zakres: [0, 1], gdzie 1 = dump wyczerpany
Cel: Wykrycie końca dump
Algorytm:
1. Velocity deceleration:
   current_velocity = abs((TWPA(5, 0) - TWPA(20, 5)) / TWPA(20, 5))
   peak_dump_velocity = max([abs(velocity_i) w rolling windows od dump start])
   decel_score = 1 - (current_velocity / peak_dump_velocity)

2. Selling volume exhaustion:
   volume_during_dump = [sum_volume w rolling 30s windows od dump start]
   peak_dump_volume = max(volume_during_dump)
   current_volume = sum_volume(30, 0)
   volume_score = 1 - (current_volume / peak_dump_volume)

3. Support level proximity:
   current_price = TWPA(5, 0)
   support_level = find_nearest_support(lookback=3600)
   distance_to_support = abs(current_price - support_level) / support_level
   support_score = 1 - tanh(distance_to_support * 100)

4. Price stabilization:
   recent_volatility = Price_Volatility_Risk(60, 10) / 100
   dump_peak_volatility = max([volatility w rolling windows od dump start]) / 100
   stability_score = 1 - (recent_volatility / dump_peak_volatility)

5. Bid support emergence:
   recent_imbalance = Bid_Ask_Imbalance_Normalized(30, 0)
   dump_avg_imbalance = avg([Imbalance w rolling od dump start])
   support_emergence = max(0, recent_imbalance - dump_avg_imbalance) / 0.5
   bid_score = min(1, support_emergence)

6. Panic subsiding:
   recent_spread = avg(spread / mid_price, 20, 0) * 100
   peak_dump_spread = max([spread_pct w rolling od dump start])
   panic_score = 1 - (recent_spread / peak_dump_spread)

7. Composite:
   result = (decel_score * w1 + volume_score * w2 + 
            support_score * w3 + stability_score * w4 + 
            bid_score * w5 + panic_score * w6) / sum(weights)
Parametry:

velocity_current_window (int): np. 5
velocity_previous_window (int): np. 20
velocity_lookback_for_peak (int): np. 300
volume_window (int): np. 30
volume_lookback_for_peak (int): np. 300
support_detection_lookback (int): np. 3600
support_tolerance (float): np. 0.01
min_support_touches (int): np. 2
volatility_window (int): np. 60
volatility_step (int): np. 10
volatility_lookback_for_peak (int): np. 300
imbalance_recent_window (int): np. 30
imbalance_lookback_for_avg (int): np. 120
spread_recent_window (int): np. 20
spread_lookback_for_peak (int): np. 300
weight_deceleration (float): np. 0.25
weight_volume (float): np. 0.20
weight_support (float): np. 0.20
weight_stability (float): np. 0.15
weight_bid_support (float): np. 0.10
weight_panic (float): np. 0.10

Interpretacja:

0.0-0.3: Dump w pełni
0.3-0.5: Dump słabnie
0.5-0.7: Znaczące wyczerpanie
0.7-0.9: Dump prawdopodobnie skończony
0.9-1.0: Dump definitywnie wyczerpany


Bounce_Probability_Score
Typ: general
Zakres: [0, 1]
Cel: Prawdopodobieństwo odbicia po dump
Algorytm:
1. Dump exhaustion check:
   exhaustion = Dump_Exhaustion_Score(params)

2. Oversold condition:
   current_price = TWPA(5, 0)
   pre_pump_baseline = TWPA(1800, 900)
   drop_from_baseline = (pre_pump_baseline - current_price) / pre_pump_baseline
   
   if drop_from_baseline > 0:
     oversold_score = tanh(drop_from_baseline * 100 / 10)
   else:
     oversold_score = 0

3. Volume pattern reversal:
   support_level = find_nearest_support()
   distance_to_support = abs(current_price - support_level) / support_level
   
   if distance_to_support < 0.02:
     recent_volume = sum_volume(15, 0)
     baseline_volume = sum_volume(300, 60)
     volume_spike = recent_volume / (baseline_volume / 20)
     volume_reversal = tanh(volume_spike / 2)
   else:
     volume_reversal = 0

4. Positive momentum emergence:
   recent_velocity = (TWPA(5, 0) - TWPA(15, 5)) / TWPA(15, 5)
   if recent_velocity > 0:
     momentum_score = tanh(recent_velocity * 100 / 2)
   else:
     momentum_score = 0

5. Bid-ask flip:
   recent_imbalance = Bid_Ask_Imbalance_Normalized(20, 0)
   dump_imbalance = Bid_Ask_Imbalance_Normalized(120, 60)
   
   if recent_imbalance > 0.5 and dump_imbalance < 0.5:
     flip_score = (recent_imbalance - 0.5) * 2
   else:
     flip_score = 0

6. Composite:
   result = (exhaustion * w1 + oversold_score * w2 + 
            volume_reversal * w3 + momentum_score * w4 + 
            flip_score * w5) / sum(weights)
Parametry:

exhaustion_params (dict)
baseline_start (int): np. 1800
baseline_end (int): np. 900
oversold_threshold_scale (float): np. 10.0
support_proximity_threshold (float): np. 0.02
volume_spike_window (int): np. 15
volume_baseline_start (int): np. 300
volume_baseline_end (int): np. 60
velocity_current (int): np. 5
velocity_previous (int): np. 15
imbalance_recent (int): np. 20
imbalance_dump_start (int): np. 120
imbalance_dump_end (int): np. 60
weight_exhaustion (float): np. 0.35
weight_oversold (float): np. 0.25
weight_volume (float): np. 0.20
weight_momentum (float): np. 0.10
weight_flip (float): np. 0.10

Interpretacja:

0.0-0.2: Bardzo niskie prawdopodobieństwo bounce
0.2-0.4: Niskie prawdopodobieństwo
0.4-0.6: Średnie prawdopodobieństwo
0.6-0.8: Wysokie prawdopodobieństwo bounce
0.8-1.0: Bardzo wysokie (imminent bounce)


WSKAŹNIKI RISK
Zakres: [0, 100]
Price_Volatility_Risk
Typ: risk
Zakres: [0, 100]
Cel: Kwantyfikacja zmienności jako ryzyko
Algorytm:
1. prices = [TWPA(i*step, (i+1)*step) for i in range(window/step)]
2. returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
3. stdev = standard_deviation(returns)
4. annualized_vol = stdev * sqrt(periods_per_year)
5. result = min(100, annualized_vol * volatility_multiplier)
Parametry:

window (int): np. 600 sekund

Znaczenie: Okno do obliczenia zmienności


step (int): np. 30 sekund

Znaczenie: Granulacja próbkowania


volatility_multiplier (float): np. 100.0

Znaczenie: Skala do 0-100 range



Interpretacja:

0-20: Niskie ryzyko (stabilna cena)
20-40: Umiarkowane ryzyko
40-60: Wysokie ryzyko (volatile)
60-100: Ekstremalne ryzyko (pump/dump w toku)


ATR_Risk_Percentage
Typ: risk
Zakres: [0, 100]
Cel: Average True Range jako procent ceny
Algorytm:
1. ranges = []
2. Dla każdego tick w oknie:
     range_i = abs(price_i - price_i-1)
     ranges.append(range_i)
3. atr = exponential_moving_average(ranges, alpha=2/(period+1))
4. atr_percent = (atr / current_price) * 100
5. result = min(100, atr_percent * atr_multiplier)
Parametry:

period (int): np. 50 ticków

Znaczenie: Okres EMA dla ATR


lookback_seconds (int): np. 300

Znaczenie: Maksymalne okno wstecz


atr_multiplier (float): np. 20.0

Znaczenie: Skala do 0-100



Interpretacja:

0-15: Niski ATR (spokojny rynek)
15-30: Normalny ATR
30-50: Podwyższony ATR
50-100: Ekstremalny ATR (pump/dump)


Momentum_Death_Risk
Typ: risk
Zakres: [0, 100]
Cel: Jak daleko momentum spadło od szczytu
Algorytm:
1. current_velocity = Velocity_Normalized(current_params)
2. max_velocity = max([Velocity_Normalized w rolling windows z ostatnich lookback_seconds])
3. death_ratio = (max_velocity - current_velocity) / max_velocity
4. result = death_ratio * 100
Parametry:

current_velocity_params (dict): parametry dla Velocity_Normalized
lookback_seconds (int): np. 600

Znaczenie: Okno szukania maksimum


rolling_window_step (int): np. 30

Znaczenie: Step dla rolling windows



Interpretacja:

0-20: Momentum silne (pump trwa)
20-40: Momentum osłabia się
40-60: Znaczący spadek momentum
60-100: Momentum umarło (szczyt minął)


Volume_Exhaustion_Risk
Typ: risk
Zakres: [0, 100]
Cel: Stopień wyczerpania wolumenu
Algorytm:
1. volume_surge_history = [Volume_Surge_Normalized(...) dla rolling windows]
2. max_surge = max(volume_surge_history w lookback_period)
3. current_surge = Volume_Surge_Normalized(current_params)
4. exhaustion_ratio = (max_surge - current_surge) / max_surge
5. result = exhaustion_ratio * 100
Parametry:

current_surge_params (dict): parametry dla Volume_Surge_Normalized
lookback_seconds (int): np. 600
rolling_window_step (int): np. 30

Interpretacja:

0-20: Wolumen silny
20-40: Wolumen osłabia się
40-70: Znaczące wyczerpanie
70-100: Wolumen prawie martwy (dump imminent)


Liquidity_Collapse_Risk
Typ: risk
Zakres: [0, 100]
Cel: Ryzyko nagłego braku płynności
Algorytm:
1. liquidity_drain = Liquidity_Drain_Index(drain_params)
2. spread_expansion = Spread_Percentage_Normalized(spread_params)
3. composite_risk = (liquidity_drain * drain_weight + 
                    spread_expansion * spread_weight) / (drain_weight + spread_weight)
4. result = composite_risk * 100
Parametry:

drain_params (dict): dla Liquidity_Drain_Index
spread_params (dict): dla Spread_Percentage_Normalized
drain_weight (float): np. 0.6
spread_weight (float): np. 0.4

Interpretacja:

0-25: Płynność dobra
25-50: Płynność słabnie
50-75: Płynność krytyczna
75-100: Płynność zapadła się (emergency exit)


Pump_Reversal_Risk
Typ: risk
Zakres: [0, 100]
Cel: Całkowite ryzyko odwrócenia pumpa
Algorytm:
1. momentum_death = Momentum_Death_Risk(...)
2. volume_exhaustion = Volume_Exhaustion_Risk(...)
3. liquidity_collapse = Liquidity_Collapse_Risk(...)
4. composite = (momentum_death * w1 + volume_exhaustion * w2 + 
               liquidity_collapse * w3) / (w1 + w2 + w3)
5. result = composite
Parametry:

momentum_death_params (dict)
volume_exhaustion_params (dict)
liquidity_collapse_params (dict)
weight_momentum (float): np. 0.35
weight_volume (float): np. 0.35
weight_liquidity (float): np. 0.30

Interpretacja:

0-30: Niskie ryzyko reversal
30-50: Umiarkowane ryzyko
50-70: Wysokie ryzyko (szczyt blisko)
70-100: Ekstremalnie wysokie (dump started/imminent)


Flash_Crash_Risk
Typ: risk
Zakres: [0, 100]
Cel: Ryzyko gwałtownego crash
Algorytm:
1. liquidity_drain = Liquidity_Drain_Index(params)
2. recent_spread = avg(spread / mid_price, 15, 0) * 100
3. baseline_spread = avg(spread / mid_price, 300, 60) * 100
4. spread_ratio = recent_spread / baseline_spread
5. recent_total_liquidity = avg(bid_qty + ask_qty, 30, 0)
6. baseline_liquidity = avg(bid_qty + ask_qty, 600, 300)
7. thinness_ratio = baseline_liquidity / recent_total_liquidity
8. recent_vol = Price_Volatility_Risk(60, 10) / 100
9. baseline_vol = Price_Volatility_Risk(600, 30) / 100
10. vol_ratio = recent_vol / baseline_vol
11. result = min(100, liquidity_drain * 30 + 
                     (spread_ratio - 1) * 20 + 
                     (thinness_ratio - 1) * 30 + 
                     (vol_ratio - 1) * 20)
Parametry:

liquidity_drain_params (dict)
spread_recent_window (int): np. 15
spread_baseline_start (int): np. 300
spread_baseline_end (int): np. 60
liquidity_recent_window (int): np. 30
liquidity_baseline_start (int): np. 600
liquidity_baseline_end (int): np. 300
volatility_recent_window (int): np. 60
volatility_recent_step (int): np. 10
volatility_baseline_window (int): np. 600
volatility_baseline_step (int): np. 30

Interpretacja:

0-25: Niskie ryzyko flash crash
25-50: Umiarkowane ryzyko
50-75: Wysokie ryzyko
75-100: Ekstremalne ryzyko (flash crash possible any moment)


9. Micro-Reversal Count (Licznik Mikro-Odwróceń)
Typ: risk
Koncepcja: Pump często ma małe "zawahania" - cena idzie w górę, ale co kilka ticków lekko cofa. Naturalna volatility nie ma tego wzorca.
Algorytm:
# Ostatnie 20 zmian ceny
price_changes = [price[i] - price[i-1] for last 20]

# Policz ile razy zmiana zmieniła znak ale WRÓCIŁA do głównego trendu
main_trend = sign(sum(price_changes))  # +1 lub -1

micro_reversals = 0
for i in range(1, len(price_changes)):
    if sign(price_changes[i]) != sign(price_changes[i-1]):
        # Była zmiana kierunku
        if sign(price_changes[i]) == main_trend:
            # I wróciła do głównego trendu
            micro_reversals += 1

reversal_rate = micro_reversals / 20
Operacje: ~30 operacji, <3ms
Co to wykrywa:

reversal_rate > 0.4 = dużo mikro-cofnięć które wracają do trendu

ZNACZENIE: "Step-wise pump" - manipulator podnosi cenę stopniowo z przerwami = PUMP PATTERN


reversal_rate < 0.1 = brak odwróceń, tylko jeden kierunek

ZNACZENIE: Agresywny pump bez wahań LUB naturalna zmienność
Normalny rynek: ~0.2-0.3
Próg: >0.35 = pattern pumpowania


Manipulation_Detection_Risk
Typ: risk
Zakres: [0, 100]
Cel: Prawdopodobieństwo że trwa manipulacja
Algorytm:
1. coordination = Coordinated_Action_Detector(params)
2. coord_risk = coordination * 50

3. break_score = Microstructure_Break_Detector(params)
4. micro_risk = break_score * 30

5. volumes = [vol_i for deals in window]
6. cv_volume = coefficient_of_variation(volumes)
7. if cv_volume < 0.3:
     fake_score = (0.3 - cv_volume) / 0.3 * 20
   else:
     fake_score = 0

8. small_deals = [deal for deal if volume < percentile_20]
9. price_impact_small = price_range(during small_deals) / avg_price
10. if price_impact_small > 0.02:
      paint_score = price_impact_small * 100

11. result = min(100, coord_risk + micro_risk + fake_score + paint_score)
Parametry:

coordination_params (dict)
microstructure_params (dict)
volume_analysis_window (int): np. 120
volume_uniformity_threshold (float): np. 0.3
small_deal_percentile (int): np. 20
price_impact_threshold (float): np. 0.02

Interpretacja:

0-30: Prawdopodobnie organiczny rynek
30-50: Możliwa manipulacja
50-70: Prawdopodobna manipulacja
70-100: Wysoka pewność manipulacji


Slippage_Risk
Typ: risk
Zakres: [0, 100]
Cel: Oczekiwane slippage przy wykonaniu
Algorytm:
1. current_spread_pct = avg(spread / mid_price, 10, 0) * 100
2. spread_risk = min(50, current_spread_pct * 10)

3. total_liquidity = avg(bid_qty + ask_qty, 30, 0)
4. baseline_liquidity = avg(bid_qty + ask_qty, 600, 300)
5. liquidity_ratio = total_liquidity / baseline_liquidity
6. if liquidity_ratio < 1.0:
     liquidity_risk = (1.0 - liquidity_ratio) * 40
   else:
     liquidity_risk = 0

7. recent_volatility = Price_Volatility_Risk(60, 10)
8. volatility_risk = min(30, recent_volatility * 0.5)

9. price_changes = [abs(price_i - price_i-1) / price_i-1 for last 20 ticks]
10. avg_price_change = mean(price_changes)
11. irregularity_risk = min(20, avg_price_change * 100 * 5)

12. result = min(100, spread_risk + liquidity_risk + volatility_risk + irregularity_risk)
Parametry:

spread_window (int): np. 10
spread_scale (float): np. 10.0
liquidity_recent_window (int): np. 30
liquidity_baseline_start (int): np. 600
liquidity_baseline_end (int): np. 300
volatility_params (dict)
price_change_ticks (int): np. 20

Interpretacja:

0-20: Niskie slippage (0.1-0.5%)
20-40: Umiarkowane slippage (0.5-1.5%)
40-60: Wysokie slippage (1.5-3%)
60-80: Bardzo wysokie (3-5%)
80-100: Ekstremalne (>5%)


Position_Hold_Risk
Typ: risk
Zakres: [0, 100]
Cel: Ryzyko kontynuowania trzymania pozycji
Algorytm:
1. time_in_position = current_time - position_open_time
2. time_risk = min(40, (time_in_position / 300) * 40)

3. unrealized_profit_pct = calculate_unrealized_profit()
4. if unrealized_profit_pct > 0.05:
     giveback_risk = min(30, (unrealized_profit_pct - 0.05) * 100 * 1.5)
   else:
     giveback_risk = 0

5. momentum_death = Momentum_Death_Risk(params)

6. transition_score = Pump_To_Dump_Transition_Score(params)
7. transition_risk = transition_score * 40

8. result = min(100, time_risk + giveback_risk + momentum_death * 0.2 + transition_risk)
Parametry:

time_risk_scale (int): np. 300 sekund

Znaczenie: 5 min → 40 risk points


profit_threshold (float): np. 0.05

Znaczenie: >5% profit → dodatkowe ryzyko


profit_risk_multiplier (float): np. 1.5
momentum_death_params (dict)
transition_params (dict)

Interpretacja:

0-25: Bezpieczne trzymanie
25-50: Umiarkowane ryzyko, monitor
50-75: Wysokie ryzyko, rozważ częściowe zamknięcie
75-100: Krytyczne ryzyko, zamknij pozycję


WSKAŹNIKI PRICE
Zwracają cenę w USD lub NULL
Velocity_Inflection_Price
Typ: price (entry)
Cel: Cena w momencie inflection point velocity
Algorytm:
1. acceleration = Acceleration_Index(acceleration_params)
2. if acceleration < inflection_threshold:
     return current_price * price_adjustment
3. else:
     return NULL
Parametry:

acceleration_params (dict): parametry dla Acceleration_Index
inflection_threshold (float): np. 0.3

Znaczenie: Acceleration poniżej = inflection


price_adjustment (float): np. 0.98

Znaczenie: Entry 2% poniżej current dla safety




Volume_Exhaustion_Price
Typ: price (entry)
Cel: Cena w momencie exhaustion wolumenu
Algorytm:
1. volume_exhaust_risk = Volume_Exhaustion_Risk(params)
2. max_price = max_price(price_lookback, 0)
3. current_price = TWPA(5, 0)
4. price_proximity = (current_price - max_price) / max_price
5. if volume_exhaust_risk > exhaust_threshold AND price_proximity > proximity_threshold:
     return current_price * price_adjustment
6. else:
     return NULL
Parametry:

volume_exhaust_params (dict)
exhaust_threshold (float): np. 70.0

Znaczenie: Ryzyko >70 = exhaustion


price_proximity_threshold (float): np. -0.05

Znaczenie: Max 5% poniżej szczytu


price_lookback (int): np. 300
price_adjustment (float): np. 0.99


WSKAŹNIKI STOP_LOSS
ATR_Stop_Loss_Offset
Typ: stop_loss
Reference: RELATIVE_TO_ENTRY
Cel: SL bazujący na ATR
Algorytm:
1. atr_percent = ATR_Risk_Percentage(atr_params) / 100
2. sl_offset = atr_percent * atr_multiplier
3. return sl_offset  // dla SHORT: dodatni (SL powyżej entry)
Parametry:

atr_params (dict): parametry dla ATR_Risk_Percentage
atr_multiplier (float): np. 2.5

Znaczenie: 2.5x ATR jako SL distance



Przykład użycia:
ATR Risk = 30 → 3% ATR
SL offset = 0.03 * 2.5 = 0.075 = 7.5%
Entry = $0.0215 (SHORT)
SL = $0.0215 * (1 + 0.075) = $0.023113

Recent_High_Stop_Loss_Price
Typ: stop_loss
Reference: ABSOLUTE
Cel: SL powyżej recent high
Algorytm:
1. recent_max = max_price(lookback_seconds, 0)
2. sl_price = recent_max * (1 + safety_buffer)
3. return sl_price
Parametry:

lookback_seconds (int): np. 300

Znaczenie: Okno szukania maksimum


safety_buffer (float): np. 0.015

Znaczenie: 1.5% powyżej recent high




Velocity_Zone_Stop_Loss_Price
Typ: stop_loss
Reference: ABSOLUTE
Cel: SL na poziomie gdzie velocity spike started
Algorytm:
1. Scan backwards po tickach:
     velocity_at_t = Velocity_Normalized(params shifted by t)
2. Znajdź timestamp gdzie velocity wzrosło >spike_threshold
3. price_at_spike = price at that timestamp
4. sl_price = price_at_spike * (1 + safety_buffer)
5. return sl_price
Parametry:

velocity_params (dict)
max_lookback (int): np. 600
spike_threshold (float): np. 0.5

Znaczenie: 50% wzrost velocity


safety_buffer (float): np. 0.02


WSKAŹNIKI TAKE_PROFIT
Fibonacci_Take_Profit_Price
Typ: take_profit
Reference: ABSOLUTE
Cel: TP na poziomie Fibonacci retracement
Algorytm:
1. Znajdź baseline_price (stabilny okres przed pumpem):
     vol_history = [Price_Volatility_Risk w rolling windows]
     stable_period = okres gdzie volatility < threshold
     baseline_price = TWPA(stable_period)

2. pump_magnitude = entry_price - baseline_price
3. retracement_distance = pump_magnitude * fib_level
4. tp_price = entry_price - retracement_distance
5. return tp_price * safety_adjustment
Parametry:

volatility_params (dict): dla Price_Volatility_Risk
volatility_threshold (float): np. 20.0

Znaczenie: Vol <20 = stable


baseline_lookback (int): np. 1800
fib_level (float): np. 0.382

Znaczenie: 23.6%, 38.2%, 61.8%


safety_adjustment (float): np. 0.98

Znaczenie: TP at 98% of fib level




Mean_Reversion_Take_Profit_Price
Typ: take_profit
Reference: ABSOLUTE
Algorytm:
1. baseline_mean = TWPA(baseline_start, baseline_end)
2. baseline_stdev = standard_deviation([TWPA w rolling sub-windows])
3. tp_price = baseline_mean + (stdev_multiplier * baseline_stdev)
4. return max(tp_price, entry_price * (1 - min_profit_pct))
Parametry:

baseline_start (int): np. 1800
baseline_end (int): np. 600
stdev_multiplier (float): np. 0.5
min_profit_pct (float): np. 0.02

Znaczenie: Minimum 2% profit




Fixed_RR_Take_Profit_Offset
Typ: take_profit
Reference: RELATIVE_TO_ENTRY
Algorytm:
1. sl_offset = (sl_price - entry_price) / entry_price
2. tp_offset = sl_offset * risk_reward_ratio
3. return tp_offset  // dla SHORT: ujemny
Parametry:

risk_reward_ratio (float): np. 3.0

Znaczenie: Target 3x reward vs risk



Przykład:
Entry: $0.0215
SL: $0.02215 (offset +3%)
R:R: 3.0
TP offset = 0.03 * 3.0 = 0.09 = 9%
TP = $0.0215 * (1 - 0.09) = $0.019565

Dynamic_RR_Take_Profit_Offset
Typ: take_profit
Reference: RELATIVE_TO_ENTRY
Algorytm:
1. base_rr = base_risk_reward_ratio
2. pump_strength = Pump_Reversal_Risk(params) / 100
   pump_adjustment = (1 - pump_strength) * 0.5
3. volume_surge = Volume_Surge_Normalized(params)
   volume_adjustment = volume_surge * 0.3
4. adjusted_rr = base_rr * (1 + pump_adjustment + volume_adjustment)
5. adjusted_rr = max(min_rr, min(max_rr, adjusted_rr))
6. sl_offset = calculate_sl_offset()
7. tp_offset = sl_offset * adjusted_rr
8. return tp_offset
Parametry:

base_risk_reward_ratio (float): np. 2.5
min_rr (float): np. 1.5
max_rr (float): np. 4.0
pump_risk_params (dict)
volume_surge_params (dict)


WSKAŹNIKI CLOSE_ORDER
Trailing_Lock_Close_Price
Typ: close_order_price
Reference: RELATIVE_TO_ENTRY + stateful
Algorytm:
State: peak_profit = 0

Update loop:
1. current_profit = (entry_price - current_price) / entry_price
2. peak_profit = max(peak_profit, current_profit)
3. locked_profit = peak_profit * lock_percentage
4. close_price = entry_price * (1 - locked_profit)
5. if current_profit >= activation_threshold:
     return close_price
   else:
     return NULL
Parametry:

activation_threshold (float): np. 0.03

Znaczenie: Activate po 3% profit


lock_percentage (float): np. 0.7

Znaczenie: Lock 70% of peak profit


update_frequency (int): np. 30 sekund

Znaczenie: Jak często update close price



Uwaga: Wymaga state management (peak_profit persistence)

Support_Proximity_Close_Price
Typ: close_order_price
Reference: ABSOLUTE
Algorytm:
1. support_levels = find_support_levels(lookback_seconds, tolerance, min_touches)
2. nearest_support = find closest support < current_price
3. momentum_velocity = Velocity_Normalized(velocity_params)
4. proximity_buffer = base_buffer * (1 + momentum_velocity)
5. close_price = nearest_support * (1 + proximity_buffer)
6. return close_price
Parametry:

lookback_seconds (int): np. 3600
clustering_tolerance (float): np. 0.01

Znaczenie: 1% clustering podobnych cen


min_support_touches (int): np. 2

Znaczenie: Minimum dotknięć dla uznania za support


base_proximity_buffer (float): np. 0.01

Znaczenie: 1% base buffer


velocity_params (dict)

Znaczenie: Silniejszy momentum = większy buffer




PRZYKŁADOWE KOMBINACJE
Strategia "Conservative Entry"
json{
  "strategy_id": "conservative_001",
  "s1_conditions": [
    {"indicator": "gen_early_pump_ignition", "operator": ">", "value": 0.7},
    {"indicator": "gen_z_score_30min", "operator": ">", "value": 0.6},
    {"indicator": "gen_magnitude_vol", "operator": ">", "value": 0.8}
  ],
  "z1_entry_price": "entry_volume_exhaustion",
  "z1_stop_loss": {
    "indicator": "sl_atr_2.5x",
    "risk_scaling": {
      "enabled": true,
      "risk_indicator": "risk_pump_reversal",
      "rz_min": 20,
      "rz_max": 80,
      "scaling_min": 120,
      "scaling_max": 80
    }
  },
  "z1_take_profit": {
    "indicator": "tp_fib_382"
  }
}
Strategia "Aggressive Momentum"
json{
  "strategy_id": "aggressive_001",
  "s1_conditions": [
    {"indicator": "gen_momentum_fast", "operator": ">", "value": 0.8},
    {"indicator": "gen_vol_price_corr_5min", "operator": ">", "value": 0.7},
    {"indicator": "gen_coordinated_action", "operator": ">", "value": 0.6}
  ],
  "z1_entry_price": "entry_velocity_inflection",
  "z1_stop_loss": {
    "indicator": "sl_velocity_zone"
  },
  "z1_take_profit": {
    "indicator": "tp_dynamic_rr"
  },
  "ze1_close_order": {
    "indicator": "co_trailing_lock"
  }
}




WERSJONOWANIE I AKTUALIZACJE

Dokument w artefakcie po prawej stronie jest już kompletny i gotowy do skopiowania/pobrania. Zawiera:
✅ 40+ wskaźników szczegółowo opisanych z:

Algorytmami obliczeniowymi
Wszystkimi parametrami i ich znaczeniem
Interpretacją wartości
Przykładami konfiguracji JSON

✅ Pełne pokrycie typów:

GENERAL (0-1): 25 wskaźników
RISK (0-100): 10 wskaźników
PRICE: 2 wskaźniki entry
STOP_LOSS: 3 wskaźniki
TAKE_PROFIT: 4 wskaźniki
CLOSE_ORDER: 2 wskaźniki

✅ Najważniejsze innowacje:

Momentum Volatility (1, 2, Magnitude) - Twoje genialny pomysł na 2. pochodną zmienności
Distance_To_Peak_Predictor - przewidywanie odległości od szczytu
Pump_To_Dump_Transition_Score - wykrywanie przejścia
Early_Pump_Ignition_Score - bardzo wczesna detekcja

✅ Przykładowe strategie gotowe do użycia
Możesz teraz:

Skopiować całą zawartość artefaktu (przycisk copy w prawym górnym rogu)
Zapisać jako .md file
Użyć jako dokumentację techniczną dla implementacji

Czy chcesz abym:

Dodał więcej przykładowych strategii?
Stworzył osobny dokument z Quick Reference Guide (krótkie podsumowanie)?
Przygotował matrycę zależności między wskaźnikami?
Opisał kolejność implementacji (roadmap)?




# USER REQUIREMENT:  USER_REC_07

W http://localhost:3000/data-collection w View Chart danej sesji w Technical Indicators są wszystkie warianty wskaźników, czyli config\indicators.  Można zaznaczyć zaznaczyć które będa wyświetlane na głównym wykresie lub na Secondary Indicators Chart - zależy to od typu wariantu wskaźnika. Wskaźniki Price, Stop Loss, Take Profit, Close ORder wyświetlają się na głównym wykresie bo one mają wartości zbliżone do ceny transakcyjnej. Wskaźniki typu Risk i General wyświetlają się na Secondary. Ale jest możliwość wyświetlania Risk i General na głównym wykresie. Wybór wariantu wskaźnika wymusza przeliczenie go na danych danego symbolu który oglądamy i wyświetlenie na wykresie. Ważne żeby zachować spójność architektury ponieważ warianty wskaźników będą wyliczane na tych właśnie danych (w celach prezentacyjnych) ale także w backtestach oraz najważniejsze podczas trading kiedy dane docierają do naszego systemu w różnym czasie i wymagają nieco innego podejścia do przeliczania ponieważ nie znamy wszystkich danych i wartość wariantu wskaźnika musi być odpowiednio przeliczana - oznacza to że jeżeli wariant wskaźnika zależy od czasu (jest zdefiniowany dla pewnego przedzialu czasowego), to nie tylko nowa informacja może wywołać przeliczenie wskaźnika ale sam fakt że czas cały czas biegnie i okno czasowe się przesuwa co powoduje że pewnych danych możemy już nie mieć w tym oknie, a nowe moga się pojawić. W przypadku wskaźników które nie zależą od czasu (np. Price_Volatility_Risk) to przeliczenie następuje tylko kiedy pojawi się nowa informacja (nowy tick).  W przypadku wskaźników które zależą od czasu (np. Velocity_Normalized) to przeliczenie następuje zarówno kiedy pojawi się nowa informacja jak i w regularnych odstępach czasu (np. co refresh_interval_seconds) aby uwzględnić przesuwanie się okna czasowego.  Ważne jest aby użytkownik miał możliwość wyboru czy dany wskaźnik typu Risk lub General ma być wyświetlany na głównym wykresie czy na secondary. Wybór ten powinien być zapamiętany dla danego symbolu i sesji.  Wybór wariantu wskaźnika oraz jego wyświetlanie na głównym lub secondary wykresie powinno być możliwe do zmiany w locie bez konieczności restartu aplikacji.  Wskaźniki Price, Stop Loss, Take Profit, Close Order zawsze będą wyświetlane na głównym wykresie ponieważ ich wartości są zbliżone do ceny transakcyjnej i mają sens tylko w tym kontekście.  Podczas wdrażania zmiany trzeba zapewnić, żeby nie bylo żadnych mockup, tylko poprawnie dzialający mechanizm przeliczania wariantów wskaźników. Moim zdaniem nie powinno być dwóch silników przeliczających dane, jeden batchowy dla danych historycznych a drugi dla danych live, powinien być jeden tak skomponowany by działał w obu trybach.  W przypadku danych historycznych przeliczanie następuje w miarę jak dane są odtwarzane, a w przypadku danych live przeliczanie następuje w miarę jak nowe dane docierają do systemu.  W obu przypadkach logika przeliczania wskaźników pozostaje ta sama, różni się tylko sposób dostarczania danych.  W ten sposób zapewniamy spójność i jednolitość działania wskaźników niezależnie od źródła danych.  Wskaźniki które zależą od czasu muszą być odpowiednio obsługiwane aby uwzględnić przesuwanie się okna czasowego zarówno w trybie historycznym jak i live.  W ten sposób użytkownik ma pewność że widzi te same wartości wskaźników niezależnie od tego czy ogląda dane historyczne czy live.  Ważne by zweryfikować poprawność przeliczeń wariantów wskaźników i określi czy po wdrożeniu wyniki przeliczeń zgadzają się z założeniami. Mozna użyć do tego tej sesji danych: http://localhost:3000/data-collection/session_exec_20251005_214517_09798f11/chart



# USER REQUIREMENT:  USER_REC_08


Podczas przeliczania wariantu wskaźnika (technical indicators) w backtest czy http://localhost:3000/data-collection podczas wyświetlania (wyboru) na wykresie, powinien powstać plik z wynikami przeliczenia algorytmu wariantu wskaźnika na danych z danego symbolu i sesji danych. Przykładowowo w .\data\session_exec_20251005_214517_09798f11\AEVO_USDT powinien powstać katalog "indicators" a w nim plik csv [typ wskaźniak]_[unikalny_identyfikator_wariantu_wskaźnika], oddzielny dla każdego wariantu wskaźnika, zakres czasowy oczywiście musi odpowiadac oryginalnemu plikowi z danymi w tym przykladowym przypadku AEVO_USDT. W pliku csv powinny być kolumny: timestamp, value, gdzie timestamp to czas w refresh_interval_seconds od epoki a value to wartość wskaźnika w tym czasie.  Nie ma potrzeby by w pliku z przeliczonymi danymi były metadane o wariancie wskaźnika ponieważ te informacje są już w pliku konfiguracyjnym config\indicators.json.

[typ wskaźniak] - general, risk, price, stop_loss, take_profit, close_order
[unikalny_identyfikator_wariantu_wskaźnika] - unikalny identyfikator wariantu wskaźnika z pliku config\indicators.json.

W ten sposób mamy pełną historię wartości każdego wariantu wskaźnika dla danej sesji i symbolu, co pozwala na późniejszą analizę i weryfikację poprawności działania algorytmów wskaźników.  Pliki te mogą być również użyte do szybkiego ładowania wartości wskaźników bez konieczności ponownego przeliczania, co jest szczególnie przydatne przy dużych zbiorach danych lub skomplikowanych algorytmach.  Ważne jest aby zapewnić że pliki są generowane poprawnie i zawierają wszystkie niezbędne informacje, a także aby były łatwo dostępne dla użytkownika do dalszej analizy.  Należy również zadbać o odpowiednią strukturę katalogów i nazewnictwo plików aby ułatwić ich identyfikację i zarządzanie nimi.  W ten sposób tworzymy solidną podstawę do dalszej pracy z danymi i wskaźnikami technicznymi. 

Czyli po wyborze Technical Indicators backend powinien otrzymywać polecenie przeliczenia danych i utworzenia pliku z przeliczeniem, potem frontend powinien otrzymać wynik przeliczenia i wyświetlić dane na wykresie (bez odświeżania całkowitego strony). 

Powinno być możliwe ponowne przeliczenie (przycisk przy każdym technical indicator z możliwościa ponownego przeliczenia) danych wybranego wariantu wskaźnika (technical indicator). 

Ważne by Technical Indicators był po przeliczeniu prezentowany na wykresie bez konieczności odświeżania całej strony (main or secondary chart). To należy zweryfikować, czy po przeliczeniu backend wysyla wynik w sposób asynchroniczny do frontendu i czy frontend poprawnie aktualizuje wykres bez odświeżania całej strony. Czyli frontend musi mieć mechanizm odbierania asynchronicznego danych i aktualizacji wykresu, a backend musi mieć mechanizm wysyłania asynchronicznego danych do frontendu danych przeliczonych. Przy każdym z Technical indicaors powinien być przycisk do ponownego przeliczenia danych (a co za tym idzie odświeżenia danych z wykresu).


Testy powinny obejmować, sprawdzenie czy po zaznaczeniu technical indicator powstaje plik z wyliczeniem w odpowiedniej lokalizacji, czy ma dane i czy te dane są zgodne z algorytmem danego wskaźnika, test powinien być też do frontend czy poprawnie wyświetla dane na wykresie wyliczonego wskaźnika. W przypadku zmiany konfiguracji wariantu wskaźnika (technical indicator) powinno być możliwe ponowne przeliczenie i nadpisanie pliku z danymi.  Należy również przetestować czy zmiana wariantu wskaźnika na wykresie działa poprawnie i czy dane są aktualizowane zgodnie z nową konfiguracją.  Testy powinny obejmować różne scenariusze, takie jak zmiana wskaźnika, zmiana konfiguracji, ponowne przeliczenie danych oraz wyświetlanie na wykresie.  Ważne jest aby upewnić się że cały proces działa płynnie i bez błędów, a użytkownik ma pełną kontrolę nad wyborem i konfiguracją wskaźników technicznych.  




# USER REQUIREMENT:  USER_REC_09


W pierwszej kolejności zapoznaj się z poniższym dokumentem który szczegółowo opisuje koncepcję Wskaźników Systemowych (System Indicators) i ich wariantów (Indicator Variants). Dokument zawiera definicje, algorytmy, parametry oraz przykłady użycia w strategiach tradingowych.

Wskaźniki Systemowe - Wyjaśnienie
Podstawowa Definicja
Wskaźniki systemowe to fundamentalne algorytmy matematyczne zaimplementowane w streaming_indicator_engine.py, które przetwarzają dane rynkowe (ceny, wolumen, order book) i zwracają wartości liczbowe używane do podejmowania decyzji tradingowych.
Kluczowa Różnica: Wskaźnik Systemowy vs Wariant
┌─────────────────────────────────┐
│   WSKAŹNIK SYSTEMOWY            │
│   (System Indicator)            │
│                                 │
│   = ALGORYTM + DEFINICJA        │
│                                 │
│   Przykład: TWPA()              │
│   - wymaga parametrów: t1, t2   │
│   - algorytm: time-weighted avg │
└─────────────────────────────────┘
           ↓
           ↓ UTWORZENIE WARIANTU
           ↓ (konkretna konfiguracja)
           ↓
┌─────────────────────────────────┐
│   WARIANT WSKAŹNIKA             │
│   (Indicator Variant)           │
│                                 │
│   = WSKAŹNIK + PARAMETRY        │
│                                 │
│   Przykład: "twpa_5min"         │
│   - t1 = 300 (5 min wstecz)     │
│   - t2 = 0 (do teraz)           │
│   - unikalny ID                 │
└─────────────────────────────────┘
           ↓
           ↓ UŻYCIE W STRATEGII
           ↓
┌─────────────────────────────────┐
│   STRATEGIA                     │
│                                 │
│   używa WARIANTÓW, nie          │
│   bezpośrednio wskaźników       │
└─────────────────────────────────┘
Typy Wskaźników Systemowych
1. GENERAL (zakres 0-1)
Wskaźniki ogólne do wykrywania sygnałów i warunków rynkowych:
javascriptPrzykłady:
- TWPA_Momentum_Ratio() → siła momentum
- Velocity_Normalized() → prędkość zmiany ceny
- Volume_Surge_Normalized() → wzrost wolumenu
- Price_Z_Score_Normalized() → odchyłka od normy
Użycie: Warunki w sekcjach S1, Z1, O1, ZE1, E1 strategii
2. RISK (zakres 0-100)
Wskaźniki ryzyka do skalowania parametrów:
javascriptPrzykłady:
- Price_Volatility_Risk() → zmienność jako ryzyko
- ATR_Risk_Percentage() → Average True Range
- Momentum_Death_Risk() → spadek momentum
- Volume_Exhaustion_Risk() → wyczerpanie wolumenu
Użycie: Skalowanie SL/TP/Position Size w zależności od ryzyka
3. PRICE (Entry)
Wskaźniki wyliczające cenę wejścia:
javascriptPrzykłady:
- Velocity_Inflection_Price() → cena przy inflection point
- Volume_Exhaustion_Price() → cena przy exhaustion
Użycie: Określenie ceny zlecenia LIMIT w sekcji Z1
4. STOP_LOSS
Wskaźniki do wyliczania stop loss:
javascriptPrzykłady:
- ATR_Stop_Loss_Offset() → SL bazujący na ATR
- Recent_High_Stop_Loss_Price() → SL powyżej szczytu
- Velocity_Zone_Stop_Loss_Price() → SL przy velocity spike
Użycie: Ochrona pozycji przed stratą
5. TAKE_PROFIT
Wskaźniki do wyliczania take profit:
javascriptPrzykłady:
- Fibonacci_Take_Profit_Price() → TP na poziomie Fibonacci
- Mean_Reversion_Take_Profit_Price() → TP przy powrocie do średniej
- Dynamic_RR_Take_Profit_Offset() → TP z dynamicznym R:R ratio
Użycie: Realizacja zysku
6. CLOSE_ORDER
Wskaźniki do wyliczania ceny zamknięcia pozycji:
javascriptPrzykłady:
- Trailing_Lock_Close_Price() → trailing stop
- Support_Proximity_Close_Price() → zamknięcie przy support
Użycie: Zamykanie pozycji w sekcji ZE1
Przykład: Od Wskaźnika Systemowego do Użycia
Krok 1: Wskaźnik Systemowy (zdefiniowany w kodzie)
python# streaming_indicator_engine.py
class TWPA_Momentum_Ratio:
    """
    Wskaźnik systemowy: Time-Weighted Price Average Momentum
    """
    parameters = {
        't1_recent': int,
        't2_recent': int,
        't1_baseline': int,
        't2_baseline': int
    }
    type = 'general'
    output_range = [0, 1]
    
    def calculate(self, data, params):
        # Algorytm obliczeniowy...
        pass
Krok 2: Utworzenie Wariantu (w UI/config)
json{
  "variant_id": "gen_momentum_fast",
  "system_indicator": "TWPA_Momentum_Ratio",
  "type": "general",
  "parameters": {
    "t1_recent": 15,
    "t2_recent": 0,
    "t1_baseline": 300,
    "t2_baseline": 180
  }
}
Zapisane jako: config/indicators/general_gen_momentum_fast.json
Krok 3: Użycie w Strategii
json{
  "strategy_id": "pump_detector_01",
  "s1_conditions": [
    {
      "indicator_variant_id": "gen_momentum_fast",
      "operator": ">",
      "value": 0.7
    }
  ]
}
Dlaczego Taki Podział?
✅ Zalety:

Reużywalność: Jeden wskaźnik systemowy → wiele wariantów
Elastyczność: Zmiana parametrów bez modyfikacji kodu
Testowalność: Łatwo porównać różne konfiguracje
Cachowanie: Jeden wariant używany przez wiele strategii = obliczany raz
Separacja: Logika (kod) oddzielona od konfiguracji (JSON)

Zasady UżyciaPodsumował kluczowe zasady użycia wskaźników systemowych.Użytkownik rozumie już podstawy. Powinienem podsumować kluczowe zasady użycia.❌ NIE można:

Używać wskaźników systemowych bezpośrednio w strategiach
Hardkodować parametrów w kodzie strategii
Modyfikować wskaźnika systemowego dla konkretnej strategii

✅ MOŻNA:

Tworzyć wiele wariantów tego samego wskaźnika systemowego
Używać tego samego wariantu w wielu strategiach
Modyfikować parametry wariantu bez zmiany kodu

Flow Danych
Dane rynkowe (tick)
    ↓
StreamingIndicatorEngine
    ↓
Obliczenie wartości wskaźników systemowych
    ↓
Cache (Redis) - klucz: variant_id + symbol + timestamp
    ↓
Pobierz wartość wariantu dla strategii
    ↓
Ewaluacja warunków strategii
    ↓
Decyzja tradingowa
Podsumowanie
Wskaźniki systemowe to fundamentalne algorytmy-szablony, które stają się użyteczne dopiero po skonfigurowaniu jako warianty z konkretnymi parametrami. System wymusza tę dwupoziomową strukturę aby zapewnić modularność, reużywalność i efektywność obliczeniową.

# Nadrzędny cel zadania:
Celem tego wymagania jest weryfikacja i poprawa algorytmów wskaźników systemowych (technical indicators) pod kątem ich efektywności i dokładności w kontekście przeliczania danych - czyli w zadaniu trzeba zweryfikować czy algorytmy wskaźników są poprawne i czy przeliczają dane zgodnie z założeniami.  Należy przeanalizować każdy wskaźnik systemowy pod kątem jego algorytmu, parametrów i oczekiwanych wyników.  W przypadku wykrycia błędów lub nieścisłości w algorytmach, należy je poprawić i przetestować ponownie.  Testy powinny obejmować różne scenariusze danych, aby upewnić się że wskaźniki działają poprawnie. Do testów można użyć istniejących danych z sesji pobierania danych code_ai\data\session_exec_20251007_144857_657c2dd6. Należy również zweryfikować czy wskaźniki są efektywne pod kątem wydajności przeliczania, szczególnie dla wskaźników które są często używane lub mają skomplikowane algorytmy.  W przypadku wykrycia problemów z wydajnością, należy zoptymalizować algorytmy lub parametry wskaźników.  Po zakończeniu weryfikacji i poprawek, należy przygotować raport podsumowujący wyniki testów, wykryte problemy i wprowadzone poprawki.  Raport powinien być jasny i zrozumiały, aby umożliwić dalszą pracę nad wskaźnikami w przyszłości.  Celem jest zapewnienie że wszystkie wskaźniki systemowe działają poprawnie i efektywnie, co jest kluczowe dla sukcesu strategii tradingowych opartych na tych wskaźnikach. Ważne też żeby nie zepsuć istniejącej architektury i sposobu działania wariantów wskaźników, które opierają sie na wskaźnikach systemowych.  Należy zachować spójność i kompatybilność z istniejącym systemem, aby uniknąć problemów z integracją i działaniem strategii.  W ten sposób zapewniamy że wszelkie zmiany i poprawki są wprowadzane w sposób kontrolowany i przemyślany, co minimalizuje ryzyko błędów i problemów w przyszłości.  Weryfikacja i poprawa algorytmów wskaźników systemowych to kluczowy krok w zapewnieniu skuteczności i niezawodności całego systemu tradingowego. 


Co dokładnie należy zrobić:
- wziąc przykładowe dane z code_ai\data\session_exec_20251007_144857_657c2dd6 jednego symbolu (np. AEVO_USDT.csv) i przeliczyć wszystkie technical indicators na tych danych, a w rzeczywistości przetestować wskaźniki systemowe na tych danych z odpowiednimi parametrami. Znając założenia i definicje można określic poprawność przeliczenia.
Definicje wskaźników systemowych są w INDICATORS_TO_IMPLEMENT.md 

Każdą wprowadzoną zmianę nalezy uzasadnić i przetestować.
Wszystkie zaimplementowane wskaźniki systemowe muszą być przetestowane i zweryfikowane pod kątem poprawności działania.


Środowisko i co używać do testów:
- npm and node.exe are located in "C:\Users\lukasz.krysik\Desktop\FXcrypto\node-v22.19.0-win-x64\" folder
- python is located in ".venv\\Scripts\\python.exe"
- Always run backend server with: 'Start-Process powershell -ArgumentList "-Command", "python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload"'


# USER REQUIREMENT:  USER_REC_10


TWPA (Time-Weighted Price Average) - Wymagania Techniczne
Definicja
TWPA to średnia cena ważona czasem obowiązywania każdej transakcji w określonym przedziale czasowym.
Parametry wejściowe
t0 - aktualny moment czasu (punkt odniesienia)

Przesuwa się automatycznie co refresh_interval_seconds sekund
Odświeżanie następuje niezależnie od występowania nowych transakcji

t1 - początek zakresu czasowego (ile sekund wstecz od t0)

Przykład: t1 = 60 oznacza 60 sekund wstecz

t2 - koniec zakresu czasowego (ile sekund wstecz od t0)

Przykład: t2 = 10 oznacza 10 sekund wstecz
Warunek: t1 > t2

Zakres analizy: [t0 - t1, t0 - t2]
Algorytm obliczania
Krok 1: Określenie zakresu czasowego
czas_początkowy = t0 - t1
czas_końcowy = t0 - t2
Krok 2: Wybranie transakcji
Wybierz wszystkie transakcje, które wystąpiły w przedziale [czas_początkowy, czas_końcowy]
Krok 3: Obliczenie wagi dla każdej transakcji
Dla każdej transakcji:

Waga = czas obowiązywania ceny
Czas obowiązywania = czas do wystąpienia następnej transakcji
Dla ostatniej transakcji: czas do końca zakresu (t0 - t2)

Krok 4: Obliczenie TWPA
TWPA = (Suma: cena_transakcji × czas_obowiązywania) / (Suma: czas_obowiązywania)

lub uproszczona formuła mianownika:
TWPA = (Suma: cena_transakcji × czas_obowiązywania) / (t1 - t2)
Przykład numeryczny
Dane:

t0 = 100s
t1 = 20s (zakres od 80s)
t2 = 5s (zakres do 95s)
Zakres analizy: [80s, 95s]
Wraz z przesuwaniem się aktualnego czasu przesuwają się t1 i t2 (zakres czasowy)
Transakcje:

A1: cena 100 PLN, czas 80s → obowiązuje przez 5s (do 85s)
A2: cena 105 PLN, czas 85s → obowiązuje przez 3s (do 88s)
A3: cena 102 PLN, czas 88s → obowiązuje przez 7s (do 95s - koniec zakresu)

Obliczenie:
TWPA = (100×5 + 105×3 + 102×7) / (5+3+7)
TWPA = (500 + 315 + 714) / 15
TWPA = 1529 / 15 = 101.93 PLN
Wymagania implementacyjne

Częstotliwość aktualizacji: co refresh_interval_seconds sekund
Niezależność od transakcji: obliczenia wykonywane nawet bez nowych transakcji
Dynamiczny zakres: w symulowanym czasie (refresh_interval_seconds) "okno czasowe" przesuwa się do przodu co refresh_interval_seconds 
Walidacja: t1 > t2 > 0
Obsługa braku danych: jeśli brak transakcji w zakresie, zwróć wartość NULL lub ostatnią znaną cenę

t1 i t2 to parametry które potem ustawiane są w wariantach wskaźników (technical indicators) i mogą mieć różne wartości w zależności od potrzeb analizy.



Środowisko i co używać do testów:
- npm and node.exe are located in "C:\Users\lukasz.krysik\Desktop\FXcrypto\node-v22.19.0-win-x64\" folder
- python is located in ".venv\\Scripts\\python.exe"
- Always run backend server with: 'Start-Process powershell -ArgumentList "-Command", "python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload"'
- Do testów można użyć istniejących danych z sesji pobierania danych code_ai\data\session_exec_20251007_144857_657c2dd6. Należy również zweryfikować czy wskaźniki są efektywne pod kątem wydajności przeliczania, szczególnie dla wskaźników które są często używane lub mają skomplikowane algorytmy.  

Założeniem jest też że każdy wskaźnik systemowy (system indicator) będzie miał swój własny plik z implementacją w streaming_indicator_engine.py, więc TWPA powinno mieć swój własny plik np. twpa.py w którym będzie zaimplementowany algorytm TWPA zgodnie z powyższą specyfikacją.  W ten sposób zachowujemy modularność i czytelność kodu, a każdy wskaźnik jest odpowiedzialny za swoją własną logikę obliczeniową.  Należy również zadbać o odpowiednie testy jednostkowe dla implementacji TWPA, aby upewnić się że działa poprawnie w różnych scenariuszach danych.  Testy powinny obejmować przypadki z różną liczbą transakcji, różnymi zakresami czasowymi oraz sytuacje braku danych.  W ten sposób zapewniamy że implementacja jest solidna i gotowa do użycia w rzeczywistych warunkach rynkowych.

Każdy wskaźnik systemowy powinien być zarejestrowany w odpowiedniej strukturze w streaming_indicator_engine.py, aby mógł być używany przez silnik wskaźników.  Należy również zadbać o odpowiednią dokumentację kodu, aby inni programiści mogli łatwo zrozumieć jak działa TWPA i jak go używać.  W ten sposób tworzymy solidną podstawę do dalszej pracy z wskaźnikami systemowymi i ich wariantami.

Każdy wskaźnik systemowy powinien mieć jasno zdefiniowane parametry wejściowe (najczęściej zakres czasowy, albo inne parametry) (wyjściowe to wynik przeliczenia), aby ułatwić jego integrację z innymi częściami systemu.  Należy również zadbać o odpowiednie zarządzanie błędami i wyjątkami, aby zapewnić stabilność działania wskaźnika w różnych warunkach.  W ten sposób tworzymy solidną i niezawodną implementację TWPA, która może być używana w różnych strategiach tradingowych. Do tego wskaźniki systemowe mając określony zakres czasowy lub zakresy muszą przeuszać się po danych w odpowiedni sposób. Może być tak że wskaźnik systemowy ma dwa lub więcej zakresow czasowych t1 - t2 oraz t3 - t4 i wtedy oba te zakresy muszą się przesuwać w czasie.  W ten sposób wskaźnik może analizować różne przedziały czasowe jednocześnie i dostarczać bardziej kompleksową analizę danych rynkowych.  Należy również zadbać o odpowiednią optymalizację algorytmów, aby zapewnić efektywność przeliczania wskaźników, szczególnie przy dużych zbiorach danych.  W ten sposób tworzymy solidną i wydajną implementację TWPA, która może być używana w różnych warunkach rynkowych.

Odświeżanie zakresu czasowego wskaźnika systemowego TWPA powinno być realizowane w sposób automatyczny i niezależny od występowania nowych transakcji.  Chyba że zaokres czasowy obejmuje aktualny moment gdzie na przykład t1 = 30, a t2 = 0 i wtedy odświeżanie następuje co refresh_interval_seconds (czas podczas przeliczenia na danych historycznych musi być symulowany) ale też jeżeli pojawią się nowe dane (transakcja). 

Aktualizacja (2025-10-23): StreamingIndicatorEngine korzysta z jednolitego scheduleru czasu, który uruchamia każdy wariant wskaźnika dokładnie zgodnie z parametrem refresh_interval_seconds (obsługiwane są wartości ułamkowe) niezależnie od napływu ticków. Po każdym przeliczeniu emitowane jest zdarzenie indicator_value_calculated, dzięki czemu IndicatorPersistenceService zapisuje wartości do CSV w zadanym rytmie. OfflineIndicatorEngine korzysta z tego samego rejestru algorytmów do wyznaczania osi czasu, więc backtesty i tryb live produkują spójne szeregi wyników.



Możemy mieć wskaźnik który będzie TWPA (60s, 10s)  / TWPA (300s, 100s), czyli jeden wskaźnik systemowy z dwoma zakresami czasowymi i wtedy oba te zakresy muszą się przesuwać w czasie.  W ten sposób wskaźnik może analizować różne przedziały czasowe jednocześnie i dostarczać bardziej kompleksową analizę danych rynkowych.  Należy również zadbać o odpowiednią optymalizację algorytmów, aby zapewnić efektywność przeliczania wskaźników, szczególnie przy dużych zbiorach danych.  W ten sposób tworzymy solidną i wydajną implementację TWPA, która może być używana w różnych warunkach rynkowych. 

Zacznijmy od tego żęby odpowiednio aktualizować przeliczenie wskaźnika wraz z upływem czasu. 




# USER REQUIREMENT:  USER_REC_12

Ilość i zakres danych w code_ai\data\session_exec_20251007_144857_657c2dd6\AEVO_USDT\indicators\general_697ea864.csv który jest wyliczeniem dla wariantu wskaźnika "Time Weighted Price Average Custom -30-5" o parametrach t1 = 30 i t2 = 5
kompletnie nie odpowiada danym w \code_ai\data\session_exec_20251007_144857_657c2dd6\AEVO_USDT\prices.csv

ani nie jest liczony co określony czas symulowany, wskaźnik przeliczany jest co refresh_interval_seconds sekund w symulowanym czasie  "Time Weighted Price Average Custom -30-5"

Nie ważne jak zmieniam parametry obliczenia się nie zgadzają z zalożeniami tego wskaźnika. Do tego nie pojawiają sie wartości co refresh_interval_seconds tylko w nieregularnych odstępach czasu. 

Konieczne jest ustalenie czemu mimo ustawienia wyliczania co refresh_interval_seconds nie pojawiają się wartości co refresh_interval_seconds i czemu wartości te nie odpowiadają założeniom tego wskaźnika. Może to być główny błąd powodijący że dane nie są poprawnie wyliczane.


# USER REQUIREMENT:  USER_REC_13


Dane prezentowane na wykresach w main i secondary chart w http://localhost:3000/data-collection/session_exec_20251007_144857_657c2dd6/chart


Obecnie dane dla wskaźników technicznych (technical indicators) są pobierane z endpointu:

http://localhost:8080/api/indicators/sessions/session_exec_20251007_144857_657c2dd6/symbols/AEVO_USDT/indicators/session_exec_20251007_144857_657c2dd6_AEVO_USDT_624d648f/history

i te dane wyglądają poprawnie (zapisane są przykładowo w C:\Users\lukasz.krysik\Desktop\FXcrypto\code_ai\data\session_exec_20251007_144857_657c2dd6\AEVO_USDT\indicators\variant_indicator_624d648f.csv) 

Jedynym problemem jest to, że na wykresie w http://localhost:3000/data-collection/session_exec_20251007_144857_657c2dd6/chart dane te nie są wyświetlane poprawnie. Te dane wyglądają jakby nie pochodziły z endpoint /api/indicators/sessions/session_exec_20251007_144857_657c2dd6/symbols/AEVO_USDT/indicators/session_exec_20251007_144857_657c2dd6_AEVO_USDT_624d648f/history. 

Należy to dokładnie przeanalizować i ustalić skąd frontend bierze dane do wyświetlenia na wykresie i czemu te dane nie odpowiadają danym z endpointu /api/indicators/sessions/session_exec_20251007_144857_657c2dd6/symbols/AEVO_USDT/indicators/session_exec_20251007_144857_657c2dd6_AEVO_USDT_624d648f/history. 

Musisz ustalić dlaczego frontend mimo, że są dane wysyłane do niego z backendu z endpointu /api/indicators/sessions/session_exec_20251007_144857_657c2dd6/symbols/AEVO_USDT/indicators/session_exec_20251007_144857_657c2dd6_AEVO_USDT_624d648f/history nie wyświetla ich poprawnie na wykresie. Jak znajdziesz przyczynę to ją napraw ale także uzasadnij dlaczego to jest prawdziwa przyczyna i jak to naprawiłeś.


# USER REQUIREMENT:  USER_REC_14

Wymagania Techniczne i Biznesowe: Jednolity Mechanizm Przeliczania Wskaźników Technicznych
1. WPROWADZENIE I KONTEKST
1.1 Problem Biznesowy
System tradingowy wymaga obliczania wskaźników technicznych w dwóch fundamentalnie różnych kontekstach operacyjnych. Pierwszy kontekst to analiza historyczna, obejmująca backtesting oraz przeglądanie wykresów, gdzie wszystkie dane są dostępne z góry i użytkownik oczekuje szybkiego przetworzenia w czasie rzędu sekund lub minut. Drugi kontekst to trading na żywo, gdzie dane docierają w czasie rzeczywistym, a system musi obliczać wskaźniki na bieżąco, nadążając za dynamiką rynku.
Kluczowym wyzwaniem jest zapewnienie, że te same algorytmy wskaźników działają identycznie w obu kontekstach. Użytkownik testujący strategię na danych historycznych musi mieć gwarancję, że te same sygnały wystąpią podczas tradingu na żywo przy identycznych warunkach rynkowych.
1.2 Ryzyko Podwójnej Implementacji
Alternatywne podejście polegające na stworzeniu dwóch oddzielnych silników obliczeniowych - jednego zoptymalizowanego pod kątem szybkości przetwarzania wsadowego dla danych historycznych, oraz drugiego zoptymalizowanego pod kątem niskiego opóźnienia dla danych na żywo - stwarza poważne ryzyko biznesowe i techniczne.
Podwójna implementacja tego samego algorytmu prowadzi do nieuniknionych rozbieżności. Nawet przy najlepszych intencjach programistycznych, dwa niezależnie utrzymywane fragmenty kodu implementujące ten sam algorytm będą się stopniowo różnić. Ktoś naprawi błąd w jednej wersji, ale zapomni o drugiej. Ktoś zoptymalizuje algorytm w jednym miejscu, zmieniając subtelnie jego zachowanie, ale nie przeniesie tej zmiany do drugiej implementacji.
Konsekwencje biznesowe takiego rozwiązania są poważne. Strategia testowana na danych historycznych może pokazywać zyski, podczas gdy ta sama strategia w środowisku produkcyjnym generuje straty - nie z powodu zmieniających się warunków rynkowych, ale z powodu różnic w implementacji algorytmów. Prowadzi to do utraty zaufania użytkowników do systemu oraz niemożności wiarygodnej weryfikacji strategii tradingowych.
Dodatkowo, podwójna implementacja oznacza podwójny koszt utrzymania kodu, podwójną liczbę błędów do naprawienia, oraz znacznie dłuższy czas potrzebny na implementację nowych wskaźników.
1.3 Proponowane Rozwiązanie
Rozwiązaniem jest architektura oparta na zasadzie rozdzielenia odpowiedzialności, gdzie algorytm wskaźnika jest całkowicie niezależny od kontekstu jego wykonania. System używa pojedynczej implementacji algorytmu obliczeniowego, która jest następnie osadzona w różnych kontekstach operacyjnych poprzez mechanizm wstrzykiwania zależności.
Kluczowa różnica między trybem historycznym a trybem na żywo nie leży w algorytmie obliczeniowym, ale w sposobie zarządzania czasem oraz dostarczania danych. W trybie historycznym system symuluje upływ czasu bez faktycznego czekania, iterując po wygenerowanej sekwencji timestampów. W trybie na żywo system czeka na rzeczywiste upływy czasu oraz reaguje na napływające dane rynkowe.
2. FUNDAMENTALNE ZASADY ARCHITEKTURY
2.1 Zasada Rozdzielenia Odpowiedzialności
Architektura systemu opiera się na rozdzieleniu trzech fundamentalnie różnych aspektów przeliczania wskaźników: algorytmu obliczeniowego określającego CO jest liczone, zarządzania czasem określającego KIEDY następują obliczenia, oraz dostarczania danych określającego SKĄD pochodzą informacje wejściowe.
Ten podział pozwala na niezależny rozwój i testowanie każdego aspektu. Algorytm wskaźnika może być rozwijany i testowany w izolacji, bez wiedzy o tym czy będzie używany dla danych historycznych czy na żywo. Zarządzanie czasem może być implementowane osobno dla różnych trybów operacyjnych. Dostarczanie danych może pochodzić z różnych źródeł bez wpływu na logikę obliczeniową.
2.2 Koncepcja Czystej Funkcji Obliczeniowej
Algorytm wskaźnika jest implementowany jako czysta funkcja matematyczna, która dla tych samych danych wejściowych zawsze zwraca identyczny wynik. Funkcja ta nie posiada efektów ubocznych, nie modyfikuje stanu globalnego, nie odwołuje się do czasu systemowego ani nie wykonuje operacji wejścia-wyjścia.
Czysta funkcja przyjmuje trzy kategorie parametrów wejściowych. Pierwszy to ramka danych zawierająca informacje rynkowe dostępne do danego momentu czasu. Drugi to parametry konfiguracyjne wariantu wskaźnika określające jego zachowanie. Trzeci to konkretny moment czasowy, dla którego ma być wykonane obliczenie.
Taka konstrukcja gwarantuje deterministyczność i przewidywalność. Jeśli algorytm otrzyma identyczne dane rynkowe, te same parametry konfiguracyjne, i ten sam timestamp, zawsze zwróci identyczną wartość, niezależnie od kontekstu wykonania. Ta właściwość jest fundamentalna dla zapewnienia spójności między trybem historycznym a trybem na żywo.
2.3 Zarządzanie Czasem jako Oddzielna Odpowiedzialność
Zarządzanie czasem jest całkowicie odseparowane od algorytmu obliczeniowego. Komponent zarządzający czasem ma jedną odpowiedzialność - generować sekwencję timestampów, dla których mają być wykonane obliczenia wskaźnika.
W trybie przetwarzania wsadowego dla danych historycznych, generator timestampów tworzy pełną sekwencję momentów czasu od początku do końca zakresu danych, z odstępami równymi interwałowi odświeżania. Ta sekwencja jest generowana natychmiast i iterowana tak szybko, jak to możliwe, bez rzeczywistego czekania na upływ czasu. Jest to kluczowe dla wydajności - przetworzenie godziny danych zajmuje sekundy, nie godzinę.
W trybie na żywo, generator timestampów działa w czasie rzeczywistym. Oblicza następny moment czasowy zaokrąglony do wielokrotności interwału odświeżania, czeka rzeczywiście na jego nadejście, a następnie zgłasza gotowość do wykonania obliczenia. Generator działa w nieskończoność, dopóki trading jest aktywny.
Krytyczne jest to, że algorytm obliczeniowy wskaźnika w ogóle nie wie, z którego generatora timestampów korzysta. Otrzymuje po prostu informację o kolejnym momencie czasowym do obliczenia i wykonuje swoją funkcję.
2.4 Dostarczanie Danych jako Oddzielna Odpowiedzialność
Podobnie jak zarządzanie czasem, dostarczanie danych jest odseparowane od algorytmu obliczeniowego. Komponent dostarczający dane ma jedną odpowiedzialność - dla podanego momentu czasowego zwrócić wszystkie dane rynkowe dostępne do tego momentu włącznie.
W trybie przetwarzania wsadowego, dostawca danych operuje na pełnej ramce danych załadowanej z pliku historycznego. Dla każdego żądanego timestampu wykonuje filtrację, zwracając tylko te wiersze gdzie timestamp jest mniejszy lub równy żądanemu momentowi. Jest to bardzo szybka operacja gdy kolumna timestamp jest zaindeksowana.
W trybie na żywo, dostawca danych utrzymuje bufor kroczący najnowszych danych rynkowych. Gdy docierają nowe ticki z giełdy, są dodawane do bufora. Gdy żądane są dane dla konkretnego timestampu, dostawca zwraca wszystkie elementy z bufora spełniające kryterium czasowe.
Znowu, algorytm obliczeniowy wskaźnika nie wie, czy pracuje z danymi historycznymi z pliku czy z danymi na żywo z bufora. Otrzymuje ramkę danych i wykonuje obliczenie.
2.5 Orkiestrator jako Łącznik Komponentów
Orkiestrator jest komponentem najwyższego poziomu, który łączy wszystkie elementy w spójny proces. Jego zadaniem jest koordynacja przepływu między generatorem timestampów, dostawcą danych, i silnikiem obliczeniowym wskaźnika.
Kluczowa właściwość orkiestratora jest taka, że jego logika jest identyczna niezależnie od trybu działania. Orkiestrator wykonuje pętlę: pobierz kolejny timestamp z generatora, zapytaj dostawcę danych o dane do tego momentu, przekaż dane i timestamp do silnika obliczeniowego wskaźnika, odbierz wynik i zapisz go w magazynie. Ta sama logika działa zarówno dla danych historycznych jak i dla danych na żywo.
Różnice między trybami są "wstrzykiwane" poprzez różne implementacje komponentów przekazanych do orkiestratora. Gdy orkiestrator otrzymuje generator timestampów dla trybu wsadowego i dostawcę danych dla trybu wsadowego, całość działa jako system przetwarzania historycznego. Gdy otrzymuje generator dla trybu live i dostawcę dla trybu live, całość działa jako system czasu rzeczywistego. Ale sam orkiestrator i silnik obliczeniowy wskaźnika pozostają niezmienione.
3. WYMAGANIA DOTYCZĄCE GENEROWANIA TIMESTAMPÓW
3.1 Kompletność Sekwencji Timestampów
System musi generować timestampy do przeliczenia wskaźnika zgodnie z globalnym parametrem interwału odświeżania, niezależnie od faktycznego występowania transakcji w danych źródłowych. Jest to fundamentalne wymaganie wynikające z natury wskaźników zależnych od czasu.
Należy zrozumieć, że wskaźniki techniczne wykorzystujące okna czasowe, takie jak średnie ważone czasem czy wskaźniki prędkości zmiany ceny, zmieniają swoją wartość nawet wtedy, gdy nie pojawiają się nowe transakcje rynkowe. Dzieje się tak ponieważ okno czasowe przesuwa się wraz z upływem czasu, a stare transakcje "wypadają" z okna podczas gdy zakres czasowy obejmuje nowe obszary.
Przykładowo, wskaźnik TWPA obliczający średnią ważoną z ostatnich trzydziestu sekund będzie zmieniał swoją wartość co pięć sekund, nawet jeśli przez ten czas nie wystąpiła żadna nowa transakcja. Jeśli ostatnia transakcja miała miejsce trzydzieści pięć sekund temu, po kolejnych pięciu sekundach ta transakcja wypadnie z okna czasowego i wartość wskaźnika zmieni się na zero lub wartość niezdefiniowaną.
Dlatego system nie może generować timestampów tylko w momentach występowania transakcji. Musi generować pełną sekwencję timestampów co określony interwał w całym zakresie czasowym, tworząc regularną siatkę momentów czasowych niezależną od rytmu napływających danych rynkowych.
3.2 Matematyczna Definicja Sekwencji
Sekwencja timestampów do obliczenia jest zdefiniowana matematycznie jako ciąg arytmetyczny. Pierwszy element sekwencji to najmniejszy timestamp większy niż początek zakresu danych, zaokrąglony w górę do najbliższej wielokrotności interwału odświeżania. Każdy kolejny element jest większy od poprzedniego o dokładnie wartość interwału odświeżania. Ostatni element to największy timestamp nie większy niż koniec zakresu danych, który spełnia warunek wielokrotności interwału.
Innymi słowy, jeśli dane zaczynają się od timestampu tysiąc trzy, a interwał odświeżania wynosi pięć sekund, pierwszym timestampem do obliczenia będzie tysiąc pięć. Następne to tysiąc dziesięć, tysiąc piętnaście i tak dalej, aż do końca zakresu danych.
Liczba elementów w sekwencji jest w przybliżeniu równa zakresowi czasowemu danych podzielonemu przez interwał odświeżania. Dla godziny danych przy interwale pięciu sekund, sekwencja zawiera siedemset dwadzieścia timestampów. Dla doby danych przy tym samym interwale, sekwencja zawiera siedemnaście tysięcy dwieście osiemdziesiąt timestampów.
3.3 Niezależność od Danych Źródłowych
Krytyczne jest zrozumienie, że sekwencja timestampów jest generowana całkowicie niezależnie od faktycznych timestampów występujących w danych rynkowych. System nie iteruje po unikalnych timestampach z pliku z cenami. Zamiast tego generuje własną regularną siatkę czasową na podstawie początku i końca zakresu oraz interwału odświeżania.
W praktyce oznacza to, że większość timestampów w sekwencji obliczeniowej nie będzie pokrywać się z timestampami transakcji w danych źródłowych. Jeśli transakcje przychodzą nieregularnie, na przykład o sekundach tysiąc trzy, tysiąc siedem, tysiąc jedenaście, podczas gdy sekwencja obliczeniowa to tysiąc pięć, tysiąc dziesięć, tysiąc piętnaście, to timestampy nie pokrywają się wcale.
To jest prawidłowe i zamierzone zachowanie. Wskaźnik będzie obliczany dla timestampów tysiąc pięć, tysiąc dziesięć i tysiąc piętnaście, używając danych dostępnych do tych momentów, nawet jeśli w tych dokładnych chwilach nie było transakcji.
3.4 Obsługa Długich Luk w Danych
Gdy w danych źródłowych występuje długa luka - na przykład przez pięćdziesiąt sekund nie było żadnych transakcji - system nadal musi generować timestampy co interwał odświeżania w obrębie tej luki i obliczać wskaźnik dla każdego z tych momentów.
Wartość wskaźnika w tych momentach będzie obliczana na podstawie starszych danych, które nadal mieszczą się w oknie czasowym wskaźnika. W miarę przesuwania się okna czasowego, wartość może pozostać stała jeśli te same stare transakcje są w oknie, lub może się zmienić gdy niektóre transakcje wypadną z okna.
Jest to kluczowa różnica od naiwnego podejścia, gdzie przeliczanie następowałoby tylko w momentach nowych danych. Takie naiwne podejście prowadziłoby do brakujących wartości wskaźnika w pliku wynikowym i niepoprawnego przedstawienia dynamiki rynku.
4. WYMAGANIA DOTYCZĄCE OBLICZANIA WSKAŹNIKÓW
4.1 Uniwersalność Algorytmu Obliczeniowego
Algorytm obliczeniowy każdego wskaźnika musi być implementowany jako pojedyncza funkcja, która działa identycznie niezależnie od kontekstu wykonania. Funkcja nie może zawierać logiki warunkowej zależnej od trybu działania, nie może sprawdzać czy działa w trybie historycznym czy na żywo.
Wszystkie informacje potrzebne do obliczenia są przekazywane jako parametry wejściowe. Dane rynkowe dostępne do danego momentu czasowego są przekazywane jako struktura tabelaryczna. Parametry konfiguracyjne wariantu wskaźnika, takie jak długość okien czasowych, są przekazywane jako słownik parametrów. Moment czasowy, dla którego ma być wykonane obliczenie, jest przekazywany jako wartość timestampu.
Funkcja zwraca pojedynczą wartość liczbową będącą wynikiem obliczenia wskaźnika dla podanego momentu czasowego. W przypadku braku wystarczających danych do wykonania obliczenia, funkcja zwraca wartość nieokreśloną lub zgłasza wyjątek, który jest obsługiwany na wyższym poziomie.
4.2 Zakres Danych Wejściowych
Dane rynkowe przekazywane do funkcji obliczeniowej muszą zawierać wszystkie informacje dostępne do momentu obliczenia włącznie, ale nie mogą zawierać informacji z przyszłości. Jest to fundamentalne dla zachowania realizmu obliczeniowego.
W trybie przetwarzania historycznego, gdy obliczamy wskaźnik dla timestampu na przykład tysiąc pięćdziesiąt, dane wejściowe mogą zawierać tylko transakcje gdzie timestamp jest mniejszy lub równy tysiąc pięćdziesiąt. Nawet jeśli w pliku historycznym mamy już dane z późniejszych momentów, nie mogą one być widoczne dla funkcji obliczeniowej. System musi symulować stan wiedzy, jaki byłby dostępny w tym momencie podczas rzeczywistego tradingu.
W trybie na żywo, ta zasada jest zachowana naturalnie - dane z przyszłości po prostu jeszcze nie nadeszły. Ale w trybie historycznym wymaga to świadomego filtrowania danych przed przekazaniem ich do funkcji obliczeniowej.
4.3 Określenie Okna Czasowego
Dla wskaźników operujących na oknach czasowych, zakres okna jest określany przez dwa parametry wyrażone jako liczba sekund wstecz od momentu obliczenia. Pierwszy parametr określa początek okna, drugi określa koniec okna.
Na przykład, jeśli obliczamy wskaźnik dla timestampu tysiąc dwieście, a parametr początkowy wynosi sześćdziesiąt, a parametr końcowy wynosi dziesięć, to okno czasowe obejmuje zakres od tysiąc sto czterdzieści do tysiąc sto dziewięćdziesiąt. Początek okna to tysiąc dwieście minus sześćdziesiąt, koniec okna to tysiąc dwieście minus dziesięć.
Szczególny przypadek występuje gdy parametr końcowy wynosi zero. Oznacza to, że okno kończy się w momencie obliczenia, czyli obejmuje zakres "od pewnego momentu w przeszłości do teraz". Taki wskaźnik reaguje na każdą nową transakcję, która pojawia się w bieżącym momencie.
Inny przypadek to gdy parametr końcowy jest większy od zera. Oznacza to, że okno kończy się w przeszłości, nie obejmując bieżącego momentu. Taki wskaźnik nie reaguje na nowe transakcje dopóki nie znajdą się one w oknie czasowym, co następuje dopiero po upływie czasu określonego przez parametr końcowy.
4.4 Obsługa Braku Danych w Oknie
Funkcja obliczeniowa musi określić swoje zachowanie gdy w oknie czasowym nie ma żadnych danych. Może to wystąpić na początku zakresu danych, gdy okno czasowe sięga przed pierwszy dostępny timestamp, lub podczas długich luk w danych.
Dla wskaźników cenowych, rozsądnym zachowaniem jest zwrócenie ostatniej znanej ceny sprzed początku okna, jeśli taka istnieje. Jeśli nie istnieje żadna wcześniejsza cena, funkcja zwraca wartość nieokreśloną.
Dla wskaźników ryzyka lub wskaźników ogólnych, rozsądnym zachowaniem jest zwrócenie wartości neutralnej, takiej jak zero dla wskaźników znormalizowanych do zakresu zero-jeden, lub wartość nieokreślona gdy nie da się określić sensownej wartości neutralnej.
System nie może po prostu pominąć timestampów gdzie brak danych - to prowadziłoby do luk w pliku wynikowym. Zamiast tego musi zapisać wartość nieokreśloną lub wartość domyślną, zachowując kompletność sekwencji timestampów.
4.5 Determinizm i Powtarzalność
Kluczową właściwością funkcji obliczeniowej jest pełny determinizm. Dla identycznych danych wejściowych, identycznych parametrów konfiguracyjnych, i identycznego timestampu, funkcja musi zawsze zwrócić dokładnie tę samą wartość liczbową.
Nie może być żadnej losowości w algorytmie. Nie może być zależności od stanu globalnego, zmiennych zewnętrznych, czy czasu systemowego. Funkcja nie może odwoływać się do żadnych zasobów zewnętrznych podczas obliczenia.
Ta właściwość jest kluczowa dla testowania i debugowania. Pozwala na izolowane testowanie algorytmu na zestawach testowych. Pozwala na wiarygodne porównanie wyników między trybem historycznym a trybem na żywo. Pozwala na reprodukcję problemów poprzez ponowne uruchomienie obliczeń z tymi samymi danymi wejściowymi.
5. WYMAGANIA DOTYCZĄCE DANYCH WYJŚCIOWYCH
5.1 Format i Lokalizacja Plików
Wyniki obliczeń wskaźnika muszą być zapisywane w strukturze katalogowej odzwierciedlającej hierarchię sesji, symbolu, i wariantu wskaźnika. Dla każdej sesji pobierania danych istnieje katalog główny. Wewnątrz niego, dla każdego symbolu istnieje podkatalog. Wewnątrz katalogu symbolu istnieje podkatalog indicators, a w nim pliki CSV dla poszczególnych wariantów wskaźników.
Nazwa pliku składa się z typu wskaźnika i unikalnego identyfikatora wariantu, rozdzielonych podkreśleniem, z rozszerzeniem CSV. Typ wskaźnika to jedna z wartości: general, risk, price, stop_loss, take_profit, close_order. Identyfikator wariantu to unikalny ciąg znaków identyfikujący konkretną konfigurację parametrów wskaźnika.
Przykładowa pełna ścieżka może wyglądać następująco: data/session_exec_20251007_144857_657c2dd6/AEVO_USDT/indicators/general_697ea864.csv
5.2 Struktura Pliku CSV
Plik CSV zawiera dokładnie dwie kolumny: timestamp i value. Pierwsza kolumna zawiera timestamp w formacie Unix time, czyli liczba sekund od epoki. Druga kolumna zawiera obliczoną wartość wskaźnika w tym momencie, jako liczba zmiennoprzecinkowa.
Plik zawiera wiersz nagłówka z nazwami kolumn. Każdy kolejny wiersz reprezentuje jeden moment czasowy i jedną wartość wskaźnika. Wiersze są uporządkowane rosnąco według timestampu.
Plik nie zawiera żadnych metadanych o wariancie wskaźnika, takich jak nazwa wskaźnika systemowego czy parametry konfiguracyjne. Te informacje są przechowywane oddzielnie w pliku konfiguracyjnym wariantów wskaźników. Identyfikator wariantu w nazwie pliku pozwala na powiązanie danych z konfiguracją.
5.3 Kompletność Zakres Czasowego
Zakres timestampów w pliku z wynikami wskaźnika musi odpowiadać zakresowi danych źródłowych z pliku cen. Pierwszy timestamp w pliku wyników to pierwszy timestamp z sekwencji obliczeniowej, który jest wewnątrz zakresu danych źródłowych. Ostatni timestamp w pliku wyników to ostatni timestamp z sekwencji obliczeniowej wewnątrz tego zakresu.
Liczba wierszy w pliku wyników musi być w przybliżeniu równa zakresowi czasowemu danych źródłowych podzielonemu przez interwał odświeżania. Niewielka różnica plus minus jeden wiersz jest dopuszczalna ze względu na zaokrąglenia timestampów do wielokrotności interwału.
Każdy timestamp w pliku wyników musi być dokładną wielokrotnością interwału odświeżania. Różnica między kolejnymi timestampami musi być równa interwałowi odświeżania, bez wyjątków. Nie może być luk czasowych w pliku wyników, chyba że wynikają one z braku danych źródłowych w pewnym zakresie i polityka wskaźnika nakazuje pominięcie takich momentów.
5.4 Obsługa Wartości Nieokreślonych
Gdy funkcja obliczeniowa nie może określić wartości wskaźnika dla danego timestampu ze względu na brak wystarczających danych, system musi to odnotować w pliku wyników. Możliwe są dwa podejścia.
Pierwsze podejście to zapisanie wartości null w kolumnie value. Jest to wyraźne oznaczenie, że obliczenie było próbowane, ale nie powiodło się z powodu braku danych. Timestamp pozostaje w pliku, zachowując kompletność sekwencji, ale wartość jest wyraźnie niezdefiniowana.
Drugie podejście to całkowite pominięcie wiersza dla danego timestampu. Jest to dopuszczalne tylko w przypadkach, gdy brak danych jest uzasadniony, na przykład na samym początku zakresu danych gdy okno czasowe wskaźnika sięga przed dostępne dane. Ale takie pominięcie musi być spójne i udokumentowane w specyfikacji wskaźnika.
Wybór podejścia może zależeć od typu wskaźnika i polityki obsługi błędów. Najważniejsze jest, aby zachowanie było konsekwentne i przewidywalne dla użytkownika analizującego wyniki.
5.5 Precyzja Numeryczna
Wartości wskaźników muszą być zapisywane z wystarczającą precyzją numeryczną, aby uniknąć błędów zaokrągleń. Dla większości wskaźników, precyzja sześciu miejsc po przecinku jest wystarczająca. Dla wskaźników operujących na bardzo małych wartościach lub wymagających wysokiej dokładności, precyzja może być większa.
Kluczowe jest, aby precyzja zapisu w pliku nie była mniejsza niż precyzja wewnętrznych obliczeń. Jeśli algorytm oblicza wartości z precyzją podwójnej precyzji zmiennoprzecinkowej, zapisanie tylko dwóch miejsc po przecinku spowodowałoby utratę informacji i niemożność wiarygodnego porównania wyników.
6. WYMAGANIA DOTYCZĄCE TRYBU PRZETWARZANIA WSADOWEGO
6.1 Charakter Symulacji Czasu
W trybie przetwarzania wsadowego system symuluje upływ czasu bez rzeczywistego czekania. Generator timestampów tworzy pełną sekwencję momentów czasowych na początku, a następnie system iteruje po tej sekwencji tak szybko, jak pozwalają na to zasoby obliczeniowe.
Słowo "symulacja" odnosi się tutaj do konceptualnego przesuwania się punktu odniesienia czasu. Dla każdej iteracji pętli, system zachowuje się tak jakby "teraz" było w konkretnym momencie określonym przez aktualny timestamp z sekwencji. Filtruje dane do tego momentu, oblicza wskaźnik, zapisuje wynik, i natychmiast przechodzi do następnego timestampu.
Nie ma opóźnień między iteracjami. System nie wywołuje funkcji uśpienia. Pętla wykonuje się z maksymalną możliwą prędkością, ograniczoną tylko przez czas potrzebny na filtrowanie danych, wykonanie obliczeń, i zapis wyniku.
To podejście pozwala na przetworzenie godziny danych historycznych w kilka sekund rzeczywistego czasu wykonania, co jest kluczowe dla użyteczności systemu w kontekście analizy historycznej i backtestingu.
6.2 Wydajność Przetwarzania
System musi być zoptymalizowany pod kątem wydajności przetwarzania wsadowego. Dla typowego wskaźnika o umiarkowanej złożoności obliczeniowej, przetworzenie godziny danych przy interwale pięciu sekund, co daje około siedmiuset dwudziestu punktów obliczeniowych, powinno zająć maksymalnie kilka sekund rzeczywistego czasu.
Dla pełnej doby danych, około siedemnastu tysięcy punktów obliczeniowych, czas wykonania nie powinien przekraczać jednej do dwóch minut dla prostych wskaźników. Dla bardziej złożonych wskaźników wymagających intensywnych obliczeń, czas do pięciu minut jest akceptowalny.
Kluczowa metryka to liczba punktów obliczeniowych przetworzonych na sekundę. Dla prostych wskaźników, system powinien osiągać setki punktów na sekundę. Dla złożonych wskaźników, dziesiątki punktów na sekundę są akceptowalne.
Jeśli czasy przetwarzania przekraczają te wartości, należy zoptymalizować algorytm lub infrastrukturę obliczeniową. Możliwe optymalizacje obejmują lepsze indeksowanie danych, unikanie zbędnych kopii struktur danych, wykorzystanie operacji wektoryzowanych zamiast iteracji, lub równoległe przetwarzanie gdy algorytm na to pozwala.
6.3 Obsługa Dużych Zbiorów Danych
System musi być zaprojektowany tak, aby efektywnie obsługiwać duże zbiory danych historycznych. Dla sesji danych obejmującej tydzień lub miesiąc, plik z cenami może zawierać setki tysięcy lub miliony wierszy.
Kluczowe jest unikanie wielokrotnego ładowania lub kopiowania pełnego zbioru danych. Dane powinny być załadowane raz na początku procesu, a następnie wielokrotnie filtrowane dla kolejnych timestampów bez tworzenia pełnych kopii.
Filtrowanie danych do danego timestampu musi być operacją o złożoności logarytmicznej lub liniowej, nie kwadratowej. Użycie odpowiednich struktur danych i indeksów jest kluczowe. W praktyce oznacza to wykorzystanie możliwości bibliotek do przetwarzania danych, które implementują efektywne indeksowanie i filtrowanie.
Jeśli przetwarzanie bardzo dużych zbiorów danych nadal jest problemem, można rozważyć przetwarzanie segmentowe, gdzie zakres czasowy jest dzielony na mniejsze segmenty przetwarzane sekwencyjnie, z wynikami zapisywanymi przyrostowo.
6.4 Raportowanie Postępu
Dla długotrwałych operacji przetwarzania, system powinien raportować postęp do użytkownika lub systemu monitorującego. Po przetworzeniu określonego procentu punktów obliczeniowych, na przykład co dwadzieścia pięć procent, system emituje zdarzenie informujące o aktualnym stanie postępu.
Raport postępu zawiera informacje takie jak liczba przetworzonych punktów, całkowita liczba punktów do przetworzenia, aktualny procent ukończenia, przewidywany pozostały czas na podstawie dotychczasowej prędkości przetwarzania.
Te informacje są szczególnie ważne w kontekście interfejsu użytkownika, gdzie użytkownik czeka na wyniki po zaznaczeniu wskaźnika do wyświetlenia na wykresie. Pasek postępu z odliczaniem pozostałego czasu znacząco poprawia doświadczenie użytkownika w porównaniu do braku informacji zwrotnej.
6.5 Możliwość Anulowania
Użytkownik musi mieć możliwość anulowania długotrwałej operacji przetwarzania. System regularnie sprawdza flagę anulowania między iteracjami pętli obliczeniowej, i jeśli jest ustawiona, przerywa przetwarzanie w sposób kontrolowany.
Częściowe wyniki obliczone przed anulowaniem mogą być zachowane lub odrzucone, w zależności od polityki systemu i preferencji użytkownika. Jeśli częściowe wyniki są zachowane, plik z wynikami zawiera timestampy do momentu przerwania, wyraźnie oznaczając że obliczenia nie są kompletne.
Mechanizm anulowania jest szczególnie ważny gdy użytkownik eksperymentuje z różnymi wariantami wskaźników i szybko przełącza się między nimi. Możliwość przerwania poprzedniego obliczenia pozwala uniknąć marnotrawstwa zasobów obliczeniowych i długiego oczekiwania.
7. WYMAGANIA DOTYCZĄCE TRYBU NA ŻYWO
7.1 Charakter Przetwarzania Czasu Rzeczywistego
W trybie na żywo system działa w czasie rzeczywistym, przetwarzając dane w miarę ich napływania z giełdy. Generator timestampów działa jako timer, który rzeczywiście czeka na upływ interwału odświeżania między kolejnymi obliczeniami.
System oblicza następny timestamp do obliczenia jako najbliższą przyszłą wielokrotność interwału odświeżania. Następnie czeka na nadejście tego momentu, wykorzystując mechanizmy asynchroniczne systemu operacyjnego. Gdy moment nadejdzie, wykonywane jest obliczenie wskaźnika na podstawie danych dostępnych w tym momencie.
Równolegle, system nasłuchuje na napływające dane rynkowe z giełdy. Gdy przybywa nowy tick - informacja o wykonanej transakcji - jest dodawany do bufora danych. Dla wskaźników, których okno czasowe kończy się w bieżącym momencie, nowy tick może dodatkowo wyzwolić przeliczenie wskaźnika, niezależnie od regularnego timera.
7.2 Mechanizm Podwójnego Wyzwalania
Dla wskaźników, gdzie parametr końca okna czasowego wynosi zero, czyli okno kończy się w bieżącym momencie, system implementuje podwójny mechanizm wyzwalania obliczeń.
Pierwszy mechanizm to timer działający co interwał odświeżania. Zapewnia on regularne obliczenia niezależnie od tego czy przybyły nowe dane. Jest to kluczowe dla uwzględnienia przesuwania się okna czasowego i wypadania starych transakcji z okna.
Drugi mechanizm to reakcja na zdarzenie nowego ticka. Gdy przybędzie nowa transakcja, a wskaźnik ma okno kończące się teraz, nowa transakcja natychmiast wpływa na wartość wskaźnika. System może opcjonalnie wykonać dodatkowe obliczenie w tym momencie, dostarczając najbardziej aktualną wartość wskaźnika.
Ważne jest, aby dodatkowe obliczenie wywołane przez tick nie zastępowało regularnego obliczenia z timera. Oba mechanizmy działają równolegle. Timer nadal odmierza czas i wykonuje obliczenia według swojego harmonogramu. Ticki mogą wywoływać dodatkowe obliczenia między tymi regularnymi momentami.
7.3 Zarządzanie Buforem Danych
System w trybie na żywo utrzymuje bufor danych rynkowych obejmujący ostatni okres czasu wystarczający do obliczenia wszystkich aktywnych wskaźników. Rozmiar bufora jest określony jako maksymalna długość okna czasowego spośród wszystkich wskaźników, plus margines bezpieczeństwa.
Gdy przybywa nowy tick, jest dodawany na koniec bufora. Jeśli bufor osiągnął swój maksymalny rozmiar, najstarszy element jest usuwany. To zapewnia, że bufor zawsze zawiera najnowsze dane, a pamięć nie rośnie bez ograniczeń.
Dostęp do bufora musi być synchronizowany, ponieważ dane są dodawane asynchronicznie przez wątek obsługujący strumień danych z giełdy, a odczytywane przez wątek wykonujący obliczenia wskaźników. Synchronizacja musi być efektywna, aby nie wprowadzać opóźnień.
7.4 Opóźnienie Obliczeniowe
Kluczową metryką w trybie na żywo jest opóźnienie między momentem nadejścia danych a momentem udostępnienia obliczonej wartości wskaźnika. To opóźnienie składa się z czasu dostępu do bufora, czasu wykonania algorytmu obliczeniowego, i czasu zapisu wyniku.
Dla większości wskaźników, całkowite opóźnienie powinno być mniejsze niż sto milisekund. Dla prostych wskaźników, opóźnienie poniżej dziesięciu milisekund jest osiągalne. Tylko bardzo złożone wskaźniki wymagające intensywnych obliczeń mogą mieć opóźnienia rzędu setek milisekund.
Jeśli opóźnienie jest zbyt duże, wpływa to na jakość sygnałów tradingowych. Strategia otrzymuje nieaktualne informacje i podejmuje decyzje na podstawie przestarzałych danych. Może to prowadzić do gorszych wyników tradingowych lub nawet strat.
Monitorowanie opóźnienia obliczeniowego jest kluczowe. System powinien mierzyć i logować opóźnienie dla każdego obliczenia, oraz alarmować gdy przekracza ono akceptowalne progi.
7.5 Trwałość Danych
W trybie na żywo, wyniki obliczeń wskaźników mogą być zapisywane przyrostowo do pliku CSV dla celów historycznych i późniejszej analizy. Po każdym obliczeniu, nowy wiersz z timestampem i wartością jest dopisywany na koniec pliku.
Alternatywnie, dla optymalizacji wydajności, wyniki mogą być najpierw buforowane w pamięci lub szybkim magazynie tymczasowym, a następnie zapisywane wsadowo do pliku co określony interwał lub po zgromadzeniu określonej liczby wyników.
Niezależnie od mechanizmu zapisu do pliku, wyniki muszą być natychmiast dostępne dla innych komponentów systemu, takich jak moduł podejmowania decyzji tradingowych czy interfejs użytkownika pokazujący bieżące wartości wskaźników. Te komponenty otrzymują wartości poprzez mechanizmy publikacji zdarzeń lub współdzielonego stanu w pamięci, nie czekając na zapis do pliku.
7.6 Odporność na Zakłócenia
System w trybie na żywo musi być odporny na typowe zakłócenia strumienia danych. Mogą wystąpić krótkie przerwy w łączności z giełdą, opóźnienia w dostarczaniu danych, lub dane docierające w nieprawidłowej kolejności.
Gdy wystąpi przerwa w danych, system kontynuuje obliczanie wskaźników w zaplanowanych momentach timera, używając ostatnio dostępnych danych. Wartości wskaźników mogą pozostać stałe do momentu nadejścia nowych danych, co jest prawidłowym zachowaniem.
Gdy dane docierają z opóźnieniem ale z poprawnymi timestampami historycznymi, system może opcjonalnie przeliczać wskaźniki wstecz dla tych momentów, aktualizując historyczne wartości. To zależy od polityki systemu i wymagań dokładności historycznej.
Gdy dane docierają w nieprawidłowej kolejności, system sortuje je przed dodaniem do bufora lub odrzuca duplikaty. Mechanizmy walidacji zapewniają spójność i poprawność danych wejściowych.
8. WYMAGANIA DOTYCZĄCE SPÓJNOŚCI MIĘDZY TRYBAMI
8.1 Gwarancja Identycznych Wyników
Fundamentalnym wymaganiem systemu jest gwarancja, że obliczenie wskaźnika dla tego samego momentu czasowego, przy tych samych dostępnych danych rynkowych, zwróci identyczną wartość niezależnie od tego czy obliczenie było wykonane w trybie przetwarzania wsadowego czy w trybie na żywo.
Ta gwarancja jest zapewniona przez użycie tego samego kodu algorytmu obliczeniowego w obu trybach. Nie ma oddzielnych implementacji, nie ma logiki warunkowej zależnej od trybu. Funkcja obliczeniowa otrzymuje dane i parametry, wykonuje obliczenie, zwraca wynik. Kontekst wykonania jest niewidoczny dla funkcji.
Weryfikacja tej gwarancji odbywa się poprzez testy porównawcze. System przetwarza ten sam zestaw danych historycznych dwa razy - raz w trybie wsadowym, raz w trybie symulowanego czasu rzeczywistego gdzie dane są odtwarzane jakby docierały na żywo. Wyniki są porównywane punkt po punkcie. Różnice większe niż marginalne błędy zaokrągleń zmiennoprzecinkowych wskazują na problem w implementacji.
8.2 Testowanie Spójności
Proces testowania spójności jest formalny i zautomatyzowany. Zestaw testowy zawiera reprezentatywne dane rynkowe obejmujące różne scenariusze - normalne zachowanie rynku, wysoką zmienność, długie luki w danych, ekstremalne wartości cen.
Dla każdego wariantu wskaźnika, test wykonuje pełne obliczenie w trybie wsadowym, zapisując wszystkie wyniki do pliku referencyjnego. Następnie test wykonuje symulację trybu na żywo, gdzie dane są odtwarzane z kontrolowaną prędkością, a wyniki są zapisywane do pliku testowego. Na końcu test porównuje oba pliki wiersz po wierszu.
Porównanie akceptuje minimalne różnice wynikające z ograniczonej precyzji arytmetyki zmiennoprzecinkowej. Typowo, różnica mniejsza niż dziesięć do potęgi minus dziesięć jest akceptowalna. Większe różnice są traktowane jako błąd implementacji.
Test również weryfikuje, że liczba wierszy w obu plikach jest identyczna, że timestampy się pokrywają, i że brak wartości null występuje w tych samych miejscach w obu plikach.
8.3 Polityka Naprawy Rozbieżności
Jeśli wykryte zostaną rozbieżności między wynikami trybu wsadowego a trybu na żywo, priorytetowa jest ich natychmiastowa naprawa. Rozbieżności są traktowane jako błędy krytyczne, ponieważ podważają fundamentalną gwarancję systemu.
Proces naprawy rozpoczyna się od dokładnej analizy przyczyny rozbieżności. Typowe przyczyny obejmują niewłaściwe filtrowanie danych w jednym z trybów, różnice w zaokrągleniach lub konwersjach typów, niezamierzoną zależność od stanu globalnego lub czasu systemowego, błędy w implementacji mechanizmów synchronizacji w trybie na żywo.
Po zidentyfikowaniu przyczyny, naprawa jest implementowana tak, aby usunąć różnicę bez zmiany fundamentalnej logiki algorytmu. Jeśli zmiana w algorytmie jest konieczna, musi być wykonana w jednym miejscu i automatycznie wpływać na oba tryby.
Po naprawie, pełny zestaw testów spójności jest uruchamiany ponownie, aby upewnić się że problem został rozwiązany i nie wprowadzono nowych rozbieżności.
8.4 Monitoring Produkcyjny
W środowisku produkcyjnym, gdzie system działa w trybie na żywo, okresowo wykonywane są testy weryfikacyjne porównujące bieżące wyniki z ponownymi obliczeniami historycznymi na tych samych danych. Jeśli strategia była aktywna przez ostatnie dwadzieścia cztery godziny, system może po zakończeniu sesji tradingowej przeliczyć wskaźniki w trybie wsadowym na danych z tej sesji i porównać z wartościami obliczonymi na żywo.
Wykryte rozbieżności są logowane i alarmują zespół odpowiedzialny za system. Nawet jeśli rozbieżności są małe i nie spowodowały błędnych decyzji tradingowych, są badane i naprawiane, aby zapobiec ich narastaniu.
Ten monitoring produkcyjny służy jako dodatkowa warstwa weryfikacji, że system działa zgodnie z założeniami w rzeczywistych warunkach rynkowych, nie tylko w kontrolowanym środowisku testowym.
9. WYMAGANIA DOTYCZĄCE WYDAJNOŚCI
9.1 Metryki Wydajności dla Trybu Wsadowego
Wydajność w trybie przetwarzania wsadowego jest mierzona jako liczba punktów obliczeniowych przetworzonych na sekundę rzeczywistego czasu wykonania. Dla prostych wskaźników, takich jak średnie ruchome czy TWPA, system powinien osiągać od dwustu do pięciuset punktów na sekundę na typowym sprzęcie serwerowym.
Dla bardziej złożonych wskaźników wymagających iteracyjnych obliczeń lub operacji na dużych oknach danych, akceptowalna wydajność to od pięćdziesięciu do stu punktów na sekundę.
Całkowity czas przetworzenia jest oceniany w kontekście doświadczenia użytkownika. Użytkownik zaznaczający wskaźnik do wyświetlenia na wykresie obejmującym godzinę danych oczekuje wyników w czasie do dziesięciu sekund. Dla wykresu obejmującego dobę danych, akceptowalne jest oczekiwanie do dwóch minut. Dla dłuższych zakresów, do dziesięciu minut jest maksymalnym akceptowalnym czasem.
9.2 Metryki Wydajności dla Trybu Na Żywo
W trybie na żywo kluczową metryką jest opóźnienie obliczeniowe - czas od momentu nadejścia danych do momentu udostępnienia wartości wskaźnika. Dla większości wskaźników, opóźnienie powinno być poniżej stu milisekund. Dla krytycznych wskaźników używanych do podejmowania szybkich decyzji tradingowych, opóźnienie poniżej dwudziestu milisekund jest pożądane.
Druga metryka to stabilność częstotliwości obliczania. Timer powinien wyzwalać obliczenia z precyzją co najmniej stu milisekund względem zaplanowanego interwału. Jeśli interwał odświeżania to pięć sekund, obliczenia powinny następować co pięć sekund plus minus sto milisekund.
Trzecia metryka to wykorzystanie zasobów systemowych. Obliczanie wskaźników w trybie na żywo nie powinno konsumować więcej niż dziesiąt procent dostępnej mocy obliczeniowej procesora w typowych warunkach. Zużycie pamięci powinno być stałe, bez przecieków, z buforem danych zajmującym nie więcej niż kilkaset megabajtów dla typowej konfiguracji wskaźników.
9.3 Optymalizacje Wymagane
System musi implementować podstawowe optymalizacje aby osiągnąć wymagane metryki wydajności. Po pierwsze, unikanie wielokrotnego kopiowania dużych struktur danych. Dane rynkowe ładowane na początku procesu powinny pozostać w jednym miejscu w pamięci, a operacje filtrowania i selekcji powinny zwracać widoki lub referencje, nie pełne kopie.
Po drugie, wykorzystanie indeksowania na kolumnach timestamp. Filtrowanie ramki danych do określonego momentu czasowego powinno używać operacji indeksowanej, nie sekwencyjnego skanowania wszystkich wierszy.
Po trzecie, wykorzystanie operacji wektoryzowanych dostarczanych przez biblioteki do przetwarzania danych. Operacje takie jak mnożenie kolumny przez skalę, sumowanie wartości, czy obliczanie statystyk powinny używać natywnych implementacji w języku C, nie pętli interpretowanych w języku wysokiego poziomu.
Po czwarte, minimalizacja alokacji pamięci wewnątrz pętli obliczeniowej. Struktury tymczasowe potrzebne do obliczeń powinny być alokowane raz i reużywane, nie tworzone od nowa dla każdego punktu obliczeniowego.
9.4 Możliwości Równoległego Przetwarzania
Dla bardzo dużych zbiorów danych lub wielu wariantów wskaźników obliczanych jednocześnie, system może wykorzystać równoległe przetwarzanie. Jeśli algorytm wskaźnika jest bezstanowy i działa na niezależnych odcinkach czasowych, możliwe jest podzielenie pełnego zakresu na segmenty i przetwarzanie ich równolegle w wielu procesach lub wątkach.
Ważne jest aby równoległość nie naruszyła gwarancji deterministyczności. Wyniki muszą być identyczne niezależnie czy przetwarzanie było sekwencyjne czy równoległe. Oznacza to, że nie może być współdzielonego stanu między równoległymi jednostkami przetwarzania, oraz że wyniki muszą być scalane w poprawnej kolejności.
Decyzja o użyciu równoległości powinna być podejmowana automatycznie przez system na podstawie rozmiaru danych i dostępnych zasobów. Dla małych zbiorów danych, narzut związany z równoległością może przewyższać korzyści, więc sekwencyjne przetwarzanie jest lepsze.
9.5 Profilowanie i Monitoring Wydajności
System musi zawierać mechanizmy profilowania wydajności identyfikujące wąskie gardła w obliczeniach. Dla każdego wariantu wskaźnika, system mierzy średni czas wykonania pojedynczego obliczenia, rozkład czasów, oraz identyfikuje operacje konsumujące najwięcej czasu.
Te informacje są używane do priorytetyzacji optymalizacji. Wskaźniki o najgorszej wydajności są optymalizowane jako pierwsze. Operacje w ramach algorytmu konsumujące najwięcej czasu są głównym celem optymalizacji.
Monitoring wydajności w środowisku produkcyjnym pozwala wykrywać degradację wydajności w czasie. Jeśli średni czas obliczania wskaźnika rośnie, może to wskazywać na problemy takie jak fragmentacja pamięci, przecieki, lub zwiększające się rozmiary danych wymagające skalowania infrastruktury.
10. WYMAGANIA DOTYCZĄCE JAKOŚCI I NIEZAWODNOŚCI
10.1 Pokrycie Testami Jednostkowymi
Każdy algorytm wskaźnika musi mieć kompletny zestaw testów jednostkowych weryfikujących poprawność obliczeń. Testy obejmują przypadki podstawowe z znanymi oczekiwanymi wynikami, które mogą być weryfikowane ręcznie lub obliczone niezależnie.
Testy obejmują przypadki brzegowe takie jak puste dane wejściowe, dane zawierające pojedynczy punkt, dane gdzie wszystkie wartości są identyczne, dane zawierające wartości ekstremalne, długie luki w danych, dane na granicy zakresu timestampów.
Dla wskaźników operujących na oknach czasowych, testy weryfikują poprawność obsługi granic okna, poprawność przesuwania się okna w czasie, oraz poprawność obsługi sytuacji gdy okno rozciąga się poza dostępne dane.
Pokrycie kodu testami jednostkowymi powinno przekraczać dziewięćdziesiąt procent dla kodu algorytmów wskaźników. Każda ścieżka wykonania w algorytmie powinna być przetestowana.
10.2 Testy Integracyjne
Oprócz testów jednostkowych algorytmów, system wymaga testów integracyjnych weryfikujących poprawne współdziałanie komponentów. Testy integracyjne obejmują pełny przepływ od załadowania danych przez wygenerowanie timestampów, wykonanie obliczeń, do zapisu wyników.
Testy integracyjne używają realistycznych zbiorów danych symulujących rzeczywiste warunki rynkowe. Weryfikują czy plik wynikowy ma poprawną strukturę, poprawne timestampy, poprawną liczbę wierszy, poprawne wartości liczbowe.
Testy integracyjne również weryfikują obsługę błędów i sytuacji wyjątkowych. Co się dzieje gdy dane wejściowe są uszkodzone, gdy parametry wariantu są nieprawidłowe, gdy brak uprawnień do zapisu pliku wynikowego, gdy proces jest przerwany w połowie wykonania.
10.3 Walidacja Numeryczna
Dla algorytmów wskaźników implementujących znane wzory matematyczne lub statystyczne, system wykonuje walidację numeryczną porównując wyniki z niezależnymi implementacjami referencyjnymi. Mogą to być implementacje w innych bibliotekach numerycznych, implementacje w innych językach programowania, lub obliczenia ręczne dla małych zbiorów danych testowych.
Walidacja numeryczna weryfikuje nie tylko poprawność wartości średnich, ale również stabilność numeryczną algorytmu. Algorytm nie powinien być nadmiernie wrażliwy na małe zmiany w danych wejściowych. Nie powinien tracić precyzji przy operacjach na bardzo małych lub bardzo dużych wartościach.
Dla wskaźników gdzie nie istnieje jednoznaczna definicja matematyczna lub referencja, walidacja polega na weryfikacji zgodności z opisem biznesowym i oczekiwaniami domenowymi ekspertów tradingowych.
10.4 Obsługa Błędów
System musi obsługiwać błędy w sposób przewidywalny i dokumentowany. Gdy wystąpi błąd podczas obliczania wskaźnika, system loguje szczegółowe informacje o błędzie włączając timestamp, parametry, oraz fragment danych wejściowych.
Błędy są kategoryzowane według powagi. Błędy krytyczne, takie jak uszkodzone dane wejściowe lub nieprawidłowe parametry, powodują przerwanie procesu i zgłoszenie do systemu monitorującego. Błędy ostrzegawcze, takie jak brak danych w określonym przedziale czasowym, powodują zapisanie wartości null dla tego punktu ale kontynuację przetwarzania.
W trybie na żywo, błędy w obliczeniu pojedynczego punktu nie mogą zatrzymać całego procesu. System musi być odporny i kontynuować działanie mimo sporadycznych błędów. Jednak jeśli błędy stają się częste, system alarmuje o problemie.
10.5 Logowanie Diagnostyczne
System implementuje wielopoziomowe logowanie diagnostyczne. Na poziomie informacyjnym, logowane są rozpoczęcie i zakończenie przetwarzania, liczba przetworzonych punktów, czas wykonania, lokalizacja pliku wynikowego.
Na poziomie ostrzeżeń, logowane są sytuacje nietypowe takie jak długie luki w danych, wartości ekstremalne, wolne wykonanie, oraz wszelkie sytuacje gdzie obliczenie było wykonane ale wynik może być niepewny.
Na poziomie szczegółowym, używanym podczas debugowania, logowane są informacje o każdym kroku procesu - pobraniu danych dla timestampu, filtrowaniu do okna czasowego, wykonaniu algorytmu, wartości pośrednie w obliczeniach.
Logi są strukturyzowane i możliwe do przetwarzania automatycznego. Zawierają kontekst taki jak identyfikator sesji, symbol, identyfikator wariantu wskaźnika, co pozwala na korelację logów z różnych komponentów systemu.
11. WYMAGANIA BIZNESOWE
11.1 Wartość dla Użytkownika
Użytkownik systemu, którym jest trader lub analityk rynków finansowych, otrzymuje następujące wartości biznesowe z poprawnie zaimplementowanego systemu wskaźników.
Po pierwsze, możliwość wiarygodnego testowania strategii tradingowych na danych historycznych. Użytkownik wie, że jeśli strategia pokazuje zyski w backteście, te same sygnały wystąpią podczas rzeczywistego tradingu. Nie ma ryzyka rozbieżności między testem a produkcją.
Po drugie, szybkość analizy. Użytkownik zaznaczając wskaźnik na wykresie otrzymuje wyniki w ciągu sekund, nie minut czy godzin. Może eksperymentować z różnymi konfiguracjami, szybko iterować, testować hipotezy. Szybkość analizy przekłada się na produktywność i jakość decyzji tradingowych.
Po trzecie, pewność jakości danych. Użytkownik wie, że wskaźniki są obliczane według ścisłych reguł, z pełną kompletnoscia timestampów, bez luk czy błędów. Może polegać na wskaźnikach w kluczowych momentach podejmowania decyzji.
11.2 Przewaga Konkurencyjna
System oferujący jednolitą implementację wskaźników z gwarancją spójności między backtestem a tradingiem na żywo daje przewagę konkurencyjną na rynku platform tradingowych.
Wiele konkurencyjnych platform ma oddzielne silniki dla danych historycznych i danych na żywo, co prowadzi do rozbieżności. Traderzy tracą zaufanie gdy strategia "zarabiająca" w backteście generuje straty na produkcji. Platforma oferująca gwarancję spójności może to wykorzystać jako punkt różnicujący w marketingu.
Dodatkowo, szybkość przetwarzania danych historycznych pozwala na oferowanie zaawansowanych funkcji analitycznych, które byłyby niepraktyczne przy wolnym przetwarzaniu. Użytkownik może analizować długie okresy historii, testować setki konfiguracji parametrów, przeprowadzać optymalizacje strategii.
11.3 Redukcja Kosztów Rozwoju
Jednolita implementacja algorytmów wskaźników znacząco redukuje koszty rozwoju produktu. Dodanie nowego wskaźnika wymaga napisania jednego algorytmu, który automatycznie działa w obu trybach. Nie ma potrzeby implementacji dwóch wersji, nie ma konieczności synchronizacji zmian między wersjami.
Czas potrzebny na implementację nowego wskaźnika spada z dni do godzin. Programista skupia się na logice biznesowej wskaźnika, nie na integracji z infrastrukturą. Framework dostarcza wszystkie mechanizmy zarządzania czasem, dostępu do danych, zapisu wyników.
Redukcja kosztów dotyczy również utrzymania kodu. Błędy są naprawiane w jednym miejscu. Optymalizacje benefitują oba tryby jednocześnie. Nie ma ryzyka, że zmiana w jednej wersji nie została przeniesiona do drugiej.
11.4 Wiarygodność i Zaufanie
Dla platformy tradingowej, wiarygodność jest fundamentalna dla sukcesu biznesowego. Użytkownicy powierzają platformie swoje pieniądze i decyzje inwestycyjne. Muszą mieć absolutne zaufanie, że system działa zgodnie z deklaracjami.
Gwarancja spójności między backtestem a tradingiem na żywo buduje to zaufanie. Użytkownik może zweryfikować działanie wskaźników testując je na znanych danych historycznych. Jeśli widzi, że wartości się zgadzają z oczekiwaniami, ma pewność że tak samo będzie działać na produkcji.
Transparentność implementacji również buduje zaufanie. Algorytmy wskaźników mogą być udokumentowane i wyjaśnione użytkownikom. Użytkownicy zaawansowani mogą weryfikować poprawność obliczeń. Brak "czarnych skrzynek" gdzie nie wiadomo jak dokładnie coś jest liczone.
11.5 Skalowalność Biznesu
System zaprojektowany zgodnie z tymi wymaganiami jest skalowalny biznesowo. Może obsługiwać rosnącą liczbę użytkowników, rosnącą liczbę symboli tradingowych, rosnącą liczbę wariantów wskaźników.
Wydajność przetwarzania wsadowego pozwala na obsługę wielu jednoczesnych żądań użytkowników przeglądających wykresy historyczne. Architektura bezstanowa algorytmów pozwala na równoległe przetwarzanie i skalowanie horyzontalne.
W trybie na żywo, efektywne zarządzanie zasobami pozwala na obliczanie wielu wskaźników dla wielu symboli jednocześnie na pojedynczym serwerze. Architektura umożliwia dodawanie kolejnych serwerów gdy rośnie obciążenie.
Możliwość szybkiego dodawania nowych wskaźników pozwala na szybką reakcję na potrzeby rynku i użytkowników. Konkurencja wprowadza nowy popularny wskaźnik - platforma może dodać go w ciągu dni, nie miesięcy.
12. PODSUMOWANIE KLUCZOWYCH ZASAD
System przeliczania wskaźników technicznych opiera się na trzech fundamentalnych zasadach.
Pierwsza zasada to rozdzielenie algorytmu obliczeniowego od kontekstu wykonania. Algorytm wskaźnika to czysta funkcja matematyczna, która nie wie czy działa w trybie historycznym czy na żywo. Otrzymuje dane, parametry, timestamp. Zwraca wartość. Koniec.
Druga zasada to kompletność sekwencji timestampów. System generuje i oblicza wartości wskaźnika dla każdego momentu czasowego zgodnie z interwałem odświeżania, niezależnie od tego czy w tym momencie były transakcje. To kluczowe dla wskaźników zależnych od czasu, których wartość zmienia się nawet bez nowych danych ze względu na przesuwanie się okna czasowego.
Trzecia zasada to gwarancja spójności. Ten sam algorytm, te same dane, ten sam timestamp - zawsze ta sama wartość, niezależnie od trybu. To gwarantowane przez architekturę, weryfikowane przez testy, monitorowane w produkcji.
Te zasady zapewniają, że użytkownik testujący strategię na danych historycznych może ufać, że te same sygnały wystąpią podczas tradingu na żywo. Zapewniają szybkość przetwarzania wymaganą dla użyteczności systemu. Zapewniają łatwość rozwoju i utrzymania kodu. Zapewniają jakość i niezawodność krytyczną dla platformy tradingowej.


Dodatkowe informacje przydatne do utworzenia planu zmian w kodzie - obecne działanie kodu:
W ramach data-collection przeliczenie wskaźnika wyzwalasz przez dodanie wariantu do sesji (POST /api/indicators/sessions/{session}/symbols/{symbol}/indicators). Serwis StreamingIndicatorEngine.add_indicator_to_session tworzy obiekt wskaźnika na podstawie wariantu (wczytanego z config/indicators/**), nadaje mu metadane (type, period, timeframe) i rejestruje w strukturach silnika (src/domain/services/streaming_indicator_engine.py:4683-4734).
Po rejestracji wskaźnik trafia do indeksu _indicators_by_symbol, co pozwala go znaleźć przy obsłudze nowych ticków (_track_indicator, src/domain/services/streaming_indicator_engine.py:1030-1053).
Dane wejściowe muszą nadal napływać do silnika (_on_market_data, src/domain/services/streaming_indicator_engine.py:1498-1784): moduł aktualizuje bufory cenowe/dealowe i dla każdej subskrypcji wywołuje _calculate_with_circuit_breaker, które z limitem czasu odpala właściwe obliczenie (np. SMA/EMA/RSI albo TWPA).
Wynik trafia do indicator.series i zostaje opublikowany na event-busie (_update_indicators_safe, src/domain/services/streaming_indicator_engine.py:1730-1790). Dopiero wtedy backend ma realne wartości, które frontend może odpytując /sessions/{session}/symbols/{symbol}/values zmapować do wskaźnika zgodnie z identyfikatorem.
W obecnej implementacji historia (/indicators/{indicator_id}/history) wciąż zwraca pustą listę, bo endpoint ma tymczasowy stub (src/api/indicators_routes.py:590-610). Dopóki nie zostanie podpięta persystencja/odczyt plików, frontend nie zobaczy wykresu historycznego, nawet jeśli obliczenia w tle działają.

