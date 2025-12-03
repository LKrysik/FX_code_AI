# System Agentów AI - FXcrypto

## Struktura

```
Driver Agent (1)
    │
    ├── Executor Agent A (kod backend)
    ├── Executor Agent B (kod frontend)
    ├── Executor Agent C (testy)
    └── Executor Agent D (infrastruktura)
```

## Role

| Agent | Rola | Odpowiedzialność |
|-------|------|------------------|
| **Driver** | Inicjator/Kierownik | Planuje, pyta, wymusza postępy, weryfikuje |
| **Executor** | Realizator | Pisze kod, testuje, raportuje problemy |

## Komunikacja

Driver → Executor:
- Zleca zadania z AC/DoD
- Pyta o status, blokery, ryzyka
- Weryfikuje czy nie ma mocków/halucynacji

Executor → Driver:
- Raportuje postęp z dowodami
- Zgłasza problemy i ryzyka
- Prosi o wyjaśnienia i priorytety

## Zasady

1. **Driver nigdy nie koduje** - tylko zarządza i weryfikuje
2. **Executor nigdy nie ogłasza sukcesu** - tylko raportuje fakty z dowodami
3. **Żadnych halucynacji** - każde twierdzenie ma dowód (output, test, curl)
4. **Ciągła pętla** - Driver wraca do początku po każdej iteracji

## Pliki

- `driver.md` - definicja Driver Agent
- `executor.md` - definicja Executor Agent
