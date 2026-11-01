# P4 – mapa programů z panelu (2026-11-01)

**Postup:** `candy_watch.py --interval 5`, uživatel přepínal programy na panelu (myčka v klidu, nic se nespouštělo).
**Data:** `data/watch/2026-11-01_mapa-programu.jsonl` (188 čtení, 09:26–09:42).

## Programy na panelu (5)

| Panel (`r1`) | `Program` | `RemTime` | Odhad (délka + Hoover H-Dish) |
|---|---|---|---|
| 1 | P2 | 130 (s ExtraDry 140, viz P1) | Intenzivní 75 °C |
| 2 | P5 | 120 | Univerzální 60 °C |
| 3 | P8 | 230 | Eco 45 °C |
| 4 | P12 | 5 | Předmytí – výchozí po zapnutí |
| 5 | P19 | 39 | Rychlý (Hoover má na 5. pozici P13) |

Appka nabízí víc programů – mají zřejmě vlastní kódy `Px` mimo panel; zjistit při testech zápisu.

## Další pozorování

- `StatoWiFi` při mačkání panelu spadne na 0 a ~5 s po posledním stisku se vrátí na 1 → je to
  „dálkové ovládání povoleno“, ne stav sítě; panel má přednost. HTTP čtení funguje i při 0.
- Od 09:37 zůstal `StatoWiFi=0` až do konce logu – uživatel **vypnul režim dálkového ovládání**
  tlačítkem, aby mohl volně ovládat panel (v režimu vzdálené správy panel nereaguje plně).
- `r1` při rychlém přepínání krátce zaostává (2× P8 s `r1=4`, za 5 s opraveno) → spolehlivý je `Program`.
- ExtraDry prodlužuje P2 o 10 min (140 vs. 130).
