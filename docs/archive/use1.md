użytkwonik to ja
chce móc zbierać dane - gromadzic dane w plikach csv obecnie, żeby używac do backtestów

backtest powinien od razu wyliczyć wsystko na raz oraz wartosci wskaźników strategii użytych w backtestach, 
Backtest powinien dobrze symulować wszystko , bo jak wyliczamy to wszystko szybko to czas się skraca a tym samym i wartości wskaźników dlatego musi być to odpowiednio przeliczane 
po uruchomieniu i wytliczeniu, można wybrać strategię i przegladać wartosci wskaźników w czasie by zobaczyć jak zmieniają sie w stosunku do danych historycznych, by móc ocenić czy porpawnie są wyliczane, na tym wykresie w czasie też odnotowywane są sygnaly generowane przez strategię w danym momencie by zobaczyć co się dzieje
wykonuje się backtest i otrzymuję zestawienie dla strategii , w strategii mogę zobaczyć dla których symboli była najlepsza, zestawienie musi zawierać istotne informacje o ilości sygnałów, fałszywych, błędnych decyji, o wartościach parametrów jakie byly podczas podejmowania decyzji i błędnych decyzji, czy były emergency exit, jaki zysk, jakie straty itd. 
Per-Trade Breakdown z Wartościami Wskaźników - To mechanizm zapisywania pełnego kontekstu decyzyjnego w każdym kluczowym momencie życia trade'a. (zapisywania wartości wskaźników)




W trading live i paper robię to samo w zasadzie co backtest ustawiając strategię i symbole które będa analizowane za pomocą strategii, po zakończeniu sejsi mam podsumowanie

W zakładce wskaźniki dla już skonstruowanych wskaźników (zdefiniowanych w systemie) mogę je parametryzować zgodnie z ich właściwościami, przykładowo średnia ceny ttransakci może być liczona 1 wstecz do 15 min wstecz, i tak mogę zrobić swój wskaźnik średnia która podąża w oknie 1 godzina wstecz - 15 min wstecz, jeżeli inne wskaźniki mają parametry do ustawienia to mogę je tu sobie skonfigurować, 
może być wiele wskaźników przykładowo wiele średnich (będą miały swoje unikalne nazwy) 
na przykłąd stworzę średnią z ostatnich 15 min, albo średnia liczoną od 6 godzin wstecz do 2 godzin wstecz, - będą to warianty średniej - natomiast sam algorytm średniej jest zaimplementowany w backend tylko udostępnia parametry oraz opis żeby ustawić 
Jest wiele wskaźników które są zaprogramowane w backend i można tworzyć swoje warianty za pomocą parametrów. Mogą być też wskaźniki które nie posiadają opcji parametryzacji , wtedy będzie tylko jeden domyslny wariant. 

Wskaźniki można używać w strategiach , wskaźnikiem jest ryzyko, wszystko co liczy się na danych pochodzącychc z MEXC 

Domyślnie strategia na początk powinna być prosta w budowie 
alb musi pozwolić na wykrycie pamp (wtedy otwieramy lock na symbolu i żadna inna strategia nie może już nic robić w tym czasie), w trakie otwarcia (wykrycia) wyczliane są dodatkowe paramtry jak ryzyko, przewidywany moment na złożenie zlecenia - wartość po jakiej zlecenie zostanie złożone, oraz przewidywana cena wyjścia, cały czas jest to liczone, ryzko, inne wskaźniki które użytkownik użyje do określenia kiedy złożyć zlecenie i po jakiej wartości, gdzie take profit a gdzie stop loss, oraz cały czas liczone są wskaźniki do emergency exit , oraz zamknięcia sygnału jeżeli nie dojdzie do skutku i zostanie określony jako unieważniony (unieważnia sygnał odwołanie go, timeout określony przez użytkownika, emergency exit, wyjście stop loss, wyjście przez take profit) 

# strategy-builder


Strategie są zapisywane config/strategies/ jako json
Stretegy Builder ma dwie zakładki, jedną z listą wszystkich strategi odczytanyumi z plików config/strategies/ , w momencie wczytania strategie są validowane (czy poprawnie stworzona, czy warianty wskaźników użyte w strategii istnieją), jeżeli któraś ma bład to jest oznaczana jako błedna. Strategie można edytować, albo kopiować/klonować oraz usuwać za pomocą tej listy
W drugiej zakładce jest właściwy Builder gdzie się tworzy nowe strategie albo modyfikuje istniejące. 



## Builder

✅ 5-sekcyjna struktura strategii (S1/Z1/O1/ZE1,E1) - Bardzo jasna i logiczna
W strategii używane są jedynie warianty wskaźników odczytanych z config/indicators/

1
* Sygnał (S1) - użytkownik za pomoca wskaźników określa kiedy będzie można uznać że mamy sygnał wykrycia pump - czyli użytkownik ustali, ze wskaźnik W1 > 0.50 a wskaźnik R1 < 100, wskaźnik W2 między 0.2 a 0.8, jeżeli warunek spełniony to mamy wykrycie pump i dany symbol jest blokowany i zaczyna się liczenie innych wskaźników. Sygnał wykrycia jeżeli zostanie ustanowiony na danym Symbolu blokuje możliwość zrobienia tego samego innym strategiom. 
Jeżeli zostanie wykryty sygnal to zapisywane są wartości wskaźników użytych do wykrycia sygnału. 


2. Odwołanie sygnału (01) - Pozwala włączyć dwie opcje 
a) za pomocą warunków zdefiniowanych przez wskaźniki określamy czy sygnał zostanie odwołany (tylko w przypadku kiedy nie otwarto zlecenia). spełnienie jakiś warunkow na wskaźnikach na przykład R1 wzrasta > 150  AND  W10 < 0.1 wtedy odwołanie
b) timeout po jakim nastąpi odwołanie sygnału S1 
Obie opcje są opcjonalne i mogą działać równocześnie 
Możliwe jest też ustawienie cool down dla tej strategi po odwołaniu. Jest to opcjonalne.
Jeżeli włączone jest odwoływanie sygnalu za pomocą warunków to zapisywane są wartości wskaźników użytych do odwołania sygnału

3.
* Wykrycie momentu złożenia zlecenia (Z1) - za pomocą warunków zdefiniowanych przez wskaźniki określamy moment złożenia zlecenia (tylko gdy Sygnal (S1) jest aktywny dla danej strategii) I Na przykład gdy WE1 > 0.4 AND RZ < 40 wtedy za pomocą odpowiednich wskaźników (dedykowanych) do wyliczania ceny zlecenia CZ tworzymy zlecenie  (takich wskaźników będziemy mieli dużo) , użytkownik będzie decydował w Strategy Builder którego wskażnika CZ użyć (może nie wybierać wskaźnika do ceny zlecenia wtedy zlecenie będzie po każdej cenie), do tego do zlecenia będzie używany wskaźnik Stop Loss (ST) oraz Take Profit (TP), użytkownik wybiera który wskaźnik ST i TP użyć w danej strategi do skladania zlecenia (ST - jest w tym wypadku opcjonalne)
Wskaźniki typu "ryzyko" mogą służyc do Risk-adjusted sizing (większe ryzyko = mniejsza pozycja). czyli pomniejszania lub zwiększa wielkość zlecenia (Possition Size). O ile zostanie to ustawione w strategii. Wtedy określamy wartości brzegowe danego wskaźnika ryzyk czyli dla wartości ryzyka = 20 określamy procent wielkości pozycji otwarcia na przyklad 120% pozycji (czy to procentowej czy fixed), a jeżeli ryzyko będzie = 70 to Position Size zlecenia będzie 55% (pomniejszone), i przeliczamy dla wartości pośrednich , czyli określamy wartość i procent Position Size.
Jeżeli określimy że dla ryzyka = 20 mamy 120% , to nie skaluje sie niżej, że dla ryzyka = 10 mamy 150% ceny , tak samo dla ryzyka 90 nie skaluje się do np 35%, natomiast wartości pośredne są wyliczane liniowo, na przyklad ryzyko = 30 to wielkości pozycji zlecenia to około 105% itd, 
Jeżeli zlecenie zostanie zrealizowane (zawarte) to zapisywane są informacje o cenie zawarcia i wielkości, ryzyku, oraz innych wybranych parametrach, ta wartość jest używana przez wskaźniki wyliczania ceny zamknięcia (służą one jako wartość bazowa do określenia ceny zamknięcia pozycji)
Zapisywane są pozostałe wartości wskaźników użytych do wykrycia momentu złożenia zlecenia

4
* Wykrycie momentu zamknięcia zlecenia (ZE1) (realizacja zysku inaczej niż przez take profit, ale może działać równolegle do take profit) - za pomocą warunków zdefiniowanych przez wskaźniki określamy moment zamknięcia zlecenia (tylko gdy Sygnal (S1) jest aktywny) I Na przykład gdy WZ1 <= 0.6 oraz RZ > 80 wtedy za pomocą odpowiednich wskaźników (dedykowanych) do wyliczania ceny zamknięcia zlecenia  użytkownik będzie decydował w Strategy Builder którego wskażnika użyc do ceny zamknięcia zlecenia czy może po każdej cenie. 
Do wyznaczenia zamknięcia zlecenia można użyć wskaźnika wyliczajacego zamknięcie zlecenia (typ wyznaczajacy cenę zamknięcia zlecenia).
Można też użyć wskaźnika typu "ryzyko" by złożyć zlecenie po gorszej cenie (gdy dyże ryzyko) lub zlożyć zlecenie po lepszej cenie (gdy małe ryzyko). 
I można określić podonie że dla wskaźnika Ryzyko R1 gdy ryzyko 120 (definiowalne) wynosi to na przykład pogarszamy cenę na przykład o 5% (definiowalne), gdy ryzyko wynosi 30 (definiowalne) to polepszamy cenę zamknięcia zlecenia o na przykład 10% (definiowalne) od ceny wyliczonej przez wskaźnik wyliczania ceny zamknięcia. 
Jeżeli nastapi wykrycie momentu zamknięcia zlecenia to zapisywane są wartości wskaźników użytych do Wykrycie momentu zamknięcia zlecenia



5
* Emergency Exit (E1) - także określane warunkami za pomocą wskaźników , na przyklad jeżeli wskaźnik Ryzyko1 > 200 oraz WT1 < 0.01 to wykonywana jest operacja emergency exit, czyli jeżeli złożono zlecenie ale nie doszło jeszcze do skuktu to natychmiast anulowane jest, jeżeli zlecenie doszlo do skutku to natychmiast pozycja zamykana jest po cenie jaka jest oferowana, jeżeli nie zlożono zlecenia ale otwarty jest sygnał S1 to jest odwoływny i robiony jest cooldown liczony w minutach określony przez użytkownika w strategii - czas kiedy na danym symbolu dana strategia nie monitoruje
Cancel pending order (if not yet filled)
Close position at market (if order filled)
Jeżeli nastapi wykrycie Emergency Exit to zapisywane są wartości wskaźników użytych do Emergency Exit


Wszystkie warunki mają warunek "AND" (add condition) - obecnie usunąć warunki "OR" 
Operatory jakie można używać >=, >, <=, <
Każdy sygnal musi być logowany w systemie szczegółowo 

# /indicators
Warianty wskaźników zapisywane są w config/indicators/ w podziale na typy (ryzyko, stop loss, take profit, general, price, close order price ) jako json 
W zakładce "Indicator Varianst" jest tylko lista wariantów wskaźników odczytana z config/indicators/. Wskaźniki (warianty) są weryfikowane (validowane) podczas wczytywania listy czy są poprawnie skonfigurowane w stosunku do wskaźników systemowych (czy parametry mają odpowiednio zapisane zgodnie z wymaganiami danego wskaźnika systemowego). Wskaźniki można edytować, kopiować, lub usunąć, edycja powoduje zmianę definicji w pliku json odpowiedniego wariantu, usunięcie powoduje usunięcie pliku json danego wariantu. Skopiowanie wariantu wskaźnika powoduje utworzenie nowego pliku json. Każdy wariant wskaźnika dostaje swój unikalny identyfikator (niepowtarzalny), ktory będzie użyty w strategiach do wskazania danego wariantu. Używamy unikalnego identyfikatora w programie do identyfikacji wariantów wskaźników
W zakładce "Create Variant" znajduję się lista System Indicators  w podziale na typy (all types, general, risk, price, stop loss, take profit, close order)
Tu jest list wszystkich wskaźników systemowych (System Indicators) wraz z nazwą, opisem i opisem parametrów. 


tworznie wskaźników, użytkownik pownien widzieć wskaźniki systemowe wedlug kategorii 



Każdy sygnal musi być logowany w systemie szczegółowo 


Sugerowane wskaźniki 


Wskaźniki do wyznaczania ceny
**Dynamic position sizing (Kelly, Fixed Fractional, Optimal F)**


Cross-symbol emergency exit (wszystko spada = zamknij wszystko) (to na przyszlosć będzie do zrobienia)

Odpowiedzi backend mnie nie interesują, 



i móc utworzyć wariant, 




Są różne typy wskaźników 
Typ ogólny, typ ryzyko,  

typ cena zlecenia (cena po jakiej wykonane jest zlecenie do MEXC),   typ stop loss, typ take profit , cena zamknięcia zlecenia

do składania zleceia mozna użyć tylko typ: cena zlecenia , stop loss, take profit

cena zlecenia to po jakiej cenie będzie złożone zlecenie, stop lost wylicza wartość stop loss, take profit wylicza wartośc take profit do zlecenia 

do zamknięcia zlecenia (jeżeli będzie sygnal) można użyć wskaźnika wyliczajacego zamknięcie zlecenia 

Wszystkie te typy: cena zlecenia , cena zamknięcia zlecenia, stop loss, take profit należa do tej samem grupy wskaźnikow systemowych służacych tylko do ceny zlecenia, dla każdego z tych wskaźników można określić do czego może być używany (na przyklad do stop loss, take profit, ablbo cena zlecenia i cena zamkniecia zlecenia itd) 

Wskaźniki rysyko mogą służyc do Risk-adjusted sizing (większe ryzyko = mniejsza pozycja). czyli pomniejszania ceny zlecenia o ile zostanie to ustawione w strategii. Wtedy określamy wartości brzegowe danego wskaźnika ryzyk czyli dla wartości ryzyka = 20 określamy procent ceny otwarcia na przyklad 120% wyliczonej ceny, a jeżeli ryzyko będzie = 70 to cena zlecenia będzie 55% , i przeliczamy dla wartości pośrednich , czyli określamy wartość i procent ceny wyliczonej 
tylko jeżeli określimy że dla ryzyka = 20 mamy 120% , to nie skaluje sie niżej, że dla ryzyka = 10 mamy 150% ceny , tak samo dla ryzyka 90 nie skaluje się do np 35%, natomiast wartości pośredne są wyliczane liniowo, na przyklad ryzyko = 30 to procent ceny to około 105% itd, 
można dodać więcej ryzyk do Risk-adjusted sizing, albo żadnego wtedy zawsze 100% , musi być też wybrany wskaźnik do wyliczania ceny zlecenia (bo w przeciwnym razie po każdej cenie będzie zlecenie)


Typ ogólny, typ ryzyko wskażniki systemowe, używane są do wykrywania sygnałów - do określania warunkow sygnałów - na nich robi się warunki że jeżeli zostną spełnione to wykonywane są akcje . 

Dla każdego wskaźnika można stworzyć wariant o ile posiada parametry do konfiguracji, wtedy taki wariant (jego definicja) zapisywany jest jako json czy yaml , ważne żeby w definicji zapisany był identyfikator wskaźnika systemowego , bo każdy wskaźnik systemowy ma swój unikalny identyfikatorz



Dla każdej strategii określa się jaką kwota będzie używana do tworzenia zlecen, czy fixed, czy percent z całosci, i jaki lewar do transakcji. 



 Szczegółowy opis słowny
