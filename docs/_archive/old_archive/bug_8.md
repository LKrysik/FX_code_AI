Build Error

Failed to compile

Next.js (14.2.32) is outdated (learn more)
./src/components/strategy/ConditionBlock.tsx
Error: 
  × Unexpected token `Paper`. Expected jsx identifier
     ╭─[C:\Users\lukasz.krysik\Desktop\FXcrypto\code_ai\frontend\src\components\strategy\ConditionBlock.tsx:94:1]
  94 │   };
  95 │ 
  96 │   return (
  97 │     <Paper
     ·      ─────
  98 │       elevation={1}
  99 │       sx={{
 100 │         p: 2,
     ╰────

Caused by:
    Syntax Error

Import trace for requested module:
./src/components/strategy/ConditionBlock.tsx
./src/components/strategy/StrategyBuilder4Section.tsx
./src/app/strategy-builder/page.tsx


Znalazłem problem! W pliku ConditionBlock.tsx brakuje właściwości id w interfejsie Condition i w użyciu.
Porównując oba pliki:
W StrategyBuilder4Section.tsx (linia 145):
typescriptconst newCondition: Condition = {
  id: `${section}_${Date.now()}`,  // ← TU JEST id
  indicatorId: '',
  operator: '>',
  value: 0,
};
W ConditionBlock.tsx nie ma obsługi condition.id!
Musisz dodać id do typu Condition w pliku @/types/strategy.ts:
typescriptexport interface Condition {
  id: string;  // ← DODAJ TO
  indicatorId: string;
  operator: '>' | '<' | '>=' | '<=' | '==';
  value: number;
}
LUB jeśli id już jest w typie, to problem jest w tym, że w ConditionBlock.tsx używasz condition.id (np. w key props), ale kompilator TypeScript może mieć problem z rozpoznaniem tego typu.
Sprawdź plik src/types/strategy.ts i upewnij się, że:

Condition ma pole id: string
Plik jest poprawnie wyeksportowany
Nie ma błędów składniowych w tym pliku

Jeśli strategy.ts wygląda dobrze, wyślij mi jego zawartość, to znajdę dokładny problem.