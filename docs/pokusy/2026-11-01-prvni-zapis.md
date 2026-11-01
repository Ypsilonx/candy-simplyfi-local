# P8 – první zápis: start P12 a stop (2026-11-01)

**Výchozí stav:** myčka prázdná, zapnutá, dálkové ovládání zapnuté (`StatoWiFi=1`), `StatoDWash=2`, `Program=P12`.
**Nástroj:** `python -m candy_netscan.send … --send` (čtení stavu před a 5 s po příkazu).

| Čas | Příkaz (plaintext) | Odpověď | Změna stavu |
|---|---|---|---|
| 10:40:30 | `DelayStart=0&ExtraDry=0&OpenDoorOpt=0&TreinUno=0&Program=P12&MetaCarico=0&OpzProg=0&w1=4&StartStop=1&Eco=0` | `{"response":"SUCCESS"}` (šifrovaně) | `StartStop` 0→1, `StatoDWash` 2→3, `r2` 0→2 |
| 10:40:43 | `Reset=1` | `{"response":"SUCCESS"}` | `StartStop` 1→0, `StatoDWash` 3→2, `r5` 0→1 |

## Závěry

- ✅ Lokální zápis funguje: formát řady nautilus (`Program=P<cycleId>&w1=<pozice>`) je pro naši myčku správný.
- ✅ Odpověď na zápis je šifrovaná stejným XOR klíčem: `{"response":"SUCCESS"}`.
- ✅ `Reset=1` zastaví běžící program a vrátí myčku do výběru (`StatoDWash=2`).
- `r5` 0→1 po stopu (v P1 1→0 v 16. min) – 🟡 vypouštění / čerpadlo?
- Uživatel u myčky: po startu se rozběhlo čerpadlo a napouštění vody, chvíli běžela; po `Reset=1`
  zablikaly všechny LED, ticho a návrat do stavu před startem (výběr programu).