Scenariusz: Użytkownik tworzy swoją pierwszą strategię tradingową

Krok 1: Użytkownik przechodzi do listy strategii
Akcja użytkownika:

Użytkownik ma już utworzone 11 wskaźników (VWAP_15min, Risk_Fast, etc.)
Użytkownik ma zakończoną kolekcję danych DC_20250928_0900 (87,492 rekordów)
Użytkownik klika "Strategies" w menu nawigacyjnym
Przeglądarka ładuje stronę /strategies

Co dzieje się w tle:
Frontend wysyła request:
GET /api/v1/strategies
Backend odpowiada listą strategii użytkownika (może być pusta) oraz metadanymi.
Co widzi użytkownik:

Stronę z nagłówkiem "Strategies"
Sekcję "MY STRATEGIES (0)" - pusta lista
Przycisk "[+ Create New Strategy]" w prawym górnym rogu
Jeśli miałby jakieś strategie, widziałby je jako karty z:

Nazwą strategii
Statusem (Draft, Active, Tested)
Ostatnimi wynikami backtestów
Przyciskami [Edit] [Duplicate] [Delete]




Krok 2: Użytkownik klika Create New Strategy
Akcja użytkownika:

Użytkownik klika "[+ Create New Strategy]"

Co dzieje się w tle:

Frontend NIE robi API call
Frontend przekierowuje użytkownika na /strategies/new
Ładuje się nowa strona z formularzem strategii
Frontend robi API call po listę dostępnych wskaźników:

GET /api/v1/indicators/variants
Backend zwraca wszystkie warianty wskaźników użytkownika (te 11 które stworzył).
Co widzi użytkownik:

Stronę "Strategy Builder"
Na górze pole tekstowe: "Strategy Name: [___________]"
Pod spodem 4 duże sekcje:

"SECTION 1: SIGNAL DETECTION (S1)"
"SECTION 2: ORDER ENTRY (Z1)"
"SECTION 3: SIGNAL CANCELLATION (O1)"
"SECTION 4: EMERGENCY EXIT"


Każda sekcja jest zwinięta/rozwinięta (accordion)
Na dole przyciski: "[Validate Strategy]" "[Save Strategy]" "[Cancel]"


Krok 3: Użytkownik podaje nazwę strategii
Akcja użytkownika:

Użytkownik widzi pole "Strategy Name" na górze
Pole jest puste z placeholder tekst "Enter strategy name..."
Użytkownik klika w pole (focus)
Kursor miga w polu
Użytkownik zaczyna pisać na klawiaturze: "Q", "u", "i", "c", "k"...
Tekst pojawia się w polu w czasie rzeczywistym
Użytkownik kończy pisać: "Quick Pump v2"

Co dzieje się w tle:

Frontend przechowuje wartość lokalnie w React state
NIE robi żadnych API calls podczas pisania
Gdy użytkownik przestaje pisać na 500ms, frontend sprawdza czy nazwa jest unikalna:

GET /api/v1/strategies/check-name?name=Quick+Pump+v2
Backend sprawdza czy ta nazwa już istnieje i zwraca {"available": true} lub {"available": false}.
Co widzi użytkownik:

Tekst "Quick Pump v2" w polu
Po 500ms bez pisania, obok pola pojawia się:

Jeśli dostępna: zielony checkmark ✓ i tekst "Name available"
Jeśli zajęta: czerwony krzyżyk ✗ i tekst "Name already exists"




Krok 4: Użytkownik otwiera sekcję S1 (Signal Detection)
Akcja użytkownika:

Użytkownik widzi "SECTION 1: SIGNAL DETECTION (S1)" - sekcja jest domyślnie rozwinięta
Pod nagłówkiem widzi opis:

  "This section defines when to open a signal (lock symbol for further 
   analysis). All conditions must be TRUE simultaneously."

Widzi tekst "Conditions (AND logic):"
Pod spodem widzi przycisk "[+ Add Condition]"
Użytkownik klika "[+ Add Condition]"

Co dzieje się w tle:

Frontend NIE robi API call
Frontend dodaje nowy pusty komponent "Condition" do listy
Komponent renderuje się na ekranie

Co widzi użytkownik:

Pojawia się nowy blok z obramowaniem:

  ┌────────────────────────────────────────────┐
  │ Condition 1:                    [X] Remove │
  │ [Select indicator ▼] [▼] [_____]         │
  │ Description: (empty)                       │
  └────────────────────────────────────────────┘

Widzi trzy pola:

Dropdown "Select indicator"
Dropdown z operatorami (pusty na razie)
Pole tekstowe na wartość (puste)


W prawym górnym rogu widzi przycisk "[X] Remove"


Krok 5: Użytkownik wybiera pierwszy wskaźnik dla S1
Akcja użytkownika:

Użytkownik klika dropdown "[Select indicator ▼]"
Dropdown się rozwija

Co widzi użytkownik w dropdown:

Lista WSZYSTKICH jego wariantów wskaźników (11 sztuk)
Każdy wpis pokazuje:

Nazwę wskaźnika (np. "VWAP_15min")
Typ bazowy w nawiasie (np. "(VWAP)")
Krótki opis parametrów (np. "900s→0s")


Lista jest posortowana alfabetycznie
Lista pokazuje TYLKO wskaźniki typu "Ogólny" i "Ryzyko" (NIE pokazuje wskaźników typu "Cena zlecenia", "Stop Loss", "Take Profit")

Dostępne wskaźniki w dropdown:
VWAP_15min (VWAP) - 900s→0s
Risk_Fast (Risk Calculator) - fast mode, 60s window
Volume_Surge (Volume Surge Detector) - threshold 2.0
Entry_Signal (Entry Confidence) - sensitivity 0.8
Risk_Z (Risk Calculator) - 120s window
Risk1 (Risk Calculator) - 180s window
W10 (Window Indicator) - size 10
WT1 (Threshold Indicator) - 0.01
UWAGA: Wskaźniki CZ_VWAP, ST_ATR, TP_Percentage NIE są widoczne tutaj, bo są typu "Cena zlecenia/SL/TP" - te będą dostępne tylko w sekcji Z1.
Akcja użytkownika:

Użytkownik przewija dropdown
Użytkownik klika na "VWAP_15min"

Co dzieje się w ble:

Frontend zapisuje wybór lokalnie
Frontend automatycznie wypełnia pole "Description":

  "VWAP_15min: Volume Weighted Average Price calculated over 
   last 15 minutes (900s backwards from now). Returns 0.0-1.0."

NIE robi API call

Co widzi użytkownik:

Dropdown zamyka się
W dropdownie widzi teraz: "[VWAP_15min ▼]"
Pod spodem widzi wypełniony opis
Drugi dropdown (operator) staje się aktywny (niebieski, nie wyszarzony)


Krok 6: Użytkownik wybiera operator
Akcja użytkownika:

Użytkownik klika drugi dropdown (operator)
Dropdown rozwija się

Co widzi użytkownik:

5 opcji:

  > (greater than)
  < (less than)
  >= (greater than or equal)
  <= (less than or equal)
  == (equal)
Akcja użytkownika:

Użytkownik klika ">"

Co dzieje się w tle:

Frontend zapisuje wybór lokalnie
NIE robi API call

Co widzi użytkownik:

Dropdown zamyka się
W dropdownie widzi: "[> ▼]"
Trzecie pole (wartość) staje się aktywne


Krok 7: Użytkownik wpisuje wartość progową
Akcja użytkownika:

Użytkownik widzi trzecie pole tekstowe (aktywne, białe tło)
Użytkownik klika w pole
Kursor miga
Użytkownik wpisuje na klawiaturze: "0.50"

Co dzieje się w ble:

Frontend waliduje czy to liczba (pozwala tylko na cyfry i kropkę)
Zapisuje wartość lokalnie
NIE robi API call

Co widzi użytkownik:

W polu widzi: "0.50"
Opis pod kondycją aktualizuje się:

  "VWAP_15min must be greater than 0.50"

Cały blok kondycji wygląda teraz:

  ┌────────────────────────────────────────────┐
  │ Condition 1:                    [X] Remove │
  │ [VWAP_15min ▼] [> ▼] [0.50]              │
  │ Description: VWAP_15min must be > 0.50     │
  └────────────────────────────────────────────┘

Kondycja jest kompletna (wszystkie 3 pola wypełnione)


Krok 8: Użytkownik dodaje drugą kondycję S1
Akcja użytkownika:

Użytkownik klika ponownie "[+ Add Condition]" pod pierwszą kondycją

Co widzi użytkownik:

Pojawia się drugi blok:

  ┌────────────────────────────────────────────┐
  │ Condition 2:                    [X] Remove │
  │ [Select indicator ▼] [▼] [_____]         │
  │ Description: (empty)                       │
  └────────────────────────────────────────────┘
Akcja użytkownika:

Użytkownik powtarza kroki 5-7:

Klika dropdown wskaźnika
Wybiera "Risk_Fast"
Wybiera operator "<"
Wpisuje wartość "100"



Co widzi użytkownik po zakończeniu:

Dwie kondycje:

  ┌────────────────────────────────────────────┐
  │ Condition 1:                    [X] Remove │
  │ [VWAP_15min ▼] [> ▼] [0.50]              │
  │ Description: VWAP_15min must be > 0.50     │
  └────────────────────────────────────────────┘
  
  ┌────────────────────────────────────────────┐
  │ Condition 2:                    [X] Remove │
  │ [Risk_Fast ▼] [< ▼] [100]                │
  │ Description: Risk_Fast must be < 100       │
  └────────────────────────────────────────────┘

Krok 9: Użytkownik dodaje trzecią kondycję S1
Akcja użytkownika:

Użytkownik klika "[+ Add Condition]" ponownie
Powtarza proces dla trzeciej kondycji:

Wskaźnik: "Volume_Surge"
Operator: ">"
Wartość: "2.0"



Co widzi użytkownik:

Trzy kondycje w sekcji S1
Pod wszystkimi kondycjami widzi przycisk "[+ Add Condition]" - może dodać więcej jeśli chce
Nad kondycjami widzi informację: "All conditions must be TRUE simultaneously (AND logic)"


Krok 10: Użytkownik przechodzi do sekcji Z1 (Order Entry)
Akcja użytkownika:

Użytkownik przewija stronę w dół
Widzi "SECTION 2: ORDER ENTRY (Z1)"
Sekcja jest domyślnie zwinięta (collapsed)
Użytkownik klika nagłówek sekcji

Co dzieje się w ble:

Frontend tylko rozwija/zwija accordion
NIE robi API call

Co widzi użytkownik:

Sekcja rozwija się
Widzi opis:

  "This section defines when to actually place an order (after S1 is 
   triggered). Symbol is locked until order is placed or signal cancelled."

Widzi dwie podsekcje:

"Entry Conditions (AND logic):" z przyciskiem "[+ Add Condition]"
"Order Configuration:" z formularzem




Krok 11: Użytkownik dodaje kondycje entry
Akcja użytkownika:

W podsekcji "Entry Conditions", użytkownik klika "[+ Add Condition]"
Dodaje kondycję 1:

Wskaźnik: "Entry_Signal"
Operator: ">"
Wartość: "0.4"


Klika "[+ Add Condition]" ponownie
Dodaje kondycję 2:

Wskaźnik: "Risk_Z"
Operator: "<"
Wartość: "40"



Co widzi użytkownik:

Dwie kondycje entry w sekcji Z1
Te kondycje działają dokładnie tak samo jak w S1


Krok 12: Użytkownik konfiguruje cenę zlecenia
Akcja użytkownika:

Użytkownik przewija do podsekcji "Order Configuration"
Widzi pierwsze pole: "Price Calculation:"
Pod spodem widzi:

  Use indicator: [Select price indicator ▼]
  Description: (empty)

Użytkownik klika dropdown

Co widzi użytkownik w dropdown:

TYLKO wskaźniki typu "Cena zlecenia":

  CZ_VWAP (VWAP Price Calculator) - 300s→0s
  [może być więcej innych wskaźników typu "cena zlecenia"]

NIE widzi Risk_Fast, VWAP_15min, etc. - bo te nie są typu "Cena zlecenia"

Akcja użytkownika:

Użytkownik wybiera "CZ_VWAP"

Co widzi użytkownik:

Dropdown pokazuje: "[CZ_VWAP ▼]"
Opis aktualizuje się:

  "Order will be placed at price calculated by CZ_VWAP indicator"

Krok 13: Użytkownik konfiguruje Stop Loss
Akcja użytkownika:

Użytkownik widzi poniżej:

  Stop Loss (Optional):
  [☐] Enable Stop Loss

Użytkownik klika checkbox

Co dzieje się w ble:

Frontend pokazuje dodatkowe pola
NIE robi API call

Co widzi użytkownik:

Checkbox zmienia się na: [☑] Enable Stop Loss
Poniżej pojawiają się pola:

  Use indicator: [Select SL indicator ▼]
  Offset: [_____] % (negative = below entry)
Akcja użytkownika:

Użytkownik klika dropdown "Select SL indicator"

Co widzi użytkownik w dropdown:

TYLKO wskaźniki typu "Stop Loss":

  ST_ATR (ATR Stop Loss Calculator) - period 14, mult 2.0
  [inne wskaźniki typu SL jeśli są]
Akcja użytkownika:

Użytkownik wybiera "ST_ATR"
W polu "Offset" wpisuje: "-2.0"

Co widzi użytkownik:

Konfiguracja SL kompletna:

  [☑] Enable Stop Loss
  Use indicator: [ST_ATR ▼]
  Offset: [-2.0] %
  Description: Stop Loss will be placed at price from ST_ATR 
               minus 2.0%

Krok 14: Użytkownik konfiguruje Take Profit
Akcja użytkownika:

Użytkownik widzi poniżej:

  Take Profit:
  [☑] Enable Take Profit (required)

Checkbox jest już zaznaczony i disabled (nie można odznaczyć)
Poniżej widzi pola (już widoczne):

  Use indicator: [Select TP indicator ▼]
  Offset: [_____] % (positive = above entry)
Akcja użytkownika:

Klika dropdown "Select TP indicator"

Co widzi użytkownik w dropdown:

TYLKO wskaźniki typu "Take Profit":

  TP_Percentage (Percentage TP Calculator) - 1.5%
  [inne wskaźniki typu TP jeśli są]
Akcja użytkownika:

Wybiera "TP_Percentage"
W polu "Offset" wpisuje: "+1.5"

Co widzi użytkownik:

TP skonfigurowany:

  Use indicator: [TP_Percentage ▼]
  Offset: [+1.5] %
  Description: Take Profit at price from TP_Percentage plus 1.5%

Krok 15: Użytkownik konfiguruje wielkość pozycji
Akcja użytkownika:

Użytkownik widzi poniżej "Position Size:"
Widzi trzy radio buttony:

  ○ Fixed amount: [$_____]
  ● Percentage of balance: [____] %
  ○ Use indicator: [_____▼]

Domyślnie zaznaczony jest "Percentage of balance"
Użytkownik wpisuje w pole: "10"

Co widzi użytkownik:

Wartość "10" w polu
Pod polem widzi helper text:

  "(Max $100 per trade at $1000 balance)"

Frontend oblicza to lokalnie (10% z assumed $1000 balance)


Krok 16: Użytkownik przechodzi do sekcji O1 (Cancellation)
Akcja użytkownika:

Użytkownik przewija w dół
Widzi "SECTION 3: SIGNAL CANCELLATION (O1)"
Klika nagłówek żeby rozwinąć

Co widzi użytkownik:

Sekcja rozwija się
Widzi opis:

  "This section defines when to cancel a signal (unlock symbol) if 
   order was NOT yet placed. Either timeout OR conditions trigger."

Widzi dwie podsekcje:

"Timeout:"
"OR Custom Conditions:"




Krok 17: Użytkownik ustawia timeout
Akcja użytkownika:

W podsekcji "Timeout:" widzi:

  [☑] Enable timeout
  Cancel signal after: [____] seconds if order not placed

