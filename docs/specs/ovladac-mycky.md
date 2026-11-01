# Návrh: vlastní ovladač myčky místo appky simply-Fi

## Cíl

Webová stránka (PC i mobil v domácí síti), která nahradí appku: přehled programů s délkou a povolenými
volbami, start (i „konec v HH:MM“), stop, nastavení myčky a **vlastní evidence údržby**, která se neztratí.
Hotovo v1 = spustím program s volbami z mobilu, vidím průběh a zbývající čas, po skončení se cyklus zapíše
do historie a stránka ukáže, za kolik cyklů čistit filtr a odvápnit.

## Klíčová rozhodnutí

1. **Jeden „správce“ myčky.** Server je jediný, kdo s myčkou mluví (čte á 15 s jako appka, příkazy
   sériově). Stránky se ptají serveru, ne myčky → žádný souběh spojení, který zasekává modul.
2. **Technologie (rozhodnuto):** backend **FastAPI + uvicorn** přes `uv`, frontend **vanilla JS bez
   bundleru** (živý přehled stavu = hodně stavu v prohlížeči). **Vše lokální, žádné CDN ani internet** –
   případné knihovny přibalené ve `static/vendor/`. Vývoj na Windows (hlavní PC), provoz na Linuxu
   (druhé PC, systemd). Nástroje `scan`/`watch`/`send` zůstávají jen na standardní knihovně.
3. **Katalog programů jako data** (`candy/programs.json`): kód, české jméno, popis, `w1`, teplota,
   jmenovitá délka, povolené volby (maska z appky). Délky se **doučí z provozu** (`RemTime` po startu
   s danými volbami se uloží) – appkové délky u nás nesedí vždy (Eco 230 vs. 180).
4. **Pravidla voleb** podle appky: povolené jen bity z masky programu; vzájemně se vylučují
   ExtraDry ↔ ½ náplň ↔ Eco (páry 3, 5, 6); 3v1 se kombinuje volně. 🟡 Otevírání dvířek (16) asi
   náš model nemá (neověřeno) – v UI skryto, dokud se neověří.
5. **Historie a údržba** v `data/historie.jsonl` (jeden řádek = cyklus: start, konec, program, volby,
   délka, fáze). Počítadla: filtr á 100 cyklů, odvápnění podle tvrdosti `r7` (110…85). Tlačítka
   „filtr vyčištěn“ / „odvápněno“ zapíšou značku. Nic se nedrží v telefonu ani v cloudu.
6. **„Konec v HH:MM“**: `DelayStart = round((konec − teď − délka) / 30 min)`, UI ukáže skutečný
   odhad konce (±15 min) – žádné ujíždění jako v appce.
7. **Bezpečnost**: příkaz jen při `StatoWiFi=1`, po příkazu ověření čtením stavu (modul hlásí SUCCESS
   i na ignorované). Server poslouchá jen v domácí síti, bez přihlašování (v1).

## Programy a volby (z appky + naše měření)

| Kód | Název | `w1` | Délka (naše/appka) | ExtraDry | ½ náplň | Eco | 3v1 |
|---|---|---|---|---|---|---|---|
| P2 | Intensivní 75 °C | 1 | 130 / 130 | ✔ | ✔ | ✔ | ✔ |
| P5 | Univerzální 60 °C | 2 | 120 / 120 | ✔ | ✔ | ✔ | ✔ |
| P8 | Eco 45 °C | 3 | 230 / 180 | ✔ | ✔ | ✔ | ✔ |
| P12 | Předmytí | 4 | 5 / 5 | – | – | – | ✔ |
| P19 | ZOOM 39′ 60 °C | 5 | 39 / 39 | – | – | ✔ | ✔ |
| P9, P16, P17, P20 | Jemný 45 °C, Auto denní 55–65 °C, Noc 55 °C, Rychlý 32′ 50 °C | ? | – / 85, 95, 240, 24 | | | | |

Programy jen z appky: `w1` neznámé → v1 je nabídne jako „experimentální“ až po ověření startem.

## Struktura modulů

```
candy_netscan/            dnešní nástroje (scan, watch, send) – jen stdlib
  client.py               NOVÉ: XOR, čtení stavu, odeslání příkazu (sdílí watch, send i server)
ovladac/                  NOVÉ: aplikace
  config.py               Settings (pydantic-settings, .env): IP, klíč, interval, dry_run, cesta k datům
  services/
    model.py              význam polí stavu → čitelný stav (čisté funkce)
    programs.py + programs.json   katalog programů, pravidla voleb, výpočet „konec v“
    history.py            detekce začátku/konce cyklu, zápis do data/historie.jsonl, údržba
    appliance.py          jediný správce myčky: poller (task v lifespan), cache stavu, fronta příkazů
  routers/api.py          /api/stav, /api/programy, /api/start, /api/stop, /api/nastaveni, /api/udrzba
  main.py                 FastAPI app, lifespan, statické soubory
  static/                 index.html, css/, js/ (api.js, app.js …), vendor/ (jen lokální kopie)
tests/                    unit testy model/programs/history (na reálných logech z data/watch/)
```

## Otevřené otázky

1. Notifikace „hotovo“ / „chybí sůl“ – později (bez internetu jen v rámci stránky / lokálně).
2. Pípání na konci: `BM` (r6) už je 0 a stejně pípá → zjistit při provozu, co ho ovládá (ladíme za běhu).
3. Délky s volbami (ExtraDry +10 min u P2) a ověření programů z appky – doplní se z historie za provozu.
