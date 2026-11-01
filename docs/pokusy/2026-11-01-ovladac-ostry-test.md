# P11 – ostrý test ovladače z webového UI (2026-11-01)

**Cíl:** ověřit celý řetězec stránka → FastAPI server → myčka naostro (T6 plánu ovladače).
**Postup:** server `DRY_RUN=false uv run uvicorn ovladac.main:app` (jediný klient myčky, appka zavřená),
uživatel u myčky, dálkové ovládání zapnuté. V UI (Playwright, Edge) výběr P12 → Spustit → potvrzení,
po ~25 s Zastavit → potvrzení.

## Průběh

| Čas | Akce | Výsledek |
|---|---|---|
| 12:12:07 | start P12 (`DelayStart=0&…&Program=P12&…&OpzProg=0&w1=4&StartStop=1&Eco=0`) | SUCCESS; po 5 s `StatoDWash` 2→3, `StartStop` 0→1, `DelayStart` 29→0, `r5` 1→0; UI „Myje / Mytí, zbývá 5 min“ |
| 12:12:38 | stop `Reset=1` | po 5 s „Připraveno“, P12, `aktivni=False` |
| 12:12:44 | tracker | do `data/historie.jsonl` 1 cyklus P12 `zruseno` (32 s); počítadla údržby beze změny (100/100) |

## Závěry

- Ovladač naostro funguje: start, stop, ověření čtením, detekce a zápis cyklu. ✅
- `DelayStart` mimo čekání drží starou hodnotu (tu bylo 29 ve stavu výběr) a start ji vynuluje. ✅
  Ovladač ji proto mimo čekání ignoruje (`model.interpret`).
- Chyba UI nalezená při testu: štítek „Zkušební režim“ svítil i naostro – `.badge { display }`
  přebil atribut `hidden`. Opraveno v `base.css` (`[hidden] { display: none !important; }`).
