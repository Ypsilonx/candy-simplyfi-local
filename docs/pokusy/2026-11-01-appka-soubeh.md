# P3 – souběh s appkou, výběr programu v appce, dvířka (2026-11-01)

**Cíl:** zjistit, jestli souběh appky simply-Fi a čtení z PC zasekává modul, a co appka do myčky posílá.
**Výchozí stav:** po tvrdém restartu, myčka v klidu, appka otevřená na mobilu. Jednotlivá čtení `http-read.json`.

| Čas | Akce uživatele | Stav z API |
|---|---|---|
| 09:19 | appka otevřená (nastaveno „použít poslední cyklus“) | `StatoDWash=2`, `Program=P12`, `r1=4`, `RemTime=5` – beze změny |
| 09:23 | přepnut program **v appce** | beze změny (`P12`, `r1=4`) |
| 09:24 | fyzicky otevřena dvířka | `OpenDoor` 0→1, jinak beze změny |

## Závěry

- Souběh appky a PC: 3 čtení prošla, modul se nezasekl. Ranní zaseknutí souběhem zatím nepotvrzeno.
- API je živé (dvířka se projevila okamžitě) → **výběr programu v appce se do myčky neposílá**,
  appka ho drží u sebe a nejspíš ho odešle až se startem (`Program=…&w1=…&StartStop=1`).
- Na panelu je po restartu **P4**, API hlásí `Program=P12`, `r1=4` → `r1` = číslo programu na displeji,
  `Program` = interní kód. (Uživatel potvrdil P4 na panelu; P1 u nočního cyklu zatím nepotvrzeno.)
- Volba appky „použít poslední cyklus“ myčku po restartu nepřestaví – ta po restartu vždy začíná na P4.
