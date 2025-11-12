authStore.ts:70 
 POST http://localhost:8080/api/v1/auth/login 429 (Too Many Requests)
login	@	authStore.ts:70
handleDemoLogin	@	LoginForm.tsx:84
onClick	@	LoginForm.tsx:219



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