# P9 – dvířka během běhu a odložený start (2026-11-01)

## A) Otevření dvířek během programu

Start P12 přes `send.py`, čtení stavu á 3 s, uživatel otevřel a zavřel dvířka, pak `Reset=1`.

| Čas | Událost | Stav |
|---|---|---|
| 10:57:04 | start P12 (stav čten 1 s po příkazu) | `StartStop` 0→1, `StatoDWash` 2→**4**, `StatoWiFi` 1→0, `r5` 1→0 |
| 10:57:08 | | `StatoDWash` 4→3, `StatoWiFi` 0→1 |
| 10:57:17 | dvířka otevřena | `OpenDoor` 0→1, `StatoDWash` 3→**4** |
| 10:57:27 | dvířka zavřena | `OpenDoor` 1→0 |
| 10:57:30 | | `StatoDWash` 4→3 – pokračuje sama |
| 10:58:46 | `Reset=1` (čteno 1 s po) | `StatoDWash` 3→**1**, `Program` P12→**P0**, `RemTime` 5→0, `Reset` 0→1, `StartStop` 1→0, `r5` 0→1 |
| 10:58:54 | | `StatoDWash=2`, `Program=P12`, `Reset=0` (zpět ve výběru), `r2` zůstává 2 |

Závěry:
- ✅ `StatoDWash=4` = pauza; otevření dvířek běžící program pozastaví, po zavření ~3 s pokračuje sám.
- ✅ Hned po startu krátce `StatoDWash=4` a `StatoWiFi=0` (~4 s) – rozběh; neznamená chybu.
- ✅ Reset proběhne přes krátký stav `StatoDWash=1` / `Program=P0` / `Reset=1` (~1–8 s), pak výběr (2).
- `r2` po stopu drží poslední fázi – mimo běh ho nebrat vážně.

## B) Odložený start a jeho zrušení

| Čas | Příkaz | Stav |
|---|---|---|
| 10:59:13 | start P12 s `DelayStart=1` | `DelayStart` 0→**30**, `StartStop` 0→1, `StatoDWash` 2→3, `r2` →0, `r5` 1→0 |
| 10:59:31 | | `StatoDWash=3`, `DelayStart=30`, `RemTime=5`, `r2=0` |
| 11:00:39 | | `DelayStart=29` – odpočítává po minutách |
| 11:00:40 | `Reset=1` | `StartStop` 1→0, `StatoDWash` 3→2, `r5` 0→1 (`DelayStart` v diffu beze změny) |

Závěry:
- ✅ Příkaz `DelayStart` = počet **půlhodin**, stav `DelayStart` = **zbývající minuty** do startu.
- ✅ Čekající odložený start: `StatoDWash=3` (ne 99), `StartStop=1`, `r2=0`, `DelayStart > 0`.
- ✅ `Reset=1` odložený start spolehlivě zruší.
- Pro „konec v HH:MM“: `DelayStart = round((konec − teď − délka programu) / 30 min)` → přesnost ±15 min.