Checkbox już zaznaczony domyślnie
Użytkownik wpisuje w pole: "30"

Co widzi użytkownik:

Wartość "30" w polu
Timeout skonfigurowany


Krok 18: Użytkownik dodaje warunki odwołania
Akcja użytkownika:

W podsekcji "OR Custom Conditions:" użytkownik widzi:

  "Note: Conditions use OR logic - ANY true condition cancels signal"
  [+ Add Condition]

Użytkownik klika "[+ Add Condition]"
Dodaje kondycję 1:

Wskaźnik: "Risk1"
Operator: ">"
Wartość: "150"


Klika "[+ Add Condition]" ponownie
Dodaje kondycję 2:

Wskaźnik: "W10"
Operator: "<"
Wartość: "0.1"



Co widzi użytkownik:

Dwie kondycje odwołania
Nad kondycjami widzi info: "ANY true condition cancels signal (OR logic)"
WAŻNE: To jest OR logic, nie AND jak w S1/Z1


Krok 19: Użytkownik przechodzi do Emergency Exit
Akcja użytkownika:

Użytkownik przewija w dół
Widzi "SECTION 4: EMERGENCY EXIT"
Klika nagłówek żeby rozwinąć

Co widzi użytkownik:

Sekcja rozwija się
Widzi opis:

  "This section defines when to immediately exit position or cancel 
   pending orders. Highest priority - overrides everything."

Widzi:

"Emergency Conditions (any condition = emergency exit):"
"Post-Emergency Cooldown:"
"Emergency Actions:"




Krok 20: Użytkownik dodaje warunki emergency
Akcja użytkownika:

W "Emergency Conditions:" klika "[+ Add Condition]"
Dodaje kondycję 1:

Wskaźnik: "Risk1"
Operator: ">"
Wartość: "200"


Klika "[+ Add Condition]"
Dodaje kondycję 2:

Wskaźnik: "WT1"
Operator: "<"
Wartość: "0.01"



Co widzi użytkownik:

Dwie kondycje emergency
Używają OR logic (ANY = emergency)


Krok 21: Użytkownik ustawia cooldown
Akcja użytkownika:

W "Post-Emergency Cooldown:" widzi:

  After emergency exit, prevent this strategy from trading this 
  symbol for: [____] minutes

Użytkownik wpisuje: "5"

Co widzi użytkownik:

Wartość "5" w polu
Helper text:

  "Strategy will not monitor this symbol for 5 minutes after 
   emergency exit"

Krok 22: Użytkownik zaznacza akcje emergency
Co widzi użytkownik:

Pod cooldown widzi "Emergency Actions:":

  [☑] Cancel pending order (if not yet filled)
  [☑] Close position at market (if order filled)
  [☑] Log emergency event for analysis

Wszystkie checkboxy są domyślnie zaznaczone
Użytkownik ZOSTAWIA je zaznaczone (nie zmienia)


Krok 23: Użytkownik waliduje strategię
Akcja użytkownika:

Użytkownik przewija na dół strony
Widzi przyciski:

  [Validate Strategy] [Save Strategy] [Save & Run Backtest] [Cancel]

Użytkownik klika "[Validate Strategy]"

Co dzieje się w ble:
Frontend zbiera wszystkie dane z formularza i wysyła:
POST /api/v1/strategies/validate
Body: {cała konfiguracja strategii jako JSON}
Backend:

Sprawdza czy wszystkie wskaźniki istnieją
Sprawdza czy parametry są poprawne
Sprawdza czy nie ma circular dependencies
Sprawdza czy operatory są kompatybilne z typami wskaźników
Zwraca listę błędów/ostrzeżeń

Co widzi użytkownik:

Pojawia się modal "Strategy Validation Results"
W modalu widzi:

  Checking strategy "Quick Pump v2"...
  
  ✓ Structure validation
    • All required sections present
    • Signal Detection: 3 conditions configured
    • Order Entry: 2 conditions configured
    • Cancellation: timeout + 2 conditions
    • Emergency Exit: 2 conditions configured
  
  ✓ Indicator availability
    • VWAP_15min: configured, active
    • Risk_Fast: configured, active
    • Volume_Surge: configured, active
    • Entry_Signal: configured, active
    • Risk_Z: configured, active
    • CZ_VWAP: configured, active
    • ST_ATR: configured, active
    • TP_Percentage: configured, active
    • Risk1: configured, active
    • W10: configured, active
    • WT1: configured, active
  
  ⚠️  Warnings (strategy will work, but consider):
    • Risk_Z threshold (40) may be too high based on typical 
      values. Consider monitoring first.
  
  ✓ Logic validation
    • No circular dependencies
    • All operators compatible with indicator types
    • Take Profit configuration valid
  
  Strategy is valid and ready to use!
  
  [Close] [Save & Run Backtest]

Krok 24: Użytkownik zapisuje strategię
Akcja użytkownika:

Użytkownik w modalu klika "[Close]"
Modal zamyka się
Użytkownik jest z powrotem na stronie strategii
Użytkownik klika "[Save Strategy]" na dole strony

Co dzieje się w ble:
Frontend zapisuje strategię:
POST /api/v1/strategies
Body: {
  "name": "Quick Pump v2",
  "s1_signal": {
    "conditions": [
      {"indicator_id": "...", "operator": ">", "value": 0.50},
      {"indicator_id": "...", "operator": "<", "value": 100},
      {"indicator_id": "...", "operator": ">", "value": 2.0}
    ]
  },
  "z1_entry": {
    "conditions": [
      {"indicator_id": "...", "operator": ">", "value": 0.4},
      {"indicator_id": "...", "operator": "<", "value": 40}
    ],
    "price_indicator_id": "...",
    "stop_loss": {
      "enabled": true,
      "indicator_id": "...",
      "offset_percent": -2.0
    },
    "take_profit": {
      "enabled": true,
      "indicator_id": "...",
      "offset_percent": 1.5
    },
    "position_size": {
      "type": "percentage",
      "value": 10
    }
  },
  "o1_cancel": {
    "timeout_seconds": 30,
    "conditions": [
      {"indicator_id": "...", "operator": ">", "value": 150},
      {"indicator_id": "...", "operator": "<", "value": 0.1}
    ]
  },
  "emergency_exit": {
    "conditions": [
      {"indicator_id": "...", "operator": ">", "value": 200},
      {"indicator_id": "...", "operator": "<", "value": 0.01}
    ],
    "cooldown_minutes": 5,
    "actions": {
      "cancel_pending": true,
      "close_position": true,
      "log_event": true
    }
  }
}
Backend zapisuje strategię jako YAML lub JSON do pliku/bazy.
Co widzi użytkownik:

Przekierowanie na listę strategii /strategies
Toast notification: "✓ Strategy 'Quick Pump v2' saved successfully"
Na liście strategii widzi nową kartę:

  ┌──────────────────────────────────────────┐
  │ Quick Pump v2          [Edit] [Duplicate]│
  │ Status: ⚪ Draft (not tested)           │
  │ Created: 2025-09-29 21:30               │
  │ Indicators: 11 used                      │
  │ [Run Backtest] [Delete]                  │
  └──────────────────────────────────────────┘

To jest kompletny opis tworzenia strategii. Czy kontynuować z backtestingiem? Powinienem opisać też:

Dodawanie wariantów wskaźników (szczegółowo z typami)
Backtest (konfiguracja, wykonanie, wyniki, chart view)
Paper/Live Trading
Porównania


Oto szczegółowy opis każdego ekranu, funkcji i interakcji.

EKRAN 1: INDICATORS - Zarządzanie Wskaźnikami
1.1 Przegląd Ekranu
┌─────────────────────────────────────────────────────────────────────┐
│ Indicators                                          [+ New Indicator] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Search: [_________________] 🔍  Filter: [All Types ▼] [All Symbols ▼]│
│                                                                       │
│ MY INDICATORS (23)                                                    │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ VWAP_15min                                        [Edit] [Delete] ││
│ │ Base Type: VWAP | Symbol: BTC_USDT               [📊 Chart View] ││
│ │ Window: Last 15 minutes (900s backwards from now)                ││
│ │ Status: 🟢 Active | Last Value: 0.6734 | Updated: 2s ago        ││
│ │ Used in: Quick Pump v2, Steady Rider (2 strategies)             ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Risk_Fast                                         [Edit] [Delete] ││
│ │ Base Type: Risk Calculator | Symbol: ALL                         ││
│ │ Parameters: fast_mode=true, window=60s                           ││
│ │ Status: 🟢 Active | Last Value: 45.2 | Updated: 1s ago          ││
│ │ Used in: Quick Pump v2 (1 strategy)                             ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Entry_Signal                                      [Edit] [Delete] ││
│ │ Base Type: Entry Confidence | Symbol: BTC_USDT, ETH_USDT        ││
│ │ Parameters: sensitivity=0.8, lookback=300s                       ││
│ │ Status: 🟢 Active | Last Value: 0.42 | Updated: 3s ago          ││
│ │ Used in: Quick Pump v2, Flash Hunter (2 strategies)             ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ [Load More...] (20 more indicators)                                  │
│                                                                       │
│ SYSTEM INDICATORS (Read-only base types)                             │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ 📘 VWAP - Volume Weighted Average Price                          ││
│ │ Description: Calculates average price weighted by volume         ││
│ │ Parameters: window_start, window_end (seconds backwards)         ││
│ │ Returns: Float (0.0 - 1.0 normalized)                           ││
│ │ [Create Variant]                                                 ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ 📘 Risk Calculator - Real-time risk assessment                   ││
│ │ Description: Calculates position risk based on volatility        ││
│ │ Parameters: fast_mode (bool), window (seconds)                   ││
│ │ Returns: Float (0-200, higher = more risk)                       ││
│ │ [Create Variant]                                                 ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ [...] (50+ more system indicators)                                   │
└─────────────────────────────────────────────────────────────────────┘

lub 

2.1 Ekran: Lista Wskaźników┌──────────────────────────────────────────────────────────────┐
│ Indicator Management                    [+ Create Variant]   │
├──────────────────────────────────────────────────────────────┤
│ Filter: [All Types ▼] [All Symbols ▼] [Search___________]   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Base Indicators (built-in):                                 │
│ ├─ Price-based (4)                                          │
│ │  ├─ VWAP              [Create Variant]                   │
│ │  ├─ SMA               [Create Variant]                   │
│ │  ├─ EMA               [Create Variant]                   │
│ │  └─ Price_Velocity    [Create Variant]                   │
│ │                                                            │
│ ├─ Volume-based (3)                                         │
│ │  ├─ Volume_Surge_Ratio [Create Variant]                  │
│ │  ├─ Volume_MA          [Create Variant]                  │
│ │  └─ Smart_Money_Flow   [Create Variant]                  │
│ │                                                            │
│ └─ Composite (3)                                            │
│    ├─ Pump_Magnitude    [Create Variant]                   │
│    ├─ Risk_Score        [Create Variant]                   │
│    └─ Momentum_Index    [Create Variant]                   │
│                                                              │
│ My Custom Variants (12):                                    │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ Name              │Base   │Window    │Symbols│Used In │   │
│ ├───────────────────┼───────┼──────────┼───────┼────────┤   │
│ │ VWAP_5min_fast    │VWAP   │5min      │All    │3 strats│   │
│ │ VWAP_1h_slow      │VWAP   │1h        │All    │1 strat │   │
│ │ SMA_15min         │SMA    │15min     │All    │2 strats│   │
│ │ SMA_1h_to_15min   │SMA    │1h-15min  │BTC,ETH│1 strat │   │
│ │ Vol_Surge_Fast    │Vol_S  │1min/30min│All    │4 strats│   │
│ │ Risk_Conservative │Risk   │Custom    │All    │5 strats│   │
│ └────────────────────────────────────────────────────────┘   │
│                                                              │
│ Actions: [Edit] [Duplicate] [Test] [Delete]                 │
└──────────────────────────────────────────────────────────────┘

1.2 Tworzenie Nowego Wskaźnika



