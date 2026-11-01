# P2 – čtení `http-getStatistics.json` (2026-11-01)

**Cíl:** bezpečně (jen GET) zjistit, co vrací endpoint statistik.
**Stav myčky:** po dokončeném cyklu P2 (`StatoDWash=5`), dvířka otevřená, `StatoWiFi=1`.

## Průběh

| Čas | Dotaz | Výsledek |
|---|---|---|
| 08:24 | `http-read.json?encrypted=1` | OK (poslední funkční čtení) |
| ~08:56 | `http-getStatistics.json?encrypted=1` | timeout 8 s |
| ~08:57 | `http-getStatistics.json?encrypted=1` | timeout 25 s |
| ~08:57 | `http-read.json?encrypted=1` (3 s po timeoutu) | `Remote end closed connection without response` |
| 08:57:39–08:58:29 | 6× `http-read.json?encrypted=1` po 10 s | vždy `Remote end closed connection` |
| ~08:59 | ping | odpovídá (20–100 ms) |

## Závěry

- `http-getStatistics.json` neodpověděl. **Po něm HTTP server přestal obsluhovat i `http-read.json`**,
  přestože modul je na síti. Hypotézy: (a) dotaz modul zasekl, (b) modul přešel do úsporného/jiného
  režimu nezávisle (otevřená dvířka po konci cyklu, myčka se vypíná), (c) souběh s cloudem.
- ⚠️ Než se `getStatistics` zkusí znovu, ověřit, že čtení stavu funguje, a otestovat ho jen jednou.

## Výsledek obnovy

- Během pokusu byla na mobilu zapnutá appka simply-Fi. Po jejím úplném ukončení čtení stále
  `Remote end closed connection` → appka (sama) příčinou není.
- 09:14 po tvrdém restartu myčky (vypnout/zapnout) čtení opět funguje.
- Stav po restartu: `StatoDWash=2`, `StartStop=0`, `Program=P12`, `r1=4`, `r2=0`, `RemTime=5`,
  `TreinUno=0`, `ExtraDry=0` (volby se restartem vynulovaly).

## Kontrolní opakování (09:15, appka zavřená, po restartu)

- 1× `getStatistics` → timeout 25 s; 5 s poté `http-read.json` **OK**.
- ⇒ `getStatistics` sám modul **nezasekává**, jen neodpovídá (na myčce nejspíš nepodporován).
- Ranní zaseknutí mělo jinou příčinu. Hlavní hypotéza: souběh s otevřenou appkou simply-Fi
  (modul ESP zvládá málo spojení naráz). Ověřit pokusem se zapnutou appkou.
