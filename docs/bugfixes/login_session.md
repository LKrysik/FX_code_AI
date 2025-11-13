Generowanie danych technical indicators zawiesza się i nie generuje danych dla przykładowego żądania:
INFO:     127.0.0.1:60446 - "GET /api/indicators/sessions/exec_20251102_113922_361d6250/symbols/AEVO_USDT/values HTTP/1.1" 200 OK


Ostatnio zapisane dane do tabeli SELECT * FROM indicators są z dnia  2025-11-02T16:30:02.000000Z. Czyli do tego momentu dane są generowane poprawnie. Potem coś następuje co psuje kod



Zanim naprawisz błędy zrób
Dokładna analiza architecture
przeanalizuj jak zmiana wpłynie na na program i inne moduły 
Testowanie każdej zmiany pojedynczo
Zweryfikuj swoje założenia, nie może być założeń bez weryfikacji
Śledź powiązane obiekty
Podczas przygotowywania propozycji zmian trzeba wziąć pod uwagę żeby nie powstawały alternatywne metody i kod który wykonuje to samo w dwóch miejscach oraz żeby unikać backward compatibility tylko od razu tworzyć docelowe działajace rozwiazanie 
Bardzo ważne żeby podczas zmian nie powstał dead code, żeby obiekty niepotrzebne były usuwane.
Jak juz będziesz miał uzasadnienie, to zadbaj o wprowadzenie zmian w kodzie w sposób uzasadniony, zapewniajacy spójność architektury, a jeżeli znajdziesz podczas analizy jakieś niespójności, wady programu, problemy architektoniczne to musisz je uzasadnić w kontekscie całego programu i wtedy zaraportować mi

Zweryfikuj czy wcześniej w danym obszarze nie było zmian które mogłyby uzasadnić, ze twoja propozycja naprawy jest niewłaściwa. Zobacz historię zmian kodu który zidentyfikowałeś jako błędny by ustalić czy twoje propozycje są na pewno właściwe. Uzasadnij.
Przy każdej okazji weryfikuj czy w danym obszarze analizy występują jakieś problemy z kodem, błędy architektoniczne, albo błędy logiczne, albo dead code, albo nie optymalne rozwiażania
Podczas zmian zadbaj by zaktualizować testy w run_tests.py (jeżeli są jakieś testy któe staną się nieaktualne to usuń, jeżeli trzeba zmodyfikować jakieś testy to zmodyfiku, jeżeli dodać to dodaj - jeżeli coś wynika ze zmian w kodzie to musi być aktualizacja testów i twoje uzasadnienie czemu wprowadzane są zmiamy w testach)
Zwróć uwagę czy nie istnieją takie problemy w innych miejscach. 
Musisz udowodnić, że nie modyfikujesz działającego kodu i nie powodujesz, że przestaje działać. 
Jeżeli naprawisz kod to dodawaj komentarz dlaczego to zostalo zmienione. Jeżeli istnieje już komentarz to sprawdź czy jest aktualny i czy odpowiada temu co zostało zmienione. Jeżeli nie to zaktualizuj komentarz.



Chcę żebys przeanalizował zidentyfikowane błędy w sposób przemyślany przygotował plan zmian w kodzie, i przygotował plan rozdzielenia prac na 6 agentów, 
w taki sposób by wymieniać informacje między agentami i mieć jednego koordynatora który będzie scalał prace, bedzie dbał o spójność, 
będzie wykrywal potencjalne błędy i ryzyka, problemy architektoniczne i będzie zlecal prace kolejnym agentom. 
Koordynator ma zadbac by prace przebiegały sprawnie, będzie monitorował postepy. 
Wszystkie swoje decyzje i przemyślenia uzasadniaj i podawaj dowody. Zmiany wynikajace z dokumentów muszą być przemyślane i uzasadnione.
Użyj agentów do weryfikacji kodu, czy nie ma niespójności, błędów, 
race condition i innych wad kodu zarówno architektonicznych jak i przepływu danych oraz całego porcesu. Niech każdy agent uzasadnia to co odkrył, 
dostarcza dowodów i przemyśleń jak to powinno być poprawione.

Masz realizować zadania za pomocą wielu agnetów równolegle, pamietaj że każdy agent musi sprawdzić historie zmian w obszarze który naprawia żeby nie poprawiać czegoś co zostalo z jakiegos powodu poprawione, ale agent musi to przeanalizować i uzasadnić czemu musi wykonać zmiane w tym obszarze kodu i czy nie jest to jakieś uwstecznienie. 