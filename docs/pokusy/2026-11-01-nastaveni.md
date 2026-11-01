# P10 – nastavení myčky zápisem: zvuk, poslední cyklus, tvrdost vody (2026-11-01)

**Výchozí stav:** klid (`StatoDWash=2`), dálkové ovládání zapnuté, `r6=0`, `r7=2`, `r8=1`, `r15=1`.
**Postup:** `python -m candy_netscan.send raw "<parametr>" --send --wait 5`, každé nastavení tam a zpět.

| Čas | Příkaz | Změna stavu |
|---|---|---|
| 11:04:03 | `BM=1` | `r6` 0→1 |
| 11:04:12 | `BM=0` | `r6` 1→0 |
| 11:04:22 | `LC=0` | `r8` 1→0 |
| 11:04:31 | `LC=1` | `r8` 0→1 |
| 11:04:40 | `HL=3` | `r7` 2→3 |
| 11:04:49 | `HL=2` | `r7` 3→2 |

## Závěry

- ✅ `BM` = zvuková signalizace → `r6`; `LC` = pamatovat poslední cyklus → `r8`; `HL` = tvrdost vody → `r7`.
- ✅ Změna se projeví do 5 s; odpověď `SUCCESS`. Vše vráceno na původní hodnoty.
- Tvrdost: index 0–5 (appka: `hardness_values` 110…85 cyklů do odvápnění) – rozsah zápisem neověřen nad 3.
- Tvrdost: index `HL` = `r7` = pořadí v seznamu appky (0 velmi měkká … 5 velmi tvrdá), viz protokol.

## Restart myčky (11:05–11:11)

`BM=1` → uživatel vypnul a zapnul myčku tlačítkem a zapnul dálkové ovládání → čtení 11:11:39:
`r6=1`, `r7=2`, `r8=1` (beze změny), `Program=P12`, `TreinUno=0`, `ExtraDry=0`. Pak `BM=0` vráceno.

- ✅ Nastavení `BM`/`HL`/`LC` **jsou uložená v myčce a restart tlačítkem přežijí**.
- Restart nuluje jen výběr programu (P12) a volby programu (3v1, ExtraDry) – viz P2.
- ⇒ „Ztráta nastavení“ v appce se týká údajů, které drží **jen appka/cloud** (údržba, tablety,
  počítadla), ne nastavení myčky. Odpojení od proudu netestováno.