Kliknięcie [+ New Indicator] otwiera dialog:
┌─────────────────────────────────────────────────────────────────────┐
│ Create New Indicator                                     [X] Close   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Step 1: Select Base Type                                             │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Search base types: [_________________] 🔍                        ││
│ │                                                                   ││
│ │ Categories:                                                       ││
│ │ • Price-based (VWAP, TWPA, Price_Velocity, ...)                 ││
│ │ • Volume-based (Volume_Surge, Volume_Concentration, ...)         ││
│ │ • Risk (Risk_Fast, Risk_Z, Confidence_Score, ...)               ││
│ │ • Entry/Exit (Entry_Signal, Exit_Signal, ...)                   ││
│ │ • Technical (RSI, MACD, Bollinger, ...)                          ││
│ │                                                                   ││
│ │ Selected: [VWAP ▼]                                               ││
│ │                                                                   ││
│ │ Description:                                                      ││
│ │ Volume Weighted Average Price - calculates price weighted by     ││
│ │ trading volume over specified time window. Returns normalized    ││
│ │ value 0.0-1.0 where 1.0 means current price is at VWAP.         ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 2: Name Your Indicator                                          │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Name: [VWAP_15min_____________________]                          ││
│ │ ⚠️  This name will be used in strategies                         ││
│ │ ✓  Name is unique                                                ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 3: Configure Parameters                                         │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Symbols:                                                          ││
│ │ ○ Specific symbols                                               ││
│ │   [☑ BTC_USDT] [☐ ETH_USDT] [☐ ADA_USDT] [Show all...]         ││
│ │ ● All symbols (applies to any symbol used in strategies)        ││
│ │                                                                   ││
│ │ Time Window:                                                      ││
│ │ Window Start: [900] seconds backwards (15 minutes ago)           ││
│ │ Window End:   [0__] seconds backwards (now)                      ││
│ │                                                                   ││
│ │ Visual: [====900s=====>NOW]                                      ││
│ │         "From 15 minutes ago to current moment"                  ││
│ │                                                                   ││
│ │ Advanced Options: [▼ Show]                                       ││
│ │ ┌────────────────────────────────────────────────────────────┐  ││
│ │ │ Update Frequency:                                           │  ││
│ │ │ ○ Real-time (every new trade)                              │  ││
│ │ │ ● Interval: [5] seconds                                     │  ││
│ │ │ ○ On-demand only                                            │  ││
│ │ │                                                              │  ││
│ │ │ Caching:                                                     │  ││
│ │ │ [☑] Enable caching (60s buckets)                           │  ││
│ │ │ Cache key includes timestamp bucket for time-based accuracy │  ││
│ │ │                                                              │  ││
│ │ │ Data Quality:                                                │  ││
│ │ │ [☑] Enable anomaly detection                               │  ││
│ │ │ [☑] Log outliers (don't reject exchange data)              │  ││
│ │ │ Minimum data points: [10]                                   │  ││
│ │ └────────────────────────────────────────────────────────────┘  ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 4: Test Configuration                                           │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ [Test with Live Data]                                            ││
│ │                                                                   ││
│ │ Test Results:                                                     ││
│ │ Symbol: BTC_USDT                                                 ││
│ │ Current Value: 0.6734                                            ││
│ │ Data Points Used: 87                                             ││
│ │ Calculation Time: 12ms                                           ││
│ │ Status: ✓ Working correctly                                      ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│                            [Cancel] [Create Indicator]                │
└─────────────────────────────────────────────────────────────────────┘
1.3 Edycja Istniejącego Wskaźnika
Kliknięcie [Edit] przy wskaźniku otwiera ten sam dialog, ale:

Nazwa jest tylko do odczytu (nie można zmienić nazwy już używanego wskaźnika)
Pokazuje ostrzeżenie jeśli wskaźnik jest używany w strategiach:

⚠️  Warning: This indicator is used in 2 strategies:
   • Quick Pump v2
   • Steady Rider
   
   Changes will affect these strategies. Consider creating a new
   variant instead of modifying this one.
   
   [Cancel] [Create New Variant Instead] [Save Changes Anyway]
1.4 Chart View - Podgląd Wskaźnika na Wykresie
Kliknięcie [📊 Chart View] otwiera pełnoekranowy widok:
┌─────────────────────────────────────────────────────────────────────┐
│ Indicator Chart View: VWAP_15min                         [X] Close   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Symbol: [BTC_USDT ▼]  Time Range: [Last 6 Hours ▼]  [◀ ▶] [Refresh]│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │                                                                   ││
│ │  1.0 ┤                                                            ││
│ │      │        ╱╲                    ╱╲                           ││
│ │  0.8 ┤       ╱  ╲                  ╱  ╲                          ││
│ │      │      ╱    ╲    ╱╲          ╱    ╲                         ││
│ │  0.6 ┤─────╱──────╲──╱──╲────────╱──────╲─────── VWAP_15min     ││
│ │      │              ╲╱    ╲      ╱                               ││
│ │  0.4 ┤                     ╲    ╱                                ││
│ │      │                      ╲  ╱                                 ││
│ │  0.2 ┤                       ╲╱                                  ││
│ │      │                                                            ││
│ │  0.0 ┤────────────────────────────────────────────────────────   ││
│ │      12:00  13:00  14:00  15:00  16:00  17:00  18:00           ││
│ │                                                                   ││
│ │  Price (BTC_USDT):                                               ││
│ │ 44000┤      ___                                                  ││
│ │      │     /   \___                                              ││
│ │ 43500┤____/        \___                                          ││
│ │      │                 \___                                      ││
│ │ 43000┤                     \___                                  ││
│ │      12:00  13:00  14:00  15:00  16:00  17:00  18:00           ││
│ │                                                                   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Live Values (updated every 5s):                                      │
│ Current: 0.6734 | Min: 0.1245 (14:23) | Max: 0.9823 (16:45)        │
│ Average: 0.5821 | StdDev: 0.1234                                    │
│                                                                       │
│ Hover over chart to see exact values at any time point.              │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
Interakcje:

Hover nad wykresem pokazuje tooltip z dokładną wartością i timestampem
Można zoomować (scroll) i przesuwać (drag)
Przełączanie symbolu pokazuje ten sam wskaźnik dla innego symbolu
Refresh pobiera najnowsze dane


EKRAN 2: STRATEGY BUILDER - Tworzenie Strategii
2.1 Lista Strategii
┌─────────────────────────────────────────────────────────────────────┐
│ Strategies                                    [+ Create New Strategy] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Search: [_________________] 🔍  Filter: [All Status ▼]               │
│                                                                       │
│ MY STRATEGIES (5)                                                     │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Quick Pump v2                                 [Edit] [Duplicate]  ││
│ │ Status: 🟢 Active (running in Paper Trading)                     ││
│ │ Performance: +12.7% (8 signals, 62.5% success)                   ││
│ │ Symbols: BTC_USDT, ETH_USDT                                      ││
│ │ Last Modified: 2025-09-29 15:20                                  ││
│ │ [View Backtest Results] [Stop Trading] [Settings]               ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Flash Hunter                                  [Edit] [Duplicate]  ││
│ │ Status: ⚪ Draft (not tested)                                    ││
│ │ Performance: N/A                                                  ││
│ │ Symbols: BTC_USDT                                                ││
│ │ Last Modified: 2025-09-28 10:15                                  ││
│ │ [Run Backtest] [Delete]                                          ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ [...more strategies...]                                               │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
2.2 Tworzenie/Edycja Strategii - Pełny Formularz
Kliknięcie [+ Create New Strategy] lub [Edit] otwiera edytor:
┌─────────────────────────────────────────────────────────────────────┐
│ Strategy Builder: [Quick Pump v2_____________________] [Save] [Cancel]│
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ 🎯 SECTION 1: SIGNAL DETECTION (S1)                                  │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ This section defines when to open a "signal" (lock symbol for        │
│ further analysis). All conditions must be TRUE simultaneously.        │
│                                                                       │
│ Conditions (AND logic):                                               │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Condition 1:                                          [X] Remove  ││
│ │ [VWAP_15min     ▼] [>  ▼] [0.50___]                             ││
│ │ Available indicators: [Show all 23 indicators ▼]                 ││
│ │ Description: Current VWAP must be above 0.50                     ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Condition 2:                                          [X] Remove  ││
│ │ [Risk_Fast      ▼] [<  ▼] [100___]                              ││
│ │ Description: Fast risk assessment must be below 100              ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Condition 3:                                          [X] Remove  ││
│ │ [Volume_Surge   ▼] [>  ▼] [2.0___]                              ││
│ │ Description: Volume surge must be above 2x normal                ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ [+ Add Condition]                                                     │
│                                                                       │
│ Operator dropdown zawiera: [>, <, >=, <=, ==]                        │
│ Indicator dropdown pokazuje TYLKO Twoje skonfigurowane wskaźniki     │
│ z ekranu Indicators (nie system indicators, tylko Twoje warianty)    │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ 💰 SECTION 2: ORDER ENTRY (Z1)                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ This section defines when to actually place an order (after S1 is    │
│ triggered). Symbol is locked until order is placed or signal          │
│ cancelled.                                                            │
│                                                                       │
│ Entry Conditions (AND logic):                                         │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Condition 1:                                          [X] Remove  ││
│ │ [Entry_Signal   ▼] [>  ▼] [0.4___]                              ││
│ │ Description: Entry confidence must exceed 0.4                    ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Condition 2:                                          [X] Remove  ││
│ │ [Risk_Z         ▼] [<  ▼] [40___]                               ││
│ │ Description: Entry-specific risk must be below 40                ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ [+ Add Condition]                                                     │
│                                                                       │
│ Order Configuration:                                                  │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Price Calculation:                                                ││
│ │ Use indicator: [CZ_VWAP        ▼]                                ││
│ │ Description: Use this indicator's value as order price           ││
│ │                                                                   ││
│ │ Stop Loss (Optional):                                            ││
│ │ [☑] Enable Stop Loss                                            ││
│ │ Use indicator: [ST_ATR         ▼]                                ││
│ │ Offset:        [-2.0___] % (negative = below entry)             ││
│ │ Description: Place SL at price calculated by ST_ATR minus 2%     ││
│ │                                                                   ││
│ │ Take Profit:                                                      ││
│ │ [☑] Enable Take Profit (required)                               ││
│ │ Use indicator: [TP_Percentage  ▼]                                ││
│ │ Offset:        [+1.5___] % (positive = above entry)             ││
│ │ Description: Place TP at price calculated by indicator plus 1.5% ││
│ │                                                                   ││
│ │ Position Size:                                                    ││
│ │ ○ Fixed amount: [$___100.00___]                                 ││
│ │ ● Percentage of balance: [10___] %                              ││
│ │ ○ Use indicator: [________▼]                                    ││
│ │                                                                   ││
│ │ Max Slippage:                                                     ││
│ │ [0.5___] % (reject order if price moves more than this)         ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ ❌ SECTION 3: SIGNAL CANCELLATION (O1)                               │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ This section defines when to cancel a signal (unlock symbol) if      │
│ order was NOT yet placed. Either timeout OR conditions trigger.       │
│                                                                       │
│ Timeout:                                                              │
│ [☑] Enable timeout                                                   │
│ Cancel signal after: [30___] seconds if order not placed             │
│                                                                       │
│ OR Custom Conditions (any condition = cancel):                        │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Condition 1:                                          [X] Remove  ││
│ │ [Risk1          ▼] [>  ▼] [150___]                              ││
│ │ Description: Risk spikes above 150                               ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Condition 2:                                          [X] Remove  ││
│ │ [W10            ▼] [<  ▼] [0.1___]                               ││
│ │ Description: Window indicator drops below 0.1                    ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ [+ Add Condition]                                                     │
│                                                                       │
│ Note: Conditions use OR logic - ANY true condition cancels signal    │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ 🚨 SECTION 4: EMERGENCY EXIT                                         │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ This section defines when to immediately exit position or cancel      │
│ pending orders. Highest priority - overrides everything.              │
│                                                                       │
│ Emergency Conditions (any condition = emergency exit):                │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Condition 1:                                          [X] Remove  ││
│ │ [Risk1          ▼] [>  ▼] [200___]                              ││
│ │ Description: Extreme risk detected                               ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Condition 2:                                          [X] Remove  ││
│ │ [WT1            ▼] [<  ▼] [0.01___]                              ││
│ │ Description: Critical threshold breached                         ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ [+ Add Condition]                                                     │
│                                                                       │
│ Post-Emergency Cooldown:                                              │
│ After emergency exit, prevent this strategy from trading this symbol  │
│ for: [5___] minutes                                                   │
│                                                                       │
│ Emergency Actions:                                                    │
│ [☑] Cancel pending order (if not yet filled)                        │
│ [☑] Close position at market (if order filled)                      │
│ [☑] Log emergency event for analysis                                │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ [Validate Strategy] [Save Strategy] [Save & Run Backtest] [Cancel]   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
2.3 Walidacja Strategii
Kliknięcie [Validate Strategy] uruchamia sprawdzenie:
┌─────────────────────────────────────────────────────────────────────┐
│ Strategy Validation Results                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Checking strategy "Quick Pump v2"...                                 │
│                                                                       │
│ ✓ Structure validation                                               │
│   • All required sections present                                    │
│   • Signal Detection: 3 conditions configured                        │
│   • Order Entry: 2 conditions configured                             │
│   • Cancellation: timeout + 2 conditions                             │
│   • Emergency Exit: 2 conditions configured                          │
│                                                                       │
│ ✓ Indicator availability                                             │
│   • VWAP_15min: configured, active                                   │
│   • Risk_Fast: configured, active                                    │
│   • Volume_Surge: configured, active                                 │
│   • Entry_Signal: configured, active                                 │
│   • Risk_Z: configured, active                                       │
│   • CZ_VWAP: configured, active                                      │
│   • ST_ATR: configured, active                                       │
│   • TP_Percentage: configured, active                                │
│   • Risk1: configured, active                                        │
│   • W10: configured, active                                          │
│   • WT1: configured, active                                          │
│                                                                       │
│ ⚠️  Warnings (strategy will work, but consider):                     │
│   • Risk_Z threshold (40) may be too high - 2 emergency exits in     │
│     last backtest. Consider lowering to 35.                          │
│   • Stop Loss is optional but recommended for risk management        │
│                                                                       │
│ ✓ Logic validation                                                   │
│   • No circular dependencies                                         │
│   • All operators compatible with indicator types                    │
│   • Take Profit configuration valid                                  │
│                                                                       │
│ ✓ Parameter ranges                                                   │
│   • All numeric values within acceptable ranges                      │
│   • Cooldown period (5 min) reasonable                               │
│                                                                       │
│ Strategy is valid and ready to use!                                  │
│                                                                       │
│                                    [Close] [Save & Run Backtest]     │
└─────────────────────────────────────────────────────────────────────┘

EKRAN 3: DATA COLLECTION - Zbieranie Danych
(Tu pozostaje bez zmian z poprzedniej wersji, ale dodam szczegóły)
EKRAN 3: DATA COLLECTION - Zbieranie Danych (dokończenie)
┌─────────────────────────────────────────────────────────────────────┐
│ Data Collection                                  [+ Start Collection] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Filter: [All Status ▼] [All Symbols ▼] Sort: [Newest First ▼]      │
│                                                                       │
│ ACTIVE COLLECTIONS (1)                                                │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ DC_20250929_1430                                   [Stop] [Details]││
│ │ Symbols: BTC_USDT, ETH_USDT                                      ││
│ │ Started: 2025-09-29 14:30:15                                     ││
│ │ Duration: 6h 15m / 24h                                           ││
│ │ Progress: ████████████░░░░░░ 60%                                ││
│ │ Records: 45,231 (ETA: 8h 45m remaining)                         ││
│ │ Rate: ~2.1 records/sec                                           ││
│ │ Storage: data/DC_20250929_1430/                                 ││
│ │   • BTC_USDT.csv (23,145 records, 4.2 MB)                       ││
│ │   • ETH_USDT.csv (22,086 records, 3.8 MB)                       ││
│ │ Last Update: 2 seconds ago                                       ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ COMPLETED COLLECTIONS (12)                                            │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ DC_20250928_0900                         [Use in Backtest] [Delete]││
│ │ Symbols: BTC_USDT, ETH_USDT, ADA_USDT                           ││
│ │ Collected: 2025-09-28 09:00 → 2025-09-29 09:00 (24h)           ││
│ │ Records: 87,492 total                                            ││
│ │ Storage: data/DC_20250928_0900/ (15.6 MB)                       ││
│ │   • BTC_USDT.csv (29,164 records, 5.2 MB)                       ││
│ │   • ETH_USDT.csv (28,905 records, 5.1 MB)                       ││
│ │   • ADA_USDT.csv (29,423 records, 5.3 MB)                       ││
│ │ Quality: ✓ No gaps, ✓ No anomalies                             ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ DC_20250927_1500                         [Use in Backtest] [Delete]││
│ │ Symbols: BTC_USDT                                                ││
│ │ Collected: 2025-09-27 15:00 → 2025-09-27 21:00 (6h)            ││
│ │ Records: 21,745 total                                            ││
│ │ Storage: data/DC_20250927_1500/ (3.9 MB)                        ││
│ │   • BTC_USDT.csv (21,745 records, 3.9 MB)                       ││
│ │ Quality: ⚠️  3 small gaps (max 12s), ✓ No anomalies            ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ [...10 more collections...]                                           │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
3.1 Start Collection Dialog
Kliknięcie [+ Start Collection]:
┌─────────────────────────────────────────────────────────────────────┐
│ Start Data Collection                                    [X] Close   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Step 1: Select Symbols                                               │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ [☑ BTC_USDT]  [☑ ETH_USDT]  [☐ ADA_USDT]                        ││
│ │ [☐ SOL_USDT]  [☐ DOT_USDT]  [☐ LINK_USDT]                       ││
│ │ [Show all 50+ symbols...]                                         ││
│ │                                                                   ││
│ │ [☑] Select All  [☐] Deselect All                                ││
│ │                                                                   ││
│ │ Selected: 2 symbols                                              ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 2: Duration                                                      │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ ○ Fixed duration:                                                ││
│ │   Value: [24___] Unit: [Hours ▼]                                ││
│ │   (Options: Seconds, Minutes, Hours, Days)                       ││
│ │                                                                   ││
│ │ ● Continuous collection                                          ││
│ │   Will run until manually stopped                                ││
│ │   ⚠️  Monitor disk space regularly                               ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 3: Storage                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Storage Path: [data/___________________________]                 ││
│ │ Session ID will be auto-generated: DC_YYYYMMDD_HHMM             ││
│ │                                                                   ││
│ │ Estimated size (24h):                                            ││
│ │ • BTC_USDT: ~5 MB                                                ││
│ │ • ETH_USDT: ~5 MB                                                ││
│ │ Total: ~10 MB                                                    ││
│ │                                                                   ││
│ │ Available disk space: 234 GB                                     ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 4: Data Quality Options                                         │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ [☑] Log data quality metrics                                     ││
│ │ [☑] Detect and log anomalies (don't reject exchange data)       ││
│ │ [☑] Record connection status                                     ││
│ │ [☑] Auto-retry on connection loss (max 3 attempts)              ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Summary:                                                              │
│ • Collecting 2 symbols (BTC_USDT, ETH_USDT)                         │
│ • Duration: 24 hours                                                  │
│ • Estimated records: ~86,000                                          │
│ • Estimated size: ~10 MB                                              │
│ • Storage: data/DC_20250929_1825/                                    │
│                                                                       │
│                                    [Cancel] [Start Collection]        │
└─────────────────────────────────────────────────────────────────────┘
3.2 Collection Details View
Kliknięcie [Details] przy aktywnej kolekcji:
┌─────────────────────────────────────────────────────────────────────┐
│ Collection Details: DC_20250929_1430               [Stop] [X] Close  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Status: 🟢 Active                                                    │
│ Started: 2025-09-29 14:30:15                                         │
│ Running: 6h 15m / 24h (26% complete)                                 │
│ ETA Completion: 2025-09-30 14:30:15 (in 17h 45m)                    │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ Real-time Statistics:                                                 │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Symbol    │ Records │ Rate/sec │ Last Update │ File Size │ Status││
│ ├───────────┼─────────┼──────────┼─────────────┼───────────┼───────┤│
│ │ BTC_USDT  │ 23,145  │ 1.05     │ 1s ago      │ 4.2 MB    │ 🟢   ││
│ │ ETH_USDT  │ 22,086  │ 1.02     │ 2s ago      │ 3.8 MB    │ 🟢   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Connection Health:                                                    │
│ • WebSocket: Connected (uptime 99.8%)                                │
│ • Data feed: Normal (avg latency 45ms)                               │
│ • Reconnections: 1 (auto-recovered in 3s)                            │
│                                                                       │
│ Data Quality:                                                         │
│ • Gaps detected: 0                                                    │
│ • Anomalies logged: 2 (within normal range)                          │
│ • Data completeness: 99.97%                                           │
│                                                                       │
│ Storage:                                                              │
│ Path: data/DC_20250929_1430/                                         │
│ Total size: 8.0 MB                                                    │
│ Disk space remaining: 234 GB                                          │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ Recent Events Log:                                                    │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ 18:42:15 | BTC_USDT | Anomaly detected: price spike +0.8%       ││
│ │ 18:35:22 | Connection | Reconnected after 3s disconnect          ││
│ │ 18:35:19 | Connection | WebSocket disconnected                   ││
│ │ 18:12:03 | ETH_USDT | Anomaly detected: volume surge 3.2x       ││
│ │ 17:45:30 | System | 25% progress checkpoint reached             ││
│ │ [Show all logs...]                                                ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Actions:                                                              │
│ [Stop Collection Now] [Download Current Data] [View Raw CSV]         │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

EKRAN 4: BACKTESTING - Testowanie Strategii
4.1 Konfiguracja Backtestu
┌─────────────────────────────────────────────────────────────────────┐
│ Backtesting                                     [+ New Backtest Run]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ CONFIGURE BACKTEST                                                    │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ Step 1: Select Data Source                                           │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Data Collection: [DC_20250928_0900 ▼]                           ││
│ │                                                                   ││
│ │ Details:                                                          ││
│ │ • Time Range: 2025-09-28 09:00 → 2025-09-29 09:00 (24h)        ││
│ │ • Available Symbols: BTC_USDT, ETH_USDT, ADA_USDT               ││
│ │ • Total Records: 87,492                                          ││
│ │ • Quality: ✓ Complete (no gaps)                                 ││
│ │                                                                   ││
│ │ [Browse All Collections...]                                       ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 2: Select Symbols                                               │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Test on: (based on data source availability)                     ││
│ │ [☑ BTC_USDT] - 29,164 records available                         ││
│ │ [☑ ETH_USDT] - 28,905 records available                         ││
│ │ [☐ ADA_USDT] - 29,423 records available                         ││
│ │                                                                   ││
│ │ Selected: 2 symbols                                              ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 3: Select Strategies                                            │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Test these strategies: (select 1 or more for comparison)         ││
│ │                                                                   ││
│ │ [☑] Quick Pump v2                                                ││
│ │     Last backtest: +12.7% (8 signals, 62.5% success)            ││
│ │     Uses indicators: VWAP_15min, Risk_Fast, Volume_Surge, ...   ││
│ │                                                                   ││
│ │ [☐] Flash Hunter                                                 ││
│ │     Not tested yet                                                ││
│ │     Uses indicators: Entry_Signal, Risk_Z, ...                   ││
│ │                                                                   ││
│ │ [☐] Steady Rider                                                 ││
│ │     Last backtest: +8.3% (12 signals, 75% success)              ││
│ │     Uses indicators: VWAP_30min, Volume_Surge, ...              ││
│ │                                                                   ││
│ │ Selected: 1 strategy                                             ││
│ │ ⚠️  For comparison, select 2+ strategies                         ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 4: Execution Settings                                           │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Speed Multiplier:                                                 ││
│ │ [10x___▼] (Options: 1x, 5x, 10x, 50x, 100x, MAX)               ││
│ │                                                                   ││
│ │ ℹ️  Speed affects:                                                ││
│ │ • Data replay rate (10x = 24h data in 2.4h)                     ││
│ │ • Indicator timing adjustments (windows scaled accordingly)      ││
│ │ • Real-time simulation accuracy                                  ││
│ │                                                                   ││
│ │ Estimated runtime: ~2.4 hours                                    ││
│ │                                                                   ││
│ │ Initial Budget:                                                   ││
│ │ [$1000.00______]                                                 ││
│ │                                                                   ││
│ │ Transaction Costs:                                                ││
│ │ [☑] Include fees (0.1% per trade)                               ││
│ │ [☑] Include slippage (realistic market impact)                  ││
│ │                                                                   ││
│ │ Risk Management:                                                  ││
│ │ [☑] Enforce max position size limits                            ││
│ │ [☑] Enforce stop-loss rules                                     ││
│ │ [☑] Track drawdown limits                                       ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 5: Analysis Options                                             │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ [☑] Record all indicator values at decision points               ││
│ │     (Required for detailed analysis and chart view)              ││
│ │                                                                   ││
│ │ [☑] Log all signals (successful and false positives)            ││
│ │ [☑] Calculate Sharpe/Sortino/Calmar ratios                      ││
│ │ [☑] Track max drawdown and recovery times                       ││
│ │ [☑] Generate trade-by-trade breakdown                           ││
│ │                                                                   ││
│ │ ⚠️  More analysis = longer processing time                       ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Summary:                                                              │
│ • Data: DC_20250928_0900 (24h, 87k records)                         │
│ • Symbols: BTC_USDT, ETH_USDT                                        │
│ • Strategies: Quick Pump v2                                          │
│ • Speed: 10x (est. 2.4h runtime)                                     │
│ • Budget: $1,000.00                                                   │
│                                                                       │
│                             [Cancel] [Start Backtest] [Save Config]  │
└─────────────────────────────────────────────────────────────────────┘
4.2 Backtest Execution - Live Progress
Po kliknięciu [Start Backtest], system przechodzi do widoku wykonania:
┌─────────────────────────────────────────────────────────────────────┐
│ Backtest Running: BT_20250929_1845                      [Abort Run]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Strategy: Quick Pump v2                                              │
│ Data: DC_20250928_0900 (24h)                                        │
│ Speed: 10x                                                            │
│                                                                       │
│ Progress: ████████████████░░░░ 78% Complete                         │
│ Elapsed: 1h 52m / Est. Total: 2h 24m                                │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ Current Virtual Time: 2025-09-29 06:45:23 (18h into 24h data)       │
│ Processing Rate: 12.8 records/sec                                    │
│                                                                       │
│ Live Performance:                                                     │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Current Balance: $1,127.50 (+12.75%)                             ││
│ │ Peak Balance: $1,145.20 (at 15:23 virtual time)                 ││
│ │ Max Drawdown: -3.4% (from peak)                                  ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Signals & Trades:                                                     │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Total Signals: 8                                                  ││
│ │ Orders Placed: 6                                                  ││
│ │ Completed Trades: 5 (3 profit, 2 loss)                          ││
│ │ Active Positions: 1 (BTC_USDT, +$12.30 unrealized)              ││
│ │ Cancelled Signals: 2 (timeout/conditions)                        ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Recent Activity:                                                      │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ 06:45:12 | BTC_USDT | Position opened at $43,250                ││
│ │ 06:42:35 | BTC_USDT | S1 triggered (VWAP=0.67, Risk=45)         ││
│ │ 05:23:18 | ETH_USDT | Trade closed: +$45.00 (TP hit)            ││
│ │ 05:18:45 | ETH_USDT | Position opened at $3,125                 ││
│ │ 05:15:22 | ETH_USDT | S1 triggered (VWAP=0.52, Risk=89)         ││
│ │ [View full log...]                                                ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ System Status:                                                        │
│ CPU: 45% | Memory: 1.2 GB | Indicators Calculated: 45,231           │
│                                                                       │
│ Note: You can close this window - backtest will continue in          │
│ background. Check "Backtest History" for results when complete.      │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
4.3 Backtest Results - Główny Przegląd
Po zakończeniu backtestu (lub kliknięciu na ukończony test):
┌─────────────────────────────────────────────────────────────────────┐
│ Backtest Results: BT_20250929_1845                   [Export] [Share]│
│ Strategy: Quick Pump v2 | Data: DC_20250928_0900 (24h)              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ OVERALL PERFORMANCE                                                   │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Final Balance: $1,127.50        Return: +12.75%        ✓ PROFIT │ │
│ │ Total Signals: 8                Win Rate: 62.5% (5/8)            │ │
│ │ Sharpe Ratio: 1.82              Sortino Ratio: 2.14             │ │
│ │ Max Drawdown: -3.4%             Calmar Ratio: 3.75              │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ Navigation:                                                           │
│ [📊 Chart View] [🔍 Symbol Breakdown] [📋 All Trades] [⚙️ Settings]  │
│                                                                       │
│ Current View: Symbol Breakdown                                        │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ BTC_USDT ANALYSIS                                      [▼ Collapse]  │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ Performance: +$95.20 (9.52%) | 5 signals | 4 successful (80%)       │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │                                                                   ││
│ │ Trade #1: +$45.00 ✓ SUCCESSFUL                                   ││
│ │ ├─ Entry (S1 Triggered): 2025-09-28 14:23:15                    ││
│ │ │  Conditions met:                                               ││
│ │ │  • VWAP_15min = 0.67 > 0.50 ✓                                 ││
│ │ │  • Risk_Fast = 45 < 100 ✓                                     ││
│ │ │  • Volume_Surge = 2.8 > 2.0 ✓                                 ││
│ │ │  → Symbol locked for analysis                                  ││
│ │ │                                                                 ││
│ │ ├─ Order Placed (Z1 Triggered): 2025-09-28 14:23:47 (+32s)     ││
│ │ │  Entry conditions met:                                         ││
│ │ │  • Entry_Signal = 0.52 > 0.4 ✓                                ││
│ │ │  • Risk_Z = 35 < 40 ✓                                         ││
│ │ │  Order details:                                                ││
│ │ │  • Price: $43,250 (from CZ_VWAP indicator)                    ││
│ │ │  • Size: $100 (10% of balance)                                ││
│ │ │  • Stop Loss: $42,385 (-2.0% from ST_ATR)                    ││
│ │ │  • Take Profit: $43,890 (+1.5% from TP_Percentage)           ││
│ │ │                                                                 ││
│ │ ├─ Position Monitoring: 8 minutes                               ││
│ │ │  Risk levels stable (max reached: 52)                         ││
│ │ │  Price movement: $43,250 → $43,890                            ││
│ │ │                                                                 ││
│ │ └─ Exit (Take Profit): 2025-09-28 14:31:23                      ││
│ │    • TP hit at $43,890 (+1.48% actual)                          ││
│ │    • Duration: 8m 8s                                             ││
│ │    • Profit: +$45.00 (after 0.1% fees)                          ││
│ │                                                                   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │                                                                   ││
│ │ Trade #2: -$20.00 ⚠️ EMERGENCY EXIT                              ││
│ │ ├─ Entry (S1 Triggered): 2025-09-28 15:10:42                    ││
│ │ │  Conditions met:                                               ││
│ │ │  • VWAP_15min = 0.52 > 0.50 ✓                                 ││
│ │ │  • Risk_Fast = 89 < 100 ✓                                     ││
│ │ │  • Volume_Surge = 2.1 > 2.0 ✓                                 ││
│ │ │                                                                 ││
│ │ ├─ Order Placed (Z1 Triggered): 2025-09-28 15:11:15 (+33s)     ││
│ │ │  Entry conditions met:                                         ││
│ │ │  • Entry_Signal = 0.48 > 0.4 ✓                                ││
│ │ │  • Risk_Z = 38 < 40 ✓                                         ││
│ │ │  Order details:                                                ││
│ │ │  • Price: $43,100                                              ││
│ │ │  • Size: $100                                                  ││
│ │ │  • Stop Loss: $42,236 (-2.0%)                                 ││
│ │ │  • Take Profit: $43,747 (+1.5%)                               ││
│ │ │                                                                 ││
│ │ ├─ Emergency Exit Triggered: 2025-09-28 15:13:28                ││
│ │ │  ⚠️  PROBLEM IDENTIFIED:                                       ││
│ │ │  Emergency condition met:                                      ││
│ │ │  • Risk1 = 215 > 200 ✗ (spiked from 89 to 215 in 2m)        ││
│ │ │  • WT1 = 0.008 < 0.01 ✗                                       ││
│ │ │                                                                 ││
│ │ └─ Exit (Market Order): 2025-09-28 15:13:30                     ││
│ │    • Closed at: $43,050 (-0.12% from entry)                     ││
│ │    • Duration: 2m 15s                                            ││
│ │    • Loss: -$20.00 (after fees and slippage)                    ││
│ │    • Cooldown: 5 minutes (strategy disabled for BTC_USDT)       ││
│ │
│ │                                                                   ││
│ │ 💡 LESSON LEARNED:                                                ││
│ │ Risk escalation was too rapid (89 → 215 in 2 minutes).          ││
│ │ Recommendation: Consider lowering Risk_Z threshold from 40 to 35 ││
│ │ to avoid entering positions with borderline risk levels.         ││
│ │                                                                   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │                                                                   ││
│ │ Trade #3: +$30.00 ✓ SUCCESSFUL                                   ││
│ │ ├─ Entry (S1 Triggered): 2025-09-28 16:45:12                    ││
│ │ │  Conditions met:                                               ││
│ │ │  • VWAP_15min = 0.71 > 0.50 ✓                                 ││
│ │ │  • Risk_Fast = 52 < 100 ✓                                     ││
│ │ │  • Volume_Surge = 3.2 > 2.0 ✓                                 ││
│ │ │                                                                 ││
│ │ ├─ Order Placed (Z1 Triggered): 2025-09-28 16:45:58 (+46s)     ││
│ │ │  • Entry_Signal = 0.61 > 0.4 ✓                                ││
│ │ │  • Risk_Z = 32 < 40 ✓ (good risk level)                      ││
│ │ │  • Price: $43,500 | Size: $100                                ││
│ │ │  • SL: $42,630 | TP: $44,153                                  ││
│ │ │                                                                 ││
│ │ └─ Exit (Take Profit): 2025-09-28 16:57:45                      ││
│ │    • TP hit at $44,153 (+1.5%)                                  ││
│ │    • Duration: 11m 47s                                           ││
│ │    • Profit: +$30.00                                             ││
│ │                                                                   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │                                                                   ││
│ │ Trade #4: +$25.00 ✓ SUCCESSFUL                                   ││
│ │ [Similar detailed breakdown...]                                   ││
│ │                                                                   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │                                                                   ││
│ │ Trade #5: +$15.00 ✓ SUCCESSFUL                                   ││
│ │ [Similar detailed breakdown...]                                   ││
│ │                                                                   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ FALSE POSITIVES (Signals that didn't convert to trades):             │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │                                                                   ││
│ │ Signal #1: CANCELLED (Timeout)                                    ││
│ │ Triggered: 2025-09-28 17:22:33                                   ││
│ │ S1 conditions met:                                                ││
│ │ • VWAP_15min = 0.53 > 0.50 ✓                                     ││
│ │ • Risk_Fast = 95 < 100 ✓                                         ││
│ │ • Volume_Surge = 2.3 > 2.0 ✓                                     ││
│ │                                                                   ││
│ │ Cancellation reason: Timeout (30s elapsed)                        ││
│ │ Z1 conditions never met:                                          ││
│ │ • Entry_Signal stayed at 0.35 < 0.4 ✗                           ││
│ │                                                                   ││
│ │ 💡 Analysis: Entry signal too weak. S1 triggered on basic        ││
│ │ indicators but market conditions weren't strong enough for entry. ││
│ │                                                                   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │                                                                   ││
│ │ Signal #2: CANCELLED (Conditions)                                 ││
│ │ Triggered: 2025-09-28 18:05:19                                   ││
│ │ S1 conditions met initially                                       ││
│ │                                                                   ││
│ │ Cancellation reason: O1 condition triggered                       ││
│ │ • Risk1 = 152 > 150 ✗                                            ││
│ │ • W10 = 0.05 < 0.1 ✗                                             ││
│ │                                                                   ││
│ │ 💡 Analysis: Risk escalated quickly, smart to cancel.            ││
│ │ Avoided potential loss.                                           ││
│ │                                                                   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ ETH_USDT ANALYSIS                                      [▼ Collapse]  │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ Performance: +$32.30 (3.23%) | 3 signals | 2 successful (66.7%)     │
│                                                                       │
│ [Similar detailed breakdown for ETH_USDT...]                          │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ PARAMETER PERFORMANCE ANALYSIS                                        │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Indicator Performance:                                            ││
│ │                                                                   ││
│ │ VWAP_15min (threshold: 0.50)                                     ││
│ │ • Used in: 8/8 signals (100%)                                    ││
│ │ • Success rate when > 0.60: 100% (3/3 trades)                   ││
│ │ • Success rate when 0.50-0.60: 40% (2/5 trades)                 ││
│ │ 💡 Recommendation: Consider raising threshold to 0.55 or 0.60    ││
│ │                                                                   ││
│ │ Risk_Fast (threshold: < 100)                                     ││
│ │ • All 8 signals passed this check                                ││
│ │ • Average at entry: 68.5                                         ││
│ │ • Successful trades avg: 54.2                                    ││
│ │ • Failed/cancelled avg: 91.7                                     ││
│ │ 💡 Recommendation: Consider < 80 for higher quality signals      ││
│ │                                                                   ││
│ │ Risk_Z (threshold: < 40)                                         ││
│ │ • Emergency exits occurred at Risk_Z: 35, 38                     ││
│ │ • Safe trades had Risk_Z: 28-32                                  ││
│ │ 💡 Recommendation: Lower to < 35 as originally suspected         ││
│ │                                                                   ││
│ │ Volume_Surge (threshold: > 2.0)                                  ││
│ │ • Higher surge = higher success: 3.0+ had 100% success          ││
│ │ • 2.0-2.5 range: 50% success                                     ││
│ │ 💡 Recommendation: Consider > 2.5 for better quality             ││
│ │                                                                   ││
│ │ Entry_Signal (threshold: > 0.4)                                  ││
│ │ • Strong signals (> 0.55): 100% success                          ││
│ │ • Weak signals (0.4-0.5): 33% success                           ││
│ │ 💡 Recommendation: Raise to > 0.5 for better entries             ││
│ │                                                                   ││
│ │ Take Profit (TP_Percentage: +1.5%)                               ││
│ │ • Average actual TP: +1.48%                                       ││
│ │ • All successful trades hit TP                                    ││
│ │ ✓ Current setting is optimal                                     ││
│ │                                                                   ││
│ │ Stop Loss (ST_ATR: -2.0%)                                        ││
│ │ • Never triggered in this backtest                                ││
│ │ • Emergency exits happened before SL                              ││
│ │ ℹ️  SL is safety net - keep as configured                        ││
│ │                                                                   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ RECOMMENDED OPTIMIZATIONS                                             │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ Based on this backtest, consider these changes:                      │
│                                                                       │
│ 1. S1 Signal Detection:                                              │
│    • VWAP_15min: 0.50 → 0.55 (reduce weak signals)                  │
│    • Risk_Fast: < 100 → < 80 (better risk filter)                   │
│    • Volume_Surge: > 2.0 → > 2.5 (stronger confirmation)            │
│                                                                       │
│ 2. Z1 Order Entry:                                                    │
│    • Entry_Signal: > 0.4 → > 0.5 (higher confidence)                │
│    • Risk_Z: < 40 → < 35 (avoid emergency exits)                    │
│                                                                       │
│ 3. Keep unchanged:                                                    │
│    • TP at +1.5% (working well)                                      │
│    • SL at -2.0% (good safety net)                                   │
│    • Timeout at 30s (appropriate)                                    │
│    • Emergency conditions (saved from larger losses)                 │
│                                                                       │
│ Expected impact if applied:                                           │
│ • Fewer signals (6-7 vs 8)                                           │
│ • Higher win rate (~80% vs 62.5%)                                    │
│ • Similar or better total return                                      │
│ • Lower risk exposure                                                 │
│                                                                       │
│ [Apply Optimizations to New Strategy] [Run A/B Test] [Ignore]        │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
4.4 Chart View - Wizualizacja Wskaźników w Czasie
Kliknięcie [📊 Chart View] w wynikach backtestu:
┌─────────────────────────────────────────────────────────────────────┐
│ Backtest Chart View: BT_20250929_1845                   [X] Close   │
│ Strategy: Quick Pump v2                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Symbol: [BTC_USDT ▼]  View: [Full 24h ▼]  [◀ Zoom In] [Zoom Out ▶] │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │                     PRICE CHART                                   ││
│ │ 44500┤                    ╱╲                                      ││
│ │      │                   ╱  ╲                                     ││
│ │ 44000┤     🔴──────────╱────╲────────                            ││
│ │      │     │ Trade #2       ╲                                    ││
│ │ 43500┤  🟢─┤ Emergency       ╲                                   ││
│ │      │  │  │                  ╲       🟢                         ││
│ │ 43000┤──┤──────────────────────╲─────│─🟢────                   ││
│ │      │  Trade #1                ╲    │ │ T#3                    ││
│ │ 42500┤                            ╲___│─┤                        ││
│ │      09:00  12:00  15:00  18:00  21:00  00:00  03:00  06:00    ││
│ │                                                                   ││
│ │ Signals: 🟢 Entry  🔴 Exit  ⚪ False Positive  🟡 Signal (no order)││
│ │                                                                   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Selected Indicators (toggle visibility):                              │
│ [☑] VWAP_15min  [☑] Risk_Fast  [☑] Entry_Signal  [☐] Volume_Surge   │
│ [☐] Risk_Z      [☐] Risk1      [☐] W10          [☐] WT1             │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │                  INDICATOR: VWAP_15min                            ││
│ │  1.0 ┤                                                            ││
│ │      │        ╱╲      ╱╲                    ╱╲                   ││
│ │  0.8 ┤       ╱  ╲    ╱  ╲                  ╱  ╲                  ││
│ │      │      ╱    ╲  ╱    ╲    ╱╲          ╱    ╲                 ││
│ │  0.6 ┤─────╱──────╲╱──────╲──╱──╲────────╱──────╲─────          ││
│ │      │    🟢      🔴        ╲╱    ╲      🟢                       ││
│ │  0.4 ┤             ⚪              ╲    ╱  🟢                     ││
│ │      │                              ╲  ╱                          ││
│ │  0.2 ┤                               ╲╱                           ││
│ │  0.0 ┤────────────────────────────────────────────────────────   ││
│ │      09:00  12:00  15:00  18:00  21:00  00:00  03:00  06:00    ││
│ │                                                                   ││
│ │ Threshold: ─── 0.50 (min for S1)                                ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │                  INDICATOR: Risk_Fast                             ││
│ │ 250 ┤                                                             ││
│ │     │                          🔴                                 ││
│ │ 200 ┤                          │                                  ││
│ │     │                          │   (Emergency exit               ││
│ │ 150 ┤──────────────────────────┼────spike to 215)                ││
│ │     │                         ╱│╲                                 ││
│ │ 100 ┤────────────────────────╱─┼─╲───────────────────────────   ││
│ │     │  🟢      🟢      ⚪   ╱   │  ╲   🟢  🟢                    ││
│ │  50 ┤──────────────────────╱────┼───╲──────────────────────     ││
│ │     │                            │                                ││
│ │   0 ┤────────────────────────────┼─────────────────────────────  ││
│ │      09:00  12:00  15:00  18:00  21:00  00:00  03:00  06:00    ││
│ │                                                                   ││
│ │ Threshold: ─── 100 (max for S1)                                 ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │                  INDICATOR: Entry_Signal                          ││
│ │  1.0 ┤                                                            ││
│ │      │                                                            ││
│ │  0.8 ┤                                                            ││
│ │      │        🟢          🟢              🟢  🟢                  ││
│ │  0.6 ┤        │           │               │   │                  ││
│ │      │        │           │               │   │                  ││
│ │  0.4 ┤────────┼─────⚪────┼─────🔴────────┼───┼──────────────   ││
│ │      │        │     │     │     │         │   │                  ││
│ │  0.2 ┤        │     │     │     │         │   │                  ││
│ │      │        │     │     │     │         │   │                  ││
│ │  0.0 ┤────────────────────────────────────────────────────────   ││
│ │      09:00  12:00  15:00  18:00  21:00  00:00  03:00  06:00    ││
│ │                                                                   ││
│ │ Threshold: ─── 0.40 (min for Z1)                                ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Hover over any point to see exact values at that timestamp.          │
│                                                                       │
│ Click on signal markers for detailed breakdown:                      │
│ • 🟢 Green: Successful trade details                                 │
│ • 🔴 Red: Failed/emergency exit details                              │
│ • ⚪ White: False positive details                                   │
│ • 🟡 Yellow: Signal without order details                            │
│                                                                       │
│ [Export Chart as PNG] [Export Data as CSV] [Print Report]            │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
Interakcje w Chart View:

Hover nad sygnałem (np. 🟢 Trade #1) pokazuje tooltip:

┌─────────────────────────────────────────┐
│ Trade #1 - SUCCESSFUL                   │
│ Entry: 2025-09-28 14:23:15              │
│ Exit: 2025-09-28 14:31:23 (+8m)        │
│ Profit: +$45.00 (+1.48%)                │
│                                          │
│ Indicators at entry:                     │
│ • VWAP_15min: 0.67                      │
│ • Risk_Fast: 45                          │
│ • Entry_Signal: 0.52                     │
│ • Risk_Z: 35                             │
│                                          │
│ Click for full details →                 │
└─────────────────────────────────────────┘

Kliknięcie na sygnał otwiera pełny breakdown (jak w Symbol Breakdown powyżej)
Zoom - możesz przybliżyć konkretny przedział czasowy (np. tylko Trade #2)
Toggle indicators - włącz/wyłącz wykresy wskaźników aby zobaczyć różne kombinacje


EKRAN 5: TRADING (Paper/Live) - Uruchamianie Strategii
5.1 Lista Sesji Trading
┌─────────────────────────────────────────────────────────────────────┐
│ Trading Sessions                              [+ Start New Session]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Filter: [All Types ▼] [All Status ▼] Sort: [Newest First ▼]        │
│                                                                       │
│ ACTIVE SESSIONS (1)                                                   │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ SESSION_20250929_1900                          [Stop] [Monitor]   ││
│ │ Type: 📄 PAPER TRADING                                           ││
│ │ Strategy: Quick Pump v2                                          ││
│ │ Symbols: BTC_USDT, ETH_USDT                                      ││
│ │ Started: 2025-09-29 19:00:15 (running 2h 15m)                   ││
│ │                                                                   ││
│ │ Performance:                                                      ││
│ │ Balance: $1,045.30 (+4.53%)                                      ││
│ │ Signals: 3 | Trades: 2 (1 active) | Win Rate: 50%              ││
│ │ Max Drawdown: -1.2%                                              ││
│ │                                                                   ││
│ │ Active Positions:                                                 ││
│ │ • BTC_USDT: +$12.50 unrealized (opened 15m ago)                 ││
│ │                                                                   ││
│ │ Last Activity: 1 minute ago                                      ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ COMPLETED SESSIONS (8)                                                │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ SESSION_20250928_1400                        [Results] [Archive]  ││
│ │ Type: 📄 PAPER TRADING                                           ││
│ │ Strategy: Quick Pump v2                                          ││
│ │ Duration: 6h 32m (2025-09-28 14:00 → 20:32)                     ││
│ │ Final P&L: +$87.20 (+8.72%)                                      ││
│ │ Signals: 5 | Trades: 4 | Win Rate: 75%                          ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ SESSION_20250927_1000                        [Results] [Archive]  ││
│ │ Type: 💵 LIVE TRADING                                            ││
│ │ Strategy: Steady Rider                                           ││
│ │ Duration: 4h 15m (2025-09-27 10:00 → 14:15)                     ││
│ │ Final P&L: +$34.50 (+3.45%)                                      ││
│ │ Signals: 3 | Trades: 3 | Win Rate: 100%                         ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ [...6 more sessions...]                                               │
│                                                                       │
│ OBSERVATION MODE SESSIONS (Monitor Only)                              │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ OBS_20250929_2000                           [Stop] [View Charts]  ││
│ │ Purpose: 🔍 INDICATOR OBSERVATION                                ││
│ │ Symbols: BTC_USDT                                                ││
│ │ Monitoring indicators:                                            ││
│ │ • VWAP_15min, Risk_Fast, Volume_Surge                           ││
│ │ • Entry_Signal, Risk_Z                                           ││
│ │ Started: 2025-09-29 20:00:00 (running 1h 15m)                   ││
│ │ No trading - observation only                                    ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
5.2 Start New Session - Pełna Konfiguracja
Kliknięcie [+ Start New Session]:
┌─────────────────────────────────────────────────────────────────────┐
│ Start New Trading Session                                [X] Close   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Step 1: Session Type                                                  │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ ● Paper Trading (Virtual Money)                                  ││
│ │   Test strategies with simulated funds. No real money at risk.   ││
│ │   Perfect for validating backtest results in live conditions.    ││
│ │                                                                   ││
│ │ ○ Live Trading (Real Money)                                      ││
│ │   Execute real trades on exchange using actual funds.            ││
│ │   ⚠️  RISK WARNING: Real money will be used. Double-check all   ││
│ │   settings before starting.                                       ││
│ │                                                                   ││
│ │ ○ Observation Mode (No Trading)                                  ││
│ │   Monitor indicators in real-time without any trading.           ││
│ │   Useful for validating indicator calculations on live data.     ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 2: Select Strategy                                              │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Strategy: [Quick Pump v2 ▼]                                      ││
│ │                                                                   ││
│ │ Strategy Details:                                                 ││
│ │ • Last backtest: BT_20250929_1845                                ││
│ │   Performance: +12.75% (8 signals, 62.5% win rate)              ││
│ │ • Recommended optimizations available (click to review)          ││
│ │                                                                   ││
│ │ Required Indicators (auto-loaded):                                ││
│ │ ✓ VWAP_15min, Risk_Fast, Volume_Surge                           ││
│ │ ✓ Entry_Signal, Risk_Z, CZ_VWAP                                 ││
│ │ ✓ ST_ATR, TP_Percentage, Risk1, W10, WT1                        ││
│ │                                                                   ││
│ │ All indicators configured and active ✓                            ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 3: Symbol Assignment                                            │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Select symbols to trade:                                          ││
│ │                                                                   ││
│ │ [☑] BTC_USDT                                                     ││
│ │     Last price: $43,250 | 24h volume: $2.3B                     ││
│ │     Liquidity: Excellent | Spread: 0.01%                         ││
│ │     All required indicators: ✓ Available                         ││
│ │                                                                   ││
│ │ [☑] ETH_USDT                                                     ││
│ │     Last price: $3,125 | 24h volume: $1.1B                      ││
│ │     Liquidity: Excellent | Spread: 0.01%                         ││
│ │     All required indicators: ✓ Available                         ││
│ │                                                                   ││
│ │ [☐] ADA_USDT                                                     ││
│ │     Last price: $0.48 | 24h volume: $145M                       ││
│ │     Liquidity: Good | Spread: 0.02%                              ││
│ │     ⚠️  Lower liquidity - may affect execution                   ││
│ │                                                                   ││
│ │ [Show all 50+ symbols...]                                         ││
│ │                                                                   ││
│ │ Selected: 2 symbols                                              ││
│ │                                                                   ││
│ │ ⚠️  Each symbol will be monitored independently. Signals on one  ││
│ │ symbol don't affect others (unless same symbol lock applies).    ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Step 4: Budget & Risk Limits                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐
│ Live Trading Monitor: SESSION_20250929_1900            [Stop Session]│
│ Strategy: Quick Pump v2 | Type: Paper Trading                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Session Status: 🟢 ACTIVE | Running: 2h 15m | Auto-refresh: ON      │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ PERFORMANCE OVERVIEW                                                  │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ ┌───────────────────────────────────────────────────────────────┐   │
│ │ Starting Balance: $1,000.00                                    │   │
│ │ Current Balance:  $1,045.30  (+$45.30 / +4.53%) 🟢           │   │
│ │ Peak Balance:     $1,058.20  (at 20:45)                       │   │
│ │ Current Drawdown: -1.2% (from peak)                            │   │
│ └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│ ┌───────────────────────────────────────────────────────────────┐   │
│ │ Total Signals:      3                                          │   │
│ │ Orders Placed:      2                                          │   │
│ │ Active Positions:   1 (BTC_USDT, +$12.50 unrealized)         │   │
│ │ Completed Trades:   1 (1 profit, 0 loss)                      │   │
│ │ Cancelled Signals:  1 (timeout)                                │   │
│ │ Win Rate:           100% (of completed trades)                 │   │
│ └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│ Risk Status:                                                          │
│ • Exposure: $100 / $300 max (33% of limit) ✓                        │
│ • Positions: 1 / 3 max ✓                                             │
│ • Daily P&L: +$45.30 (+4.53%) ✓ (Stop at -5%)                       │
│ • Max Drawdown: -1.2% ✓ (Stop at -10%)                              │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ ACTIVE POSITIONS                                                      │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ BTC_USDT | Position #1                         [Force Close] [🔍]││
│ │                                                                   ││
│ │ Status: 🟢 OPEN (15 minutes)                                     ││
│ │ Entry: $43,250.00 at 21:00:15                                    ││
│ │ Current: $43,375.00 (+0.29%)                                     ││
│ │ Size: $100.00 (0.00231 BTC)                                      ││
│ │                                                                   ││
│ │ Unrealized P&L: +$12.50 (+12.5% of position) 🟢                 ││
│ │                                                                   ││
│ │ Stop Loss: $42,385 (-2.0%) | 🔴 $865 away                       ││
│ │ Take Profit: $43,890 (+1.5%) | 🟢 $515 away                     ││
│ │                                                                   ││
│ │ Current Indicators:                                               ││
│ │ • Risk_Fast: 68 (was 52 at entry)                                ││
│ │ • Risk1: 85 (Emergency at 200)                                   ││
│ │ • VWAP_15min: 0.71                                               ││
│ │ • WT1: 0.15                                                       ││
│ │                                                                   ││
│ │ Last Update: 3 seconds ago                                        ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ LIVE ACTIVITY LOG                                   [Filter] [Export]│
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ 21:15:22 | BTC_USDT | Indicators updated                         ││
│ │          | Risk_Fast: 52→68, VWAP: 0.71, Position healthy       ││
│ │                                                                   ││
│ │ 21:12:45 | BTC_USDT | Price: $43,375 (+0.29% from entry)        ││
│ │          | Unrealized P&L: +$12.50, TP $515 away                ││
│ │                                                                   ││
│ │ 21:00:47 | BTC_USDT | ✓ ORDER FILLED                            ││
│ │          | Z1 executed: $100 @ $43,250                           ││
│ │          | SL: $42,385 | TP: $43,890                            ││
│ │                                                                   ││
│ │ 21:00:15 | BTC_USDT | 🟡 SIGNAL S1 TRIGGERED                    ││
│ │          | VWAP=0.71 > 0.50 ✓, Risk=52 < 100 ✓, Vol=2.8 > 2.0 ✓││
│ │          | Symbol locked, evaluating entry conditions...         ││
│ │                                                                   ││
│ │ 20:45:30 | ETH_USDT | ✓ TRADE CLOSED - PROFIT                   ││
│ │          | Take Profit hit @ $3,172 (+1.5%)                      ││
│ │          | Profit: +$32.80, Duration: 12m 15s                    ││
│ │                                                                   ││
│ │ 20:33:15 | ETH_USDT | ✓ ORDER FILLED                            ││
│ │          | Z1 executed: $100 @ $3,125                            ││
│ │                                                                   ││
│ │ 20:33:02 | ETH_USDT | 🟡 SIGNAL S1 TRIGGERED                    ││
│ │          | VWAP=0.68, Risk=58, Vol=3.1                          ││
│ │                                                                   ││
│ │ 20:15:18 | BTC_USDT | ⚪ SIGNAL CANCELLED - TIMEOUT             ││
│ │          | S1 triggered but Z1 conditions not met in 30s        ││
│ │          | Entry_Signal stayed at 0.38 < 0.4                    ││
│ │                                                                   ││
│ │ 19:00:15 | System   | 🟢 SESSION STARTED                        ││
│ │          | Paper Trading, Balance: $1,000, Symbols: 2           ││
│ │                                                                   ││
│ │ [Load More Events...] (showing last 10)                          ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ LIVE INDICATOR VALUES                          [Chart View] [Config]│
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ Symbol: [BTC_USDT ▼]  Last Update: 2 seconds ago                    │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Indicator      │ Current │ Threshold │ Status │ Last Change      ││
│ ├────────────────┼─────────┼───────────┼────────┼──────────────────┤│
│ │ VWAP_15min     │ 0.71    │ > 0.50    │ ✓ PASS │ +0.03 (5m ago)  ││
│ │ Risk_Fast      │ 68      │ < 100     │ ✓ PASS │ +16 (3m ago)    ││
│ │ Volume_Surge   │ 2.3     │ > 2.0     │ ✓ PASS │ -0.5 (8m ago)   ││
│ │ Entry_Signal   │ 0.45    │ > 0.4     │ ✓ PASS │ +0.07 (12m ago) ││
│ │ Risk_Z         │ 35      │ < 40      │ ✓ PASS │ Stable          ││
│ │ Risk1          │ 85      │ < 200     │ ✓ SAFE │ +5 (2m ago)     ││
│ │ WT1            │ 0.15    │ > 0.01    │ ✓ SAFE │ Stable          ││
│ │ W10            │ 0.25    │ > 0.1     │ ✓ PASS │ +0.02 (1m ago)  ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Symbol: [ETH_USDT ▼]  Last Update: 3 seconds ago                    │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Indicator      │ Current │ Threshold │ Status │ Last Change      ││
│ ├────────────────┼─────────┼───────────┼────────┼──────────────────┤│
│ │ VWAP_15min     │ 0.48    │ > 0.50    │ ✗ FAIL │ -0.08 (2m ago)  ││
│ │ Risk_Fast      │ 92      │ < 100     │ ✓ PASS │ +12 (1m ago)    ││
│ │ Volume_Surge   │ 1.8     │ > 2.0     │ ✗ FAIL │ -0.3 (5m ago)   ││
│ │ Entry_Signal   │ 0.32    │ > 0.4     │ ✗ FAIL │ -0.05 (3m ago)  ││
│ │ Risk_Z         │ 42      │ < 40      │ ✗ FAIL │ +8 (1m ago) ⚠️  ││
│ │ Risk1          │ 105     │ < 200     │ ✓ SAFE │ +15 (1m ago)    ││
│ │ WT1            │ 0.08    │ > 0.01    │ ✓ SAFE │ -0.02 (4m ago)  ││
│ │ W10            │ 0.18    │ > 0.1     │ ✓ PASS │ Stable          ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ℹ️  Red indicators show why no signal is currently active for ETH.  │
│                                                                       │
│ [Open Chart View for Real-time Visualization]                        │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
5.4 Observation Mode - Monitor Indicators bez TradinguJeśli wybrano Observation Mode w Step 1:┌─────────────────────────────────────────────────────────────────────┐
│ Observation Mode: OBS_20250929_2000                  [Stop] [Export] │
│ Purpose: Monitor indicators without trading                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Mode: 🔍 OBSERVATION ONLY (No orders will be placed)                │
│ Running: 1h 15m | Last Update: 1 second ago                         │
│                                                                       │
│ Monitoring:                                                           │
│ • Symbols: BTC_USDT, ETH_USDT                                        │
│ • Indicators: VWAP_15min, Risk_Fast, Volume_Surge, Entry_Signal,    │
│   Risk_Z, Risk1, WT1, W10                                           │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ LIVE INDICATOR CHARTS                                                 │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ BTC_USDT - Last 1 Hour                           [Zoom] [Config] ││
│ │                                                                   ││
│ │ VWAP_15min                                                        ││
│ │  1.0 ┤                                                            ││
│ │      │                          ╱╲                                ││
│ │  0.8 ┤                         ╱  ╲                               ││
│ │      │      ╱╲                ╱    ╲                              ││
│ │  0.6 ┤─────╱──╲──────────────╱──────╲──────────── 0.50 threshold││
│ │      │          ╲            ╱                                    ││
│ │  0.4 ┤           ╲          ╱                                     ││
│ │      │            ╲        ╱                                      ││
│ │  0.2 ┤             ╲──────╱                                       ││
│ │      │                                                            ││
│ │  0.0 ┤────────────────────────────────────────────────────────   ││
│ │      20:00      20:15      20:30      20:45      21:00    NOW   ││
│ │      Current: 0.71 ✓ Above threshold                             ││
│ │                                                                   ││
│ │ Risk_Fast                                                         ││
│ │ 200 ┤                                                             ││
│ │     │                                                             ││
│ │ 150 ┤                                                             ││
│ │     │                            ╱╲                               ││
│ │ 100 ┤───────────────────────────╱──╲────────────── 100 threshold││
│ │     │    ╱╲                    ╱    ╲                            ││
│ │  50 ┤───╱──╲──────────────────╱──────╲───────                   ││
│ │     │       ╲                ╱                                    ││
│ │   0 ┤────────╲──────────────╱─────────────────────────────────  ││
│ │      20:00      20:15      20:30      20:45      21:00    NOW   ││
│ │      Current: 68 ✓ Below threshold                               ││
│ │                                                                   ││
│ │ [Show more indicators...]                                         ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ ETH_USDT - Last 1 Hour                           [Zoom] [Config] ││
│ │ [Similar charts for ETH_USDT...]                                 ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Hypothetical Signals (if trading was enabled):                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ 21:00:15 | BTC_USDT | S1 would trigger                          ││
│ │          | VWAP=0.71 > 0.50, Risk=52 < 100, Vol=2.8 > 2.0       ││
│ │          | → Would lock symbol and evaluate Z1                   ││
│ │                                                                   ││
│ │ 20:33:02 | ETH_USDT | S1 would trigger                          ││
│ │          | VWAP=0.68, Risk=58, Vol=3.1                          ││
│ │                                                                   ││
│ │ 20:15:18 | BTC_USDT | S1 would trigger but cancel (timeout)     ││
│ │          | Entry_Signal never reached 0.4                        ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Data Collection:                                                      │
│ • All indicator values being logged                                  │
│ • Export available as CSV for analysis                               │
│ • Can be used to validate indicator calculations                     │
│                                                                       │
│ [Export Last Hour] [Export Full Session] [Switch to Paper Trading]   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘EKRAN 6: RESULTS COMPARISON - Porównanie Backtest vs Live/Paper┌─────────────────────────────────────────────────────────────────────┐
│ Results Comparison                                       [Export PDF] │
│ Compare backtest predictions with actual trading performance         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Backtest: [BT_20250929_1845 ▼]                                      │
│ Live/Paper: [SESSION_20250929_1900 ▼]                               │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ PERFORMANCE COMPARISON                                                │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ ┌───────────────────────────────────────────────────────────────┐   │
│ │ Metric              │ Backtest     │ Live/Paper   │ Difference │   │
│ ├─────────────────────┼──────────────┼──────────────┼────────────┤   │
│ │ Total Return        │ +12.75%      │ +4.53%       │ -8.22%    │   │
│ │ Win Rate            │ 62.5%        │ 100%         │ +37.5%    │   │
│ │ Total Signals       │ 8            │ 3            │ -5        │   │
│ │ Completed Trades    │ 8            │ 1            │ -7        │   │
│ │ Avg Trade Duration  │ 9m 45s       │ 12m 15s      │ +2m 30s   │   │
│ │ Max Drawdown        │ -3.4%        │ -1.2%        │ +2.2%     │   │
│ │ Sharpe Ratio        │ 1.82         │ N/A (too few)│ -         │   │
│ └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│ ℹ️  Live session is only 2h 15m vs 24h backtest - limited data     │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ SIGNAL COMPARISON                                                     │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ Signals generated at similar conditions?                              │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Time Period    │ Backtest │ Live     │ Match? │ Notes            ││
│ ├────────────────┼──────────┼──────────┼────────┼──────────────────┤│
│ │ 20:15 - 20:30  │ Yes (S1) │ Yes (S1) │ ✓      │ Both cancelled   ││
│ │                │ Cancelled│ Cancelled│        │ - timeout        ││
│ ├────────────────┼──────────┼──────────┼────────┼──────────────────┤│
│ │ 20:30 - 20:45  │ Yes (S1) │ Yes (S1) │ ✓      │ Both successful  ││
│ │                │ Trade OK │ Trade OK │        │ - TP hit         ││
│ ├────────────────┼──────────┼──────────┼────────┼──────────────────┤│
│ │ 21:00 - 21:15  │ Yes (S1) │ Yes (S1) │ ✓      │ Both active      ││
│ │                │ Active   │ Active   │        │ - in position    ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Signal consistency: 100% (3/3 signals matched)                       │
│ ✓ Indicators behaving consistently between backtest and live         │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ INDICATOR VALUE COMPARISON                                            │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ At Signal Time: 20:33:02 (ETH_USDT Trade #1)                        │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Indicator      │ Backtest │
│ ═══════════════════════════════════════════════════════════════════ │
│ INDICATOR VALUE COMPARISON                                            │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ At Signal Time: 20:33:02 (ETH_USDT Trade #1)                        │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Indicator      │ Backtest │ Live     │ Diff   │ Status          ││
│ ├────────────────┼──────────┼──────────┼────────┼─────────────────┤│
│ │ VWAP_15min     │ 0.68     │ 0.68     │ 0.00   │ ✓ Identical     ││
│ │ Risk_Fast      │ 58       │ 58       │ 0      │ ✓ Identical     ││
│ │ Volume_Surge   │ 3.1      │ 3.1      │ 0.0    │ ✓ Identical     ││
│ │ Entry_Signal   │ 0.51     │ 0.52     │ +0.01  │ ⚠️ Minor diff   ││
│ │ Risk_Z         │ 32       │ 33       │ +1     │ ⚠️ Minor diff   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Analysis: Indicators within acceptable variance (< 5%)                │
│ ✓ Calculations consistent between backtest and live                  │
│                                                                       │
│ At Emergency Exit: 15:13:28 (BTC_USDT Trade #2 in backtest)         │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Indicator      │ Backtest │ Live     │ Notes                     ││
│ ├────────────────┼──────────┼──────────┼───────────────────────────┤│
│ │ Risk1          │ 215      │ N/A      │ Similar situation not yet ││
│ │ WT1            │ 0.008    │ N/A      │ encountered in live       ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ℹ️  No emergency exits in live session yet - cannot compare         │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ EXECUTION DIFFERENCES                                                 │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Factor              │ Backtest      │ Live/Paper    │ Impact    ││
│ ├─────────────────────┼───────────────┼───────────────┼───────────┤│
│ │ Order Fill Time     │ Instant       │ 50-200ms      │ Minimal   ││
│ │ Slippage            │ Simulated     │ Simulated     │ None      ││
│ │ Fees                │ 0.1%          │ 0.1%          │ None      ││
│ │ Data Latency        │ None (replay) │ 20-50ms       │ Minimal   ││
│ │ Indicator Calc Time │ Post-process  │ Real-time     │ Minimal   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Overall: Execution differences negligible for Paper Trading          │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ SUMMARY & INSIGHTS                                                    │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ ✓ POSITIVE FINDINGS:                                                 │
│ • Indicators calculating identically in live vs backtest             │
│ • Signal detection logic working as expected                         │
│ • Win rate in live (100%) better than backtest (62.5%)              │
│ • No unexpected behavior or anomalies                                │
│                                                                       │
│ ⚠️  CAVEATS:                                                         │
│ • Live session only 2h 15m - need more data                         │
│ • Only 1 completed trade - insufficient for statistical analysis     │
│ • Haven't encountered high-risk scenarios yet                        │
│ • Market conditions may differ from backtest period                  │
│                                                                       │
│ 💡 RECOMMENDATIONS:                                                  │
│ • Continue live session for at least 6-12 hours                      │
│ • Monitor for emergency exit scenarios                               │
│ • Compare again after 5+ completed trades                            │
│ • If performance deviates >20%, investigate indicator calculations   │
│                                                                       │
│ [Continue Monitoring] [Generate Full Report] [Export Comparison]     │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘


EKRAN 6: RESULTS COMPARISON (dokończenie)
│ ═══════════════════════════════════════════════════════════════════ │
│ INDICATOR VALUE COMPARISON                                            │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ At Signal Time: 20:33:02 (ETH_USDT Trade #1)                        │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Indicator      │ Backtest │ Live     │ Diff   │ Status          ││
│ ├────────────────┼──────────┼──────────┼────────┼─────────────────┤│
│ │ VWAP_15min     │ 0.68     │ 0.68     │ 0.00   │ ✓ Identical     ││
│ │ Risk_Fast      │ 58       │ 58       │ 0      │ ✓ Identical     ││
│ │ Volume_Surge   │ 3.1      │ 3.1      │ 0.0    │ ✓ Identical     ││
│ │ Entry_Signal   │ 0.51     │ 0.52     │ +0.01  │ ⚠️ Minor diff   ││
│ │ Risk_Z         │ 32       │ 33       │ +1     │ ⚠️ Minor diff   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Analysis: Indicators within acceptable variance (< 5%)                │
│ ✓ Calculations consistent between backtest and live                  │
│                                                                       │
│ At Emergency Exit: 15:13:28 (BTC_USDT Trade #2 in backtest)         │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Indicator      │ Backtest │ Live     │ Notes                     ││
│ ├────────────────┼──────────┼──────────┼───────────────────────────┤│
│ │ Risk1          │ 215      │ N/A      │ Similar situation not yet ││
│ │ WT1            │ 0.008    │ N/A      │ encountered in live       ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ℹ️  No emergency exits in live session yet - cannot compare         │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ EXECUTION DIFFERENCES                                                 │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Factor              │ Backtest      │ Live/Paper    │ Impact    ││
│ ├─────────────────────┼───────────────┼───────────────┼───────────┤│
│ │ Order Fill Time     │ Instant       │ 50-200ms      │ Minimal   ││
│ │ Slippage            │ Simulated     │ Simulated     │ None      ││
│ │ Fees                │ 0.1%          │ 0.1%          │ None      ││
│ │ Data Latency        │ None (replay) │ 20-50ms       │ Minimal   ││
│ │ Indicator Calc Time │ Post-process  │ Real-time     │ Minimal   ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ Overall: Execution differences negligible for Paper Trading          │
│                                                                       │
│ ═══════════════════════════════════════════════════════════════════ │
│ SUMMARY & INSIGHTS                                                    │
│ ═══════════════════════════════════════════════════════════════════ │
│                                                                       │
│ ✓ POSITIVE FINDINGS:                                                 │
│ • Indicators calculating identically in live vs backtest             │
│ • Signal detection logic working as expected                         │
│ • Win rate in live (100%) better than backtest (62.5%)              │
│ • No unexpected behavior or anomalies                                │
│                                                                       │
│ ⚠️  CAVEATS:                                                         │
│ • Live session only 2h 15m - need more data                         │
│ • Only 1 completed trade - insufficient for statistical analysis     │
│ • Haven't encountered high-risk scenarios yet                        │
│ • Market conditions may differ from backtest period                  │
│                                                                       │
│ 💡 RECOMMENDATIONS:                                                  │
│ • Continue live session for at least 6-12 hours                      │
│ • Monitor for emergency exit scenarios                               │
│ • Compare again after 5+ completed trades                            │
│ • If performance deviates >20%, investigate indicator calculations   │
│                                                                       │
│ [Continue Monitoring] [Generate Full Report] [Export Comparison]     │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

PODSUMOWANIE CAŁEGO MVP - KOMPLETNY PRZEPŁYW
Workflow użytkownika od początku do końca:
1. POCZĄTEK - Konfiguracja Wskaźników
Czas: 30 minut
User → Ekran INDICATORS
├─ Przegląd dostępnych typów wskaźników (VWAP, Risk, etc.)
├─ Kliknięcie [+ New Indicator]
│  ├─ Wybór typu: VWAP
│  ├─ Nazwa: VWAP_15min
│  ├─ Parametry: window 900s → 0s
│  ├─ Symbols: ALL
│  └─ [Test with Live Data] → wartość 0.67 ✓
├─ Powtórz dla wszystkich wskaźników (11 sztuk):
│  • VWAP_15min, Risk_Fast, Volume_Surge
│  • Entry_Signal, Risk_Z, CZ_VWAP
│  • ST_ATR, TP_Percentage, Risk1, W10, WT1
└─ [Chart View] dla każdego → weryfikacja obliczeń
2. ZBIERANIE DANYCH
Czas: 24 godziny (automatyczne)
User → Ekran DATA COLLECTION
├─ Kliknięcie [+ Start Collection]
├─ Wybór symboli: BTC_USDT, ETH_USDT
├─ Duration: 24 hours
├─ [Start Collection]
│  └─ System zbiera dane w tle
│     ├─ Progress bar: 0% → 100%
│     ├─ Real-time licznik rekordów
│     └─ Po 24h: 87,492 records → data/DC_20250928_0900/
└─ [Use in Backtest] → przejście do backtestu
3. TWORZENIE STRATEGII
Czas: 20 minut
User → Ekran STRATEGIES → [+ Create New Strategy]
├─ Nazwa: "Quick Pump v2"
│
├─ SECTION 1: SIGNAL (S1)
│  ├─ Condition 1: VWAP_15min > 0.50
│  ├─ Condition 2: Risk_Fast < 100
│  └─ Condition 3: Volume_Surge > 2.0
│
├─ SECTION 2: ORDER ENTRY (Z1)
│  ├─ Condition 1: Entry_Signal > 0.4
│  ├─ Condition 2: Risk_Z < 40
│  ├─ Price: CZ_VWAP
│  ├─ Stop Loss: ST_ATR (-2%)
│  ├─ Take Profit: TP_Percentage (+1.5%)
│  └─ Position Size: 10% balance
│
├─ SECTION 3: CANCELLATION (O1)
│  ├─ Timeout: 30 seconds
│  └─ OR: Risk1 > 150 AND W10 < 0.1
│
├─ SECTION 4: EMERGENCY EXIT
│  ├─ Condition: Risk1 > 200 AND WT1 < 0.01
│  └─ Cooldown: 5 minutes
│
├─ [Validate Strategy] → wszystko OK ✓
└─ [Save Strategy]
4. BACKTEST - Testowanie
Czas: 2-3 godziny (przy 10x speed)
User → Ekran BACKTESTING
├─ Data Source: DC_20250928_0900
├─ Symbols: BTC_USDT, ETH_USDT
├─ Strategy: Quick Pump v2
├─ Speed: 10x
├─ Budget: $1,000
├─ [Start Backtest]
│  └─ System przetwarza 24h danych w 2.4h
│     ├─ Live progress bar: 0% → 100%
│     ├─ Real-time performance updates
│     └─ Zapisuje wszystkie wartości wskaźników
│
└─ Po zakończeniu → RESULTS
   ├─ Overall: +$127.50 (12.7%), 8 signals
   │
   ├─ BTC_USDT breakdown:
   │  ├─ Trade #1: +$45 ✓ (TP hit)
   │  ├─ Trade #2: -$20 ⚠️ (Emergency - Risk spike)
   │  ├─ Trade #3: +$30 ✓
   │  └─ False Positive #1: Cancelled (timeout)
   │
   ├─ Parameter Analysis:
   │  • VWAP > 0.60 → 100% success
   │  • Risk_Z < 35 → fewer emergencies
   │  • Volume > 2.5 → better quality
   │
   ├─ [📊 Chart View]
   │  └─ Wykresy wskaźników w czasie
   │     • Każdy trade zaznaczony
   │     • Wartości wskaźników na timeline
   │     • Hover dla szczegółów
   │
   └─ Recommendations: Lower Risk_Z to 35
5. CHART VIEW - Analiza Wizualna
Czas: 15 minut
User → W Results → [📊 Chart View]
├─ Widzi wykresy:
│  ├─ Price chart z zaznaczonymi trades
│  ├─ VWAP_15min z threshold line
│  ├─ Risk_Fast z Emergency spike
│  └─ Entry_Signal z success/fail points
│
├─ Hover nad Trade #2 (Emergency):
│  └─ Widzi: Risk spiked 89 → 215 w 2 minuty
│     💡 "Risk_Z was 38, too close to 40 limit"
│
├─ Zoom do problematycznego okresu 15:10-15:15
│  └─ Dokładnie widzi jak wskaźniki zmieniały się
│
└─ Konkluzja: Risk_Z < 35 faktycznie potrzebne
6. OPTYMALIZACJA
Czas: 5 minut
User → W Results → [Apply Optimizations to New Strategy]
├─ System tworzy "Quick Pump v2.1":
│  • VWAP_15min: 0.50 → 0.55
│  • Risk_Fast: < 100 → < 80
│  • Volume_Surge: > 2.0 → > 2.5
│  • Risk_Z: < 40 → < 35
│
└─ [Run A/B Test]
   ├─ Uruchamia backtest dla obu wersji
   └─ Porównuje wyniki
7. PAPER TRADING - Weryfikacja Live
Czas: 6-12 godzin
User → Ekran TRADING → [+ Start New Session]
├─ Type: Paper Trading
├─ Strategy: Quick Pump v2
├─ Symbols: BTC_USDT, ETH_USDT
├─ Budget: $1,000 (virtual)
├─ Duration: Until stopped
├─ [Start Session]
│
└─ Monitoring:
   ├─ Real-time indicator values (auto-refresh)
   ├─ Signals pojawiają się live
   ├─ Trades wykonywane automatycznie
   ├─ Log wszystkich zdarzeń
   │
   └─ Po 6 godzinach:
      ├─ 3 signals, 2 trades, 100% win rate
      └─ Porównanie z backtest:
         • Signals w tych samych momentach ✓
         • Indicator values identyczne ✓
         • Zachowanie zgodne z oczekiwaniami ✓
8. OBSERVATION MODE - Debugging
Czas: W razie problemów
Jeśli coś się nie zgadza:

User → [Start New Session] → Observation Mode
├─ Monitoruje same wskaźniki bez tradingu
├─ Porównuje z backtest chart view
│  └─ Sprawdza czy obliczenia się zgadzają
│
└─ Jeśli VWAP w live = 0.50, ale w backtest = 0.68:
   ⚠️ Problem z kalkulacją wskaźnika!
   → Trzeba poprawić kod kalkulacji
9. LIVE TRADING - Prawdziwe Pieniądze
Czas: Tylko po pełnej weryfikacji
Po successful paper trading przez ≥24h:

User → [+ Start New Session]
├─ Type: LIVE TRADING ⚠️
├─ Strategy: Quick Pump v2
├─ Symbols: BTC_USDT (start small!)
├─ Budget: $500 (real money)
│  └─ Position size: 5% = $25 per trade
│
├─ Extra confirmations:
│  "⚠️ Real money will be used"
│  "⚠️ Exchange fees apply"
│  "⚠️ Cannot undo live trades"
│  [I understand, Start Live Trading]
│
└─ Działa identycznie jak Paper, ale:
   • Prawdziwe API calls do exchange
   • Prawdziwe zlecenia
   • Prawdziwe pieniądze!

KLUCZOWE RÓŻNICE vs. Obecny System
Co USUNĘLIŚMY:

❌ ReactFlow canvas (za skomplikowany)
❌ Market Scanner (nie jest potrzebny)
❌ Portfolio Management (to nie jest broker)
❌ Risk Management dashboard (podstawowe limity wystarczą)
❌ Market Data page (duplikat Indicators)
❌ Strategies gallery (niepotrzebne szablony)
❌ Settings z 5 zakładkami (uproszczenie)

Co DODALIŚMY:

✓ Szczegółowy breakdown każdego trade
✓ Wartości wskaźników przy każdej decyzji
✓ "Lessons learned" dla błędnych decyzji
✓ Chart View z timeline wszystkich wskaźników
✓ Porównanie backtest vs live
✓ Observation Mode (bez tradingu)
✓ Parameter Performance Analysis

Co POPRAWILIŚMY:

✓ Prosty formularz zamiast drag-and-drop
✓ Bezpośrednie linki między ekranami
✓ Real-time wszystko (nie tylko cena)
✓ Jeden przepływ: Data → Strategy → Backtest → Live
✓ Feedback loop: wyniki → optymalizacja → test


ROADMAP IMPLEMENTACJI - 3 Tygodnie
Tydzień 1: Backend Core (Dni 1-7)
Backend musi umieć:

Zapisać konfigurację wskaźnika (nazwa, typ, parametry, symbole)
Obliczyć wskaźnik w czasie rzeczywistym na podstawie parametrów
Cache'ować wyniki z timestamp buckets
Zapisać strategię w formacie 4-sekcyjnym (S1/Z1/O1/Emergency)
Walidować strategię (czy wszystkie wskaźniki istnieją)
Wykonać backtest:

Załadować CSV
Odtworzyć dane z speed multiplier
Obliczać wskaźniki (z adjusted timing)
Ewaluować S1/Z1/O1/Emergency
Zapisać WSZYSTKIE wartości wskaźników przy każdej decyzji
Zwrócić szczegółowe wyniki per-trade


Wykonać paper/live trading:

Real-time stream danych
Obliczać wskaźniki live
Ewaluować strategię
Wykonywać/symulować zlecenia
Logować wszystko



Tydzień 2: Frontend Screens (Dni 8-14)
Dzień 8-9: Indicators Screen

Lista wskaźników (CRUD)
Dialog tworzenia (wszystkie pola jak opisane)
Test with Live Data
Chart View

Dzień 10-11: Strategy Builder

Formularz 4-sekcyjny
Dropdown ze wskaźnikami
Walidacja
Save/Load

Dzień 12-13: Backtest Configuration

Select data source
Select symbols
Select strategies
Speed multiplier
Risk limits

Dzień 14: Data Collection

Start dialog
Progress monitoring
List completed

Tydzień 3: Results & Polish (Dni 15-21)
Dzień 15-17: Backtest Results

Overall stats
Symbol breakdown z trade details
False positives analysis
Parameter performance
Chart View z timeline

Dzień 18-19: Live Trading

Session configuration
Live monitoring
Real-time indicator values
Activity log
Stop controls

Dzień 20: Comparison View - - Statystycznie Bezwartościowy (odrzucone przez biznesowego właściciela)

Backtest vs Live
Indicator value comparison
Signal consistency check

Dzień 21: E2E Testing & Documentation

Pełny workflow test
Bug fixes
User guide
Deploy